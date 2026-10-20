import unittest

from agent.problem_corpus.boundaries import ProblemSpan, detect_spans


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

    def test_q_numbered_econometrics_problem_set(self):
        body = (
            "Problem Set 1\nDirections for the class.\n\n"
            "Q1. Let Y be random.\n(a) Show its mean.\n\n"
            "Q2. Consider OLS.\n\n"
            "Q3. Estimate a treatment effect.\n"
        )
        spans = detect_spans(body)
        self.assertEqual([span.problem_label for span in spans],
                         ["Problem 1", "Problem 2", "Problem 3"])
        self.assertNotIn("Q2.", spans[0].text)

    def test_bold_q_labels_in_solution_document_are_detectable(self):
        # Detection is content-only; the stage must exclude standalone solution files.
        spans = detect_spans("**Q1.** Solution one.\n**Q2.** Solution two.\n**Q3.** Solution three.\n")
        self.assertEqual([span.problem_label for span in spans],
                         ["Problem 1", "Problem 2", "Problem 3"])

    def test_explicit_labels_ignore_numbered_recitation_lists(self):
        body = "1. Definition one.\n2. Definition two.\n3. Definition three.\n"
        self.assertEqual(len(detect_spans(body)), 3)
        self.assertEqual(detect_spans(body, require_explicit_label=True), [])
        exercises = "Q1. First exercise.\nQ2. Second exercise.\nQ3. Third exercise.\n"
        self.assertEqual(len(detect_spans(exercises, require_explicit_label=True)), 3)

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
