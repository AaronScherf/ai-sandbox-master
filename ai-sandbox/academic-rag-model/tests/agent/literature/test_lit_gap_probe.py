import tempfile
import unittest

from agent.literature.gap.match import Constraint
from agent.literature.gap.probe import build_query, match_work, wilson
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


if __name__ == "__main__":
    unittest.main()
