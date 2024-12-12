from django_components.plugin import ComponentPlugin, OnJsPreprocessContext


# TODO - DOCUMENT THIS
class CorePlugin(ComponentPlugin):
    def on_js_preprocess(self, ctx: OnJsPreprocessContext) -> str:
        from django_components.dependencies import preprocess_inlined_js

        return preprocess_inlined_js(ctx.component_cls, ctx.js)
