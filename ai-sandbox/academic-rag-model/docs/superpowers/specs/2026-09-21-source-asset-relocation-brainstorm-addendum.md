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
  `academic_notes/math-camp/lecture_notes/` (the one outlier vs. every
  other course's `lecture_notes`).

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
