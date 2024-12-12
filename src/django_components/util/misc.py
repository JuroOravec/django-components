import re
import sys
from typing import Any, Callable, List, Optional, Tuple, Type, TypeVar, get_origin, get_args

from django.template.defaultfilters import escape

from django_components.util.nanoid import generate
from django_components.util.types import Annotated

T = TypeVar("T")


# Based on nanoid implementation from
# https://github.com/puyuan/py-nanoid/tree/99e5b478c450f42d713b6111175886dccf16f156/nanoid
def gen_id() -> str:
    """Generate a unique ID that can be associated with a Node"""
    # Alphabet is only alphanumeric. Compared to the default alphabet used by nanoid,
    # we've omitted `-` and `_`.
    # With this alphabet, at 6 chars, the chance of collision is 1 in 3.3M.
    # See https://zelark.github.io/nano-id-cc/
    return generate(
        "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
        size=6,
    )


def find_last_index(lst: List, predicate: Callable[[Any], bool]) -> Any:
    for r_idx, elem in enumerate(reversed(lst)):
        if predicate(elem):
            return len(lst) - 1 - r_idx
    return -1


def is_str_wrapped_in_quotes(s: str) -> bool:
    return s.startswith(('"', "'")) and s[0] == s[-1] and len(s) >= 2


def any_regex_match(string: str, patterns: List[re.Pattern]) -> bool:
    return any(p.search(string) is not None for p in patterns)


def no_regex_match(string: str, patterns: List[re.Pattern]) -> bool:
    return all(p.search(string) is None for p in patterns)


# See https://stackoverflow.com/a/2020083/9788634
def get_import_path(cls_or_fn: Type[Any]) -> str:
    """
    Get the full import path for a class or a function, e.g. `"path.to.MyClass"`
    """
    module = cls_or_fn.__module__
    if module == "builtins":
        return cls_or_fn.__qualname__  # avoid outputs like 'builtins.str'
    return module + "." + cls_or_fn.__qualname__


def extract_annotated_metadata(annotated_type: Any) -> Tuple[Any, Tuple[Any, ...]]:
    """
    If a variable was typed with `Annotated[type, extra, ...]`,
    this extracts the contents of the `Annotated` type into type and extras.
    """
    origin = get_origin(annotated_type)
    if origin is Annotated:
        args = get_args(annotated_type)
        base_type = args[0]
        metadata = args[1:]
        return base_type, metadata
    else:
        return annotated_type, ()


def get_class_source_file(cls: Type) -> Optional[str]:
    """Get the full path of the file where the component was defined."""
    module_name = cls.__module__
    if module_name == "__main__":
        # NOTE: If a class is defined in __main__ module, it was NOT defined in a file,
        # but instead in REPL (terminal).
        return None
    module_obj = sys.modules[module_name]
    return module_obj.__file__


def wrap_js_script(js_script: str, wrapper: Callable[[str], str]) -> str:
    import esprima  # TODO MOVE OUT

    # The script MAY be a JS module (.mjs) or TypeScript (.ts), in which case it would
    # include import statements like `import X from 'y'`.
    # These import statements MUST be at the beginning of the file. What this means for us
    # is that if we want to insert something into the JS script, we have to insert it AFTER
    # the import statements.
    #
    # So for that we parse the JavaScript code into AST, and search for the LAST
    # import statement.
    parsed = esprima.parseModule(js_script, comment=True, tolerant=True, range=True)

    from esprima import Syntax, nodes
    # So we Find the last import statements and their positions
    last_import: Optional[nodes.ImportDeclaration] = None
    for node in parsed.body:
        if node.type == Syntax.ImportDeclaration:
            last_import = node
            # imports.append(js_script[node.range[0]:node.range[1]])
            body_start = node.range[1]
        else:
            body_start = node.range[0]
            break  # Non-import statement found

    body_start = last_import.range[1] if last_import else 0

    # The rest of the code is the body
    body_code = js_script[body_start:].strip()

    # Wrap the script body
    wrapped_body = wrapper(body_code)
    # And prepend back the import statements
    output_js = js_script[:body_start] + wrapped_body

    return output_js


_ME_REGEX = re.compile(r"(?:^|\.|(\s|[^a-zA-Z0-9\-\_]))(me|this|self)(?![a-zA-Z])")


# Based on css-scope-inline
# See https://github.com/gnat/css-scope-inline/blob/8fa0285261edd936998f6652c427070df4ba4a4b/script.js
def scope_css(component_id: str, css_content: str) -> str:
    scope = f"[data-comp-id-{component_id}]"

    # Replace "me", "this", "self" with the unique scope
    out_css_content = _ME_REGEX.sub(f"\\1{scope}", css_content)

    # NOTE: We skip this step of css-scope-inline, since we're not using a dot in the scope name
    #
    # Handle @keyframes and animation names
    # out_css_content = out_css_content.replace(
    #     r'((@keyframes|animation:|animation-name:)[^{};]*)\.me__',
    #     r'\1me__'
    # )

    # NOTE: We skip this step of css-scope-inline, which sets media queries.
    # This is outside of scope of django_components
    #
    # Handle @media queries
    # out_css_content = out_css_content.replace(
    #     r'(?:@media)\s(xs-|sm-|md-|lg-|xl-|sm|md|lg|xl|xx)',
    #     lambda match: f"@media {css_scope_breakpoints[match[0]]}"
    # )

    return out_css_content


# See https://stackoverflow.com/a/58800331/9788634
# str.replace(/\\|`|\$/g, '\\$&');
JS_STRING_LITERAL_SPECIAL_CHARS_REGEX = re.compile(r"\\|`|\$")


# See https://stackoverflow.com/a/34064434/9788634
def escape_js_string_literal(js: str) -> str:
    escaped_js = escape(js)

    def on_replace_match(match: "re.Match[str]") -> str:
        return f"\\{match[0]}"

    escaped_js = JS_STRING_LITERAL_SPECIAL_CHARS_REGEX.sub(on_replace_match, escaped_js)
    return escaped_js


def default(val: Optional[T], default: T) -> T:
    return val if val is not None else default


def get_last_index(lst: List, key: Callable[[Any], bool]) -> Optional[int]:
    for index, item in enumerate(reversed(lst)):
        if key(item):
            return len(lst) - 1 - index
    return None


def _escape_js(content: str, wrap: bool = True, eval: bool = True) -> str:
    escaped_js = escape_js_string_literal(content)
    if not wrap:
        return escaped_js
    # `unescapeJs` is the function we call in the browser to parse the escaped JS
    escaped_js = f"Components.unescapeJs(`{escaped_js}`)"
    return f"eval({escaped_js})" if eval else escaped_js
