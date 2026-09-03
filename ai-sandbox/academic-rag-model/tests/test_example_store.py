import json
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from viz.example_store import ExampleRecord, _cosine_similarity, _derive_keywords, _embed, _load, _store_path, _write


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


if __name__ == "__main__":
    unittest.main()
