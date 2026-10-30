import tempfile
import unittest

from agent.literature.gap.resolve import level_of, resolve, shortlist
from agent.literature.gap.subregions import load_subregions
from agent.literature.vocab import Term, Vocabulary
from gap_helpers import VOCABS, fx, make_corpus, write_toy_tables


class TestResolve(unittest.TestCase):
    def setUp(self):
        self.corpus = make_corpus({
            "paper-a": {"facts": [fx("intervention", "i.cash_uncond"), fx("countries", "SO")]},
            "paper-b": {"facts": [fx("intervention", "i.cash_cond")]},
            "paper-c": {"facts": [fx("intervention", "i.voucher")]},
        })

    def run_resolve(self, facet, value, **kw):
        return resolve(self.corpus, VOCABS, facet, value, **kw)

    def test_exact_label_resolves_to_one_term(self):
        res = self.run_resolve("intervention", "CASH")
        self.assertEqual(res.constraint.value, "i.cash")
        self.assertEqual(res.constraint.resolved_by, "exact")
        self.assertEqual(res.constraint.phrase, "CASH")

    def test_duplicate_label_is_ambiguous_and_lists_both_positions(self):
        res = self.run_resolve("intervention", "training")
        self.assertIsNone(res.constraint)
        self.assertEqual(sorted(c.term_id for c in res.candidates), ["i.agri.training", "i.social.training"])

    def test_unresolved_phrase_gives_ranked_candidates_with_level_children_and_paper_counts(self):
        res = self.run_resolve("intervention", "unconditional payments")
        self.assertIsNone(res.constraint)
        first = res.candidates[0]
        self.assertEqual((first.term_id, first.level, first.children, first.papers), ("i.cash_uncond", 2, 0, 1))
        self.assertEqual(first.path, "Social protection programmes > Cash transfers")  # tells same-label positions apart
        res = self.run_resolve("intervention", "transfer")
        self.assertEqual([c.term_id for c in res.candidates], ["i.cash", "i.cash_cond", "i.cash_uncond"])
        self.assertEqual((res.candidates[0].children, res.candidates[0].papers), (2, 2))

    def test_no_overlap_gives_no_candidates_and_a_message(self):
        res = self.run_resolve("intervention", "zzz")
        self.assertIsNone(res.constraint)
        self.assertEqual(res.candidates, [])
        self.assertIn("no candidate", res.message.lower())

    def test_candidate_list_is_capped_at_eight(self):
        terms = {f"g.{n}": Term(id=f"g.{n}", label=f"Grant {n}") for n in range(12)}
        vocabs = {"intervention": Vocabulary("intervention", 1, "provisional", "test", terms)}
        res = resolve(self.corpus, vocabs, "intervention", "grant")
        self.assertEqual(len(res.candidates), 8)
        self.assertEqual(len(shortlist(self.corpus, vocabs, "intervention", "grant", limit=3)), 3)

    def test_shortlist_matches_the_order_resolve_reports(self):
        res = self.run_resolve("intervention", "transfer")
        self.assertEqual(shortlist(self.corpus, VOCABS, "intervention", "transfer"), res.candidates)

    def test_pick_resolves_and_records_the_phrase(self):
        res = self.run_resolve("intervention", "transfer", pick="i.cash")
        self.assertEqual((res.constraint.value, res.constraint.phrase, res.constraint.resolved_by),
                         ("i.cash", "transfer", "user"))
        card = self.run_resolve("intervention", "transfer", pick="i.cash", resolved_by="card")
        self.assertEqual(card.constraint.resolved_by, "card")

    def test_pick_outside_the_facet_vocabulary_is_rejected(self):
        res = self.run_resolve("intervention", "transfer", pick="o.food")
        self.assertIsNone(res.constraint)
        self.assertIn("o.food", res.message)

    def test_country_code_case_and_name(self):
        self.assertEqual(self.run_resolve("countries", "so").constraint.value, "SO")
        with tempfile.TemporaryDirectory() as tmp:
            sub, ctry = write_toy_tables(tmp)
            toy = load_subregions(sub, ctry)
        self.assertEqual(self.run_resolve("countries", "Somalia", subregions=toy).constraint.value, "SO")
        bad = self.run_resolve("countries", "XX", subregions=toy)
        self.assertIsNone(bad.constraint)
        self.assertTrue(bad.message)

    def test_unknown_facet_raises_value_error(self):
        with self.assertRaises(ValueError):
            self.run_resolve("nonsense", "x")


class TestLevel(unittest.TestCase):
    def test_level_counts_ancestors(self):
        v = VOCABS["intervention"]
        self.assertEqual([level_of(t, v) for t in ("i.social", "i.cash", "i.cash_uncond")], [0, 1, 2])


if __name__ == "__main__":
    unittest.main()
