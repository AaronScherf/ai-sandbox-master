import json
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from viz.example_store import (
    EXAMPLE_SIMILARITY_THRESHOLD, MAX_EXAMPLES, ExampleRecord, _cosine_similarity,
    _derive_keywords, _embed, _load, _store_path, _write, find_examples,
)


class TestDeriveKeywords(unittest.TestCase):
    def test_drops_short_words_and_stopwords(self):
        result = _derive_keywords("The eigenvectors and eigenvalues of a symmetric matrix")
        self.assertEqual(result, {"eigenvectors", "eigenvalues", "symmetric", "matrix"})

    def test_lowercases_and_splits_on_non_alphanumeric(self):
        result = _derive_keywords("Gradient-Descent: Convergence!")
        self.assertEqual(result, {"gradient", "descent", "convergence"})

    def test_empty_text_returns_empty_set(self):
        self.assertEqual(_derive_keywords(""), set())


class TestCosineSimilarity(unittest.TestCase):
    def test_identical_vectors_similarity_is_one(self):
        self.assertAlmostEqual(_cosine_similarity([1.0, 0.0], [1.0, 0.0]), 1.0)

    def test_orthogonal_vectors_similarity_is_zero(self):
        self.assertAlmostEqual(_cosine_similarity([1.0, 0.0], [0.0, 1.0]), 0.0)

    def test_empty_vector_returns_zero(self):
        self.assertEqual(_cosine_similarity([], [1.0, 0.0]), 0.0)

    def test_mismatched_length_returns_zero(self):
        self.assertEqual(_cosine_similarity([1.0], [1.0, 0.0]), 0.0)


class TestEmbed(unittest.TestCase):
    @patch("viz.example_store.urllib.request.urlopen")
    def test_returns_embedding_on_success(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"embedding": [0.1, 0.2, 0.3]}).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response
        result = _embed("eigenvalues")
        self.assertEqual(result, [0.1, 0.2, 0.3])

    @patch("viz.example_store.urllib.request.urlopen", side_effect=OSError("connection refused"))
    def test_returns_none_on_connection_failure(self, mock_urlopen):
        self.assertIsNone(_embed("eigenvalues"))


class TestLoadWriteRoundTrip(unittest.TestCase):
    def test_write_then_load_round_trip(self):
        with tempfile.TemporaryDirectory() as store_dir:
            record = ExampleRecord(
                concept="spectral decomposition", context="some passage text",
                keywords=["spectral", "decomposition"], embedding=[0.1, 0.2],
                script="fig = go.Figure()", created_at="2026-09-03T00:00:00+00:00",
            )
            _write(store_dir, [record])
            loaded = _load(store_dir)
            self.assertEqual(loaded, [record])

    def test_load_missing_file_returns_empty_list(self):
        with tempfile.TemporaryDirectory() as store_dir:
            self.assertEqual(_load(store_dir), [])

    def test_load_corrupt_file_returns_empty_list(self):
        with tempfile.TemporaryDirectory() as store_dir:
            path = _store_path(store_dir)
            with open(path, "w", encoding="utf-8") as f:
                f.write("not valid json{{{")
            self.assertEqual(_load(store_dir), [])

    def test_write_creates_store_dir_if_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            store_dir = os.path.join(tmp, "nested", ".examples")
            record = ExampleRecord(
                concept="c", context="", keywords=[], embedding=[0.1],
                script="fig = go.Figure()", created_at="2026-09-03T00:00:00+00:00",
            )
            _write(store_dir, [record])
            self.assertTrue(os.path.exists(_store_path(store_dir)))


def _record(concept, keywords, embedding, script="fig = go.Figure()"):
    return ExampleRecord(
        concept=concept, context="", keywords=keywords, embedding=embedding,
        script=script, created_at="2026-09-03T00:00:00+00:00",
    )


class TestFindExamples(unittest.TestCase):
    def test_empty_store_returns_empty_list(self):
        with tempfile.TemporaryDirectory() as store_dir:
            self.assertEqual(find_examples("eigenvalues", "", store_dir), [])

    @patch("viz.example_store._embed")
    def test_returns_matches_above_threshold_highest_first(self, mock_embed):
        with tempfile.TemporaryDirectory() as store_dir:
            best_match = _record("eigenvectors basics", ["eigenvectors"], [1.0, 0.0])
            second_match = _record("spectral decomposition", ["spectral", "decomposition"], [0.99, 0.01])
            below_threshold = _record("gradient descent", ["gradient", "descent"], [0.0, 1.0])
            _write(store_dir, [second_match, best_match, below_threshold])
            mock_embed.return_value = [1.0, 0.0]
            result = find_examples("eigenvalues", "", store_dir)
            self.assertEqual(result, [best_match, second_match])

    @patch("viz.example_store._embed")
    def test_falls_back_to_keywords_when_nothing_above_threshold(self, mock_embed):
        with tempfile.TemporaryDirectory() as store_dir:
            record = _record("gradient descent optimization", ["gradient", "descent", "optimization"], [0.0, 1.0])
            _write(store_dir, [record])
            mock_embed.return_value = [1.0, 0.0]  # orthogonal -- similarity 0.0, below threshold
            result = find_examples("gradient descent for neural networks", "", store_dir)
            self.assertEqual(result, [record])

    @patch("viz.example_store._embed")
    def test_returns_empty_when_neither_embedding_nor_keywords_match(self, mock_embed):
        with tempfile.TemporaryDirectory() as store_dir:
            record = _record("gradient descent", ["gradient", "descent"], [0.0, 1.0])
            _write(store_dir, [record])
            mock_embed.return_value = [1.0, 0.0]
            result = find_examples("totally unrelated topic", "", store_dir)
            self.assertEqual(result, [])

    @patch("viz.example_store._embed", return_value=None)
    def test_embedding_failure_falls_back_to_keywords(self, mock_embed):
        with tempfile.TemporaryDirectory() as store_dir:
            record = _record("gradient descent", ["gradient", "descent"], [0.0, 1.0])
            _write(store_dir, [record])
            result = find_examples("gradient descent basics", "", store_dir)
            self.assertEqual(result, [record])

    @patch("viz.example_store._embed", return_value=None)
    def test_embedding_and_keyword_both_fail_returns_empty(self, mock_embed):
        with tempfile.TemporaryDirectory() as store_dir:
            record = _record("gradient descent", ["gradient", "descent"], [0.0, 1.0])
            _write(store_dir, [record])
            result = find_examples("totally unrelated", "", store_dir)
            self.assertEqual(result, [])

    def test_caps_at_max_examples(self):
        with tempfile.TemporaryDirectory() as store_dir:
            records = [_record(f"concept {i}", ["shared"], [1.0, 0.0]) for i in range(5)]
            _write(store_dir, records)
            with patch("viz.example_store._embed", return_value=[1.0, 0.0]):
                result = find_examples("shared topic", "", store_dir)
            self.assertEqual(len(result), MAX_EXAMPLES)

    def test_keyword_fallback_ties_broken_by_insertion_order(self):
        with tempfile.TemporaryDirectory() as store_dir:
            first = _record("first concept", ["shared", "gradient"], [0.0, 1.0])
            second = _record("second concept", ["shared", "gradient"], [0.0, 1.0])
            third = _record("third concept", ["shared"], [0.0, 1.0])
            _write(store_dir, [first, second, third])
            with patch("viz.example_store._embed", return_value=None):
                result = find_examples("shared gradient topic", "", store_dir)
            # first and second both overlap on {"shared", "gradient"} (2 words, tied) --
            # insertion order breaks the tie, so first comes before second; third
            # overlaps on only {"shared"} (1 word) and loses to both on overlap count.
            self.assertEqual(result, [first, second])


if __name__ == "__main__":
    unittest.main()
