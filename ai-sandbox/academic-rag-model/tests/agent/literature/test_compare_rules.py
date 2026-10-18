import unittest

from agent.literature.compare import diff_records
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


if __name__ == "__main__":
    unittest.main()
