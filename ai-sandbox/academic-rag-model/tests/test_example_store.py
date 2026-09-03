import unittest

from viz.example_store import _cosine_similarity, _derive_keywords


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


if __name__ == "__main__":
    unittest.main()
