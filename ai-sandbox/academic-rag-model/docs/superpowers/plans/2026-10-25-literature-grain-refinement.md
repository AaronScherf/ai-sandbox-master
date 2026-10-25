# Literature Grain-Refinement Pass Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a new, narrower double-pass extraction stage (`refine_grain`) that re-extracts only `core.intervention` and `core.outcome` for all 62 papers, scoped per-paper to a full (untruncated) subtree of the vocabulary so the extractor can pick a specific leaf term instead of defaulting to the coarse bucket `_vocab_listing`'s `LISTING_LIMIT` collapse forces it into today.

**Architecture:** A new module `agent/literature/refine_grain.py`, parallel to `stage.py`, exposing the same duck-typed shape `core/agent_tasks/loop.py` expects from a stage module (`STAGE`, `make_tasks`, `validate_result`, `apply_result`). It computes a scoped vocabulary listing per paper (own current fact's root branch, falling back to `sector`, falling back to today's grouping-only listing), builds double-pass cards against the same transcripts, and on submit merges only the two facets back into the existing record -- every other field stays untouched. Wired into the CLI exactly like `verify`/`submit` already work: a new `refine-grain` subcommand, and one new entry in `cmd_submit`'s existing per-stage dispatch dict.

**Tech Stack:** Python 3.13, stdlib only for this change (no new dependencies). Existing `core.agent_tasks` task/record plumbing, existing `agent.literature.vocab`/`validate`/`compare`/`proposals`/`store` modules.

**Spec:** `docs/superpowers/specs/literature_taxonomy/2026-10-25-grain-refinement-design.md`

## Global Constraints

- Every field in a record other than `core.intervention` and `core.outcome` must be byte-for-byte unchanged by this pass (spec "Goal").
- Double-pass rigor is required: both pass "a" and pass "b" get independently-built cards, neither pass is shown the other's answer or the paper's own prior (possibly coarse) fact (spec "Goal", "Instructions").
- Scoping never derives one vocabulary's term id from another vocabulary's id or from a label-to-id string transformation; the 3ie taxonomy's own ids are inconsistent across vocabularies for the same real-world category (confirmed: the "Public Administration" root is `intervention.public_administration_2` but `outcome.public_administration` and `sector.public_administration` -- no suffix). Only `.label` string equality is a safe cross-vocabulary match (spec "Scoping rule actually used").
- `make_tasks`/`apply_result` only operate on a pass that already has an existing record (confirmed: all 62 papers already have both pass "a" and pass "b" records, so this is not a simplification that loses real cases -- it removes an edge case the spec's wording left ambiguous without changing what the rollout actually needs).
- No change to `stage.py`'s main extraction path, `compare.py`, or `tiers.py` -- this plan only adds new code and makes two small, backward-compatible additions to `cli.py`'s dispatch tables and one field to `tests/agent/literature/lit_helpers.py`'s `write_vocab_dir`.

## Review Focus

- A paper whose pass "a" and pass "b" currently disagree even on the coarse root term: each pass's new card must be scoped from *that pass's own* current record, not a shared/union scope -- Task 3's test with mismatched pass a/b roots.
- A paper with zero facts in a facet (6 for intervention, 4 for outcome in the real corpus) must still get a useful scoped listing via its `sector` fact(s), not an empty one -- Task 1's sector-fallback tests.
- The cross-vocabulary id-mismatch quirk (`intervention.public_administration_2` vs `outcome.public_administration`/`sector.public_administration`) must not silently produce an empty scope when falling back through `sector` -- Task 1's dedicated test reproducing this exact mismatch.
- A `proposed: true` fact (no `vocab_id`) in the paper's *current* intervention/outcome facts must not crash root-finding and must simply not contribute a root -- Task 1's test.
- `apply_result` must leave `study_design`, `population`, `sector`, `data_sources`, `results`, `geography`, `appraisal`, `identity`, `transcript_sha` and `review` exactly as they were before the merge, on both passes -- Task 5's primary test, the single most important guarantee of this whole feature.

---

## Task 1: Scoping -- `_root`, `scope_roots`, and a `write_vocab_dir` fix

**Files:**
- Create: `agent/literature/refine_grain.py`
- Modify: `tests/agent/literature/lit_helpers.py:84-91` (`write_vocab_dir` drops `parent` when serializing; needed so a worktree test that writes a hierarchical vocab to disk and reloads it actually sees the hierarchy)
- Test: `tests/agent/literature/test_lit_refine_grain.py`

**Interfaces:**
- Produces: `refine_grain._root(term_id: str | None, vocab) -> str | None` -- `term_id`'s top-level ancestor (a term with `parent is None`) in `vocab`, or `None` if `vocab` is `None` or `term_id` isn't one of its terms.
- Produces: `refine_grain._root_ids_from_facts(facts: list[dict] | None, vocab) -> set[str]` -- the `_root` of every fact's `vocab_id` in `facts` (skips facts with no `vocab_id`, i.e. `proposed: true` facts).
- Produces: `refine_grain._root_by_label(vocab, label: str) -> str | None` -- the id of `vocab`'s root term (`parent is None`) whose `.label == label`, or `None`.
- Produces: `refine_grain.scope_roots(record: dict, facet: str, vocab, sector_vocab) -> set[str]` -- root ids in `vocab` to expand in full for this paper's `facet` listing.

- [ ] **Step 1: Write the failing tests for `_root`, `_root_ids_from_facts`, `_root_by_label`, `scope_roots`**

Create `tests/agent/literature/test_lit_refine_grain.py`:

```python
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
        from agent.literature.refine_grain import Term as _unused  # noqa: F401  (sanity: label match is root-only)
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


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests to verify they fail with an import error**

Run: `python -m pytest tests/agent/literature/test_lit_refine_grain.py -v`
Expected: FAIL -- `ModuleNotFoundError: No module named 'agent.literature.refine_grain'`

- [ ] **Step 3: Create `agent/literature/refine_grain.py` with the scoping functions**

```python
"""Stage: re-extract only intervention/outcome, scoped to a full (untruncated) vocabulary branch per paper, so the
extractor can pick a specific term instead of defaulting to the coarse bucket stage.py's grouping-only listing
forces it into for a vocabulary over LISTING_LIMIT (docs/superpowers/specs/literature_taxonomy/
2026-10-25-grain-refinement-design.md, TODO-0085)."""
from __future__ import annotations


def _root(term_id: str | None, vocab) -> str | None:
    """`term_id`'s top-level ancestor (a term with no parent) in `vocab`, or None when `vocab` is None, `term_id`
    is None, or `term_id` isn't one of `vocab`'s terms."""
    if vocab is None or term_id is None or term_id not in vocab.terms:
        return None
    seen: set[str] = set()
    cur = term_id
    while vocab.terms[cur].parent and vocab.terms[cur].parent not in seen:
        seen.add(cur)
        cur = vocab.terms[cur].parent
    return cur


def _root_ids_from_facts(facts: list[dict] | None, vocab) -> set[str]:
    """The root of every fact's `vocab_id` in `facts`. A `proposed: true` fact has no `vocab_id` and contributes
    nothing -- it cannot anchor a branch."""
    return {r for f in (facts or []) if (r := _root(f.get("vocab_id"), vocab))}


def _root_by_label(vocab, label: str) -> str | None:
    """The id of `vocab`'s root term (parent is None) whose label equals `label`, or None. Matching by label, not
    id, because the 3ie taxonomy's ids for the same real-world category are not consistent across vocabularies
    (e.g. intervention's "Public Administration" root is `intervention.public_administration_2`, but outcome's
    and sector's are not `_2`-suffixed)."""
    if vocab is None:
        return None
    for term in vocab.terms.values():
        if term.parent is None and term.label == label:
            return term.id
    return None


def scope_roots(record: dict, facet: str, vocab, sector_vocab) -> set[str]:
    """Root ids in `vocab` to show in full for this paper's `facet` listing: the roots of its own current facts in
    that facet; if it has none, the roots (matched by label) implied by its `sector` facts instead. Empty when
    neither exists -- the caller then falls back to today's grouping-only listing for this facet."""
    core = record.get("core") or {}
    own = _root_ids_from_facts(core.get(facet), vocab)
    if own:
        return own
    sector_facts = core.get("sector") or []
    sector_ids = {f.get("vocab_id") for f in sector_facts if f.get("vocab_id")}
    labels = {sector_vocab.terms[sid].label for sid in sector_ids
              if sector_vocab is not None and sid in sector_vocab.terms}
    return {r for label in labels if (r := _root_by_label(vocab, label))}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/agent/literature/test_lit_refine_grain.py -v`
Expected: PASS (all of `TestRoot`, `TestRootIdsFromFacts`, `TestRootByLabel`, `TestScopeRoots`)

- [ ] **Step 5: Write the failing test for the `write_vocab_dir` parent-preservation fix**

Add to `tests/agent/literature/lit_helpers.py`'s own test coverage is none today (it's a fixture helper, not tested directly) -- instead, add this test to the new file, proving the round trip through disk preserves hierarchy (needed by Task 6's end-to-end CLI test later):

```python
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
```

- [ ] **Step 6: Run the test to verify it fails**

Run: `python -m pytest tests/agent/literature/test_lit_refine_grain.py::TestWriteVocabDirPreservesParent -v`
Expected: FAIL -- `AssertionError: None != 'intervention.climate_adaption_mitigation_strategies'` (today's `write_vocab_dir` drops `parent` when serializing)

- [ ] **Step 7: Fix `write_vocab_dir` in `tests/agent/literature/lit_helpers.py`**

Find (around line 84-91):

```python
def write_vocab_dir(directory, vocabs=None):
    """Writes the fixture vocabularies as vocab_data-style YAML files."""
    for name, v in (vocabs or VOCABS).items():
        data = {"vocabulary": name, "version": v.version, "provenance": v.provenance, "source": v.source,
                "terms": [{"id": t.id, "label": t.label, **({"definition": t.definition} if t.definition else {})}
                          for t in v.terms.values()]}
        (Path(directory) / f"{name}.yaml").write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
                                                       encoding="utf-8", newline="\n")
```

Replace with:

```python
def write_vocab_dir(directory, vocabs=None):
    """Writes the fixture vocabularies as vocab_data-style YAML files."""
    for name, v in (vocabs or VOCABS).items():
        data = {"vocabulary": name, "version": v.version, "provenance": v.provenance, "source": v.source,
                "terms": [{"id": t.id, "label": t.label,
                           **({"parent": t.parent} if t.parent else {}),
                           **({"definition": t.definition} if t.definition else {})}
                          for t in v.terms.values()]}
        (Path(directory) / f"{name}.yaml").write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
                                                       encoding="utf-8", newline="\n")
```

- [ ] **Step 8: Run the test to verify it passes, then run the full literature suite to confirm no regression**

Run: `python -m pytest tests/agent/literature/test_lit_refine_grain.py::TestWriteVocabDirPreservesParent -v`
Expected: PASS

Run: `python -m pytest tests/agent/literature/ -q`
Expected: all existing tests still pass (this fixture change only adds a key when `parent` is set; every existing fixture vocab is flat, so no existing written YAML gains a `parent` field)

- [ ] **Step 9: Commit**

```bash
git add agent/literature/refine_grain.py tests/agent/literature/test_lit_refine_grain.py tests/agent/literature/lit_helpers.py
git commit -m "feat(literature): grain-refinement scoping (_root, scope_roots)"
```

---

## Task 2: Scoped listing text -- `_subtree_listing`, `_vocab_listing_for`

**Files:**
- Modify: `agent/literature/refine_grain.py`
- Test: `tests/agent/literature/test_lit_refine_grain.py`

**Interfaces:**
- Consumes: `scope_roots(record, facet, vocab, sector_vocab) -> set[str]` (Task 1); `stage._vocab_listing(vocabs: dict) -> str` (existing, `agent/literature/stage.py`).
- Produces: `refine_grain._subtree_listing(vocab, root_ids: set[str]) -> str` -- every term in `vocab` whose root is in `root_ids`, one `- id: label` line per term (with `- definition` suffix when present), full depth.
- Produces: `refine_grain._vocab_listing_for(record: dict, vocabs: dict) -> str` -- the combined intervention + outcome listing for one paper's refine card.

- [ ] **Step 1: Write the failing tests**

Add to `tests/agent/literature/test_lit_refine_grain.py`:

```python
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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/agent/literature/test_lit_refine_grain.py::TestSubtreeListing tests/agent/literature/test_lit_refine_grain.py::TestVocabListingFor -v`
Expected: FAIL -- `ImportError: cannot import name '_subtree_listing'`

- [ ] **Step 3: Add `_subtree_listing` and `_vocab_listing_for` to `agent/literature/refine_grain.py`**

Append to the file:

```python
def _subtree_listing(vocab, root_ids: set[str]) -> str:
    """Every term in `vocab` whose top-level ancestor is in `root_ids` (the roots themselves included), full
    depth, no LISTING_LIMIT collapse -- one `- id: label` line per term."""
    lines = [f"- {t.id}: {t.label}" + (f" - {t.definition}" if t.definition else "")
             for t in vocab.terms.values() if _root(t.id, vocab) in root_ids]
    return "\n".join(lines)


def _vocab_listing_for(record: dict, vocabs: dict) -> str:
    """The scoped intervention/outcome listing for one paper's refine card. Falls back to stage._vocab_listing's
    existing grouping-only rendering for a facet when scope_roots finds nothing to anchor on (should not occur in
    practice -- every paper carries a sector fact -- but keeps today's behavior as a safety net rather than
    showing an empty listing)."""
    from .stage import _vocab_listing

    sector_vocab = vocabs.get("sector")
    lines: list[str] = []
    for facet in ("intervention", "outcome"):
        vocab = vocabs.get(facet)
        if vocab is None:
            continue
        roots = scope_roots(record, facet, vocab, sector_vocab)
        if roots:
            lines += ["", f"Vocabulary {facet} (version {vocab.version}, {vocab.provenance}; scoped to this "
                           "paper's own category, full depth, no grouping collapse):",
                      _subtree_listing(vocab, roots)]
        else:
            # facet name and vocabulary name coincide for intervention/outcome (schema.FACETS maps each to
            # itself), so this single-entry dict is exactly what stage._vocab_listing expects.
            lines.append(_vocab_listing({facet: vocab}))
    return "\n".join(lines)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/agent/literature/test_lit_refine_grain.py -v`
Expected: PASS (all tests so far)

- [ ] **Step 5: Commit**

```bash
git add agent/literature/refine_grain.py tests/agent/literature/test_lit_refine_grain.py
git commit -m "feat(literature): scoped vocabulary listing for grain refinement"
```

---

## Task 3: `make_tasks`

**Files:**
- Modify: `agent/literature/refine_grain.py`
- Test: `tests/agent/literature/test_lit_refine_grain.py`

**Interfaces:**
- Consumes: `_vocab_listing_for(record, vocabs)` (Task 2); `stage.Target`, `stage.MAX_CARD_CHARS`, `stage._offered_pages`, `stage._sha` (existing, `agent/literature/stage.py`); `papers.Paper` (existing, `agent/literature/papers.py`); `transcript.split_pages` (existing, `agent/literature/transcript.py`); `core.agent_tasks.tasks.Task`, `core.agent_tasks.tasks.Passage` (existing).
- Produces: `refine_grain.STAGE = "refine_grain"`; `refine_grain.PROMPT_VERSION = "refine-v1"`; `refine_grain.INSTRUCTIONS: str`; `refine_grain.make_tasks(target: stage.Target, papers: list[Paper], *, pass_label: str = "a", redo: bool = False) -> tuple[list[Task], dict[str, str]]`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/agent/literature/test_lit_refine_grain.py`:

```python
import tempfile
from pathlib import Path

from agent.literature import refine_grain, stage
from agent.literature.papers import eligible_papers
from agent.literature.proposals import Proposals
from agent.literature.store import RecordStore
from core.agent_tasks.work import task_entry
from lit_helpers import PAGES, VOCABS, good, make_index

PROV = {"driver": "agent", "agent": "antigravity", "run": "r1"}
FID = "0123456789abcdef"


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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/agent/literature/test_lit_refine_grain.py::TestMakeTasks -v`
Expected: FAIL -- `AttributeError: module 'agent.literature.refine_grain' has no attribute 'make_tasks'`

- [ ] **Step 3: Add `STAGE`, `PROMPT_VERSION`, `INSTRUCTIONS`, `make_tasks` to `agent/literature/refine_grain.py`**

Add these imports at the top of the file, just below the module docstring:

```python
from pathlib import Path

from core.agent_tasks.tasks import Passage, Task

from .papers import Paper
from .stage import MAX_CARD_CHARS, Target, _sha
from .transcript import split_pages
```

Append to the file:

```python
STAGE = "refine_grain"
PROMPT_VERSION = "refine-v1"

INSTRUCTIONS = """\
Below is this paper's intervention and outcome vocabulary, narrowed to the specific category this paper already
uses (full depth, not the usual grouping-only view). Re-identify this paper's intervention and outcome facts from
the pages listed under "Offered passages", picking the most specific listed term that fits -- do not settle for a
broad category when a listed child describes the paper's own wording better. Answer as a YAML mapping under
`## Result`:

  intervention: [{value: "cash transfers", vocab_id: "intervention.cash_transfer", quote: "...", locator: 4}]
  outcome: [{value: "food consumption", proposed: true, quote: "...", locator: 3}]

Rules:
- State only what the paper itself says; do not extract from the reference list or from other papers it cites.
- Every fact needs a `quote` copied exactly from the page text (8 to 300 characters) and a `locator`: the page
  number, or a list of page numbers.
- Use a `vocab_id` from the listing below when a term fits, picking the most specific one. If none fits, write
  `proposed: true` instead of a `vocab_id` and a short `value`. Never give both. Do not propose a term that is
  already listed.
- Be complete: list every distinct intervention and outcome the study itself reports, not only the main one.
- Write [] for a facet the paper does not give."""


def make_tasks(target: Target, papers: list[Paper], *, pass_label: str = "a", redo: bool = False):
    """Cards that re-extract only intervention and outcome, scoped to each paper's own vocabulary branch. Only
    builds a task for a paper that already has a record for `pass_label` -- every one of the real 62 papers
    already has both passes, so this is not a narrowing of the real rollout, just a precondition the merge step
    (apply_result) needs satisfied."""
    tasks: list[Task] = []
    skipped: dict[str, str] = {}
    for paper in papers:
        record = target.records.read(paper.file_id, pass_label)
        if record is None:
            skipped[paper.file_id] = "no refine_grain record for this pass yet (run collect --double first)"
            continue
        try:
            md = (Path(target.index_root) / paper.path).read_text(encoding="utf-8")
        except OSError as exc:
            skipped[paper.file_id] = f"cannot read the transcript: {exc}"
            continue
        pages = split_pages(md)
        if not pages:
            skipped[paper.file_id] = "transcript has no page markers"
            continue
        size = sum(len(t) for t in pages.values())
        if size > MAX_CARD_CHARS:
            skipped[paper.file_id] = (f"transcript is {size} characters, over the {MAX_CARD_CHARS} limit for one "
                                      "card (chunked extraction is not built)")
            continue
        sha = _sha(md)
        if (not redo and record.get("extractor", {}).get("grain_refine_version") == PROMPT_VERSION
                and record.get("transcript_sha") == sha):
            skipped[paper.file_id] = "already refined (use --redo to refine again)"
            continue
        context = "\n".join([f"Paper: {paper.title or paper.file_id}", f"file_id: {paper.file_id}",
                             _vocab_listing_for(record, target.vocabs)])
        passages = [Passage(id=f"P{n}", source=paper.title or paper.file_id, ref=f"page {n}", text=text)
                    for n, text in sorted(pages.items())]
        task_id = f"refine-{paper.file_id}" if pass_label == "a" else f"refine-{paper.file_id}-{pass_label}"
        tasks.append(Task(id=task_id, stage=STAGE, subject={"file_id": paper.file_id, "pass": pass_label,
                                                              "transcript_sha": sha},
                           instructions=INSTRUCTIONS, context=context, passages=passages))
    return tasks, skipped
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/agent/literature/test_lit_refine_grain.py::TestMakeTasks -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agent/literature/refine_grain.py tests/agent/literature/test_lit_refine_grain.py
git commit -m "feat(literature): refine_grain.make_tasks"
```

---

## Task 4: `validate_result`

**Files:**
- Modify: `agent/literature/refine_grain.py`
- Test: `tests/agent/literature/test_lit_refine_grain.py`

**Interfaces:**
- Consumes: `validate._facts(path, facts, vocabs, vocab_name, pages, extra_keys=()) -> list[str]` (existing, `agent/literature/validate.py`); `stage._offered_pages(entry) -> dict[int, str]` (existing).
- Produces: `refine_grain.validate_result(entry: dict, result, target) -> list[str]`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/agent/literature/test_lit_refine_grain.py`:

```python
from types import SimpleNamespace


class TestValidateResult(unittest.TestCase):
    def _entry(self):
        return {"passages": [{"id": "P1", "ref": "page 1", "text": PAGES[1]}]}

    def test_a_good_result_has_no_problems(self):
        target = SimpleNamespace(vocabs=VOCABS)
        result = {"intervention": [{"value": "cash transfers", "vocab_id": "intervention.cash_transfer",
                                     "quote": "We study cash transfers in rural Somalia", "locator": 1}],
                  "outcome": []}
        self.assertEqual(refine_grain.validate_result(self._entry(), result, target), [])

    def test_an_unknown_vocab_id_is_reported(self):
        target = SimpleNamespace(vocabs=VOCABS)
        result = {"intervention": [{"value": "x", "vocab_id": "intervention.nonexistent",
                                     "quote": "We study cash transfers in rural Somalia", "locator": 1}],
                  "outcome": []}
        problems = refine_grain.validate_result(self._entry(), result, target)
        self.assertTrue(any("intervention[0].vocab_id" in p for p in problems))

    def test_a_quote_not_on_the_offered_page_is_reported(self):
        target = SimpleNamespace(vocabs=VOCABS)
        result = {"intervention": [], "outcome": [{"value": "x", "proposed": True,
                                                     "quote": "this sentence is not on the page", "locator": 1}]}
        problems = refine_grain.validate_result(self._entry(), result, target)
        self.assertTrue(any("outcome[0]" in p for p in problems))

    def test_an_unknown_top_level_key_is_reported(self):
        target = SimpleNamespace(vocabs=VOCABS)
        result = {"intervention": [], "outcome": [], "sector": []}
        problems = refine_grain.validate_result(self._entry(), result, target)
        self.assertTrue(any("sector" in p for p in problems))

    def test_a_non_mapping_result_is_reported(self):
        target = SimpleNamespace(vocabs=VOCABS)
        self.assertTrue(refine_grain.validate_result(self._entry(), "not a mapping", target))
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/agent/literature/test_lit_refine_grain.py::TestValidateResult -v`
Expected: FAIL -- `AttributeError: module 'agent.literature.refine_grain' has no attribute 'validate_result'`

- [ ] **Step 3: Add `validate_result` to `agent/literature/refine_grain.py`**

Add this import near the top (with the others added in Task 3):

```python
from .stage import _offered_pages
from .validate import _facts
```

Append to the file:

```python
def validate_result(entry: dict, result, target) -> list[str]:
    if not isinstance(result, dict):
        return ["result: must be a mapping with intervention and outcome lists"]
    out = [f"result: unknown key {k!r}" for k in sorted(set(result) - {"intervention", "outcome"})]
    pages = _offered_pages(entry)
    out += _facts("intervention", result.get("intervention"), target.vocabs, "intervention", pages)
    out += _facts("outcome", result.get("outcome"), target.vocabs, "outcome", pages)
    return out
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/agent/literature/test_lit_refine_grain.py::TestValidateResult -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agent/literature/refine_grain.py tests/agent/literature/test_lit_refine_grain.py
git commit -m "feat(literature): refine_grain.validate_result"
```

---

## Task 5: `apply_result` (the merge-back)

**Files:**
- Modify: `agent/literature/refine_grain.py`
- Test: `tests/agent/literature/test_lit_refine_grain.py`

**Interfaces:**
- Consumes: `target.records.read(file_id, pass_label) -> dict | None`, `target.records.write(record, pass_label)` (existing, `agent/literature/store.py`); `target.proposals.add(file_id, vocabulary, value, quote, locator, pass_label) -> bool` (existing, `agent/literature/proposals.py`); `compare.reconcile(records, file_id, vocabs) -> None` (existing, `agent/literature/compare.py`).
- Produces: `refine_grain.apply_result(target, entry: dict, result: dict, provenance: dict) -> str | None`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/agent/literature/test_lit_refine_grain.py`:

```python
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
            for label in ("a", "b"):
                tasks, _ = refine_grain.make_tasks(target, papers, pass_label=label)
                refine_grain.apply_result(target, task_entry(tasks[0]), {"intervention": [], "outcome": []}, PROV)
            record = target.records.read(FID, "a")
        # both passes now say [] for intervention/outcome where good() had real facts -- reconcile must have
        # re-diffed the whole record and flagged the (new) disagreement, proving it ran after the merge
        self.assertEqual(record["review"]["status"], "needs_review")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/agent/literature/test_lit_refine_grain.py::TestApplyResult -v`
Expected: FAIL -- `AttributeError: module 'agent.literature.refine_grain' has no attribute 'apply_result'`

- [ ] **Step 3: Add `apply_result` to `agent/literature/refine_grain.py`**

Add this import near the top (with the others):

```python
from .compare import reconcile
```

Append to the file:

```python
def apply_result(target: Target, entry: dict, result: dict, provenance: dict) -> str | None:
    s = entry["subject"]
    fid, label = s["file_id"], s["pass"]
    record = target.records.read(fid, label)
    record["core"]["intervention"] = result.get("intervention") or []
    record["core"]["outcome"] = result.get("outcome") or []
    extractor = dict(record.get("extractor") or {})
    extractor["grain_refine_version"] = PROMPT_VERSION
    vocab_versions = dict(extractor.get("vocab_versions") or {})
    for facet in ("intervention", "outcome"):
        vocab = target.vocabs.get(facet)
        if vocab is not None:
            vocab_versions[facet] = vocab.version
    extractor["vocab_versions"] = vocab_versions
    record["extractor"] = extractor
    target.records.write(record, label)
    for facet in ("intervention", "outcome"):
        for fact in result.get(facet) or []:
            if fact.get("proposed"):
                target.proposals.add(fid, facet, fact["value"], fact["quote"], fact["locator"], label)
    reconcile(target.records, fid, target.vocabs)
    return None
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/agent/literature/test_lit_refine_grain.py -v`
Expected: PASS (every test in the file so far)

- [ ] **Step 5: Commit**

```bash
git add agent/literature/refine_grain.py tests/agent/literature/test_lit_refine_grain.py
git commit -m "feat(literature): refine_grain.apply_result"
```

---

## Task 6: CLI wiring (`refine-grain` subcommand, `submit` dispatch)

**Files:**
- Modify: `agent/literature/cli.py`
- Test: `tests/agent/literature/test_lit_cli.py`

**Interfaces:**
- Consumes: `refine_grain.STAGE`, `refine_grain.make_tasks` (Task 3); `core.agent_tasks.loop.collect_run` (existing, already imported in `cli.py`).

- [ ] **Step 1: Write the failing tests**

Add to `tests/agent/literature/test_lit_cli.py`:

```python
class TestRefineGrain(unittest.TestCase):
    def _collected(self, root):
        env = Env(root)
        _run(env.args("collect", "--run-id", "c1", "--double"))
        fill_card(env.card("c1", f"extract-{FID}"), good())
        fill_card(env.card("c1", f"extract-{FID}-b"), good())
        _run(env.args("submit", "c1"))
        return env

    def test_stages_a_card_for_each_pass(self):
        with tempfile.TemporaryDirectory() as root:
            env = self._collected(root)
            code, out = _run(env.args("refine-grain", "--run-id", "r1"))
            self.assertEqual(code, 0)
            self.assertTrue(env.card("r1", f"refine-{FID}").is_file())
            self.assertTrue(env.card("r1", f"refine-{FID}-b").is_file())

    def test_submit_merges_the_filled_card_without_disturbing_other_fields(self):
        with tempfile.TemporaryDirectory() as root:
            env = self._collected(root)
            before = json.loads((Path(root) / ".index" / "study_records" / f"{FID}.json").read_text(encoding="utf-8"))
            _run(env.args("refine-grain", "--run-id", "r1"))
            fill_card(env.card("r1", f"refine-{FID}"), {"intervention": [], "outcome": []})
            fill_card(env.card("r1", f"refine-{FID}-b"), {"intervention": [], "outcome": []})
            code, _ = _run(env.args("submit", "r1"))
            after = json.loads((Path(root) / ".index" / "study_records" / f"{FID}.json").read_text(encoding="utf-8"))
        self.assertEqual(code, 0)
        self.assertEqual(after["core"]["intervention"], [])
        self.assertEqual(after["core"]["study_design"], before["core"]["study_design"])
        self.assertEqual(after["core"]["data_sources"], before["core"]["data_sources"])

    def test_file_id_filters_to_one_paper(self):
        with tempfile.TemporaryDirectory() as root:
            env = self._collected(root)
            make_index(root, file_id="1111111111111111", title="A different paper")
            _run(env.args("collect", "--run-id", "c2", "--file-id", "1111111111111111"))
            fill_card(env.card("c2", "extract-1111111111111111"), good())
            _run(env.args("submit", "c2"))
            code, out = _run(env.args("refine-grain", "--run-id", "r1", "--file-id", FID))
        self.assertEqual(code, 0)
        self.assertTrue(env.card("r1", f"refine-{FID}").is_file())
        self.assertFalse(env.card("r1", "refine-1111111111111111").is_file())

    def test_the_scoped_listing_reaches_the_card_through_real_vocab_files_on_disk(self):
        from lit_helpers import write_vocab_dir
        from test_lit_refine_grain import _hierarchical_vocabs

        with tempfile.TemporaryDirectory() as root:
            vocab_dir = Path(root) / "vocabs"
            vocab_dir.mkdir()
            write_vocab_dir(vocab_dir, _hierarchical_vocabs())
            make_index(root)
            result = good()
            result["core"]["intervention"] = [{"value": "crop diversification",
                                                "vocab_id": "intervention.crop_diversification",
                                                "quote": "We study cash transfers in rural Somalia", "locator": 1}]
            result["core"]["outcome"] = [{"value": "crop production", "vocab_id": "outcome.crop_production",
                                           "quote": "raised household food consumption by twelve percent", "locator": 3}]
            argv_base = ["--index-root", root, "--vocab-dir", str(vocab_dir)]
            _run([*argv_base, "collect", "--run-id", "c1"])
            fill_card(Path(root) / ".agent_work" / "c1" / "cards" / f"extract-{FID}.md", result)
            _run([*argv_base, "submit", "c1"])
            _run([*argv_base, "refine-grain", "--run-id", "r1"])
            card_text = (Path(root) / ".agent_work" / "r1" / "cards" / f"refine-{FID}.md").read_text(encoding="utf-8")
        # the scoped listing must show the sibling child term, not just the root the paper already had
        self.assertIn("intervention.climate_adaption_mitigation_strategies", card_text)
        self.assertNotIn("intervention.land_titling_reform", card_text)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/agent/literature/test_lit_cli.py::TestRefineGrain -v`
Expected: FAIL -- `SystemExit` / argparse error (`invalid choice: 'refine-grain'`), since the subcommand does not exist yet

- [ ] **Step 3: Wire `refine_grain` into `agent/literature/cli.py`**

Find (around line 12):

```python
from . import cluster as clusters, contribute, db as litdb, review, stage, synth, tiers, verify
```

Replace with:

```python
from . import cluster as clusters, contribute, db as litdb, refine_grain, review, stage, synth, tiers, verify
```

Find `cmd_verify` (around line 106-123) and add a new function directly after it:

```python
def cmd_refine_grain(args) -> int:
    target = _target(args)
    papers, _ = eligible_papers(args.index_root)
    if args.file_id:
        papers = [p for p in papers if p.file_id in set(args.file_id)]
    tasks, skipped = refine_grain.make_tasks(target, papers, pass_label="a", redo=args.redo)
    b_tasks, b_skipped = refine_grain.make_tasks(target, papers, pass_label="b", redo=args.redo)
    tasks += b_tasks
    skipped.update({f"{k} (pass b)": v for k, v in b_skipped.items()})
    for fid, reason in skipped.items():
        print(f"skipped {fid}: {reason}")
    try:
        run = collect_run(refine_grain.STAGE, tasks, _work_root(args), target.records.dir, run_id=args.run_id, repo_label="records")
    except (ValueError, FileExistsError) as exc:
        print(f"cannot create the run: {exc}")
        return 2
    if run is None:
        print("nothing to refine")
        return 0
    print(f"collected {len(tasks)} refine-grain card(s) in run {run.run_id}: {run.root}")
    return 0
```

Find `cmd_submit` (around line 96-103):

```python
def cmd_submit(args) -> int:
    run = _load(args)
    if run is None:
        return 2
    module = {verify.STAGE: verify, contribute.STAGE: contribute, synth.STAGE: synth}.get(run.stage, stage)
    report = submit_run(run, module, _target(args), args.agent_name, provenance_fn=provenance, target_label="study records")
    _print_report(report)
    return 0
```

Replace the `module = ` line with:

```python
    module = {verify.STAGE: verify, contribute.STAGE: contribute, synth.STAGE: synth,
              refine_grain.STAGE: refine_grain}.get(run.stage, stage)
```

Find the `verify` subparser block (around line 382-386):

```python
    v = sub.add_parser("verify", help="Write cards that ask for an independent check of facts only one pass found.")
    v.add_argument("--file-id", action="append", default=[], help="Only this paper (repeatable).")
    v.add_argument("--run-id", default=None)
    v.add_argument("--redo", action="store_true", help="Verify again even if the paper was already verified.")
    v.add_argument("--full-paper", action="store_true", help="Second look: offer the whole paper for facts the first check did not support.")
```

Add directly after it:

```python
    rg = sub.add_parser("refine-grain", help="Re-extract only intervention/outcome, scoped to each paper's own vocabulary branch (TODO-0085).")
    rg.add_argument("--file-id", action="append", default=[], help="Only this paper (repeatable).")
    rg.add_argument("--run-id", default=None)
    rg.add_argument("--redo", action="store_true", help="Refine again even if the paper was already refined.")
```

Find the dispatch dict in `main` (around line 436-438):

```python
    return {"collect": cmd_collect, "verify": cmd_verify, "silver": cmd_silver, "submit": cmd_submit, "bootstrap": cmd_bootstrap, "status": cmd_status,
            "proposals": cmd_proposals, "eval": cmd_eval, "remap": cmd_remap, "tiers": cmd_tiers, "backfill-years": cmd_backfill_years,
            "cluster": cmd_cluster, "annotate": cmd_annotate, "synthesize": cmd_synthesize, "render": cmd_render, "db": cmd_db}[args.command](args)
```

Replace with:

```python
    return {"collect": cmd_collect, "verify": cmd_verify, "silver": cmd_silver, "submit": cmd_submit, "bootstrap": cmd_bootstrap, "status": cmd_status,
            "proposals": cmd_proposals, "eval": cmd_eval, "remap": cmd_remap, "tiers": cmd_tiers, "backfill-years": cmd_backfill_years,
            "cluster": cmd_cluster, "annotate": cmd_annotate, "synthesize": cmd_synthesize, "render": cmd_render, "db": cmd_db,
            "refine-grain": cmd_refine_grain}[args.command](args)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/agent/literature/test_lit_cli.py::TestRefineGrain -v`
Expected: PASS

- [ ] **Step 5: Run the full literature test suite to confirm no regression**

Run: `python -m pytest tests/agent/literature/ -q`
Expected: all tests pass, no change to the count of pre-existing tests' outcomes

- [ ] **Step 6: Update `agent/literature/README.md`'s command list**

Find the `backfill-years` line added in the earlier years-backfill work:

```
python -m agent.literature backfill-years [--mailto you@example.com]  # fill publication_year from OpenAlex, no LLM
```

Add directly after it:

```
python -m agent.literature refine-grain [--file-id ID] [--redo]       # re-extract only intervention/outcome, scoped per paper (TODO-0085)
```

- [ ] **Step 7: Commit**

```bash
git add agent/literature/cli.py agent/literature/README.md tests/agent/literature/test_lit_cli.py
git commit -m "feat(literature): wire refine-grain into the CLI and submit dispatch"
```

---

## Rollout (not a coding task -- run after all six tasks land)

Once the branch is landed, run the pass for all 62 real papers:

```bash
python -m agent.literature --index-root <research> --vocab-dir <resources/3ie/vocab> refine-grain --run-id grain1
# relay all 124 cards through Antigravity/Gemini, same workflow as the original extraction
python -m agent.literature --index-root <research> --vocab-dir <resources/3ie/vocab> submit grain1
# each record's verification block still has its pre-refinement transcript_sha, so verify would otherwise skip
# every paper as "already verified" and leave new single-pass facts stuck open in the confidence tiers
python -m agent.literature --index-root <research> --vocab-dir <resources/3ie/vocab> verify --redo
python -m agent.literature --index-root <research> --vocab-dir <resources/3ie/vocab> verify --full-paper --redo
python -m agent.literature --index-root <research> --vocab-dir <resources/3ie/vocab> db build
```

Then recheck the intervention/outcome label distributions against today's baseline (34 papers on "Climate
adaption & mitigation strategies"; "Agriculture & Forestry" appearing as an intervention) to confirm the fix
actually reduced the coarse-bucket concentration, per the spec's "Rollout" section.
