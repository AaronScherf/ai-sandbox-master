import unittest
from unittest.mock import patch

from common.ollama_utils import OLLAMA_TIMEOUT
from problem_gen.llm_gen import (
    MAX_ATTEMPTS, _build_generation_prompt, _build_verification_prompt,
    _extract_problem_and_solution, _parse_verdict, generate_and_verify,
)


class TestBuildGenerationPrompt(unittest.TestCase):
    def test_first_attempt_has_no_retry_content(self):
        prompt = _build_generation_prompt("eigenvalues", [], [])
        self.assertNotIn("previous attempt", prompt)
        self.assertNotIn("That attempt failed", prompt)

    def test_includes_style_examples_with_do_not_copy_warning(self):
        prompt = _build_generation_prompt("eigenvalues", ["Find the eigenvalues of [[2,0],[0,3]]."], [])
        self.assertIn("Find the eigenvalues of [[2,0],[0,3]].", prompt)
        self.assertIn("do not copy them", prompt)

    def test_includes_content_excerpts_when_provided(self):
        prompt = _build_generation_prompt("eigenvalues", [], ["An eigenvalue satisfies Av = lv."])
        self.assertIn("An eigenvalue satisfies Av = lv.", prompt)

    def test_omits_content_block_when_empty(self):
        prompt = _build_generation_prompt("eigenvalues", ["example"], [])
        self.assertNotIn("Background from the student's own textbooks", prompt)

    def test_retry_includes_previous_problem_solution_and_error(self):
        prompt = _build_generation_prompt(
            "eigenvalues", ["example"], [],
            previous_problem="Find X.", previous_solution="X = 5.",
            previous_error="the solution never actually solves for X",
        )
        self.assertIn("Find X.", prompt)
        self.assertIn("X = 5.", prompt)
        self.assertIn("the solution never actually solves for X", prompt)

    def test_retry_without_previous_problem_still_includes_error(self):
        prompt = _build_generation_prompt(
            "eigenvalues", [], [], previous_problem=None, previous_solution=None,
            previous_error="the response did not contain both a '## Problem' and '## Solution' section",
        )
        self.assertIn("did not contain both", prompt)


class TestExtractProblemAndSolution(unittest.TestCase):
    def test_extracts_both_sections(self):
        text = "## Problem\nFind the eigenvalues.\n\n## Solution\nThey are 2 and 3."
        result = _extract_problem_and_solution(text)
        self.assertEqual(result, ("Find the eigenvalues.", "They are 2 and 3."))

    def test_case_insensitive_headings(self):
        text = "## problem\nFind X.\n\n## solution\nX = 1."
        self.assertEqual(_extract_problem_and_solution(text), ("Find X.", "X = 1."))

    def test_returns_none_when_solution_section_missing(self):
        self.assertIsNone(_extract_problem_and_solution("## Problem\nFind X."))

    def test_returns_none_when_problem_section_empty(self):
        self.assertIsNone(_extract_problem_and_solution("## Problem\n\n## Solution\nX = 1."))

    def test_returns_none_when_no_sections_at_all(self):
        self.assertIsNone(_extract_problem_and_solution("just some prose"))


class TestParseVerdict(unittest.TestCase):
    def test_valid_returns_none(self):
        self.assertIsNone(_parse_verdict("VALID"))

    def test_valid_case_insensitive(self):
        self.assertIsNone(_parse_verdict("valid"))

    def test_invalid_returns_reason(self):
        self.assertEqual(_parse_verdict("INVALID: the answer sign is wrong"), "the answer sign is wrong")

    def test_invalid_with_no_reason_gets_a_generic_one(self):
        self.assertEqual(_parse_verdict("INVALID:"), "the verification response gave no reason")

    def test_unparseable_response_treated_as_invalid(self):
        result = _parse_verdict("I think it's probably fine")
        self.assertIsNotNone(result)
        self.assertIn("not in the expected", result)


class TestGenerateAndVerify(unittest.TestCase):
    def test_returns_none_when_ollama_unreachable(self):
        with patch("problem_gen.llm_gen.call_ollama", return_value=None) as mock_call:
            result = generate_and_verify("eigenvalues", ["example"], [])
        self.assertIsNone(result)
        self.assertEqual(mock_call.call_count, 1)  # unreachable Ollama isn't worth retrying

    def test_succeeds_on_first_attempt_when_verification_passes(self):
        responses = ["## Problem\nFind X.\n\n## Solution\nX = 1.", "VALID"]
        with patch("problem_gen.llm_gen.call_ollama", side_effect=responses) as mock_call:
            result = generate_and_verify("eigenvalues", ["example"], [])
        self.assertEqual(result, ("Find X.", "X = 1."))
        self.assertEqual(mock_call.call_count, 2)

    def test_retries_after_extraction_failure_then_succeeds(self):
        responses = [
            "no sections here",                                    # attempt 1 generation
            "## Problem\nFind X.\n\n## Solution\nX = 1.",           # attempt 2 generation
            "VALID",                                                # attempt 2 verification
        ]
        with patch("problem_gen.llm_gen.call_ollama", side_effect=responses) as mock_call:
            result = generate_and_verify("eigenvalues", ["example"], [])
        self.assertEqual(result, ("Find X.", "X = 1."))
        self.assertEqual(mock_call.call_count, 3)
        second_prompt = mock_call.call_args_list[1].args[0]
        self.assertIn("did not contain both", second_prompt)

    def test_retries_after_invalid_verification_with_reason_fed_back(self):
        responses = [
            "## Problem\nFind X.\n\n## Solution\nX = 2.",           # attempt 1 generation
            "INVALID: X should equal 1, not 2",                     # attempt 1 verification
            "## Problem\nFind X.\n\n## Solution\nX = 1.",           # attempt 2 generation
            "VALID",                                                # attempt 2 verification
        ]
        with patch("problem_gen.llm_gen.call_ollama", side_effect=responses) as mock_call:
            result = generate_and_verify("eigenvalues", ["example"], [])
        self.assertEqual(result, ("Find X.", "X = 1."))
        self.assertEqual(mock_call.call_count, 4)
        third_prompt = mock_call.call_args_list[2].args[0]
        self.assertIn("X should equal 1, not 2", third_prompt)

    def test_retries_after_ollama_timeout(self):
        responses = [OLLAMA_TIMEOUT, "## Problem\nFind X.\n\n## Solution\nX = 1.", "VALID"]
        with patch("problem_gen.llm_gen.call_ollama", side_effect=responses) as mock_call:
            result = generate_and_verify("eigenvalues", ["example"], [])
        self.assertEqual(result, ("Find X.", "X = 1."))
        self.assertEqual(mock_call.call_count, 3)

    def test_returns_none_when_max_attempts_exhausted(self):
        with patch("problem_gen.llm_gen.call_ollama", return_value="never valid sections") as mock_call:
            result = generate_and_verify("eigenvalues", ["example"], [])
        self.assertIsNone(result)
        self.assertEqual(mock_call.call_count, MAX_ATTEMPTS)

    def test_generation_and_verification_prompts_carry_the_expected_content(self):
        responses = ["## Problem\nFind X.\n\n## Solution\nX = 1.", "VALID"]
        with patch("problem_gen.llm_gen.call_ollama", side_effect=responses) as mock_call:
            generate_and_verify("eigenvalues", ["example"], [])
        first_call_prompt = mock_call.call_args_list[0].args[0]
        second_call_prompt = mock_call.call_args_list[1].args[0]
        self.assertIn("eigenvalues", first_call_prompt)
        self.assertIn("Find X.", second_call_prompt)
        self.assertIn("X = 1.", second_call_prompt)


if __name__ == "__main__":
    unittest.main()
