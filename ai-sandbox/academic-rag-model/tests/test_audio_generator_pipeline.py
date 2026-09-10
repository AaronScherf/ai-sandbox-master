import os
import tempfile
import unittest
from unittest.mock import patch

from audio_generator.discovery import SourceFile
from audio_generator.pipeline import run_pipeline
from audio_generator.sections import NarratedSection
from audio_generator.state import load_state


def _make_source(
    hub: str, rel_md: str = "academic_notes/math-camp/lecture-notes/a.md", content: str = "hello world",
    content_type: str = "notes",
) -> SourceFile:
    abs_md = os.path.join(hub, rel_md.replace("/", os.sep))
    os.makedirs(os.path.dirname(abs_md), exist_ok=True)
    with open(abs_md, "w", encoding="utf-8") as f:
        f.write(content)
    return SourceFile(
        course="math-camp", content_type=content_type,
        rel_md_path=rel_md, abs_md_path=abs_md,
        rel_mp3_path=rel_md[:-3] + ".mp3", abs_mp3_path=abs_md[:-3] + ".mp3",
    )


class TestRunPipelineTextbookSources(unittest.TestCase):
    """textbook content is unaffected by spec §3.2's episode splitting --
    still exactly one <name>.mp3/<name>.narrated.md per source, the same
    behavior as before this revision."""

    @patch("audio_generator.pipeline.synthesize_speech")
    @patch("audio_generator.pipeline.narrate_for_speech", side_effect=lambda text: text)
    @patch("audio_generator.pipeline.discover_source_files")
    def test_generates_audio_for_a_new_source(self, mock_discover, mock_narrate, mock_synthesize):
        with tempfile.TemporaryDirectory() as hub, tempfile.TemporaryDirectory() as audio_generator_root:
            source = _make_source(hub, content_type="textbook")
            mock_discover.return_value = [source]

            summary = run_pipeline("math-camp", hub, audio_generator_root, ["textbook"], engine="piper")

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
            source = _make_source(hub, content_type="textbook")
            mock_discover.return_value = [source]
            with open(source.abs_mp3_path, "wb") as f:
                f.write(b"fake mp3")

            run_pipeline("math-camp", hub, audio_generator_root, ["textbook"], engine="piper")
            mock_synthesize.reset_mock()
            summary = run_pipeline("math-camp", hub, audio_generator_root, ["textbook"], engine="piper")

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
            source = _make_source(hub, content="![diagram](img.png)", content_type="textbook")
            mock_discover.return_value = [source]

            summary = run_pipeline("math-camp", hub, audio_generator_root, ["textbook"], engine="piper")

            self.assertEqual(summary["skipped_empty"], 1)
            mock_synthesize.assert_not_called()

    @patch("audio_generator.pipeline.synthesize_speech", side_effect=RuntimeError("engine crashed"))
    @patch("audio_generator.pipeline.narrate_for_speech", side_effect=lambda text: text)
    @patch("audio_generator.pipeline.discover_source_files")
    def test_a_failed_synthesis_is_recorded_and_does_not_raise(self, mock_discover, mock_narrate, mock_synthesize):
        with tempfile.TemporaryDirectory() as hub, tempfile.TemporaryDirectory() as audio_generator_root:
            source = _make_source(hub, content_type="textbook")
            mock_discover.return_value = [source]

            summary = run_pipeline("math-camp", hub, audio_generator_root, ["textbook"], engine="piper")

            self.assertEqual(summary["failed"], 1)
            state = load_state(audio_generator_root)
            self.assertNotIn(source.rel_md_path, state)
            self.assertFalse(os.path.exists(source.abs_md_path[:-3] + ".narrated.md"))

    @patch("audio_generator.pipeline.synthesize_speech")
    @patch("audio_generator.pipeline.narrate_for_speech", side_effect=lambda text: text)
    @patch("audio_generator.pipeline.discover_source_files")
    def test_a_changed_source_is_regenerated(self, mock_discover, mock_narrate, mock_synthesize):
        with tempfile.TemporaryDirectory() as hub, tempfile.TemporaryDirectory() as audio_generator_root:
            source = _make_source(hub, content="version one", content_type="textbook")
            mock_discover.return_value = [source]
            run_pipeline("math-camp", hub, audio_generator_root, ["textbook"], engine="piper")

            with open(source.abs_mp3_path, "wb") as f:
                f.write(b"fake mp3")
            with open(source.abs_md_path, "w", encoding="utf-8") as f:
                f.write("version two, changed")
            mock_synthesize.reset_mock()

            summary = run_pipeline("math-camp", hub, audio_generator_root, ["textbook"], engine="piper")
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
            source = _make_source(hub, content="Some raw markdown with $E[X]$ in it.", content_type="textbook")
            mock_discover.return_value = [source]

            run_pipeline("math-camp", hub, audio_generator_root, ["textbook"], engine="piper")

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


class TestRunPipelineNotesEpisodes(unittest.TestCase):
    """notes content goes through spec §3.2's episode-splitting path:
    one or more <name>__partNN.mp3/.narrated.md per source, plus a
    <name>__index.md manifest. narrate_sections() (the boundary that
    calls the real narrate.py/Gemini path) is mocked throughout; the
    real split_into_sections()/group_sections_into_episodes() run
    unmocked, since they're pure and already covered by test_sections.py."""

    @patch("audio_generator.pipeline.synthesize_speech")
    @patch("audio_generator.pipeline.narrate_sections")
    @patch("audio_generator.pipeline.discover_source_files")
    def test_short_single_section_note_produces_exactly_one_part(self, mock_discover, mock_narrate_sections, mock_synthesize):
        with tempfile.TemporaryDirectory() as hub, tempfile.TemporaryDirectory() as audio_generator_root:
            source = _make_source(hub, content="Some short note with no headers.")
            mock_discover.return_value = [source]
            mock_narrate_sections.return_value = [NarratedSection(title="", text="A short narrated body.")]

            summary = run_pipeline("math-camp", hub, audio_generator_root, ["notes"], engine="piper")

            self.assertEqual(summary["generated"], 1)
            base = source.abs_md_path[:-3]
            mock_synthesize.assert_called_once_with("A short narrated body.", f"{base}__part01.mp3", engine="piper")
            self.assertTrue(os.path.exists(f"{base}__part01.narrated.md"))
            self.assertTrue(os.path.exists(f"{base}__index.md"))
            state = load_state(audio_generator_root)
            self.assertIn(f"{source.rel_md_path}::part01", state)

    @patch("audio_generator.pipeline.synthesize_speech")
    @patch("audio_generator.pipeline.narrate_sections")
    @patch("audio_generator.pipeline.discover_source_files")
    def test_note_spanning_two_episodes_produces_two_parts(self, mock_discover, mock_narrate_sections, mock_synthesize):
        with tempfile.TemporaryDirectory() as hub, tempfile.TemporaryDirectory() as audio_generator_root:
            source = _make_source(hub, content="# A\nbody\n\n# B\nbody")
            mock_discover.return_value = [source]
            # Each section is already at the default 20-min max (969*20=19380 chars) on its own,
            # so grouping must give them separate episodes rather than merging.
            mock_narrate_sections.return_value = [
                NarratedSection(title="A", text="x" * 20000),
                NarratedSection(title="B", text="y" * 20000),
            ]

            summary = run_pipeline("math-camp", hub, audio_generator_root, ["notes"], engine="piper")

            self.assertEqual(summary["generated"], 2)
            base = source.abs_md_path[:-3]
            called_paths = {call.args[1] for call in mock_synthesize.call_args_list}
            self.assertEqual(called_paths, {f"{base}__part01.mp3", f"{base}__part02.mp3"})

    @patch("audio_generator.pipeline.synthesize_speech")
    @patch("audio_generator.pipeline.narrate_sections")
    @patch("audio_generator.pipeline.discover_source_files")
    def test_rerun_with_no_change_skips_all_parts(self, mock_discover, mock_narrate_sections, mock_synthesize):
        with tempfile.TemporaryDirectory() as hub, tempfile.TemporaryDirectory() as audio_generator_root:
            source = _make_source(hub, content="Some note.")
            mock_discover.return_value = [source]
            mock_narrate_sections.return_value = [NarratedSection(title="", text="Narrated body.")]

            run_pipeline("math-camp", hub, audio_generator_root, ["notes"], engine="piper")
            # needs_regeneration() checks os.path.exists(abs_mp3_path) -- synthesize_speech is
            # mocked and never actually writes it, so create it manually for the second run's check.
            base = source.abs_md_path[:-3]
            with open(f"{base}__part01.mp3", "wb") as f:
                f.write(b"fake mp3")
            mock_synthesize.reset_mock()

            summary = run_pipeline("math-camp", hub, audio_generator_root, ["notes"], engine="piper")

            self.assertEqual(summary["skipped_unchanged"], 1)
            mock_synthesize.assert_not_called()

    @patch("audio_generator.pipeline.synthesize_speech")
    @patch("audio_generator.pipeline.narrate_sections")
    @patch("audio_generator.pipeline.discover_source_files")
    def test_editing_the_source_regenerates_all_parts(self, mock_discover, mock_narrate_sections, mock_synthesize):
        with tempfile.TemporaryDirectory() as hub, tempfile.TemporaryDirectory() as audio_generator_root:
            source = _make_source(hub, content="version one")
            mock_discover.return_value = [source]
            mock_narrate_sections.return_value = [NarratedSection(title="", text="Narrated body one.")]
            run_pipeline("math-camp", hub, audio_generator_root, ["notes"], engine="piper")
            base = source.abs_md_path[:-3]
            with open(f"{base}__part01.mp3", "wb") as f:
                f.write(b"fake mp3")

            with open(source.abs_md_path, "w", encoding="utf-8") as f:
                f.write("version two, changed")
            mock_narrate_sections.return_value = [NarratedSection(title="", text="Narrated body two.")]
            mock_synthesize.reset_mock()

            summary = run_pipeline("math-camp", hub, audio_generator_root, ["notes"], engine="piper")

            self.assertEqual(summary["generated"], 1)
            mock_synthesize.assert_called_once()

    @patch("audio_generator.pipeline.synthesize_speech")
    @patch("audio_generator.pipeline.narrate_sections")
    @patch("audio_generator.pipeline.discover_source_files")
    def test_a_source_with_no_speakable_sections_is_skipped_not_failed(self, mock_discover, mock_narrate_sections, mock_synthesize):
        with tempfile.TemporaryDirectory() as hub, tempfile.TemporaryDirectory() as audio_generator_root:
            source = _make_source(hub, content="![diagram](img.png)")
            mock_discover.return_value = [source]
            mock_narrate_sections.return_value = [NarratedSection(title="", text="")]

            summary = run_pipeline("math-camp", hub, audio_generator_root, ["notes"], engine="piper")

            self.assertEqual(summary["skipped_empty"], 1)
            mock_synthesize.assert_not_called()

    @patch("audio_generator.pipeline.synthesize_speech", side_effect=RuntimeError("engine crashed"))
    @patch("audio_generator.pipeline.narrate_sections")
    @patch("audio_generator.pipeline.discover_source_files")
    def test_a_failed_synthesis_is_recorded_and_does_not_raise(self, mock_discover, mock_narrate_sections, mock_synthesize):
        with tempfile.TemporaryDirectory() as hub, tempfile.TemporaryDirectory() as audio_generator_root:
            source = _make_source(hub, content="Some note.")
            mock_discover.return_value = [source]
            mock_narrate_sections.return_value = [NarratedSection(title="", text="Narrated body.")]

            summary = run_pipeline("math-camp", hub, audio_generator_root, ["notes"], engine="piper")

            self.assertEqual(summary["failed"], 1)
            state = load_state(audio_generator_root)
            base = source.abs_md_path[:-3]
            self.assertNotIn(f"{source.rel_md_path}::part01", state)
            self.assertFalse(os.path.exists(f"{base}__part01.narrated.md"))

    @patch("audio_generator.pipeline.synthesize_speech")
    @patch("audio_generator.pipeline.narrate_sections")
    @patch("audio_generator.pipeline.discover_source_files")
    def test_index_manifest_lists_section_titles_per_part(self, mock_discover, mock_narrate_sections, mock_synthesize):
        with tempfile.TemporaryDirectory() as hub, tempfile.TemporaryDirectory() as audio_generator_root:
            source = _make_source(hub, content="# Intro\nbody")
            mock_discover.return_value = [source]
            mock_narrate_sections.return_value = [NarratedSection(title="Intro", text="Narrated body.")]

            run_pipeline("math-camp", hub, audio_generator_root, ["notes"], engine="piper")

            base = source.abs_md_path[:-3]
            with open(f"{base}__index.md", "r", encoding="utf-8") as f:
                index_content = f.read()
            self.assertIn("Intro", index_content)
            self.assertIn("Part 01", index_content)
