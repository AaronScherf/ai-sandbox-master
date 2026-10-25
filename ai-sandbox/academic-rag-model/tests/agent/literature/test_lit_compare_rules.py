import unittest

from agent.literature.compare import agreed_facts, diff_records
from agent.literature.vocab import Term, Vocabulary
from lit_helpers import VOCABS, good


def _record(result):
    return {"core": result["core"], "appraisal": result["appraisal"], "identity": {"file_id": "x"}}


def _vocabs():
    t = {
        "intervention.transfers": Term(id="intervention.transfers", label="Transfers"),
        "intervention.cash_transfer": Term(id="intervention.cash_transfer", label="Cash transfer",
                                           parent="intervention.transfers"),
        "intervention.voucher": Term(id="intervention.voucher", label="Voucher"),
    }
    return dict(VOCABS, intervention=Vocabulary("intervention", 1, "3ie", "test", t))


def _with(facet, facts):
    r = good()
    r["core"][facet] = facts
    return _record(r)


def _p(value):
    return {"value": value, "proposed": True, "quote": "some supporting words", "locator": 1}


class TestRules(unittest.TestCase):
    def test_a_parent_and_its_child_agree(self):
        a = _with("intervention", [{"value": "x", "vocab_id": "intervention.transfers", "quote": "q" * 10, "locator": 1}])
        b = _with("intervention", [{"value": "x", "vocab_id": "intervention.cash_transfer", "quote": "q" * 10, "locator": 1}])
        self.assertEqual([m for m in diff_records(a, b, _vocabs()) if "intervention" in m], [])

    def test_unrelated_terms_still_disagree(self):
        a = _with("intervention", [{"value": "x", "vocab_id": "intervention.voucher", "quote": "q" * 10, "locator": 1}])
        b = _with("intervention", [{"value": "x", "vocab_id": "intervention.cash_transfer", "quote": "q" * 10, "locator": 1}])
        self.assertEqual(len([m for m in diff_records(a, b, _vocabs()) if "intervention" in m]), 1)

    def test_proposed_values_that_contain_one_another_agree(self):
        a, b = _with("outcome", [_p("subjective wellbeing")]), _with("outcome", [_p("Wellbeing")])
        self.assertEqual([m for m in diff_records(a, b) if "core.outcome" in m], [])
        c = _with("outcome", [_p("net welfare")])
        self.assertEqual(len([m for m in diff_records(a, c) if "core.outcome" in m]), 1)

    def test_general_population_is_ignored_but_other_populations_count(self):
        gen = {"value": "everyone", "vocab_id": "population.general_population", "quote": "q" * 10, "locator": 1}
        hh = {"value": "households", "vocab_id": "population.households", "quote": "q" * 10, "locator": 1}
        v = dict(VOCABS)
        self.assertEqual(diff_records(_with("population", [gen]), _with("population", []), v), [])
        self.assertEqual(len(diff_records(_with("population", [gen]), _with("population", [hh]), v)), 1)


class TestAgreedFactsPrefersTheFinerTerm(unittest.TestCase):
    """When a parent/child pair closes diff_records' disagreement, agreed_facts used to always keep pass a's own
    copy -- even when pass b found the more specific child. That silently threw away grain the second pass
    contributed (e.g. a paper always showing the broad parent bucket in the matrix, never the child a human
    reviewer would want). It should show whichever side is the more specific (descendant) term instead."""

    def test_pass_b_s_more_specific_child_wins_over_pass_a_s_parent(self):
        a = _with("intervention", [{"value": "transfers", "vocab_id": "intervention.transfers",
                                     "quote": "q" * 10, "locator": 1}])
        b = _with("intervention", [{"value": "cash", "vocab_id": "intervention.cash_transfer",
                                     "quote": "w" * 10, "locator": 2}])
        agreed = agreed_facts(a, b, _vocabs())
        item = next(i for i in agreed if i["facet"] == "intervention")
        self.assertEqual(item["shown"], "intervention.cash_transfer")
        self.assertEqual(item["label"], "Cash transfer")
        self.assertEqual(item["quote"], "w" * 10)

    def test_pass_a_s_more_specific_child_is_kept_as_before(self):
        a = _with("intervention", [{"value": "cash", "vocab_id": "intervention.cash_transfer",
                                     "quote": "q" * 10, "locator": 1}])
        b = _with("intervention", [{"value": "transfers", "vocab_id": "intervention.transfers",
                                     "quote": "w" * 10, "locator": 2}])
        agreed = agreed_facts(a, b, _vocabs())
        item = next(i for i in agreed if i["facet"] == "intervention")
        self.assertEqual(item["shown"], "intervention.cash_transfer")
        self.assertEqual(item["quote"], "q" * 10)

    def test_two_proposed_values_that_merely_overlap_in_words_keep_pass_a_as_before(self):
        a, b = _with("outcome", [_p("subjective wellbeing")]), _with("outcome", [_p("Wellbeing")])
        agreed = agreed_facts(a, b)
        item = next(i for i in agreed if i["facet"] == "outcome")
        self.assertEqual(item["shown"], "proposed:subjective wellbeing")

    def test_an_exact_match_is_unaffected(self):
        a = _with("intervention", [{"value": "cash", "vocab_id": "intervention.cash_transfer",
                                     "quote": "q" * 10, "locator": 1}])
        b = _with("intervention", [{"value": "cash transfers", "vocab_id": "intervention.cash_transfer",
                                     "quote": "w" * 10, "locator": 2}])
        agreed = agreed_facts(a, b, _vocabs())
        item = next(i for i in agreed if i["facet"] == "intervention")
        self.assertEqual(item["quote"], "q" * 10)  # pass a's own copy, same as before this fix


if __name__ == "__main__":
    unittest.main()
