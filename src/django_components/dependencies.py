"""All code related to management of component dependencies (JS and CSS scripts)"""

import base64
import itertools
import json
import os
import re
from hashlib import md5
from pathlib import Path
from textwrap import dedent
from typing import (
    TYPE_CHECKING,
    Dict,
    List,
    Literal,
    Mapping,
    Optional,
    Sequence,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
)

from django.conf import settings
from django.forms import Media
from django.http import HttpRequest, HttpResponse, HttpResponseNotAllowed, HttpResponseNotFound
from django.shortcuts import redirect
from django.template import Context, TemplateSyntaxError
from django.templatetags.static import static
from django.urls import path, reverse
from django.utils.safestring import SafeString, mark_safe
from djc_core_html_parser import set_html_attributes

from django_components.cache import get_component_media_cache
from django_components.constants import COMP_ID_LENGTH
from django_components.node import BaseNode
from django_components.extension import OnExtraMediaContext, extensions
from django_components.util.css import scope_css
from django_components.util.misc import hash_comp_cls, is_nonempty_str, wrap_js_script

if TYPE_CHECKING:
    from django_components.component import Component


ScriptType = Literal["css", "js"]
DependenciesStrategy = Literal["document", "fragment", "simple", "prepend", "append", "ignore"]
"""
Type for the available strategies for rendering JS and CSS dependencies.

Read more about the [dependencies strategies](../../concepts/advanced/rendering_js_css).
"""

DEPS_STRATEGIES = ("document", "fragment", "simple", "prepend", "append", "ignore")


#########################################################
# 1. Cache the inlined component JS and CSS scripts (`Component.js` and `Component.css`).
#
#    To support HTML fragments, when a fragment is loaded on a page,
#    we on-demand request the JS and CSS files of the components that are
#    referenced in the fragment.
#
#    Thus, we need to persist the JS and CSS files across requests. These are then accessed
#    via `cached_script_view` endpoint.
#########################################################


# Generate keys like
# `__components:MyButton_a78y37:js:df7c6d10`
# `__components:MyButton_a78y37:css`
def _gen_cache_key(
    comp_cls_id: str,
    script_type: ScriptType,
    input_hash: Optional[str],
) -> str:
    if input_hash:
        return f"__components:{comp_cls_id}:{script_type}:{input_hash}"
    else:
        return f"__components:{comp_cls_id}:{script_type}"


def _is_script_in_cache(
    comp_cls: Type["Component"],
    script_type: ScriptType,
    input_hash: Optional[str],
) -> bool:
    cache_key = _gen_cache_key(comp_cls.class_id, script_type, input_hash)
    cache = get_component_media_cache()
    return cache.has_key(cache_key)


def _cache_script(
    comp_cls: Type["Component"],
    script: str,
    script_type: ScriptType,
    input_hash: Optional[str],
) -> None:
    """
    Given a component and it's inlined JS or CSS, store the JS/CSS in a cache,
    so it can be retrieved via URL endpoint.
    """
    # TODO - CALL `on_css_postprocess` and `on_js_postprocess` HERE
    #        TO ENABLE MINIFICATION AND OTHER POST-PROCESSING

    # E.g. `__components:MyButton:js:df7c6d10`
    if script_type in ("js", "css"):
        cache_key = _gen_cache_key(comp_cls.class_id, script_type, input_hash)
    else:
        raise ValueError(f"Unexpected script_type '{script_type}'")
    
    # Do NOT save file to the cache if it is among the static files!
    # This allows users to "export" the files with `collectcomponent` and post-process
    # the files (e.g. use Sass or TypeScript)
    # NOTE: This make sense only for when `input_hash` is None, because thn we are
    # processing component's inlined JS / CSS.
    if not input_hash and has_component_inline_dependency_in_static(comp_cls, script_type):
        return

    # But if the file is NOT among the static files, we will cache it for the lifetime of
    # the server.
    # NOTE: By setting the script in the cache, we will be able to retrieve it
    # via the endpoint, e.g. when we make a request to `/components/cache/MyComp_ab0c2d.js`.
    cache = get_component_media_cache()
    cache.set(cache_key, script.strip())


def preprocess_inlined_js(comp_cls: Type["Component"], content: str) -> str:
    def wrap_js_body(body: str) -> str:
        # TODO - HERE WE CAN REGISTER THE PLUGINS (AS THIRD ARG). JS PLUGINS ARE HIGHER ORDER FUNCTIONS / DECORATORS
        on_load_func = dedent(
            f"""
            const $onLoad = (cb) => globalThis.Components.manager.registerComponent(
              "{comp_cls._class_hash}",
              cb,
            );
            """
        )

        # TODO: HERE SOMEHOW FIGURE OUT HOW TO MAKE THE EXEC SCRIPT WAIT FOR THE COMPONENTS' JS TO LOAD
        mark_loaded = f'Components.manager.markScriptLoaded("js", "{comp_cls._class_hash}");'

        body = f"{on_load_func}\n{body}\n{mark_loaded}"

        if not comp_cls.js_wrap_in_function:
            return body

        return dedent(f"""
            (async () => {{
              {body}
            }})()
        """)

    # TODO UPDAATE COMMENT - WE WRAP IN SELF_CLOASING AND EXPOSE $ON_LOAD

    # We wrap the user's definition of `Component.js` in a callback, so that we can control
    # when to call it (per instance), and to be able to provide extra metadata.
    # Since the JS script may be JS module or TypeScript file, with import statements,
    # we have to use `wrap_js_script` which smartly wraps the content, AFTER the import statements.
    return wrap_js_script(content, wrap_js_body)


def cache_component_js(comp_cls: Type["Component"]) -> None:
    """
    Cache the content from `Component.js`. This is the common JS that's shared
    among all instances of the same component. So even if the component is rendered multiple
    times, this JS is loaded only once.
    """
    if not comp_cls.js or not is_nonempty_str(comp_cls.js) or _is_script_in_cache(comp_cls, "js", None):
        return None

    _cache_script(
        comp_cls=comp_cls,
        script=comp_cls.js,
        script_type="js",
        input_hash=None,
    )


# NOTE: In CSS, we link the CSS vars to the component via a stylesheet that defines
# the CSS vars under `[data-djc-css-a1b2c3]`. Because of this we define the variables
# separately from the rest of the CSS definition.
#
# We use conceptually similar approach for JS, except in JS we have to manually associate
# the JS variables ("stylesheet") with the target HTML element ("component").
#
# It involves 3 steps:
# 1. Register the common logic (equivalent to registering common CSS).
#    with `Components.manager.registerComponent`.
# 2. Register the unique set of JS variables (equivalent to defining CSS vars)
#    with `Components.manager.registerComponentData`.
# 3. Actually run a component's JS instance with `Components.manager.callComponent`,
#    specifying the components HTML elements with `component_id`, and JS vars with `input_hash`.
def cache_component_js_vars(comp_cls: Type["Component"], js_vars: Mapping) -> Optional[str]:
    if not is_nonempty_str(comp_cls.js):
        return None

    # The hash for the file that holds the JS variables is derived from the variables themselves.
    json_data = json.dumps(js_vars)
    input_hash = md5(json_data.encode()).hexdigest()[0:6]

    # Generate and cache a JS script that contains the JS variables.
    if not _is_script_in_cache(comp_cls, "js", input_hash):
        js_vars_script = _gen_exec_script(
            to_load_css_tags=[],
            to_load_js_tags=[],
            loaded_css_urls=[],
            loaded_js_urls=[],
            comp_calls=[],
            comp_js_vars=[
                # TODO - MAKE INTO NAMEDTUPLE
                (comp_cls._class_hash, input_hash, json_data),
            ]
        )

        _cache_script(
            comp_cls=comp_cls,
            script=cast(str, js_vars_script),
            script_type="js",
            input_hash=input_hash,
        )

    return input_hash


def wrap_component_js(comp_cls: Type["Component"], content: str) -> str:
    if "</script" in content:
        raise RuntimeError(
            f"Content of `Component.js` for component '{comp_cls.__name__}' contains '</script>' end tag. "
            "This is not allowed, as it would break the HTML."
        )

    # TODO: if app_settings.COMPILERS_ENABLED and "--format=esm" in app_settings.COMPILERS_ESBUILD_CONFIG:
    #       then: type="module"
    # TODO: HERE WE PARAMETRIZE HOW THE INLINED SCRIPT IS TURNED INTO A TAG, SO THAT FOR VUE
    #       WE CAN USE `type="module"`
    # script = mark_safe(comp_cls.js_tag(script))
    # TODO: This is how it is done by default
    return f"<script>{content}</script>"


def cache_component_css(comp_cls: Type["Component"]) -> None:
    """
    Cache the content from `Component.css`. This is the common CSS that's shared
    among all instances of the same component. So even if the component is rendered multiple
    times, this CSS is loaded only once.
    """
    if not comp_cls.css or not is_nonempty_str(comp_cls.css) or _is_script_in_cache(comp_cls, "css", None):
        return None

    # Apply the CSS part of Vue-like CSS scoping
    css_content = comp_cls.css
    if comp_cls.css_scoped:
        comp_cls_hash = hash_comp_cls(comp_cls, include_name=False)
        scope = f"[data-djc-scope-{comp_cls_hash}]"
        css_content = scope_css(css_code=comp_cls.css, scope_id=scope)

    _cache_script(
        comp_cls=comp_cls,
        script=css_content,
        script_type="css",
        input_hash=None,
    )


# NOTE: In CSS, we link the CSS vars to the component via a stylesheet that defines
# the CSS vars under the CSS selector `[data-djc-css-a1b2c3]`. We define the stylesheet
# with variables separately from `Component.css`, because different instances may return different
# data from `get_css_data()`, which will live in different stylesheets.
def cache_component_css_vars(comp_cls: Type["Component"], css_vars: Mapping) -> Optional[str]:
    if not is_nonempty_str(comp_cls.css):
        return None

    # The hash for the file that holds the CSS variables is derived from the variables themselves.
    json_data = json.dumps(css_vars)
    input_hash = md5(json_data.encode()).hexdigest()[0:6]

    # Generate and cache a CSS stylesheet that contains the CSS variables.
    if not _is_script_in_cache(comp_cls, "css", input_hash):
        formatted_vars = "\n".join([
            f"  --{key}: {value};"
            for key, value in css_vars.items()
        ])

        # ```css
        # [data-djc-css-f3f3eg9] {
        #   --my-var: red;
        # }
        # ```
        input_css = dedent(f"""
            /* {comp_cls._class_hash} */
            [data-djc-css-{input_hash}] {{ 
            {formatted_vars}
            }}
        """)

        _cache_script(
            comp_cls=comp_cls,
            script=input_css,
            script_type="css",
            input_hash=input_hash,
        )

    return input_hash


def wrap_component_css(comp_cls: Type["Component"], content: str) -> str:
    if "</style" in content:
        raise RuntimeError(
            f"Content of `Component.css` for component '{comp_cls.__name__}' contains '</style>' end tag. "
            "This is not allowed, as it would break the HTML."
        )

    # TODO: HERE WE PARAMETRIZE HOW THE INLINED STYLE IS TURNED INTO A TAG
    # script = mark_safe(comp_cls.css_tag(script))
    # TODO: This is how it is done by default
    return f"<style>{content}</style>"


def make_component_inline_dependency_static_path(comp_cls: Type["Component"], script_type: str) -> Optional[Path]:
    if comp_cls._comp_path_relative is None:
        return None

    # E.g. `<static_root>/path/to/component/rel/to/components/dir/compFilename-MyTable_a0b20cd.js`
    # Where:
    # - Path from <static_root> to the component is the same as the path from
    #   the corresponding `COMPONENTS.dirs` parent to the component.
    # - To allow multiple components to be defined in a single file, the filename
    #   for each inlined CSS / JS is `<filename>-<component_hash>.<suffix>`
    file_stem = Path(comp_cls._comp_path_relative).stem  # Get original filename
    file_name = f"{file_stem}-{comp_cls._class_hash}.{script_type}"  # Append component hash and suffix
    file_path = Path(settings.STATIC_ROOT, comp_cls._comp_path_relative).with_name(file_name)
    return file_path


def make_component_inline_dependency_static_url(comp_cls_hash: str, script_type: ScriptType) -> str:
    file_path = f"django_components/cache/{comp_cls_hash}.{script_type}"
    file_url = static(file_path)
    return file_url


def write_component_inline_dependencies_to_static(comp_cls: Type["Component"]) -> List[Path]:
    written_files: List[Path] = []

    # Write the component's JS/CSS to files inside STATIC_ROOT
    dependencies: List[Tuple[str, Optional[str]]] = [
        (comp_cls.js_lang, comp_cls.js),
        (comp_cls.css_lang, comp_cls.css),
    ]
    for script_type, content in dependencies:
        # Construct static dir path, e.g.
        # `<static_root>/todo/todo_Todo_7877e9.js`
        # `<static_root>/todo/todo_Todo_7877e9.ts`
        # `<static_root>/todo/todo_Todo_7877e9.css`
        file_path = make_component_inline_dependency_static_path(comp_cls, script_type)
        if file_path is None:
            continue

        # Write component's JS/CSS to external file, so it can be post-processed
        if content:
            os.makedirs(file_path.parent, exist_ok=True)
            file_path.write_text(content, "utf-8")
            written_files.append(file_path)
        else:
            # Delete stale file if present
            if file_path.exists():
                file_path.unlink()

    return written_files


def has_component_inline_dependency_in_static(comp_cls: Type["Component"], script_type: ScriptType) -> bool:
    file_path = make_component_inline_dependency_static_path(comp_cls, script_type)
    return file_path.exists() if file_path is not None else False


#########################################################
# 2. Modify the HTML to use the same IDs defined in previous
#    step for the inlined CSS and JS scripts, so the scripts
#    can be applied to the correct HTML elements. And embed
#    component + JS/CSS relationships as HTML comments.
#########################################################


def set_component_attrs_for_js_and_css(
    html_content: Union[str, SafeString],
    component_id: Optional[str],
    class_id: Optional[str],
    css_input_hash: Optional[str],
    root_attributes: Optional[List[str]] = None,
) -> Tuple[Union[str, SafeString], Dict[str, List[str]]]:
    # These are the attributes that we want to set on the root element.
    all_root_attributes = [*root_attributes] if root_attributes else []

    # Component ID is used for executing JS script, e.g. `data-djc-id-ca1b2c3`
    #
    # NOTE: We use `data-djc-css-a1b2c3` and `data-djc-id-ca1b2c3` instead of
    # `data-djc-css="a1b2c3"` and `data-djc-id="a1b2c3"`, to allow
    # multiple values to be associated with the same element, which may happen if
    # one component renders another.
    if component_id:
        all_root_attributes.append(f"data-djc-id-{component_id}")

    # We apply the CSS scoping attribute to both root and non-root tags.
    #
    # This is the HTML part of Vue-like CSS scoping.
    # That is, for each HTML element that the component renders, we add a `data-djc-scope-a1b2c3` attribute.
    # And we stop when we come across a nested components.
    if class_id:
        all_attributes.append(f"data-djc-classid-{class_id}")

    # Attribute by which we bind the CSS variables to the component's CSS,
    # e.g. `data-djc-css-a1b2c3`
    if css_input_hash:
        all_root_attributes.append(f"data-djc-css-{css_input_hash}")

    # These attributes are set on all tags
    all_attributes = []

    is_safestring = isinstance(html_content, SafeString)
    updated_html, child_components = set_html_attributes(
        html_content,
        root_attributes=all_root_attributes,
        all_attributes=all_attributes,
        # Setting this means that set_html_attributes will check for HTML elemetnts with this
        # attribute, and return a dictionary of {attribute_value: [attributes_set_on_this_tag]}.
        #
        # So if HTML contains tag <template djc-render-id="123"></template>,
        # and we set on that tag `data-djc-id-123`, then we will get
        # {
        #   "123": ["data-djc-id-123"],
        # }
        #
        # This is a minor optimization. Without this, when we're rendering components in
        # component_post_render(), we'd have to parse each `<template djc-render-id="123"></template>`
        # to find the HTML attribute that were set on it.
        watch_on_attribute="djc-render-id",
    )
    updated_html = mark_safe(updated_html) if is_safestring else updated_html

    return updated_html, child_components


# NOTE: To better understand the next section, consider this:
#
# We define and cache the component's JS and CSS at the same time as
# when we render the HTML. However, the resulting HTML MAY OR MAY NOT
# be used in another component.
#
# IF the component's HTML IS used in another component, and the other
# component want to render the JS or CSS dependencies (e.g. inside <head>),
# then it's only at that point when we want to access the data about
# which JS and CSS scripts is the component's HTML associated with.
#
# This happens AFTER the rendering context, so there's no Context to rely on.
#
# Hence, we store the info about associated JS and CSS right in the HTML itself.
# As an HTML comment `<!-- -->`. Thus, the inner component can be used as many times
# and in different components, and they will all know to fetch also JS and CSS of the
# inner components.
def insert_component_dependencies_comment(
    content: str,
    # NOTE: We pass around the component CLASS, so the dependencies logic is not
    # dependent on ComponentRegistries
    component_cls: Type["Component"],
    component_id: str,
    js_input_hash: Optional[str],
    css_input_hash: Optional[str],
) -> SafeString:
    """
    Given some textual content, prepend it with a short string that
    will be used by the `render_dependencies()` function to collect all
    declared JS / CSS scripts.
    """
    data = f"{component_cls.class_id},{component_id},{js_input_hash or ''},{css_input_hash or ''}"

    # NOTE: It's important that we put the comment BEFORE the content, so we can
    # use the order of comments to evaluate components' instance JS code in the correct order.
    output = mark_safe(COMPONENT_DEPS_COMMENT.format(data=data) + content)
    return output


#########################################################
# 3. Given a FINAL HTML composed of MANY components,
#    process all the HTML dependency comments (created in
#    previous step), obtaining ALL JS and CSS scripts
#    required by this HTML document. And post-process them,
#    so the scripts are either inlined into the HTML, or
#    fetched when the HTML is loaded in the browser.
#########################################################


TContent = TypeVar("TContent", bound=Union[bytes, str])


CSS_PLACEHOLDER_NAME = "CSS_PLACEHOLDER"
CSS_PLACEHOLDER_NAME_B = CSS_PLACEHOLDER_NAME.encode()
JS_PLACEHOLDER_NAME = "JS_PLACEHOLDER"
JS_PLACEHOLDER_NAME_B = JS_PLACEHOLDER_NAME.encode()

CSS_DEPENDENCY_PLACEHOLDER = f'<link name="{CSS_PLACEHOLDER_NAME}">'
JS_DEPENDENCY_PLACEHOLDER = f'<script name="{JS_PLACEHOLDER_NAME}"></script>'
COMPONENT_DEPS_COMMENT = "<!-- _RENDERED {data} -->"

# E.g. `<!-- _RENDERED table,123,a92ef298,bd002c3 -->`
COMPONENT_COMMENT_REGEX = re.compile(rb"<!--\s+_RENDERED\s+(?P<data>[\w\-,/]+?)\s+-->")
# E.g. `table,123,a92ef298,bd002c3`
# - comp_cls_id - Cache key of the component class that was rendered
# - id - Component render ID
# - js - Cache key for the JS data from `get_js_data()`
# - css - Cache key for the CSS data from `get_css_data()`
SCRIPT_NAME_REGEX = re.compile(
    rb"^(?P<comp_cls_id>[\w\-\./]+?),(?P<id>[\w]+?),(?P<js>[0-9a-f]*?),(?P<css>[0-9a-f]*?)$"
)
# E.g. `data-djc-id-ca1b2c3`, but the length is set from `COMP_ID_LENGTH`
MAYBE_COMP_ID = r'(?: data-djc-id-\w{{{COMP_ID_LENGTH}}}="")?'.format(COMP_ID_LENGTH=COMP_ID_LENGTH)
# E.g. `data-djc-css-99914b`
MAYBE_COMP_CSS_ID = r'(?: data-djc-css-\w{6}="")?'
# TODO - ACTUALLY CHANGE THIS TO `data-djc-cls`? Because the hash will be unique for each component CLASS.
# E.g. `data-djc-scope-99914b=""`
MAYBE_SCOPE_CSS_ID = r'(?: data-djc-scope-\w{6}="")?'

PLACEHOLDER_REGEX = re.compile(
    r"{css_placeholder}|{js_placeholder}".format(
        # TODO - REFACTRO THE PATTERNS BELOW TO ACCEPT ANY AMOUNT OF HTML ATTRS
        #        BEFORE AND AFTER THE PLACEHOLDER NAME

        # NOTE: Optionally, the CSS and JS placeholders may have any of the following attributes,
        # as these attributes are assigned BEFORE we replace the placeholders with actual <script> / <link> tags:
        # - `data-djc-scope-xxxxxx`
        # - `data-djc-id-xxxxxx`
        # - `data-djc-css-xxxxxx`
        css_placeholder=f'<link name="{CSS_PLACEHOLDER_NAME}"{MAYBE_COMP_CSS_ID}{MAYBE_COMP_ID}{MAYBE_SCOPE_CSS_ID}/?>',  # noqa: E501
        js_placeholder=f'<script name="{JS_PLACEHOLDER_NAME}"{MAYBE_COMP_CSS_ID}{MAYBE_COMP_ID}{MAYBE_SCOPE_CSS_ID}></script>',  # noqa: E501
    ).encode()
)


def render_dependencies(content: TContent, strategy: DependenciesStrategy = "document") -> TContent:
    """
    Given an HTML string (str or bytes) that contains parts that were rendered by components,
    this function searches the HTML for the components used in the rendering,
    and inserts the JS and CSS of the used components into the HTML.

    Returns the edited copy of the HTML.

    See [Rendering JS / CSS](../../concepts/advanced/rendering_js_css/).

    **Args:**

    - `content` (str | bytes): The rendered HTML string that is searched for components, and
        into which we insert the JS and CSS tags. Required.

    - `type` - Optional. Configure how to handle JS and CSS dependencies. Read more about
        [Render types](../../concepts/fundamentals/rendering_components#render-types).

        There are five render types:

        - [`"document"`](../../concepts/advanced/rendering_js_css#document) (default)
            - Smartly inserts JS / CSS into placeholders or into `<head>` and `<body>` tags.
            - Inserts extra script to allow `fragment` types to work.
            - Assumes the HTML will be rendered in a JS-enabled browser.
        - [`"fragment"`](../../concepts/advanced/rendering_js_css#fragment)
            - A lightweight HTML fragment to be inserted into a document.
            - No JS / CSS included.
        - [`"simple"`](../../concepts/advanced/rendering_js_css#simple)
            - Smartly insert JS / CSS into placeholders or into `<head>` and `<body>` tags.
            - No extra script loaded.
        - [`"prepend"`](../../concepts/advanced/rendering_js_css#prepend)
            - Insert JS / CSS before the rendered HTML.
            - No extra script loaded.
        - [`"append"`](../../concepts/advanced/rendering_js_css#append)
            - Insert JS / CSS after the rendered HTML.
            - No extra script loaded.

    Example:
    ```python
    def my_view(request):
        template = Template('''
            {% load components %}
            <!doctype html>
            <html>
                <head></head>
                <body>
                    <h1>{{ table_name }}</h1>
                    {% component "table" name=table_name / %}
                </body>
            </html>
        ''')

        html = template.render(
            Context({
                "table_name": request.GET["name"],
            })
        )

        # This inserts components' JS and CSS
        processed_html = render_dependencies(html)

        return HttpResponse(processed_html)
    ```
    """
    if strategy not in DEPS_STRATEGIES:
        raise ValueError(f"Invalid strategy '{strategy}'")
    elif strategy == "ignore":
        return content

    is_safestring = isinstance(content, SafeString)

    if isinstance(content, str):
        content_ = content.encode()
    else:
        content_ = cast(bytes, content)

    content_, js_dependencies, css_dependencies = _process_dep_declarations(content_, strategy)

    # Replace the placeholders with the actual content
    # If strategy in (`document`, 'simple'), we insert the JS and CSS directly into the HTML,
    #                        where the placeholders were.
    # If strategy == `fragment`, we let the client-side manager load the JS and CSS,
    #                        and remove the placeholders.
    did_find_js_placeholder = False
    did_find_css_placeholder = False
    css_replacement = css_dependencies if strategy in ("document", "simple") else b""
    js_replacement = js_dependencies if strategy in ("document", "simple") else b""

    def on_replace_match(match: "re.Match[bytes]") -> bytes:
        nonlocal did_find_css_placeholder
        nonlocal did_find_js_placeholder

        if CSS_PLACEHOLDER_NAME_B in match[0]:
            replacement = css_replacement
            did_find_css_placeholder = True
        elif JS_PLACEHOLDER_NAME_B in match[0]:
            replacement = js_replacement
            did_find_js_placeholder = True
        else:
            raise RuntimeError(
                "Unexpected error: Regex for component dependencies processing"
                f" matched unknown string '{match[0].decode()}'"
            )
        return replacement

    content_ = PLACEHOLDER_REGEX.sub(on_replace_match, content_)

    # By default ("document") and for "simple" strategy, if user didn't specify any `{% component_dependencies %}`,
    # then try to insert the JS scripts at the end of <body> and CSS sheets at the end
    # of <head>.
    if strategy in ("document", "simple") and (not did_find_js_placeholder or not did_find_css_placeholder):
        maybe_transformed = _insert_js_css_to_default_locations(
            content_.decode(),
            css_content=None if did_find_css_placeholder else css_dependencies.decode(),
            js_content=None if did_find_js_placeholder else js_dependencies.decode(),
        )

        if maybe_transformed is not None:
            content_ = maybe_transformed.encode()

    # In case of a fragment, we only append the JS (actually JSON) to trigger the call of dependency-manager
    elif strategy == "fragment":
        content_ += js_dependencies
    # For prepend / append, we insert the JS and CSS before / after the content
    elif strategy == "prepend":
        content_ = js_dependencies + css_dependencies + content_
    elif strategy == "append":
        content_ = content_ + js_dependencies + css_dependencies

    # Return the same type as we were given
    output = content_.decode() if isinstance(content, str) else content_
    output = mark_safe(output) if is_safestring else output
    return cast(TContent, output)


# Renamed so we can access use this function where there's kwarg of the same name
_render_dependencies = render_dependencies


# Overview of this function:
# 1. We extract all HTML comments like `<!-- _RENDERED table_10bac31,1234-->`.
# 2. We look up the corresponding component classes
# 3. For each component class we get the component's inlined JS and CSS,
#    and the JS and CSS from `Media.js/css`
# 4. We add our client-side JS logic into the mix (`django_components/django_components.min.js`)
#    - For fragments, we would skip this step.
# 5. For all the above JS and CSS, we figure out which JS / CSS needs to be inserted directly
#    into the HTML, and which can be loaded with the client-side manager.
#    - Components' inlined JS is inserted directly into the HTML as `<script> ... <script>`,
#      to avoid having to issues 10s of requests for each component separately.
#    - Components' inlined CSS is inserted directly into the HTML as `<style> ... <style>`,
#      to avoid a [flash of unstyled content](https://en.wikipedia.org/wiki/Flash_of_unstyled_content)
#      that would occur if we had to load the CSS via JS request.
#    - For CSS from `Media.css` we insert that as `<link href="...">` HTML tags, also to avoid
#      the flash of unstyled content
#    - For JS from `Media.js`, we let the client-side manager load that, so that, even if
#      multiple components link to the same JS script in their `Media.js`, the linked JS
#      will be fetched and executed only once.
# 6. And lastly, we generate a JS script that will load / mark as loaded the JS and CSS
#    as categorized in previous step.
def _process_dep_declarations(content: bytes, strategy: DependenciesStrategy) -> Tuple[bytes, bytes, bytes]:
    """
    Process a textual content that may include metadata on rendered components.
    The metadata has format like this

    `<!-- _RENDERED component_name,component_id,js_hash,css_hash;... -->`

    E.g.

    `<!-- _RENDERED table_10bac31,123,a92ef298,bd002c3 -->`
    """
    # Extract all matched instances of `<!-- _RENDERED ... -->` while also removing them from the text
    all_parts: List[bytes] = list()

    def on_replace_match(match: "re.Match[bytes]") -> bytes:
        all_parts.append(match.group("data"))
        return b""

    content = COMPONENT_COMMENT_REGEX.sub(on_replace_match, content)

    # NOTE: Python's set does NOT preserve order, so both set and list are needed
    seen_comp_hashes: Set[str] = set()
    comp_hashes: List[str] = []
    # Used for passing Python vars to JS/CSS
    variables_data: List[Tuple[str, ScriptType, Optional[str]]] = []  # TODO ADD TYPES FOR THESE FOR CLARITY
    comp_data: List[Tuple[str, ScriptType, Optional[str]]] = []
    comp_calls: List[Tuple[str, str, Optional[str]]] = []

    # Process individual parts. Each part is like a CSV row of `name,id,js,css`.
    # E.g. something like this:
    # `table_10bac31,1234,a92ef298,a92ef298`
    for part in all_parts:
        part_match = SCRIPT_NAME_REGEX.match(part)

        if not part_match:
            raise RuntimeError("Malformed dependencies data")

        comp_cls_id: str = part_match.group("comp_cls_id").decode("utf-8")
        comp_id = part_match.group("id").decode("utf-8")
        js_variables_hash: Optional[str] = part_match.group("js").decode("utf-8") or None
        css_variables_hash: Optional[str] = part_match.group("css").decode("utf-8") or None

        if comp_cls_id in seen_comp_hashes:
            continue

        comp_hashes.append(comp_cls_id)
        seen_comp_hashes.add(comp_cls_id)

        # Schedule to load the `<script>` / `<link>` tags for the JS / CSS from `Component.js/css`.
        comp_data.append((comp_cls_id, "js", None))
        comp_data.append((comp_cls_id, "css", None))

        # Schedule to load the `<script>` / `<link>` tags for the JS / CSS variables.
        # Skip if no variables are defined.
        if js_variables_hash is not None:
            variables_data.append((comp_cls_id, "js", js_variables_hash))
        if css_variables_hash is not None:
            variables_data.append((comp_cls_id, "css", css_variables_hash))

        # Add component instance to the queue of calls to `$onLoad` callbacks
        comp_cls = comp_hash_mapping[comp_cls_hash]
        has_js = is_nonempty_str(comp_cls.js)
        if has_js:
            comp_calls.append((comp_cls_hash, comp_id, js_input_hash))

    # Take Components' own JS / CSS (Component.js/css)
    # and decide which ones should be:
    # - Inserted into the HTML as <script> / <style> tags
    # - Loaded with the client-side manager
    # - Marked as loaded in the dependency manager
    (
        component_js_urls_to_load,
        component_css_urls_to_load,
        component_js_tags,
        component_css_tags,
        component_js_urls_loaded,
        component_css_urls_loaded,
    ) = _prepare_tags_and_urls(comp_data, strategy)

    # Take JS / CSS for component variables (e.g. if component returned something
    # from `get_js_data()` and `get_css_data()`) and decide which ones should be:
    # - Inserted into the HTML as <script> / <style> tags
    # - Loaded with the client-side manager
    # - Marked as loaded in the dependency manager
    (
        js_variables_urls_to_load,
        css_variables_urls_to_load,
        js_variables_tags,
        css_variables_tags,
        js_variables_urls_loaded,
        css_variables_urls_loaded,
    ) = _prepare_tags_and_urls(variables_data, strategy)

    def get_component_media(comp_cls_id: str) -> Media:
        from django_components.component import get_component_by_class_id

        comp_cls = get_component_by_class_id(comp_cls_id)
        return comp_cls.media

    all_medias = [
        # JS / CSS files from Plugins
        *plugins.medias,

        # JS / CSS files from Component.Media.js/css.
        *[get_component_media(comp_cls_id) for comp_cls_id in comp_hashes],
        # All the inlined scripts that we plan to fetch / load
        Media(
            js=[*component_js_urls_to_load, *js_variables_urls_to_load],
            css={"all": [*component_css_urls_to_load, *css_variables_urls_to_load]},
        ),
    ]

    # Once we have ALL JS and CSS URLs that we want to fetch, we can convert them to
    # <script> and <link> tags. Note that this is done by the user-provided Media classes.
    # fmt: off
    media_css_tags = [
        tag
        for media in all_medias if media is not None
        for tag in media.render_css()
    ]
    media_js_tags = [
        tag
        for media in all_medias if media is not None
        for tag in media.render_js()
    ]
    # fmt: on

    # Postprocess all <script> and <link> tags to 1) dedupe, and 2) extract URLs.
    # For the deduplication, if multiple components link to the same JS/CSS, but they
    # render the <script> or <link> tag differently, we go with the first tag that we come across.
    media_css_tags, media_css_urls = _postprocess_media_tags("css", media_css_tags)
    media_js_tags, media_js_urls = _postprocess_media_tags("js", media_js_tags)

    loaded_css_urls = sorted(
        [
            *component_css_urls_loaded,
            *css_variables_urls_loaded,
            # NOTE: When rendering a "document", the initial CSS is inserted directly into the HTML
            # to avoid a flash of unstyled content. In such case, the "CSS to load" is actually already
            # loaded, so we have to mark those scripts as loaded in the dependency manager.
            *(media_css_urls if strategy == "document" else []),
        ]
    )
    loaded_js_urls = sorted(
        [
            *component_js_urls_loaded,
            *js_variables_urls_loaded,
            # NOTE: When rendering a "document", the initial JS is inserted directly into the HTML
            # so the scripts are executed at proper order. In such case, the "JS to load" is actually already
            # loaded, so we have to mark those scripts as loaded in the dependency manager.
            *(media_js_urls if strategy == "document" else []),
        ]
    )

    # NOTE: No exec script for the "simple" mode, as that one is NOT using the dependency manager
    if strategy in ("document", "fragment"):
        exec_script = _gen_exec_script(
            to_load_js_tags=media_js_tags if strategy == "fragment" else [],
            to_load_css_tags=media_css_tags if strategy == "fragment" else [],
            loaded_js_urls=loaded_js_urls,
            loaded_css_urls=loaded_css_urls,
            comp_calls=comp_calls,
            comp_js_vars=[],
        )
    else:
        exec_script = None

    # Core scripts without which the rest wouldn't work
    core_script_tags = Media(
        # NOTE: When rendering a document, the initial JS is inserted directly into the HTML
        js=[static("django_components/django_components.min.js")] if strategy == "document" else [],
    ).render_js()

    # TODO: HERE WE INSERT THE PLUGIN'S JS AND CSS!!
    plugin_medias = plugins.on_extra_media(
        OnExtraMediaContext(
            # Plugins receive a list of components (+ IDs) that were rendered
            # NOTE: The list is generated from `comp_calls` for simplicity, since it contains the IDs.
            components=[
                (comp_hash_mapping[comp_cls_hash], comp_id)
                for comp_cls_hash, comp_id, _ in comp_calls
            ],
        )
    )
    plugin_js_tags = itertools.chain(*[plugin_media.render_js() for plugin_media in plugin_medias])
    plugin_css_tags = itertools.chain(*[plugin_media.render_css() for plugin_media in plugin_medias])

    final_script_tags = "".join(
        [
            # JS by us
            *[tag for tag in core_script_tags],

            # JS from plugins
            *[tag for tag in plugin_js_tags],

            # Make calls to the JS dependency manager
            # Loads JS from `Media.js` and `Component.js` if fragment
            *([exec_script] if exec_script else []),
            # JS from `Media.js`
            # NOTE: When strategy in ("document", "simple", "prepend", "append"), the initial JS is inserted
            # directly into the HTML so the scripts are executed at proper order. In the dependency manager,
            # we only mark those scripts as loaded.
            *(media_js_tags if strategy in ("document", "simple", "prepend", "append") else []),
            # JS variables
            *[tag for tag in js_variables_tags],
            # JS from `Component.js` (if not fragment)
            *[tag for tag in component_js_tags],
        ]
    )

    final_css_tags = "".join(
        [
            # CSS by us
            # <NONE>

            # CSS from plugins
            *[tag for tag in plugin_css_tags],

            # CSS from `Component.css` (if not fragment)
            *[tag for tag in component_css_tags],
            # CSS variables
            *[tag for tag in css_variables_tags],
            # CSS from `Media.css` (plus from `Component.css` if fragment)
            # NOTE: Similarly to JS, the initial CSS is loaded outside of the dependency
            #       manager, and only marked as loaded, to avoid a flash of unstyled content.
            *[tag for tag in media_css_tags],
        ]
    )

    return (content, final_script_tags.encode("utf-8"), final_css_tags.encode("utf-8"))


href_pattern = re.compile(r'href="([^"]+)"')
src_pattern = re.compile(r'src="([^"]+)"')


# Detect duplicates by URLs, extract URLs, and sort by URLs
def _postprocess_media_tags(
    script_type: ScriptType,
    tags: List[str],
) -> Tuple[List[str], List[str]]:
    urls: List[str] = []
    tags_by_url: Dict[str, str] = {}

    for tag in tags:
        # Extract the URL from <script src="..."> or <link href="...">
        if script_type == "js":
            attr = "src"
            attr_pattern = src_pattern
        else:
            attr = "href"
            attr_pattern = href_pattern

        maybe_url_match = attr_pattern.search(tag.strip())
        maybe_url = maybe_url_match.group(1) if maybe_url_match else None

        if not is_nonempty_str(maybe_url):
            raise RuntimeError(
                f"One of entries for `Component.Media.{script_type}` media is missing a "
                f"value for attribute '{attr}'. If there is content inlined inside the `<{attr}>` tags, "
                f"you must move the content to a `.{script_type}` file and reference it via '{attr}'.\nGot:\n{tag}"
            )

        url = cast(str, maybe_url)

        # Skip duplicates
        if url in tags_by_url:
            continue

        tags_by_url[url] = tag
        urls.append(url)

    # Ensure consistent order
    tags = [tags_by_url[url] for url in urls]

    return tags, urls


def _prepare_tags_and_urls(
    data: List[Tuple[str, ScriptType, Optional[str]]],
    strategy: DependenciesStrategy,
) -> Tuple[List[str], List[str], List[str], List[str], List[str], List[str]]:
    from django_components.component import get_component_by_class_id

    # JS / CSS that we should insert into the HTML
    inlined_js_tags: List[str] = []
    inlined_css_tags: List[str] = []
    # JS / CSS that the client-side dependency managers should load
    to_load_js_urls: List[str] = []
    to_load_css_urls: List[str] = []
    # JS / CSS that we want to mark as loaded in the dependency manager
    loaded_js_urls: List[str] = []
    loaded_css_urls: List[str] = []

    # When `strategy="document"`, we insert the actual <script> and <style> tags into the HTML.
    # But even in that case we still need to call `Components.manager.markScriptLoaded`,
    # so the client knows NOT to fetch them again.
    # So in that case we populate both `inlined` and `loaded` lists
    for comp_cls_id, script_type, input_hash in data:
        # TODO - THIS IS NOT RIGHT! CSS scope is class-level, not instance-level
        #
        # NOTE: When CSS is scoped, then EVERY component instance will have different
        # copy of the style, because each copy will have component's ID embedded.
        # So, in that case we inline the style into the HTML (See `set_component_attrs_for_js_and_css`),
        # which means that we are NOT going to load / inline it again.
        comp_cls = get_component_by_class_id(comp_cls_id)

        # When strategy is "document", "simple", "prepend", or "append", we insert the actual <script> and
        # <style> tags into the HTML.
        #
        # But in case of strategy == "document" we still need to call `Components.manager.markScriptLoaded`,
        # so the client knows NOT to fetch the scripts again.
        # So in that case we populate both `inlined` and `loaded` lists
        if strategy == "document":
            # NOTE: Skip fetching of inlined JS/CSS if it's not defined or empty for given component
            if script_type == "js" and is_nonempty_str(comp_cls.js):
                # Components may set `js_autoload=False` to manually decide where and how to load the JS in the client.
                # TODO IS IT STILL NEEEDED?
                if comp_cls.js_autoload:
                    # NOTE: If `input_hash` is `None`, then we get the component's JS/CSS
                    #       (e.g. `/components/cache/table.js`).
                    #       And if `input_hash` is given, we get the component's JS/CSS variables
                    #       (e.g. `/components/cache/table.0ab2c3.js`).
                    inlined_js_tags.append(get_script_tag("js", comp_cls, input_hash))
                loaded_js_urls.append(get_script_url("js", comp_cls, input_hash))

            if script_type == "css" and is_nonempty_str(comp_cls.css):
                if comp_cls.css_autoload:
                    inlined_css_tags.append(get_script_tag("css", comp_cls, input_hash))
                loaded_css_urls.append(get_script_url("css", comp_cls, input_hash))

        elif strategy in ("simple", "prepend", "append"):
            if script_type == "js" and is_nonempty_str(comp_cls.js):
                inlined_js_tags.append(get_script_tag("js", comp_cls, input_hash))

            if script_type == "css" and is_nonempty_str(comp_cls.css):
                inlined_css_tags.append(get_script_tag("css", comp_cls, input_hash))

        # When a fragment, then scripts are NOT inserted into the HTML,
        # and instead we fetch and load them all via our JS dependency manager.
        elif strategy == "fragment":
            if script_type == "js" and is_nonempty_str(comp_cls.js) and comp_cls.js_autoload:
                to_load_js_urls.append(get_script_url("js", comp_cls, input_hash))

            if script_type == "css" and is_nonempty_str(comp_cls.css) and comp_cls.css_autoload:
                to_load_css_urls.append(get_script_url("css", comp_cls, input_hash))

    return (
        to_load_js_urls,
        to_load_css_urls,
        inlined_js_tags,
        inlined_css_tags,
        loaded_js_urls,
        loaded_css_urls,
    )


# TODO DOCUMENT AND TEST
def get_script_content(
    script_type: ScriptType,
    comp_cls: Type["Component"],
    input_hash: Optional[str],
) -> Optional[str]:
    # If the script is among the static files, use that
    if input_hash is None and has_component_inline_dependency_in_static(comp_cls, script_type):
        file_path = make_component_inline_dependency_static_path(comp_cls, script_type)
        # NOTE: If `has_component_inline_dependency_in_static` is True then `file_path` cannot be `None`
        script: Optional[str] = cast(Path, file_path).read_text("utf-8")
    else:
        cache = get_component_media_cache()
        cache_key = _gen_cache_key(comp_cls.class_id, script_type, input_hash)
        script = cache.get(cache_key)

    return script


def get_script_tag(
    script_type: ScriptType,
    comp_cls: Type["Component"],
    input_hash: Optional[str],
) -> str:
    content = get_script_content(script_type, comp_cls, input_hash)
    if content is None:
        raise RuntimeError(
            f"Could not find {script_type.upper()} for component '{comp_cls.__name__}' (id: {comp_cls.class_id})"
        )

    if script_type == "js":
        content = wrap_component_js(comp_cls, content)
    elif script_type == "css":
        content = wrap_component_css(comp_cls, content)
    else:
        raise ValueError(f"Unexpected script_type '{script_type}'")

    return content


# TODO DOCUMENT AND TEST
def get_script_url(
    script_type: ScriptType,
    comp_cls: Type["Component"],
    input_hash: Optional[str],
) -> str:
    return reverse(
        CACHE_ENDPOINT_NAME,
        kwargs={
            "comp_cls_id": comp_cls.class_id,
            "script_type": script_type,
            **({"input_hash": input_hash} if input_hash is not None else {}),
        },
    )


def _gen_exec_script(
    to_load_js_tags: List[str],
    to_load_css_tags: List[str],
    loaded_js_urls: List[str],
    loaded_css_urls: List[str],
    comp_js_vars: List[Tuple[str, str, str]],
    comp_calls: List[Tuple[str, str, Optional[str]]],
) -> Optional[str]:
    # Return None if all lists are empty
    if not any([to_load_js_tags, to_load_css_tags, loaded_css_urls, loaded_js_urls, comp_js_vars, comp_calls]):
        return None

    def to_base64(tag: str) -> str:
        return base64.b64encode(tag.encode()).decode()

    def map_to_base64(lst: Sequence[str]) -> List[str]:
        return [to_base64(tag) for tag in lst]

    # Generate JSON that will tell the JS dependency manager which JS and CSS to load
    #
    # NOTE: It would be simpler to pass only the URL itself for `loadJs/loadCss`, instead of a whole tag.
    #    But because we allow users to specify the Media class, and thus users can
    #    configure how the `<link>` or `<script>` tags are rendered, we need pass the whole tag.
    #
    # NOTE 2: Convert to Base64 to avoid any issues with `</script>` tags in the content
    exec_script_data = {
        "loadedCssUrls": map_to_base64(loaded_css_urls),
        "loadedJsUrls": map_to_base64(loaded_js_urls),
        "toLoadCssTags": map_to_base64(to_load_css_tags),
        "toLoadJsTags": map_to_base64(to_load_js_tags),
        # TODO
        # TODO
        # TODO
        # NOTE: Component call data contains only hashes and IDs. But since this info is taken
        # from the rendered HTML, which could have been tampered with, it's better to escape these to base64 too.
        "componentJsVars": [map_to_base64(js_vars) for js_vars in comp_js_vars],

        # NOTE: Component call data contains only hashes and IDs. But since this info is taken
        # from the rendered HTML, which could have been tampered with, it's better to escape these to base64 too.
        "componentCalls": [
            [
                to_base64(comp_cls_hash),
                to_base64(comp_id),
                # `None` (converted to `null` in JSON) means that the component has no JS variables
                to_base64(js_input_hash) if js_input_hash is not None else None,
            ]
            for comp_cls_hash, comp_id, js_input_hash in comp_calls
        ],
    }

    # NOTE: This data is embedded into the HTML as JSON. It is the responsibility of
    # the client-side code to detect that this script was inserted, and to load the
    # corresponding assets
    # See https://developer.mozilla.org/en-US/docs/Web/HTML/Element/script#embedding_data_in_html
    exec_script = json.dumps(exec_script_data)
    exec_script = f'<script type="application/json" data-djc>{exec_script}</script>'
    return exec_script


head_or_body_end_tag_re = re.compile(r"<\/(?:head|body)\s*>", re.DOTALL)


def _insert_js_css_to_default_locations(
    html_content: str,
    js_content: Optional[str],
    css_content: Optional[str],
) -> Optional[str]:
    """
    This function tries to insert the JS and CSS content into the default locations.

    JS is inserted at the end of `<body>`, and CSS is inserted at the end of `<head>`.

    We find these tags by looking for the first `</head>` and last `</body>` tags.
    """
    if css_content is None and js_content is None:
        return None

    did_modify_html = False

    first_end_head_tag_index = None
    last_end_body_tag_index = None

    # First check the content for the first `</head>` and last `</body>` tags
    for match in head_or_body_end_tag_re.finditer(html_content):
        tag_name = match[0][2:6]

        # We target the first `</head>`, thus, after we set it, we skip the rest
        if tag_name == "head":
            if css_content is not None and first_end_head_tag_index is None:
                first_end_head_tag_index = match.start()

        # But for `</body>`, we want the last occurrence, so we insert the content only
        # after the loop.
        elif tag_name == "body":
            if js_content is not None:
                last_end_body_tag_index = match.start()

        else:
            raise ValueError(f"Unexpected tag name '{tag_name}'")

    # Then do two string insertions. First the CSS, because we assume that <head> is before <body>.
    index_offset = 0
    updated_html = html_content
    if css_content is not None and first_end_head_tag_index is not None:
        updated_html = updated_html[:first_end_head_tag_index] + css_content + updated_html[first_end_head_tag_index:]
        index_offset = len(css_content)
        did_modify_html = True

    if js_content is not None and last_end_body_tag_index is not None:
        js_index = last_end_body_tag_index + index_offset
        updated_html = updated_html[:js_index] + js_content + updated_html[js_index:]
        did_modify_html = True

    if did_modify_html:
        return updated_html
    else:
        return None  # No changes made


#########################################################
# 4. Endpoints for fetching the JS / CSS scripts from within
#    the browser, as defined from previous steps.
#########################################################


CACHE_ENDPOINT_NAME = "components_cached_script"
_CONTENT_TYPES = {"js": "text/javascript", "css": "text/css"}


def _get_content_types(script_type: ScriptType) -> str:
    if script_type not in _CONTENT_TYPES:
        raise ValueError(f"Unknown script_type '{script_type}'")

    return _CONTENT_TYPES[script_type]


def cached_script_view(
    req: HttpRequest,
    comp_cls_id: str,
    script_type: ScriptType,
    input_hash: Optional[str] = None,
) -> HttpResponse:
    from django_components.component import get_component_by_class_id

    if req.method != "GET":
        return HttpResponseNotAllowed(["GET"])

    try:
        comp_cls = get_component_by_class_id(comp_cls_id)
    except KeyError:
        return HttpResponseNotFound()

    # If the script is among the static files, use that
    if input_hash is None and has_component_inline_dependency_in_static(comp_cls, script_type):
        file_url = make_component_inline_dependency_static_url(comp_cls_hash, script_type)
        return redirect(file_url)

    # Otherwise check if the file is among the dynamically generated files in the cache
    script = get_script_content(script_type, comp_cls, input_hash)
    if script is None:
        return HttpResponseNotFound()

    content_type = _get_content_types(script_type)
    return HttpResponse(content=script, content_type=content_type)


urlpatterns = [
    # E.g. `/components/cache/MyTable_a1b2c3.js` or `/components/cache/MyTable_a1b2c3.0ab2c3.js`
    path("cache/<str:comp_cls_id>.<str:input_hash>.<str:script_type>", cached_script_view, name=CACHE_ENDPOINT_NAME),
    path("cache/<str:comp_cls_id>.<str:script_type>", cached_script_view, name=CACHE_ENDPOINT_NAME),
]


#########################################################
# 5. Template tags
#########################################################


def _component_dependencies(type: Literal["js", "css"]) -> SafeString:
    """Marks location where CSS link and JS script tags should be rendered."""
    if type == "css":
        placeholder = CSS_DEPENDENCY_PLACEHOLDER
    elif type == "js":
        placeholder = JS_DEPENDENCY_PLACEHOLDER
    else:
        raise TemplateSyntaxError(
            f"Unknown dependency type in {{% component_dependencies %}}. Must be one of 'css' or 'js', got {type}"
        )

    return mark_safe(placeholder)


class ComponentCssDependenciesNode(BaseNode):
    """
    Marks location where CSS link tags should be rendered after the whole HTML has been generated.

    Generally, this should be inserted into the `<head>` tag of the HTML.

    If the generated HTML does NOT contain any `{% component_css_dependencies %}` tags, CSS links
    are by default inserted into the `<head>` tag of the HTML. (See
    [Default JS / CSS locations](../../concepts/advanced/rendering_js_css/#default-js-css-locations))

    Note that there should be only one `{% component_css_dependencies %}` for the whole HTML document.
    If you insert this tag multiple times, ALL CSS links will be duplicately inserted into ALL these places.
    """

    tag = "component_css_dependencies"
    end_tag = None  # inline-only
    allowed_flags = []

    def render(self, context: Context) -> str:
        return _component_dependencies("css")


class ComponentJsDependenciesNode(BaseNode):
    """
    Marks location where JS link tags should be rendered after the whole HTML has been generated.

    Generally, this should be inserted at the end of the `<body>` tag of the HTML.

    If the generated HTML does NOT contain any `{% component_js_dependencies %}` tags, JS scripts
    are by default inserted at the end of the `<body>` tag of the HTML. (See
    [Default JS / CSS locations](../../concepts/advanced/rendering_js_css/#default-js-css-locations))

    Note that there should be only one `{% component_js_dependencies %}` for the whole HTML document.
    If you insert this tag multiple times, ALL JS scripts will be duplicately inserted into ALL these places.
    """

    tag = "component_js_dependencies"
    end_tag = None  # inline-only
    allowed_flags = []

    def render(self, context: Context) -> str:
        return _component_dependencies("js")
