from django_components import register, types
from django_vue.templatetags.vue import vue_registry
from django_vue.component import VueComponent
@register('Linked', registry=vue_registry)
class Linked(VueComponent):
    template_lang = 'html'
    template_name = '../components/linked/Linked.html'
    js_lang = 'js'
    js_name = '../components/linked/Linked.js'
    css_lang = 'css'
    css_name = '../components/linked/Linked.css'
