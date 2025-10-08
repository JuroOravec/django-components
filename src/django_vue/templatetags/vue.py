from django.template import Library

from django_components import ComponentRegistry, RegistrySettings

# NOTE: Variable name `register` is required by Django to recognize this as a template tag library
# See https://docs.djangoproject.com/en/dev/howto/custom-template-tags
register = Library()

vue_registry = ComponentRegistry(
    library=register,
    settings=RegistrySettings(
        tag_formatter="django_components.component_shorthand_formatter",
        context_behavior="isolated",
    )
)
