import os
import tempfile
import unittest

import yaml

from resume_manager.markdown_sync import export_to_markdown
from resume_manager.sync_tailored_md import sync_tailored_md

_TAILORED = {
    "contact": {"name": "Aaron Scherf", "email": "a@x.com"},
    "work_experience": [
        {"id": "acme-1", "org": "Acme", "role": "Engineer", "location": "NYC",
         "start_date": "2020", "end_date": "Present", "bullets": ["Grew revenue 30%"]},
    ],
    "education": [], "awards": [], "publications": [], "skills": [],
}


class TestSyncTailoredMd(unittest.TestCase):
    def _setup(self, tmp):
        yaml_path = os.path.join(tmp, "tailored_resume.yaml")
        with open(yaml_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(_TAILORED, f, sort_keys=False, allow_unicode=True)
        md_path = os.path.join(tmp, "tailored_resume.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(export_to_markdown(_TAILORED))
        return yaml_path, md_path

    def test_edited_bullet_syncs_into_the_yaml_and_rerenders_pdf(self):
        with tempfile.TemporaryDirectory() as tmp:
            yaml_path, md_path = self._setup(tmp)
            with open(md_path, encoding="utf-8") as f:
                markdown_text = f.read()
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(markdown_text.replace("Grew revenue 30%", "Grew revenue 45%, a company record"))

            result = sync_tailored_md(tmp)

            self.assertIn("Synced", result)
            with open(yaml_path, encoding="utf-8") as f:
                updated = yaml.safe_load(f)
            self.assertEqual(updated["work_experience"][0]["bullets"], ["Grew revenue 45%, a company record"])
            pdf_path = os.path.join(tmp, "Tailored_Resume.pdf")
            self.assertTrue(os.path.exists(pdf_path))
            with open(pdf_path, "rb") as f:
                self.assertTrue(f.read(5).startswith(b"%PDF"))

    def test_missing_md_file_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                sync_tailored_md(tmp)
