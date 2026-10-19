import unittest
from unittest.mock import patch

from agent.literature import schema, stage
from agent.literature.vocab import Term, Vocabulary


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
        self.assertEqual(schema.PROMPT_VERSION, "extract-v2")
        self.assertIn("most specific", stage.INSTRUCTIONS)


if __name__ == "__main__":
    unittest.main()
