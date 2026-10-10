import unittest

from agent.tutor.claims import ClaimsError, parse_claims, parse_recognizer

TECH = {"all": [["default"], ["selected", "chosen"], ["no", "nothing"]], "window": 10}
EVERYDAY = {"all": [["only"], ["default"], ["if"]], "window": 10}
ANY = {"any_of": [TECH, EVERYDAY]}


class TestAnyOf(unittest.TestCase):
    def test_matches_when_any_option_matches(self):
        r = parse_recognizer(ANY)
        self.assertTrue(r.matches("the default is selected when no other option is considered"))
        self.assertTrue(r.matches("you only pick the default if nothing else is considered"))
        self.assertFalse(r.matches("what makes the default option special"))

    def test_masked_positions_apply_to_each_option(self):
        r = parse_recognizer(ANY)
        tokens = "only the default if".split()
        self.assertTrue(r.matches_tokens(tokens))
        self.assertFalse(r.matches_tokens(tokens, masked={0, 1, 2, 3}))

    def test_a_single_option_or_mixed_shape_is_rejected(self):
        for raw in ({"any_of": [TECH]}, {"any_of": []}, {"any_of": "x"}, {"any_of": [TECH, 3]},
                    {"any_of": [TECH, EVERYDAY], "window": 5}, {"any_of": [ANY, TECH]},
                    {"any_of": [TECH, {"all": [], "window": 5}]}):
            with self.subTest(raw=raw):
                with self.assertRaises(ClaimsError):
                    parse_recognizer(raw)

    def test_error_names_the_failing_option(self):
        with self.assertRaises(ClaimsError) as ctx:
            parse_recognizer({"any_of": [TECH, {"all": [], "window": 5}]}, "q1.claims[0].recognizer")
        self.assertIn("q1.claims[0].recognizer.any_of[1]", str(ctx.exception))

    def test_works_inside_a_claims_file(self):
        raw = {"q1": {"claims": [{"id": "C1", "text": "t", "recognizer": ANY}], "routes": {"main": ["C1"]}}}
        out, errors = parse_claims(raw, ["q1"])
        self.assertEqual(errors, [])
        self.assertTrue(out["q1"].claims[0].recognizer.matches("only the default if"))


if __name__ == "__main__":
    unittest.main()
