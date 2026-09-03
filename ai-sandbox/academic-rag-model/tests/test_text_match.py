import unittest

from journal_discovery.text_match import normalize


class TestNormalize(unittest.TestCase):
    def test_lowercases(self):
        self.assertEqual(normalize("Causal Inference"), "causalinference")

    def test_strips_punctuation_and_whitespace(self):
        self.assertEqual(normalize("Causal Inference, from Hypothetical-Evaluations!!"),
                          "causalinferencefromhypotheticalevaluations")

    def test_empty_string(self):
        self.assertEqual(normalize(""), "")


if __name__ == "__main__":
    unittest.main()
