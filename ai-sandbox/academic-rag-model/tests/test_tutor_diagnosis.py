import unittest
from unittest.mock import MagicMock

from core.indexer.index_search import PassageResult
from rag.rag_agent import Citation
from rag.session_log import Event
from rag.tutor_diagnosis import (
    Diagnosis, DiagnosisParseError, diagnose_draft, generate_hint, generate_ungrounded_hint,
    VERIFY_MODEL, generate_verification, summarize_unit, _rubric_averages_line,
    _ungrounded_fallback_line, _question_snippet, _format_event,
)


def _passage(chunk_id="a-000", file_id="a", text="text", citation="p. 1", root="/root"):
    return PassageResult(
        chunk_id=chunk_id, file_id=file_id, path=f"{file_id}.md", course="microecon",
        score=1.0, text=text, citation=citation, root=root,
    )


def _fake_client(response_text):
    client = MagicMock()
    response = MagicMock()
    response.text = response_text
    client.models.generate_content.return_value = response
    return client


_WELL_FORMED = """The attempt correctly states Axiom alpha but never checks the beta case.

CORRECTNESS: 3
RIGOR: 2
COURSE_FIT: 4
GAP_TAG: beta-case-overlooked"""


class TestDiagnoseDraftWellFormed(unittest.TestCase):
    def test_parses_text_and_rubric_scores(self):
        client = _fake_client(_WELL_FORMED)
        diagnosis = diagnose_draft("q", "reference", [_passage()], "my draft", client)
        self.assertIsInstance(diagnosis, Diagnosis)
        self.assertIn("never checks the beta case", diagnosis.text)
        self.assertNotIn("CORRECTNESS", diagnosis.text)
        self.assertEqual(diagnosis.correctness, 3)
        self.assertEqual(diagnosis.rigor, 2)
        self.assertEqual(diagnosis.course_fit, 4)
        self.assertEqual(diagnosis.gap_tag, "beta-case-overlooked")

    def test_uses_tutor_model(self):
        client = _fake_client(_WELL_FORMED)
        diagnose_draft("q", "reference", [_passage()], "my draft", client)
        from rag.rag_agent import TUTOR_MODEL
        self.assertEqual(client.models.generate_content.call_args.kwargs["model"], TUTOR_MODEL)

    def test_prompt_includes_reference_and_draft(self):
        client = _fake_client(_WELL_FORMED)
        diagnose_draft("what is X", "X is Y", [_passage()], "I think X is Z", client)
        prompt = client.models.generate_content.call_args.kwargs["contents"]
        self.assertIn("X is Y", prompt)
        self.assertIn("I think X is Z", prompt)
        self.assertIn("what is X", prompt)


class TestDiagnoseDraftMalformed(unittest.TestCase):
    def test_missing_rubric_lines_raises_instead_of_defaulting(self):
        client = _fake_client("Just some prose with no rubric lines at all.")
        with self.assertRaises(DiagnosisParseError):
            diagnose_draft("q", "reference", [_passage()], "draft", client)

    def test_partial_rubric_lines_raises(self):
        client = _fake_client("Some analysis.\n\nCORRECTNESS: 3\nRIGOR: 2")
        with self.assertRaises(DiagnosisParseError):
            diagnose_draft("q", "reference", [_passage()], "draft", client)

    def test_out_of_range_score_raises(self):
        client = _fake_client(
            "Analysis.\n\nCORRECTNESS: 9\nRIGOR: 2\nCOURSE_FIT: 4\nGAP_TAG: some-tag"
        )
        with self.assertRaises(DiagnosisParseError):
            diagnose_draft("q", "reference", [_passage()], "draft", client)


class TestDiagnoseDraftMarkdownTolerant(unittest.TestCase):
    """Regression for the final-review Important finding: gemini-3.1-flash-lite
    commonly bolds the rubric labels/values with markdown, which the original
    strict regex rejected as malformed, crashing the REPL on ordinary output."""

    def test_tolerates_markdown_bold_around_labels_and_values(self):
        client = _fake_client(
            "Analysis of the attempt.\n\n"
            "**CORRECTNESS:** 3\n"
            "**RIGOR:** 2\n"
            "**COURSE_FIT:** 4\n"
            "**GAP_TAG:** beta-case-overlooked"
        )
        diagnosis = diagnose_draft("q", "reference", [_passage()], "draft", client)
        self.assertEqual((diagnosis.correctness, diagnosis.rigor, diagnosis.course_fit), (3, 2, 4))
        self.assertEqual(diagnosis.gap_tag, "beta-case-overlooked")
        self.assertNotIn("CORRECTNESS", diagnosis.text)

    def test_tolerates_slash_five_suffix(self):
        client = _fake_client(
            "Analysis.\n\nCORRECTNESS: 3/5\nRIGOR: 2/5\nCOURSE_FIT: 4/5\nGAP_TAG: some-tag"
        )
        diagnosis = diagnose_draft("q", "reference", [_passage()], "draft", client)
        self.assertEqual((diagnosis.correctness, diagnosis.rigor, diagnosis.course_fit), (3, 2, 4))


class TestGenerateHint(unittest.TestCase):
    def test_uses_tutor_model(self):
        client = _fake_client("Think about the Projection Theorem.")
        generate_hint("q", [_passage()], client)
        from rag.rag_agent import TUTOR_MODEL
        self.assertEqual(client.models.generate_content.call_args.kwargs["model"], TUTOR_MODEL)

    def test_prompt_bars_stating_the_final_answer(self):
        client = _fake_client("hint")
        generate_hint("q", [_passage()], client)
        prompt = client.models.generate_content.call_args.kwargs["contents"]
        self.assertIn("Do NOT state the final answer", prompt)

    def test_prompt_includes_excerpts_and_question(self):
        client = _fake_client("hint")
        generate_hint("what is X", [_passage(text="excerpt content", citation="p. 9")], client)
        prompt = client.models.generate_content.call_args.kwargs["contents"]
        self.assertIn("excerpt content", prompt)
        self.assertIn("p. 9", prompt)
        self.assertIn("what is X", prompt)

    def test_returns_stripped_response_text(self):
        client = _fake_client("  a hint with whitespace  \n")
        result = generate_hint("q", [_passage()], client)
        self.assertEqual(result, "a hint with whitespace")


class TestGenerateUngroundedHint(unittest.TestCase):
    def test_uses_tutor_model(self):
        client = _fake_client("Think about the Projection Theorem.")
        generate_ungrounded_hint("q", client)
        from rag.rag_agent import TUTOR_MODEL
        self.assertEqual(client.models.generate_content.call_args.kwargs["model"], TUTOR_MODEL)

    def test_prompt_bars_stating_the_final_answer(self):
        client = _fake_client("hint")
        generate_ungrounded_hint("q", client)
        prompt = client.models.generate_content.call_args.kwargs["contents"]
        self.assertIn("Do NOT state the final answer", prompt)

    def test_prompt_includes_the_question_and_no_excerpts_block(self):
        client = _fake_client("hint")
        generate_ungrounded_hint("what is the Luce model", client)
        prompt = client.models.generate_content.call_args.kwargs["contents"]
        self.assertIn("what is the Luce model", prompt)
        self.assertNotIn("Excerpts:", prompt)

    def test_returns_stripped_response_text(self):
        client = _fake_client("  a hint with whitespace  \n")
        result = generate_ungrounded_hint("q", client)
        self.assertEqual(result, "a hint with whitespace")


class TestGenerateVerification(unittest.TestCase):
    def test_uses_verify_model_not_tutor_model(self):
        client = _fake_client("An independent solution.")
        generate_verification("q", client)
        self.assertEqual(client.models.generate_content.call_args.kwargs["model"], VERIFY_MODEL)
        from rag.rag_agent import TUTOR_MODEL
        self.assertNotEqual(VERIFY_MODEL, TUTOR_MODEL)

    def test_prompt_does_not_assume_a_prior_answer_is_correct(self):
        client = _fake_client("solution")
        generate_verification("q", client)
        prompt = client.models.generate_content.call_args.kwargs["contents"]
        self.assertIn("Do not assume any prior answer is correct", prompt)

    def test_prompt_contains_only_the_question_no_excerpts_or_prior_answer(self):
        client = _fake_client("solution")
        generate_verification("what is X", client)
        prompt = client.models.generate_content.call_args.kwargs["contents"]
        self.assertIn("what is X", prompt)
        self.assertNotIn("Excerpts", prompt)

    def test_returns_stripped_response_text(self):
        client = _fake_client("  solution text  \n")
        result = generate_verification("q", client)
        self.assertEqual(result, "solution text")


def _event(**overrides):
    defaults = dict(
        type="answer", course="microecon", unit="homework_3", question="q", text="a",
        citations=[Citation(chunk_id="c", file_id="c", path="c.md", citation="p. 1", root="/root")],
        timestamp="2026-09-27T00:00:00+00:00", gap_tag=None, correctness=None, rigor=None, course_fit=None,
    )
    defaults.update(overrides)
    return Event(**defaults)


class TestRubricAveragesLine(unittest.TestCase):
    def test_none_when_no_draft_events(self):
        events = [_event(type="answer"), _event(type="hint")]
        self.assertIsNone(_rubric_averages_line(events))

    def test_averages_only_draft_events(self):
        events = [
            _event(type="answer"),
            _event(type="draft", correctness=4, rigor=2, course_fit=5),
            _event(type="draft", correctness=2, rigor=4, course_fit=3),
        ]
        line = _rubric_averages_line(events)
        self.assertIn("Correctness 3.0/5", line)
        self.assertIn("Rigor 3.0/5", line)
        self.assertIn("Course-fit 4.0/5", line)
        self.assertIn("2 attempt", line)


class TestQuestionSnippet(unittest.TestCase):
    def test_collapses_whitespace_and_newlines(self):
        self.assertEqual(_question_snippet("## Question 4\n\nAbout random utility"),
                          "## Question 4 About random utility")

    def test_short_question_is_unchanged(self):
        self.assertEqual(_question_snippet("short"), "short")

    def test_long_question_is_truncated_with_ellipsis(self):
        result = _question_snippet("x" * 100, limit=80)
        self.assertEqual(len(result), 83)  # 80 chars + "..."
        self.assertTrue(result.endswith("..."))


class TestFormatEvent(unittest.TestCase):
    def test_ungrounded_hint_includes_a_note(self):
        formatted = _format_event(_event(type="hint", grounded=False))
        self.assertIn("no matching course material was found", formatted)

    def test_grounded_hint_has_no_note(self):
        formatted = _format_event(_event(type="hint", grounded=True))
        self.assertNotIn("no matching course material was found", formatted)

    def test_non_hint_events_never_get_the_note_even_if_ungrounded(self):
        formatted = _format_event(_event(type="answer", grounded=False))
        self.assertNotIn("no matching course material was found", formatted)


class TestUngroundedFallbackLine(unittest.TestCase):
    def test_none_when_no_hint_events(self):
        events = [_event(type="answer"), _event(type="draft", correctness=3, rigor=3, course_fit=3)]
        self.assertIsNone(_ungrounded_fallback_line(events))

    def test_reports_zero_fallbacks_when_all_hints_grounded(self):
        events = [_event(type="hint", grounded=True), _event(type="hint", grounded=True)]
        line = _ungrounded_fallback_line(events)
        self.assertIn("all 2 hint(s)", line)
        self.assertIn("grounded in your own course materials", line)

    def test_reports_count_and_question_snippets_when_some_ungrounded(self):
        events = [
            _event(type="hint", grounded=True, question="a grounded question"),
            _event(type="hint", grounded=False, question="the Luce model question"),
            _event(type="hint", grounded=False, question="the Block Marschak question"),
        ]
        line = _ungrounded_fallback_line(events)
        self.assertIn("2 of 3 hint(s)", line)
        self.assertIn("corpus gap", line)
        self.assertIn("the Luce model question", line)
        self.assertIn("the Block Marschak question", line)
        self.assertNotIn("a grounded question", line)

    def test_ignores_non_hint_events_when_counting(self):
        events = [_event(type="answer"), _event(type="hint", grounded=True)]
        line = _ungrounded_fallback_line(events)
        self.assertIn("all 1 hint(s)", line)


class TestSummarizeUnit(unittest.TestCase):
    def test_uses_tutor_model(self):
        client = _fake_client("What we learned...\n\nWhat to focus on...")
        summarize_unit([_event()], client)
        from rag.rag_agent import TUTOR_MODEL
        self.assertEqual(client.models.generate_content.call_args.kwargs["model"], TUTOR_MODEL)

    def test_prompt_includes_event_question_and_text(self):
        client = _fake_client("summary")
        summarize_unit([_event(question="what is X", text="X is Y")], client)
        prompt = client.models.generate_content.call_args.kwargs["contents"]
        self.assertIn("what is X", prompt)
        self.assertIn("X is Y", prompt)

    def test_appends_rubric_averages_when_draft_events_present(self):
        client = _fake_client("summary text")
        result = summarize_unit([_event(type="draft", correctness=5, rigor=5, course_fit=5)], client)
        self.assertIn("summary text", result)
        self.assertIn("Correctness 5.0/5", result)

    def test_no_rubric_line_when_no_draft_events(self):
        client = _fake_client("summary text")
        result = summarize_unit([_event(type="answer")], client)
        self.assertEqual(result, "summary text")

    def test_appends_grounding_line_when_hint_events_present(self):
        client = _fake_client("summary text")
        result = summarize_unit([_event(type="hint", grounded=False, question="the Luce model")], client)
        self.assertIn("summary text", result)
        self.assertIn("corpus gap", result)
        self.assertIn("the Luce model", result)

    def test_no_grounding_line_when_no_hint_events(self):
        client = _fake_client("summary text")
        result = summarize_unit([_event(type="answer")], client)
        self.assertEqual(result, "summary text")
