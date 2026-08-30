import unittest
from unittest.mock import MagicMock

from index_card import GENERATION_MODEL
from index_search import PassageResult
from rag_agent import (
    Turn, Citation, AnswerResult, _diversify_by_file, _reformulate_query,
    TUTOR_MODEL, _generate_answer,
)


def _passage(chunk_id, file_id, text="text", citation="p. 1"):
    return PassageResult(
        chunk_id=chunk_id, file_id=file_id, path=f"{file_id}.md", course="math-camp",
        score=1.0, text=text, citation=citation,
    )


class TestDiversifyByFile(unittest.TestCase):
    def test_caps_results_per_file(self):
        results = [_passage(f"a-{i}", "a") for i in range(5)]
        kept = _diversify_by_file(results, max_per_file=2)
        self.assertEqual(len(kept), 2)

    def test_preserves_relevance_order(self):
        results = [_passage("a-0", "a"), _passage("b-0", "b"), _passage("a-1", "a")]
        kept = _diversify_by_file(results, max_per_file=1)
        self.assertEqual([r.chunk_id for r in kept], ["a-0", "b-0"])

    def test_under_the_cap_is_unaffected(self):
        results = [_passage("a-0", "a"), _passage("b-0", "b")]
        kept = _diversify_by_file(results, max_per_file=3)
        self.assertEqual(kept, results)

    def test_empty_input_returns_empty(self):
        self.assertEqual(_diversify_by_file([], max_per_file=3), [])


def _fake_generate_client(response_text):
    client = MagicMock()
    response = MagicMock()
    response.text = response_text
    client.models.generate_content.return_value = response
    return client


class TestReformulateQuery(unittest.TestCase):
    def test_uses_generation_model(self):
        client = _fake_generate_client("What is the spectral theorem proof?")
        history = [Turn(role="user", text="Explain the spectral theorem"),
                   Turn(role="assistant", text="It states that...")]
        result = _reformulate_query("explain the proof differently", history, client)
        self.assertEqual(result, "What is the spectral theorem proof?")
        self.assertEqual(client.models.generate_content.call_args.kwargs["model"], GENERATION_MODEL)

    def test_includes_recent_history_in_prompt(self):
        client = _fake_generate_client("standalone question")
        history = [Turn(role="user", text="Explain eigenvalues"), Turn(role="assistant", text="An eigenvalue is...")]
        _reformulate_query("what about eigenvectors", history, client)
        prompt = client.models.generate_content.call_args.kwargs["contents"]
        self.assertIn("Explain eigenvalues", prompt)
        self.assertIn("An eigenvalue is...", prompt)
        self.assertIn("what about eigenvectors", prompt)

    def test_falls_back_to_original_question_on_empty_response(self):
        client = _fake_generate_client("")
        result = _reformulate_query("explain that again", [Turn(role="user", text="x")], client)
        self.assertEqual(result, "explain that again")


class TestGenerateAnswer(unittest.TestCase):
    def test_uses_tutor_model(self):
        client = _fake_generate_client("The spectral theorem states...")
        passages = [_passage("aaa-000", "aaa", text="Content about eigenvalues.", citation="§3.7, p. 44")]
        answer = _generate_answer("what is the spectral theorem", [], passages, client)
        self.assertEqual(answer, "The spectral theorem states...")
        self.assertEqual(client.models.generate_content.call_args.kwargs["model"], TUTOR_MODEL)

    def test_includes_excerpt_text_and_citation_in_prompt(self):
        client = _fake_generate_client("answer")
        passages = [_passage("aaa-000", "aaa", text="Content about eigenvalues.", citation="§3.7, p. 44")]
        _generate_answer("q", [], passages, client)
        prompt = client.models.generate_content.call_args.kwargs["contents"]
        self.assertIn("Content about eigenvalues.", prompt)
        self.assertIn("§3.7, p. 44", prompt)

    def test_no_history_block_on_first_turn(self):
        client = _fake_generate_client("answer")
        _generate_answer("q", [], [], client)
        prompt = client.models.generate_content.call_args.kwargs["contents"]
        self.assertNotIn("Recent conversation", prompt)

    def test_includes_history_block_on_follow_up(self):
        client = _fake_generate_client("answer")
        history = [Turn(role="user", text="Explain eigenvalues"), Turn(role="assistant", text="An eigenvalue is...")]
        _generate_answer("q", history, [], client)
        prompt = client.models.generate_content.call_args.kwargs["contents"]
        self.assertIn("Recent conversation", prompt)
        self.assertIn("Explain eigenvalues", prompt)


if __name__ == "__main__":
    unittest.main()
