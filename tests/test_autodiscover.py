import sys
from unittest import TestCase

from django.conf import settings

from django_components import AlreadyRegistered, registry
from django_components.autodiscovery import autodiscover, import_libraries

from .django_test_setup import setup_test_config


# NOTE: This is different from BaseTestCase in testutils.py, because here we need
# TestCase instead of SimpleTestCase.
class _TestCase(TestCase):
    def tearDown(self) -> None:
        super().tearDown()
        registry.clear()


class TestAutodiscover(_TestCase):
    def test_autodiscover(self):
        setup_test_config({"autodiscover": False})

        all_components = registry.all().copy()
        self.assertNotIn("single_file_component", all_components)
        self.assertNotIn("multi_file_component", all_components)
        self.assertNotIn("relative_file_component", all_components)
        self.assertNotIn("relative_file_pathobj_component", all_components)

        try:
            modules = autodiscover(map_module=lambda p: "tests." + p if p.startswith("components") else p)
        except AlreadyRegistered:
            self.fail("Autodiscover should not raise AlreadyRegistered exception")

        self.assertIn("tests.components", modules)
        self.assertIn("tests.components.single_file", modules)
        self.assertIn("tests.components.staticfiles.staticfiles", modules)
        self.assertIn("tests.components.multi_file.multi_file", modules)
        self.assertIn("tests.components.relative_file_pathobj.relative_file_pathobj", modules)
        self.assertIn("tests.components.relative_file.relative_file", modules)
        self.assertIn("tests.test_app.components.app_lvl_comp.app_lvl_comp", modules)
        self.assertIn("django_components.components", modules)
        self.assertIn("django_components.components.dynamic", modules)

        all_components = registry.all().copy()
        self.assertIn("single_file_component", all_components)
        self.assertIn("multi_file_component", all_components)
        self.assertIn("relative_file_component", all_components)
        self.assertIn("relative_file_pathobj_component", all_components)


class TestImportLibraries(_TestCase):
    def test_import_libraries(self):
        # Prepare settings
        setup_test_config({"autodiscover": False})
        settings.COMPONENTS["libraries"] = ["tests.components.single_file", "tests.components.multi_file.multi_file"]

        # Ensure we start with a clean state
        registry.clear()
        all_components = registry.all().copy()
        self.assertNotIn("single_file_component", all_components)
        self.assertNotIn("multi_file_component", all_components)

        # Ensure that the modules are executed again after import
        if "tests.components.single_file" in sys.modules:
            del sys.modules["tests.components.single_file"]
        if "tests.components.multi_file.multi_file" in sys.modules:
            del sys.modules["tests.components.multi_file.multi_file"]

        try:
            modules = import_libraries()
        except AlreadyRegistered:
            self.fail("Autodiscover should not raise AlreadyRegistered exception")

        self.assertIn("tests.components.single_file", modules)
        self.assertIn("tests.components.multi_file.multi_file", modules)

        all_components = registry.all().copy()
        self.assertIn("single_file_component", all_components)
        self.assertIn("multi_file_component", all_components)

        settings.COMPONENTS["libraries"] = []

    def test_import_libraries_map_modules(self):
        # Prepare settings
        setup_test_config(
            {
                "autodiscover": False,
            }
        )
        settings.COMPONENTS["libraries"] = ["components.single_file", "components.multi_file.multi_file"]

        # Ensure we start with a clean state
        registry.clear()
        all_components = registry.all().copy()
        self.assertNotIn("single_file_component", all_components)
        self.assertNotIn("multi_file_component", all_components)

        # Ensure that the modules are executed again after import
        if "tests.components.single_file" in sys.modules:
            del sys.modules["tests.components.single_file"]
        if "tests.components.multi_file.multi_file" in sys.modules:
            del sys.modules["tests.components.multi_file.multi_file"]

        try:
            modules = import_libraries(map_module=lambda p: "tests." + p if p.startswith("components") else p)
        except AlreadyRegistered:
            self.fail("Autodiscover should not raise AlreadyRegistered exception")

        self.assertIn("tests.components.single_file", modules)
        self.assertIn("tests.components.multi_file.multi_file", modules)

        all_components = registry.all().copy()
        self.assertIn("single_file_component", all_components)
        self.assertIn("multi_file_component", all_components)

        settings.COMPONENTS["libraries"] = []
