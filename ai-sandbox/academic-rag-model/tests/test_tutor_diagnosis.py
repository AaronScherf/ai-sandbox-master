import unittest
from unittest.mock import MagicMock

from indexer.index_search import PassageResult
from rag.tutor_diagnosis import Diagnosis, DiagnosisParseError, diagnose_draft, generate_hint


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
