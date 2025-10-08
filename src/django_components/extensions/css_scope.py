from typing import ClassVar, Optional

from django_components.extension import ComponentExtension, OnComponentRenderedContext, OnSlotRenderedContext, OnComponentInputContext
from django_components.dependencies import link_dependencies_with_component_html


# TODO - UPDATE DOCSTRINGS
class ComponentCssScope(ComponentExtension.ExtensionClass):  # type: ignore
    """
    The interface for `Component.DebugHighlight`.

    The fields of this class are used to configure the component debug highlighting for this component
    and its direct slots.

    Read more about [Component debug highlighting](../../concepts/advanced/component_debug_highlighting).

    **Example:**

    ```python
    from django_components import Component

    class MyComponent(Component):
        class DebugHighlight:
            highlight_components = True
            highlight_slots = True
    ```

    To highlight ALL components and slots, set
    [`ComponentsSettings.DEBUG_HIGHLIGHT_SLOTS`](../../settings/components_settings.md#debug_highlight_slots) and
    [`ComponentsSettings.DEBUG_HIGHLIGHT_COMPONENTS`](../../settings/components_settings.md#debug_highlight_components)
    to `True`.
    """

    enabled: ClassVar[bool] = False
    """Whether to scope the CSS of this component."""


# TODO UPDATE DOSCTRINGS
class CssScopeExtension(ComponentExtension):
    """
    This extension adds the ability to highlight components and slots in the rendered output.

    To highlight slots, set `ComponentsSettings.DEBUG_HIGHLIGHT_SLOTS` to `True` in your settings.

    To highlight components, set `ComponentsSettings.DEBUG_HIGHLIGHT_COMPONENTS` to `True`.

    Highlighting is done by wrapping the content in a `<div>` with a border and a highlight color.

    This extension is automatically added to all components.
    """

    name = "css_scope"
    ExtensionClass = ComponentCssScope

    # Remember which component defined the `{% fill %}` tags
    def on_component_input(self, ctx: OnComponentInputContext) -> None:
        for slot_name, slot_content in ctx.slots.items():
            # CSS scoping is implemented as seen in Vue, where the CSS scoping is applied to slot fills
            # only if the slot fills were defined the HTML template. So our equivalent of `{% fill %}` tag.
            #
            # So if a slot was defined with a function or plain string passed to `Component.render()`,
            # we DO NOT apply CSS scoping.
            if slot_content.source != "template":
                continue

            # When a slot fill is defined with `{% fill %}`, it is converted to a Slot instance.
            # The slot may then be passed around through any number of other components and slots.
            #
            # No matter how deep the slot is passed, the CSS scoping should still apply to where
            # the `{% fill %}` tag was originally defined.
            #
            # So we mark the corresponding component only if not set already, to preserve
            # the original relationship.
            if slot_content.extra.get("css_scope", None) is not None:
                continue

            # Mark the component that defined the `{% fill %}` tag.
            slot_content.extra["css_scope"] = ctx.component.class_id

    # Apply CSS scoping to the slot's rendered output
    def on_slot_rendered(self, ctx: OnSlotRenderedContext) -> Optional[str]:
        css_scope_cls: Optional[ComponentCssScope] = getattr(ctx.component_cls, "CssScope", None)
        if not css_scope_cls or not css_scope_cls.enabled:
            return None

        # If the component is set to apply CSS scoping, we want to apply it to the slot fills
        # that were defined as part of the original template file - AKA the content inside
        # the `{% fill %}` tags that you can see in the template file - This is consistent with
        # Vue's scoped CSS behavior.
        #
        # As for the other slot fills, e.g. those that were passed in as functions, those are NOT scoped
        # by default. And instead, users can opt-in by passing in a Slot instance with
        # `Slot.meta["css_scope"]=MyComp.class_id`.
        #
        # This will apply HTML attribute like `data-djc-scope-123456` to all HTML elements rendered by the slot.
        if ctx.slot.extra.get("css_scope", None) is None:
            return None
        
        # TODO CONTINUE IMPLEMENTATION!!!
        # TODO CONTINUE IMPLEMENTATION!!!
        # TODO CONTINUE IMPLEMENTATION!!!
        # TODO CONTINUE IMPLEMENTATION!!!
        # TODO CONTINUE IMPLEMENTATION!!!
        #      1. USE set_html_attributes()
        #      2. We need to apply the CSS scoping, but only until we come across `data-djc-id` or `data-djc-render-id`
        #         as that's where child components start rendered.
        modified = link_dependencies_with_component_html(
            component_id=None,
            css_scope_id=ctx.slot.extra["css_scope"],
            html_content=ctx.result,
            # TODO - SHOULD SLOTS HAVE ACCESS TO CSS VARIABLES? - NO, slots will have access
            #        to those CSS variables where they are eventually placed.
            css_input_hash=None,
        )
        return mark_safe(modified) if isinstance(output, SafeString) else modified



# TODO
# APPLYING THE HTML ATTRIBUTE (TAKEN FROM dependenies.py)
#
# # We apply the CSS scoping attribute to both root and non-root tags.
# #
# # This is the HTML part of Vue-like CSS scoping.
# # That is, for each HTML element that the component renders, we add a `data-djc-scope-a1b2c3` attribute.
# # And we stop when we come across a nested components.
# if css_scope_id:
#     all_attributes.append(f"data-djc-scope-{css_scope_id}")

