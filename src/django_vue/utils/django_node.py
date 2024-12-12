from django.template import Node


def replace_node_in_parent(old_node: Node, new_node: Node, parent: Node) -> None:
    """
    Remove a node from its parent's nodelist.

    This function is taken from `django.template.base.Node.remove()`.
    """
    for attr in parent.child_nodelists:
        nodelist = getattr(parent, attr, [])
        if old_node in nodelist:
            node_index = nodelist.index(old_node)
            nodelist[node_index] = new_node
            return
    raise ValueError("Node could not be found in parent's nodelist.")
