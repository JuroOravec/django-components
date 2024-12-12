import json
from typing import Any, Dict, Generic, Mapping

from django.template import Context, Template
from django_components.component import Component, ArgsType, KwargsType, SlotsType, DataType, JsDataType, CssDataType

from django_alpinui.utils.types import PropMeta

# TODO
from django_components.util.misc import _escape_js


# TODO: Allow to pass-through html attributes (unlike Vue, set it in Python component)
#      - This also means that when we set inheritAttrs to false, the `$attrs` object should contain all attributes.
#        And we should be able to passthem down on.
# TODO: Receive component name as a parameter, and then dynamically load it.
# TODO: Move the input validation here (or to the plugin, with a check that it is applied only to VueComponents?)
# TODO: Regular vs scoped vs module CSS:
#       - Vue allows all 3 to co-exist, django_components does not.
#       - Workaround:
#         1. Use the scoped variant (with `scoped: True`) as the default.
#            And let django_components handle CSS scopings.
#         2. Then, at `onCssPostprocess`, if the component class HAS regular CSS,
#            then append the regular CSS to the end of the scoped CSS.
#         3. If there is `module` CSS, then we'll handle that CSS ourselves, and then
#            also append it to the component's CSS.
#       - CSS module processing:
#         1. Parse the CSS with `cssutils` (See https://cssutils.readthedocs.io/en/latest/parse.html)
#         2. Get the CSS rules and then generate a unique class name for the module.
#            (MUST be DIFFERENT than the unique class used for scoped CSS).
#         3. Expose the `styles` variable (or similar) to the component (boh Python AND JS).
#            See Vue for exact implementation.
# TODO: Passthrough props:
#       - <MyComp ssr-bind="py_obj" ssr:key="val" ssr:key_str="'val'" /> -> {% vue "MyComp" ...py_obj key=val key_str='val' / %}
#         - SSR PROPS -> USED AS PROPS
#         - SSR NON-PROPS -> PASSED AS HTML ATTRIBUTES
#       - <MyComp v-bind="jsObj" :key="val" key2="val" /> -> {% vue "MyComp" x-bind="jsObj" js:key="val" js:key2="'val'" / %}
#           which internally processes the `x-bind` and `jsKey` into `x-bind="genAttrs(() => ({ ...jsObj, key: val, key2: "val" }))"`
#       - <MyComp v-bind="jsObj" :class="val" class="val" /> -> {% vue "MyComp" x-bind="genAttrs(() => ({ ...jsObj, key: val, key2: "val" }))" / %}
#         - JS PROPS -> USED AS PROPS
#         - JS NON-PROPS -> PASSED AS HTML ATTRIBUTES
class VueComponent(
    Component[ArgsType, KwargsType, SlotsType, DataType, JsDataType, CssDataType],
    Generic[ArgsType, KwargsType, SlotsType, DataType, JsDataType, CssDataType],
):
    js_wrap_in_function = False
    js_autoload = False

    @classmethod
    def js_tag(cls, content: str) -> str:
        raise 3
        return f'<script type="module">{content}</script>'

#     def on_render_before(self, context: Context, template: Template) -> None:
#         super().on_render_before(context, template)

#         kwargs = {**self.input.kwargs}
#         attrs = kwargs.pop("attrs", {})

#         maybe_inputs = self._get_types()
#         if not maybe_inputs:
#             raise ValueError(f"Failed to obtain type annotation for AlpineComponent '${self.__class__.__name__}'")

#         args_type, kwargs_type, slots_type, data_type, js_data_type, css_data_type = maybe_inputs

#         props = gen_alpine_props(kwargs_type, kwargs)

#         attrs = {
#             **attrs,
#             "x-data": self.__class__.__name__,
#             "x-props": props,
#             "data-x-init": json.dumps({"slots": self.is_filled}),
#         }

#         context["attrs"] = attrs
#         context["self"] = self


# def gen_alpine_props(prop_type: Any, kwargs: Mapping) -> str:
#     kwargs = {**kwargs}
#     js: Dict = kwargs.pop("js", {})
#     js = js.copy()

#     all_keys = set([*kwargs.keys(), *js.keys()])

#     merged = {}
#     props_str = ""
#     for key in all_keys:
#         if key in ("attrs", "spread"):
#             continue

#         if key in kwargs and key in js:
#             raise ValueError(f"Key '{key}' is defined in both kwargs and js")
#         elif key in kwargs:
#             merged[key] = kwargs[key]
#             props_str += f"{key}: {json.dumps(kwargs[key])}, "
#         else:
#             val = js[key]
#             merged["js"] = merged.get("js", {})
#             merged["js"][key] = val
#             props_str += f"{key}: {val}, "
    
#     if "js" in kwargs and "spread" in kwargs["js"]:
#         props_str += f'...{kwargs["js"]["spread"]}, '

#     props_str = "{" + props_str + "}"

#     # Each fields is `NotRequired[Annotated[<actual_type>, PropMeta(required=bool)]]`
#     for key, field in prop_type.__annotations__.items():
#         prop_meta: PropMeta = field.__args__[0].__metadata__[0]

#         if (key not in merged or not merged[key]) and prop_meta.required:
#             raise ValueError(f"Required key '{key}' is missing")

#     return props_str








# TODO
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



# TODO:
# - Once django-components is out, reach out to Vue team, telling them about django-vue
#   and whether they would be interested in a collaboration.
# - Roadmap:
#   1. Complete django-components to v1.
#      - Work on django-vue at the same time, so django-components is compatible with it.
#   2. django-vue templating
#   3. Finish alpinui components
#   4. Continue with django-vue
# - NOTE: Ask https://savannahostrowski.com/ about her experience at Microsoft about Python DevExp
