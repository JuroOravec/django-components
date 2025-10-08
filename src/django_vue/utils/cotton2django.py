"""
Code to be able to convert

```html
<d-my-component>
</d-my-component>

<d-MyComponent />

<d-my-component
    type="text"
    :value=my_value
    :attrs:class=my_value
    :attrs:class="red-400"
    :js:myVar="1 + 1"
/>

<d-my-component>
    <p>Hello</p>
</d-my-component>

<d-my-component>
    <d-fill :name="my-slot">
        <p>Hello</p>
    </d-fill>
</d-my-component>

<div>
    <d-slot name="my-slot">
        <p>Hello</p>
    </d-slot>
</div>

<d-provide>
</d-provide>
```

To

```django
{% component "my-component" / %}
{% endcomponent %}

{% component "MyComponent" / %}

{% component "my-component"
    attrs:type="text"
    value=my_value
    attrs:class=my_value
    attrs:class="red-400"
    js:myVar="1 + 1"
/ %}

{% component "my-component" %}
    <p>Hello</p>
{% endcomponent %}

{% component "my-component" %}
    {% fill name="my-slot" %}
        <p>Hello</p>
    {% endfill %}
{% endcomponent %}

<div>
    {% slot name="my-slot" %}
        <p>Hello</p>
    {% endslot %}
</div>
```
"""

import re
from typing import List, Literal, Optional, Sequence, Tuple, Union, cast

from django_vue.utils.html_parser import Tag, parse_html


# TODO
def cotton2django_normalize(html: str) -> str:
    def on_tag(html: str, tag: Tag) -> str:
        tag_type = _get_tag_type(tag)

        if tag_type == "component":
            html = _alpine2django_component(html)
        elif tag_type == "slot":
            html = _alpine2django_slot(html, tag)
        elif tag_type == "fill":
            html = _alpine2django_fill(html, tag)
        elif tag_type == "ssr_if_else":
            html = _alpine2django_if_else(html, tag)
        elif tag_type == "ssr_for":
            html = _alpine2django_for(html, tag)
        else:
            html = _alpine2django_tag(html, tag)

        return html

    out_html = parse_html(html, on_tag, convert_interpolation=False, expand_shorthand_tags=False)

    return out_html


ALPINE_DIRECTIVES = {
    # Alpine directives with equivalent in Vue
    "x-text",
    "x-html",
    "x-show",
    "x-if",
    "x-for",
    "x-on",
    "x-bind",
    "x-cloak",
    "x-ref", # TODO - This behaves differently in Vue - document that

    # Alpine directives that do NOT have direct equivalent in Vue,
    # BUT same effect can be achieved differently in Vue.
    # E.g. using Vue's `computed()` and `watchEffect()` instead of Alpine's `x-effect`
    "x-data",
    "x-effect",
    "x-init",

    # TODO - DO LATER, ONCE YOU CAN TEST
    # See https://vuejs.org/guide/components/v-model
    # https://alpinejs.dev/directives/model#range-inputs
    "x-model",
    "x-modelable",
    "x-transition", # TODO - Implement as `<Transition>` and `<TransitionGroup>`
    "x-ignore",
    "x-teleport", # TODO - Implement as `<Teleport>`
    "x-id",
}


def _alpine2django_component(html: str) -> str:
    # TODO
    pass
    # TODO
    # TODO - ssr-html and ssr-text do NOT actually need to be on <template>!
    #        instead they should be handled same way as HTML attrs, AKA we check
    #        ALL tags, and modify those that have these present
    # TODO
    # elif tag.name == "template" and tag.has_attr("ssr-html"):
    #     return "ssr_html"
    # elif tag.name == "template" and tag.has_attr("ssr-text"):
    #     return "ssr_text"


# Construct HTML attributes like so:
# ```django
# <a
#   {% expr '{"aria-role": "button"}' as default_attrs %}
#   {% html_attrs
#     attrs
#     default_attrs
#     class="v-breadcrumbs-item--link"
#     x-bind="genAttrs(() => ({
#       ...jsAttrs,
#       href: link.href.value,
#       'aria-current': isActive.value ? 'page' : undefined,
#       @click: link.navigate,
#     }))"
#   %}
# >
# ```
#
# Handles:
# - v-bind -> spread inside genAttrs
# - ssr-text - as a replacement for Django's `{{ ...|safe }}` syntax
# - ssr-html - as a replacement for Django's `{{ ... }}` syntax
# - ssr-bind - as a replacement for django-components's `...attrs` syntax
# - ssr:key - as a replacement for django-components's `key=val` syntax
# - x-...
# - @...
# - :...11
# - class, style
# - other attributes
def _alpine2django_tag(html: str, tag: Tag) -> str:
    # TODO: MODELS!
    content_mod: Literal[None, "html", "text"] = None
    default_attrs: List[str] = []
    # List of key=val or ...spread
    ssr_attrs: Sequence[Union[str, List[str]]] = []
    appended = []
    bound: List[Tuple[str, Optional[str]]] = []
    for attr in tag.attrs:
        if attr.key.startswith("x-") or attr.key.startswith("@"):
            bound.append((attr.key, attr.value))
        elif attr.key.startswith(":"):
            bound.append((attr.key[1:], attr.value))
        elif attr.key == "v-bind" or attr.key == "x-bind":
            bound.append((f"...{attr.value}", None))
        elif attr.key == "ssr-bind":
            if attr.value is None:
                raise ValueError(f"ssr-bind attribute cannot be empty at index {tag.open_tag_start_index + attr.start_index}")
            cast(List[str], ssr_attrs).append(attr.value)
        elif attr.key == "ssr-html":
            content_mod = "html"
        elif attr.key == "ssr-text":
            content_mod = "text"
        elif attr.key.startswith("ssr:"):
            if not ssr_attrs or not isinstance(ssr_attrs[-1], list):
                curr_attrs: List[str] = []
                cast(List, ssr_attrs).append(ssr_attrs)
            else:
                curr_attrs = ssr_attrs[-1]
            curr_attrs.append(attr.formatted)
        # If class or style are given, they are appeneded, while other attributes are overwritten
        elif attr.key == "class" or attr.key == "style":
            appended.append(attr.formatted)
        else:
            default_attrs.append(attr.formatted)

    # The tag's attributes have been categories and will be processed based on their
    # type. So we remove all attributes that were there until now to start with a clean slate.
    html = tag.clear_attrs(html)

    DEFAULT_ATTRS_VAR = "default_attrs"
    ATTRS_VAR = "attrs"

    django_attrs = f"{ATTRS_VAR}" if ssr_attrs else "None"
    django_attrs += f" {DEFAULT_ATTRS_VAR}" if default_attrs else " None"

    for item in appended:
        django_attrs += f" {item}"

    if bound:
        # Construct HTML attribute like this:
        # ```
        # x-bind="genAttrs(() => ({
        #   ...jsAttrs,
        #   href: link.href.value,
        #   'aria-current': isActive.value ? 'page' : undefined,
        #   @click: link.navigate,
        # }))"
        # ```
        django_attrs += ' x-bind="genAttrs(() => ({'
        for key, value in bound:
            if value is None:
                django_attrs += key + ", "
            else:
                django_attrs += f"'{key}': {value}, "
        django_attrs += '}))"'

    if content_mod == "html":
        html = tag.replace_content(html, "{{ " + content_mod + " }}")
    elif content_mod == "text":
        html = tag.replace_content(html, "{{ " + content_mod + "|safe }}")

    # TODO
    # TODO - SHOULD I STRIP THE QUOTES AROUND VALUES??
    # TODO

    # {% expr "{'a': 'b'}" as default_attrs %}
    if default_attrs:
        default_attrs_expr_content = ""
        for default_attr in default_attrs:
            if "=" in default_attr:
                key, val = default_attr.split("=", 1)
            else:
                key = default_attr
                val = "True"
            default_attrs_expr_content += f"'{key}': {val}, "
        # NOTE: The dict is wrapped in single quotes, so we need to escape them
        default_attrs_expr_content = "'{" + default_attrs_expr_content.replace("'", "\\'") + "}'"
        expr_tag = "{% expr " + default_attrs_expr_content + f" as {DEFAULT_ATTRS_VAR} %}}\n"
        html = tag.prepend(html, expr_tag)

    # TODO
    # TODO - SHOULD I STRIP THE QUOTES AROUND VALUES??
    # TODO

    # {% expr '{**ssr_attrs, \'key\': val, \'key2\': \'val2\' }' as attrs %}
    if ssr_attrs:
        ssr_attrs_expr_content = "" 
        for ssr_attr_group in ssr_attrs:
            if isinstance(ssr_attr_group, str):
                ssr_attrs_expr_content += f"**{ssr_attr_group}, "
            elif isinstance(ssr_attr_group, list):
                for ssr_attr in ssr_attr_group:
                    if "=" in ssr_attr:
                        key, val = ssr_attr.split("=", 1)
                    else:
                        key = ssr_attr
                        val = "True"
                    key = attr.key[4:]
                    ssr_attrs_expr_content += f"'{key}': {val}, "
            else:
                raise ValueError(f"Unknown ssr attribute type '{type(ssr_attr_group)}' at index {tag.open_tag_start_index}")
        # NOTE: The dict is wrapped in single quotes, so we need to escape them
        ssr_attrs_expr_content = "'{" + ssr_attrs_expr_content.replace("'", "\\'") + "}'"
        expr_tag = "{% expr " + ssr_attrs_expr_content + f" as {ATTRS_VAR} %}}\n"
        html = tag.prepend(html, expr_tag)

    django_attrs = "{% html_attrs " + django_attrs + " %}"

    if django_attrs:
        html = tag.add_attr(html, key=django_attrs, value=None, quoted=False)

    return html


# TODO REQUIRES SUPPORT FOR {% slot alpine="slotProps" %}
#
# Slots:
#   <slot /> -> {% slot name="default" default / %}
#   <slot name="xyz" /> -> {% slot name="xyz" / %}
#   <slot name="xyz" ssr-bind="slot_data" /> -> {% slot name="xyz" ...slot_data / %}
#   <slot name="xyz" ssr:key="val" /> -> {% slot name="xyz" key=val / %}
#   <slot name="xyz" ssr-required /> -> {% slot name="xyz" required / %}
#   <slot name="xyz">Default content</slot> -> {% slot name="xyz" %}Default content{% endslot %}
#   <slot name="xyz" :some="data" other="two" /> -> {% slot "xyz" js:some="data" js:other="'two'" alpine %}
def _alpine2django_slot(html: str, tag: Tag) -> str:
    slot_name = "default"
    # List of key=val or ...spread
    ssr_attrs: Sequence[Union[str, List[str]]] = []
    required = False
    js_data = {}

    for attr in tag.attrs:
        if attr.key == "name":
            if attr.value is None:
                raise ValueError(f"Slot name cannot be empty at index {tag.open_tag_start_index + attr.start_index}")
            slot_name = attr.value
        elif attr.key == "ssr-bind":
            if attr.value is None:
                raise ValueError(f"ssr-bind attribute cannot be empty at index {tag.open_tag_start_index + attr.start_index}")
            cast(List[str], ssr_attrs).append(attr.value)
        elif attr.key == "ssr-required":
            required = True
        elif attr.key.startswith("ssr:"):
            if not ssr_attrs or not isinstance(ssr_attrs[-1], list):
                curr_attrs: List[str] = []
                cast(List, ssr_attrs).append(ssr_attrs)
            else:
                curr_attrs = ssr_attrs[-1]
            curr_attrs.append(attr.formatted)
        # All the rest are slot data of scoped slots
        else:
            # If the slot JS data attribute starts with `:`, e.g. `<slot :my-var="someStatement">`
            # then what's inside the quotes is a JS expression, and should be passed as is.
            # Otherwise, it's a string, and should be wrapped in quotes.
            if attr.key[0] == ":":
                key = attr.key[1:]
                value = attr.value
            else:
                key = attr.key
                value = ("'" + attr.value.replace("'", "\\'") + "'") if attr.value else "true"

            js_data[key] = value

    django_attrs = f'name="{slot_name}"'

    if slot_name == "default":
        django_attrs += " default"
    if required:
        django_attrs += " required"
    if js_data:
        django_attrs += " alpine"

    for ssr_attr_group in ssr_attrs:
        if isinstance(ssr_attr_group, str):
            django_attrs += f" ...{ssr_attr_group}"
        elif isinstance(ssr_attr_group, list):
            for ssr_attr in ssr_attr_group:
                if "=" in ssr_attr:
                    key, val = ssr_attr.split("=", 1)
                else:
                    key = ssr_attr
                    val = "True"
                key = attr.key[4:]
                django_attrs += f" {key}={val}"
        else:
            raise ValueError(f"Unknown ssr attribute type '{type(ssr_attr_group)}' at index {tag.open_tag_start_index}")

    for key, value in js_data.items():
        django_attrs += f" js:{key}={value}"

    django_slot_open = "{% slot " + django_attrs + " %}"
    django_slot_close = "{% endslot %}"

    html = tag.insert_content(html, django_slot_open, index=0)
    html = tag.insert_content(html, django_slot_close, index=-2)
    html = tag.unwrap(html)
    return html


# TODO REQUIRES SUPPORT FOR {% fill alpine="slotProps" %}
#
# Fills:
#   <template #slotName> -> {% fill name="slotName" %}
#     - or `v-slot:slotName`
#   <template #default> -> {% fill %}
#     - or `v-slot:default`
#   <template #slotName ssr-data="slot_data"> -> {% fill data="slot_data" %}
#     - or `v-slot:slotName  ssr-data="slot_data"`
#     - Use as `<div ssr-text="slot_data.mydata">`
#   <template #slotName ssr-default="slot_default"> -> {% fill default="slot_default" %}
#     - or `v-slot:slotName ssr-default="slot_default"`
#     - Use as `<div ssr-html="slot_default">`
#   <template #slotName="slotProps"> -> {% fill alpine="slotProps" %}
#     - or `v-slot:slotName="slotProps"`
#     - Destructuring: <template #slotName="{ abc, xyz: { c: [a] } }"> -> {% fill alpine="{ abc, xyz: { c: [a] } }" %}
#   <template #[var] /> ->  {% fill name=var %}
#     - or `v-slot:[var]`
def _alpine2django_fill(html: str, tag: Tag) -> str:
    slot_name = "default"
    slot_name_is_var = False
    ssr_spread = None
    data_var = None
    default_var = None
    js_data = None

    for attr in tag.attrs:
        if attr.key.startswith("#") or attr.key.startswith("v-slot:"):
            if attr.key.startswith("#"):
                slot_name = attr.key[1:]
            else:
                slot_name = attr.key.split(":")[1]
            if slot_name[0] == "[" and slot_name[-1] == "]":
                slot_name = slot_name[1:-1]
                slot_name_is_var = True
            js_data = attr.value
        elif attr.key == "ssr-bind":
            ssr_spread = attr.value
        elif attr.key == "ssr-data":
            data_var = attr.value
        elif attr.key == "ssr-default":
            default_var = attr.value
        else:
            raise ValueError(f"Unknown fill attribute '{attr.key}' at index {tag.open_tag_start_index + attr.start_index}")
    
    if not slot_name:
        raise ValueError(f"Slot name cannot be empty at index {tag.open_tag_start_index}")

    if slot_name == "default" and not slot_name_is_var:
        django_attrs = ""
    elif slot_name_is_var:
        django_attrs = f'name={slot_name}'
    else:
        django_attrs = f'name="{slot_name}"'

    if data_var:
        django_attrs += f' data="{data_var}"'
    if default_var:
        django_attrs += f' default="{default_var}"'
    if js_data:
        django_attrs += f' alpine="{default_var}"'
    if ssr_spread:
        django_attrs += f"...{ssr_spread}"

    django_slot_open = "{% fill " + django_attrs + " %}"
    django_slot_close = "{% endfill %}"

    html = tag.insert_content(html, django_slot_open, index=0)
    html = tag.insert_content(html, django_slot_close, index=-1)
    html = tag.unwrap(html)
    return html


# Logic:
#   <template ssr-if="show"> -> {% if show %}
#   <template ssr-else-if="show"> -> {% elif show %}
#   <template ssr-else> -> {% else show %}
#   <template ssr-if="show" ssr-if-end> -> {% if show %} ... {% endif %}
def _alpine2django_if_else(html: str, tag: Tag) -> str:
    if tag.has_attr("ssr-if"):
        django_tag = "if"
        attr_name = "ssr-if"
    elif tag.has_attr("ssr-else-if"):
        django_tag = "elif"
        attr_name = "ssr-else-if"
    elif tag.has_attr("ssr-else"):
        django_tag = "else"
        attr_name = "ssr-else"
    else:
        raise ValueError(
            "Expected a tag that has one of attributes 'ssr-if', 'ssr-else-if', 'ssr-else',"
            f" at index {tag.open_tag_start_index}"
        )

    value = tag.get_attr(attr_name).value
    html = tag.delete_attr(html, attr_name)
    
    has_end = tag.has_attr("ssr-if-end")
    if has_end:
        html = tag.delete_attr(html, "ssr-if-end")

    if tag.attrs:
        raise ValueError(
            "Template with 'ssr-if', 'ssr-else-if', 'ssr-else' does not accept additional attributes,"
            f" got '{tag.attrs[0].key}' at index {tag.open_tag_start_index + tag.attrs[0].start_index}"
        )

    django_tag_open = f"{{% {django_tag} {value} %}}"
    django_tag_close = "{% endif %}" if has_end else ""

    html = tag.insert_content(html, django_tag_open, index=0)
    html = tag.insert_content(html, django_tag_close, index=-1)
    html = tag.unwrap(html)
    return html


# Logic:
#   <template ssr-for="item in items"> -> {% for item in items %}
#   <template ssr-for="item, index in items"> -> {% for item, index in items %}
def _alpine2django_for(html: str, tag: Tag) -> str:
    if not tag.has_attr("ssr-for"):
        raise ValueError(
            f"Expected a tag that to have attribute 'ssr-for' at index {tag.open_tag_start_index}"
        )
    
    for_attr = tag.get_attr("ssr-for")
    if not for_attr.value:
        raise ValueError(
            f"'ssr-for' attribute is missing a value at index {tag.open_tag_start_index + for_attr.start_index}"
        )
    
    value = for_attr.value
    html = tag.delete_attr(html, "ssr-for")

    if tag.attrs:
        raise ValueError(
            "Template with 'ssr-for' does not accept additional attributes,"
            f" got '{tag.attrs[0].key}' at index {tag.open_tag_start_index + tag.attrs[0].start_index}"
        )

    django_tag_open = f"{{% for {value} %}}"
    django_tag_close = "{% endfor %}"

    html = tag.insert_content(html, django_tag_open, index=0)
    html = tag.insert_content(html, django_tag_close, index=-1)
    html = tag.unwrap(html)
    return html


TagType = Literal[
    "component",
    "fill",
    "slot",
    "ssr_if_else",
    "ssr_for",
    "tag",
]

fill_re = re.compile(r"^#|^v-slot:")
if_else_re = re.compile(r"^ssr-if$|^ssr-else-if$|^ssr-else$")

def _get_tag_type(tag: Tag) -> TagType:
    if tag.name.startswith("d-"):
        return "component"
    elif tag.name == "slot":
        return "slot"
    elif tag.name == "template" and tag.has_attr(fill_re):
        return "fill"
    elif tag.name == "template" and tag.has_attr(if_else_re):
        return "ssr_if_else"
    elif tag.name == "template" and tag.has_attr("ssr-for"):
        return "ssr_for"
    else:
        return "tag"


# ALPINE TO DJANGO CASES:
# Components:
# # TODO
#   - <MyComp /> -> {% vue "MyComp" / %}
#   - <MyComp key="val" :key2="val2" /> -> {% vue "MyComp" js:key="'val'" js:key2="val2" / %}
#   - <MyComp ssr-bind="py_attrs" /> -> {% vue "MyComp" ...py_attrs / %}
#   - <MyComp ssr:key="val" /> -> {% vue "MyComp" key=val / %}
#   - <MyComp ssr-text="my_var" /> -> {% vue "MyComp" / %}{{ my_var|safe }}{% endvue %}
#   - <MyComp ssr-html="my_var" /> -> {% vue "MyComp" / %}{{ my_var }}{% endvue %}
#
#     # TODO - FINISH - STATIC NON-PROPS SHOULD BE PASSED AS HTML ATTRS
#                       WHILE DYNAMIC NON-PROPS SHOULD BE APPLIED LIKE `x-bind="genAttrs(() => ({ ... }))"`
#   - <MyComp class="w-full" :style="styleVar" /> -> {% vue "MyComp" attrs:class="w-full" js:key2="val2" / %}
#
# Slots:
#   ✅ <slot /> -> {% slot name="default" default / %}
#   ✅ <slot name="xyz" /> -> {% slot name="xyz" / %}
#   ✅ <slot name="xyz" ssr-bind="slot_data" /> -> {% slot name="xyz" ...slot_data / %}
#   ✅ <slot name="xyz" ssr-key="val" /> -> {% slot name="xyz" key=val / %}
#   ✅ <slot name="xyz" ssr-required /> -> {% slot name="xyz" required / %}
#   ✅ <slot name="xyz">Default content</slot> -> {% slot name="xyz" %}Default content{% endslot %}
#   ✅ <slot name="xyz" :some="data" other="two" /> -> {% slot "xyz" js:some="data" js:other="'two'" alpine %}
# Fills:
#   ✅ <template #slotName> -> {% fill name="slotName" %}
#   ✅ (or `v-slot:slotName`)
#   ✅ <template #default> -> {% fill %}
#   ✅ (or `v-slot:default`)
#   ✅ <template #slotName ssr-data="slot_data"> -> {% fill data="slot_data" %}
#   ✅ (or `v-slot:slotName`)
#        - Use as `<div ssr-text="slot_data.mydata">`
#   ✅ <template #slotName ssr-default="slot_default"> -> {% fill default="slot_default" %}
#   ✅ (or `v-slot:slotName`)
#        - Use as `<div ssr-html="slot_default">`
#   ✅ <template #slotName="slotProps"> -> {% fill alpine="slotProps" %}
#   ✅ (or `v-slot:slotName="slotProps"`)
#        - Destructuring:
#          <template #slotName="{ abc, xyz: { c: [a] } }"> -> {% fill alpine="{ abc, xyz: { c: [a] } }" %}
#   ✅ <template #[var] /> ->  {% fill name=var %}
# Logic:
#   ✅ <template ssr-if="show"> -> {% if show %}
#   ✅ <template ssr-else-if="show"> -> {% elif show %}
#   ✅ <template ssr-else> -> {% else show %}
#   ✅ <template ssr-if="show" ssr-if-end> -> {% if show %} ... {% endif %}
#   ✅ <template ssr-for="item in items"> -> {% for item in items %}
#   ✅ <template ssr-for="item, index in items"> -> {% for item, index in items %}
# Misc:
#   ✅ <div ssr-text="my_var"> -> <div>{{ my_var|safe }}</div>
#   ✅ <div ssr-html="my_var"> -> <div>{{ my_var }}</div>
#   ✅ <div class="abc" id="3" ssr-bind="attrs"> -> <div {% html_attrs attrs class="abc" id="3" %}>
#   ✅ <div class="abc" id="3" ssr:key="val"> -> <div {% expr '{"key": val}' as attrs %}{% html_attrs attrs class="abc" id="3" %}>

# NOTE: SLOTS ARE RESOLVED AT SSR, JS-SIDE DYNAMIC SLOTS NOT SUPPORTED! # TODO DOCUMENT


# TODO DELETE
if __name__ == "__main__":
    text = """
    <d-my-component>
    </d-my-component>

    <d-MyComponent />

    <d-my-component
        type="text"
        :value=my_value
        :attrs:class=my_value
        :attrs:class="red-400"
        :js:myVar="1 + 1"
    />

    <d-my-component>
        <p>Hello</p>
    </d-my-component>

    <d-my-component>
        <d-fill :name="my-slot">
            <p>Hello</p>
        </d-fill>
    </d-my-component>

    <div>
        <d-slot name="my-slot">
            <p>Hello</p>
        </d-slot>
    </div>
    """
    print("\n", cotton2django_normalize(text))
