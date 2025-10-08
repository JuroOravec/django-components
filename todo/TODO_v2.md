# V2 suggestions

- Remove support for positional args
    - This would simplify the code a lot
        - Would allow to infer flags (kwargs without values) as `kwarg=True`,
          thus processing ALL tag inputs (args, kwargs, flags) as kwargs
            - See https://github.com/EmilStenstrom/django-components/discussions/486
            - See https://github.com/Xzya/django-web-components#attributes-with-special-characters
    - Would align the API with React, Vue, django-web-components, django-slippers
    - With this, `kwargs` could be renamed to `props`
- Make it work outside of Django

- Plugins
  - Would be possible to pre-process inputs passed to tags, e.g. so slot could accept `alpine="{}"`
    keyword. Each Node would have a `meta` or `extra` attribute, and this is where plugin
    authors could store the extra data that could then later be accessed in render phase.
  - They could also modify the template (or rather, make copies from the original templates?)
    So that the support for Alpine slots could be implmenteded as template transformation.

- Expose `self` inside templates

- Use [Shoelance](https://shoelace.style/) / [Lit](https://lit.dev/)
  to define the components as web-components?
  - [Read more](https://developer.salesforce.com/blogs/2020/01/accessibility-for-web-components)
  - <https://lit.dev/playground/>
- The name should represent what people search for: "web ui components python"

- Modify Vetur.js to create language service provider for Django templates
  - Evan You said in one interview that they designed Vetur such that it can be modified to work
    for other languages too.
  - See https://chatgpt.com/c/df3a6d0d-1d0f-4fff-8681-6be436e4af66
  - And https://github.com/vuejs/vetur/blob/master/server/src/modes/template/services/htmlCompletion.ts
  - And https://vuejs.github.io/vetur/

  - Order of execution:
    1. Write parser / tokenizer for HTML, extending it to work with `{% %}`. Basically rewriting
        these file
        - https://github.com/vuejs/vetur/blob/master/server/src/modes/template/parser/htmlScanner.ts
        - https://github.com/vuejs/vetur/blob/master/server/src/modes/template/parser/htmlParser.ts
      - NOTE: For the language HTML parser to work, Django's interpolation must NEVER
              cross HTML boundaries.
          - So this is ok:
            ```django
            {{ before }} <div {{ as_attr }}> {{ after }}
              {{ within }}
            </div>
            ```
            even this is ok:
            ```django
            <{{ as_tag }} {{ as_attr }}>  # So for start tags we should also check for `<\{\{` and `<\{%`
              {{ within }}
            </{{ as_tag }}>  # And for end tags we should also check for `</\{\{` and `</\{%`
            ```

            But this is NOT OK:
            {{ "<" }}div {{ as_attr }}> {{ after }}
              {{ within }}
            {{ "\</di" }}v>
            ```
    2. See in how many places the `createScanner` is used. This is basically all the features we want
       to have for the HTML template.
       - See https://github.com/search?q=repo%3Avuejs/vetur%20createScanner&type=code

    3. See how the info on Vue components is collected by Vetur.
       We would need that in order to provide "go to definition" feature, where user could CTRL + CLICK
       the component name in a template.
       - See https://github.com/vuejs/vetur/blob/master/server/src/modes/template-common/tagDefinition.ts#L6
