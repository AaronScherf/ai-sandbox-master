import unittest

from audio_generator.sections import (
    Episode,
    NarratedSection,
    Section,
    group_sections_into_episodes,
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
