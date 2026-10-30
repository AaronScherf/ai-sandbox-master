import unittest

from agent.literature.gap.corpus import load_corpus
from agent.literature.gap.match import Constraint, fact_matches, papers_matching, vocab_for
from gap_helpers import VOCABS, fx, make_conn, make_corpus


class TestCorpus(unittest.TestCase):
    def test_load_corpus_reads_papers_facts_results(self):
        conn = make_conn({
            "paper-a": {"year": 2019, "facts": [fx("intervention", "i.cash"), fx("countries", "SO")],
                        "results": [("Cash raised food consumption", "positive")]},
            "paper-b": {"year": None, "facts": [fx("outcome", "o.food")]},
        })
        corpus = load_corpus(conn)
        self.assertEqual(sorted(corpus.papers), ["paper-a", "paper-b"])
        self.assertEqual(corpus.papers["paper-a"].year, 2019)
        self.assertIsNone(corpus.papers["paper-b"].year)
        self.assertEqual([f.facet for f in corpus.facts["paper-a"]], ["intervention", "countries"])
        self.assertEqual(corpus.facts["paper-a"][0].tier, "A")
        self.assertEqual(corpus.results["paper-a"][0]["direction"], "positive")
        self.assertEqual(corpus.results.get("paper-b", []), [])


class TestMatching(unittest.TestCase):
    def test_vocab_for_maps_facets_and_skips_countries(self):
        self.assertIs(vocab_for("data_sources", VOCABS), VOCABS["data_source"])
        self.assertIsNone(vocab_for("countries", VOCABS))

    def test_descendant_matches_parent_constraint(self):
        corpus = make_corpus({"paper-a": {"facts": [fx("intervention", "i.cash_uncond")]},
                              "paper-b": {"facts": [fx("intervention", "i.voucher")]}})
        c = Constraint("intervention", "i.cash")
        self.assertEqual(papers_matching(corpus, [c], VOCABS), ["paper-a"])

    def test_matching_is_by_id_so_same_label_terms_stay_distinct(self):
        corpus = make_corpus({"paper-a": {"facts": [fx("intervention", "i.agri.training")]},
                              "paper-b": {"facts": [fx("intervention", "i.social.training")]}})
        self.assertEqual(VOCABS["intervention"].terms["i.agri.training"].label,
                         VOCABS["intervention"].terms["i.social.training"].label)
        c = Constraint("intervention", "i.agri.training")
        self.assertEqual(papers_matching(corpus, [c], VOCABS), ["paper-a"])

    def test_proposed_fact_matches_on_label_only(self):
        corpus = make_corpus({"paper-a": {"facts": [fx("intervention", "proposed:cash grants")]},
                              "paper-b": {"facts": [fx("intervention", "proposed:school meals")]}})
        c = Constraint("intervention", "i.grants")
        self.assertEqual(papers_matching(corpus, [c], VOCABS), ["paper-a"])

    def test_country_constraint_is_case_insensitive_on_the_fact(self):
        corpus = make_corpus({"paper-a": {"facts": [fx("countries", "so")]},
                              "paper-b": {"facts": [fx("countries", "SO")]},
                              "paper-c": {"facts": [fx("countries", "KE")]}})
        c = Constraint("countries", "SO")
        self.assertEqual(papers_matching(corpus, [c], VOCABS), ["paper-a", "paper-b"])
        self.assertTrue(fact_matches(c, corpus.facts["paper-a"][0], VOCABS))

    def test_papers_matching_requires_every_constraint(self):
        corpus = make_corpus({
            "paper-a": {"facts": [fx("intervention", "i.cash"), fx("outcome", "o.food_cons")]},
            "paper-b": {"facts": [fx("intervention", "i.cash")]},
            "paper-c": {"facts": [fx("outcome", "o.food_cons"), fx("outcome", "o.health")]},
        })
        both = [Constraint("intervention", "i.cash"), Constraint("outcome", "o.food_cons")]
        self.assertEqual(papers_matching(corpus, both, VOCABS), ["paper-a"])
        same_facet = [Constraint("outcome", "o.food_cons"), Constraint("outcome", "o.health")]
        self.assertEqual(papers_matching(corpus, same_facet, VOCABS), ["paper-c"])


if __name__ == "__main__":
    unittest.main()
