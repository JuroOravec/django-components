import json
from textwrap import dedent
from typing import List, Optional, Tuple, Type

from django.utils.safestring import mark_safe
from django.forms.widgets import Media as MediaCls
from selectolax.lexbor import parse_fragment

from django_components import Component, ComponentExtension, types
# TODO - SORT AND USE ONLY PUBLIC API!!!
from django_components.dependencies import _escape_js, get_script_content, get_script_url
from django_components.util.html import serialize_multiroot_html
from django_components.extension import (
    OnExtraMediaContext,
    OnTemplateLoadedContext,
)

# TODO
from django_vue.utils.js import js_arr



# TODO: THEN ALSO MODIFY THE HTML TEMPLATE TO AUTOMATICALLY INSERT `x-data` AND `x-props` ATTRIBUTES
#       BASED ON COMPONENT'S CLASS OR FILENAME (IF PYTHON CLASS NAME IS NOT PROVIDED).

# TODO - DOCUMENT THIS
class VueExtension(ComponentExtension):
    ####################################
    # JS component as default export
    ####################################

    class Media:
        js = [
            # TODO ADD alpine-provide-inject, alpine-alpine, alpine-reactivity, alpine-composition, alpine
            # TODO: Allow users to override these via settings as a map from e.g. "alpine" to a URL

            # AlpineJS plugins (must be loaded before AlpineJS itself)
            "https://cdn.jsdelivr.net/npm/alpine-alpine@0.1.x/dist/cdn.min.js",
            "https://cdn.jsdelivr.net/npm/alpine-provide-inject@0.3.x/dist/cdn.min.js",
            "https://cdn.jsdelivr.net/npm/alpine-reactivity@0.1.x/dist/cdn.min.js",
            "https://cdn.jsdelivr.net/npm/alpine-composition@0.1.28/dist/cdn.min.js",
            
            # AlpineJS
            "https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js",
        ]

    # This extra media hook is used together with `Component.js_autoload = False`
    # and `Component.js_wrap_in_function = False`
    # to load the JS of VueComponents as JS modules. This is because in Vue, the (JS) components
    # are expected to be exported as default exports. E.g.:
    #
    # ```html
    # <script type="module">
    #   export default {
    #     name: 'MyComponent',
    #     data() {
    #       return {
    #         ...
    #       };
    #     },
    #     ...
    #   };
    # </script>
    # ```
    #
    # We add an extra script that imports all these JS files of the VueComponents and then registers them
    # with Alpine.js. This is done by calling `registerComponent` function from `createAlpineComposition`.
    #
    # ```js
    # import MyTable from '/components/cache/MyTable.js';
    # import ListItem from '/components/cache/ListItem.js';
    #
    # const components = [MyTable, ListItem];
    # const componentUrls = ['/components/cache/MyTable.js', '/components/cache/ListItem.js'];
    #
    # const { registerComponent } = AlpineComposition.createAlpineComposition({
    #     plugins: [],
    # });
    #
    # components.forEach((comp) => registerComponent(Alpine, comp));
    # componentUrls.forEach((url) => Components.manager.markScriptLoaded("js", url));
    # ```
    def on_extra_media(self, ctx: OnExtraMediaContext) -> Optional[MediaCls]:
        comp_classes = ctx.components
        if not comp_classes:
            return None

        load_js_components_script = _gen_vue_js_loader_script(comp_classes)
        media = MediaCls(
            js=[
                mark_safe("<script>" + load_as_module_script + "</script>"),
                mark_safe("<script>" + gen_attrs_script + "</script>"),
                mark_safe(load_js_components_script),
            ],
            # TODO REMOVE THIS
            # TODO: Ideally, we would have a separate `head` attribute on Media, to specify non-CSS head tags.
            # NOTE: WORKAROUND: We pretend that the <link> tags are CSS, so they get placed in the same places as CSS,
            #       which is the head of the document.
            # css={"all": [mark_safe(tag) for tag in preload_tags]}
        )
        return media

    ###############################################
    # Associate AlpineJS component with template
    ###############################################

    # TODO - ADD `x-props` ATTRIBUTE TO THE ROOT ELEMENT OF THE COMPONENT'S TEMPLATE!!
    # TODO - DO I NEED TO WRAP THESE IF IT'S A MULTI-ROOT TEMPLATE??

    # Add `x-data` to the root element of the component's template, so that Alpine.js
    # variables are available in the template.
    def on_template_loaded(self, ctx: OnTemplateLoadedContext) -> str:
        raise 1
        html = parse_fragment(ctx.template)
        for node in html:
            if not node.tag or node.tag.startswith("-"):
                continue
            node.attrs["x-data"] = ctx.component_cls.__name__
        return serialize_multiroot_html(html)


def _gen_vue_js_loader_script(component_classes: List[Type[Component]]) -> str:
    # Generate JS expressions like so:
    # ```js
    # const MyTable = await loadAsModule(_unescape(`export default { ... }`)).default;
    # const ListItem = await loadAsModule(_unescape(`export default { ... }`)).default;
    # ...
    # ```
    comp_js_imports_list: List[str] = []
    comp_names: List[str] = []
    comp_urls: List[str] = []

    for comp_cls in component_classes:
        script = get_script_content("js", comp_cls, None)
        url = get_script_url("js", comp_cls, None)

        comp_names.append(comp_cls.__name__)
        comp_urls.append(url)
        comp_js_imports_list.append(
            f"const {comp_cls.__name__} = (await loadAsModule({_escape_js(script, eval=False)})).default;"
        )

    comp_js_imports = "\n".join(comp_js_imports_list)

    # NOTE: No need to wrap in self-invoking function as this script will be executed as a module script
    exec_script: types.js = f"""
        // TODO
        const alpinePromise = new Promise((resolve) => {{
            document.addEventListener('alpine:init', () => {{
                resolve();
            }});
        }});

        const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
        const waitForAlpine = async () => {{
            while (!window.AlpineComposition) {{
                await wait(50);
            }}
        }};

        await waitForAlpine();

        {comp_js_imports}

        const components = {js_arr(comp_names)};
        const componentUrls = {json.dumps(comp_urls)};

        componentUrls.forEach((url) => Components.manager.markScriptLoaded("js", url));

        const {{ registerComponent }} = AlpineComposition.createAlpineComposition({{
            // TODO -  HERE WE CAN INSERT PLUGINS THAT MODIFY ALPINE'S BEHAVIOR
            plugins: [],
        }});

        await alpinePromise;
        components.forEach((comp) => registerComponent(Alpine, comp));
    """

    exec_script = f'<script type="module">{dedent(exec_script)}</script>'
    return exec_script


# TODO - CAN WE ENSURE THIS GETS LOADED ONLY ONCE??
#
# Use Blob to load a JS module as a string. That way we can insert the component's JS directly
# into the HTML response, instead of having to fetch it from the server.
load_as_module_script: types.js = """
    var loadAsModule = async (content) => {
        try {
            const blob = new Blob([content], { type: 'text/javascript' });
            const moduleURL = URL.createObjectURL(blob);
            const importedModule = await import(moduleURL);

            // Revoke the Blob URL to free up resources
            URL.revokeObjectURL(moduleURL);

            return importedModule;
        } catch (error) {
            console.error('Error importing inline module:', error);
        }
    };
"""



# TODO CLEANUP
# TODO - CAN WE ENSURE THIS GETS LOADED ONLY ONCE??
gen_attrs_script: types.js = """
    (() => {
        // TODO SCOPE IN SELF-INVOKING FUNCTION
        let genAttrId = 0;

        // This function makes it possible to bind reactive objects of AlpineReactivity
        // via AlpineJS's dynamic attributes (e.g.`:class="myRef"`).
        globalThis.genAttrs = (attrsGetter) => {
            const attrsKey = "__alpinuiAttrs" + genAttrId;
            genAttrId++;

            // Handle passing a ref or object directly instead of a getter
            const getter = (typeof attrsGetter === 'function') ? attrsGetter : () => attrsGetter;

            // Create computed that resolves any refs and touches all values,
            // so this computed is refreshed whenever any of the refs change.
            const resolvedAttrs = AlpineReactivity.computed(() => {
                // Handle if the whole object passed is a ref
                const attrs = AlpineReactivity.unref(getter());

                return Object.entries(attrs).reduce((acc, [key, value]) => {
                if (key.startsWith('@') || typeof value === 'function') {
                    acc[key] = value
                    return acc
                }

                // Handle if the value is a ref
                acc[key] = AlpineReactivity.unref(value);

                return acc;
                }, {});
            });

            // Returning a function here is the same as if we defined function inside `x-data`, e.g.
            // `x-data="function() => { ... }"`.
            // We need to do this so we can access the current Alpine component under `this`.
            return function() {
                debugger;
                const vm = this;

                // For Alpine to pick up the changes, there's several conditions:
                // 1. The keys have to be defined as reactive, starting with `:` or `x-`.
                // 2. The values have to be reactive, so functions.
                // 3. Inside the reactive functions, we need to touch the properties of `vm` that we
                //    use to tell Alpine that it needs to track them. (this is the same as Vue's `computed`).
                //    For that we use this `attrsKey`, that.
                // 4. Whenever the reactive `attrs` change, then `watchEffect` makes sure that `vm[attrsKey]`
                // 5. Alpine detects that we've changed `vm[attrsKey]`. And because in step 3. all bound attributes
                //    touch this property, they will be re-calculated.
                vm[attrsKey] = {};

                AlpineReactivity.watchEffect(() => {
                debugger;
                vm[attrsKey] = resolvedAttrs.value;
                });

                return Object.entries(vm[attrsKey]).reduce((acc, [key, value]) => {
                if (key.startsWith('@') || typeof value === 'function') {
                    acc[key] = value
                    return acc
                }

                // See https://github.com/alpinejs/alpine/discussions/4408#discussioncomment-11001443
                const theKey = key.startsWith(':') || key.startsWith('x-') ? key : `:${key}`
                acc[theKey] = () => vm[attrsKey][key];

                return acc;
                }, {});
            }
        }
    })();
"""
