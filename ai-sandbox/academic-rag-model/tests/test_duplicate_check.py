import os
import sys
import tempfile
import unittest
from io import StringIO

from indexer.duplicate_check import (
    normalize_title,
    parse_author_year_from_folder_name,
    score_candidate,
    SURFACE_THRESHOLD,
    find_exact_duplicate,
    find_fuzzy_candidates,
)
from indexer.index_card import save_shard


class TestNormalizeTitle(unittest.TestCase):
    def test_lowercases_and_strips_punctuation(self):
        self.assertEqual(normalize_title("Microeconomic Theory!"), "microeconomic theory")

    def test_collapses_whitespace(self):
        self.assertEqual(normalize_title("  Real   Analysis  "), "real analysis")

    def test_empty_input(self):
        self.assertEqual(normalize_title(""), "")
        self.assertEqual(normalize_title(None), "")


class TestParseAuthorYearFromFolderName(unittest.TestCase):
    def test_typical_folder_name(self):
        author, year = parse_author_year_from_folder_name("Ok_RealAnalysisWithEconomicApplications_2007")
        self.assertEqual(author, "Ok")
        self.assertEqual(year, "2007")

    def test_single_token_folder_name_has_no_year(self):
        author, year = parse_author_year_from_folder_name("converted_textbook")
        self.assertEqual(author, "converted")
        self.assertEqual(year, "")


class TestScoreCandidate(unittest.TestCase):
    def test_identical_title_author_year_scores_at_or_near_one(self):
        incoming = {"title": "Real Analysis with Economic Applications", "author": "Ok", "year": "2007"}
        result = score_candidate(incoming, "Real Analysis with Economic Applications", "Ok", "2007")
        self.assertGreaterEqual(result["combined"], 0.95)

    def test_similar_but_different_books_surface_above_threshold(self):
        # Real risk case (spec Testing section): Mas-Colell's "Microeconomic
        # Theory" vs. Rubinstein's "Lecture Notes in Microeconomic Theory"
        # -- different books, but title overlap alone clears the surfacing
        # threshold. This is *expected* -- it's why Tier 2 never auto-skips
        # on score alone (see Task 6's orchestration, which never treats a
        # high score as a "yes" by itself).
        incoming = {"title": "Microeconomic Theory", "author": "Mas-Colell", "year": "1995"}
        result = score_candidate(incoming, "Lecture Notes in Microeconomic Theory", "Rubinstein", "2012")
        self.assertGreaterEqual(result["combined"], SURFACE_THRESHOLD)

    def test_unrelated_titles_score_low(self):
        incoming = {"title": "Real Analysis with Economic Applications", "author": "Ok", "year": "2007"}
        result = score_candidate(incoming, "Introduction to Spanish Grammar", "Garcia", "2015")
        self.assertLess(result["combined"], SURFACE_THRESHOLD)

    def test_year_off_by_one_gets_partial_bonus(self):
        # Title deliberately not a perfect match (score ~0.82, no author
        # bonus since author is omitted) so the combined score has
        # headroom below 1.0 -- otherwise min(1.0, ...) clipping would
        # erase the very year-bonus difference this test checks for
        # (confirmed while writing this plan: a same-title/same-author
        # pairing saturates past 1.0 regardless of year, making every
        # variant compare equal).
        incoming = {"title": "Elements of Microeconomic Analysis", "author": "", "year": "2020"}
        exact_year = score_candidate(incoming, "Foundations of Microeconomic Analysis", "", "2020")
        off_by_one = score_candidate(incoming, "Foundations of Microeconomic Analysis", "", "2021")
        off_by_many = score_candidate(incoming, "Foundations of Microeconomic Analysis", "", "1999")
        self.assertGreater(exact_year["combined"], off_by_one["combined"])
        self.assertGreater(off_by_one["combined"], off_by_many["combined"])


class TestFindExactDuplicate(unittest.TestCase):
    def _write_pdf(self, path: str, content: bytes = b"%PDF-1.4 fake content") -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(content)

    def test_finds_match_in_a_different_course(self):
        with tempfile.TemporaryDirectory() as academic_hub_root:
            from indexer.index_card import compute_file_id

            pdf_path = os.path.join(academic_hub_root, "academic_resources", "microecon", "textbooks", "Ok.pdf")
            self._write_pdf(pdf_path)
            file_id = compute_file_id(pdf_path)

            save_shard(academic_hub_root, "econometrics", [{
                "file_id": file_id, "path": "econometrics/textbooks/processed_outputs/Ok_RealAnalysis_2007/Ok_RealAnalysis_2007.md",
                "source_pdf_path": "academic_resources/econometrics/textbooks/Ok.pdf", "course": "econometrics",
                "doc_type": "textbook", "title": "Real Analysis with Economic Applications",
            }])

            result = find_exact_duplicate(academic_hub_root, pdf_path, current_course="microecon")
            self.assertIsNotNone(result)
            course, card = result
            self.assertEqual(course, "econometrics")
            self.assertEqual(card["file_id"], file_id)

    def test_match_in_the_same_course_is_not_a_cross_course_duplicate(self):
        with tempfile.TemporaryDirectory() as academic_hub_root:
            from indexer.index_card import compute_file_id

            pdf_path = os.path.join(academic_hub_root, "academic_resources", "microecon", "textbooks", "Ok.pdf")
            self._write_pdf(pdf_path)
            file_id = compute_file_id(pdf_path)

            save_shard(academic_hub_root, "microecon", [{
                "file_id": file_id, "path": "microecon/textbooks/processed_outputs/Ok_RealAnalysis_2007/Ok_RealAnalysis_2007.md",
                "source_pdf_path": "academic_resources/microecon/textbooks/Ok.pdf", "course": "microecon",
                "doc_type": "textbook", "title": "Real Analysis with Economic Applications",
            }])

            result = find_exact_duplicate(academic_hub_root, pdf_path, current_course="microecon")
            self.assertIsNone(result)

    def test_no_match_anywhere(self):
        with tempfile.TemporaryDirectory() as academic_hub_root:
            pdf_path = os.path.join(academic_hub_root, "academic_resources", "microecon", "textbooks", "New.pdf")
            self._write_pdf(pdf_path, content=b"%PDF-1.4 never seen before")
            result = find_exact_duplicate(academic_hub_root, pdf_path, current_course="microecon")
            self.assertIsNone(result)


class TestFindFuzzyCandidates(unittest.TestCase):
    def _card(self, folder_name, title, doc_type="textbook", course="econometrics"):
        return {
            "file_id": f"fid-{folder_name}", "path": f"{course}/textbooks/processed_outputs/{folder_name}/{folder_name}.md",
            "source_pdf_path": f"academic_resources/{course}/textbooks/x.pdf", "course": course,
            "doc_type": doc_type, "title": title,
        }

    def test_finds_and_ranks_candidates_above_threshold(self):
        with tempfile.TemporaryDirectory() as academic_hub_root:
            save_shard(academic_hub_root, "econometrics", [
                self._card("Ok_RealAnalysisWithEconomicApplications_2007", "Real Analysis with Economic Applications"),
                self._card("Garcia_SpanishGrammar_2015", "Introduction to Spanish Grammar"),
            ])
            incoming = {"title": "Real Analysis with Economic Applications", "author": "Ok", "year": "2007"}

            results = find_fuzzy_candidates(academic_hub_root, incoming, current_course="microecon")

            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["course"], "econometrics")
            self.assertEqual(results[0]["card"]["title"], "Real Analysis with Economic Applications")

    def test_excludes_non_textbook_doc_types(self):
        with tempfile.TemporaryDirectory() as academic_hub_root:
            save_shard(academic_hub_root, "econometrics", [
                self._card("Ok_RealAnalysisWithEconomicApplications_2007", "Real Analysis with Economic Applications", doc_type="problem_set"),
            ])
            incoming = {"title": "Real Analysis with Economic Applications", "author": "Ok", "year": "2007"}
            results = find_fuzzy_candidates(academic_hub_root, incoming, current_course="microecon")
            self.assertEqual(results, [])

    def test_excludes_current_course(self):
        with tempfile.TemporaryDirectory() as academic_hub_root:
            save_shard(academic_hub_root, "microecon", [
                self._card("Ok_RealAnalysisWithEconomicApplications_2007", "Real Analysis with Economic Applications", course="microecon"),
            ])
            incoming = {"title": "Real Analysis with Economic Applications", "author": "Ok", "year": "2007"}
            results = find_fuzzy_candidates(academic_hub_root, incoming, current_course="microecon")
            self.assertEqual(results, [])

    def test_similar_titled_different_book_surfaces_for_confirmation(self):
        # The Mas-Colell/Rubinstein worked example from the spec's Testing
        # section -- must surface (so a human gets asked), which this test
        # confirms; Task 6's orchestration is what ensures it's never
        # auto-skipped.
        with tempfile.TemporaryDirectory() as academic_hub_root:
            save_shard(academic_hub_root, "math-methods", [
                self._card("Rubinstein_LectureNotesInMicroeconomicTheory_2012", "Lecture Notes in Microeconomic Theory", course="math-methods"),
            ])
            incoming = {"title": "Microeconomic Theory", "author": "Mas-Colell", "year": "1995"}
            results = find_fuzzy_candidates(academic_hub_root, incoming, current_course="microecon")
            self.assertEqual(len(results), 1)

    def test_corrupt_shard_logs_warning_and_is_skipped_not_crashed(self):
        with tempfile.TemporaryDirectory() as academic_hub_root:
            index_dir = os.path.join(academic_hub_root, ".index")
            os.makedirs(index_dir, exist_ok=True)
            with open(os.path.join(index_dir, "econometrics.json"), "w", encoding="utf-8") as f:
                f.write("not valid json{{{")
            save_shard(academic_hub_root, "math-methods", [
                self._card("Ok_RealAnalysisWithEconomicApplications_2007", "Real Analysis with Economic Applications", course="math-methods"),
            ])
            incoming = {"title": "Real Analysis with Economic Applications", "author": "Ok", "year": "2007"}

            captured_stderr = StringIO()
            old_stderr = sys.stderr
            sys.stderr = captured_stderr
            try:
                results = find_fuzzy_candidates(academic_hub_root, incoming, current_course="microecon")
            finally:
                sys.stderr = old_stderr

            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["course"], "math-methods")
            self.assertIn("WARNING", captured_stderr.getvalue())


class TestDismissals(unittest.TestCase):
    def test_load_missing_file_returns_empty_list(self):
        from indexer.duplicate_check import load_dismissals
        with tempfile.TemporaryDirectory() as academic_hub_root:
            self.assertEqual(load_dismissals(academic_hub_root), [])

    def test_record_then_is_dismissed_regardless_of_argument_order(self):
        from indexer.duplicate_check import record_dismissal, load_dismissals, is_dismissed
        with tempfile.TemporaryDirectory() as academic_hub_root:
            record_dismissal(academic_hub_root, "id-a", "id-b")
            dismissals = load_dismissals(academic_hub_root)
            self.assertTrue(is_dismissed(dismissals, "id-a", "id-b"))
            self.assertTrue(is_dismissed(dismissals, "id-b", "id-a"))

    def test_unrelated_pair_is_not_dismissed(self):
        from indexer.duplicate_check import record_dismissal, load_dismissals, is_dismissed
        with tempfile.TemporaryDirectory() as academic_hub_root:
            record_dismissal(academic_hub_root, "id-a", "id-b")
            dismissals = load_dismissals(academic_hub_root)
            self.assertFalse(is_dismissed(dismissals, "id-a", "id-c"))

    def test_recording_the_same_pair_twice_does_not_duplicate(self):
        from indexer.duplicate_check import record_dismissal, load_dismissals
        with tempfile.TemporaryDirectory() as academic_hub_root:
            record_dismissal(academic_hub_root, "id-a", "id-b")
            record_dismissal(academic_hub_root, "id-a", "id-b")
            self.assertEqual(len(load_dismissals(academic_hub_root)), 1)

    def test_persists_to_the_expected_path(self):
        from indexer.duplicate_check import record_dismissal
        with tempfile.TemporaryDirectory() as academic_hub_root:
            record_dismissal(academic_hub_root, "id-a", "id-b")
            expected_path = os.path.join(academic_hub_root, ".index", "duplicate_dismissals.json")
            self.assertTrue(os.path.exists(expected_path))


import shutil

from indexer.index_card import compute_id_from_parts, load_courses, load_shard
from indexer.duplicate_check import copy_duplicate_artifacts


class TestCopyDuplicateArtifacts(unittest.TestCase):
    def _make_canonical_book(self, academic_hub_root, course="econometrics", folder_category="textbooks", folder_name="Ok_RealAnalysisWithEconomicApplications_2007"):
        book_dir = os.path.join(academic_hub_root, course, folder_category, "processed_outputs", folder_name)
        os.makedirs(os.path.join(book_dir, "images"), exist_ok=True)
        with open(os.path.join(book_dir, f"{folder_name}.md"), "w", encoding="utf-8") as f:
            f.write("# Real Analysis with Economic Applications\n\nBody text.")
        with open(os.path.join(book_dir, "images", "page_1.png"), "wb") as f:
            f.write(b"fake png bytes")
        with open(os.path.join(book_dir, f"{folder_name}_metadata.json"), "w", encoding="utf-8") as f:
            f.write('{"title": "Real Analysis with Economic Applications"}')

        canonical_card = {
            "file_id": "canonical-fid", "path": f"{course}/{folder_category}/processed_outputs/{folder_name}/{folder_name}.md",
            "source_pdf_path": f"academic_resources/{course}/{folder_category}/Ok.pdf", "course": course,
            "doc_type": "textbook", "title": "Real Analysis with Economic Applications",
            "summary": "A real analysis textbook.", "tags": ["math"], "level": "advanced",
            "has_solutions": False, "page_count": 700, "embedding": [0.1, 0.2], "embedding_model": "gemini-embedding-001:768",
            "content_hash": "abc123", "needs_indexing": False,
        }
        save_shard(academic_hub_root, course, [canonical_card])
        return book_dir, folder_name, canonical_card

    def test_copies_all_artifact_files(self):
        with tempfile.TemporaryDirectory() as academic_hub_root:
            _, folder_name, canonical_card = self._make_canonical_book(academic_hub_root)

            copy_duplicate_artifacts(
                academic_hub_root, "econometrics", canonical_card, "microecon", "textbooks",
                "academic_resources/microecon/textbooks/Ok.pdf",
            )

            new_book_dir = os.path.join(academic_hub_root, "microecon", "textbooks", "processed_outputs", folder_name)
            self.assertTrue(os.path.exists(os.path.join(new_book_dir, f"{folder_name}.md")))
            self.assertTrue(os.path.exists(os.path.join(new_book_dir, "images", "page_1.png")))
            self.assertTrue(os.path.exists(os.path.join(new_book_dir, f"{folder_name}_metadata.json")))

    def test_canonical_files_are_untouched(self):
        with tempfile.TemporaryDirectory() as academic_hub_root:
            book_dir, folder_name, canonical_card = self._make_canonical_book(academic_hub_root)
            before = open(os.path.join(book_dir, f"{folder_name}.md"), encoding="utf-8").read()

            copy_duplicate_artifacts(
                academic_hub_root, "econometrics", canonical_card, "microecon", "textbooks",
                "academic_resources/microecon/textbooks/Ok.pdf",
            )

            after = open(os.path.join(book_dir, f"{folder_name}.md"), encoding="utf-8").read()
            self.assertEqual(before, after)

    def test_new_card_has_a_derived_non_colliding_file_id(self):
        with tempfile.TemporaryDirectory() as academic_hub_root:
            _, folder_name, canonical_card = self._make_canonical_book(academic_hub_root)

            new_card = copy_duplicate_artifacts(
                academic_hub_root, "econometrics", canonical_card, "microecon", "textbooks",
                "academic_resources/microecon/textbooks/Ok.pdf",
            )

            expected_id = compute_id_from_parts([canonical_card["file_id"], "microecon"])
            self.assertEqual(new_card["file_id"], expected_id)
            self.assertNotEqual(new_card["file_id"], canonical_card["file_id"])
            self.assertEqual(new_card["duplicate_of_file_id"], canonical_card["file_id"])
            self.assertEqual(new_card["course"], "microecon")
            self.assertEqual(new_card["source_pdf_path"], "academic_resources/microecon/textbooks/Ok.pdf")
            self.assertEqual(new_card["title"], canonical_card["title"])

    def test_new_card_is_saved_in_the_new_course_shard(self):
        with tempfile.TemporaryDirectory() as academic_hub_root:
            _, folder_name, canonical_card = self._make_canonical_book(academic_hub_root)

            copy_duplicate_artifacts(
                academic_hub_root, "econometrics", canonical_card, "microecon", "textbooks",
                "academic_resources/microecon/textbooks/Ok.pdf",
            )

            new_shard = load_shard(academic_hub_root, "microecon")
            self.assertEqual(len(new_shard), 1)
            self.assertEqual(new_shard[0]["course"], "microecon")

    def test_rerunning_is_idempotent(self):
        with tempfile.TemporaryDirectory() as academic_hub_root:
            _, folder_name, canonical_card = self._make_canonical_book(academic_hub_root)

            copy_duplicate_artifacts(
                academic_hub_root, "econometrics", canonical_card, "microecon", "textbooks",
                "academic_resources/microecon/textbooks/Ok.pdf",
            )
            copy_duplicate_artifacts(
                academic_hub_root, "econometrics", canonical_card, "microecon", "textbooks",
                "academic_resources/microecon/textbooks/Ok.pdf",
            )

            new_shard = load_shard(academic_hub_root, "microecon")
            self.assertEqual(len(new_shard), 1)


if __name__ == "__main__":
    unittest.main()
