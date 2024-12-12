import dataclasses
import functools
from typing import Callable, Dict, Literal, Optional, Type, Union, cast, overload
from weakref import WeakKeyDictionary

from django.template import Context, Template
from django.template.base import TextNode
from django.utils.safestring import SafeString, mark_safe
from django_components import SlotFunc, SlotRef, SlotResult, Component, ComponentPlugin
# TODO - SORT AND USE ONLY PUBLIC API!!!
from django_components.node import NodeTraverse, walk_nodelist
from django_components.slots import SlotFill, SlotNode, TSlotData
from django_components.plugin import (
    OnSlotsResolvedContext,
    OnTagComponentBeforeContext,
    OnTagFillBeforeContext,
    OnTagSlotBeforeContext,
    OnTemplateLoadContext,
)
from django_components.util.cache import LRUCache

from django_vue.utils.js import extract_bindings
from django_vue.utils.django_node import replace_node_in_parent
from django_vue.utils.django_tag_parser import Tag


# Holds something like this:
# { MyComponent: { slot_id: True | AlpineConfig } }
alpine_slots_per_component: WeakKeyDictionary[Type[Component], Dict[str, Union[str, Literal[True]]]] = WeakKeyDictionary()

# NOTE: Since we don't know when the rendering ends, we don't know when to clear the cache.
#       So we limit the cache to avoid memory leak.
alpine_slot_data_vars_per_component: LRUCache[Dict[str, str]] = LRUCache(maxsize=500)


# TODO - DOCUMENT THIS
class AlpineSlotPlugin(ComponentPlugin):
    """
    This plugin implements Vue's scoped slot in Django components using AlpineJS.
    While django_components supports passing Python (render-time / server-side) data to slots,
    it doesn't support passing JS (runtime / client-side) data.

    Convert

    ```django
    {# Child component #}
    {% slot "my_slot" default alpine py_var=123 js:abc="123" js:xyz="'123'" %}
      default lolo
    {% endslot %}

    {# Parent component #}
    {% component "child" %}
      {% fill "my_slot" alpine="{ abc: varOne, xyz: varTwo }" %}
        <div x-text="abc">
        </div>
      {% endfill %}
    {% endcomponent %}
    ```

    into

    ```django
    <span id="slot_id"></span>
    ```

    and prepend the template with

    ```django
    <template x-teleport="#slot_id">
      <span x-data="{ $slot: { abc: 123, xyz: '123' } }">
        <span x-data="{ varOne: $slot.abc, varTwo: $slot.xyz }">
          {% slot "my_slot" default py_var=123 / %}
        </span>
      </span>
    </template>
    ```
    """

    def on_tag_component_before(self, ctx: OnTagComponentBeforeContext) -> None:
        if not hasattr(ctx.parser, "_components"):
            ctx.parser._components = []
        ctx.parser._components.append(ctx.tag_id)


    # Remove the `alpine` flag from the `{% slot %}` tag and store it
    # in the weakref mapping as `{ MyComponent: { slot_id: True | AlpineConfig } }`
    def on_tag_slot_before(self, ctx: OnTagSlotBeforeContext) -> None:
        component_cls = ctx.component_cls

        # Slot was defined outside of a component - ignore
        if not component_cls:
            return

        tag = Tag(ctx.token.contents)
        attr = tag.get_attr("alpine")

        # Slot doesn't have the `alpine` flag
        if not attr:
            return

        tag.remove_attr("alpine")
        ctx.token.contents = tag.content

        if component_cls not in alpine_slots_per_component:
            alpine_slots_per_component[component_cls] = {}

        alpine_slots_per_component[component_cls][ctx.tag_id] = attr.value if attr.value is not None else True

    # Remove the `alpine` flag from the `{% fill %}` tag and store it
    # in the weakref mapping as `{ component_id: { slot_id: True | AlpineConfig } }`
    def on_tag_fill_before(self, ctx: OnTagFillBeforeContext) -> None:
        tag = Tag(ctx.token.contents)
        attr = tag.get_attr("alpine")

        # Fill doesn't have the `alpine` flag
        if not attr:
            return
        
        if attr.value is None:
            raise ValueError("AlpineJS slot data variable name is missing")
        
        # Slot was defined outside of a component - ignore
        if not hasattr(ctx.parser, "_components"):
            return

        component_id = ctx.parser._components[-1]

        alpine_slot_data_vars = alpine_slot_data_vars_per_component.get(component_id)
        if alpine_slot_data_vars is None:
            alpine_slot_data_vars = {}
            alpine_slot_data_vars_per_component.set(component_id, alpine_slot_data_vars)

        alpine_slot_data_vars[ctx.tag_id] = attr.value

        tag.remove_attr("alpine")
        ctx.token.contents = tag.content

    # Modify the slot nodes to insert AlpineJS x-teleport, so that AlpineJS variables
    # can be accessed in the slot content.
    def on_template_load(self, ctx: OnTemplateLoadContext) -> Template:
        template = ctx.template

        def on_node(entry: NodeTraverse):
            node = entry.node
            if not isinstance(node, SlotNode):
                return
            
            # If not present, this component doesn't have any alpine slots
            if ctx.component_cls not in alpine_slots_per_component:
                return

            alpine_slots = alpine_slots_per_component[ctx.component_cls]

            # If not present, this component HAS alpine slots, but it is not THIS particular node
            if node.node_id not in alpine_slots:
                return
            
            # Skip modifications if they were already done
            if getattr(node, "__alpine", False):
                return

            alpine_attr_value = alpine_slots[node.node_id]

            # 1. Wrap the slot content in a span with the slot ID
            slot_target = TextNode(mark_safe(f'<span id="{node.node_id}"></span>'))
            if entry.parent is None:
                node_index = template.nodelist.index(node)
                template.nodelist[node_index] = slot_target
            else:
                replace_node_in_parent(old_node=node, new_node=slot_target, parent=entry.parent.node)

            # 2. Define AlpineJS teleport at the top of the template, so it has access to the AlpineJS
            # variables defined outside of this template.
            #
            # ```
            # <template x-teleport="#{{ slot_id }}">
            #     <{{ tag }} x-data="{ $slot: {{ data }} }" {% html_attrs attrs %}>
            #         {% slot "default" default / %}
            #     </{{ tag }}>
            # </template>
            # ```
            prepended_nodes = [
                TextNode(
                    mark_safe(f'<template x-teleport="#{node.node_id}">')
                ),
                node,
                TextNode(
                    mark_safe('</template>'),
                ),
            ]

            for node_to_insert in reversed(prepended_nodes):
                template.nodelist.insert(0, node_to_insert)

            node.__alpine = True

        walk_nodelist(template.nodelist, on_node)
        return template

    # Modify the fill nodes to be able to map JS slot data
    def on_slots_resolved(self, ctx: OnSlotsResolvedContext) -> None:
        component_cls = ctx.component.__class__
        if component_cls not in alpine_slots_per_component:
            return

        alpine_slots = alpine_slots_per_component[component_cls]
        alpine_slot_data_vars = alpine_slot_data_vars_per_component.get(ctx.component.component_id)
        if alpine_slot_data_vars is None:
            return

        for slot_id, maybe_settings in alpine_slots.items():
            slot_fill = ctx.slots[slot_id]

            # Check if the slot wasn't already processed. Slots that were passed as functions
            # NEED to be wrapped in `alpine_slot()` decorator if they want to access JS slot data.
            # And `alpine_slot` adds the `_alpine_slot` attribute to the function.
            if getattr(slot_fill.content_func, "_alpine_slot", False):
                continue

            # If `_alpine_slot` is present, function was passed to `alpine_slot()` decorator.
            # If the slot fill was defined in the template e.g. `{% fill "my_slot" alpine="slotProps" %}`,
            # then it will have a `fill_id` attribute.
            # So if a function has neither, then it the slot is not an alpine slot.
            if not hasattr(slot_fill.content_func, "fill_id"):
                continue

            # The rest of this code is only for alpine slots defined via Django template, e.g. `{% fill "my_slot" %}`
            fill_id = slot_fill.content_func.fill_id

            # A fill without `alpine` attribute was passed to a slot with `alpine`, in which
            # case we treat it as a regular slot.
            if fill_id not in alpine_slot_data_vars:
                continue

            alpine_slot_data_var = alpine_slot_data_vars[fill_id]

            # Wrap the fill, so the resulting HTML is wrapped in extra <span> tags that
            # set the AlpineJS variables via x-data, so the behavior is similar to Vue's scoped slots.
            scoped_slot_fn = alpine_slot(alpine_slot_data_var, slot_fill.content_func)
            new_slot_fill = SlotFill(**{
                **dataclasses.asdict(slot_fill),
                "content_func": scoped_slot_fn
            })
            ctx.slots[slot_id] = new_slot_fill


# Convert fill HTML into a scoped slot:
# E.g. if we have
# ```django
# {% slot "my_slot" js:abc="123" js:xyz="'some-text'"alpine %}
# {% endslot %}
#
# {% fill "my_slot" alpine="{ abc, xyz }" %}
#   <div x-text="abc">
#     Hello
#   </div>
# {% endfill %}
# ```
#
# We want to convert the slot into:
#
# ```html
# <span id="ab31c2">
# </span>
# ```
#
# And we want to convert the fill into:
#
# ```html
# <template x-teleport="#ab31c2">
#   <span x-data="{ $slot: { abc: 123, xyz: 'some-text' } }">
#     <span x-data="{ abc: $slot.abc, xyz: $slot.xyz }">
#     </span>
#   </span>
# </template>
# ```

@overload
def alpine_slot(
    alpine_slot_data_var: str,
) -> Callable[[SlotFunc[TSlotData]], SlotFunc[TSlotData]]: ...

@overload
def alpine_slot(
    alpine_slot_data_var: str,
    fn: SlotFunc[TSlotData]
) -> SlotFunc[TSlotData]: ...

def alpine_slot(
    alpine_slot_data_var: str,
    fn: Optional[SlotFunc[TSlotData]] = None
) -> Union[SlotFunc[TSlotData], Callable[[SlotFunc[TSlotData]], SlotFunc[TSlotData]]]:
    # Convert user's destruction syntax:
    #
    # `alpine="[{ name: userName, age }]"`
    #
    # into a string that can be used in JS:
    #
    # `{ userName: $slot[0].name, age: $slot[0].age }`
    bindings = extract_bindings(alpine_slot_data_var)
    bindings_str = ""
    for key, val in bindings.items():
        key = key.replace('"', '&quot;')
        val = val.replace('"', '&quot;')
        bindings_str += f"{key}: {val}, "
    bindings_str = "{" + bindings_str + "}"

    def make_wrapper(fn: SlotFunc[TSlotData]):
        @functools.wraps(fn)
        def wrapper(ctx: Context, slot_data: TSlotData, slot_ref: "SlotRef") -> SlotResult:
            # Render the original slot
            html = fn(ctx, slot_data, slot_ref)

            # Wrap it in an outer <span> which groups all the JS slot vars together
            # under the `$slot` key.
            js_data = slot_data.get("js", {})

            js_data_str = ""
            for key, val in js_data.items():
                key = key.replace('"', '&quot;').replace("'", "\\'")
                val = val.replace('"', '&quot;')
                js_data_str += f"'{key}': {val}, "
            js_data_str = "{" + js_data_str + "}"

            outer_span = f'<span x-data="{{ $slot: {js_data_str} }}">'

            # Wrap in an inner <span> which maps the `$slot` key into a user-defined
            # variables.
            # This allows to use the scoped slots similarly to how Vue does it
            # with `#default={ name, age }`.
            # Without this, the user would have to access the slot data like so:
            # `$slot[0].name`, `$slot[0].age`.
            inner_span = f'<span x-data="{bindings_str}">'
            
            wrapped_html = outer_span + inner_span + html + "</span></span>"
            is_safe = isinstance(html, SafeString)
            return mark_safe(wrapped_html) if is_safe else wrapped_html

        wrapper._alpine_slot = True  # type: ignore[attr-defined]
        return wrapper
    
    # Handle `@alpine_slot("{ abc }", fn)` syntax
    if fn is not None:
        return make_wrapper(fn)

    # Handle `@alpine_slot("{ abc }")` syntax
    def decorator(fn: SlotFunc[TSlotData]) -> SlotFunc[TSlotData]:
        wrapper = make_wrapper(fn)
        return cast(SlotFunc[TSlotData], wrapper)

    return decorator
