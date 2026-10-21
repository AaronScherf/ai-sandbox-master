# Stage 3 Literature Synthesis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the stage 2 study records of a facet-defined group of papers into a local-only literature review and annotated bibliography in which every citation and number is mechanically traceable.

**Architecture:** Five small modules in `agent/literature/`: `cluster` (membership by tier A/B facets), `annotation` (deterministic per-paper annotation and citation keys), `contribute` (`annotate` stage: a one-sentence contribution and limitation per paper), `synth` (`synthesize` stage: chunk cards, an optional merge card, and a mechanical citation and number validator), `review` (deterministic rendering). They reuse `core/agent_tasks` (cards, runs, `submit_run`) exactly as the `extract` and `verify` stages do; the CLI routes `submit` by the run's stage.

**Tech Stack:** Python 3.13, PyYAML, `unittest`/pytest, existing `core.agent_tasks`, `agent.literature.{tiers,verify,stage,transcript}`.

**Spec:** `docs/superpowers/specs/literature_taxonomy/2026-10-21-stage3-synthesis-design.md` (umbrella: `2026-10-15-literature-taxonomy-pipeline-design.md`). Working directory for every command: `ai-sandbox/academic-rag-model/` inside the `claude-literature-synthesis` worktree; interpreter `C:\Users\theaa\ai-sandbox-master\ai-sandbox\academic-rag-model\.venv\Scripts\python.exe` (below written `$PY`). Run tests with `PYTHONPATH=tests/agent/literature $PY -m pytest tests/agent/literature -q`.

## Global Constraints

- Output lives only under `<index-root>/literature_reviews/<topic>/` (index root is `ai-sandbox/research`); it is gitignored. No paper text, quote or 3ie wording is ever committed: tests use the synthetic fixtures in `lit_helpers.py`.
- Only facts in confidence tiers A and B (`tiers.at_least(items, "B")`) feed annotations and synthesis.
- No paid API calls; cards are filled by the subscription agent (Antigravity) and checked by `submit`.
- Run folders (`.agent_work/<run>`) must not sit inside the output folder (`create_run` already refuses).
- The bibliography is built only from the index card, the record and the annotation files, never from model prose in the synthesis.
- Stage files use the repo's existing style: module docstring, `from __future__ import annotations`, no new dependencies.
- Stage ids: `annotate`, `synthesize`. Task ids: `annotate-<file_id>`, `synth-c<N>` (chunk cards), `synth-final` (single card or merge card).
- Commit messages end with `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`; stage explicit paths only.

## Review Focus

- A cluster that matches no paper, or a constraint naming a term that does not exist, must fail loudly instead of producing an empty review.
- A cluster with unannotated papers must refuse to synthesize and list the missing papers.
- A paragraph whose number appears only in prose, or only in an uncited paper, must bounce with the number named.
- Two papers with the same title and year must get different citation keys.
- `render` before the final synthesis exists (chunks accepted, merge missing) must say what is missing, not write a partial review.

## File Structure

| File | Responsibility |
| --- | --- |
| `agent/literature/cluster.py` | `Cluster`, constraint parsing, membership, `cluster.yaml` read/write, `topic_dir` |
| `agent/literature/annotation.py` | `annotation_of`, `render_annotation_md`, `cite_key` |
| `agent/literature/contribute.py` | `annotate` stage: `make_tasks`, `validate_result`, `apply_result`, `load_annotations` |
| `agent/literature/synth.py` | `synthesize` stage: ids, chunking, `check_sections`, chunk and merge cards, `apply_result` |
| `agent/literature/review.py` | `render`: `review.md` and `bibliography.md` |
| `agent/literature/cli.py` | `cluster`, `annotate`, `synthesize`, `render` commands; `submit` routing |
| `tests/agent/literature/synth_helpers.py` | fixture builder shared by the new tests |
| `tests/agent/literature/test_lit_{cluster,annotation,contribute,synth,review,synthesis_cli}.py` | tests |
| `.gitignore`, `agent/literature/README.md`, `docs/status/literature/2026-10-22-stage3-synthesis.md` | ignore rule, usage, status |

---

### Task 1: Ignore rule and shared test fixture

**Files:**
- Modify: `../../.gitignore` (repo root `.gitignore`, add after the `study_records/` line)
- Create: `tests/agent/literature/synth_helpers.py`

**Interfaces:**
- Produces: `synth_helpers.build(root, results: dict[str, dict]) -> (Target, list[Paper])` (each file_id gets an index card with `publication_year` 2019 and title `Paper <file_id>`, then two extraction passes with that result), `synth_helpers.with_sector(result)`, constants `F1="aaaaaaaaaaaaaaaa"`, `F2="bbbbbbbbbbbbbbbb"`, `F3="cccccccccccccccc"`.

- [ ] **Step 1: Add the ignore rule**

In the root `.gitignore`, directly after the line `ai-sandbox/research/.index/study_records/`, add:

```
# Stage 3 literature reviews quote paper text: local only.
ai-sandbox/research/literature_reviews/
```

- [ ] **Step 2: Verify git ignores it**

Run (from the worktree root): `git check-ignore -v ai-sandbox/research/literature_reviews/x/review.md`
Expected: prints the `.gitignore` line that matches.

- [ ] **Step 3: Write the fixture**

```python
"""Fixture builder for the stage 3 tests: several papers, each extracted twice with a given result."""
import copy
from pathlib import Path

from agent.literature import stage
from agent.literature.papers import eligible_papers
from agent.literature.proposals import Proposals
from agent.literature.store import RecordStore
from core.agent_tasks.work import task_entry
from lit_helpers import VOCABS, good, make_index

PROV = {"driver": "agent", "agent": "antigravity", "run": "r1"}
F1, F2, F3 = "a" * 16, "b" * 16, "c" * 16


def with_sector(result):
    out = copy.deepcopy(result)
    out["core"]["sector"] = [{"value": "social protection", "vocab_id": "sector.social_protection",
                              "quote": "We study cash transfers in rural Somalia", "locator": 1}]
    return out


def build(root, results: dict):
    for fid in results:
        make_index(root, fid, title=f"Paper {fid}", card_extra={"publication_year": 2019})
    records = RecordStore(Path(root) / ".index" / "study_records")
    target = stage.Target(str(root), records, VOCABS, Proposals(records.dir))
    papers, _ = eligible_papers(str(root))
    for label in ("a", "b"):
        tasks, _ = stage.make_tasks(target, papers, pass_label=label, redo=True)
        for t in tasks:
            stage.apply_result(target, task_entry(t), results[t.subject["file_id"]], PROV)
    return target, papers


def three_papers():
    """F1 and F3 are social protection papers on cash transfers; F2 is a voucher paper with no sector."""
    voucher = copy.deepcopy(good())
    voucher["core"]["intervention"][0].update(vocab_id="intervention.voucher", value="vouchers")
    return {F1: with_sector(good()), F2: voucher, F3: with_sector(good())}
```

- [ ] **Step 4: Check the fixture builds**

Run: `PYTHONPATH=tests/agent/literature $PY -c "import tempfile; from synth_helpers import *; d=tempfile.mkdtemp(); t,p=build(d, three_papers()); print(len(p), t.records.ids())"`
Expected: `3 ['aaaaaaaaaaaaaaaa', 'bbbbbbbbbbbbbbbb', 'cccccccccccccccc']`

- [ ] **Step 5: Commit**

```bash
git add .gitignore ai-sandbox/academic-rag-model/tests/agent/literature/synth_helpers.py
git commit -m "test(literature): stage 3 fixture builder; ignore research/literature_reviews"
```

---

### Task 2: Cluster membership

**Files:**
- Create: `agent/literature/cluster.py`
- Test: `tests/agent/literature/test_lit_cluster.py`

**Interfaces:**
- Consumes: `tiers.tiered_facts(records, fid, vocabs)`, `tiers.at_least(items, floor)`, `compare._ancestors(vid, vocab)`, `schema.FACETS`, `transcript.normalize`.
- Produces: `FACETS`, `ClusterError`, `Cluster(name, constraints, floor, file_ids)`, `topic_dir(index_root, name) -> Path`, `parse_constraint(text) -> {"facet","value"}`, `define_cluster(records, vocabs, name, where, floor="B") -> Cluster`, `save_cluster(index_root, cluster) -> Path`, `load_cluster(index_root, name) -> Cluster`.

- [ ] **Step 1: Write the failing tests**

```python
import tempfile
import unittest

from agent.literature.cluster import (ClusterError, define_cluster, load_cluster, parse_constraint,
                                      save_cluster, topic_dir)
from lit_helpers import VOCABS
from synth_helpers import F1, F2, F3, build, three_papers


class TestCluster(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.target, _ = build(self.tmp.name, three_papers())

    def define(self, *where, floor="B"):
        return define_cluster(self.target.records, VOCABS, "demo", list(where), floor)

    def test_papers_join_when_every_constraint_matches_a_tier_a_or_b_fact(self):
        self.assertEqual(self.define("sector=social protection").file_ids, [F1, F3])
        self.assertEqual(self.define("intervention=voucher").file_ids, [F2])
        self.assertEqual(self.define("sector=social protection", "intervention=cash transfer").file_ids, [F1, F3])
        self.assertEqual(self.define("sector=social protection", "intervention=voucher").file_ids, [])

    def test_a_term_id_and_a_country_code_work_as_values(self):
        self.assertEqual(self.define("sector=sector.social_protection").file_ids, [F1, F3])
        self.assertEqual(self.define("countries=so").file_ids, [F1, F2, F3])

    def test_an_unknown_facet_or_term_fails_loudly(self):
        with self.assertRaises(ClusterError):
            parse_constraint("colour=blue")
        with self.assertRaises(ClusterError):
            self.define("sector=no such sector")
        with self.assertRaises(ClusterError):
            define_cluster(self.target.records, VOCABS, "demo", [])

    def test_a_bad_topic_name_is_refused(self):
        with self.assertRaises(ClusterError):
            define_cluster(self.target.records, VOCABS, "../x", ["countries=SO"])

    def test_a_cluster_round_trips_through_cluster_yaml(self):
        cluster = self.define("sector=social protection")
        path = save_cluster(self.tmp.name, cluster)
        self.assertEqual(path, topic_dir(self.tmp.name, "demo") / "cluster.yaml")
        self.assertEqual(load_cluster(self.tmp.name, "demo"), cluster)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to see it fail**

Run: `PYTHONPATH=tests/agent/literature $PY -m pytest tests/agent/literature/test_lit_cluster.py -q`
Expected: FAIL (`ModuleNotFoundError: agent.literature.cluster`).

- [ ] **Step 3: Implement**

```python
"""A cluster of papers chosen by facet constraints on their tier A/B facts."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from . import schema
from .compare import _ancestors
from .tiers import at_least, tiered_facts
from .transcript import normalize

FACETS = tuple(schema.FACETS) + ("countries",)
_NAME = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}")


class ClusterError(ValueError):
    pass


@dataclass
class Cluster:
    name: str
    constraints: list
    floor: str
    file_ids: list


def topic_dir(index_root, name: str) -> Path:
    if not _NAME.fullmatch(name or ""):
        raise ClusterError(f"topic name {name!r}: use lowercase letters, digits, - and _ (up to 64 characters)")
    return Path(index_root) / "literature_reviews" / name


def parse_constraint(text: str) -> dict:
    facet, sep, value = text.partition("=")
    facet, value = facet.strip(), value.strip()
    if not sep or not value or facet not in FACETS:
        raise ClusterError(f"{text!r}: write facet=value with a facet from {', '.join(FACETS)}")
    return {"facet": facet, "value": value}


def _matcher(constraint: dict, vocabs: dict):
    facet, value = constraint["facet"], constraint["value"]
    if facet == "countries":
        code = value.upper()
        return lambda i: i["facet"] == "countries" and i["shown"].upper() == code
    vocab = vocabs.get(schema.FACETS[facet])
    term = (vocab.terms.get(value) or vocab.find(value)) if vocab is not None else None
    if term is None:
        raise ClusterError(f"{value!r} is not a term of the {schema.FACETS[facet]} vocabulary")
    label = normalize(term.label)
    return lambda i: i["facet"] == facet and (i["shown"] == term.id or normalize(i["label"]) == label
                                                or term.id in _ancestors(i["shown"], vocab))


def define_cluster(records, vocabs: dict, name: str, where: list, floor: str = "B") -> Cluster:
    topic_dir("", name)  # validates the name
    if not where:
        raise ClusterError("give at least one facet=value constraint")
    constraints = [parse_constraint(w) for w in where]
    matchers = [_matcher(c, vocabs) for c in constraints]
    members = []
    for fid in sorted(records.ids()):
        items = at_least(tiered_facts(records, fid, vocabs), floor)
        if items and all(any(m(i) for i in items) for m in matchers):
            members.append(fid)
    return Cluster(name, constraints, floor, members)


def save_cluster(index_root, cluster: Cluster) -> Path:
    path = topic_dir(index_root, cluster.name) / "cluster.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {"name": cluster.name, "constraints": cluster.constraints, "floor": cluster.floor, "file_ids": cluster.file_ids}
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8", newline="\n")
    return path


def load_cluster(index_root, name: str) -> Cluster:
    path = topic_dir(index_root, name) / "cluster.yaml"
    if not path.is_file():
        raise ClusterError(f"no cluster {name!r}: run `cluster define {name} --where facet=value` first")
    d = yaml.safe_load(path.read_text(encoding="utf-8"))
    return Cluster(d["name"], d["constraints"], d["floor"], d["file_ids"])
```

- [ ] **Step 4: Run to see it pass**

Run: `PYTHONPATH=tests/agent/literature $PY -m pytest tests/agent/literature/test_lit_cluster.py -q`
Expected: 5 passed. If `test_a_term_id_and_a_country_code_work_as_values` fails because `Vocabulary.find` or `terms` lookups differ, fix `_matcher` (not the test).

- [ ] **Step 5: Commit**

```bash
git add ai-sandbox/academic-rag-model/agent/literature/cluster.py ai-sandbox/academic-rag-model/tests/agent/literature/test_lit_cluster.py
git commit -m "feat(literature): cluster membership by facet constraints on tier A/B facts"
```

---

### Task 3: Deterministic annotations and citation keys

**Files:**
- Create: `agent/literature/annotation.py`
- Test: `tests/agent/literature/test_lit_annotation.py`

**Interfaces:**
- Consumes: `tiers.tiered_facts`, `tiers.at_least`, the record's `identity`, `core.results`, `appraisal`.
- Produces: `annotation_of(records, file_id, vocabs, floor="B") -> dict` with keys `file_id, identity, facts ({facet: [{label,tier,quote,locator}]}), results ([{id:"R1",claim,effect_direction,magnitude,quote,locator}]), confidence`; `render_annotation_md(ann, label) -> str`; `cite_keys(identities: dict[file_id, identity]) -> dict[file_id, str]` (unique keys, sorted by file_id).

- [ ] **Step 1: Write the failing tests**

```python
import tempfile
import unittest

from agent.literature.annotation import annotation_of, cite_keys, render_annotation_md
from lit_helpers import VOCABS
from synth_helpers import F1, F2, build, three_papers


class TestAnnotation(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.target, _ = build(self.tmp.name, three_papers())

    def test_annotation_lists_tier_a_b_facts_and_numbered_results(self):
        ann = annotation_of(self.target.records, F1, VOCABS)
        self.assertEqual(ann["file_id"], F1)
        self.assertTrue(all(f["tier"] in "AB" for fs in ann["facts"].values() for f in fs))
        self.assertEqual([r["id"] for r in ann["results"]], ["R1"])
        self.assertEqual(ann["results"][0]["magnitude"], "12%")
        self.assertIn("intervention", ann["facts"])

    def test_the_markdown_names_each_result_with_the_label_given(self):
        ann = annotation_of(self.target.records, F1, VOCABS)
        text = render_annotation_md(ann, "P1")
        self.assertIn("P1.R1", text)
        self.assertIn("12%", text)
        self.assertIn("cash transfer", text.lower())

    def test_same_title_and_year_still_get_different_keys(self):
        ids = {F1: {"title": "Cash transfers in Somalia: an evaluation", "publication_year": 2019},
               F2: {"title": "Cash transfers in Somalia: an evaluation", "publication_year": 2019}}
        keys = cite_keys(ids)
        self.assertEqual(len(set(keys.values())), 2)
        self.assertTrue(all("2019" in k for k in keys.values()))
        self.assertEqual(keys[F1], "Cash transfers in Somalia 2019")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to see it fail**

Run: `PYTHONPATH=tests/agent/literature $PY -m pytest tests/agent/literature/test_lit_annotation.py -q`
Expected: FAIL (module missing).

- [ ] **Step 3: Implement**

```python
"""The deterministic per-paper annotation: what the record says, with tiers and result ids; and citation keys."""
from __future__ import annotations

import re

from .tiers import at_least, tiered_facts

_RESULT_KEYS = ("claim", "effect_direction", "magnitude", "quote", "locator")


def annotation_of(records, file_id: str, vocabs: dict | None = None, floor: str = "B") -> dict:
    record = records.read(file_id, "a")
    facts: dict = {}
    for item in at_least(tiered_facts(records, file_id, vocabs), floor):
        facts.setdefault(item["facet"], []).append(
            {k: item[k] for k in ("label", "tier", "quote", "locator")})
    results = [{"id": f"R{n}", **{k: r.get(k) for k in _RESULT_KEYS}}
               for n, r in enumerate(record["core"].get("results") or [], 1)]
    return {"file_id": file_id, "identity": record["identity"], "facts": facts, "results": results,
            "confidence": (record.get("appraisal") or {}).get("confidence")}


def render_annotation_md(ann: dict, label: str) -> str:
    ident = ann["identity"]
    lines = [f"{label}: {ident.get('title') or ann['file_id']} ({ident.get('publication_year', 'year unknown')})"]
    for facet in sorted(ann["facts"]):
        lines.append(f"  {facet.replace('_', ' ')}: " + "; ".join(f"{f['label']} [{f['tier']}]" for f in ann["facts"][facet]))
    for r in ann["results"]:
        lines.append(f"  {label}.{r['id']}: {r['claim']} | direction {r['effect_direction']} | magnitude {r['magnitude']}"
                     f" | page {r['locator']}")
    if ann.get("confidence"):
        lines.append(f"  extractor confidence: {ann['confidence']}")
    return "\n".join(lines)


def cite_keys(identities: dict) -> dict:
    """A short readable key per paper: first words of the title and the year; clashes get a letter."""
    taken: dict = {}
    out = {}
    for fid in sorted(identities):
        ident = identities[fid]
        words = re.findall(r"[A-Za-z0-9]+", (ident.get("title") or "paper").split(":")[0])[:5]
        base = " ".join(words) + (f" {ident['publication_year']}" if ident.get("publication_year") else "")
        n = taken.get(base, 0)
        taken[base] = n + 1
        out[fid] = base if n == 0 else f"{base}{chr(ord('a') + n)}"
    return out
```

- [ ] **Step 4: Run to see it pass**

Run: `PYTHONPATH=tests/agent/literature $PY -m pytest tests/agent/literature/test_lit_annotation.py -q`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add ai-sandbox/academic-rag-model/agent/literature/annotation.py ai-sandbox/academic-rag-model/tests/agent/literature/test_lit_annotation.py
git commit -m "feat(literature): deterministic paper annotations and unique citation keys"
```

---

### Task 4: The `annotate` stage

**Files:**
- Create: `agent/literature/contribute.py`
- Test: `tests/agent/literature/test_lit_contribute.py`

**Interfaces:**
- Consumes: `stage._offered_pages`, `stage._sha`, `stage.MAX_CARD_CHARS`, `stage.Target`, `transcript.split_pages/check_quote`, `annotation.annotation_of/render_annotation_md`, `cluster.Cluster/topic_dir`, `core.agent_tasks.tasks.Task/Passage`.
- Produces: `STAGE = "annotate"`, `make_tasks(target, cluster, papers, *, redo=False) -> (tasks, skipped)`, `validate_result(entry, result, target) -> list[str]`, `apply_result(target, entry, result, provenance) -> None`, `load_annotations(index_root, topic) -> {file_id: dict}` (each dict: `contribution`, `limitations` with `text, quote, locator`, plus `run_id`, `agent_name`, `transcript_sha`).
- Card subject: `{"file_id", "topic", "transcript_sha"}`. Result shape: `{contribution: {text, quote, locator}, limitations: {text, quote, locator}}`.

- [ ] **Step 1: Write the failing tests**

```python
import tempfile
import unittest

from agent.literature import contribute
from agent.literature.cluster import define_cluster
from core.agent_tasks.work import task_entry
from lit_helpers import PAGES, VOCABS
from synth_helpers import F1, F2, PROV, build, three_papers


def _answer(**over):
    r = {"contribution": {"text": "It shows that cash transfers raised food consumption among treated households.",
                          "quote": "Cash transfers raised household food consumption", "locator": 3},
         "limitations": {"text": "The authors note attrition between survey waves.",
                         "quote": "given attrition between survey waves", "locator": 4}}
    r.update(over)
    return r


class TestAnnotateStage(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.target, self.papers = build(self.tmp.name, three_papers())
        self.cluster = define_cluster(self.target.records, VOCABS, "demo", ["sector=social protection"])

    def tasks(self, **kw):
        return contribute.make_tasks(self.target, self.cluster, self.papers, **kw)

    def test_one_card_per_cluster_paper_with_the_cited_pages_offered(self):
        tasks, skipped = self.tasks()
        self.assertEqual(sorted(t.subject["file_id"] for t in tasks), [F1, "c" * 16])
        t = tasks[0]
        self.assertEqual((t.stage, t.subject["topic"]), ("annotate", "demo"))
        refs = {p.ref for p in t.passages}
        self.assertIn("page 3", refs)
        self.assertIn("12%", t.context)
        self.assertNotIn(F2, {x.subject["file_id"] for x in tasks})

    def test_a_good_answer_is_accepted_and_written_under_the_topic(self):
        entry = task_entry(self.tasks()[0][0])
        self.assertEqual(contribute.validate_result(entry, _answer(), self.target), [])
        contribute.apply_result(self.target, entry, _answer(), PROV)
        notes = contribute.load_annotations(self.tmp.name, "demo")
        self.assertEqual(notes[entry["subject"]["file_id"]]["contribution"]["locator"], 3)
        self.assertEqual(notes[entry["subject"]["file_id"]]["run_id"], "r1")

    def test_a_quote_that_is_not_on_the_page_or_a_missing_part_bounces(self):
        entry = task_entry(self.tasks()[0][0])
        bad = _answer(contribution={"text": "It shows a large effect on everything measured.",
                                    "quote": "Transfers cured all poverty", "locator": 3})
        self.assertTrue(any("quote" in m for m in contribute.validate_result(entry, bad, self.target)))
        self.assertTrue(contribute.validate_result(entry, {"contribution": _answer()["contribution"]}, self.target))
        short = _answer(limitations={"text": "ok", "quote": "given attrition between survey waves", "locator": 4})
        self.assertTrue(any("text" in m for m in contribute.validate_result(entry, short, self.target)))

    def test_papers_already_annotated_are_skipped_unless_redo(self):
        entry = task_entry(self.tasks()[0][0])
        contribute.apply_result(self.target, entry, _answer(), PROV)
        tasks, skipped = self.tasks()
        self.assertEqual(len(tasks), 1)
        self.assertIn("already annotated", skipped[entry["subject"]["file_id"]])
        self.assertEqual(len(self.tasks(redo=True)[0]), 2)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to see it fail**

Run: `PYTHONPATH=tests/agent/literature $PY -m pytest tests/agent/literature/test_lit_contribute.py -q`
Expected: FAIL (module missing).

- [ ] **Step 3: Implement**

```python
"""The `annotate` stage: a one-sentence contribution and limitation per paper, each backed by a verified quote."""
from __future__ import annotations

import json
import os
from pathlib import Path

from core.agent_tasks.tasks import Passage, Task

from .annotation import annotation_of, render_annotation_md
from .cluster import Cluster, topic_dir
from .papers import Paper
from .stage import MAX_CARD_CHARS, Target, _offered_pages, _sha
from .transcript import check_quote, split_pages

STAGE = "annotate"
PARTS = ("contribution", "limitations")

INSTRUCTIONS = """\
Below is what the study record says about one paper, and the pages it cites. Write two short notes about the paper as an
answer, a YAML mapping under `## Result`:

  contribution: {text: "one sentence on what this study adds", quote: "...", locator: 3}
  limitations: {text: "one sentence on a limitation the paper itself states or that its design implies", quote: "...", locator: 4}

Rules:
- `text` is one plain sentence (20 to 400 characters) about this study, not a topic from its literature review.
- `quote` is copied exactly from the offered page text (8 to 300 characters) and `locator` is that page number.
- Use only what the offered pages say."""


def _path(index_root, topic: str, file_id: str) -> Path:
    return topic_dir(index_root, topic) / "annotations" / f"{file_id}.json"


def load_annotations(index_root, topic: str) -> dict:
    folder = topic_dir(index_root, topic) / "annotations"
    return {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted(folder.glob("*.json"))} if folder.is_dir() else {}


def make_tasks(target: Target, cluster: Cluster, papers: list[Paper], *, redo: bool = False):
    tasks: list[Task] = []
    skipped: dict[str, str] = {}
    done = load_annotations(target.index_root, cluster.name)
    for paper in papers:
        if paper.file_id not in cluster.file_ids:
            continue
        try:
            md = (Path(target.index_root) / paper.path).read_text(encoding="utf-8")
        except OSError as exc:
            skipped[paper.file_id] = f"cannot read the transcript: {exc}"
            continue
        sha = _sha(md)
        if not redo and done.get(paper.file_id, {}).get("transcript_sha") == sha:
            skipped[paper.file_id] = "already annotated (use --redo to annotate again)"
            continue
        ann = annotation_of(target.records, paper.file_id, target.vocabs, cluster.floor)
        record = target.records.read(paper.file_id, "a")
        pages = split_pages(md)
        wanted = {r["locator"] for r in ann["results"] if isinstance(r["locator"], int)}
        for loc in [(record.get("appraisal") or {}).get("locator")]:
            wanted |= {loc} if isinstance(loc, int) else set(loc or [])
        wanted = sorted(n for n in wanted if n in pages)
        if not wanted:
            skipped[paper.file_id] = "none of the cited pages is in the transcript"
            continue
        while sum(len(pages[n]) for n in wanted) > MAX_CARD_CHARS and len(wanted) > 1:
            wanted.pop()
        tasks.append(Task(
            id=f"annotate-{paper.file_id}", stage=STAGE,
            subject={"file_id": paper.file_id, "topic": cluster.name, "transcript_sha": sha},
            instructions=INSTRUCTIONS, context=render_annotation_md(ann, "This paper"),
            passages=[Passage(id=f"P{n}", source=paper.title or paper.file_id, ref=f"page {n}", text=pages[n]) for n in wanted]))
    return tasks, skipped


def validate_result(entry: dict, result, target: Target) -> list[str]:
    if not isinstance(result, dict):
        return ["result: must be a mapping with contribution and limitations"]
    pages = _offered_pages(entry)
    out: list[str] = []
    for part in PARTS:
        row = result.get(part)
        if not isinstance(row, dict):
            out.append(f"{part}: must be a mapping with text, quote and locator")
            continue
        text = row.get("text")
        if not isinstance(text, str) or not 20 <= len(text.strip()) <= 400:
            out.append(f"{part}.text: one sentence of 20 to 400 characters")
        if "locator" not in row:
            out.append(f"{part}.locator: required")
        elif problem := check_quote(row.get("quote"), row["locator"], pages):
            out.append(f"{part}.quote: {problem}")
    return out


def apply_result(target: Target, entry: dict, result: dict, provenance: dict) -> str | None:
    s = entry["subject"]
    path = _path(target.index_root, s["topic"], s["file_id"])
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {"file_id": s["file_id"], "transcript_sha": s["transcript_sha"], "run_id": provenance["run"],
            "agent_name": provenance["agent"], **{p: {k: result[p][k] for k in ("text", "quote", "locator")} for p in PARTS}}
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n")
    os.replace(tmp, path)
    return None
```

- [ ] **Step 4: Run to see it pass**

Run: `PYTHONPATH=tests/agent/literature $PY -m pytest tests/agent/literature/test_lit_contribute.py -q`
Expected: 4 passed. If a test fails because the fixture's page 3/4 are not both cited, adjust the card page selection, not the test.

- [ ] **Step 5: Commit**

```bash
git add ai-sandbox/academic-rag-model/agent/literature/contribute.py ai-sandbox/academic-rag-model/tests/agent/literature/test_lit_contribute.py
git commit -m "feat(literature): annotate stage writes a verified contribution and limitation per paper"
```

---

### Task 5: Synthesis validator (citations and numbers)

**Files:**
- Create: `agent/literature/synth.py` (validator part only in this task)
- Test: `tests/agent/literature/test_lit_synth.py`

**Interfaces:**
- Produces: `STAGE = "synthesize"`, `assign_ids(file_ids) -> {file_id: "P1"...}` (sorted order), `allowed_for(annotations: dict, ids: dict) -> {"P1": {"year": int|None, "results": {"R1": "<claim> <magnitude> <quote>"}}}`, `check_sections(sections, allowed, must_cover) -> list[str]`.
- Rules checked: `sections` non-empty list of `{heading: str, paragraphs: [{text, cites}]}`; text 30+ characters with no raw `P\d` ids; `cites` non-empty and each `P<n>` or `P<n>.R<m>` known in `allowed`; each number (`\d+(?:[.,]\d+)*`) in text appears in the text of a cited result (a bare `P<n>` cite stands for all of that paper's results) or equals a cited paper's year; every id in `must_cover` is cited at least once.

- [ ] **Step 1: Write the failing tests**

```python
import unittest

from agent.literature import synth

ALLOWED = {"P1": {"year": 2019, "results": {"R1": "Cash transfers raised food consumption 12% raised household food consumption"}},
           "P2": {"year": 2020, "results": {"R1": "Vouchers had no effect 0.5 points"}}}


def paragraph(text, *cites):
    return {"sections": [{"heading": "Findings", "paragraphs": [{"text": text, "cites": list(cites)}]}]}


class TestCheckSections(unittest.TestCase):
    def check(self, doc, cover=("P1",)):
        return synth.check_sections(doc["sections"] if isinstance(doc, dict) else doc, ALLOWED, list(cover))

    def test_a_cited_paragraph_with_traceable_numbers_passes(self):
        doc = paragraph("Transfers raised food consumption by 12% in the treated districts.", "P1.R1")
        self.assertEqual(self.check(doc), [])
        self.assertEqual(self.check(paragraph("Work published in 2019 found gains.", "P1"), cover=("P1",)), [])

    def test_a_number_only_in_prose_or_only_in_an_uncited_paper_bounces_naming_it(self):
        msgs = self.check(paragraph("Transfers raised food consumption by 15% in treated districts.", "P1.R1"))
        self.assertTrue(any("15" in m for m in msgs), msgs)
        msgs = self.check(paragraph("Vouchers moved scores by 0.5 points in the sample.", "P1.R1"))
        self.assertTrue(any("0.5" in m for m in msgs), msgs)

    def test_citations_must_exist_and_every_paragraph_needs_one(self):
        self.assertTrue(any("P9" in m for m in self.check(paragraph("Some evidence points the same way here.", "P9"))))
        self.assertTrue(any("P1.R7" in m for m in self.check(paragraph("Some evidence points the same way here.", "P1.R7"))))
        self.assertTrue(self.check(paragraph("Some evidence points the same way here.")))

    def test_raw_ids_in_prose_and_uncovered_papers_bounce(self):
        self.assertTrue(any("P1" in m for m in self.check(paragraph("As P1 shows, evidence points the same way.", "P1"))))
        msgs = self.check(paragraph("Some evidence points the same way here.", "P1"), cover=("P1", "P2"))
        self.assertTrue(any("P2" in m and "not cited" in m for m in msgs), msgs)

    def test_the_shape_is_checked(self):
        self.assertTrue(self.check([]))
        self.assertTrue(self.check([{"heading": "x", "paragraphs": "no"}]))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to see it fail**

Run: `PYTHONPATH=tests/agent/literature $PY -m pytest tests/agent/literature/test_lit_synth.py -q`
Expected: FAIL (module missing).

- [ ] **Step 3: Implement the validator**

```python
"""The `synthesize` stage: cluster synthesis whose citations and numbers are checked mechanically."""
from __future__ import annotations

import re

STAGE = "synthesize"
_CITE = re.compile(r"P(\d+)(?:\.R(\d+))?")
_RAW_ID = re.compile(r"\bP\d+(?:\.R\d+)?\b")
_NUM = re.compile(r"\d+(?:[.,]\d+)*")


def assign_ids(file_ids) -> dict:
    return {fid: f"P{n}" for n, fid in enumerate(sorted(file_ids), 1)}


def allowed_for(annotations: dict, ids: dict) -> dict:
    """annotations: file_id -> deterministic annotation (see annotation.annotation_of)."""
    out = {}
    for fid, pid in ids.items():
        ann = annotations[fid]
        out[pid] = {"year": ann["identity"].get("publication_year"),
                    "results": {r["id"]: f"{r['claim']} {r['magnitude']} {r['quote']}" for r in ann["results"]}}
    return out


def _numbers(text: str) -> set:
    return {n.rstrip(".,") for n in _NUM.findall(text or "")}


def check_sections(sections, allowed: dict, must_cover: list) -> list[str]:
    if not isinstance(sections, list) or not sections:
        return ["sections: must be a non-empty list of {heading, paragraphs}"]
    out: list[str] = []
    cited: set = set()
    for si, sec in enumerate(sections):
        where = f"sections[{si}]"
        if not isinstance(sec, dict) or not isinstance(sec.get("heading"), str) or not isinstance(sec.get("paragraphs"), list) or not sec["paragraphs"]:
            out.append(f"{where}: must be a mapping with a heading and a non-empty list of paragraphs")
            continue
        for pi, para in enumerate(sec["paragraphs"]):
            path = f"{where}.paragraphs[{pi}]"
            if not isinstance(para, dict) or not isinstance(para.get("text"), str) or not isinstance(para.get("cites"), list):
                out.append(f"{path}: must be a mapping with text and a cites list")
                continue
            text = para["text"]
            if len(text.strip()) < 30:
                out.append(f"{path}.text: at least 30 characters")
            if raw := _RAW_ID.search(text):
                out.append(f"{path}.text: contains the raw id {raw.group()}; put ids in cites, not in the sentence")
            if not para["cites"]:
                out.append(f"{path}.cites: every paragraph needs at least one citation")
                continue
            evidence: set = set()
            bad = False
            for c in para["cites"]:
                m = _CITE.fullmatch(c) if isinstance(c, str) else None
                paper = allowed.get(f"P{m.group(1)}") if m else None
                if paper is None:
                    out.append(f"{path}.cites: {c!r} is not a paper of this card")
                    bad = True
                    continue
                cited.add(f"P{m.group(1)}")
                if m.group(2) is None:
                    texts = list(paper["results"].values())
                else:
                    rid = f"R{m.group(2)}"
                    if rid not in paper["results"]:
                        out.append(f"{path}.cites: {c} is not a result of that paper")
                        bad = True
                        continue
                    texts = [paper["results"][rid]]
                for t in texts:
                    evidence |= _numbers(t)
                if paper.get("year"):
                    evidence.add(str(paper["year"]))
            if bad:
                continue
            for n in sorted(_numbers(text) - evidence):
                out.append(f"{path}.text: the number {n} does not appear in any result you cite")
    for pid in must_cover:
        if pid not in cited:
            out.append(f"{pid} is not cited anywhere; every paper on this card must appear")
    return out
```

- [ ] **Step 4: Run to see it pass**

Run: `PYTHONPATH=tests/agent/literature $PY -m pytest tests/agent/literature/test_lit_synth.py -q`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add ai-sandbox/academic-rag-model/agent/literature/synth.py ai-sandbox/academic-rag-model/tests/agent/literature/test_lit_synth.py
git commit -m "feat(literature): synthesis validator traces every citation and number to a cited result"
```

---

### Task 6: Synthesis cards: chunking, merge, apply

**Files:**
- Modify: `agent/literature/synth.py`
- Test: `tests/agent/literature/test_lit_synth_cards.py`

**Interfaces:**
- Consumes: `annotation.annotation_of/render_annotation_md`, `contribute.load_annotations`, `cluster.Cluster/topic_dir`, `stage.Target`, `Task`.
- Produces: `MAX_PAPERS = 20`, `chunks(cluster, annotations, max_papers) -> list[list[file_id]]` (sorted by first country then file_id, sliced evenly), `make_tasks(target, cluster, *, max_papers=MAX_PAPERS, merge=False) -> (tasks, skipped)`, `validate_result(entry, result, target)`, `apply_result(target, entry, result, provenance)`, `load_outputs(index_root, topic) -> {task_id: dict}`.
- Rules: raises `ValueError` listing unannotated papers; one chunk gives task `synth-final`; several give `synth-c1..` and, with `merge=True` once every chunk output exists, one `synth-final` merge card whose context holds the chunk paragraphs with their cites. Subject: `{"topic","task","allowed":{...},"must_cover":[...]}`. Outputs saved to `<topic>/synthesis/<task id>.json`.

- [ ] **Step 1: Write the failing tests**

```python
import tempfile
import unittest

from agent.literature import contribute, synth
from agent.literature.cluster import define_cluster
from core.agent_tasks.work import task_entry
from lit_helpers import VOCABS
from synth_helpers import F1, F3, PROV, build, three_papers
from test_lit_contribute import _answer


def _doc(*cites, text="Transfers raised food consumption by 12% in treated districts."):
    return {"sections": [{"heading": "Findings", "paragraphs": [{"text": text, "cites": list(cites)}]}]}


class TestSynthCards(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.target, self.papers = build(self.tmp.name, three_papers())
        self.cluster = define_cluster(self.target.records, VOCABS, "demo", ["sector=social protection"])

    def annotate_all(self):
        tasks, _ = contribute.make_tasks(self.target, self.cluster, self.papers)
        for t in tasks:
            contribute.apply_result(self.target, task_entry(t), _answer(), PROV)

    def test_synthesis_refuses_until_every_paper_is_annotated(self):
        with self.assertRaises(ValueError) as ctx:
            synth.make_tasks(self.target, self.cluster)
        self.assertIn(F1, str(ctx.exception))

    def test_a_small_cluster_gets_one_final_card_listing_papers_results_and_notes(self):
        self.annotate_all()
        tasks, _ = synth.make_tasks(self.target, self.cluster)
        self.assertEqual([t.id for t in tasks], ["synth-final"])
        t = tasks[0]
        self.assertIn("P1.R1", t.context)
        self.assertIn("attrition", t.context)
        self.assertEqual(sorted(t.subject["allowed"]), ["P1", "P2"])
        self.assertEqual(t.subject["must_cover"], ["P1", "P2"])

    def test_a_good_answer_is_applied_and_a_bad_one_bounces(self):
        self.annotate_all()
        entry = task_entry(synth.make_tasks(self.target, self.cluster)[0][0])
        self.assertTrue(synth.validate_result(entry, _doc("P1.R1"), self.target))  # P2 not cited
        good = {"sections": [{"heading": "Findings", "paragraphs": [
            {"text": "Transfers raised food consumption by 12% in treated districts.", "cites": ["P1.R1", "P2.R1"]}]}]}
        self.assertEqual(synth.validate_result(entry, good, self.target), [])
        synth.apply_result(self.target, entry, good, PROV)
        self.assertEqual(synth.load_outputs(self.tmp.name, "demo")["synth-final"]["sections"], good["sections"])

    def test_a_large_cluster_is_chunked_then_merged(self):
        self.annotate_all()
        tasks, _ = synth.make_tasks(self.target, self.cluster, max_papers=1)
        self.assertEqual([t.id for t in tasks], ["synth-c1", "synth-c2"])
        with self.assertRaises(ValueError):
            synth.make_tasks(self.target, self.cluster, max_papers=1, merge=True)  # chunks not answered yet
        for t in tasks:
            pid = t.subject["must_cover"][0]
            synth.apply_result(self.target, task_entry(t), _doc(f"{pid}.R1"), PROV)
        merge, _ = synth.make_tasks(self.target, self.cluster, max_papers=1, merge=True)
        self.assertEqual([t.id for t in merge], ["synth-final"])
        self.assertIn("12%", merge[0].context)
        self.assertEqual(merge[0].subject["must_cover"], ["P1", "P2"])


if __name__ == "__main__":
    unittest.main()
```

(`from test_lit_contribute import _answer` relies on pytest's rootdir import; if the import fails under the chunked runner, copy `_answer` into `synth_helpers.py` instead and import it from there in both tests.)

- [ ] **Step 2: Run to see it fail**

Run: `PYTHONPATH=tests/agent/literature $PY -m pytest tests/agent/literature/test_lit_synth_cards.py -q`
Expected: FAIL (`make_tasks` missing).

- [ ] **Step 3: Implement (append to `synth.py`)**

Add these imports at the top of `synth.py`: `import json, os`, `from pathlib import Path`, `from core.agent_tasks.tasks import Task`, `from .annotation import annotation_of, render_annotation_md`, `from .cluster import Cluster, topic_dir`, `from .contribute import load_annotations`, `from .stage import Target`. Then append:

```python
MAX_PAPERS = 20

INSTRUCTIONS = """\
Write a short literature review of the papers below as a YAML mapping under `## Result`:

  sections:
    - heading: "What the studies find"
      paragraphs:
        - text: "Two or three sentences in plain prose."
          cites: [P1.R1, P3]

Rules:
- Every paragraph needs `cites`: paper ids (P3) or result ids (P3.R2) from this card. Do not write ids inside `text`.
- Any digit you write must appear in the claim, magnitude or quote of a result you cite (cite P3 to cover all of its results).
- Write counts of studies in words. Do not state a finding that is not in the lines below.
- Every paper on this card must be cited at least once.
- Group papers by what they find or how they were studied, and say where they disagree."""

MERGE_NOTE = """
This card joins several partial reviews of one literature. Keep their findings and citations, remove repetition, and
order the sections so the whole reads as one review. You may reuse the cites shown under each paragraph."""


def _out_path(index_root, topic: str, task_id: str) -> Path:
    return topic_dir(index_root, topic) / "synthesis" / f"{task_id}.json"


def load_outputs(index_root, topic: str) -> dict:
    folder = topic_dir(index_root, topic) / "synthesis"
    return {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted(folder.glob("*.json"))} if folder.is_dir() else {}


def chunks(cluster: Cluster, annotations: dict, max_papers: int = MAX_PAPERS) -> list[list]:
    def first_country(fid):
        countries = [f["label"] for f in annotations[fid]["facts"].get("countries", [])]
        return (countries[0] if countries else "~", fid)
    ordered = sorted(cluster.file_ids, key=first_country)
    n = max(1, -(-len(ordered) // max_papers))
    size = -(-len(ordered) // n)
    return [ordered[i:i + size] for i in range(0, len(ordered), size)]


def _paper_block(ann: dict, note: dict, pid: str) -> str:
    text = render_annotation_md(ann, pid)
    if note:
        text += f"\n  contribution: {note['contribution']['text']}\n  limitation: {note['limitations']['text']}"
    return text


def make_tasks(target: Target, cluster: Cluster, *, max_papers: int = MAX_PAPERS, merge: bool = False):
    notes = load_annotations(target.index_root, cluster.name)
    missing = [f for f in cluster.file_ids if f not in notes]
    if missing:
        raise ValueError("annotate these papers first (run `annotate`): " + ", ".join(missing))
    anns = {f: annotation_of(target.records, f, target.vocabs, cluster.floor) for f in cluster.file_ids}
    ids = assign_ids(cluster.file_ids)
    parts = chunks(cluster, anns, max_papers)
    if len(parts) == 1:
        merge = False
    elif merge:
        outputs = load_outputs(target.index_root, cluster.name)
        absent = [f"synth-c{i}" for i in range(1, len(parts) + 1) if f"synth-c{i}" not in outputs]
        if absent:
            raise ValueError("answer and submit these chunk cards first: " + ", ".join(absent))
    tasks: list[Task] = []
    jobs = [("synth-final", cluster.file_ids)] if merge or len(parts) == 1 else [(f"synth-c{i}", p) for i, p in enumerate(parts, 1)]
    for task_id, members in jobs:
        blocks = [_paper_block(anns[f], notes[f], ids[f]) for f in members]
        context = "\n\n".join(blocks)
        if merge:
            outputs = load_outputs(target.index_root, cluster.name)
            drafts = []
            for i in range(1, len(parts) + 1):
                for sec in outputs[f"synth-c{i}"]["sections"]:
                    for para in sec["paragraphs"]:
                        drafts.append(f"[{sec['heading']}] {para['text']} (cites: {', '.join(para['cites'])})")
            context = "Partial reviews to join:\n" + "\n".join(drafts) + "\n\nPapers and results:\n\n" + context
        tasks.append(Task(
            id=task_id, stage=STAGE,
            subject={"topic": cluster.name, "task": task_id,
                     "allowed": allowed_for(anns, {f: ids[f] for f in members}),
                     "must_cover": [ids[f] for f in members]},
            instructions=INSTRUCTIONS + (MERGE_NOTE if merge else ""), context=context))
    return tasks, {}


def validate_result(entry: dict, result, target: Target) -> list[str]:
    if not isinstance(result, dict):
        return ["result: must be a mapping with a `sections` list"]
    s = entry["subject"]
    return check_sections(result.get("sections"), s["allowed"], s["must_cover"])


def apply_result(target: Target, entry: dict, result: dict, provenance: dict) -> str | None:
    s = entry["subject"]
    path = _out_path(target.index_root, s["topic"], s["task"])
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {"task": s["task"], "run_id": provenance["run"], "agent_name": provenance["agent"], "sections": result["sections"]}
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n")
    os.replace(tmp, path)
    return None
```

- [ ] **Step 4: Run to see it pass**

Run: `PYTHONPATH=tests/agent/literature $PY -m pytest tests/agent/literature/test_lit_synth.py tests/agent/literature/test_lit_synth_cards.py -q`
Expected: all pass. In the chunk test the chunk card for each paper cites only its own `P<n>.R1`; if the order of chunks puts `P2` first, the test already reads `must_cover[0]`.

- [ ] **Step 5: Commit**

```bash
git add ai-sandbox/academic-rag-model/agent/literature/synth.py ai-sandbox/academic-rag-model/tests/agent/literature/test_lit_synth_cards.py
git commit -m "feat(literature): synthesis chunk and merge cards with stored per-paper allowed results"
```

---

### Task 7: Render the review and bibliography

**Files:**
- Create: `agent/literature/review.py`
- Test: `tests/agent/literature/test_lit_review.py`

**Interfaces:**
- Consumes: `cluster.load_cluster/topic_dir`, `contribute.load_annotations`, `synth.assign_ids/load_outputs`, `annotation.annotation_of/cite_keys`.
- Produces: `render(target, name) -> (review_path, bibliography_path)`; raises `ValueError` when `synth-final` is missing (message names chunk/merge state) or any cluster paper is unannotated.
- Output: `review.md` with frontmatter (`title`, `tags: [literature-review]`, `cluster`, `tier_floor`, `papers`), each paragraph followed by ` ([Key](bibliography.md#anchor); ...)`; `bibliography.md` with one `## Key` section per paper (title, year, DOI if known, design and countries from tier A/B facts, result lines with page, contribution and limitation notes with their quote and page).

- [ ] **Step 1: Write the failing tests**

```python
import tempfile
import unittest

from agent.literature import contribute, review, synth
from agent.literature.cluster import define_cluster, save_cluster
from core.agent_tasks.work import task_entry
from lit_helpers import VOCABS
from synth_helpers import PROV, build, three_papers
from test_lit_contribute import _answer


class TestRender(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.target, self.papers = build(self.tmp.name, three_papers())
        self.cluster = define_cluster(self.target.records, VOCABS, "demo", ["sector=social protection"])
        save_cluster(self.tmp.name, self.cluster)

    def annotate(self):
        for t in contribute.make_tasks(self.target, self.cluster, self.papers)[0]:
            contribute.apply_result(self.target, task_entry(t), _answer(), PROV)

    def finish(self):
        self.annotate()
        entry = task_entry(synth.make_tasks(self.target, self.cluster)[0][0])
        doc = {"sections": [{"heading": "Findings", "paragraphs": [
            {"text": "Transfers raised food consumption by 12% in treated districts.", "cites": ["P1.R1", "P2.R1"]}]}]}
        synth.apply_result(self.target, entry, doc, PROV)

    def test_render_refuses_without_a_final_synthesis(self):
        self.annotate()
        with self.assertRaises(ValueError) as ctx:
            review.render(self.target, "demo")
        self.assertIn("synth-final", str(ctx.exception))

    def test_review_cites_by_key_and_bibliography_has_every_paper(self):
        self.finish()
        review_path, bib_path = review.render(self.target, "demo")
        text, bib = review_path.read_text(encoding="utf-8"), bib_path.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\n"))
        self.assertIn("tags: [literature-review]", text)
        self.assertIn("12%", text)
        self.assertIn("](bibliography.md#", text)
        self.assertNotIn("P1.R1", text)
        self.assertEqual(bib.count("\n## "), 2)
        self.assertIn("attrition", bib)
        self.assertIn("12%", bib)

    def test_rendering_twice_gives_the_same_files(self):
        self.finish()
        first = [p.read_text(encoding="utf-8") for p in review.render(self.target, "demo")]
        second = [p.read_text(encoding="utf-8") for p in review.render(self.target, "demo")]
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to see it fail**

Run: `PYTHONPATH=tests/agent/literature $PY -m pytest tests/agent/literature/test_lit_review.py -q`
Expected: FAIL (module missing).

- [ ] **Step 3: Implement**

```python
"""Render the review and the annotated bibliography. Deterministic: the bibliography never depends on model prose."""
from __future__ import annotations

import re

from .annotation import annotation_of, cite_keys
from .cluster import load_cluster, topic_dir
from .contribute import load_annotations
from .stage import Target
from .synth import assign_ids, load_outputs

_CITE = re.compile(r"P(\d+)(?:\.R\d+)?")


def _anchor(key: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", key.lower()).strip("-")


def _bibliography(cluster, anns, notes, keys) -> str:
    out = [f"# Annotated bibliography: {cluster.name}", ""]
    for fid in sorted(cluster.file_ids):
        ann, note, ident = anns[fid], notes[fid], anns[fid]["identity"]
        out += [f"## {keys[fid]}", "", f"{ident.get('title') or fid} ({ident.get('publication_year', 'year unknown')})"]
        if ident.get("doi"):
            out.append(f"DOI: {ident['doi']}")
        for facet in ("study_design", "countries", "intervention", "outcome"):
            if ann["facts"].get(facet):
                out.append(f"- {facet.replace('_', ' ')}: " + "; ".join(f"{f['label']} [{f['tier']}]" for f in ann["facts"][facet]))
        for r in ann["results"]:
            out.append(f"- result {r['id']}: {r['claim']} ({r['effect_direction']}, {r['magnitude']}; page {r['locator']})")
        for part, title in (("contribution", "Contribution"), ("limitations", "Limitations")):
            n = note[part]
            out += ["", f"**{title}.** {n['text']}", f"> {n['quote']} (page {n['locator']})"]
        out.append("")
    return "\n".join(out)


def render(target: Target, name: str):
    cluster = load_cluster(target.index_root, name)
    notes = load_annotations(target.index_root, name)
    if missing := [f for f in cluster.file_ids if f not in notes]:
        raise ValueError("annotate these papers first: " + ", ".join(missing))
    final = load_outputs(target.index_root, name).get("synth-final")
    if final is None:
        raise ValueError("synth-final is missing: run `synthesize` (and `synthesize --merge` if it made chunk cards), "
                         "fill the cards and submit them")
    anns = {f: annotation_of(target.records, f, target.vocabs, cluster.floor) for f in cluster.file_ids}
    keys = cite_keys({f: anns[f]["identity"] for f in cluster.file_ids})
    by_pid = {pid: fid for fid, pid in assign_ids(cluster.file_ids).items()}
    where = ", ".join(f"{c['facet']}={c['value']}" for c in cluster.constraints)
    lines = ["---", f'title: "Literature review: {name}"', "tags: [literature-review]", f'cluster: "{where}"',
             f"tier_floor: {cluster.floor}", f"papers: {len(cluster.file_ids)}", "---", "", f"# Literature review: {name}", ""]
    for sec in final["sections"]:
        lines += [f"## {sec['heading']}", ""]
        for para in sec["paragraphs"]:
            fids = list(dict.fromkeys(by_pid[f"P{_CITE.fullmatch(c).group(1)}"] for c in para["cites"]))
            links = "; ".join(f"[{keys[f]}](bibliography.md#{_anchor(keys[f])})" for f in fids)
            lines += [f"{para['text'].strip()} ({links})", ""]
    folder = topic_dir(target.index_root, name)
    review_path, bib_path = folder / "review.md", folder / "bibliography.md"
    review_path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    bib_path.write_text(_bibliography(cluster, anns, notes, keys), encoding="utf-8", newline="\n")
    return review_path, bib_path
```

- [ ] **Step 4: Run to see it pass**

Run: `PYTHONPATH=tests/agent/literature $PY -m pytest tests/agent/literature/test_lit_review.py -q`
Expected: 3 passed. The `\n## ` count in the bibliography test is 2 for the two cluster papers; the review file's `## Findings` is not in that file.

- [ ] **Step 5: Commit**

```bash
git add ai-sandbox/academic-rag-model/agent/literature/review.py ai-sandbox/academic-rag-model/tests/agent/literature/test_lit_review.py
git commit -m "feat(literature): render the review and annotated bibliography deterministically"
```

---

### Task 8: CLI commands and submit routing

**Files:**
- Modify: `agent/literature/cli.py`
- Test: `tests/agent/literature/test_lit_synthesis_cli.py`

**Interfaces:**
- Commands: `cluster define NAME --where facet=value [--where ...] [--floor A|B|C]`, `cluster show NAME`, `annotate NAME [--redo] [--run-id R]`, `synthesize NAME [--merge] [--max-papers N] [--run-id R]`, `render NAME`; `submit RUN` routes `run.stage` to `verify`, `contribute` or `synth` (else `stage`).
- Cards go to `<work-root>/<run>/cards/`; the output repo passed to `collect_run` is the topic folder.

- [ ] **Step 1: Write the failing end-to-end test**

```python
import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from agent.literature.cli import main
from core.agent_tasks.work import load_run
from lit_helpers import fill_card, write_vocab_dir
from synth_helpers import build, three_papers
from test_lit_contribute import _answer


def run_cli(root, vocab_dir, *args):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = main(["--index-root", root, "--vocab-dir", vocab_dir, *args])
    return code, out.getvalue()


class TestSynthesisCli(unittest.TestCase):
    def test_define_annotate_synthesize_render_end_to_end(self):
        with tempfile.TemporaryDirectory() as root:
            build(root, three_papers())
            vocab_dir = Path(root) / "vocab"
            vocab_dir.mkdir()
            write_vocab_dir(vocab_dir)
            v = str(vocab_dir)
            code, out = run_cli(root, v, "cluster", "define", "demo", "--where", "sector=social protection")
            self.assertEqual(code, 0)
            self.assertIn("2 papers", out)
            self.assertEqual(run_cli(root, v, "cluster", "define", "demo", "--where", "sector=nope")[0], 2)

            self.assertEqual(run_cli(root, v, "annotate", "demo", "--run-id", "ann1")[0], 0)
            run = load_run(Path(root) / ".agent_work", "ann1")
            for entry in run.tasks:
                fill_card(run.card_path(entry["id"]), _answer())
            code, out = run_cli(root, v, "submit", "ann1")
            self.assertEqual(code, 0)
            self.assertEqual(run_cli(root, v, "render", "demo")[0], 2)  # no synthesis yet

            self.assertEqual(run_cli(root, v, "synthesize", "demo", "--run-id", "syn1")[0], 0)
            run = load_run(Path(root) / ".agent_work", "syn1")
            fill_card(run.card_path("synth-final"), {"sections": [{"heading": "Findings", "paragraphs": [
                {"text": "Transfers raised food consumption by 12% in treated districts.", "cites": ["P1.R1", "P2.R1"]}]}]})
            run_cli(root, v, "submit", "syn1")
            code, out = run_cli(root, v, "render", "demo")
            self.assertEqual(code, 0)
            self.assertTrue((Path(root) / "literature_reviews" / "demo" / "review.md").is_file())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to see it fail**

Run: `PYTHONPATH=tests/agent/literature $PY -m pytest tests/agent/literature/test_lit_synthesis_cli.py -q`
Expected: FAIL (unknown command, argparse exit).

- [ ] **Step 3: Implement**

In `cli.py`: change the import line to `from . import cluster as clusters, contribute, review, stage, synth, tiers, verify` (keep the existing `from .remap import remap_record`). Replace the module selection in `cmd_submit`:

```python
    module = {verify.STAGE: verify, contribute.STAGE: contribute, synth.STAGE: synth}.get(run.stage, stage)
```

Add the commands above `cmd_bootstrap`:

```python
def cmd_cluster(args) -> int:
    target = _target(args)
    try:
        if args.action == "show":
            c = clusters.load_cluster(args.index_root, args.name)
        else:
            c = clusters.define_cluster(target.records, target.vocabs, args.name, args.where, args.floor)
            clusters.save_cluster(args.index_root, c)
    except clusters.ClusterError as exc:
        print(f"cluster: {exc}")
        return 2
    print(f"cluster {c.name}: {len(c.file_ids)} papers at tier {c.floor} or better")
    for fid in c.file_ids:
        print(f"  {fid}")
    return 0


def _collect(args, stage_name, tasks, skips, label) -> int:
    for fid, reason in skips.items():
        print(f"skipped {fid}: {reason}")
    try:
        run = collect_run(stage_name, tasks, _work_root(args), clusters.topic_dir(args.index_root, args.name),
                          run_id=args.run_id, repo_label="literature review folder")
    except (ValueError, FileExistsError) as exc:
        print(f"cannot create the run: {exc}")
        return 2
    if run is None:
        print(f"nothing to {label}")
        return 0
    print(f"collected {len(tasks)} {label} card(s) in run {run.run_id}: {run.root}")
    return 0


def cmd_annotate(args) -> int:
    target = _target(args)
    try:
        cluster = clusters.load_cluster(args.index_root, args.name)
    except clusters.ClusterError as exc:
        print(f"annotate: {exc}")
        return 2
    papers, _ = eligible_papers(args.index_root)
    tasks, skips = contribute.make_tasks(target, cluster, papers, redo=args.redo)
    return _collect(args, contribute.STAGE, tasks, skips, "annotation")


def cmd_synthesize(args) -> int:
    target = _target(args)
    try:
        cluster = clusters.load_cluster(args.index_root, args.name)
        tasks, skips = synth.make_tasks(target, cluster, max_papers=args.max_papers, merge=args.merge)
    except (clusters.ClusterError, ValueError) as exc:
        print(f"synthesize: {exc}")
        return 2
    return _collect(args, synth.STAGE, tasks, skips, "synthesis")


def cmd_render(args) -> int:
    try:
        review_path, bib_path = review.render(_target(args), args.name)
    except (clusters.ClusterError, ValueError) as exc:
        print(f"render: {exc}")
        return 2
    print(f"wrote {review_path}\nwrote {bib_path}")
    return 0
```

In `build_parser` (before `ev = ...`):

```python
    cl = sub.add_parser("cluster", help="Choose the papers of a review by facet constraints on tier A/B facts.")
    cl.add_argument("action", choices=["define", "show"])
    cl.add_argument("name")
    cl.add_argument("--where", action="append", default=[], help="facet=value, repeatable (facet: intervention, outcome, study_design, sector, population, data_sources, countries).")
    cl.add_argument("--floor", choices=["A", "B", "C"], default="B")
    an = sub.add_parser("annotate", help="Cards for a contribution and limitation note per paper of a cluster.")
    an.add_argument("name")
    an.add_argument("--run-id", default=None)
    an.add_argument("--redo", action="store_true")
    sy = sub.add_parser("synthesize", help="Cards that write the cluster review; --merge joins chunk answers.")
    sy.add_argument("name")
    sy.add_argument("--run-id", default=None)
    sy.add_argument("--merge", action="store_true")
    sy.add_argument("--max-papers", type=int, default=synth.MAX_PAPERS)
    rd = sub.add_parser("render", help="Write review.md and bibliography.md under literature_reviews/<name>/.")
    rd.add_argument("name")
```

and add `"cluster": cmd_cluster, "annotate": cmd_annotate, "synthesize": cmd_synthesize, "render": cmd_render` to the dispatch dict in `main`.

- [ ] **Step 4: Run to see it pass, then the whole literature suite**

Run: `PYTHONPATH=tests/agent/literature $PY -m pytest tests/agent/literature -q`
Expected: all pass (the previous 158 plus the new tests). Fix `fill_card` use if a card has no empty fence: it expects exactly one ```` ```yaml\n``` ```` fence per card.

- [ ] **Step 5: Commit**

```bash
git add ai-sandbox/academic-rag-model/agent/literature/cli.py ai-sandbox/academic-rag-model/tests/agent/literature/test_lit_synthesis_cli.py
git commit -m "feat(literature): cluster, annotate, synthesize and render commands; submit routes by stage"
```

---

### Task 9: Documentation, status and landing prep

**Files:**
- Modify: `agent/literature/README.md`
- Create: `docs/status/literature/2026-10-22-stage3-synthesis.md`

- [ ] **Step 1: README**

Add under Commands:

```
python -m agent.literature cluster define NAME --where sector=<term> --where countries=SO   # papers of a review (tier A/B facts)
python -m agent.literature annotate NAME --run-id a1       # cards: contribution + limitation note per paper
python -m agent.literature synthesize NAME --run-id s1     # cards: the review (chunks of up to 20 papers; --merge joins them)
python -m agent.literature render NAME                     # review.md + bibliography.md under research/literature_reviews/NAME/
```

and a short "Synthesis (stage 3)" section: output is local only; citations and numbers are checked at `submit`; the bibliography is deterministic; the order is define, annotate, synthesize (merge), render.

- [ ] **Step 2: Status doc**

Write the doc with: what is built, the validator rules, the first-run plan (small social-protection cluster first, then agriculture), how to hand off to Antigravity (one run per stage, each run a fresh chat, `submit` at the end), known limits (clusters by facet only, no embeddings, numbers only traced to result text, counts of studies must be words), and not-done items (embedding clusters, vault export, stage 4 database).

- [ ] **Step 3: Full test run and commit**

Run: `$PY tools/run_tests_chunked.py` Expected: every chunk passes.

```bash
git add ai-sandbox/academic-rag-model/agent/literature/README.md ai-sandbox/academic-rag-model/docs/status/literature/2026-10-22-stage3-synthesis.md
git commit -m "docs(literature): stage 3 synthesis usage and status"
```

- [ ] **Step 4: Landing**

Follow `docs/WORKTREE_WORKFLOW.md`: `land_branch check --full` from the worktree's `ai-sandbox/academic-rag-model`, then ask the owner to approve the exact SHA. Never merge without that approval.

---

## Self-review

- **Spec coverage:** cluster define (Task 2), deterministic annotation and the annotate card (3, 4), synthesis cards with chunking and merge (6), mechanical validation (5), deterministic render and bibliography (7), CLI and stage routing (8), local-only output (1, Global Constraints), docs (9). The spec's "no paper outside the cluster is named" is enforced by citing only ids on the card and forbidding raw ids in prose.
- **Placeholders:** none; every code step has code. Task 9 steps 1 and 2 are prose by nature.
- **Types:** `Cluster.file_ids`, `assign_ids`, `allowed_for`, `check_sections(sections, allowed, must_cover)`, `load_annotations`, `load_outputs`, `cite_keys` are used with the signatures defined in the earlier tasks.
- **Review Focus coverage:** empty or unknown cluster (Task 2 tests), unannotated papers refuse (Task 6), number traced (Task 5), duplicate keys (Task 3), render before final (Task 7).
