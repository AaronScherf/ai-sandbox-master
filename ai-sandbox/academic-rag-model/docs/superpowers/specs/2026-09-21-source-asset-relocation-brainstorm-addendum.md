# Source Asset Relocation: Brainstorm Addendum (concurrent session)

Written by a second, concurrent Claude Code session on this same machine
that independently started brainstorming this same restructuring (from
`docs/status/2026-09-21-obsidian-git-sync-status.md`'s "Restructuring
problem scope" section) before discovering this worktree's spec + plan
already existed, in progress. Rather than duplicate the work, that session
brainstormed the gaps the existing spec/plan don't cover, got the user's
decisions on each, and is handing them off here as an addendum. **Nothing
in this file has been implemented.** The other session should read this,
fold the decisions below into the spec/plan (or a new task), and continue
execution from wherever Task 3 currently stands.

## Confirms the existing design (no change needed)

These were asked independently, without reading the existing spec first,
and the user's answers match what's already designed -- recorded here as
confirmation, not new scope:

- **Split criterion:** strictly by file type (all raw source formats --
  PDF, SVG/PNG exports, docx, pptx, textbooks, scanned images -- move to
  `academic_resources/`; only `.md` and `.excalidraw.md` stay in
  `academic_notes/`), not a size threshold. Matches the spec's mirrored-path
  convention already.
- **Source linking:** an explicit metadata field on the index card (not
  path-convention-only inference). Matches the existing `source_asset_path`
  field exactly.
- **History handling:** best-effort only, don't invest in cross-repo
  git-history-preserving surgery for the move. No design impact.

## New scope: NOT covered by the existing spec/plan

### 1. Folder vocabulary unification -- underscores everywhere

Both the course-directory level and the category-folder level currently
mix hyphens and underscores between the two trees. User's decision, both
times: **underscores everywhere** (matches the majority convention already
in `academic_notes/`: `ta_notes`, `problem_sets`, `study_plan`,
`cheat_sheet`, `handwritten_notes`, `professor_notes`).

Renames needed (survey was math-camp-focused; **re-survey all courses**
before executing -- the original brainstorm only fully inventoried
math-camp in depth):

- `academic_resources/math-methods/` -> `academic_resources/math_methods/`
  (currently spelled differently across the two trees for what looks like
  the same course as `academic_notes/math_methods/`).
- `academic_resources/<course>/lecture-slides/` ->
  `academic_resources/<course>/lecture_slides/` (wherever present).
- `academic_resources/<course>/lecture-recordings/` ->
  `academic_resources/<course>/lecture_recordings/` (wherever present).
- `academic_notes/math-camp/lecture-notes/` ->
  `academic_notes/math-camp/lecture_notes/`. **Flagged 2026-09-21, caught
  before execution:** this is not a naming inconsistency --
  `academic_notes/<course>/lecture-notes/` (hyphenated) was a hardcoded,
  load-bearing directory name for a completely different subsystem, the
  video-lecture-notes pipeline (`video_notes/note_indexing.py`,
  `indexer/index_search.py`'s `_video_lecture_note_paths`) -- unrelated to
  the Excalidraw pipeline's `lecture_notes` (underscored) category that
  every other course uses. Renaming the folder alone would have broken
  `rebuild()`'s discovery of math-camp's video lecture notes -- the exact
  same class of silent-orphaning bug Task 3 of the main plan just fixed
  for Excalidraw notes, reintroduced for a different content type.
  **Executed anyway on 2026-09-22, per the user:** both hardcoded
  references updated to match (see that date's section below) -- the
  folder is renamed for real now, with the two subsystems' code kept in
  sync rather than left inconsistent. The original brainstorm's "one
  outlier" framing undersold the risk (it's not just a naming quirk, it's
  a real cross-subsystem dependency), but the rename itself was fine once
  the dependent code came along with it.

**Sequencing recommendation:** do this rename pass *before* running the
file migration (Task 8/9), so `common/academic_hub_paths.py`'s mirrored-path
convention never has to reconcile mismatched category names between the
two trees mid-migration. If the other session is already past this point,
treat it as a follow-up rename pass instead and confirm
`to_resources_root`/`to_notes_root` don't assume a specific category-name
set (they shouldn't -- they only swap the root segment).

### 2. Duplicate PDF resolution (math-camp, found and verified)

`academic_notes/math-camp/ta_notes/2025/*.pdf` (6 files) are
**byte-identical** (hash-verified) to
`academic_resources/math-camp/lecture-slides/*.pdf` -- the same content
already exists in both trees under different category names, presumably
from an earlier partial/manual migration attempt.

User's decision: these are TA lecture notes, not professor lecture slides,
so **`ta_notes` is the correct category** (matches every other course's
vocabulary). After the vocabulary rename above, keep one canonical copy at
`academic_resources/math-camp/ta_notes/` and **delete** the
`academic_resources/math-camp/lecture-slides/` copies as redundant
duplicates (don't re-move the `academic_notes/ta_notes/2025/` originals --
migrate them normally through the existing Task 8/9 migration script once
the vocabulary rename lands).

### 3. docx/pptx scope -- confirmed in scope

`study_plan/` folders contain a few raw `.docx` files (e.g. `Columbia Math
Camp Prep Schedule (15 week).docx`) that **no automated pipeline currently
touches** -- confirmed via `grep -rl "\.docx\|\.pptx" academic-rag-model
--include="*.py"`, only `essays/convert_essays.py` and
`indexer/chunk_index.py` reference docx/pptx at all, both unrelated to this
project's notes pipeline.

User's decision: **move them too**, under the strict-by-type policy,
even though nothing reads them from their new location automatically. This
is a purely mechanical file move -- confirmed no code in `notes/` or
`indexer/` hardcodes a path to any `.docx`/`.pptx` file, so it needs no
code changes, just inclusion in whatever migration script/pass handles the
physical moves (the existing `find_migration_candidates()` in
`notes/migrate_sources_to_resources.py` currently only matches `.pdf` and
`.excalidraw.{png,svg}` -- extend its filter to include `.docx`/`.pptx` if
that script is still the intended vehicle for these, or handle them in a
separate pass since they need no reindexing).

## Still open -- not yet decided by the user, needs its own brainstorming turn

These were identified during research but the session ended (handed off to
this addendum) before they could be brought to the user for a decision:

- **README updates**: `academic-hub/README.md` (confirmed exists) needs to
  describe the new split, the unified vocabulary, and the docx/pptx
  handling policy above. Worth checking whether `academic_notes/` or
  `academic_resources/` should each get their own README too (neither
  currently has one at the subproject root, only `academic-hub/README.md`
  at the parent level).
- **`.gitignore` / Direct Git Sync updates**: the outer
  `ai-sandbox-master/.gitignore`'s existing `academic_resources/`
  selective-heavy-subpath-exclusion pattern (~lines 1-50) will need new/
  renamed entries once categories are renamed and new content (docx/pptx,
  the migrated math-camp files) lands there. Separately, the tablet's and
  laptop's **Direct Git Sync per-device "User defined ignore rules"**
  settings (local `data.json`, not git-tracked -- see
  `docs/status/2026-09-21-obsidian-git-sync-status.md`) need the equivalent
  manual update on both devices; this can only be documented as an
  instruction, not automated.
- **Triplicate `.excalidraw.md` files**: found during research -- some
  `.excalidraw.md` scene files currently exist in *three* places: the
  category directory (canonical), a copy inside `processed_outputs/`
  (looks like leftover/accidental duplication, not an intentional second
  copy), and the separate `.excalidraw.rag.md` transcription output (this
  third one is correct and expected, not a duplicate). The `processed_outputs/`
  copy of the raw `.excalidraw.md` itself looks like cleanup debt,
  independent of this migration -- needs its own small investigation
  (which courses/files are affected, why the copy exists) before deciding
  whether to delete it.

## 2026-09-21 follow-up: two of the three "still open" items resolved

The main session investigated the two more concrete "still open" items
directly (per the user's explicit go-ahead); README updates remain
deferred until after the real migration, per the user's own preference.

### Triplicate `.excalidraw.md` -- false alarm, not cleanup debt

Investigated all 8 real instances in the corpus (4 econometrics, 4
microecon). The `processed_outputs/`-nested copy is **not** a duplicate of
the canonical scene file -- it's `transcribe_excalidraw.py`'s own
intentional "raw transcription" output, by design since the original
2026-09-09 plan (`<name>.md` raw + `<name>.rag.md` expanded), which just
happens to reuse the same `.excalidraw.md` filename suffix as its source.
Confirmed directly, not assumed: the canonical source
(`econometrics/lecture_notes/Econometrics 2026-09-09 10.11.39.excalidraw.md`)
is 1.78MB of compressed-JSON Excalidraw scene data; the
`processed_outputs/` file of the identical name is 6.3KB of markdown with
its own `source_excalidraw`/`source_image`/`routing`/`chunks`/`model`
frontmatter and the actual chunked transcription text -- a byte diff of
the first 200 bytes of each confirms they're unrelated content, not a
stale copy of one another. **No cleanup needed.** This is exactly the
same filename collision `route_notes_transcribe.py`'s and
`migrate_sources_to_resources.py`'s own discovery logic already guards
against by pruning `processed_outputs/` from their walks (Tasks 6 and 9) --
the collision is real, but the fix was already built before this
investigation, for an unrelated reason (avoiding rediscovering the
pipeline's own output as a new source).

### `.gitignore` / Direct Git Sync -- concrete instructions, not yet applied

**Laptop-side Direct Git Sync:** checked the real config
(`academic_notes/.obsidian/plugins/direct-git-sync/data.json`,
`ignoredPaths`): `*.pdf`, `*.docx`, `*.doc`, `*.pptx`, `*.excalidraw.svg`
are already wildcard-excluded from the vault repo. **No laptop-side change
needed for this migration** -- every file type this plan moves out of
`academic_notes/` is already excluded from that repo by extension,
regardless of path. **Action for the user:** verify the tablet's
`direct-git-sync/data.json` has the same `ignoredPaths` list (can't be
checked from this machine) -- if it doesn't, add the same five patterns
there.

**Outer `ai-sandbox-master/.gitignore`:** two real, concrete changes
needed, both only after Task 8's vocabulary rename actually lands (not
before, since these patterns must match the renamed directories):

1. `ai-sandbox/academic-hub/**/lecture-slides/` and
   `ai-sandbox/academic-hub/**/lecture-recordings/` (lines currently in
   the file, hyphenated only) need matching underscored patterns added --
   `ai-sandbox/academic-hub/**/lecture_slides/` and
   `.../lecture_recordings/` -- following this file's own existing
   both-spellings precedent for `textbooks-and-papers/`/`textbooks/`.
   Without this, the renamed directories' PDFs (currently protected as
   "plausibly institution/professor-owned," per this `.gitignore`'s own
   comment) would silently become trackable and could get committed to a
   repo this `.gitignore` itself notes is public on GitHub.
2. **New consideration, not previously flagged:** `academic_notes/` is
   currently wholesale-excluded from the outer repo (`ai-sandbox/
   academic-hub/academic_notes/`, a full directory ignore -- it's a
   separate nested repo). Its `study_plan/`'s `.docx`/`.pptx` files are
   therefore currently invisible to the outer repo entirely.
   `academic_resources/` is **not** wholesale-excluded -- only specific
   subpaths are. Once `.docx`/`.pptx` files physically move there (this
   plan's Task 9, per the "in scope" decision above), they become
   trackable-by-default in a public repo unless the user decides they
   should be excluded too, same as the textbook PDFs. **This needs an
   explicit decision, not an assumption:** should moved `.docx`/`.pptx`
   files be gitignored in their new home, or is that content fine to
   track publicly?

   **Decided (2026-09-21): yes, gitignore them** -- same reasoning as the
   textbook-PDF protection already in place. New pattern needed alongside
   the `lecture_slides/`/`lecture_recordings/` additions above:
   `ai-sandbox/academic-hub/**/*.docx` and `ai-sandbox/academic-hub/**/*.pptx`
   (unscoped by category, matching the pattern this `.gitignore` already
   uses for `*_pages_cache.json` -- these extensions never carry the
   user's own primary-authored analysis the way a `.md` transcription
   does, so a blanket match is safe here without the deny-list-not-allow-list
   care `textbooks-and-papers/`'s PDF/MD patterns needed).

## 2026-09-21: Task 8 executed for real against the live corpus

Survey (Task 8 Step 1) found a fuller picture than the original
math-camp-focused brainstorm: `math-methods`/`math_methods` was the only
course-level mismatch that actually breaks the mirrored-path convention;
`lecture-slides`/`lecture-recordings` have zero academic_notes/
counterpart either way (already correctly excluded from PDF-notes
discovery, hyphenated or not) so their rename is cosmetic, not
functional; and `math-camp/lecture-notes/` turned out to be load-bearing
for an unrelated subsystem (see the correction inline above), not
renamed. Also found: `academic_resources/intro_spanish/` has real content
(`lecture-slides/`/`lecture-recordings/`) with no `academic_notes/`
counterpart at all -- confirmed with the user as a genuinely separate
course from `interm_spanish`, not a duplicate.

**Executed for real** (user-confirmed rename list, all verified
git-untracked before touching -- `git ls-files` returned zero results for
every renamed path, so these were plain filesystem renames, not `git mv`):
- `academic_resources/math-methods/` -> `math_methods/`
- `academic_resources/<course>/lecture-slides/` -> `lecture_slides/` for
  econometrics, env-science, interm_spanish, intro_spanish, math-camp
- `academic_resources/<course>/lecture-recordings/` -> `lecture_recordings/`
  for the same 5 courses
- Created `academic_notes/intro_spanish/` (empty, matching
  `interm_spanish`'s own current empty state)

**Outer `.gitignore` updated and committed** (`ai-sandbox-master`
commit `cd2769b`): added `lecture_slides/`/`lecture_recordings/` patterns
(kept the old hyphenated ones too, same both-spellings precedent as
`textbooks-and-papers/`/`textbooks/`), and `**/*.docx`/`**/*.pptx` per the
decided docx/pptx-gitignored-too follow-up decision. `math-camp/
lecture_slides/` had real content (the same byte-identical duplicate PDFs
Decision 2 above already found) that briefly surfaced as untracked before
this gitignore update landed -- confirmed re-protected afterward, `git
status` clean.

**Re-verified against the real corpus post-rename** (same methodology as
the main plan's Task 7): `route_notes_transcribe` discovery byte-identical
to pre-rename (`PDF: 71 to process, 17 already done`); isolated-copy
`rebuild()` re-run still `orphaned: 0`, all 8 real econometrics cards
unchanged. Nothing broke.

**Not yet done:** the math-camp duplicate-PDF deletion (Decision 2) --
deliberately held for Task 10's own Step 0, a separate confirmation from
this rename pass. The real file migration (Task 9's script exists and is
tested; Task 10 is its own go/no-go, not yet reached).

## 2026-09-22: math-camp/lecture-notes/ renamed after all, with the video_notes pipeline updated to match

The user reconsidered the correction above: rather than leaving
`lecture-notes/` as the one hyphenated outlier, rename it too and update
`video_notes/note_indexing.py` + `indexer/index_search.py`'s
`_video_lecture_note_paths` to match, since both hardcode the folder
name. Executed:

- Checked for collision risk first (no course has both video-notes
  `.md`+`.meta.json` and Excalidraw `.excalidraw.md`/`.svg`/`.png` content
  in the same folder) -- confirmed safe to share the folder name.
- Updated both hardcoded references (directory path + `folder_category`
  metadata value in each) plus every dependent test; left the spec
  filename (`2026-09-06-video-lecture-notes-design.md`) and the
  "video-lecture-notes pipeline" English phrase untouched, since those
  name the spec doc and the subproject, not the folder.
- Real-renamed all 10 files via `git mv` in the vault repo (proper
  rename tracking).

**A real regression was caught by a broad, all-courses (not just
math-camp) verification pass, fixed before it shipped:** once
`lecture_notes/` was shared vocabulary, `_video_lecture_note_paths`
started scanning *every* course's `lecture_notes/` folder -- including
the Excalidraw ones -- and printed a "no sidecar" warning for every single
`.excalidraw.md` file in every course, on every `rebuild()`. Not a data-
correctness bug (no card was ever wrongly generated; `orphaned: 0`,
`generated: 0` throughout), but real noise that a course-scoped
verification alone wouldn't have caught. Fixed: `.excalidraw.md` is now
excluded up front as never being a video-lecture-note candidate, rather
than treated as one missing its sidecar. Re-verified broad, all-courses,
after the fix: silent, `orphaned: 0`.

**Separately, a second real gap found and fixed while investigating why 4
`ta_notes` cards had also gone stale:** `_notes_pdf_paths()` (the PDF-notes
walker) was hardcoded to exactly `course/category/*.pdf`, two levels, no
recursion -- unlike `route_notes_transcribe.py`'s and
`migrate_sources_to_resources.py`'s own walkers, which both already
recurse via `os.walk`. The user had reorganized `math-camp/ta_notes/`
into year subfolders (`2025/`, `2026/`) as part of their own normal vault
use (confirmed via the Direct Git Sync auto-commit history, not a bug or
another session), which made those PDFs invisible to `rebuild()` entirely,
regardless of where their `processed_outputs/` lived. Fixed: made the
walker recursive, with `folder_category` now the PDF's own immediate
parent directory basename (matches `transcribe_notes.py`'s
`derive_folder_category()` exactly, unchanged for the flat case). Then
moved the 4 affected files' `processed_outputs/` (`.md` +
`_pages_cache.json`, plus `LN_Probability`'s `audio_generator` narrated.md
family -- 19 files total) to follow their PDFs into
`ta_notes/2026/processed_outputs/`, preserving the sibling convention
every pipeline relies on. Ran the real `rebuild()` (scoped to math-camp)
against the production index afterward: all 4 cards cheaply reconciled
(path-only update, no LLM call), `orphaned: 0`. 4 pre-existing orphaned
cards remain in math-camp, confirmed unrelated to any of this session's
changes (same set before and after, unaffected by any fix here) -- left
alone, out of scope.

## Suggested handoff prompt

> Read `docs/superpowers/specs/2026-09-21-source-asset-relocation-brainstorm-addendum.md`.
> A concurrent session brainstormed the gaps in our existing spec/plan
> (folder vocabulary unification, the math-camp duplicate-PDF resolution,
> and docx/pptx scope) and got user decisions on all three -- fold them
> into the spec and plan as amendments (or a new task) before continuing
> implementation from Task 3 onward. The "Still open" section lists three
> items (README updates, gitignore/Direct-Git-Sync updates, triplicate
> .excalidraw.md cleanup) that still need their own brainstorming turn
> with the user -- don't assume an answer for those, ask.
