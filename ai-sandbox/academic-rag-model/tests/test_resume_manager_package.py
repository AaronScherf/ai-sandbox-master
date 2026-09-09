import importlib
import unittest


class TestResumeManagerPackageScaffolding(unittest.TestCase):
    def test_package_imports(self):
        module = importlib.import_module("resume_manager")
        self.assertIsNotNone(module)

    def test_xhtml2pdf_is_installed(self):
        import xhtml2pdf  # noqa: F401

    def test_markdown_is_installed(self):
        import markdown  # noqa: F401
