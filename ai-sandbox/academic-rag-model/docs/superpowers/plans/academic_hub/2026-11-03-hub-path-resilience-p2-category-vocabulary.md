# Hub Path Resilience, Plan 2: Category Vocabulary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the position-based `course_part_category` with a vocabulary-driven parser, so an extra folder layer needs no code change, and ship the one-off command that learns the vocabulary from the live tree.

**Architecture:** One hub config file (`academic-hub/hub_config.json`) holds the folder-name vocabulary: each name is a `category`, a `group` or `ignore`. The parser finds the nearest ancestor folder that is a known category; folders between the course and that category are group layers. When a path has no known category, the parser returns exactly what the legacy code returned, so nothing changes until the owner confirms a name. A learner proposes new names by the approved rule, and a small CLI stores the owner's answers.

**Tech Stack:** Python 3.13, pytest, JSON config. No API calls anywhere in this plan.

**Spec:** `docs/superpowers/specs/academic_hub/2026-11-03-hub-path-resilience-design.md` (sections 3 and 6, decisions 3, and the vocabulary audit). Phase P2 of P0-P5; P1 is merged (PR 19).

## Global Constraints

- No network or model calls. Tests use `tmp_path` hubs (`tests/core/indexer/hub_fixture.py`: `make_hub`, `write_note`).
- Core changes run the full suite: `python -m tools.run_tests_chunked` (owner decision, 2026-11-03). Landing-check selection stays off for this plan.
- Stage explicit paths only. Repo is public: `hub_config.json` holds folder names only, no course content.
- Files in this repo are partly CRLF: use the Edit tool or raw strings, never shell heredocs, for edits containing backslashes.
- Behavior is preserved on today's tree. `folder_category` values on existing cards must not change unless the owner confirms a name (see Task 3 Step 5).
- Out of scope: the review queue and shared review page (P3), the daily scan and preflight triggers (P4), `ACADEMIC_HUB_ROOT` (P5), and the doc-type maps (`KNOWN_DOC_TYPES`, `LECTURE_NOTE_DOC_TYPES`, `_PROBLEM_TIER_FOLDER_CATEGORIES`, `_CATEGORY_FOLDERS`). Those key on the category string the parser returns, and the seed keeps those strings unchanged.

## Findings that shaped this plan (evidence from the live tree, 2026-11-03)

The live tree is messier than the spec's seed list assumed. Scanning folders that directly hold content files:

- Seed names appear as expected (`syllabus` 6 courses, `textbooks` 6, `lecture_notes` 5, `problem_sets` 3, `ta_notes` 2, `professor_notes` 2).
- The approved rule ("content in at least two courses") would also propose `processed_outputs`, `chapters`, `images`, `summaries`, `assets`, `previous` and `Solutions`. Most are sub-structure, not categories. The vocabulary therefore needs a third kind, `ignore`, and the learner must show its proposals for a human call.
- Many Title-Case or spaced names exist in one course each (`Problem Sets`, `Recitation Slides`, `Hand-Written Notes`, `Lecture Notes`), plus per-student folders and per-book folders. Matching is case-insensitive but not otherwise normalized (`Problem Sets` is not `problem_sets`). Aliases are the owner's call, one name at a time. No silent merging.

## Review Focus

- A path with no known category must behave exactly as today (legacy fallback), including `part_N` handling. Pinned in Task 1 and Task 3.
- A nested layer above a known category (`course/2025_fall/part_1/lecture_notes/x.md`) yields the right category and keeps every group layer. Task 3.
- A category name that also appears as a sub-folder (`lecture_notes/Problem Sets/x.md`): nearest known ancestor wins only for confirmed names; an unconfirmed `Problem Sets` is skipped. Task 3.
- A missing or malformed `hub_config.json` must degrade to legacy behavior with a clear message, never crash a pipeline. Task 2.
- `confirm` must never overwrite a different earlier answer silently, and each name is asked once. Task 7.

## File Structure

- Create `core/env/hub_vocabulary.py`: config model, loader, parser (`parse_hub_path`), nothing else.
- Modify `core/env/academic_hub_paths.py`: `course_part_category` becomes a wrapper; `TEXTBOOK_FOLDER_NAMES`, `is_textbook_folder`, and the `part_N` regexes read the vocabulary.
- Create `ai-sandbox/academic-hub/hub_config.json`: the seed.
- Create `core/env/hub_vocab_learn.py`: scan and proposal logic (pure, takes a hub root).
- Create `tools/hub_vocabulary.py`: CLI (`propose`, `impact`, `confirm`).
- Tests: `tests/core/env/test_course_part_category_legacy.py`, `test_hub_vocabulary.py`, `test_hub_vocab_learn.py`, `tests/tools/test_hub_vocabulary_cli.py`, `tests/core/indexer/test_nested_layer_scenarios.py`.

---

### Task 1: Pin the legacy behavior

**Files:**
- Create: `tests/core/env/test_course_part_category_legacy.py`

**Interfaces:**
- Consumes: `core.env.academic_hub_paths.course_part_category(path: str) -> tuple[str, str | None, str | None] | None`
- Produces: `LEGACY_CASES: list[tuple[str, tuple | None]]` in that test module, reused by Task 3.

- [ ] **Step 1: Write the table test.** One parametrized test over `LEGACY_CASES`, each case a path and the tuple today's function returns. Include: a path with no hub root (`None`); `academic_notes/econ/lecture_notes/a.md`; `.../econ/part_2/problem_sets/a.md`; a file directly under the course (`academic_notes/econ/a.md`); Windows separators; `academic_resources/econ/class_2024/Recitations/x.pdf` (legacy category `class_2024`); `.../math_methods/Problem Sets and Solutions/x.md`; `.../microecon/textbooks/processed_outputs/Book_2013/x.md` (legacy category `textbooks`); an absolute path containing both root names (last root wins).
- [ ] **Step 2: Run it against the current code.** Run: `python -m pytest tests/core/env/test_course_part_category_legacy.py -v`. Expected: all pass (this pins today's behavior; a failure means the expected tuple was mis-transcribed, fix the table not the code).
- [ ] **Step 3: Commit** `test(env): pin legacy course_part_category behavior`.

### Task 2: Vocabulary model, loader and seed config

**Files:**
- Create: `core/env/hub_vocabulary.py`, `ai-sandbox/academic-hub/hub_config.json`
- Test: `tests/core/env/test_hub_vocabulary.py`

**Interfaces:**
- Produces: `KINDS = ("category", "group", "ignore")`; `@dataclass(frozen=True) Vocabulary(names: Mapping[str, str], textbook_folders: tuple[str, ...], group_patterns: tuple[str, ...])` with `kind_of(name: str) -> str | None` (casefold match); `load_vocabulary(path: Path | None = None) -> Vocabulary`; `LEGACY_VOCABULARY` (no names, textbook folders `("textbooks", "textbooks-and-papers")`, group patterns `(r"^part_\d+$",)`); `default_config_path() -> Path` (the `academic-hub/hub_config.json` beside the repo, resolved from `__file__`; override with env `ACADEMIC_HUB_CONFIG`).
- Config shape: `{"version": 1, "textbook_folders": [...], "group_patterns": [...], "names": {"<folder name>": {"kind": "category|group|ignore", "source": "seed|owner"}}}`.

- [ ] **Step 1: Write failing tests.** (a) loading a tmp config returns the names and `kind_of("Lecture_Notes")` matches `lecture_notes`; (b) a missing file returns `LEGACY_VOCABULARY` and logs one warning; (c) invalid JSON, an unknown `kind`, or a bad regex returns `LEGACY_VOCABULARY` with a warning naming the file (never raises); (d) the shipped `hub_config.json` loads and contains every seed name below with the stated kind.
- [ ] **Step 2: Run to verify they fail** (module missing). Expected: ImportError.
- [ ] **Step 3: Implement** `core/env/hub_vocabulary.py` per the interfaces. Cache the loaded vocabulary per path and mtime so repeated parser calls stay cheap (the parser runs per file).
- [ ] **Step 4: Write the seed.** Categories: `lecture_notes`, `problem_sets`, `ta_notes`, `professor_notes`, `textbooks`, `textbooks-and-papers`, `syllabus`, `handwritten_notes`, `cheat_sheet`, `recitation_slides`, `study_plan`, `labs`, `articles`, `briefings`, `latex`, `lecture_slides`, `lecture_recordings`, `past_exams`. Group: `part_N` pattern, `class_YYYY`, `YYYY_class` as `group_patterns`; `ignore`: `processed_outputs`, `images`, `assets`. All `"source": "seed"`. `chapters`, `summaries`, `previous`, `Solutions` are deliberately absent so the learner raises them for a decision.
- [ ] **Step 5: Run tests; expect PASS. Commit** `feat(env): hub vocabulary model, loader and seed config`.

### Task 3: Vocabulary-driven parser

**Files:**
- Modify: `core/env/hub_vocabulary.py` (add parser), `core/env/academic_hub_paths.py:37-48`
- Test: `tests/core/env/test_hub_vocabulary.py`, `tests/core/env/test_course_part_category_legacy.py`

**Interfaces:**
- Produces: `@dataclass(frozen=True) HubPath(root: str, course: str, groups: tuple[str, ...], category: str | None, source: str)`, where `source` is `"vocabulary"` or `"legacy"`; `parse_hub_path(path: str, vocab: Vocabulary | None = None) -> HubPath | None`.
- `course_part_category(path)` returns `(course, groups[0] if groups else None, category)`, or `None` when `parse_hub_path` does.

- [ ] **Step 1: Write failing tests.** Every `LEGACY_CASES` row still holds through the new function (the table is imported). New cases with a vocabulary fixture: `econ/2025_fall/part_1/lecture_notes/a.md` gives groups `("2025_fall", "part_1")` and category `lecture_notes`; `econ/class_2024/problem_sets/a.md` gives category `problem_sets` and groups `("class_2024",)`; `lecture_notes/Problem Sets/a.md` with `Problem Sets` unconfirmed gives `lecture_notes`; the same with `Problem Sets` confirmed as category gives `problem_sets` with groups `("lecture_notes",)`; `textbooks/processed_outputs/Book/a.md` gives `textbooks`; `econ/Unknown/a.md` gives the legacy result and `source == "legacy"`; the file's own name is never treated as a folder; mixed case folder names match.
- [ ] **Step 2: Run to verify the new cases fail.** Expected: ImportError or attribute errors.
- [ ] **Step 3: Implement `parse_hub_path`.** Split on `/` after normalizing `\`; find the last hub root; take the folders after the course and before the file name; scan from the file upward for the first folder with kind `category`; groups are the folders between the course and that category. If none is found, return the legacy parse unchanged with `source="legacy"`. Move the legacy body into a private `_legacy_parse` in `hub_vocabulary.py` and make `course_part_category` the wrapper.
- [ ] **Step 4: Run Task 1 and Task 2 tests, then `tests/core`. Expected: all pass.**
- [ ] **Step 5: Decide whether a changed `folder_category` costs money.** Grep where `folder_category` is compared (`_is_stale` and `_reconcile_one` in `core/indexer/index_card.py`, `index_search.py`, `chunk_index.py`). Write down, in the ledger, whether a card whose `folder_category` changes is refreshed with an API call, relabeled locally, or ignored. If it can trigger paid work, add a `Ruling:` line and extend Task 7's `impact` output with a "would re-index" column. Do not guess: read the code and show the lines.
- [ ] **Step 6: Commit** `feat(env): vocabulary-driven hub path parser with legacy fallback`.

### Task 4: One source for textbook names and the part pattern

**Files:**
- Modify: `core/env/academic_hub_paths.py` (`TEXTBOOK_FOLDER_NAMES`, `is_textbook_folder`, `course_output_dir`), `audio_generator/discovery.py:30-35,89-103`, `core/course_materials/signals.py:13,89`
- Test: `tests/core/env/test_academic_hub_paths.py`, `tests/audio_generator/` (existing discovery tests)

**Interfaces:**
- Consumes: `load_vocabulary()`, `Vocabulary.textbook_folders`, `Vocabulary.group_patterns`.
- Produces: `TEXTBOOK_FOLDER_NAMES` stays importable (now derived from the loaded vocabulary); `is_group_name(name: str, vocab=None) -> bool` in `hub_vocabulary.py`.

- [ ] **Step 1: Write failing tests.** With a vocabulary whose textbook folders include a third name, `is_textbook_folder` and audio discovery both honor it; `is_group_name("part_3")`, `("class_2024")`, `("2025_class")` are true, `("lecture_notes")` is false; `course_output_dir` still enforces `part_N` exactly as before for the default config.
- [ ] **Step 2: Run to verify failures. Step 3: Implement.** Replace the two duplicated tuples and the three `part_N` regex sites with the vocabulary. Keep module-level names so no import elsewhere breaks.
- [ ] **Step 4: Run `tests/core/env`, `tests/audio_generator`, `tests/core/course_materials`. Expected: pass.** **Step 5: Commit** `refactor(env): textbook names and group pattern come from the hub vocabulary`.

### Task 5: Nested-layer scenarios across the callers

**Files:**
- Create: `tests/core/indexer/test_nested_layer_scenarios.py`
- Modify (only where a scenario fails): `audio_generator/discovery.py` (`_course_roots`), `pipelines/transcribe_notes/route_notes_transcribe.py` (the `placeholder.pdf` parses near lines 104, 133, 194, 337, 375), `core/course_materials/model.py:93-94` (the `floor` rule), `core/indexer/markdown_sources.py:112-144`

**Interfaces:**
- Consumes: `make_hub`, `write_note`, `parse_hub_path`.

- [ ] **Step 1: Write the scenarios, one test each, on a `tmp_path` hub.** (a) Nest `lecture_notes` one more layer (`academic_notes/econ/2025_fall/part_1/lecture_notes/a.md`): the markdown source row carries `folder_category == "lecture_notes"` and the correct course; (b) audio discovery finds the note; (c) the notes-transcription routing treats the matching resource PDF as eligible and routes its output to the same layer; (d) `CourseMaterials` locates the material and its floor accounts for every group layer; (e) move a course folder to a new parent name: file identity, not path, pairs notes and resources (this one may only pin today's behavior; mark `xfail(strict=True)` with the reason if it needs P3).
- [ ] **Step 2: Run them; record which fail.** Expected: some fail (the known `part_`-only sites). Each failure names a caller to fix.
- [ ] **Step 3: Fix each failing caller with the smallest change that reads the group layers from `parse_hub_path`** (stop assuming one `part_N` level). Do not refactor beyond that.
- [ ] **Step 4: Run the full scenario file, then `python -m tools.run_tests_chunked`. Expected: all chunks pass.** **Step 5: Commit** `feat(indexer): group layers of any depth above a known category`.

### Task 6: The learner

**Files:**
- Create: `core/env/hub_vocab_learn.py`
- Test: `tests/core/env/test_hub_vocab_learn.py`

**Interfaces:**
- Produces: `propose_vocabulary(hub_root: Path, vocab: Vocabulary) -> dict` returning `{"category_candidates": [{"name", "courses": [...]}], "group_candidates": [...], "ignore_candidates": [...], "unclassified": [{"name", "courses": [...]}]}`; only names not already in `vocab.names` appear.

- [ ] **Step 1: Write failing tests** on a tmp hub with three synthetic courses: a name directly holding content files in two courses is a category candidate; the same name in one course is `unclassified` unless seeded; `part_3`, `2024_class`, `class_2025` and any all-digit name are group candidates; a name already in the vocabulary is never proposed again; hidden folders (`.git`, `.index`) and the hub's own `.index` are skipped; content files are `.md`, `.pdf`, `.svg`, `.png`, `.jpg`, `.jpeg`; both `academic_notes/` and `academic_resources/` roots are scanned and a name seen in both counts per course once.
- [ ] **Step 2: Run, verify fail. Step 3: Implement** the walk with `os.walk` (prune hidden dirs) and the approved rule: candidate if content files directly inside in at least two courses, group if numbered, year-shaped or matching `group_patterns`, everything else single-course is `unclassified`. A name that matches an ignore-shaped hint list (`processed_outputs`, `images`, `assets`, `chapters` style infrastructure) is only suggested under `ignore_candidates` when already seeded; otherwise the learner stays within the approved rule and leaves the call to the owner.
- [ ] **Step 4: Run tests; expect PASS. Commit** `feat(env): hub vocabulary learner`.

### Task 7: CLI for propose, impact and confirm

**Files:**
- Create: `tools/hub_vocabulary.py`, tests in `tests/tools/test_hub_vocabulary_cli.py`; update `tools/README.md` (or the tools doc this repo uses)

**Interfaces:**
- Consumes: `propose_vocabulary`, `load_vocabulary`, `parse_hub_path`, legacy parser.
- Produces: `python -m tools.hub_vocabulary propose --hub-root PATH`, `impact --hub-root PATH`, `confirm NAME KIND [--alias-of NAME] --hub-root PATH`. `main(argv) -> int`.

- [ ] **Step 1: Write failing tests.** `propose` prints JSON and writes nothing; `impact` lists each path whose category or group differs between the legacy parse and the vocabulary parse, with counts per course, and reads the cards in `.index/` to report how many existing cards would see a different `folder_category`; `confirm problem_sets_x category` writes the name with `source: "owner"`; confirming the same name with the same kind is a no-op; confirming it with a different kind exits non-zero and names the earlier answer unless `--replace` is passed; an invalid kind exits non-zero; the config write is atomic (temp file then replace).
- [ ] **Step 2: Run, verify fail. Step 3: Implement.** No API calls, no writes outside `hub_config.json`. **Step 4: Run tests; PASS.**
- [ ] **Step 5: Document** the three commands in the tools README, including: run `propose`, review, `confirm` each name, then `impact` before relying on a changed category. **Step 6: Commit** `feat(tools): hub_vocabulary propose, impact and confirm`.

### Task 8: Whole-plan verification (executor)

- [ ] **Step 1:** `python -m tools.run_tests_chunked`. Expected: every chunk passes.
- [ ] **Step 2:** Against the live hub, read-only: `python -m tools.hub_vocabulary propose --hub-root C:\Users\theaa\ai-sandbox-master\ai-sandbox\academic-hub` and `impact`. The worktree copy has no `academic_notes/`, so the path must be the main checkout. Report the candidate lists and the impact counts in the final message. Do not run `confirm`; the owner decides each name.

## Owner steps after merge (not part of the plan's tasks)

1. Review the `propose` output and `confirm` each name (categories, groups, ignores, aliases).
2. Run `impact` and read the card counts before the next index run.
3. P4 later folds the same learner into the daily scan, raising review items only for new names.
