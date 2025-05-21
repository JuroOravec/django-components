from collections import deque
from typing import Dict, List, Literal, Optional

from selectolax.lexbor import LexborNode, create_tag, parse_fragment
# TODO - Reimplement this so as not to depend on internals of `django_components`
from django_components.util.html import serialize_multiroot_html

from django_vue.utils.html_parser import Tag, TagAttr, parse_html
from django_vue.utils.html_tags import tags
from django_vue.utils.misc import to_kebab


TEMPLATE_TAG_ESC = "template__"


VUE_DIRECTIVES: Dict[str, Optional[str]] = {
    # Vue directives directly supported by AlpineJS
    "v-text": "x-text",
    "v-html": "x-html",
    "v-show": "x-show",
    "v-for": "x-for",
    "v-on": "x-on",
    "v-cloak": "x-cloak",
    "ref": "x-ref",

    # NOTE: `v-if` and similar should be converted to `x-if` when processing in `html_normalize`
    "v-if": "x-if",
    "v-else": None,
    "v-else-if": None,

    # Custom handling
    # "v-bind": "x-bind", # TODO
    # "v-model", # TODO
    # "v-slot",

    # NOTE: `v-pre` should be removed when processing interpolation in `html_normalize`
    "v-pre": None,

    # Unsupported Vue directives
    "v-once": None,
    "v-memo": None,
}


def vue2alpine_normalize(html: str) -> str:
    # on_tag contains changes to the HTML that can be done without having a fully-parsed tree
    def on_tag(html: str, tag: Tag) -> str:
        html = _vue2alpine_expand_default_slots(html, tag)
        # If there's multiple directives like `ssr-if`, `ssr-for`, `v-if`, `v-for`, `x-if`, `x-for`
        # on a single node, or they are not defined on `<template>` node, expand them
        html = _vue2alpine_expand_if_for(html, tag)
        # Convert <MyComp> to <c-my-comp> if it's not a standard tag. The `c-` prefix is used so that
        # user can define custom components whose names would collide with the standard tags.
        # E.g. `Button` would become `c-button`. Selectolax / Lexbor, normalize tag names to lowercase,
        # so without `c-`, `Button` would become `button`, which would collide with the standard `<button>` tag.
        html = _vue2alpine_normalize_components(html, tag)
        return html

    # Convert `{{ abc }}` to `<span x-text="abc"></span>` and expand `<div/>` to `<div></div>`
    out_html = parse_html(html, on_tag, convert_interpolation=True, expand_shorthand_tags=True)

    # For following modificagions, we already need to parse the HTML with Selectolax,
    # so we can traverse the tree.
    # NOTE: Vue templates are HTML-compatible, and may have multiple root elements, hence
    # parsed as fragment.
    tree = parse_fragment(out_html)

    # NOTE: There's a bug in Selectolax or Lexbor, where when we have a <template> tag, we cannot
    # access its children using `.iter()`. And nor can remove or replace TextNodes inside it.
    # So we temporarily change the tag
    tree = [
        _map_node_tag(node, {"template": TEMPLATE_TAG_ESC}, recursive=True, mode="top-down")
        for node in tree
    ]

    tree = _vue2alpine_expand_mixed_slots(tree)
    tree = _vue2alpine_if_else(tree)
    tree = _vue2alpine_ssr_if_else(tree)
    tree = _vue2alpine_if_for_single_root(tree)
    tree = _vue2alpine_directives(tree)

    tree = [
        _map_node_tag(node, {TEMPLATE_TAG_ESC: "template"}, recursive=True, mode="bottom-up")
        for node in tree
    ]

    out_html = serialize_multiroot_html(tree)
    return out_html


# Turn:
# ```vue
# <BaseLayout #header="slotProps">
#   <h1>Here might be a page title</h1>
# </BaseLayout>
# ```
#
# Into:
# ```vue
# <BaseLayout>
#   <template #header>
#     <h1>Here might be a page title</h1>
#   </template>
# </BaseLayout>
# ```
#
# NOTE: Vue allows for multiple named slots, and mixing of default and named slots.
# HOWEVER, when it comes to using `v-slot` / `#slot`, then Vue requires all slots
# to be named (AKA `v-slot` for the default slot cannot be set on the owner component
# while other named slots would be defined in the child `<template>` tags.
def _vue2alpine_expand_default_slots(html: str, tag: Tag) -> str:
    # TODO: To be able to handle v-slot:default, we need to allow following construct in django_components:
    #   ```django
    #   {% component "my_comp" %}
    #     {% fill data="data" default="default" %}
    #       {{ data  }}
    #     {% endfill %}
    #   {% endcomponent %}
    #   ```
    #   In other words, the default slot can be written with `{% fill %}` and by omitting the slot name.

    slot_attrs = [
        attr
        for attr in tag.attrs
        if attr.key.startswith("#") or attr.key.startswith("v-slot")
    ]

    if len(slot_attrs) > 1:
        raise ValueError(f"Multiple slot attributes found: {[attr.key for attr in slot_attrs]}")
    
    if not slot_attrs:
        return html

    slot_attr = slot_attrs[0]

    # Nothing to do, this is the target state
    if tag.name in ("template", TEMPLATE_TAG_ESC):
        return html

    # Remove attribute from its original tag if it's not on a <template> tag
    html = tag.delete_attr(html, slot_attr.key)

    # And instead wrap the tag contents (children) in a <template> tag,
    # and add the slot attribute to it
    content_start_index = tag.open_tag_start_index + tag.open_tag_length
    content_end_index = tag.close_tag_start_index

    # E.g.
    # <BaseLayout #header="slotProps">
    #   <h1>Here might be a page title</h1>
    # </BaseLayout>
    #
    # Becomes:
    # <BaseLayout>
    #   <template #header="slotProps">
    #     <h1>Here might be a page title</h1>
    #   </template>
    # </BaseLayout>
    inserted_start_tag = f"<{TEMPLATE_TAG_ESC} {slot_attr.formatted}>"
    inserted_end_tag = f"</{TEMPLATE_TAG_ESC}>"
    html = (
        html[:content_start_index]
        + inserted_start_tag
        + html[content_start_index:content_end_index]
        + inserted_end_tag
        + html[content_end_index:]
    )

    tag.close_tag_start_index += len(inserted_start_tag) + len(inserted_end_tag)

    return html


#
# Turn:
# ```vue
# <BaseLayout>
#   <h1>Here might be a page title</h1>
#   <template #footer>
#     <p>Here's some contact info</p>
#   </template>
# </BaseLayout>
# ```
#
# Into:
# ```vue
# <BaseLayout>
#   <template #default>
#     <h1>Here might be a page title</h1>
#   </template>
#   <template #footer>
#     <p>Here's some contact info</p>
#   </template>
# </BaseLayout>
# ```
def _vue2alpine_expand_mixed_slots(tree: List[LexborNode]) -> List[LexborNode]:
    # TODO: To be able to support this, we need to allow following construct in django_components:
    #   ```django
    #   {% component "my_comp" %}
    #     {% fill data="data" default="default" %}
    #       {{ data  }}
    #     {% endfill %}
    #   {% endcomponent %}
    #   ```
    #   In other words, the default slot can be written with `{% fill %}` and by omitting the slot name.

    nodes_queue = [*tree]
    while nodes_queue:
        # Depth-first
        node = nodes_queue.pop(-1)
        default_slot_nodes: List[LexborNode] = []
        has_named_slots = False

        for child_node in _get_node_children(node, include_text=True):
            if not child_node.tag:
                raise ValueError("Expected a tag node")

            # Leave non-text special tags as they are
            if child_node.tag.startswith("-") and child_node.tag != "-text":
                continue

            # Implicit default slot
            if child_node.tag not in ("template", TEMPLATE_TAG_ESC):
                default_slot_nodes.append(child_node)
                continue

            slot_attrs_keys = [
                key
                for key in child_node.attrs.keys()
                if key.startswith("#") or key.startswith("v-slot")
            ]

            if len(slot_attrs_keys) > 1:
                raise ValueError(f"Multiple slot attributes found: {slot_attrs_keys}")
            
            # <template> tag, but without a slot attribute, so it's NOT a slot
            if not slot_attrs_keys:
                default_slot_nodes.append(child_node)
                continue

            # Default:        `<MyComponent v-slot>`
            # Default scoped: `<MyComponent v-slot="slotProps">`
            # Named:          `<template v-slot:name>`
            # Named scoped:   `<template v-slot:name="slotProps">`
            #
            # See https://vuejs.org/guide/components/slots.html
            slot_key = slot_attrs_keys[0]
            # `v-slot:name` syntax
            if slot_key.startswith("v-slot"):
                is_default_slot = ":" not in slot_key
            # `#name` syntax
            else:
                is_default_slot = slot_key.split("=")[0] == "#default"

            if is_default_slot and len(default_slot_nodes):
                raise ValueError("Detected implicit default slot mixed with named default slot")

            # Named slots
            if not has_named_slots and not is_default_slot:
                has_named_slots = True

        # Detected implicit default slot mixed with named slots!
        # In such case, we will create new <template #default> tag,
        # and move the nodes of the implicit default slot to it.
        if has_named_slots and len(default_slot_nodes):
            default_slot = create_tag(TEMPLATE_TAG_ESC)
            default_slot.attrs["#default"] = ""  # type: ignore[index]  # TODO: Fix in Selectolax

            # NOTE: We need to copy the nodes, so we can then remove them from their original
            # position. If we tried to just insert them, the nodes would be at 2 places.
            default_slot_html = ""
            for default_slot_node in default_slot_nodes:
                default_slot_html += default_slot_node.html or ""
                default_slot_node.remove(recursive=True)

            default_slot_fragment = parse_fragment(default_slot_html)
            for default_slot_fragment_node in default_slot_fragment:
                default_slot.insert_child(default_slot_fragment_node)

            node.insert_child(default_slot)

        nodes_queue.extend(_get_node_children(node, include_text=True))

    return tree


ALL_IF_FOR_DIRECTIVES = (
    "ssr-if",
    "ssr-else-if",
    "ssr-else",
    "ssr-for",
    "v-if",
    "v-else-if",
    "v-else",
    "v-for",
)

# Turn:
# ```vue
# <BaseList v-if="abc" v-for="item in list">
#   <h1>{{ item }}</h1>
# </BaseList>
# ```
#
# Into:
# ```vue
# <BaseList>
#   <template #header>
#     <h1>Here might be a page title</h1>
#   </template>
# </BaseList>
# ```
def _vue2alpine_expand_if_for(html: str, tag: Tag) -> str:
    # Make a copy, because we'll be modifying the list
    attrs = [*tag.attrs]

    matched_attrs: List[TagAttr] = []
    for attr in attrs:
        if attr.key not in ALL_IF_FOR_DIRECTIVES:
            continue

        if attr.key in ("v-if", "v-else-if", "v-else"):
            has_alpine_attr = any(a.key == "x-if" for a in attrs)
            if has_alpine_attr:
                raise ValueError(f"Cannot have '{attr.key}' directive and 'x-if' on the same tag: {tag.name}")

        if attr.key == "v-for":
            has_alpine_attr = any(a.key == "x-for" for a in attrs)
            if has_alpine_attr:
                raise ValueError(f"Cannot have '{attr.key}' directive and 'x-for' on the same tag: {tag.name}")

        matched_attrs.append(attr)

    # Nothing to do, this is the target state
    if len(matched_attrs) == 0 or (tag.name in ("template", TEMPLATE_TAG_ESC) and len(matched_attrs) == 1):
        return html
    
    # If this is alerady a <template> tag, then we can have one directive on it, but the rest
    # will have to be on separate <template> tags.
    # And since the order of directives in ALL_IF_FOR_DIRECTIVES decides which <template> should
    # be in which, then we will search for the "inner-most", by walking from the end of the list.
    if tag.name in ("template", TEMPLATE_TAG_ESC):
        for directive in reversed(ALL_IF_FOR_DIRECTIVES):
            if not any(attr.key == directive for attr in matched_attrs):
                continue
            
            matched_index = None
            for index, attr in enumerate(matched_attrs):
                if attr.key == directive:
                    matched_index = index
                    break

            if matched_index is not None:
                matched_attrs.pop(index)
                break

    for attr in matched_attrs:
        # Remove attribute from its original tag if it's not on a <template> tag
        html = tag.delete_attr(html, attr.key)

        # And instead wrap the tag's outer HTML in a <template> tag,
        # and move the attribute to it
        html = tag.wrap(
            html,
            start_tag=f"<{TEMPLATE_TAG_ESC} {attr.formatted}>",
            end_tag=f"</{TEMPLATE_TAG_ESC}>",

        )

    return html


# Turn `<MyComponent>` into `<c-my-component>`
#
# To allow to have components like `Button`, we need to pass along the fact that
# the tag is custom. Because Selectolax / Lexbor normalize tags to lowercase, so `<Button>`
# would become `<button>`, which would collide with the standard `<button>` tag.
# Thus we prefix custom components with `c-`, so `Button` becomes `c-button`.
def _vue2alpine_normalize_components(html: str, tag: Tag, known_tags: Optional[List[str]] = None) -> str:
    non_comp_tags = set(known_tags) if known_tags is not None else tags

    tag_name = tag.name
    has_uppercase = any(char.isupper() for char in tag_name)
    if has_uppercase:
        tag_name = to_kebab(tag_name)

    # Check if the tag is among known tags. And if it's not, we prefix it with `c-`.
    is_component = tag_name not in non_comp_tags

    # Nothing to do, this is the target state
    if not is_component:
        return html
    
    tag_name = f"c-{tag_name}"
    html = tag.rename_tag(html, tag_name)

    return html


# Convert Vue's `v-if`, `v-else-if`, `v-else` to Alpine's `x-if`
def _vue2alpine_if_else(nodes: List[LexborNode]) -> List[LexborNode]:
    for root_node in nodes:
        stack = deque([root_node])

        while len(stack):
            curr_node = stack.pop()
            tag_name = curr_node.tag

            if not tag_name:
                raise ValueError("Node must have a tag name")

            # Ignore text, comment and doctype nodes
            if tag_name.startswith("-"):
                continue
            else:
                stack.extend(_get_node_children(curr_node, include_text=True))

            # Convert Vue's `v-if` to Alpine's `x-if` on current node
            conditions: List[str] = []

            def make_not_condition() -> str:
                return " && ".join([
                    "!(" + cond.replace('"', '\\"')+ ")" for cond in conditions
                ])

            if "v-if" in curr_node.attrs:  # type: ignore  # TODO: Fix in Selectolax
                if not curr_node.attrs["v-if"]:  # type: ignore  # TODO: Fix in Selectolax
                    raise ValueError("Empty 'v-if' attribute")

                condition = curr_node.attrs["x-if"] = curr_node.attrs["v-if"]  # type: ignore  # TODO: Fix in Selectolax
                del curr_node.attrs["v-if"]  # type: ignore  # TODO: Fix in Selectolax

                # NOTE: The attributes do NOT contain the wrapping quotes, so `v-if="abc"`
                # becomes {"v-if": "abc"}`
                conditions.append(condition)

                # Process `v-else-if` and `v-else`. These must be on the same level as `v-if`
                # and immediately after it.
                next_node = curr_node.next

                while next_node is not None:
                    if not next_node.tag:
                        raise ValueError("Node must have a tag name")

                    # Skip comments and empty text nodes
                    is_empty_text = next_node.tag.startswith("-text") and not next_node.text().strip()
                    if next_node.tag == "-comment" or is_empty_text:
                        next_node = next_node.next
                        continue

                    # AlpineJS does NOT support `x-else-if`. So to emulate it, we use `x-if`,
                    # and set a condition such that this node must NOT match any of previous conditions.
                    # E.g.
                    # <div v-if="abc">1</div>
                    # <div v-else-if="def">2</div>
                    # <div v-else-if="ghi">3</div>
                    # <div v-else>4</div>
                    #
                    # Becomes:
                    # <div x-if="abc">1</div>
                    # <div x-if="!(abc) && def">2</div>
                    # <div x-if="!(abc) && !(def) && ghi">3</div>
                    # <div x-if="!(abc) && !(def) && !(ghi)">4</div>
                    if "v-else-if" in next_node.attrs:  # type: ignore  # TODO: Fix in Selectolax
                        if not next_node.attrs["v-else-if"]:  # type: ignore  # TODO: Fix in Selectolax
                            raise ValueError("Empty 'v-else-if' attribute")

                        next_node_not_conds = make_not_condition()

                        next_node_orig_cond = next_node.attrs["v-else-if"]  # type: ignore  # TODO: Fix in Selectolax
                        conditions.append(next_node_orig_cond)
                        del next_node.attrs["v-else-if"]  # type: ignore  # TODO: Fix in Selectolax

                        next_node.attrs["x-if"] = f"({next_node_not_conds}) && ({next_node_orig_cond})"  # type: ignore  # TODO: Fix in Selectolax

                        next_node = next_node.next

                    elif "v-else" in next_node.attrs:  # type: ignore  # TODO: Fix in Selectolax
                        next_node_not_conds = make_not_condition()

                        next_node.attrs["x-if"] = f"({next_node_not_conds})"  # type: ignore  # TODO: Fix in Selectolax
                        del next_node.attrs["v-else"]  # type: ignore  # TODO: Fix in Selectolax

                        next_node = next_node.next

                    # Vue's `v-else-if` and `v-else` must be immediately after `v-if`. So if neither,
                    # then there are no more `v-else-if` or `v-else` nodes.
                    else:
                        break

    return nodes


# Add `ssr-if-end` to the last element of `ssr-if`, `ssr-else-if`, `ssr-else`, so we will know
# when to insert `{% endif %}` when converting to django_components.
def _vue2alpine_ssr_if_else(nodes: List[LexborNode]) -> List[LexborNode]:
    stack = deque([*nodes])

    while len(stack):
        node = stack.pop()
        tag_name = node.tag

        if not tag_name:
            raise ValueError("Node must have a tag name")

        # Ignore text, comment and doctype nodes
        if tag_name.startswith("-"):
            continue
        else:
            stack.extend(_get_node_children(node, include_text=True))

        if "ssr-if" in node.attrs:  # type: ignore  # TODO: Fix in Selectolax
            if not node.attrs["ssr-if"]:  # type: ignore  # TODO: Fix in Selectolax
                raise ValueError("Empty 'ssr-if' attribute")

            # Process `ssr-else-if` and `ssr-else`. These must be on the same level as `ssr-if`
            # and immediately after it.
            last_node = node
            next_node = node.next

            while next_node is not None:
                if not next_node.tag:
                    raise ValueError("Node must have a tag name")

                # Skip comments and empty text nodes
                is_empty_text = next_node.tag.startswith("-text") and not next_node.text().strip()
                if next_node.tag == "-comment" or is_empty_text:
                    next_node = next_node.next
                    continue

                if "ssr-else-if" in next_node.attrs or "ssr-else" in next_node.attrs:  # type: ignore  # TODO: Fix in Selectolax
                    last_node = next_node
                    next_node = next_node.next

                # `ssr-else-if` and `ssr-else` must be immediately after `ssr-if`. So if neither,
                # then there are no more `ssr-else-if` or `ssr-else` nodes.
                else:
                    last_node.attrs["ssr-if-end"] = ""  # type: ignore  # TODO: Fix in Selectolax
                    break

    return nodes


# AlpineJS requires a single non-text root element when using `x-for` and `x-if` directives.
# 
# So for multi-root fragments, we must wrap them in a single root element.
#
# In Vue, we can do:
# ```html
# <template x-if="abc">
#   <span>1</span>
#   <span>2</span>
# </template>
# ```
#
# But in AlpineJS, we must do:
# ```html
# <template x-if="abc">
#   <span>
#     <span>1</span>
#     <span>2</span>
#   </span>
# </template>
# ```
#
# Similarly, Alpine directives don't allow text as root element.
#
# So while in Vue we can do:
# ```html
# <template x-if="abc">
#   Some text
# </template>
# ```
#
# In AlpineJS, we must do:
# ```html
# <template x-if="abc">
#   <span>Some text</span>
# </template>
# ```
def _vue2alpine_if_for_single_root(tree: List[LexborNode]) -> List[LexborNode]:
    nodes_queue = [*tree]
    while nodes_queue:
        # Depth-first
        node = nodes_queue.pop(-1)

        if node.tag.startswith("-"):  # type: ignore  # TODO: Fix in Selectolax
            continue

        if_or_for_attr_key: Optional[str] = None
        for key in node.attrs.keys():
            if key in ("x-if", "x-for"):
                if_or_for_attr_key = key
                break

        if node.tag not in ("template", TEMPLATE_TAG_ESC) or if_or_for_attr_key is None:
            nodes_queue.extend(_get_node_children(node, include_text=True))
            continue

        child_nodes = _get_node_children(node, include_text=True)

        # Check if node already has the target state, AKA single root element
        # (leading and trailing whitespace can be ignored)
        nonwhitespace_nodes = []
        for child_node in child_nodes:
            if child_node.tag != "-text" or child_node.text().strip():
                nonwhitespace_nodes.append(child_node)

        has_single_nonwhitespace_node = (
            len(nonwhitespace_nodes) == 1
            and nonwhitespace_nodes[0].tag != "-text"
        )

        # Target state, nothing to do
        if has_single_nonwhitespace_node:
            nodes_queue.extend(child_nodes)
            continue

        # Otherwise, wrap the content in a single <span>
        wrapper_node = create_tag("span")

        # NOTE: We need to copy the nodes, so we can then remove them from their original
        # position. If we tried to just insert them, the nodes would be at 2 places.
        content_html = ""
        for child_node in child_nodes:
            content_html += child_node.html or ""
            child_node.remove()

        content_fragment = parse_fragment(content_html)
        for fragment_node in content_fragment:
            wrapper_node.insert_child(fragment_node)

        node.insert_child(wrapper_node)

        nodes_queue.extend(_get_node_children(node, include_text=True))

    return tree


# Convert Vue's directives to Alpine's
def _vue2alpine_directives(nodes: List[LexborNode]) -> List[LexborNode]:
    stack = deque([*nodes])
    while len(stack):
        node = stack.pop()
        tag_name = node.tag

        if not tag_name:
            raise ValueError("Node must have a tag name")

        # Ignore text, comment and doctype nodes
        if tag_name.startswith("-"):
            continue

        for attr_key in node.attrs.keys():
            if attr_key not in VUE_DIRECTIVES:
                continue

            old_key = attr_key
            mapped_key = VUE_DIRECTIVES[old_key]
            if mapped_key is None:
                raise ValueError(f"Vue directive '{old_key}' is not supported in AlpineJS")
            
            if mapped_key in node.attrs:  # type: ignore  # TODO: Fix in Selectolax
                raise ValueError(
                    f"Cannot convert attribute '{old_key}' to '{mapped_key}'. Attribute '{mapped_key}'"
                    f" already exists on tag '{tag_name}'"
                )
        
            node.attrs[mapped_key] = node.attrs[old_key]  # type: ignore  # TODO: Fix in Selectolax
            del node.attrs[old_key]  # type: ignore  # TODO: Fix in Selectolax

        stack.extend(_get_node_children(node, include_text=True))

    return nodes


def _get_node_children(node: LexborNode, include_text: bool) -> List[LexborNode]:
    if node.tag == "template":
        return _get_template_node_children(node, include_text)
    else:
        return list(node.iter(include_text=include_text))

def _get_template_node_children(node: LexborNode, include_text: bool) -> List[LexborNode]:
    # NOTE: Selectolax / Lexbor has bug that it doesn't return children of <template> tags
    # so as a workaround we replace <template> with <span>, and then extract the children like usual.
    faux_html = f"<{TEMPLATE_TAG_ESC}" + node.html.strip()[9:-9] + f"{TEMPLATE_TAG_ESC}>"  # type: ignore  # TODO: Fix in Selectolax
    frag = parse_fragment(faux_html)[0]
    parent = frag.parent
    frag.unwrap()

    return list(parent.iter(include_text=include_text))  # type: ignore  # TODO: Fix in Selectolax


def _change_node_tag(node: LexborNode, tag: str) -> LexborNode:
    old_tag_name = node.tag
    
    new_start_tag = "<" + tag
    new_end_tag = tag + ">"
    len_to_strip = len(old_tag_name) + 1  # type: ignore  # TODO: Fix in Selectolax
    new_html = new_start_tag + node.html.strip()[len_to_strip:-len_to_strip] + new_end_tag  # type: ignore  # TODO: Fix in Selectolax

    [new_node] = parse_fragment(new_html)

    node.replace_with(new_node)
    return new_node


def _map_node_tag(
    node: LexborNode,
    tag_map: Dict[str, str],
    recursive: bool,
    mode: Literal["top-down", "bottom-up"],
) -> LexborNode:
    # First we change the tag, then we traverse the children
    if mode == "top-down":
        if node.tag in tag_map:
            new_node = _change_node_tag(node, tag_map[node.tag])
        else:
            new_node = node

        if recursive:
            children = _get_node_children(new_node, include_text=True)
            new_children = [_map_node_tag(child, tag_map, recursive, mode) for child in children]

            for child, new_child in zip(children, new_children):
                child.replace_with(new_child)

    # First traverse the children, then change the tag
    else:
        if recursive:
            children = _get_node_children(node, include_text=True)
            new_children = [_map_node_tag(child, tag_map, recursive, mode) for child in children]

            for child, new_child in zip(children, new_children):
                child.replace_with(new_child)

        if node.tag in tag_map:
            new_node = _change_node_tag(node, tag_map[node.tag])
        else:
            new_node = node

    return new_node


# TODO - When converting slots Django, remember to define the default slot by omitting the slot name:
# ```django
# {% component "my_comp" %}
#   {% fill data="data" %}
#     {{ data  }}
#   {% endfill %}
# {% endcomponent %}


# TODO - `ssr-if` as a replacement for Django's `{% if %}` syntax
# TODO - `ssr-for` as a replacement for Django's `{% for %}` syntax
# TODO - `ssr-text` as a replacement for Django's `{{ ... }}` syntax
# TODO - `ssr-html` as a replacement for Django's `{{ ... }}` syntax
# TODO - `ssr-bind` as a replacement for django-components's `...attrs` syntax
# TODO - `ssr:key` as a replacement for django-components's `key=val` syntax

# TODO - Selectolax - Allow to create boolean attributes when `default_slot.attrs["#default"] = True`
# TODO - Selectolax - Fix typing when `default_slot.attrs["#default"] = ""`
# TODO - Selectolax - Allow self-closing tags by resolving the HTML before passing it to Lexbor
# TODO - Selectolax - Lexbor bug - Raise error when accessing `attrs` of text (maybe also comment & doctype) nodes
#        E.g. `list(selectolax.lexbor.parse_fragment("<div a=\"b\"> {{ }} </div>")[0].traverse(True))[1].attrs`
# TODO - Selectolax - bug - `.iter()` doesn't work on <template> tags, returns an empty list
#        E.g. `list(parse_fragment("<span" + node.html.strip()[9:-10] + "span>")[0].iter(include_text=True)))`
# TODO - Selectolax - bug - There's a bug in Selectolax or Lexbor, where when we have a <template> tag, we cannot
#        access its children using `.iter()`. And nor can remove or replace TextNodes inside it.


# TODO DELETE
if __name__ == "__main__":
    text = """
    <div #myslot="props" v-if="bla">
        hello 1{{ abc }}2
        3<MyComp #default />4
        5world 6{{ ghi.def }}7
        8<input value="lol" />9
        10<h3 x="y" xx=20 />11
        12{{ jkl ? "yes" : "no" }}13
        14<div ssr-if="x" ssr-for="y in x" v-if="abc" x-for="item in list">15
        16</div>17
    </div>

    <div v-else-if="bla2">
        hello 1{{ abc }}2
        <template #header>
          3<MyComp #default />4
        </template>

        5world 6{{ ghi.def }}7

        <template #footer>
          8<input value="lol" />9
        </template>
        10<h3 x="y" xx=20 />11
    12</div>

    <table v-else>13
      TBL
    14</table>

    15<table v-pre>
      <thead>
      <tr>
        <th>
          16{{ lol }}17
        </th>
      </tr>
      </thead>
    </table>18

    21<template v-if="true">
      <span>23</span>
      <span>24</span>
        <div #myslot="props" v-if="bla" />
        <div v-else-if="bla2">
            hello 1{{ abc }}2
            <template #header>
                3
            </template>
        </div>
        <table v-else />
    </template>25

    26<template v-for="x in list" v-if="abc">
      27
    </template>28

    <!-- <div x-for="a in b" v-for="c in d" /> -->

    <span ssr-if="True" />
    <span ssr-else-if="False" />
    <span ssr-else />
    """
    print("\n", vue2alpine_normalize(text))
