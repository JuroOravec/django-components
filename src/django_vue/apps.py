from textwrap import indent

from django.apps import AppConfig
from django.conf import settings

from django_vue.utils.misc import to_snake


class DjangoVueConfig(AppConfig):
    name = "django_vue"

    # This is the code that gets run when user adds django_vue
    # to Django's INSTALLED_APPS
    def ready(self) -> None:
        # TODO - General flow:
        # 1. Get the components dirs from django-components
        # 2. Search those dirs for .vue files
        # 3. For each Vue file:
        #    3.1 Create a new Component class
        #    3.2 Add the class to the registry
        #    <-- HTML -->
        #    3.3 Set the `Component.template` to the Vue's <template>.
        #         NOTE: If <template src="">, set `Component.template_name` instead
        #    3.4  Set `Component.template_lang` to the template's `lang` attribute
        #    <-- JS -->
        #    3.5 Set the `Component.js` to the Vue's <script>
        #         NOTE: If <script src="">, set `Component.js_name` instead
        #    3.6  Set `Component.js_lang` to the script's `lang` attribute
        #    <-- CSS -->
        #    3.7 Set the component's CSS to the Vue's <style>
        #         NOTE: If <style src="">, set `Component.css_name` instead
        #    3.8  Set `Component.css_lang` to the style's `lang` attribute
        #    3.9. There can be up to 3 <style> tags: scoped, module, and regular
        #         See https://vuejs.org/api/sfc-css-features.html.
        # 
        pass

        # NOTES:
        # 1. Taking Emil's suggestion that things should be explicit, I'm thinking of
        #    generating all the Vue files into Componnets inside a top-level `vue` dir.
        #    So there would be an explicit step to generate the Vue Django components,
        #    PLUS one would be able to interspect them.
        #    It would still respect app boundaries by nesting the components by apps:
        #    ```
        #    vue/
        #      app1/
        #        component1.py
        #        component2.py
        #      app2/
        #        component3.py
        #        component4.py
        #    ```
        #
        #    To make this work, we would need to re-gen the components every time the
        #    server restarts (which should happen when the Vue file is changed / saved).
        #    To make THAT efficient, the generated files should contain a hash of the
        #    Vue file's content, and only re-gen if the hash changes.
        #    (And also include timestamp of when the file was updated, for a good measure)
        #
        #    All of the above means that we need to:
        #    1. Extend django-components' searched dirs to include the `vue` dir.
        #    2. Search for .vue files in django-components' searched dir.
        #


import shutil
from pathlib import Path
from typing import Dict, List

# TODO - REIMPLEMENT serialize_multiroot_html
from django_components.util.html import serialize_multiroot_html
from django_components.util.loader import get_component_files
from django_vue.utils.vue_parser import VueEntry, parse_vue_file


def _tab(text: str, n: int = 1) -> str:
    return indent(text, "    " * n)


# TODO
# TODO
# TODO
# 3. For each Vue file:
#    3.1 Create a new Component class
#    3.2 Add the class to the registry
#    <-- HTML -->
#    3.3 Set the `Component.template` to the Vue's <template>.
#         NOTE: If <template src="">, set `Component.template_name` instead
#    3.4  Set `Component.template_lang` to the template's `lang` attribute
#    <-- JS -->
#    3.5 Set the `Component.js` to the Vue's <script>
#         NOTE: If <script src="">, set `Component.js_name` instead
#    3.6  Set `Component.js_lang` to the script's `lang` attribute
#    <-- CSS -->
#    3.7 Set the component's CSS to the Vue's <style>
#         NOTE: If <style src="">, set `Component.css_name` instead
#    3.8  Set `Component.css_lang` to the style's `lang` attribute
#    3.9. There can be up to 3 <style> tags: scoped, module, and regular
#         See https://vuejs.org/api/sfc-css-features.html.
def _vue2django_component(vue_entry: VueEntry) -> str:
    comp_name = vue_entry.name
    attrs: Dict[str, str] = {}

    if vue_entry.template is not None:
        html_lang = (vue_entry.template.lang or "html").replace("'", "\\'")
        attrs["template_lang"] = f"'{html_lang}'"
        html_typing_lang = f"django_{html_lang}" if html_lang == "html" else html_lang

        if vue_entry.template.src:
            src = vue_entry.template.src.replace("'", "\\'")
            attrs["template_name"] = f"'{src}'"
        elif vue_entry.template.content:
            content = vue_entry.template.content.replace('"""', '\\"\\"\\"')
            attrs[f"template: types.{html_typing_lang}"] = f'"""\n{content}\n"""'
        else:
            raise ValueError(f"{comp_name}: Template must have either content or src")

    if vue_entry.script is not None:
        js_lang = (vue_entry.script.lang or "js").replace("'", "\\'")
        attrs["js_lang"] = f"'{js_lang}'"

        if vue_entry.script.src:
            src = vue_entry.script.src.replace("'", "\\'")
            attrs["js_name"] = f"'{src}'"
        elif vue_entry.script.content:
            content = vue_entry.script.content.replace('"""', '\\"\\"\\"')
            attrs[f"js: types.{js_lang}"] = f'"""\n{content}\n"""'
        else:
            raise ValueError(f"{comp_name}: Script must have either content or src")

    # TODO: SUPPORT MULTIPLE INLINED CSS PER COMPONENT??? So that we can have scoped, module, and regular
    if vue_entry.styles:
        for kind, style in vue_entry.styles.items():
            css_lang = (style.lang or "css").replace("'", "\\'")
            attrs["css_lang"] = f"'{css_lang}'"

            if style.src:
                src = style.src.replace("'", "\\'")
                attrs["css_name"] = f"'{src}'"
            elif style.content:
                content = style.content.replace('"""', '\\"\\"\\"')
                attrs[f"css: types.{css_lang}"] = f'"""\n{content}\n"""'
            else:
                raise ValueError(f"{comp_name}: Style of kind {kind} must have either content or src")
            

    if vue_entry.server is not None:
        if vue_entry.server.lang is not None and vue_entry.server.lang != "py":
            raise ValueError(f"{comp_name}: Server script must have lang='py'")
        
        if vue_entry.server.src:
            server_script = Path(vue_entry.server.src).read_text("utf-8")
        elif vue_entry.server.content:
            server_script = vue_entry.server.content
        else:
            raise ValueError(f"{comp_name}: Server script must have either content or src")

        # Scope the script inside <server> tag insde a function, e.g.:
        # ```python
        # def _gen_MyTable():
        #     some_var = 42
        #     class MyTable(VueComponent):
        #        ...
        #     return MyTable
        #
        # _MyTable = _gen_MyTable()
        # ```
        script = [
            "from django_components import register, types",
            "from django_vue.templatetags.vue import vue_registry",
            "",
            f"def _gen_{comp_name}():",
            _tab(server_script),
            _tab(f"return {comp_name}"),
            "",
            f"_{comp_name} = _gen_{comp_name}()",
            "",
        ]

        parent_class = f"_{comp_name}"
    else:
        parent_class = "VueComponent"
        script = [
            "from django_components import register, types",
            "from django_vue.templatetags.vue import vue_registry",
            "from django_vue.component import VueComponent",
        ]

    
    script.extend([
        f"@register('{comp_name}', registry=vue_registry)",
        f"class {comp_name}({parent_class}):",
    ])

    # Assign the attributes to the class
    if not attrs:
        script.append(_tab("pass"))
    else:
        for key, value in attrs.items():
            script.append(_tab(f"{key} = {value}"))
    
    script.append("")

    return "\n".join(script)


def main() -> None:
    vue_dir = Path(settings.BASE_DIR) / "vue"

    try:
        shutil.rmtree(vue_dir)
    except FileNotFoundError:
        pass

    vue_dir.mkdir(exist_ok=True)

    vue_files = get_component_files(".vue")

    for vue_file in vue_files:
        vue_entry = parse_vue_file(vue_file, vue_dir)
        file_name = to_snake(vue_entry.name) + ".py"
        file_content = _vue2django_component(vue_entry)

        out_file = vue_dir / file_name
        out_file.write_text(file_content, "utf-8")


# <script lang="ts">
# export default defineComponent({
#   props: {
#     classes: {
#       type: String,
#       default: ''
#     }
#   },
#   methods: {
#     onClick() {
#         this.$emit('click');
#     }
#   },
#   setup() {
#       return {}
#   },
# });
# </script>

# <template>
#   <button @click="onClick" :class="classes">
#     <slot></slot>
#   </button>
# </template>

# <style lang="css">
# button {
#   background-color: #4CAF50;
#   border: none;
#   color: white;
#   padding: 15px 32px;
#   text-align: center;
#   text-decoration: none;
#   display: inline-block;
#   font-size: 16px;
#   margin: 4px 2px;
#   cursor: pointer;
# }
# </style>
