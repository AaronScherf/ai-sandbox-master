import os
import tempfile
import unittest

import yaml

from resume_manager.markdown_sync import export_to_markdown
from resume_manager.sync_master_md import sync_master_md

_MASTER = {
    "contact": {"name": "Aaron Scherf", "email": "a@x.com"},
    "work_experience": [
        {"id": "acme-1", "org": "Acme", "role": "Engineer", "location": "NYC",
         "start_date": "2020", "end_date": "Present", "bullets": ["Grew revenue 30%"]},
    ],
    "education": [], "awards": [], "publications": [], "skills": [],
}


class TestSyncMasterMd(unittest.TestCase):
    def _setup(self, tmp, master=_MASTER):
        master_path = os.path.join(tmp, "resume_master.yaml")
        with open(master_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(master, f, sort_keys=False, allow_unicode=True)
        master_md_path = os.path.join(tmp, "resume_master.md")
        with open(master_md_path, "w", encoding="utf-8") as f:
            f.write(export_to_markdown(master, embed_hash=True))
        return master_path, master_md_path

    def test_edited_bullet_syncs_into_the_yaml(self):
        with tempfile.TemporaryDirectory() as tmp:
            master_path, master_md_path = self._setup(tmp)
            with open(master_md_path, encoding="utf-8") as f:
                markdown_text = f.read()
            edited = markdown_text.replace("Grew revenue 30%", "Grew revenue 45%, a company record")

            with open(master_md_path, "w", encoding="utf-8") as f:
                f.write(edited)

            result = sync_master_md(tmp)

            self.assertIn("Synced", result)
            with open(master_path, encoding="utf-8") as f:
                updated = yaml.safe_load(f)
            self.assertEqual(updated["work_experience"][0]["bullets"], ["Grew revenue 45%, a company record"])
            self.assertEqual(updated["work_experience"][0]["id"], "acme-1")

    def test_refreshes_the_md_hash_after_a_successful_sync(self):
        with tempfile.TemporaryDirectory() as tmp:
            master_path, master_md_path = self._setup(tmp)
            sync_master_md(tmp)
            # A second sync (no further edits) must still succeed -- the
            # hash embedded after the first sync should match the
            # now-current YAML.
            result = sync_master_md(tmp)
            self.assertIn("Synced", result)

    def test_stale_md_is_refused_not_silently_overwritten(self):
        # Real risk this guards against: merge_resumes.py changes
        # resume_master.yaml after resume_master.md was exported --
        # syncing the (now stale) .md back must not silently discard
        # that auto-merged change.
        with tempfile.TemporaryDirectory() as tmp:
            master_path, master_md_path = self._setup(tmp)

            changed_master = {**_MASTER, "awards": [{"name": "New Award", "description": "d", "date": "2020"}]}
            with open(master_path, "w", encoding="utf-8") as f:
                yaml.safe_dump(changed_master, f, sort_keys=False, allow_unicode=True)

            with self.assertRaises(RuntimeError):
                sync_master_md(tmp)

            with open(master_path, encoding="utf-8") as f:
                still_current = yaml.safe_load(f)
            self.assertEqual(still_current, changed_master)

    def test_missing_md_file_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            master_path = os.path.join(tmp, "resume_master.yaml")
            with open(master_path, "w", encoding="utf-8") as f:
                yaml.safe_dump(_MASTER, f)
            with self.assertRaises(FileNotFoundError):
                sync_master_md(tmp)
