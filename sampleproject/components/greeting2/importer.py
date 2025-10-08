from typing import Any, Dict

from django_components import Component
from django_components.utils import getmembers


# TODO - write
def import_components():
    # raise if there's multiple components
    components = []
    for name, component in getmembers(Greeting2, is_component):
        if isinstance(component, Component):
            components.append(component)
    if len(components) > 1:
        raise ValueError("Multiple components found in greeting2 module")
    return components[0]

