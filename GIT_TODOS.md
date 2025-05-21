Next in line:

3. (PR) Pass Slots to {% fill %} with 'body' kwarg (https://github.com/django-components/django-components/pull/1203)
4. (READY FOR PR) Add `Component.args`, `Component.kwargs`, `Component.slots`, and `{{ component_vars.args }}`, `{{ component_vars.kwargs }}`, `{{ component_vars.slots }}` deprecate `Component.is_filled` and `{{ component_vars.is_filled }}` (71dd0b4987e127fd4e03f99ae1134cc890a8c68d)
5. (READY FOR PR) Update docs on slots (01cf249980af7050d7eae67499d0ad3ab9835764)
6. (READY FOR PR) Extension hook for on_slot_render (b1319137cbc0472180944c66d0ccfd8ca39e0355)
7. (READY FOR PR) fix: KeyError on component_context_cache when slot rendered outside (2de100d7df6b00ccc92f0f3a48d55f4bb3eb2acf)
8. (READY FOR PR) Remove slot escaping from `_normalize_slot_fills()`. (a45f6e41976bd1f83911120da5520f0cffe9de4e)
9. (READY FOR PR) Make component instantiation internal (532a3614e1158a01f9bb983c2bfaacff696cee7d)
10. (READY FOR PR) Move defaults applying back to ext, raise on passing Slot to Slot, and docs cleanup (ef16685e0adaf17ad368613cec9b1f3538faef17)
11. (READY FOR PR) extension defaults + docs + API cleanup (a42d67cd7241d48510042a4d9fb2438af8ebb824)
12. (READY FOR PR) More slots metadata - `slot.source` and `slot.extra` (58c9bef4dcc388ad5068a81a8e6cf9874e2ac84a)
13. `Component.on_render()` - see https://github.com/django-components/django-components/issues/1085
14. Make `@register()` decorator optional
----- v0.140 -----
14. After the release, update Pydantic integration, because it relied on using the Component generics.
    - Since validation is now part of the render process, the extension doesn't need to call the hooks.
      It will only provide fixes for compatibility with Pydantic.
15. Update djc-heroicons project.
16. Add djc-ninja integration.
17. Finish storybook integration.
----- For later -----
18. Add `Component.parent`, `Component.root`, `Component.ancestors`, `Component.closest(OtherComp)`
19. Persist component instances on `component_context_cache` as long as any of its children components instances are alive.
    - That way, one could use `Component.closest()` to find a parent component instance even outside of the component's render context.
    - To implement it, call `_get_parent_component_context()` in `Component.__init__()` and add the child component
      to a list of references for parent component.
    - And then add finalizer on child component to remove it from the parent's list of references.
      And if the count of references is 0, remove the parent component from `component_context_cache`.
20. ErrorFallback - see https://github.com/django-components/django-components/issues/1085
21. Address templates loading
22. Pass template metadata to BaseNode, so `{% fill %}` tags know 1. which template, and 2. which component
    they came from.
23. Add `Slot.origin` - the origin of the slot, the component / template that originally rendered it.


NOTE: Reasons why to use `self.args`, `component_vars.args`, etc:
  - Allow to migrate users from django-cotton to django-components
    - People can get "almost" the same behaviour by using `component_vars.args`
  - For the `ErrorFallback` component, I will need to access parent components.
    And I'm thinking of adding `Component.parent` and `Component.root` properties.
    - `Component.parent` - the parent component (instance) of the current component.
    - `Component.root` - the root component (instance) of the current component.
    These `parent` / `root` properties + `args` / `kwargs` etc will be very powerful together:
    ```py
    class Theme(Component):
        ...

    class Table(Component):
        def on_render_before(self, *args, **kwargs):
            # Do something based on the root component's args/kwargs/slots
            theme_comp = self.closest(Theme)
            if theme_comp.kwargs.get("show_header"):
                self.slots["header"] = self.root.kwargs["header"]
    ```
