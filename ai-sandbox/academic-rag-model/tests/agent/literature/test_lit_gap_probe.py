import tempfile
import unittest

from agent.literature.gap.match import Constraint
from agent.literature.gap.probe import build_query, match_work, run_probe, wilson
from agent.literature.gap.subregions import load_subregions
from discovery.discover_journal_articles.discovery import Work
from gap_helpers import VOCABS, make_corpus, write_toy_tables


def work(openalex_id="https://openalex.org/W999", doi=None, title="Unrelated"):
    return Work(openalex_id=openalex_id, doi=doi, title=title, authors=[], year=2020, abstract=None)


class TestWilson(unittest.TestCase):
    def test_wilson_known_values(self):
        lo, hi = wilson(0, 25)
        self.assertEqual(lo, 0.0)
        self.assertAlmostEqual(hi, 0.1332, places=3)
        self.assertEqual(wilson(25, 25)[1], 1.0)
        lo, hi = wilson(5, 10)
        self.assertAlmostEqual(lo, 0.2366, places=3)
        self.assertAlmostEqual(hi, 0.7634, places=3)
        self.assertIsNone(wilson(0, 0))


class TestQuery(unittest.TestCase):
    def setUp(self):
        self.sub = load_subregions(*write_toy_tables(tempfile.mkdtemp()))

    def query(self, *constraints):
        return build_query(list(constraints), VOCABS, self.sub)

    def test_query_uses_intervention_outcome_and_country_names_only(self):
        q = self.query(Constraint("intervention", "i.cash"), Constraint("outcome", "o.food"),
                       Constraint("countries", "SO"), Constraint("study_design", "d.rct"))
        self.assertEqual(q, "Cash transfers Food security Somalia")

    def test_label_group_contributes_its_label_once_and_nothing_relevant_gives_empty(self):
        group = Constraint("intervention", "i.agri.training", "t", "label_group", ("i.agri.training", "i.social.training"))
        self.assertEqual(self.query(group), "Training")
        self.assertEqual(self.query(Constraint("study_design", "d.rct")), "")


class TestMatch(unittest.TestCase):
    def setUp(self):
        self.corpus = make_corpus({
            "p1": {"title": "Study One", "openalex_id": "W1"},
            "p2": {"title": "Study Two", "doi": "10.1/abc"},
            "p3": {"title": "Cash Transfers in Somalia"},
            "p4": {"title": None},
        })

    def test_match_by_id_then_doi_then_title(self):
        self.assertEqual(match_work(work("https://openalex.org/W1"), self.corpus), ("p1", "openalex_id"))
        self.assertEqual(match_work(work(doi="https://doi.org/10.1/ABC"), self.corpus), ("p2", "doi"))
        self.assertEqual(match_work(work(title="Cash, Transfers in Somalia!"), self.corpus), ("p3", "title"))
        self.assertIsNone(match_work(work(), self.corpus))

    def test_missing_fields_never_match_missing_fields(self):
        self.assertIsNone(match_work(work(openalex_id=None, doi=None, title=None), self.corpus))


class TestRunProbe(unittest.TestCase):
    def setUp(self):
        self.corpus = make_corpus({"p1": {"title": "Study One", "openalex_id": "W1"},
                                   "p2": {"title": "Cash Transfers in Somalia"}})
        self.sub = load_subregions(*write_toy_tables(tempfile.mkdtemp()))
        self.constraints = [Constraint("intervention", "i.cash"), Constraint("countries", "SO")]
        self.calls = []

    def fetch_of(self, works):
        def fetch(keywords, mailto, batch_size):
            self.calls.append((keywords, mailto, batch_size))
            return iter(works)
        return fetch

    def probe(self, works, constraints=None, **kw):
        return run_probe(self.corpus, constraints or self.constraints, VOCABS, self.sub, "a@b.c",
                         fetch=self.fetch_of(works), today="2026-10-31", **kw)

    def test_probe_counts_matches_and_intervals(self):
        out = self.probe([work("W1"), work(title="Cash Transfers in Somalia"), work("W7", title="x"), work("W8", title="y")])
        self.assertEqual((out["retrieved"], out["in_corpus"], out["not_in_corpus"], out["requested"]), (4, 2, 2, 25))
        self.assertEqual(out["interval"], list(wilson(2, 4)))
        self.assertEqual(out["matched"], [{"file_id": "p1", "by": "openalex_id"}, {"file_id": "p2", "by": "title"}])
        self.assertEqual((out["query"], out["fetched"]), ("Cash transfers Somalia", "2026-10-31"))
        self.assertEqual(self.calls, [("Cash transfers Somalia", "a@b.c", 25)])

    def test_probe_takes_at_most_n_works(self):
        out = self.probe([work(f"W{i}", title=f"t{i}") for i in range(10)], n=3)
        self.assertEqual((out["retrieved"], out["requested"]), (3, 3))

    def test_empty_result_has_no_interval(self):
        out = self.probe([])
        self.assertEqual((out["retrieved"], out["in_corpus"], out["interval"]), (0, 0, None))

    def test_empty_query_errors_without_calling_fetch(self):
        out = self.probe([work()], constraints=[Constraint("study_design", "d.rct")])
        self.assertIn("error", out)
        self.assertEqual(self.calls, [])

    def test_fetch_exception_becomes_error(self):
        def boom(*a):
            raise RuntimeError("boom")
        out = run_probe(self.corpus, self.constraints, VOCABS, self.sub, "a@b.c", fetch=boom)
        self.assertIn("boom", out["error"])
        self.assertEqual(out["query"], "Cash transfers Somalia")


if __name__ == "__main__":
    unittest.main()
