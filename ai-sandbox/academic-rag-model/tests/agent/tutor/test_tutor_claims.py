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


from agent.tutor.claims import (
    LEAK_RECALL, MIN_LEAK, PartClaims, parse_claims, self_test,
)

RAW = {"p1": {
    "claims": [
        {"id": "C1", "text": "a must be considered", "object_terms": ["the chosen item"],
         "recognizer": {"all": [["consider*"], ["chosen", "select*", "best"]], "window": 12}},
        {"id": "C2", "text": "independence gives a product", "object_terms": ["combining probabilities"],
         "recognizer": {"all": [["independen*"], ["multipl*", "product", "together"]], "window": 12}}],
    "routes": {"A": ["C1", "C2"]},
    "pitfalls": [{"id": "P1", "tag": "adds-independent-probabilities", "axis": "rigor", "resolved_by": "C2",
                  "recognizer": {"all": [["independen*"], ["add", "sum", "plus"]], "window": 12},
                  "repair_question": "Does combining add or multiply?"}]}}


def deepcopy_raw():
    import copy
    return copy.deepcopy(RAW)


class TestParseClaims(unittest.TestCase):
    def test_valid_claims_parse(self):
        claims, errors = parse_claims(RAW, ["p1"])
        self.assertEqual(errors, [])
        pc = claims["p1"]
        self.assertIsInstance(pc, PartClaims)
        self.assertEqual([c.id for c in pc.claims], ["C1", "C2"])
        self.assertEqual(pc.routes, {"A": ["C1", "C2"]})
        self.assertEqual(pc.pitfalls[0].resolved_by, "C2")
        self.assertIsNone(pc.final_answer)

    def test_each_defect_is_reported(self):
        def errors_for(mutate):
            raw = deepcopy_raw()
            mutate(raw["p1"])
            return "\n".join(parse_claims(raw, ["p1"])[1])
        self.assertIn("duplicate claim id", errors_for(lambda p: p["claims"][1].update(id="C1")))
        self.assertIn("routes", errors_for(lambda p: p["routes"].update(A=["C1", "C9"])))
        self.assertIn("'text'", errors_for(lambda p: p["claims"][0].update(text="")))
        self.assertIn("axis", errors_for(lambda p: p["pitfalls"][0].update(axis="style")))
        self.assertIn("resolved_by", errors_for(lambda p: p["pitfalls"][0].update(resolved_by="C9")))
        self.assertIn("repair_question", errors_for(lambda p: p["pitfalls"][0].update(repair_question="")))
        self.assertIn("recognizer", errors_for(lambda p: p["claims"][0].update(recognizer={"all": [], "window": 5})))
        self.assertIn("non-empty list", errors_for(lambda p: p.update(claims=[])))

    def test_missing_and_unknown_parts(self):
        _, errors = parse_claims(RAW, ["p1", "p2"])
        self.assertTrue(any("no entry for part p2" in e for e in errors))
        _, errors = parse_claims({**RAW, "zz": RAW["p1"]}, ["p1"])
        self.assertTrue(any("unknown part zz" in e for e in errors))
        _, errors = parse_claims([], ["p1"])
        self.assertTrue(errors)

    def test_final_answer_is_optional_and_parsed(self):
        raw = deepcopy_raw()
        raw["p1"]["final_answer"] = {"all": [["answer"]], "window": 4}
        claims, errors = parse_claims(raw, ["p1"])
        self.assertEqual(errors, [])
        self.assertTrue(claims["p1"].final_answer.matches("the answer is 3"))


PREFIXES = ["Remember that", "Keep in mind that", "It turns out that", "You should see that", "Here is the thing:"]


def good_samples():
    c1 = [f"{p} the item must be considered to be chosen" for p in PREFIXES] + \
         [f"{p} being selected requires the item enters the consideration set" for p in PREFIXES]
    c2 = [f"{p} independent events combine by multiplication" for p in PREFIXES] + \
         [f"{p} independence means the joint probability is a product" for p in PREFIXES]
    return {"p1": {
        "claims": {
            "C1": {"leak_samples": c1, "student_samples": [
                "it has to be considered and chosen", "the item must be considered then selected",
                "a needs to be considered to be the best", "it is chosen only if considered",
                "consideration comes first, then the best is selected"]},
            "C2": {"leak_samples": c2, "student_samples": [
                "since they are independent I multiply", "independence lets us take the product",
                "multiplying the independent probabilities", "the product follows from independence",
                "independent so we multiply them together"]}},
        "pitfalls": {"P1": {"student_samples": [
            "for independent events we add them", "independent so I sum the probabilities",
            "we add the independent probabilities"]}},
        "neutral_samples": ["What have you tried so far?", "Which part of the model feels least clear?",
                            "How would you say the setup in your own words?", "What does the problem ask you to show?",
                            "Which assumption have you not used yet?", "What would a simple example look like?"]}}


class TestSelfTest(unittest.TestCase):
    def setUp(self):
        self.claims, _ = parse_claims(RAW, ["p1"])

    def test_good_samples_pass(self):
        self.assertEqual(self_test(self.claims, good_samples()), [])

    def test_missing_part_and_too_few_samples_are_reported(self):
        self.assertTrue(any("no entry for p1" in e for e in self_test(self.claims, {})))
        s = good_samples()
        s["p1"]["claims"]["C1"]["leak_samples"] = s["p1"]["claims"]["C1"]["leak_samples"][:3]
        self.assertTrue(any("C1" in e and str(MIN_LEAK) in e for e in self_test(self.claims, s)))

    def test_low_leak_recall_names_the_unmatched_sample(self):
        s = good_samples()
        s["p1"]["claims"]["C1"]["leak_samples"] = [
            f"{p} the item has to enter the aware set" for p in PREFIXES] * 2   # no recognizer words
        errors = "\n".join(self_test(self.claims, s))
        self.assertIn("C1", errors)
        self.assertIn("leak", errors)
        self.assertIn("aware set", errors)
        self.assertGreater(LEAK_RECALL, 0.5)

    def test_neutral_sample_that_matches_a_recognizer_is_reported(self):
        s = good_samples()
        s["p1"]["neutral_samples"][0] = "Is the item considered and then chosen?"
        errors = "\n".join(self_test(self.claims, s))
        self.assertIn("neutral sample matches claim C1", errors)

    def test_pitfall_recall_is_checked(self):
        s = good_samples()
        s["p1"]["pitfalls"]["P1"]["student_samples"] = ["we do something else", "no idea", "unrelated words"]
        self.assertTrue(any("pitfall P1" in e for e in self_test(self.claims, s)))
