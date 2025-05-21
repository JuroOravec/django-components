use lazy_static;
use pest::Parser;
use pest_derive::Parser;
use pyo3::prelude::*;
use regex;
use thiserror::Error;

#[derive(Parser)]
#[grammar = "grammar.pest"]
pub struct TagParser;

/// Top-level tag attribute, e.g. `key=my_var` or without key like `my_var|filter`
#[pyclass]
#[derive(Debug, PartialEq, Clone)]
pub struct TagAttr {
    #[pyo3(get)]
    pub key: Option<TagToken>,
    #[pyo3(get)]
    pub value: TagValue,

    /// Start index (incl. filters)
    #[pyo3(get)]
    pub start_index: usize,
    /// End index (incl. filters)
    #[pyo3(get)]
    pub end_index: usize,
    /// Line and column (incl. filters)
    #[pyo3(get)]
    pub line_col: (usize, usize),
}

#[pyclass]
#[derive(Debug, PartialEq, Clone)]
pub enum ValueKind {
    List,
    Dict,
    Int,
    Float,
    Variable,
    Expression,
    Translation,
    String,
}

#[pymethods]
impl ValueKind {
    fn __str__(&self) -> String {
        match self {
            ValueKind::List => "list".to_string(),
            ValueKind::Dict => "dict".to_string(),
            ValueKind::Int => "int".to_string(),
            ValueKind::Float => "float".to_string(),
            ValueKind::Variable => "variable".to_string(),
            ValueKind::Expression => "expression".to_string(),
            ValueKind::Translation => "translation".to_string(),
            ValueKind::String => "string".to_string(),
        }
    }
}

/// Metadata of the matched token
#[pyclass]
#[derive(Debug, PartialEq, Clone)]
pub struct TagToken {
    /// String value of the token (excl. filters and spread)
    #[pyo3(get)]
    pub token: String,
    /// Start index (excl. filters and spread)
    #[pyo3(get)]
    pub start_index: usize,
    /// End index (excl. filters and spread)
    #[pyo3(get)]
    pub end_index: usize,
    /// Line and column (excl. filters and spread)
    #[pyo3(get)]
    pub line_col: (usize, usize),
}

#[pyclass]
#[derive(Debug, PartialEq, Clone)]
pub struct TagValue {
    /// Position and string value of the value (excl. filters and spread)
    ///
    /// NOTE: If this TagValue has NO filters, position and index in `token` are the same
    ///       as `start_index`, `end_index` and `line_col` defined directly on `TagValue`.
    #[pyo3(get)]
    pub token: TagToken,
    /// Children of this TagValue - e.g. list items like `[1, 2, 3]` or dict key-value entries like `{"key": "value"}`
    #[pyo3(get)]
    pub children: Vec<TagValue>,

    #[pyo3(get)]
    pub kind: ValueKind,
    #[pyo3(get)]
    pub spread: Option<String>,
    #[pyo3(get)]
    pub filters: Vec<TagValueFilter>,

    /// Start index (incl. filters and spread)
    #[pyo3(get)]
    pub start_index: usize,
    /// End index (incl. filters and spread)
    #[pyo3(get)]
    pub end_index: usize,
    /// Line and column (incl. filters and spread)
    #[pyo3(get)]
    pub line_col: (usize, usize),
}

#[pyclass]
#[derive(Debug, PartialEq, Clone)]
pub struct TagValueFilter {
    /// Token of the filter, e.g. `filter`
    #[pyo3(get)]
    pub token: TagToken,
    /// Argument of the filter, e.g. `my_var`
    #[pyo3(get)]
    pub arg: Option<TagValue>,

    /// Start index (incl. `|`)
    #[pyo3(get)]
    pub start_index: usize,
    /// End index (incl. `|`)
    #[pyo3(get)]
    pub end_index: usize,
    /// Line and column (incl. `|`)
    #[pyo3(get)]
    pub line_col: (usize, usize),
}

#[pyclass]
#[derive(Debug, PartialEq, Clone)]
pub struct TagValueFilterArg {
    /// Value of the filter argument, e.g. `my_var` in `var|filter:my_var`
    #[pyo3(get)]
    pub value: TagValue,

    /// Start index (incl. `:`)
    #[pyo3(get)]
    pub start_index: usize,
    /// End index (incl. `:`)
    #[pyo3(get)]
    pub end_index: usize,
    /// Line and column (incl. `:`)
    #[pyo3(get)]
    pub line_col: (usize, usize),
}

#[derive(Error, Debug)]
pub enum ParseError {
    #[error("Pest parser error: {0}")]
    PestError(#[from] pest::error::Error<Rule>),
    #[error("Invalid key: {0}")]
    InvalidKey(String),
}

// Add conversion from our ParseError to PyErr
impl From<ParseError> for pyo3::PyErr {
    fn from(err: ParseError) -> Self {
        pyo3::exceptions::PyValueError::new_err(err.to_string())
    }
}

impl TagParser {
    pub fn parse_tag(input: &str) -> Result<Vec<TagAttr>, ParseError> {
        let pairs = Self::parse(Rule::tag, input)?;
        let mut attributes = Vec::new();

        // Process the tag rule
        for pair in pairs {
            if pair.as_rule() == Rule::tag {
                // Process each attribute inside the tag
                for inner_pair in pair.into_inner() {
                    if inner_pair.as_rule() == Rule::attribute {
                        attributes.push(Self::process_attribute(inner_pair)?);
                    }
                }
            }
        }

        Ok(attributes)
    }

    fn process_attribute(attr_pair: pest::iterators::Pair<Rule>) -> Result<TagAttr, ParseError> {
        let start_index = attr_pair.as_span().start();
        let line_col = attr_pair.line_col();

        let attr_str = attr_pair.as_str().to_string(); // Clone the string before moving the pair
        let mut inner_pairs = attr_pair.into_inner().peekable();

        // println!("Processing attribute: {:?}", attr_str);
        // if let Some(next_rule) = inner_pairs.peek() {
        //     println!("Next rule: {:?}", next_rule.as_rule());
        // }

        // Check if this is a key-value pair or just a value
        match inner_pairs.peek().map(|p| p.as_rule()) {
            Some(Rule::key) => {
                // println!("Found key-value pair");

                // Key
                let key_pair = inner_pairs.next().unwrap();
                let key_value = key_pair.as_str().to_string();
                let key_end_index = key_pair.as_span().end();

                // Value
                let value_pair = inner_pairs
                    .filter(|p| p.as_rule() == Rule::filtered_value)
                    .next()
                    .ok_or_else(|| {
                        ParseError::InvalidKey(format!("Missing value for key: {}", key_value))
                    })?;

                let value = Self::process_filtered_value(value_pair)?;
                let value_end_index = value.end_index;

                Ok(TagAttr {
                    key: Some(TagToken {
                        token: key_value,
                        start_index,
                        end_index: key_end_index,
                        line_col,
                    }),
                    value,
                    start_index,
                    end_index: value_end_index,
                    line_col,
                })
            }
            Some(Rule::spread_value) => {
                // println!("Found spread value");

                // Spread value form
                let spread_value = inner_pairs.next().unwrap();

                // println!("Spread value: {:?}", spread_value.as_str());
                // println!("Spread value rule: {:?}", spread_value.as_rule());

                // Get the value part after the ... operator
                let mut value_pairs = spread_value.into_inner();
                let value_pair = value_pairs.next().unwrap();

                // println!("Value pair: {:?}", value_pair.as_str());
                // println!("Value pair rule: {:?}", value_pair.as_rule());

                // Process the value part
                let mut value = match value_pair.as_rule() {
                    Rule::filtered_value => Self::process_filtered_value(value_pair)?,
                    other => {
                        return Err(ParseError::InvalidKey(format!(
                            "Expected filtered_value after spread operator, got {:?}",
                            other
                        )))
                    }
                };

                // Update indices
                value.spread = Some("...".to_string());
                value.start_index -= 3;
                value.line_col = (value.line_col.0, value.line_col.1 - 3);

                let end_index = value.end_index;

                Ok(TagAttr {
                    key: None,
                    value,
                    start_index,
                    end_index,
                    line_col,
                })
            }
            Some(Rule::filtered_value) => {
                // println!("Found filtered value");

                let value_pair = inner_pairs.next().unwrap();
                let value = Self::process_filtered_value(value_pair)?;
                let end_index = value.end_index;

                Ok(TagAttr {
                    key: None,
                    value,
                    start_index,
                    end_index,
                    line_col,
                })
            }
            _ => unreachable!("Invalid attribute structure"),
        }
    }

    // Filtered value means that:
    // 1. It is "value" - meaning that it is the same as "basic value" + list and dict
    // 2. It may have a filter chain after it
    //
    // E.g. `my_var`, `my_var|filter`, `[1, 2, 3]|filter1|filter2` are all filtered values
    fn process_filtered_value(
        value_pair: pest::iterators::Pair<Rule>,
    ) -> Result<TagValue, ParseError> {
        // println!("Processing value: {:?}", value_pair.as_str());
        // println!("Rule: {:?}", value_pair.as_rule());

        let total_span = value_pair.as_span();
        let total_start_index = total_span.start();
        let total_end_index = total_span.end();
        let total_line_col = value_pair.line_col();

        let mut inner_pairs = value_pair.into_inner();

        // Get the main value part
        let value_part = inner_pairs.next().unwrap();

        // println!("Value part rule: {:?}", value_part.as_rule());
        // println!("Value part text: {:?}", value_part.as_str());
        // println!("Inner pairs of value_part:");
        // for pair in value_part.clone().into_inner() {
        //     println!("  Rule: {:?}, Text: {:?}", pair.as_rule(), pair.as_str());
        // }

        let mut result = match value_part.as_rule() {
            Rule::value => {
                // Get the actual value (stripping the * if present)
                let mut inner_pairs = value_part.clone().into_inner();
                let inner_value = inner_pairs.next().unwrap();

                // println!(
                //     "  Inner value rule: {:?}, Text: {:?}",
                //     inner_value.as_rule(),
                //     inner_value.as_str()
                // );

                // Process the value
                match inner_value.as_rule() {
                    Rule::list => {
                        let list_str = inner_value.as_str().to_string();

                        // println!("  Processing list: {:?}", list_str);

                        let span = inner_value.as_span();
                        let token_start_index = span.start();
                        let token_end_index = span.end();
                        let token_line_col = inner_value.line_col();

                        let children = Self::process_list(inner_value)?;

                        Ok(TagValue {
                            token: TagToken {
                                token: list_str,
                                start_index: token_start_index,
                                end_index: token_end_index,
                                line_col: token_line_col,
                            },
                            spread: None,
                            filters: vec![],
                            kind: ValueKind::List,
                            children,
                            start_index: total_start_index,
                            end_index: total_end_index,
                            line_col: total_line_col,
                        })
                    }
                    Rule::dict => {
                        let dict_str = inner_value.as_str().to_string();

                        // println!("  Processing dict: {:?}", dict_str);

                        let span = inner_value.as_span();
                        let token_start_index = span.start();
                        let token_end_index = span.end();
                        let token_line_col = inner_value.line_col();

                        let children = Self::process_dict(inner_value)?;

                        Ok(TagValue {
                            token: TagToken {
                                token: dict_str,
                                start_index: token_start_index,
                                end_index: token_end_index,
                                line_col: token_line_col,
                            },
                            spread: None,
                            filters: vec![],
                            kind: ValueKind::Dict,
                            children,
                            start_index: total_start_index,
                            end_index: total_end_index,
                            line_col: total_line_col,
                        })
                    }
                    _ => {
                        let mut result = Self::process_basic_value(inner_value);

                        // Update indices
                        result = result.map(|mut tag_value| {
                            tag_value.start_index = total_start_index;
                            tag_value.end_index = total_end_index;
                            tag_value.line_col = total_line_col;
                            tag_value
                        });

                        result
                    }
                }
            }
            other => Err(ParseError::InvalidKey(format!(
                "Expected value, got {:?}",
                other
            ))),
        };

        // Process any filters
        if let Some(filter_chain) = inner_pairs.next() {
            result = result.and_then(|mut tag_value| {
                tag_value.filters = Self::process_filters(filter_chain)?;
                Ok(tag_value)
            });
        }

        result
    }

    // Basic value is a string, number, or i18n string
    //
    // NOTE: Basic value is NOT a filtered value
    //
    // E.g. `my_var`, `42`, `"hello world"`, `_("hello world")` are all basic values
    fn process_basic_value(
        value_pair: pest::iterators::Pair<Rule>,
    ) -> Result<TagValue, ParseError> {
        // println!(
        //     "Processing basic value: Rule={:?}, Text={:?}",
        //     value_pair.as_rule(),
        //     value_pair.as_str()
        // );

        let start_index = value_pair.as_span().start();
        let end_index = value_pair.as_span().end();
        let line_col = value_pair.line_col();

        // Determine the value kind, so that downstream processing doesn't need to
        let text = value_pair.as_str();
        let kind = match value_pair.as_rule() {
            Rule::i18n_string => ValueKind::Translation,
            Rule::string_literal => {
                if Self::has_dynamic_expression(text) {
                    ValueKind::Expression
                } else {
                    ValueKind::String
                }
            }
            Rule::int => ValueKind::Int,
            Rule::float => ValueKind::Float,
            Rule::variable => ValueKind::Variable,
            _ => unreachable!("Invalid basic value {:?}", value_pair.as_rule()),
        };

        // If this is an i18n string, remove the whitespace between `_()` and the text
        let mut text = text.to_string();
        if kind == ValueKind::Translation {
            // Find the first occurrence of either quote type
            let single_quote_pos = text.find('\'');
            let double_quote_pos = text.find('"');

            // Select the quote char that appears first
            let quote_char = match (single_quote_pos, double_quote_pos) {
                // If both quotes are present, use the one that appears first
                (Some(s), Some(d)) if s < d => '\'',
                (Some(_), Some(_)) => '"',
                // If only one quote is present, use it
                (Some(_), None) => '\'',
                (None, Some(_)) => '"',
                // If no quotes are present, return an error
                (None, None) => {
                    return Err(ParseError::InvalidKey(
                        "No quotes found in i18n string".to_string(),
                    ))
                }
            };

            let start = text.find(quote_char).unwrap();
            let end = text.rfind(quote_char).unwrap();
            let quoted_part = &text[start..=end];
            text = format!("_({})", quoted_part);
        }

        Ok(TagValue {
            token: TagToken {
                token: text.to_string(),
                start_index,
                end_index,
                line_col,
            },
            spread: None,
            filters: vec![],
            kind,
            children: vec![],
            line_col,
            start_index,
            end_index,
        })
    }

    // Process a basic value that may have filters
    fn process_filtered_basic_value(
        value_pair: pest::iterators::Pair<Rule>,
    ) -> Result<TagValue, ParseError> {
        // println!(
        //     "Processing filtered basic value: Rule={:?}, Text={:?}",
        //     value_pair.as_rule(),
        //     value_pair.as_str()
        // );

        let total_span = value_pair.as_span();
        let total_start_index = total_span.start();
        let total_end_index = total_span.end();
        let total_line_col = value_pair.line_col();

        let mut inner_pairs = value_pair.into_inner();
        let basic_value = inner_pairs.next().unwrap();
        let mut result = Self::process_basic_value(basic_value);

        // Update indices
        result = result.map(|mut tag_value| {
            tag_value.start_index = total_start_index;
            tag_value.end_index = total_end_index;
            tag_value.line_col = total_line_col;
            tag_value
        });

        // Process any filters
        if let Some(filter_chain) = inner_pairs.next() {
            result = result.and_then(|mut tag_value| {
                tag_value.filters = Self::process_filters(filter_chain)?;
                Ok(tag_value)
            });
        }

        result
    }

    fn process_list(inner_value: pest::iterators::Pair<Rule>) -> Result<Vec<TagValue>, ParseError> {
        let mut items = Vec::new();
        for item in inner_value.into_inner() {
            // println!(
            //     "    ALL list tokens: Rule={:?}, Text={:?}",
            //     item.as_rule(),
            //     item.as_str()
            // );

            if item.as_rule() == Rule::list_item {
                let has_spread = item.as_str().starts_with('*');

                // println!("      List item inner tokens:");

                for inner in item.clone().into_inner() {
                    // println!(
                    //     "        Rule={:?}, Text={:?}",
                    //     inner.as_rule(),
                    //     inner.as_str()
                    // );

                    if inner.as_rule() == Rule::filtered_value {
                        let mut tag_value = Self::process_filtered_value(inner)?;

                        // Update indices
                        if has_spread {
                            tag_value.spread = Some("*".to_string());
                            tag_value.start_index -= 1;
                            tag_value.line_col = (tag_value.line_col.0, tag_value.line_col.1 - 1);
                        }
                        items.push(tag_value);
                    }
                }
            }
        }
        Ok(items)
    }

    fn process_dict(dict_pair: pest::iterators::Pair<Rule>) -> Result<Vec<TagValue>, ParseError> {
        let mut items = Vec::new();
        for item in dict_pair.into_inner() {
            // println!(
            //     "    ALL dict tokens: Rule={:?}, Text={:?}",
            //     item.as_rule(),
            //     item.as_str()
            // );

            match item.as_rule() {
                Rule::dict_item_pair => {
                    let mut inner = item.into_inner();
                    let key_pair = inner.next().unwrap();
                    let mut value_pair = inner.next().unwrap();

                    // Skip comments in dict items
                    while value_pair.as_rule() == Rule::COMMENT {
                        value_pair = inner.next().unwrap();
                    }

                    // println!(
                    //     "    dict_item_pair: Key={:?}, Value={:?}",
                    //     key_pair.as_str(),
                    //     value_pair.as_str()
                    // );

                    let key = Self::process_filtered_basic_value(key_pair)?;
                    let value = Self::process_filtered_value(value_pair)?;

                    // println!(
                    //     "    dict_item_pair(parsed): Key={:?}, Value={:?}",
                    //     key.token, value.token
                    // );

                    // Check that key is not a list or dict
                    match key.kind {
                        ValueKind::List | ValueKind::Dict => {
                            return Err(ParseError::InvalidKey(
                                "Dictionary keys cannot be lists or dictionaries".to_string(),
                            ));
                        }
                        _ => {}
                    }
                    items.push(key);
                    items.push(value);
                }
                Rule::dict_item_spread => {
                    let mut inner = item.into_inner();
                    let mut value_pair = inner.next().unwrap();

                    // println!("    dict_item_spread: Value={:?}", inner.as_str());

                    // Skip comments in dict items
                    while value_pair.as_rule() == Rule::COMMENT {
                        value_pair = inner.next().unwrap();
                    }

                    let mut value = Self::process_filtered_value(value_pair)?;

                    // Update indices
                    value.spread = Some("**".to_string());
                    value.start_index -= 2;
                    value.line_col = (value.line_col.0, value.line_col.1 - 2);

                    // println!("    dict_item_spread(parsed): Value={:?}", value.token);

                    items.push(value);
                }
                Rule::COMMENT => {}
                _ => unreachable!("Invalid dictionary item {:?}", item.as_rule()),
            }
        }
        Ok(items)
    }

    fn process_filters(
        filter_chain: pest::iterators::Pair<Rule>,
    ) -> Result<Vec<TagValueFilter>, ParseError> {
        // Return error if not a filter chain rule
        if filter_chain.as_rule() != Rule::filter_chain
            && filter_chain.as_rule() != Rule::filter_chain_noarg
        {
            return Err(ParseError::InvalidKey(format!(
                "Expected filter chain, got {:?}",
                filter_chain.as_rule()
            )));
        }

        let mut filters = Vec::new();

        // println!(
        //     "Found rule {:?}, processing filters...",
        //     filter_chain.as_rule()
        // );

        for filter in filter_chain.into_inner() {
            // Skip comments
            if filter.as_rule() == Rule::COMMENT {
                continue;
            }

            // println!("Processing filter: {:?}", filter.as_str());

            if filter.as_rule() != Rule::filter && filter.as_rule() != Rule::filter_noarg {
                return Err(ParseError::InvalidKey(format!(
                    "Expected filter, got {:?}",
                    filter.as_rule()
                )));
            }

            let filter_span = filter.as_span();
            let filter_start_index = filter_span.start();
            let filter_end_index = filter_span.end();
            let filter_line_col = filter.line_col();

            // Find the filter name (skipping the pipe token)
            let mut filter_parts = filter.into_inner();
            let filter_pair = filter_parts
                .find(|p| p.as_rule() == Rule::filter_name)
                .unwrap();
            let filter_name = filter_pair.as_str().to_string();
            let token_start_index = filter_pair.as_span().start();
            let token_end_index = filter_pair.as_span().end();
            let token_line_col = filter_pair.line_col();

            // println!("Found filter name: {:?}", filter_name);

            let filter_arg = if let Some(arg_part) =
                filter_parts.find(|p| p.as_rule() == Rule::filter_arg_part)
            {
                // Position, includeing the `:`
                let arg_span = arg_part.as_span();
                let arg_start_index = arg_span.start();
                let arg_end_index = arg_span.end();
                let arg_line_col = arg_part.line_col();

                let arg_value_pair: pest::iterators::Pair<'_, Rule> = arg_part
                    .into_inner()
                    .find(|p| p.as_rule() == Rule::filter_arg)
                    .unwrap();

                // Process the filter argument as a TagValue
                let mut result = Self::process_filtered_value(arg_value_pair)?;

                // Update indices
                result.start_index = arg_start_index;
                result.end_index = arg_end_index;
                result.line_col = arg_line_col;
                Some(result)
            } else {
                None
            };

            filters.push(TagValueFilter {
                arg: filter_arg,
                token: TagToken {
                    token: filter_name,
                    start_index: token_start_index,
                    end_index: token_end_index,
                    line_col: token_line_col,
                },
                start_index: filter_start_index,
                end_index: filter_end_index,
                line_col: filter_line_col,
            });

            // println!("Added filter to chain: {:?}", filters.last().unwrap());
        }

        // println!(
        //     "Completed processing filter chain, returning {:?} filters",
        //     filters.len()
        // );

        Ok(filters)
    }

    fn has_dynamic_expression(s: &str) -> bool {
        // Don't check for dynamic expressions in i18n strings
        if s.starts_with("_(") {
            return false;
        }

        // Check for any of the Django template tags with their closing tags
        // The pattern ensures that:
        // 1. Opening and closing tags are properly paired
        // 2. Tags are in the correct order (no closing before opening)
        lazy_static::lazy_static! {
            static ref VAR_TAG: regex::Regex = regex::Regex::new(r"\{\{.*?\}\}").unwrap();
            static ref BLOCK_TAG: regex::Regex = regex::Regex::new(r"\{%.*?%\}").unwrap();
            static ref COMMENT_TAG: regex::Regex = regex::Regex::new(r"\{#.*?#\}").unwrap();
        }

        VAR_TAG.is_match(s) || BLOCK_TAG.is_match(s) || COMMENT_TAG.is_match(s)
    }
}

#[cfg(test)]
mod tests {
    use std::vec;

    use super::*;

    #[test]
    fn test_arg_single_variable() {
        // Test simple variable name
        let input = "val";
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result,
            vec![TagAttr {
                key: None,
                value: TagValue {
                    token: TagToken {
                        token: "val".to_string(),
                        start_index: 0,
                        end_index: 3,
                        line_col: (1, 1),
                    },
                    children: vec![],
                    spread: None,
                    filters: vec![],
                    kind: ValueKind::Variable,
                    start_index: 0,
                    end_index: 3,
                    line_col: (1, 1),
                },
                start_index: 0,
                end_index: 3,
                line_col: (1, 1),
            }]
        );
    }

    #[test]
    fn test_arg_single_variable_with_dots() {
        // Test variable with dots
        let input = "my.nested.value";
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result,
            vec![TagAttr {
                key: None,
                value: TagValue {
                    token: TagToken {
                        token: "my.nested.value".to_string(),
                        start_index: 0,
                        end_index: 15,
                        line_col: (1, 1),
                    },
                    children: vec![],
                    spread: None,
                    filters: vec![],
                    kind: ValueKind::Variable,
                    start_index: 0,
                    end_index: 15,
                    line_col: (1, 1),
                },
                start_index: 0,
                end_index: 15,
                line_col: (1, 1),
            }]
        );
    }

    #[test]
    fn test_arg_single_number() {
        let input = "42";
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result,
            vec![TagAttr {
                key: None,
                value: TagValue {
                    token: TagToken {
                        token: "42".to_string(),
                        start_index: 0,
                        end_index: 2,
                        line_col: (1, 1),
                    },
                    children: vec![],
                    spread: None,
                    filters: vec![],
                    kind: ValueKind::Int,
                    start_index: 0,
                    end_index: 2,
                    line_col: (1, 1),
                },
                start_index: 0,
                end_index: 2,
                line_col: (1, 1),
            }]
        );

        let input = "001";
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result,
            vec![TagAttr {
                key: None,
                value: TagValue {
                    token: TagToken {
                        token: "001".to_string(),
                        start_index: 0,
                        end_index: 3,
                        line_col: (1, 1),
                    },
                    children: vec![],
                    spread: None,
                    filters: vec![],
                    kind: ValueKind::Int,
                    start_index: 0,
                    end_index: 3,
                    line_col: (1, 1),
                },
                start_index: 0,
                end_index: 3,
                line_col: (1, 1),
            }]
        );
    }

    #[test]
    fn test_arg_single_number_with_decimal() {
        let input = "-1.5";
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result,
            vec![TagAttr {
                key: None,
                value: TagValue {
                    token: TagToken {
                        token: "-1.5".to_string(),
                        start_index: 0,
                        end_index: 4,
                        line_col: (1, 1),
                    },
                    children: vec![],
                    spread: None,
                    filters: vec![],
                    kind: ValueKind::Float,
                    start_index: 0,
                    end_index: 4,
                    line_col: (1, 1),
                },
                start_index: 0,
                end_index: 4,
                line_col: (1, 1),
            }]
        );

        let input = "+2.";
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result,
            vec![TagAttr {
                key: None,
                value: TagValue {
                    token: TagToken {
                        token: "+2.".to_string(),
                        start_index: 0,
                        end_index: 3,
                        line_col: (1, 1),
                    },
                    children: vec![],
                    spread: None,
                    filters: vec![],
                    kind: ValueKind::Float,
                    start_index: 0,
                    end_index: 3,
                    line_col: (1, 1),
                },
                start_index: 0,
                end_index: 3,
                line_col: (1, 1),
            }]
        );

        let input = ".3";
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result,
            vec![TagAttr {
                key: None,
                value: TagValue {
                    token: TagToken {
                        token: ".3".to_string(),
                        start_index: 0,
                        end_index: 2,
                        line_col: (1, 1),
                    },
                    children: vec![],
                    spread: None,
                    filters: vec![],
                    kind: ValueKind::Float,
                    start_index: 0,
                    end_index: 2,
                    line_col: (1, 1),
                },
                start_index: 0,
                end_index: 2,
                line_col: (1, 1),
            }]
        );
    }

    #[test]
    fn test_arg_single_number_scientific() {
        let input = "-1.2e2";
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result,
            vec![TagAttr {
                key: None,
                value: TagValue {
                    token: TagToken {
                        token: "-1.2e2".to_string(),
                        start_index: 0,
                        end_index: 6,
                        line_col: (1, 1),
                    },
                    children: vec![],
                    spread: None,
                    filters: vec![],
                    kind: ValueKind::Float,
                    start_index: 0,
                    end_index: 6,
                    line_col: (1, 1),
                },
                start_index: 0,
                end_index: 6,
                line_col: (1, 1),
            }]
        );

        let input = ".2e-02";
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result,
            vec![TagAttr {
                key: None,
                value: TagValue {
                    token: TagToken {
                        token: ".2e-02".to_string(),
                        start_index: 0,
                        end_index: 6,
                        line_col: (1, 1),
                    },
                    children: vec![],
                    spread: None,
                    filters: vec![],
                    kind: ValueKind::Float,
                    start_index: 0,
                    end_index: 6,
                    line_col: (1, 1),
                },
                start_index: 0,
                end_index: 6,
                line_col: (1, 1),
            }]
        );

        let input = "20.e+02";
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result,
            vec![TagAttr {
                key: None,
                value: TagValue {
                    token: TagToken {
                        token: "20.e+02".to_string(),
                        start_index: 0,
                        end_index: 7,
                        line_col: (1, 1),
                    },
                    children: vec![],
                    spread: None,
                    filters: vec![],
                    kind: ValueKind::Float,
                    start_index: 0,
                    end_index: 7,
                    line_col: (1, 1),
                },
                start_index: 0,
                end_index: 7,
                line_col: (1, 1),
            }]
        );
    }

    #[test]
    fn test_arg_single_quoted_string() {
        // Test single quoted string
        let input = "'hello world'";
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result,
            vec![TagAttr {
                key: None,
                value: TagValue {
                    token: TagToken {
                        token: "'hello world'".to_string(),
                        start_index: 0,
                        end_index: 13,
                        line_col: (1, 1),
                    },
                    children: vec![],
                    spread: None,
                    filters: vec![],
                    kind: ValueKind::String,
                    start_index: 0,
                    end_index: 13,
                    line_col: (1, 1),
                },
                start_index: 0,
                end_index: 13,
                line_col: (1, 1),
            }]
        );
    }

    #[test]
    fn test_arg_single_double_quoted_string() {
        // Test double quoted string
        let input = "\"hello world\"";
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result,
            vec![TagAttr {
                key: None,
                value: TagValue {
                    token: TagToken {
                        token: "\"hello world\"".to_string(),
                        start_index: 0,
                        end_index: 13,
                        line_col: (1, 1),
                    },
                    children: vec![],
                    spread: None,
                    filters: vec![],
                    kind: ValueKind::String,
                    start_index: 0,
                    end_index: 13,
                    line_col: (1, 1)
                },
                start_index: 0,
                end_index: 13,
                line_col: (1, 1),
            }]
        );
    }

    #[test]
    fn test_arg_single_i18n_string() {
        // Test i18n string
        let input = "_('hello world')";
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result,
            vec![TagAttr {
                key: None,
                value: TagValue {
                    token: TagToken {
                        token: "_('hello world')".to_string(),
                        start_index: 0,
                        end_index: 16,
                        line_col: (1, 1),
                    },
                    children: vec![],
                    spread: None,
                    filters: vec![],
                    kind: ValueKind::Translation,
                    start_index: 0,
                    end_index: 16,
                    line_col: (1, 1),
                },
                start_index: 0,
                end_index: 16,
                line_col: (1, 1),
            }]
        );
    }

    #[test]
    fn test_arg_single_i18n_string_with_double_quotes() {
        // Test i18n string with double quotes
        let input = "_(\"hello world\")";
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result,
            vec![TagAttr {
                key: None,
                value: TagValue {
                    token: TagToken {
                        token: "_(\"hello world\")".to_string(),
                        start_index: 0,
                        end_index: 16,
                        line_col: (1, 1),
                    },
                    children: vec![],
                    spread: None,
                    filters: vec![],
                    kind: ValueKind::Translation,
                    start_index: 0,
                    end_index: 16,
                    line_col: (1, 1),
                },
                start_index: 0,
                end_index: 16,
                line_col: (1, 1),
            }]
        );
    }

    #[test]
    fn test_arg_single_whitespace() {
        let input = " val ";
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result,
            vec![TagAttr {
                key: None,
                value: TagValue {
                    token: TagToken {
                        token: "val".to_string(),
                        start_index: 1,
                        end_index: 4,
                        line_col: (1, 2),
                    },
                    children: vec![],
                    spread: None,
                    filters: vec![],
                    kind: ValueKind::Variable,
                    start_index: 1,
                    end_index: 4,
                    line_col: (1, 2),
                },
                start_index: 1,
                end_index: 4,
                line_col: (1, 2),
            }]
        );
    }

    #[test]
    fn test_arg_multiple() {
        let input = "component value1 value2";
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result,
            vec![
                TagAttr {
                    key: None,
                    value: TagValue {
                        token: TagToken {
                            token: "component".to_string(),
                            start_index: 0,
                            end_index: 9,
                            line_col: (1, 1),
                        },
                        children: vec![],
                        spread: None,
                        filters: vec![],
                        kind: ValueKind::Variable,
                        start_index: 0,
                        end_index: 9,
                        line_col: (1, 1),
                    },
                    start_index: 0,
                    end_index: 9,
                    line_col: (1, 1),
                },
                TagAttr {
                    key: None,
                    value: TagValue {
                        token: TagToken {
                            token: "value1".to_string(),
                            start_index: 10,
                            end_index: 16,
                            line_col: (1, 11),
                        },
                        children: vec![],
                        spread: None,
                        filters: vec![],
                        kind: ValueKind::Variable,
                        start_index: 10,
                        end_index: 16,
                        line_col: (1, 11),
                    },
                    start_index: 10,
                    end_index: 16,
                    line_col: (1, 11),
                },
                TagAttr {
                    key: None,
                    value: TagValue {
                        token: TagToken {
                            token: "value2".to_string(),
                            start_index: 17,
                            end_index: 23,
                            line_col: (1, 18),
                        },
                        children: vec![],
                        spread: None,
                        filters: vec![],
                        kind: ValueKind::Variable,
                        start_index: 17,
                        end_index: 23,
                        line_col: (1, 18),
                    },
                    start_index: 17,
                    end_index: 23,
                    line_col: (1, 18),
                }
            ]
        );
    }

    #[test]
    fn test_kwarg_single() {
        let input = "key=val";
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result,
            vec![TagAttr {
                key: Some(TagToken {
                    token: "key".to_string(),
                    start_index: 0,
                    end_index: 3,
                    line_col: (1, 1),
                }),
                value: TagValue {
                    token: TagToken {
                        token: "val".to_string(),
                        start_index: 4,
                        end_index: 7,
                        line_col: (1, 5),
                    },
                    children: vec![],
                    spread: None,
                    filters: vec![],
                    kind: ValueKind::Variable,
                    start_index: 4,
                    end_index: 7,
                    line_col: (1, 5),
                },
                start_index: 0,
                end_index: 7,
                line_col: (1, 1),
            }]
        );
    }

    #[test]
    fn test_kwarg_single_whitespace() {
        let input = " key=val ";
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result,
            vec![TagAttr {
                key: Some(TagToken {
                    token: "key".to_string(),
                    start_index: 1,
                    end_index: 4,
                    line_col: (1, 2),
                }),
                value: TagValue {
                    token: TagToken {
                        token: "val".to_string(),
                        start_index: 5,
                        end_index: 8,
                        line_col: (1, 6),
                    },
                    children: vec![],
                    spread: None,
                    filters: vec![],
                    kind: ValueKind::Variable,
                    start_index: 5,
                    end_index: 8,
                    line_col: (1, 6),
                },
                start_index: 1,
                end_index: 8,
                line_col: (1, 2),
            }]
        );
    }

    #[test]
    fn test_kwarg_multiple() {
        let input = "key=val key2=val2";
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result,
            vec![
                TagAttr {
                    key: Some(TagToken {
                        token: "key".to_string(),
                        start_index: 0,
                        end_index: 3,
                        line_col: (1, 1),
                    }),
                    value: TagValue {
                        token: TagToken {
                            token: "val".to_string(),
                            start_index: 4,
                            end_index: 7,
                            line_col: (1, 5),
                        },
                        children: vec![],
                        spread: None,
                        filters: vec![],
                        kind: ValueKind::Variable,
                        start_index: 4,
                        end_index: 7,
                        line_col: (1, 5),
                    },
                    start_index: 0,
                    end_index: 7,
                    line_col: (1, 1),
                },
                TagAttr {
                    key: Some(TagToken {
                        token: "key2".to_string(),
                        start_index: 8,
                        end_index: 12,
                        line_col: (1, 9),
                    }),
                    value: TagValue {
                        token: TagToken {
                            token: "val2".to_string(),
                            start_index: 13,
                            end_index: 17,
                            line_col: (1, 14),
                        },
                        children: vec![],
                        spread: None,
                        filters: vec![],
                        kind: ValueKind::Variable,
                        start_index: 13,
                        end_index: 17,
                        line_col: (1, 14),
                    },
                    start_index: 8,
                    end_index: 17,
                    line_col: (1, 9),
                }
            ]
        );
    }

    // Test that we do NOT allow whitespace around the `=`, e.g. `key= val`, `key =val`, `key = val`
    #[test]
    fn test_kwarg_whitespace_around_equals() {
        // Test whitespace after key
        let input = "key= val";
        assert!(
            TagParser::parse_tag(input).is_err(),
            "Should not allow whitespace after key before equals"
        );

        // Test whitespace before value
        let input = "key =val";
        assert!(
            TagParser::parse_tag(input).is_err(),
            "Should not allow whitespace before value after equals"
        );

        // Test whitespace on both sides
        let input = "key = val";
        assert!(
            TagParser::parse_tag(input).is_err(),
            "Should not allow whitespace around equals"
        );

        // Test multiple attributes with mixed whitespace
        let input = "key1= val1 key2 =val2 key3 = val3";
        assert!(
            TagParser::parse_tag(input).is_err(),
            "Should not allow whitespace around equals in any attribute"
        );
    }

    #[test]
    fn test_kwarg_special_chars() {
        let input = "@click.stop=handler attr:key=val";
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result,
            vec![
                TagAttr {
                    key: Some(TagToken {
                        token: "@click.stop".to_string(),
                        start_index: 0,
                        end_index: 11,
                        line_col: (1, 1),
                    }),
                    value: TagValue {
                        token: TagToken {
                            token: "handler".to_string(),
                            start_index: 12,
                            end_index: 19,
                            line_col: (1, 13),
                        },
                        children: vec![],
                        spread: None,
                        filters: vec![],
                        kind: ValueKind::Variable,
                        start_index: 12,
                        end_index: 19,
                        line_col: (1, 13)
                    },
                    start_index: 0,
                    end_index: 19,
                    line_col: (1, 1),
                },
                TagAttr {
                    key: Some(TagToken {
                        token: "attr:key".to_string(),
                        start_index: 20,
                        end_index: 28,
                        line_col: (1, 21),
                    }),
                    value: TagValue {
                        token: TagToken {
                            token: "val".to_string(),
                            start_index: 29,
                            end_index: 32,
                            line_col: (1, 30),
                        },
                        children: vec![],
                        spread: None,
                        filters: vec![],
                        kind: ValueKind::Variable,
                        start_index: 29,
                        end_index: 32,
                        line_col: (1, 30)
                    },
                    start_index: 20,
                    end_index: 32,
                    line_col: (1, 21),
                }
            ]
        );
    }

    #[test]
    fn test_kwarg_invalid() {
        let inputs = vec![
            ":key=val",
            "...key=val",
            "_('hello')=val",
            "\"key\"=val",
            "key[0]=val",
        ];

        for input in inputs {
            assert!(
                TagParser::parse_tag(input).is_err(),
                "Input should fail: {}",
                input
            );
        }
    }

    #[test]
    fn test_comment_before() {
        // Test comment before attribute
        let input = "{# comment #}key=val";
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result,
            vec![TagAttr {
                key: Some(TagToken {
                    token: "key".to_string(),
                    start_index: 13,
                    end_index: 16,
                    line_col: (1, 14),
                }),
                value: TagValue {
                    token: TagToken {
                        token: "val".to_string(),
                        start_index: 17,
                        end_index: 20,
                        line_col: (1, 18),
                    },
                    children: vec![],
                    spread: None,
                    filters: vec![],
                    kind: ValueKind::Variable,
                    start_index: 17,
                    end_index: 20,
                    line_col: (1, 18),
                },
                start_index: 13,
                end_index: 20,
                line_col: (1, 14),
            }]
        );
    }

    #[test]
    fn test_comment_after() {
        // Test comment after attribute
        let input = "key=val{# comment #}";
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result,
            vec![TagAttr {
                key: Some(TagToken {
                    token: "key".to_string(),
                    start_index: 0,
                    end_index: 3,
                    line_col: (1, 1),
                }),
                value: TagValue {
                    token: TagToken {
                        token: "val".to_string(),
                        start_index: 4,
                        end_index: 7,
                        line_col: (1, 5),
                    },
                    children: vec![],
                    spread: None,
                    filters: vec![],
                    kind: ValueKind::Variable,
                    start_index: 4,
                    end_index: 7,
                    line_col: (1, 5),
                },
                start_index: 0,
                end_index: 7,
                line_col: (1, 1),
            }]
        );
    }

    #[test]
    fn test_comment_between() {
        let input = "key1=val1 {# comment #} key2=val2";
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result,
            vec![
                TagAttr {
                    key: Some(TagToken {
                        token: "key1".to_string(),
                        start_index: 0,
                        end_index: 4,
                        line_col: (1, 1),
                    }),
                    value: TagValue {
                        token: TagToken {
                            token: "val1".to_string(),
                            start_index: 5,
                            end_index: 9,
                            line_col: (1, 6),
                        },
                        children: vec![],
                        spread: None,
                        filters: vec![],
                        kind: ValueKind::Variable,
                        start_index: 5,
                        end_index: 9,
                        line_col: (1, 6),
                    },
                    start_index: 0,
                    end_index: 9,
                    line_col: (1, 1),
                },
                TagAttr {
                    key: Some(TagToken {
                        token: "key2".to_string(),
                        start_index: 24,
                        end_index: 28,
                        line_col: (1, 25),
                    }),
                    value: TagValue {
                        token: TagToken {
                            token: "val2".to_string(),
                            start_index: 29,
                            end_index: 33,
                            line_col: (1, 30),
                        },
                        children: vec![],
                        spread: None,
                        filters: vec![],
                        kind: ValueKind::Variable,
                        start_index: 29,
                        end_index: 33,
                        line_col: (1, 30),
                    },
                    start_index: 24,
                    end_index: 33,
                    line_col: (1, 25),
                }
            ]
        );
    }

    #[test]
    fn test_comment_multiple() {
        // Test multiple comments
        let input = "{# c1 #}key1=val1{# c2 #}key2=val2{# c3 #}";
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result,
            vec![
                TagAttr {
                    key: Some(TagToken {
                        token: "key1".to_string(),
                        start_index: 8,
                        end_index: 12,
                        line_col: (1, 9),
                    }),
                    value: TagValue {
                        token: TagToken {
                            token: "val1".to_string(),
                            start_index: 13,
                            end_index: 17,
                            line_col: (1, 14),
                        },
                        children: vec![],
                        spread: None,
                        filters: vec![],
                        kind: ValueKind::Variable,
                        start_index: 13,
                        end_index: 17,
                        line_col: (1, 14),
                    },
                    start_index: 8,
                    end_index: 17,
                    line_col: (1, 9),
                },
                TagAttr {
                    key: Some(TagToken {
                        token: "key2".to_string(),
                        start_index: 25,
                        end_index: 29,
                        line_col: (1, 26),
                    }),
                    value: TagValue {
                        token: TagToken {
                            token: "val2".to_string(),
                            start_index: 30,
                            end_index: 34,
                            line_col: (1, 31),
                        },
                        children: vec![],
                        spread: None,
                        filters: vec![],
                        kind: ValueKind::Variable,
                        start_index: 30,
                        end_index: 34,
                        line_col: (1, 31),
                    },
                    start_index: 25,
                    end_index: 34,
                    line_col: (1, 26),
                }
            ]
        );
    }

    #[test]
    fn test_comment_with_newlines() {
        // Test comment with newlines
        let input = "key1=val1 {# multi\nline\ncomment #} key2=val2";
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result,
            vec![
                TagAttr {
                    key: Some(TagToken {
                        token: "key1".to_string(),
                        start_index: 0,
                        end_index: 4,
                        line_col: (1, 1),
                    }),
                    value: TagValue {
                        token: TagToken {
                            token: "val1".to_string(),
                            start_index: 5,
                            end_index: 9,
                            line_col: (1, 6),
                        },
                        children: vec![],
                        spread: None,
                        filters: vec![],
                        kind: ValueKind::Variable,
                        start_index: 5,
                        end_index: 9,
                        line_col: (1, 6),
                    },
                    start_index: 0,
                    end_index: 9,
                    line_col: (1, 1),
                },
                TagAttr {
                    key: Some(TagToken {
                        token: "key2".to_string(),
                        start_index: 35,
                        end_index: 39,
                        line_col: (3, 12),
                    }),
                    value: TagValue {
                        token: TagToken {
                            token: "val2".to_string(),
                            start_index: 40,
                            end_index: 44,
                            line_col: (3, 17),
                        },
                        children: vec![],
                        spread: None,
                        filters: vec![],
                        kind: ValueKind::Variable,
                        start_index: 40,
                        end_index: 44,
                        line_col: (3, 17),
                    },
                    start_index: 35,
                    end_index: 44,
                    line_col: (3, 12),
                }
            ]
        );
    }

    #[test]
    fn test_comment_not_allowed_between_key_and_value() {
        // Test comment between key and equals
        let input = "key{# comment #}=val";
        assert!(
            TagParser::parse_tag(input).is_err(),
            "Should not allow comment between key and equals"
        );

        // Test comment between equals and value
        let input = "key={# comment #}val";
        assert!(
            TagParser::parse_tag(input).is_err(),
            "Should not allow comment between equals and value"
        );
    }

    #[test]
    fn test_spread_basic() {
        let input = "...myvalue";
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result,
            vec![TagAttr {
                key: None,
                value: TagValue {
                    token: TagToken {
                        token: "myvalue".to_string(),
                        start_index: 3,
                        end_index: 10,
                        line_col: (1, 4),
                    },
                    children: vec![],
                    spread: Some("...".to_string()),
                    filters: vec![],
                    kind: ValueKind::Variable,
                    start_index: 0,
                    end_index: 10,
                    line_col: (1, 1),
                },
                start_index: 0,
                end_index: 10,
                line_col: (1, 1),
            }]
        );
    }

    #[test]
    fn test_spread_between() {
        // Test spread with other attributes
        let input = "key1=val1 ...myvalue key2=val2";
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result,
            vec![
                TagAttr {
                    key: Some(TagToken {
                        token: "key1".to_string(),
                        start_index: 0,
                        end_index: 4,
                        line_col: (1, 1),
                    }),
                    value: TagValue {
                        token: TagToken {
                            token: "val1".to_string(),
                            start_index: 5,
                            end_index: 9,
                            line_col: (1, 6),
                        },
                        children: vec![],
                        spread: None,
                        filters: vec![],
                        kind: ValueKind::Variable,
                        start_index: 5,
                        end_index: 9,
                        line_col: (1, 6),
                    },
                    start_index: 0,
                    end_index: 9,
                    line_col: (1, 1),
                },
                TagAttr {
                    key: None,
                    value: TagValue {
                        token: TagToken {
                            token: "myvalue".to_string(),
                            start_index: 13,
                            end_index: 20,
                            line_col: (1, 14),
                        },
                        children: vec![],
                        spread: Some("...".to_string()),
                        filters: vec![],
                        kind: ValueKind::Variable,
                        start_index: 10,
                        end_index: 20,
                        line_col: (1, 11),
                    },
                    start_index: 10,
                    end_index: 20,
                    line_col: (1, 11),
                },
                TagAttr {
                    key: Some(TagToken {
                        token: "key2".to_string(),
                        start_index: 21,
                        end_index: 25,
                        line_col: (1, 22),
                    }),
                    value: TagValue {
                        token: TagToken {
                            token: "val2".to_string(),
                            start_index: 26,
                            end_index: 30,
                            line_col: (1, 27),
                        },
                        children: vec![],
                        spread: None,
                        filters: vec![],
                        kind: ValueKind::Variable,
                        start_index: 26,
                        end_index: 30,
                        line_col: (1, 27),
                    },
                    start_index: 21,
                    end_index: 30,
                    line_col: (1, 22),
                }
            ]
        );
    }

    #[test]
    fn test_spread_multiple() {
        let input = "...dict1 key=val ...dict2";
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result,
            vec![
                TagAttr {
                    key: None,
                    value: TagValue {
                        token: TagToken {
                            token: "dict1".to_string(),
                            start_index: 3,
                            end_index: 8,
                            line_col: (1, 4),
                        },
                        children: vec![],
                        spread: Some("...".to_string()),
                        filters: vec![],
                        kind: ValueKind::Variable,
                        start_index: 0,
                        end_index: 8,
                        line_col: (1, 1),
                    },
                    start_index: 0,
                    end_index: 8,
                    line_col: (1, 1),
                },
                TagAttr {
                    key: Some(TagToken {
                        token: "key".to_string(),
                        start_index: 9,
                        end_index: 12,
                        line_col: (1, 10),
                    }),
                    value: TagValue {
                        token: TagToken {
                            token: "val".to_string(),
                            start_index: 13,
                            end_index: 16,
                            line_col: (1, 14),
                        },
                        children: vec![],
                        spread: None,
                        filters: vec![],
                        kind: ValueKind::Variable,
                        start_index: 13,
                        end_index: 16,
                        line_col: (1, 14),
                    },
                    start_index: 9,
                    end_index: 16,
                    line_col: (1, 10),
                },
                TagAttr {
                    key: None,
                    value: TagValue {
                        token: TagToken {
                            token: "dict2".to_string(),
                            start_index: 20,
                            end_index: 25,
                            line_col: (1, 21),
                        },
                        children: vec![],
                        spread: Some("...".to_string()),
                        filters: vec![],
                        kind: ValueKind::Variable,
                        start_index: 17,
                        end_index: 25,
                        line_col: (1, 18),
                    },
                    start_index: 17,
                    end_index: 25,
                    line_col: (1, 18),
                }
            ]
        );
    }

    #[test]
    fn test_spread_dict() {
        // Test spread with dictionary
        let input = r#"...{"key": "value"}"#;
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result,
            vec![TagAttr {
                key: None,
                value: TagValue {
                    token: TagToken {
                        token: "{\"key\": \"value\"}".to_string(),
                        start_index: 3,
                        end_index: 19,
                        line_col: (1, 4),
                    },
                    children: vec![
                        TagValue {
                            token: TagToken {
                                token: "\"key\"".to_string(),
                                start_index: 4,
                                end_index: 9,
                                line_col: (1, 5),
                            },
                            children: vec![],
                            spread: None,
                            filters: vec![],
                            kind: ValueKind::String,
                            start_index: 4,
                            end_index: 9,
                            line_col: (1, 5),
                        },
                        TagValue {
                            token: TagToken {
                                token: "\"value\"".to_string(),
                                start_index: 11,
                                end_index: 18,
                                line_col: (1, 12),
                            },
                            children: vec![],
                            spread: None,
                            filters: vec![],
                            kind: ValueKind::String,
                            start_index: 11,
                            end_index: 18,
                            line_col: (1, 12),
                        },
                    ],
                    spread: Some("...".to_string()),
                    filters: vec![],
                    kind: ValueKind::Dict,
                    start_index: 0,
                    end_index: 19,
                    line_col: (1, 1),
                },
                start_index: 0,
                end_index: 19,
                line_col: (1, 1),
            }]
        );
    }

    #[test]
    fn test_spread_list() {
        let input = "...[1, 2, 3]";
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result,
            vec![TagAttr {
                key: None,
                value: TagValue {
                    token: TagToken {
                        token: "[1, 2, 3]".to_string(),
                        start_index: 3,
                        end_index: 12,
                        line_col: (1, 4),
                    },
                    children: vec![
                        TagValue {
                            token: TagToken {
                                token: "1".to_string(),
                                start_index: 4,
                                end_index: 5,
                                line_col: (1, 5),
                            },
                            children: vec![],
                            spread: None,
                            filters: vec![],
                            kind: ValueKind::Int,
                            start_index: 4,
                            end_index: 5,
                            line_col: (1, 5),
                        },
                        TagValue {
                            token: TagToken {
                                token: "2".to_string(),
                                start_index: 7,
                                end_index: 8,
                                line_col: (1, 8),
                            },
                            children: vec![],
                            spread: None,
                            filters: vec![],
                            kind: ValueKind::Int,
                            start_index: 7,
                            end_index: 8,
                            line_col: (1, 8),
                        },
                        TagValue {
                            token: TagToken {
                                token: "3".to_string(),
                                start_index: 10,
                                end_index: 11,
                                line_col: (1, 11),
                            },
                            children: vec![],
                            spread: None,
                            filters: vec![],
                            kind: ValueKind::Int,
                            start_index: 10,
                            end_index: 11,
                            line_col: (1, 11),
                        }
                    ],
                    spread: Some("...".to_string()),
                    filters: vec![],
                    kind: ValueKind::List,
                    start_index: 0,
                    end_index: 12,
                    line_col: (1, 1),
                },
                start_index: 0,
                end_index: 12,
                line_col: (1, 1),
            }]
        );
    }

    #[test]
    fn test_spread_i18n() {
        // Test spread with i18n string
        let input = "..._('hello')";
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result,
            vec![TagAttr {
                key: None,
                value: TagValue {
                    token: TagToken {
                        token: "_('hello')".to_string(),
                        start_index: 3,
                        end_index: 13,
                        line_col: (1, 4),
                    },
                    children: vec![],
                    spread: Some("...".to_string()),
                    filters: vec![],
                    kind: ValueKind::Translation,
                    start_index: 0,
                    end_index: 13,
                    line_col: (1, 1),
                },
                start_index: 0,
                end_index: 13,
                line_col: (1, 1),
            }]
        );
    }

    #[test]
    fn test_spread_variable() {
        // Test spread with variable
        let input = "...my_var";
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result[0],
            TagAttr {
                key: None,
                value: TagValue {
                    token: TagToken {
                        token: "my_var".to_string(),
                        start_index: 3,
                        end_index: 9,
                        line_col: (1, 4),
                    },
                    children: vec![],
                    spread: Some("...".to_string()),
                    filters: vec![],
                    kind: ValueKind::Variable,
                    start_index: 0,
                    end_index: 9,
                    line_col: (1, 1),
                },
                start_index: 0,
                end_index: 9,
                line_col: (1, 1),
            }
        );
    }

    #[test]
    fn test_spread_number() {
        // Test spread with number
        let input = "...42";
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result,
            vec![TagAttr {
                key: None,
                value: TagValue {
                    token: TagToken {
                        token: "42".to_string(),
                        start_index: 3,
                        end_index: 5,
                        line_col: (1, 4),
                    },
                    children: vec![],
                    spread: Some("...".to_string()),
                    filters: vec![],
                    kind: ValueKind::Int,
                    start_index: 0,
                    end_index: 5,
                    line_col: (1, 1),
                },
                start_index: 0,
                end_index: 5,
                line_col: (1, 1),
            }]
        );
    }

    #[test]
    fn test_spread_string() {
        // Test spread with string literal
        let input = r#"..."hello""#;
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result[0],
            TagAttr {
                key: None,
                value: TagValue {
                    token: TagToken {
                        token: "\"hello\"".to_string(),
                        start_index: 3,
                        end_index: 10,
                        line_col: (1, 4),
                    },
                    children: vec![],
                    spread: Some("...".to_string()),
                    filters: vec![],
                    kind: ValueKind::String,
                    start_index: 0,
                    end_index: 10,
                    line_col: (1, 1),
                },
                start_index: 0,
                end_index: 10,
                line_col: (1, 1),
            }
        );
    }

    #[test]
    fn test_spread_invalid() {
        // Test spread missing value
        let input = "...";
        assert!(
            TagParser::parse_tag(input).is_err(),
            "Should not allow spread operator without a value"
        );
        // Test spread whitespace between operator and value
        let input = "...  myvalue";
        assert!(
            TagParser::parse_tag(input).is_err(),
            "Should not allow spread operator with whitespace between operator and value"
        );

        // Test spread in key position
        let input = "...key=val";
        assert!(
            TagParser::parse_tag(input).is_err(),
            "Should not allow spread operator in key position"
        );

        // Test spread in value position of key-value pair
        let input = "key=...val";
        assert!(
            TagParser::parse_tag(input).is_err(),
            "Should not allow spread operator in value position of key-value pair"
        );

        // Test spread operator inside list
        let input = "[1, ...my_list, 2]";
        assert!(
            TagParser::parse_tag(input).is_err(),
            "Should not allow ... spread operator inside list"
        );

        // Test spread operator inside list with filters
        let input = "[1, ...my_list|filter, 2]";
        assert!(
            TagParser::parse_tag(input).is_err(),
            "Should not allow ... spread operator inside list with filters"
        );

        // Test spread operator inside nested list
        let input = "[1, [...my_list], 2]";
        assert!(
            TagParser::parse_tag(input).is_err(),
            "Should not allow ... spread operator inside nested list"
        );
    }

    #[test]
    fn test_filter_basic() {
        let input = "value|lower";
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result,
            vec![TagAttr {
                key: None,
                value: TagValue {
                    token: TagToken {
                        token: "value".to_string(),
                        start_index: 0,
                        end_index: 5,
                        line_col: (1, 1),
                    },
                    children: vec![],
                    spread: None,
                    filters: vec![TagValueFilter {
                        arg: None,
                        token: TagToken {
                            token: "lower".to_string(),
                            start_index: 6,
                            end_index: 11,
                            line_col: (1, 7),
                        },
                        start_index: 5,
                        end_index: 11,
                        line_col: (1, 6),
                    }],
                    kind: ValueKind::Variable,
                    start_index: 0,
                    end_index: 11,
                    line_col: (1, 1),
                },
                start_index: 0,
                end_index: 11,
                line_col: (1, 1),
            }]
        );
    }

    #[test]
    fn test_filter_multiple() {
        let input = "value|lower|title|default:'hello'";
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result,
            vec![TagAttr {
                key: None,
                value: TagValue {
                    token: TagToken {
                        token: "value".to_string(),
                        start_index: 0,
                        end_index: 5,
                        line_col: (1, 1),
                    },
                    children: vec![],
                    kind: ValueKind::Variable,
                    spread: None,
                    filters: vec![
                        TagValueFilter {
                            token: TagToken {
                                token: "lower".to_string(),
                                start_index: 6,
                                end_index: 11,
                                line_col: (1, 7),
                            },
                            arg: None,
                            start_index: 5,
                            end_index: 11,
                            line_col: (1, 6),
                        },
                        TagValueFilter {
                            token: TagToken {
                                token: "title".to_string(),
                                start_index: 12,
                                end_index: 17,
                                line_col: (1, 13),
                            },
                            arg: None,
                            start_index: 11,
                            end_index: 17,
                            line_col: (1, 12),
                        },
                        TagValueFilter {
                            token: TagToken {
                                token: "default".to_string(),
                                start_index: 18,
                                end_index: 25,
                                line_col: (1, 19),
                            },
                            arg: Some(TagValue {
                                token: TagToken {
                                    token: "'hello'".to_string(),
                                    start_index: 26,
                                    end_index: 33,
                                    line_col: (1, 27),
                                },
                                children: vec![],
                                kind: ValueKind::String,
                                spread: None,
                                filters: vec![],
                                start_index: 25,
                                end_index: 33,
                                line_col: (1, 26),
                            }),
                            start_index: 17,
                            end_index: 33,
                            line_col: (1, 18),
                        }
                    ],
                    start_index: 0,
                    end_index: 33,
                    line_col: (1, 1),
                },
                start_index: 0,
                end_index: 33,
                line_col: (1, 1),
            }]
        );
    }

    #[test]
    fn test_filter_arg_string() {
        let input = "value|default:'hello'";
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result,
            vec![TagAttr {
                key: None,
                value: TagValue {
                    token: TagToken {
                        token: "value".to_string(),
                        start_index: 0,
                        end_index: 5,
                        line_col: (1, 1),
                    },
                    children: vec![],
                    spread: None,
                    filters: vec![TagValueFilter {
                        token: TagToken {
                            token: "default".to_string(),
                            start_index: 6,
                            end_index: 13,
                            line_col: (1, 7),
                        },
                        arg: Some(TagValue {
                            token: TagToken {
                                token: "'hello'".to_string(),
                                start_index: 14,
                                end_index: 21,
                                line_col: (1, 15),
                            },
                            children: vec![],
                            kind: ValueKind::String,
                            spread: None,
                            filters: vec![],
                            start_index: 13,
                            end_index: 21,
                            line_col: (1, 14),
                        }),
                        start_index: 5,
                        end_index: 21,
                        line_col: (1, 6),
                    }],
                    kind: ValueKind::Variable,
                    start_index: 0,
                    end_index: 21,
                    line_col: (1, 1),
                },
                start_index: 0,
                end_index: 21,
                line_col: (1, 1),
            }]
        );
    }

    #[test]
    fn test_filter_arg_number() {
        let input = "value|add:42";
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result,
            vec![TagAttr {
                key: None,
                value: TagValue {
                    token: TagToken {
                        token: "value".to_string(),
                        start_index: 0,
                        end_index: 5,
                        line_col: (1, 1),
                    },
                    children: vec![],
                    spread: None,
                    filters: vec![TagValueFilter {
                        token: TagToken {
                            token: "add".to_string(),
                            start_index: 6,
                            end_index: 9,
                            line_col: (1, 7),
                        },
                        arg: Some(TagValue {
                            token: TagToken {
                                token: "42".to_string(),
                                start_index: 10,
                                end_index: 12,
                                line_col: (1, 11),
                            },
                            children: vec![],
                            kind: ValueKind::Int,
                            spread: None,
                            filters: vec![],
                            start_index: 9,
                            end_index: 12,
                            line_col: (1, 10),
                        }),
                        start_index: 5,
                        end_index: 12,
                        line_col: (1, 6),
                    }],
                    kind: ValueKind::Variable,
                    start_index: 0,
                    end_index: 12,
                    line_col: (1, 1),
                },
                start_index: 0,
                end_index: 12,
                line_col: (1, 1),
            }]
        );
    }

    #[test]
    fn test_filter_arg_variable() {
        let input = "value|default:my_var.field";
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result,
            vec![TagAttr {
                key: None,
                value: TagValue {
                    token: TagToken {
                        token: "value".to_string(),
                        start_index: 0,
                        end_index: 5,
                        line_col: (1, 1),
                    },
                    children: vec![],
                    spread: None,
                    filters: vec![TagValueFilter {
                        token: TagToken {
                            token: "default".to_string(),
                            start_index: 6,
                            end_index: 13,
                            line_col: (1, 7),
                        },
                        arg: Some(TagValue {
                            token: TagToken {
                                token: "my_var.field".to_string(),
                                start_index: 14,
                                end_index: 26,
                                line_col: (1, 15),
                            },
                            children: vec![],
                            kind: ValueKind::Variable,
                            spread: None,
                            filters: vec![],
                            start_index: 13,
                            end_index: 26,
                            line_col: (1, 14),
                        }),
                        start_index: 5,
                        end_index: 26,
                        line_col: (1, 6),
                    }],
                    kind: ValueKind::Variable,
                    start_index: 0,
                    end_index: 26,
                    line_col: (1, 1),
                },
                start_index: 0,
                end_index: 26,
                line_col: (1, 1),
            }]
        );
    }

    #[test]
    fn test_filter_arg_i18n() {
        let input = "value|default:_('hello')";
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result,
            vec![TagAttr {
                key: None,
                value: TagValue {
                    token: TagToken {
                        token: "value".to_string(),
                        start_index: 0,
                        end_index: 5,
                        line_col: (1, 1),
                    },
                    children: vec![],
                    spread: None,
                    filters: vec![TagValueFilter {
                        token: TagToken {
                            token: "default".to_string(),
                            start_index: 6,
                            end_index: 13,
                            line_col: (1, 7),
                        },
                        arg: Some(TagValue {
                            token: TagToken {
                                token: "_('hello')".to_string(),
                                start_index: 14,
                                end_index: 24,
                                line_col: (1, 15),
                            },
                            children: vec![],
                            kind: ValueKind::Translation,
                            spread: None,
                            filters: vec![],
                            start_index: 13,
                            end_index: 24,
                            line_col: (1, 14),
                        }),
                        start_index: 5,
                        end_index: 24,
                        line_col: (1, 6),
                    }],
                    kind: ValueKind::Variable,
                    start_index: 0,
                    end_index: 24,
                    line_col: (1, 1),
                },
                start_index: 0,
                end_index: 24,
                line_col: (1, 1),
            }]
        );
    }

    #[test]
    fn test_filter_arg_list() {
        let input = "value|default:[1, 2, 3]";
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result,
            vec![TagAttr {
                key: None,
                value: TagValue {
                    token: TagToken {
                        token: "value".to_string(),
                        start_index: 0,
                        end_index: 5,
                        line_col: (1, 1),
                    },
                    children: vec![],
                    spread: None,
                    filters: vec![TagValueFilter {
                        token: TagToken {
                            token: "default".to_string(),
                            start_index: 6,
                            end_index: 13,
                            line_col: (1, 7),
                        },
                        arg: Some(TagValue {
                            token: TagToken {
                                token: "[1, 2, 3]".to_string(),
                                start_index: 14,
                                end_index: 23,
                                line_col: (1, 15),
                            },
                            children: vec![
                                TagValue {
                                    token: TagToken {
                                        token: "1".to_string(),
                                        start_index: 15,
                                        end_index: 16,
                                        line_col: (1, 16),
                                    },
                                    children: vec![],
                                    kind: ValueKind::Int,
                                    spread: None,
                                    filters: vec![],
                                    start_index: 15,
                                    end_index: 16,
                                    line_col: (1, 16),
                                },
                                TagValue {
                                    token: TagToken {
                                        token: "2".to_string(),
                                        start_index: 18,
                                        end_index: 19,
                                        line_col: (1, 19),
                                    },
                                    children: vec![],
                                    kind: ValueKind::Int,
                                    spread: None,
                                    filters: vec![],
                                    start_index: 18,
                                    end_index: 19,
                                    line_col: (1, 19),
                                },
                                TagValue {
                                    token: TagToken {
                                        token: "3".to_string(),
                                        start_index: 21,
                                        end_index: 22,
                                        line_col: (1, 22),
                                    },
                                    children: vec![],
                                    kind: ValueKind::Int,
                                    spread: None,
                                    filters: vec![],
                                    start_index: 21,
                                    end_index: 22,
                                    line_col: (1, 22),
                                },
                            ],
                            kind: ValueKind::List,
                            spread: None,
                            filters: vec![],
                            start_index: 13,
                            end_index: 23,
                            line_col: (1, 14),
                        }),
                        start_index: 5,
                        end_index: 23,
                        line_col: (1, 6),
                    }],
                    kind: ValueKind::Variable,
                    start_index: 0,
                    end_index: 23,
                    line_col: (1, 1),
                },
                start_index: 0,
                end_index: 23,
                line_col: (1, 1),
            }]
        );
    }

    #[test]
    fn test_filter_arg_dict() {
        let input = r#"value|default:{"key": "val"}"#;
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result,
            vec![TagAttr {
                key: None,
                value: TagValue {
                    token: TagToken {
                        token: "value".to_string(),
                        start_index: 0,
                        end_index: 5,
                        line_col: (1, 1),
                    },
                    children: vec![],
                    spread: None,
                    filters: vec![TagValueFilter {
                        token: TagToken {
                            token: "default".to_string(),
                            start_index: 6,
                            end_index: 13,
                            line_col: (1, 7),
                        },
                        arg: Some(TagValue {
                            token: TagToken {
                                token: "{\"key\": \"val\"}".to_string(),
                                start_index: 14,
                                end_index: 28,
                                line_col: (1, 15),
                            },
                            children: vec![
                                TagValue {
                                    token: TagToken {
                                        token: "\"key\"".to_string(),
                                        start_index: 15,
                                        end_index: 20,
                                        line_col: (1, 16),
                                    },
                                    children: vec![],
                                    kind: ValueKind::String,
                                    spread: None,
                                    filters: vec![],
                                    start_index: 15,
                                    end_index: 20,
                                    line_col: (1, 16),
                                },
                                TagValue {
                                    token: TagToken {
                                        token: "\"val\"".to_string(),
                                        start_index: 22,
                                        end_index: 27,
                                        line_col: (1, 23),
                                    },
                                    children: vec![],
                                    kind: ValueKind::String,
                                    spread: None,
                                    filters: vec![],
                                    start_index: 22,
                                    end_index: 27,
                                    line_col: (1, 23),
                                },
                            ],
                            kind: ValueKind::Dict,
                            spread: None,
                            filters: vec![],
                            start_index: 13,
                            end_index: 28,
                            line_col: (1, 14),
                        }),
                        start_index: 5,
                        end_index: 28,
                        line_col: (1, 6),
                    }],
                    kind: ValueKind::Variable,
                    start_index: 0,
                    end_index: 28,
                    line_col: (1, 1),
                },
                start_index: 0,
                end_index: 28,
                line_col: (1, 1),
            }]
        );
    }

    #[test]
    fn test_filter_arg_expression() {
        let input = r#"value|default:"{{ var }}""#;
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result,
            vec![TagAttr {
                key: None,
                value: TagValue {
                    token: TagToken {
                        token: "value".to_string(),
                        start_index: 0,
                        end_index: 5,
                        line_col: (1, 1),
                    },
                    children: vec![],
                    spread: None,
                    filters: vec![TagValueFilter {
                        token: TagToken {
                            token: "default".to_string(),
                            start_index: 6,
                            end_index: 13,
                            line_col: (1, 7),
                        },
                        arg: Some(TagValue {
                            token: TagToken {
                                token: "\"{{ var }}\"".to_string(),
                                start_index: 14,
                                end_index: 25,
                                line_col: (1, 15),
                            },
                            children: vec![],
                            kind: ValueKind::Expression,
                            spread: None,
                            filters: vec![],
                            start_index: 13,
                            end_index: 25,
                            line_col: (1, 14),
                        }),
                        start_index: 5,
                        end_index: 25,
                        line_col: (1, 6),
                    }],
                    kind: ValueKind::Variable,
                    start_index: 0,
                    end_index: 25,
                    line_col: (1, 1),
                },
                start_index: 0,
                end_index: 25,
                line_col: (1, 1),
            }]
        );
    }

    #[test]
    fn test_filter_arg_nested() {
        let input = r#"value|default:[1, {"key": "val"}, _("hello")]"#;
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result,
            vec![TagAttr {
                key: None,
                value: TagValue {
                    token: TagToken {
                        token: "value".to_string(),
                        start_index: 0,
                        end_index: 5,
                        line_col: (1, 1),
                    },
                    children: vec![],
                    spread: None,
                    filters: vec![TagValueFilter {
                        token: TagToken {
                            token: "default".to_string(),
                            start_index: 6,
                            end_index: 13,
                            line_col: (1, 7),
                        },
                        arg: Some(TagValue {
                            token: TagToken {
                                token: "[1, {\"key\": \"val\"}, _(\"hello\")]".to_string(),
                                start_index: 14,
                                end_index: 45,
                                line_col: (1, 15),
                            },
                            children: vec![
                                TagValue {
                                    token: TagToken {
                                        token: "1".to_string(),
                                        start_index: 15,
                                        end_index: 16,
                                        line_col: (1, 16),
                                    },
                                    children: vec![],
                                    kind: ValueKind::Int,
                                    spread: None,
                                    filters: vec![],
                                    start_index: 15,
                                    end_index: 16,
                                    line_col: (1, 16),
                                },
                                TagValue {
                                    token: TagToken {
                                        token: "{\"key\": \"val\"}".to_string(),
                                        start_index: 18,
                                        end_index: 32,
                                        line_col: (1, 19),
                                    },
                                    children: vec![
                                        TagValue {
                                            token: TagToken {
                                                token: "\"key\"".to_string(),
                                                start_index: 19,
                                                end_index: 24,
                                                line_col: (1, 20),
                                            },
                                            children: vec![],
                                            kind: ValueKind::String,
                                            spread: None,
                                            filters: vec![],
                                            start_index: 19,
                                            end_index: 24,
                                            line_col: (1, 20),
                                        },
                                        TagValue {
                                            token: TagToken {
                                                token: "\"val\"".to_string(),
                                                start_index: 26,
                                                end_index: 31,
                                                line_col: (1, 27),
                                            },
                                            children: vec![],
                                            kind: ValueKind::String,
                                            spread: None,
                                            filters: vec![],
                                            start_index: 26,
                                            end_index: 31,
                                            line_col: (1, 27),
                                        },
                                    ],
                                    kind: ValueKind::Dict,
                                    spread: None,
                                    filters: vec![],
                                    start_index: 18,
                                    end_index: 32,
                                    line_col: (1, 19),
                                },
                                TagValue {
                                    token: TagToken {
                                        token: "_(\"hello\")".to_string(),
                                        start_index: 34,
                                        end_index: 44,
                                        line_col: (1, 35),
                                    },
                                    children: vec![],
                                    kind: ValueKind::Translation,
                                    spread: None,
                                    filters: vec![],
                                    start_index: 34,
                                    end_index: 44,
                                    line_col: (1, 35),
                                },
                            ],
                            kind: ValueKind::List,
                            spread: None,
                            filters: vec![],
                            start_index: 13,
                            end_index: 45,
                            line_col: (1, 14),
                        }),
                        start_index: 5,
                        end_index: 45,
                        line_col: (1, 6),
                    }],
                    kind: ValueKind::Variable,
                    start_index: 0,
                    end_index: 45,
                    line_col: (1, 1),
                },
                start_index: 0,
                end_index: 45,
                line_col: (1, 1),
            }]
        );
    }

    #[test]
    fn test_filter_whitespace() {
        // Test whitespace around pipe
        let input = "value | lower";
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result,
            vec![TagAttr {
                key: None,
                value: TagValue {
                    token: TagToken {
                        token: "value".to_string(),
                        start_index: 0,
                        end_index: 5,
                        line_col: (1, 1),
                    },
                    children: vec![],
                    spread: None,
                    filters: vec![TagValueFilter {
                        token: TagToken {
                            token: "lower".to_string(),
                            start_index: 8,
                            end_index: 13,
                            line_col: (1, 9),
                        },
                        arg: None,
                        start_index: 6,
                        end_index: 13,
                        line_col: (1, 7),
                    }],
                    kind: ValueKind::Variable,
                    start_index: 0,
                    end_index: 13,
                    line_col: (1, 1),
                },
                start_index: 0,
                end_index: 13,
                line_col: (1, 1),
            }]
        );
    }

    #[test]
    fn test_filter_arg_whitespace() {
        // Test whitespace around colon
        let input = "value|default : 'hello'";
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result,
            vec![TagAttr {
                key: None,
                value: TagValue {
                    token: TagToken {
                        token: "value".to_string(),
                        start_index: 0,
                        end_index: 5,
                        line_col: (1, 1),
                    },
                    children: vec![],
                    spread: None,
                    filters: vec![TagValueFilter {
                        token: TagToken {
                            token: "default".to_string(),
                            start_index: 6,
                            end_index: 13,
                            line_col: (1, 7),
                        },
                        arg: Some(TagValue {
                            token: TagToken {
                                token: "'hello'".to_string(),
                                start_index: 16,
                                end_index: 23,
                                line_col: (1, 17),
                            },
                            children: vec![],
                            spread: None,
                            filters: vec![],
                            kind: ValueKind::String,
                            start_index: 13,
                            end_index: 23,
                            line_col: (1, 14),
                        }),
                        start_index: 5,
                        end_index: 23,
                        line_col: (1, 6),
                    }],
                    kind: ValueKind::Variable,
                    start_index: 0,
                    end_index: 23,
                    line_col: (1, 1),
                },
                start_index: 0,
                end_index: 23,
                line_col: (1, 1),
            }]
        );
    }

    #[test]
    fn test_filter_whitespace_everywhere() {
        let input = "value  |  default  :  _( 'hello' )";
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result,
            vec![TagAttr {
                key: None,
                value: TagValue {
                    token: TagToken {
                        token: "value".to_string(),
                        start_index: 0,
                        end_index: 5,
                        line_col: (1, 1),
                    },
                    children: vec![],
                    spread: None,
                    filters: vec![TagValueFilter {
                        token: TagToken {
                            token: "default".to_string(),
                            start_index: 10,
                            end_index: 17,
                            line_col: (1, 11),
                        },
                        arg: Some(TagValue {
                            token: TagToken {
                                token: "_('hello')".to_string(),
                                start_index: 22,
                                end_index: 34,
                                line_col: (1, 23),
                            },
                            children: vec![],
                            kind: ValueKind::Translation,
                            spread: None,
                            filters: vec![],
                            start_index: 17,
                            end_index: 34,
                            line_col: (1, 18),
                        }),
                        start_index: 7,
                        end_index: 34,
                        line_col: (1, 8),
                    }],
                    kind: ValueKind::Variable,
                    start_index: 0,
                    end_index: 34,
                    line_col: (1, 1),
                },
                start_index: 0,
                end_index: 34,
                line_col: (1, 1),
            }]
        );
    }

    #[test]
    fn test_filter_comments() {
        // Test comments around pipe
        let input = "value {# pipe comment1 #}|{# pipe comment2 #}lower";
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result,
            vec![TagAttr {
                key: None,
                value: TagValue {
                    token: TagToken {
                        token: "value".to_string(),
                        start_index: 0,
                        end_index: 5,
                        line_col: (1, 1),
                    },
                    children: vec![],
                    spread: None,
                    filters: vec![TagValueFilter {
                        token: TagToken {
                            token: "lower".to_string(),
                            start_index: 45,
                            end_index: 50,
                            line_col: (1, 46),
                        },
                        arg: None,
                        start_index: 25,
                        end_index: 50,
                        line_col: (1, 26),
                    }],
                    kind: ValueKind::Variable,
                    start_index: 0,
                    end_index: 50,
                    line_col: (1, 1),
                },
                start_index: 0,
                end_index: 50,
                line_col: (1, 1),
            }]
        );
    }

    #[test]
    fn test_filter_arg_comments() {
        // Test comments around colon
        let input = "value|default{# colon comment1 #}:{# colon comment2 #}'hello'";
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result,
            vec![TagAttr {
                key: None,
                value: TagValue {
                    token: TagToken {
                        token: "value".to_string(),
                        start_index: 0,
                        end_index: 5,
                        line_col: (1, 1),
                    },
                    children: vec![],
                    spread: None,
                    filters: vec![TagValueFilter {
                        token: TagToken {
                            token: "default".to_string(),
                            start_index: 6,
                            end_index: 13,
                            line_col: (1, 7),
                        },
                        arg: Some(TagValue {
                            token: TagToken {
                                token: "'hello'".to_string(),
                                start_index: 54,
                                end_index: 61,
                                line_col: (1, 55),
                            },
                            children: vec![],
                            kind: ValueKind::String,
                            spread: None,
                            filters: vec![],
                            start_index: 13,
                            end_index: 61,
                            line_col: (1, 14),
                        }),
                        start_index: 5,
                        end_index: 61,
                        line_col: (1, 6),
                    }],
                    kind: ValueKind::Variable,
                    start_index: 0,
                    end_index: 61,
                    line_col: (1, 1),
                },
                start_index: 0,
                end_index: 61,
                line_col: (1, 1),
            }]
        );
    }

    #[test]
    fn test_filter_comments_everywhere() {
        // Test comments everywhere
        let input = "value {# pipe #}| {# name #}default{# colon #}:{# arg #}_({# open #}'hello'{# close #})";
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result,
            vec![TagAttr {
                key: None,
                value: TagValue {
                    token: TagToken {
                        token: "value".to_string(),
                        start_index: 0,
                        end_index: 5,
                        line_col: (1, 1),
                    },
                    children: vec![],
                    spread: None,
                    filters: vec![TagValueFilter {
                        token: TagToken {
                            token: "default".to_string(),
                            start_index: 28,
                            end_index: 35,
                            line_col: (1, 29),
                        },
                        arg: Some(TagValue {
                            token: TagToken {
                                token: "_('hello')".to_string(),
                                start_index: 56,
                                end_index: 87,
                                line_col: (1, 57),
                            },
                            children: vec![],
                            kind: ValueKind::Translation,
                            spread: None,
                            filters: vec![],
                            start_index: 35,
                            end_index: 87,
                            line_col: (1, 36),
                        }),
                        start_index: 16,
                        end_index: 87,
                        line_col: (1, 17),
                    }],
                    kind: ValueKind::Variable,
                    start_index: 0,
                    end_index: 87,
                    line_col: (1, 1),
                },
                start_index: 0,
                end_index: 87,
                line_col: (1, 1),
            }]
        );
    }

    #[test]
    fn test_filter_invalid() {
        // Test using colon instead of pipe
        let input = "value:filter";
        assert!(
            TagParser::parse_tag(input).is_err(),
            "Should not allow colon instead of pipe for filter"
        );

        // Test using colon with filter argument
        let input = "value:filter:arg";
        assert!(
            TagParser::parse_tag(input).is_err(),
            "Should not allow colon instead of pipe for filter with argument"
        );

        // Test using colon after a valid filter
        let input = "value|filter:arg:filter2";
        assert!(
            TagParser::parse_tag(input).is_err(),
            "Should not allow colon to start a new filter after an argument"
        );
    }

    #[test]
    fn test_i18n_whitespace() {
        let input = "value|default:_( 'hello' )";
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result,
            vec![TagAttr {
                key: None,
                value: TagValue {
                    token: TagToken {
                        token: "value".to_string(),
                        start_index: 0,
                        end_index: 5,
                        line_col: (1, 1),
                    },
                    children: vec![],
                    spread: None,
                    filters: vec![TagValueFilter {
                        token: TagToken {
                            token: "default".to_string(),
                            start_index: 6,
                            end_index: 13,
                            line_col: (1, 7),
                        },
                        arg: Some(TagValue {
                            token: TagToken {
                                token: "_('hello')".to_string(),
                                start_index: 14,
                                end_index: 26,
                                line_col: (1, 15),
                            },
                            children: vec![],
                            kind: ValueKind::Translation,
                            spread: None,
                            filters: vec![],
                            start_index: 13,
                            end_index: 26,
                            line_col: (1, 14),
                        }),
                        start_index: 5,
                        end_index: 26,
                        line_col: (1, 6),
                    }],
                    kind: ValueKind::Variable,
                    start_index: 0,
                    end_index: 26,
                    line_col: (1, 1),
                },
                start_index: 0,
                end_index: 26,
                line_col: (1, 1),
            }]
        );
    }

    #[test]
    fn test_i18n_comments() {
        let input = "value|default:_({# open paren #}'hello'{# close paren #})";
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result,
            vec![TagAttr {
                key: None,
                value: TagValue {
                    token: TagToken {
                        token: "value".to_string(),
                        start_index: 0,
                        end_index: 5,
                        line_col: (1, 1),
                    },
                    children: vec![],
                    spread: None,
                    filters: vec![TagValueFilter {
                        token: TagToken {
                            token: "default".to_string(),
                            start_index: 6,
                            end_index: 13,
                            line_col: (1, 7),
                        },
                        arg: Some(TagValue {
                            token: TagToken {
                                token: "_('hello')".to_string(),
                                start_index: 14,
                                end_index: 57,
                                line_col: (1, 15),
                            },
                            children: vec![],
                            kind: ValueKind::Translation,
                            spread: None,
                            filters: vec![],
                            start_index: 13,
                            end_index: 57,
                            line_col: (1, 14),
                        }),
                        start_index: 5,
                        end_index: 57,
                        line_col: (1, 6),
                    }],
                    kind: ValueKind::Variable,
                    start_index: 0,
                    end_index: 57,
                    line_col: (1, 1),
                },
                start_index: 0,
                end_index: 57,
                line_col: (1, 1),
            }]
        );
    }

    #[test]
    fn test_list_empty() {
        // Empty list
        let input = "[]";
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result,
            vec![TagAttr {
                key: None,
                value: TagValue {
                    token: TagToken {
                        token: "[]".to_string(),
                        start_index: 0,
                        end_index: 2,
                        line_col: (1, 1),
                    },
                    children: vec![],
                    spread: None,
                    filters: vec![],
                    kind: ValueKind::List,
                    start_index: 0,
                    end_index: 2,
                    line_col: (1, 1),
                },
                start_index: 0,
                end_index: 2,
                line_col: (1, 1),
            }]
        );
    }

    #[test]
    fn test_list_basic() {
        // Simple list with numbers
        let input = "[1, 2, 3]";
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result,
            vec![TagAttr {
                key: None,
                value: TagValue {
                    token: TagToken {
                        token: "[1, 2, 3]".to_string(),
                        start_index: 0,
                        end_index: 9,
                        line_col: (1, 1),
                    },
                    children: vec![
                        TagValue {
                            token: TagToken {
                                token: "1".to_string(),
                                start_index: 1,
                                end_index: 2,
                                line_col: (1, 2),
                            },
                            spread: None,
                            filters: vec![],
                            children: vec![],
                            kind: ValueKind::Int,
                            start_index: 1,
                            end_index: 2,
                            line_col: (1, 2),
                        },
                        TagValue {
                            token: TagToken {
                                token: "2".to_string(),
                                start_index: 4,
                                end_index: 5,
                                line_col: (1, 5),
                            },
                            spread: None,
                            filters: vec![],
                            children: vec![],
                            kind: ValueKind::Int,
                            start_index: 4,
                            end_index: 5,
                            line_col: (1, 5),
                        },
                        TagValue {
                            token: TagToken {
                                token: "3".to_string(),
                                start_index: 7,
                                end_index: 8,
                                line_col: (1, 8),
                            },
                            spread: None,
                            filters: vec![],
                            children: vec![],
                            kind: ValueKind::Int,
                            start_index: 7,
                            end_index: 8,
                            line_col: (1, 8),
                        },
                    ],
                    spread: None,
                    filters: vec![],
                    kind: ValueKind::List,
                    start_index: 0,
                    end_index: 9,
                    line_col: (1, 1),
                },
                start_index: 0,
                end_index: 9,
                line_col: (1, 1),
            }]
        );
    }

    #[test]
    fn test_list_mixed() {
        // List with mixed types
        let input = "[42, 'hello', my_var]";
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result,
            vec![TagAttr {
                key: None,
                value: TagValue {
                    token: TagToken {
                        token: "[42, 'hello', my_var]".to_string(),
                        start_index: 0,
                        end_index: 21,
                        line_col: (1, 1),
                    },
                    children: vec![
                        TagValue {
                            token: TagToken {
                                token: "42".to_string(),
                                start_index: 1,
                                end_index: 3,
                                line_col: (1, 2),
                            },
                            spread: None,
                            filters: vec![],
                            children: vec![],
                            kind: ValueKind::Int,
                            start_index: 1,
                            end_index: 3,
                            line_col: (1, 2),
                        },
                        TagValue {
                            token: TagToken {
                                token: "'hello'".to_string(),
                                start_index: 5,
                                end_index: 12,
                                line_col: (1, 6),
                            },
                            spread: None,
                            filters: vec![],
                            children: vec![],
                            kind: ValueKind::String,
                            start_index: 5,
                            end_index: 12,
                            line_col: (1, 6),
                        },
                        TagValue {
                            token: TagToken {
                                token: "my_var".to_string(),
                                start_index: 14,
                                end_index: 20,
                                line_col: (1, 15),
                            },
                            spread: None,
                            filters: vec![],
                            children: vec![],
                            kind: ValueKind::Variable,
                            start_index: 14,
                            end_index: 20,
                            line_col: (1, 15),
                        },
                    ],
                    spread: None,
                    filters: vec![],
                    kind: ValueKind::List,
                    start_index: 0,
                    end_index: 21,
                    line_col: (1, 1),
                },
                start_index: 0,
                end_index: 21,
                line_col: (1, 1),
            }]
        );
    }

    #[test]
    fn test_list_filter() {
        // List with filter on the entire list
        let input = "[1, 2, 3]|first";
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result,
            vec![TagAttr {
                key: None,
                value: TagValue {
                    token: TagToken {
                        token: "[1, 2, 3]".to_string(),
                        start_index: 0,
                        end_index: 9,
                        line_col: (1, 1),
                    },
                    children: vec![
                        TagValue {
                            token: TagToken {
                                token: "1".to_string(),
                                start_index: 1,
                                end_index: 2,
                                line_col: (1, 2),
                            },
                            spread: None,
                            filters: vec![],
                            children: vec![],
                            kind: ValueKind::Int,
                            start_index: 1,
                            end_index: 2,
                            line_col: (1, 2),
                        },
                        TagValue {
                            token: TagToken {
                                token: "2".to_string(),
                                start_index: 4,
                                end_index: 5,
                                line_col: (1, 5),
                            },
                            spread: None,
                            filters: vec![],
                            children: vec![],
                            kind: ValueKind::Int,
                            start_index: 4,
                            end_index: 5,
                            line_col: (1, 5),
                        },
                        TagValue {
                            token: TagToken {
                                token: "3".to_string(),
                                start_index: 7,
                                end_index: 8,
                                line_col: (1, 8),
                            },
                            spread: None,
                            filters: vec![],
                            children: vec![],
                            kind: ValueKind::Int,
                            start_index: 7,
                            end_index: 8,
                            line_col: (1, 8),
                        },
                    ],
                    spread: None,
                    filters: vec![TagValueFilter {
                        token: TagToken {
                            token: "first".to_string(),
                            start_index: 10,
                            end_index: 15,
                            line_col: (1, 11),
                        },
                        arg: None,
                        start_index: 9,
                        end_index: 15,
                        line_col: (1, 10),
                    }],
                    kind: ValueKind::List,
                    start_index: 0,
                    end_index: 15,
                    line_col: (1, 1),
                },
                start_index: 0,
                end_index: 15,
                line_col: (1, 1),
            }]
        );
    }

    #[test]
    fn test_list_filter_item() {
        // List with filters on individual items
        let input = "['hello'|upper, 'world'|title]";
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result,
            vec![TagAttr {
                key: None,
                value: TagValue {
                    token: TagToken {
                        token: "['hello'|upper, 'world'|title]".to_string(),
                        start_index: 0,
                        end_index: 30,
                        line_col: (1, 1),
                    },
                    children: vec![
                        TagValue {
                            token: TagToken {
                                token: "'hello'".to_string(),
                                start_index: 1,
                                end_index: 8,
                                line_col: (1, 2),
                            },
                            spread: None,
                            filters: vec![TagValueFilter {
                                arg: None,
                                token: TagToken {
                                    token: "upper".to_string(),
                                    start_index: 9,
                                    end_index: 14,
                                    line_col: (1, 10),
                                },
                                start_index: 8,
                                end_index: 14,
                                line_col: (1, 9),
                            }],
                            children: vec![],
                            kind: ValueKind::String,
                            start_index: 1,
                            end_index: 14,
                            line_col: (1, 2),
                        },
                        TagValue {
                            token: TagToken {
                                token: "'world'".to_string(),
                                start_index: 16,
                                end_index: 23,
                                line_col: (1, 17),
                            },
                            spread: None,
                            filters: vec![TagValueFilter {
                                arg: None,
                                token: TagToken {
                                    token: "title".to_string(),
                                    start_index: 24,
                                    end_index: 29,
                                    line_col: (1, 25),
                                },
                                start_index: 23,
                                end_index: 29,
                                line_col: (1, 24),
                            }],
                            children: vec![],
                            kind: ValueKind::String,
                            start_index: 16,
                            end_index: 29,
                            line_col: (1, 17),
                        },
                    ],
                    spread: None,
                    filters: vec![],
                    kind: ValueKind::List,
                    start_index: 0,
                    end_index: 30,
                    line_col: (1, 1),
                },
                start_index: 0,
                end_index: 30,
                line_col: (1, 1),
            }]
        );
    }

    #[test]
    fn test_list_filter_everywhere() {
        // List with both item filters and list filter
        let input = "['a'|upper, 'b'|upper]|join:','";
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result,
            vec![TagAttr {
                key: None,
                value: TagValue {
                    token: TagToken {
                        token: "['a'|upper, 'b'|upper]".to_string(),
                        start_index: 0,
                        end_index: 22,
                        line_col: (1, 1),
                    },
                    children: vec![
                        TagValue {
                            token: TagToken {
                                token: "'a'".to_string(),
                                start_index: 1,
                                end_index: 4,
                                line_col: (1, 2),
                            },
                            spread: None,
                            filters: vec![TagValueFilter {
                                arg: None,
                                token: TagToken {
                                    token: "upper".to_string(),
                                    start_index: 5,
                                    end_index: 10,
                                    line_col: (1, 6),
                                },
                                start_index: 4,
                                end_index: 10,
                                line_col: (1, 5),
                            }],
                            children: vec![],
                            kind: ValueKind::String,
                            start_index: 1,
                            end_index: 10,
                            line_col: (1, 2),
                        },
                        TagValue {
                            token: TagToken {
                                token: "'b'".to_string(),
                                start_index: 12,
                                end_index: 15,
                                line_col: (1, 13),
                            },
                            spread: None,
                            filters: vec![TagValueFilter {
                                arg: None,
                                token: TagToken {
                                    token: "upper".to_string(),
                                    start_index: 16,
                                    end_index: 21,
                                    line_col: (1, 17),
                                },
                                start_index: 15,
                                end_index: 21,
                                line_col: (1, 16),
                            }],
                            children: vec![],
                            kind: ValueKind::String,
                            start_index: 12,
                            end_index: 21,
                            line_col: (1, 13),
                        },
                    ],
                    spread: None,
                    filters: vec![TagValueFilter {
                        arg: Some(TagValue {
                            token: TagToken {
                                token: "','".to_string(),
                                start_index: 28,
                                end_index: 31,
                                line_col: (1, 29),
                            },
                            spread: None,
                            filters: vec![],
                            children: vec![],
                            kind: ValueKind::String,
                            start_index: 27,
                            end_index: 31,
                            line_col: (1, 28),
                        }),
                        token: TagToken {
                            token: "join".to_string(),
                            start_index: 23,
                            end_index: 27,
                            line_col: (1, 24),
                        },
                        start_index: 22,
                        end_index: 31,
                        line_col: (1, 23),
                    }],
                    kind: ValueKind::List,
                    start_index: 0,
                    end_index: 31,
                    line_col: (1, 1),
                },
                start_index: 0,
                end_index: 31,
                line_col: (1, 1),
            }]
        );
    }

    #[test]
    fn test_list_nested() {
        // Simple nested list
        let input = "[1, [2, 3], 4]";
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result,
            vec![TagAttr {
                key: None,
                value: TagValue {
                    token: TagToken {
                        token: "[1, [2, 3], 4]".to_string(),
                        start_index: 0,
                        end_index: 14,
                        line_col: (1, 1),
                    },
                    children: vec![
                        TagValue {
                            token: TagToken {
                                token: "1".to_string(),
                                start_index: 1,
                                end_index: 2,
                                line_col: (1, 2),
                            },
                            spread: None,
                            filters: vec![],
                            children: vec![],
                            kind: ValueKind::Int,
                            start_index: 1,
                            end_index: 2,
                            line_col: (1, 2),
                        },
                        TagValue {
                            token: TagToken {
                                token: "[2, 3]".to_string(),
                                start_index: 4,
                                end_index: 10,
                                line_col: (1, 5),
                            },
                            children: vec![
                                TagValue {
                                    token: TagToken {
                                        token: "2".to_string(),
                                        start_index: 5,
                                        end_index: 6,
                                        line_col: (1, 6),
                                    },
                                    spread: None,
                                    filters: vec![],
                                    children: vec![],
                                    kind: ValueKind::Int,
                                    start_index: 5,
                                    end_index: 6,
                                    line_col: (1, 6),
                                },
                                TagValue {
                                    token: TagToken {
                                        token: "3".to_string(),
                                        start_index: 8,
                                        end_index: 9,
                                        line_col: (1, 9),
                                    },
                                    spread: None,
                                    filters: vec![],
                                    children: vec![],
                                    kind: ValueKind::Int,
                                    start_index: 8,
                                    end_index: 9,
                                    line_col: (1, 9),
                                },
                            ],
                            spread: None,
                            filters: vec![],
                            kind: ValueKind::List,
                            start_index: 4,
                            end_index: 10,
                            line_col: (1, 5),
                        },
                        TagValue {
                            token: TagToken {
                                token: "4".to_string(),
                                start_index: 12,
                                end_index: 13,
                                line_col: (1, 13),
                            },
                            spread: None,
                            filters: vec![],
                            children: vec![],
                            kind: ValueKind::Int,
                            start_index: 12,
                            end_index: 13,
                            line_col: (1, 13),
                        },
                    ],
                    spread: None,
                    filters: vec![],
                    kind: ValueKind::List,
                    start_index: 0,
                    end_index: 14,
                    line_col: (1, 1),
                },
                start_index: 0,
                end_index: 14,
                line_col: (1, 1),
            }]
        );
    }

    #[test]
    fn test_list_nested_filter() {
        // Nested list with filters
        let input = "[[1, 2]|first, [3, 4]|last]|join:','";
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result,
            vec![TagAttr {
                key: None,
                value: TagValue {
                    token: TagToken {
                        token: "[[1, 2]|first, [3, 4]|last]".to_string(),
                        start_index: 0,
                        end_index: 27,
                        line_col: (1, 1),
                    },
                    children: vec![
                        TagValue {
                            token: TagToken {
                                token: "[1, 2]".to_string(),
                                start_index: 1,
                                end_index: 7,
                                line_col: (1, 2),
                            },
                            children: vec![
                                TagValue {
                                    token: TagToken {
                                        token: "1".to_string(),
                                        start_index: 2,
                                        end_index: 3,
                                        line_col: (1, 3),
                                    },
                                    spread: None,
                                    filters: vec![],
                                    children: vec![],
                                    kind: ValueKind::Int,
                                    start_index: 2,
                                    end_index: 3,
                                    line_col: (1, 3),
                                },
                                TagValue {
                                    token: TagToken {
                                        token: "2".to_string(),
                                        start_index: 5,
                                        end_index: 6,
                                        line_col: (1, 6),
                                    },
                                    spread: None,
                                    filters: vec![],
                                    children: vec![],
                                    kind: ValueKind::Int,
                                    start_index: 5,
                                    end_index: 6,
                                    line_col: (1, 6),
                                },
                            ],
                            spread: None,
                            filters: vec![TagValueFilter {
                                arg: None,
                                token: TagToken {
                                    token: "first".to_string(),
                                    start_index: 8,
                                    end_index: 13,
                                    line_col: (1, 9),
                                },
                                start_index: 7,
                                end_index: 13,
                                line_col: (1, 8),
                            }],
                            kind: ValueKind::List,
                            start_index: 1,
                            end_index: 13,
                            line_col: (1, 2),
                        },
                        TagValue {
                            token: TagToken {
                                token: "[3, 4]".to_string(),
                                start_index: 15,
                                end_index: 21,
                                line_col: (1, 16),
                            },
                            children: vec![
                                TagValue {
                                    token: TagToken {
                                        token: "3".to_string(),
                                        start_index: 16,
                                        end_index: 17,
                                        line_col: (1, 17),
                                    },
                                    spread: None,
                                    filters: vec![],
                                    children: vec![],
                                    kind: ValueKind::Int,
                                    start_index: 16,
                                    end_index: 17,
                                    line_col: (1, 17),
                                },
                                TagValue {
                                    token: TagToken {
                                        token: "4".to_string(),
                                        start_index: 19,
                                        end_index: 20,
                                        line_col: (1, 20),
                                    },
                                    spread: None,
                                    filters: vec![],
                                    children: vec![],
                                    kind: ValueKind::Int,
                                    start_index: 19,
                                    end_index: 20,
                                    line_col: (1, 20),
                                },
                            ],
                            spread: None,
                            filters: vec![TagValueFilter {
                                arg: None,
                                token: TagToken {
                                    token: "last".to_string(),
                                    start_index: 22,
                                    end_index: 26,
                                    line_col: (1, 23),
                                },
                                start_index: 21,
                                end_index: 26,
                                line_col: (1, 22),
                            }],
                            kind: ValueKind::List,
                            start_index: 15,
                            end_index: 26,
                            line_col: (1, 16),
                        },
                    ],
                    spread: None,
                    filters: vec![TagValueFilter {
                        arg: Some(TagValue {
                            token: TagToken {
                                token: "','".to_string(),
                                start_index: 33,
                                end_index: 36,
                                line_col: (1, 34),
                            },
                            spread: None,
                            filters: vec![],
                            children: vec![],
                            kind: ValueKind::String,
                            start_index: 32,
                            end_index: 36,
                            line_col: (1, 33),
                        }),
                        token: TagToken {
                            token: "join".to_string(),
                            start_index: 28,
                            end_index: 32,
                            line_col: (1, 29),
                        },
                        start_index: 27,
                        end_index: 36,
                        line_col: (1, 28),
                    }],
                    kind: ValueKind::List,
                    start_index: 0,
                    end_index: 36,
                    line_col: (1, 1),
                },
                start_index: 0,
                end_index: 36,
                line_col: (1, 1),
            }]
        );
    }

    #[test]
    fn test_list_whitespace() {
        // Test whitespace in list
        let input = "[ 1 , 2 , 3 ]";
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result,
            vec![TagAttr {
                key: None,
                value: TagValue {
                    token: TagToken {
                        token: "[ 1 , 2 , 3 ]".to_string(),
                        start_index: 0,
                        end_index: 13,
                        line_col: (1, 1),
                    },
                    children: vec![
                        TagValue {
                            token: TagToken {
                                token: "1".to_string(),
                                start_index: 2,
                                end_index: 3,
                                line_col: (1, 3),
                            },
                            spread: None,
                            filters: vec![],
                            children: vec![],
                            kind: ValueKind::Int,
                            start_index: 2,
                            end_index: 3,
                            line_col: (1, 3),
                        },
                        TagValue {
                            token: TagToken {
                                token: "2".to_string(),
                                start_index: 6,
                                end_index: 7,
                                line_col: (1, 7),
                            },
                            spread: None,
                            filters: vec![],
                            children: vec![],
                            kind: ValueKind::Int,
                            start_index: 6,
                            end_index: 7,
                            line_col: (1, 7),
                        },
                        TagValue {
                            token: TagToken {
                                token: "3".to_string(),
                                start_index: 10,
                                end_index: 11,
                                line_col: (1, 11),
                            },
                            spread: None,
                            filters: vec![],
                            children: vec![],
                            kind: ValueKind::Int,
                            start_index: 10,
                            end_index: 11,
                            line_col: (1, 11),
                        },
                    ],
                    spread: None,
                    filters: vec![],
                    kind: ValueKind::List,
                    start_index: 0,
                    end_index: 13,
                    line_col: (1, 1),
                },
                start_index: 0,
                end_index: 13,
                line_col: (1, 1),
            }]
        );
    }

    #[test]
    fn test_list_comments() {
        // Test comments in list
        let input =
            "{# before start #}[{# first #}1,{# second #}2,{# third #}3{# end #}]{# after end #}";
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result,
            vec![TagAttr {
                key: None,
                value: TagValue {
                    token: TagToken {
                        token: "[{# first #}1,{# second #}2,{# third #}3{# end #}]".to_string(),
                        start_index: 18,
                        end_index: 68,
                        line_col: (1, 19),
                    },
                    children: vec![
                        TagValue {
                            token: TagToken {
                                token: "1".to_string(),
                                start_index: 30,
                                end_index: 31,
                                line_col: (1, 31),
                            },
                            spread: None,
                            filters: vec![],
                            children: vec![],
                            kind: ValueKind::Int,
                            start_index: 30,
                            end_index: 31,
                            line_col: (1, 31),
                        },
                        TagValue {
                            token: TagToken {
                                token: "2".to_string(),
                                start_index: 44,
                                end_index: 45,
                                line_col: (1, 45),
                            },
                            spread: None,
                            filters: vec![],
                            children: vec![],
                            kind: ValueKind::Int,
                            start_index: 44,
                            end_index: 45,
                            line_col: (1, 45),
                        },
                        TagValue {
                            token: TagToken {
                                token: "3".to_string(),
                                start_index: 57,
                                end_index: 58,
                                line_col: (1, 58),
                            },
                            spread: None,
                            filters: vec![],
                            children: vec![],
                            kind: ValueKind::Int,
                            start_index: 57,
                            end_index: 58,
                            line_col: (1, 58),
                        },
                    ],
                    spread: None,
                    filters: vec![],
                    kind: ValueKind::List,
                    start_index: 18,
                    end_index: 68,
                    line_col: (1, 19),
                },
                start_index: 18,
                end_index: 68,
                line_col: (1, 19),
            }]
        );
    }

    #[test]
    fn test_list_trailing_comma() {
        let input = "[1, 2, 3,]";
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result,
            vec![TagAttr {
                key: None,
                value: TagValue {
                    token: TagToken {
                        token: "[1, 2, 3,]".to_string(),
                        start_index: 0,
                        end_index: 10,
                        line_col: (1, 1),
                    },
                    children: vec![
                        TagValue {
                            token: TagToken {
                                token: "1".to_string(),
                                start_index: 1,
                                end_index: 2,
                                line_col: (1, 2),
                            },
                            spread: None,
                            filters: vec![],
                            children: vec![],
                            kind: ValueKind::Int,
                            start_index: 1,
                            end_index: 2,
                            line_col: (1, 2),
                        },
                        TagValue {
                            token: TagToken {
                                token: "2".to_string(),
                                start_index: 4,
                                end_index: 5,
                                line_col: (1, 5),
                            },
                            spread: None,
                            filters: vec![],
                            children: vec![],
                            kind: ValueKind::Int,
                            start_index: 4,
                            end_index: 5,
                            line_col: (1, 5),
                        },
                        TagValue {
                            token: TagToken {
                                token: "3".to_string(),
                                start_index: 7,
                                end_index: 8,
                                line_col: (1, 8),
                            },
                            spread: None,
                            filters: vec![],
                            children: vec![],
                            kind: ValueKind::Int,
                            start_index: 7,
                            end_index: 8,
                            line_col: (1, 8),
                        },
                    ],
                    spread: None,
                    filters: vec![],
                    kind: ValueKind::List,
                    start_index: 0,
                    end_index: 10,
                    line_col: (1, 1),
                },
                start_index: 0,
                end_index: 10,
                line_col: (1, 1),
            }]
        );
    }

    #[test]
    fn test_list_spread() {
        let input =
            "[1, *[2, 3], *{'a': 1}, *my_list, *'xyz', *_('hello'), *'{{ var }}', *3.14, 4]";
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result,
            vec![TagAttr {
                key: None,
                value: TagValue {
                    token: TagToken {
                        token: "[1, *[2, 3], *{'a': 1}, *my_list, *'xyz', *_('hello'), *'{{ var }}', *3.14, 4]".to_string(),
                        start_index: 0,
                        end_index: 78,
                        line_col: (1, 1),
                    },
                    children: vec![
                        TagValue {
                            token: TagToken {
                                token: "1".to_string(),
                                start_index: 1,
                                end_index: 2,
                                line_col: (1, 2),
                            },
                            spread: None,
                            filters: vec![],
                            children: vec![],
                            kind: ValueKind::Int,
                            start_index: 1,
                            end_index: 2,
                            line_col: (1, 2),
                        },
                        TagValue {
                            token: TagToken {
                                token: "[2, 3]".to_string(),
                                start_index: 5,
                                end_index: 11,
                                line_col: (1, 6),
                            },
                            children: vec![
                                TagValue {
                                    token: TagToken {
                                        token: "2".to_string(),
                                        start_index: 6,
                                        end_index: 7,
                                        line_col: (1, 7),
                                    },
                                    spread: None,
                                    filters: vec![],
                                    children: vec![],
                                    kind: ValueKind::Int,
                                    start_index: 6,
                                    end_index: 7,
                                    line_col: (1, 7),
                                },
                                TagValue {
                                    token: TagToken {
                                        token: "3".to_string(),
                                        start_index: 9,
                                        end_index: 10,
                                        line_col: (1, 10),
                                    },
                                    spread: None,
                                    filters: vec![],
                                    children: vec![],
                                    kind: ValueKind::Int,
                                    start_index: 9,
                                    end_index: 10,
                                    line_col: (1, 10),
                                },
                            ],
                            spread: Some("*".to_string()),
                            filters: vec![],
                            kind: ValueKind::List,
                            start_index: 4,
                            end_index: 11,
                            line_col: (1, 5),
                        },
                        TagValue {
                            token: TagToken {
                                token: "{'a': 1}".to_string(),
                                start_index: 14,
                                end_index: 22,
                                line_col: (1, 15),
                            },
                            children: vec![
                                TagValue {
                                    token: TagToken {
                                        token: "'a'".to_string(),
                                        start_index: 15,
                                        end_index: 18,
                                        line_col: (1, 16),
                                    },
                                    spread: None,
                                    filters: vec![],
                                    children: vec![],
                                    kind: ValueKind::String,
                                    start_index: 15,
                                    end_index: 18,
                                    line_col: (1, 16),
                                },
                                TagValue {
                                    token: TagToken {
                                        token: "1".to_string(),
                                        start_index: 20,
                                        end_index: 21,
                                        line_col: (1, 21),
                                    },
                                    spread: None,
                                    filters: vec![],
                                    children: vec![],
                                    kind: ValueKind::Int,
                                    start_index: 20,
                                    end_index: 21,
                                    line_col: (1, 21),
                                },
                            ],
                            spread: Some("*".to_string()),
                            filters: vec![],
                            kind: ValueKind::Dict,
                            start_index: 13,
                            end_index: 22,
                            line_col: (1, 14),
                        },
                        TagValue {
                            token: TagToken {
                                token: "my_list".to_string(),
                                start_index: 25,
                                end_index: 32,
                                line_col: (1, 26),
                            },
                            spread: Some("*".to_string()),
                            filters: vec![],
                            children: vec![],
                            kind: ValueKind::Variable,
                            start_index: 24,
                            end_index: 32,
                            line_col: (1, 25),
                        },
                        TagValue {
                            token: TagToken {
                                token: "'xyz'".to_string(),
                                start_index: 35,
                                end_index: 40,
                                line_col: (1, 36),
                            },
                            spread: Some("*".to_string()),
                            filters: vec![],
                            children: vec![],
                            kind: ValueKind::String,
                            start_index: 34,
                            end_index: 40,
                            line_col: (1, 35),
                        },
                        TagValue {
                            token: TagToken {
                                token: "_('hello')".to_string(),
                                start_index: 43,
                                end_index: 53,
                                line_col: (1, 44),
                            },
                            spread: Some("*".to_string()),
                            filters: vec![],
                            children: vec![],
                            kind: ValueKind::Translation,
                            start_index: 42,
                            end_index: 53,
                            line_col: (1, 43),
                        },
                        TagValue {
                            token: TagToken {
                                token: "'{{ var }}'".to_string(),
                                start_index: 56,
                                end_index: 67,
                                line_col: (1, 57),
                            },
                            spread: Some("*".to_string()),
                            filters: vec![],
                            children: vec![],
                            kind: ValueKind::Expression,
                            start_index: 55,
                            end_index: 67,
                            line_col: (1, 56),
                        },
                        TagValue {
                            token: TagToken {
                                token: "3.14".to_string(),
                                start_index: 70,
                                end_index: 74,
                                line_col: (1, 71),
                            },
                            spread: Some("*".to_string()),
                            filters: vec![],
                            children: vec![],
                            kind: ValueKind::Float,
                            start_index: 69,
                            end_index: 74,
                            line_col: (1, 70),
                        },
                        TagValue {
                            token: TagToken {
                                token: "4".to_string(),
                                start_index: 76,
                                end_index: 77,
                                line_col: (1, 77),
                            },
                            spread: None,
                            filters: vec![],
                            children: vec![],
                            kind: ValueKind::Int,
                            start_index: 76,
                            end_index: 77,
                            line_col: (1, 77),
                        },
                    ],
                    spread: None,
                    filters: vec![],
                    kind: ValueKind::List,
                    start_index: 0,
                    end_index: 78,
                    line_col: (1, 1),
                },
                start_index: 0,
                end_index: 78,
                line_col: (1, 1),
            }]
        );
    }

    #[test]
    fn test_list_spread_filter() {
        let input = "[1, *[2|upper, 3|lower], *{'a': 1}|default:empty, *my_list|join:\",\", *'xyz'|upper, *_('hello')|escape, *'{{ var }}'|safe, *3.14|round, 4|default:0]";
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result[0],
            TagAttr {
                key: None,
                value: TagValue {
                    token: TagToken {
                        token: "[1, *[2|upper, 3|lower], *{'a': 1}|default:empty, *my_list|join:\",\", *'xyz'|upper, *_('hello')|escape, *'{{ var }}'|safe, *3.14|round, 4|default:0]".to_string(),
                        start_index: 0,
                        end_index: 147,
                        line_col: (1, 1),
                    },
                    children: vec![
                        TagValue {
                            token: TagToken {
                                token: "1".to_string(),
                                start_index: 1,
                                end_index: 2,
                                line_col: (1, 2),
                            },
                            spread: None,
                            filters: vec![],
                            children: vec![],
                            kind: ValueKind::Int,
                            start_index: 1,
                            end_index: 2,
                            line_col: (1, 2),
                        },
                        TagValue {
                            token: TagToken {
                                token: "[2|upper, 3|lower]".to_string(),
                                start_index: 5,
                                end_index: 23,
                                line_col: (1, 6),
                            },
                            children: vec![
                                TagValue {
                                    token: TagToken {
                                        token: "2".to_string(),
                                        start_index: 6,
                                        end_index: 7,
                                        line_col: (1, 7),
                                    },
                                    spread: None,
                                    children: vec![],
                                    filters: vec![TagValueFilter {
                                        arg: None,
                                        token: TagToken {
                                            token: "upper".to_string(),
                                            start_index: 8,
                                            end_index: 13,
                                            line_col: (1, 9),
                                        },
                                        start_index: 7,
                                        end_index: 13,
                                        line_col: (1, 8),
                                    }],
                                    kind: ValueKind::Int,
                                    start_index: 6,
                                    end_index: 13,
                                    line_col: (1, 7),
                                },
                                TagValue {
                                    token: TagToken {
                                        token: "3".to_string(),
                                        start_index: 15,
                                        end_index: 16,
                                        line_col: (1, 16),
                                    },
                                    spread: None,
                                    children: vec![],
                                    filters: vec![TagValueFilter {
                                        arg: None,
                                        token: TagToken {
                                            token: "lower".to_string(),
                                            start_index: 17,
                                            end_index: 22,
                                            line_col: (1, 18),
                                        },
                                        start_index: 16,
                                        end_index: 22,
                                        line_col: (1, 17),
                                    }],
                                    kind: ValueKind::Int,
                                    start_index: 15,
                                    end_index: 22,
                                    line_col: (1, 16),
                                },
                            ],
                            spread: Some("*".to_string()),
                            filters: vec![],
                            kind: ValueKind::List,
                            start_index: 4,
                            end_index: 23,
                            line_col: (1, 5),
                        },
                        TagValue {
                            token: TagToken {
                                token: "{'a': 1}".to_string(),
                                start_index: 26,
                                end_index: 34,
                                line_col: (1, 27),
                            },
                            children: vec![
                                TagValue {
                                    token: TagToken {
                                        token: "'a'".to_string(),
                                        start_index: 27,
                                        end_index: 30,
                                        line_col: (1, 28),
                                    },
                                    spread: None,
                                    filters: vec![],
                                    children: vec![],
                                    kind: ValueKind::String,
                                    start_index: 27,
                                    end_index: 30,
                                    line_col: (1, 28),
                                },
                                TagValue {
                                    token: TagToken {
                                        token: "1".to_string(),
                                        start_index: 32,
                                        end_index: 33,
                                        line_col: (1, 33),
                                    },
                                    spread: None,
                                    filters: vec![],
                                    children: vec![],
                                    kind: ValueKind::Int,
                                    start_index: 32,
                                    end_index: 33,
                                    line_col: (1, 33),
                                },
                            ],
                            spread: Some("*".to_string()),
                            filters: vec![TagValueFilter {
                                token: TagToken {
                                    token: "default".to_string(),
                                    start_index: 35,
                                    end_index: 42,
                                    line_col: (1, 36),
                                },
                                arg: Some(TagValue {
                                    token: TagToken {
                                        token: "empty".to_string(),
                                        start_index: 43,
                                        end_index: 48,
                                        line_col: (1, 44),
                                    },
                                    spread: None,
                                    filters: vec![],
                                    children: vec![],
                                    kind: ValueKind::Variable,
                                    start_index: 42,
                                    end_index: 48,
                                    line_col: (1, 43),
                                }),
                                start_index: 34,
                                end_index: 48,
                                line_col: (1, 35),
                            }],
                            kind: ValueKind::Dict,
                            start_index: 25,
                            end_index: 48,
                            line_col: (1, 26),
                        },
                        TagValue {
                            token: TagToken {
                                token: "my_list".to_string(),
                                start_index: 51,
                                end_index: 58,
                                line_col: (1, 52),
                            },
                            spread: Some("*".to_string()),
                            children: vec![],
                            filters: vec![TagValueFilter {
                                token: TagToken {
                                    token: "join".to_string(),
                                    start_index: 59,
                                    end_index: 63,
                                    line_col: (1, 60),
                                },
                                arg: Some(TagValue {
                                    token: TagToken {
                                        token: "\",\"".to_string(),
                                        start_index: 64,
                                        end_index: 67,
                                        line_col: (1, 65),
                                    },
                                    spread: None,
                                    filters: vec![],
                                    children: vec![],
                                    kind: ValueKind::String,
                                    start_index: 63,
                                    end_index: 67,
                                    line_col: (1, 64),
                                }),
                                start_index: 58,
                                end_index: 67,
                                line_col: (1, 59),
                            }],
                            kind: ValueKind::Variable,
                            start_index: 50,
                            end_index: 67,
                            line_col: (1, 51),
                        },
                        TagValue {
                            token: TagToken {
                                token: "'xyz'".to_string(),
                                start_index: 70,
                                end_index: 75,
                                line_col: (1, 71),
                            },
                            spread: Some("*".to_string()),
                            children: vec![],
                            filters: vec![TagValueFilter {
                                token: TagToken {
                                    token: "upper".to_string(),
                                    start_index: 76,
                                    end_index: 81,
                                    line_col: (1, 77),
                                },
                                arg: None,
                                start_index: 75,
                                end_index: 81,
                                line_col: (1, 76),
                            }],
                            kind: ValueKind::String,
                            start_index: 69,
                            end_index: 81,
                            line_col: (1, 70),
                        },
                        TagValue {
                            token: TagToken {
                                token: "_('hello')".to_string(),
                                start_index: 84,
                                end_index: 94,
                                line_col: (1, 85),
                            },
                            spread: Some("*".to_string()),
                            children: vec![],
                            filters: vec![TagValueFilter {
                                token: TagToken {
                                    token: "escape".to_string(),
                                    start_index: 95,
                                    end_index: 101,
                                    line_col: (1, 96),
                                },
                                arg: None,
                                start_index: 94,
                                end_index: 101,
                                line_col: (1, 95),
                            }],
                            kind: ValueKind::Translation,
                            start_index: 83,
                            end_index: 101,
                            line_col: (1, 84),
                        },
                        TagValue {
                            token: TagToken {
                                token: "'{{ var }}'".to_string(),
                                start_index: 104,
                                end_index: 115,
                                line_col: (1, 105),
                            },
                            spread: Some("*".to_string()),
                            children: vec![],
                            filters: vec![TagValueFilter {
                                token: TagToken {
                                    token: "safe".to_string(),
                                    start_index: 116,
                                    end_index: 120,
                                    line_col: (1, 117),
                                },
                                arg: None,
                                start_index: 115,
                                end_index: 120,
                                line_col: (1, 116),
                            }],
                            kind: ValueKind::Expression,
                            start_index: 103,
                            end_index: 120,
                            line_col: (1, 104),
                        },
                        TagValue {
                            token: TagToken {
                                token: "3.14".to_string(),
                                start_index: 123,
                                end_index: 127,
                                line_col: (1, 124),
                            },
                            spread: Some("*".to_string()),
                            children: vec![],
                            filters: vec![TagValueFilter {
                                token: TagToken {
                                    token: "round".to_string(),
                                    start_index: 128,
                                    end_index: 133,
                                    line_col: (1, 129),
                                },
                                arg: None,
                                start_index: 127,
                                end_index: 133,
                                line_col: (1, 128),
                            }],
                            kind: ValueKind::Float,
                            start_index: 122,
                            end_index: 133,
                            line_col: (1, 123),
                        },
                        TagValue {
                            token: TagToken {
                                token: "4".to_string(),
                                start_index: 135,
                                end_index: 136,
                                line_col: (1, 136),
                            },
                            spread: None,
                            children: vec![],
                            filters: vec![TagValueFilter {
                                token: TagToken {
                                    token: "default".to_string(),
                                    start_index: 137,
                                    end_index: 144,
                                    line_col: (1, 138),
                                },
                                arg: Some(TagValue {
                                    token: TagToken {
                                        token: "0".to_string(),
                                        start_index: 145,
                                        end_index: 146,
                                        line_col: (1, 146),
                                    },
                                    spread: None,
                                    filters: vec![],
                                    children: vec![],
                                    kind: ValueKind::Int,
                                    start_index: 144,
                                    end_index: 146,
                                    line_col: (1, 145),
                                }),
                                start_index: 136,
                                end_index: 146,
                                line_col: (1, 137),
                            }],
                            kind: ValueKind::Int,
                            start_index: 135,
                            end_index: 146,
                            line_col: (1, 136),
                        },
                    ],
                    spread: None,
                    filters: vec![],
                    kind: ValueKind::List,
                    start_index: 0,
                    end_index: 147,
                    line_col: (1, 1),
                },
                start_index: 0,
                end_index: 147,
                line_col: (1, 1),
            }
        );
    }

    #[test]
    fn test_list_spread_invalid() {
        // Test asterisk at top level as value-only
        let input = "*value";
        assert!(
            TagParser::parse_tag(input).is_err(),
            "Should not allow asterisk operator at top level"
        );

        // Test asterisk in value position of key-value pair
        let input = "key=*value";
        assert!(
            TagParser::parse_tag(input).is_err(),
            "Should not allow asterisk operator in value position of key-value pair"
        );

        // Test asterisk in key position
        let input = "*key=value";
        assert!(
            TagParser::parse_tag(input).is_err(),
            "Should not allow asterisk operator in key position"
        );

        // Test asterisk with nested list at top level
        let input = "*[1, 2, 3]";
        assert!(
            TagParser::parse_tag(input).is_err(),
            "Should not allow asterisk operator with list at top level"
        );

        // Test asterisk with nested list in key-value pair
        let input = "key=*[1, 2, 3]";
        assert!(
            TagParser::parse_tag(input).is_err(),
            "Should not allow asterisk operator with list in key-value pair"
        );

        // Test combining spread operators
        let input = "...*[1, 2, 3]";
        assert!(
            TagParser::parse_tag(input).is_err(),
            "Should not allow combining spread operators"
        );

        // Test combining spread operators with variable
        let input = "...*my_list";
        assert!(
            TagParser::parse_tag(input).is_err(),
            "Should not allow combining spread operators with variable"
        );

        // Test combining spread operators
        let input = "*...[1, 2, 3]";
        assert!(
            TagParser::parse_tag(input).is_err(),
            "Should not allow combining spread operators"
        );
    }

    #[test]
    fn test_list_spread_comments() {
        // Test comments before / after spread
        let input = "[{# ... #}*{# ... #}1,*{# ... #}2,{# ... #}3]";
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result,
            vec![TagAttr {
                key: None,
                value: TagValue {
                    token: TagToken {
                        token: "[{# ... #}*{# ... #}1,*{# ... #}2,{# ... #}3]".to_string(),
                        start_index: 0,
                        end_index: 45,
                        line_col: (1, 1),
                    },
                    children: vec![
                        TagValue {
                            token: TagToken {
                                token: "1".to_string(),
                                start_index: 20,
                                end_index: 21,
                                line_col: (1, 21),
                            },
                            spread: Some("*".to_string()),
                            filters: vec![],
                            children: vec![],
                            kind: ValueKind::Int,
                            start_index: 19,
                            end_index: 21,
                            line_col: (1, 20),
                        },
                        TagValue {
                            token: TagToken {
                                token: "2".to_string(),
                                start_index: 32,
                                end_index: 33,
                                line_col: (1, 33),
                            },
                            spread: Some("*".to_string()),
                            filters: vec![],
                            children: vec![],
                            kind: ValueKind::Int,
                            start_index: 31,
                            end_index: 33,
                            line_col: (1, 32),
                        },
                        TagValue {
                            token: TagToken {
                                token: "3".to_string(),
                                start_index: 43,
                                end_index: 44,
                                line_col: (1, 44),
                            },
                            spread: None,
                            filters: vec![],
                            children: vec![],
                            kind: ValueKind::Int,
                            start_index: 43,
                            end_index: 44,
                            line_col: (1, 44),
                        },
                    ],
                    spread: None,
                    filters: vec![],
                    kind: ValueKind::List,
                    start_index: 0,
                    end_index: 45,
                    line_col: (1, 1),
                },
                start_index: 0,
                end_index: 45,
                line_col: (1, 1),
            }]
        );
    }

    #[test]
    fn test_list_spread_nested_comments() {
        // Test comments with nested spread
        let input = "{# c0 #}[1, {# c1 #}*{# c2 #}[2, {# c3 #}*{# c4 #}[3, 4]], 5]{# c5 #}";
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result,
            vec![TagAttr {
                key: None,
                value: TagValue {
                    token: TagToken {
                        token: "[1, {# c1 #}*{# c2 #}[2, {# c3 #}*{# c4 #}[3, 4]], 5]".to_string(),
                        start_index: 8,
                        end_index: 61,
                        line_col: (1, 9),
                    },
                    children: vec![
                        TagValue {
                            token: TagToken {
                                token: "1".to_string(),
                                start_index: 9,
                                end_index: 10,
                                line_col: (1, 10),
                            },
                            spread: None,
                            filters: vec![],
                            children: vec![],
                            kind: ValueKind::Int,
                            start_index: 9,
                            end_index: 10,
                            line_col: (1, 10),
                        },
                        TagValue {
                            token: TagToken {
                                token: "[2, {# c3 #}*{# c4 #}[3, 4]]".to_string(),
                                start_index: 29,
                                end_index: 57,
                                line_col: (1, 30),
                            },
                            children: vec![
                                TagValue {
                                    token: TagToken {
                                        token: "2".to_string(),
                                        start_index: 30,
                                        end_index: 31,
                                        line_col: (1, 31),
                                    },
                                    spread: None,
                                    children: vec![],
                                    filters: vec![],
                                    kind: ValueKind::Int,
                                    start_index: 30,
                                    end_index: 31,
                                    line_col: (1, 31),
                                },
                                TagValue {
                                    token: TagToken {
                                        token: "[3, 4]".to_string(),
                                        start_index: 50,
                                        end_index: 56,
                                        line_col: (1, 51),
                                    },
                                    children: vec![
                                        TagValue {
                                            token: TagToken {
                                                token: "3".to_string(),
                                                start_index: 51,
                                                end_index: 52,
                                                line_col: (1, 52),
                                            },
                                            spread: None,
                                            filters: vec![],
                                            children: vec![],
                                            kind: ValueKind::Int,
                                            start_index: 51,
                                            end_index: 52,
                                            line_col: (1, 52),
                                        },
                                        TagValue {
                                            token: TagToken {
                                                token: "4".to_string(),
                                                start_index: 54,
                                                end_index: 55,
                                                line_col: (1, 55),
                                            },
                                            spread: None,
                                            filters: vec![],
                                            children: vec![],
                                            kind: ValueKind::Int,
                                            start_index: 54,
                                            end_index: 55,
                                            line_col: (1, 55),
                                        },
                                    ],
                                    spread: Some("*".to_string()),
                                    filters: vec![],
                                    kind: ValueKind::List,
                                    start_index: 49,
                                    end_index: 56,
                                    line_col: (1, 50),
                                },
                            ],
                            spread: Some("*".to_string()),
                            filters: vec![],
                            kind: ValueKind::List,
                            start_index: 28,
                            end_index: 57,
                            line_col: (1, 29),
                        },
                        TagValue {
                            token: TagToken {
                                token: "5".to_string(),
                                start_index: 59,
                                end_index: 60,
                                line_col: (1, 60),
                            },
                            spread: None,
                            filters: vec![],
                            children: vec![],
                            kind: ValueKind::Int,
                            start_index: 59,
                            end_index: 60,
                            line_col: (1, 60),
                        },
                    ],
                    spread: None,
                    filters: vec![],
                    kind: ValueKind::List,
                    start_index: 8,
                    end_index: 61,
                    line_col: (1, 9),
                },
                start_index: 8,
                end_index: 61,
                line_col: (1, 9),
            }]
        );
    }

    #[test]
    fn test_dynamic_expression_negative() {
        // Test simple string without dynamic expression
        let input = "\"Hello\"";
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result[0],
            TagAttr {
                key: None,
                value: TagValue {
                    token: TagToken {
                        token: "\"Hello\"".to_string(),
                        start_index: 0,
                        end_index: 7,
                        line_col: (1, 1),
                    },
                    children: vec![],
                    spread: None,
                    filters: vec![],
                    kind: ValueKind::String,
                    start_index: 0,
                    end_index: 7,
                    line_col: (1, 1),
                },
                start_index: 0,
                end_index: 7,
                line_col: (1, 1),
            }
        );
    }

    #[test]
    fn test_dynamic_expression_block() {
        // Test string with {% tag %}
        let input = "\"Hello {% lorem w 1 %}\"";
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result[0],
            TagAttr {
                key: None,
                value: TagValue {
                    token: TagToken {
                        token: "\"Hello {% lorem w 1 %}\"".to_string(),
                        start_index: 0,
                        end_index: 23,
                        line_col: (1, 1),
                    },
                    children: vec![],
                    spread: None,
                    filters: vec![],
                    kind: ValueKind::Expression,
                    start_index: 0,
                    end_index: 23,
                    line_col: (1, 1),
                },
                start_index: 0,
                end_index: 23,
                line_col: (1, 1),
            }
        );
    }

    #[test]
    fn test_dynamic_expression_variable() {
        // Test string with {{ variable }}
        let input = "\"Hello {{ last_name }}\"";
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result[0],
            TagAttr {
                key: None,
                value: TagValue {
                    token: TagToken {
                        token: "\"Hello {{ last_name }}\"".to_string(),
                        start_index: 0,
                        end_index: 23,
                        line_col: (1, 1),
                    },
                    children: vec![],
                    spread: None,
                    filters: vec![],
                    kind: ValueKind::Expression,
                    start_index: 0,
                    end_index: 23,
                    line_col: (1, 1),
                },
                start_index: 0,
                end_index: 23,
                line_col: (1, 1),
            }
        );
    }

    #[test]
    fn test_dynamic_expression_comment() {
        // Test string with {# comment #}
        let input = "\"Hello {# TODO #}\"";
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result[0],
            TagAttr {
                key: None,
                value: TagValue {
                    token: TagToken {
                        token: "\"Hello {# TODO #}\"".to_string(),
                        start_index: 0,
                        end_index: 18,
                        line_col: (1, 1),
                    },
                    children: vec![],
                    spread: None,
                    filters: vec![],
                    kind: ValueKind::Expression,
                    start_index: 0,
                    end_index: 18,
                    line_col: (1, 1),
                },
                start_index: 0,
                end_index: 18,
                line_col: (1, 1),
            }
        );
    }

    #[test]
    fn test_dynamic_expression_mixed() {
        // Test string with multiple expressions
        let input = "\"Hello {{ first_name }} {% lorem 1 w %} {# TODO #}\"";
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result[0],
            TagAttr {
                key: None,
                value: TagValue {
                    token: TagToken {
                        token: "\"Hello {{ first_name }} {% lorem 1 w %} {# TODO #}\"".to_string(),
                        start_index: 0,
                        end_index: 51,
                        line_col: (1, 1),
                    },
                    children: vec![],
                    spread: None,
                    filters: vec![],
                    kind: ValueKind::Expression,
                    start_index: 0,
                    end_index: 51,
                    line_col: (1, 1),
                },
                start_index: 0,
                end_index: 51,
                line_col: (1, 1),
            }
        );
    }

    #[test]
    fn test_dynamic_expression_invalid() {
        // Test incomplete expressions (should not be marked as dynamic)
        let inputs = vec![
            "\"Hello {{ first_name\"",
            "\"Hello {% first_name\"",
            "\"Hello {# first_name\"",
            "\"Hello {{ first_name %}\"",
            "\"Hello first_name }}\"",
            "\"Hello }} first_name {{\"",
        ];
        for input in inputs {
            let result = TagParser::parse_tag(input).unwrap();
            assert_eq!(
                result[0],
                TagAttr {
                    key: None,
                    value: TagValue {
                        token: TagToken {
                            token: input.to_string(),
                            start_index: 0,
                            end_index: input.len(),
                            line_col: (1, 1),
                        },
                        children: vec![],
                        spread: None,
                        filters: vec![],
                        kind: ValueKind::String,
                        start_index: 0,
                        end_index: input.len(),
                        line_col: (1, 1),
                    },
                    start_index: 0,
                    end_index: input.len(),
                    line_col: (1, 1),
                }
            );
        }
    }

    #[test]
    fn test_dynamic_expression_filter_arg() {
        // Test that dynamic expressions are detected in filter args
        let input = "value|default:\"{{ var }}\"";
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result[0],
            TagAttr {
                key: None,
                value: TagValue {
                    token: TagToken {
                        token: "value".to_string(),
                        start_index: 0,
                        end_index: 5,
                        line_col: (1, 1),
                    },
                    children: vec![],
                    spread: None,
                    filters: vec![TagValueFilter {
                        token: TagToken {
                            token: "default".to_string(),
                            start_index: 6,
                            end_index: 13,
                            line_col: (1, 7),
                        },
                        arg: Some(TagValue {
                            token: TagToken {
                                token: "\"{{ var }}\"".to_string(),
                                start_index: 14,
                                end_index: 25,
                                line_col: (1, 15),
                            },
                            children: vec![],
                            spread: None,
                            filters: vec![],
                            kind: ValueKind::Expression,
                            start_index: 13,
                            end_index: 25,
                            line_col: (1, 14),
                        }),
                        start_index: 5,
                        end_index: 25,
                        line_col: (1, 6),
                    }],
                    kind: ValueKind::Variable,
                    start_index: 0,
                    end_index: 25,
                    line_col: (1, 1),
                },
                start_index: 0,
                end_index: 25,
                line_col: (1, 1),
            }
        );
    }

    #[test]
    fn test_dynamic_expression_i18n() {
        // Test that dynamic expressions are not detected in i18n strings
        let input = "_(\"{{ var }}\")";
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result[0],
            TagAttr {
                key: None,
                value: TagValue {
                    token: TagToken {
                        token: "_(\"{{ var }}\")".to_string(),
                        start_index: 0,
                        end_index: 14,
                        line_col: (1, 1),
                    },
                    children: vec![],
                    spread: None,
                    filters: vec![],
                    kind: ValueKind::Translation,
                    start_index: 0,
                    end_index: 14,
                    line_col: (1, 1),
                },
                start_index: 0,
                end_index: 14,
                line_col: (1, 1),
            }
        );
    }

    #[test]
    fn test_dict_empty() {
        // Empty dict
        let input = "{}";
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result,
            vec![TagAttr {
                key: None,
                value: TagValue {
                    token: TagToken {
                        token: "{}".to_string(),
                        start_index: 0,
                        end_index: 2,
                        line_col: (1, 1),
                    },
                    children: vec![],
                    spread: None,
                    filters: vec![],
                    kind: ValueKind::Dict,
                    start_index: 0,
                    end_index: 2,
                    line_col: (1, 1),
                },
                start_index: 0,
                end_index: 2,
                line_col: (1, 1),
            }]
        );
    }

    #[test]
    fn test_dict_basic() {
        // Simple dict with string key and value
        let input = r#"{"key": "value"}"#;
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result,
            vec![TagAttr {
                key: None,
                value: TagValue {
                    token: TagToken {
                        token: r#"{"key": "value"}"#.to_string(),
                        start_index: 0,
                        end_index: 16,
                        line_col: (1, 1),
                    },
                    children: vec![
                        TagValue {
                            token: TagToken {
                                token: "\"key\"".to_string(),
                                start_index: 1,
                                end_index: 6,
                                line_col: (1, 2),
                            },
                            children: vec![],
                            spread: None,
                            filters: vec![],
                            kind: ValueKind::String,
                            start_index: 1,
                            end_index: 6,
                            line_col: (1, 2),
                        },
                        TagValue {
                            token: TagToken {
                                token: "\"value\"".to_string(),
                                start_index: 8,
                                end_index: 15,
                                line_col: (1, 9),
                            },
                            children: vec![],
                            spread: None,
                            filters: vec![],
                            kind: ValueKind::String,
                            start_index: 8,
                            end_index: 15,
                            line_col: (1, 9),
                        }
                    ],
                    spread: None,
                    filters: vec![],
                    kind: ValueKind::Dict,
                    start_index: 0,
                    end_index: 16,
                    line_col: (1, 1),
                },
                start_index: 0,
                end_index: 16,
                line_col: (1, 1),
            }]
        );
    }

    #[test]
    fn test_dict_multiple() {
        // Dict with multiple key types
        let input = r#"{"key1": 42, my_var: "value2", _("hello"): var3}"#;
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result[0],
            TagAttr {
                key: None,
                value: TagValue {
                    token: TagToken {
                        token: r#"{"key1": 42, my_var: "value2", _("hello"): var3}"#.to_string(),
                        start_index: 0,
                        end_index: 48,
                        line_col: (1, 1),
                    },
                    children: vec![
                        TagValue {
                            token: TagToken {
                                token: "\"key1\"".to_string(),
                                start_index: 1,
                                end_index: 7,
                                line_col: (1, 2),
                            },
                            children: vec![],
                            spread: None,
                            filters: vec![],
                            kind: ValueKind::String,
                            start_index: 1,
                            end_index: 7,
                            line_col: (1, 2),
                        },
                        TagValue {
                            token: TagToken {
                                token: "42".to_string(),
                                start_index: 9,
                                end_index: 11,
                                line_col: (1, 10),
                            },
                            children: vec![],
                            spread: None,
                            filters: vec![],
                            kind: ValueKind::Int,
                            start_index: 9,
                            end_index: 11,
                            line_col: (1, 10),
                        },
                        TagValue {
                            token: TagToken {
                                token: "my_var".to_string(),
                                start_index: 13,
                                end_index: 19,
                                line_col: (1, 14),
                            },
                            children: vec![],
                            spread: None,
                            filters: vec![],
                            kind: ValueKind::Variable,
                            start_index: 13,
                            end_index: 19,
                            line_col: (1, 14),
                        },
                        TagValue {
                            token: TagToken {
                                token: "\"value2\"".to_string(),
                                start_index: 21,
                                end_index: 29,
                                line_col: (1, 22),
                            },
                            children: vec![],
                            spread: None,
                            filters: vec![],
                            kind: ValueKind::String,
                            start_index: 21,
                            end_index: 29,
                            line_col: (1, 22),
                        },
                        TagValue {
                            token: TagToken {
                                token: "_(\"hello\")".to_string(),
                                start_index: 31,
                                end_index: 41,
                                line_col: (1, 32),
                            },
                            children: vec![],
                            spread: None,
                            filters: vec![],
                            kind: ValueKind::Translation,
                            start_index: 31,
                            end_index: 41,
                            line_col: (1, 32),
                        },
                        TagValue {
                            token: TagToken {
                                token: "var3".to_string(),
                                start_index: 43,
                                end_index: 47,
                                line_col: (1, 44),
                            },
                            children: vec![],
                            spread: None,
                            filters: vec![],
                            kind: ValueKind::Variable,
                            start_index: 43,
                            end_index: 47,
                            line_col: (1, 44),
                        },
                    ],
                    spread: None,
                    filters: vec![],
                    kind: ValueKind::Dict,
                    start_index: 0,
                    end_index: 48,
                    line_col: (1, 1),
                },
                start_index: 0,
                end_index: 48,
                line_col: (1, 1),
            }
        );
    }

    #[test]
    fn test_dict_filters_key() {
        // Test filters on keys
        let input = r#"{"key"|upper|lower: "value"}"#;
        let result = TagParser::parse_tag(input).unwrap();

        assert_eq!(
            result,
            vec![TagAttr {
                key: None,
                value: TagValue {
                    token: TagToken {
                        token: r#"{"key"|upper|lower: "value"}"#.to_string(),
                        start_index: 0,
                        end_index: 28,
                        line_col: (1, 1),
                    },
                    children: vec![
                        TagValue {
                            token: TagToken {
                                token: "\"key\"".to_string(),
                                start_index: 1,
                                end_index: 6,
                                line_col: (1, 2),
                            },
                            children: vec![],
                            spread: None,
                            filters: vec![
                                TagValueFilter {
                                    arg: None,
                                    token: TagToken {
                                        token: "upper".to_string(),
                                        start_index: 7,
                                        end_index: 12,
                                        line_col: (1, 8),
                                    },
                                    start_index: 6,
                                    end_index: 12,
                                    line_col: (1, 7),
                                },
                                TagValueFilter {
                                    arg: None,
                                    token: TagToken {
                                        token: "lower".to_string(),
                                        start_index: 13,
                                        end_index: 18,
                                        line_col: (1, 14),
                                    },
                                    start_index: 12,
                                    end_index: 18,
                                    line_col: (1, 13),
                                },
                            ],
                            kind: ValueKind::String,
                            start_index: 1,
                            end_index: 18,
                            line_col: (1, 2),
                        },
                        TagValue {
                            token: TagToken {
                                token: "\"value\"".to_string(),
                                start_index: 20,
                                end_index: 27,
                                line_col: (1, 21),
                            },
                            children: vec![],
                            spread: None,
                            filters: vec![],
                            kind: ValueKind::String,
                            start_index: 20,
                            end_index: 27,
                            line_col: (1, 21),
                        },
                    ],
                    spread: None,
                    filters: vec![],
                    kind: ValueKind::Dict,
                    start_index: 0,
                    end_index: 28,
                    line_col: (1, 1),
                },
                start_index: 0,
                end_index: 28,
                line_col: (1, 1),
            }]
        );
    }

    #[test]
    fn test_dict_filters_value() {
        // Test filters on values
        let input = r#"{"key": "value"|upper|lower}"#;
        let result = TagParser::parse_tag(input).unwrap();

        assert_eq!(
            result,
            vec![TagAttr {
                key: None,
                value: TagValue {
                    token: TagToken {
                        token: r#"{"key": "value"|upper|lower}"#.to_string(),
                        start_index: 0,
                        end_index: 28,
                        line_col: (1, 1),
                    },
                    children: vec![
                        TagValue {
                            token: TagToken {
                                token: "\"key\"".to_string(),
                                start_index: 1,
                                end_index: 6,
                                line_col: (1, 2),
                            },
                            children: vec![],
                            spread: None,
                            filters: vec![],
                            kind: ValueKind::String,
                            start_index: 1,
                            end_index: 6,
                            line_col: (1, 2),
                        },
                        TagValue {
                            token: TagToken {
                                token: "\"value\"".to_string(),
                                start_index: 8,
                                end_index: 15,
                                line_col: (1, 9),
                            },
                            children: vec![],
                            spread: None,
                            filters: vec![
                                TagValueFilter {
                                    arg: None,
                                    token: TagToken {
                                        token: "upper".to_string(),
                                        start_index: 16,
                                        end_index: 21,
                                        line_col: (1, 17),
                                    },
                                    start_index: 15,
                                    end_index: 21,
                                    line_col: (1, 16),
                                },
                                TagValueFilter {
                                    arg: None,
                                    token: TagToken {
                                        token: "lower".to_string(),
                                        start_index: 22,
                                        end_index: 27,
                                        line_col: (1, 23),
                                    },
                                    start_index: 21,
                                    end_index: 27,
                                    line_col: (1, 22),
                                },
                            ],
                            kind: ValueKind::String,
                            start_index: 8,
                            end_index: 27,
                            line_col: (1, 9),
                        },
                    ],
                    spread: None,
                    filters: vec![],
                    kind: ValueKind::Dict,
                    start_index: 0,
                    end_index: 28,
                    line_col: (1, 1),
                },
                start_index: 0,
                end_index: 28,
                line_col: (1, 1),
            }]
        );
    }

    #[test]
    fn test_dict_filters() {
        // Test filter on entire dict
        let input = r#"{"key": "value"}|default:empty_dict"#;
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result,
            vec![TagAttr {
                key: None,
                value: TagValue {
                    token: TagToken {
                        token: r#"{"key": "value"}"#.to_string(),
                        start_index: 0,
                        end_index: 16,
                        line_col: (1, 1),
                    },
                    children: vec![
                        TagValue {
                            token: TagToken {
                                token: "\"key\"".to_string(),
                                start_index: 1,
                                end_index: 6,
                                line_col: (1, 2),
                            },
                            children: vec![],
                            spread: None,
                            filters: vec![],
                            kind: ValueKind::String,
                            start_index: 1,
                            end_index: 6,
                            line_col: (1, 2),
                        },
                        TagValue {
                            token: TagToken {
                                token: "\"value\"".to_string(),
                                start_index: 8,
                                end_index: 15,
                                line_col: (1, 9),
                            },
                            children: vec![],
                            spread: None,
                            filters: vec![],
                            kind: ValueKind::String,
                            start_index: 8,
                            end_index: 15,
                            line_col: (1, 9),
                        },
                    ],
                    spread: None,
                    filters: vec![TagValueFilter {
                        token: TagToken {
                            token: "default".to_string(),
                            start_index: 17,
                            end_index: 24,
                            line_col: (1, 18),
                        },
                        arg: Some(TagValue {
                            token: TagToken {
                                token: "empty_dict".to_string(),
                                start_index: 25,
                                end_index: 35,
                                line_col: (1, 26),
                            },
                            children: vec![],
                            spread: None,
                            filters: vec![],
                            kind: ValueKind::Variable,
                            start_index: 24,
                            end_index: 35,
                            line_col: (1, 25),
                        }),
                        start_index: 16,
                        end_index: 35,
                        line_col: (1, 17),
                    }],
                    kind: ValueKind::Dict,
                    start_index: 0,
                    end_index: 35,
                    line_col: (1, 1),
                },
                start_index: 0,
                end_index: 35,
                line_col: (1, 1),
            }]
        );
    }

    #[test]
    fn test_dict_filters_all() {
        // Test filter on all dict
        let input = r#"{"key" | default: "value" | default : empty_dict} | default : empty_dict"#;
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result,
            vec![TagAttr {
                key: None,
                value: TagValue {
                    token: TagToken {
                        token: r#"{"key" | default: "value" | default : empty_dict}"#.to_string(),
                        start_index: 0,
                        end_index: 49,
                        line_col: (1, 1),
                    },
                    children: vec![
                        TagValue {
                            token: TagToken {
                                token: "\"key\"".to_string(),
                                start_index: 1,
                                end_index: 6,
                                line_col: (1, 2),
                            },
                            children: vec![],
                            spread: None,
                            filters: vec![TagValueFilter {
                                arg: None,
                                token: TagToken {
                                    token: "default".to_string(),
                                    start_index: 9,
                                    end_index: 16,
                                    line_col: (1, 10),
                                },
                                start_index: 7,
                                end_index: 16,
                                line_col: (1, 8),
                            }],
                            kind: ValueKind::String,
                            start_index: 1,
                            end_index: 16,
                            line_col: (1, 2),
                        },
                        TagValue {
                            token: TagToken {
                                token: "\"value\"".to_string(),
                                start_index: 18,
                                end_index: 25,
                                line_col: (1, 19),
                            },
                            children: vec![],
                            spread: None,
                            filters: vec![TagValueFilter {
                                arg: Some(TagValue {
                                    token: TagToken {
                                        token: "empty_dict".to_string(),
                                        start_index: 38,
                                        end_index: 48,
                                        line_col: (1, 39),
                                    },
                                    children: vec![],
                                    spread: None,
                                    filters: vec![],
                                    kind: ValueKind::Variable,
                                    start_index: 35,
                                    end_index: 48,
                                    line_col: (1, 36),
                                }),
                                token: TagToken {
                                    token: "default".to_string(),
                                    start_index: 28,
                                    end_index: 35,
                                    line_col: (1, 29),
                                },
                                start_index: 26,
                                end_index: 48,
                                line_col: (1, 27),
                            }],
                            kind: ValueKind::String,
                            start_index: 18,
                            end_index: 48,
                            line_col: (1, 19),
                        },
                    ],
                    spread: None,
                    filters: vec![TagValueFilter {
                        arg: Some(TagValue {
                            token: TagToken {
                                token: "empty_dict".to_string(),
                                start_index: 62,
                                end_index: 72,
                                line_col: (1, 63),
                            },
                            children: vec![],
                            spread: None,
                            filters: vec![],
                            kind: ValueKind::Variable,
                            start_index: 59,
                            end_index: 72,
                            line_col: (1, 60),
                        }),
                        token: TagToken {
                            token: "default".to_string(),
                            start_index: 52,
                            end_index: 59,
                            line_col: (1, 53),
                        },
                        start_index: 50,
                        end_index: 72,
                        line_col: (1, 51),
                    }],
                    kind: ValueKind::Dict,
                    start_index: 0,
                    end_index: 72,
                    line_col: (1, 1),
                },
                start_index: 0,
                end_index: 72,
                line_col: (1, 1),
            }]
        );
    }

    #[test]
    fn test_dict_nested() {
        // Test dict in list
        let input = "[1, {\"key\": \"val\"}, 2]";
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result,
            vec![TagAttr {
                key: None,
                value: TagValue {
                    token: TagToken {
                        token: r#"[1, {"key": "val"}, 2]"#.to_string(),
                        start_index: 0,
                        end_index: 22,
                        line_col: (1, 1),
                    },
                    children: vec![
                        TagValue {
                            token: TagToken {
                                token: "1".to_string(),
                                start_index: 1,
                                end_index: 2,
                                line_col: (1, 2),
                            },
                            children: vec![],
                            spread: None,
                            filters: vec![],
                            kind: ValueKind::Int,
                            start_index: 1,
                            end_index: 2,
                            line_col: (1, 2),
                        },
                        TagValue {
                            token: TagToken {
                                token: r#"{"key": "val"}"#.to_string(),
                                start_index: 4,
                                end_index: 18,
                                line_col: (1, 5),
                            },
                            children: vec![
                                TagValue {
                                    token: TagToken {
                                        token: "\"key\"".to_string(),
                                        start_index: 5,
                                        end_index: 10,
                                        line_col: (1, 6),
                                    },
                                    children: vec![],
                                    spread: None,
                                    filters: vec![],
                                    kind: ValueKind::String,
                                    start_index: 5,
                                    end_index: 10,
                                    line_col: (1, 6),
                                },
                                TagValue {
                                    token: TagToken {
                                        token: "\"val\"".to_string(),
                                        start_index: 12,
                                        end_index: 17,
                                        line_col: (1, 13),
                                    },
                                    children: vec![],
                                    spread: None,
                                    filters: vec![],
                                    kind: ValueKind::String,
                                    start_index: 12,
                                    end_index: 17,
                                    line_col: (1, 13),
                                },
                            ],
                            spread: None,
                            filters: vec![],
                            kind: ValueKind::Dict,
                            start_index: 4,
                            end_index: 18,
                            line_col: (1, 5),
                        },
                        TagValue {
                            token: TagToken {
                                token: "2".to_string(),
                                start_index: 20,
                                end_index: 21,
                                line_col: (1, 21),
                            },
                            children: vec![],
                            spread: None,
                            filters: vec![],
                            kind: ValueKind::Int,
                            start_index: 20,
                            end_index: 21,
                            line_col: (1, 21),
                        },
                    ],
                    spread: None,
                    filters: vec![],
                    kind: ValueKind::List,
                    start_index: 0,
                    end_index: 22,
                    line_col: (1, 1),
                },
                start_index: 0,
                end_index: 22,
                line_col: (1, 1),
            }]
        );
    }

    #[test]
    fn test_dict_nested_list() {
        // Test list in dict
        let input = r#"{"key": [1, 2, 3]}"#;
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result,
            vec![TagAttr {
                key: None,
                value: TagValue {
                    token: TagToken {
                        token: r#"{"key": [1, 2, 3]}"#.to_string(),
                        start_index: 0,
                        end_index: 18,
                        line_col: (1, 1),
                    },
                    children: vec![
                        TagValue {
                            token: TagToken {
                                token: "\"key\"".to_string(),
                                start_index: 1,
                                end_index: 6,
                                line_col: (1, 2),
                            },
                            children: vec![],
                            spread: None,
                            filters: vec![],
                            kind: ValueKind::String,
                            start_index: 1,
                            end_index: 6,
                            line_col: (1, 2),
                        },
                        TagValue {
                            token: TagToken {
                                token: r#"[1, 2, 3]"#.to_string(),
                                start_index: 8,
                                end_index: 17,
                                line_col: (1, 9),
                            },
                            children: vec![
                                TagValue {
                                    token: TagToken {
                                        token: "1".to_string(),
                                        start_index: 9,
                                        end_index: 10,
                                        line_col: (1, 10),
                                    },
                                    children: vec![],
                                    spread: None,
                                    filters: vec![],
                                    kind: ValueKind::Int,
                                    start_index: 9,
                                    end_index: 10,
                                    line_col: (1, 10),
                                },
                                TagValue {
                                    token: TagToken {
                                        token: "2".to_string(),
                                        start_index: 12,
                                        end_index: 13,
                                        line_col: (1, 13),
                                    },
                                    children: vec![],
                                    spread: None,
                                    filters: vec![],
                                    kind: ValueKind::Int,
                                    start_index: 12,
                                    end_index: 13,
                                    line_col: (1, 13),
                                },
                                TagValue {
                                    token: TagToken {
                                        token: "3".to_string(),
                                        start_index: 15,
                                        end_index: 16,
                                        line_col: (1, 16),
                                    },
                                    children: vec![],
                                    spread: None,
                                    filters: vec![],
                                    kind: ValueKind::Int,
                                    start_index: 15,
                                    end_index: 16,
                                    line_col: (1, 16),
                                },
                            ],
                            spread: None,
                            filters: vec![],
                            kind: ValueKind::List,
                            start_index: 8,
                            end_index: 17,
                            line_col: (1, 9),
                        },
                    ],
                    spread: None,
                    filters: vec![],
                    kind: ValueKind::Dict,
                    start_index: 0,
                    end_index: 18,
                    line_col: (1, 1),
                },
                start_index: 0,
                end_index: 18,
                line_col: (1, 1),
            }]
        );
    }

    #[test]
    fn test_dict_invalid() {
        let invalid_inputs = vec![
            (
                r#"{key|lower:my_arg: 123}"#,
                "filter arguments in dictionary keys",
            ),
            (
                r#"{"key"|default:empty_dict: "value"|default:empty_dict}"#,
                "filter arguments in dictionary keys",
            ),
            ("{key}", "missing value"),
            ("{key,}", "missing value with comma"),
            ("{key:}", "missing value after colon"),
            ("{:value}", "missing key"),
            ("{key: key:}", "double colon"),
            ("{:key :key}", "double key"),
        ];

        for (input, msg) in invalid_inputs {
            assert!(
                TagParser::parse_tag(input).is_err(),
                "Should not allow {}: {}",
                msg,
                input
            );
        }
    }

    #[test]
    fn test_dict_key_types() {
        // Test string literal key
        let input = r#"{"key": "value"}"#;
        assert!(TagParser::parse_tag(input).is_ok());

        // Test variable key
        let input = r#"{my_var: "value"}"#;
        assert!(TagParser::parse_tag(input).is_ok());

        // Test i18n string key
        let input = r#"{_("hello"): "value"}"#;
        assert!(TagParser::parse_tag(input).is_ok());

        // Test number key
        let input = r#"{42: "value"}"#;
        assert!(TagParser::parse_tag(input).is_ok());

        // Test filtered key
        let input = r#"{"key"|upper: "value"}"#;
        assert!(TagParser::parse_tag(input).is_ok());

        // Test list as key (should fail)
        let input = r#"{[1, 2]: "value"}"#;
        assert!(
            TagParser::parse_tag(input).is_err(),
            "Should not allow list as dictionary key"
        );

        // Test dict as key (should fail)
        let input = r#"{{"nested": "dict"}: "value"}"#;
        assert!(
            TagParser::parse_tag(input).is_err(),
            "Should not allow dictionary as dictionary key"
        );
    }

    #[test]
    fn test_dict_value_types() {
        // Test string literal value
        let input = r#"{"key": "value"}"#;
        assert!(TagParser::parse_tag(input).is_ok());

        // Test variable value
        let input = r#"{"key": my_var}"#;
        assert!(TagParser::parse_tag(input).is_ok());

        // Test i18n string value
        let input = r#"{"key": _("hello")}"#;
        assert!(TagParser::parse_tag(input).is_ok());

        // Test number value
        let input = r#"{"key": 42}"#;
        assert!(TagParser::parse_tag(input).is_ok());

        // Test list value
        let input = r#"{"key": [1, 2, 3]}"#;
        assert!(TagParser::parse_tag(input).is_ok());

        // Test dict value
        let input = r#"{"key": {"nested": "dict"}}"#;
        assert!(TagParser::parse_tag(input).is_ok());

        // Test filtered value
        let input = r#"{"key": "value"|upper}"#;
        assert!(TagParser::parse_tag(input).is_ok());

        // Test spread value
        let input = r#"{"key1": "val1", **other_dict}"#;
        assert!(TagParser::parse_tag(input).is_ok());

        // Test spread with filter that might return dict
        let input = r#"{"key1": "val1", **42|make_dict}"#;
        assert!(TagParser::parse_tag(input).is_ok());
    }

    #[test]
    fn test_dict_spread() {
        // Test spreading into dict
        let input =
            r#"{"key1": "val1", **other_dict, "key2": "val2", **"{{ key3 }}", **_( " key4 ")}"#;
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result,
            vec![TagAttr {
                key: None,
                value: TagValue {
                    token: TagToken {
                        token: r#"{"key1": "val1", **other_dict, "key2": "val2", **"{{ key3 }}", **_( " key4 ")}"#.to_string(),
                        start_index: 0,
                        end_index: 78,
                        line_col: (1, 1),
                    },
                    children: vec![
                        TagValue {
                            token: TagToken {
                                token: "\"key1\"".to_string(),
                                start_index: 1,
                                end_index: 7,
                                line_col: (1, 2),
                            },
                            children: vec![],
                            spread: None,
                            filters: vec![],
                            kind: ValueKind::String,
                            start_index: 1,
                            end_index: 7,
                            line_col: (1, 2),
                        },
                        TagValue {
                            token: TagToken {
                                token: "\"val1\"".to_string(),
                                start_index: 9,
                                end_index: 15,
                                line_col: (1, 10),
                            },
                            children: vec![],
                            spread: None,
                            filters: vec![],
                            kind: ValueKind::String,
                            start_index: 9,
                            end_index: 15,
                            line_col: (1, 10),
                        },
                        TagValue {
                            token: TagToken {
                                token: "other_dict".to_string(),
                                start_index: 19,
                                end_index: 29,
                                line_col: (1, 20),
                            },
                            children: vec![],
                            spread: Some("**".to_string()),
                            filters: vec![],
                            kind: ValueKind::Variable,
                            start_index: 17,
                            end_index: 29,
                            line_col: (1, 18),
                        },
                        TagValue {
                            token: TagToken {
                                token: "\"key2\"".to_string(),
                                start_index: 31,
                                end_index: 37,
                                line_col: (1, 32),
                            },
                            children: vec![],
                            spread: None,
                            filters: vec![],
                            kind: ValueKind::String,
                            start_index: 31,
                            end_index: 37,
                            line_col: (1, 32),
                        },
                        TagValue {
                            token: TagToken {
                                token: "\"val2\"".to_string(),
                                start_index: 39,
                                end_index: 45,
                                line_col: (1, 40),
                            },
                            children: vec![],
                            spread: None,
                            filters: vec![],
                            kind: ValueKind::String,
                            start_index: 39,
                            end_index: 45,
                            line_col: (1, 40),
                        },
                        TagValue {
                            token: TagToken {
                                token: "\"{{ key3 }}\"".to_string(),
                                start_index: 49,
                                end_index: 61,
                                line_col: (1, 50),
                            },
                            children: vec![],
                            spread: Some("**".to_string()),
                            filters: vec![],
                            kind: ValueKind::Expression,
                            start_index: 47,
                            end_index: 61,
                            line_col: (1, 48),
                        },
                        TagValue {
                            token: TagToken {
                                token: "_(\" key4 \")".to_string(),
                                start_index: 65,
                                end_index: 77,
                                line_col: (1, 66),
                            },
                            children: vec![],
                            spread: Some("**".to_string()),
                            filters: vec![],
                            kind: ValueKind::Translation,
                            start_index: 63,
                            end_index: 77,
                            line_col: (1, 64),
                        },
                    ],
                    spread: None,
                    filters: vec![],
                    kind: ValueKind::Dict,
                    start_index: 0,
                    end_index: 78,
                    line_col: (1, 1),
                },
                start_index: 0,
                end_index: 78,
                line_col: (1, 1),
            }]
        );
    }

    #[test]
    fn test_dict_spread_filters() {
        // Test spreading into dict + filters
        let input =
            r#"{"key1": "val1", **other_dict, "key2": "val2", **"{{ key3 }}", **_( " key4 ")}"#;
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result,
            vec![TagAttr {
                key: None,
                value: TagValue {
                    token: TagToken {
                        token: r#"{"key1": "val1", **other_dict, "key2": "val2", **"{{ key3 }}", **_( " key4 ")}"#.to_string(),
                        start_index: 0,
                        end_index: 78,
                        line_col: (1, 1),
                    },
                    children: vec![
                        TagValue {
                            token: TagToken {
                                token: "\"key1\"".to_string(),
                                start_index: 1,
                                end_index: 7,
                                line_col: (1, 2),
                            },
                            children: vec![],
                            spread: None,
                            filters: vec![],
                            kind: ValueKind::String,
                            start_index: 1,
                            end_index: 7,
                            line_col: (1, 2),
                        },
                        TagValue {
                            token: TagToken {
                                token: "\"val1\"".to_string(),
                                start_index: 9,
                                end_index: 15,
                                line_col: (1, 10),
                            },
                            children: vec![],
                            spread: None,
                            filters: vec![],
                            kind: ValueKind::String,
                            start_index: 9,
                            end_index: 15,
                            line_col: (1, 10),
                        },
                        TagValue {
                            token: TagToken {
                                token: "other_dict".to_string(),
                                start_index: 19,
                                end_index: 29,
                                line_col: (1, 20),
                            },
                            children: vec![],
                            spread: Some("**".to_string()),
                            filters: vec![],
                            kind: ValueKind::Variable,
                            start_index: 17,
                            end_index: 29,
                            line_col: (1, 18),
                        },
                        TagValue {
                            token: TagToken {
                                token: "\"key2\"".to_string(),
                                start_index: 31,
                                end_index: 37,
                                line_col: (1, 32),
                            },
                            children: vec![],
                            spread: None,
                            filters: vec![],
                            kind: ValueKind::String,
                            start_index: 31,
                            end_index: 37,
                            line_col: (1, 32),
                        },
                        TagValue {
                            token: TagToken {
                                token: "\"val2\"".to_string(),
                                start_index: 39,
                                end_index: 45,
                                line_col: (1, 40),
                            },
                            children: vec![],
                            spread: None,
                            filters: vec![],
                            kind: ValueKind::String,
                            start_index: 39,
                            end_index: 45,
                            line_col: (1, 40),
                        },
                        TagValue {
                            token: TagToken {
                                token: "\"{{ key3 }}\"".to_string(),
                                start_index: 49,
                                end_index: 61,
                                line_col: (1, 50),
                            },
                            children: vec![],
                            spread: Some("**".to_string()),
                            filters: vec![],
                            kind: ValueKind::Expression,
                            start_index: 47,
                            end_index: 61,
                            line_col: (1, 48),
                        },
                        TagValue {
                            token: TagToken {
                                token: "_(\" key4 \")".to_string(),
                                start_index: 65,
                                end_index: 77,
                                line_col: (1, 66),
                            },
                            children: vec![],
                            spread: Some("**".to_string()),
                            filters: vec![],
                            kind: ValueKind::Translation,
                            start_index: 63,
                            end_index: 77,
                            line_col: (1, 64),
                        },
                    ],
                    spread: None,
                    filters: vec![],
                    kind: ValueKind::Dict,
                    start_index: 0,
                    end_index: 78,
                    line_col: (1, 1),
                },
                start_index: 0,
                end_index: 78,
                line_col: (1, 1),
            }]
        );
    }

    #[test]
    fn test_dict_spread_dict() {
        // Test spreading literal dict
        let input = r#"{"key1": "val1", **{"inner": "value"}, "key2": "val2"}"#;
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result[0],
            TagAttr {
                key: None,
                value: TagValue {
                    token: TagToken {
                        token: r#"{"key1": "val1", **{"inner": "value"}, "key2": "val2"}"#
                            .to_string(),
                        start_index: 0,
                        end_index: 54,
                        line_col: (1, 1),
                    },
                    children: vec![
                        TagValue {
                            token: TagToken {
                                token: "\"key1\"".to_string(),
                                start_index: 1,
                                end_index: 7,
                                line_col: (1, 2),
                            },
                            children: vec![],
                            spread: None,
                            filters: vec![],
                            kind: ValueKind::String,
                            start_index: 1,
                            end_index: 7,
                            line_col: (1, 2),
                        },
                        TagValue {
                            token: TagToken {
                                token: "\"val1\"".to_string(),
                                start_index: 9,
                                end_index: 15,
                                line_col: (1, 10),
                            },
                            children: vec![],
                            spread: None,
                            filters: vec![],
                            kind: ValueKind::String,
                            start_index: 9,
                            end_index: 15,
                            line_col: (1, 10),
                        },
                        TagValue {
                            token: TagToken {
                                token: r#"{"inner": "value"}"#.to_string(),
                                start_index: 19,
                                end_index: 37,
                                line_col: (1, 20),
                            },
                            children: vec![
                                TagValue {
                                    token: TagToken {
                                        token: "\"inner\"".to_string(),
                                        start_index: 20,
                                        end_index: 27,
                                        line_col: (1, 21),
                                    },
                                    children: vec![],
                                    spread: None,
                                    filters: vec![],
                                    kind: ValueKind::String,
                                    start_index: 20,
                                    end_index: 27,
                                    line_col: (1, 21),
                                },
                                TagValue {
                                    token: TagToken {
                                        token: "\"value\"".to_string(),
                                        start_index: 29,
                                        end_index: 36,
                                        line_col: (1, 30),
                                    },
                                    children: vec![],
                                    spread: None,
                                    filters: vec![],
                                    kind: ValueKind::String,
                                    start_index: 29,
                                    end_index: 36,
                                    line_col: (1, 30),
                                },
                            ],
                            spread: Some("**".to_string()),
                            filters: vec![],
                            kind: ValueKind::Dict,
                            start_index: 17,
                            end_index: 37,
                            line_col: (1, 18),
                        },
                        TagValue {
                            token: TagToken {
                                token: "\"key2\"".to_string(),
                                start_index: 39,
                                end_index: 45,
                                line_col: (1, 40),
                            },
                            children: vec![],
                            spread: None,
                            filters: vec![],
                            kind: ValueKind::String,
                            start_index: 39,
                            end_index: 45,
                            line_col: (1, 40),
                        },
                        TagValue {
                            token: TagToken {
                                token: "\"val2\"".to_string(),
                                start_index: 47,
                                end_index: 53,
                                line_col: (1, 48),
                            },
                            children: vec![],
                            spread: None,
                            filters: vec![],
                            kind: ValueKind::String,
                            start_index: 47,
                            end_index: 53,
                            line_col: (1, 48),
                        },
                    ],
                    spread: None,
                    filters: vec![],
                    kind: ValueKind::Dict,
                    start_index: 0,
                    end_index: 54,
                    line_col: (1, 1),
                },
                start_index: 0,
                end_index: 54,
                line_col: (1, 1),
            }
        );
    }

    #[test]
    fn test_dict_key_value_types() {
        // Test valid key types
        let valid_keys = vec![r#""string_key""#, "123", "_('i18n_key')", "my_var"];

        for key in valid_keys {
            let input = format!("{{{}: 42}}", key);
            assert!(
                TagParser::parse_tag(&input).is_ok(),
                "Should allow {} as dictionary key",
                key
            );
        }

        // Test invalid key types (lists and dicts)
        let invalid_keys = vec!["[1, 2, 3]", "{a: 1}"];

        for key in invalid_keys {
            let input = format!("{{{}: 42}}", key);
            assert!(
                TagParser::parse_tag(&input).is_err(),
                "Should not allow {} as dictionary key",
                key
            );
        }

        // Test all value types (should all be valid)
        let valid_values = vec![
            r#""string_value""#,
            "123",
            "_('i18n_value')",
            "my_var",
            "[1, 2, 3]",
            "{a: 1}",
        ];

        for value in valid_values {
            let input = format!(r#"{{"key": {}}}"#, value);
            assert!(
                TagParser::parse_tag(&input).is_ok(),
                "Should allow {} as dictionary value",
                value
            );
        }
    }

    #[test]
    fn test_dict_with_comments() {
        // Test comments after values
        let input = r#"{# comment before dict #}{{# comment after dict start #}
            "key1": "value1", {# comment after first value #}
            "key2": "value2"
        {# comment before dict end #}}{# comment after dict #}"#;
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result[0],
            TagAttr {
                key: None,
                value: TagValue {
                    token: TagToken {
                        token: r#"{{# comment after dict start #}
            "key1": "value1", {# comment after first value #}
            "key2": "value2"
        {# comment before dict end #}}"#
                            .to_string(),
                        start_index: 25,
                        end_index: 186,
                        line_col: (1, 26),
                    },
                    children: vec![
                        TagValue {
                            token: TagToken {
                                token: "\"key1\"".to_string(),
                                start_index: 69,
                                end_index: 75,
                                line_col: (2, 13),
                            },
                            children: vec![],
                            spread: None,
                            filters: vec![],
                            kind: ValueKind::String,
                            start_index: 69,
                            end_index: 75,
                            line_col: (2, 13),
                        },
                        TagValue {
                            token: TagToken {
                                token: "\"value1\"".to_string(),
                                start_index: 77,
                                end_index: 85,
                                line_col: (2, 21),
                            },
                            children: vec![],
                            spread: None,
                            filters: vec![],
                            kind: ValueKind::String,
                            start_index: 77,
                            end_index: 85,
                            line_col: (2, 21),
                        },
                        TagValue {
                            token: TagToken {
                                token: "\"key2\"".to_string(),
                                start_index: 131,
                                end_index: 137,
                                line_col: (3, 13),
                            },
                            children: vec![],
                            spread: None,
                            filters: vec![],
                            kind: ValueKind::String,
                            start_index: 131,
                            end_index: 137,
                            line_col: (3, 13),
                        },
                        TagValue {
                            token: TagToken {
                                token: "\"value2\"".to_string(),
                                start_index: 139,
                                end_index: 147,
                                line_col: (3, 21),
                            },
                            children: vec![],
                            spread: None,
                            filters: vec![],
                            kind: ValueKind::String,
                            start_index: 139,
                            end_index: 147,
                            line_col: (3, 21),
                        },
                    ],
                    spread: None,
                    filters: vec![],
                    kind: ValueKind::Dict,
                    start_index: 25,
                    end_index: 186,
                    line_col: (1, 26),
                },
                start_index: 25,
                end_index: 186,
                line_col: (1, 26),
            }
        );
    }

    #[test]
    fn test_dict_comments_colons_commas() {
        // Test comments around colons and commas
        let input = r#"{
            "key1" {# comment before colon #}: {# comment after colon #} "value1" {# comment before comma #}, {# comment after comma #}
            "key2": "value2"
        }"#;
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result[0],
            TagAttr {
                key: None,
                value: TagValue {
                    token: TagToken {
                        token: r#"{
            "key1" {# comment before colon #}: {# comment after colon #} "value1" {# comment before comma #}, {# comment after comma #}
            "key2": "value2"
        }"#.to_string(),
                        start_index: 0,
                        end_index: 176,
                        line_col: (1, 1),
                    },
                    children: vec![
                        TagValue {
                            token: TagToken {
                                token: "\"key1\"".to_string(),
                                start_index: 14,
                                end_index: 20,
                                line_col: (2, 13),
                            },
                            children: vec![],
                            spread: None,
                            filters: vec![],
                            kind: ValueKind::String,
                            start_index: 14,
                            end_index: 20,
                            line_col: (2, 13),
                        },
                        TagValue {
                            token: TagToken {
                                token: "\"value1\"".to_string(),
                                start_index: 75,
                                end_index: 83,
                                line_col: (2, 74),
                            },
                            children: vec![],
                            spread: None,
                            filters: vec![],
                            kind: ValueKind::String,
                            start_index: 75,
                            end_index: 83,
                            line_col: (2, 74),
                        },
                        TagValue {
                            token: TagToken {
                                token: "\"key2\"".to_string(),
                                start_index: 150,
                                end_index: 156,
                                line_col: (3, 13),
                            },
                            children: vec![],
                            spread: None,
                            filters: vec![],
                            kind: ValueKind::String,
                            start_index: 150,
                            end_index: 156,
                            line_col: (3, 13),
                        },
                        TagValue {
                            token: TagToken {
                                token: "\"value2\"".to_string(),
                                start_index: 158,
                                end_index: 166,
                                line_col: (3, 21),
                            },
                            children: vec![],
                            spread: None,
                            filters: vec![],
                            kind: ValueKind::String,
                            start_index: 158,
                            end_index: 166,
                            line_col: (3, 21),
                        },
                    ],
                    spread: None,
                    filters: vec![],
                    kind: ValueKind::Dict,
                    start_index: 0,
                    end_index: 176,
                    line_col: (1, 1),
                },
                start_index: 0,
                end_index: 176,
                line_col: (1, 1),
            }
        );
    }

    #[test]
    fn test_dict_comments_spread() {
        // Test comments around spread operator
        let input = r#"{
            "key1": "value1",
            {# comment before spread #}**{# comment after spread #}{"key2": "value2"}
        }"#;
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result,
            vec![TagAttr {
                key: None,
                value: TagValue {
                    token: TagToken {
                        token: r#"{
            "key1": "value1",
            {# comment before spread #}**{# comment after spread #}{"key2": "value2"}
        }"#
                        .to_string(),
                        start_index: 0,
                        end_index: 127,
                        line_col: (1, 1),
                    },
                    children: vec![
                        TagValue {
                            token: TagToken {
                                token: "\"key1\"".to_string(),
                                start_index: 14,
                                end_index: 20,
                                line_col: (2, 13),
                            },
                            children: vec![],
                            spread: None,
                            filters: vec![],
                            kind: ValueKind::String,
                            start_index: 14,
                            end_index: 20,
                            line_col: (2, 13),
                        },
                        TagValue {
                            token: TagToken {
                                token: "\"value1\"".to_string(),
                                start_index: 22,
                                end_index: 30,
                                line_col: (2, 21),
                            },
                            children: vec![],
                            spread: None,
                            filters: vec![],
                            kind: ValueKind::String,
                            start_index: 22,
                            end_index: 30,
                            line_col: (2, 21),
                        },
                        TagValue {
                            token: TagToken {
                                token: r#"{"key2": "value2"}"#.to_string(),
                                start_index: 99,
                                end_index: 117,
                                line_col: (3, 68),
                            },
                            children: vec![
                                TagValue {
                                    token: TagToken {
                                        token: "\"key2\"".to_string(),
                                        start_index: 100,
                                        end_index: 106,
                                        line_col: (3, 69),
                                    },
                                    children: vec![],
                                    spread: None,
                                    filters: vec![],
                                    kind: ValueKind::String,
                                    start_index: 100,
                                    end_index: 106,
                                    line_col: (3, 69),
                                },
                                TagValue {
                                    token: TagToken {
                                        token: "\"value2\"".to_string(),
                                        start_index: 108,
                                        end_index: 116,
                                        line_col: (3, 77),
                                    },
                                    children: vec![],
                                    spread: None,
                                    filters: vec![],
                                    kind: ValueKind::String,
                                    start_index: 108,
                                    end_index: 116,
                                    line_col: (3, 77),
                                },
                            ],
                            spread: Some("**".to_string()),
                            filters: vec![],
                            kind: ValueKind::Dict,
                            start_index: 97,
                            end_index: 117,
                            line_col: (3, 66),
                        },
                    ],
                    spread: None,
                    filters: vec![],
                    kind: ValueKind::Dict,
                    start_index: 0,
                    end_index: 127,
                    line_col: (1, 1),
                },
                start_index: 0,
                end_index: 127,
                line_col: (1, 1),
            }]
        );
    }

    #[test]
    fn test_string_kinds() {
        // Test simple string without dynamic expression
        let input = "\"Hello\"";
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result[0].value.kind,
            ValueKind::String,
            "Simple string should be marked as string"
        );

        // Test string with {% tag %}
        let input = "\"Hello {% lorem w 1 %}\"";
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result[0].value.kind,
            ValueKind::Expression,
            "String with {{%}} tag should be marked as expression"
        );

        // Test string with {{ variable }}
        let input = "\"Hello {{ name }}\"";
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result[0].value.kind,
            ValueKind::Expression,
            "String with {{{{}}}} should be marked as expression"
        );

        // Test string with {{# comment #}}
        let input = "\"Hello {# comment #}\"";
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result[0].value.kind,
            ValueKind::Expression,
            "String with {{#}} should be marked as expression"
        );

        // Test i18n string
        let input = "_('Hello')";
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result[0].value.kind,
            ValueKind::Translation,
            "i18n string should be marked as translation"
        );

        // Test variable
        let input = "my_var";
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result[0].value.kind,
            ValueKind::Variable,
            "Variable should have no string kind"
        );

        // Test number
        let input = "42";
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result[0].value.kind,
            ValueKind::Int,
            "Number should have no string kind"
        );

        // Test list
        let input = "[1, 2, 3]";
        let result = TagParser::parse_tag(input).unwrap();
        assert_eq!(
            result[0].value.kind,
            ValueKind::List,
            "List should have no string kind"
        );
    }
}
