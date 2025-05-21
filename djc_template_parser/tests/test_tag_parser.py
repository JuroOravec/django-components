# # This same set of tests is also found in django-components, to ensure that
# # this implementation can be replaced with the django-components' pure-python implementation

# from djc_core_html_parser import set_html_attributes
# from typing import Dict, List


# def test_basic_transformation():
#     html = "<div><p>Hello</p></div>"
#     result, _ = set_html_attributes(html, ["data-root"], ["data-all"])
#     expected = '<div data-root="" data-all=""><p data-all="">Hello</p></div>'
#     assert result == expected


# def test_multiple_roots():
#     html = "<div>First</div><span>Second</span>"
#     result, _ = set_html_attributes(html, ["data-root"], ["data-all"])
#     expected = '<div data-root="" data-all="">First</div><span data-root="" data-all="">Second</span>'
#     assert result == expected


# def test_complex_html():
#     html = """
#         <div class="container" id="main">
#             <header class="flex">
#                 <h1 title="Main Title">Hello & Welcome</h1>
#                 <nav data-existing="true">
#                     <a href="/home">Home</a>
#                     <a href="/about" class="active">About</a>
#                 </nav>
#             </header>
#             <main>
#                 <article data-existing="true">
#                     <h2>Article 1</h2>
#                     <p>Some text with <strong>bold</strong> and <em>emphasis</em></p>
#                     <img src="test.jpg" alt="Test Image"/>
#                 </article>
#             </main>
#         </div>
#         <footer id="footer">
#             <p>&copy; 2024</p>
#         </footer>
#     """

#     result, _ = set_html_attributes(html, ["data-root"], ["data-all", "data-v-123"])
#     expected = """
#         <div class="container" id="main" data-root="" data-all="" data-v-123="">
#             <header class="flex" data-all="" data-v-123="">
#                 <h1 title="Main Title" data-all="" data-v-123="">Hello & Welcome</h1>
#                 <nav data-existing="true" data-all="" data-v-123="">
#                     <a href="/home" data-all="" data-v-123="">Home</a>
#                     <a href="/about" class="active" data-all="" data-v-123="">About</a>
#                 </nav>
#             </header>
#             <main data-all="" data-v-123="">
#                 <article data-existing="true" data-all="" data-v-123="">
#                     <h2 data-all="" data-v-123="">Article 1</h2>
#                     <p data-all="" data-v-123="">Some text with <strong data-all="" data-v-123="">bold</strong> and <em data-all="" data-v-123="">emphasis</em></p>
#                     <img src="test.jpg" alt="Test Image" data-all="" data-v-123=""/>
#                 </article>
#             </main>
#         </div>
#         <footer id="footer" data-root="" data-all="" data-v-123="">
#             <p data-all="" data-v-123="">&copy; 2024</p>
#         </footer>
#     """  # noqa: E501
#     assert result == expected


# def test_void_elements():
#     test_cases = [
#         ('<meta charset="utf-8">', '<meta charset="utf-8" data-root="" data-v-123=""/>'),
#         ('<meta charset="utf-8"/>', '<meta charset="utf-8" data-root="" data-v-123=""/>'),
#         ("<div><br><hr></div>", '<div data-root="" data-v-123=""><br data-v-123=""/><hr data-v-123=""/></div>'),
#         ('<img src="test.jpg" alt="Test">', '<img src="test.jpg" alt="Test" data-root="" data-v-123=""/>'),
#     ]

#     for input_html, expected in test_cases:
#         result, _ = set_html_attributes(input_html, ["data-root"], ["data-v-123"])
#         assert result == expected


# def test_html_head_with_meta():
#     html = """
#         <head>
#             <meta charset="utf-8">
#             <title>Test Page</title>
#             <link rel="stylesheet" href="style.css">
#             <meta name="description" content="Test">
#         </head>"""

#     result, _ = set_html_attributes(html, ["data-root"], ["data-v-123"])
#     expected = """
#         <head data-root="" data-v-123="">
#             <meta charset="utf-8" data-v-123=""/>
#             <title data-v-123="">Test Page</title>
#             <link rel="stylesheet" href="style.css" data-v-123=""/>
#             <meta name="description" content="Test" data-v-123=""/>
#         </head>"""
#     assert result == expected


# def test_watch_attribute():
#     html = """
#         <div data-id="123">
#             <p>Regular element</p>
#             <span data-id="456">Nested element</span>
#             <img data-id="789" src="test.jpg"/>
#         </div>"""

#     result: str
#     captured: Dict[str, List[str]]
#     result, captured = set_html_attributes(html, ["data-root"], ["data-v-123"], watch_on_attribute="data-id")
#     expected = """
#         <div data-id="123" data-root="" data-v-123="">
#             <p data-v-123="">Regular element</p>
#             <span data-id="456" data-v-123="">Nested element</span>
#             <img data-id="789" src="test.jpg" data-v-123=""/>
#         </div>"""
#     assert result == expected

#     # Verify attribute capturing
#     assert len(captured) == 3

#     # Root element should have both root and all attributes
#     assert "123" in captured
#     assert "data-root" in captured["123"]
#     assert "data-v-123" in captured["123"]

#     # Non-root elements should only have all attributes
#     assert "456" in captured
#     assert captured["456"] == ["data-v-123"]
#     assert "789" in captured
#     assert captured["789"] == ["data-v-123"]


# def test_whitespace_preservation():
#     html = """<div>
#         <p>  Hello  World  </p>
#         <span> Text with spaces </span>
#     </div>"""

#     result, _ = set_html_attributes(html, ["data-root"], ["data-all"])
#     expected = """<div data-root="" data-all="">
#         <p data-all="">  Hello  World  </p>
#         <span data-all=""> Text with spaces </span>
#     </div>"""
#     assert result == expected






from unittest import skip

from django.template import Context, Template, TemplateSyntaxError
from django.template.base import Parser
from django.template.engine import Engine

from django_components import Component, register, types
from django_components.util.tag_parser import TagAttr, TagValue, TagValuePart, TagValueStruct, parse_tag

from .django_test_setup import setup_test_config
from .testutils import BaseTestCase

setup_test_config({"autodiscover": False})


# NOTE: We have to define the parser to be able to resolve filters
def _get_parser() -> Parser:
    engine = Engine.get_default()
    return Parser(
        tokens=[],
        libraries=engine.template_libraries,
        builtins=engine.template_builtins,
        origin=None,
    )


class TagParserTests(BaseTestCase):
    def test_args_kwargs(self):
        _, attrs = parse_tag("component 'my_comp' key=val key2='val2 two' ", None)

        expected_attrs = [
            TagAttr(
                key=None,
                start_index=0,
                value=TagValueStruct(
                    type="simple",
                    meta={},
                    spread=None,
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="component", quoted=None, spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                ),
            ),
            TagAttr(
                key=None,
                start_index=10,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value="my_comp", quoted="'", spread=None, translation=False, filter=None)
                            ]
                        )
                    ],
                ),
            ),
            TagAttr(
                key="key",
                start_index=20,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[TagValuePart(value="val", quoted=None, spread=None, translation=False, filter=None)]
                        )
                    ],
                ),
            ),
            TagAttr(
                key="key2",
                start_index=28,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value="val2 two", quoted="'", spread=None, translation=False, filter=None)
                            ]
                        )
                    ],
                ),
            ),
        ]

        self.assertEqual(attrs, expected_attrs)
        self.assertEqual(
            [a.serialize() for a in attrs],
            [
                "component",
                "'my_comp'",
                "key=val",
                "key2='val2 two'",
            ],
        )

    def test_nested_quotes(self):
        _, attrs = parse_tag("component 'my_comp' key=val key2='val2 \"two\"' text=\"organisation's\" ", None)

        expected_attrs = [
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="component", quoted=None, spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                ),
                start_index=0,
            ),
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value="my_comp", quoted="'", spread=None, translation=False, filter=None)
                            ]
                        )
                    ],
                ),
                start_index=10,
            ),
            TagAttr(
                key="key",
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[TagValuePart(value="val", quoted=None, spread=None, translation=False, filter=None)]
                        )
                    ],
                ),
                start_index=20,
            ),
            TagAttr(
                key="key2",
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value='val2 "two"', quoted="'", spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                ),
                start_index=28,
            ),
            TagAttr(
                key="text",
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="organisation's", quoted='"', spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                ),
                start_index=46,
            ),
        ]

        self.assertEqual(attrs, expected_attrs)
        self.assertEqual(
            [a.serialize() for a in attrs],
            [
                "component",
                "'my_comp'",
                "key=val",
                "key2='val2 \"two\"'",
                'text="organisation\'s"',
            ],
        )

    def test_trailing_quote_single(self):
        _, attrs = parse_tag("component 'my_comp' key=val key2='val2 \"two\"' text=\"organisation's\" 'abc", None)

        expected_attrs = [
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    meta={},
                    spread=None,
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="component", quoted=None, spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                ),
                start_index=0,
            ),
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value="my_comp", quoted="'", spread=None, translation=False, filter=None)
                            ]
                        )
                    ],
                ),
                start_index=10,
            ),
            TagAttr(
                key="key",
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[TagValuePart(value="val", quoted=None, spread=None, translation=False, filter=None)]
                        )
                    ],
                ),
                start_index=20,
            ),
            TagAttr(
                key="key2",
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value='val2 "two"', quoted="'", spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                ),
                start_index=28,
            ),
            TagAttr(
                key="text",
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="organisation's", quoted='"', spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                ),
                start_index=46,
            ),
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value="'abc", quoted=None, spread=None, translation=False, filter=None)
                            ]
                        )
                    ],
                ),
                start_index=68,
            ),
        ]

        self.assertEqual(attrs, expected_attrs)
        self.assertEqual(
            [a.serialize() for a in attrs],
            [
                "component",
                "'my_comp'",
                "key=val",
                "key2='val2 \"two\"'",
                'text="organisation\'s"',
                "'abc",
            ],
        )

    def test_trailing_quote_double(self):
        _, attrs = parse_tag('component "my_comp" key=val key2="val2 \'two\'" text=\'organisation"s\' "abc', None)

        expected_attrs = [
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="component", quoted=None, spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                ),
                start_index=0,
            ),
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value="my_comp", quoted='"', spread=None, translation=False, filter=None)
                            ]
                        )
                    ],
                ),
                start_index=10,
            ),
            TagAttr(
                key="key",
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[TagValuePart(value="val", quoted=None, spread=None, translation=False, filter=None)]
                        )
                    ],
                ),
                start_index=20,
            ),
            TagAttr(
                key="key2",
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="val2 'two'", quoted='"', spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                ),
                start_index=28,
            ),
            TagAttr(
                key="text",
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value='organisation"s', quoted="'", spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                ),
                start_index=46,
            ),  # noqa: E501
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value='"abc', quoted=None, spread=None, translation=False, filter=None)
                            ]
                        )
                    ],
                ),
                start_index=68,
            ),
        ]

        self.assertEqual(attrs, expected_attrs)
        self.assertEqual(
            [a.serialize() for a in attrs],
            [
                "component",
                '"my_comp"',
                "key=val",
                "key2=\"val2 'two'\"",
                "text='organisation\"s'",
                '"abc',
            ],
        )

    def test_trailing_quote_as_value_single(self):
        _, attrs = parse_tag(
            "component 'my_comp' key=val key2='val2 \"two\"' text=\"organisation's\" value='abc",
            None,
        )

        expected_attrs = [
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="component", quoted=None, spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                ),
                start_index=0,
            ),
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value="my_comp", quoted="'", spread=None, translation=False, filter=None)
                            ]
                        )
                    ],
                ),
                start_index=10,
            ),
            TagAttr(
                key="key",
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[TagValuePart(value="val", quoted=None, spread=None, translation=False, filter=None)]
                        )
                    ],
                ),
                start_index=20,
            ),
            TagAttr(
                key="key2",
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value='val2 "two"', quoted="'", spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                ),
                start_index=28,
            ),
            TagAttr(
                key="text",
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="organisation's", quoted='"', spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                ),
                start_index=46,
            ),
            TagAttr(
                key="value",
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value="'abc", quoted=None, spread=None, translation=False, filter=None)
                            ]
                        )
                    ],
                ),
                start_index=68,
            ),
        ]

        self.assertEqual(attrs, expected_attrs)
        self.assertEqual(
            [a.serialize() for a in attrs],
            [
                "component",
                "'my_comp'",
                "key=val",
                "key2='val2 \"two\"'",
                'text="organisation\'s"',
                "value='abc",
            ],
        )

    def test_trailing_quote_as_value_double(self):
        _, attrs = parse_tag(
            'component "my_comp" key=val key2="val2 \'two\'" text=\'organisation"s\' value="abc',
            None,
        )

        expected_attrs = [
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="component", quoted=None, spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                ),
                start_index=0,
            ),
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value="my_comp", quoted='"', spread=None, translation=False, filter=None)
                            ]
                        )
                    ],
                ),
                start_index=10,
            ),
            TagAttr(
                key="key",
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[TagValuePart(value="val", quoted=None, spread=None, translation=False, filter=None)]
                        )
                    ],
                ),
                start_index=20,
            ),
            TagAttr(
                key="key2",
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="val2 'two'", quoted='"', spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                ),
                start_index=28,
            ),
            TagAttr(
                key="text",
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value='organisation"s', quoted="'", spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                ),
                start_index=46,
            ),
            TagAttr(
                key="value",
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value='"abc', quoted=None, spread=None, translation=False, filter=None)
                            ]
                        )
                    ],
                ),
                start_index=68,
            ),
        ]

        self.assertEqual(attrs, expected_attrs)
        self.assertEqual(
            [a.serialize() for a in attrs],
            [
                "component",
                '"my_comp"',
                "key=val",
                "key2=\"val2 'two'\"",
                "text='organisation\"s'",
                'value="abc',
            ],
        )

    def test_translation(self):
        _, attrs = parse_tag('component "my_comp" _("one") key=_("two")', None)

        expected_attrs = [
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="component", quoted=None, spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                ),
                start_index=0,
            ),
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value="my_comp", quoted='"', spread=None, translation=False, filter=None)
                            ]
                        )
                    ],
                ),
                start_index=10,
            ),
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[TagValuePart(value="one", quoted='"', spread=None, translation=True, filter=None)]
                        )
                    ],
                ),
                start_index=20,
            ),
            TagAttr(
                key="key",
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[TagValuePart(value="two", quoted='"', spread=None, translation=True, filter=None)]
                        )
                    ],
                ),
                start_index=29,
            ),
        ]

        self.assertEqual(attrs, expected_attrs)
        self.assertEqual(
            [a.serialize() for a in attrs],
            [
                "component",
                '"my_comp"',
                '_("one")',
                'key=_("two")',
            ],
        )

    def test_tag_parser_filters(self):
        _, attrs = parse_tag(
            'component "my_comp" value|lower key=val|yesno:"yes,no" key2=val2|default:"N/A"|upper',
            None,
        )

        expected_attrs = [
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="component", quoted=None, spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                ),
                start_index=0,
            ),
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value="my_comp", quoted='"', spread=None, translation=False, filter=None)
                            ]
                        )
                    ],
                ),
                start_index=10,
            ),
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value="value", quoted=None, spread=None, translation=False, filter=None),
                                TagValuePart(value="lower", quoted=None, spread=None, translation=False, filter="|"),
                            ]
                        )
                    ],
                ),
                start_index=20,
            ),
            TagAttr(
                key="key",
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value="val", quoted=None, spread=None, translation=False, filter=None),
                                TagValuePart(value="yesno", quoted=None, spread=None, translation=False, filter="|"),
                                TagValuePart(value="yes,no", quoted='"', spread=None, translation=False, filter=":"),
                            ]
                        )
                    ],
                ),
                start_index=32,
            ),
            TagAttr(
                key="key2",
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value="val2", quoted=None, spread=None, translation=False, filter=None),
                                TagValuePart(value="default", quoted=None, spread=None, translation=False, filter="|"),
                                TagValuePart(value="N/A", quoted='"', spread=None, translation=False, filter=":"),
                                TagValuePart(value="upper", quoted=None, spread=None, translation=False, filter="|"),
                            ]
                        )
                    ],
                ),
                start_index=55,
            ),
        ]

        self.assertEqual(attrs, expected_attrs)
        self.assertEqual(
            [a.serialize() for a in attrs],
            [
                "component",
                '"my_comp"',
                "value|lower",
                'key=val|yesno:"yes,no"',
                'key2=val2|default:"N/A"|upper',
            ],
        )

    def test_translation_whitespace(self):
        _, attrs = parse_tag('component value=_(  "test"  )', None)

        expected_attrs = [
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="component", quoted=None, spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                ),
                start_index=0,
            ),
            TagAttr(
                key="value",
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value="test", quoted='"', spread=None, translation=True, filter=None),
                            ]
                        )
                    ],
                ),
                start_index=10,
            ),
        ]
        self.assertEqual(attrs, expected_attrs)

    def test_filter_whitespace(self):
        _, attrs = parse_tag("component value  |  lower    key=val  |  upper    key2=val2", None)

        expected_attrs = [
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="component", quoted=None, spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                ),
                start_index=0,
            ),
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value="value", quoted=None, spread=None, translation=False, filter=None),
                                TagValuePart(value="lower", quoted=None, spread=None, translation=False, filter="|"),
                            ]
                        )
                    ],
                ),
                start_index=10,
            ),
            TagAttr(
                key="key",
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value="val", quoted=None, spread=None, translation=False, filter=None),
                                TagValuePart(value="upper", quoted=None, spread=None, translation=False, filter="|"),
                            ]
                        )
                    ],
                ),
                start_index=29,
            ),
            TagAttr(
                key="key2",
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value="val2", quoted=None, spread=None, translation=False, filter=None),
                            ]
                        )
                    ],
                ),
                start_index=50,
            ),
        ]

        self.assertEqual(attrs, expected_attrs)

    def test_filter_argument_must_follow_filter(self):
        with self.assertRaisesMessage(
            TemplateSyntaxError,
            "Filter argument (':arg') must follow a filter ('|filter')",
        ):
            parse_tag('component value=val|yesno:"yes,no":arg', None)

    def test_dict_simple(self):
        _, attrs = parse_tag('component data={ "key": "val" }', None)

        expected_attrs = [
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="component", quoted=None, spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                ),
                start_index=0,
            ),
            TagAttr(
                key="data",
                value=TagValueStruct(
                    type="dict",
                    meta={},
                    spread=None,
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value="key", quoted='"', spread=None, translation=False, filter=None),
                            ]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(value="val", quoted='"', spread=None, translation=False, filter=None),
                            ]
                        ),
                    ],
                ),
                start_index=10,
            ),
        ]

        self.assertEqual(attrs, expected_attrs)

    def test_dict_trailing_comma(self):
        _, attrs = parse_tag('component data={ "key": "val", }', None)

        expected_attrs = [
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="component", quoted=None, spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                ),
                start_index=0,
            ),
            TagAttr(
                key="data",
                value=TagValueStruct(
                    type="dict",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value="key", quoted='"', spread=None, translation=False, filter=None),
                            ]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(value="val", quoted='"', spread=None, translation=False, filter=None),
                            ]
                        ),
                    ],
                ),
                start_index=10,
            ),
        ]

        self.assertEqual(attrs, expected_attrs)

    def test_dict_missing_colon(self):
        with self.assertRaisesMessage(TemplateSyntaxError, "Dictionary key is missing a value"):
            parse_tag('component data={ "key" }', None)

    def test_dict_missing_colon_2(self):
        with self.assertRaisesMessage(TemplateSyntaxError, "Dictionary key is missing a value"):
            parse_tag('component data={ "key", "val" }', None)

    def test_dict_extra_colon(self):
        with self.assertRaisesMessage(TemplateSyntaxError, "Unexpected colon"):
            _, attrs = parse_tag("component data={ key:: key }", None)

    def test_dict_spread(self):
        _, attrs = parse_tag("component data={ **spread }", None)

        expected_attrs = [
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="component", quoted=None, spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                ),
                start_index=0,
            ),
            TagAttr(
                key="data",
                value=TagValueStruct(
                    type="dict",
                    meta={},
                    spread=None,
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value="spread", quoted=None, spread="**", translation=False, filter=None),
                            ]
                        )
                    ],
                ),
                start_index=10,
            ),
        ]

        self.assertEqual(attrs, expected_attrs)

    def test_dict_spread_between_key_value_pairs(self):
        _, attrs = parse_tag('component data={ "key": val, **spread, "key2": val2 }', None)

        expected_attrs = [
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="component", quoted=None, spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                ),
                start_index=0,
            ),
            TagAttr(
                key="data",
                value=TagValueStruct(
                    type="dict",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value="key", quoted='"', spread=None, translation=False, filter=None),
                            ]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(value="val", quoted=None, spread=None, translation=False, filter=None),
                            ]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(value="spread", quoted=None, spread="**", translation=False, filter=None),
                            ]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(value="key2", quoted='"', spread=None, translation=False, filter=None),
                            ]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(value="val2", quoted=None, spread=None, translation=False, filter=None),
                            ]
                        ),
                    ],
                ),
                start_index=10,
            ),
        ]

        self.assertEqual(attrs, expected_attrs)

    # Test that dictionary keys cannot have filter arguments - The `:` is parsed as dictionary key separator
    # So instead, the content below will be parsed as key `"key"|filter`, and value `"arg":"value"'
    # And the latter is invalid because it's missing the `|` separator.
    def test_colon_in_dictionary_keys(self):
        with self.assertRaisesMessage(
            TemplateSyntaxError, "Filter argument (':arg') must follow a filter ('|filter')"
        ):
            _, attrs = parse_tag('component data={"key"|filter:"arg": "value"}', None)

    def test_list_simple(self):
        _, attrs = parse_tag("component data=[1, 2, 3]", None)

        expected_attrs = [
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    meta={},
                    spread=None,
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="component", quoted=None, spread=None, translation=False, filter=None
                                ),
                            ]
                        )
                    ],
                ),
                start_index=0,
            ),
            TagAttr(
                key="data",
                value=TagValueStruct(
                    type="list",
                    meta={},
                    spread=None,
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value="1", quoted=None, spread=None, translation=False, filter=None),
                            ]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(value="2", quoted=None, spread=None, translation=False, filter=None),
                            ]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(value="3", quoted=None, spread=None, translation=False, filter=None),
                            ]
                        ),
                    ],
                ),
                start_index=10,
            ),
        ]

        self.assertEqual(attrs, expected_attrs)

    def test_list_trailing_comma(self):
        _, attrs = parse_tag("component data=[1, 2, 3, ]", None)

        expected_attrs = [
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    meta={},
                    spread=None,
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="component", quoted=None, spread=None, translation=False, filter=None
                                ),
                            ]
                        )
                    ],
                ),
                start_index=0,
            ),
            TagAttr(
                key="data",
                value=TagValueStruct(
                    type="list",
                    meta={},
                    spread=None,
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value="1", quoted=None, spread=None, translation=False, filter=None),
                            ]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(value="2", quoted=None, spread=None, translation=False, filter=None),
                            ]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(value="3", quoted=None, spread=None, translation=False, filter=None),
                            ]
                        ),
                    ],
                ),
                start_index=10,
            ),
        ]

        self.assertEqual(attrs, expected_attrs)

    def test_lists_complex(self):
        _, attrs = parse_tag(
            """
                component
                nums=[
                    1,
                    2|add:3,
                    *spread
                ]
                items=[
                    "a"|upper,
                    'b'|lower,
                    c|default:"d"
                ]
                mixed=[
                    1,
                    [*nested],
                    {"key": "val"}
                ]
            """,
            None,
        )

        expected_attrs = [
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="component", quoted=None, spread=None, translation=False, filter=None
                                ),
                            ]
                        )
                    ],
                ),
                start_index=17,
            ),
            TagAttr(
                key="nums",
                value=TagValueStruct(
                    type="list",
                    meta={},
                    spread=None,
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[TagValuePart(value="1", quoted=None, spread=None, translation=False, filter=None)]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(value="2", quoted=None, spread=None, translation=False, filter=None),
                                TagValuePart(value="add", quoted=None, spread=None, translation=False, filter="|"),
                                TagValuePart(value="3", quoted=None, spread=None, translation=False, filter=":"),
                            ]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(value="spread", quoted=None, spread="*", translation=False, filter=None)
                            ]
                        ),
                    ],
                ),
                start_index=43,
            ),
            TagAttr(
                key="items",
                value=TagValueStruct(
                    type="list",
                    meta={},
                    spread=None,
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value="a", quoted='"', spread=None, translation=False, filter=None),
                                TagValuePart(value="upper", quoted=None, spread=None, translation=False, filter="|"),
                            ]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(value="b", quoted="'", spread=None, translation=False, filter=None),
                                TagValuePart(value="lower", quoted=None, spread=None, translation=False, filter="|"),
                            ]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(value="c", quoted=None, spread=None, translation=False, filter=None),
                                TagValuePart(value="default", quoted=None, spread=None, translation=False, filter="|"),
                                TagValuePart(value="d", quoted='"', spread=None, translation=False, filter=":"),
                            ]
                        ),
                    ],
                ),
                start_index=164,
            ),
            TagAttr(
                key="mixed",
                value=TagValueStruct(
                    type="list",
                    meta={},
                    spread=None,
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[TagValuePart(value="1", quoted=None, spread=None, translation=False, filter=None)]
                        ),
                        TagValueStruct(
                            type="list",
                            meta={},
                            spread=None,
                            parser=None,
                            entries=[
                                TagValue(
                                    parts=[
                                        TagValuePart(
                                            value="nested",
                                            quoted=None,
                                            spread="*",
                                            translation=False,
                                            filter=None,
                                        )
                                    ]
                                ),
                            ],
                        ),
                        TagValueStruct(
                            type="dict",
                            meta={},
                            spread=None,
                            parser=None,
                            entries=[
                                TagValue(
                                    parts=[
                                        TagValuePart(
                                            value="key",
                                            quoted='"',
                                            spread=None,
                                            translation=False,
                                            filter=None,
                                        )
                                    ]
                                ),
                                TagValue(
                                    parts=[
                                        TagValuePart(
                                            value="val",
                                            quoted='"',
                                            spread=None,
                                            translation=False,
                                            filter=None,
                                        )
                                    ]
                                ),
                            ],
                        ),
                    ],
                ),
                start_index=302,
            ),
        ]

        self.assertEqual(attrs, expected_attrs)
        self.assertEqual(
            [a.serialize() for a in attrs],
            [
                "component",
                "nums=[1, 2|add:3, *spread]",
                'items=["a"|upper, \'b\'|lower, c|default:"d"]',
                'mixed=[1, [*nested], {"key": "val"}]',
            ],
        )

    def test_dicts_complex(self):
        _, attrs = parse_tag(
            """
            component
            simple={
                "a": 1|add:2
            }
            nested={
                "key"|upper: val|lower,
                **spread,
                "obj": {"x": 1|add:2}
            }
            filters={
                "a"|lower: "b"|upper,
                c|default: "e"|yesno:"yes,no"
            }
            """,
            None,
        )

        expected_attrs = [
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
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
                start_index=13,
            ),
            TagAttr(
                key="simple",
                value=TagValueStruct(
                    type="dict",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[TagValuePart(value="a", quoted='"', spread=None, translation=False, filter=None)]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(value="1", quoted=None, spread=None, translation=False, filter=None),
                                TagValuePart(value="add", quoted=None, spread=None, translation=False, filter="|"),
                                TagValuePart(value="2", quoted=None, spread=None, translation=False, filter=":"),
                            ]
                        ),
                    ],
                ),
                start_index=35,
            ),
            TagAttr(
                key="nested",
                value=TagValueStruct(
                    type="dict",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value="key", quoted='"', spread=None, translation=False, filter=None),
                                TagValuePart(value="upper", quoted=None, spread=None, translation=False, filter="|"),
                            ]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(value="val", quoted=None, spread=None, translation=False, filter=None),
                                TagValuePart(value="lower", quoted=None, spread=None, translation=False, filter="|"),
                            ]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(value="spread", quoted=None, spread="**", translation=False, filter=None)
                            ]
                        ),
                        TagValue(
                            parts=[TagValuePart(value="obj", quoted='"', spread=None, translation=False, filter=None)]
                        ),
                        TagValueStruct(
                            type="dict",
                            meta={},
                            spread=None,
                            parser=None,
                            entries=[
                                TagValue(
                                    parts=[
                                        TagValuePart(
                                            value="x", quoted='"', spread=None, translation=False, filter=None
                                        )
                                    ]
                                ),
                                TagValue(
                                    parts=[
                                        TagValuePart(
                                            value="1", quoted=None, spread=None, translation=False, filter=None
                                        ),
                                        TagValuePart(
                                            value="add",
                                            quoted=None,
                                            spread=None,
                                            translation=False,
                                            filter="|",
                                        ),
                                        TagValuePart(
                                            value="2", quoted=None, spread=None, translation=False, filter=":"
                                        ),
                                    ]
                                ),
                            ],
                        ),
                    ],
                ),
                start_index=99,
            ),
            TagAttr(
                key="filters",
                value=TagValueStruct(
                    type="dict",
                    meta={},
                    spread=None,
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value="a", quoted='"', spread=None, translation=False, filter=None),
                                TagValuePart(value="lower", quoted=None, spread=None, translation=False, filter="|"),
                            ]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(value="b", quoted='"', spread=None, translation=False, filter=None),
                                TagValuePart(value="upper", quoted=None, spread=None, translation=False, filter="|"),
                            ]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(value="c", quoted=None, spread=None, translation=False, filter=None),
                                TagValuePart(value="default", quoted=None, spread=None, translation=False, filter="|"),
                            ]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(value="e", quoted='"', spread=None, translation=False, filter=None),
                                TagValuePart(value="yesno", quoted=None, spread=None, translation=False, filter="|"),
                                TagValuePart(value="yes,no", quoted='"', spread=None, translation=False, filter=":"),
                            ]
                        ),
                    ],
                ),
                start_index=238,
            ),
        ]

        self.assertEqual(attrs, expected_attrs)
        self.assertEqual(
            [a.serialize() for a in attrs],
            [
                "component",
                'simple={"a": 1|add:2}',
                'nested={"key"|upper: val|lower, **spread, "obj": {"x": 1|add:2}}',
                'filters={"a"|lower: "b"|upper, c|default: "e"|yesno:"yes,no"}',
            ],
        )

    def test_mixed_complex(self):
        _, attrs = parse_tag(
            """
            component
            data={
                "items": [
                    1|add:2,
                    {"x"|upper: 2|add:3},
                    *spread_items|default:""
                ],
                "nested": {
                    "a": [
                        1|add:2,
                        *nums|default:""
                    ],
                    "b": {
                        "x": [
                            *more|default:""
                        ]
                    }
                },
                **rest|default,
                "key": _('value')|upper
            }
            """,
            None,
        )

        expected_attrs = [
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
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
                start_index=13,
            ),
            TagAttr(
                key="data",
                value=TagValueStruct(
                    type="dict",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value="items", quoted='"', spread=None, translation=False, filter=None)
                            ]
                        ),
                        TagValueStruct(
                            type="list",
                            spread=None,
                            meta={},
                            parser=None,
                            entries=[
                                TagValue(
                                    parts=[
                                        TagValuePart(
                                            value="1", quoted=None, spread=None, translation=False, filter=None
                                        ),
                                        TagValuePart(
                                            value="add",
                                            quoted=None,
                                            spread=None,
                                            translation=False,
                                            filter="|",
                                        ),
                                        TagValuePart(
                                            value="2", quoted=None, spread=None, translation=False, filter=":"
                                        ),
                                    ]
                                ),
                                TagValueStruct(
                                    type="dict",
                                    spread=None,
                                    meta={},
                                    parser=None,
                                    entries=[
                                        TagValue(
                                            parts=[
                                                TagValuePart(
                                                    value="x",
                                                    quoted='"',
                                                    spread=None,
                                                    translation=False,
                                                    filter=None,
                                                ),
                                                TagValuePart(
                                                    value="upper",
                                                    quoted=None,
                                                    spread=None,
                                                    translation=False,
                                                    filter="|",
                                                ),
                                            ]
                                        ),
                                        TagValue(
                                            parts=[
                                                TagValuePart(
                                                    value="2",
                                                    quoted=None,
                                                    spread=None,
                                                    translation=False,
                                                    filter=None,
                                                ),
                                                TagValuePart(
                                                    value="add",
                                                    quoted=None,
                                                    spread=None,
                                                    translation=False,
                                                    filter="|",
                                                ),
                                                TagValuePart(
                                                    value="3",
                                                    quoted=None,
                                                    spread=None,
                                                    translation=False,
                                                    filter=":",
                                                ),
                                            ]
                                        ),
                                    ],
                                ),
                                TagValue(
                                    parts=[
                                        TagValuePart(
                                            value="spread_items",
                                            quoted=None,
                                            spread="*",
                                            translation=False,
                                            filter=None,
                                        ),
                                        TagValuePart(
                                            value="default",
                                            quoted=None,
                                            spread=None,
                                            translation=False,
                                            filter="|",
                                        ),
                                        TagValuePart(value="", quoted='"', spread=None, translation=False, filter=":"),
                                    ]
                                ),
                            ],
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(value="nested", quoted='"', spread=None, translation=False, filter=None)
                            ]
                        ),
                        TagValueStruct(
                            type="dict",
                            meta={},
                            spread=None,
                            parser=None,
                            entries=[
                                TagValue(
                                    parts=[
                                        TagValuePart(
                                            value="a", quoted='"', spread=None, translation=False, filter=None
                                        )
                                    ]
                                ),
                                TagValueStruct(
                                    type="list",
                                    spread=None,
                                    meta={},
                                    parser=None,
                                    entries=[
                                        TagValue(
                                            parts=[
                                                TagValuePart(
                                                    value="1",
                                                    quoted=None,
                                                    spread=None,
                                                    translation=False,
                                                    filter=None,
                                                ),
                                                TagValuePart(
                                                    value="add",
                                                    quoted=None,
                                                    spread=None,
                                                    translation=False,
                                                    filter="|",
                                                ),
                                                TagValuePart(
                                                    value="2",
                                                    quoted=None,
                                                    spread=None,
                                                    translation=False,
                                                    filter=":",
                                                ),
                                            ],
                                        ),
                                        TagValue(
                                            parts=[
                                                TagValuePart(
                                                    value="nums",
                                                    quoted=None,
                                                    spread="*",
                                                    translation=False,
                                                    filter=None,
                                                ),
                                                TagValuePart(
                                                    value="default",
                                                    quoted=None,
                                                    spread=None,
                                                    translation=False,
                                                    filter="|",
                                                ),
                                                TagValuePart(
                                                    value="",
                                                    quoted='"',
                                                    spread=None,
                                                    translation=False,
                                                    filter=":",
                                                ),
                                            ]
                                        ),
                                    ],
                                ),
                                TagValue(
                                    parts=[
                                        TagValuePart(
                                            value="b", quoted='"', spread=None, translation=False, filter=None
                                        )
                                    ]
                                ),
                                TagValueStruct(
                                    type="dict",
                                    meta={},
                                    spread=None,
                                    parser=None,
                                    entries=[
                                        TagValue(
                                            parts=[
                                                TagValuePart(
                                                    value="x",
                                                    quoted='"',
                                                    spread=None,
                                                    translation=False,
                                                    filter=None,
                                                )
                                            ]
                                        ),
                                        TagValueStruct(
                                            type="list",
                                            meta={},
                                            spread=None,
                                            parser=None,
                                            entries=[
                                                TagValue(
                                                    parts=[
                                                        TagValuePart(
                                                            value="more",
                                                            quoted=None,
                                                            spread="*",
                                                            translation=False,
                                                            filter=None,
                                                        ),
                                                        TagValuePart(
                                                            value="default",
                                                            quoted=None,
                                                            spread=None,
                                                            translation=False,
                                                            filter="|",
                                                        ),
                                                        TagValuePart(
                                                            value="",
                                                            quoted='"',
                                                            spread=None,
                                                            translation=False,
                                                            filter=":",
                                                        ),
                                                    ]
                                                ),
                                            ],
                                        ),
                                    ],
                                ),
                            ],
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(value="rest", quoted=None, spread="**", translation=False, filter=None),
                                TagValuePart(value="default", quoted=None, spread=None, translation=False, filter="|"),
                            ]
                        ),
                        TagValue(
                            parts=[TagValuePart(value="key", quoted='"', spread=None, translation=False, filter=None)]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(value="value", quoted="'", spread=None, translation=True, filter=None),
                                TagValuePart(value="upper", quoted=None, spread=None, translation=False, filter="|"),
                            ]
                        ),
                    ],
                ),
                start_index=35,
            ),
        ]

        self.assertEqual(attrs, expected_attrs)
        self.assertEqual(
            [a.serialize() for a in attrs],
            [
                "component",
                'data={"items": [1|add:2, {"x"|upper: 2|add:3}, *spread_items|default:""], "nested": {"a": [1|add:2, *nums|default:""], "b": {"x": [*more|default:""]}}, **rest|default, "key": _(\'value\')|upper}',  # noqa: E501
            ],
        )

    # Test that spread operator cannot be used as dictionary value
    def test_spread_as_dictionary_value(self):
        with self.assertRaisesMessage(
            TemplateSyntaxError,
            "Spread syntax cannot be used in place of a dictionary value",
        ):
            parse_tag('component data={"key": **spread}', None)

    def test_spread_with_colon_interpreted_as_key(self):
        with self.assertRaisesMessage(
            TemplateSyntaxError,
            "Spread syntax cannot be used in place of a dictionary key",
        ):
            _, attrs = parse_tag("component data={**spread|abc: 123 }", None)

    def test_spread_in_filter_position(self):
        with self.assertRaisesMessage(
            TemplateSyntaxError,
            "Spread syntax cannot be used inside of a filter",
        ):
            _, attrs = parse_tag("component data=val|...spread|abc }", None)

    def test_spread_whitespace(self):
        # NOTE: Separating `...` from its variable is NOT valid, and will result in error.
        with self.assertRaisesMessage(
            TemplateSyntaxError,
            "Spread syntax '...' is missing a value",
        ):
            _, attrs = parse_tag("component ... attrs", None)

        _, attrs = parse_tag('component dict={"a": "b", ** my_attr} list=["a", * my_list]', None)

        expected_attrs = [
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
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
            TagAttr(
                key="dict",
                value=TagValueStruct(
                    type="dict",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value="a", quoted='"', spread=None, translation=False, filter=None),
                            ]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(value="b", quoted='"', spread=None, translation=False, filter=None),
                            ]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="my_attr", quoted=None, spread="**", translation=False, filter=None
                                ),
                            ]
                        ),
                    ],
                ),
                start_index=10,
            ),
            TagAttr(
                key="list",
                value=TagValueStruct(
                    type="list",
                    meta={},
                    spread=None,
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value="a", quoted='"', spread=None, translation=False, filter=None),
                            ]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(value="my_list", quoted=None, spread="*", translation=False, filter=None),
                            ]
                        ),
                    ],
                ),
                start_index=38,
            ),
        ]
        self.assertEqual(attrs, expected_attrs)

    # Test that one cannot use e.g. `...`, `**`, `*` in wrong places
    def test_spread_incorrect_syntax(self):
        with self.assertRaisesMessage(
            TemplateSyntaxError,
            "Spread syntax '*' found outside of a list",
        ):
            _, attrs = parse_tag('component dict={"a": "b", *my_attr}', None)

        with self.assertRaisesMessage(
            TemplateSyntaxError,
            "Spread syntax '...' found in dict. It must be used on tag attributes only",
        ):
            _, attrs = parse_tag('component dict={"a": "b", ...my_attr}', None)

        with self.assertRaisesMessage(
            TemplateSyntaxError,
            "Spread syntax '**' found outside of a dictionary",
        ):
            _, attrs = parse_tag('component list=["a", "b", **my_list]', None)

        with self.assertRaisesMessage(
            TemplateSyntaxError,
            "Spread syntax '...' found in list. It must be used on tag attributes only",
        ):
            _, attrs = parse_tag('component list=["a", "b", ...my_list]', None)

        with self.assertRaisesMessage(
            TemplateSyntaxError,
            "Spread syntax '*' found outside of a list",
        ):
            _, attrs = parse_tag("component *attrs", None)

        with self.assertRaisesMessage(
            TemplateSyntaxError,
            "Spread syntax '**' found outside of a dictionary",
        ):
            _, attrs = parse_tag("component **attrs", None)

        with self.assertRaisesMessage(
            TemplateSyntaxError,
            "Spread syntax '*' found outside of a list",
        ):
            _, attrs = parse_tag("component key=*attrs", None)

        with self.assertRaisesMessage(
            TemplateSyntaxError,
            "Spread syntax '**' found outside of a dictionary",
        ):
            _, attrs = parse_tag("component key=**attrs", None)

    # Test that one cannot do `key=...{"a": "b"}`
    def test_spread_onto_key(self):
        with self.assertRaisesMessage(
            TemplateSyntaxError,
            "Spread syntax '...' cannot follow a key ('key=...attrs')",
        ):
            _, attrs = parse_tag('component key=...{"a": "b"}', None)

        with self.assertRaisesMessage(
            TemplateSyntaxError,
            "Spread syntax '...' cannot follow a key ('key=...attrs')",
        ):
            _, attrs = parse_tag('component key=...["a", "b"]', None)

        with self.assertRaisesMessage(
            TemplateSyntaxError,
            "Spread syntax '...' cannot follow a key ('key=...attrs')",
        ):
            _, attrs = parse_tag("component key=...attrs", None)

    def test_spread_dict_literal_nested(self):
        _, attrs = parse_tag('component { **{"key": val2}, "key": val1 }', None)

        expected_attrs = [
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="component", quoted=None, spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                    spread=None,
                    meta={},
                ),
                start_index=0,
            ),
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="dict",
                    spread=None,
                    parser=None,
                    meta={},
                    entries=[
                        TagValueStruct(
                            type="dict",
                            spread="**",
                            meta={},
                            parser=None,
                            entries=[
                                TagValue(
                                    parts=[
                                        TagValuePart(
                                            value="key",
                                            quoted='"',
                                            spread=None,
                                            translation=False,
                                            filter=None,
                                        )
                                    ]
                                ),
                                TagValue(
                                    parts=[
                                        TagValuePart(
                                            value="val2",
                                            quoted=None,
                                            spread=None,
                                            translation=False,
                                            filter=None,
                                        )
                                    ]
                                ),
                            ],
                        ),
                        TagValue(
                            parts=[TagValuePart(value="key", quoted='"', spread=None, translation=False, filter=None)]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(value="val1", quoted=None, spread=None, translation=False, filter=None)
                            ]
                        ),
                    ],
                ),
                start_index=10,
            ),
        ]
        self.assertEqual(attrs, expected_attrs)

        self.assertEqual(
            [a.serialize() for a in attrs],
            [
                "component",
                '{**{"key": val2}, "key": val1}',
            ],
        )

    def test_spread_dict_literal_as_attribute(self):
        _, attrs = parse_tag('component ...{"key": val2}', None)

        expected_attrs = [
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="component", quoted=None, spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                ),
                start_index=0,
            ),
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="dict",
                    spread="...",
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[TagValuePart(value="key", quoted='"', spread=None, translation=False, filter=None)]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(value="val2", quoted=None, spread=None, translation=False, filter=None)
                            ]
                        ),
                    ],
                ),
                start_index=10,
            ),
        ]
        self.assertEqual(attrs, expected_attrs)

        self.assertEqual(
            [a.serialize() for a in attrs],
            [
                "component",
                '...{"key": val2}',
            ],
        )

    def test_spread_list_literal_nested(self):
        _, attrs = parse_tag("component [ *[val1], val2 ]", None)

        expected_attrs = [
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="component", quoted=None, spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                    spread=None,
                    meta={},
                ),
                start_index=0,
            ),
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="list",
                    spread=None,
                    parser=None,
                    meta={},
                    entries=[
                        TagValueStruct(
                            type="list",
                            spread="*",
                            meta={},
                            parser=None,
                            entries=[
                                TagValue(
                                    parts=[
                                        TagValuePart(
                                            value="val1",
                                            quoted=None,
                                            spread=None,
                                            translation=False,
                                            filter=None,
                                        )
                                    ]
                                ),
                            ],
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(value="val2", quoted=None, spread=None, translation=False, filter=None)
                            ]
                        ),
                    ],
                ),
                start_index=10,
            ),
        ]
        self.assertEqual(attrs, expected_attrs)

        self.assertEqual(
            [a.serialize() for a in attrs],
            [
                "component",
                "[*[val1], val2]",
            ],
        )

    def test_spread_list_literal_as_attribute(self):
        _, attrs = parse_tag("component ...[val1]", None)

        expected_attrs = [
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="component", quoted=None, spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                    spread=None,
                    meta={},
                ),
                start_index=0,
            ),
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="list",
                    spread="...",
                    parser=None,
                    meta={},
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value="val1", quoted=None, spread=None, translation=False, filter=None)
                            ]
                        ),
                    ],
                ),
                start_index=10,
            ),
        ]
        self.assertEqual(attrs, expected_attrs)

        self.assertEqual(
            [a.serialize() for a in attrs],
            [
                "component",
                "...[val1]",
            ],
        )

    def test_dynamic_expressions(self):
        _, attrs = parse_tag("component '{% lorem w 4 %}'", None)

        expected_attrs = [
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="component", quoted=None, spread=None, translation=False, filter=None
                                )  # noqa: E501
                            ],
                        )
                    ],
                    spread=None,
                    meta={},
                    parser=None,
                ),
                start_index=0,
            ),
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="{% lorem w 4 %}", quoted="'", spread=None, translation=False, filter=None
                                )
                            ],
                        )
                    ],
                    spread=None,
                    meta={},
                    parser=None,
                ),
                start_index=10,
            ),
        ]
        self.assertEqual(attrs, expected_attrs)

    def test_dynamic_expressions_in_dict(self):
        _, attrs = parse_tag('component { "key": "{% lorem w 4 %}" }', None)

        expected_attrs = [
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="component", quoted=None, spread=None, translation=False, filter=None
                                )  # noqa: E501
                            ]
                        )
                    ],
                    spread=None,
                    meta={},
                    parser=None,
                ),
                start_index=0,
            ),
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="dict",
                    entries=[
                        TagValue(
                            parts=[TagValuePart(value="key", quoted='"', spread=None, translation=False, filter=None)]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="{% lorem w 4 %}", quoted='"', spread=None, translation=False, filter=None
                                )  # noqa: E501
                            ]
                        ),
                    ],
                    spread=None,
                    meta={},
                    parser=None,
                ),
                start_index=10,
            ),
        ]
        self.assertEqual(attrs, expected_attrs)

    def test_dynamic_expressions_in_list(self):
        _, attrs = parse_tag("component [ '{% lorem w 4 %}' ]", None)

        expected_attrs = [
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="component", quoted=None, spread=None, translation=False, filter=None
                                )  # noqa: E501
                            ],
                        )
                    ],
                    spread=None,
                    meta={},
                    parser=None,
                ),
                start_index=0,
            ),
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="list",
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="{% lorem w 4 %}", quoted="'", spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                    spread=None,
                    meta={},
                    parser=None,
                ),
                start_index=10,
            ),
        ]
        self.assertEqual(attrs, expected_attrs)

    def test_comments(self):
        _, attrs = parse_tag("component {# comment #} val", None)

        expected_attrs = [
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type='simple',
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value='component', quoted=None, spread=None, translation=False, filter=None)
                            ],
                            compiled=None,
                        )
                    ],
                    spread=None,
                    meta={},
                    parser=None,
                ),
                start_index=0
            ),
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    entries=[
                        TagValue(
                            parts=[TagValuePart(value="val", quoted=None, spread=None, translation=False, filter=None)]
                        )
                    ],
                    spread=None,
                    meta={},
                    parser=None,
                ),
                start_index=24,
            ),
        ]

        self.assertEqual(attrs, expected_attrs)

    def test_comments_within_list(self):
        _, attrs = parse_tag("component [ *[val1], {# comment #} val2 ]", None)

        expected_attrs = [
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type='simple',
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value='component', quoted=None, spread=None, translation=False, filter=None)
                            ],
                        )
                    ],
                    spread=None,
                    meta={},
                    parser=None,
                ),
                start_index=0
            ),
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type='list',
                    entries=[
                        TagValueStruct(
                            type="list",
                            entries=[
                                TagValue(
                                    parts=[
                                        TagValuePart(value="val1", quoted=None, spread=None, translation=False, filter=None)
                                    ],
                                )
                            ],
                            spread="*",
                            meta={},
                            parser=None,
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(value="val2", quoted=None, spread=None, translation=False, filter=None)
                            ]
                        ),
                    ],
                    spread=None,
                    meta={},
                    parser=None,
                ),
                start_index=10,
            ),
        ]

        self.assertEqual(attrs, expected_attrs)

    def test_comments_within_dict(self):
        _, attrs = parse_tag('component { "key": "123" {# comment #} }', None)

        expected_attrs = [
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type='simple',
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value='component', quoted=None, spread=None, translation=False, filter=None)
                            ],
                        )
                    ],
                    spread=None,
                    meta={},
                    parser=None
                ),
                start_index=0
            ),
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type='dict',
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value='key', quoted='"', spread=None, translation=False, filter=None)
                            ]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(value='123', quoted='"', spread=None, translation=False, filter=None)
                            ]
                        )
                    ],
                    spread=None,
                    meta={},
                    parser=None,
                ),
                start_index=10
            )
        ]

        self.assertEqual(attrs, expected_attrs)
