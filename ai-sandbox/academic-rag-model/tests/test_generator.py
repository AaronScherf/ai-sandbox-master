import unittest
from unittest.mock import MagicMock, patch

from indexer.index_search import PassageResult
from problem_gen.generator import GeneratedProblem, ProblemSource, _match_known_course, generate_problem


def _passage(chunk_id, file_id, text="text", citation="Problem 1", root="/root"):
    return PassageResult(
        chunk_id=chunk_id, file_id=file_id, path=f"{file_id}.md", course="math-camp",
        score=1.0, text=text, citation=citation, root=root,
    )


class TestMatchKnownCourse(unittest.TestCase):
    def test_matches_a_plainly_named_course(self):
        with patch("problem_gen.generator.load_courses", return_value={"microeconomics": {}}):
            result = _match_known_course("generate a problem for my microeconomics course", ["/root"])
        self.assertEqual(result, "microeconomics")

    def test_matches_hyphen_space_variant(self):
        with patch("problem_gen.generator.load_courses", return_value={"math-camp": {}}):
            result = _match_known_course("give me a problem from math camp", ["/root"])
        self.assertEqual(result, "math-camp")

    def test_no_known_course_mentioned_returns_none(self):
        with patch("problem_gen.generator.load_courses", return_value={"microeconomics": {}}):
            result = _match_known_course("give me a problem on derivatives", ["/root"])
        self.assertIsNone(result)

    def test_checks_every_given_root(self):
        def fake_load_courses(root):
            return {"a-course": {}} if root == "/root-a" else {"b-course": {}}
        with patch("problem_gen.generator.load_courses", side_effect=fake_load_courses):
            result = _match_known_course("a problem for b-course", ["/root-a", "/root-b"])
        self.assertEqual(result, "b-course")


class TestGenerateProblem(unittest.TestCase):
    def test_empty_style_pool_returns_none_without_generating(self):
        client = MagicMock()
        with patch("problem_gen.generator.search_passages", return_value=[]) as mock_search, \
             patch("problem_gen.generator.generate_and_verify") as mock_generate:
            result = generate_problem("q", ["/root"], client, course="math-camp")
        self.assertIsNone(result)
        mock_generate.assert_not_called()
        mock_search.assert_called_once_with(
            ["/root"], "q", client, course="math-camp", doc_type="problem_set", top_k=3,
        )

    def test_requests_problem_set_doc_type_for_style_pool(self):
        style = [_passage("s-000", "s")]
        with patch("problem_gen.generator.search_passages", side_effect=[style, []]) as mock_search, \
             patch("problem_gen.generator.generate_and_verify", return_value=("P", "S")):
            generate_problem("q", ["/root"], MagicMock(), course="math-camp")
        self.assertEqual(mock_search.call_args_list[0].kwargs["doc_type"], "problem_set")

    def test_requests_textbook_doc_type_for_content_pool(self):
        style = [_passage("s-000", "s")]
        with patch("problem_gen.generator.search_passages", side_effect=[style, []]) as mock_search, \
             patch("problem_gen.generator.generate_and_verify", return_value=("P", "S")):
            generate_problem("q", ["/root"], MagicMock(), course="math-camp")
        self.assertEqual(mock_search.call_args_list[1].kwargs["doc_type"], "textbook")

    def test_content_pool_empty_still_generates(self):
        style = [_passage("s-000", "s")]
        with patch("problem_gen.generator.search_passages", side_effect=[style, []]), \
             patch("problem_gen.generator.generate_and_verify", return_value=("P", "S")) as mock_generate:
            result = generate_problem("q", ["/root"], MagicMock(), course="math-camp")
        self.assertIsNotNone(result)
        mock_generate.assert_called_once_with("q", ["text"], [])

    def test_sources_tagged_by_role(self):
        style = [_passage("s-000", "s", text="style text")]
        content = [_passage("c-000", "c", text="content text")]
        with patch("problem_gen.generator.search_passages", side_effect=[style, content]), \
             patch("problem_gen.generator.generate_and_verify", return_value=("P", "S")):
            result = generate_problem("q", ["/root"], MagicMock(), course="math-camp")
        roles_by_chunk = {s.chunk_id: s.role for s in result.sources}
        self.assertEqual(roles_by_chunk, {"s-000": "style", "c-000": "content"})

    def test_generation_failure_returns_none(self):
        style = [_passage("s-000", "s")]
        with patch("problem_gen.generator.search_passages", side_effect=[style, []]), \
             patch("problem_gen.generator.generate_and_verify", return_value=None):
            result = generate_problem("q", ["/root"], MagicMock(), course="math-camp")
        self.assertIsNone(result)

    def test_explicit_course_skips_known_course_matching(self):
        with patch("problem_gen.generator._match_known_course") as mock_match, \
             patch("problem_gen.generator.search_passages", return_value=[]):
            generate_problem("q for microeconomics", ["/root"], MagicMock(), course="math-camp")
        mock_match.assert_not_called()

    def test_course_none_uses_known_course_matching(self):
        with patch("problem_gen.generator._match_known_course", return_value="microeconomics") as mock_match, \
             patch("problem_gen.generator.search_passages", return_value=[]) as mock_search:
            generate_problem("q", ["/root"], MagicMock())
        mock_match.assert_called_once()
        self.assertEqual(mock_search.call_args_list[0].kwargs["course"], "microeconomics")


if __name__ == "__main__":
    unittest.main()
