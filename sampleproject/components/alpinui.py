from typing import Any, Dict

from django_components import Component, ComponentView, register, types


@register("alpine_scoped_slot_inner")
class AlpineScopedSlotInner(Component):
    template: types.django_html = """
        {% load component_tags %}
        <div x-data="{ a: 123 }">
          {% slot "slot1" default alpine js:key="a + 1" %}
              Default slot1 content
          {% endslot %}
          {% slot "slot2" alpine %}
              Default slot2 content
          {% endslot %}
        </div>
    """

@register("three_slots")
class ThreeSlots(Component):
    template: types.django_html = """
        {% load component_tags %}
        <div>
            {% slot "slot1" default %}
                Default slot1 content
            {% endslot %}
            <br/>
            {% slot "slot2" %}
                Default slot2 content
            {% endslot %}
            <br/>
            {% slot "slot3" %}
                Default slot3 content
            {% endslot %}
        </div>
    """


class AlpinuiDemo(Component):
    def get_context_data(self, *args, **kwargs) -> Dict[str, Any]:
        return {"self": self, "the_slots": ["slot"], "outer_loop": ["1", "2", "3"]}

    template: types.django_html = """
        {% load component_tags %}
        {% load alpinui %}

        <!DOCTYPE html>
        <html lang="en">
        <head>
            <script type="importmap">
              {
                "imports": {
                  "@unhead/shared": "https://cdn.jsdelivr.net/npm/@unhead/shared@1.11.10/dist/index.mjs",
                  "@unhead/dom": "https://cdn.jsdelivr.net/npm/@unhead/dom@1.11.10/dist/index.mjs",
                  "unhead": "https://cdn.jsdelivr.net/npm/unhead@1.11.10/dist/index.mjs",
                  "hookable": "https://cdn.jsdelivr.net/npm/hookable@5.5.3/dist/index.mjs"
                }
              }
            </script>
            <script type="module">
              import * as unhead from 'unhead';
              globalThis.unhead = unhead;
            </script>
            {% AlpinuiCss / %}
            {% AlpinuiJs / %}
        </head>
        <body>
            {% Alpinui %}
                <main role="main">
                <div class='container main-container'>
                    {% block body %}
                    {% endblock %}
                </div>
                </main>
            {% /Alpinui %}

            <button x-data="{color: 'blue'}" :style="`color: ${color}`">
                Change color
            </button>

            <br/>
            SLOTS:
            {{ the_slots }}
            <br/>

            NOTE: USE FOLLOWING TO ACCESS PROPS AND SLOTS INSIDE ALPINUI COMPONENTS
            <br/>
            $props:
            <span x-text="JSON.stringify($props)"></span>
            <br/>
            $initState.slots:
            <span x-text="JSON.stringify($initState.slots)"></span>

            <br/>
            Pre-rendred server-side list:
            <br/>
            <div
              x-data="{
                id: 123,
                items: [],
                initialized: false,
                init() {
                  const prerenderedItems = $el.querySelectorAll(`[data-a-list-${this.id}]`);
                  this.items = [...prerenderedItems].map(el => JSON.parse(el.getAttribute('data-x-item')));
                  this.initialized = true;

                  prerenderedItems.forEach((el) => el.remove())
                },
              }"
            >
                <!-- Alpine-managed list -->
                <template x-for="(item, index) in items" :key="item.name">
                  <div x-text="`This is ${item.name} (${item.age})`"></span>
                </template>

                <!-- Pre-rendered server-side list (hidden after Alpine initializes) -->
                <div data-a-list-123 data-x-item='{ "name": "John", "age": 37 }'>
                  This is John (37)
                </div>
                <div data-a-list-123 data-x-item='{ "name": "Audrie", "age": 27 }'>
                  This is Audrie (27)
                </div>
            </div>
      

            {% component "three_slots" %}
                {% for outer in outer_loop %}
                    {% for slot_name in the_slots %}
                        {% fill name=slot_name|add:outer %}
                            OVERRIDEN: {{ slot_name }} - {{ outer }}
                        {% endfill %}
                    {% endfor %}
                {% endfor %}
            {% endcomponent %}

            <hr/>

            {% Alpinui %}
              {% comment %}
                One:
                <div x-data="{one: 123 }" @myev="console.log">
                    {% ADivider opacity=0.3 attrs:style="margin:20px" %}
                        {% fill "default" %}
                            <span x-text="one" @click="$dispatch('myev', 456)">
                            </span>
                        {% endfill %}
                    {% /ADivider %}
                </div>
                Two:
                
                <div x-data="{
                  color: 'blue',
                  change(){
                    debugger;
                    console.log('Changing to red!');
                    // THIS DOES NOT UPDATE THE CHILD!!!
                    this.color = 'red';

                    // NOR THIS!!!
                    // this.$el.setAttribute('x-data', '{ color: \\'red\\'}');
                  }
                }" @click="change">
                {% endcomment %}
                <div x-data="{
                  // THIS WORKS!!!!!!!!!!!!!!!!!
                  // THIS WORKS!!!!!!!!!!!!!!!!!
                  // THIS WORKS!!!!!!!!!!!!!!!!!
                  color: AlpineReactivity.ref('blue'),
                  change(){
                    console.log('Changing to red!');
                    this.color.value = this.color.value === 'blue' ? 'red' : 'blue';
                  }
                }" @click="change">

                  <div x-data="{
                    innerColor: color,
                  }" :style="{height: '50px', background: innerColor.value }">
                  </div>
                  <!--
                    THIS WORKS!!!!!!!!!!!!!!!!!
                    JS REFS PASSED TO COMPONENTS CAN BE EITHER `myVal` OR `myVal.value`!!!!!!!!!!!!!!!!!
                    JS REFS PASSED TO COMPONENTS CAN BE EITHER `myVal` OR `myVal.value`!!!!!!!!!!!!!!!!!
                    JS REFS PASSED TO COMPONENTS CAN BE EITHER `myVal` OR `myVal.value`!!!!!!!!!!!!!!!!!
                    THIS WORKS!!!!!!!!!!!!!!!!!
                  -->
                  {# TODO - IN PROPS VALIDATION, IF TYPE IS STR, ALSO ALLOW REF<STR>, ETC - # TODO #}
                  {# TODO - IN PROPS VALIDATION, IF TYPE IS STR, ALSO ALLOW REF<STR>, ETC - # TODO #}
                  {# TODO - IN PROPS VALIDATION, IF TYPE IS STR, ALSO ALLOW REF<STR>, ETC - # TODO #}
                  {# TODO - IN PROPS VALIDATION, IF TYPE IS STR, ALSO ALLOW REF<STR>, ETC - # TODO #}
                  {% ADivider
                    thickness=20
                    js:color="color.value"
                    attrs:style="margin:20px"
                  / %}
                  <!--
                    THEN INSIDE COMPONENT I NEED TO DO!!!!!!!!!!!!!!!!!
                    THEN INSIDE COMPONENT I NEED TO DO!!!!!!!!!!!!!!!!!
                    (props) => {
                      const {} = toRefs(props);
                    };
                    THEN INSIDE COMPONENT I NEED TO DO!!!!!!!!!!!!!!!!!
                    THEN INSIDE COMPONENT I NEED TO DO!!!!!!!!!!!!!!!!!
                  -->
                </div>
            {% /Alpinui %}

            {% comment %}
            <div x-data @click>
                <div x-data @click>
                    <button x-data type="button"
                        @click="message = 'selected'"
                        @click.shift="message = 'added to selection'"
                        @mousemove.shift="message = 'add to selection'"
                        @mouseout="message = 'select'"
                        x-text="message"
                    >
                </button>
            </div>
            {% endcomment %}


            <br />
            Test alpine slots:
            <br />

          <div x-data="{ c: 11, a: 5 }">
            {% component "alpine_scoped_slot_inner" %}
              {% fill alpine="{ key }" %}
                <div x-text="key"></div>
                <div x-text="c"></div>
                <div x-text="a"></div>
              {% endfill %}

              {% fill "slot2" %}
                <div x-text="key"></div>
                <div x-text="c"></div>
                <div x-text="a"></div>
              {% endfill %}
            {% endcomponent %}
          </div>

        </body>
      </html>
    """

    class View(ComponentView):
        def get(self, request, *args, **kwargs):
            context = {"name": request.GET.get("name", "")}
            return self.component.render_to_response(context=context)
