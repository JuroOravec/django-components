import inspect
import types
from collections import deque
from contextlib import contextmanager
from dataclasses import dataclass
from typing import (
    Any,
    Callable,
    ClassVar,
    Deque,
    Dict,
    Generator,
    Generic,
    List,
    Literal,
    Mapping,
    NamedTuple,
    Optional,
    Protocol,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
)

from django.core.exceptions import ImproperlyConfigured
from django.forms.widgets import Media as MediaCls
from django.http import HttpRequest, HttpResponse
from django.template.base import UNKNOWN_SOURCE, NodeList, Template, TextNode, Origin
from django.template.context import Context
from django.template.loader import get_template
from django.template.loader_tags import BLOCK_CONTEXT_KEY
from django.utils.html import conditional_escape
from django.views import View

from django_components.app_settings import ContextBehavior
from django_components.component_media import ComponentMedia, ComponentMediaInput
from django_components.component_registry import ComponentRegistry
from django_components.component_registry import registry as registry_
from django_components.context import (
    _COMPONENT_SLOT_CTX_CONTEXT_KEY,
    _REGISTRY_CONTEXT_KEY,
    _ROOT_CTX_CONTEXT_KEY,
    get_injected_context_var,
    make_isolated_context_copy,
)
from django_components.dependencies import (
    RenderType,
    cache_inlined_css,
    cache_inlined_js,
    postprocess_component_html,
)
from django_components.expression import Expression, RuntimeKwargs, safe_resolve_list
from django_components.node import BaseNode
from django_components.plugin import (
    OnDataAfterContext,
    OnDataBeforeContext,
    OnRenderAfterContext,
    OnRenderBeforeContext,
    OnSlotsResolvedContext,
    OnTemplateLoadContext,
)
from django_components.plugin_runner import plugins
from django_components.slots import (
    ComponentSlotContext,
    Slot,
    SlotContent,
    SlotFunc,
    SlotIsFilled,
    SlotName,
    SlotRef,
    SlotResult,
    _is_extracting_fill,
    _nodelist_to_slot_render_func,
    resolve_fills,
)
from django_components.template import cached_template
from django_components.util.logger import trace_msg
from django_components.util.misc import _escape_js, extract_annotated_metadata, gen_id, scope_css
from django_components.util.validation import validate_type

# TODO_REMOVE_IN_V1 - Users should use top-level import instead
# isort: off
from django_components.component_registry import AlreadyRegistered as AlreadyRegistered  # NOQA
from django_components.component_registry import ComponentRegistry as ComponentRegistry  # NOQA
from django_components.component_registry import NotRegistered as NotRegistered  # NOQA
from django_components.component_registry import register as register  # NOQA
from django_components.component_registry import registry as registry  # NOQA

# isort: on

COMP_ONLY_FLAG = "only"

# Tracks all Component classes, so we an easily find them end export their JS and CSS
# during collectstatic
_ALL_COMPONENTS: Set[Type["Component"]] = set()

# Define TypeVars for args and kwargs
ArgsType = TypeVar("ArgsType", bound=tuple, contravariant=True)
KwargsType = TypeVar("KwargsType", bound=Mapping[str, Any], contravariant=True)
# TODO - Do tests for how slots behave if we pass None?
SlotsType = TypeVar("SlotsType", bound=Mapping[SlotName, SlotContent])
DataType = TypeVar("DataType", bound=Mapping[str, Any], covariant=True)
JsDataType = TypeVar("JsDataType", bound=Mapping[str, Any])
CssDataType = TypeVar("CssDataType", bound=Mapping[str, Any])

# Rename, so we can use `type()` inside functions with kwrags of the same name
_type = type


@dataclass(frozen=True)
class RenderInput(Generic[ArgsType, KwargsType, SlotsType]):
    context: Context
    args: ArgsType
    kwargs: KwargsType
    slots: SlotsType
    type: RenderType
    render_dependencies: bool


@dataclass()
class RenderStackItem(Generic[ArgsType, KwargsType, SlotsType]):
    input: RenderInput[ArgsType, KwargsType, SlotsType]
    is_filled: Optional[SlotIsFilled]


class ViewFn(Protocol):
    def __call__(self, request: HttpRequest, *args: Any, **kwargs: Any) -> Any: ...  # noqa: E704


class ComponentVars(NamedTuple):
    """
    Type for the variables available inside the component templates.

    All variables here are scoped under `component_vars.`, so e.g. attribute
    `is_filled` on this class is accessible inside the template as:

    ```django
    {{ component_vars.is_filled }}
    ```
    """

    is_filled: Dict[str, bool]
    """
    Dictonary describing which component slots are filled (`True`) or are not (`False`).

    <i>New in version 0.70</i>

    Use as `{{ component_vars.is_filled }}`

    Example:

    ```django
    {# Render wrapping HTML only if the slot is defined #}
    {% if component_vars.is_filled.my_slot %}
        <div class="slot-wrapper">
            {% slot "my_slot" / %}
        </div>
    {% endif %}
    ```

    This is equivalent to checking if a given key is among the slot fills:

    ```py
    class MyTable(Component):
        def get_context_data(self, *args, **kwargs):
            return {
                "my_slot_filled": "my_slot" in self.input.slots
            }
    ```
    """


class ComponentMeta(type):
    def __new__(mcs, name: str, bases: Tuple[Type, ...], attrs: Dict[str, Any]) -> Type:
        cls = cast(Type["Component"], super().__new__(mcs, name, bases, attrs))

        paths_to_resolve = {
            "template_name": cls.template_name,
            "js_name": cls.js_name,
            "css_name": cls.css_name,
        }
        cls._media = ComponentMedia(cls, cls.Media, paths_to_resolve)

        _ALL_COMPONENTS.add(cls)

        # TODO REMOVE ALL THE REST AROUND THIS WHEN COMMITTING
        cls.js = cls._get_static_asset("JS", inlined_attr="js", file_attr="js_name")
        cls.css = cls._get_static_asset("CSS", inlined_attr="css", file_attr="css_name")

        # TODO THIS IS FOR LATER
        cls.js_lang = _get_content_language(cls, "js") or cls.js_lang
        cls.css_lang = _get_content_language(cls, "css") or cls.css_lang

        return cls


def _get_content_language(
    comp_cls: Type["Component"],
    kind: Literal["template", "js", "css"],
) -> Optional[str]:
    from typing import get_type_hints  # TODO

    hints = get_type_hints(comp_cls, include_extras=True)

    if kind == "js":
        # annotated_attr = "js_name" if comp_cls.js_name else "js" # TODO
        annotated_attr = "js"
        _, meta = extract_annotated_metadata(hints[annotated_attr])
    elif kind == "css":
        # annotated_attr = "css_name" if comp_cls.css_name else "css" # TODO
        annotated_attr = "css"
        _, meta = extract_annotated_metadata(hints[annotated_attr])
    # TODO
    # elif kind == "template":
    #     annotated_attr = "template"

    lang = meta[0] if len(meta) else None
    return lang


# NOTE: We use metaclass to automatically define the HTTP methods as defined
# in `View.http_method_names`.
class ComponentViewMeta(type):
    def __new__(cls, name: str, bases: Any, dct: Dict) -> Any:
        # Default implementation shared by all HTTP methods
        def create_handler(method: str) -> Callable:
            def handler(self, request: HttpRequest, *args: Any, **kwargs: Any):  # type: ignore[no-untyped-def]
                component: "Component" = self.component
                return getattr(component, method)(request, *args, **kwargs)

            return handler

        # Add methods to the class
        for method_name in View.http_method_names:
            if method_name not in dct:
                dct[method_name] = create_handler(method_name)

        return super().__new__(cls, name, bases, dct)


class ComponentView(View, metaclass=ComponentViewMeta):
    """
    Subclass of [`django.views.View`](https://docs.djangoproject.com/en/5.1/ref/class-based-views/base/#view)
    that accepts a [`Component`](../api#django_components.Component) instance.

    This class makes it possible to define `get()`, `post()`, `put()`, `delete()`, etc. methods on the component.

    It automatically creates methods for all HTTP methods defined in
    [`View.http_method_names`](https://docs.djangoproject.com/en/5.1/ref/class-based-views/base/#django.views.generic.base.View.http_method_names).
    These methods forward the handlers to the component.

    So when e.g. a GET request is passed to `ComponentView.get()`, it will pass it to
    `Component.get()`.

    ```python
    class ComponentView(View):
        def get(self, request: HttpRequest, *args: Any, **kwargs: Any):
            return self.component.get(request, *args, **kwargs)
    ```

    This class is also used by [`Component.as_view()`](../api#django_components.Component.as_view).

    Learn more about using [components as Django views](../../concepts/fundamentals/components_as_views).
    """

    # NOTE: This attribute must be declared on the class for `View.as_view()` to allow
    # us to pass `component` kwarg.
    component: "Component" = cast("Component", None)
    """Component instance associated with this view."""

    def __init__(self, component: "Component", **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.component = component


class Component(
    Generic[ArgsType, KwargsType, SlotsType, DataType, JsDataType, CssDataType],
    metaclass=ComponentMeta,
):
    # #####################################
    # PUBLIC API (Configurable by users)
    # #####################################

    template_name: Optional[str] = None
    """
    Filepath to the Django template associated with this component.

    The filepath must be relative to either the file where the component class was defined,
    or one of the component directories defined by
    [`COMPONENTS.dirs`](../settings#django_components.app_settings.ComponentsSettings.dirs)
    or
    [`COMPONENTS.app_dirs`](../settings#django_components.app_settings.ComponentsSettings.app_dirs).

    Only one of
    [`template_name`](../api#django_components.Component.template_name),
    [`get_template_name()`](../api#django_components.Component.get_template_name),
    [`template`](../api#django_components.Component.template)
    or
    [`get_template()`](../api#django_components.Component.get_template)
    must be defined.

    **Example**

    Assuming this project layout:
    ```txt
    |- components/
      |- table/
        |- table.html
        |- table.css
        |- table.js
    ```

    Template name can be either relative to the python file (`components/table/table.py`):

    ```python
    class Table(Component):
        template_name = "table.html"
    ```

    Or relative to one of the directories in `COMPONENTS.dirs` or `COMPONENTS.app_dirs`
    (`components/`):

    ```python
    class Table(Component):
        template_name = "table/table.html"
    ```
    """

    def get_template_name(self, context: Context) -> Optional[str]:
        """
        Same as [`Component.template_name`](../api#django_components.Component.template_name),
        but allows to dynamically resolve the template name at render time.

        Only one of
        [`template_name`](../api#django_components.Component.template_name),
        [`get_template_name()`](../api#django_components.Component.get_template_name),
        [`template`](../api#django_components.Component.template)
        or
        [`get_template()`](../api#django_components.Component.get_template)
        must be defined.

        See [`Component.template_name`](../api#django_components.Component.template_name)
        for more info and examples.

        Args:
            context (Context): The Django template\
                [`Context`](https://docs.djangoproject.com/en/5.1/ref/templates/api/#django.template.Context)\
                in which the component is rendered.
        
        Returns:
            Optional[str]: The filepath to the template.
        """
        return None

    template: Optional[Union[str, Template]] = None
    """
    Inlined Django template associated with this component. Can be a plain string
    or a [`Template`](https://docs.djangoproject.com/en/5.1/topics/templates/#template) instance.

    Only one of
    [`template_name`](../api#django_components.Component.template_name),
    [`get_template_name()`](../api#django_components.Component.get_template_name),
    [`template`](../api#django_components.Component.template)
    or
    [`get_template()`](../api#django_components.Component.get_template)
    must be defined.

    **Example**

    Template name can be either plain string:

    ```python
    class Table(Component):
        template = '''
          <div>
            {{ my_var }}
          </div>
        '''
    ```

    Or a Template instance:

    ```python
    class Table(Component):
        template = Template('''
          <div>
            {{ my_var }}
          </div>
        ''')
    ```

    # Syntax highlighting
    
    When using the inlined template, you can enable syntax highlighting.
    Learn more about [syntax highlighting](../../guides/setup/syntax_highlight).
    """

    # TODO - REMOVE THE `Type["Component"]`?
    def get_template(self, context: Context) -> Optional[Union[str, Template, Type["Component"]]]:
        """
        Same as [`Component.template`](../api#django_components.Component.template),
        but allows to dynamically resolve the template at render time.

        This function can also return another Component class, in which case the
        template of that component will be used.

        Only one of
        [`template_name`](../api#django_components.Component.template_name),
        [`get_template_name()`](../api#django_components.Component.get_template_name),
        [`template`](../api#django_components.Component.template)
        or
        [`get_template()`](../api#django_components.Component.get_template)
        must be defined.

        See [`Component.template`](../api#django_components.Component.template) for more info and examples.

        Args:
            context (Context): The Django template\
            [`Context`](https://docs.djangoproject.com/en/5.1/ref/templates/api/#django.template.Context)\
            in which the component is rendered.
        
        Returns:
            Optional[Union[str, Template, Type[Component]]]: The inlined Django template string or\
            a [`Template`](https://docs.djangoproject.com/en/5.1/topics/templates/#template) instance
            or a Component class.
        """
        return None

    def get_context_data(self, *args: Any, **kwargs: Any) -> DataType:
        return cast(DataType, {})

    def get_js_data(self, *args: Any, **kwargs: Any) -> JsDataType:
        """Variables exposed to the associated JS script."""
        return cast(JsDataType, {})

    def get_css_data(self, *args: Any, **kwargs: Any) -> CssDataType:
        return cast(CssDataType, {})

    js: Optional[str] = None
    """Inlined JS associated with this component."""

    js_name: Optional[str] = None  # TODO UPDATE DOCS
    """Inlined JS associated with this component."""

    js_lang: str = "js"  # TODO

    # TODO: Document that, by default, the inlined JS is loaded in the browser as a module script (type="module").
    #       If the user wants to use non-module script, they can override `js_tag` and set `js_wrap_in_function=True`.
    #       # TODO THIS IS NO LONGER TRUE!!! SCRIPTS ARE LOADED AS SYNC SCRIPTS, SO THEIR ORDER IS GUARANTEED
    js_wrap_in_function: bool = False

    js_autoload: bool = True

    @classmethod
    def js_tag(cls, content: str) -> str:
        if content is None:
            raise ValueError(f"{cls.__name__}: `js_tag()` called with no content defined")
        return f'<script>{_escape_js(content)}</script>'
        # TODO: In django-vue we override this to add `type="module"`
        # return f'<script type="module">{_escape_js(content)}</script>'

    css: Optional[str] = None
    """Inlined CSS associated with this component."""

    css_name: Optional[str] = None  # TODO UPDATE DOCS
    """Inlined CSS associated with this component."""

    css_scoped: Optional[bool] = False

    css_lang: str = "css"  # TODO

    css_autoload: bool = True

    @classmethod
    def css_tag(cls, content: str) -> str:
        if content is None:
            raise ValueError(f"{cls.__name__}: `css_tag()` called with no content defined")
        return f"<style>{content}</style>"

    """
    Normalized definition of JS and CSS media files associated with this component.

    NOTE: This field is generated from Component.Media class.
    """
    media_class: MediaCls = MediaCls
    Media: Optional[type[ComponentMediaInput]] = None
    """Defines JS and CSS media files associated with this component."""

    response_class = HttpResponse
    """This allows to configure what class is used to generate response from `render_to_response`"""
    View = ComponentView

    # #####################################
    # PUBLIC API - HOOKS
    # #####################################

    def on_render_before(self, context: Context, template: Optional[Template]) -> None:
        """
        Hook that runs just before the component's template is rendered.

        You can use this hook to access or modify the context or the template.
        """
        pass

    def on_render(self, context: Context, template: Optional[Template]) -> SlotResult:
        """
        Hook that runs just before the component's template is rendered.

        You can use this hook to access or modify the context or the template.
        """
        return template.render(context) if template is not None else ""

    def on_render_after(self, context: Context, template: Optional[Template], content: str) -> Optional[SlotResult]:
        """
        Hook that runs just after the component's template was rendered.
        It receives the rendered output as the last argument.

        You can use this hook to access the context or the template, but modifying
        them won't have any effect.

        To override the content that gets rendered, you can return a string or SafeString
        from this hook.
        """
        pass

    # #####################################
    # MISC
    # #####################################

    _class_hash: ClassVar[int]
    _media: ComponentMedia

    # NOTE: These paths are set by the metaclass
    _comp_path_absolute: Optional[str] = None
    _comp_path_relative: Optional[str] = None

    def __init__(
        self,
        registered_name: Optional[str] = None,
        component_id: Optional[str] = None,
        outer_context: Optional[Context] = None,
        registry: Optional[ComponentRegistry] = None,  # noqa F811
    ):
        # When user first instantiates the component class before calling
        # `render` or `render_to_response`, then we want to allow the render
        # function to make use of the instantiated object.
        #
        # So while `MyComp.render()` creates a new instance of MyComp internally,
        # if we do `MyComp(registered_name="abc").render()`, then we use the
        # already-instantiated object.
        #
        # To achieve that, we want to re-assign the class methods as instance methods.
        # For that we have to "unwrap" the class methods via __func__.
        # See https://stackoverflow.com/a/76706399/9788634
        self.render_to_response = types.MethodType(self.__class__.render_to_response.__func__, self)  # type: ignore
        self.render = types.MethodType(self.__class__.render.__func__, self)  # type: ignore
        self.as_view = types.MethodType(self.__class__.as_view.__func__, self)  # type: ignore

        self.registered_name: Optional[str] = registered_name
        self.outer_context: Context = outer_context or Context()
        self.component_id = component_id or gen_id()
        self.registry = registry or registry_
        self._render_stack: Deque[RenderStackItem[ArgsType, KwargsType, SlotsType]] = deque()
        # None == uninitialized, False == No types, Tuple == types
        self._types: Optional[Union[Tuple[Any, Any, Any, Any, Any, Any], Literal[False]]] = None

    def __init_subclass__(cls, **kwargs: Any) -> None:
        cls._class_hash = hash(inspect.getfile(cls) + cls.__name__)

    @property
    def name(self) -> str:
        """Read-only component name."""
        return self.registered_name or self.__class__.__name__

    @property
    def media(self) -> MediaCls:
        # NOTE: This is lazily resolved
        return self._media.resolved.media

    @property
    def input(self) -> RenderInput[ArgsType, KwargsType, SlotsType]:
        """
        Input holds the data (like arg, kwargs, slots) that were passsed to
        the current execution of the `render` method.
        """
        if not len(self._render_stack):
            raise RuntimeError(f"{self.name}: Tried to access Component input while outside of rendering execution")

        # NOTE: Input is managed as a stack, so if `render` is called within another `render`,
        # the propertes below will return only the inner-most state.
        return self._render_stack[-1].input

    @property
    def is_filled(self) -> SlotIsFilled:
        """
        Dictionary describing which slots have or have not been filled.

        This attribute is available for use only within the template as `{{ component_vars.is_filled.slot_name }}`,
        and within `on_render_before` and `on_render_after` hooks.
        """
        if not len(self._render_stack):
            raise RuntimeError(
                f"{self.name}: Tried to access Component's `is_filled` attribute "
                "while outside of rendering execution"
            )

        ctx = self._render_stack[-1]
        if ctx.is_filled is None:
            raise RuntimeError(
                f"{self.name}: Tried to access Component's `is_filled` attribute " "before slots were resolved"
            )

        return ctx.is_filled

    # NOTE: When the template is taken from a file (AKA specified via `template_name`),
    # then we leverage Django's template caching. This means that the same instance
    # of Template is reused. This is important to keep in mind, because the implication
    # is that we should treat Templates AND their nodelists as IMMUTABLE.
    def _get_template(self, context: Context) -> Optional[Template]:
        # TODO
        # TODO - INSTEAD OF self.template_name USE self._media.resolved.extra_paths["template_name"]
        # TODO

        # Resolve template name
        if self.template_name is not None:
            template_name: Optional[str] = self.template_name
            if self.get_template_name(context) is not None:
                raise ImproperlyConfigured(
                    "Received non-null value from both 'template_name' and 'get_template_name' in"
                    f" Component {type(self).__name__}. Only one of the two must be set."
                )
        else:
            template_name = self.get_template_name(context)

        # Resolve template str
        template_input = self.template
        if self.template is not None:
            if self.get_template(context) is not None:
                raise ImproperlyConfigured(
                    "Received non-null value from both 'template' and 'get_template' in"
                    f" Component {type(self).__name__}. Only one of the two must be set."
                )
        else:
            # TODO_REMOVE_IN_V1 - Remove `self.get_template_string` in v1
            template_getter = getattr(self, "get_template_string", self.get_template)
            template_input = template_getter(context)
            if isinstance(template_input, type) and issubclass(template_input, Component):
                template_input = template_input()._get_template(context)

        if template_name is not None and template_input is not None:
            raise ImproperlyConfigured(
                f"Received both 'template_name' and 'template' in Component {type(self).__name__}."
                " Only one of the two must be set."
            )

        if template_name is not None:
            # TODO
            # TODO: WITH THE REMOVAL OF `get_template`, WE CAN ALSO REMOVE THE SETUP STEP
            #       WHERE WE DECLARE THE COMPONENT HTML FILES AS DJANGO TEMPLATES
            # return get_template(template_name).template
            return _load_template(self.__class__, template_name)

        elif template_input is not None:
            # We got template string, so we convert it to Template
            if isinstance(template_input, str):
                origin = Origin(self.__class__.__name__ + " (inlined)")
                origin.component = self.__class__
                template: Template = cached_template(template_input, name=origin.name, origin=origin)
            else:
                # TODO - DISALLOW PASSING TEMPLATE INSTANCE TO `Component.template`
                #        BECAUSE OF THE LOGIC BELOW - IT FORCES US TO RE-PARSE THE TEMPLATE
                template = template_input

                # NOTE: For the plugin hooks to know which component is being rendered
                #       when we hit hooks like `on_tag_slot_before`, we need to somehow
                #       pass down the info on the component. We do this by setting the
                #       component on the template's Origin instance, because that gets
                #       passed to the Parser.
                #
                #       HOWEVER, if user supplied an already-initialized Template, then
                #       this template aleady populated their `Template.nodelist`, and the
                #       hook already ran, but with no component set.
                #       
                #       To fix this, we need we to set the component instance and then
                #       re-parse the template, so that the Component instance will be correctly 
                #       availble to the plugin hooks.
                if not template.origin:
                    template.origin = Origin(UNKNOWN_SOURCE)
                template.origin.component = self.__class__
                template.nodelist = template.compile_nodelist()

            return template

        # TODO: REMOVE THIS TO ADD SUPPORT FOR "renderless" components:
        #       - THESE ALLOW BOTH `template_name` and `template` to be None,
        #         relying only on `self.on_render` to return the content.
        # raise ImproperlyConfigured(
        #     f"Either 'template_name' or 'template' must be set for Component {type(self).__name__}."
        # )
        return None

    # TODO ADD TESTS

    # TODO: UPDATE DOCS BELOW, WE EVENTUALLY WANT THE TEMPLATE TO BE STATIC TOO!
    # NOTE: While the template can be resolved at render time using `get_template` or `get_template_name`,
    # component's JS and CSS are static. Hence we can resolve component's JS / CSS at class creation (__new__).
    # Hence why we have these methods as classmethods.
    @classmethod
    def _get_static_asset(cls, asset_type: str, inlined_attr: str, file_attr: str) -> Optional[str]:
        """
        In case of Component's JS or CSS, one can either define that as "inlined" or as a file.

        E.g.
        ```python
        class MyComp(Component):
            js = "console.log('Hello, world!')"
        ```
        or
        ```python
        class MyComp(Component):
            js_name = "my_comp.js"
        ```
        
        This method resolves the content like above.

        - `inlined_attr` - The attribute name for the inlined content.
        - `file_attr` - The attribute name for the file name.
        """
        inlined_asset = getattr(cls, inlined_attr, None)
        file_asset = getattr(cls, file_attr, None)
        # TODO
        # TODO - INSTEAD OF self.css_name USE self._media.resolved.extra_paths["css_name"]
        # TODO
        if file_asset is not None and inlined_asset is not None:
            raise ImproperlyConfigured(
                f"Received non-null value from both '{inlined_attr}' and '{file_attr}' in"
                f" Component {cls.__name__}. Only one of the two must be set."
            )

        # TODO MOVE
        from pathlib import Path
        from django.contrib.staticfiles import finders  # TODO

        if file_asset is not None:
            asset_path = finders.find(file_asset)
            if asset_path is None:
                raise ValueError(f"Could not find {asset_type} file {file_asset}")
            content = Path(asset_path).read_text()
        elif inlined_asset is not None:
            content = inlined_asset
        else:
            content = None

        return content

    def inject(self, key: str, default: Optional[Any] = None) -> Any:
        """
        Use this method to retrieve the data that was passed to a `{% provide %}` tag
        with the corresponding key.

        To retrieve the data, `inject()` must be called inside a component that's
        inside the `{% provide %}` tag.

        You may also pass a default that will be used if the `provide` tag with given
        key was NOT found.

        This method mut be used inside the `get_context_data()` method and raises
        an error if called elsewhere.

        Example:

        Given this template:
        ```django
        {% provide "provider" hello="world" %}
            {% component "my_comp" %}
            {% endcomponent %}
        {% endprovide %}
        ```

        And given this definition of "my_comp" component:
        ```py
        from django_components import Component, register

        @register("my_comp")
        class MyComp(Component):
            template = "hi {{ data.hello }}!"
            def get_context_data(self):
                data = self.inject("provider")
                return {"data": data}
        ```

        This renders into:
        ```
        hi world!
        ```

        As the `{{ data.hello }}` is taken from the "provider".
        """
        if self.input is None:
            raise RuntimeError(
                f"Method 'inject()' of component '{self.name}' was called outside of 'get_context_data()'"
            )

        return get_injected_context_var(self.name, self.input.context, key, default)

    @classmethod
    def as_view(cls, **initkwargs: Any) -> ViewFn:
        """
        Shortcut for calling `Component.View.as_view` and passing component instance to it.
        """
        # This method may be called as class method or as instance method.
        # If called as class method, create a new instance.
        if isinstance(cls, Component):
            comp: Component = cls
        else:
            comp = cls()

        # Allow the View class to access this component via `self.component`
        return comp.View.as_view(**initkwargs, component=comp)

    # #####################################
    # RENDERING
    # #####################################

    @classmethod
    def render_to_response(
        cls,
        context: Optional[Union[Dict[str, Any], Context]] = None,
        slots: Optional[SlotsType] = None,
        escape_slots_content: bool = True,
        args: Optional[ArgsType] = None,
        kwargs: Optional[KwargsType] = None,
        type: RenderType = "document",
        *response_args: Any,
        **response_kwargs: Any,
    ) -> HttpResponse:
        """
        Render the component and wrap the content in the response class.

        The response class is taken from `Component.response_class`. Defaults to `django.http.HttpResponse`.

        This is the interface for the `django.views.View` class which allows us to
        use components as Django views with `component.as_view()`.

        Inputs:
        - `args` - Positional args for the component. This is the same as calling the component
          as `{% component "my_comp" arg1 arg2 ... %}`
        - `kwargs` - Kwargs for the component. This is the same as calling the component
          as `{% component "my_comp" key1=val1 key2=val2 ... %}`
        - `slots` - Component slot fills. This is the same as pasing `{% fill %}` tags to the component.
            Accepts a dictionary of `{ slot_name: slot_content }` where `slot_content` can be a string
            or render function.
        - `escape_slots_content` - Whether the content from `slots` should be escaped.
        - `context` - A context (dictionary or Django's Context) within which the component
          is rendered. The keys on the context can be accessed from within the template.
            - NOTE: In "isolated" mode, context is NOT accessible, and data MUST be passed via
              component's args and kwargs.
        - `type` - Configure how to handle JS and CSS dependencies.
            - `"document"` (default) - JS dependencies are inserted into `{% component_js_dependencies %}`,
              or to the end of the `<body>` tag. CSS dependencies are inserted into
              `{% component_css_dependencies %}`, or the end of the `<head>` tag.
            - `"fragment"` - `{% component_js_dependencies %}` and `{% component_css_dependencies %}`,
              are ignored, and a script that loads the JS and CSS dependencies is appended to the HTML.

        Any additional args and kwargs are passed to the `response_class`.

        Example:
        ```py
        MyComponent.render_to_response(
            args=[1, "two", {}],
            kwargs={
                "key": 123,
            },
            slots={
                "header": 'STATIC TEXT HERE',
                "footer": lambda ctx, slot_kwargs, slot_ref: f'CTX: {ctx['hello']} SLOT_DATA: {slot_kwargs['abc']}',
            },
            escape_slots_content=False,
            # HttpResponse input
            status=201,
            headers={...},
        )
        # HttpResponse(content=..., status=201, headers=...)
        ```
        """
        content = cls.render(
            args=args,
            kwargs=kwargs,
            context=context,
            slots=slots,
            escape_slots_content=escape_slots_content,
            type=type,
            render_dependencies=True,
        )
        return cls.response_class(content, *response_args, **response_kwargs)

    @classmethod
    def render(
        cls,
        context: Optional[Union[Dict[str, Any], Context]] = None,
        args: Optional[ArgsType] = None,
        kwargs: Optional[KwargsType] = None,
        slots: Optional[SlotsType] = None,
        escape_slots_content: bool = True,
        type: RenderType = "document",
        render_dependencies: bool = True,
    ) -> str:
        """
        Render the component into a string.

        Inputs:
        - `args` - Positional args for the component. This is the same as calling the component
          as `{% component "my_comp" arg1 arg2 ... %}`
        - `kwargs` - Kwargs for the component. This is the same as calling the component
          as `{% component "my_comp" key1=val1 key2=val2 ... %}`
        - `slots` - Component slot fills. This is the same as pasing `{% fill %}` tags to the component.
            Accepts a dictionary of `{ slot_name: slot_content }` where `slot_content` can be a string
            or render function.
        - `escape_slots_content` - Whether the content from `slots` should be escaped.
        - `context` - A context (dictionary or Django's Context) within which the component
          is rendered. The keys on the context can be accessed from within the template.
            - NOTE: In "isolated" mode, context is NOT accessible, and data MUST be passed via
              component's args and kwargs.
        - `type` - Configure how to handle JS and CSS dependencies.
            - `"document"` (default) - JS dependencies are inserted into `{% component_js_dependencies %}`,
              or to the end of the `<body>` tag. CSS dependencies are inserted into
              `{% component_css_dependencies %}`, or the end of the `<head>` tag.
            - `"fragment"` - `{% component_js_dependencies %}` and `{% component_css_dependencies %}`,
              are ignored, and a script that loads the JS and CSS dependencies is appended to the HTML.
        - `render_dependencies` - Set this to `False` if you want to insert the resulting HTML into another component.

        Example:
        ```py
        MyComponent.render(
            args=[1, "two", {}],
            kwargs={
                "key": 123,
            },
            slots={
                "header": 'STATIC TEXT HERE',
                "footer": lambda ctx, slot_kwargs, slot_ref: f'CTX: {ctx['hello']} SLOT_DATA: {slot_kwargs['abc']}',
            },
            escape_slots_content=False,
        )
        ```
        """
        # This method may be called as class method or as instance method.
        # If called as class method, create a new instance.
        if isinstance(cls, Component):
            comp: Component = cls
        else:
            comp = cls()

        return comp._render(context, args, kwargs, slots, escape_slots_content, type, render_dependencies)

    # This is the internal entrypoint for the render function
    def _render(
        self,
        context: Optional[Union[Dict[str, Any], Context]] = None,
        args: Optional[ArgsType] = None,
        kwargs: Optional[KwargsType] = None,
        slots: Optional[SlotsType] = None,
        escape_slots_content: bool = True,
        type: RenderType = "document",
        render_dependencies: bool = True,
    ) -> str:
        try:
            return self._render_impl(context, args, kwargs, slots, escape_slots_content, type, render_dependencies)
        except Exception as err:
            # Nicely format the error message to include the component path.
            # E.g.
            # ```
            # KeyError: "An error occured while rendering components ProjectPage > ProjectLayoutTabbed >
            # Layout > RenderContextProvider > Base > TabItem:
            # Component 'TabItem' tried to inject a variable '_tab' before it was provided.
            # ```

            if not hasattr(err, "_components"):
                err._components = []  # type: ignore[attr-defined]

            components = getattr(err, "_components", [])

            # Access the exception's message, see https://stackoverflow.com/a/75549200/9788634
            if not components:
                orig_msg = err.args[0]
            else:
                orig_msg = err.args[0].split("\n", 1)[1]

            components.insert(0, self.name)
            comp_path = " > ".join(components)
            prefix = f"An error occured while rendering components {comp_path}:\n"

            err.args = (prefix + orig_msg,)  # tuple of one
            raise err

    def _render_impl(
        self,
        context: Optional[Union[Dict[str, Any], Context]] = None,
        args: Optional[ArgsType] = None,
        kwargs: Optional[KwargsType] = None,
        slots: Optional[SlotsType] = None,
        escape_slots_content: bool = True,
        type: RenderType = "document",
        render_dependencies: bool = True,
    ) -> str:
        # TODO - Move type validation out? See https://github.com/EmilStenstrom/django-components/pull/733#discussion_r1826941190
        #        Replace with `on_before_inputs()`

        # NOTE: We must run validation before we normalize the slots, because the normalization
        #       wraps them in functions.
        self._validate_inputs(args or (), kwargs or {}, slots or {})

        # Allow to provide no args/kwargs/slots/context
        args = cast(ArgsType, args or ())
        kwargs = cast(KwargsType, kwargs or {})
        slots_untyped = self._normalize_slot_fills(slots or {}, escape_slots_content)
        slots = cast(SlotsType, slots_untyped)
        context = context or Context()

        # Allow to provide a dict instead of Context
        # NOTE: This if/else is important to avoid nested Contexts,
        # See https://github.com/EmilStenstrom/django-components/issues/414
        context = context if isinstance(context, Context) else Context(context)

        # By adding the current input to the stack, we temporarily allow users
        # to access the provided context, slots, etc. Also required so users can
        # call `self.inject()` from within `get_context_data()`.
        self._render_stack.append(
            RenderStackItem(
                input=RenderInput(
                    context=context,
                    slots=slots,
                    args=args,
                    kwargs=kwargs,
                    type=type,
                    render_dependencies=render_dependencies,
                ),
                is_filled=None,
            ),
        )

        # TODO: RENAME TO `on_input`
        plugins.on_data_before(OnDataBeforeContext(self))

        # TODO - We need to remove the `context` arg from `get_template`.
        #        OOOOOR mention a caveat that `get_template` uses the PARENT'S context, not this component's
        # TODO - ALSO DOCUMENT THE ORDER OF EXECUTION when rendering:
        #        1. Input validated
        #        2. Template resolved
        #        3. JS / CSS resolved
        #        4. data (Context / JS / CSS) prepared
        #        5. Context prepared
        #        6. on_render_before
        #        7. template.render
        #        8. on_render_after
        #        9. postprocess_component_html
        #
        context_data = self.get_context_data(*args, **kwargs)
        js_data = self.get_js_data(*args, **kwargs)
        css_data = self.get_css_data(*args, **kwargs)

        # TODO - Move type validation out? See https://github.com/EmilStenstrom/django-components/pull/733#discussion_r1826941190
        #        Replace with `on_after_data()`
        self._validate_outputs(data=context_data, js_data=js_data, css_data=css_data)

        # TODO: RENAME TO `on_data`
        plugins.on_data_after(
            OnDataAfterContext(
                component=self,
                context_data=cast(Dict, context_data),
                js_data=cast(Dict, js_data),
                css_data=cast(Dict, css_data),
            )
        )

        # Process JS and CSS files
        js_content = self.js or ""
        js_input_hash = cache_inlined_js(self.__class__, js_content, js_data)

        css_content = self.css or ""
        if css_content and self.css_scoped:
            css_content = scope_css(self.component_id, css_content)
        css_input_hash = cache_inlined_css(self.__class__, css_content, css_data)

        # TODO
        # with _prepare_template(self, context) as template:
        with _prepare_template(self, context, context_data) as template:
            # TODO - REMOVE THIS ONE, PLUGINS CAN INSTEAD USE `on_input`
            plugins.on_slots_resolved(
                OnSlotsResolvedContext(component=self, context=context, slots=resolved_fills)
            )

            # For users, we expose boolean variables that they may check
            # to see if given slot was filled, e.g.:
            # `{% if variable > 8 and component_vars.is_filled.header %}`
            is_filled = SlotIsFilled(slots_untyped)
            self._render_stack[-1].is_filled = is_filled

            component_slot_ctx = ComponentSlotContext(
                component_name=self.name,
                template_name=template.name,
                fills=slots_untyped,
                is_dynamic_component=getattr(self, "_is_dynamic_component", False),
                # This field will be modified from within `SlotNodes.render()`:
                # - The `default_slot` will be set to the first slot that has the `default` attribute set.
                #   If multiple slots have the `default` attribute set, yet have different name, then
                #   we will raise an error.
                default_slot=None,
            )

            with context.update(
                {
                    # TODO
                    # Data from `get_context_data`
                    # **context_data,
                    # Private context fields
                    _ROOT_CTX_CONTEXT_KEY: self.outer_context,
                    _COMPONENT_SLOT_CTX_CONTEXT_KEY: component_slot_ctx,
                    _REGISTRY_CONTEXT_KEY: self.registry,
                    # NOTE: Public API for variables accessible from within a component's template
                    # See https://github.com/EmilStenstrom/django-components/issues/280#issuecomment-2081180940
                    "component_vars": ComponentVars(
                        is_filled=is_filled,
                    ),
                }
            ):
                plugins.on_render_before(
                    OnRenderBeforeContext(self, context, template)
                )

                self.on_render_before(context, template)

                # Get the component's HTML
                html_content = self.on_render(context, template)

                # TODO: Rename to `on_component_render_after()`
                new_output = plugins.on_render_after(
                    OnRenderAfterContext(self, context, template, html_content)
                )
                html_content = new_output if new_output is not None else html_content

                # Allow to optionally override/modify the rendered content
                new_output = self.on_render_after(context, template, html_content)
                html_content = new_output if new_output is not None else html_content

                output = postprocess_component_html(
                    component_cls=self.__class__,
                    component_id=self.component_id,
                    html_content=html_content,
                    css_content=css_content,
                    css_scoped=self.css_scoped or False,
                    css_input_hash=css_input_hash,
                    js_input_hash=js_input_hash,
                    type=type,
                    render_dependencies=render_dependencies,
                )

        # After rendering is done, remove the current state from the stack, which means
        # properties like `self.context` will no longer return the current state.
        self._render_stack.pop()

        return output

    def _normalize_slot_fills(
        self,
        fills: Mapping[SlotName, SlotContent],
        escape_content: bool = True,
    ) -> Dict[SlotName, Slot]:
        # Preprocess slots to escape content if `escape_content=True`
        norm_fills = {}

        # NOTE: `gen_escaped_content_func` is defined as a separate function, instead of being inlined within
        #       the forloop, because the value the forloop variable points to changes with each loop iteration.
        def gen_escaped_content_func(content: SlotFunc) -> Slot:
            def content_fn(ctx: Context, slot_data: Dict, slot_ref: SlotRef) -> SlotResult:
                rendered = content(ctx, slot_data, slot_ref)
                return conditional_escape(rendered) if escape_content else rendered

            slot = Slot(content_func=cast(SlotFunc, content_fn))
            return slot

        for slot_name, content in fills.items():
            if content is None:
                continue
            elif not callable(content):
                slot = _nodelist_to_slot_render_func(
                    slot_name,
                    NodeList([TextNode(conditional_escape(content) if escape_content else content)]),
                    data_var=None,
                    default_var=None,
                )
            else:
                slot = gen_escaped_content_func(content)

            norm_fills[slot_name] = slot

        return norm_fills

    # #####################################
    # VALIDATION
    # #####################################

    def _get_types(self) -> Optional[Tuple[Any, Any, Any, Any, Any, Any]]:
        """
        Extract the types passed to the Component class.

        So if a component subclasses Component class like so

        ```py
        class MyComp(Component[MyArgs, MyKwargs, MySlots, MyData, MyJsData, MyCssData]):
            ...
        ```

        Then we want to extract the tuple (MyArgs, MyKwargs, MySlots, MyData, MyJsData, MyCssData).

        Returns `None` if types were not provided. That is, the class was subclassed
        as:

        ```py
        class MyComp(Component):
            ...
        ```
        """
        # For efficiency, the type extraction is done only once.
        # If `self._types` is `False`, that means that the types were not specified.
        # If `self._types` is `None`, then this is the first time running this method.
        # Otherwise, `self._types` should be a tuple of (Args, Kwargs, Data, Slots)
        if self._types == False:  # noqa: E712
            return None
        elif self._types:
            return self._types

        # Since a class can extend multiple classes, e.g.
        #
        # ```py
        # class MyClass(BaseOne, BaseTwo, ...):
        #     ...
        # ```
        #
        # Then we need to find the base class that is our `Component` class.
        #
        # NOTE: __orig_bases__ is a tuple of _GenericAlias
        # See https://github.com/python/cpython/blob/709ef004dffe9cee2a023a3c8032d4ce80513582/Lib/typing.py#L1244
        # And https://github.com/python/cpython/issues/101688
        generics_bases: Tuple[Any, ...] = self.__orig_bases__  # type: ignore[attr-defined]
        component_generics_base = None
        for base in generics_bases:
            origin_cls = base.__origin__
            if origin_cls == Component or issubclass(origin_cls, Component):
                component_generics_base = base
                break

        if not component_generics_base:
            # If we get here, it means that the Component class wasn't supplied any generics
            self._types = False
            return None

        # If we got here, then we've found ourselves the typed Component class, e.g.
        #
        # `Component(Tuple[int], MyKwargs, MySlots, Any, Any, Any)`
        #
        # By accessing the __args__, we access individual types between the brackets, so
        #
        # (Tuple[int], MyKwargs, MySlots, Any, Any, Any)
        args_type, kwargs_type, slots_type, data_type, js_data_type, css_data_type = component_generics_base.__args__

        self._types = args_type, kwargs_type, slots_type, data_type, js_data_type, css_data_type
        return self._types

    def _validate_inputs(self, args: Tuple, kwargs: Any, slots: Any) -> None:
        maybe_inputs = self._get_types()
        if maybe_inputs is None:
            return
        args_type, kwargs_type, slots_type, data_type, js_data_type, css_data_type = maybe_inputs

        # Validate args
        validate_type(args, args_type, f"Positional arguments of component '{self.name}' failed validation")
        # Validate kwargs
        validate_type(kwargs, kwargs_type, f"Keyword arguments of component '{self.name}' failed validation")
        # Validate slots
        validate_type(slots, slots_type, f"Slots of component '{self.name}' failed validation")

    def _validate_outputs(self, data: Any, js_data: Any, css_data: Any) -> None:
        maybe_inputs = self._get_types()
        if maybe_inputs is None:
            return
        args_type, kwargs_type, slots_type, data_type, js_data_type, css_data_type = maybe_inputs

        # Validate data
        validate_type(data, data_type, f"Data of component '{self.name}' failed validation")
        # Validate JS data
        validate_type(js_data, js_data_type, f"JS data of component '{self.name}' failed validation")
        # Validate CSS data
        validate_type(css_data, css_data_type, f"CSS data of component '{self.name}' failed validation")


class ComponentNode(BaseNode):
    """Django.template.Node subclass that renders a django-components component"""

    def __init__(
        self,
        name: str,
        args: List[Expression],
        kwargs: RuntimeKwargs,
        registry: ComponentRegistry,  # noqa F811
        isolated_context: bool = False,
        nodelist: Optional[NodeList] = None,
        node_id: Optional[str] = None,
    ) -> None:
        super().__init__(nodelist=nodelist or NodeList(), args=args, kwargs=kwargs, node_id=node_id)

        self.name = name
        self.isolated_context = isolated_context
        self.registry = registry

    def __repr__(self) -> str:
        return "<ComponentNode: {}. Contents: {!r}>".format(
            self.name,
            getattr(self, "nodelist", None),  # 'nodelist' attribute only assigned later.
        )

    def render(self, context: Context) -> str:
        trace_msg("RENDR", "COMP", self.name, self.node_id)

        # Do not render nested `{% component %}` tags in other `{% component %}` tags
        # at the stage when we are determining if the latter has named fills or not.
        if _is_extracting_fill(context):
            return ""

        component_cls: Type[Component] = self.registry.get(self.name)

        # Resolve FilterExpressions and Variables that were passed as args to the
        # component, then call component's context method
        # to get values to insert into the context
        args = safe_resolve_list(context, self.args)
        kwargs = self.kwargs.resolve(context)

        # TODO - ADD PLUGIN HOOK `on_component_kwargs_resolved` for consistency?

        slot_fills = resolve_fills(context, self.nodelist, self.name)

        component: Component = component_cls(
            registered_name=self.name,
            outer_context=context,
            component_id=self.node_id,
            registry=self.registry,
        )

        # Prevent outer context from leaking into the template of the component
        if self.isolated_context or self.registry.settings.context_behavior == ContextBehavior.ISOLATED:
            context = make_isolated_context_copy(context)

        output = component._render(
            context=context,
            args=args,
            kwargs=kwargs,
            slots=slot_fills,
            # NOTE: When we render components inside the template via template tags,
            # do NOT render deps, because this may be decided by outer component
            render_dependencies=False,
        )

        trace_msg("RENDR", "COMP", self.name, self.node_id, "...Done!")
        return output


def monkeypatch_template(template_cls: type[Template]) -> None:
    # Modify `Template.render` to set `isolated_context` kwarg of `push_state`
    # based on our custom `Template._dc_is_component_nested`.
    #
    # Part of fix for https://github.com/EmilStenstrom/django-components/issues/508
    #
    # NOTE 1: While we could've subclassed Template, then we would need to either
    # 1) ask the user to change the backend, so all templates are of our subclass, or
    # 2) copy the data from user's Template class instance to our subclass instance,
    # which could lead to doubly parsing the source, and could be problematic if users
    # used more exotic subclasses of Template.
    #
    # Instead, modifying only the `render` method of an already-existing instance
    # should work well with any user-provided custom subclasses of Template, and it
    # doesn't require the source to be parsed multiple times. User can pass extra args/kwargs,
    # and can modify the rendering behavior by overriding the `_render` method.
    #
    # NOTE 2: Instead of setting `Template._dc_is_component_nested`, alternatively we could
    # have passed the value to `monkeypatch_template` directly. However, we intentionally
    # did NOT do that, so the monkey-patched method is more robust, and can be e.g. copied
    # to other.
    if hasattr(template_cls, "_dc_patched"):
        # Do not patch if done so already. This helps us avoid RecursionError
        return

    def _template_render(self: Template, context: Context, *args: Any, **kwargs: Any) -> str:
        #  ---------------- OUR CHANGES START ----------------
        # We parametrized `isolated_context`, which was `True` in the original method.
        if not hasattr(self, "_dc_is_component_nested"):
            isolated_context = True
        else:
            # MUST be `True` for templates that are NOT import with `{% extends %}` tag,
            # and `False` otherwise.
            isolated_context = not self._dc_is_component_nested
        #  ---------------- OUR CHANGES END ----------------

        with context.render_context.push_state(self, isolated_context=isolated_context):
            if context.template is None:
                with context.bind_template(self):
                    context.template_name = self.name
                    return self._render(context, *args, **kwargs)
            else:
                return self._render(context, *args, **kwargs)

    template_cls.render = _template_render
    template_cls._dc_patched = True


@contextmanager
def _maybe_bind_template(context: Context, template: Template) -> Generator[None, Any, None]:
    if context.template is None:
        with context.bind_template(template):
            yield
    else:
        yield


@contextmanager
def _prepare_template(
    component: Component,
    context: Context,
    context_data: Any,
) -> Generator[Optional[Template], Any, None]:
    with context.update(context_data):
        # Associate the newly-created Context with a Template, otherwise we get
        # an error when we try to use `{% include %}` tag inside the template?
        # See https://github.com/EmilStenstrom/django-components/issues/580
        # And https://github.com/EmilStenstrom/django-components/issues/634
        template = component._get_template(context)

        if template is None:
            # If template is None, then the component is "renderless",
            # and we skip template processing.
            yield template
            return
        
        plugins.on_template_load(
            OnTemplateLoadContext(component_cls=component.__class__, template=template)
        )

        if not getattr(template, "_dc_patched"):
            raise RuntimeError(
                "Django-components received a Template instance which was not patched."
                "If you are using Django's Template class, check if you added django-components"
                "to INSTALLED_APPS. If you are using a custom template class, then you need to"
                "manually patch the class."
            )

        # Set `Template._dc_is_component_nested` based on whether we're currently INSIDE
        # the `{% extends %}` tag.
        # Part of fix for https://github.com/EmilStenstrom/django-components/issues/508
        template._dc_is_component_nested = bool(context.render_context.get(BLOCK_CONTEXT_KEY))

        with _maybe_bind_template(context, template):
            yield template


# TODO
# @contextmanager
# def _prepare_template(
#     component: Component,
#     context: Context,
# ) -> Generator[Template, Any, None]:
#     # Associate the newly-created Context with a Template, otherwise we get
#     # an error when we try to use `{% include %}` tag inside the template?
#     # See https://github.com/EmilStenstrom/django-components/issues/580
#     # And https://github.com/EmilStenstrom/django-components/issues/634
#     template = component._get_template(context)
#     monkeypatch_template(template)

#     # Set `Template._dc_is_component_nested` based on whether we're currently INSIDE
#     # the `{% extends %}` tag.
#     # Part of fix for https://github.com/EmilStenstrom/django-components/issues/508
#     template._dc_is_component_nested = bool(context.render_context.get(BLOCK_CONTEXT_KEY))

#     with _maybe_bind_template(context, template):
#         yield template




from pathlib import Path
from django.template import Origin
from django_components.util.loader import resolve_file


def _load_template(component: Type[Component], template_path: str) -> Template:
    resolved_path = resolve_file(template_path)
    if not resolved_path:
        raise ValueError(f"{component.name}: Template '{template_path}' does not exist")

    content = Path(resolved_path).read_text()

    origin = Origin(
        name=str(resolved_path),
        template_name=template_path,
        loader=None,
    )
    origin.component = component

    template = Template(
        template_string=content,
        origin=origin,
        name=origin.template_name,
    )
    
    return template
