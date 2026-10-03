# Subset-Note Linking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Link each handwriting-only Excalidraw lecture note to its "with slides" superset on the subset's index card, and make default search/passage-search return only the superset.

**Architecture:** A new `core/indexer/related.py` detects pairs (same course+folder+date, slides-flag direction) and confirms them by word-3-gram containment of the subset's handwriting inside the superset's `[Handwritten]` blocks, writing `subset_of`/`subset_link_score` on the subset card. `search()` drops any card whose `subset_of` superset is also a surviving candidate (so dangling links never hide content); `search_passages()` inherits this. Linking runs from the Excalidraw `write_outputs` hook and from `rebuild`, both non-fatal.

**Tech Stack:** Python 3.13, pytest, existing `core.indexer.index_card` shard I/O, `core.env.frontmatter.parse_frontmatter`.

**Spec:** `docs/superpowers/specs/indexer/2026-10-03-subset-note-linking-design.md`

**Working directory for every command:** the worktree's `ai-sandbox/academic-rag-model/` (branch `claude/excalidraw-slides`). Use the main checkout's venv: `/c/Users/theaa/ai-sandbox-master/ai-sandbox/academic-rag-model/.venv/Scripts/python`, referred to below as `$PY`. Stage explicit paths only; never `git add -A`.

## Global Constraints

- Containment threshold is **0.3**; n-gram size is **3**; tokens are `[A-Za-z]{3,}` or `\\[A-Za-z]+` after lowercasing (this exact tokenization reproduced the measured 0.59 to 0.83 true-pair / <= 0.02 non-pair separation).
- Links are one level only: a subset's `subset_of` never points at another subset.
- A dangling or unusable link must never hide content: the subset is returned whenever its superset is not a surviving search candidate.
- `core/indexer` is shared: the full suite (1857+ tests) must pass after the last task.
- Linking failures are always non-fatal (print a `WARNING:` line, continue).
- Commits end with: `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.
- Never print or commit API keys. The real-data task uses `--dry-run` first and applies only with the user's go-ahead.
- **Deviation from the spec (fixing it is Task 5):** the overrides file lives at `.index/links/overrides.json`, not `.index/links_overrides.json`. A top-level `.index/*.json` would be treated by `list_courses()` and `_flag_or_prune_orphans` as a course shard (see `duplicate_check.py`'s note on `.index/duplicates/`); a subdirectory is invisible to both.

## Review Focus

- Same-day lecture and recitation notes (different content, same date): must not link. (Task 2 test.)
- A "with slides" note and a plain note whose filenames share no parsable date: must not link. (Task 2 test.)
- Superset deleted/unindexed after linking: subset must reappear in default search and the stale link must be cleared on the next link pass. (Tasks 2 and 3 tests.)
- Superset excluded by the caller's own filters (e.g. `max_level`) while the subset passes: subset must still be returned. (Task 3 test.)
- Raw transcript missing on disk (e.g. the orphaned `Drawing 2026-09-07` card): excluded from linking, no crash. (Task 2 test.)

## File Structure

- Create `core/indexer/related.py` — all link detection, overrides, CLI. One responsibility: decide and record subset links.
- Modify `core/indexer/index_search.py` — `include_subsets` on `search`/`search_passages`, CLI flag, `rebuild` hook.
- Modify `pipelines/transcribe_notes/transcribe_excalidraw.py` — `write_outputs` hook.
- Create `tests/core/indexer/test_related.py`; modify `tests/core/indexer/test_index_search.py`, `tests/pipelines/transcribe_notes/test_transcribe_excalidraw.py`.
- Modify `core/indexer/README.md` and the spec (overrides path).

---

### Task 1: Text extraction and containment primitives

**Files:**
- Create: `core/indexer/related.py`
- Test: `tests/core/indexer/test_related.py`

**Interfaces:**
- Produces (used by Task 2):
  - `CONTAINMENT_THRESHOLD: float = 0.3`
  - `raw_transcript_path(card_path: str) -> str | None` — `".../X.excalidraw.rag.md"` -> `".../X.excalidraw.md"`, else `None`.
  - `read_raw(academic_hub_root: str, card: dict) -> tuple[dict, str] | None` — `(frontmatter_fields, body)` of the card's raw transcript, `None` if the path doesn't map or the file is missing.
  - `handwriting_text(meta: dict, body: str) -> str` — slides note (`meta["embedded_slides"] == "true"`): only `**[Handwritten]**` blocks; otherwise the whole body; chunk markers always removed.
  - `containment(subset_text: str, superset_text: str) -> float` — fraction of the subset's word 3-grams present in the superset's; `0.0` if the subset has none.
  - `lecture_date(card_path: str) -> str | None` — first `YYYY-MM-DD` in the file's basename.

- [ ] **Step 1: Write the failing tests**

Create `tests/core/indexer/test_related.py`:

```python
import os

from core.indexer.related import (
    containment,
    handwriting_text,
    lecture_date,
    raw_transcript_path,
    read_raw,
)

HW = (
    "preference relation complete transitive define strict preference asymmetric "
    "indifference symmetric choice set nonempty by completeness utility function "
    "represents preferences ordinal"
)
HW_OTHER = (
    "consumer demand slutsky equation income substitution effect compensated hicksian "
    "marshallian expenditure minimization duality"
)


def test_raw_transcript_path_drops_the_rag_infix():
    assert raw_transcript_path("a/processed_outputs/X 2026-09-15.excalidraw.rag.md") == (
        "a/processed_outputs/X 2026-09-15.excalidraw.md"
    )


def test_raw_transcript_path_is_none_for_other_cards():
    assert raw_transcript_path("a/textbook.md") is None


def test_lecture_date_reads_first_iso_date_from_basename():
    assert lecture_date("a/b/Microeconomics with slides 2026-09-15 10.15.55.excalidraw.rag.md") == "2026-09-15"
    assert lecture_date("a/2026-01-01/Microeconomics.excalidraw.rag.md") is None


def test_handwriting_text_slides_note_keeps_only_handwritten_blocks():
    body = (
        "<!-- chunk 1 -->\n\n**[Slide]**\nslide words here\n\n**[Handwritten]**\n"
        f"{HW}\n\n<!-- chunk 2 -->\n\n**[Slide]**\nmore slide words\n"
    )
    text = handwriting_text({"embedded_slides": "true"}, body)
    assert "preference relation" in text
    assert "slide words" not in text
    assert "chunk" not in text


def test_handwriting_text_plain_note_is_whole_body_without_chunk_markers():
    text = handwriting_text({}, f"<!-- chunk 1 -->\n\n{HW}\n")
    assert "preference relation" in text
    assert "chunk" not in text


def test_containment_identical_is_one_and_disjoint_is_zero():
    assert containment(HW, HW) == 1.0
    assert containment(HW, HW_OTHER) == 0.0


def test_containment_is_asymmetric_subset_in_superset():
    assert containment(HW, HW + " " + HW_OTHER) == 1.0
    assert containment(HW + " " + HW_OTHER, HW) < 0.6


def test_containment_of_text_with_no_ngrams_is_zero():
    assert containment("", HW) == 0.0
    assert containment("two words", HW) == 0.0


def test_read_raw_returns_frontmatter_and_body_or_none(tmp_path):
    out = tmp_path / "academic_notes" / "c" / "lecture_notes" / "processed_outputs"
    out.mkdir(parents=True)
    (out / "N 2026-09-15.excalidraw.md").write_text("---\nchunks: 2\nembedded_slides: true\n---\n\nBODY", encoding="utf-8")
    card = {"path": "academic_notes/c/lecture_notes/processed_outputs/N 2026-09-15.excalidraw.rag.md"}
    meta, body = read_raw(str(tmp_path), card)
    assert meta["embedded_slides"] == "true" and body == "BODY"
    assert read_raw(str(tmp_path), {"path": "academic_notes/c/lecture_notes/processed_outputs/Gone.excalidraw.rag.md"}) is None
    assert read_raw(str(tmp_path), {"path": "x.md"}) is None
```

- [ ] **Step 2: Run to verify failure**

Run: `$PY -m pytest tests/core/indexer/test_related.py -q`
Expected: collection error `ModuleNotFoundError: No module named 'core.indexer.related'`.

- [ ] **Step 3: Implement**

Create `core/indexer/related.py`:

```python
"""
related.py
Links a handwriting-only Excalidraw lecture note (the "subset") to its
"with slides" counterpart (the "superset") on the subset's index card, so
default search can return just the superset. Detection: same course and
folder, same YYYY-MM-DD in the filename, the superset's raw transcript
flagged embedded_slides: true and the subset's not -- then confirmed by
word-3-gram containment of the subset's handwriting inside the superset's
[Handwritten] blocks (whole-card embeddings were measured and cannot
separate true pairs from different lectures on the same topic).

Spec: docs/superpowers/specs/indexer/2026-10-03-subset-note-linking-design.md
"""
from __future__ import annotations

import os
import re

from core.env.frontmatter import parse_frontmatter

CONTAINMENT_THRESHOLD = 0.3
_NGRAM = 3

_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
_LABEL_RE = re.compile(r"^\*\*\[(Slide|Handwritten)\]\*\*[ \t]*$", re.MULTILINE)
_CHUNK_MARKER_RE = re.compile(r"^<!-- chunk \d+ -->[ \t]*$", re.MULTILINE)
_TOKEN_RE = re.compile(r"[A-Za-z]{3,}|\\[A-Za-z]+")
_RAG_SUFFIX = ".excalidraw.rag.md"


def raw_transcript_path(card_path: str) -> str | None:
    if not card_path.endswith(_RAG_SUFFIX):
        return None
    return card_path[: -len(_RAG_SUFFIX)] + ".excalidraw.md"


def lecture_date(card_path: str) -> str | None:
    match = _DATE_RE.search(os.path.basename(card_path))
    return match.group(0) if match else None


def read_raw(academic_hub_root: str, card: dict) -> tuple[dict, str] | None:
    rel = raw_transcript_path(card.get("path", ""))
    if rel is None:
        return None
    full = os.path.join(academic_hub_root, *rel.split("/"))
    if not os.path.exists(full):
        return None
    with open(full, encoding="utf-8") as f:
        return parse_frontmatter(f.read())


def handwriting_text(meta: dict, body: str) -> str:
    text = _CHUNK_MARKER_RE.sub("", body)
    if meta.get("embedded_slides", "").strip().lower() != "true":
        return text
    parts = _LABEL_RE.split(text)  # [pre, label, body, label, body, ...]
    return "\n".join(parts[i + 1] for i in range(1, len(parts) - 1, 2) if parts[i] == "Handwritten")


def _ngrams(text: str) -> set[tuple[str, ...]]:
    words = _TOKEN_RE.findall(text.lower())
    return {tuple(words[i : i + _NGRAM]) for i in range(len(words) - _NGRAM + 1)}


def containment(subset_text: str, superset_text: str) -> float:
    sub = _ngrams(subset_text)
    if not sub:
        return 0.0
    return len(sub & _ngrams(superset_text)) / len(sub)
```

- [ ] **Step 4: Run to verify pass**

Run: `$PY -m pytest tests/core/indexer/test_related.py -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add ai-sandbox/academic-rag-model/core/indexer/related.py ai-sandbox/academic-rag-model/tests/core/indexer/test_related.py
git commit -m "feat(indexer): subset-link text primitives (handwriting extraction, containment)"
```
(Run from the repo root of the worktree, or adjust paths.)

---

### Task 2: Pair detection, overrides, `link_subsets`, CLI

**Files:**
- Modify: `core/indexer/related.py`
- Test: `tests/core/indexer/test_related.py`

**Interfaces:**
- Consumes (Task 1): `CONTAINMENT_THRESHOLD`, `read_raw`, `handwriting_text`, `containment`, `lecture_date`.
- Consumes (existing): `core.indexer.index_card.load_shard(root, course)`, `save_shard(root, course, cards)`, `list_courses(root)`.
- Produces (used by Tasks 3-4):
  - `@dataclass(frozen=True) Link(subset_id: str, superset_id: str, score: float, forced: bool)`
  - `overrides_path(academic_hub_root: str) -> str` — `<root>/.index/links/overrides.json`
  - `load_overrides(academic_hub_root: str) -> dict` — `{"force": [...], "block": [...]}`, empty lists if file missing.
  - `link_subsets(academic_hub_root: str, course: str, dry_run: bool = False) -> list[Link]` — computes links, writes/clears `subset_of` and `subset_link_score` on the course shard (only when something changed and not `dry_run`), returns the links sorted by `subset_id`.
  - `main(argv: list[str] | None = None) -> None` — CLI.

- [ ] **Step 1: Write the failing tests**

Append to `tests/core/indexer/test_related.py`:

```python
import json
from unittest.mock import patch

import core.indexer.related as related
from core.indexer.index_card import load_shard, save_shard
from core.indexer.related import link_subsets, load_overrides, overrides_path

SLIDE_FILLER = "**[Slide]**\nbudget set indifference curve slide text about consumer choice\n\n"


def _note(hub, basename, *, slides, handwriting, file_id, course="microecon",
          category="lecture_notes", write_raw=True):
    out = os.path.join(hub, "academic_notes", course, category, "processed_outputs")
    os.makedirs(out, exist_ok=True)
    if write_raw:
        front = "---\nchunks: 1\n" + ("embedded_slides: true\n" if slides else "") + "---\n\n"
        body = (SLIDE_FILLER + "**[Handwritten]**\n" + handwriting + "\n\n" + SLIDE_FILLER) if slides else handwriting
        with open(os.path.join(out, f"{basename}.excalidraw.md"), "w", encoding="utf-8") as f:
            f.write(front + body)
    return {
        "file_id": file_id, "doc_type": "excalidraw_notes", "course": course,
        "path": f"academic_notes/{course}/{category}/processed_outputs/{basename}.excalidraw.rag.md",
        "embedding": [1.0, 0.0], "needs_indexing": False,
    }


def _pair(tmp_path, hw_sub=HW, hw_sup=HW):
    hub = str(tmp_path)
    sub = _note(hub, "Micro 2026-09-15 10.15.55", slides=False, handwriting=hw_sub, file_id="sub")
    sup = _note(hub, "Micro with slides 2026-09-15 10.15.55", slides=True, handwriting=hw_sup, file_id="sup")
    save_shard(hub, "microecon", [sub, sup])
    return hub


def test_links_a_true_pair_and_leaves_the_superset_untouched(tmp_path):
    hub = _pair(tmp_path)
    links = link_subsets(hub, "microecon")
    assert [(l.subset_id, l.superset_id) for l in links] == [("sub", "sup")]
    cards = {c["file_id"]: c for c in load_shard(hub, "microecon")}
    assert cards["sub"]["subset_of"] == "sup"
    assert cards["sub"]["subset_link_score"] == 1.0
    assert "subset_of" not in cards["sup"]


def test_second_run_is_idempotent_and_does_not_rewrite_the_shard(tmp_path):
    hub = _pair(tmp_path)
    link_subsets(hub, "microecon")
    with patch.object(related, "save_shard") as mock_save:
        links = link_subsets(hub, "microecon")
    assert len(links) == 1
    mock_save.assert_not_called()


def test_same_day_different_content_does_not_link(tmp_path):
    # lecture vs recitation on the same date: same-date candidates, different ink
    hub = _pair(tmp_path, hw_sub=HW_OTHER, hw_sup=HW)
    assert link_subsets(hub, "microecon") == []
    assert "subset_of" not in load_shard(hub, "microecon")[0]


def test_different_date_does_not_link(tmp_path):
    hub = str(tmp_path)
    sub = _note(hub, "Micro 2026-09-10 10.00.00", slides=False, handwriting=HW, file_id="sub")
    sup = _note(hub, "Micro with slides 2026-09-15 10.15.55", slides=True, handwriting=HW, file_id="sup")
    save_shard(hub, "microecon", [sub, sup])
    assert link_subsets(hub, "microecon") == []


def test_filename_without_a_date_does_not_link(tmp_path):
    hub = str(tmp_path)
    sub = _note(hub, "Micro notes", slides=False, handwriting=HW, file_id="sub")
    sup = _note(hub, "Micro with slides notes", slides=True, handwriting=HW, file_id="sup")
    save_shard(hub, "microecon", [sub, sup])
    assert link_subsets(hub, "microecon") == []


def test_different_folder_does_not_link(tmp_path):
    hub = str(tmp_path)
    sub = _note(hub, "Micro 2026-09-15", slides=False, handwriting=HW, file_id="sub", category="lecture_notes")
    sup = _note(hub, "Micro with slides 2026-09-15", slides=True, handwriting=HW, file_id="sup", category="recitation")
    save_shard(hub, "microecon", [sub, sup])
    assert link_subsets(hub, "microecon") == []


def test_two_plain_notes_or_two_slides_notes_never_link(tmp_path):
    hub = str(tmp_path)
    a = _note(hub, "A 2026-09-15 1", slides=False, handwriting=HW, file_id="a")
    b = _note(hub, "B 2026-09-15 2", slides=False, handwriting=HW, file_id="b")
    c = _note(hub, "C with slides 2026-09-15 3", slides=True, handwriting=HW, file_id="c")
    d = _note(hub, "D with slides 2026-09-15 4", slides=True, handwriting=HW, file_id="d")
    save_shard(hub, "microecon", [a, b])
    assert link_subsets(hub, "microecon") == []
    save_shard(hub, "microecon", [c, d])
    assert link_subsets(hub, "microecon") == []


def test_missing_raw_transcript_excludes_the_card_without_crashing(tmp_path):
    hub = str(tmp_path)
    sub = _note(hub, "Drawing 2026-09-15", slides=False, handwriting=HW, file_id="sub", write_raw=False)
    sup = _note(hub, "Micro with slides 2026-09-15", slides=True, handwriting=HW, file_id="sup")
    save_shard(hub, "microecon", [sub, sup])
    assert link_subsets(hub, "microecon") == []


def test_threshold_is_enforced(tmp_path):
    hub = _pair(tmp_path)
    with patch.object(related, "CONTAINMENT_THRESHOLD", 1.1):
        assert link_subsets(hub, "microecon") == []


def test_best_scoring_superset_wins(tmp_path):
    hub = str(tmp_path)
    sub = _note(hub, "Micro 2026-09-15", slides=False, handwriting=HW, file_id="sub")
    weak = _note(hub, "Weak with slides 2026-09-15", slides=True, handwriting=HW[: len(HW) // 2] + " " + HW_OTHER, file_id="weak")
    strong = _note(hub, "Strong with slides 2026-09-15", slides=True, handwriting=HW, file_id="strong")
    save_shard(hub, "microecon", [sub, weak, strong])
    links = link_subsets(hub, "microecon")
    assert [(l.subset_id, l.superset_id) for l in links] == [("sub", "strong")]


def test_block_override_prevents_a_link(tmp_path):
    hub = _pair(tmp_path)
    os.makedirs(os.path.dirname(overrides_path(hub)))
    with open(overrides_path(hub), "w", encoding="utf-8") as f:
        json.dump({"block": ["sub"]}, f)
    assert link_subsets(hub, "microecon") == []


def test_force_override_links_regardless_of_content(tmp_path):
    hub = _pair(tmp_path, hw_sub=HW_OTHER, hw_sup=HW)
    os.makedirs(os.path.dirname(overrides_path(hub)))
    with open(overrides_path(hub), "w", encoding="utf-8") as f:
        json.dump({"force": [{"subset": "sub", "superset": "sup"}]}, f)
    links = link_subsets(hub, "microecon")
    assert [(l.subset_id, l.superset_id, l.forced) for l in links] == [("sub", "sup", True)]
    assert load_shard(hub, "microecon")[0]["subset_of"] == "sup"


def test_force_to_a_missing_card_or_onto_itself_is_ignored(tmp_path):
    hub = _pair(tmp_path, hw_sub=HW_OTHER, hw_sup=HW)
    os.makedirs(os.path.dirname(overrides_path(hub)))
    with open(overrides_path(hub), "w", encoding="utf-8") as f:
        json.dump({"force": [{"subset": "sub", "superset": "nope"}, {"subset": "sup", "superset": "sup"}]}, f)
    assert link_subsets(hub, "microecon") == []


def test_forced_chain_is_dropped_so_links_stay_one_level(tmp_path):
    hub = _pair(tmp_path)
    cards = load_shard(hub, "microecon")
    cards.append(_note(hub, "Third 2026-09-15", slides=False, handwriting=HW, file_id="third"))
    save_shard(hub, "microecon", cards)
    os.makedirs(os.path.dirname(overrides_path(hub)))
    with open(overrides_path(hub), "w", encoding="utf-8") as f:
        json.dump({"force": [{"subset": "third", "superset": "sub"}]}, f)
    ids = {(l.subset_id, l.superset_id) for l in link_subsets(hub, "microecon")}
    assert ("third", "sub") not in ids  # sub is itself a subset


def test_stale_link_is_cleared_when_the_superset_disappears(tmp_path):
    hub = _pair(tmp_path)
    link_subsets(hub, "microecon")
    save_shard(hub, "microecon", [c for c in load_shard(hub, "microecon") if c["file_id"] != "sup"])
    assert link_subsets(hub, "microecon") == []
    sub = load_shard(hub, "microecon")[0]
    assert "subset_of" not in sub and "subset_link_score" not in sub


def test_dry_run_computes_but_writes_nothing(tmp_path):
    hub = _pair(tmp_path)
    with patch.object(related, "save_shard") as mock_save:
        links = link_subsets(hub, "microecon", dry_run=True)
    assert len(links) == 1
    mock_save.assert_not_called()
    assert "subset_of" not in load_shard(hub, "microecon")[0]


def test_load_overrides_defaults_when_file_missing(tmp_path):
    assert load_overrides(str(tmp_path)) == {"force": [], "block": []}


def test_cli_dry_run_prints_links(tmp_path, capsys):
    hub = _pair(tmp_path)
    related.main(["--root", hub, "--course", "microecon", "--dry-run"])
    out = capsys.readouterr().out
    assert "sub" in out and "sup" in out and "1.00" in out
    assert "subset_of" not in load_shard(hub, "microecon")[0]
```

- [ ] **Step 2: Run to verify failure**

Run: `$PY -m pytest tests/core/indexer/test_related.py -q`
Expected: import error for `link_subsets` / `load_overrides` / `overrides_path`.

- [ ] **Step 3: Implement**

Add imports at the top of `core/indexer/related.py`:

```python
import argparse
import json
from dataclasses import dataclass

from core.indexer.index_card import list_courses, load_shard, save_shard
```

Append to `core/indexer/related.py`:

```python
@dataclass(frozen=True)
class Link:
    subset_id: str
    superset_id: str
    score: float
    forced: bool = False


def overrides_path(academic_hub_root: str) -> str:
    # In a subdirectory, not a direct child of .index/: list_courses() and
    # _flag_or_prune_orphans() treat every top-level .index/*.json as a course
    # shard (same reason duplicate_check.py keeps its files in .index/duplicates/).
    return os.path.join(academic_hub_root, ".index", "links", "overrides.json")


def load_overrides(academic_hub_root: str) -> dict:
    path = overrides_path(academic_hub_root)
    if not os.path.exists(path):
        return {"force": [], "block": []}
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return {"force": data.get("force", []), "block": data.get("block", [])}


def _is_excalidraw(card: dict) -> bool:
    return card.get("doc_type") == "excalidraw_notes"


def _score(academic_hub_root: str, sub_card: dict, sup_card: dict) -> float | None:
    """Containment of sub's handwriting in sup's, or None if either raw
    transcript is missing or the slides-flag direction is wrong."""
    sub_raw = read_raw(academic_hub_root, sub_card)
    sup_raw = read_raw(academic_hub_root, sup_card)
    if sub_raw is None or sup_raw is None:
        return None
    sub_slides = sub_raw[0].get("embedded_slides", "").strip().lower() == "true"
    sup_slides = sup_raw[0].get("embedded_slides", "").strip().lower() == "true"
    if sub_slides or not sup_slides:
        return None
    return containment(handwriting_text(*sub_raw), handwriting_text(*sup_raw))


def _compute_links(academic_hub_root: str, cards: list[dict], overrides: dict) -> list[Link]:
    by_id = {c["file_id"]: c for c in cards}
    blocked = set(overrides["block"])
    forced = {f["subset"]: f["superset"] for f in overrides["force"] if "subset" in f and "superset" in f}
    excalidraw = [c for c in cards if _is_excalidraw(c)]

    links: dict[str, Link] = {}
    for sub in excalidraw:
        sub_id = sub["file_id"]
        if sub_id in blocked:
            continue
        if sub_id in forced:
            sup_id = forced[sub_id]
            if sup_id in by_id and sup_id != sub_id:
                score = _score(academic_hub_root, sub, by_id[sup_id])
                links[sub_id] = Link(sub_id, sup_id, round(score or 0.0, 4), forced=True)
            continue
        sub_date = lecture_date(sub["path"])
        if sub_date is None:
            continue
        best: Link | None = None
        for sup in excalidraw:
            if sup["file_id"] == sub_id or lecture_date(sup["path"]) != sub_date:
                continue
            if os.path.dirname(sup["path"]) != os.path.dirname(sub["path"]):
                continue
            score = _score(academic_hub_root, sub, sup)
            if score is None or score < CONTAINMENT_THRESHOLD:
                continue
            if best is None or score > best.score:
                best = Link(sub_id, sup["file_id"], round(score, 4))
        if best is not None:
            links[sub_id] = best

    # One level only: drop any link whose superset is itself a linked subset.
    return sorted((l for l in links.values() if l.superset_id not in links), key=lambda l: l.subset_id)


def link_subsets(academic_hub_root: str, course: str, dry_run: bool = False) -> list[Link]:
    """Computes and records subset links for one course shard. Idempotent:
    the shard is rewritten only when a card's link fields actually change.
    Also clears links that no longer qualify (superset gone, now blocked,
    text changed)."""
    cards = load_shard(academic_hub_root, course)
    links = _compute_links(academic_hub_root, cards, load_overrides(academic_hub_root))
    if dry_run:
        return links
    desired = {l.subset_id: l for l in links}
    changed = False
    for card in cards:
        link = desired.get(card["file_id"])
        if link is not None:
            if card.get("subset_of") != link.superset_id or card.get("subset_link_score") != link.score:
                card["subset_of"] = link.superset_id
                card["subset_link_score"] = link.score
                changed = True
        elif "subset_of" in card or "subset_link_score" in card:
            card.pop("subset_of", None)
            card.pop("subset_link_score", None)
            changed = True
    if changed:
        save_shard(academic_hub_root, course, cards)
    return links


_DEFAULT_ROOT = os.path.join(os.path.dirname(__file__), "..", "..", "..", "academic-hub")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Link handwriting-only Excalidraw notes to their with-slides supersets.")
    parser.add_argument("--root", default=_DEFAULT_ROOT, help="Corpus root (academic-hub).")
    parser.add_argument("--course", default=None, help="Only this course (default: all).")
    parser.add_argument("--dry-run", action="store_true", help="Print links without writing them.")
    args = parser.parse_args(argv)
    for course in [args.course] if args.course else list_courses(args.root):
        for link in link_subsets(args.root, course, dry_run=args.dry_run):
            tag = " (forced)" if link.forced else ""
            print(f"[{course}] {link.subset_id} -> {link.superset_id}  containment={link.score:.2f}{tag}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run to verify pass**

Run: `$PY -m pytest tests/core/indexer/test_related.py -q`
Expected: all pass. If `test_best_scoring_superset_wins` fails because the "weak" note still scores above the strong one, the fixture text is wrong, not the code: `weak` keeps only the first half of `HW` so its containment is ~0.5 versus 1.0.

- [ ] **Step 5: Commit**

```bash
git add ai-sandbox/academic-rag-model/core/indexer/related.py ai-sandbox/academic-rag-model/tests/core/indexer/test_related.py
git commit -m "feat(indexer): detect and record subset links with overrides and CLI"
```

---

### Task 3: Search integration (`include_subsets`)

**Files:**
- Modify: `core/indexer/index_search.py` (`search`, `search_passages`, `build_arg_parser`, `main`)
- Test: `tests/core/indexer/test_index_search.py`

**Interfaces:**
- Consumes: cards may carry `subset_of: <file_id>` (Task 2 writes it; tests set it directly).
- Produces: `search(..., include_subsets: bool = False)`, `search_passages(..., include_subsets: bool = False)`, CLI `query --include-subsets`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/core/indexer/test_index_search.py` (it already imports `search`, `search_passages`, `save_shard`, `recompute_course_entry`, `save_chunks`, `build_arg_parser`; `_card` and `_fake_query_client` are defined in the file):

```python
class TestSearchSubsets(unittest.TestCase):
    def _shard(self, tmp, sup_overrides=None, sub_overrides=None):
        sup = _card("sup", [1.0, 0.0], **(sup_overrides or {}))
        sub = _card("sub", [1.0, 0.0], subset_of="sup", **(sub_overrides or {}))
        save_shard(tmp, "math-camp", [sup, sub])
        recompute_course_entry(tmp, "math-camp")

    def test_subset_is_hidden_by_default_when_its_superset_is_a_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._shard(tmp)
            results = search([tmp], "q", client=_fake_query_client([1.0, 0.0]))
            self.assertEqual([r.file_id for r in results], ["sup"])

    def test_include_subsets_returns_both(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._shard(tmp)
            results = search([tmp], "q", client=_fake_query_client([1.0, 0.0]), include_subsets=True)
            self.assertEqual({r.file_id for r in results}, {"sup", "sub"})

    def test_subset_returned_when_superset_is_unindexed(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._shard(tmp, sup_overrides={"needs_indexing": True})
            results = search([tmp], "q", client=_fake_query_client([1.0, 0.0]))
            self.assertEqual([r.file_id for r in results], ["sub"])

    def test_subset_returned_when_superset_has_no_embedding(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._shard(tmp, sup_overrides={"embedding": None})
            results = search([tmp], "q", client=_fake_query_client([1.0, 0.0]))
            self.assertEqual([r.file_id for r in results], ["sub"])

    def test_subset_returned_when_superset_is_removed_by_the_callers_own_filter(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._shard(tmp, sup_overrides={"level": "advanced"}, sub_overrides={"level": "introductory"})
            results = search([tmp], "q", client=_fake_query_client([1.0, 0.0]), max_level="introductory")
            self.assertEqual([r.file_id for r in results], ["sub"])

    def test_dangling_subset_of_never_hides_the_card(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [_card("sub", [1.0, 0.0], subset_of="deleted")])
            recompute_course_entry(tmp, "math-camp")
            results = search([tmp], "q", client=_fake_query_client([1.0, 0.0]))
            self.assertEqual([r.file_id for r in results], ["sub"])

    def test_search_passages_inherits_the_collapse(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._shard(tmp)
            chunks = [
                {"chunk_id": f"{fid}-000", "file_id": fid, "chunk_index": 0, "tier": "page",
                 "heading_path": None, "problem_label": None, "page_range": [1, 1],
                 "text": f"text {fid}", "embedding": [1.0, 0.0], "embedding_model": "m", "content_hash": "h"}
                for fid in ("sup", "sub")
            ]
            save_chunks(tmp, "math-camp", chunks)
            default = search_passages([tmp], "q", client=_fake_query_client([1.0, 0.0]))
            self.assertEqual({p.file_id for p in default}, {"sup"})
            both = search_passages([tmp], "q", client=_fake_query_client([1.0, 0.0]), include_subsets=True)
            self.assertEqual({p.file_id for p in both}, {"sup", "sub"})

    def test_cli_exposes_include_subsets_flag(self):
        self.assertFalse(build_arg_parser().parse_args(["query", "q"]).include_subsets)
        self.assertTrue(build_arg_parser().parse_args(["query", "q", "--include-subsets"]).include_subsets)
```

- [ ] **Step 2: Run to verify failure**

Run: `$PY -m pytest tests/core/indexer/test_index_search.py -k Subsets -q`
Expected: failures (`unexpected keyword argument 'include_subsets'` / `AttributeError: include_subsets`).

- [ ] **Step 3: Implement**

In `core/indexer/index_search.py`:

1. `search()` signature: add `include_subsets: bool = False` as the last parameter:

```python
def search(
    roots: list[str], query: str, client, course: str | None = None, top_k: int = 5,
    doc_type: str | None = None, has_solutions: bool | None = None, max_level: str | None = None,
    include_subsets: bool = False,
) -> list[SearchResult]:
```

2. Inside `search()`, before `scored: list[SearchResult] = []` add `subset_parent: dict[tuple[str, str], str] = {}`. In the loop, right after `scored.append(SearchResult(...))` add:

```python
            if card.get("subset_of"):
                subset_parent[(root, card["file_id"])] = card["subset_of"]
```

3. Replace the tail (`scored.sort(...)` / `return scored[:top_k]`) with:

```python
    if not include_subsets and subset_parent:
        # Drop a subset only when its superset is itself a surviving candidate
        # (same root, passed every filter above): a stale, unindexed, or
        # filtered-out superset must never hide the subset's content.
        present = {(r.root, r.file_id) for r in scored}
        scored = [
            r for r in scored
            if (r.root, subset_parent.get((r.root, r.file_id), "")) not in present
        ]

    scored.sort(key=lambda r: r.score, reverse=True)
    return scored[:top_k]
```

(Cards without `subset_of` map to `""`, and `(root, "")` is never in `present`, so they are kept.)

4. `search_passages()` signature: add `include_subsets: bool = False` after `doc_type`, and change its file-level call to:

```python
    file_results = search(roots, query, client, course=course, top_k=file_top_k, doc_type=doc_type,
                          include_subsets=include_subsets)
```

5. `build_arg_parser()`: after the `--passages` argument of `query`, add:

```python
    query.add_argument("--include-subsets", action="store_true",
                        help="Also return handwriting-only notes that are a subset of a with-slides note.")
```

6. `main()`: pass `include_subsets=args.include_subsets` to both the `search_passages(...)` and `search(...)` calls in the `query` branch.

- [ ] **Step 4: Run to verify pass, then the whole file**

Run: `$PY -m pytest tests/core/indexer/test_index_search.py -q`
Expected: all pass (existing tests unchanged).

- [ ] **Step 5: Commit**

```bash
git add ai-sandbox/academic-rag-model/core/indexer/index_search.py ai-sandbox/academic-rag-model/tests/core/indexer/test_index_search.py
git commit -m "feat(indexer): search collapses subset notes into their superset by default"
```

---

### Task 4: Hooks (`write_outputs` and `rebuild`)

**Files:**
- Modify: `pipelines/transcribe_notes/transcribe_excalidraw.py` (`write_outputs`)
- Modify: `core/indexer/index_search.py` (`rebuild`, imports)
- Test: `tests/pipelines/transcribe_notes/test_transcribe_excalidraw.py`, `tests/core/indexer/test_index_search.py`

**Interfaces:**
- Consumes: `core.indexer.related.link_subsets(root, course) -> list[Link]`.
- Produces: none (side effects only).

- [ ] **Step 1: Write the failing tests**

Append to `tests/pipelines/transcribe_notes/test_transcribe_excalidraw.py`:

```python
def _write_outputs_kwargs(tmp_path):
    course_dir = tmp_path / "academic-hub" / "academic_notes" / "math_methods" / "lecture_notes"
    course_dir.mkdir(parents=True)
    md_path = course_dir / "Drawing 2026-09-08.excalidraw.md"
    png_path = course_dir / "Drawing 2026-09-08.excalidraw.png"
    md_path.write_text("---\n---\n")
    png_path.write_bytes(b"fake-png")
    return dict(
        excalidraw_md_path=str(md_path), image_path=str(png_path),
        raw_markdown="raw", expanded_markdown="expanded", transcription_model="m",
        expansion_meta={}, num_chunks=1, academic_hub_root=str(tmp_path / "academic-hub"), client=object(),
    )


def test_write_outputs_links_subsets_for_the_notes_course(tmp_path):
    kwargs = _write_outputs_kwargs(tmp_path)
    with patch("pipelines.transcribe_notes.transcribe_excalidraw.reconcile_and_write"), \
         patch("pipelines.transcribe_notes.transcribe_excalidraw.link_subsets") as mock_link:
        write_outputs(**kwargs)
    mock_link.assert_called_once_with(kwargs["academic_hub_root"], "math_methods")


def test_write_outputs_survives_a_linking_failure(tmp_path, capsys):
    kwargs = _write_outputs_kwargs(tmp_path)
    with patch("pipelines.transcribe_notes.transcribe_excalidraw.reconcile_and_write"), \
         patch("pipelines.transcribe_notes.transcribe_excalidraw.link_subsets", side_effect=RuntimeError("boom")):
        raw_path, rag_path = write_outputs(**kwargs)
    assert os.path.exists(rag_path)
    assert "WARNING" in capsys.readouterr().out
```

Append to `tests/core/indexer/test_index_search.py`:

```python
class TestRebuildLinksSubsets(unittest.TestCase):
    def test_rebuild_links_each_course_and_survives_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_excalidraw_note(tmp, "math-camp", "lecture_notes", "Drawing 2026-09-08")
            with patch("core.indexer.index_search.link_subsets") as mock_link:
                rebuild(tmp, client=_fake_client())
            mock_link.assert_any_call(tmp, "math-camp")

    def test_rebuild_with_course_filter_links_only_that_course(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_excalidraw_note(tmp, "math-camp", "lecture_notes", "Drawing 2026-09-08")
            with patch("core.indexer.index_search.link_subsets") as mock_link:
                rebuild(tmp, client=_fake_client(), course="math-camp")
            mock_link.assert_called_once_with(tmp, "math-camp")

    def test_a_linking_failure_does_not_fail_rebuild(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_excalidraw_note(tmp, "math-camp", "lecture_notes", "Drawing 2026-09-08")
            with patch("core.indexer.index_search.link_subsets", side_effect=RuntimeError("boom")):
                stats = rebuild(tmp, client=_fake_client())
            self.assertEqual(stats["generated"], 1)
```

- [ ] **Step 2: Run to verify failure**

Run: `$PY -m pytest tests/pipelines/transcribe_notes/test_transcribe_excalidraw.py -k links_subsets -q; $PY -m pytest tests/core/indexer/test_index_search.py -k LinksSubsets -q`
Expected: failures (`link_subsets` not an attribute of either module).

- [ ] **Step 3: Implement**

In `core/indexer/index_search.py`:
- Add to the `from core.indexer.index_card import (...)` list: `list_courses,` (alphabetical placement after `find_card_by_file_id,`).
- Add below that import block: `from core.indexer.related import link_subsets`
- Add this helper just above `def rebuild(`:

```python
def _link_subsets_safely(academic_hub_root: str, course_filter: str | None) -> None:
    for c in [course_filter] if course_filter else list_courses(academic_hub_root):
        try:
            link_subsets(academic_hub_root, c)
        except Exception as err:
            print(f"WARNING: subset linking failed for course {c} ({err}); "
                  f"rerun `python -m core.indexer.related` later.")
```

- In `rebuild()`, replace the final two lines `_flag_or_prune_orphans(...)` / `return stats` with:

```python
    _flag_or_prune_orphans(academic_hub_root, seen_file_ids, course, prune, stats)
    _link_subsets_safely(academic_hub_root, course)
    return stats
```

In `pipelines/transcribe_notes/transcribe_excalidraw.py`:
- Add `from core.indexer.related import link_subsets` next to the other `core.indexer` import.
- In `write_outputs`, inside the existing `try:` block, directly after the `reconcile_and_write(...)` call, add:

```python
        link_subsets(academic_hub_root, course)
```

(The existing `except Exception as err:` prints a `WARNING: source-indexer update failed ...` line, which satisfies the non-fatal requirement for both indexing and linking. `course` is already defined above the call.)

- [ ] **Step 4: Run to verify pass**

Run: `$PY -m pytest tests/pipelines/transcribe_notes tests/core/indexer -q`
Expected: all pass. The existing `test_write_outputs_creates_both_files_with_frontmatter` still passes because it patches `reconcile_and_write` and the real `link_subsets` finds an empty shard (`load_shard` returns `[]` for a missing file).

- [ ] **Step 5: Commit**

```bash
git add ai-sandbox/academic-rag-model/core/indexer/index_search.py ai-sandbox/academic-rag-model/pipelines/transcribe_notes/transcribe_excalidraw.py ai-sandbox/academic-rag-model/tests/core/indexer/test_index_search.py ai-sandbox/academic-rag-model/tests/pipelines/transcribe_notes/test_transcribe_excalidraw.py
git commit -m "feat(indexer): link subset notes from write_outputs and rebuild (non-fatal)"
```

---

### Task 5: Docs, spec correction, full regression, real-data check

**Files:**
- Modify: `core/indexer/README.md`
- Modify: `docs/superpowers/specs/indexer/2026-10-03-subset-note-linking-design.md`

**Interfaces:** none.

- [ ] **Step 1: Correct the spec's overrides path**

In the spec, replace every `.index/links_overrides.json` with `.index/links/overrides.json`, and replace the sentence beginning "Not a course shard, so ..." with: "Lives in a subdirectory, not as a direct child of `.index/`, because `list_courses()` and `_flag_or_prune_orphans()` treat every top-level `.index/*.json` as a course shard (see `duplicate_check.py`'s note on `.index/duplicates/`)." Also change the status line to "approved; implemented per the 2026-10-03 plan".

- [ ] **Step 2: Document in the indexer README**

In `core/indexer/README.md`, under "Key files", add after the `index_search.py` bullet:

```markdown
- `related.py` (2026-10-03) — links a handwriting-only Excalidraw note to its
  "with slides" superset: `subset_of`/`subset_link_score` on the subset's card.
  Candidates share course, folder, and a `YYYY-MM-DD` in the filename (superset's
  raw transcript has `embedded_slides: true`); confirmed by word-3-gram
  containment >= 0.3 of the subset's handwriting in the superset's `[Handwritten]`
  blocks (whole-card embeddings can't separate same-topic lectures). `search()`
  hides a subset whenever its superset is also a surviving candidate
  (`--include-subsets` / `include_subsets=True` to see both); an unindexed,
  missing, or filtered-out superset never hides the subset. Runs from
  `transcribe_excalidraw.write_outputs` and `rebuild`; manual:
  `python -m core.indexer.related [--course X] [--dry-run]`. Manual corrections:
  `.index/links/overrides.json` `{"force": [{"subset": id, "superset": id}], "block": [id]}`.
```

- [ ] **Step 3: Full regression**

Run: `$PY -m pytest tests -q -p no:cacheprovider`
Expected: all pass (1857 before this work plus the new tests); no `SyntaxWarning`s from new test files (`$PY -W error::SyntaxWarning -m pytest tests/core/indexer/test_related.py -q`).

- [ ] **Step 4: Real-data dry run (read-only)**

Run (load the worktree's code against the main checkout's vault):

```bash
PYTHONPATH="$(pwd -W)" $PY -m core.indexer.related --root "C:/Users/theaa/ai-sandbox-master/ai-sandbox/academic-hub" --course microecon --dry-run
```

Expected exactly 4 lines, each `-> <the matching "with slides" file_id>`: the 09-07 `Microeconomics lecture`, the 09-10 `Microeconomics lecture`, `Microeconomics 2026-09-15`, `Microeconomics 2026-09-17`, each with containment between 0.59 and 0.83 (the 09-07 pair was measured at 0.83); nothing for 09-22 and nothing for the orphaned `Drawing 2026-09-07`. If the set differs, stop and report instead of adjusting the threshold.

- [ ] **Step 5: Commit, then ask before applying to the real index**

```bash
git add ai-sandbox/academic-rag-model/core/indexer/README.md ai-sandbox/academic-rag-model/docs/superpowers/specs/indexer/2026-10-03-subset-note-linking-design.md
git commit -m "docs(indexer): document subset linking; correct overrides path in spec"
```

Applying the links writes to the main checkout's `.index/microecon.json`; ask the user, then run the same command without `--dry-run`, and verify with `python -m core.indexer.index_search --root <hub> query "preference relation utility representation" --course microecon` that only "with slides" notes appear, and that adding `--include-subsets` also shows the handwriting-only ones.
