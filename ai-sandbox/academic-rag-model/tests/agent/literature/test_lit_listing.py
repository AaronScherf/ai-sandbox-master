import unittest
from unittest.mock import patch

from agent.literature import schema, stage, verify
from agent.literature.vocab import Term, Vocabulary
from agent.literature.listing import tree_listing


def _tree():
    terms = {
        "intervention.health": Term(id="intervention.health", label="Health"),
        "intervention.vaccines": Term(id="intervention.vaccines", label="Vaccines", parent="intervention.health",
                                      definition="Immunisation programmes"),
        "intervention.measles_shot": Term(id="intervention.measles_shot", label="Measles shot",
                                          parent="intervention.vaccines"),
    }
    return Vocabulary("intervention", 1, "3ie", "test fixture", terms)


class TestListing(unittest.TestCase):
    def test_tree_order_and_indentation(self):
        v = _tree()
        first = tree_listing(v, list(v.terms.values()), "a", "paper", "intervention")
        self.assertEqual(first.splitlines(), ["- intervention.health: Health",
            "  - intervention.vaccines: Vaccines - Immunisation programmes",
            "    - intervention.measles_shot: Measles shot"])
        siblings = {f"intervention.child{i}": Term(id=f"intervention.child{i}", label=f"Child {i}",
                    parent="intervention.health") for i in range(12)}
        v.terms.update(siblings)
        a = tree_listing(v, list(v.terms.values()), "a", "paper", "intervention")
        b = tree_listing(v, list(v.terms.values()), "b", "paper", "intervention")
        self.assertEqual(b, tree_listing(v, list(v.terms.values()), "b", "paper", "intervention"))
        self.assertNotEqual(a, b)
        self.assertEqual(set(a.splitlines()), set(b.splitlines()))
    def test_a_small_vocabulary_is_listed_in_full(self):
        text = stage._vocab_listing({"intervention": _tree()})
        self.assertIn("intervention.measles_shot", text)

    def test_a_large_vocabulary_lists_only_the_grouping_levels(self):
        with patch.object(stage, "LISTING_LIMIT", 2):
            text = stage._vocab_listing({"intervention": _tree()})
        self.assertIn("intervention.vaccines: Vaccines - Immunisation programmes", text)
        self.assertIn("intervention.health", text)
        self.assertNotIn("intervention.measles_shot", text)
        self.assertIn("grouping levels", text)

    def test_the_prompt_version_names_the_3ie_instructions(self):
        self.assertEqual(schema.PROMPT_VERSION, "extract-v5")
        self.assertIn("Choose a child term only when its definition", stage.INSTRUCTIONS)
        self.assertIn("Resilience outcomes concern a household's capacity", stage.INSTRUCTIONS)
        self.assertNotIn("most specific listed term", stage.INSTRUCTIONS)
        self.assertIn("this study itself", stage.INSTRUCTIONS)
        self.assertIn("every distinct", stage.INSTRUCTIONS)

    def test_the_instructions_limit_countries_and_review_data_sources(self):
        text = stage.INSTRUCTIONS
        self.assertIn("own sample or setting", text)
        self.assertIn("examples", text)
        self.assertIn("acknowledgements", text)
        self.assertIn("countries: []", text)
        self.assertIn("review, overview or competition", text)
        self.assertIn("analysed itself", text)

    def test_the_checker_applies_the_same_country_test(self):
        self.assertIn("own sample or setting", verify.INSTRUCTIONS)


if __name__ == "__main__":
    unittest.main()
