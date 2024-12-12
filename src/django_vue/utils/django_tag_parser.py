import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple, Union


TAG_WHITESPACE = (" ", "\t", "\n", "\r", "\f")


@dataclass
class TagAttr:
    key: str
    value: Optional[str]
    start_index: int
    """
    Start index of the attribute (include both key and value),
    relative to the start of the owner Tag.
    """
    quoted: bool
    """Whether the value is quoted (either with single or double quotes)"""

    @property
    def formatted(self) -> str:
        if self.value is None:
            return self.key

        if self.quoted:
            return f'{self.key}="{self.value}"'
        else:
            return f"{self.key}={self.value}"

    @property
    def length(self) -> int:
        return len(self.formatted)


class Tag:
    content: str
    attrs: List[TagAttr]

    def __init__(self, content: str) -> None:
        content, attrs = parse_tag_attrs(content)
        self.content = content
        self.attrs = attrs

    def get_attr(self, key: Union[str, re.Pattern]) -> Optional[TagAttr]:
        for attr in self.attrs:
            if isinstance(key, str):
                if attr.key == key:
                    return attr
            elif key.match(attr.key):
                return attr
        return None

    def has_attr(self, key: Union[str, re.Pattern]) -> bool:
        for attr in self.attrs:
            if isinstance(key, str):
                if attr.key == key:
                    return True
            elif key.match(attr.key):
                return True
        return False

    def remove_attr(self, key: str, ) -> None:
        found_attr = None
        found_attr_index = None
        for index, attr in enumerate(self.attrs):
            if attr.key == key:
                found_attr = attr
                found_attr_index = index
                break

        if not found_attr or found_attr_index is None:
            raise KeyError(f"Attribute '{key}' not found")

        new_content = self.content[: found_attr.start_index] + self.content[found_attr.start_index + found_attr.length :]
        self.content = new_content

        self.attrs.pop(found_attr_index)


# Parse the content of a Django template tag like this:
#
# ```django
# {% component "my_comp" key=val key2=val2 %}
# ```
#
# into a tag name and a list of attributes:
#
# ```python
# {
#     "component": "component",
# }
# ```
def parse_tag_attrs(text: str) -> Tuple[str, List[TagAttr]]:
    index = 0
    normalized = ""

    def add_token(token: Union[str, Tuple[str, ...]]) -> None:
        nonlocal normalized
        nonlocal index

        text = "".join(token)
        normalized += text
        index += len(text)

    def replace_next(length: int, replacement: Union[str, Tuple[str, ...]]) -> None:
        nonlocal normalized
        nonlocal index

        normalized += "".join(replacement)
        index += length

    def is_next_token(*tokens: Union[str, Tuple[str, ...]]) -> bool:
        if not tokens:
            raise ValueError("No tokens provided")

        def is_token_match(token: Union[str, Tuple[str, ...]]) -> bool:
            if not token:
                raise ValueError("Empty token")

            for token_index, token_char in enumerate(token):
                text_char = text[index + token_index] if index + token_index < len(text) else None
                if text_char is None or text_char != token_char:
                    return False
            return True

        for token in tokens:
            is_match = is_token_match(token)
            if is_match:
                return True
        return False

    def taken_n(n: int) -> str:
        nonlocal index
        result = text[index : index + n]
        add_token(result)
        return result

    # tag_name = take_until([" ", "\t", "\n", "\r", "\f", ">", "/>"])
    def take_until(
        tokens: Sequence[Union[str, Tuple[str, ...]]],
        ignore: Optional[
            Sequence[
                Union[
                    Union[str, Tuple[str, ...]],
                    Dict[Union[str, Tuple[str, ...]], Union[str, Tuple[str, ...]]],
                ]
            ]
        ] = None,
    ) -> str:
        nonlocal index
        nonlocal text

        result = ""
        while index < len(text):
            char = text[index]

            ignore_token_match: Optional[Union[str, Tuple[str, ...]]] = None
            ignore_token_replacement: Optional[Union[str, Tuple[str, ...]]] = None
            for ignore_token in ignore or []:
                if isinstance(ignore_token, dict):
                    ignore_token, replacement = list(ignore_token.items())[0]
                else:
                    replacement = None

                if is_next_token(ignore_token):
                    ignore_token_match = ignore_token
                    ignore_token_replacement = replacement

            if ignore_token_match:
                if ignore_token_replacement is not None:
                    result += "".join(ignore_token_replacement)
                    replace_next(len(ignore_token_match), ignore_token_replacement)
                else:
                    result += "".join(ignore_token_match)
                    add_token(ignore_token_match)
                continue

            if any(is_next_token(token) for token in tokens):
                return result

            result += char
            add_token(char)
        return result

    # tag_name = take_while([" ", "\t", "\n", "\r", "\f"])
    def take_while(tokens: Sequence[Union[str, Tuple[str, ...]]]) -> str:
        nonlocal index
        nonlocal text

        result = ""
        while index < len(text):
            char = text[index]

            if any(is_next_token(token) for token in tokens):
                result += char
                add_token(char)
            else:
                return result

        return result

    # Parse
    attrs: List[TagAttr] = []
    while index < len(text):
        take_while(TAG_WHITESPACE)

        start_index = len(normalized)

        key = take_until(["=", *TAG_WHITESPACE])

        if not key:
            break

        # Has value
        if is_next_token("="):
            add_token("=")
            # E.g. `height="20"`
            # NOTE: We don't need to parse the attributes fully. We just need to account
            # for the quotes.
            if is_next_token("'", '"'):
                quote_char = taken_n(1)
                # NOTE: Handle escaped quotes like \" or \', and continue until we reach the closing quote.
                value = take_until([quote_char], ignore=["\\" + quote_char])
                add_token(quote_char)
                quoted = True
            # E.g. `height=20`
            else:
                value = take_until(TAG_WHITESPACE)
                quoted = False
        else:
            value = None
            quoted = False

        attrs.append(
            TagAttr(
                key=key,
                value=value,
                start_index=start_index,
                quoted=quoted,
            )
        )

    return normalized, attrs


# TODO
tag = Tag("component 'my_comp' key=val key2='val2 two' ")
print(tag.attrs)
print(tag.content[tag.attrs[0].start_index : tag.attrs[0].start_index + tag.attrs[0].length])
tag.remove_attr("key")
print(tag.content)
