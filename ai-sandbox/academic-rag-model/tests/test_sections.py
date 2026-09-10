import unittest
from unittest.mock import MagicMock, patch

from audio_generator.sections import (
    Episode,
    NarratedSection,
    Section,
    group_sections_into_episodes,
    narrate_sections,
    split_into_sections,
)


class TestSplitIntoSections(unittest.TestCase):
    def test_no_headers_produces_one_titleless_section(self):
        sections = split_into_sections("Just plain prose, no headers here at all.")
        self.assertEqual(len(sections), 1)
        self.assertIsNone(sections[0].title)
        self.assertIn("Just plain prose", sections[0].body)

    def test_splits_at_every_header_level(self):
        md = "# Chapter One\nBody one.\n\n## 1.1 Subsection\nBody two.\n\n# Chapter Two\nBody three."
        sections = split_into_sections(md)
        self.assertEqual([s.title for s in sections], ["Chapter One", "1.1 Subsection", "Chapter Two"])

    def test_content_before_first_header_becomes_titleless_leading_section(self):
        md = "Some preamble text.\n\n# First Real Header\nBody."
        sections = split_into_sections(md)
        self.assertEqual(len(sections), 2)
        self.assertIsNone(sections[0].title)
        self.assertIn("preamble", sections[0].body)
        self.assertEqual(sections[1].title, "First Real Header")

    def test_body_excludes_the_header_line_itself(self):
        md = "# A Title\nThe body text."
        sections = split_into_sections(md)
        self.assertNotIn("# A Title", sections[0].body)
        self.assertIn("The body text.", sections[0].body)

    def test_a_section_body_runs_up_to_but_not_into_the_next_header(self):
        md = "# One\nBody one.\n\n# Two\nBody two."
        sections = split_into_sections(md)
        self.assertNotIn("Two", sections[0].body)


def _narrated(title: str, char_count: int) -> NarratedSection:
    return NarratedSection(title=title, text="x" * char_count)


class TestGroupSectionsIntoEpisodes(unittest.TestCase):
    def test_short_sections_are_grouped_into_one_episode(self):
        sections = [_narrated("A", 1000), _narrated("B", 1000)]
        episodes = group_sections_into_episodes(sections, chars_per_minute=1000, target_min_minutes=10, target_max_minutes=20)
        self.assertEqual(len(episodes), 1)

    def test_stops_grouping_once_the_minimum_is_met_and_the_max_would_be_exceeded(self):
        # chars_per_minute=1000, min=10min (10000 chars), max=20min (20000 chars).
        # First section alone hits the minimum; a second big section would blow past the max.
        sections = [_narrated("A", 11000), _narrated("B", 15000)]
        episodes = group_sections_into_episodes(sections, chars_per_minute=1000, target_min_minutes=10, target_max_minutes=20)
        self.assertEqual(len(episodes), 2)
        self.assertEqual(episodes[0].section_titles, ["A"])
        self.assertEqual(episodes[1].section_titles, ["B"])

    def test_keeps_grouping_past_the_max_if_the_minimum_has_not_yet_been_met(self):
        # A single section far exceeding target-max, on its own, still becomes one episode
        # (never split inside a section -- spec §3.2).
        sections = [_narrated("Huge", 50000)]
        episodes = group_sections_into_episodes(sections, chars_per_minute=1000, target_min_minutes=10, target_max_minutes=20)
        self.assertEqual(len(episodes), 1)
        self.assertEqual(episodes[0].section_titles, ["Huge"])

    def test_preserves_section_order_within_and_across_episodes(self):
        sections = [_narrated("A", 500), _narrated("B", 500), _narrated("C", 30000)]
        episodes = group_sections_into_episodes(sections, chars_per_minute=1000, target_min_minutes=10, target_max_minutes=20)
        all_titles = [t for ep in episodes for t in ep.section_titles]
        self.assertEqual(all_titles, ["A", "B", "C"])

    def test_episode_text_includes_titles_and_bodies(self):
        sections = [_narrated("My Title", 20)]
        episodes = group_sections_into_episodes(sections, chars_per_minute=1000, target_min_minutes=10, target_max_minutes=20)
        self.assertIn("My Title", episodes[0].text)
        self.assertIn("x" * 20, episodes[0].text)

    def test_titleless_section_omits_the_period_prefix(self):
        sections = [NarratedSection(title="", text="some body text")]
        episodes = group_sections_into_episodes(sections, chars_per_minute=1000, target_min_minutes=10, target_max_minutes=20)
        self.assertEqual(episodes[0].text, "some body text")


@patch("audio_generator.sections.load_dotenv_override")
@patch("audio_generator.sections.get_gemini_client")
class TestNarrateSections(unittest.TestCase):
    def test_dispatches_every_sections_chunks_through_one_shared_call(self, mock_get_client, mock_dotenv):
        client = MagicMock()
        client.models.generate_content.return_value = MagicMock(
            text="Rewritten text long enough to pass the sanity check nicely here yes indeed.",
        )
        mock_get_client.return_value = client

        sections = [
            Section(title="A", body="Body A with $x$ in it. " * 10),
            Section(title="B", body="Body B with $y$ in it. " * 10),
        ]
        with patch("audio_generator.sections.narrate_chunks", side_effect=lambda chunks, client=None: chunks) as mock_narrate_chunks:
            narrate_sections(sections)

        mock_narrate_chunks.assert_called_once()  # one shared call, not one per section
        flat_chunks_arg = mock_narrate_chunks.call_args[0][0]
        self.assertEqual(len(flat_chunks_arg), 2)  # both sections' (single, short) chunks flattened together

    def test_regroups_narrated_chunks_back_into_the_right_sections_in_order(self, mock_get_client, mock_dotenv):
        client = MagicMock()

        def _side_effect(*, model, contents, config):
            if "BODY-A-MARKER" in contents:
                return MagicMock(text="Rewritten A, long enough to pass the sanity check. " * 20)
            return MagicMock(text="Rewritten B, long enough to pass the sanity check. " * 20)

        client.models.generate_content.side_effect = _side_effect
        mock_get_client.return_value = client

        sections = [
            Section(title="A", body="BODY-A-MARKER with $x$ in it. " * 20),
            Section(title="B", body="BODY-B-MARKER with $y$ in it. " * 20),
        ]
        result = narrate_sections(sections)

        self.assertIn("Rewritten A", result[0].text)
        self.assertNotIn("Rewritten B", result[0].text)
        self.assertIn("Rewritten B", result[1].text)
        self.assertNotIn("Rewritten A", result[1].text)

    def test_titleless_section_produces_empty_title(self, mock_get_client, mock_dotenv):
        client = MagicMock()
        client.models.generate_content.return_value = MagicMock(text="irrelevant")
        mock_get_client.return_value = client

        result = narrate_sections([Section(title=None, body="Plain prose, no math at all.")])
        self.assertEqual(result[0].title, "")
