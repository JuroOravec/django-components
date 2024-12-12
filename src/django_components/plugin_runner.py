from typing import List

from django_components.app_settings import app_settings
from django_components.plugin import ComponentPlugin, MergePlugin


class PluginRunner(MergePlugin):
    def __init__(self) -> None:
        # Noop so that the initialiaation doesn't accept any arguments
        pass

    @property
    def plugins(self) -> List[ComponentPlugin]:  # type: ignore[override]
        return app_settings.PLUGINS


plugins = PluginRunner()
