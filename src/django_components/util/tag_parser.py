# ruff: noqa: S105
# TODO - UPDATE THIS TO MATCH THE NEW PARSER
"""
Parser for Django template tags.

The parser reads a tag like this (without the `{%` `%}`):

```django
{% component 'my_comp' key=val key2='val2 two' %}
```

and returns an AST representation of the tag:

```py
[
    TagAttr(
        key=None,
        value=TagValueStruct(
            type="simple",
            spread=None,
            meta={},
            entries=[
                TagValue(
                    parts=[
                        TagValuePart(
                            value="component", quoted=None, spread=None, translation=False, filter=None
                        ),
                    ]
                ),
            ],
        ),
        start_index=0,
    ),
    ...
]
```

See `parse_tag()` for details.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

from djc_template_parser import TagValue
from django.template.base import FilterExpression, Parser, Variable
from django.template.context import Context
from django.template.exceptions import TemplateSyntaxError

from django_components.expression import DynamicFilterExpression, is_dynamic_expression

# TODO - ADD SUPPORT FOR 1.2e2 or 1.2E2 formatting to new parser
# 
#
# TODO - UPDATE THIS TO MATCH THE NEW PARSER
# TODO - UPDATE THIS TO MATCH THE NEW PARSER
# TODO - UPDATE THIS TO MATCH THE NEW PARSER
def resolve_tag_value(value: TagValue, context: Context) -> Any:
    compiled = compile_tag_value(value)
    pass


compiled_values_cache: Dict[TagValue, FilterExpression] = {}


def compile_tag_value(value: TagValue) -> Any:
    if value in compiled_values_cache:
        return compiled_values_cache[value]
    
    value.

    # When we want to render the TagValueStruct, which may contain nested lists and dicts,
    # we need to find all leaf nodes (the "simple" types) and compile them to FilterExpression.
    #
    # To make sure that the compilation needs to be done only once, the result
    # each TagValueStruct contains a `compiled` flag to signal to its parent.
    def compile(self) -> None:
        if self.compiled:
            return

        def compile_value(value: Union[TagValue, TagValueStruct]) -> None:
            if isinstance(value, TagValue):
                value.compile(self.parser)
            else:
                value.compile()

        if self.type == "simple":
            value = self.entries[0]
            compile_value(value)
        elif self.type == "list":
            for entry in self.entries:
                compile_value(entry)
        elif self.type == "dict":
            # NOTE: Here we assume that the dict pairs have been validated by the parser and
            #       that the pairs line up.
            for entry in self.entries:
                compile_value(entry)

        self.compiled = True


# TODO
# TODO


class DjcVariable(Variable):
    """Variable that accepts TagValue instead of a string."""

    def __init__(self, value: TagValue):
        self.var = value.token.token
        self.literal = None
        self.lookups = None
        self.translate = False
        self.message_context = None

        if value.kind == "translation":
            # The result of the lookup should be translated at rendering time.
            self.translate = True
            inner = value.token.token[2:-1]
            self.literal = mark_safe(unescape_string_literal(inner))
        # If it's wrapped with quotes (single or double), then
        # we're also dealing with a literal.
        try:
            self.literal = mark_safe(unescape_string_literal(var))
        except ValueError:
            self.lookups = tuple(var.split(VARIABLE_ATTRIBUTE_SEPARATOR))


# TODO
# TODO
from django.utils.safestring import mark_safe
from django.utils.text import unescape_string_literal
# TODO
# TODO
class DjcFilterExpression(FilterExpression):
    """FilterExpression that accepts TagValue instead of a string."""

    def __init__(self, value: TagValue, parser: Optional[Parser]):
        self.token = value
        self.is_var = False

        if value.kind in ("list", "dict"):
            self.var = [DjcFilterExpression(v, parser) for v in value.children]
        elif value.kind == "int":
            self.var = int(value.token.token)
        elif value.kind == "float":
            self.var = float(value.token.token)
        elif value.kind == "string":
            self.var = mark_safe(unescape_string_literal(value.token.token))
        elif value.kind in ("variable", "translation"):
            # Translations are passed to Variable to be resolved at rendering time.
            self.var = DjcVariable(value.token.token)
            self.is_var = True
        elif value.kind == "expression":
            self.var = DynamicFilterExpression(parser, value.token.token)
        else:
            raise TemplateSyntaxError(f"Unknown tag value kind: {value.kind}")

        # TODO
        from typing import Callable

        filters: List[Tuple[Callable, List[Tuple[bool, Any]]]] = []
        for filter in value.filters:
            filter_name = filter.token.token
            filter_func = parser.find_filter(filter_name)

            if filter.arg is None:
                filter_arg = ()
            else:
                # The `True` here tells `FilterExpression.resolve()` to resolve the argument.
                filter_arg = (True, DjcFilterExpression(filter.arg, parser))

            # TODO - The original `validate_tag_input` should be renamed and moved to validation.py
            #      - And in it's place should be `validate_tag_input` that craetes the validation signature
            #        and formats the error message
            #      - And signature should be made optional, so that in this case we can
            #        make the signature only if __code__ is not available.
            from django_components.util.template_tag import TagParam, validate_tag_input
            import inspect
            filter_signature = inspect.signature(filter_func)
            try:
                validate_tag_input(
                    filter_func,
                    filter_signature,
                    "#TODO",
                    [TagParam(key=None, value=1)] if filter_arg else []
                )
            except Exception as e:
                raise TemplateSyntaxError(f"Invalid parameters for filter '{filter_name}': {str(e)}") from None

            filters.append((filter_func, [filter_arg]))

        self.filters = filters

    def __str__(self):
        return self.token
    
    def resolve(self, context, ignore_failures=False):
        if self.token.kind == "list":
            # TODO - NEED TO RESOLVE SPREADS HERE!
            return [DjcFilterExpression(v, self.parser) for v in self.token.children]
        
        # TODO - CALL super().resolve() for each item in lists / dicts

        if self.type == "simple":
            value = self.entries[0]
            if not isinstance(value, TagValue):
                raise TemplateSyntaxError("Malformed tag: simple value is not a TagValue")
            return value.resolve(context)

        elif self.type == "list":
            resolved_list: List[Any] = []
            for entry in self.entries:
                resolved = entry.resolve(context)
                # Case: Spreading a literal list: [ *[1, 2, 3] ]
                if isinstance(entry, TagValueStruct) and entry.spread:
                    if not entry.type == "list":
                        raise TemplateSyntaxError("Malformed tag: cannot spread non-list value into a list")
                    resolved_list.extend(resolved)
                # Case: Spreading a variable: [ *val ]
                elif isinstance(entry, TagValue) and entry.is_spread:
                    resolved_list.extend(resolved)
                # Case: Plain value: [ val ]
                else:
                    resolved_list.append(resolved)
            return resolved_list

        elif self.type == "dict":
            resolved_dict: Dict = {}
            dict_pair: List = []

            # NOTE: Here we assume that the dict pairs have been validated by the parser and
            #       that the pairs line up.
            for entry in self.entries:
                resolved = entry.resolve(context)
                if isinstance(entry, TagValueStruct) and entry.spread:
                    if dict_pair:
                        raise TemplateSyntaxError(
                            "Malformed dict: spread operator cannot be used on the position of a dict value"
                        )
                    # Case: Spreading a literal dict: { **{"key": val2} }
                    resolved_dict.update(resolved)
                elif isinstance(entry, TagValue) and entry.is_spread:
                    if dict_pair:
                        raise TemplateSyntaxError(
                            "Malformed dict: spread operator cannot be used on the position of a dict value"
                        )
                    # Case: Spreading a variable: { **val }
                    resolved_dict.update(resolved)
                else:
                    # Case: Plain value: { key: val }
                    dict_pair.append(resolved)

                if len(dict_pair) == 2:
                    dict_key = dict_pair[0]
                    dict_value = dict_pair[1]
                    resolved_dict[dict_key] = dict_value
                    dict_pair = []
            return resolved_dict



# TODO DELETE
# @dataclass
# class TagAttr:
#     """
#     A tag attribute represents a single token of a tag.

#     E.g. the following tag:

#     ```django
#     {% component "my_comp" key=val key2='val2 two' %}
#     ```

#     Has 4 attributes: `component`, `my_comp`, `key=val` and `key2='val2 two'`.
#     """

#     key: Optional[str]
#     value: "TagValueStruct"
#     start_index: int

#     def serialize(self, omit_key: bool = False) -> str:
#         s = self.value.serialize()
#         if not omit_key and self.key:
#             return f"{self.key}={s}"
#         return s


# TODO DEL
@dataclass
class TagValueOLD:
    """
    A tag value represents the text to the right of the `=` in a tag attribute.

    E.g. in the following tag:
    ```django
    {% component "my_comp" key=val2|filter1:"one" %}
    ```

    The `key` attribute has the TagValue `val2|filter1:"one"`.
    """

    parts: List["TagValuePart"]
    compiled: Optional[FilterExpression] = None

    @property
    def is_spread(self) -> bool:
        if not self.parts:
            return False
        return self.parts[0].spread is not None

    def serialize(self) -> str:
        return "".join(part.serialize() for part in self.parts)

    def compile(self, parser: Optional[Parser]) -> None:
        if self.compiled is not None:
            return

        serialized = self.serialize()
        # Remove the spread token from the start of the serialized value
        # E.g. `*val|filter:arg` -> `val|filter:arg`
        if self.is_spread:
            spread_token = self.parts[0].spread
            spread_token_offset = len(spread_token) if spread_token else 0
            serialized = serialized[spread_token_offset:]

        # Allow to use dynamic expressions as args, e.g. `"{{ }}"` inside of strings
        if is_dynamic_expression(serialized):
            self.compiled = DynamicFilterExpression(parser, serialized)
        else:
            self.compiled = FilterExpression(serialized, parser)

    def resolve(self, context: Context) -> Any:
        if self.compiled is None:
            raise TemplateSyntaxError("Malformed tag: TagValue.resolve() called before compile()")
        return self.compiled.resolve(context)


@dataclass
class TagValuePart:
    """
    Django tag attributes may consist of multiple parts, being separated by filter pipes (`|`)
    or filter arguments (`:`). This class represents a single part of the attribute value.

    E.g. in the following tag:
    ```django
    {% component "my_comp" key="my val's" key2=val2|filter1:"one" %}
    ```

    The value of attribute `key2` has three parts: `val2`, `filter1` and `"one"`.
    """

    value: str
    """The textual value"""
    quoted: Optional[str]
    """Whether the value is quoted, and the character that's used for the quotation"""
    spread: Optional[str]
    """
    The prefix used by a spread syntax, e.g. `...`, `*`, or `**`. If present, it means
    this values should be spread into the parent tag / list / dict.
    """
    translation: bool
    """Whether the value is a translation string, e.g. `_("my string")`"""
    filter: Optional[str]
    """The prefix of the filter, e.g. `|` or `:`"""

    def serialize(self) -> str:
        value = f"{self.quoted}{self.value}{self.quoted}" if self.quoted else self.value
        if self.translation:
            value = f"_({value})"
        elif self.spread:
            value = f"{self.spread}{value}"

        if self.filter:
            value = f"{self.filter}{value}"

        return value

    # # NOTE: dataclass is used so we can validate the input. But dataclasses are not hashable,
    # # by default, hence these methods.
    # def __hash__(self) -> int:
    #     # Create a hash based on the attributes that define object equality
    #     return hash((self.value, self.quoted, self.spread, self.translation, self.filter))

    # def __eq__(self, other: Any) -> bool:
    #     if not isinstance(other, TagValuePart):
    #         return False
    #     return (
    #         self.value == other.value
    #         and self.quoted == other.quoted
    #         and self.spread == other.spread
    #         and self.translation == other.translation
    #         and self.filter == other.filter
    #     )


@dataclass
class TagValueStruct:
    """
    TagValueStruct represents a potential container (list or dict) that holds other tag values.

    Types:

    - `simple`: Plain tag value
    - `list`: A list of tag values
    - `dict`: A dictionary of tag values

    TagValueStruct may be arbitrarily nested, creating JSON-like structures
    that contains lists, dicts, and simple values.
    """

    type: Literal["list", "dict", "simple"]
    entries: List[Union["TagValueStruct", TagValue]]
    spread: Optional[str]
    """
    The prefix used by a spread syntax, e.g. `...`, `*`, or `**`. If present, it means
    this values should be spread into the parent tag / list / dict.
    """
    # Container for parser-specific metadata
    meta: Dict[str, Any]
    # Parser is passed through so we can resolve variables with filters
    parser: Optional[Parser]
    compiled: bool = False

    # TODO CAN BE DELETED
    def serialize(self) -> str:
        """
        Recursively walks down the value of potentially nested lists and dicts,
        and serializes them all to a string.

        This is effectively the inverse of `parse_tag()`.
        """

        def render_value(value: Union[TagValue, TagValueStruct]) -> str:
            if isinstance(value, TagValue):
                return value.serialize()
            return value.serialize()

        if self.type == "simple":
            value = self.entries[0]
            return render_value(value)
        if self.type == "list":
            prefix = self.spread or ""
            return prefix + "[" + ", ".join([render_value(entry) for entry in self.entries]) + "]"
        if self.type == "dict":
            prefix = self.spread or ""
            dict_pairs = []
            dict_pair: List[str] = []
            # NOTE: Here we assume that the dict pairs have been validated by the parser and
            #       that the pairs line up.
            for entry in self.entries:
                rendered = render_value(entry)
                if isinstance(entry, TagValueStruct):
                    if entry.spread:
                        if dict_pair:
                            raise TemplateSyntaxError("Malformed dict: spread operator cannot be used as a dict key")
                        dict_pairs.append(rendered)
                    else:
                        dict_pair.append(rendered)
                elif entry.is_spread:
                    if dict_pair:
                        raise TemplateSyntaxError("Malformed dict: spread operator cannot be used as a dict key")
                    dict_pairs.append(rendered)
                else:
                    dict_pair.append(rendered)
                if len(dict_pair) == 2:
                    dict_pairs.append(": ".join(dict_pair))
                    dict_pair = []
            return prefix + "{" + ", ".join(dict_pairs) + "}"

        raise ValueError(f"Invalid type: {self.type}")

    # When we want to render the TagValueStruct, which may contain nested lists and dicts,
    # we need to find all leaf nodes (the "simple" types) and compile them to FilterExpression.
    #
    # To make sure that the compilation needs to be done only once, the result
    # each TagValueStruct contains a `compiled` flag to signal to its parent.
    def compile(self) -> None:
        if self.compiled:
            return

        def compile_value(value: Union[TagValue, TagValueStruct]) -> None:
            if isinstance(value, TagValue):
                value.compile(self.parser)
            else:
                value.compile()

        if self.type == "simple":
            value = self.entries[0]
            compile_value(value)
        elif self.type == "list":
            for entry in self.entries:
                compile_value(entry)
        elif self.type == "dict":
            # NOTE: Here we assume that the dict pairs have been validated by the parser and
            #       that the pairs line up.
            for entry in self.entries:
                compile_value(entry)

        self.compiled = True

    # Walk down the TagValueStructs and resolve the expressions.
    #
    # NOTE: This is where the TagValueStructs are converted to lists and dicts.
    def resolve(self, context: Context) -> Any:
        self.compile()

        if self.type == "simple":
            value = self.entries[0]
            if not isinstance(value, TagValue):
                raise TemplateSyntaxError("Malformed tag: simple value is not a TagValue")
            return value.resolve(context)

        if self.type == "list":
            resolved_list: List[Any] = []
            for entry in self.entries:
                resolved = entry.resolve(context)
                # Case: Spreading a literal list: [ *[1, 2, 3] ]
                if isinstance(entry, TagValueStruct) and entry.spread:
                    if not entry.type == "list":
                        raise TemplateSyntaxError("Malformed tag: cannot spread non-list value into a list")
                    resolved_list.extend(resolved)
                # Case: Spreading a variable: [ *val ]
                elif isinstance(entry, TagValue) and entry.is_spread:
                    resolved_list.extend(resolved)
                # Case: Plain value: [ val ]
                else:
                    resolved_list.append(resolved)
            return resolved_list

        if self.type == "dict":
            resolved_dict: Dict = {}
            dict_pair: List = []

            # NOTE: Here we assume that the dict pairs have been validated by the parser and
            #       that the pairs line up.
            for entry in self.entries:
                resolved = entry.resolve(context)
                if isinstance(entry, TagValueStruct) and entry.spread:
                    if dict_pair:
                        raise TemplateSyntaxError(
                            "Malformed dict: spread operator cannot be used on the position of a dict value",
                        )
                    # Case: Spreading a literal dict: { **{"key": val2} }
                    resolved_dict.update(resolved)
                elif isinstance(entry, TagValue) and entry.is_spread:
                    if dict_pair:
                        raise TemplateSyntaxError(
                            "Malformed dict: spread operator cannot be used on the position of a dict value",
                        )
                    # Case: Spreading a variable: { **val }
                    resolved_dict.update(resolved)
                else:
                    # Case: Plain value: { key: val }
                    dict_pair.append(resolved)

                if len(dict_pair) == 2:
                    dict_key = dict_pair[0]
                    dict_value = dict_pair[1]
                    resolved_dict[dict_key] = dict_value
                    dict_pair = []
            return resolved_dict

        raise ValueError(f"Invalid type: {self.type}")


def parse_tag(text: str, parser: Optional[Parser]) -> Tuple[str, List[TagAttr]]:
    """
    Parse the content of a Django template tag like this:

    ```django
    {% component 'my_comp' key=val key2='val2 two' %}
    ```

    into an AST representation:

    [
        TagAttr(
            key=None,
            start_index=0,
            value=TagValue(
                parts=tuple([
                    TagValuePart(value="component", quoted=None, spread=None, translation=False, filter=None)
                ])
            ),
        ),
        TagAttr(
            key=None,
            start_index=10,
            value=TagValue(
                parts=tuple([
                    TagValuePart(value="my_comp", quoted="'", spread=None, translation=False, filter=None)
                ])
            ),
        ),
        ...
    ]
    ```

    Supported syntax:
    - Variables: `val`, `key`
    - Kwargs (attributes): `key=val`, `key2='val2 two'`
    - Quoted strings: `"my string"`, `'my string'`
    - Translation: `_("my string")`
    - Filters: `val|filter`, `val|filter:arg`
    - List literals: `[value1, value2]`, `key=[value1, [1, 2, 3]]`
    - Dict literals: `{"key1": value1, "key2": value2}`, `key={"key1": value1, "key2": {"nested": "value"}}`
    - Trailing commas: `[1, 2, 3,]`, `{"key": "value", "key2": "value2",}`
    - Spread operators: `...`, `*`, `**`
    - Spread inside lists and dicts: `key=[1, *val, 3]`, `key={"key": val, **kwargs, "key2": 3}`
    - Spread with list and dict literals: `{**{"key": val2}, "key": val1}`, `[ ...[val1], val2 ]`
    - Spread list and dict literals as attributes: `{% ...[val1] %}`, `{% ...{"key" val1 } %}`

    Invalid syntax:
    - Spread inside a filter: `val|...filter`
    - Spread inside a dictionary key: `attr={...attrs: "value"}`
    - Spread inside a dictionary value: `attr={"key": ...val}`
    - Misplaced spread: `attr=[...val]`, `attr={...val}`, `attr=[**val]`, `attr={*val}`
    - Spreading lists and dicts: `...[1, 2, 3]`, `...{"key": "value"}`
    """

    # TODO!!
    tag_attrs: List[TagAttr] = djc_template_parser.parse_tag(text, parser)
    return tag_attrs
