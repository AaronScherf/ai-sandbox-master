import tempfile
import unittest

from agent.literature.gap.adjacent import widen
from agent.literature.gap.corpus import Fact
from agent.literature.gap.match import Constraint
from agent.literature.gap.subregions import load_subregions
from gap_helpers import VOCABS, write_toy_tables


def fact(facet, shown):
    return Fact(facet, shown, shown, "A")


class TestWiden(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as tmp:
            cls.toy = load_subregions(*write_toy_tables(tmp))

    def w(self, facet, value):
        return widen(Constraint(facet, value), VOCABS, self.toy)

    def test_outcome_widens_to_siblings_with_descendants(self):
        w = self.w("outcome", "o.food_cons")
        self.assertTrue(w.matches(fact("outcome", "o.food_div"), VOCABS))
        label = w.label_for(fact("outcome", "o.food_div"), VOCABS)
        self.assertIn("different outcome", label)
        self.assertIn("Dietary diversity", label)
        self.assertIn("Food consumption", label)
        self.assertIn("1 sibling", label)

    def test_intervention_widens_the_same_way(self):
        w = self.w("intervention", "i.cash_uncond")
        self.assertTrue(w.matches(fact("intervention", "i.cash_cond"), VOCABS))
        self.assertIn("different intervention", w.label_for(fact("intervention", "i.cash_cond"), VOCABS))

    def test_a_descendant_of_a_sibling_matches(self):
        w = self.w("outcome", "o.food_cons")
        grandchild = fact("outcome", "o.food_div_hh")
        self.assertTrue(w.matches(grandchild, VOCABS))
        self.assertIn("Dietary diversity", w.label_for(grandchild, VOCABS))
        self.assertFalse(w.matches(fact("outcome", "o.health_child"), VOCABS))

    def test_own_subtree_is_not_in_the_widening(self):
        w = self.w("outcome", "o.food_cons")
        self.assertFalse(w.matches(fact("outcome", "o.food_cons"), VOCABS))
        self.assertFalse(w.matches(fact("outcome", "o.food"), VOCABS))

    def test_term_under_a_root_is_not_widened(self):
        for facet, term in (("intervention", "i.cash"), ("intervention", "i.seeds"), ("intervention", "i.root_only"),
                            ("intervention", "i.social"), ("outcome", "o.welfare"), ("outcome", "o.food")):
            self.assertIsNone(self.w(facet, term), term)

    def test_grandparent_is_not_adjacent(self):
        w = self.w("outcome", "o.food_cons")
        self.assertFalse(w.matches(fact("outcome", "o.health"), VOCABS))

    def test_country_widens_to_same_subregion_only(self):
        w = self.w("countries", "SO")
        self.assertTrue(w.matches(fact("countries", "ke"), VOCABS))
        self.assertFalse(w.matches(fact("countries", "NG"), VOCABS))
        self.assertFalse(w.matches(fact("countries", "SO"), VOCABS))
        self.assertEqual(w.label_for(fact("countries", "KE"), VOCABS), "different country (same subregion: Eastern Africa)")

    def test_country_missing_from_table_cannot_be_widened(self):
        self.assertIsNone(self.w("countries", "GB"))

    def test_sector_population_design_and_data_source_are_never_widened(self):
        for facet, term in (("sector", "s.social"), ("population", "p.households"),
                            ("study_design", "d.panel"), ("data_sources", "ds.fsnau")):
            self.assertIsNone(self.w(facet, term), facet)


if __name__ == "__main__":
    unittest.main()
