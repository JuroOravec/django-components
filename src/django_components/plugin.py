import itertools
from typing import TYPE_CHECKING, Dict, List, NamedTuple, Optional, Type

from django.forms.widgets import Media as MediaCls
from django.template import Context, Template
from django.template.base import Parser, Token

# TODO
from django_components.component_media import ComponentMediaInput, ComponentMedia

# TODO
if TYPE_CHECKING:
    from django_components import Component

    # TODO - REMOVE ALL THESE, DO NOT EXPOSE THEM AS PUBLIC API
    from django_components.component import ComponentNode
    from django_components.slots import FillNode, SlotFill, SlotNode
    from django_components.templatetags.component_tags import ParsedTag
    from django_components.provide import ProvideNode


class OnExtraMediaContext(NamedTuple):
    components: List[Type["Component"]]


class OnDataBeforeContext(NamedTuple):
    component: "Component"


class OnDataAfterContext(NamedTuple):
    component: "Component"
    context_data: Dict
    js_data: Dict
    css_data: Dict


class OnCssPreprocessContext(NamedTuple):
    component_cls: Type["Component"]
    css: str


class OnCssPostprocessContext(NamedTuple):
    component_cls: Type["Component"]
    css: str


class OnJsPreprocessContext(NamedTuple):
    component_cls: Type["Component"]
    js: str


class OnJsPostprocessContext(NamedTuple):
    component_cls: Type["Component"]
    js: str


class OnTemplatePreprocessContext(NamedTuple):
    component_cls: Type["Component"]
    template: str


class OnTemplateLoadContext(NamedTuple):
    component_cls: Type["Component"]
    template: Template


class OnSlotsResolvedContext(NamedTuple):
    component: "Component"
    context: Context
    slots: Dict[str, "SlotFill"]


class OnRenderBeforeContext(NamedTuple):
    component: "Component"
    context: Context
    template: Template


class OnRenderAfterContext(NamedTuple):
    component: "Component"
    context: Context
    template: Template
    html: str


class OnTagComponentBeforeContext(NamedTuple):
    component_cls: Optional[Type["Component"]]
    parser: Parser
    token: Token
    tag_id: str


class OnTagComponentAfterContext(NamedTuple):
    component_cls: Optional[Type["Component"]]
    parser: Parser
    token: Token
    tag_id: str
    node: "ComponentNode"
    tag: "ParsedTag"


class OnTagFillBeforeContext(NamedTuple):
    component_cls: Optional[Type["Component"]]
    parser: Parser
    token: Token
    tag_id: str


class OnTagFillAfterContext(NamedTuple):
    component_cls: Optional[Type["Component"]]
    parser: Parser
    token: Token
    tag_id: str
    node: "FillNode"
    tag: "ParsedTag"


class OnTagProvideBeforeContext(NamedTuple):
    component_cls: Optional[Type["Component"]]
    parser: Parser
    token: Token
    tag_id: str


class OnTagProvideAfterContext(NamedTuple):
    component_cls: Optional[Type["Component"]]
    parser: Parser
    token: Token
    tag_id: str
    node: "ProvideNode"
    tag: "ParsedTag"


class OnTagSlotBeforeContext(NamedTuple):
    component_cls: Optional[Type["Component"]]
    parser: Parser
    token: Token
    tag_id: str


class OnTagSlotAfterContext(NamedTuple):
    component_cls: Optional[Type["Component"]]
    parser: Parser
    token: Token
    tag_id: str
    # node: "SlotNode" # TODO REMOVE
    tag: "ParsedTag"


class ComponentPlugin(metaclass=MediaMeta):
    ##########################
    # Media (JS and CSS)
    ##########################

    media: MediaCls
    """
    Normalized definition of JS and CSS media files associated with this component.

    NOTE: This field is generated from Component.Media class.
    """
    media_class: MediaCls = MediaCls
    Media: type[ComponentMediaInput]
    """Defines JS and CSS media files associated with this component."""

    # TODO
    def on_extra_media(self, ctx: OnExtraMediaContext) -> Optional[MediaCls]:
        pass

    ##########################
    # Hooks
    ##########################

    def on_data_before(self, ctx: OnDataBeforeContext) -> None:
        """Before calling `Component.get_context_data()`, `get_js_data()` and `get_css_data()`."""
        # # Access Inputs
        # ctx.component.input.args
        # ctx.component.input.kwargs
        # ctx.component.input.slots
        # # Access Context
        # ctx.component.input.context
        pass

    def on_data_after(self, ctx: OnDataAfterContext) -> None:
        """
        After calling `Component.get_context_data()`, `get_js_data()` and `get_css_data()`.

        The data from these methods is passed to this hook.
        """
        # context_data = ctx.context
        # js_data = ctx.js
        # css_data = ctx.css
        pass

    # TODO
    # TODO
    # TODO - IMPLEMENT THIS
    # TODO
    # TODO
    def on_template_preprocess(self, ctx: OnTemplatePreprocessContext) -> str:
        """When Component's template is read as string and assigned to the component."""
        return ctx.template

    def on_template_load(self, ctx: OnTemplateLoadContext) -> Template:
        """When Component's template is converted to Template."""
        return ctx.template

    # TODO
    def on_js_preprocess(self, ctx: OnJsPreprocessContext) -> str:
        """When Component's JS is read as string and assigned to the component."""
        return ctx.js

    # TODO
    def on_js_postprocess(self, ctx: OnJsPostprocessContext) -> str:
        """When Component's JS is finalised, but not yet cached, for use cases like CSS / JS minification."""
        return ctx.js

    # TODO
    def on_css_preprocess(self, ctx: OnCssPreprocessContext) -> str:
        """When Component's CSS is read as string and assigned to the component."""
        return ctx.css

    # TODO
    def on_css_postprocess(self, ctx: OnCssPostprocessContext) -> str:
        """When Component's CSS is finalised, but not yet cached, for use cases like CSS / JS minification."""
        return ctx.css

    def on_slots_resolved(self, ctx: OnSlotsResolvedContext) -> None:
        # TODO DOCS
        pass

    def on_render_before(self, ctx: OnRenderBeforeContext) -> None:
        """Before calling `Component.render()`."""
        pass

    def on_render_after(self, ctx: OnRenderAfterContext) -> Optional[str]:
        """After calling `Component.render()`."""
        pass

    ##########################
    # Template tags hooks
    ##########################

    def on_tag_component_before(self, ctx: OnTagComponentBeforeContext) -> None:
        """Before `{% component %}` tag is parsed."""
        pass

    def on_tag_component_after(self, ctx: OnTagComponentAfterContext) -> None:
        """After `{% component %}` tag is parsed."""
        pass

    def on_tag_fill_before(self, ctx: OnTagFillBeforeContext) -> None:
        """Before `{% fill %}` tag is parsed."""
        pass

    def on_tag_fill_after(self, ctx: OnTagFillAfterContext) -> None:
        """After `{% fill %}` tag is parsed."""
        pass

    def on_tag_provide_before(self, ctx: OnTagProvideBeforeContext) -> None:
        """Before `{% provide %}` tag is parsed."""
        pass

    def on_tag_provide_after(self, ctx: OnTagProvideAfterContext) -> None:
        """After `{% provide %}` tag is parsed."""
        pass

    def on_tag_slot_before(self, ctx: OnTagSlotBeforeContext) -> None:
        """Before `{% slot %}` tag is parsed."""
        pass

    def on_tag_slot_after(self, ctx: OnTagSlotAfterContext) -> None:
        """After `{% slot %}` tag is parsed."""
        pass

    ##########################
    # JS Manager hooks
    ##########################

    # TODO
    js_manager_plugins: List[str] = []
    """
    List of browser (client) function names that will be available in the browser
    and which may extend or modify the behavior of `$onLoad`.
    """


# Merge multiple plugins into one
class MergePlugin:
    def __init__(self, plugins: List[ComponentPlugin]):
        self.plugins = plugins

    ##########################
    # Media (JS and CSS)
    ##########################

    @property
    def medias(self) -> List[MediaCls]:
        return [plugin.media for plugin in self.plugins]
    
    def on_extra_media(self, ctx: OnExtraMediaContext) -> List[MediaCls]:
        medias: List[MediaCls] = []
        for plugin in self.plugins:
            maybe_media = plugin.on_extra_media(ctx)
            if maybe_media is not None:
                medias.append(maybe_media)
        return medias

    ##########################
    # Hooks
    ##########################

    def on_data_before(self, ctx: OnDataBeforeContext) -> None:
        for plugin in self.plugins:
            plugin.on_data_before(ctx)

    def on_data_after(self, ctx: OnDataAfterContext) -> None:
        for plugin in self.plugins:
            plugin.on_data_after(ctx)

    def on_template_preprocess(self, ctx: OnTemplatePreprocessContext) -> str:
        for plugin in self.plugins:
            template = plugin.on_template_preprocess(ctx)
            ctx = ctx._replace(template=template)
        return ctx.template

    def on_template_load(self, ctx: OnTemplateLoadContext) -> Template:
        for plugin in self.plugins:
            template = plugin.on_template_load(ctx)
            ctx = ctx._replace(template=template)
        return ctx.template

    def on_js_preprocess(self, ctx: OnJsPreprocessContext) -> str:
        for plugin in self.plugins:
            js = plugin.on_js_preprocess(ctx)
            ctx = ctx._replace(js=js)
        return ctx.js

    def on_js_postprocess(self, ctx: OnJsPostprocessContext) -> str:
        for plugin in self.plugins:
            js = plugin.on_js_postprocess(ctx)
            ctx = ctx._replace(js=js)
        return ctx.js

    def on_css_preprocess(self, ctx: OnCssPreprocessContext) -> str:
        for plugin in self.plugins:
            css = plugin.on_css_preprocess(ctx)
            ctx = ctx._replace(css=css)
        return ctx.css

    def on_css_postprocess(self, ctx: OnCssPostprocessContext) -> str:
        for plugin in self.plugins:
            css = plugin.on_css_postprocess(ctx)
            ctx = ctx._replace(css=css)
        return ctx.css
    
    def on_slots_resolved(self, ctx: OnSlotsResolvedContext) -> None:
        for plugin in self.plugins:
            plugin.on_slots_resolved(ctx)
    
    def on_render_before(self, ctx: OnRenderBeforeContext) -> None:
        for plugin in self.plugins:
            plugin.on_render_before(ctx)

    def on_render_after(self, ctx: OnRenderAfterContext) -> Optional[str]:
        for plugin in self.plugins:
            maybe_html = plugin.on_render_after(ctx)
            if maybe_html is not None:
                ctx = ctx._replace(html=maybe_html)
        return ctx.html

    ##########################
    # Template tags hooks
    ##########################

    def on_tag_component_before(self, ctx: OnTagComponentBeforeContext) -> None:
        for plugin in self.plugins:
            plugin.on_tag_component_before(ctx)

    def on_tag_component_after(self, ctx: OnTagComponentAfterContext) -> None:
        for plugin in self.plugins:
            plugin.on_tag_component_after(ctx)

    def on_tag_fill_before(self, ctx: OnTagFillBeforeContext) -> None:
        for plugin in self.plugins:
            plugin.on_tag_fill_before(ctx)

    def on_tag_fill_after(self, ctx: OnTagFillAfterContext) -> None:
        for plugin in self.plugins:
            plugin.on_tag_fill_after(ctx)

    def on_tag_provide_before(self, ctx: OnTagProvideBeforeContext) -> None:
        for plugin in self.plugins:
            plugin.on_tag_provide_before(ctx)

    def on_tag_provide_after(self, ctx: OnTagProvideAfterContext) -> None:
        for plugin in self.plugins:
            plugin.on_tag_provide_after(ctx)

    def on_tag_slot_before(self, ctx: OnTagSlotBeforeContext) -> None:
        for plugin in self.plugins:
            plugin.on_tag_slot_before(ctx)

    def on_tag_slot_after(self, ctx: OnTagSlotAfterContext) -> None:
        for plugin in self.plugins:
            plugin.on_tag_slot_after(ctx)

    ##########################
    # JS Manager hooks
    ##########################

    # TODO
    @property
    def js_manager_plugins(self) -> List[str]:
        return list(itertools.chain(*[plugin.js_manager_plugins for plugin in self.plugins]))



# TODO
# TODO - EXPLANAITON OF THE HOOKS:
#   1. Following allow to add extra JS / CSS dependencies:
#      - media_class: MediaCls = MediaCls
#      - Media: type[ComponentMediaInput]
#      - on_extra_media
#
#   2. To move validation out of django_components:
#      - on_data_before
#      - on_data_after
#
#   3. To intercept parsing of template tags, e.g. to allow extra flags / kwargs:
#      - on_tag_component_before
#      - on_tag_component_after
#      - on_tag_fill_before
#      - on_tag_fill_after
#      - on_tag_provide_before
#      - on_tag_provide_after
#      - on_tag_slot_before
#      - on_tag_slot_after
#
#  4. To allow extra processing of the component's JS / CSS / HTML
#      - on_template_preprocess
#      - on_template_load
#      - on_js_preprocess
#      - on_js_postprocess
#      - on_css_preprocess
#      - on_css_postprocess
#
#   5. To modify the rendering context:
#      - on_render_before
#      - on_render_after
#
#   6. To modify slots behavior:
#      - on_slots_resolved
