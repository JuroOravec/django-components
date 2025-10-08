Next in line:


----- v0.140 -----
21. Add djc-ninja integration.
22. Finish storybook integration.
----- For later -----
24. ErrorFallback - see https://github.com/django-components/django-components/issues/1085
25. Make `@register()` decorator optional + `Component.name` to override the registered name
26. Remake `{% html_attrs %}` into just `{% attrs %}`, and leveraging the extra features we can do inside our template tags
    like `{% attrs ... %}`.
27. Add `Component.parent`, `Component.root`, `Component.ancestors`
    - NOTE: There is no reason to change anything about `component_context_cache`. Instead:
       1. At component instantiation, component receives `parent` instance (maybe also `root`?).
       2. For accessing `parent` / `root` / `ancestors`, if needed these all are implemented by walking up the tree using the `Component.parent` property.

      That way, one could use `Component.ancestors` to find a parent component instance even outside of the component's render context.
