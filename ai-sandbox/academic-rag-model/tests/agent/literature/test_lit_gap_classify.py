import itertools
import tempfile
import unittest

from agent.literature.gap import VERDICTS
from agent.literature.gap.classify import classify
from agent.literature.gap.match import Constraint
from agent.literature.gap.subregions import load_subregions
from gap_helpers import VOCABS, fx, make_corpus, write_toy_tables


def paper(*facts, year=2020):
    return {"year": year, "facts": list(facts)}


class TestClassify(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as tmp:
            cls.toy = load_subregions(*write_toy_tables(tmp))

    def run_classify(self, papers, *constraints):
        return classify(make_corpus(papers), list(constraints), VOCABS, self.toy)

    def test_leaf_under_parent_constraint_is_direct(self):
        r = self.run_classify({"paper-a": paper(fx("intervention", "i.cash_uncond")),
                               "paper-b": paper(fx("intervention", "i.voucher"))},
                              Constraint("intervention", "i.cash"))
        self.assertEqual(r.direct, ["paper-a"])
        self.assertEqual(r.verdict, "tried_directly")

    def test_one_adjacent_case_each_for_intervention_outcome_country(self):
        r = self.run_classify({"paper-a": paper(fx("intervention", "i.cash_cond"), fx("countries", "SO"))},
                              Constraint("intervention", "i.cash_uncond"), Constraint("countries", "SO"))
        self.assertEqual(list(r.adjacent), ["paper-a"])
        self.assertIn("different intervention", r.adjacent["paper-a"][0])
        r = self.run_classify({"paper-a": paper(fx("outcome", "o.food_div"), fx("countries", "SO"))},
                              Constraint("outcome", "o.food_cons"), Constraint("countries", "SO"))
        self.assertIn("different outcome", r.adjacent["paper-a"][0])
        r = self.run_classify({"paper-a": paper(fx("outcome", "o.food_cons"), fx("countries", "KE"))},
                              Constraint("outcome", "o.food_cons"), Constraint("countries", "SO"))
        self.assertEqual(r.adjacent["paper-a"], ["different country (same subregion: Eastern Africa)"])
        self.assertEqual(r.verdict, "tried_adjacent")

    def test_two_relaxations_needed_is_partial_not_adjacent(self):
        r = self.run_classify({"paper-a": paper(fx("outcome", "o.food_div"), fx("countries", "KE"), fx("sector", "s.social"))},
                              Constraint("outcome", "o.food_cons"), Constraint("countries", "SO"), Constraint("sector", "s.social"))
        self.assertEqual(r.adjacent, {})
        self.assertEqual(r.partial, [("paper-a", 1)])
        self.assertEqual(r.verdict, "no_evidence_in_corpus")

    def test_direct_paper_is_never_listed_adjacent(self):
        r = self.run_classify({"paper-a": paper(fx("outcome", "o.food_cons"), fx("outcome", "o.food_div"))},
                              Constraint("outcome", "o.food_cons"))
        self.assertEqual((r.direct, r.adjacent), (["paper-a"], {}))

    def test_two_constraints_on_one_facet_both_required(self):
        r = self.run_classify({"paper-a": paper(fx("outcome", "o.food_cons")),
                               "paper-b": paper(fx("outcome", "o.food_cons"), fx("outcome", "o.health"))},
                              Constraint("outcome", "o.food_cons"), Constraint("outcome", "o.health"))
        self.assertEqual(r.direct, ["paper-b"])
        self.assertEqual(r.partial, [("paper-a", 1)])

    def test_single_constraint_question_can_be_relaxed_and_has_no_partial_list(self):
        r = self.run_classify({"paper-a": paper(fx("outcome", "o.food_div")), "paper-b": paper(fx("outcome", "o.health"))},
                              Constraint("outcome", "o.food_cons"))
        self.assertEqual(list(r.adjacent), ["paper-a"])
        self.assertEqual(r.partial, [])

    def test_different_method_is_separate_from_adjacent_and_partial(self):
        r = self.run_classify({"paper-a": paper(fx("intervention", "i.cash"), fx("study_design", "d.rct")),
                               "paper-b": paper(fx("intervention", "i.cash"), fx("study_design", "d.panel"))},
                              Constraint("intervention", "i.cash"), Constraint("study_design", "d.panel"))
        self.assertEqual((r.direct, r.different_method, r.partial, r.adjacent), (["paper-b"], ["paper-a"], [], {}))
        r = self.run_classify({"paper-a": paper(fx("intervention", "i.cash_cond"), fx("study_design", "d.rct"), fx("countries", "SO"))},
                              Constraint("intervention", "i.cash_uncond"), Constraint("study_design", "d.panel"),
                              Constraint("countries", "SO"))
        self.assertEqual((r.different_method, r.adjacent, r.partial), ([], {}, [("paper-a", 1)]))

    def test_design_only_question_has_no_different_method(self):
        r = self.run_classify({"paper-a": paper(fx("study_design", "d.rct"))}, Constraint("study_design", "d.panel"))
        self.assertEqual(r.different_method, [])

    def test_unwidenable_constraints_are_reported(self):
        r = self.run_classify({"paper-a": paper(fx("intervention", "i.root_only"), fx("countries", "GB"))},
                              Constraint("intervention", "i.root_only"), Constraint("countries", "GB"))
        self.assertEqual(r.unwidenable, ["intervention=i.root_only", "countries=GB"])

    def test_partial_list_is_capped_at_ten_and_ordered(self):
        papers = {f"paper-{n:02d}": paper(fx("intervention", "i.cash"), year=2000 + n) for n in range(1, 13)}
        r = self.run_classify(papers, Constraint("intervention", "i.cash"), Constraint("outcome", "o.health"))
        self.assertEqual(len(r.partial), 10)
        self.assertEqual([fid for fid, _ in r.partial][:2], ["paper-12", "paper-11"])
        self.assertEqual(r.partial[-1], ("paper-03", 1))

    def test_each_verdict_and_rule_text(self):
        direct = self.run_classify({"paper-a": paper(fx("outcome", "o.food_cons"))}, Constraint("outcome", "o.food_cons"))
        adjacent = self.run_classify({"paper-a": paper(fx("outcome", "o.food_div"))}, Constraint("outcome", "o.food_cons"))
        none = self.run_classify({"paper-a": paper(fx("outcome", "o.health"))}, Constraint("outcome", "o.food_cons"))
        self.assertEqual([r.verdict for r in (direct, adjacent, none)],
                         ["tried_directly", "tried_adjacent", "no_evidence_in_corpus"])
        self.assertIn("1 paper", direct.rule)
        self.assertIn("exactly one", adjacent.rule)
        self.assertIn("corpus only", none.rule)

    def test_found_externally_is_never_produced_but_is_reserved(self):
        self.assertIn("found_externally_not_in_corpus", VERDICTS)
        self.assertEqual(len(VERDICTS), 4)

    def test_empty_corpus_gives_no_evidence(self):
        r = self.run_classify({}, Constraint("outcome", "o.food_cons"))
        self.assertEqual((r.direct, r.adjacent, r.partial, r.verdict), ([], {}, [], "no_evidence_in_corpus"))

    def test_properties_over_a_grid_of_constraint_sets(self):
        papers = {
            "p1": paper(fx("intervention", "i.cash_uncond"), fx("outcome", "o.food_cons"), fx("countries", "SO")),
            "p2": paper(fx("intervention", "i.cash_cond"), fx("outcome", "o.food_div"), fx("countries", "KE")),
            "p3": paper(fx("intervention", "i.cash_cond"), fx("outcome", "o.food_cons"), fx("countries", "SO")),
            "p4": paper(fx("outcome", "o.food_div"), fx("countries", "NG")),
            "p5": paper(fx("intervention", "i.voucher"), fx("study_design", "d.rct")),
        }
        pool = [Constraint("intervention", "i.cash_uncond"), Constraint("outcome", "o.food_cons"),
                Constraint("countries", "SO"), Constraint("study_design", "d.panel")]
        corpus = make_corpus(papers)
        for size in (1, 2, 3, 4):
            for combo in itertools.combinations(pool, size):
                r = classify(corpus, list(combo), VOCABS, self.toy)
                self.assertTrue(set(r.direct).isdisjoint(r.adjacent), combo)
                expected = "tried_directly" if r.direct else "tried_adjacent" if r.adjacent else "no_evidence_in_corpus"
                self.assertEqual(r.verdict, expected, combo)
                listed = [fid for fid, _ in r.partial]
                self.assertTrue(set(listed).isdisjoint(r.direct) and set(listed).isdisjoint(r.adjacent)
                                and set(listed).isdisjoint(r.different_method), combo)


if __name__ == "__main__":
    unittest.main()
