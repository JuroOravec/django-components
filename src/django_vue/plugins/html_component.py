from typing import Any, Dict, Optional, Tuple, Type

from pydantic import TypeAdapter, ValidationError

from django_components import Component, ComponentExtension
from django_components.extension import (
    OnInputContext,
    OnDataContext,
)


# TODO: RULES:
# - The aim is to make it as easy as possible to use components in HTML.
#
# - `<c-my-component>` would be transformed to {% component "my-component" %}
#   - Thus, this would require people to name components in lowercase.
#   - BUUUT, they could also do `<c-MyComponent>` and then transform to {% component "MyComponent" %} ✅
#
# - Normal HTML attributes should be set as they are, without any special handling.
#   - Thus
#     ```html
#     <c-my-input type="text" />
#     ```
#     should be transformed to
#     ```html
#     {% component "my-input" attrs:type="text" %}
#     ```
#
# - Django component inputs would be prefixed with `:`
#   - Thus
#     ```html
#     <c-my-input type="text" :value="my_value" />
#     ```
#     should be transformed to
#     ```html
#     {% component "my-input" attrs:type="text" value=my_value %}
#     ```
#
# - To pass Django variables to attributes, one would use:
#     ```html
#     <c-my-input type="text" :attrs:class=my_value />
#     ```
#     should be transformed to
#     ```html
#     {% component "my-input" attrs:type="text" attrs:class=my_value / %}
#     ```
#
# - In case of AlpineJS or Vue inputs, which start with `:`, there'd be an ambiguity.
#   - Instead, I recomment people to pass JS expressions down via `js` dictionary.
#     So to pass a AlpineJS expression down via a component, one would use
#     ```html
#     <c-my-input :js:myVar="1 + 1" />
#     ```
#     which would be transformed to
#     ```html
#     {% component "my-input" js:myVar="1 + 1" %}
#     ```
#     and which they can then apply within their content as
#     ```html
#     <div x-data="{ myVar: 1 + 1 }">
#       <c-my-input :js:myVar="myVar" />
#     </div>
#     ```
#
# - Default slot fills should be set as they are, without any special handling.
#   - Thus
#     ```html
#     <c-my-component>
#       <p>Hello</p>
#     </c-my-component>
#     ```
#     should be transformed to
#     ```html
#     {% component "my-component" %}
#       <p>Hello</p>
#     {% endcomponent %}
#     ```
#
# - Named slot fills should be set as `<fill name="my-slot">...</fill>`, so it's consistent
#   with django-components.
#   - Thus
#     ```html
#     <c-my-component>
#       <fill :name="my-slot">
#         <p>Hello</p>
#       </fill>
#     </c-my-component>
#     ```
#     should be transformed to
#     ```html
#     {% component "my-component" %}
#       {% fill name="my-slot" %}
#         <p>Hello</p>
#       {% endfill %}
#     {% endcomponent %}
#     ```
#
# - Slot should be set as `<slot name="my-slot">...</slot>`, so it's consistent
#   with django-components.
#   - Thus
#     ```html
#     <div>
#       <slot name="my-slot">
#         <p>Hello</p>
#       </slot>
#     </div>
#     ```
#     should be transformed to
#     ```html
#     <div>
#       {% slot name="my-slot" %}
#         <p>Hello</p>
#       {% endslot %}
#     </div>
#     ```
#
# - Self-closing tags should be transformed to `{% component ... / %}`
#   - Thus
#     ```html
#     <c-my-component />
#     ```
#     should be transformed to
#     ```html
#     {% component "my-component" / %}
#     ```







# Holds the types for each component class
#
# E.g. if a component class is defined as:
#
# ```py
# class MyComp(Component[MyArgs, MyKwargs, MySlots, MyData, MyJsData, MyCssData]):
#     ...
# ```
#
# Then `types_store[MyComp]` will be `(MyArgs, MyKwargs, MySlots, MyData, MyJsData, MyCssData)`
types_store: Dict[Type[Component], Optional[Tuple[Any, Any, Any, Any, Any, Any]]] = {}


def validate_type(value: Any, type: Any, msg: str) -> None:
    try:
        # See https://docs.pydantic.dev/2.3/usage/type_adapter/
        TypeAdapter(type).validate_python(value)
    except ValidationError as err:
        raise TypeError(msg) from err


def _get_types(comp_cls: Type[Component]) -> Optional[Tuple[Any, Any, Any, Any, Any, Any]]:
    """
    Extract the types passed to the Component class.

    So if a component subclasses Component class like so

    ```py
    class MyComp(Component[MyArgs, MyKwargs, MySlots, MyData, MyJsData, MyCssData]):
        ...
    ```

    Then we want to extract the tuple (MyArgs, MyKwargs, MySlots, MyData, MyJsData, MyCssData).

    Returns `None` if types were not provided. That is, the class was subclassed as:

    ```py
    class MyComp(Component):
        ...
    ```
    """
    if comp_cls in types_store:
        return types_store[comp_cls]

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
    generics_bases: Tuple[Any, ...] = comp_cls.__orig_bases__  # type: ignore[attr-defined]
    component_generics_base = None
    for base in generics_bases:
        origin_cls = base.__origin__
        if origin_cls == Component or issubclass(origin_cls, Component):
            component_generics_base = base
            break

    if not component_generics_base:
        # If we get here, it means that the Component class wasn't supplied any generics
        types_store[comp_cls] = None
    else:
        # If we got here, then we've found ourselves the typed Component class, e.g.
        #
        # `Component(Tuple[int], MyKwargs, MySlots, Any, Any, Any)`
        #
        # By accessing the __args__, we access individual types between the brackets, so
        #
        # (Tuple[int], MyKwargs, MySlots, Any, Any, Any)
        args_type, kwargs_type, slots_type, data_type, js_data_type, css_data_type = component_generics_base.__args__
        types_store[comp_cls] = args_type, kwargs_type, slots_type, data_type, js_data_type, css_data_type

    return types_store[comp_cls]


# TODO - DOCUMENT THIS
class PydanticExtension(ComponentExtension):
    # Validate inputs to the component on `Component.render()`
    def on_input(self, ctx: OnInputContext) -> None:
        maybe_inputs = _get_types(ctx.component_cls)
        if maybe_inputs is None:
            return

        args_type, kwargs_type, slots_type, data_type, js_data_type, css_data_type = maybe_inputs
        comp_name = ctx.component_cls.__name__

        # Validate args
        validate_type(ctx.args, args_type, f"Positional arguments of component '{comp_name}' failed validation")
        # Validate kwargs
        validate_type(ctx.kwargs, kwargs_type, f"Keyword arguments of component '{comp_name}' failed validation")
        # Validate slots
        validate_type(ctx.slots, slots_type, f"Slots of component '{comp_name}' failed validation")

    # Validate the data generated from `get_context_data()`, `get_js_data()` and `get_css_data()`
    def on_data(self, ctx: OnDataContext) -> None:
        maybe_inputs = _get_types(ctx.component_cls)
        if maybe_inputs is None:
            return

        args_type, kwargs_type, slots_type, data_type, js_data_type, css_data_type = maybe_inputs
        comp_name = ctx.component_cls.__name__

        # Validate data
        validate_type(ctx.context_data, data_type, f"Data of component '{comp_name}' failed validation")
        # Validate JS data
        validate_type(ctx.js_data, js_data_type, f"JS data of component '{comp_name}' failed validation")
        # Validate CSS data
        validate_type(ctx.css_data, css_data_type, f"CSS data of component '{comp_name}' failed validation")
