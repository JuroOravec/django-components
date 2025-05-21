from django_components import register, types
from django_vue.templatetags.vue import vue_registry

def _gen_WithPython():

    from django_vue.component import VueComponent

    class WithPython(VueComponent):
        def get_context_data(self):
            return {"classes": "abc"}

        def get(self, request, *args, **kwargs):
            context = {"name": request.GET.get("name", "")}
            return self.render_to_response(context=context)


    return WithPython

_WithPython = _gen_WithPython()

@register('WithPython', registry=vue_registry)
class WithPython(_WithPython):
    template_lang = 'html'
    template: types.django_html = """
    <button   {% html_attrs None None x-bind="genAttrs(() => ({'@click': onClick, 'class': classes, }))" %}>
        {% slot name="default" default %}
      {% endslot %}</button>
    """
    js_lang = 'ts'
    js: types.ts = """

    // TODO
    const defineComponent = (options) => options;

    // TODO
    console.log("INSIDE WITH_PYTHON");

    export default defineComponent({
      name: "WithPython",
      props: {
        classes: {
          type: String,
          default: ''
        }
      },
      setup() {
        const onClick = () => {
          debugger;
          this.$emit('click');
        }
        return { onClick };
      },
      // TODO: Support Options syntax
      // methods: {
      //   onClick() {
      //       this.$emit('click');
      //   }
      // },
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
