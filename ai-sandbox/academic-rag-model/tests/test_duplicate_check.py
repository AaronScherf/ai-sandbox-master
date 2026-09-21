import json
import os
import sys
import tempfile
import unittest
from io import StringIO
from unittest import mock

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
                "file_id": file_id, "path": "academic_resources/econometrics/textbooks/processed_outputs/Ok_RealAnalysis_2007/Ok_RealAnalysis_2007.md",
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
                "file_id": file_id, "path": "academic_resources/microecon/textbooks/processed_outputs/Ok_RealAnalysis_2007/Ok_RealAnalysis_2007.md",
                "source_pdf_path": "academic_resources/microecon/textbooks/Ok.pdf", "course": "microecon",
                "doc_type": "textbook", "title": "Real Analysis with Economic Applications",
            }])

            result = find_exact_duplicate(academic_hub_root, pdf_path, current_course="microecon")
            self.assertIsNone(result)

    def test_same_course_hit_wins_over_an_alphabetically_earlier_other_course(self):
        # Regression (final review, Finding 5): find_card_by_file_id()
        # returns the FIRST match in list_courses()'s *sorted* order, so
        # when the same file_id has cards in both the current course
        # ("microecon") and an alphabetically-earlier one ("econometrics"),
        # the naive lookup reported "econometrics" and cloned the book into
        # a course that already had it. The current course's own shard must
        # be consulted first -- a same-course hit means this is not a
        # cross-course duplicate at all.
        with tempfile.TemporaryDirectory() as academic_hub_root:
            from indexer.index_card import compute_file_id, list_courses

            pdf_path = os.path.join(academic_hub_root, "academic_resources", "microecon", "textbooks", "Ok.pdf")
            self._write_pdf(pdf_path)
            file_id = compute_file_id(pdf_path)

            shared = {
                "file_id": file_id, "doc_type": "textbook",
                "title": "Real Analysis with Economic Applications",
            }
            save_shard(academic_hub_root, "econometrics", [dict(
                shared, course="econometrics",
                path="academic_resources/econometrics/textbooks/processed_outputs/Ok_RealAnalysis_2007/Ok_RealAnalysis_2007.md",
                source_pdf_path="academic_resources/econometrics/textbooks/Ok.pdf",
            )])
            save_shard(academic_hub_root, "microecon", [dict(
                shared, course="microecon",
                path="academic_resources/microecon/textbooks/processed_outputs/Ok_RealAnalysis_2007/Ok_RealAnalysis_2007.md",
                source_pdf_path="academic_resources/microecon/textbooks/Ok.pdf",
            )])

            # Guards the premise: "econometrics" really does sort first, so
            # the unfixed lookup really would have returned it.
            self.assertEqual(list_courses(academic_hub_root), ["econometrics", "microecon"])

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
            "file_id": f"fid-{folder_name}", "path": f"academic_resources/{course}/textbooks/processed_outputs/{folder_name}/{folder_name}.md",
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

    def test_excludes_cards_still_pending_confirmation(self):
        # Real bug found by the final whole-branch review: a clone still
        # awaiting human review must never itself be matched as a
        # candidate by a third course -- otherwise rejecting the original
        # auto-skip leaves a dangling reference nothing can trace.
        with tempfile.TemporaryDirectory() as academic_hub_root:
            pending_clone = self._card("Ok_RealAnalysisWithEconomicApplications_2007", "Real Analysis with Economic Applications", course="microecon")
            pending_clone["duplicate_pending_confirmation"] = True
            save_shard(academic_hub_root, "microecon", [pending_clone])
            incoming = {"title": "Real Analysis with Economic Applications", "author": "Ok", "year": "2007"}
            results = find_fuzzy_candidates(academic_hub_root, incoming, current_course="mathcamp")
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
            expected_path = os.path.join(academic_hub_root, ".index", "duplicates", "dismissals.json")
            self.assertTrue(os.path.exists(expected_path))


import shutil

from indexer.index_card import compute_id_from_parts, load_courses, load_shard
from indexer.duplicate_check import copy_duplicate_artifacts


class TestCopyDuplicateArtifacts(unittest.TestCase):
    def _make_canonical_book(self, academic_hub_root, course="econometrics", folder_category="textbooks", folder_name="Ok_RealAnalysisWithEconomicApplications_2007"):
        book_dir = os.path.join(academic_hub_root, "academic_resources", course, folder_category, "processed_outputs", folder_name)
        os.makedirs(os.path.join(book_dir, "images"), exist_ok=True)
        with open(os.path.join(book_dir, f"{folder_name}.md"), "w", encoding="utf-8") as f:
            f.write("# Real Analysis with Economic Applications\n\nBody text.")
        with open(os.path.join(book_dir, "images", "page_1.png"), "wb") as f:
            f.write(b"fake png bytes")
        # Shaped like a real one: convert_textbook.py always records
        # source_pdf_path/source_pdf_file_id, and index_search.py's rebuild
        # backfill recomputes a book folder's identity from exactly those
        # two fields.
        with open(os.path.join(book_dir, f"{folder_name}_metadata.json"), "w", encoding="utf-8") as f:
            json.dump({
                "title": "Real Analysis with Economic Applications",
                "source_pdf_path": f"academic_resources/{course}/{folder_category}/Ok.pdf",
                "source_pdf_filename": "Ok.pdf",
                "source_pdf_file_id": "canonical-fid",
                "total_pages_processed": 700,
            }, f, indent=4)

        canonical_card = {
            "file_id": "canonical-fid", "path": f"academic_resources/{course}/{folder_category}/processed_outputs/{folder_name}/{folder_name}.md",
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

            new_book_dir = os.path.join(academic_hub_root, "academic_resources", "microecon", "textbooks", "processed_outputs", folder_name)
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

    def test_pending_confirmation_flag_marks_the_new_card(self):
        with tempfile.TemporaryDirectory() as academic_hub_root:
            _, folder_name, canonical_card = self._make_canonical_book(academic_hub_root)

            new_card = copy_duplicate_artifacts(
                academic_hub_root, "econometrics", canonical_card, "microecon", "textbooks",
                "academic_resources/microecon/textbooks/Ok.pdf",
                pending_confirmation=True,
            )

            self.assertTrue(new_card["duplicate_pending_confirmation"])
            saved_card = load_shard(academic_hub_root, "microecon")[0]
            self.assertTrue(saved_card["duplicate_pending_confirmation"])

    def test_pending_confirmation_flag_defaults_to_absent_not_false(self):
        with tempfile.TemporaryDirectory() as academic_hub_root:
            _, folder_name, canonical_card = self._make_canonical_book(academic_hub_root)

            new_card = copy_duplicate_artifacts(
                academic_hub_root, "econometrics", canonical_card, "microecon", "textbooks",
                "academic_resources/microecon/textbooks/Ok.pdf",
            )

            self.assertNotIn("duplicate_pending_confirmation", new_card)

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

    def test_new_card_path_and_directory_keep_the_academic_resources_prefix(self):
        # Regression (final review, Finding 1): the destination used to be
        # rebuilt as "<new_course>/<category>/processed_outputs/...", which
        # silently dropped the leading "academic_resources/" segment that
        # every real card carries (verified against a live shard) and that
        # index_search.py's _textbook_book_dirs requires -- so the clone
        # landed somewhere nothing in the pipeline ever looks.
        with tempfile.TemporaryDirectory() as academic_hub_root:
            _, folder_name, canonical_card = self._make_canonical_book(academic_hub_root)

            new_card = copy_duplicate_artifacts(
                academic_hub_root, "econometrics", canonical_card, "microecon", "textbooks",
                "academic_resources/microecon/textbooks/Ok.pdf",
            )

            self.assertEqual(
                new_card["path"],
                f"academic_resources/microecon/textbooks/processed_outputs/{folder_name}/{folder_name}.md",
            )
            # The card's `path` must resolve to the file that was actually
            # written, and the un-prefixed location must not exist at all.
            self.assertTrue(os.path.exists(os.path.join(academic_hub_root, *new_card["path"].split("/"))))
            self.assertFalse(os.path.exists(os.path.join(academic_hub_root, "microecon")))

    def test_copied_metadata_is_repointed_at_the_new_courses_pdf(self):
        # Regression (final review, Finding 6): the copied _metadata.json
        # still named the CANONICAL course's PDF, so an index_search.py
        # `rebuild` over the new course would recompute the canonical
        # file_id from this clone and rewrite the canonical card's own
        # `path` to point here -- breaking spec 5's "canonical is never
        # modified" guarantee from the outside.
        with tempfile.TemporaryDirectory() as academic_hub_root:
            book_dir, folder_name, canonical_card = self._make_canonical_book(academic_hub_root)

            new_card = copy_duplicate_artifacts(
                academic_hub_root, "econometrics", canonical_card, "microecon", "textbooks",
                "academic_resources/microecon/textbooks/Ok.pdf",
            )

            copied_metadata_path = os.path.join(
                academic_hub_root, "academic_resources", "microecon", "textbooks",
                "processed_outputs", folder_name, f"{folder_name}_metadata.json",
            )
            with open(copied_metadata_path, encoding="utf-8") as f:
                copied = json.load(f)
            self.assertEqual(copied["source_pdf_path"], "academic_resources/microecon/textbooks/Ok.pdf")
            self.assertEqual(copied["source_pdf_file_id"], new_card["file_id"])
            # Unrelated fields survive the rewrite untouched.
            self.assertEqual(copied["title"], "Real Analysis with Economic Applications")
            self.assertEqual(copied["total_pages_processed"], 700)

            # And the canonical book's own metadata is still canonical.
            with open(os.path.join(book_dir, f"{folder_name}_metadata.json"), encoding="utf-8") as f:
                original = json.load(f)
            self.assertEqual(original["source_pdf_path"], "academic_resources/econometrics/textbooks/Ok.pdf")
            self.assertEqual(original["source_pdf_file_id"], "canonical-fid")

    def test_copied_metadata_gets_a_duplicate_of_file_id_marker(self):
        # New behavior (pipeline-autonomy-policies spec, Component 3):
        # index_search.py's rebuild() needs to recognize a clone directory
        # from its on-disk _metadata.json alone -- it never reads the
        # index card while walking book directories on disk. This marker
        # is what lets rebuild() skip re-hashing a clone instead of
        # colliding with the canonical book's own file_id.
        with tempfile.TemporaryDirectory() as academic_hub_root:
            _, folder_name, canonical_card = self._make_canonical_book(academic_hub_root)

            copy_duplicate_artifacts(
                academic_hub_root, "econometrics", canonical_card, "microecon", "textbooks",
                "academic_resources/microecon/textbooks/Ok.pdf",
            )

            copied_metadata_path = os.path.join(
                academic_hub_root, "academic_resources", "microecon", "textbooks",
                "processed_outputs", folder_name, f"{folder_name}_metadata.json",
            )
            with open(copied_metadata_path, encoding="utf-8") as f:
                copied = json.load(f)
            self.assertEqual(copied["duplicate_of_file_id"], "canonical-fid")

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


from indexer.duplicate_check import run_duplicate_check
from indexer.duplicate_check import build_arg_parser


class TestRunDuplicateCheck(unittest.TestCase):
    def _write_pdf(self, path, content):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(content)

    def test_no_candidates_converts_everything(self):
        with tempfile.TemporaryDirectory() as academic_hub_root:
            subdir = "academic_resources/microecon/textbooks"
            self._write_pdf(os.path.join(academic_hub_root, subdir, "New_Book_2020.pdf"), b"brand new content")

            result = run_duplicate_check(subdir, academic_hub_root, non_interactive=True, resolutions={})

            self.assertEqual(result["to_convert"], ["New_Book_2020.pdf"])
            self.assertEqual(result["skipped"], [])

    def test_exact_duplicate_is_skipped_and_copied_without_any_prompt(self):
        with tempfile.TemporaryDirectory() as academic_hub_root:
            subdir = "academic_resources/microecon/textbooks"
            pdf_path = os.path.join(academic_hub_root, subdir, "Ok.pdf")
            self._write_pdf(pdf_path, b"%PDF-1.4 identical bytes")
            from indexer.index_card import compute_file_id
            file_id = compute_file_id(pdf_path)

            book_dir = os.path.join(academic_hub_root, "academic_resources", "econometrics", "textbooks", "processed_outputs", "Ok_RealAnalysis_2007")
            os.makedirs(book_dir, exist_ok=True)
            with open(os.path.join(book_dir, "Ok_RealAnalysis_2007.md"), "w", encoding="utf-8") as f:
                f.write("# Real Analysis")
            save_shard(academic_hub_root, "econometrics", [{
                "file_id": file_id, "path": "academic_resources/econometrics/textbooks/processed_outputs/Ok_RealAnalysis_2007/Ok_RealAnalysis_2007.md",
                "source_pdf_path": "academic_resources/econometrics/textbooks/Ok.pdf", "course": "econometrics",
                "doc_type": "textbook", "title": "Real Analysis with Economic Applications",
            }])

            result = run_duplicate_check(subdir, academic_hub_root, non_interactive=True, resolutions={})

            self.assertEqual(result["to_convert"], [])
            self.assertEqual(len(result["skipped"]), 1)
            self.assertEqual(result["skipped"][0][0], "Ok.pdf")
            new_book_dir = os.path.join(academic_hub_root, "academic_resources", "microecon", "textbooks", "processed_outputs", "Ok_RealAnalysis_2007")
            self.assertTrue(os.path.exists(os.path.join(new_book_dir, "Ok_RealAnalysis_2007.md")))

    def test_non_interactive_fuzzy_match_is_left_unresolved_and_kept_in_to_convert(self):
        # Uses the Mas-Colell/Rubinstein ambiguous band (score >= SURFACE_
        # THRESHOLD but below AUTO_SKIP_THRESHOLD) deliberately -- this
        # test's whole point is the "surfaced but not auto-resolved" path,
        # which the two-tier policy (pipeline-autonomy-policies spec,
        # Component 1a) now reserves for exactly this confidence band. A
        # near-identical title (like the old "Ok_RealAnalysis..." fixture)
        # would now score high enough to auto-skip before ever reaching
        # here -- see Task 3's Global Constraints note.
        with tempfile.TemporaryDirectory() as academic_hub_root:
            subdir = "academic_resources/microecon/textbooks"
            self._write_pdf(os.path.join(academic_hub_root, subdir, "Microeconomic Theory -- Mas-Colell.pdf"), b"a different but similarly-titled book")

            book_dir = os.path.join(academic_hub_root, "academic_resources", "math-methods", "textbooks", "processed_outputs", "Rubinstein_LectureNotesInMicroeconomicTheory_2012")
            os.makedirs(book_dir, exist_ok=True)
            with open(os.path.join(book_dir, "Rubinstein_LectureNotesInMicroeconomicTheory_2012.md"), "w", encoding="utf-8") as f:
                f.write("# Lecture Notes in Microeconomic Theory")
            save_shard(academic_hub_root, "math-methods", [{
                "file_id": "rubinstein-fid", "path": "academic_resources/math-methods/textbooks/processed_outputs/Rubinstein_LectureNotesInMicroeconomicTheory_2012/Rubinstein_LectureNotesInMicroeconomicTheory_2012.md",
                "source_pdf_path": "academic_resources/math-methods/textbooks/x.pdf", "course": "math-methods",
                "doc_type": "textbook", "title": "Lecture Notes in Microeconomic Theory",
            }])

            result = run_duplicate_check(subdir, academic_hub_root, non_interactive=True, resolutions={})

            self.assertEqual(result["to_convert"], ["Microeconomic Theory -- Mas-Colell.pdf"])
            self.assertEqual(len(result["unresolved"]), 1)
            self.assertEqual(result["auto_skipped_pending_confirmation"], [])

    def test_resolve_yes_skips_and_copies(self):
        with tempfile.TemporaryDirectory() as academic_hub_root:
            subdir = "academic_resources/microecon/textbooks"
            pdf_path = os.path.join(academic_hub_root, subdir, "Ok_RealAnalysisWithEconomicApplications_2007.pdf")
            self._write_pdf(pdf_path, b"a re-scanned copy, different bytes")
            from indexer.index_card import compute_file_id
            incoming_file_id = compute_file_id(pdf_path)

            book_dir = os.path.join(academic_hub_root, "academic_resources", "econometrics", "textbooks", "processed_outputs", "Ok_RealAnalysisWithEconomicApplications_2007")
            os.makedirs(book_dir, exist_ok=True)
            with open(os.path.join(book_dir, "Ok_RealAnalysisWithEconomicApplications_2007.md"), "w", encoding="utf-8") as f:
                f.write("# Real Analysis")
            save_shard(academic_hub_root, "econometrics", [{
                "file_id": "some-other-fid", "path": "academic_resources/econometrics/textbooks/processed_outputs/Ok_RealAnalysisWithEconomicApplications_2007/Ok_RealAnalysisWithEconomicApplications_2007.md",
                "source_pdf_path": "academic_resources/econometrics/textbooks/Ok.pdf", "course": "econometrics",
                "doc_type": "textbook", "title": "Real Analysis with Economic Applications",
            }])

            result = run_duplicate_check(
                subdir, academic_hub_root, non_interactive=True,
                resolutions={incoming_file_id: "yes"},
            )

            self.assertEqual(result["to_convert"], [])
            self.assertEqual(len(result["skipped"]), 1)

    def test_resolve_no_dismisses_and_keeps_in_to_convert_without_reprompting(self):
        with tempfile.TemporaryDirectory() as academic_hub_root:
            subdir = "academic_resources/microecon/textbooks"
            pdf_path = os.path.join(academic_hub_root, subdir, "Ok_RealAnalysisWithEconomicApplications_2007.pdf")
            self._write_pdf(pdf_path, b"a re-scanned copy, different bytes")
            from indexer.index_card import compute_file_id
            incoming_file_id = compute_file_id(pdf_path)

            book_dir = os.path.join(academic_hub_root, "academic_resources", "econometrics", "textbooks", "processed_outputs", "Ok_RealAnalysisWithEconomicApplications_2007")
            os.makedirs(book_dir, exist_ok=True)
            with open(os.path.join(book_dir, "Ok_RealAnalysisWithEconomicApplications_2007.md"), "w", encoding="utf-8") as f:
                f.write("# Real Analysis")
            save_shard(academic_hub_root, "econometrics", [{
                "file_id": "some-other-fid", "path": "academic_resources/econometrics/textbooks/processed_outputs/Ok_RealAnalysisWithEconomicApplications_2007/Ok_RealAnalysisWithEconomicApplications_2007.md",
                "source_pdf_path": "academic_resources/econometrics/textbooks/Ok.pdf", "course": "econometrics",
                "doc_type": "textbook", "title": "Real Analysis with Economic Applications",
            }])

            result = run_duplicate_check(
                subdir, academic_hub_root, non_interactive=True,
                resolutions={incoming_file_id: "no"},
            )
            self.assertEqual(result["to_convert"], ["Ok_RealAnalysisWithEconomicApplications_2007.pdf"])

            # Second run: same pair, no resolution given -- must not be
            # surfaced as unresolved again (spec §4).
            result_2 = run_duplicate_check(subdir, academic_hub_root, non_interactive=True, resolutions={})
            self.assertEqual(result_2["to_convert"], ["Ok_RealAnalysisWithEconomicApplications_2007.pdf"])
            self.assertEqual(result_2["unresolved"], [])

    def test_interactive_mode_uses_prompt_fn(self):
        # Same ambiguous-band fixture as the test above -- a near-perfect
        # match would now be auto-skipped before ever calling prompt_fn.
        with tempfile.TemporaryDirectory() as academic_hub_root:
            subdir = "academic_resources/microecon/textbooks"
            pdf_path = os.path.join(academic_hub_root, subdir, "Microeconomic Theory -- Mas-Colell.pdf")
            self._write_pdf(pdf_path, b"a different but similarly-titled book")

            book_dir = os.path.join(academic_hub_root, "academic_resources", "math-methods", "textbooks", "processed_outputs", "Rubinstein_LectureNotesInMicroeconomicTheory_2012")
            os.makedirs(book_dir, exist_ok=True)
            with open(os.path.join(book_dir, "Rubinstein_LectureNotesInMicroeconomicTheory_2012.md"), "w", encoding="utf-8") as f:
                f.write("# Lecture Notes in Microeconomic Theory")
            save_shard(academic_hub_root, "math-methods", [{
                "file_id": "rubinstein-fid", "path": "academic_resources/math-methods/textbooks/processed_outputs/Rubinstein_LectureNotesInMicroeconomicTheory_2012/Rubinstein_LectureNotesInMicroeconomicTheory_2012.md",
                "source_pdf_path": "academic_resources/math-methods/textbooks/x.pdf", "course": "math-methods",
                "doc_type": "textbook", "title": "Lecture Notes in Microeconomic Theory",
            }])

            prompt_calls = []

            def _record_and_confirm(pdf_filename, candidate):
                prompt_calls.append(pdf_filename)
                return "yes"

            result = run_duplicate_check(
                subdir, academic_hub_root, non_interactive=False, resolutions={},
                prompt_fn=_record_and_confirm,
            )
            self.assertEqual(len(result["skipped"]), 1)
            self.assertEqual(prompt_calls, ["Microeconomic Theory -- Mas-Colell.pdf"])

    def test_high_confidence_match_is_auto_skipped_without_any_prompt_or_resolution(self):
        with tempfile.TemporaryDirectory() as academic_hub_root:
            subdir = "academic_resources/microecon/textbooks"
            # This exact fixture already scores 1.0 via the real filename-
            # parsing pipeline (title/author/year all match) -- see Task
            # 3's Global Constraints note.
            pdf_path = os.path.join(academic_hub_root, subdir, "Ok_RealAnalysisWithEconomicApplications_2007.pdf")
            self._write_pdf(pdf_path, b"a re-scanned copy, different bytes")

            book_dir = os.path.join(academic_hub_root, "academic_resources", "econometrics", "textbooks", "processed_outputs", "Ok_RealAnalysisWithEconomicApplications_2007")
            os.makedirs(book_dir, exist_ok=True)
            with open(os.path.join(book_dir, "Ok_RealAnalysisWithEconomicApplications_2007.md"), "w", encoding="utf-8") as f:
                f.write("# Real Analysis")
            save_shard(academic_hub_root, "econometrics", [{
                "file_id": "some-other-fid", "path": "academic_resources/econometrics/textbooks/processed_outputs/Ok_RealAnalysisWithEconomicApplications_2007/Ok_RealAnalysisWithEconomicApplications_2007.md",
                "source_pdf_path": "academic_resources/econometrics/textbooks/Ok.pdf", "course": "econometrics",
                "doc_type": "textbook", "title": "Real Analysis with Economic Applications",
            }])

            def _fail_if_called(pdf_filename, candidate):
                self.fail("prompt_fn must not be called for a high-confidence auto-skip")

            result = run_duplicate_check(
                subdir, academic_hub_root, non_interactive=False, resolutions={},
                prompt_fn=_fail_if_called,
            )

            self.assertEqual(result["to_convert"], [])
            self.assertEqual(len(result["skipped"]), 1)
            self.assertEqual(len(result["auto_skipped_pending_confirmation"]), 1)
            pending = result["auto_skipped_pending_confirmation"][0]
            self.assertEqual(pending["pdf_filename"], "Ok_RealAnalysisWithEconomicApplications_2007.pdf")
            self.assertEqual(pending["matched_course"], "econometrics")
            self.assertGreaterEqual(pending["score"], 0.85)

            new_book_dir = os.path.join(academic_hub_root, "academic_resources", "microecon", "textbooks", "processed_outputs", "Ok_RealAnalysisWithEconomicApplications_2007")
            self.assertTrue(os.path.exists(os.path.join(new_book_dir, "Ok_RealAnalysisWithEconomicApplications_2007.md")))

            new_card = load_shard(academic_hub_root, "microecon")[0]
            self.assertTrue(new_card["duplicate_pending_confirmation"])

    def test_explicit_resolve_decision_wins_over_the_auto_skip_threshold(self):
        # An explicit --resolve decision is a real human/agent decision --
        # it must never be silently overridden by the heuristic, even for
        # a candidate that would otherwise auto-skip. Passing "no" here
        # must dismiss and convert, not auto-skip, despite the score.
        with tempfile.TemporaryDirectory() as academic_hub_root:
            subdir = "academic_resources/microecon/textbooks"
            pdf_path = os.path.join(academic_hub_root, subdir, "Ok_RealAnalysisWithEconomicApplications_2007.pdf")
            self._write_pdf(pdf_path, b"a re-scanned copy, different bytes")
            from indexer.index_card import compute_file_id
            incoming_file_id = compute_file_id(pdf_path)

            book_dir = os.path.join(academic_hub_root, "academic_resources", "econometrics", "textbooks", "processed_outputs", "Ok_RealAnalysisWithEconomicApplications_2007")
            os.makedirs(book_dir, exist_ok=True)
            with open(os.path.join(book_dir, "Ok_RealAnalysisWithEconomicApplications_2007.md"), "w", encoding="utf-8") as f:
                f.write("# Real Analysis")
            save_shard(academic_hub_root, "econometrics", [{
                "file_id": "some-other-fid", "path": "academic_resources/econometrics/textbooks/processed_outputs/Ok_RealAnalysisWithEconomicApplications_2007/Ok_RealAnalysisWithEconomicApplications_2007.md",
                "source_pdf_path": "academic_resources/econometrics/textbooks/Ok.pdf", "course": "econometrics",
                "doc_type": "textbook", "title": "Real Analysis with Economic Applications",
            }])

            result = run_duplicate_check(
                subdir, academic_hub_root, non_interactive=True,
                resolutions={incoming_file_id: "no"},
            )

            self.assertEqual(result["to_convert"], ["Ok_RealAnalysisWithEconomicApplications_2007.pdf"])
            self.assertEqual(result["skipped"], [])
            self.assertEqual(result["auto_skipped_pending_confirmation"], [])


class TestBuildArgParser(unittest.TestCase):
    def test_resolve_can_repeat(self):
        parser = build_arg_parser()
        args = parser.parse_args([
            "--textbook-subdir", "academic_resources/microecon/textbooks",
            "--non-interactive", "--resolve", "aaa=yes", "--resolve", "bbb=no",
        ])
        self.assertEqual(args.resolve, ["aaa=yes", "bbb=no"])

    def test_emit_to_convert_defaults_to_none_and_is_accepted(self):
        parser = build_arg_parser()
        base = ["--textbook-subdir", "academic_resources/microecon/textbooks"]
        self.assertIsNone(parser.parse_args(base).emit_to_convert)
        args = parser.parse_args(base + ["--emit-to-convert", "/tmp/to_convert.txt"])
        self.assertEqual(args.emit_to_convert, "/tmp/to_convert.txt")


class TestEmitToConvert(unittest.TestCase):
    """Regression coverage (final review, Finding 3): both instructions
    documents used to re-derive PDF_FILENAMES by re-globbing
    TEXTBOOK_SUBDIR after the check -- but a confirmed duplicate's source
    PDF is deliberately never deleted, so the re-glob returned the exact
    same list and the 'skipped' book got uploaded and reconverted anyway.
    --emit-to-convert is the mechanism that actually removes it."""

    def _write_pdf(self, path, content):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(content)

    def test_writes_one_filename_per_line_creating_parent_dirs(self):
        from indexer.duplicate_check import write_to_convert_file
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "nested", "to_convert.txt")
            write_to_convert_file(out, ["A_Book_2020.pdf", "B Book, with spaces.pdf"])
            with open(out, encoding="utf-8") as f:
                self.assertEqual(f.read().splitlines(), ["A_Book_2020.pdf", "B Book, with spaces.pdf"])

    def test_empty_to_convert_writes_an_empty_file(self):
        from indexer.duplicate_check import write_to_convert_file
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "to_convert.txt")
            write_to_convert_file(out, [])
            self.assertTrue(os.path.exists(out))
            with open(out, encoding="utf-8") as f:
                self.assertEqual(f.read(), "")

    def test_main_emits_only_the_unskipped_pdf_not_the_whole_folder(self):
        import indexer.duplicate_check as dc
        from indexer.index_card import compute_file_id

        with tempfile.TemporaryDirectory() as academic_hub_root, tempfile.TemporaryDirectory() as tmp:
            subdir = "academic_resources/microecon/textbooks"
            dup_path = os.path.join(academic_hub_root, subdir, "Ok.pdf")
            self._write_pdf(dup_path, b"%PDF-1.4 identical bytes")
            self._write_pdf(os.path.join(academic_hub_root, subdir, "New_Book_2020.pdf"), b"brand new content")
            file_id = compute_file_id(dup_path)

            book_dir = os.path.join(
                academic_hub_root, "academic_resources", "econometrics", "textbooks",
                "processed_outputs", "Ok_RealAnalysis_2007",
            )
            os.makedirs(book_dir, exist_ok=True)
            with open(os.path.join(book_dir, "Ok_RealAnalysis_2007.md"), "w", encoding="utf-8") as f:
                f.write("# Real Analysis")
            save_shard(academic_hub_root, "econometrics", [{
                "file_id": file_id,
                "path": "academic_resources/econometrics/textbooks/processed_outputs/Ok_RealAnalysis_2007/Ok_RealAnalysis_2007.md",
                "source_pdf_path": "academic_resources/econometrics/textbooks/Ok.pdf", "course": "econometrics",
                "doc_type": "textbook", "title": "Real Analysis with Economic Applications",
            }])

            out = os.path.join(tmp, "to_convert.txt")
            argv = [
                "duplicate_check", "--textbook-subdir", subdir,
                "--academic-hub-root", academic_hub_root,
                "--non-interactive", "--emit-to-convert", out,
            ]
            with mock.patch.object(sys, "argv", argv), mock.patch("sys.stdout", new=StringIO()):
                dc.main()

            with open(out, encoding="utf-8") as f:
                emitted = f.read().splitlines()

            # Both PDFs are still on disk (the duplicate's source is never
            # deleted) -- so a re-glob would return both. The emitted list
            # is what makes the skip actually take effect.
            self.assertTrue(os.path.exists(dup_path))
            self.assertEqual(emitted, ["New_Book_2020.pdf"])

    def test_emitted_file_is_lf_only_even_on_windows(self):
        # Confirmed live running this exact file from Windows Git Bash:
        # a plain open(path, "w", encoding="utf-8") lets Python's text-mode
        # write translate every "\n" to "\r\n" on Windows. `mapfile -t`
        # (the shell command both instructions documents use to read this
        # file back) only strips the trailing "\n", leaving an invisible
        # "\r" on every filename it reads -- which then breaks every path
        # built from it. Reading with plain open()/encoding="utf-8" (no
        # explicit newline=) would silently normalize "\r\n" back to "\n"
        # via Python's own universal-newline handling and never catch
        # this -- this test opens the file in binary mode specifically to
        # see the raw bytes mapfile would actually see.
        from indexer.duplicate_check import write_to_convert_file

        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "to_convert.txt")
            write_to_convert_file(out, ["Some Book.pdf", "Another Book.pdf"])

            with open(out, "rb") as f:
                raw = f.read()

            self.assertNotIn(b"\r", raw)
            self.assertEqual(raw, b"Some Book.pdf\nAnother Book.pdf\n")


class TestReviewPending(unittest.TestCase):
    def test_review_pending_lists_entries_across_all_courses(self):
        import indexer.duplicate_check as dc
        with tempfile.TemporaryDirectory() as academic_hub_root:
            dc.record_pending_confirmation(academic_hub_root, {
                "incoming_file_id": "a", "pdf_filename": "Ok.pdf", "course": "microecon",
                "matched_course": "econometrics", "matched_file_id": "canonical-fid",
                "matched_title": "Real Analysis with Economic Applications", "score": 0.91,
                "new_card_file_id": "clone-fid", "queued_at": "2026-09-20T00:00:00+00:00",
            })
            argv = ["duplicate_check", "--review-pending", "--academic-hub-root", academic_hub_root]
            captured = StringIO()
            with mock.patch.object(sys, "argv", argv), mock.patch("sys.stdout", new=captured):
                dc.main()
            output = captured.getvalue()
            self.assertIn("Ok.pdf", output)
            self.assertIn("econometrics", output)
            self.assertIn("Real Analysis with Economic Applications", output)

    def test_review_pending_does_not_require_textbook_subdir(self):
        import indexer.duplicate_check as dc
        with tempfile.TemporaryDirectory() as academic_hub_root:
            argv = ["duplicate_check", "--review-pending", "--academic-hub-root", academic_hub_root]
            with mock.patch.object(sys, "argv", argv), mock.patch("sys.stdout", new=StringIO()):
                dc.main()  # must not raise SystemExit

    def test_normal_run_still_requires_textbook_subdir(self):
        # Replaces the old parser-level test (build_arg_parser() no longer
        # marks --textbook-subdir required=True at the argparse layer,
        # since --review-pending must be usable without it) -- the
        # requirement now lives in main() instead.
        import indexer.duplicate_check as dc
        with mock.patch.object(sys, "argv", ["duplicate_check"]):
            with self.assertRaises(SystemExit):
                dc.main()


class TestAutoSkipReportSection(unittest.TestCase):
    def test_report_includes_auto_skipped_section_with_review_command(self):
        import indexer.duplicate_check as dc
        with tempfile.TemporaryDirectory() as academic_hub_root:
            subdir = "academic_resources/microecon/textbooks"
            pdf_path = os.path.join(academic_hub_root, subdir, "Ok_RealAnalysisWithEconomicApplications_2007.pdf")
            os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
            with open(pdf_path, "wb") as f:
                f.write(b"a re-scanned copy, different bytes")

            book_dir = os.path.join(academic_hub_root, "academic_resources", "econometrics", "textbooks", "processed_outputs", "Ok_RealAnalysisWithEconomicApplications_2007")
            os.makedirs(book_dir, exist_ok=True)
            with open(os.path.join(book_dir, "Ok_RealAnalysisWithEconomicApplications_2007.md"), "w", encoding="utf-8") as f:
                f.write("# Real Analysis")
            save_shard(academic_hub_root, "econometrics", [{
                "file_id": "some-other-fid", "path": "academic_resources/econometrics/textbooks/processed_outputs/Ok_RealAnalysisWithEconomicApplications_2007/Ok_RealAnalysisWithEconomicApplications_2007.md",
                "source_pdf_path": "academic_resources/econometrics/textbooks/Ok.pdf", "course": "econometrics",
                "doc_type": "textbook", "title": "Real Analysis with Economic Applications",
            }])

            argv = ["duplicate_check", "--textbook-subdir", subdir, "--academic-hub-root", academic_hub_root, "--non-interactive"]
            captured = StringIO()
            with mock.patch.object(sys, "argv", argv), mock.patch("sys.stdout", new=captured):
                dc.main()
            output = captured.getvalue()
            self.assertIn("Auto-skipped as likely duplicate", output)
            self.assertIn("--review-pending", output)


class TestConfirmAndRejectPending(unittest.TestCase):
    def _make_auto_skipped_clone(self, academic_hub_root):
        """Sets up exactly what Task 3's auto-skip path leaves behind:
        a real copied book directory, a clone card flagged
        duplicate_pending_confirmation, and a matching pending-confirmation
        entry -- built via the real production functions, not
        hand-fabricated, so this test exercises the actual recovery path
        against real state."""
        canonical_book_dir = os.path.join(
            academic_hub_root, "academic_resources", "econometrics", "textbooks", "processed_outputs",
            "Ok_RealAnalysisWithEconomicApplications_2007",
        )
        os.makedirs(canonical_book_dir, exist_ok=True)
        with open(os.path.join(canonical_book_dir, "Ok_RealAnalysisWithEconomicApplications_2007.md"), "w", encoding="utf-8") as f:
            f.write("# Real Analysis")
        canonical_card = {
            "file_id": "canonical-fid",
            "path": "academic_resources/econometrics/textbooks/processed_outputs/Ok_RealAnalysisWithEconomicApplications_2007/Ok_RealAnalysisWithEconomicApplications_2007.md",
            "source_pdf_path": "academic_resources/econometrics/textbooks/Ok.pdf", "course": "econometrics",
            "doc_type": "textbook", "title": "Real Analysis with Economic Applications",
        }
        save_shard(academic_hub_root, "econometrics", [canonical_card])

        new_card = copy_duplicate_artifacts(
            academic_hub_root, "econometrics", canonical_card, "microecon", "textbooks",
            "academic_resources/microecon/textbooks/Ok.pdf", pending_confirmation=True,
        )
        from indexer.duplicate_check import record_pending_confirmation, now_iso
        pending_entry = {
            "incoming_file_id": "incoming-fid", "pdf_filename": "Ok.pdf", "course": "microecon",
            "matched_course": "econometrics", "matched_file_id": "canonical-fid",
            "matched_title": "Real Analysis with Economic Applications", "score": 0.99,
            "new_card_file_id": new_card["file_id"], "queued_at": now_iso(),
        }
        record_pending_confirmation(academic_hub_root, pending_entry)
        return new_card

    def test_confirm_removes_the_pending_entry_and_leaves_the_clone_in_place(self):
        from indexer.duplicate_check import confirm_pending_confirmation, load_pending_confirmations
        with tempfile.TemporaryDirectory() as academic_hub_root:
            self._make_auto_skipped_clone(academic_hub_root)

            confirm_pending_confirmation(academic_hub_root, "incoming-fid")

            self.assertEqual(load_pending_confirmations(academic_hub_root), [])
            clone_cards = load_shard(academic_hub_root, "microecon")
            self.assertEqual(len(clone_cards), 1)
            new_book_dir = os.path.join(academic_hub_root, "academic_resources", "microecon", "textbooks", "processed_outputs", "Ok_RealAnalysisWithEconomicApplications_2007")
            self.assertTrue(os.path.exists(new_book_dir))

    def test_confirm_raises_for_an_unknown_incoming_file_id(self):
        from indexer.duplicate_check import confirm_pending_confirmation
        with tempfile.TemporaryDirectory() as academic_hub_root:
            with self.assertRaises(ValueError):
                confirm_pending_confirmation(academic_hub_root, "no-such-id")

    def test_reject_removes_the_clone_card_and_folder(self):
        from indexer.duplicate_check import reject_pending_confirmation, load_pending_confirmations
        with tempfile.TemporaryDirectory() as academic_hub_root:
            self._make_auto_skipped_clone(academic_hub_root)

            reject_pending_confirmation(academic_hub_root, "incoming-fid")

            self.assertEqual(load_pending_confirmations(academic_hub_root), [])
            self.assertEqual(load_shard(academic_hub_root, "microecon"), [])
            new_book_dir = os.path.join(academic_hub_root, "academic_resources", "microecon", "textbooks", "processed_outputs", "Ok_RealAnalysisWithEconomicApplications_2007")
            self.assertFalse(os.path.exists(new_book_dir))

    def test_reject_records_a_permanent_dismissal(self):
        from indexer.duplicate_check import reject_pending_confirmation, is_dismissed, load_dismissals
        with tempfile.TemporaryDirectory() as academic_hub_root:
            self._make_auto_skipped_clone(academic_hub_root)

            reject_pending_confirmation(academic_hub_root, "incoming-fid")

            self.assertTrue(is_dismissed(load_dismissals(academic_hub_root), "incoming-fid", "canonical-fid"))

    def test_reject_leaves_the_canonical_book_untouched(self):
        from indexer.duplicate_check import reject_pending_confirmation
        with tempfile.TemporaryDirectory() as academic_hub_root:
            self._make_auto_skipped_clone(academic_hub_root)

            reject_pending_confirmation(academic_hub_root, "incoming-fid")

            canonical_cards = load_shard(academic_hub_root, "econometrics")
            self.assertEqual(len(canonical_cards), 1)
            self.assertEqual(canonical_cards[0]["file_id"], "canonical-fid")
            canonical_book_dir = os.path.join(academic_hub_root, "academic_resources", "econometrics", "textbooks", "processed_outputs", "Ok_RealAnalysisWithEconomicApplications_2007")
            self.assertTrue(os.path.exists(canonical_book_dir))

    def test_reject_raises_for_an_unknown_incoming_file_id(self):
        from indexer.duplicate_check import reject_pending_confirmation
        with tempfile.TemporaryDirectory() as academic_hub_root:
            with self.assertRaises(ValueError):
                reject_pending_confirmation(academic_hub_root, "no-such-id")

    def test_cli_confirm_pending_flag(self):
        import indexer.duplicate_check as dc
        with tempfile.TemporaryDirectory() as academic_hub_root:
            self._make_auto_skipped_clone(academic_hub_root)
            argv = ["duplicate_check", "--confirm-pending", "incoming-fid", "--academic-hub-root", academic_hub_root]
            with mock.patch.object(sys, "argv", argv), mock.patch("sys.stdout", new=StringIO()):
                dc.main()
            self.assertEqual(dc.load_pending_confirmations(academic_hub_root), [])

    def test_cli_reject_pending_flag(self):
        import indexer.duplicate_check as dc
        with tempfile.TemporaryDirectory() as academic_hub_root:
            self._make_auto_skipped_clone(academic_hub_root)
            argv = ["duplicate_check", "--reject-pending", "incoming-fid", "--academic-hub-root", academic_hub_root]
            with mock.patch.object(sys, "argv", argv), mock.patch("sys.stdout", new=StringIO()):
                dc.main()
            self.assertEqual(load_shard(academic_hub_root, "microecon"), [])

    def test_full_lifecycle_auto_skip_then_reject_then_reconverts(self):
        # The spec's own named end-to-end guarantee (final whole-branch
        # review finding): a rejected auto-skip's source PDF re-enters
        # to_convert on a later run. Drives a REAL run_duplicate_check
        # (not the hand-fabricated incoming_file_id in
        # _make_auto_skipped_clone above), so the load-bearing link -- the
        # id an auto-skip records is the same id a later run recomputes
        # for the same PDF -- is actually protected by a test.
        from indexer.duplicate_check import reject_pending_confirmation, run_duplicate_check

        with tempfile.TemporaryDirectory() as academic_hub_root:
            subdir = "academic_resources/microecon/textbooks"
            pdf_path = os.path.join(academic_hub_root, subdir, "Ok_RealAnalysisWithEconomicApplications_2007.pdf")
            os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
            with open(pdf_path, "wb") as f:
                f.write(b"a re-scanned copy, different bytes")

            book_dir = os.path.join(academic_hub_root, "academic_resources", "econometrics", "textbooks", "processed_outputs", "Ok_RealAnalysisWithEconomicApplications_2007")
            os.makedirs(book_dir, exist_ok=True)
            with open(os.path.join(book_dir, "Ok_RealAnalysisWithEconomicApplications_2007.md"), "w", encoding="utf-8") as f:
                f.write("# Real Analysis")
            save_shard(academic_hub_root, "econometrics", [{
                "file_id": "some-other-fid",
                "path": "academic_resources/econometrics/textbooks/processed_outputs/Ok_RealAnalysisWithEconomicApplications_2007/Ok_RealAnalysisWithEconomicApplications_2007.md",
                "source_pdf_path": "academic_resources/econometrics/textbooks/Ok.pdf", "course": "econometrics",
                "doc_type": "textbook", "title": "Real Analysis with Economic Applications",
            }])

            result = run_duplicate_check(subdir, academic_hub_root, non_interactive=True, resolutions={})
            self.assertEqual(result["to_convert"], [])
            self.assertEqual(len(result["auto_skipped_pending_confirmation"]), 1)
            real_incoming_file_id = result["auto_skipped_pending_confirmation"][0]["incoming_file_id"]

            reject_pending_confirmation(academic_hub_root, real_incoming_file_id)

            result_2 = run_duplicate_check(subdir, academic_hub_root, non_interactive=True, resolutions={})
            self.assertEqual(result_2["to_convert"], ["Ok_RealAnalysisWithEconomicApplications_2007.pdf"])
            self.assertEqual(result_2["unresolved"], [])
            self.assertEqual(result_2["auto_skipped_pending_confirmation"], [])


class TestRunDuplicateCheckErrorIsolation(unittest.TestCase):
    """Regression coverage for the gap the code review caught: the
    file_id/copy/dismissal steps inside run_duplicate_check's per-PDF loop
    were unguarded, so one bad PDF could raise uncaught and lose every
    other PDF's already-accumulated result in the same batch (violates
    spec §6's per-candidate error isolation, Global Constraints line
    above). Each test here forces one specific PDF's step to fail and
    asserts (a) the batch doesn't crash, (b) an unrelated PDF processed in
    the same run is unaffected, and (c) the failing PDF lands in
    to_convert (fail-toward-converting), never silently dropped."""

    def _write_pdf(self, path, content):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(content)

    def test_file_id_computation_failure_is_isolated_to_one_pdf(self):
        import indexer.duplicate_check as dc

        with tempfile.TemporaryDirectory() as academic_hub_root:
            subdir = "academic_resources/microecon/textbooks"
            good_path = os.path.join(academic_hub_root, subdir, "Good_Book_2020.pdf")
            bad_path = os.path.join(academic_hub_root, subdir, "Bad_Book_2021.pdf")
            self._write_pdf(good_path, b"good book content")
            self._write_pdf(bad_path, b"bad book content")

            real_compute_file_id = dc.compute_file_id

            def flaky_compute_file_id(path):
                if os.path.basename(path) == "Bad_Book_2021.pdf":
                    raise RuntimeError("simulated hash failure")
                return real_compute_file_id(path)

            captured_stderr = StringIO()
            old_stderr = sys.stderr
            sys.stderr = captured_stderr
            try:
                with mock.patch.object(dc, "compute_file_id", side_effect=flaky_compute_file_id):
                    result = dc.run_duplicate_check(subdir, academic_hub_root, non_interactive=True, resolutions={})
            finally:
                sys.stderr = old_stderr

            # Neither PDF crashes the batch; both land in to_convert since
            # there are no candidates at all in this hub.
            self.assertEqual(sorted(result["to_convert"]), ["Bad_Book_2021.pdf", "Good_Book_2020.pdf"])
            self.assertEqual(result["skipped"], [])
            self.assertIn("WARNING", captured_stderr.getvalue())
            self.assertIn("Bad_Book_2021.pdf", captured_stderr.getvalue())

    def test_copy_failure_on_exact_duplicate_falls_back_to_convert_not_skipped(self):
        import indexer.duplicate_check as dc
        from indexer.index_card import compute_file_id, save_shard

        with tempfile.TemporaryDirectory() as academic_hub_root:
            subdir = "academic_resources/microecon/textbooks"
            good_path = os.path.join(academic_hub_root, subdir, "Good_Book_2020.pdf")
            dup_path = os.path.join(academic_hub_root, subdir, "Ok.pdf")
            self._write_pdf(good_path, b"good book content, no match anywhere")
            self._write_pdf(dup_path, b"%PDF-1.4 identical bytes")
            file_id = compute_file_id(dup_path)

            book_dir = os.path.join(academic_hub_root, "academic_resources", "econometrics", "textbooks", "processed_outputs", "Ok_RealAnalysis_2007")
            os.makedirs(book_dir, exist_ok=True)
            with open(os.path.join(book_dir, "Ok_RealAnalysis_2007.md"), "w", encoding="utf-8") as f:
                f.write("# Real Analysis")
            save_shard(academic_hub_root, "econometrics", [{
                "file_id": file_id, "path": "academic_resources/econometrics/textbooks/processed_outputs/Ok_RealAnalysis_2007/Ok_RealAnalysis_2007.md",
                "source_pdf_path": "academic_resources/econometrics/textbooks/Ok.pdf", "course": "econometrics",
                "doc_type": "textbook", "title": "Real Analysis with Economic Applications",
            }])

            captured_stderr = StringIO()
            old_stderr = sys.stderr
            sys.stderr = captured_stderr
            try:
                with mock.patch.object(dc, "copy_duplicate_artifacts", side_effect=OSError("disk full")):
                    result = dc.run_duplicate_check(subdir, academic_hub_root, non_interactive=True, resolutions={})
            finally:
                sys.stderr = old_stderr

            # The exact-duplicate PDF's copy blew up -- it must NOT be
            # reported as "skipped" (that would claim artifacts exist in
            # the new course when they don't); it must still convert.
            self.assertEqual(result["skipped"], [])
            self.assertEqual(sorted(result["to_convert"]), ["Good_Book_2020.pdf", "Ok.pdf"])
            self.assertIn("WARNING", captured_stderr.getvalue())

    def test_dismissal_recording_failure_does_not_crash_and_still_converts(self):
        import indexer.duplicate_check as dc
        from indexer.index_card import compute_file_id, save_shard

        with tempfile.TemporaryDirectory() as academic_hub_root:
            subdir = "academic_resources/microecon/textbooks"
            pdf_path = os.path.join(academic_hub_root, subdir, "Ok_RealAnalysisWithEconomicApplications_2007.pdf")
            self._write_pdf(pdf_path, b"a re-scanned copy, different bytes")
            incoming_file_id = compute_file_id(pdf_path)

            book_dir = os.path.join(academic_hub_root, "academic_resources", "econometrics", "textbooks", "processed_outputs", "Ok_RealAnalysisWithEconomicApplications_2007")
            os.makedirs(book_dir, exist_ok=True)
            with open(os.path.join(book_dir, "Ok_RealAnalysisWithEconomicApplications_2007.md"), "w", encoding="utf-8") as f:
                f.write("# Real Analysis")
            save_shard(academic_hub_root, "econometrics", [{
                "file_id": "some-other-fid", "path": "academic_resources/econometrics/textbooks/processed_outputs/Ok_RealAnalysisWithEconomicApplications_2007/Ok_RealAnalysisWithEconomicApplications_2007.md",
                "source_pdf_path": "academic_resources/econometrics/textbooks/Ok.pdf", "course": "econometrics",
                "doc_type": "textbook", "title": "Real Analysis with Economic Applications",
            }])

            captured_stderr = StringIO()
            old_stderr = sys.stderr
            sys.stderr = captured_stderr
            try:
                with mock.patch.object(dc, "record_dismissal", side_effect=OSError("permission denied")):
                    result = dc.run_duplicate_check(
                        subdir, academic_hub_root, non_interactive=True,
                        resolutions={incoming_file_id: "no"},
                    )
            finally:
                sys.stderr = old_stderr

            self.assertEqual(result["to_convert"], ["Ok_RealAnalysisWithEconomicApplications_2007.pdf"])
            self.assertIn("WARNING", captured_stderr.getvalue())


class TestCorruptDismissalsFile(unittest.TestCase):
    """Regression coverage (final review, Finding 4): load_dismissals() was
    the one unguarded call in run_duplicate_check -- a hand-edited or
    truncated dismissals file raised json.JSONDecodeError before a single
    PDF was looked at, taking down the whole batch. It must degrade to
    'nothing was ever dismissed' (the safe direction: at worst a pair gets
    re-asked) with a warning, like every other step in that loop."""

    def _write_pdf(self, path, content):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(content)

    def _write_dismissals(self, academic_hub_root, raw):
        from indexer.duplicate_check import _dismissals_path
        path = _dismissals_path(academic_hub_root)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(raw)

    def _run_capturing_stderr(self, academic_hub_root, subdir):
        import indexer.duplicate_check as dc
        captured_stderr = StringIO()
        old_stderr = sys.stderr
        sys.stderr = captured_stderr
        try:
            result = dc.run_duplicate_check(subdir, academic_hub_root, non_interactive=True, resolutions={})
        finally:
            sys.stderr = old_stderr
        return result, captured_stderr.getvalue()

    def test_malformed_json_warns_and_the_run_still_completes(self):
        with tempfile.TemporaryDirectory() as academic_hub_root:
            subdir = "academic_resources/microecon/textbooks"
            self._write_pdf(os.path.join(academic_hub_root, subdir, "New_Book_2020.pdf"), b"brand new content")
            self._write_dismissals(academic_hub_root, "[{\"file_id_a\": \"a\", truncated")

            result, stderr = self._run_capturing_stderr(academic_hub_root, subdir)

            self.assertEqual(result["to_convert"], ["New_Book_2020.pdf"])
            self.assertIn("WARNING", stderr)
            self.assertIn("dismissals", stderr)

    def test_wrong_json_shape_warns_and_the_run_still_completes(self):
        # Valid JSON, but an object rather than the expected list -- would
        # otherwise blow up later, inside is_dismissed's iteration.
        with tempfile.TemporaryDirectory() as academic_hub_root:
            subdir = "academic_resources/microecon/textbooks"
            self._write_pdf(os.path.join(academic_hub_root, subdir, "New_Book_2020.pdf"), b"brand new content")
            self._write_dismissals(academic_hub_root, '{"file_id_a": "a", "file_id_b": "b"}')

            result, stderr = self._run_capturing_stderr(academic_hub_root, subdir)

            self.assertEqual(result["to_convert"], ["New_Book_2020.pdf"])
            self.assertIn("WARNING", stderr)

    def test_corrupt_dismissals_does_not_prevent_duplicate_resolution(self):
        # The stronger claim: a corrupt dismissals file degrades ONLY the
        # dismissal memory -- the rest of the run (here, an exact-match
        # skip+copy) still does its real work.
        from indexer.index_card import compute_file_id

        with tempfile.TemporaryDirectory() as academic_hub_root:
            subdir = "academic_resources/microecon/textbooks"
            dup_path = os.path.join(academic_hub_root, subdir, "Ok.pdf")
            self._write_pdf(dup_path, b"%PDF-1.4 identical bytes")
            self._write_pdf(os.path.join(academic_hub_root, subdir, "New_Book_2020.pdf"), b"brand new content")
            file_id = compute_file_id(dup_path)
            self._write_dismissals(academic_hub_root, "not valid json{{{")

            book_dir = os.path.join(
                academic_hub_root, "academic_resources", "econometrics", "textbooks",
                "processed_outputs", "Ok_RealAnalysis_2007",
            )
            os.makedirs(book_dir, exist_ok=True)
            with open(os.path.join(book_dir, "Ok_RealAnalysis_2007.md"), "w", encoding="utf-8") as f:
                f.write("# Real Analysis")
            save_shard(academic_hub_root, "econometrics", [{
                "file_id": file_id,
                "path": "academic_resources/econometrics/textbooks/processed_outputs/Ok_RealAnalysis_2007/Ok_RealAnalysis_2007.md",
                "source_pdf_path": "academic_resources/econometrics/textbooks/Ok.pdf", "course": "econometrics",
                "doc_type": "textbook", "title": "Real Analysis with Economic Applications",
            }])

            result, stderr = self._run_capturing_stderr(academic_hub_root, subdir)

            self.assertEqual(result["to_convert"], ["New_Book_2020.pdf"])
            self.assertEqual(len(result["skipped"]), 1)
            self.assertIn("WARNING", stderr)


class TestDismissalsStorageLocation(unittest.TestCase):
    """Regression coverage (final review, Finding 2): the dismissals file
    used to sit at .index/duplicate_dismissals.json, which
    index_card.list_courses() enumerates as a course shard -- making a
    phantom "duplicate_dismissals" course that index_search.py's
    `rebuild --prune` would empty out, silently wiping every dismissal."""

    def test_dismissals_file_is_not_visible_to_list_courses(self):
        from indexer.duplicate_check import record_dismissal, _dismissals_path
        from indexer.index_card import list_courses

        with tempfile.TemporaryDirectory() as academic_hub_root:
            save_shard(academic_hub_root, "econometrics", [])
            record_dismissal(academic_hub_root, "id-a", "id-b")

            self.assertTrue(os.path.exists(_dismissals_path(academic_hub_root)))
            self.assertEqual(list_courses(academic_hub_root), ["econometrics"])
            self.assertNotIn("duplicate_dismissals", list_courses(academic_hub_root))
            self.assertNotIn("dismissals", list_courses(academic_hub_root))

    def test_dismissals_survive_a_round_trip_from_the_nested_location(self):
        from indexer.duplicate_check import record_dismissal, load_dismissals, is_dismissed

        with tempfile.TemporaryDirectory() as academic_hub_root:
            record_dismissal(academic_hub_root, "id-a", "id-b")
            self.assertTrue(is_dismissed(load_dismissals(academic_hub_root), "id-b", "id-a"))


class TestPendingConfirmations(unittest.TestCase):
    """Mirrors TestDismissals/TestDismissalsStorageLocation exactly -- same
    store shape, same nested-path reasoning (pipeline-autonomy-policies
    spec, Component 1b)."""

    def test_load_missing_file_returns_empty_list(self):
        from indexer.duplicate_check import load_pending_confirmations
        with tempfile.TemporaryDirectory() as academic_hub_root:
            self.assertEqual(load_pending_confirmations(academic_hub_root), [])

    def test_record_then_load_round_trips(self):
        from indexer.duplicate_check import record_pending_confirmation, load_pending_confirmations
        with tempfile.TemporaryDirectory() as academic_hub_root:
            entry = {
                "incoming_file_id": "incoming-fid", "pdf_filename": "Ok.pdf", "course": "microecon",
                "matched_course": "econometrics", "matched_file_id": "canonical-fid",
                "matched_title": "Real Analysis with Economic Applications", "score": 0.91,
                "new_card_file_id": "clone-fid", "queued_at": "2026-09-20T00:00:00+00:00",
            }
            record_pending_confirmation(academic_hub_root, entry)
            entries = load_pending_confirmations(academic_hub_root)
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0], entry)

    def test_recording_multiple_entries_appends_not_overwrites(self):
        from indexer.duplicate_check import record_pending_confirmation, load_pending_confirmations
        with tempfile.TemporaryDirectory() as academic_hub_root:
            record_pending_confirmation(academic_hub_root, {"incoming_file_id": "a", "pdf_filename": "A.pdf"})
            record_pending_confirmation(academic_hub_root, {"incoming_file_id": "b", "pdf_filename": "B.pdf"})
            entries = load_pending_confirmations(academic_hub_root)
            self.assertEqual([e["incoming_file_id"] for e in entries], ["a", "b"])

    def test_recording_the_same_incoming_and_new_card_id_twice_does_not_duplicate(self):
        # Real bug found by the final whole-branch review: the documented
        # non-interactive re-run workflow re-evaluates the same
        # never-deleted source PDF every pass, which used to append a
        # duplicate queue entry for the identical auto-skip each time.
        from indexer.duplicate_check import record_pending_confirmation, load_pending_confirmations
        with tempfile.TemporaryDirectory() as academic_hub_root:
            entry = {"incoming_file_id": "a", "pdf_filename": "A.pdf", "new_card_file_id": "clone-a"}
            record_pending_confirmation(academic_hub_root, entry)
            record_pending_confirmation(academic_hub_root, entry)
            self.assertEqual(len(load_pending_confirmations(academic_hub_root)), 1)

    def test_persists_to_the_expected_nested_path(self):
        from indexer.duplicate_check import record_pending_confirmation, _pending_confirmation_path
        with tempfile.TemporaryDirectory() as academic_hub_root:
            record_pending_confirmation(academic_hub_root, {"incoming_file_id": "a", "pdf_filename": "A.pdf"})
            expected_path = os.path.join(academic_hub_root, ".index", "duplicates", "pending_confirmation.json")
            self.assertEqual(_pending_confirmation_path(academic_hub_root), expected_path)
            self.assertTrue(os.path.exists(expected_path))

    def test_pending_confirmation_file_is_not_visible_to_list_courses(self):
        # Same regression class as TestDismissalsStorageLocation -- a flat
        # .index/-level file would be misread as a phantom course by
        # list_courses(), and a future rebuild --prune would delete it.
        from indexer.duplicate_check import record_pending_confirmation
        from indexer.index_card import list_courses, save_shard
        with tempfile.TemporaryDirectory() as academic_hub_root:
            save_shard(academic_hub_root, "econometrics", [])
            record_pending_confirmation(academic_hub_root, {"incoming_file_id": "a", "pdf_filename": "A.pdf"})
            self.assertEqual(list_courses(academic_hub_root), ["econometrics"])
            self.assertNotIn("pending_confirmation", list_courses(academic_hub_root))


if __name__ == "__main__":
    unittest.main()
