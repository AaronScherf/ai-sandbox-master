import tempfile
import unittest
from pathlib import Path

from agent.literature import refine_grain, stage
from agent.literature.papers import eligible_papers
from agent.literature.proposals import Proposals
from agent.literature.store import RecordStore
from agent.literature.vocab import Term, Vocabulary
from core.agent_tasks.work import task_entry
from lit_helpers import PAGES, VOCABS, good, make_index

PROV = {"driver": "agent", "agent": "antigravity", "run": "r1"}
FID = "0123456789abcdef"


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


def _setup(root, vocabs=None):
    """An index with one eligible paper that already has a pass-"a" extraction record, as every one of the real
    62 papers already does (confirmed: zero papers are missing either pass in the real corpus)."""
    make_index(root)
    vocabs = vocabs or VOCABS
    records = RecordStore(Path(root) / ".index" / "study_records")
    target = stage.Target(str(root), records, vocabs, Proposals(records.dir))
    papers, _ = eligible_papers(str(root))
    tasks, _ = stage.make_tasks(target, papers, pass_label="a", redo=True)
    stage.apply_result(target, task_entry(tasks[0]), good(), PROV)
    return target, papers


class TestMakeTasks(unittest.TestCase):
    def test_builds_one_task_per_paper_with_an_existing_record_for_this_pass(self):
        with tempfile.TemporaryDirectory() as root:
            target, papers = _setup(root)
            tasks, skipped = refine_grain.make_tasks(target, papers, pass_label="a")
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].id, f"refine-{FID}")
        self.assertEqual(tasks[0].stage, refine_grain.STAGE)
        self.assertEqual(skipped, {})

    def test_skips_a_pass_with_no_record_yet(self):
        with tempfile.TemporaryDirectory() as root:
            target, papers = _setup(root)
            tasks, skipped = refine_grain.make_tasks(target, papers, pass_label="b")
        self.assertEqual(tasks, [])
        self.assertIn("refine_grain record", skipped[FID])

    def test_a_pass_b_task_has_the_pass_b_suffix_in_its_id(self):
        with tempfile.TemporaryDirectory() as root:
            target, papers = _setup(root)
            b_tasks, _ = stage.make_tasks(target, papers, pass_label="b", redo=True)
            stage.apply_result(target, task_entry(b_tasks[0]), good(), PROV)
            tasks, _ = refine_grain.make_tasks(target, papers, pass_label="b")
        self.assertEqual(tasks[0].id, f"refine-{FID}-b")

    def test_the_context_carries_the_scoped_vocabulary_listing(self):
        with tempfile.TemporaryDirectory() as root:
            target, papers = _setup(root)
            tasks, _ = refine_grain.make_tasks(target, papers, pass_label="a")
        self.assertIn("intervention.cash_transfer", tasks[0].context)

    def test_already_refined_is_skipped_unless_redo(self):
        with tempfile.TemporaryDirectory() as root:
            target, papers = _setup(root)
            record = target.records.read(FID, "a")
            record["extractor"]["grain_refine_version"] = refine_grain.PROMPT_VERSION
            target.records.write(record, "a")
            tasks, skipped = refine_grain.make_tasks(target, papers, pass_label="a")
            self.assertEqual(tasks, [])
            self.assertIn("already refined", skipped[FID])
            tasks, _ = refine_grain.make_tasks(target, papers, pass_label="a", redo=True)
            self.assertEqual(len(tasks), 1)

    def test_an_unreadable_transcript_is_skipped(self):
        with tempfile.TemporaryDirectory() as root:
            target, papers = _setup(root)
            (Path(root) / papers[0].path).unlink()
            tasks, skipped = refine_grain.make_tasks(target, papers, pass_label="a")
        self.assertEqual(tasks, [])
        self.assertIn("cannot read the transcript", skipped[FID])

    def test_offers_the_same_pages_as_the_original_extraction(self):
        with tempfile.TemporaryDirectory() as root:
            target, papers = _setup(root)
            tasks, _ = refine_grain.make_tasks(target, papers, pass_label="a")
        refs = sorted(p.ref for p in tasks[0].passages)
        self.assertEqual(refs, sorted(f"page {n}" for n in PAGES))

    def test_each_pass_is_scoped_from_its_own_record_not_the_other_pass_s(self):
        """Pass a and pass b can currently disagree even on the coarse root (this is exactly the comparison
        scenario diff_records flags). Each pass's refine card must reflect its OWN current record's branch, not
        a shared/union scope -- otherwise a disagreement on the broad bucket would leak one pass's scope into
        the other's card."""
        vocabs = _hierarchical_vocabs()
        with tempfile.TemporaryDirectory() as root:
            make_index(root)
            records = RecordStore(Path(root) / ".index" / "study_records")
            target = stage.Target(str(root), records, vocabs, Proposals(records.dir))
            papers, _ = eligible_papers(str(root))
            a_result, b_result = good(), good()
            a_result["core"]["intervention"] = [{"value": "crop diversification",
                                                   "vocab_id": "intervention.crop_diversification",
                                                   "quote": "We study cash transfers in rural Somalia", "locator": 1}]
            b_result["core"]["intervention"] = [{"value": "land titling", "vocab_id": "intervention.land_titling_reform",
                                                   "quote": "We study cash transfers in rural Somalia", "locator": 1}]
            for result in (a_result, b_result):
                result["core"]["outcome"] = []
            a_tasks, _ = stage.make_tasks(target, papers, pass_label="a", redo=True)
            stage.apply_result(target, task_entry(a_tasks[0]), a_result, PROV)
            b_tasks, _ = stage.make_tasks(target, papers, pass_label="b", redo=True)
            stage.apply_result(target, task_entry(b_tasks[0]), b_result, PROV)
            refine_a, _ = refine_grain.make_tasks(target, papers, pass_label="a")
            refine_b, _ = refine_grain.make_tasks(target, papers, pass_label="b")
        self.assertIn("intervention.climate_adaption_mitigation_strategies", refine_a[0].context)
        self.assertNotIn("intervention.land_titling_reform", refine_a[0].context)
        self.assertIn("intervention.land_titling_reform", refine_b[0].context)
        self.assertNotIn("intervention.climate_adaption_mitigation_strategies", refine_b[0].context)


class TestApplyResult(unittest.TestCase):
    def test_merges_only_intervention_and_outcome_leaving_everything_else_untouched(self):
        with tempfile.TemporaryDirectory() as root:
            target, papers = _setup(root)
            before = target.records.read(FID, "a")
            tasks, _ = refine_grain.make_tasks(target, papers, pass_label="a")
            entry = task_entry(tasks[0])
            result = {"intervention": [{"value": "vouchers", "vocab_id": "intervention.voucher",
                                         "quote": "We study cash transfers in rural Somalia", "locator": 1}],
                      "outcome": []}
            refine_grain.apply_result(target, entry, result, PROV)
            after = target.records.read(FID, "a")
        self.assertEqual(after["core"]["intervention"], result["intervention"])
        self.assertEqual(after["core"]["outcome"], [])
        for key in ("study_design", "population", "sector", "data_sources", "geography", "results"):
            self.assertEqual(after["core"][key], before["core"][key])
        self.assertEqual(after["appraisal"], before["appraisal"])
        self.assertEqual(after["identity"], before["identity"])
        self.assertEqual(after["transcript_sha"], before["transcript_sha"])

    def test_sets_the_refine_version_marker_and_updates_only_the_two_vocab_versions(self):
        with tempfile.TemporaryDirectory() as root:
            target, papers = _setup(root)
            before_versions = dict(target.records.read(FID, "a")["extractor"]["vocab_versions"])
            tasks, _ = refine_grain.make_tasks(target, papers, pass_label="a")
            refine_grain.apply_result(target, task_entry(tasks[0]), {"intervention": [], "outcome": []}, PROV)
            after = target.records.read(FID, "a")
        self.assertEqual(after["extractor"]["grain_refine_version"], refine_grain.PROMPT_VERSION)
        self.assertEqual(after["extractor"]["vocab_versions"]["intervention"], target.vocabs["intervention"].version)
        self.assertEqual(after["extractor"]["vocab_versions"]["outcome"], target.vocabs["outcome"].version)
        for k, v in before_versions.items():
            if k not in ("intervention", "outcome"):
                self.assertEqual(after["extractor"]["vocab_versions"][k], v)

    def test_a_new_proposed_fact_is_filed_as_a_proposal(self):
        with tempfile.TemporaryDirectory() as root:
            target, papers = _setup(root)
            tasks, _ = refine_grain.make_tasks(target, papers, pass_label="a")
            entry = task_entry(tasks[0])
            result = {"intervention": [], "outcome": [{"value": "a brand new outcome", "proposed": True,
                                                         "quote": "raised household food consumption by twelve percent",
                                                         "locator": 3}]}
            refine_grain.apply_result(target, entry, result, PROV)
            self.assertEqual(len(target.proposals.open()), 1)
            self.assertEqual(target.proposals.open()[0]["value"], "a brand new outcome")

    def test_reconcile_runs_after_the_merge(self):
        with tempfile.TemporaryDirectory() as root:
            target, papers = _setup(root)
            b_tasks, _ = stage.make_tasks(target, papers, pass_label="b", redo=True)
            stage.apply_result(target, task_entry(b_tasks[0]), good(), PROV)
            # only pass a is refined to empty; pass b keeps good()'s real facts -- a genuine new mismatch that
            # proves reconcile re-diffed the whole record after this merge, not merely left the prior status alone
            tasks, _ = refine_grain.make_tasks(target, papers, pass_label="a")
            refine_grain.apply_result(target, task_entry(tasks[0]), {"intervention": [], "outcome": []}, PROV)
            record = target.records.read(FID, "a")
        self.assertEqual(record["review"]["status"], "needs_review")


class TestValidateResult(unittest.TestCase):
    def _entry(self):
        return {"passages": [{"id": "P1", "ref": "page 1", "text": PAGES[1]}]}

    def test_a_good_result_has_no_problems(self):
        from types import SimpleNamespace
        target = SimpleNamespace(vocabs=VOCABS)
        result = {"intervention": [{"value": "cash transfers", "vocab_id": "intervention.cash_transfer",
                                     "quote": "We study cash transfers in rural Somalia", "locator": 1}],
                  "outcome": []}
        self.assertEqual(refine_grain.validate_result(self._entry(), result, target), [])

    def test_an_unknown_vocab_id_is_reported(self):
        from types import SimpleNamespace
        target = SimpleNamespace(vocabs=VOCABS)
        result = {"intervention": [{"value": "x", "vocab_id": "intervention.nonexistent",
                                     "quote": "We study cash transfers in rural Somalia", "locator": 1}],
                  "outcome": []}
        problems = refine_grain.validate_result(self._entry(), result, target)
        self.assertTrue(any("intervention[0].vocab_id" in p for p in problems))

    def test_a_quote_not_on_the_offered_page_is_reported(self):
        from types import SimpleNamespace
        target = SimpleNamespace(vocabs=VOCABS)
        result = {"intervention": [], "outcome": [{"value": "x", "proposed": True,
                                                     "quote": "this sentence is not on the page", "locator": 1}]}
        problems = refine_grain.validate_result(self._entry(), result, target)
        self.assertTrue(any("outcome[0]" in p for p in problems))

    def test_an_unknown_top_level_key_is_reported(self):
        from types import SimpleNamespace
        target = SimpleNamespace(vocabs=VOCABS)
        result = {"intervention": [], "outcome": [], "sector": []}
        problems = refine_grain.validate_result(self._entry(), result, target)
        self.assertTrue(any("sector" in p for p in problems))

    def test_a_non_mapping_result_is_reported(self):
        from types import SimpleNamespace
        target = SimpleNamespace(vocabs=VOCABS)
        self.assertTrue(refine_grain.validate_result(self._entry(), "not a mapping", target))


class TestSubtreeListing(unittest.TestCase):
    def test_lists_every_term_under_the_given_roots_full_depth(self):
        from agent.literature.refine_grain import _subtree_listing
        vocabs = _hierarchical_vocabs()
        text = _subtree_listing(vocabs["intervention"], {"intervention.agriculture_forestry"})
        for tid in ("intervention.agriculture_forestry", "intervention.climate_adaption_mitigation_strategies",
                    "intervention.crop_diversification"):
            self.assertIn(tid, text)
        self.assertNotIn("intervention.land_titling_reform", text)
        self.assertNotIn("intervention.public_administration_2", text)

    def test_two_root_ids_combine_both_branches(self):
        from agent.literature.refine_grain import _subtree_listing
        vocabs = _hierarchical_vocabs()
        text = _subtree_listing(vocabs["intervention"],
                                 {"intervention.agriculture_forestry", "intervention.public_administration_2"})
        self.assertIn("intervention.crop_diversification", text)
        self.assertIn("intervention.land_titling_reform", text)

    def test_an_empty_root_set_is_an_empty_listing(self):
        from agent.literature.refine_grain import _subtree_listing
        vocabs = _hierarchical_vocabs()
        self.assertEqual(_subtree_listing(vocabs["intervention"], set()), "")


class TestVocabListingFor(unittest.TestCase):
    def _record(self, intervention=None, outcome=None, sector=None):
        return {"core": {"intervention": intervention or [], "outcome": outcome or [], "sector": sector or []}}

    def test_scopes_each_facet_to_its_own_roots(self):
        from agent.literature.refine_grain import _vocab_listing_for
        vocabs = _hierarchical_vocabs()
        record = self._record(
            intervention=[{"value": "x", "vocab_id": "intervention.crop_diversification", "quote": "q" * 10, "locator": 1}],
            outcome=[{"value": "y", "vocab_id": "outcome.crop_production", "quote": "q" * 10, "locator": 1}])
        text = _vocab_listing_for(record, vocabs)
        self.assertIn("intervention.climate_adaption_mitigation_strategies", text)
        self.assertIn("outcome.crop_production", text)
        self.assertNotIn("intervention.land_titling_reform", text)
        self.assertNotIn("outcome.public_administration", text)

    def test_falls_back_to_grouping_only_when_a_facet_has_no_anchor_at_all(self):
        from agent.literature.refine_grain import _vocab_listing_for
        vocabs = _hierarchical_vocabs()
        text = _vocab_listing_for(self._record(), vocabs)
        self.assertIn("Vocabulary intervention", text)
        self.assertIn("Vocabulary outcome", text)


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
