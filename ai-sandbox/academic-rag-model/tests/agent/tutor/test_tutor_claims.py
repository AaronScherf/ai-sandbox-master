# tests/agent/tutor/test_tutor_claims.py
import unittest

from agent.tutor.claims import ClaimsError, parse_recognizer, tokenize


class TestTokenize(unittest.TestCase):
    def test_lowercases_and_drops_punctuation_and_math_symbols(self):
        self.assertEqual(tokenize("Let γ(b) ≻ a, then p(a, A)!"),
                         ["let", "γ", "b", "a", "then", "p", "a", "a"])

    def test_contractions_become_negation(self):
        self.assertEqual(tokenize("It wouldn't work, can't stop"), ["it", "would", "not", "work", "ca", "not", "stop"])
        self.assertEqual(tokenize("isn’t"), ["is", "not"])  # curly apostrophe

    def test_latex_and_empty_input_do_not_crash(self):
        self.assertEqual(tokenize("$x \\succeq y$"), ["x", "succeq", "y"])
        self.assertEqual(tokenize(""), [])
        self.assertEqual(tokenize("   ...  "), [])


def rec(groups, window=8):
    return parse_recognizer({"all": groups, "window": window})


class TestRecognizerMatching(unittest.TestCase):
    def test_every_group_must_be_present(self):
        r = rec([["consider*"], ["chosen", "best"]])
        self.assertTrue(r.matches("a must be considered to be chosen"))
        self.assertFalse(r.matches("a must be chosen"))
        self.assertFalse(r.matches("a must be considered"))

    def test_prefix_entries_and_case(self):
        r = rec([["consider*"], ["chosen", "best"]])
        self.assertTrue(r.matches("Consideration comes first and then the BEST item"))

    def test_plain_entries_match_whole_tokens_only(self):
        r = rec([["not"], ["consider*"]])
        self.assertFalse(r.matches("notice the considered item"))   # 'notice' is not 'not'
        self.assertTrue(r.matches("it is not considered"))
        self.assertTrue(r.matches("it isn't considered"))           # n't -> not

    def test_window_limits_the_distance(self):
        r = rec([["alpha"], ["omega"]], window=3)
        self.assertTrue(r.matches("alpha x omega"))
        self.assertFalse(r.matches("alpha x y omega"))

    def test_one_token_can_satisfy_two_groups(self):
        r = rec([["unconsidered"], ["unconsidered", "ignored"]])
        self.assertTrue(r.matches("the item stays unconsidered"))

    def test_empty_text_never_matches(self):
        self.assertFalse(rec([["a"]]).matches(""))


class TestParseRecognizer(unittest.TestCase):
    def test_rejects_bad_shapes(self):
        bad = [
            None, [], {"all": [["a"]]}, {"window": 5}, {"all": [], "window": 5},
            {"all": [[]], "window": 5}, {"all": [["a"]], "window": 1}, {"all": [["a"]], "window": True},
            {"all": [["a", 3]], "window": 5}, {"all": [["a"]], "window": 5, "extra": 1}, {"all": ["a"], "window": 5},
        ]
        for raw in bad:
            with self.subTest(raw=raw):
                with self.assertRaises(ClaimsError):
                    parse_recognizer(raw)

    def test_error_names_where(self):
        with self.assertRaises(ClaimsError) as ctx:
            parse_recognizer({"all": [], "window": 5}, "q1.claims[0].recognizer")
        self.assertIn("q1.claims[0].recognizer", str(ctx.exception))

    def test_entries_are_lowercased_and_stripped(self):
        r = parse_recognizer({"all": [[" Consider* "]], "window": 4})
        self.assertEqual(r.groups, (("consider*",),))
