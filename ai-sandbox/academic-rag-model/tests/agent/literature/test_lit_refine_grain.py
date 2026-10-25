import unittest

from agent.literature.vocab import Term, Vocabulary


def _hierarchical_vocabs():
    """A small vocab set reproducing the real 3ie files' structure just enough to test scoping: two branches
    ("Agriculture & Forestry" and "Public Administration") each with a short chain of children, and the real
    cross-vocabulary id quirk where intervention's "Public Administration" root is `_2`-suffixed but outcome's and
    sector's are not -- only label equality can match them."""
    iv_terms = {
        "intervention.agriculture_forestry": Term(id="intervention.agriculture_forestry", label="Agriculture & Forestry"),
        "intervention.climate_adaption_mitigation_strategies": Term(
            id="intervention.climate_adaption_mitigation_strategies", label="Climate adaption & mitigation strategies",
            parent="intervention.agriculture_forestry"),
        "intervention.crop_diversification": Term(
            id="intervention.crop_diversification", label="Crop diversification",
            parent="intervention.climate_adaption_mitigation_strategies"),
        "intervention.public_administration_2": Term(id="intervention.public_administration_2", label="Public Administration"),
        "intervention.land_titling_reform": Term(
            id="intervention.land_titling_reform", label="Land titling & reform", parent="intervention.public_administration_2"),
    }
    oc_terms = {
        "outcome.agriculture_forestry": Term(id="outcome.agriculture_forestry", label="Agriculture & Forestry"),
        "outcome.crop_production": Term(id="outcome.crop_production", label="Crop production", parent="outcome.agriculture_forestry"),
        "outcome.public_administration": Term(id="outcome.public_administration", label="Public Administration"),
    }
    sec_terms = {
        "sector.agriculture_forestry": Term(id="sector.agriculture_forestry", label="Agriculture & Forestry"),
        "sector.public_administration": Term(id="sector.public_administration", label="Public Administration"),
    }
    return {
        "intervention": Vocabulary("intervention", 1, "3ie", "test", iv_terms),
        "outcome": Vocabulary("outcome", 1, "3ie", "test", oc_terms),
        "sector": Vocabulary("sector", 1, "3ie", "test", sec_terms),
    }


class TestRoot(unittest.TestCase):
    def test_walks_up_to_the_term_with_no_parent(self):
        from agent.literature.refine_grain import _root
        vocabs = _hierarchical_vocabs()
        self.assertEqual(_root("intervention.crop_diversification", vocabs["intervention"]),
                          "intervention.agriculture_forestry")

    def test_a_root_term_is_its_own_root(self):
        from agent.literature.refine_grain import _root
        vocabs = _hierarchical_vocabs()
        self.assertEqual(_root("intervention.agriculture_forestry", vocabs["intervention"]),
                          "intervention.agriculture_forestry")

    def test_unknown_term_or_missing_vocab_is_none(self):
        from agent.literature.refine_grain import _root
        vocabs = _hierarchical_vocabs()
        self.assertIsNone(_root("intervention.nonexistent", vocabs["intervention"]))
        self.assertIsNone(_root("intervention.agriculture_forestry", None))
        self.assertIsNone(_root(None, vocabs["intervention"]))


class TestRootIdsFromFacts(unittest.TestCase):
    def test_collects_roots_and_skips_proposed_facts(self):
        from agent.literature.refine_grain import _root_ids_from_facts
        vocabs = _hierarchical_vocabs()
        facts = [{"value": "x", "vocab_id": "intervention.crop_diversification", "quote": "q" * 10, "locator": 1},
                 {"value": "y", "proposed": True, "quote": "q" * 10, "locator": 2}]
        self.assertEqual(_root_ids_from_facts(facts, vocabs["intervention"]), {"intervention.agriculture_forestry"})

    def test_empty_or_none_facts_give_an_empty_set(self):
        from agent.literature.refine_grain import _root_ids_from_facts
        vocabs = _hierarchical_vocabs()
        self.assertEqual(_root_ids_from_facts([], vocabs["intervention"]), set())
        self.assertEqual(_root_ids_from_facts(None, vocabs["intervention"]), set())


class TestRootByLabel(unittest.TestCase):
    def test_finds_the_root_with_a_matching_label(self):
        from agent.literature.refine_grain import _root_by_label
        vocabs = _hierarchical_vocabs()
        self.assertEqual(_root_by_label(vocabs["intervention"], "Public Administration"),
                          "intervention.public_administration_2")

    def test_no_matching_root_is_none(self):
        from agent.literature.refine_grain import _root_by_label
        vocabs = _hierarchical_vocabs()
        self.assertIsNone(_root_by_label(vocabs["intervention"], "Nonexistent Category"))

    def test_a_non_root_term_with_the_same_label_text_is_never_matched(self):
        from agent.literature.refine_grain import _root_by_label
        vocabs = _hierarchical_vocabs()
        # "Crop diversification" is a real label in this fixture but is not a root -- must not match
        self.assertIsNone(_root_by_label(vocabs["intervention"], "Crop diversification"))


class TestScopeRoots(unittest.TestCase):
    def _record(self, intervention=None, outcome=None, sector=None):
        return {"core": {"intervention": intervention or [], "outcome": outcome or [], "sector": sector or []}}

    def test_uses_the_root_of_the_paper_s_own_current_fact(self):
        from agent.literature.refine_grain import scope_roots
        vocabs = _hierarchical_vocabs()
        record = self._record(intervention=[{"value": "x", "vocab_id": "intervention.crop_diversification",
                                              "quote": "q" * 10, "locator": 1}])
        self.assertEqual(scope_roots(record, "intervention", vocabs["intervention"], vocabs["sector"]),
                          {"intervention.agriculture_forestry"})

    def test_a_proposed_fact_with_no_vocab_id_is_ignored_for_rooting(self):
        from agent.literature.refine_grain import scope_roots
        vocabs = _hierarchical_vocabs()
        record = self._record(intervention=[{"value": "x", "proposed": True, "quote": "q" * 10, "locator": 1}])
        self.assertEqual(scope_roots(record, "intervention", vocabs["intervention"], vocabs["sector"]), set())

    def test_falls_back_to_sector_when_the_facet_has_no_vocab_anchored_fact(self):
        from agent.literature.refine_grain import scope_roots
        vocabs = _hierarchical_vocabs()
        record = self._record(sector=[{"value": "x", "vocab_id": "sector.public_administration",
                                        "quote": "q" * 10, "locator": 1}])
        # sector's id is "sector.public_administration"; intervention's matching root (by label only, since the
        # real taxonomy's intervention root for this category is "_2"-suffixed) is "intervention.public_administration_2"
        self.assertEqual(scope_roots(record, "intervention", vocabs["intervention"], vocabs["sector"]),
                          {"intervention.public_administration_2"})

    def test_two_sector_facts_give_two_root_branches(self):
        from agent.literature.refine_grain import scope_roots
        vocabs = _hierarchical_vocabs()
        record = self._record(sector=[
            {"value": "x", "vocab_id": "sector.public_administration", "quote": "q" * 10, "locator": 1},
            {"value": "y", "vocab_id": "sector.agriculture_forestry", "quote": "q" * 10, "locator": 2}])
        self.assertEqual(scope_roots(record, "outcome", vocabs["outcome"], vocabs["sector"]),
                          {"outcome.public_administration", "outcome.agriculture_forestry"})

    def test_no_anchor_anywhere_is_an_empty_set(self):
        from agent.literature.refine_grain import scope_roots
        vocabs = _hierarchical_vocabs()
        self.assertEqual(scope_roots(self._record(), "intervention", vocabs["intervention"], vocabs["sector"]), set())


class TestWriteVocabDirPreservesParent(unittest.TestCase):
    def test_a_written_and_reloaded_vocab_keeps_its_parent_links(self):
        import tempfile
        from pathlib import Path

        from agent.literature.vocab import load_vocabulary
        from lit_helpers import write_vocab_dir

        vocabs = _hierarchical_vocabs()
        with tempfile.TemporaryDirectory() as d:
            write_vocab_dir(d, vocabs)
            reloaded = load_vocabulary(Path(d) / "intervention.yaml")
        self.assertEqual(reloaded.terms["intervention.crop_diversification"].parent,
                          "intervention.climate_adaption_mitigation_strategies")


if __name__ == "__main__":
    unittest.main()
