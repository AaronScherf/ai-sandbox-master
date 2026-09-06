import unittest
from unittest.mock import MagicMock, patch

from problem_corpus.llm_extract import (
    PROBLEM_CORPUS_GEMINI_MODEL, ExtractedRecord, _build_extraction_prompt, _parse_response, extract_record,
)


class TestBuildExtractionPrompt(unittest.TestCase):
    def test_includes_the_span_text(self):
        prompt = _build_extraction_prompt("1. Find the eigenvalues of A.")
        self.assertIn("Find the eigenvalues of A.", prompt)

    def test_instructs_none_for_missing_solution(self):
        prompt = _build_extraction_prompt("some span")
        self.assertIn("NONE", prompt)

    def test_asks_for_three_labeled_sections(self):
        prompt = _build_extraction_prompt("some span")
        self.assertIn("## Problem", prompt)
        self.assertIn("## Solution", prompt)
        self.assertIn("## Topic", prompt)

    def test_instructs_verbatim_solution_not_a_rewrite(self):
        prompt = _build_extraction_prompt("some span")
        self.assertIn("verbatim", prompt)


class TestParseResponse(unittest.TestCase):
    def test_parses_all_three_sections(self):
        text = "## Problem\nFind X.\n\n## Solution\nX = 1.\n\n## Topic\nalgebra"
        result = _parse_response(text)
        self.assertEqual(result, ExtractedRecord(problem_text="Find X.", solution_text="X = 1.", topic_tag="algebra"))

    def test_none_solution_becomes_python_none(self):
        text = "## Problem\nFind X.\n\n## Solution\nNONE\n\n## Topic\nalgebra"
        result = _parse_response(text)
        self.assertIsNone(result.solution_text)

    def test_none_solution_is_case_insensitive(self):
        text = "## Problem\nFind X.\n\n## Solution\nnone\n\n## Topic\nalgebra"
        result = _parse_response(text)
        self.assertIsNone(result.solution_text)

    def test_case_insensitive_headings(self):
        text = "## problem\nFind X.\n\n## solution\nNONE\n\n## topic\nalgebra"
        result = _parse_response(text)
        self.assertEqual(result.problem_text, "Find X.")

    def test_returns_none_when_topic_section_missing(self):
        self.assertIsNone(_parse_response("## Problem\nFind X.\n\n## Solution\nNONE"))

    def test_returns_none_when_problem_section_empty(self):
        self.assertIsNone(_parse_response("## Problem\n\n## Solution\nNONE\n\n## Topic\nalgebra"))

    def test_returns_none_when_topic_section_empty(self):
        self.assertIsNone(_parse_response("## Problem\nFind X.\n\n## Solution\nNONE\n\n## Topic\n"))

    def test_returns_none_when_no_sections_at_all(self):
        self.assertIsNone(_parse_response("just some prose"))

    def test_sections_are_stripped(self):
        text = "## Problem\n  Find X.  \n\n## Solution\nNONE\n\n## Topic\n  algebra  "
        result = _parse_response(text)
        self.assertEqual(result.problem_text, "Find X.")
        self.assertEqual(result.topic_tag, "algebra")


class TestExtractRecord(unittest.TestCase):
    def test_returns_parsed_record_on_success(self):
        client = MagicMock()
        client.models.generate_content.return_value = MagicMock(
            text="## Problem\nFind X.\n\n## Solution\nX = 1.\n\n## Topic\nalgebra"
        )
        result = extract_record("1. Find X.", client)
        self.assertEqual(result, ExtractedRecord(problem_text="Find X.", solution_text="X = 1.", topic_tag="algebra"))

    def test_uses_the_configured_model(self):
        client = MagicMock()
        client.models.generate_content.return_value = MagicMock(
            text="## Problem\nX\n\n## Solution\nNONE\n\n## Topic\nt"
        )
        extract_record("span", client)
        self.assertEqual(client.models.generate_content.call_args.kwargs["model"], PROBLEM_CORPUS_GEMINI_MODEL)

    def test_passes_the_span_text_through(self):
        client = MagicMock()
        client.models.generate_content.return_value = MagicMock(
            text="## Problem\nX\n\n## Solution\nNONE\n\n## Topic\nt"
        )
        extract_record("a very specific span of text", client)
        self.assertIn("a very specific span of text", client.models.generate_content.call_args.kwargs["contents"])

    def test_returns_none_when_call_with_retries_raises(self):
        client = MagicMock()
        with patch("problem_corpus.llm_extract.call_with_retries", side_effect=Exception("quota exceeded")):
            result = extract_record("span", client)
        self.assertIsNone(result)

    def test_returns_none_when_response_does_not_parse(self):
        client = MagicMock()
        client.models.generate_content.return_value = MagicMock(text="not in the expected format")
        result = extract_record("span", client)
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
