import os
from textwrap import dedent, indent
from typing import Any, NamedTuple

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError, CommandParser

from django_components.app_settings import app_settings


class BoilerplateContext(NamedTuple):
    name: str
    """Component name"""


# TODO FIX indentations and TEST!
class ComponentBoilerplate:
    js_filename: str = "script.js"
    css_filename: str = "style.css"
    template_filename: str = "template.html"

    js_inlined: bool = False
    css_inlined: bool = False
    template_inlined: bool = False

    def js_render(self, comp_name: str, filepath: str) -> str:
        return f"""
            window.addEventListener('load', (event) => {{
                console.log("{comp_name} component is fully loaded");
            }});
        """

    def css_render(self, comp_name: str, filepath: str) -> str:
        return f"""
            .component-{comp_name} {{
                background: red;
            }}
        """

    def template_render(self, comp_name: str, filepath: str) -> str:
        return f"""
            <div class="component-{comp_name}">
                Hello from {comp_name} component!
                <br>
                This is {{ param }} context value.
            </div>
        """

    def py_render(
        self,
        comp_name: str,
        filepath: str,
        inline: bool,
        js_content: str,
        css_content: str,
        template_content: str,
    ) -> str:
        if inline:
            # TODO - INDENTATION WRONG HERE!
            deps = f"""
                template = \"\"\"
                    {template_content}
                \"\"\"

                js = \"\"\"
                    {js_content}
                \"\"\"

                css = \"\"\"
                    {css_content}
                \"\"\"
            """
        else:
            deps = f"""
                template_name = "{self.template_filename}"

                class Media:
                    css = "{self.css_filename}"
                    js = "{self.js_filename}"
            """

        return f"""
            from django_components import Component, register

            @register("{comp_name}")
            class {comp_name.capitalize()}(Component):
                {deps}

                def get_context_data(self, value):
                    return {{
                        "param": "sample value",
                    }}

        """


boilerplate = ComponentBoilerplate()


class Command(BaseCommand):
    """
    ### Management Command Usage

    To use the command, run the following command in your terminal:

    ```bash
    python manage.py startcomponent <name> --path <path> --js <js_filename> --css <css_filename>\
        --template <template_filename> --force --verbose --dry-run
    ```

    Replace `<name>`, `<path>`, `<js_filename>`, `<css_filename>`, and `<template_filename>`
    with your desired values.

    ### Management Command Examples

    Here are some examples of how you can use the command:

    #### Creating a Component with Default Settings

    To create a [component](../api#django_components.Component) with the default settings,
    you only need to provide the name of the component:

    ```bash
    python manage.py startcomponent my_component
    ```

    This will create a new component named `my_component` in the `components` directory of
    your Django project. The JavaScript, CSS, and template files will be named `script.js`,
    `style.css`, and `template.html`, respectively.

    #### Creating a Component with Custom Settings

    You can also create a component with custom settings by providing additional arguments:

    ```bash
    python manage.py startcomponent new_component --path my_components --js my_script.js --css\
        my_style.css --template my_template.html
    ```

    This will create a new component named `new_component` in the `my_components` directory.
    The JavaScript, CSS, and template files will be named `my_script.js`, `my_style.css`, and
    `my_template.html`, respectively.

    #### Overwriting an Existing Component

    If you want to overwrite an existing component, you can use the `--force` option:

    ```bash
    python manage.py startcomponent my_component --force
    ```

    This will overwrite the existing `my_component` if it exists.

    #### Simulating Component Creation

    If you want to simulate the creation of a component without actually creating any files, you can use the `--dry-run` option:

    ```bash
    python manage.py startcomponent my_component --dry-run
    ```

    This will simulate the creation of `my_component` without creating any files.
    """  # noqa: E501

    help = "Create a new django component."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "name",
            type=str,
            help="The name of the component to create. This is a required argument.",
        )
        parser.add_argument(
            "--path",
            type=str,
            help=(
                "The path to the component's directory. This is an optional argument. If not provided, "
                "the command will use the `COMPONENTS.dirs` setting from your Django settings."
            ),
        )
        parser.add_argument(
            "--js",
            type=str,
            help="The name of the JavaScript file. This is an optional argument. The default value is `script.js`.",
        )
        parser.add_argument(
            "--css",
            type=str,
            help="The name of the CSS file. This is an optional argument. The default value is `style.css`.",
        )
        parser.add_argument(
            "--template",
            type=str,
            help="The name of the template file. This is an optional argument. The default value is `template.html`.",
        )
        parser.add_argument(
            "--inline",
            action="store_true",
            help="Inline the component's JS, CSS and HTML",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="This option allows you to overwrite existing files if they exist. This is an optional argument.",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help=(
                "This option allows the command to print additional information during component "
                "creation. This is an optional argument."
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help=(
                "This option allows you to simulate component creation without actually creating any files. "
                "This is an optional argument. The default value is `False`."
            ),
        )

    def handle(self, *args: Any, **kwargs: Any) -> None:
        name = kwargs["name"]

        if not name:
            raise CommandError("You must specify a component name")

        path = kwargs["path"]
        js_filename = kwargs.get("js") or boilerplate.js_filename
        css_filename = kwargs.get("css") or boilerplate.css_filename
        template_filename = kwargs.get("template") or boilerplate.template_filename
        inline = kwargs["inline"]
        force = kwargs["force"]
        verbose = kwargs["verbose"]
        dry_run = kwargs["dry_run"]

        if path:
            component_path = os.path.join(path, name)
        else:
            if not app_settings.DIRS:
                raise CommandError(
                    "Missing component destination - Either specify 'path' argument, "
                    "or set COMPONENTS.dirs in your django settings."
                )
            elif not len(app_settings.DIRS) > 1:
                raise CommandError(
                    "Ambiguous component destination - COMPONENTS.dirs contains multiple directories, "
                    "please specify path with the 'path' argument"
                )

            component_dir = app_settings.DIRS[0]
            if isinstance(component_dir, tuple):
                component_dir = component_dir[1]

            component_path = os.path.join(component_dir, name)

        if os.path.exists(component_path):
            if force:
                if verbose:
                    self.stdout.write(
                        self.style.WARNING(
                            f'The component "{name}" already exists at {component_path}. Overwriting...'
                        )
                    )
                else:
                    self.stdout.write(self.style.WARNING(f'The component "{name}" already exists. Overwriting...'))
            else:
                raise CommandError(
                    f'The component "{name}" already exists at {component_path}. Use --force to overwrite.'
                )

        if not dry_run:
            os.makedirs(component_path, exist_ok=force)

            if not inline:
                js_filepath = os.path.join(component_path, js_filename)
                with open(js_filepath, "w") as f:
                    js_content = boilerplate.js_render(name, js_filepath)
                    js_content = dedent(js_content).strip()
                    f.write(js_content)

                css_filepath = os.path.join(component_path, css_filename)
                with open(css_filepath, "w") as f:
                    css_content = boilerplate.js_render(name, css_filepath)
                    css_content = dedent(css_content).strip()
                    f.write(css_content)

                template_filepath = os.path.join(component_path, template_filename)
                with open(template_filepath, "w") as f:
                    template_content = boilerplate.template_render(name, template_filepath)
                    css_content = dedent(css_content).strip()
                    f.write(css_content)

            py_filepath = os.path.join(component_path, f"{name}.py")
            with open(py_filepath, "w") as f:
                content = boilerplate.py_render(name, py_filepath, inline, js_content, css_content, template_content)
                content = dedent(content).strip()
                f.write(content)

        if verbose:
            self.stdout.write(self.style.SUCCESS(f"Successfully created {name} component at {component_path}"))
        else:
            self.stdout.write(self.style.SUCCESS(f"Successfully created {name} component"))
