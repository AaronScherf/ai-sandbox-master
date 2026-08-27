import unittest

from postprocess_findings import (
    documents_needing_review,
    find_isolated_candidate_spans,
    group_findings_by_signature,
    is_allowlisted_span,
    search_reference_documents,
)


class TestIsAllowlistedSpan(unittest.TestCase):
    def test_ordinary_ascii_letter_is_allowlisted(self):
        # Confirmed real finding: the allowlist can't distinguish the
        # radical-as-p bug from any other ordinary ASCII letter -- both
        # pass this check. Suppression only helps the *other* false-
        # positive class (see the next tests).
        self.assertTrue(is_allowlisted_span("p"))

    def test_greek_letter_is_allowlisted(self):
        # Real case from the design spike: xi/eta are legitimate math
        # notation, already covered by transcribe_notes.py's own
        # ALLOWED_MATH_RANGES (Greek and Coptic).
        self.assertTrue(is_allowlisted_span("ξ"))  # xi

    def test_private_use_area_character_is_not_allowlisted(self):
        self.assertFalse(is_allowlisted_span(""))

    def test_whitespace_only_span_is_allowlisted(self):
        self.assertTrue(is_allowlisted_span("   "))


class TestFindIsolatedCandidateSpans(unittest.TestCase):
    def test_single_span_line_with_one_character_is_a_candidate(self):
        # Real case: Analysis_Exercises.pdf page 6, a radical sign
        # extracting as a standalone "p" on its own line.
        lines = [[{"text": "p", "origin": (100.0, 200.0)}]]
        candidates = find_isolated_candidate_spans(lines)
        self.assertEqual(candidates, [{"text": "p", "origin": (100.0, 200.0)}])

    def test_multi_span_line_is_not_a_candidate(self):
        lines = [[{"text": "5. Divide by", "origin": (0.0, 0.0)}, {"text": " ", "origin": (0.0, 0.0)}]]
        self.assertEqual(find_isolated_candidate_spans(lines), [])

    def test_single_span_multi_character_line_is_not_a_candidate(self):
        lines = [[{"text": "h^2 + k^2", "origin": (0.0, 0.0)}]]
        self.assertEqual(find_isolated_candidate_spans(lines), [])

    def test_empty_lines_list_returns_empty(self):
        self.assertEqual(find_isolated_candidate_spans([]), [])


class TestGroupFindingsBySignature(unittest.TestCase):
    def test_groups_same_text_same_document_together(self):
        findings = [
            {"document": "a.md", "flagged_text": "p"},
            {"document": "a.md", "flagged_text": "p"},
            {"document": "a.md", "flagged_text": "q"},
        ]
        grouped = group_findings_by_signature(findings)
        self.assertEqual(len(grouped["a.md::p"]), 2)
        self.assertEqual(len(grouped["a.md::q"]), 1)

    def test_same_text_different_documents_stay_separate(self):
        findings = [
            {"document": "a.md", "flagged_text": "p"},
            {"document": "b.md", "flagged_text": "p"},
        ]
        grouped = group_findings_by_signature(findings)
        self.assertEqual(len(grouped), 2)


class TestDocumentsNeedingReview(unittest.TestCase):
    def test_document_crossing_threshold_is_flagged(self):
        grouped = {
            "a.md::p": [{"document": "a.md", "flagged_text": "p"}] * 5,
        }
        self.assertEqual(documents_needing_review(grouped, threshold=5), ["a.md"])

    def test_document_below_threshold_is_not_flagged(self):
        # This is the explicit requirement this design exists to satisfy:
        # don't surface a review for every single potentially-corrupted
        # character, only for a real pattern.
        grouped = {
            "a.md::p": [{"document": "a.md", "flagged_text": "p"}] * 2,
        }
        self.assertEqual(documents_needing_review(grouped, threshold=5), [])

    def test_no_findings_returns_empty_list(self):
        self.assertEqual(documents_needing_review({}, threshold=5), [])


class TestSearchReferenceDocuments(unittest.TestCase):
    def test_finds_term_with_surrounding_context(self):
        refs = {"textbook.md": "The Hessian matrix H_f(x) is symmetric under mild conditions."}
        matches = search_reference_documents("Hessian", refs, context_chars=10)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["document"], "textbook.md")
        self.assertIn("Hessian", matches[0]["context"])

    def test_case_insensitive(self):
        refs = {"a.md": "the hessian matrix"}
        matches = search_reference_documents("Hessian", refs)
        self.assertEqual(len(matches), 1)

    def test_finds_multiple_occurrences_across_documents(self):
        refs = {"a.md": "Hessian here.", "b.md": "Hessian there too."}
        matches = search_reference_documents("Hessian", refs)
        self.assertEqual(len(matches), 2)

    def test_no_match_returns_empty_list(self):
        refs = {"a.md": "no relevant content"}
        self.assertEqual(search_reference_documents("Hessian", refs), [])

    def test_blank_term_returns_empty_list(self):
        self.assertEqual(search_reference_documents("   ", {"a.md": "text"}), [])


if __name__ == "__main__":
    unittest.main()
