import os
import tempfile
import unittest

from audio_generator.discovery import SourceFile
from audio_generator.state import compute_content_hash, load_state, needs_regeneration, save_state


def _source(hub_dir: str, rel_md: str = "academic_notes/math-camp/lecture-notes/a.md") -> SourceFile:
    abs_md = os.path.join(hub_dir, rel_md.replace("/", os.sep))
    os.makedirs(os.path.dirname(abs_md), exist_ok=True)
    return SourceFile(
        course="math-camp", content_type="notes",
        rel_md_path=rel_md, abs_md_path=abs_md,
        rel_mp3_path=rel_md[:-3] + ".mp3", abs_mp3_path=abs_md[:-3] + ".mp3",
    )


class TestComputeContentHash(unittest.TestCase):
    def test_same_content_same_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "a.md")
            with open(path, "w", encoding="utf-8") as f:
                f.write("hello")
            self.assertEqual(compute_content_hash(path), compute_content_hash(path))

    def test_different_content_different_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            path_a, path_b = os.path.join(tmp, "a.md"), os.path.join(tmp, "b.md")
            with open(path_a, "w", encoding="utf-8") as f:
                f.write("hello")
            with open(path_b, "w", encoding="utf-8") as f:
                f.write("hello there")
            self.assertNotEqual(compute_content_hash(path_a), compute_content_hash(path_b))


class TestStateRoundTrip(unittest.TestCase):
    def test_save_then_load_round_trips(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_state(tmp, {"academic_notes/math-camp/lecture-notes/a.md": "abc123"})
            self.assertEqual(load_state(tmp), {"academic_notes/math-camp/lecture-notes/a.md": "abc123"})

    def test_missing_state_file_returns_empty_dict(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(load_state(tmp), {})


class TestNeedsRegeneration(unittest.TestCase):
    def test_true_when_no_prior_record(self):
        with tempfile.TemporaryDirectory() as hub:
            source = _source(hub)
            self.assertTrue(needs_regeneration({}, source, "somehash"))

    def test_false_when_hash_matches_and_mp3_exists(self):
        with tempfile.TemporaryDirectory() as hub:
            source = _source(hub)
            with open(source.abs_mp3_path, "wb") as f:
                f.write(b"fake mp3")
            state = {source.rel_md_path: "somehash"}
            self.assertFalse(needs_regeneration(state, source, "somehash"))

    def test_true_when_hash_matches_but_mp3_is_missing(self):
        with tempfile.TemporaryDirectory() as hub:
            source = _source(hub)
            state = {source.rel_md_path: "somehash"}
            self.assertTrue(needs_regeneration(state, source, "somehash"))

    def test_true_when_hash_differs(self):
        with tempfile.TemporaryDirectory() as hub:
            source = _source(hub)
            with open(source.abs_mp3_path, "wb") as f:
                f.write(b"fake mp3")
            state = {source.rel_md_path: "oldhash"}
            self.assertTrue(needs_regeneration(state, source, "newhash"))
