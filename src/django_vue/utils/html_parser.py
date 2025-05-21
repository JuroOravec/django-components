import re
from dataclasses import dataclass
from typing import Callable, Dict, List, Literal, Optional, Sequence, Tuple, Union


HtmlState = Literal[
    "text",
    "comment",
    "cdata",
    "start_tag",
    "script",
    "interpolation",
]


COMMENT_START = "<!--"
COMMENT_END = "-->"
CDATA_START = "<![CDATA["
CDATA_END = "]]>"
START_TAG_START = "<"
END_TAG_START = "</"
TAG_END = ">"
TAG_END_SELF_CLOSING = "/>"
INTERPOLATION_START = "{{"
INTERPOLATION_END = "}}"

TAG_WHITESPACE = (" ", "\t", "\n", "\r", "\f")
TAG_NAME_DELIIMITERS = (*TAG_WHITESPACE, TAG_END, TAG_END_SELF_CLOSING)

# See https://developer.mozilla.org/en-US/docs/Glossary/Void_element
VOID_ELEMENTS = (
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
)


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


@dataclass
class Tag:
    name: str
    open_tag_start_index: int
    open_tag_length: int
    close_tag_start_index: int
    close_tag_length: int
    # length: int
    attrs: List[TagAttr]
    parse_interpolation: bool

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

    def rename_attr(self, html: str, old_key: str, new_key: str) -> str:
        found_index = -1
        for index, attr in enumerate(self.attrs):
            if attr.key == old_key:
                found_index = index
                break

        if found_index == -1:
            raise KeyError(f"Attribute with key '{old_key}' not found")

        # The attributes up to the renamed one are not affected.
        # For the rest, we need to adjust the start index.
        attrs_len = len(self.attrs)
        found_attr = self.attrs[found_index]
        found_attr.key = new_key

        key_size_change = len(new_key) - len(old_key)

        self.open_tag_length += key_size_change
        self.close_tag_start_index += key_size_change

        # Iterate only over the remaining attributes
        for index in range(found_index, attrs_len - 1):
            attr = self.attrs[index]
            attr.start_index += key_size_change

        # Update the given HTML - omit the slice containing the attribute
        attr_start_index = self.open_tag_start_index + found_attr.start_index
        html = html[:attr_start_index] + found_attr.formatted + html[attr_start_index + found_attr.length :]

        return html

    def delete_attr(self, html: str, key: str) -> str:
        found_index = -1
        for index, attr in enumerate(self.attrs):
            if attr.key == key:
                found_index = index
                break

        if found_index == -1:
            raise KeyError(f"Attribute with key '{key}' not found")

        # The attributes up to the removed one are not affected.
        # For the rest, we need to adjust the start index.
        attrs_len = len(self.attrs)
        found_attr = self.attrs.pop(found_index)

        self.open_tag_length -= found_attr.length
        self.close_tag_start_index -= found_attr.length

        # Iterate only over the remaining attributes
        for index in range(found_index, attrs_len - 1):
            attr = self.attrs[index]
            attr.start_index -= found_attr.length

        # Update the given HTML - omit the slice containing the attribute
        attr_start_index = self.open_tag_start_index + found_attr.start_index
        html = html[:attr_start_index] + html[attr_start_index + found_attr.length :]

        return html

    def add_attr(self, html: str, key: str, value: Optional[str], quoted: bool) -> str:
        new_attr = TagAttr(
            key=key,
            value=value,
            start_index=self.open_tag_length - 1,
            quoted=quoted,
        )
        self.attrs.append(new_attr)

        # Update the given HTML
        self.open_tag_length += new_attr.length + 1  # +1 for the space
        self.close_tag_start_index += new_attr.length + 1

        html = html[:self.open_tag_start_index + new_attr.start_index] + " " + new_attr.formatted + html[self.open_tag_start_index + new_attr.start_index :]
        return html
    
    def clear_attrs(self, html: str) -> str:
        while len(self.attrs):
            html = self.delete_attr(html, self.attrs[-1].key)
        return html
    
    # Insert content inside the tag at the given index
    def insert_content(self, html: str, content: str, index: int) -> str:
        if index < 0:
            # +2 to account for:
            # - When we're inserting from the end, the end is -1, so we need to add 1
            # - Another +1 to insert AFTER the last character
            position = self.close_tag_start_index + index + 2
        else:
            position = self.open_tag_start_index + self.open_tag_length + index

        html = html[:position] + content + html[position:]
        self.close_tag_start_index += len(content)

        return html

    def clear_content(self, html: str) -> str:
        html = html[:self.open_tag_start_index + self.open_tag_length] + html[self.close_tag_start_index :]
        self.close_tag_start_index = self.open_tag_start_index + self.open_tag_length
        return html

    def replace_content(self, html: str, content: str) -> str:
        html = self.clear_content(html)
        html = self.insert_content(html, content, index=0)
        return html

    def prepend(self, html: str, content: str) -> str:
        html = html[:self.open_tag_start_index] + content + html[self.open_tag_start_index:]
        self.open_tag_start_index += len(content)
        self.close_tag_start_index += len(content)
        return html

    def append(self, html: str, content: str) -> str:
        end_index = self.close_tag_start_index + self.close_tag_length
        html = html[:end_index] + content + html[end_index:]
        return html
    
    def wrap(self, html: str, start_tag: str, end_tag: str) -> str:
        content_end_index = self.close_tag_start_index + self.close_tag_length

        html = (
            html[:self.open_tag_start_index]
            + start_tag
            + html[self.open_tag_start_index:content_end_index]
            + end_tag
            + html[content_end_index:]
        )

        # NOTE: Attributes' indices are relative to the start tag, so they don't need updating
        self.open_tag_start_index += len(start_tag)
        self.close_tag_start_index += len(start_tag)

        return html

    # Remove opening and closing tags, leaving only the content
    def unwrap(self, html: str) -> str:
        html = (
            # Text BEFORE the opening tag
            html[:self.open_tag_start_index]
            # Content
            + html[self.open_tag_start_index + self.open_tag_length : self.close_tag_start_index]
            # Text AFTER the closing tag
            + html[self.close_tag_start_index + self.close_tag_length :]
        )
        return html
    
    def rename_tag(self, html: str, new_tag_name: str) -> str:
        # Rename start tag
        html = html[:self.open_tag_start_index] + new_tag_name + html[self.open_tag_start_index + len(self.name):]
        # Rename end tag
        html = html[:self.close_tag_start_index] + new_tag_name + html[self.close_tag_start_index + len(self.name):]

        self.name = new_tag_name
        return html


# Pre-process Vue HTML, so it can be parsed with Selectolax / Lexbor and used with AlpineJs:
# 1. Self-closing tags are converted to regular tags, unless they are void elements
# 2. Vue's `{{ ... }}` syntax is converted to Alpine's `<span x-text="..."></span>`
#
# TODO: Doesn't support regexes inside interpolation!
#
# ==========================
#
# NOTES:
#
# ```html
# <!doctype html>
# <html>
#   <head>
#     <title>Test</title>
#   </head>
#   <body>
#     <!-- "-->" -->
#     <div x="<!-- -->" y='adw' z=`dwada`>
#       <link />
#     </div>
#     <script type="text/javascript">
#       // <![CDATA[
#         console.log("</script>");
#       // ]]>
#     </script>
#   </body>
# </html>
# ```
#
# States:
# 1. Text (can enter tag, comment, CDATA)
# 2. Inside HTML comment (will end at `-- >`)
# 3. Inside CDATA (will end at `]]>`)
# 4. Inside start tag (can enter attribute, will end at `>` or `/>`)
#    - If either `/>` reached, or the tag is a void element, then the tag ends immediately
#    - Otherwise, at `>`, we enter the tag's content (the "text" state)
# 5. Inside tag content (will end at `</tagname >`)
# 6. Inside attribute (will end at `"` or `'`, escaped quotes do nothing)
#
# Rules:
# 1. HTML comments
#   1.1. Comments allowed only as content (NOT inside tags or attributes)
#   1.2. If in HTML comment, comment WILL end at `-- >` (without space). Quotes or backslash do nothing
#
# 2. CDATA
#   2.1. CDATA allowed only as content (NOT inside tags or attributes)
#   1.2. If in CDATA, it WILL end at `]]>`. Quotes or backslash do nothing.
#
# 3. Tags
#   3.1. Tags allowed only as content (NOT inside tags or attributes)
#   3.2. If we come across tag, ignore any content inside its attributes (<div x="" y='adw'>)
#   3.2. If in tag, tag WILL end at `>`. Quotes or backslash do nothing.
#
# 4. Attributes
#   4.1. Attributes allowed only inside tags
#   4.2. If in attribute, attribute WILL end at `"` or `'`. Escaped quotes do nothing.
#
# 5. Text
#   5.1. Text allowed only as content (NOT inside tags or attributes)
#   5.2. If in text, text WILL end at `<` (start of start tag), `</` (start of end tag), `<!--` (start of comment), `<![CDATA[` (start of CDATA)
def parse_html(
    text: str,
    on_tag: Callable[[str, Tag], str],
    convert_interpolation: bool,
    expand_shorthand_tags: bool,
) -> str:
    # State
    state: HtmlState = "text"

    index = 0
    normalized = ""

    tag_stack: List[Tag] = []

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

    while index < len(text):
        char = text[index]
        curr_tag_name = tag_stack[-1].name if tag_stack else None

        # Start comment
        if state == "text" and is_next_token(COMMENT_START):
            add_token(COMMENT_START)
            state = "comment"
            continue

        # Inside comment
        elif state == "comment" and not is_next_token(COMMENT_END):
            add_token(char)
            continue

        # End comment
        elif state == "comment" and is_next_token(COMMENT_END):
            add_token(COMMENT_END)
            state = "text"
            continue

        elif state == "comment":
            raise ValueError("Invalid state: Reached unknown state for 'comment'")

        # Start CDATA
        elif state == "text" and is_next_token(CDATA_START):
            add_token(CDATA_START)
            state = "cdata"
            continue

        # Inside CDATA
        elif state == "cdata" and not is_next_token(CDATA_END):
            add_token(char)
            continue

        # End CDATA
        elif state == "cdata" and is_next_token(CDATA_END):
            add_token(CDATA_END)
            state = "text"
            continue

        # Start StartTag
        elif state == "text" and is_next_token(START_TAG_START) and not is_next_token(END_TAG_START):
            start_index = len(normalized)

            add_token(START_TAG_START)
            state = "start_tag"
            new_tag_name = take_until(TAG_NAME_DELIIMITERS).strip()
            if not new_tag_name:
                raise ValueError(f"Start tag MUST have a tag name (around index {index})")

            tag = Tag(
                name=new_tag_name,
                open_tag_start_index=start_index,
                open_tag_length=0,
                close_tag_start_index=0,
                close_tag_length=0,
                attrs=[],
                parse_interpolation=tag_stack[-1].parse_interpolation if tag_stack else True,
            )
            tag_stack.append(tag)

            continue

        # Inside StartTag
        elif state == "start_tag" and not is_next_token(TAG_END, TAG_END_SELF_CLOSING):
            if not tag_stack:
                raise ValueError(f"Invalid state: No tag in the stack at index {index}")
            tag = tag_stack[-1]

            # Parse HTML attributes
            attrs: List[TagAttr] = []
            while True:
                take_while(TAG_WHITESPACE)
                if is_next_token(TAG_END, TAG_END_SELF_CLOSING):
                    break

                attr_start_index = len(normalized) - tag.open_tag_start_index
                key = take_until(["=", *TAG_WHITESPACE, TAG_END, TAG_END_SELF_CLOSING])

                # Has value
                if is_next_token("="):
                    add_token("=")
                    # E.g. `height="20"`
                    # NOTE: We don't need to parse the HTML attributes fully. We just need to account
                    # for the quotes.
                    if is_next_token("'", '"'):
                        quote_char = taken_n(1)
                        # NOTE: Inside an attribute value, there's no such thing as escaping quotes
                        #       like in JS you can do \" or \'. So we parse whatever is inside the quotes
                        #       until we reach the closing quote.
                        value = take_until([quote_char])
                        add_token(quote_char)
                        quoted = True
                    # E.g. `height=20`
                    else:
                        value = take_until(TAG_NAME_DELIIMITERS)
                        quoted = False
                else:
                    value = None
                    quoted = False

                attrs.append(
                    TagAttr(
                        key=key,
                        value=value,
                        start_index=attr_start_index,
                        quoted=quoted,
                    )
                )

            tag.attrs = attrs

            if convert_interpolation and tag.has_attr("v-pre"):
                tag.parse_interpolation = False
                normalized = tag.delete_attr(normalized, "v-pre")

            continue

        # End StartTag (regular)
        elif state == "start_tag" and is_next_token(TAG_END):
            if not curr_tag_name:
                raise ValueError(f"Invalid state: Reached end of start tag without a tag name at index {index}")

            add_token(char)

            # Mark the end of the start tag
            if not tag_stack:
                raise ValueError(f"Invalid state: No tag in the stack at index {index}")
            tag = tag_stack[-1]
            tag.open_tag_length = len(normalized) - tag.open_tag_start_index

            if curr_tag_name.lower() in VOID_ELEMENTS:
                # Mark the end of the start tag
                tag.open_tag_length = len(normalized) - tag.open_tag_start_index
                tag_stack.pop()
                state = "text"
                continue

            # NOTE: Inside a <script> tag, there may be nested tags as comments or strings
            # e.g.
            # ```html
            # <script>
            #  // <div></div>
            # console.log("</script>");
            # </script>
            # ```
            if curr_tag_name.lower() == "script":
                state = "script"
            else:
                state = "text"

            continue

        # End StartTag (self-closing)
        elif state == "start_tag" and is_next_token(TAG_END_SELF_CLOSING):
            if not curr_tag_name:
                raise ValueError("Invalid state: Reached self-closing tag without a tag name")

            tag = tag_stack[-1]

            # NOTE: If the tag is a void element, then it doesn't have a closing tag.
            #       If any other tag is using self-closing syntax, then it's technically invalid,
            #       and we add a closing tag for it.
            #       See https://developer.mozilla.org/en-US/docs/Glossary/Void_element
            #
            #       This way we enable Vue's syntax, where one can use self-closing tags even
            #       with non-void tags or custom components.
            if curr_tag_name.lower() in VOID_ELEMENTS or not expand_shorthand_tags:
                add_token(TAG_END_SELF_CLOSING)
                # Mark the end of the start tag
                tag.open_tag_length = len(normalized) - tag.open_tag_start_index
            else:
                # Expand self-closing tags by inserting e.g. `></div>` instead of `/>`
                replace_next(len(TAG_END_SELF_CLOSING), TAG_END)

                tag.open_tag_length = len(normalized) - tag.open_tag_start_index
                tag.close_tag_start_index = tag.open_tag_start_index + tag.open_tag_length
                tag.close_tag_length = len(f"{END_TAG_START}{curr_tag_name}{TAG_END}")

                replace_next(0, f"{END_TAG_START}{curr_tag_name}{TAG_END}")

            normalized = on_tag(normalized, tag)

            # NOTE: When we pop, we enter "text" state, because only there we can enter tags.
            tag_stack.pop()
            state = "text"
            continue

        elif state == "start_tag":
            raise ValueError("Invalid state: Reached unknown state for 'start_tag'")

        # EndTag
        elif state == "text" and is_next_token(END_TAG_START):
            tag = tag_stack[-1]

            tag.close_tag_start_index = len(normalized)

            add_token(END_TAG_START)
            tag_name = take_until(TAG_END).strip()
            add_token(TAG_END)

            tag.close_tag_length = len(normalized) - tag.close_tag_start_index

            if not tag_name:
                raise ValueError(f"End tag MUST have a tag name (around index {index})")

            if curr_tag_name is None or tag_name != curr_tag_name:
                raise ValueError(
                    f"End tag '{tag_name}' does not match the current tag '{curr_tag_name}' at index {index}"
                )

            normalized = on_tag(normalized, tag)

            # NOTE: When we pop, we enter "text" state, because only there we can enter tags.
            tag_stack.pop()
            state = "text"

            continue

        # Inside script tag
        elif state == "script":
            # Handle `//` JS comments
            if is_next_token("//"):
                add_token("//")
                take_until(["\n", "\r\n"])
                if is_next_token("\r\n"):
                    add_token("\r\n")
                else:
                    add_token("\n")
                continue

            # Handle `/**/` JS comments
            elif is_next_token("/*"):
                add_token("/*")
                take_until(["*/"])
                add_token("*/")
                continue

            # Handle strings
            elif is_next_token("'"):
                add_token("'")
                take_until(["'"], ignore=["\\'"])
                add_token("'")
                continue

            elif is_next_token('"'):
                add_token('"')
                take_until(['"'], ignore=['\\"'])
                add_token('"')
                continue

            elif is_next_token("`"):
                add_token("`")
                take_until(["`"], ignore=["\\`"])
                add_token("`")
                continue

            # e.g. `</script`
            elif is_next_token(f"{END_TAG_START}script"):
                # We've reached the end of the script tag, so delegate back to the "text" state
                state = "text"
                continue

            # Any other characters
            else:
                add_token(char)
                continue

        # Start interpolation
        elif state == "text" and is_next_token(INTERPOLATION_START):
            # Leave `{{ ... }}` as they are if any ancestor contains `v-pre`
            if not convert_interpolation or (tag_stack and not tag_stack[-1].parse_interpolation):
                add_token(INTERPOLATION_START)
                continue

            # NOTE: This is where we convert Vue's `{{ ... }}` syntax
            # to Alpine's `<span x-text="..."></span>`
            replace_next(len(INTERPOLATION_START), '<span x-text="')
            state = "interpolation"
            continue

        # Inside interpolation
        elif state == "interpolation" and not is_next_token(INTERPOLATION_END):
            # Handle strings
            if is_next_token("'"):
                add_token("'")
                take_until(["'"], ignore=["\\'"])
                add_token("'")
                continue

            # NOTE: We need to escape double quotes because those are used to wrap the string
            elif is_next_token('"'):
                replace_next(1, "&quot;")

                while True:
                    take_until(['"', "\\"])
                    # Handle escaped quotes
                    if is_next_token("\\"):
                        taken_n(2)
                        continue
                    break

                replace_next(1, "&quot;")
                continue

            elif is_next_token("`"):
                add_token("`")
                take_until(["`"], ignore=["\\`"])
                add_token("`")
                continue

            # Any other in-string character
            else:
                add_token(char)
                continue

        # End interpolation
        elif state == "interpolation" and is_next_token(INTERPOLATION_END):
            replace_next(len(INTERPOLATION_END), '"></span>')
            state = "text"
            continue

        # Regular text
        elif state == "text":
            add_token(char)
            continue

        else:
            raise ValueError(f"Invalid state '{state}' with character '{char}' at index {index} in text '{text}'")

    return normalized
