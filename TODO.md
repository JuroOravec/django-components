# TODO:

IMPLEMENTING CSS VARS:
1. commit code around `get_css_data`
2. To `{% slot %}`

## OUTSTANDING PRs:


# IMPLEMENT `on_template_preprocess`!!!!


1. FIX DOCS

4. Plugin system
  - Allow {html,js,css} pre-process for use cases like `<comp "" />`
  - Allow {html,js,css} post-process (before cached) for use cases like CSS / JS minification
  - Allow template transform - For AlpineJS slot
  - Allow pre-process inputs to `slot` / `comp` / `fill` tags - For AlpineJS slot

5. CSS Modules
  - See https://vite.dev/guide/features#css-modules
  - See https://github.com/css-modules/css-modules/blob/master/README.md
  - The component's styles would be available to the component from inside the `$onLoad`
    hook.


TODO
- Also mention in docs that we're fully-tested (97% coverage)
- See on integrating django-cotton into django-components
    - https://www.reddit.com/r/django/comments/1fp5v6k/comment/lp2qjh1/?utm_source=share&utm_medium=web3x&utm_name=web3xcss&utm_term=1&utm_content=share_button
    - https://github.com/fbinz/django-components-preprocessor
        - NOTE: Actually the cotton-support will need to work in both SFC and normal modes
          So in normal component definintion, we'd need some way to flag that the HTML uses
          `<>` instead of `{}`

          E.g.

          ```py
          class MyComp(Component):
              template_name: types.django_comp = "path/to/file.html"
              template: types.django_comp = """
                <MyComp abc=def>
                </MyComp>
              """
          ```
          
          Or

          ```py
          class MyComp(Component):
              template_name = ComponentTemplate("path/to/file.html", tag="html")
              template = ComponentTemplate(
                  """
                    <MyComp abc=def>
                    </MyComp>
                  """,
                  tag="html",
              )
          ```
          
          Or

          ```py
          class MyComp(Component):
              template_tag = "html" | "django"
              template_name = "path/to/file.html"
              template = """
                <MyComp abc=def>
                </MyComp>
              """
          ```


# TODO - Use pydantic for validation
#        - Would allow to recursively pass typed tuples and dicts
#        - So then we could allow extra kwargs
#        - And then we could generate the component docs based on the Args / Kwargs / Slots, etc.

# TODO - Allow to pass string (as import path) instead of direct reference to `ComponentRegistry.register()`
# TODO - Add events to JS - See https://github.com/tetra-framework/tetra/discussions/71#discussioncomment-10641556
# TODO - ALLOW PEOPLE TO OPT OUT OF SCOPED CSS
# TODO - Error boundary
# See https://github.com/EmilStenstrom/django-components/discussions/480

# - TODO TETRA INSPO
#    - Converts class name to snake_case if no name is provided for the `register` decorator
#    - Use JSON Encoder/Encoder
#      - Also specially handle Models, so we call `._as_dict()` on them
#    - Use AttrsNode's way of merging classes / styles

# TODO - OTHER??? (Do we really want to?)
#   ADD TO COMPILERS FILE:
#   - WHAT IF WE COMPILED TS TO JS AS PYTON FUNCTION?
#     - See https://github.com/EmilStenstrom/django-components/pull/870#discussion_r1899740984
#
#   - Open issue for supporting multiple files in `js_file` and others
#     - See https://github.com/EmilStenstrom/django-components/pull/870#discussion_r1899515376

# Comparisons from - https://github.com/EmilStenstrom/django-components/discussions/310
# Unicorn, Tetra, Reactor, TurboDjango, Sockpuppet, djhtmx

- Add support for django plugins `djc-plugin-`

5. Passing data from Django_component's JS script to AlpineJS
  - See https://chatgpt.com/c/1e3729d9-ea87-4b3e-acf6-65ecbba49d5c
  ```html
  <div x-data="{ nodeRef: null }">
    <!-- Reference to be updated -->
    <span x-ref="node" x-text="nodeRef ? 'Node reference set!' : 'No reference yet'"></span>
  </div>
  ```
  And inside the JS script:
  ```js
  // Inside mycomp or directly from the browser console
  const dataEl = document.querySelector('div[x-data]');
  let node = dataEl.__x.$data.nodeRef;
  if (node) {
    node.textContent = 'This was updated via Node reference!';
  } else {
    dataEl.__x.$data = document.querySelector('#...');
  }
  ```
  The function would accept a node or a list of nodes, so we can use it with `$els`
  ```js
  // This sets `x-data=""` attribute on the elements if `__x` is not defined yet,
  // otherwise just updates `.__x.$data.[key]`
  setAlpineData($els, {
    'key': data.value,
    ref: $els[0],
    ...
  });
  ```

6. Slot/fill improvements: Allow to encapsulate slots inside other template tags, and dynamic slots/fills

      ## Background

      For the UI component library, I'm trying to write slots that will work with both Django and AlpineJS at the same time. What I mean by that is that when I write AlpineJS logic inside a django_components slot, I want to have the inner AlpineJS block to behave as if it was embedded inside the outer scope:

      ```django
      <div x-data="{ icon: 'outline-plus' }">
        {% component "button" %}
          {# Render icon based on the outer `icon` AlpineJS variable #}
          <div class="mdi" :class="'mdi-' + icon">
          </div>
        {% endcomponent %}
      </div>
      ```

      To achieve this, I plan to do 2 steps:
      1. Define a slot inside django_components at the root of the component, so it can access the outer AlpineJS scope.
      2. Wrap the django_components slot with Alpine's [x-teleport](https://alpinejs.dev/directives/teleport), so that the html is actually rendered at the desired place.

      So the HTML for the `button` component could look like this:

      ```django
      {# Slot defined here, so that AlpineJS variables have the same context as the outer scope #}
      {# If the slot was directly inserted inside `card` component, AlpineJS variables would be taken #}
      {# from there instead. #}
      <div x-teleport="dc-{{ id }}-content">
        {% slot "content" default / %}
      </div>

      {% component "card" %}
        <button id="dc-{{ id }}-content">
        </button>
      {% endcomponent %}
      ```

      ## Suggestions

      It would be to encapsulate the whole
      ```django
      <div x-teleport="dc-{{ id }}-content">
        {% slot "content" default / %}
      </div>
      ```

## More competitiom:

- [Streamlit](https://github.com/streamlit/streamlit)
- [Solara](https://github.com/widgetti/solara)
- [Reactpy](https://github.com/reactive-python/reactpy)
- FastHTML
- [Trame](https://github.com/kitware/trame)
  - Intersting:
    ```py
    html_view = vtk.VtkRemoteView(renderWindow)
    with SinglePageLayout(server) as layout:
        # [...]
        with layout.content:
            with vuetify.VContainer(
                fluid=True,
                classes="pa-0 fill-height",
            ):
                # html_view = vtk.VtkLocalView(renderWindow)
                html_view = vtk.VtkRemoteView(renderWindow)
    ```

See
https://star-history.com/#EmilStenstrom/django-components&mixxorz/slippers&Xzya/django-web-components&rails-inspire-django/django-viewcomponent&tetra-framework/tetra&adamghill/django-unicorn&reactive-python/reactpy&Date

## Long term vision

- Bring the "ease of development with component UI libraries" experience to non-JS communities (Python, Go, Rust)
- To support multiple languages, we cannot couple too close with the templating libraries (like django-components). Instead, we should make a port of Vuetify in AlpineJS (Alpify or Alpinify or AlpUI or _AlpineUI_), as a lightweight alternative that's not bound to Vue. AlpineUI components would have standardized way to pass data to the components (via e.g. `data-init` attribute). Thus, to bring Vuetify to Py/Go/Rs, we'd need to make AlpineUI only once, and then make bindings in Py/Go/Rs (which might require creating a templating library in given language like django-components in Py).
    - see https://stackoverflow.com/questions/65710987/reusable-alpine-js-components
- Attract devs form top companies by attracting them to the idea that we want to "bring web dev excellence" to Py/Rs/Go. And that we want to move it closer to Rs/Go to improve performance (4x vs NodeJS, 100x vs Py (?)). And that I'm looking for fellow builders.


## AlpineJS Component libraries
- https://www.google.com/search?q=alpinejs+components
- https://alpinejs.dev/components
- https://github.com/markmead/alpinejs-component
- https://www.alpinetoolbox.com/
- https://github.com/topics/alpinejs-components
