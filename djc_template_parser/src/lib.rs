use pyo3::prelude::*;
use tag_parser::{TagAttr, TagParser, TagToken, TagValue, TagValueFilter, TagValueFilterArg};

mod tag_parser;

#[pymodule]
fn djc_template_parser(_py: Python<'_>, m: &PyModule) -> PyResult<()> {
    m.add_class::<TagAttr>()?;
    m.add_class::<TagValue>()?;
    m.add_class::<TagValueFilter>()?;
    m.add_class::<TagToken>()?;
    m.add_class::<TagValueFilterArg>()?;
    m.add_function(wrap_pyfunction!(parse_tag, m)?)?;
    Ok(())
}

#[pyfunction]
fn parse_tag(input: &str) -> PyResult<Vec<TagAttr>> {
    let attributes = TagParser::parse_tag(input)?;
    Ok(attributes)
}
