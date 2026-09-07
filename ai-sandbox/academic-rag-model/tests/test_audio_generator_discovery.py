import os
import tempfile
import unittest

from audio_generator.discovery import discover_source_files


def _touch(path: str, content: str = "content") -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


class TestDiscoverNotes(unittest.TestCase):
    def test_finds_md_directly_in_a_category(self):
        with tempfile.TemporaryDirectory() as hub:
            _touch(os.path.join(hub, "academic_notes", "math-camp", "lecture-notes", "real-analysis.md"))
            sources = discover_source_files(hub, "math-camp", ["notes"])
            self.assertEqual(len(sources), 1)
            self.assertEqual(sources[0].content_type, "notes")
            self.assertEqual(sources[0].rel_md_path, "academic_notes/math-camp/lecture-notes/real-analysis.md")
            self.assertEqual(sources[0].rel_mp3_path, "academic_notes/math-camp/lecture-notes/real-analysis.mp3")

    def test_finds_md_in_a_category_processed_outputs_subfolder(self):
        with tempfile.TemporaryDirectory() as hub:
            _touch(os.path.join(hub, "academic_notes", "math-camp", "ta_notes", "processed_outputs", "Aug 17 Analysis.md"))
            _touch(os.path.join(hub, "academic_notes", "math-camp", "ta_notes", "LN1-Analysis.pdf"))
            sources = discover_source_files(hub, "math-camp", ["notes"])
            self.assertEqual(len(sources), 1)
            self.assertTrue(sources[0].rel_md_path.endswith("Aug 17 Analysis.md"))

    def test_ignores_non_md_sidecar_files(self):
        with tempfile.TemporaryDirectory() as hub:
            base = os.path.join(hub, "academic_notes", "math-camp", "handwritten_notes", "processed_outputs")
            _touch(os.path.join(base, "Aug 17 Analysis.md"))
            _touch(os.path.join(base, "Aug 17 Analysis_pages_cache.json"))
            sources = discover_source_files(hub, "math-camp", ["notes"])
            self.assertEqual(len(sources), 1)

    def test_missing_course_returns_empty_list(self):
        with tempfile.TemporaryDirectory() as hub:
            self.assertEqual(discover_source_files(hub, "nonexistent-course", ["notes"]), [])


class TestDiscoverTextbooks(unittest.TestCase):
    def test_finds_book_md_matching_its_own_folder_name(self):
        with tempfile.TemporaryDirectory() as hub:
            book_dir = os.path.join(hub, "academic_resources", "math-camp", "textbooks", "processed_outputs", "Axler_2026")
            _touch(os.path.join(book_dir, "Axler_2026.md"))
            _touch(os.path.join(book_dir, "Axler_2026_metadata.json"))
            sources = discover_source_files(hub, "math-camp", ["textbook"])
            self.assertEqual(len(sources), 1)
            self.assertEqual(sources[0].content_type, "textbook")

    def test_excludes_the_rag_md_variant(self):
        with tempfile.TemporaryDirectory() as hub:
            book_dir = os.path.join(hub, "academic_resources", "math-camp", "textbooks", "processed_outputs", "Axler_2026")
            _touch(os.path.join(book_dir, "Axler_2026.md"))
            _touch(os.path.join(book_dir, "Axler_2026.rag.md"))
            sources = discover_source_files(hub, "math-camp", ["textbook"])
            self.assertEqual(len(sources), 1)
            self.assertTrue(sources[0].abs_md_path.endswith("Axler_2026.md"))
            self.assertFalse(sources[0].abs_md_path.endswith(".rag.md"))

    def test_recognizes_both_textbook_folder_aliases(self):
        with tempfile.TemporaryDirectory() as hub:
            book_dir = os.path.join(
                hub, "academic_resources", "econometrics", "textbooks-and-papers", "processed_outputs", "Wooldridge_2020",
            )
            _touch(os.path.join(book_dir, "Wooldridge_2020.md"))
            sources = discover_source_files(hub, "econometrics", ["textbook"])
            self.assertEqual(len(sources), 1)


class TestDiscoverSourceFilesContentTypeFilter(unittest.TestCase):
    def test_defaults_can_combine_both_types(self):
        with tempfile.TemporaryDirectory() as hub:
            _touch(os.path.join(hub, "academic_notes", "math-camp", "lecture-notes", "a.md"))
            book_dir = os.path.join(hub, "academic_resources", "math-camp", "textbooks", "processed_outputs", "B")
            _touch(os.path.join(book_dir, "B.md"))
            sources = discover_source_files(hub, "math-camp", ["notes", "textbook"])
            self.assertEqual({s.content_type for s in sources}, {"notes", "textbook"})

    def test_rejects_unknown_content_type(self):
        with tempfile.TemporaryDirectory() as hub:
            with self.assertRaises(ValueError):
                discover_source_files(hub, "math-camp", ["journal-article"])
