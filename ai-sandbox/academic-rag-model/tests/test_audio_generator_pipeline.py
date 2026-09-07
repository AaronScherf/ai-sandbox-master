import os
import tempfile
import unittest
from unittest.mock import patch

from audio_generator.discovery import SourceFile
from audio_generator.pipeline import run_pipeline
from audio_generator.state import load_state


def _make_source(hub: str, rel_md: str = "academic_notes/math-camp/lecture-notes/a.md", content: str = "hello world") -> SourceFile:
    abs_md = os.path.join(hub, rel_md.replace("/", os.sep))
    os.makedirs(os.path.dirname(abs_md), exist_ok=True)
    with open(abs_md, "w", encoding="utf-8") as f:
        f.write(content)
    return SourceFile(
        course="math-camp", content_type="notes",
        rel_md_path=rel_md, abs_md_path=abs_md,
        rel_mp3_path=rel_md[:-3] + ".mp3", abs_mp3_path=abs_md[:-3] + ".mp3",
    )


class TestRunPipeline(unittest.TestCase):
    @patch("audio_generator.pipeline.synthesize_speech")
    @patch("audio_generator.pipeline.narrate_for_speech", side_effect=lambda text: text)
    @patch("audio_generator.pipeline.discover_source_files")
    def test_generates_audio_for_a_new_source(self, mock_discover, mock_narrate, mock_synthesize):
        with tempfile.TemporaryDirectory() as hub, tempfile.TemporaryDirectory() as audio_generator_root:
            source = _make_source(hub)
            mock_discover.return_value = [source]

            summary = run_pipeline("math-camp", hub, audio_generator_root, ["notes"], engine="piper")

            self.assertEqual(summary["generated"], 1)
            mock_synthesize.assert_called_once()
            self.assertEqual(mock_synthesize.call_args[0][1], source.abs_mp3_path)
            state = load_state(audio_generator_root)
            self.assertIn(source.rel_md_path, state)

    @patch("audio_generator.pipeline.synthesize_speech")
    @patch("audio_generator.pipeline.narrate_for_speech", side_effect=lambda text: text)
    @patch("audio_generator.pipeline.discover_source_files")
    def test_skips_a_source_whose_mp3_is_already_up_to_date(self, mock_discover, mock_narrate, mock_synthesize):
        with tempfile.TemporaryDirectory() as hub, tempfile.TemporaryDirectory() as audio_generator_root:
            source = _make_source(hub)
            mock_discover.return_value = [source]
            with open(source.abs_mp3_path, "wb") as f:
                f.write(b"fake mp3")

            run_pipeline("math-camp", hub, audio_generator_root, ["notes"], engine="piper")
            mock_synthesize.reset_mock()
            summary = run_pipeline("math-camp", hub, audio_generator_root, ["notes"], engine="piper")

            self.assertEqual(summary["skipped_unchanged"], 1)
            mock_synthesize.assert_not_called()

    @patch("audio_generator.pipeline.synthesize_speech")
    @patch("audio_generator.pipeline.narrate_for_speech", side_effect=lambda text: text)
    @patch("audio_generator.pipeline.discover_source_files")
    def test_a_source_with_no_speakable_text_is_skipped_not_failed(self, mock_discover, mock_narrate, mock_synthesize):
        with tempfile.TemporaryDirectory() as hub, tempfile.TemporaryDirectory() as audio_generator_root:
            # A bare image reference has no text node for BeautifulSoup's
            # get_text() to return -- unlike a code block, which cleaner.py
            # deliberately replaces with a non-empty "[Code snippet
            # omitted.]" placeholder (see test_cleaner.py).
            source = _make_source(hub, content="![diagram](img.png)")
            mock_discover.return_value = [source]

            summary = run_pipeline("math-camp", hub, audio_generator_root, ["notes"], engine="piper")

            self.assertEqual(summary["skipped_empty"], 1)
            mock_synthesize.assert_not_called()

    @patch("audio_generator.pipeline.synthesize_speech", side_effect=RuntimeError("engine crashed"))
    @patch("audio_generator.pipeline.narrate_for_speech", side_effect=lambda text: text)
    @patch("audio_generator.pipeline.discover_source_files")
    def test_a_failed_synthesis_is_recorded_and_does_not_raise(self, mock_discover, mock_narrate, mock_synthesize):
        with tempfile.TemporaryDirectory() as hub, tempfile.TemporaryDirectory() as audio_generator_root:
            source = _make_source(hub)
            mock_discover.return_value = [source]

            summary = run_pipeline("math-camp", hub, audio_generator_root, ["notes"], engine="piper")

            self.assertEqual(summary["failed"], 1)
            state = load_state(audio_generator_root)
            self.assertNotIn(source.rel_md_path, state)
            self.assertFalse(os.path.exists(source.abs_md_path[:-3] + ".narrated.md"))

    @patch("audio_generator.pipeline.synthesize_speech")
    @patch("audio_generator.pipeline.narrate_for_speech", side_effect=lambda text: text)
    @patch("audio_generator.pipeline.discover_source_files")
    def test_a_changed_source_is_regenerated(self, mock_discover, mock_narrate, mock_synthesize):
        with tempfile.TemporaryDirectory() as hub, tempfile.TemporaryDirectory() as audio_generator_root:
            source = _make_source(hub, content="version one")
            mock_discover.return_value = [source]
            run_pipeline("math-camp", hub, audio_generator_root, ["notes"], engine="piper")

            with open(source.abs_mp3_path, "wb") as f:
                f.write(b"fake mp3")
            with open(source.abs_md_path, "w", encoding="utf-8") as f:
                f.write("version two, changed")
            mock_synthesize.reset_mock()

            summary = run_pipeline("math-camp", hub, audio_generator_root, ["notes"], engine="piper")
            self.assertEqual(summary["generated"], 1)
            mock_synthesize.assert_called_once()

    @patch("audio_generator.pipeline.synthesize_speech")
    @patch("audio_generator.pipeline.narrate_for_speech")
    @patch("audio_generator.pipeline.discover_source_files")
    def test_narrate_runs_before_clean_and_result_is_written_to_a_sibling_file(
        self, mock_discover, mock_narrate, mock_synthesize,
    ):
        mock_narrate.return_value = "# Heading\n\nThe expected value of X is three."
        with tempfile.TemporaryDirectory() as hub, tempfile.TemporaryDirectory() as audio_generator_root:
            source = _make_source(hub, content="Some raw markdown with $E[X]$ in it.")
            mock_discover.return_value = [source]

            run_pipeline("math-camp", hub, audio_generator_root, ["notes"], engine="piper")

            mock_narrate.assert_called_once_with("Some raw markdown with $E[X]$ in it.")
            narrated_path = source.abs_md_path[:-3] + ".narrated.md"
            self.assertTrue(os.path.exists(narrated_path))
            with open(narrated_path, "r", encoding="utf-8") as f:
                written = f.read()
            # The written file is cleaner.py's output (markup stripped),
            # not narrate.py's raw markdown-with-heading return value --
            # confirms clean_markdown_for_speech() ran on narrate.py's
            # output, in that order (spec §3.1).
            self.assertNotIn("#", written)
            self.assertIn("The expected value of X is three.", written)
            self.assertEqual(mock_synthesize.call_args[0][0], written)
