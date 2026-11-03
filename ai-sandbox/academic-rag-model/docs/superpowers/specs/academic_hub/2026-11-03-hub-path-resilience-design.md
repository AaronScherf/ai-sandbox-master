# Hub path resilience: design

**Status:** draft for owner review. No code changed. Owner: Claude (design); Codex implements per `docs/AGENT_ROUTING.md`.
**Related:** `docs/MONOREPO_SPLIT_EVALUATION.md` (track 2), `specs/indexer/2026-10-31-part-path-discovery-design.md` (the fix this generalizes), `specs/tools/2026-11-03-hub-binary-guard-design.md`.
**Scope:** `core/env/academic_hub_paths.py`, `core/indexer/*`, `pipelines/transcribe_notes/*`, `tools/corpus_health/*`, plus a hub-root setting.

## Intent

A hub user should be able to nest folders, move a course, or rename a file and have the hub keep its links without a refactor. Nesting notes one layer deeper (the `part_N` change) cost days of code and test work. For another user that would be unacceptable.

**Owner's words (2026-11-03):** the hub should link files by filename and card, not by exact path and folder structure; relinking should be easy to infer, including from git commits; ask when ambiguous, never guess silently; use the existing review queue; check in both the daily scan and at pipeline start.

## Goals, non-goals, anti-goals

**Goals**
1. Moves, renames and added folder layers repair automatically when the match is unambiguous, and go to the review queue when it is not.
2. A move or rename never triggers paid regeneration or re-embedding.
3. New folder layers need configuration at most, not code.
4. The daily scan and each pipeline run both detect broken links.

**Non-goals**
- Not a general file-sync tool; it only repairs the hub's own links, cards and mirror pairing.
- No history rewriting, no deleting content, no change to `academic_resources` being gitignored.

**Anti-goals (failure even if it "works")**
- A silent wrong match.
- A paid bulk rebuild caused by a move.
- Another layout special case in code.

## Why it breaks today (evidence from code and the part-path spec)

| Cause | Where | Effect of an extra folder layer or move |
|---|---|---|
| Category is a fixed position; only `^part_\d+$` is skipped | `course_part_category` in `academic_hub_paths.py` | Any other layer is read as the category; the mirror check fails |
| Notes pair to sources by mirrored path | `eligible_resource_note_pdf`, `to_notes_root` / `to_resources_root` | Pairing and eligibility depend on identical folder names on both sides |
| Markdown staleness hash covers location fields | `compute_content_hash`; frontmatter holds `source_pdf`, `source_excalidraw`, `source_image`, `duplicate_of_path` | A pure move rewrites frontmatter, so 221 of 239 cards looked stale (about 3,900 API calls) |
| Clone IDs include the source path | `compute_id_from_parts([duplicate_of_file_id, rel_pdf_path])` | A move orphans clone cards |
| Paths persisted in sidecars | textbook `_metadata.json` `rag_md_path` | A rebuild writes the stale path back |
| Discovery gates on directory structure | `index_search._notes_pdf_paths` and siblings | Nested sources are missed or textbooks swept in |

PDF cards already survive moves: `file_id` is a hash of the file's bytes (`compute_file_id`). The gaps are Markdown and derived content, the location fields, and structure assumptions.

## Design

### 1. Identity: three tiers, location is only a hint

| Content | Identity | Notes |
|---|---|---|
| PDFs and other binaries | byte hash (`file_id`, exists) | Unchanged |
| Authored Markdown / Excalidraw scenes | `hub_id` written once into frontmatter (a short random ID) | Survives edits, moves, renames. *My proposal.* Obsidian preserves frontmatter on move |
| Derived outputs (cards, `.rag.md`, transcriptions) | parent `hub_id` / `file_id` plus a role name | Never path-derived |

Paths in frontmatter and cards become **hints** next to the ID (`source_id` is authoritative, `source_pdf` is a cached location). A hint that no longer resolves is repaired from the ID, not treated as an error.

### 2. Hash only what is content

Define a canonical content hash for Markdown: body plus frontmatter with all location fields removed. A move, rename or relink then leaves the hash, and the card, valid. One-time migration: recompute hashes locally for existing cards and write them back, with no API calls (the same idea as the existing `relocate_index_paths` tool).

Clone cards get a stable stored ID (generated once), not one derived from the path.

### 3. Layout without positional assumptions

Replace position parsing with a **category vocabulary**: the nearest ancestor folder whose name is a known category (`lecture_notes`, `problem_sets`, `ta_notes`, `professor_notes`, `textbooks`, and so on) is the category. Folders between the course and the category are **group layers** (`part_1`, `week_3`, anything). The vocabulary lives in one hub config file, not in code. An unrecognized folder name is not guessed: the scan raises a "folder with no known category" finding.

Notes/resources pairing uses file identity first, and the group-plus-category path only as a tiebreaker or hint.

### 4. Reconcile engine (one function, two callers)

`reconcile(hub_root)` builds a tree snapshot, compares it with the cards, and classifies every difference. Matching order, strongest first:

1. **Exact byte hash** (binaries) or `hub_id` (authored): a single match is unambiguous.
2. **Git rename detection** (`git diff -M`, `git log --follow` over the hub repos) for tracked files.
3. **Filename (stem) plus course** and body similarity, as a ranked suggestion only.

Actions:
- *Unambiguous* (a single exact match): update hints and write a log line. *My guess:* safe to apply automatically since it changes only location metadata and is reversible. **Owner to confirm.**
- *Ambiguous or weak* (several candidates, or similarity only): create a review item with the candidates ranked. Nothing is linked until the owner answers. Consumers refuse to use the unresolved link.
- *No match*: report the card as orphaned. Never relink, never delete.

Review items follow the repo convention for human decisions (`academic-rag-model/CLAUDE.md`, Scope): an interactive Artifact review page (checkbox / Link / Dismiss, decisions in its `db` collection) applied through the pipeline's own resolve/reject functions, the pattern in `core/indexer/offering_links.py`. The corpus-health ledger records the finding; the raw ledger files are for code, not for review. Accepted relinks are applied locally with no API calls.

### 5. Two triggers

- **Daily scan** (`tools/corpus_health scan`): full reconcile, adds findings, never mutates corpus files (as today).
- **Pipeline preflight:** each pipeline compares a cheap tree fingerprint (names, sizes, mtimes, recorded in `.index/`) against the last reconcile. Unchanged: continue. Changed: run reconcile; if any unresolved item touches what the pipeline needs, stop with a pointer to the review queue. This keeps the common case nearly free.

### 6. Configuration and root

One hub config (name and format are the builder's call) holds the hub root (the `ACADEMIC_HUB_ROOT` setting, default `../academic-hub`), the category vocabulary, textbook folder names, and the group-layer pattern (default: any folder). The existing `TEXTBOOK_FOLDER_NAMES` and the `part_N` regex move there.

## What is left to the builder

Config format; exact tree-fingerprint fields; similarity metric; how to store `hub_id` for formats without frontmatter; migration ordering for existing cards; Windows path-case handling.

## Phases

| Phase | Deliverable | Value on its own |
|---|---|---|
| P0 | Characterization tests on a fixture hub, no API: nest a layer, rename a file, rename a folder, move a course | Shows today's failures; becomes the regression suite |
| P1 | Canonical content hash, stable clone IDs, no persisted path sidecars, local migration | Removes the paid-rebuild risk |
| P2 | Category vocabulary and hub config replace `course_part_category` | Extra layers need no code |
| P3 | `reconcile` engine and review integration | Moves and renames self-repair or ask |
| P4 | Daily scan and pipeline preflight triggers | Detection in both places |
| P5 | `ACADEMIC_HUB_ROOT` and temp-scaffold fixtures | Needed for a public template and independent tests |

Each phase lands separately behind the landing check; P1 goes first.

## Acceptance (scenario matrix, fixture hub)

Every scenario runs with the model client mocked to fail on any call:

| Scenario | Expected |
|---|---|
| Nest notes one layer (`group/`) | zero API calls; links repaired or listed in review; no silent wrong match |
| Rename a file (same content) | auto-repair |
| Rename and edit | review item with the ranked candidate |
| Rename a course folder | one review item, or auto-repair of every file by exact match |
| Two identical files after a move | review item; neither linked |
| Delete a file | orphaned card reported; nothing deleted |
| Pipeline run with an unresolved item it needs | refuses with a pointer to the queue |

## Open questions

1. Is automatic repair of a single exact-match move acceptable (logged, reversible), or should every repair go through review?
2. Is writing a `hub_id` into the frontmatter of authored notes acceptable? It edits files in `academic_notes/` (a separate repo), so you would commit that change there.
3. Where does the category vocabulary live, and who edits it: you by hand, or learned from the existing tree on first run?
4. Should the preflight fingerprint also run in landing checks, or only in pipelines?
5. Should the `offering_links` / `document_pairing` queue and the corpus-health ledger become one queue, or stay two with a link between them? The Artifact review page would be shared either way.
