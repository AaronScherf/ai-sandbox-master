import unittest
from unittest.mock import MagicMock

from index_search import PassageResult
from rag_agent import Turn, Citation, AnswerResult, _diversify_by_file


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


if __name__ == "__main__":
    unittest.main()
