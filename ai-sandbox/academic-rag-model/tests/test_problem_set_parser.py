import tempfile
import os
import unittest

from rag.problem_set_parser import extract_question, QuestionNotFoundError

_HEADING_STYLE = """## Question 1

First question text,
on two lines.

## Question 2

Second question text.

## Question 10

Tenth question text.
"""

_HEADING_WITH_SUBPARTS_STYLE = """## Question 1: Some things to clear up from class

1. Come up with a choice correspondence that satisfies property alpha.
2. Show that if a choice correspondence has a utility representation.
3. Prove that a choice correspondence satisfies alpha and beta.

## Question 2: Alternative Choice Procedures

1. Satisficing: a decision maker choosing between books.
2. Elimination by Aspects: the DM is choosing between kettles.
"""

_NUMBERED_STYLE = """Some preamble line.

1. First numbered question.

2. Second numbered question,
   also two lines.

10. Tenth numbered question.
"""


def _write(tmp, name, content):
    path = os.path.join(tmp, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


class TestExtractQuestionHeadingStyle(unittest.TestCase):
    def test_extracts_by_heading_number(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(tmp, "hw.md", _HEADING_STYLE)
            result = extract_question(path, "2")
        self.assertIn("Second question text.", result)
        self.assertNotIn("Tenth question text.", result)

    def test_multi_line_question_captured_in_full(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(tmp, "hw.md", _HEADING_STYLE)
            result = extract_question(path, "1")
        self.assertIn("First question text,", result)
        self.assertIn("on two lines.", result)

    def test_ref_does_not_match_prefixed_number(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(tmp, "hw.md", _HEADING_STYLE)
            result = extract_question(path, "1")
        self.assertNotIn("Tenth question text.", result)


class TestExtractQuestionHeadingWithNumberedSubparts(unittest.TestCase):
    """Regression for the final-review Critical finding: real problem-set
    files (e.g. academic-hub's homework_1_solutions.md/homework_3.md) put
    numbered sub-parts *inside* a `## Question N` section. The old
    heading/numbered dual-mode search treated every sub-part's `N. ` line
    as its own question start/stop, truncating heading-style questions at
    their first sub-part and misattributing later sub-parts to the wrong
    ref."""

    def test_full_heading_section_returned_including_all_subparts(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(tmp, "hw.md", _HEADING_WITH_SUBPARTS_STYLE)
            result = extract_question(path, "1")
        self.assertIn("Some things to clear up from class", result)
        self.assertIn("Come up with a choice correspondence", result)
        self.assertIn("Show that if a choice correspondence", result)
        self.assertIn("Prove that a choice correspondence", result)
        self.assertNotIn("Alternative Choice Procedures", result)
        self.assertNotIn("Satisficing", result)

    def test_ref_two_returns_question_two_not_a_subpart(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(tmp, "hw.md", _HEADING_WITH_SUBPARTS_STYLE)
            result = extract_question(path, "2")
        self.assertIn("Alternative Choice Procedures", result)
        self.assertIn("Satisficing", result)
        self.assertIn("Elimination by Aspects", result)
        self.assertNotIn("Come up with a choice correspondence", result)


class TestExtractQuestionNumberedStyle(unittest.TestCase):
    def test_extracts_by_numbered_item(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(tmp, "hw.md", _NUMBERED_STYLE)
            result = extract_question(path, "2")
        self.assertIn("Second numbered question,", result)
        self.assertIn("also two lines.", result)
        self.assertNotIn("Tenth numbered question.", result)

    def test_ref_one_does_not_match_ref_ten(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(tmp, "hw.md", _NUMBERED_STYLE)
            result = extract_question(path, "1")
        self.assertIn("First numbered question.", result)
        self.assertNotIn("Tenth numbered question.", result)


class TestExtractQuestionNotFound(unittest.TestCase):
    def test_raises_when_ref_not_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(tmp, "hw.md", _HEADING_STYLE)
            with self.assertRaises(QuestionNotFoundError):
                extract_question(path, "99")
