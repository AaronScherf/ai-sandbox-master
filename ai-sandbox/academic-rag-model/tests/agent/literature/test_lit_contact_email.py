import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from agent.literature.cli import _contact_email


class TestContactEmail(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.env_file = Path(tmp.name) / ".env"
        patcher = mock.patch("core.env.gemini_utils._resolve_env_path", lambda *a: self.env_file)
        patcher.start()
        self.addCleanup(patcher.stop)

    def write_env(self, text):
        self.env_file.write_text(text, encoding="utf-8")

    def test_explicit_beats_environment_beats_dotenv(self):
        self.write_env("OPENALEX_CONTACT_EMAIL=dotenv@x.test\n")
        with mock.patch.dict(os.environ, {"OPENALEX_CONTACT_EMAIL": "env@x.test"}):
            self.assertEqual(_contact_email("flag@x.test"), "flag@x.test")
            self.assertEqual(_contact_email(None), "env@x.test")
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(_contact_email(None), "dotenv@x.test")

    def test_dotenv_read_does_not_touch_the_environment(self):
        self.write_env("OPENALEX_CONTACT_EMAIL=dotenv@x.test\nGEMINI_API_KEY=secret\n")
        with mock.patch.dict(os.environ, {}, clear=True):
            _contact_email(None)
            self.assertEqual(dict(os.environ), {})

    def test_missing_file_or_key_or_blank_value_gives_none(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(_contact_email(None))  # no .env file
            self.write_env("OTHER=1\n")
            self.assertIsNone(_contact_email(None))
            self.write_env("OPENALEX_CONTACT_EMAIL=\n")
            self.assertIsNone(_contact_email(None))


if __name__ == "__main__":
    unittest.main()
