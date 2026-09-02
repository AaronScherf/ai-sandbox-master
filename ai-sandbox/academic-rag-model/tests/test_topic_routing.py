import tempfile
import unittest
from pathlib import Path

from journal_discovery.discovery import Work
from journal_discovery.topic_routing import pdf_filename, route_to_folder, sanitize_topic_name


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


if __name__ == "__main__":
    unittest.main()
