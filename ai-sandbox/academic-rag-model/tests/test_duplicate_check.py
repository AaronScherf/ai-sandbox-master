import os
import tempfile
import unittest

from indexer.duplicate_check import (
    normalize_title,
    parse_author_year_from_folder_name,
    score_candidate,
    SURFACE_THRESHOLD,
    find_exact_duplicate,
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


if __name__ == "__main__":
    unittest.main()
