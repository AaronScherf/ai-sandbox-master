import importlib
import unittest


class TestVideoNotesPackageScaffolding(unittest.TestCase):
    def test_package_imports(self):
        module = importlib.import_module("video_notes")
        self.assertIsNotNone(module)

    def test_yt_dlp_is_installed(self):
        import yt_dlp  # noqa: F401

    def test_faster_whisper_is_installed(self):
        import faster_whisper  # noqa: F401
