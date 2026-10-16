# Stage 2: Study-Record Extraction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn each converted journal paper's transcript into a validated, quote-backed `study_record.json` (3ie-derived core plus extensions) through task cards that Antigravity fills, with code doing all validation.

**Architecture:** New package `agent/literature/` is a stage module for the shared `core/agent_tasks` loop (`validate_result` / `apply_result`). One task card per paper: the paper's pages become `Passage`s (so a locator is simply a page number), the vocabularies are listed in the card, and the agent answers with a YAML mapping of facts, each with a quote and a page locator. Submit verifies every quote against the offered page text, checks vocabulary membership (or an explicit `proposed` flag), and writes `research/.index/study_records/<file_id>.json` (gitignored). Vocabularies are data files, so the 3ie codebook drops in without code changes. A second extraction pass (gold set, or per-paper opt-in) is stored beside the first and diffed.

**Tech Stack:** Python 3.13, PyYAML, pytest/unittest, existing `core/agent_tasks`, `core/indexer`.

**Spec:** `docs/superpowers/specs/literature_taxonomy/2026-10-15-literature-taxonomy-pipeline-design.md` (section 6 stage 2, section 8, section 9, section 12 as amended by this plan's Task 11).

**Landed prerequisites:** stage 0 (`core/agent_tasks/`, commit `a8cb707`) and stage 1 (journal converter driver, identity on index cards, `70f26f4`).

## Owner decisions (2026-10-16)

1. **3ie codebook:** incorporate the real 3ie material now rather than a made-up draft first; the owner is fetching it. The machinery is built and fully tested against a small synthetic test vocabulary; Task 10 (gated) loads the real codebook, then runs the pilot.
2. **Quotes:** `study_record.json` files are **not committed**. They live under `research/.index/study_records/`, which this plan gitignores (Task 1).
3. **Double extraction:** gold set always, plus a per-paper opt-in flag (`--double`).
4. **Table images:** text only for v1. `Task.attachments` stays unused here.

## Global Constraints

- Subscription route by default: `collect` then Antigravity fills cards then `submit`. `api` is an explicit opt-in subcommand behind `core.agent_tasks.loop`'s cost gate (`--approve-cost`); warn and get a go-ahead before any run estimated over $1.
- No hidden generative fallback: a pending or bounced card stays pending; nothing is sent to the API unless the `api` subcommand is invoked.
- Never commit paper text, transcripts, cards, or records. `research/.agent_work/` is already ignored (stage 1); Task 1 adds `research/.index/study_records/`. Test fixtures are synthetic text only.
- Do not edit any existing test. All new behavior gets new test files. `core/agent_tasks` is not modified.
- No new third-party dependencies (PyYAML is already required; `jsonschema` and `pycountry` are not installed and are not used). ISO country codes come from a committed `vocab_data/countries.yaml` generated from the `tzdata` package's `iso3166.tab` (Task 2).
- Quotes: at least 8 and at most 300 characters; locators are page numbers that were offered on the card.
- Stage `STAGE = "extract"`; card/manifest formats are the shared ones; do not alter them.
- Stage explicit paths only; never `git add -A`. Work in the `claude/literature-extraction` worktree. Do not land on `main`; the owner does.
- Run modules from `ai-sandbox/academic-rag-model/` with `C:\Users\theaa\ai-sandbox-master\ai-sandbox\academic-rag-model\.venv\Scripts\python.exe`.

## Review Focus

Failure modes the spec implies but a straightforward build would miss, most likely first. Each has a pinning test in the task that owns the code.

1. **Quote matching that wrongly bounces or wrongly accepts.** Real transcripts have line-break hyphenation, ligatures, curly quotes, Markdown table pipes and emphasis marks; a correct quote must still match, and a fabricated one must not, including a very short generic one ("the effect"). (Task 3)
2. **A record that no longer matches its paper.** Quotes are verified against the exact page text offered on the card, and the record stores a hash of the transcript it came from; a changed transcript is re-extracted on `--redo`/re-collect, not silently kept. (Task 5, Task 6)
3. **Vocabulary changes between collect and submit.** A term removed or renamed after the card was made must bounce with a clear reason, and the record must store the vocabulary versions it was validated against. (Task 4, Task 5)
4. **Unusable papers.** A transcript with no page markers, a paper over the size cap, a card flagged `needs_indexing`, or a paper with no transcript file must be skipped with a reported reason, never produce a half-built card or crash the batch. (Task 5, Task 6)
5. **Order dependence in double extraction.** Pass A and pass B can be applied in either order, a pass can be resubmitted after a bounce, and the diff is the same either way; re-applying never duplicates proposals. (Task 7, Task 8)

---

### Task 1: Gitignore, record schema constants, record store

**Files:**
- Modify: `.gitignore` (repo root; add `ai-sandbox/research/.index/study_records/` beside the stage 1 `research/.agent_work/` rule)
- Create: `agent/literature/__init__.py` (empty), `agent/literature/schema.py`, `agent/literature/store.py`
- Test: `tests/agent/literature/test_store.py` (create `tests/agent/literature/__init__.py` only if sibling test dirs have one; check `ls tests/agent/concept_graph`)

**Interfaces:**
- Produces: `schema.SCHEMA_VERSION = 1`, `schema.PROMPT_VERSION = "extract-v1"`, `schema.FACETS` (facet name → vocabulary name), `schema.EFFECT_DIRECTIONS`, `schema.CONFIDENCE`, `schema.SCALES`, `schema.MIN_QUOTE_CHARS = 8`, `schema.MAX_QUOTE_CHARS = 300`, `schema.MODULE_FACETS`; `store.RecordStore(root)` with `.dir`, `.path(file_id, pass_label="a") -> Path`, `.read(file_id, pass_label="a") -> dict | None`, `.write(record, pass_label="a") -> Path`, `.ids() -> list[str]`; `store.check_file_id(file_id) -> str`.

- [ ] **Step 1: Gitignore first**

Add to the root `.gitignore`, after the `ai-sandbox/research/.agent_work/` line:

```
# 2026-10-16: extracted study records hold verbatim quotes from copyrighted papers
ai-sandbox/research/.index/study_records/
```

Verify: `git check-ignore -v ai-sandbox/research/.index/study_records/abc.json` prints the new rule. Commit alone: `git add .gitignore && git commit -m "chore: ignore research/.index/study_records (records hold verbatim quotes)"`.

- [ ] **Step 2: Write the failing tests**

```python
# tests/agent/literature/test_store.py
import json
import tempfile
import unittest

from agent.literature import schema
from agent.literature.store import RecordStore, check_file_id


class TestSchemaConstants(unittest.TestCase):
    def test_facets_map_to_vocabulary_names(self):
        self.assertEqual(
            schema.FACETS,
            {"intervention": "intervention", "outcome": "outcome", "study_design": "study_design",
             "sector": "sector", "population": "population", "data_sources": "data_source"},
        )

    def test_enums_and_limits(self):
        self.assertEqual(schema.EFFECT_DIRECTIONS, ("positive", "negative", "null", "mixed", "not_reported"))
        self.assertEqual(schema.CONFIDENCE, ("low", "medium", "high"))
        self.assertEqual((schema.MIN_QUOTE_CHARS, schema.MAX_QUOTE_CHARS), (8, 300))


class TestRecordStore(unittest.TestCase):
    def test_round_trip_keeps_non_ascii_and_uses_one_file_per_paper(self):
        with tempfile.TemporaryDirectory() as root:
            s = RecordStore(root)
            rec = {"identity": {"file_id": "abc123", "title": "Élasticité β"}}
            path = s.write(rec)
            self.assertEqual(path.name, "abc123.json")
            self.assertEqual(s.read("abc123"), rec)
            self.assertIn("Élasticité", path.read_text(encoding="utf-8"))
            self.assertEqual(s.ids(), ["abc123"])

    def test_pass_b_is_a_separate_file_and_not_listed_as_a_paper(self):
        with tempfile.TemporaryDirectory() as root:
            s = RecordStore(root)
            s.write({"identity": {"file_id": "abc123"}}, "a")
            s.write({"identity": {"file_id": "abc123"}, "marker": "b"}, "b")
            self.assertEqual(s.path("abc123", "b").name, "abc123.b.json")
            self.assertEqual(s.read("abc123", "b")["marker"], "b")
            self.assertEqual(s.ids(), ["abc123"])

    def test_missing_record_is_none(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertIsNone(RecordStore(root).read("nope"))

    def test_file_id_may_not_carry_a_path(self):
        for bad in ("../x", "a/b", "a\\b", "", ".hidden", "a b"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    check_file_id(bad)

    def test_write_is_atomic_leaving_no_temp_file(self):
        with tempfile.TemporaryDirectory() as root:
            s = RecordStore(root)
            s.write({"identity": {"file_id": "abc123"}})
            self.assertEqual([p.name for p in s.dir.iterdir()], ["abc123.json"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run to verify failure**

Run: `python -m pytest tests/agent/literature/test_store.py -q`
Expected: FAIL, `ModuleNotFoundError: agent.literature`.

- [ ] **Step 4: Implement**

```python
# agent/literature/schema.py
"""Constants for the study record and the agent's result shape (stage 2). Versioned: bump SCHEMA_VERSION when a
record's shape changes incompatibly, PROMPT_VERSION when the card instructions change."""
SCHEMA_VERSION = 1
PROMPT_VERSION = "extract-v1"

# result facet -> vocabulary name (vocab/<name>.yaml)
FACETS = {
    "intervention": "intervention", "outcome": "outcome", "study_design": "study_design",
    "sector": "sector", "population": "population", "data_sources": "data_source",
}
# optional extension modules: module -> {facet -> vocabulary name}
MODULE_FACETS = {"disaster_conflict": {"hazard_types": "hazard_type"}}

EFFECT_DIRECTIONS = ("positive", "negative", "null", "mixed", "not_reported")
CONFIDENCE = ("low", "medium", "high")
SCALES = ("local", "subnational", "national", "multi_country", "global", "not_stated")
MIN_QUOTE_CHARS = 8
MAX_QUOTE_CHARS = 300
```

```python
# agent/literature/store.py
"""study_record.json files, one per paper, keyed by the index card's file_id. The records are the source of truth;
any database built on top is derived and rebuildable (spec architecture A)."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

_SAFE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")


def check_file_id(file_id: str) -> str:
    """A file_id becomes a file name, so it may not carry a path or odd characters."""
    if not isinstance(file_id, str) or not _SAFE.match(file_id):
        raise ValueError(f"invalid file_id {file_id!r}: letters, digits, hyphens and underscores only")
    return file_id


class RecordStore:
    def __init__(self, root: str | Path):
        self.dir = Path(root)

    def path(self, file_id: str, pass_label: str = "a") -> Path:
        check_file_id(file_id)
        name = f"{file_id}.json" if pass_label == "a" else f"{file_id}.{pass_label}.json"
        return self.dir / name

    def read(self, file_id: str, pass_label: str = "a") -> dict | None:
        p = self.path(file_id, pass_label)
        if not p.is_file():
            return None
        return json.loads(p.read_text(encoding="utf-8"))

    def write(self, record: dict, pass_label: str = "a") -> Path:
        p = self.path(record["identity"]["file_id"], pass_label)
        self.dir.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n")
        os.replace(tmp, p)
        return p

    def ids(self) -> list[str]:
        if not self.dir.is_dir():
            return []
        return sorted(p.stem for p in self.dir.glob("*.json") if p.stem.count(".") == 0 and not p.name.startswith("_"))
```

- [ ] **Step 5: Verify**

Run: `python -m pytest tests/agent/literature/test_store.py -q`
Expected: PASS (7 tests).

- [ ] **Step 6: Commit**

```bash
git add agent/literature/__init__.py agent/literature/schema.py agent/literature/store.py tests/agent/literature/test_store.py
git commit -m "feat(literature): record schema constants and file-per-paper record store"
```

---

### Task 2: Vocabularies as data (loader, validator, ISO countries)

**Files:**
- Create: `agent/literature/vocab.py`, `agent/literature/vocab_data/README.md`, `agent/literature/vocab_data/countries.yaml` (generated), `agent/literature/vocab_data/make_countries.py`
- Test: `tests/agent/literature/test_vocab.py`

**Interfaces:**
- Produces: `vocab.PROVENANCES = ("3ie", "provisional", "local")`; `vocab.VocabularyError`; `vocab.Term` (frozen dataclass: `id`, `label`, `parent`, `definition`, `aliases`, `source`); `vocab.Vocabulary` (`name`, `version`, `provenance`, `source`, `terms`, `.contains(term_id) -> bool`, `.find(value) -> Term | None` matching id, label or alias case/space-insensitively); `vocab.validate_vocabulary(data) -> list[str]`; `vocab.load_vocabulary(path) -> Vocabulary`; `vocab.load_vocab_dir(path) -> dict[str, Vocabulary]` (file stem must equal the vocabulary name); `vocab.load_countries(path=None) -> frozenset[str]` and `vocab.is_country(code) -> bool` (upper-case ISO 3166-1 alpha-2).
- File format (documented in `vocab_data/README.md`):

```yaml
vocabulary: intervention        # lower_snake name; file is intervention.yaml
version: 1
provenance: 3ie                 # 3ie | provisional | local
source: "3ie Evidence Gap Map codebook, <document title, date>"
terms:
  - id: intervention.cash_transfer     # must start with "<vocabulary>."
    label: Cash transfer
    parent: intervention.social_protection   # optional, must exist
    definition: "..."
    aliases: [cash transfers, unconditional cash transfer]
    source: local                      # optional; set only for terms added after the file was loaded
```

- [ ] **Step 1: Write the failing tests**

```python
# tests/agent/literature/test_vocab.py
import os
import tempfile
import unittest

import yaml

from agent.literature.vocab import (
    PROVENANCES, Vocabulary, VocabularyError, is_country, load_countries, load_vocab_dir, load_vocabulary,
    validate_vocabulary,
)


def _data(**kw):
    base = {
        "vocabulary": "intervention", "version": 1, "provenance": "provisional", "source": "test fixture",
        "terms": [
            {"id": "intervention.social_protection", "label": "Social protection"},
            {"id": "intervention.cash_transfer", "label": "Cash transfer", "parent": "intervention.social_protection",
             "definition": "Money paid to households.", "aliases": ["cash transfers", "Unconditional Cash"]},
        ],
    }
    base.update(kw)
    return base


def _write(directory, name, data):
    with open(os.path.join(directory, f"{name}.yaml"), "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)


class TestValidate(unittest.TestCase):
    def test_a_good_vocabulary_has_no_problems(self):
        self.assertEqual(validate_vocabulary(_data()), [])

    def test_problems_are_reported_in_plain_words(self):
        cases = {
            "provenance": _data(provenance="made-up"),
            "version": _data(version=0),
            "source": _data(source=""),
            "name": _data(vocabulary="Bad Name"),
        }
        for key, data in cases.items():
            with self.subTest(key=key):
                self.assertTrue(any(key in p for p in validate_vocabulary(data)), validate_vocabulary(data))

    def test_term_id_must_carry_the_vocabulary_prefix_and_be_unique(self):
        data = _data(terms=[{"id": "outcome.x", "label": "X"}, {"id": "intervention.a", "label": "A"},
                            {"id": "intervention.a", "label": "A again"}])
        problems = " | ".join(validate_vocabulary(data))
        self.assertIn("outcome.x", problems)
        self.assertIn("duplicate", problems)

    def test_parent_must_exist_and_may_not_loop(self):
        missing = _data(terms=[{"id": "intervention.a", "label": "A", "parent": "intervention.zzz"}])
        self.assertTrue(any("parent" in p for p in validate_vocabulary(missing)))
        loop = _data(terms=[{"id": "intervention.a", "label": "A", "parent": "intervention.b"},
                            {"id": "intervention.b", "label": "B", "parent": "intervention.a"}])
        self.assertTrue(any("cycle" in p for p in validate_vocabulary(loop)))

    def test_unknown_term_keys_are_refused(self):
        data = _data(terms=[{"id": "intervention.a", "label": "A", "colour": "red"}])
        self.assertTrue(any("colour" in p for p in validate_vocabulary(data)))

    def test_provenances_constant(self):
        self.assertEqual(PROVENANCES, ("3ie", "provisional", "local"))


class TestLoadAndFind(unittest.TestCase):
    def test_find_matches_id_label_and_alias_ignoring_case_and_spacing(self):
        with tempfile.TemporaryDirectory() as d:
            _write(d, "intervention", _data())
            v = load_vocabulary(os.path.join(d, "intervention.yaml"))
        self.assertIsInstance(v, Vocabulary)
        for probe in ("intervention.cash_transfer", "CASH  transfer", "unconditional cash"):
            with self.subTest(probe=probe):
                self.assertEqual(v.find(probe).id, "intervention.cash_transfer")
        self.assertIsNone(v.find("vouchers"))
        self.assertTrue(v.contains("intervention.social_protection"))
        self.assertFalse(v.contains("Social protection"))

    def test_invalid_file_raises_with_every_problem(self):
        with tempfile.TemporaryDirectory() as d:
            _write(d, "intervention", _data(provenance="nope", version=0))
            with self.assertRaises(VocabularyError) as ctx:
                load_vocabulary(os.path.join(d, "intervention.yaml"))
        self.assertIn("provenance", str(ctx.exception))
        self.assertIn("version", str(ctx.exception))

    def test_file_stem_must_equal_vocabulary_name(self):
        with tempfile.TemporaryDirectory() as d:
            _write(d, "wrongname", _data())
            with self.assertRaises(VocabularyError):
                load_vocab_dir(d)

    def test_load_vocab_dir_skips_countries_and_non_yaml(self):
        with tempfile.TemporaryDirectory() as d:
            _write(d, "intervention", _data())
            _write(d, "countries", {"countries": [{"code": "SO", "name": "Somalia"}]})
            with open(os.path.join(d, "README.md"), "w", encoding="utf-8") as f:
                f.write("x")
            self.assertEqual(sorted(load_vocab_dir(d)), ["intervention"])


class TestCountries(unittest.TestCase):
    def test_shipped_list_is_the_249_iso_codes(self):
        codes = load_countries()
        self.assertEqual(len(codes), 249)
        for c in ("SO", "US", "BD", "SS"):
            self.assertIn(c, codes)

    def test_is_country_is_strict_about_form(self):
        self.assertTrue(is_country("SO"))
        for bad in ("so", "SOM", "ZZ", "", None, 5, "S"):
            with self.subTest(bad=bad):
                self.assertFalse(is_country(bad))

    def test_shipped_list_agrees_with_the_standard_library_tzdata_when_present(self):
        try:
            import importlib.resources as r
            rows = (r.files("tzdata.zoneinfo") / "iso3166.tab").read_text(encoding="utf-8").splitlines()
        except Exception:
            self.skipTest("tzdata not installed")
        expected = {line.split("\t")[0] for line in rows if line and not line.startswith("#")}
        self.assertEqual(load_countries(), frozenset(expected))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/agent/literature/test_vocab.py -q`
Expected: FAIL, `ModuleNotFoundError: agent.literature.vocab`.

- [ ] **Step 3: Implement**

The loader module is `agent/literature/vocab.py`; the data directory is `agent/literature/vocab_data/` (a directory named `vocab/` would shadow the module). It holds `README.md`, `countries.yaml`, `make_countries.py`, and later the real vocabularies.

```python
# agent/literature/vocab.py
"""Controlled vocabularies as data files (see vocab_data/README.md for the format)."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

import yaml

PROVENANCES = ("3ie", "provisional", "local")
DATA_DIR = Path(__file__).resolve().parent / "vocab_data"
_NAME = re.compile(r"^[a-z][a-z_]*$")
_TERM_KEYS = {"id", "label", "parent", "definition", "aliases", "source"}


class VocabularyError(ValueError):
    pass


@dataclass(frozen=True)
class Term:
    id: str
    label: str
    parent: str | None = None
    definition: str = ""
    aliases: tuple[str, ...] = ()
    source: str | None = None


def _key(text) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", str(text)).casefold()).strip()


@dataclass
class Vocabulary:
    name: str
    version: int
    provenance: str
    source: str
    terms: dict[str, Term]
    _by_key: dict[str, str] = field(default_factory=dict, repr=False)

    def __post_init__(self):
        for t in self.terms.values():
            for k in (t.id, t.label, *t.aliases):
                self._by_key.setdefault(_key(k), t.id)

    def contains(self, term_id: str) -> bool:
        return term_id in self.terms

    def find(self, value) -> Term | None:
        tid = self._by_key.get(_key(value))
        return self.terms.get(tid) if tid else None


def validate_vocabulary(data) -> list[str]:
    if not isinstance(data, dict):
        return ["the file must be a YAML mapping"]
    problems: list[str] = []
    name = data.get("vocabulary")
    if not isinstance(name, str) or not _NAME.match(name):
        problems.append("name: `vocabulary` must be lower_snake_case text")
        name = None
    if not isinstance(data.get("version"), int) or isinstance(data.get("version"), bool) or data["version"] < 1:
        problems.append("version: must be an integer of at least 1")
    if data.get("provenance") not in PROVENANCES:
        problems.append(f"provenance: must be one of {PROVENANCES}")
    if not isinstance(data.get("source"), str) or not data["source"].strip():
        problems.append("source: say where this list comes from")
    terms = data.get("terms")
    if not isinstance(terms, list):
        return problems + ["terms: must be a list"]
    ids: list[str] = []
    for i, t in enumerate(terms):
        where = f"terms[{i}]"
        if not isinstance(t, dict):
            problems.append(f"{where}: must be a mapping")
            continue
        extra = sorted(set(t) - _TERM_KEYS)
        if extra:
            problems.append(f"{where}: unknown key(s) {extra}")
        tid = t.get("id")
        if not isinstance(tid, str) or not tid:
            problems.append(f"{where}: id is required")
            continue
        if name and not tid.startswith(f"{name}."):
            problems.append(f"{where}: id {tid!r} must start with '{name}.'")
        if tid in ids:
            problems.append(f"{where}: duplicate id {tid!r}")
        ids.append(tid)
        if not isinstance(t.get("label"), str) or not t["label"].strip():
            problems.append(f"{where}: label is required")
        if "aliases" in t and not (isinstance(t["aliases"], list) and all(isinstance(a, str) for a in t["aliases"])):
            problems.append(f"{where}: aliases must be a list of text")
    parents = {t["id"]: t.get("parent") for t in terms if isinstance(t, dict) and isinstance(t.get("id"), str)}
    for tid, parent in parents.items():
        if parent is not None and parent not in parents:
            problems.append(f"{tid}: parent {parent!r} is not a term in this vocabulary")
    for tid in parents:
        seen, cur = set(), tid
        while cur is not None and cur in parents:
            if cur in seen:
                problems.append(f"{tid}: parent cycle")
                break
            seen.add(cur)
            cur = parents[cur]
    return problems


def load_vocabulary(path) -> Vocabulary:
    path = Path(path)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    problems = validate_vocabulary(data)
    if problems:
        raise VocabularyError(f"{path.name}: " + "; ".join(problems))
    terms = {
        t["id"]: Term(id=t["id"], label=t["label"], parent=t.get("parent"), definition=t.get("definition", ""),
                      aliases=tuple(t.get("aliases", [])), source=t.get("source"))
        for t in data["terms"]
    }
    return Vocabulary(data["vocabulary"], data["version"], data["provenance"], data["source"], terms)


def load_vocab_dir(path=None) -> dict[str, Vocabulary]:
    out: dict[str, Vocabulary] = {}
    for p in sorted(Path(path or DATA_DIR).glob("*.yaml")):
        if p.stem == "countries":
            continue
        v = load_vocabulary(p)
        if v.name != p.stem:
            raise VocabularyError(f"{p.name}: the vocabulary is named {v.name!r}; the file must be {v.name}.yaml")
        out[v.name] = v
    return out


_COUNTRIES: dict[str, frozenset[str]] = {}


def load_countries(path=None) -> frozenset[str]:
    p = Path(path or DATA_DIR / "countries.yaml")
    key = str(p)
    if key not in _COUNTRIES:
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
        _COUNTRIES[key] = frozenset(c["code"] for c in data["countries"])
    return _COUNTRIES[key]


def is_country(code) -> bool:
    return isinstance(code, str) and len(code) == 2 and code.isupper() and code in load_countries()
```

`vocab_data/make_countries.py` (one-off generator; reads `tzdata`'s `iso3166.tab`; run once, commit the output):

```python
"""Writes countries.yaml (ISO 3166-1 alpha-2) from the standard-library-adjacent tzdata package. Run once."""
import importlib.resources as r
from pathlib import Path

import yaml

rows = (r.files("tzdata.zoneinfo") / "iso3166.tab").read_text(encoding="utf-8").splitlines()
countries = [{"code": a, "name": b} for a, b in (line.split("\t") for line in rows if line and not line.startswith("#"))]
out = Path(__file__).with_name("countries.yaml")
out.write_text("# ISO 3166-1 alpha-2, generated by make_countries.py from tzdata's iso3166.tab\n" +
               yaml.safe_dump({"countries": countries}, allow_unicode=True, sort_keys=False), encoding="utf-8", newline="\n")
print(len(countries), "countries ->", out)
```

Run it: `python agent/literature/vocab_data/make_countries.py`. Expected: `249 countries -> ...countries.yaml`.

`vocab_data/README.md`: document the file format above, the three provenances, that `3ie` vocabularies come from the owner-supplied 3ie codebook (Task 10), that `local` terms are those accepted from agent proposals, and that, if 3ie's license forbids committing a machine-readable copy, the real files go in an ignored directory passed with `--vocab-dir`.

- [ ] **Step 4: Verify**

Run: `python -m pytest tests/agent/literature/test_vocab.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add agent/literature/vocab.py agent/literature/vocab_data tests/agent/literature/test_vocab.py
git commit -m "feat(literature): vocabularies as data files with validator and ISO country list"
```

---

### Task 3: Transcript pages and quote verification

**Files:**
- Create: `agent/literature/transcript.py`
- Test: `tests/agent/literature/test_transcript.py`

**Interfaces:**
- Produces: `transcript.split_pages(md: str) -> dict[int, str]` (keys are page numbers from `<!-- page N -->` markers; `{}` when none); `transcript.normalize(text: str) -> str`; `transcript.check_quote(quote: str, locator, pages: dict[int, str]) -> str | None` (None when the quote is on the located page(s), else a plain-words problem). A locator is an `int` page or a non-empty `list[int]`; booleans are not integers here.

- [ ] **Step 1: Write the failing tests**

```python
# tests/agent/literature/test_transcript.py
import unittest

from agent.literature.transcript import check_quote, normalize, split_pages

MD = (
    "<!-- page 1 -->\n\nWe study cash trans-\nfers in rural Somalia using a panel of 1,200 households.\n\n"
    "<!-- page 2 -->\n\n| Source | DF |\n|---|---|\n| Diagnostic Test | 2 |\n\n"
    "The \u201cdifference-in-differences\u201d estimate is \ufb01rm and **robust**.\n"
)


class TestSplitPages(unittest.TestCase):
    def test_pages_are_keyed_by_marker_number(self):
        pages = split_pages(MD)
        self.assertEqual(sorted(pages), [1, 2])
        self.assertIn("rural Somalia", pages[1])
        self.assertNotIn("<!--", pages[1])

    def test_no_markers_means_no_pages(self):
        self.assertEqual(split_pages("just text"), {})


class TestNormalize(unittest.TestCase):
    def test_folds_ligatures_quotes_dashes_markup_and_hyphens(self):
        self.assertEqual(normalize("The \u201cfirm\u201d \ufb01rm -- **bold**"), normalize('the "firm" firm -- bold'))
        self.assertEqual(normalize("cash trans-\nfers"), normalize("cash transfers"))
        self.assertEqual(normalize("difference-in-differences"), normalize("difference-in-\ndifferences"))


class TestCheckQuote(unittest.TestCase):
    pages = split_pages(MD)

    def test_a_correct_quote_matches_despite_hyphenation_and_spacing(self):
        self.assertIsNone(check_quote("cash transfers in rural Somalia", 1, self.pages))

    def test_matches_across_ligatures_curly_quotes_and_markup(self):
        self.assertIsNone(check_quote('The "difference-in-differences" estimate is firm and robust', 2, self.pages))

    def test_table_text_matches_without_pipes(self):
        self.assertIsNone(check_quote("Diagnostic Test 2", 2, self.pages))

    def test_a_fabricated_quote_is_rejected_with_the_page_named(self):
        msg = check_quote("cash transfers reduced hunger by 40 percent", 1, self.pages)
        self.assertIn("page 1", msg)

    def test_the_right_text_on_the_wrong_page_is_rejected(self):
        self.assertIsNotNone(check_quote("cash transfers in rural Somalia", 2, self.pages))

    def test_a_list_locator_may_span_pages(self):
        self.assertIsNone(check_quote("1,200 households. Source DF", [1, 2], self.pages))

    def test_very_short_or_too_long_quotes_are_rejected(self):
        self.assertIn("at least", check_quote("the", 1, self.pages))
        self.assertIn("at most", check_quote("x" * 301, 1, self.pages))

    def test_bad_locators_are_rejected_in_plain_words(self):
        for bad in (None, 0, 9, "2", True, [], [1, 9], 1.5, [1, True]):
            with self.subTest(bad=bad):
                msg = check_quote("cash transfers in rural Somalia", bad, self.pages)
                self.assertIsNotNone(msg)
                self.assertIn("locator", msg)

    def test_non_text_quote_is_rejected(self):
        self.assertIsNotNone(check_quote(None, 1, self.pages))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/agent/literature/test_transcript.py -q`
Expected: FAIL, `ModuleNotFoundError: agent.literature.transcript`.

- [ ] **Step 3: Implement**

```python
# agent/literature/transcript.py
"""Page-level access to a converted transcript, and the quote check every extracted fact must pass."""
from __future__ import annotations

import re
import unicodedata

from .schema import MAX_QUOTE_CHARS, MIN_QUOTE_CHARS

_PAGE = re.compile(r"<!--\s*page\s+(\d+)\s*-->")
_QUOTES = str.maketrans({"\u2018": "'", "\u2019": "'", "\u02bc": "'", "\u201c": '"', "\u201d": '"',
                         "\u2013": "-", "\u2014": "-", "\u2212": "-"})
_MARKUP = re.compile(r"[*_`#>|]")


def split_pages(md: str) -> dict[int, str]:
    parts = _PAGE.split(md)
    # parts = [preamble, "1", text1, "2", text2, ...]
    return {int(parts[i]): parts[i + 1].strip() for i in range(1, len(parts) - 1, 2)}


def normalize(text: str) -> str:
    """Fold what transcription and typesetting vary on, so a faithful quote matches and little else does:
    ligatures (NFKC), curly quotes and dashes, Markdown emphasis and table marks, and every hyphen (so a word
    broken across a line, 'trans-\\nfers', matches 'transfers'), then case and whitespace."""
    t = unicodedata.normalize("NFKC", text).replace("\u00ad", "").translate(_QUOTES)
    t = _MARKUP.sub(" ", t).replace("-", "")
    return re.sub(r"\s+", " ", t).strip().casefold()


def _pages_of(locator, pages: dict[int, str]) -> tuple[list[int] | None, str | None]:
    items = locator if isinstance(locator, list) else [locator]
    if not items or any(isinstance(p, bool) or not isinstance(p, int) for p in items):
        return None, "locator: give a page number, or a list of page numbers, that was offered on the card"
    missing = [p for p in items if p not in pages]
    if missing:
        return None, f"locator: page(s) {missing} were not offered on this card"
    return items, None


def check_quote(quote, locator, pages: dict[int, str]) -> str | None:
    """None when `quote` appears (after normalization) on the located page(s); otherwise why not."""
    located, problem = _pages_of(locator, pages)
    if problem:
        return problem
    if not isinstance(quote, str):
        return "quote: must be text copied from the page"
    n = len(quote.strip())
    if n < MIN_QUOTE_CHARS:
        return f"quote: must be at least {MIN_QUOTE_CHARS} characters"
    if n > MAX_QUOTE_CHARS:
        return f"quote: must be at most {MAX_QUOTE_CHARS} characters; quote the shortest passage that supports the fact"
    haystack = normalize(" ".join(pages[p] for p in located))
    if normalize(quote) not in haystack:
        label = "page " + ", ".join(map(str, located)) if len(located) == 1 else "pages " + ", ".join(map(str, located))
        return f"quote: not found on {label}; copy the wording exactly from the page text on the card"
    return None
```

- [ ] **Step 4: Verify**

Run: `python -m pytest tests/agent/literature/test_transcript.py -q`
Expected: PASS. If a fixture trips normalization (for example the `1,200 households. Source DF` spanning-pages probe), fix the fixture text, not the guard, then re-run.

- [ ] **Step 5: Mutation check**

Change `.replace("-", "")` in `normalize` to `.replace("-", " ")`; Expected: the hyphenation and line-break tests fail. Restore.

- [ ] **Step 6: Commit**

```bash
git add agent/literature/transcript.py tests/agent/literature/test_transcript.py
git commit -m "feat(literature): transcript page splitting and quote verification"
```

---

### Task 4: Result validator

**Files:**
- Create: `agent/literature/validate.py`
- Test: `tests/agent/literature/test_validate.py`

**Interfaces:**
- Consumes: `schema.*`, `vocab.Vocabulary`, `vocab.is_country`, `transcript.check_quote`.
- Produces: `validate.check_result(result: dict, vocabs: dict[str, Vocabulary], pages: dict[int, str]) -> list[str]` (empty list means valid; every message starts with the path of the offending field, for example `core.outcome[1].quote: ...`). The agent's result mapping has keys `core`, `appraisal`, and optional `modules`:

```yaml
core:
  intervention: [{value: "cash transfers", vocab_id: intervention.cash_transfer, quote: "...", locator: 4}]
  outcome: [...]
  study_design: [{value: "panel", proposed: true, quote: "...", locator: 3}]   # not in vocabulary
  sector: [...]
  population: [...]
  data_sources: [{value: "FSNAU", vocab_id: data_source.fsnau, resolution: "district", quote: "...", locator: 5}]
  geography: {countries: [SO], regions: ["Gedo"], scale: subnational, quote: "...", locator: 2}
  results: [{claim: "...", effect_direction: positive, magnitude: "+12%", quote: "...", locator: 8}]
appraisal: {confidence: medium, rationale: "...", quote: "...", locator: 9}   # quote/locator optional
modules:
  disaster_conflict: {hazard_types: [{value: "drought", vocab_id: hazard_type.drought, quote: "...", locator: 1}],
                      conflict_setting: "...", social_protection_modality: "..."}
```

- A fact is a mapping with `value` (non-empty text), exactly one of `vocab_id` (a term in the facet's vocabulary) or `proposed: true` (with no `vocab_id`; refused when the vocabulary already has a term matching `value`), plus `quote` and `locator`. `data_sources` facts may also carry `resolution` (text). All facet lists must be present; empty lists are allowed except `results`, which needs at least one. Unknown keys anywhere are problems.

- [ ] **Step 1: Write the failing tests**

Create the shared fixtures first (the test modules import them as `from lit_helpers import ...`, the same pattern `tests/agent/concept_graph/cg_helpers.py` uses; pytest puts the test directory on the path):

```python
# tests/agent/literature/lit_helpers.py
"""Shared fixtures for the literature tests: synthetic pages, vocabularies and a valid agent result."""
from agent.literature.vocab import Term, Vocabulary

PAGES = {
    1: "We study cash transfers in rural Somalia using a panel of 1,200 households from 2015 to 2019.",
    2: "Data come from FSNAU food security surveys collected at district level across Gedo region.",
    3: "Cash transfers raised household food consumption by twelve percent in the treated districts.",
    4: "Our confidence in these estimates is moderate given attrition between survey waves.",
}


def vocab(name, *term_ids, version=1):
    return Vocabulary(name, version, "provisional", "test fixture",
                      {t: Term(id=t, label=t.split(".", 1)[1].replace("_", " ")) for t in term_ids})


VOCABS = {
    "intervention": vocab("intervention", "intervention.cash_transfer", "intervention.voucher"),
    "outcome": vocab("outcome", "outcome.food_consumption"),
    "study_design": vocab("study_design", "study_design.panel"),
    "sector": vocab("sector", "sector.social_protection"),
    "population": vocab("population", "population.households"),
    "data_source": vocab("data_source", "data_source.fsnau"),
    "hazard_type": vocab("hazard_type", "hazard_type.drought"),
}


def good():
    return {
        "core": {
            "intervention": [{"value": "cash transfers", "vocab_id": "intervention.cash_transfer",
                              "quote": "We study cash transfers in rural Somalia", "locator": 1}],
            "outcome": [{"value": "food consumption", "vocab_id": "outcome.food_consumption",
                         "quote": "raised household food consumption by twelve percent", "locator": 3}],
            "study_design": [{"value": "panel", "vocab_id": "study_design.panel",
                              "quote": "using a panel of 1,200 households", "locator": 1}],
            "sector": [], "population": [],
            "data_sources": [{"value": "FSNAU", "vocab_id": "data_source.fsnau", "resolution": "district",
                              "quote": "FSNAU food security surveys collected at district level", "locator": 2}],
            "geography": {"countries": ["SO"], "regions": ["Gedo"], "scale": "subnational",
                          "quote": "across Gedo region", "locator": 2},
            "results": [{"claim": "Cash transfers raised food consumption", "effect_direction": "positive",
                         "magnitude": "12%", "quote": "raised household food consumption by twelve percent",
                         "locator": 3}],
        },
        "appraisal": {"confidence": "medium", "rationale": "Attrition between waves.",
                      "quote": "given attrition between survey waves", "locator": 4},
    }
```

Task 5 adds `make_index`, `write_vocab_dir` and `fill_card` to this module (and its `yaml` and index-card imports).

```python
# tests/agent/literature/test_validate.py
import copy
import unittest

from agent.literature.validate import check_result
from lit_helpers import PAGES, VOCABS, good


def problems(result):
    return check_result(result, VOCABS, PAGES)


class TestValid(unittest.TestCase):
    def test_a_complete_result_passes(self):
        self.assertEqual(problems(good()), [])

    def test_a_proposed_term_passes_when_not_in_the_vocabulary(self):
        r = good()
        r["core"]["study_design"] = [{"value": "synthetic control", "proposed": True,
                                      "quote": "using a panel of 1,200 households", "locator": 1}]
        self.assertEqual(problems(r), [])

    def test_modules_are_optional_and_validated_when_present(self):
        r = good()
        r["modules"] = {"disaster_conflict": {"hazard_types": [
            {"value": "drought", "vocab_id": "hazard_type.drought",
             "quote": "rural Somalia using a panel", "locator": 1}],
            "conflict_setting": None, "social_protection_modality": "cash"}}
        self.assertEqual(problems(r), [])


class TestProblems(unittest.TestCase):
    def _expect(self, mutate, needle):
        r = good()
        mutate(r)
        msgs = problems(r)
        self.assertTrue(any(needle in m for m in msgs), msgs)

    def test_unknown_keys(self):
        self._expect(lambda r: r.update(extra=1), "extra")
        self._expect(lambda r: r["core"]["outcome"][0].update(colour="x"), "colour")

    def test_missing_pieces(self):
        self._expect(lambda r: r.pop("appraisal"), "appraisal")
        self._expect(lambda r: r["core"].pop("outcome"), "core.outcome")
        self._expect(lambda r: r["core"].update(results=[]), "core.results")

    def test_vocabulary_membership(self):
        self._expect(lambda r: r["core"]["outcome"][0].update(vocab_id="outcome.nonsense"), "core.outcome[0].vocab_id")

    def test_vocab_id_and_proposed_are_exclusive_and_one_is_required(self):
        self._expect(lambda r: r["core"]["outcome"][0].update(proposed=True), "core.outcome[0]")
        self._expect(lambda r: r["core"]["outcome"][0].pop("vocab_id"), "core.outcome[0]")

    def test_proposing_an_existing_term_is_refused_and_names_it(self):
        def m(r):
            r["core"]["study_design"] = [{"value": "Panel", "proposed": True,
                                          "quote": "using a panel of 1,200 households", "locator": 1}]
        self._expect(m, "study_design.panel")

    def test_quote_problems_carry_the_field_path(self):
        self._expect(lambda r: r["core"]["outcome"][0].update(quote="reduced hunger by forty percent"),
                     "core.outcome[0].quote")
        self._expect(lambda r: r["core"]["outcome"][0].update(locator=99), "core.outcome[0].locator")

    def test_enums(self):
        self._expect(lambda r: r["core"]["results"][0].update(effect_direction="up"), "effect_direction")
        self._expect(lambda r: r["appraisal"].update(confidence="certain"), "appraisal.confidence")
        self._expect(lambda r: r["core"]["geography"].update(scale="galactic"), "geography.scale")

    def test_countries_must_be_iso_alpha2(self):
        self._expect(lambda r: r["core"]["geography"].update(countries=["Somalia"]), "geography.countries")
        self._expect(lambda r: r["core"]["geography"].update(countries=["so"]), "geography.countries")

    def test_geography_with_places_needs_a_quote(self):
        self._expect(lambda r: r["core"]["geography"].pop("quote"), "geography")

    def test_not_stated_geography_needs_no_quote(self):
        r = good()
        r["core"]["geography"] = {"countries": [], "regions": [], "scale": "not_stated"}
        self.assertEqual(problems(r), [])

    def test_a_vocabulary_missing_at_validation_time_is_reported_not_crashed(self):
        r = good()
        vocabs = {k: v for k, v in VOCABS.items() if k != "outcome"}
        msgs = check_result(r, vocabs, PAGES)
        self.assertTrue(any("outcome" in m and "vocabulary" in m for m in msgs), msgs)

    def test_a_non_mapping_result_is_one_clear_problem(self):
        self.assertEqual(len(check_result([], VOCABS, PAGES)), 1)

    def test_inputs_are_not_mutated(self):
        r = good()
        snapshot = copy.deepcopy(r)
        problems(r)
        self.assertEqual(r, snapshot)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/agent/literature/test_validate.py -q`
Expected: FAIL, `ModuleNotFoundError: agent.literature.validate`.

- [ ] **Step 3: Implement**

```python
# agent/literature/validate.py
"""Every rule an agent's extraction result must satisfy before it becomes a record."""
from __future__ import annotations

from . import schema
from .transcript import check_quote
from .vocab import Vocabulary, is_country

_FACT_KEYS = {"value", "vocab_id", "proposed", "quote", "locator"}
_TOP_KEYS = {"core", "appraisal", "modules"}
_CORE_KEYS = set(schema.FACETS) | {"geography", "results"}


def _fact(path: str, fact, vocab: Vocabulary | None, vocab_name: str, pages, extra_keys=()) -> list[str]:
    if not isinstance(fact, dict):
        return [f"{path}: must be a mapping with value, vocab_id (or proposed), quote and locator"]
    out: list[str] = []
    for k in sorted(set(fact) - _FACT_KEYS - set(extra_keys)):
        out.append(f"{path}: unknown key {k!r}")
    value = fact.get("value")
    if not isinstance(value, str) or not value.strip():
        out.append(f"{path}.value: required text")
    for k in extra_keys:
        if k in fact and fact[k] is not None and not isinstance(fact[k], str):
            out.append(f"{path}.{k}: must be text")
    has_id = fact.get("vocab_id") is not None
    proposed = fact.get("proposed") is True
    if "proposed" in fact and not isinstance(fact["proposed"], bool):
        out.append(f"{path}.proposed: must be true or omitted")
    if has_id == proposed:
        out.append(f"{path}: give exactly one of vocab_id (a term from the list) or proposed: true")
    elif vocab is None:
        out.append(f"{path}: the {vocab_name!r} vocabulary is not loaded, so this fact cannot be checked")
    elif has_id and not vocab.contains(fact["vocab_id"]):
        out.append(f"{path}.vocab_id: {fact['vocab_id']!r} is not a term in the {vocab_name} vocabulary")
    elif proposed and isinstance(value, str) and (hit := vocab.find(value)) is not None:
        out.append(f"{path}: {value!r} is already in the vocabulary as {hit.id}; use vocab_id instead of proposed")
    problem = check_quote(fact.get("quote"), fact.get("locator"), pages)
    if problem:
        out.append(f"{path}.{problem}")
    return out


def _facts(path: str, facts, vocabs, vocab_name: str, pages, extra_keys=()) -> list[str]:
    if not isinstance(facts, list):
        return [f"{path}: must be a list (write [] when the paper gives nothing)"]
    out: list[str] = []
    for i, f in enumerate(facts):
        out += _fact(f"{path}[{i}]", f, vocabs.get(vocab_name), vocab_name, pages, extra_keys)
    return out


def _geography(geo, pages) -> list[str]:
    if not isinstance(geo, dict):
        return ["core.geography: must be a mapping (countries, regions, scale, quote, locator)"]
    out = [f"core.geography: unknown key {k!r}" for k in sorted(set(geo) - {"countries", "regions", "scale", "quote", "locator"})]
    countries, regions = geo.get("countries", []), geo.get("regions", [])
    if not isinstance(countries, list) or not all(is_country(c) for c in countries):
        out.append("core.geography.countries: a list of upper-case ISO 3166-1 alpha-2 codes such as SO")
        countries = []
    if not isinstance(regions, list) or not all(isinstance(r, str) and r.strip() for r in regions):
        out.append("core.geography.regions: a list of text")
        regions = []
    if geo.get("scale") not in schema.SCALES:
        out.append(f"core.geography.scale: must be one of {schema.SCALES}")
    if countries or regions:
        problem = check_quote(geo.get("quote"), geo.get("locator"), pages)
        if problem:
            out.append(f"core.geography.{problem}")
    return out


def _results(results, pages) -> list[str]:
    if not isinstance(results, list) or not results:
        return ["core.results: give at least one result, with a quote"]
    out: list[str] = []
    for i, r in enumerate(results):
        path = f"core.results[{i}]"
        if not isinstance(r, dict):
            out.append(f"{path}: must be a mapping")
            continue
        out += [f"{path}: unknown key {k!r}" for k in sorted(set(r) - {"claim", "effect_direction", "magnitude", "quote", "locator"})]
        if not isinstance(r.get("claim"), str) or not r["claim"].strip():
            out.append(f"{path}.claim: required text")
        if r.get("effect_direction") not in schema.EFFECT_DIRECTIONS:
            out.append(f"{path}.effect_direction: must be one of {schema.EFFECT_DIRECTIONS}")
        if r.get("magnitude") is not None and not isinstance(r["magnitude"], str):
            out.append(f"{path}.magnitude: must be text such as '12%' (quote it) or omitted")
        problem = check_quote(r.get("quote"), r.get("locator"), pages)
        if problem:
            out.append(f"{path}.{problem}")
    return out


def _appraisal(a, pages) -> list[str]:
    if not isinstance(a, dict):
        return ["appraisal: required mapping (confidence, rationale)"]
    out = [f"appraisal: unknown key {k!r}" for k in sorted(set(a) - {"confidence", "rationale", "quote", "locator"})]
    if a.get("confidence") not in schema.CONFIDENCE:
        out.append(f"appraisal.confidence: must be one of {schema.CONFIDENCE}")
    if not isinstance(a.get("rationale"), str) or not a["rationale"].strip():
        out.append("appraisal.rationale: required text")
    if a.get("quote") is not None or a.get("locator") is not None:
        problem = check_quote(a.get("quote"), a.get("locator"), pages)
        if problem:
            out.append(f"appraisal.{problem}")
    return out


def _modules(modules, vocabs, pages) -> list[str]:
    if not isinstance(modules, dict):
        return ["modules: must be a mapping"]
    out: list[str] = []
    for name, body in modules.items():
        if name not in schema.MODULE_FACETS:
            out.append(f"modules: unknown module {name!r}")
            continue
        if not isinstance(body, dict):
            out.append(f"modules.{name}: must be a mapping")
            continue
        allowed = set(schema.MODULE_FACETS[name]) | {"conflict_setting", "social_protection_modality"}
        out += [f"modules.{name}: unknown key {k!r}" for k in sorted(set(body) - allowed)]
        for facet, vocab_name in schema.MODULE_FACETS[name].items():
            if facet in body:
                out += _facts(f"modules.{name}.{facet}", body[facet], vocabs, vocab_name, pages)
        for key in ("conflict_setting", "social_protection_modality"):
            if body.get(key) is not None and not isinstance(body[key], str):
                out.append(f"modules.{name}.{key}: must be text or null")
    return out


def check_result(result, vocabs: dict[str, Vocabulary], pages: dict[int, str]) -> list[str]:
    if not isinstance(result, dict):
        return ["the result must be a YAML mapping with core, appraisal and optional modules"]
    out = [f"unknown top-level key {k!r}" for k in sorted(set(result) - _TOP_KEYS)]
    core = result.get("core")
    if not isinstance(core, dict):
        return out + ["core: required mapping"]
    out += [f"core: unknown key {k!r}" for k in sorted(set(core) - _CORE_KEYS)]
    for facet, vocab_name in schema.FACETS.items():
        if facet not in core:
            out.append(f"core.{facet}: required list (write [] when the paper gives nothing)")
            continue
        out += _facts(f"core.{facet}", core[facet], vocabs, vocab_name, pages,
                      extra_keys=("resolution",) if facet == "data_sources" else ())
    out += _geography(core.get("geography"), pages) if "geography" in core else ["core.geography: required mapping"]
    out += _results(core.get("results"), pages)
    out += _appraisal(result.get("appraisal"), pages)
    if "modules" in result:
        out += _modules(result["modules"], vocabs, pages)
    return out
```

- [ ] **Step 4: Verify**

Run: `python -m pytest tests/agent/literature/test_validate.py -q`
Expected: PASS. If `test_proposing_an_existing_term_is_refused` fails because the fixture vocabulary's labels (derived from ids) do not match `"Panel"`, the fixture helper `_vocab` builds label `"panel"`; `find` is case-insensitive, so it should match. Fix the fixture if not.

- [ ] **Step 5: Mutation check**

Delete the `proposed and ... vocab.find(value)` branch; Expected: `test_proposing_an_existing_term_is_refused_and_names_it` fails. Restore.

- [ ] **Step 6: Commit**

```bash
git add agent/literature/validate.py tests/agent/literature/test_validate.py
git commit -m "feat(literature): extraction result validator (vocabulary, quotes, locators, enums)"
```

---

### Task 5: Stage module (papers, task builder, card, apply, proposals ledger)

**Files:**
- Create: `agent/literature/papers.py`, `agent/literature/proposals.py`, `agent/literature/stage.py`
- Modify: `tests/agent/literature/lit_helpers.py` (add `make_index`, `write_vocab_dir`, `fill_card`; created in Task 4)
- Test: `tests/agent/literature/test_papers.py`, `tests/agent/literature/test_stage.py`

**Interfaces:**
- Consumes: Tasks 1-4; `core.agent_tasks.tasks.Task`, `Passage`; `core.agent_tasks.work.task_entry`; `core.indexer.index_card.list_courses`, `load_shard`, `save_shard`.
- Produces:
  - `papers.Paper(file_id, path, title, identity)` (frozen dataclass; `path` is the transcript's path relative to the index root); `papers.eligible_papers(index_root) -> tuple[list[Paper], dict[str, str]]`.
  - `proposals.Proposals(directory)`: `.add(file_id, vocabulary, value, quote, locator, pass_label="a") -> bool`, `.all() -> list[dict]`, `.open() -> list[dict]`.
  - `stage.STAGE = "extract"`, `stage.MAX_CARD_CHARS = 240_000`, `stage.Target(index_root, records, vocabs, proposals)`, `stage.make_tasks(target, papers, *, pass_label="a", redo=False) -> tuple[list[Task], dict[str, str]]`, `stage.validate_result(entry, result, target) -> list[str]`, `stage.apply_result(target, entry, result, provenance) -> str | None`.
  - Task id `extract-<file_id>` (pass a) or `extract-<file_id>-b`; `entry["subject"] = {"file_id", "pass", "transcript_sha", "identity", "vocab_versions"}`; one `Passage` per page with `id="P<n>"`, `ref="page <n>"`.

- [ ] **Step 1: Add the remaining test helpers** to `tests/agent/literature/lit_helpers.py` (add `from pathlib import Path` and `import yaml` to its imports; the `load_shard`/`save_shard` import is shown with the code):

```python
import yaml
from core.indexer.index_card import load_shard, save_shard


def make_index(root, file_id="0123456789abcdef", *, md_text=None, card_extra=None, write_md=True, title="Cash transfers in Somalia"):
    """An index root (research-style) holding one converted journal paper. Appends to the 'economics' shard."""
    rel = f"journal-articles/economics/processed_outputs/{file_id}.md"
    if md_text is None:
        md_text = "\n\n".join(f"<!-- page {n} -->\n\n{text}" for n, text in sorted(PAGES.items()))
    if write_md:
        path = Path(root) / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(md_text, encoding="utf-8", newline="\n")
    card = {"file_id": file_id, "doc_type": "journal_article", "title": title, "path": rel, "course": "economics"}
    card.update(card_extra or {})
    save_shard(str(root), "economics", load_shard(str(root), "economics") + [card])
    return rel


def write_vocab_dir(directory, vocabs=None):
    """Writes the fixture vocabularies as vocab_data-style YAML files."""
    for name, v in (vocabs or VOCABS).items():
        data = {"vocabulary": name, "version": v.version, "provenance": v.provenance, "source": v.source,
                "terms": [{"id": t.id, "label": t.label, **({"definition": t.definition} if t.definition else {})}
                          for t in v.terms.values()]}
        (Path(directory) / f"{name}.yaml").write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
                                                       encoding="utf-8", newline="\n")


def fill_card(card_path, result):
    """Writes `result` into the empty yaml fence under '## Result', as the agent would."""
    p = Path(card_path)
    text = p.read_text(encoding="utf-8")
    marker = "```yaml\n```"
    assert text.count(marker) == 1, "card has no empty result fence"
    p.write_text(text.replace(marker, "```yaml\n" + yaml.safe_dump(result, sort_keys=False, allow_unicode=True) + "```"),
                 encoding="utf-8", newline="\n")
```

- [ ] **Step 2: Write the failing tests**

```python
# tests/agent/literature/test_papers.py
import os
import tempfile
import unittest

from agent.literature.papers import eligible_papers
from lit_helpers import make_index


class TestEligiblePapers(unittest.TestCase):
    def test_a_converted_journal_paper_is_eligible_and_carries_identity(self):
        with tempfile.TemporaryDirectory() as root:
            make_index(root, card_extra={"openalex_id": "https://openalex.org/W9", "doi": "10.1/x",
                                         "publication_year": 2021,
                                         "openalex_topics": [{"id": "https://openalex.org/T1"}]})
            papers, skipped = eligible_papers(root)
        self.assertEqual(skipped, {})
        self.assertEqual(len(papers), 1)
        p = papers[0]
        self.assertEqual(p.file_id, "0123456789abcdef")
        self.assertEqual(p.identity["title"], "Cash transfers in Somalia")
        self.assertEqual(p.identity["doi"], "10.1/x")
        self.assertEqual(p.identity["publication_year"], 2021)
        self.assertEqual(p.identity["openalex_topics"], [{"id": "https://openalex.org/T1"}])

    def test_other_document_types_are_ignored_without_a_skip_reason(self):
        with tempfile.TemporaryDirectory() as root:
            make_index(root, card_extra={"doc_type": "lecture_notes"})
            self.assertEqual(eligible_papers(root), ([], {}))

    def test_unusable_papers_are_skipped_with_a_reason_and_never_raise(self):
        cases = {
            "needs indexing": dict(card_extra={"needs_indexing": True}),
            "no transcript file": dict(write_md=False),
            "no page markers": dict(md_text="plain text with no markers"),
            "invalid file_id": dict(file_id="../x"),
        }
        for needle, kwargs in cases.items():
            with self.subTest(needle=needle), tempfile.TemporaryDirectory() as root:
                make_index(root, **kwargs)
                papers, skipped = eligible_papers(root)
                self.assertEqual(papers, [])
                self.assertEqual(len(skipped), 1)
                self.assertIn(needle, next(iter(skipped.values())))

    def test_an_empty_index_is_fine(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertEqual(eligible_papers(root), ([], {}))


if __name__ == "__main__":
    unittest.main()
```

```python
# tests/agent/literature/test_stage.py
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agent.literature import stage
from agent.literature.papers import eligible_papers
from agent.literature.proposals import Proposals
from agent.literature.store import RecordStore
from core.agent_tasks.work import task_entry
from lit_helpers import PAGES, VOCABS, good, make_index, vocab

PROV = {"driver": "agent", "agent": "antigravity", "run": "r1"}


def _setup(root, **index_kw):
    make_index(root, **index_kw)
    records = RecordStore(Path(root) / ".index" / "study_records")
    target = stage.Target(index_root=str(root), records=records, vocabs=VOCABS, proposals=Proposals(records.dir))
    papers, _ = eligible_papers(str(root))
    return target, papers


def _task(target, papers, **kw):
    tasks, skipped = stage.make_tasks(target, papers, **kw)
    assert len(tasks) == 1, skipped
    return tasks[0]


class TestMakeTasks(unittest.TestCase):
    def test_one_passage_per_page_and_the_vocabularies_are_listed(self):
        with tempfile.TemporaryDirectory() as root:
            target, papers = _setup(root)
            task = _task(target, papers)
        self.assertEqual(task.id, "extract-0123456789abcdef")
        self.assertEqual(task.stage, "extract")
        self.assertEqual([p.ref for p in task.passages], [f"page {n}" for n in sorted(PAGES)])
        self.assertEqual([p.id for p in task.passages], [f"P{n}" for n in sorted(PAGES)])
        self.assertIn("intervention.cash_transfer", task.context)
        self.assertIn("Cash transfers in Somalia", task.context)
        subj = task.subject
        self.assertEqual((subj["file_id"], subj["pass"]), ("0123456789abcdef", "a"))
        self.assertEqual(subj["identity"]["title"], "Cash transfers in Somalia")
        self.assertEqual(subj["vocab_versions"]["intervention"], 1)
        self.assertEqual(len(subj["transcript_sha"]), 16)

    def test_pass_b_has_its_own_task_id(self):
        with tempfile.TemporaryDirectory() as root:
            target, papers = _setup(root)
            self.assertEqual(_task(target, papers, pass_label="b").id, "extract-0123456789abcdef-b")

    def test_an_oversize_transcript_is_skipped_naming_the_limit(self):
        with tempfile.TemporaryDirectory() as root:
            target, papers = _setup(root)
            with patch.object(stage, "MAX_CARD_CHARS", 10):
                tasks, skipped = stage.make_tasks(target, papers)
        self.assertEqual(tasks, [])
        self.assertIn("limit", skipped["0123456789abcdef"])

    def test_a_current_record_is_skipped_unless_redo(self):
        with tempfile.TemporaryDirectory() as root:
            target, papers = _setup(root)
            stage.apply_result(target, task_entry(_task(target, papers)), good(), PROV)
            tasks, skipped = stage.make_tasks(target, papers)
            self.assertEqual(tasks, [])
            self.assertIn("current record", skipped["0123456789abcdef"])
            self.assertEqual(len(stage.make_tasks(target, papers, redo=True)[0]), 1)

    def test_a_changed_transcript_is_extracted_again(self):
        with tempfile.TemporaryDirectory() as root:
            target, papers = _setup(root)
            stage.apply_result(target, task_entry(_task(target, papers)), good(), PROV)
            md = Path(root) / papers[0].path
            md.write_text(md.read_text(encoding="utf-8") + "\n\nA new sentence added later.", encoding="utf-8")
            self.assertEqual(len(stage.make_tasks(target, papers)[0]), 1)

    def test_a_transcript_that_vanished_is_skipped_not_raised(self):
        with tempfile.TemporaryDirectory() as root:
            target, papers = _setup(root)
            (Path(root) / papers[0].path).unlink()
            tasks, skipped = stage.make_tasks(target, papers)
        self.assertEqual(tasks, [])
        self.assertIn("transcript", skipped["0123456789abcdef"])


class TestValidate(unittest.TestCase):
    def test_a_good_result_passes_and_a_fabricated_quote_bounces(self):
        with tempfile.TemporaryDirectory() as root:
            target, papers = _setup(root)
            entry = task_entry(_task(target, papers))
            self.assertEqual(stage.validate_result(entry, good(), target), [])
            bad = good()
            bad["core"]["outcome"][0]["quote"] = "hunger fell by forty percent everywhere"
            self.assertTrue(any("core.outcome[0].quote" in p for p in stage.validate_result(entry, bad, target)))

    def test_a_term_removed_since_the_card_was_made_bounces_and_says_the_vocabulary_changed(self):
        with tempfile.TemporaryDirectory() as root:
            target, papers = _setup(root)
            entry = task_entry(_task(target, papers))
            changed = dict(VOCABS, outcome=vocab("outcome", "outcome.something_else", version=2))
            moved = stage.Target(target.index_root, target.records, changed, target.proposals)
            msgs = stage.validate_result(entry, good(), moved)
        self.assertTrue(any("core.outcome[0].vocab_id" in m for m in msgs), msgs)
        self.assertTrue(any("vocabulary changed" in m for m in msgs), msgs)


class TestApply(unittest.TestCase):
    def test_record_shape_provenance_and_identity(self):
        with tempfile.TemporaryDirectory() as root:
            target, papers = _setup(root, card_extra={"doi": "10.1/x"})
            task = _task(target, papers)
            self.assertIsNone(stage.apply_result(target, task_entry(task), good(), PROV))
            rec = target.records.read("0123456789abcdef")
        self.assertEqual(rec["schema_version"], 1)
        self.assertEqual(rec["identity"]["doi"], "10.1/x")
        self.assertEqual(rec["transcript_sha"], task.subject["transcript_sha"])
        self.assertEqual(rec["core"]["geography"]["countries"], ["SO"])
        self.assertNotIn("modules", rec)
        self.assertEqual(rec["extractor"]["agent_name"], "antigravity")
        self.assertEqual(rec["extractor"]["run_id"], "r1")
        self.assertEqual(rec["extractor"]["prompt_version"], "extract-v1")
        self.assertEqual(rec["extractor"]["pass"], "a")
        self.assertEqual(rec["review"], {"status": "unreviewed", "items_flagged": []})

    def test_modules_are_kept_when_present(self):
        with tempfile.TemporaryDirectory() as root:
            target, papers = _setup(root)
            result = good()
            result["modules"] = {"disaster_conflict": {"hazard_types": [], "conflict_setting": None,
                                                       "social_protection_modality": "cash"}}
            stage.apply_result(target, task_entry(_task(target, papers)), result, PROV)
            self.assertEqual(target.records.read("0123456789abcdef")["modules"], result["modules"])

    def test_pass_b_goes_to_its_own_file(self):
        with tempfile.TemporaryDirectory() as root:
            target, papers = _setup(root)
            stage.apply_result(target, task_entry(_task(target, papers)), good(), PROV)
            stage.apply_result(target, task_entry(_task(target, papers, pass_label="b", redo=True)), good(), PROV)
            self.assertEqual(target.records.read("0123456789abcdef", "b")["extractor"]["pass"], "b")
            self.assertEqual(target.records.read("0123456789abcdef", "a")["extractor"]["pass"], "a")

    def test_proposed_terms_are_ledgered_once_even_if_the_paper_is_extracted_again(self):
        with tempfile.TemporaryDirectory() as root:
            target, papers = _setup(root)
            result = good()
            result["core"]["study_design"] = [{"value": "synthetic control", "proposed": True,
                                               "quote": "using a panel of 1,200 households", "locator": 1}]
            stage.apply_result(target, task_entry(_task(target, papers)), result, PROV)
            stage.apply_result(target, task_entry(_task(target, papers, redo=True)), result, PROV)
            stage.apply_result(target, task_entry(_task(target, papers, pass_label="b", redo=True)), result, PROV)
            items = target.proposals.all()
        self.assertEqual(len(items), 1)
        self.assertEqual((items[0]["vocabulary"], items[0]["value"], items[0]["status"]),
                         ("study_design", "synthetic control", "open"))
        self.assertEqual(items[0]["locator"], 1)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run to verify failure.** Run: `python -m pytest tests/agent/literature/test_papers.py tests/agent/literature/test_stage.py -q`. Expected: FAIL, `ModuleNotFoundError: agent.literature.papers`.

- [ ] **Step 4: Implement**

```python
# agent/literature/papers.py
"""Which converted papers can be extracted, and the identity each carries from its index card."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from core.indexer.index_card import list_courses, load_shard

from .store import check_file_id
from .transcript import split_pages

_IDENTITY_KEYS = ("openalex_id", "doi", "publication_year", "openalex_topics")


@dataclass(frozen=True)
class Paper:
    file_id: str
    path: str
    title: str
    identity: dict


def eligible_papers(index_root: str) -> tuple[list[Paper], dict[str, str]]:
    """Journal papers whose transcript exists and has page markers, plus a file_id -> reason map for the rest."""
    papers: list[Paper] = []
    skipped: dict[str, str] = {}
    for course in list_courses(index_root):
        for card in load_shard(index_root, course):
            if card.get("doc_type") != "journal_article":
                continue
            fid = str(card.get("file_id") or "")
            try:
                check_file_id(fid)
            except ValueError:
                skipped[fid or "(no file_id)"] = "invalid file_id on the index card"
                continue
            if card.get("needs_indexing") or card.get("orphaned"):
                skipped[fid] = "card needs indexing or is orphaned; convert and index the paper first"
                continue
            rel = card.get("path") or ""
            md = Path(index_root) / rel
            if not rel or not md.is_file():
                skipped[fid] = "no transcript file"
                continue
            if not split_pages(md.read_text(encoding="utf-8")):
                skipped[fid] = "transcript has no page markers"
                continue
            identity = {"file_id": fid, "title": card.get("title") or ""}
            identity.update({k: card[k] for k in _IDENTITY_KEYS if card.get(k) is not None})
            papers.append(Paper(fid, rel, identity["title"], identity))
    return papers, skipped
```

```python
# agent/literature/proposals.py
"""Terms the agent proposed because no vocabulary term fit. They wait here for a human decision; nothing is
added to a vocabulary automatically."""
from __future__ import annotations

import json
import os
from pathlib import Path

from .transcript import normalize


class Proposals:
    def __init__(self, directory):
        self.path = Path(directory) / "_proposals.json"

    def all(self) -> list[dict]:
        if not self.path.is_file():
            return []
        return json.loads(self.path.read_text(encoding="utf-8"))

    def open(self) -> list[dict]:
        return [p for p in self.all() if p["status"] == "open"]

    def _save(self, items: list[dict]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n")
        os.replace(tmp, self.path)

    def add(self, file_id: str, vocabulary: str, value: str, quote: str, locator, pass_label: str = "a") -> bool:
        """False when this paper already proposed this value for this vocabulary (any pass, any status)."""
        items = self.all()
        key = (file_id, vocabulary, normalize(value))
        if any((p["file_id"], p["vocabulary"], normalize(p["value"])) == key for p in items):
            return False
        items.append({"id": f"P{len(items) + 1:04d}", "file_id": file_id, "vocabulary": vocabulary, "value": value,
                      "quote": quote, "locator": locator, "pass": pass_label, "status": "open"})
        self._save(items)
        return True
```

```python
# agent/literature/stage.py
"""The extraction stage for core.agent_tasks: build one card per paper, validate the agent's answer, write the record."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from core.agent_tasks.tasks import Passage, Task

from . import schema
from .papers import Paper
from .proposals import Proposals
from .store import RecordStore
from .transcript import split_pages
from .validate import check_result

STAGE = "extract"
MAX_CARD_CHARS = 240_000  # about 60k tokens of transcript; longer papers need chunked extraction, which is not built


@dataclass
class Target:
    index_root: str
    records: RecordStore
    vocabs: dict
    proposals: Proposals


INSTRUCTIONS = """\
Extract a structured study record from the paper whose pages are listed under "Offered passages". Put the answer as
a YAML mapping under `## Result`, in exactly this shape (quote every value that contains a colon):

  core:
    intervention: [{value: "cash transfers", vocab_id: intervention.cash_transfer, quote: "...", locator: 4}]
    outcome: []
    study_design: [{value: "synthetic control", proposed: true, quote: "...", locator: 3}]
    sector: []
    population: []
    data_sources: [{value: "FSNAU", vocab_id: data_source.fsnau, resolution: "district", quote: "...", locator: 5}]
    geography: {countries: [SO], regions: ["Gedo"], scale: subnational, quote: "...", locator: 2}
    results: [{claim: "...", effect_direction: positive, magnitude: "12%", quote: "...", locator: 8}]
  appraisal: {confidence: medium, rationale: "...", quote: "...", locator: 9}
  modules:            # optional
    disaster_conflict: {hazard_types: [], conflict_setting: null, social_protection_modality: null}

Rules:
- State only what the paper itself says. Do not extract from the reference list or from other papers it cites.
- Every fact needs a `quote` copied exactly from the page text (8 to 300 characters; the shortest passage that
  supports the fact) and a `locator`: the page number from the passage's ref (`ref: page 3` means locator 3), or a
  list of page numbers. A quote that is not on the page you cite is rejected.
- Use a `vocab_id` from the vocabularies below when a term fits. If none fits, write `proposed: true` instead of a
  `vocab_id` and a short `value`. Never give both. Do not propose a term that is already listed.
- `countries` are upper-case ISO 3166-1 alpha-2 codes. `scale` is one of local, subnational, national, multi_country,
  global, not_stated. `effect_direction` is one of positive, negative, null, mixed, not_reported.
- `confidence` is your overall confidence in the study's causal claims: low, medium or high, with a one-line rationale.
- Write [] for any facet list the paper does not give. Give at least one result."""


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _task_id(file_id: str, pass_label: str) -> str:
    return f"extract-{file_id}" if pass_label == "a" else f"extract-{file_id}-{pass_label}"


def _vocab_listing(vocabs: dict) -> str:
    names = list(schema.FACETS.values()) + [v for m in schema.MODULE_FACETS.values() for v in m.values()]
    lines: list[str] = []
    for name in names:
        v = vocabs.get(name)
        if v is None:
            continue
        lines += ["", f"Vocabulary {name} (version {v.version}, {v.provenance}):"]
        for t in v.terms.values():
            lines.append(f"- {t.id}: {t.label}" + (f" - {t.definition}" if t.definition else ""))
    return "\n".join(lines)


def make_tasks(target: Target, papers: list[Paper], *, pass_label: str = "a", redo: bool = False):
    tasks: list[Task] = []
    skipped: dict[str, str] = {}
    versions = {n: v.version for n, v in target.vocabs.items()}
    for paper in papers:
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
            skipped[paper.file_id] = (f"transcript is {size} characters, over the {MAX_CARD_CHARS} limit for one card "
                                      f"(chunked extraction is not built)")
            continue
        sha = _sha(md)
        existing = target.records.read(paper.file_id, pass_label)
        if existing and existing.get("transcript_sha") == sha and not redo:
            skipped[paper.file_id] = "a current record already exists (use --redo to extract again)"
            continue
        ident = paper.identity
        context = "\n".join([f"Paper: {paper.title or paper.file_id}", f"file_id: {paper.file_id}",
                             *(f"{k}: {ident[k]}" for k in ("doi", "openalex_id", "publication_year") if k in ident),
                             _vocab_listing(target.vocabs)])
        passages = [Passage(id=f"P{n}", source=paper.title or paper.file_id, ref=f"page {n}", text=text)
                    for n, text in sorted(pages.items())]
        tasks.append(Task(
            id=_task_id(paper.file_id, pass_label), stage=STAGE,
            subject={"file_id": paper.file_id, "pass": pass_label, "transcript_sha": sha, "identity": ident,
                     "vocab_versions": versions},
            instructions=INSTRUCTIONS, context=context, passages=passages))
    return tasks, skipped


def _offered_pages(entry: dict) -> dict[int, str]:
    out: dict[int, str] = {}
    for p in entry.get("passages", []):
        m = re.fullmatch(r"page (\d+)", p.get("ref", ""))
        if m:
            out[int(m.group(1))] = p["text"]
    return out


def validate_result(entry: dict, result: dict, target: Target) -> list[str]:
    problems = check_result(result, target.vocabs, _offered_pages(entry))
    if problems:
        old = entry["subject"].get("vocab_versions", {})
        moved = [n for n, v in old.items() if n in target.vocabs and target.vocabs[n].version != v]
        gone = [n for n in old if n not in target.vocabs]
        if moved or gone:
            problems.append("note: the vocabulary changed since this card was made (" +
                            ", ".join(sorted(moved + gone)) + "); if a vocab_id was removed, run collect again with --redo")
    return problems


def _proposed_facts(result: dict):
    for facet, vocab_name in schema.FACETS.items():
        for fact in result["core"].get(facet, []):
            yield vocab_name, fact
    for module, facets in schema.MODULE_FACETS.items():
        for facet, vocab_name in facets.items():
            for fact in (result.get("modules", {}).get(module, {}) or {}).get(facet, []):
                yield vocab_name, fact


def apply_result(target: Target, entry: dict, result: dict, provenance: dict) -> str | None:
    s = entry["subject"]
    label = s["pass"]
    record = {"schema_version": schema.SCHEMA_VERSION, "identity": s["identity"], "transcript_sha": s["transcript_sha"],
              "core": result["core"], "appraisal": result["appraisal"]}
    if "modules" in result:
        record["modules"] = result["modules"]
    record["extractor"] = {
        "driver": provenance["driver"], "agent_name": provenance["agent"], "run_id": provenance["run"],
        "schema_version": schema.SCHEMA_VERSION, "prompt_version": schema.PROMPT_VERSION, "pass": label,
        "vocab_versions": s["vocab_versions"]}
    record["review"] = {"status": "unreviewed", "items_flagged": []}
    target.records.write(record, label)
    for vocab_name, fact in _proposed_facts(result):
        if fact.get("proposed"):
            target.proposals.add(s["file_id"], vocab_name, fact["value"], fact["quote"], fact["locator"], label)
    return None
```

- [ ] **Step 5: Verify.** Run: `python -m pytest tests/agent/literature -q`. Expected: all pass. If `test_a_changed_transcript_is_extracted_again` fails because the record's hash equals the new one, check that `_sha` hashes the whole markdown, not only the pages.

- [ ] **Step 6: Mutation checks.** (a) Remove the `target.proposals.add(...)` call: the ledger test fails. (b) Replace the `transcript_sha` comparison with `True`: the changed-transcript test fails. Restore both.

- [ ] **Step 7: Commit**

```bash
git add agent/literature/papers.py agent/literature/proposals.py agent/literature/stage.py tests/agent/literature/lit_helpers.py tests/agent/literature/test_papers.py tests/agent/literature/test_stage.py
git commit -m "feat(literature): extraction stage module (task builder, validation, record apply, proposals ledger)"
```

---

### Task 6: CLI: collect, submit, bootstrap, status, api

**Files:**
- Create: `agent/literature/cli.py`, `agent/literature/__main__.py`, `agent/literature/README.md` (short usage; finished in Task 11)
- Test: `tests/agent/literature/test_cli.py`

**Interfaces:**
- Consumes: Task 5; `core.agent_tasks.loop.collect_run`, `submit_run`, `api_run`, `provenance`, `BudgetError`; `core.agent_tasks.work.load_run`.
- Produces: `cli.main(argv: list[str] | None = None, *, complete=None) -> int` (exit code; `complete` injects the API reply function for tests). Commands: `collect [--file-id ID ...] [--run-id R] [--redo] [--double]`, `submit RUN_ID [--agent-name antigravity]`, `bootstrap RUN_ID`, `status`, `api RUN_ID [--approve-cost USD] [--model M]`. Global options: `--index-root` (default `research/` beside `academic-hub/`), `--vocab-dir` (default `agent/literature/vocab_data`), `--work-root` (default `<index-root>/.agent_work`).

- [ ] **Step 1: Write the failing tests**

```python
# tests/agent/literature/test_cli.py
import contextlib
import io
import tempfile
import unittest
from pathlib import Path

import yaml

from agent.literature import cli
from lit_helpers import good, fill_card, make_index, write_vocab_dir

FID = "0123456789abcdef"


def _run(argv, **kw):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = cli.main(argv, **kw)
    return code, out.getvalue()


class Env:
    def __init__(self, root: str):
        self.root = root
        self.vocabs = str(Path(root) / "vocabs")
        Path(self.vocabs).mkdir()
        write_vocab_dir(self.vocabs)
        make_index(root)
        make_index(root, file_id="fedcba9876543210", card_extra={"needs_indexing": True})

    def args(self, *more):
        return ["--index-root", self.root, "--vocab-dir", self.vocabs, *more]

    def card(self, run_id, name):
        return Path(self.root) / ".agent_work" / run_id / "cards" / f"{name}.md"


class TestCollect(unittest.TestCase):
    def test_collect_writes_a_card_per_eligible_paper_and_reports_skips(self):
        with tempfile.TemporaryDirectory() as root:
            env = Env(root)
            code, out = _run(env.args("collect", "--run-id", "r1"))
            self.assertEqual(code, 0)
            self.assertTrue(env.card("r1", f"extract-{FID}").is_file())
            self.assertIn("fedcba9876543210", out)
            self.assertIn("needs indexing", out)

    def test_collect_again_with_the_same_run_id_is_reported_not_a_traceback(self):
        with tempfile.TemporaryDirectory() as root:
            env = Env(root)
            _run(env.args("collect", "--run-id", "r1"))
            code, out = _run(env.args("collect", "--run-id", "r1", "--redo"))
            self.assertEqual(code, 2)
            self.assertIn("r1", out)

    def test_double_also_stages_a_pass_b_card(self):
        with tempfile.TemporaryDirectory() as root:
            env = Env(root)
            _run(env.args("collect", "--run-id", "r1", "--double"))
            self.assertTrue(env.card("r1", f"extract-{FID}-b").is_file())

    def test_unknown_file_id_is_reported(self):
        with tempfile.TemporaryDirectory() as root:
            env = Env(root)
            code, out = _run(env.args("collect", "--file-id", "deadbeefdeadbeef"))
            self.assertIn("deadbeefdeadbeef", out)

    def test_a_work_root_inside_the_records_folder_is_refused(self):
        with tempfile.TemporaryDirectory() as root:
            env = Env(root)
            bad = str(Path(root) / ".index" / "study_records" / "work")
            code, out = _run(env.args("--work-root", bad, "collect", "--run-id", "r1"))
            self.assertEqual(code, 2)
            self.assertIn("inside", out)


class TestSubmit(unittest.TestCase):
    def test_a_filled_card_becomes_a_record_and_a_bad_one_bounces_with_its_reason(self):
        with tempfile.TemporaryDirectory() as root:
            env = Env(root)
            make_index(root, file_id="1111111111111111")
            _run(env.args("collect", "--run-id", "r1"))
            fill_card(env.card("r1", f"extract-{FID}"), good())
            bad = good()
            bad["core"]["outcome"][0]["quote"] = "hunger fell by forty percent everywhere"
            fill_card(env.card("r1", "extract-1111111111111111"), bad)
            code, out = _run(env.args("submit", "r1"))
            self.assertEqual(code, 0)
            self.assertTrue((Path(root) / ".index" / "study_records" / f"{FID}.json").is_file())
            self.assertFalse((Path(root) / ".index" / "study_records" / "1111111111111111.json").exists())
            self.assertIn("core.outcome[0].quote", out)

    def test_an_unfilled_run_reports_untouched(self):
        with tempfile.TemporaryDirectory() as root:
            env = Env(root)
            _run(env.args("collect", "--run-id", "r1"))
            code, out = _run(env.args("submit", "r1"))
            self.assertIn("untouched", out)

    def test_an_unknown_run_is_a_clear_error(self):
        with tempfile.TemporaryDirectory() as root:
            env = Env(root)
            code, out = _run(env.args("submit", "nope"))
            self.assertEqual(code, 2)
            self.assertIn("nope", out)


class TestBootstrapAndStatus(unittest.TestCase):
    def test_bootstrap_names_the_run_and_the_result_block(self):
        with tempfile.TemporaryDirectory() as root:
            env = Env(root)
            code, out = _run(env.args("bootstrap", "r7"))
            self.assertIn("r7", out)
            self.assertIn("## Result", out)
            self.assertIn("submit r7", out)

    def test_status_counts_papers_records_and_proposals(self):
        with tempfile.TemporaryDirectory() as root:
            env = Env(root)
            _, before = _run(env.args("status"))
            self.assertIn("eligible papers: 1", before)
            self.assertIn("records: 0", before)
            _run(env.args("collect", "--run-id", "r1"))
            fill_card(env.card("r1", f"extract-{FID}"), good())
            _run(env.args("submit", "r1"))
            _, after = _run(env.args("status"))
            self.assertIn("records: 1", after)


class TestApi(unittest.TestCase):
    def test_over_budget_sends_nothing(self):
        calls = []
        with tempfile.TemporaryDirectory() as root:
            env = Env(root)
            _run(env.args("collect", "--run-id", "r1"))
            code, out = _run(env.args("api", "r1", "--approve-cost", "0.0000001"), complete=lambda p: calls.append(p) or "")
        self.assertEqual(code, 2)
        self.assertEqual(calls, [])
        self.assertIn("exceeds the approved", out)

    def test_an_approved_run_applies_the_reply(self):
        with tempfile.TemporaryDirectory() as root:
            env = Env(root)
            _run(env.args("collect", "--run-id", "r1"))
            reply = "```yaml\n" + yaml.safe_dump(good(), sort_keys=False, allow_unicode=True) + "```"
            code, out = _run(env.args("api", "r1", "--approve-cost", "5"), complete=lambda p: reply)
            self.assertEqual(code, 0)
            self.assertTrue((Path(root) / ".index" / "study_records" / f"{FID}.json").is_file())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify failure.** Run: `python -m pytest tests/agent/literature/test_cli.py -q`. Expected: FAIL, `ModuleNotFoundError: agent.literature.cli`.

- [ ] **Step 3: Implement**

```python
# agent/literature/cli.py
"""python -m agent.literature <command>: extract study records from converted journal papers."""
from __future__ import annotations

import argparse
from pathlib import Path

from core.agent_tasks.loop import BudgetError, api_run, collect_run, provenance, submit_run
from core.agent_tasks.work import load_run

from . import stage
from .papers import eligible_papers
from .proposals import Proposals
from .store import RecordStore
from .vocab import DATA_DIR, load_vocab_dir

_DEFAULT_ROOT = Path(__file__).resolve().parent.parent.parent.parent / "research"

BOOTSTRAP = """Agent contract for study-record extraction, run '{run}':

1. Open <index-root>/.agent_work/{run}/cards/ and read worklist.md to see which cards are pending.
2. For each pending card: read every page under "Offered passages", then write ONLY the YAML mapping described in the
   card's Instructions inside the ```yaml fence under "## Result". Do not edit any other part of the card or any other file.
3. Copy every quote exactly from the page text and cite its page number as the locator.
4. When you have filled one or more cards, run:
   python -m agent.literature submit {run}
5. If a card comes back marked bounced, fix only what the listed reasons name, in the same fence, and run submit again.
6. Stop when nothing is pending or bounced.
"""


def _target(args) -> stage.Target:
    records = RecordStore(Path(args.index_root) / ".index" / "study_records")
    return stage.Target(str(args.index_root), records, load_vocab_dir(args.vocab_dir), Proposals(records.dir))


def _work_root(args) -> Path:
    return Path(args.work_root) if args.work_root else Path(args.index_root) / ".agent_work"


def cmd_collect(args) -> int:
    target = _target(args)
    papers, skipped = eligible_papers(args.index_root)
    if args.file_id:
        known = {p.file_id for p in papers}
        for fid in args.file_id:
            if fid not in known:
                print(f"{fid}: not an eligible paper ({skipped.get(fid, 'not found in the index')})")
        papers = [p for p in papers if p.file_id in set(args.file_id)]
    tasks, task_skips = stage.make_tasks(target, papers, redo=args.redo)
    if args.double:
        b_tasks, b_skips = stage.make_tasks(target, papers, pass_label="b", redo=args.redo)
        tasks += b_tasks
        task_skips.update({f"{k} (pass b)": v for k, v in b_skips.items()})
    for fid, reason in {**skipped, **task_skips}.items():
        print(f"skipped {fid}: {reason}")
    try:
        run = collect_run(stage.STAGE, tasks, _work_root(args), target.records.dir, run_id=args.run_id, repo_label="records")
    except (ValueError, FileExistsError) as exc:
        print(f"cannot create the run: {exc}")
        return 2
    if run is None:
        print("nothing to collect")
        return 0
    print(f"collected {len(tasks)} card(s) in run {run.run_id}: {run.root}")
    return 0


def _load(args):
    try:
        return load_run(_work_root(args), args.run_id)
    except (FileNotFoundError, ValueError) as exc:
        print(f"cannot load run {args.run_id}: {exc}")
        return None


def _print_report(report) -> None:
    print(f"applied {len(report.applied)}, bounced {len(report.bounced)}, skipped {len(report.skipped)}, "
          f"untouched {len(report.untouched)}")
    for task_id, reasons in report.bounced.items():
        print(task_id)
        for r in reasons:
            print(f"  - {r}")
    for task_id, reason in report.skipped.items():
        print(f"skipped {task_id}: {reason}")


def cmd_submit(args) -> int:
    run = _load(args)
    if run is None:
        return 2
    report = submit_run(run, stage, _target(args), args.agent_name, provenance_fn=provenance, target_label="study records")
    _print_report(report)
    return 0


def cmd_bootstrap(args) -> int:
    print(BOOTSTRAP.format(run=args.run_id))
    return 0


def cmd_status(args) -> int:
    papers, skipped = eligible_papers(args.index_root)
    target = _target(args)
    have = set(target.records.ids())
    print(f"eligible papers: {len(papers)}")
    print(f"skipped papers: {len(skipped)}")
    print(f"records: {len(have & {p.file_id for p in papers})}")
    print(f"papers without a record: {len([p for p in papers if p.file_id not in have])}")
    print(f"open vocabulary proposals: {len(target.proposals.open())}")
    return 0


def _gemini_complete(model: str):
    """A complete(prompt) -> reply using the paid key. The only place this package can spend money; not unit-tested."""
    from core.env.gemini_utils import call_with_retries, get_gemini_client

    client = get_gemini_client("PAID_GEMINI_KEY")
    if client is None:
        raise SystemExit(1)
    return lambda prompt: call_with_retries(
        lambda: client.models.generate_content(model=model, contents=prompt, config={"temperature": 0}).text or "")


def cmd_api(args, complete=None) -> int:
    run = _load(args)
    if run is None:
        return 2
    try:
        report = api_run(run, stage, _target(args), complete or _gemini_complete(args.model), args.approve_cost,
                         provenance_fn=provenance, target_label="study records")
    except BudgetError as exc:
        print(str(exc))
        return 2
    _print_report(report)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m agent.literature", description=__doc__)
    p.add_argument("--index-root", default=str(_DEFAULT_ROOT), help="Research index root (holds .index/ and .agent_work/).")
    p.add_argument("--vocab-dir", default=str(DATA_DIR), help="Directory of vocabulary YAML files.")
    p.add_argument("--work-root", default=None, help="Private card directory (default: <index-root>/.agent_work).")
    sub = p.add_subparsers(dest="command", required=True)
    c = sub.add_parser("collect", help="Write extraction cards (no API calls).")
    c.add_argument("--file-id", action="append", default=[], help="Only this paper (repeatable).")
    c.add_argument("--run-id", default=None)
    c.add_argument("--redo", action="store_true", help="Extract again even if a current record exists.")
    c.add_argument("--double", action="store_true", help="Also stage an independent second pass for each paper.")
    s = sub.add_parser("submit", help="Validate filled cards and write records.")
    s.add_argument("run_id")
    s.add_argument("--agent-name", default="antigravity")
    b = sub.add_parser("bootstrap", help="Print the agent's operating contract.")
    b.add_argument("run_id")
    sub.add_parser("status", help="Counts of papers, records and open proposals.")
    a = sub.add_parser("api", help="Send pending cards to the paid API (explicit opt-in, cost-gated).")
    a.add_argument("run_id")
    a.add_argument("--approve-cost", type=float, default=None, help="Approve up to this many dollars.")
    a.add_argument("--model", default="gemini-3.8-flash")
    return p


def main(argv: list[str] | None = None, *, complete=None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "api":
        return cmd_api(args, complete)
    return {"collect": cmd_collect, "submit": cmd_submit, "bootstrap": cmd_bootstrap, "status": cmd_status}[args.command](args)
```

```python
# agent/literature/__main__.py
from .cli import main

raise SystemExit(main())
```

- [ ] **Step 4: Verify.** Run: `python -m pytest tests/agent/literature -q`. Expected: all pass.

- [ ] **Step 5: Live smoke check without spending anything.** Copy two converted papers' transcripts and their index cards into a scratch git-initialised folder (outside both repos), write a copy of `vocab_data/` there, and run `python -m agent.literature --index-root <scratch> --vocab-dir <scratch>/vocabs collect --run-id smoke`, then `status`. Expected: cards under `<scratch>/.agent_work/smoke/cards/`, `git status` clean in the worktree. (Real vocabularies arrive in Task 10; use the fixture-style files written by `write_vocab_dir` for this check.)

- [ ] **Step 6: Commit**

```bash
git add agent/literature/cli.py agent/literature/__main__.py agent/literature/README.md tests/agent/literature/test_cli.py
git commit -m "feat(literature): collect/submit/bootstrap/status/api commands"
```

---

### Task 7: Double extraction diff

**Files:**
- Create: `agent/literature/compare.py`
- Modify: `agent/literature/stage.py` (call `reconcile` at the end of `apply_result`)
- Test: `tests/agent/literature/test_compare.py`

**Interfaces:**
- Produces: `compare.diff_records(a: dict, b: dict) -> list[str]`; `compare.reconcile(records: RecordStore, file_id: str) -> None`. Facts are compared by identity (`vocab_id`, or `proposed:<normalized value>`); facets as sets; geography countries as a set and `scale` as a value; results by count and the multiset of `effect_direction`; `appraisal.confidence`; module hazard types as a set. Quotes and locators are **not** compared. `reconcile` does nothing unless both passes exist; it never edits pass b and never overrides a human review (`status` already `accepted` or `corrected`); it is idempotent and order-independent.

- [ ] **Step 1: Write the failing tests**

```python
# tests/agent/literature/test_compare.py
import copy
import tempfile
import unittest
from pathlib import Path

from agent.literature import stage
from agent.literature.compare import diff_records, reconcile
from agent.literature.papers import eligible_papers
from agent.literature.proposals import Proposals
from agent.literature.store import RecordStore
from core.agent_tasks.work import task_entry
from lit_helpers import VOCABS, good, make_index

PROV = {"driver": "agent", "agent": "antigravity", "run": "r1"}


def _record(result):
    return {"core": result["core"], "appraisal": result["appraisal"], "identity": {"file_id": "x"}}


class TestDiff(unittest.TestCase):
    def test_identical_records_agree(self):
        self.assertEqual(diff_records(_record(good()), _record(good())), [])

    def test_a_missing_or_different_fact_is_reported_with_both_sides(self):
        b = good()
        b["core"]["intervention"][0]["vocab_id"] = "intervention.voucher"
        msgs = diff_records(_record(good()), _record(b))
        self.assertEqual(len(msgs), 1)
        self.assertIn("core.intervention", msgs[0])
        self.assertIn("intervention.cash_transfer", msgs[0])
        self.assertIn("intervention.voucher", msgs[0])

    def test_proposed_and_vocabulary_versions_of_a_fact_are_different_identities(self):
        b = good()
        b["core"]["study_design"] = [{"value": "panel", "proposed": True, "quote": "using a panel of 1,200 households", "locator": 1}]
        self.assertTrue(any("core.study_design" in m for m in diff_records(_record(good()), _record(b))))

    def test_two_correct_quotes_for_one_fact_are_not_a_disagreement(self):
        b = good()
        b["core"]["outcome"][0]["quote"] = "food consumption by twelve percent"
        b["core"]["outcome"][0]["locator"] = [3]
        self.assertEqual(diff_records(_record(good()), _record(b)), [])

    def test_geography_results_and_appraisal(self):
        b = good()
        b["core"]["geography"]["countries"] = ["SO", "ET"]
        b["core"]["results"][0]["effect_direction"] = "negative"
        b["appraisal"]["confidence"] = "high"
        text = " | ".join(diff_records(_record(good()), _record(b)))
        for needle in ("geography.countries", "core.results", "appraisal.confidence"):
            self.assertIn(needle, text)


def _setup(root):
    make_index(root)
    records = RecordStore(Path(root) / ".index" / "study_records")
    target = stage.Target(str(root), records, VOCABS, Proposals(records.dir))
    papers, _ = eligible_papers(str(root))
    return target, papers


def _apply(target, papers, result, label):
    tasks, _ = stage.make_tasks(target, papers, pass_label=label, redo=True)
    stage.apply_result(target, task_entry(tasks[0]), result, PROV)


def _different():
    b = good()
    b["core"]["intervention"][0]["vocab_id"] = "intervention.voucher"
    return b


class TestReconcile(unittest.TestCase):
    def test_disagreement_is_flagged_on_pass_a_in_either_order(self):
        flagged = []
        for order in (("a", "b"), ("b", "a")):
            with tempfile.TemporaryDirectory() as root:
                target, papers = _setup(root)
                for label in order:
                    _apply(target, papers, good() if label == "a" else _different(), label)
                review = target.records.read("0123456789abcdef", "a")["review"]
                self.assertEqual(review["status"], "needs_review")
                flagged.append(review["items_flagged"])
        self.assertEqual(flagged[0], flagged[1])

    def test_agreement_is_recorded_and_leaves_status_alone(self):
        with tempfile.TemporaryDirectory() as root:
            target, papers = _setup(root)
            _apply(target, papers, good(), "a")
            _apply(target, papers, good(), "b")
            review = target.records.read("0123456789abcdef", "a")["review"]
        self.assertEqual(review, {"status": "unreviewed", "items_flagged": [], "double_pass": "agreed"})

    def test_one_pass_only_changes_nothing(self):
        with tempfile.TemporaryDirectory() as root:
            target, papers = _setup(root)
            _apply(target, papers, good(), "a")
            self.assertEqual(target.records.read("0123456789abcdef", "a")["review"],
                             {"status": "unreviewed", "items_flagged": []})

    def test_reconcile_is_idempotent_and_never_touches_pass_b(self):
        with tempfile.TemporaryDirectory() as root:
            target, papers = _setup(root)
            _apply(target, papers, good(), "a")
            _apply(target, papers, _different(), "b")
            path_b = target.records.path("0123456789abcdef", "b")
            before_a, before_b = target.records.path("0123456789abcdef", "a").read_bytes(), path_b.read_bytes()
            reconcile(target.records, "0123456789abcdef")
            self.assertEqual(target.records.path("0123456789abcdef", "a").read_bytes(), before_a)
            self.assertEqual(path_b.read_bytes(), before_b)

    def test_a_human_review_is_never_overridden(self):
        with tempfile.TemporaryDirectory() as root:
            target, papers = _setup(root)
            _apply(target, papers, good(), "a")
            _apply(target, papers, _different(), "b")
            rec = target.records.read("0123456789abcdef", "a")
            rec["review"] = {"status": "accepted", "items_flagged": []}
            target.records.write(rec, "a")
            reconcile(target.records, "0123456789abcdef")
            self.assertEqual(target.records.read("0123456789abcdef", "a")["review"]["status"], "accepted")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify failure.** Run: `python -m pytest tests/agent/literature/test_compare.py -q`. Expected: FAIL, `ModuleNotFoundError: agent.literature.compare`.

- [ ] **Step 3: Implement**

```python
# agent/literature/compare.py
"""Compare two independent extraction passes over one paper and flag where they disagree."""
from __future__ import annotations

from collections import Counter

from . import schema
from .store import RecordStore
from .transcript import normalize


def _identity(fact: dict) -> str:
    return fact["vocab_id"] if fact.get("vocab_id") else "proposed:" + normalize(fact.get("value", ""))


def _set(facts) -> set[str]:
    return {_identity(f) for f in (facts or [])}


def _only(label: str, sa: set, sb: set) -> str:
    return f"{label}: only in pass a {sorted(sa - sb)}; only in pass b {sorted(sb - sa)}"


def diff_records(a: dict, b: dict) -> list[str]:
    out: list[str] = []
    for facet in schema.FACETS:
        sa, sb = _set(a["core"].get(facet)), _set(b["core"].get(facet))
        if sa != sb:
            out.append(_only(f"core.{facet}", sa, sb))
    ga, gb = a["core"].get("geography", {}), b["core"].get("geography", {})
    ca, cb = set(ga.get("countries", [])), set(gb.get("countries", []))
    if ca != cb:
        out.append(_only("core.geography.countries", ca, cb))
    if ga.get("scale") != gb.get("scale"):
        out.append(f"core.geography.scale: pass a {ga.get('scale')!r}; pass b {gb.get('scale')!r}")
    ra, rb = a["core"].get("results", []), b["core"].get("results", [])
    da, db = Counter(r.get("effect_direction") for r in ra), Counter(r.get("effect_direction") for r in rb)
    if len(ra) != len(rb) or da != db:
        out.append(f"core.results: pass a has {len(ra)} ({dict(da)}); pass b has {len(rb)} ({dict(db)})")
    if a["appraisal"].get("confidence") != b["appraisal"].get("confidence"):
        out.append(f"appraisal.confidence: pass a {a['appraisal'].get('confidence')!r}; pass b {b['appraisal'].get('confidence')!r}")
    for module, facets in schema.MODULE_FACETS.items():
        for facet in facets:
            ma = (a.get("modules", {}).get(module) or {}).get(facet, [])
            mb = (b.get("modules", {}).get(module) or {}).get(facet, [])
            if _set(ma) != _set(mb):
                out.append(_only(f"modules.{module}.{facet}", _set(ma), _set(mb)))
    return out


def reconcile(records: RecordStore, file_id: str) -> None:
    a, b = records.read(file_id, "a"), records.read(file_id, "b")
    if a is None or b is None:
        return
    if a.get("review", {}).get("status") in ("accepted", "corrected"):
        return  # a human has already ruled; never override
    diffs = diff_records(a, b)
    review = {"status": "needs_review" if diffs else "unreviewed", "items_flagged": diffs}
    if not diffs:
        review["double_pass"] = "agreed"
    if a.get("review") != review:
        a["review"] = review
        records.write(a, "a")
```

In `stage.apply_result`, after `target.records.write(record, label)` and before the proposals loop, add: `reconcile(target.records, s["file_id"])` with `from .compare import reconcile` at the top.

- [ ] **Step 4: Verify.** Run: `python -m pytest tests/agent/literature -q`. Expected: all pass, including the unchanged Task 5 tests (a lone pass a still gets `{"status": "unreviewed", "items_flagged": []}`).

- [ ] **Step 5: Mutation check.** Make `_identity` include the quote; Expected: `test_two_correct_quotes_for_one_fact_are_not_a_disagreement` fails. Restore.

- [ ] **Step 6: Commit**

```bash
git add agent/literature/compare.py agent/literature/stage.py tests/agent/literature/test_compare.py
git commit -m "feat(literature): second-pass diff and reconcile into the review block"
```

---

### Task 8: Proposal review functions

**Files:**
- Modify: `agent/literature/proposals.py`, `agent/literature/cli.py` (add `proposals list`)
- Test: `tests/agent/literature/test_proposals.py`

**Interfaces:**
- Produces: `Proposals.accept(proposal_id, term_id, label, *, parent=None, definition="", vocab_dir=None) -> None` (appends the term to `<vocab_dir>/<vocabulary>.yaml` with `source: local`, bumps `version` by 1, validates the whole file before writing anything, then marks the proposal `accepted` with `term_id`); `Proposals.reject(proposal_id, reason="") -> None`; both raise `ValueError` for an unknown or already-decided id. Accepting never rewrites any record. `python -m agent.literature proposals list` prints open proposals.
- The interactive review page (an Artifact with checkboxes, per the repo rule that human-decision steps default to one) is stage 2b and not in this plan; this task gives that page its apply functions.

- [ ] **Step 1: Write the failing tests**

```python
# tests/agent/literature/test_proposals.py
import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from agent.literature import cli
from agent.literature.proposals import Proposals
from agent.literature.vocab import load_vocabulary
from lit_helpers import write_vocab_dir


def _setup(d):
    vocab_dir = Path(d) / "vocabs"
    vocab_dir.mkdir()
    write_vocab_dir(vocab_dir)
    props = Proposals(Path(d) / "records")
    props.add("0123456789abcdef", "study_design", "synthetic control", "a quote long enough", 3)
    return vocab_dir, props


class TestAccept(unittest.TestCase):
    def test_accept_appends_a_valid_local_term_and_bumps_the_version(self):
        with tempfile.TemporaryDirectory() as d:
            vocab_dir, props = _setup(d)
            before = load_vocabulary(vocab_dir / "study_design.yaml")
            props.accept("P0001", "study_design.synthetic_control", "Synthetic control",
                         definition="Weighted comparison units.", vocab_dir=vocab_dir)
            after = load_vocabulary(vocab_dir / "study_design.yaml")
            self.assertEqual(after.version, before.version + 1)
            self.assertEqual(after.provenance, before.provenance)
            self.assertEqual(set(after.terms) - set(before.terms), {"study_design.synthetic_control"})
            self.assertEqual(after.terms["study_design.synthetic_control"].source, "local")
            self.assertEqual(after.find("synthetic control").id, "study_design.synthetic_control")
            self.assertEqual(props.all()[0]["status"], "accepted")
            self.assertEqual(props.all()[0]["term_id"], "study_design.synthetic_control")

    def test_a_bad_term_changes_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            vocab_dir, props = _setup(d)
            text = (vocab_dir / "study_design.yaml").read_text(encoding="utf-8")
            for bad in ("outcome.wrong_prefix", "study_design.panel"):
                with self.subTest(bad=bad), self.assertRaises(ValueError):
                    props.accept("P0001", bad, "X", vocab_dir=vocab_dir)
            self.assertEqual((vocab_dir / "study_design.yaml").read_text(encoding="utf-8"), text)
            self.assertEqual(props.all()[0]["status"], "open")

    def test_unknown_or_decided_ids_raise(self):
        with tempfile.TemporaryDirectory() as d:
            vocab_dir, props = _setup(d)
            with self.assertRaises(ValueError):
                props.accept("P9999", "study_design.x", "X", vocab_dir=vocab_dir)
            props.reject("P0001", "not needed")
            with self.assertRaises(ValueError):
                props.accept("P0001", "study_design.x", "X", vocab_dir=vocab_dir)
            with self.assertRaises(ValueError):
                props.reject("P0001")


class TestRejectAndList(unittest.TestCase):
    def test_reject_records_the_reason_and_drops_it_from_open(self):
        with tempfile.TemporaryDirectory() as d:
            _, props = _setup(d)
            props.reject("P0001", "duplicate of panel")
            self.assertEqual(props.open(), [])
            self.assertEqual(props.all()[0]["reason"], "duplicate of panel")

    def test_list_shows_open_proposals(self):
        with tempfile.TemporaryDirectory() as d:
            records = Path(d) / ".index" / "study_records"
            Proposals(records).add("0123456789abcdef", "study_design", "synthetic control", "a quote long enough", 3)
            (Path(d) / "vocabs").mkdir()
            write_vocab_dir(Path(d) / "vocabs")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = cli.main(["--index-root", d, "--vocab-dir", str(Path(d) / "vocabs"), "proposals", "list"])
        self.assertEqual(code, 0)
        for needle in ("P0001", "study_design", "synthetic control", "0123456789abcdef", "page 3"):
            self.assertIn(needle, out.getvalue())

    def test_listing_with_no_proposals_does_not_crash(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "vocabs").mkdir()
            write_vocab_dir(Path(d) / "vocabs")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = cli.main(["--index-root", d, "--vocab-dir", str(Path(d) / "vocabs"), "proposals", "list"])
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify failure.** Run: `python -m pytest tests/agent/literature/test_proposals.py -q`. Expected: FAIL (`AttributeError: ... accept`; `error: invalid choice: 'proposals'`).

- [ ] **Step 3: Implement** (append to `Proposals` and the CLI)

```python
# agent/literature/proposals.py  (additions)
import yaml

from .vocab import DATA_DIR, validate_vocabulary


    def _get(self, items: list[dict], proposal_id: str) -> dict:
        for p in items:
            if p["id"] == proposal_id:
                if p["status"] != "open":
                    raise ValueError(f"proposal {proposal_id} is already {p['status']}")
                return p
        raise ValueError(f"no proposal {proposal_id}")

    def accept(self, proposal_id: str, term_id: str, label: str, *, parent: str | None = None,
               definition: str = "", vocab_dir=None) -> None:
        items = self.all()
        p = self._get(items, proposal_id)
        path = Path(vocab_dir or DATA_DIR) / f"{p['vocabulary']}.yaml"
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        term = {"id": term_id, "label": label, "source": "local"}
        if parent:
            term["parent"] = parent
        if definition:
            term["definition"] = definition
        data["terms"].append(term)
        data["version"] += 1
        problems = validate_vocabulary(data)
        if problems:
            raise ValueError("; ".join(problems))  # nothing has been written yet
        path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8", newline="\n")
        p["status"], p["term_id"] = "accepted", term_id
        self._save(items)

    def reject(self, proposal_id: str, reason: str = "") -> None:
        items = self.all()
        p = self._get(items, proposal_id)
        p["status"], p["reason"] = "rejected", reason
        self._save(items)
```

CLI: add a `proposals` subparser with a `list` sub-subcommand (`--index-root` global) and `cmd_proposals(args)` printing, for each open proposal, `P0001  study_design  'synthetic control'  paper 0123456789abcdef  page 3`. `accept` and `reject` are Python functions only in this plan (the review page calls them).

- [ ] **Step 4: Verify.** Run: `python -m pytest tests/agent/literature -q`. Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add agent/literature/proposals.py agent/literature/cli.py tests/agent/literature/test_proposals.py
git commit -m "feat(literature): accept/reject vocabulary proposals and list them"
```

---

### Task 9: Gold set format and evaluation

**Files:**
- Create: `agent/literature/gold.py`, `agent/literature/gold/README.md`
- Modify: `agent/literature/cli.py` (add `eval`)
- Test: `tests/agent/literature/test_gold.py`

**Interfaces:**
- Gold file `agent/literature/gold/gold_set.yaml` (committed: expected values only, never quotes or paper text):

```yaml
version: 1
papers:
  - file_id: 0123456789abcdef          # the index card's file_id
    expect:
      countries: [SO]
      study_design: [study_design.panel]        # vocab ids
      data_sources: ["FSNAU", "ACLED"]          # vocab ids, or labels/values (matched case- and space-insensitively)
      intervention: []
      outcome: []
    notes: ""
```

- Produces: `gold.load_gold(path) -> list[dict]` (raises `ValueError` listing every problem: missing `file_id`, unknown facet, non-list values, wrong `version`); `gold.score_record(record, expect, vocabs) -> dict[str, dict]` (per facet `{"expected", "found", "matched"}` counts); `gold.summarize(per_paper: dict[str, dict | None], *, proposals: list[dict], records: int, manifests: list[dict], double: dict) -> dict` with `facet_precision`, `facet_recall` (micro-averaged over all papers; a paper with no record, `None`, counts its expected items as unmatched), `proposal_rate` (proposals per record), `bounce_rate` (cards with `attempts > 0` over cards in extract manifests), `double_pass_agreement` (agreed / compared, `None` when none compared). Empty inputs give zeros or `None`, never a crash. `python -m agent.literature eval [--gold PATH]` prints the summary as JSON (aggregates only).
- Metric note (amends spec section 9): "quote-verification rate" is reported as `bounce_rate`, because every applied quote has by construction been verified, and the manifest keeps only the latest bounce reasons, so a per-quote failure rate cannot be reconstructed.

- [ ] **Step 1: Write the failing tests**

```python
# tests/agent/literature/test_gold.py
import tempfile
import unittest
from pathlib import Path

import yaml

from agent.literature.gold import load_gold, score_record, summarize
from lit_helpers import VOCABS


def _record(**facets):
    core = {"intervention": [], "outcome": [], "study_design": [], "sector": [], "population": [], "data_sources": [],
            "geography": {"countries": [], "regions": [], "scale": "not_stated"}, "results": []}
    core.update(facets)
    return {"core": core, "appraisal": {}}


def _gold(tmp, papers, version=1):
    p = Path(tmp) / "gold_set.yaml"
    p.write_text(yaml.safe_dump({"version": version, "papers": papers}), encoding="utf-8")
    return p


class TestLoad(unittest.TestCase):
    def test_a_good_file_loads(self):
        with tempfile.TemporaryDirectory() as d:
            papers = load_gold(_gold(d, [{"file_id": "abc", "expect": {"countries": ["SO"]}}]))
        self.assertEqual(papers[0]["file_id"], "abc")

    def test_every_problem_is_listed(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError) as ctx:
                load_gold(_gold(d, [{"expect": {"colour": ["red"]}}, {"file_id": "x", "expect": {"countries": "SO"}}], version=2))
        text = str(ctx.exception)
        for needle in ("version", "file_id", "colour", "countries"):
            self.assertIn(needle, text)


class TestScore(unittest.TestCase):
    def test_matches_by_vocab_id_label_and_proposed_value(self):
        rec = _record(
            study_design=[{"value": "panel", "vocab_id": "study_design.panel"}],
            data_sources=[{"value": "FSNAU", "vocab_id": "data_source.fsnau"}, {"value": "ACLED", "proposed": True}],
            geography={"countries": ["SO"], "regions": [], "scale": "national"})
        expect = {"study_design": ["study_design.panel"], "data_sources": ["FSNAU", "acled"], "countries": ["SO"]}
        s = score_record(rec, expect, VOCABS)
        self.assertEqual(s["study_design"], {"expected": 1, "found": 1, "matched": 1})
        self.assertEqual(s["data_sources"], {"expected": 2, "found": 2, "matched": 2})
        self.assertEqual(s["countries"], {"expected": 1, "found": 1, "matched": 1})

    def test_extra_and_missing_items_lower_precision_and_recall_counts(self):
        rec = _record(study_design=[{"value": "panel", "vocab_id": "study_design.panel"},
                                    {"value": "rct", "proposed": True}])
        s = score_record(rec, {"study_design": ["study_design.panel", "did"]}, VOCABS)
        self.assertEqual(s["study_design"], {"expected": 2, "found": 2, "matched": 1})


class TestSummarize(unittest.TestCase):
    def test_micro_averages_and_missing_records(self):
        per = {"a": {"study_design": {"expected": 2, "found": 2, "matched": 1}},
               "b": None}  # no record for paper b
        expects = {"a": {"study_design": ["x", "y"]}, "b": {"study_design": ["z"]}}
        s = summarize(per, expects=expects, proposals=[{}, {}], records=1,
                      manifests=[{"tasks": [{"attempts": 0}, {"attempts": 2}]}],
                      double={"compared": 2, "agreed": 1})
        self.assertAlmostEqual(s["facet_precision"], 1 / 2)
        self.assertAlmostEqual(s["facet_recall"], 1 / 3)
        self.assertEqual(s["proposal_rate"], 2.0)
        self.assertEqual(s["bounce_rate"], 0.5)
        self.assertEqual(s["double_pass_agreement"], 0.5)
        self.assertEqual(s["papers_missing_a_record"], ["b"])

    def test_empty_inputs_do_not_crash(self):
        s = summarize({}, expects={}, proposals=[], records=0, manifests=[], double={"compared": 0, "agreed": 0})
        self.assertEqual((s["facet_precision"], s["facet_recall"], s["proposal_rate"], s["bounce_rate"]), (0.0, 0.0, 0.0, 0.0))
        self.assertIsNone(s["double_pass_agreement"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify failure.** Run: `python -m pytest tests/agent/literature/test_gold.py -q`. Expected: FAIL, `ModuleNotFoundError: agent.literature.gold`.

- [ ] **Step 3: Implement**

```python
# agent/literature/gold.py
"""The hand-checked gold set and the evaluation summary computed against it. Aggregates only; no paper text."""
from __future__ import annotations

from pathlib import Path

import yaml

from . import schema
from .transcript import normalize

EXPECT_KEYS = set(schema.FACETS) | {"countries"}
DEFAULT_PATH = Path(__file__).resolve().parent / "gold" / "gold_set.yaml"


def load_gold(path) -> list[dict]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    problems: list[str] = []
    if not isinstance(data, dict) or data.get("version") != 1:
        raise ValueError("version: the gold file must be a mapping with version: 1")
    papers = data.get("papers")
    if not isinstance(papers, list):
        raise ValueError("papers: must be a list")
    for i, p in enumerate(papers):
        where = f"papers[{i}]"
        if not isinstance(p, dict) or not p.get("file_id"):
            problems.append(f"{where}: file_id is required")
            continue
        expect = p.get("expect") or {}
        for k, v in expect.items():
            if k not in EXPECT_KEYS:
                problems.append(f"{where}.expect: unknown facet {k!r}")
            elif not isinstance(v, list) or not all(isinstance(x, str) for x in v):
                problems.append(f"{where}.expect.{k}: must be a list of text")
    if problems:
        raise ValueError("; ".join(problems))
    return papers


def _found_keys(record: dict, facet: str) -> set[str]:
    if facet == "countries":
        return set(record["core"].get("geography", {}).get("countries", []))
    return {f["vocab_id"] if f.get("vocab_id") else "v:" + normalize(f["value"]) for f in record["core"].get(facet, [])}


def _expected_keys(items: list[str], facet: str, vocabs: dict) -> set[str]:
    if facet == "countries":
        return set(items)
    vocab = vocabs.get(schema.FACETS[facet])
    out = set()
    for item in items:
        if vocab is not None and vocab.contains(item):
            out.add(item)
        elif vocab is not None and (term := vocab.find(item)) is not None:
            out.add(term.id)
        else:
            out.add("v:" + normalize(item))
    return out


def score_record(record: dict, expect: dict, vocabs: dict) -> dict[str, dict]:
    out = {}
    for facet, items in expect.items():
        want, got = _expected_keys(items, facet, vocabs), _found_keys(record, facet)
        out[facet] = {"expected": len(want), "found": len(got), "matched": len(want & got)}
    return out


def _ratio(n: float, d: float) -> float:
    return n / d if d else 0.0


def summarize(per_paper: dict[str, dict | None], *, expects: dict[str, dict], proposals: list, records: int,
              manifests: list[dict], double: dict) -> dict:
    matched = found = expected = 0
    missing: list[str] = []
    for fid, scores in per_paper.items():
        if scores is None:
            missing.append(fid)
            expected += sum(len(v) for v in expects.get(fid, {}).values())
            continue
        for s in scores.values():
            matched += s["matched"]
            found += s["found"]
            expected += s["expected"]
    cards = [t for m in manifests for t in m.get("tasks", [])]
    bounced = sum(1 for t in cards if t.get("attempts", 0) > 0)
    compared = double.get("compared", 0)
    return {
        "facet_precision": _ratio(matched, found), "facet_recall": _ratio(matched, expected),
        "proposal_rate": _ratio(len(proposals), records), "bounce_rate": _ratio(bounced, len(cards)),
        "double_pass_agreement": (double["agreed"] / compared) if compared else None,
        "papers_missing_a_record": missing, "papers_scored": len(per_paper),
    }
```

CLI `eval`: load the gold file (default `DEFAULT_PATH`; message and exit 2 if missing); for each gold paper read `records.read(file_id)`, `score_record`; collect `expects`; load every run manifest under `<work-root>` whose `stage == "extract"` (`load_run`, ignoring unreadable folders); `double` = over papers with a pass-b record, `compared` count and `agreed` where pass a's `review.get("double_pass") == "agreed"`; print `json.dumps(summarize(...), indent=2)`. Add a CLI test in `test_cli.py` that evaluates a one-paper gold file against a record produced through `submit`, and one where the gold paper has no record.

- [ ] **Step 4: Verify.** Run: `python -m pytest tests/agent/literature -q`. Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add agent/literature/gold.py agent/literature/gold agent/literature/cli.py tests/agent/literature/test_gold.py tests/agent/literature/test_cli.py
git commit -m "feat(literature): gold set format and evaluation summary"
```

---

### Task 10: Load the 3ie codebook and run the pilot (gated: needs the owner's material and time)

This task cannot be completed by an executor alone. Tasks 1-9 are fully testable without it. Stop after Task 9 and report; resume here when the owner supplies the 3ie material.

**Inputs from the owner:** the 3ie classification documents: intervention, outcome, sector and study-design/evaluation-method lists with definitions; population and geography conventions; the critical-appraisal confidence criteria; and the licence or terms for reuse.

- [ ] **Step 1: Convert** the 3ie lists into `agent/literature/vocab_data/<vocabulary>.yaml` files in the documented format with `provenance: 3ie` and `source:` naming the exact document and date. Add `data_source` and `hazard_type` lists as `provisional` only where 3ie has no equivalent. Run `python -m pytest tests/agent/literature/test_vocab.py -q` and a loader check (`load_vocab_dir()` must succeed). If the licence forbids committing the machine-readable lists, keep them in an ignored directory and pass `--vocab-dir`.
- [ ] **Step 2: Adapt `appraisal`** to 3ie's confidence criteria: update the card instructions text (bump `PROMPT_VERSION` to `extract-v2` and add a test pinning the new version) so the agent applies their criteria and the rationale cites them.
- [ ] **Step 3: Choose the gold set** (about 10 converted papers, spanning designs and regions; the pitch's Warsame et al. paper must be included if converted: the live research index currently has only 21 converted `journal_article` cards of about 106 downloaded PDFs, and none matched Warsame or Somalia in a text scan, so it may need converting first with `python -m pipelines.convert_journal_articles.convert_journal_articles --collect` / `--submit`). The owner hand-checks the expected values into `gold/gold_set.yaml` (no quotes).
- [ ] **Step 4: Pilot run.** `python -m agent.literature collect --double --file-id <each gold paper>`; the owner hands the cards to Antigravity using `bootstrap`; `submit`; resubmit bounced cards; then `python -m agent.literature eval`. Record the numbers in a status doc: facet precision/recall, proposal rate, bounce rate, double-pass agreement, and the known failure cases.
- [ ] **Step 5: Decide** with the owner from the numbers whether prompt changes (then `extract-v3`), vocabulary additions (accept proposals), or the table-image attachments deferred in decision 4 are needed before running the remaining converted papers.

---

### Task 11: Docs, spec amendments, status

**Files:**
- Modify: `agent/literature/README.md` (finish: purpose, commands, record shape, vocab format, the gitignore note, what is not here), `docs/superpowers/specs/literature_taxonomy/2026-10-15-literature-taxonomy-pipeline-design.md`
- Create: `docs/status/literature/2026-10-16-stage2-extraction.md`

- [ ] **Step 1: Spec amendments (dated 2026-10-16).** Section 12: record decisions 1-4 above as resolved (and decision 4 of the spec's list, the rendered-review vault location, stays open for stage 3). Section 6 stage 2: locators are page numbers (cards use one `Passage` per page); results use the three groups `core`, `appraisal`, `modules`; the metric definitions from Task 9; the `proposed` flag rule; proposals review page is stage 2b. Section 3 / corpus note: only 21 of about 106 downloaded papers are converted and the pitch's Warsame check paper is not converted.
- [ ] **Step 2: Status doc** with the verification summary (suite counts, mutation checks) and the explicit "not done" list: Task 10 pilot, stage 2b review page, table images, chunking for papers over the size cap.
- [ ] **Step 3: Full verification** in per-directory chunks (the single full run was killed once for memory): `agent`, `audio_generator`, `core`, `discovery`, `pipelines`, `resume_manager`, `tools`. Expected: all pass except the three `tests/tools/` website-sync collection errors (`jsonschema` missing from the shared venv, pre-existing).
- [ ] **Step 4: Commit**

```bash
git add agent/literature/README.md docs/superpowers/specs/literature_taxonomy/2026-10-15-literature-taxonomy-pipeline-design.md docs/status/literature/2026-10-16-stage2-extraction.md
git commit -m "docs(literature): stage 2 usage, spec amendments, status"
```

## Self-review notes

- **Spec coverage:** record shape (Tasks 1, 4, 5), vocabularies with seed-from-3ie and `proposed` terms (Tasks 2, 5, 8, 10), quote and locator verification (Tasks 3, 4), task cards per paper with bounce on failure (Tasks 5, 6), gold set and metrics (Task 9, 10), double extraction (Tasks 6, 7), OpenAlex identity carried into records (Task 5 `identity`), cost gate and subscription default (Task 6).
- **Types:** `check_result(result, vocabs, pages)` (Task 4) is what `stage.validate_result` calls (Task 5); `RecordStore.write(record, pass_label)` (Task 1) is used by `apply_result` and `reconcile` (Tasks 5, 7); `Proposals.add` (Task 5) is extended by `accept`/`reject` (Task 8) without signature changes.
- **Dependencies:** none added. `pycountry` and `jsonschema` are not installed in the shared venv and are not used; countries come from a committed file generated from `tzdata`.
- **Deliberately not here:** Obsidian/vault rendering and synthesis (stage 3), the derived database (stage 4), the interactive proposal-review page (2b), table-image attachments, paper chunking above the size cap.
