from typing import TYPE_CHECKING, Any, Dict, List, Optional

from django.template import Context
from django.utils.safestring import SafeString, mark_safe
from django_components import SlotRef, ComponentExtension

# TODO - SORT AND USE ONLY PUBLIC API!!!
from django_components.slots import TSlotData
from django_components.extension import (
    OnFillInputResolvedContext,
    OnSlotRenderContext,
    OnTagContext,
    OnTemplatePostprocessContext,
)

from django_vue.utils.js import extract_bindings


if TYPE_CHECKING:
    from django_components.templatetags.component_tags import TagKwarg
    from django_components.slots import Slot


# TODO
fill_store: Dict[str, Dict[str, Any]] = {}
slot_contents_store: Dict[str, List[str]] = {}


# TODO - DOCUMENT THIS
class AlpineSlotPlugin(ComponentExtension):
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

    # The `{% fill %}` tag may have the `alpine` flag, either bare `alpine`
    # or with a value like `alpine="{ abc }"`.
    #
    # In either case, the slot fill is understood as an alpine slot, which means that,
    # behind the scenes, the slot fill is wrapped in an AlpineJS x-teleport tag, so that
    # AlpineJS variables can be accessed in the slot content.
    #
    # Since `alpine` can be given with or without a value, it may be stored as a flag or as a kwarg.
    # So we normalize it to a kwarg.
    #
    # Lastly, we update the TagSpec to allow the `alpine` kwarg, doing this means that the `alpine`
    # kwarg will pass the validation, and will be accessible in the `on_fill_input_resolved()` hook.
    def on_tag_fill(self, ctx: OnTagContext) -> None:
        if "alpine" in ctx.raw_flags:
            ctx.raw_flags.remove("alpine")
            ctx.raw_kwargs.append(
                TagKwarg(
                    type="kwarg",
                    key="alpine",
                    inner_key=None,
                    value="",
                )
            )

        # Modify the tag spec to allow the `alpine` as an optional kwarg
        tag_spec = ctx.tag_spec
        if tag_spec.keywordonly_args is not True:
            if tag_spec.keywordonly_args is None or tag_spec.keywordonly_args is False:
                tag_spec.keywordonly_args = []
            tag_spec.keywordonly_args.append("alpine")

        if tag_spec.optional_kwargs is None:
            tag_spec.optional_kwargs = []
        tag_spec.optional_kwargs.append("alpine")

    # Store the resolved value of the `alpine` kwarg of the `{% fill %}` tag,
    # so we can identify and access it once we're rendering a slot.
    def on_fill_input_resolved(self, ctx: OnFillInputResolvedContext) -> None:
        # NOTE: `name` may be either a slot name, or "default"
        slot_name = ctx.kwargs["name"]
        if ctx.component_id not in fill_store:
            fill_store[ctx.component_id] = {}
        fill_store[ctx.component_id][slot_name] = ctx.kwargs.get("alpine", None)

    # Similarly to the `{% fill %}` tag, also the `{% slot %}` tag may have the `alpine` input.
    # But in case of slots, the `alpine` input is not a flag, but a kwarg.
    #
    # This kwarg holds the dictionary of JS variables that will be available in the slot content.
    #
    # Moreover, since it's a dictionary, it may be defined with the syntax like `alpine:abc="123"`,
    # which will make the slot content have access to the `abc` variable with the value `123`.
    #
    # Also note that the values are meant to be JS expressions, so to render strings, you need
    # to wrap them in extra quotes. E.g. `alpine:abc="'my-string'"` will make the slot content have
    # access to the `abc` variable with the value `'my-string'`.
    #
    # And for completeness, the values may be also more complex JS expressions, e.g. `alpine:abc="1 + 2"`.
    def on_tag_slot(self, ctx: OnTagContext) -> None:
        # Modify the tag spec to allow the `alpine` as an optional kwarg. Since all extra kwargs
        # are passed to the slot as slot data, this `alpine` kwarg will be available in the slot
        # content as `slot_data.alpine`.
        tag_spec = ctx.tag_spec
        if tag_spec.keywordonly_args is not True:
            if tag_spec.keywordonly_args is None or tag_spec.keywordonly_args is False:
                tag_spec.keywordonly_args = []
            tag_spec.keywordonly_args.append("alpine")

        if tag_spec.optional_kwargs is None:
            tag_spec.optional_kwargs = []
        tag_spec.optional_kwargs.append("alpine")

    # When we come across a {% slot %} tag, we will render it.
    #
    # However, to add the AlpineJS x-teleport, we will do a bit of a shuffle:
    # 1. The place where the {% slot %} was placed originally, there we will place
    #    a <span> with the slot ID. This will be the target of the x-teleport.
    # 2. The original slot content will be wrapped in an AlpineJS teleport, so it has access
    #    to the AlpineJS variables defined outside of this component.
    # 3. And we will store the original content under the render ID, and wait.
    # 4. Once we're done rendering and we reach `on_template_postprocess`, we will check if
    #    there are any slot contents under the render ID. And if so, APPEND them to the
    #    fully-rendered component.
    def on_slot_render(self, ctx: OnSlotRenderContext) -> None:
        def slot_content_func(context: Context, slot_data: Dict[str, Any], slot_ref: SlotRef, *args, **kwargs):
            # Render the original slot content. But instead of returning it,
            # we will store it in the `slot_contents_store` and instead return a <span>
            # with the slot ID.
            original_content = ctx.slot_fn.content_func(context, slot_data, slot_ref, *args, **kwargs)

            # Get the `alpine` kwarg that was set on the `{% fill %}` tag by searching
            # for the slot name (which may be "default" if it's the default slot).
            curr_comp_fill_store = fill_store.get(ctx.component_id, {})
            fill_destruct_stmt = curr_comp_fill_store.get(ctx.slot_name, None)
            if fill_destruct_stmt is None and ctx.slot_is_default:
                fill_destruct_stmt = curr_comp_fill_store.get("default", None)

            # If the slot fill came from the `{% fill %}` template tag and the `alpine` kwarg was not set,
            # then we don't need to wrap the content in an AlpineJS teleport.
            #
            # As for the Slots that were defined in Python, we wrap in teleport only if
            # the `alpine_slot` entry in Slot.meta is present, which is set by the `alpine_slot()` decorator.
            if fill_destruct_stmt is None:
                if ctx.slot_fn.meta.get("alpine_slot", None) is not None:
                    fill_destruct_stmt = ctx.slot_fn.meta["alpine_slot"]
                else:
                    return original_content

            # Before we store the original content, we wrap it in an AlpineJS teleport,
            # so it has access to the AlpineJS variables defined outside of this component.
            #
            # ```
            # <template x-teleport="#{{ slot_id }}">
            #     <span x-data="{ $slot: {{ data }} }">
            #         <span x-data="{{ destruct_stmt }}">
            #             {% slot "default" default / %}
            #         </span>
            #     </span>
            # </template>
            # ```
            destruct_stmt = prepare_destruct_stmt(fill_destruct_stmt)
            slot_id = f"{ctx.component_id}--{ctx.slot_id}"
            js_slot_data: Dict = slot_data.get("alpine", {})
            wrapped_html = wrap_slot_content(original_content, js_slot_data, destruct_stmt, slot_id)

            # Store the wrapped slot content under the render ID, so we can append it to the
            # fully-rendered component once we're done rendering.
            if ctx.component_id not in slot_contents_store:
                slot_contents_store[ctx.component_id] = []
            slot_contents_store[ctx.component_id].append(wrapped_html)

            # Last, return a <span> with the slot ID. This will be the target of the x-teleport.
            return mark_safe(f'<span id="{slot_id}"></span>')

        ctx.slot_fn.content_func = slot_content_func  # type: ignore[assignment]

    # Append the slot contents to the template
    def on_template_postprocess(self, ctx: OnTemplatePostprocessContext) -> str:
        template = ctx.template
        slot_contents = slot_contents_store.pop(ctx.component_id, [])
        for content in slot_contents:
            template += content

        # Cleanup
        fill_store.pop(ctx.component_id, None)

        return template


def prepare_destruct_stmt(fill_destruct_stmt: str) -> str:
    """
    Convert user's destruction syntax:

    `alpine="[{ name: userName, age }]"`

    into a string that can be used in AlpineJS:

    `{ userName: $slot[0].name, age: $slot[0].age }`

    This achieves the same effect as Vue's scoped slots, e.g.:

    ```vue
    <template #default="{ name, age }">
      <div>{{ name }} {{ age }}</div>
    </template>
    ```

    But adapted for AlpineJS.
    """
    # We want to make sure that the keys are accessing only the slot data, and not the global data.
    # Thus we wrap the destruction statement in extra `{ $slot: <destruct_stmt> }` so that all keys
    # will be prefixed with `$slot.`
    bindings = extract_bindings(f"{{ $slot: {fill_destruct_stmt} }}")
    bindings_str = ""
    for key, val in bindings.items():
        key = key.replace('"', "&quot;")
        val = val.replace('"', "&quot;")
        bindings_str += f"{key}: {val}, "
    bindings_str = "{" + bindings_str + "}"
    return bindings_str


def wrap_slot_content(
    html: str,
    slot_data: Dict,
    destruct_stmt: str,
    slot_id: str,
) -> str:
    """
    Wrap the slot content in an AlpineJS teleport, so it has access to the AlpineJS
    variables defined outside of this component.

    The generated HTML is equivalent to this:

    ```django
    <template x-teleport="#{{ slot_id }}">
        <span x-data="{ $slot: {{ slot_alpine_data }} }">
            <span x-data="{{ destruct_stmt }}">
              {% slot "default" default / %}
            </span>
        </span>
    </template>
    ```
    """
    slot_data_str = ""
    # NOTE: Because the `alpine` entries should contain only JS expressions,
    #       they should all be strings, but user may pass any Python value.
    for key, val in slot_data.items():
        key = str(key).replace('"', "&quot;").replace("'", "\\'")
        val = str(val).replace('"', "&quot;")
        slot_data_str += f"'{key}': {val}, "
    slot_data_str = "{" + slot_data_str + "}"

    # 1. First we wrap the content in <template x-teleport="#{{ slot_id }}">,
    #    which tells AlpineJS to teleport anything inside `<template>` to the slot ID.
    #
    # 2. Then we wrap the content in an outer <span>. This groups all the JS variables
    #    that were defined in the `alpine` kwarg of the `{% slot %}` tag, and puts
    #    them under the `$slot` AlpineJS variable.
    #
    # 3. Then we wrap the content in an inner <span>. This maps the `$slot` key into
    #    a user-defined variables. This allows to use the scoped slots similarly to
    #    how Vue does it with a destructuring syntax, e.g. `#default={ name, age }`.
    #
    #    Without this, the user would have to access the slot data like so:
    #    `$slot[0].name`, `$slot[0].age`.
    #
    # 4. Finally, inside all of this, we insert the original slot content.
    wrapped_html = f"""
        <template x-teleport="#{slot_id}">
            <span x-data="{{ $slot: {slot_data_str} }}">
                <span x-data="{destruct_stmt}">
                    {html}
                </span>
            </span>
        </template>
    """

    is_safe = isinstance(html, SafeString)
    return mark_safe(wrapped_html) if is_safe else wrapped_html


# Use `alpine_slot` to mark Python-based slot functions to be able to access JS slot data
def alpine_slot(slot: Slot[TSlotData], destruct_stmt: Optional[str] = None) -> Slot[TSlotData]:
    slot_copy = slot.copy()
    slot_copy.meta["alpine_slot"] = destruct_stmt if destruct_stmt is not None else ""

    return slot_copy
