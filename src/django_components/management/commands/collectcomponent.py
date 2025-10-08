from typing import Any

from django.conf import settings
from django.contrib.staticfiles.management.commands.collectstatic import Command as CollectStaticCommand
from django.core.management.base import BaseCommand, CommandParser
from django.core import management

class Command(BaseCommand):
    # TODO UPDATE - SAY THAT IT HAS THE SAME ARGS AS COLLECTSTATIC
    help = 'Collect static files and then run extra code'

    def add_arguments(self, parser: CommandParser) -> None:
        # Use the same args as the original `collectstatic`
        # To access the `add_arguments` method, we instantiate the original command
        collectstatic_command = CollectStaticCommand()
        collectstatic_command.add_arguments(parser)

    def handle(self, *args: Any, **options: Any) -> None:
        # Call the original collectstatic command
        management.call_command('collectstatic', *args, **options)

        # TODO
        # GET ALL COMPONENT FILES
        # GET THEIR JS / CSS
        # SAVE IT TO FILES

        from django_components.autodiscovery import autodiscover
        from django_components.component import _ALL_COMPONENTS
        from django_components.util.misc import get_class_source_file, get_import_path
        from django_components.dependencies import write_component_inline_dependencies_to_static

        if hasattr(settings, "STATIC_ROOT") and settings.STATIC_ROOT:
            autodiscover()

            # TODO
            from typing import List
            from django_components.compilers import CompilerComponentData, compile_files
            data: List[CompilerComponentData] = []
            for comp_cls in _ALL_COMPONENTS:
                source_file = get_class_source_file(comp_cls)
                if not source_file:
                    self.stdout.write(f'Failed to find source file for component {get_import_path(comp_cls)}')
                    continue

                # TODO
                print("COMP_CLS: ", comp_cls)
                print("_comp_path_absolute: ", comp_cls._comp_path_absolute)
                print("_comp_path_relative: ", comp_cls._comp_path_relative)

                if not comp_cls._comp_path_relative:
                    continue

                # TODO: If compilation is NOT enabled, simply copy the files
                files = write_component_inline_dependencies_to_static(comp_cls)
                data.append(CompilerComponentData(comp_cls, files))

            # TODO
            print("FILES: ", files)
            compiled_files = compile_files(data)
            print("OUT_FILES: ", compiled_files)

            # 1. Compile TS to JS
            # 2. Compile Sass to CSS
            # 3. Modify collectstatic (or add component_collectstatic) to
            #    extract JS from components, and compile TS to JS / Sass to CSS
