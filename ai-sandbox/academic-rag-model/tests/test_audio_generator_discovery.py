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
            _touch(os.path.join(hub, "academic_notes", "math-camp", "lecture_notes", "real-analysis.md"))
            sources = discover_source_files(hub, "math-camp", ["notes"])
            self.assertEqual(len(sources), 1)
            self.assertEqual(sources[0].content_type, "notes")
            self.assertEqual(sources[0].rel_md_path, "academic_notes/math-camp/lecture_notes/real-analysis.md")

    def test_notes_mp3_path_mirrors_into_academic_resources(self):
        # 2026-09-22: audio is heavy derived content -- it belongs in
        # academic_resources/ (mirrored path, same convention as
        # common/academic_hub_paths.py), not academic_notes/, which stays
        # lightweight for git/tablet sync. Only the .mp3 moves; the source
        # .md and its .narrated.md/__index.md siblings stay in
        # academic_notes/ untouched (see test_audio_generator_pipeline.py).
        with tempfile.TemporaryDirectory() as hub:
            _touch(os.path.join(hub, "academic_notes", "math-camp", "lecture_notes", "real-analysis.md"))
            sources = discover_source_files(hub, "math-camp", ["notes"])
            self.assertEqual(len(sources), 1)
            self.assertEqual(sources[0].rel_mp3_path, "academic_resources/math-camp/lecture_notes/real-analysis.mp3")

    def test_notes_mp3_path_mirrors_a_nested_processed_outputs_path(self):
        with tempfile.TemporaryDirectory() as hub:
            _touch(os.path.join(hub, "academic_notes", "math-camp", "ta_notes", "processed_outputs", "Aug 17 Analysis.md"))
            sources = discover_source_files(hub, "math-camp", ["notes"])
            self.assertEqual(len(sources), 1)
            self.assertEqual(
                sources[0].rel_mp3_path,
                "academic_resources/math-camp/ta_notes/processed_outputs/Aug 17 Analysis.mp3",
            )

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

    def test_excludes_the_narrated_md_sibling(self):
        with tempfile.TemporaryDirectory() as hub:
            _touch(os.path.join(hub, "academic_notes", "math-camp", "lecture_notes", "real-analysis.md"))
            _touch(os.path.join(hub, "academic_notes", "math-camp", "lecture_notes", "real-analysis.narrated.md"))
            sources = discover_source_files(hub, "math-camp", ["notes"])
            self.assertEqual(len(sources), 1)
            self.assertTrue(sources[0].rel_md_path.endswith("real-analysis.md"))
            self.assertFalse(sources[0].rel_md_path.endswith(".narrated.md"))

    def test_excludes_the_per_episode_narrated_md_sibling(self):
        with tempfile.TemporaryDirectory() as hub:
            _touch(os.path.join(hub, "academic_notes", "math-camp", "lecture_notes", "real-analysis.md"))
            _touch(os.path.join(hub, "academic_notes", "math-camp", "lecture_notes", "real-analysis__part01.narrated.md"))
            sources = discover_source_files(hub, "math-camp", ["notes"])
            self.assertEqual(len(sources), 1)
            self.assertTrue(sources[0].rel_md_path.endswith("real-analysis.md"))

    def test_excludes_the_episode_index_manifest(self):
        with tempfile.TemporaryDirectory() as hub:
            _touch(os.path.join(hub, "academic_notes", "math-camp", "lecture_notes", "real-analysis.md"))
            _touch(os.path.join(hub, "academic_notes", "math-camp", "lecture_notes", "real-analysis__index.md"))
            sources = discover_source_files(hub, "math-camp", ["notes"])
            self.assertEqual(len(sources), 1)
            self.assertTrue(sources[0].rel_md_path.endswith("real-analysis.md"))

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

    def test_textbook_mp3_path_stays_a_sibling_not_mirrored(self):
        # A textbook's .md already lives in academic_resources/ (never
        # academic_notes/) -- sibling is already the right place, nothing
        # to mirror. to_resources_root() would raise on a path with no
        # academic_notes/ segment, so this must not be called for textbooks.
        with tempfile.TemporaryDirectory() as hub:
            book_dir = os.path.join(hub, "academic_resources", "math-camp", "textbooks", "processed_outputs", "Axler_2026")
            _touch(os.path.join(book_dir, "Axler_2026.md"))
            sources = discover_source_files(hub, "math-camp", ["textbook"])
            self.assertEqual(len(sources), 1)
            self.assertEqual(
                sources[0].rel_mp3_path,
                "academic_resources/math-camp/textbooks/processed_outputs/Axler_2026/Axler_2026.mp3",
            )

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
            _touch(os.path.join(hub, "academic_notes", "math-camp", "lecture_notes", "a.md"))
            book_dir = os.path.join(hub, "academic_resources", "math-camp", "textbooks", "processed_outputs", "B")
            _touch(os.path.join(book_dir, "B.md"))
            sources = discover_source_files(hub, "math-camp", ["notes", "textbook"])
            self.assertEqual({s.content_type for s in sources}, {"notes", "textbook"})

    def test_rejects_unknown_content_type(self):
        with tempfile.TemporaryDirectory() as hub:
            with self.assertRaises(ValueError):
                discover_source_files(hub, "math-camp", ["journal-article"])
