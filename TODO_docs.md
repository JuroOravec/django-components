# TODO

So when it comes to PRs, my course of actions is to:

Bugs:
- Type validation doesn't handle nested dictionaries
  - In my project I'm using Alpine, and I'm passing both Python and Alpine variables through the components.

    To distinguish the two, I've started using following pattern - Component
    inputs expecting JS variables / expressions are prefixed with `js:`

    ```django
    {% component "table"
      rows=rows
      headers=headers
      js:pagination="pageVar"
    / %}
    ```

    From the component's perspective, `js` is simply a dictionary, e.g.

    ```py
    def get_context_data(self, rows: List[Dict], headers: List[Dict], js: Dict):
        return {
            "rows": rows,
            "headers": headers,
            "js": js,
        }
    ```

    Now, since I'm also typing the components to validate the inputs, the component
    definitions may look like this:

    ```py
    class TableProps(TypedDict):
        rows: List[Dict]
        headers: List[Dict]
        js: Dict


    class Table(Component[EmptyTuple, TableProps, Any, Any, Any, Any]):
        def get_context_data(self, rows: List[Dict], headers: List[Dict], js: Dict):
            return {
                "rows": rows,
                "headers": headers,
                "js": js,
            }
    ```

    But I wanted to validate also the entries in the `js` dict, so I tried something like this:
    
    ```py
    class TableJsProps(TypedDict):
        pagination: NotRequired[str]

    class TableProps(TypedDict):
        rows: List[Dict]
        headers: List[Dict]
        js: TableJsProps
    ```

    However, our validation doesn't currently handle nested data structures.

    To resolve this, I replaced our validation with pydantic.

Tweaks:
- Added `js_name` and `css_name` attributes, which are the JS / CSS equivalents of `template_name`.
  - Same as with `template_name`, `js/css_name` and `js/css` are mutually exclusive
  - The difference between `js/css_name` and `Media.js/css` is that `js/css_name` will be treated
    specially (e.g. apply scoped CSS, etc), while `Media.js/css` is not post-processed in any way.
---

THESE ARE ALL THE DOCS PAGES THAT NEED TO BE REVIEWED / UPDATED.
(taken from http://127.0.0.1:9000/django-components/sitemap.xml)

THOSE THAT START WITH ✅ ARE ALREADY DONE:

✅ http://127.0.0.1:9000/django-components/changelog/

http://127.0.0.1:9000/django-components/SUMMARY/
http://127.0.0.1:9000/django-components/dependency_mgmt/
http://127.0.0.1:9000/django-components/migrating_from_safer_staticfiles/
http://127.0.0.1:9000/django-components/vue_comparison/
http://127.0.0.1:9000/django-components/concepts/advanced/authoring_component_libraries/
http://127.0.0.1:9000/django-components/concepts/advanced/component_registry/
http://127.0.0.1:9000/django-components/concepts/advanced/hooks/
http://127.0.0.1:9000/django-components/concepts/advanced/provide_inject/
http://127.0.0.1:9000/django-components/concepts/advanced/rendering_js_css/
http://127.0.0.1:9000/django-components/concepts/advanced/tag_formatter/
http://127.0.0.1:9000/django-components/concepts/advanced/typing_and_validation/
http://127.0.0.1:9000/django-components/concepts/fundamentals/access_component_input/
http://127.0.0.1:9000/django-components/concepts/fundamentals/autodiscovery/
http://127.0.0.1:9000/django-components/concepts/fundamentals/component_context_scope/
http://127.0.0.1:9000/django-components/concepts/fundamentals/components_as_views/
http://127.0.0.1:9000/django-components/concepts/fundamentals/components_in_python/
http://127.0.0.1:9000/django-components/concepts/fundamentals/components_in_templates/
http://127.0.0.1:9000/django-components/concepts/fundamentals/defining_js_css_html_files/
http://127.0.0.1:9000/django-components/concepts/fundamentals/html_attributes/
http://127.0.0.1:9000/django-components/concepts/fundamentals/single_file_components/
http://127.0.0.1:9000/django-components/concepts/fundamentals/slots/
http://127.0.0.1:9000/django-components/concepts/fundamentals/template_tag_syntax/
http://127.0.0.1:9000/django-components/concepts/fundamentals/your_first_component/
http://127.0.0.1:9000/django-components/devguides/dependency_mgmt/
http://127.0.0.1:9000/django-components/devguides/slot_rendering/
http://127.0.0.1:9000/django-components/devguides/slots_and_blocks/
http://127.0.0.1:9000/django-components/guides/setup/dev_server_setup/
http://127.0.0.1:9000/django-components/guides/setup/logging_and_debugging/
http://127.0.0.1:9000/django-components/guides/setup/syntax_highlight/
http://127.0.0.1:9000/django-components/overview/code_of_conduct/
http://127.0.0.1:9000/django-components/overview/community/
http://127.0.0.1:9000/django-components/overview/compatibility/
http://127.0.0.1:9000/django-components/overview/contributing/
http://127.0.0.1:9000/django-components/overview/development/
http://127.0.0.1:9000/django-components/overview/installation/
http://127.0.0.1:9000/django-components/overview/license/
http://127.0.0.1:9000/django-components/overview/security_note/
http://127.0.0.1:9000/django-components/overview/welcome/
http://127.0.0.1:9000/django-components/reference/api/
Component
 Media
 View
 component_id
 css
 css_name
 css_lang
 css_scoped
 input
 is_filled
 js
 js_name
 js_lang
 media
 media_class
 outer_context
 registered_name
 registry
 response_class
 as_view
 get_context_data
 get_css_data
 get_js_data
 inject
 on_render_after
 on_render_before
 render
 render_to_response
Slot


✅ http://127.0.0.1:9000/django-components/reference/commands/
✅ http://127.0.0.1:9000/django-components/reference/components/
✅ http://127.0.0.1:9000/django-components/reference/exceptions/
✅ http://127.0.0.1:9000/django-components/reference/middlewares/
✅ http://127.0.0.1:9000/django-components/reference/settings/
✅ http://127.0.0.1:9000/django-components/reference/tag_formatters/
✅ http://127.0.0.1:9000/django-components/reference/template_tags/
✅ http://127.0.0.1:9000/django-components/reference/template_vars/
✅ http://127.0.0.1:9000/django-components/reference/urls/
