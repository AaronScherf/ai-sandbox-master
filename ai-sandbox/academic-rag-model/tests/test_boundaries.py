import unittest

from problem_corpus.boundaries import ProblemSpan, detect_spans


class TestDetectSpans(unittest.TestCase):
    def test_plain_numbered_problems(self):
        # Real convention confirmed live in old_problem_set.md.
        body = (
            "1. For each of the following functions, state...\n\n"
            "2. Consider a production function...\n\n"
            "3. In an economy with n goods...\n\n"
        )
        spans = detect_spans(body)
        self.assertEqual(len(spans), 3)
        self.assertEqual(spans[0].problem_label, "Problem 1")
        self.assertEqual(spans[2].problem_label, "Problem 3")

    def test_bold_practice_problem_convention(self):
        # Real convention confirmed live in Practice Sheet.md.
        body = (
            "**Practice Problem 1. Involutions**\n\nLet V be...\n\n"
            "**Practice Problem 2. Norms**\n\nShow that...\n\n"
            "**Practice Problem 3. Rank**\n\nDetermine...\n\n"
        )
        spans = detect_spans(body)
        self.assertEqual(len(spans), 3)
        self.assertEqual(spans[0].problem_label, "Problem 1")

    def test_points_annotated_problems(self):
        # Real convention confirmed live in old_exam_2021.md.
        body = (
            "1. **(40 points)** Are the following statements true or false?\n\n"
            "2. **(15 points)** Consider the following matrix\n\n"
            "3. **(15 points)**. Consider the following function\n\n"
        )
        spans = detect_spans(body)
        self.assertEqual(len(spans), 3)

    def test_question_label_convention(self):
        body = "Question 1\nDoes X hold?\n\nQuestion 2\nDoes Y hold?\n\nQuestion 3\nDoes Z hold?\n\n"
        spans = detect_spans(body)
        self.assertEqual(len(spans), 3)
        self.assertEqual(spans[0].problem_label, "Problem 1")  # label word is always "Problem"

    def test_too_few_matches_returns_empty_list(self):
        # A single accidental match (e.g. one stray "1." in prose) must
        # not be trusted as real document structure -- same bar
        # chunk_index.py's own _detect_problem_boundaries uses.
        body = "Some prose that happens to mention item 1. and nothing else numbered."
        self.assertEqual(detect_spans(body), [])

    def test_no_matches_returns_empty_list(self):
        self.assertEqual(detect_spans("No numbered problems in here."), [])

    def test_span_runs_to_start_of_next_boundary(self):
        body = "1. First problem text here.\n\n2. Second problem text here.\n\n3. Third problem text here.\n\n"
        spans = detect_spans(body)
        self.assertIn("First problem text here.", spans[0].text)
        self.assertNotIn("Second problem", spans[0].text)

    def test_last_span_runs_to_end_of_document(self):
        body = "1. First.\n\n2. Second.\n\n3. Third, running all the way to the end of the document here.\n"
        spans = detect_spans(body)
        self.assertIn("running all the way to the end", spans[-1].text)

    def test_span_text_is_stripped(self):
        body = "1. First.\n\n2. Second.\n\n3. Third.\n\n   \n"
        spans = detect_spans(body)
        self.assertEqual(spans[-1].text, spans[-1].text.strip())

    def test_problem_span_is_a_dataclass_with_text_and_label(self):
        span = ProblemSpan(text="Find X.", problem_label="Problem 1")
        self.assertEqual(span.text, "Find X.")
        self.assertEqual(span.problem_label, "Problem 1")


if __name__ == "__main__":
    unittest.main()
