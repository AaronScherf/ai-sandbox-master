import unittest
from unittest.mock import MagicMock

from journal_discovery.discovery import Work
from journal_discovery.relevance import (
    ScoredWork,
    cosine_similarity,
    embed_text,
    score_work,
    select_relevant_works,
)


def _work(idx, abstract="a real abstract", title=None):
    return Work(
        openalex_id=f"W{idx}", doi=f"10.1/{idx}", title=title or f"Paper {idx}", authors=[],
        year=2024, abstract=abstract,
    )


class TestCosineSimilarity(unittest.TestCase):
    def test_identical_vectors_score_one(self):
        self.assertAlmostEqual(cosine_similarity([1.0, 0.0], [1.0, 0.0]), 1.0)

    def test_orthogonal_vectors_score_zero(self):
        self.assertAlmostEqual(cosine_similarity([1.0, 0.0], [0.0, 1.0]), 0.0)


class TestEmbedText(unittest.TestCase):
    def test_normalizes_and_converts_to_list(self):
        model = MagicMock()
        encoded = MagicMock()
        encoded.tolist.return_value = [0.1, 0.2, 0.3]
        model.encode.return_value = encoded

        result = embed_text(model, "some text")

        model.encode.assert_called_once_with("some text", normalize_embeddings=True)
        self.assertEqual(result, [0.1, 0.2, 0.3])


class TestScoreWork(unittest.TestCase):
    def test_none_when_no_abstract(self):
        model = MagicMock()
        work = _work(1, abstract=None)
        self.assertIsNone(score_work(model, [1.0, 0.0], work))

    def test_scores_via_cosine_similarity(self):
        model = MagicMock()
        encoded = MagicMock()
        encoded.tolist.return_value = [1.0, 0.0]
        model.encode.return_value = encoded
        work = _work(1, abstract="matches the prompt")

        score = score_work(model, [1.0, 0.0], work)

        self.assertAlmostEqual(score, 1.0)


class TestSelectRelevantWorks(unittest.TestCase):
    def _model_scoring(self, scores_by_abstract):
        model = MagicMock()

        def encode(text, normalize_embeddings=True):
            encoded = MagicMock()
            encoded.tolist.return_value = scores_by_abstract.get(text, [0.0, 0.0])
            return encoded

        model.encode.side_effect = encode
        return model

    def test_drops_below_threshold(self):
        model = self._model_scoring({
            "prompt": [1.0, 0.0],
            "on topic": [1.0, 0.0],
            "off topic": [0.0, 1.0],
        })
        works = [_work(1, "on topic"), _work(2, "off topic")]

        selected = select_relevant_works(
            works, model, "prompt", threshold=0.5, max_results=10, max_examined=10,
        )

        self.assertEqual([sw.work.openalex_id for sw in selected], ["W1"])

    def test_stops_at_max_results(self):
        model = self._model_scoring({"prompt": [1.0, 0.0], "on topic": [1.0, 0.0]})
        works = [_work(i, "on topic") for i in range(5)]

        selected = select_relevant_works(
            works, model, "prompt", threshold=0.5, max_results=2, max_examined=10,
        )

        self.assertEqual(len(selected), 2)

    def test_stops_at_max_examined_even_if_under_max_results(self):
        model = self._model_scoring({"prompt": [1.0, 0.0], "on topic": [1.0, 0.0]})
        works = [_work(i, "on topic") for i in range(5)]

        selected = select_relevant_works(
            works, model, "prompt", threshold=0.5, max_results=100, max_examined=3,
        )

        self.assertEqual(len(selected), 3)

    def test_no_abstract_candidates_only_fill_remaining_slots(self):
        model = self._model_scoring({"prompt": [1.0, 0.0], "on topic": [1.0, 0.0]})
        works = [_work(1, "on topic"), _work(2, None), _work(3, None)]

        selected = select_relevant_works(
            works, model, "prompt", threshold=0.5, max_results=2, max_examined=10,
        )

        self.assertEqual(len(selected), 2)
        self.assertEqual(selected[0].work.openalex_id, "W1")
        self.assertEqual(selected[0].score, 1.0)
        self.assertEqual(selected[1].work.openalex_id, "W2")
        self.assertIsNone(selected[1].score)

    def test_no_abstract_candidates_excluded_when_no_room(self):
        model = self._model_scoring({"prompt": [1.0, 0.0], "on topic": [1.0, 0.0]})
        works = [_work(i, "on topic") for i in range(2)] + [_work(9, None)]

        selected = select_relevant_works(
            works, model, "prompt", threshold=0.5, max_results=2, max_examined=10,
        )

        self.assertEqual(len(selected), 2)
        self.assertTrue(all(sw.score is not None for sw in selected))

    def test_exact_duplicate_title_skipped(self):
        # Confirmed real 2026-09-02: the same paper legitimately shows up
        # under different DOIs (an SSRN working-paper revision vs. its
        # published version) -- only the first-encountered copy should
        # ever reach selection, so the resulting worklist never shows the
        # same paper twice.
        model = self._model_scoring({"prompt": [1.0, 0.0], "on topic": [1.0, 0.0]})
        works = [
            _work(1, "on topic", title="Causal Inference from Hypothetical Evaluations"),
            _work(2, "on topic", title="Causal Inference From Hypothetical Evaluations!"),
        ]

        selected = select_relevant_works(
            works, model, "prompt", threshold=0.5, max_results=10, max_examined=10,
        )

        self.assertEqual([sw.work.openalex_id for sw in selected], ["W1"])

    def test_distinct_titles_both_kept(self):
        model = self._model_scoring({"prompt": [1.0, 0.0], "on topic": [1.0, 0.0]})
        works = [
            _work(1, "on topic", title="Paper One"),
            _work(2, "on topic", title="Paper Two"),
        ]

        selected = select_relevant_works(
            works, model, "prompt", threshold=0.5, max_results=10, max_examined=10,
        )

        self.assertEqual([sw.work.openalex_id for sw in selected], ["W1", "W2"])

    def test_duplicate_title_among_unscored_also_skipped(self):
        model = self._model_scoring({"prompt": [1.0, 0.0]})
        works = [
            _work(1, None, title="Same Title"),
            _work(2, None, title="same title"),
        ]

        selected = select_relevant_works(
            works, model, "prompt", threshold=0.5, max_results=10, max_examined=10,
        )

        self.assertEqual([sw.work.openalex_id for sw in selected], ["W1"])


if __name__ == "__main__":
    unittest.main()
