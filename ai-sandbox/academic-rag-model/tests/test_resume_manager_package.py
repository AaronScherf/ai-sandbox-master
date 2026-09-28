import importlib
import unittest


class TestResumeManagerPackageScaffolding(unittest.TestCase):
    def test_package_imports(self):
        module = importlib.import_module("resume_manager")
        self.assertIsNotNone(module)

    def test_typst_is_installed(self):
        import typst  # noqa: F401

    def test_pyyaml_is_installed(self):
        import yaml  # noqa: F401
