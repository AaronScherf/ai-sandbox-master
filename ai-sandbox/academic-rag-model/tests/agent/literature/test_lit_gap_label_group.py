import json
import tempfile
import unittest

from agent.literature.gap.adjacent import widen
from agent.literature.gap.classify import classify
from agent.literature.gap.coverage import Sidecar, coverage
from agent.literature.gap.match import Constraint, papers_matching
from agent.literature.gap.report import build_report, render_markdown
from agent.literature.gap.resolve import resolve
from agent.literature.gap.subregions import load_subregions
from gap_helpers import VOCABS, _vocab, fx, make_corpus, write_toy_tables

PAPERS = {
    "social": {"title": "Social training", "facts": [fx("intervention", "i.social.training")]},
    "agri": {"title": "Agri training", "facts": [fx("intervention", "i.agri.training")]},
    "cash": {"title": "Cash", "facts": [fx("intervention", "i.cash")]},
}
GROUP = Constraint("intervention", "i.agri.training", "training", "label_group", ("i.agri.training", "i.social.training"))


class TestLabelGroupResolve(unittest.TestCase):
    def setUp(self):
        self.corpus = make_corpus(PAPERS)

    def test_ambiguous_label_offers_a_group_candidate_first_with_the_union_paper_count(self):
        res = resolve(self.corpus, VOCABS, "intervention", "training")
        self.assertIsNone(res.constraint)
        first = res.candidates[0]
        self.assertEqual((first.term_id, first.papers, first.label), ("group:i.agri.training", 2, "Training"))
        self.assertIn("2 terms", first.path)
        self.assertEqual([c.term_id for c in res.candidates[1:]], ["i.agri.training", "i.social.training"])

    def test_picking_the_group_gives_a_label_group_constraint_of_all_same_label_terms(self):
        res = resolve(self.corpus, VOCABS, "intervention", "training", pick="group:i.social.training")
        c = res.constraint
        self.assertEqual((c.resolved_by, set(c.members), c.phrase), ("label_group", {"i.agri.training", "i.social.training"}, "training"))

    def test_a_term_with_a_unique_label_has_no_group(self):
        res = resolve(self.corpus, VOCABS, "intervention", "x", pick="group:i.cash")
        self.assertIsNone(res.constraint)
        self.assertIn("same label", res.message)


class TestLabelGroupMatch(unittest.TestCase):
    def test_group_matches_papers_under_any_member(self):
        corpus = make_corpus(PAPERS)
        self.assertEqual(papers_matching(corpus, [GROUP], VOCABS), ["agri", "social"])
        self.assertEqual(papers_matching(corpus, [Constraint("intervention", "i.agri.training")], VOCABS), ["agri"])

    def test_group_widens_to_the_siblings_of_every_member_but_not_the_members(self):
        rows = [("a", None, "A", ()), ("a.x", "a", "X", ()), ("a.x.t", "a.x", "Pilot", ()), ("a.x.s", "a.x", "Sib A", ()),
                ("b", None, "B", ()), ("b.y", "b", "Y", ()), ("b.y.t", "b.y", "Pilot", ()), ("b.y.s", "b.y", "Sib B", ())]
        vocabs = {**VOCABS, "intervention": _vocab("intervention", rows)}
        group = Constraint("intervention", "a.x.t", "pilot", "label_group", ("a.x.t", "b.y.t"))
        w = widen(group, vocabs, load_subregions(*write_toy_tables(tempfile.mkdtemp())))
        self.assertEqual(w.term_ids, {"a.x.s", "b.y.s"})

    def test_a_group_under_top_level_groupings_is_not_widened(self):
        self.assertIsNone(widen(GROUP, VOCABS, load_subregions(*write_toy_tables(tempfile.mkdtemp()))))


class TestLabelGroupReport(unittest.TestCase):
    def report(self):
        corpus = make_corpus(PAPERS)
        sub = load_subregions(*write_toy_tables(tempfile.mkdtemp()))
        result = classify(corpus, [GROUP], VOCABS, sub)
        side = Sidecar(eligible=3, excluded=0, without_record=0, open_tier_c=0, db_stale=False, db_path="d", db_mtime=1.0,
                       db_papers=3, scales={})
        return build_report("training?", [GROUP], VOCABS, result, coverage(corpus, result, [GROUP], side), corpus)

    def test_breakdown_lists_direct_papers_per_branch(self):
        r = self.report()
        (b,) = r["breakdown"]
        self.assertEqual(b["facet"], "intervention")
        self.assertEqual({(x["path"], tuple(x["papers"])) for x in b["branches"]},
                         {("Agricultural programmes > Training", ("agri",)), ("Social protection programmes > Training", ("social",))})
        json.dumps(r)

    def test_constraint_and_fact_labels_carry_their_path(self):
        r = self.report()
        self.assertEqual(r["constraints"][0]["members"], ["i.agri.training", "i.social.training"])
        self.assertEqual(r["constraints"][0]["path"], "Agricultural programmes > Training")
        self.assertEqual({e["file_id"]: e["facts"][0]["path"] for e in r["evidence"]},
                         {"agri": "Agricultural programmes > Training", "social": "Social protection programmes > Training"})
        md = render_markdown(r)
        self.assertIn("Social protection programmes > Training", md)
        self.assertIn("all 2 terms labelled Training", md)

    def test_a_plain_constraint_has_no_breakdown(self):
        corpus = make_corpus(PAPERS)
        c = Constraint("intervention", "i.cash")
        sub = load_subregions(*write_toy_tables(tempfile.mkdtemp()))
        result = classify(corpus, [c], VOCABS, sub)
        side = Sidecar(eligible=3, excluded=0, without_record=0, open_tier_c=0, db_stale=False, db_path="d", db_mtime=1.0,
                       db_papers=3, scales={})
        r = build_report("q", [c], VOCABS, result, coverage(corpus, result, [c], side), corpus)
        self.assertEqual(r["breakdown"], [])
        self.assertEqual(r["constraints"][0]["path"], "Social protection programmes > Cash transfers")


if __name__ == "__main__":
    unittest.main()
