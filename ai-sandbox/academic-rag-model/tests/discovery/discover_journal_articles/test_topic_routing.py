import tempfile
import unittest
from pathlib import Path

from discovery.discover_journal_articles.discovery import Topic, Work
from discovery.discover_journal_articles.topic_routing import (
    FolderProposal,
    pdf_filename,
    propose_folder,
    route_to_folder,
    sanitize_topic_name,
)


class TestSanitizeTopicName(unittest.TestCase):
    def test_lowercases_and_hyphenates(self):
        self.assertEqual(sanitize_topic_name("Climate Change"), "climate-change")

    def test_strips_punctuation(self):
        self.assertEqual(sanitize_topic_name("Machine Learning & AI"), "machine-learning-ai")

    def test_falls_back_to_misc_when_empty(self):
        self.assertEqual(sanitize_topic_name(""), "misc")
        self.assertEqual(sanitize_topic_name(None), "misc")


class TestRouteToFolder(unittest.TestCase):
    def test_creates_folder_from_top_concept(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Work(
                openalex_id="W1", doi=None, title="T", authors=[], year=2024, abstract=None,
                concepts=["Climate change", "Economics"],
            )
            folder = route_to_folder(tmp, work)
            self.assertEqual(folder, Path(tmp) / "climate-change")
            self.assertTrue(folder.is_dir())

    def test_falls_back_to_misc_without_concepts(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Work(openalex_id="W1", doi=None, title="T", authors=[], year=2024, abstract=None, concepts=[])
            folder = route_to_folder(tmp, work)
            self.assertEqual(folder, Path(tmp) / "misc")
            self.assertTrue(folder.is_dir())

    def test_reuses_existing_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "climate-change").mkdir()
            work = Work(
                openalex_id="W1", doi=None, title="T", authors=[], year=2024, abstract=None,
                concepts=["Climate change"],
            )
            folder = route_to_folder(tmp, work)
            self.assertEqual(folder, Path(tmp) / "climate-change")


class TestPdfFilename(unittest.TestCase):
    def test_uses_sanitized_doi(self):
        work = Work(openalex_id="W1", doi="10.1/abc", title="T", authors=[], year=2024, abstract=None)
        self.assertEqual(pdf_filename(work), "10-1-abc.pdf")

    def test_falls_back_to_openalex_id_without_doi(self):
        work = Work(openalex_id="W1", doi=None, title="T", authors=[], year=2024, abstract=None)
        self.assertEqual(pdf_filename(work), "w1.pdf")


class TestProposeFolder(unittest.TestCase):
    def test_ranks_candidates_by_score_not_breadth(self):
        # The exact bug this replaces: Concepts-based routing picked the
        # broadest label regardless of score. Topics-based proposing
        # ranks purely by relevance score.
        topics = [
            Topic(id="T1", display_name="Business", score=0.391096),
            Topic(id="T2", display_name="Soil Carbon and Nitrogen Dynamics", score=0.9),
        ]

        proposal = propose_folder(topics, current_folder="business")

        self.assertEqual(proposal.current_folder, "business")
        self.assertEqual(proposal.candidates[0], ("soil-carbon-and-nitrogen-dynamics", 0.9))
        self.assertEqual(proposal.candidates[1], ("business", 0.391096))

    def test_two_topics_sanitizing_to_the_same_folder_name_keep_only_the_higher_scored_one(self):
        topics = [
            Topic(id="T1", display_name="Climate Change", score=0.6),
            Topic(id="T2", display_name="Climate-Change!", score=0.9),
        ]

        proposal = propose_folder(topics, current_folder="misc")

        self.assertEqual(proposal.candidates, [("climate-change", 0.9)])

    def test_empty_topics_yields_no_candidates(self):
        proposal = propose_folder([], current_folder="misc")
        self.assertEqual(proposal.candidates, [])


if __name__ == "__main__":
    unittest.main()
