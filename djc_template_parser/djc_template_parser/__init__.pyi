from typing import List, Literal, Optional, Tuple

class TagToken:
    token: str
    start_index: int
    end_index: int
    line_col: Tuple[int, int]

class TagValueFilter:
    token: TagToken
    arg: Optional["TagValue"]
    start_index: int
    end_index: int
    line_col: Tuple[int, int]

class TagValue:
    token: TagToken
    children: List["TagValue"]
    kind: Literal["list", "dict", "int", "float", "variable", "expression", "translation", "string"]
    spread: Optional[str]
    filters: List[TagValueFilter]
    start_index: int
    end_index: int
    line_col: Tuple[int, int]

class TagAttr:
    key: Optional[TagToken]
    value: TagValue
    start_index: int
    end_index: int
    line_col: Tuple[int, int]

def parse_tag(input: str) -> List[TagAttr]:
    """
    Parse a Django template tag string into a list of attributes.

    If you have a template tag string like this:

    ```django
    {% my_tag ...[val1] a=b [1, 2, 3] data={"key": "value"} %}
    ```

    Then:
    - `my_tag` is the tag name
    - `...[val1] a=b [1, 2, 3] data={"key": "value"}` is the list of attributes

    This parser accepts the list of attributes as a string, and returns their AST - a list of TagAttr objects.

    ```python
    tag_ast = parse_tag("...[val1] a=b [1, 2, 3] data={"key": "value"}")
    print(tag_ast) # [TagAttr(...), TagAttr(...), ...]
    ```

    The parser supports:
    - Key-value pairs (e.g. key=value)
    - Standalone values (e.g. 1, "my string", val)
    - Spread operators (e.g. ...value, **value, *value)
    - Filters (e.g. value|filter:arg)
    - Lists and dictionaries (e.g. [1, 2, 3], {"key": "value"})
    - String literals (single/double quoted) (e.g. "my string", 'my string')
    - Numbers (e.g. 1, 1.23, 1e-10)
    - Variables (e.g. val, key)
    - Translation strings (e.g. _("text"))
    - Comments (e.g. {# comment #})

    Args:
        input: The template tag string to parse, without the {% %} delimiters

    Returns:
        List of TagAttr objects representing the parsed attributes

    Raises:
        ValueError: If the input cannot be parsed according to the grammar
    """
    ...
