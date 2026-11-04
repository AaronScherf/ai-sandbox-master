import hashlib
import os
import tempfile
import unittest
from unittest.mock import patch

from audio_generator import pipeline
from audio_generator.discovery import SourceFile
from audio_generator.state import (
    compute_content_hash, episode_state_key, legacy_content_hash, load_state, needs_regeneration, save_state,
)

NOTE = "---\ntitle: T\nsource_pdf: old/a.pdf\n---\nbody text\n"
MOVED = "---\ntitle: T\nsource_pdf: new/a.pdf\nhub_id: abc123\n---\nbody text\n"


def _make(hub, content=NOTE, rel="academic_notes/c/lecture_notes/a.md"):
    abs_md = os.path.join(hub, rel.replace("/", os.sep))
    os.makedirs(os.path.dirname(abs_md), exist_ok=True)
    with open(abs_md, "w", encoding="utf-8", newline="") as f:
        f.write(content)
    abs_mp3 = abs_md[:-3] + ".mp3"
    with open(abs_mp3, "wb") as f:
        f.write(b"mp3")
    return SourceFile(course="c", content_type="notes", rel_md_path=rel, abs_md_path=abs_md,
                      rel_mp3_path=rel[:-3] + ".mp3", abs_mp3_path=abs_mp3)


def _write(src, text):
    with open(src.abs_md_path, "w", encoding="utf-8", newline="") as f:
        f.write(text)


class TestStateHash(unittest.TestCase):
    def test_moved_note_with_rewritten_source_lines_does_not_regenerate(self):
        with tempfile.TemporaryDirectory() as hub:
            src = _make(hub)
            state = {src.rel_md_path: compute_content_hash(src.abs_md_path)}
            _write(src, MOVED)
            self.assertFalse(needs_regeneration(state, src, compute_content_hash(src.abs_md_path)))

    def test_state_stored_with_legacy_hash_does_not_regenerate_until_content_changes(self):
        with tempfile.TemporaryDirectory() as hub:
            src = _make(hub)
            state = {src.rel_md_path: legacy_content_hash(src.abs_md_path)}
            cur, leg = compute_content_hash(src.abs_md_path), legacy_content_hash(src.abs_md_path)
            self.assertNotEqual(cur, leg)
            self.assertFalse(needs_regeneration(state, src, cur, leg))
            self.assertTrue(needs_regeneration(state, src, cur))  # legacy not offered
            _write(src, NOTE + "more\n")
            self.assertTrue(needs_regeneration(state, src, compute_content_hash(src.abs_md_path),
                                               legacy_content_hash(src.abs_md_path)))

    def test_body_edit_regenerates(self):
        with tempfile.TemporaryDirectory() as hub:
            src = _make(hub)
            state = {src.rel_md_path: compute_content_hash(src.abs_md_path)}
            _write(src, NOTE.replace("body text", "other body"))
            self.assertTrue(needs_regeneration(state, src, compute_content_hash(src.abs_md_path)))

    def test_no_frontmatter_canonical_equals_legacy(self):
        with tempfile.TemporaryDirectory() as hub:
            src = _make(hub, "just a body\n")
            self.assertEqual(compute_content_hash(src.abs_md_path), legacy_content_hash(src.abs_md_path))
            self.assertEqual(legacy_content_hash(src.abs_md_path), hashlib.sha256(b"just a body\n").hexdigest())
            # existing state keeps matching with no upgrade needed
            state = {src.rel_md_path: legacy_content_hash(src.abs_md_path)}
            self.assertFalse(needs_regeneration(state, src, compute_content_hash(src.abs_md_path)))

    def test_frontmatter_without_location_lines_canonical_equals_legacy(self):
        with tempfile.TemporaryDirectory() as hub:
            src = _make(hub, "---\ntitle: T\n---\nbody\n")
            self.assertEqual(compute_content_hash(src.abs_md_path), legacy_content_hash(src.abs_md_path))


class TestPipelineUpgrade(unittest.TestCase):
    def _run_with_stubbed_episodes(self, hub, root):
        with patch.object(pipeline, "narrate_sections", return_value=[]), \
             patch.object(pipeline, "group_sections_into_episodes", return_value=["ep1", "ep2"]), \
             patch.object(pipeline, "_write_index_manifest"), \
             patch.object(pipeline, "_synthesize_episode") as synth, \
             patch.object(pipeline, "discover_source_files") as disc:
            self.src = disc.return_value = [self.src]
            summary = pipeline.run_pipeline("c", hub, root, ["notes"])
            return summary, synth

    def test_legacy_episode_entries_upgraded_without_regeneration(self):
        with tempfile.TemporaryDirectory() as hub, tempfile.TemporaryDirectory() as root:
            src = _make(hub)
            mp3_base = src.abs_mp3_path[:-4]
            for i in (1, 2):
                with open(f"{mp3_base}__part{i:02d}.mp3", "wb") as f:
                    f.write(b"x")
            leg = legacy_content_hash(src.abs_md_path)
            save_state(root, {episode_state_key(src.rel_md_path, i): leg for i in (1, 2)})
            self.src = src
            summary, synth = self._run_with_stubbed_episodes(hub, root)
            synth.assert_not_called()
            self.assertEqual(summary["skipped_unchanged"], 2)
            cur = compute_content_hash(src.abs_md_path)
            self.assertEqual(set(load_state(root).values()), {cur})
            # now the location lines are rewritten: still no regeneration
            _write(src, MOVED)
            self.src = src
            summary, synth = self._run_with_stubbed_episodes(hub, root)
            synth.assert_not_called()
            self.assertEqual(summary["skipped_unchanged"], 2)

    def test_dry_run_does_not_write_state(self):
        with tempfile.TemporaryDirectory() as hub, tempfile.TemporaryDirectory() as root:
            src = _make(hub)
            leg = legacy_content_hash(src.abs_md_path)
            state = {src.rel_md_path: leg}
            with patch.object(pipeline, "discover_source_files", return_value=[src]), \
                 patch.object(pipeline, "load_state", return_value=state), \
                 patch.object(pipeline, "save_state") as save, \
                 patch.object(pipeline.shutil, "which", return_value="ffmpeg"), \
                 patch("sys.argv", ["x", "--course", "c", "--dry-run"]), \
                 patch("builtins.print") as pr:
                pipeline.main()
            save.assert_not_called()
            self.assertEqual(state[src.rel_md_path], leg)
            pr.assert_called_with(f"up to date: {src.rel_md_path}")


if __name__ == "__main__":
    unittest.main()
