import unittest
from unittest.mock import MagicMock, patch

from indexer.index_card import GENERATION_MODEL
from indexer.index_search import PassageResult
from rag.rag_agent import (
    Turn, Citation, AnswerResult, _diversify_by_file, _reformulate_query,
    TUTOR_MODEL, _generate_answer, answer_question,
)


def _passage(chunk_id, file_id, text="text", citation="p. 1", root="/root"):
    return PassageResult(
        chunk_id=chunk_id, file_id=file_id, path=f"{file_id}.md", course="math-camp",
        score=1.0, text=text, citation=citation, root=root,
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


class TestAnswerQuestion(unittest.TestCase):
    def test_first_turn_skips_reformulation(self):
        client = _fake_generate_client("The answer.")
        passages = [_passage("aaa-000", "aaa")]
        with patch("rag.rag_agent.search_passages", return_value=passages) as mock_search:
            answer_question(["/root"], "what is X", client)
        self.assertEqual(client.models.generate_content.call_count, 1)  # only the answer call, no reformulation
        mock_search.assert_called_once_with(["/root"], "what is X", client, course=None, top_k=12)

    def test_follow_up_uses_reformulated_query_for_retrieval(self):
        client = MagicMock()
        client.models.generate_content.side_effect = [
            MagicMock(text="standalone question"), MagicMock(text="The answer."),
        ]
        passages = [_passage("aaa-000", "aaa")]
        history = [Turn(role="user", text="explain X"), Turn(role="assistant", text="X is...")]
        with patch("rag.rag_agent.search_passages", return_value=passages) as mock_search:
            answer_question(["/root"], "explain differently", client, history=history)
        mock_search.assert_called_once_with(["/root"], "standalone question", client, course=None, top_k=12)

    def test_citations_match_diversified_passages(self):
        client = _fake_generate_client("answer")
        passages = [_passage(f"aaa-{i:03d}", "aaa", text=f"text {i}", citation=f"p. {i}") for i in range(5)]
        with patch("rag.rag_agent.search_passages", return_value=passages):
            result = answer_question(["/root"], "q", client, max_per_file=2, top_k=6)
        self.assertEqual(len(result.citations), 2)  # capped by max_per_file, only one file present
        self.assertEqual(result.citations[0].chunk_id, "aaa-000")

    def test_citations_carry_the_passages_own_root_across_multiple_roots(self):
        client = _fake_generate_client("answer")
        passages = [_passage("a-000", "a", root="/root-a"), _passage("b-000", "b", root="/root-b")]
        with patch("rag.rag_agent.search_passages", return_value=passages):
            result = answer_question(["/root-a", "/root-b"], "q", client)
        self.assertEqual({c.root for c in result.citations}, {"/root-a", "/root-b"})

    def test_history_appends_new_exchange(self):
        client = _fake_generate_client("The answer.")
        with patch("rag.rag_agent.search_passages", return_value=[]):
            result = answer_question(["/root"], "what is X", client)
        self.assertEqual(result.history, [
            Turn(role="user", text="what is X"), Turn(role="assistant", text="The answer."),
        ])

    def test_history_carries_forward_prior_turns(self):
        client = MagicMock()
        client.models.generate_content.side_effect = [MagicMock(text="standalone q"), MagicMock(text="new answer")]
        prior_history = [Turn(role="user", text="q1"), Turn(role="assistant", text="a1")]
        with patch("rag.rag_agent.search_passages", return_value=[]):
            result = answer_question(["/root"], "q2", client, history=prior_history)
        self.assertEqual(len(result.history), 4)


class TestAnswerQuestionVisualize(unittest.TestCase):
    def test_visualize_false_never_calls_generate_visualization(self):
        client = _fake_generate_client("answer")
        with patch("rag.rag_agent.search_passages", return_value=[]), \
             patch("viz.viz_agent.generate_visualization") as mock_viz:
            result = answer_question(["/root"], "q", client)
        mock_viz.assert_not_called()
        self.assertIsNone(result.visualization)

    def test_visualize_true_calls_generate_visualization_with_passage_text(self):
        client = _fake_generate_client("answer")
        passages = [_passage("a-000", "a", text="eigenvalue content", root="/root")]
        fake_result = MagicMock()
        with patch("rag.rag_agent.search_passages", return_value=passages), \
             patch("viz.viz_agent.generate_visualization", return_value=fake_result) as mock_viz:
            result = answer_question(["/root"], "what is X", client, visualize=True)
        mock_viz.assert_called_once()
        args, kwargs = mock_viz.call_args
        self.assertEqual(args[0], "what is X")
        self.assertIn("eigenvalue content", kwargs["context"])
        self.assertEqual(kwargs["academic_hub_root"], "/root")
        self.assertEqual(result.visualization, fake_result)

    def test_visualize_true_passes_course_through(self):
        client = _fake_generate_client("answer")
        with patch("rag.rag_agent.search_passages", return_value=[]), \
             patch("viz.viz_agent.generate_visualization", return_value=None) as mock_viz:
            answer_question(["/root"], "q", client, course="math-camp", visualize=True)
        self.assertEqual(mock_viz.call_args.kwargs["course"], "math-camp")

    def test_visualize_true_with_no_visualization_result_is_none(self):
        client = _fake_generate_client("answer")
        with patch("rag.rag_agent.search_passages", return_value=[]), \
             patch("viz.viz_agent.generate_visualization", return_value=None):
            result = answer_question(["/root"], "q", client, visualize=True)
        self.assertIsNone(result.visualization)


if __name__ == "__main__":
    unittest.main()
