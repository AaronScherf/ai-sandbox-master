import unittest
from unittest.mock import MagicMock, patch

from common.ollama_utils import OLLAMA_TIMEOUT
from problem_gen.llm_gen import (
    MAX_ATTEMPTS, PROBLEMGEN_GEMINI_MODEL, _build_generation_prompt, _build_verification_prompt,
    _call_gemini, _extract_problem_and_solution, _parse_verdict, generate_and_verify,
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

    def test_topic_stated_as_an_explicit_required_constraint(self):
        prompt = _build_generation_prompt("must use an epsilon-delta argument", [], [])
        self.assertIn("Required constraint", prompt)
        self.assertEqual(prompt.count("must use an epsilon-delta argument"), 2)

    def test_retry_instructs_not_to_reference_the_correction_process(self):
        prompt = _build_generation_prompt(
            "eigenvalues", [], [], previous_problem="Find X.", previous_solution="X = 5.",
            previous_error="the verification response was not in the expected VALID/INVALID format",
        )
        self.assertIn("Do not mention this correction", prompt)
        self.assertIn("as if this were your first and only attempt", prompt)


class TestBuildVerificationPrompt(unittest.TestCase):
    def test_includes_topic_problem_and_solution(self):
        prompt = _build_verification_prompt("must use an epsilon-delta argument", "Find X.", "X = 1.")
        self.assertIn("must use an epsilon-delta argument", prompt)
        self.assertIn("Find X.", prompt)
        self.assertIn("X = 1.", prompt)

    def test_instructs_two_separate_technique_and_correctness_judgments(self):
        prompt = _build_verification_prompt("topic", "p", "s")
        self.assertIn("TECHNIQUE:", prompt)
        self.assertIn("CORRECTNESS:", prompt)


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
    def test_both_pass_returns_none(self):
        self.assertIsNone(_parse_verdict("TECHNIQUE: YES\nCORRECTNESS: VALID"))

    def test_case_insensitive(self):
        self.assertIsNone(_parse_verdict("technique: yes\ncorrectness: valid"))

    def test_tolerates_markdown_bold_formatting(self):
        self.assertIsNone(_parse_verdict("**TECHNIQUE:** YES\n**CORRECTNESS:** VALID"))

    def test_technique_no_returns_reason_with_detail(self):
        result = _parse_verdict("TECHNIQUE: NO - used open-cover instead of epsilon-delta\nCORRECTNESS: VALID")
        self.assertIn("does not use the required technique", result)
        self.assertIn("open-cover", result)

    def test_correctness_invalid_returns_reason_with_detail(self):
        result = _parse_verdict("TECHNIQUE: YES\nCORRECTNESS: INVALID: sign error in step 2")
        self.assertIn("incorrect or incomplete", result)
        self.assertIn("sign error in step 2", result)

    def test_both_fail_combines_both_reasons(self):
        result = _parse_verdict("TECHNIQUE: NO - wrong approach\nCORRECTNESS: INVALID: bad algebra")
        self.assertIn("does not use the required technique", result)
        self.assertIn("incorrect or incomplete", result)

    def test_missing_technique_line_fails_closed(self):
        result = _parse_verdict("CORRECTNESS: VALID")
        self.assertIn("TECHNIQUE", result)

    def test_missing_correctness_line_fails_closed(self):
        result = _parse_verdict("TECHNIQUE: YES")
        self.assertIn("CORRECTNESS", result)

    def test_completely_unparseable_response_fails_both(self):
        result = _parse_verdict("I think it's probably fine")
        self.assertIn("TECHNIQUE", result)
        self.assertIn("CORRECTNESS", result)

    def test_bare_technique_no_does_not_swallow_the_next_line(self):
        """Real trial found this: a bare 'TECHNIQUE: NO' with nothing
        else on its own line, immediately followed by a CORRECTNESS
        line, must not have that next line captured as if it were the
        technique's own detail -- that corrupted retry feedback fed
        into later attempts with the literal text 'used instead:
        CORRECTNESS: VALID' (see
        docs/2026-09-05-problem-generation-status.md's 2026-09-06 entry)."""
        result = _parse_verdict("TECHNIQUE: NO\nCORRECTNESS: VALID")
        self.assertEqual(result, "the solution does not use the required technique")

    def test_bare_correctness_invalid_does_not_swallow_a_preceding_technique_line(self):
        result = _parse_verdict("TECHNIQUE: YES\nCORRECTNESS: INVALID")
        self.assertEqual(result, "the solution is incorrect or incomplete")


class TestCallGemini(unittest.TestCase):
    def test_returns_response_text_on_success(self):
        client = MagicMock()
        client.models.generate_content.return_value = MagicMock(text="## Problem\nFind X.")
        result = _call_gemini("prompt", client)
        self.assertEqual(result, "## Problem\nFind X.")

    def test_uses_the_configured_model(self):
        client = MagicMock()
        client.models.generate_content.return_value = MagicMock(text="response")
        _call_gemini("prompt", client)
        self.assertEqual(client.models.generate_content.call_args.kwargs["model"], PROBLEMGEN_GEMINI_MODEL)

    def test_passes_the_prompt_through(self):
        client = MagicMock()
        client.models.generate_content.return_value = MagicMock(text="response")
        _call_gemini("my specific prompt", client)
        self.assertEqual(client.models.generate_content.call_args.kwargs["contents"], "my specific prompt")

    def test_strips_whitespace_from_response(self):
        client = MagicMock()
        client.models.generate_content.return_value = MagicMock(text="  response with padding  \n")
        result = _call_gemini("prompt", client)
        self.assertEqual(result, "response with padding")

    def test_returns_none_when_call_with_retries_raises(self):
        client = MagicMock()
        with patch("problem_gen.llm_gen.call_with_retries", side_effect=Exception("quota exceeded")):
            result = _call_gemini("prompt", client)
        self.assertIsNone(result)


@patch("problem_gen.llm_gen.PROBLEMGEN_BACKEND", "ollama")
class TestGenerateAndVerifyOllamaBackend(unittest.TestCase):
    def test_returns_none_when_ollama_unreachable(self):
        with patch("problem_gen.llm_gen.call_ollama", return_value=None) as mock_call:
            result = generate_and_verify("eigenvalues", ["example"], [], MagicMock())
        self.assertIsNone(result)
        self.assertEqual(mock_call.call_count, 1)  # unreachable Ollama isn't worth retrying

    def test_succeeds_on_first_attempt_when_verification_passes(self):
        responses = ["## Problem\nFind X.\n\n## Solution\nX = 1.", "TECHNIQUE: YES\nCORRECTNESS: VALID"]
        with patch("problem_gen.llm_gen.call_ollama", side_effect=responses) as mock_call:
            result = generate_and_verify("eigenvalues", ["example"], [], MagicMock())
        self.assertEqual(result, ("Find X.", "X = 1."))
        self.assertEqual(mock_call.call_count, 2)

    def test_retries_after_extraction_failure_then_succeeds(self):
        responses = [
            "no sections here",                                    # attempt 1 generation
            "## Problem\nFind X.\n\n## Solution\nX = 1.",           # attempt 2 generation
            "TECHNIQUE: YES\nCORRECTNESS: VALID",                   # attempt 2 verification
        ]
        with patch("problem_gen.llm_gen.call_ollama", side_effect=responses) as mock_call:
            result = generate_and_verify("eigenvalues", ["example"], [], MagicMock())
        self.assertEqual(result, ("Find X.", "X = 1."))
        self.assertEqual(mock_call.call_count, 3)
        second_prompt = mock_call.call_args_list[1].args[0]
        self.assertIn("did not contain both", second_prompt)

    def test_retries_after_invalid_verification_with_reason_fed_back(self):
        responses = [
            "## Problem\nFind X.\n\n## Solution\nX = 2.",                    # attempt 1 generation
            "TECHNIQUE: YES\nCORRECTNESS: INVALID: X should equal 1, not 2", # attempt 1 verification
            "## Problem\nFind X.\n\n## Solution\nX = 1.",                    # attempt 2 generation
            "TECHNIQUE: YES\nCORRECTNESS: VALID",                            # attempt 2 verification
        ]
        with patch("problem_gen.llm_gen.call_ollama", side_effect=responses) as mock_call:
            result = generate_and_verify("eigenvalues", ["example"], [], MagicMock())
        self.assertEqual(result, ("Find X.", "X = 1."))
        self.assertEqual(mock_call.call_count, 4)
        third_prompt = mock_call.call_args_list[2].args[0]
        self.assertIn("X should equal 1, not 2", third_prompt)

    def test_retries_after_technique_mismatch_with_reason_fed_back(self):
        responses = [
            "## Problem\nFind X.\n\n## Solution\nOpen-cover proof.",        # attempt 1 generation
            "TECHNIQUE: NO - used open-cover instead\nCORRECTNESS: VALID",  # attempt 1 verification
            "## Problem\nFind X.\n\n## Solution\nEpsilon-delta proof.",     # attempt 2 generation
            "TECHNIQUE: YES\nCORRECTNESS: VALID",                          # attempt 2 verification
        ]
        with patch("problem_gen.llm_gen.call_ollama", side_effect=responses) as mock_call:
            result = generate_and_verify("must use epsilon-delta", ["example"], [], MagicMock())
        self.assertEqual(result, ("Find X.", "Epsilon-delta proof."))
        self.assertEqual(mock_call.call_count, 4)
        third_prompt = mock_call.call_args_list[2].args[0]
        self.assertIn("does not use the required technique", third_prompt)
        self.assertIn("used open-cover instead", third_prompt)

    def test_retries_after_ollama_timeout(self):
        responses = [
            OLLAMA_TIMEOUT, "## Problem\nFind X.\n\n## Solution\nX = 1.", "TECHNIQUE: YES\nCORRECTNESS: VALID",
        ]
        with patch("problem_gen.llm_gen.call_ollama", side_effect=responses) as mock_call:
            result = generate_and_verify("eigenvalues", ["example"], [], MagicMock())
        self.assertEqual(result, ("Find X.", "X = 1."))
        self.assertEqual(mock_call.call_count, 3)

    def test_reverifies_the_same_pair_after_a_verification_timeout_instead_of_regenerating(self):
        responses = [
            "## Problem\nFind X.\n\n## Solution\nX = 1.",  # attempt 1 generation
            OLLAMA_TIMEOUT,                                  # attempt 1 verification -- times out
            "TECHNIQUE: YES\nCORRECTNESS: VALID",            # re-verification of the SAME pair
        ]
        with patch("problem_gen.llm_gen.call_ollama", side_effect=responses) as mock_call:
            result = generate_and_verify("eigenvalues", ["example"], [], MagicMock())
        self.assertEqual(result, ("Find X.", "X = 1."))
        # Exactly 3 calls (not 4): a fourth call would mean the timeout discarded
        # "Find X." / "X = 1." and regenerated a brand new problem instead of
        # re-verifying the one already produced.
        self.assertEqual(mock_call.call_count, 3)
        third_prompt = mock_call.call_args_list[2].args[0]
        self.assertIn("Find X.", third_prompt)
        self.assertIn("X = 1.", third_prompt)

    def test_gives_up_when_verification_keeps_timing_out(self):
        responses = ["## Problem\nFind X.\n\n## Solution\nX = 1."] + [OLLAMA_TIMEOUT] * MAX_ATTEMPTS
        with patch("problem_gen.llm_gen.call_ollama", side_effect=responses) as mock_call:
            result = generate_and_verify("eigenvalues", ["example"], [], MagicMock())
        self.assertIsNone(result)
        self.assertEqual(mock_call.call_count, 1 + MAX_ATTEMPTS)

    def test_returns_none_when_max_attempts_exhausted(self):
        with patch("problem_gen.llm_gen.call_ollama", return_value="never valid sections") as mock_call:
            result = generate_and_verify("eigenvalues", ["example"], [], MagicMock())
        self.assertIsNone(result)
        self.assertEqual(mock_call.call_count, MAX_ATTEMPTS)

    def test_generation_and_verification_prompts_carry_the_expected_content(self):
        responses = ["## Problem\nFind X.\n\n## Solution\nX = 1.", "TECHNIQUE: YES\nCORRECTNESS: VALID"]
        with patch("problem_gen.llm_gen.call_ollama", side_effect=responses) as mock_call:
            generate_and_verify("eigenvalues", ["example"], [], MagicMock())
        first_call_prompt = mock_call.call_args_list[0].args[0]
        second_call_prompt = mock_call.call_args_list[1].args[0]
        self.assertIn("eigenvalues", first_call_prompt)
        self.assertIn("eigenvalues", second_call_prompt)  # topic now also checked during verification
        self.assertIn("Find X.", second_call_prompt)
        self.assertIn("X = 1.", second_call_prompt)


class TestGenerateAndVerifyGeminiBackend(unittest.TestCase):
    """PROBLEMGEN_BACKEND defaults to "gemini" (no patching needed) --
    see docs/2026-09-05-problem-generation-status.md's 2026-09-06 entry:
    a real feasibility spike found gemini-3.1-flash-lite passed 9/9
    trials across three technique-constrained topics where the local
    Ollama model never once succeeded. Mocks _call_gemini directly
    (the single dispatch point), mirroring how the Ollama-backend tests
    above mock call_ollama, rather than reaching into the Gemini SDK's
    own client mock -- consistent with this project's established
    network-code testing convention."""

    def test_succeeds_on_first_attempt_when_verification_passes(self):
        client = MagicMock()
        responses = ["## Problem\nFind X.\n\n## Solution\nX = 1.", "TECHNIQUE: YES\nCORRECTNESS: VALID"]
        with patch("problem_gen.llm_gen._call_gemini", side_effect=responses) as mock_call:
            result = generate_and_verify("eigenvalues", ["example"], [], client)
        self.assertEqual(result, ("Find X.", "X = 1."))
        self.assertEqual(mock_call.call_count, 2)

    def test_client_is_threaded_through_to_call_gemini(self):
        client = MagicMock()
        responses = ["## Problem\nFind X.\n\n## Solution\nX = 1.", "TECHNIQUE: YES\nCORRECTNESS: VALID"]
        with patch("problem_gen.llm_gen._call_gemini", side_effect=responses) as mock_call:
            generate_and_verify("eigenvalues", ["example"], [], client)
        self.assertEqual(mock_call.call_args_list[0].args[1], client)
        self.assertEqual(mock_call.call_args_list[1].args[1], client)

    def test_returns_none_when_gemini_unreachable(self):
        client = MagicMock()
        with patch("problem_gen.llm_gen._call_gemini", return_value=None) as mock_call:
            result = generate_and_verify("eigenvalues", ["example"], [], client)
        self.assertIsNone(result)
        self.assertEqual(mock_call.call_count, 1)  # unreachable isn't worth retrying, same as Ollama

    def test_retries_after_extraction_failure_then_succeeds(self):
        client = MagicMock()
        responses = [
            "no sections here",
            "## Problem\nFind X.\n\n## Solution\nX = 1.",
            "TECHNIQUE: YES\nCORRECTNESS: VALID",
        ]
        with patch("problem_gen.llm_gen._call_gemini", side_effect=responses) as mock_call:
            result = generate_and_verify("eigenvalues", ["example"], [], client)
        self.assertEqual(result, ("Find X.", "X = 1."))
        self.assertEqual(mock_call.call_count, 3)

    def test_retries_after_technique_mismatch_with_reason_fed_back(self):
        client = MagicMock()
        responses = [
            "## Problem\nFind X.\n\n## Solution\nOpen-cover proof.",
            "TECHNIQUE: NO - used open-cover instead\nCORRECTNESS: VALID",
            "## Problem\nFind X.\n\n## Solution\nEpsilon-delta proof.",
            "TECHNIQUE: YES\nCORRECTNESS: VALID",
        ]
        with patch("problem_gen.llm_gen._call_gemini", side_effect=responses) as mock_call:
            result = generate_and_verify("must use epsilon-delta", ["example"], [], client)
        self.assertEqual(result, ("Find X.", "Epsilon-delta proof."))
        self.assertEqual(mock_call.call_count, 4)
        third_prompt = mock_call.call_args_list[2].args[0]
        self.assertIn("does not use the required technique", third_prompt)

    def test_returns_none_when_max_attempts_exhausted(self):
        client = MagicMock()
        with patch("problem_gen.llm_gen._call_gemini", return_value="never valid sections") as mock_call:
            result = generate_and_verify("eigenvalues", ["example"], [], client)
        self.assertIsNone(result)
        self.assertEqual(mock_call.call_count, MAX_ATTEMPTS)

    def test_never_touches_ollama(self):
        """The Gemini backend must never call call_ollama at all --
        confirms the dispatch is a clean either/or, not an accidental
        fallthrough."""
        client = MagicMock()
        responses = ["## Problem\nFind X.\n\n## Solution\nX = 1.", "TECHNIQUE: YES\nCORRECTNESS: VALID"]
        with patch("problem_gen.llm_gen._call_gemini", side_effect=responses), \
             patch("problem_gen.llm_gen.call_ollama") as mock_ollama:
            generate_and_verify("eigenvalues", ["example"], [], client)
        mock_ollama.assert_not_called()


if __name__ == "__main__":
    unittest.main()
