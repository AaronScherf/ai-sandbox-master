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
    def test_falls_back_to_title_when_no_abstract(self):
        # Confirmed real 2026-09-02: closed-access Elsevier articles often
        # have no abstract_inverted_index in OpenAlex at all (a publisher
        # licensing gap, not a parsing bug) -- scoring the title instead
        # of treating the candidate as unscorable gives an actual signal.
        model = MagicMock()
        encoded = MagicMock()
        encoded.tolist.return_value = [1.0, 0.0]
        model.encode.return_value = encoded
        work = _work(1, abstract=None, title="A Relevant Title")

        score, scored_from = score_work(model, [1.0, 0.0], work)

        model.encode.assert_called_once_with("A Relevant Title", normalize_embeddings=True)
        self.assertAlmostEqual(score, 1.0)
        self.assertEqual(scored_from, "title")

    def test_scores_via_cosine_similarity(self):
        model = MagicMock()
        encoded = MagicMock()
        encoded.tolist.return_value = [1.0, 0.0]
        model.encode.return_value = encoded
        work = _work(1, abstract="matches the prompt")

        score, scored_from = score_work(model, [1.0, 0.0], work)

        self.assertAlmostEqual(score, 1.0)
        self.assertEqual(scored_from, "abstract")


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

    def test_no_abstract_candidate_scored_by_title_and_kept_if_relevant(self):
        # Confirmed real 2026-09-02: a no-abstract candidate is no longer
        # an automatic filler -- it's scored against its own title text,
        # same threshold as everything else, and flagged scored_from="title"
        # so downstream code (the worklist) can show it's a weaker signal.
        model = self._model_scoring({"prompt": [1.0, 0.0], "on topic": [1.0, 0.0]})
        works = [_work(1, "on topic"), _work(2, None, title="on topic")]

        selected = select_relevant_works(
            works, model, "prompt", threshold=0.5, max_results=10, max_examined=10,
        )

        self.assertEqual([sw.work.openalex_id for sw in selected], ["W1", "W2"])
        self.assertEqual(selected[1].scored_from, "title")

    def test_no_abstract_candidate_dropped_when_title_is_off_topic(self):
        model = self._model_scoring({
            "prompt": [1.0, 0.0], "on topic": [1.0, 0.0], "off topic": [0.0, 1.0],
        })
        works = [_work(1, "on topic"), _work(2, None, title="off topic")]

        selected = select_relevant_works(
            works, model, "prompt", threshold=0.5, max_results=10, max_examined=10,
        )

        self.assertEqual([sw.work.openalex_id for sw in selected], ["W1"])

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

    def test_duplicate_title_deduped_even_when_scored_from_title(self):
        model = self._model_scoring({"prompt": [1.0, 0.0], "on topic": [1.0, 0.0]})
        works = [
            _work(1, None, title="on topic"),
            _work(2, None, title="On Topic"),
        ]

        selected = select_relevant_works(
            works, model, "prompt", threshold=0.5, max_results=10, max_examined=10,
        )

        self.assertEqual([sw.work.openalex_id for sw in selected], ["W1"])


if __name__ == "__main__":
    unittest.main()
