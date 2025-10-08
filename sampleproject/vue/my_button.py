from django_components import register, types
from django_vue.templatetags.vue import vue_registry
from django_vue.component import VueComponent
@register('MyButton', registry=vue_registry)
class MyButton(VueComponent):
    template_lang = 'html'
    template: types.django_html = """
    <button   {% html_attrs None None x-bind="genAttrs(() => ({'@click': onClick, 'class': classes, }))" %}>
        {% slot name="default" default %}{% endslot %}
      </button>
    """
    js_lang = 'ts'
    js: types.ts = """

    export default defineComponent({
      props: {
        classes: {
          type: String,
          default: ''
        }
      },
      methods: {
        onClick() {
            this.$emit('click');
        }
      },
      setup() {
          return {}
      },
    });

    """
    css_lang = 'css'
    css: types.css = """

    button {
      background-color: #4CAF50;
      border: none;
      color: white;
      padding: 15px 32px;
      text-align: center;
      text-decoration: none;
      display: inline-block;
      font-size: 16px;
      margin: 4px 2px;
      cursor: pointer;
    }

    """
