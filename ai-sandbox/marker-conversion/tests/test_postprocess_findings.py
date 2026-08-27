import unittest

from postprocess_findings import find_isolated_candidate_spans, is_allowlisted_span


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


if __name__ == "__main__":
    unittest.main()
