from typing import Dict, List

import esprima

# Make JS array whose items are interpreted as JS statements (e.g. functions)
def js_arr(lst: List) -> str:
    return "[" + ", ".join(lst) + "]"


# TODO DOCUMENT
# See https://chatgpt.com/share/67293956-4a9c-8004-a5eb-1463bf2fa0eb
def extract_bindings(pattern, base_path='$slot'):
    # Parse the pattern into an AST
    tree = esprima.parseScript(f"let {pattern} = null;")
    declarations = tree.body[0].declarations[0].id  # VariableDeclarator

    bindings: Dict[str, str] = {}
    def traverse(node, path, used_keys=None):
        if used_keys is None:
            used_keys = []
        if node.type == 'Identifier':
            bindings[node.name] = path
        elif node.type == 'ObjectPattern':
            for prop in node.properties:
                if prop.type == 'Property':
                    key_node = prop.key
                    value_node = prop.value
                    key_name = key_node.name if hasattr(key_node, 'name') else key_node.value
                    used_keys.append(key_name)
                    new_path = f"{path}.{key_name}"
                    traverse(value_node, new_path)
                elif prop.type == 'RestElement':
                    # Handle rest element in object
                    rest_var_name = prop.argument.name
                    # Exclude the used keys from the object
                    excluded_keys = ', '.join(f"'{key}'" for key in used_keys)
                    rest_expression = (
                        f"Object.fromEntries(Object.entries({path}).filter(([key]) => ![{excluded_keys}].includes(key)))"
                    )
                    bindings[rest_var_name] = rest_expression
        elif node.type == 'ArrayPattern':
            for idx, element in enumerate(node.elements):
                if element is None:
                    continue  # Skip holes in sparse arrays
                if element.type == 'Identifier':
                    bindings[element.name] = f"{path}[{idx}]"
                elif element.type == 'RestElement':
                    rest_var_name = element.argument.name
                    bindings[rest_var_name] = f"{path}.slice({idx})"
                else:
                    traverse(element, f"{path}[{idx}]")
        elif node.type == 'AssignmentPattern':
            # Handle default values
            traverse(node.left, path)
        elif node.type == 'RestElement':
            # Should not reach here for object patterns as we handle RestElement in ObjectPattern
            pass
        elif node.type == 'MemberExpression':
            # Handle nested member expressions if any
            pass  # Can be extended based on requirements

    traverse(declarations, base_path)

    return bindings


# TODO - Add tests
pattern = "{ user: { name: userName, age, ...other }, posts: [firstPost, second, ...restPosts], ...other2 }"
pattern = "[{ user: { name: userName, age, ...other }}]"
bindings = extract_bindings(pattern)
print(bindings)
print("{" + ", ".join([f"{key}: {val}" for key, val in bindings.items()]) + "}")
