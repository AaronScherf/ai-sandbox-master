# Cross-Course Duplicate Textbook Detection — Design Spec

Date: 2026-09-17
Status: approved in brainstorming, not yet planned/implemented

## 1. Problem & goals

`convert_textbook.py`'s existing skip-if-already-converted check (its
whole-book, content-hash-based check under `--output`, see
`textbook/convert_textbook.py`'s file_id skip logic) only looks inside the
*current* run's own output folder. It has no way to know that the exact
same book -- or the same book as a different scan/copy -- has already been
converted under a **different course's** `academic_resources/<course>/`
folder. Several courses draw on overlapping reading lists (confirmed
live: Efe Ok's *Real Analysis with Economic Applications* already exists,
converted, under a different course's textbook folder, while an identical
copy of the same PDF sits unconverted under `microecon/textbooks/`), so
without this check the pipeline would burn a full GPU conversion pass
(and Vertex AI bib-lookup calls) reproducing output that already exists
byte-for-byte elsewhere.

This spec adds a **local, offline, pre-flight duplicate check** that runs
before any PDF is uploaded to GCS or touches the VM, searches every other
course's already-indexed textbooks for a match, and -- once a match is
confirmed -- copies the existing artifacts instead of reconverting.

**Goals**
- Detect byte-identical duplicates across course folders with certainty,
  no confirmation needed (same guarantee `compute_file_id` already gives
  within one course, just widened in scope).
- Detect same-book-different-scan duplicates via a cheap, local,
  no-LLM fuzzy match on (title, author, year), and always get an
  explicit human yes/no before treating one as a duplicate -- a wrong
  auto-skip here silently loses a real book from the corpus, which is a
  worse failure than an occasional unnecessary confirmation prompt.
- Never re-ask about a pair of books the user has already said "no,
  those are different" about.
- Cost nothing extra on the happy path: no GPU, no VM, no Vertex AI, no
  Gemini calls -- runs in the same class of environment as
  `indexer/index_card.py` and `textbook/bib_info.py` (pure Python, no
  torch/marker/pypdf/genai import).
- Reusable indefinitely, not a one-off fix for the Ok Efe case -- this is
  expected to fire regularly as more courses' reading lists overlap.

**Non-goals**
- No fuzzy matching against non-textbook doc types (problem sets, lecture
  notes, essays) -- scoped to `doc_type == "textbook"` cards only.
- No attempt to merge or de-duplicate content *within* a single course
  (e.g. two different editions deliberately kept side by side) -- this
  only fires across courses.
- No change to the existing single-course, same-run skip check in
  `convert_textbook.py` -- this is an additional, earlier check, not a
  replacement.
- No UI -- output is a plain-text report plus an in-terminal y/n prompt,
  consistent with every other step in this pipeline.

## 2. Where this runs

A new module, `indexer/duplicate_check.py`, run as **Step 0.4** in
`convert_textbook_instructions.md` (and the new agent-facing instructions,
§6) -- immediately after Step 0.2 populates `PDF_FILENAMES` and before
Step 0.3's `gcloud version` check. It runs on the local machine (or inside
the Step 0.1 container, either works -- no GPU/Docker-specific dependency),
using the same `academic-hub` mount/path convention as the rest of the
pipeline.

Entry point:
```
python -m indexer.duplicate_check --textbook-subdir <TEXTBOOK_SUBDIR> --academic-hub-root <path>
```
Takes the same `TEXTBOOK_SUBDIR` the session already declared in Step 0.2.
Only looks directly inside that folder (not subfolders) -- matching Step
0.2's own existing scoping note about not re-descending into
`processed_outputs/`.

## 3. Matching tiers

For each PDF file in `TEXTBOOK_SUBDIR`:

**Tier 1 -- exact (certain, no confirmation):**
`indexer.index_card.compute_file_id(pdf_path)` against
`indexer.index_card.find_card_by_file_id(academic_hub_root, file_id)`,
searched across every course (not just the current one, which is the only
change from what `find_card_by_file_id` already does today). A hit in a
*different* course is a certain duplicate.

**Tier 2 -- fuzzy (always confirmed):** only attempted if Tier 1 finds
nothing. Extracts `(title, author, year)` from the incoming PDF's filename
via the existing `textbook.bib_info.extract_bibliographic_info_from_filename`
(free, local, already used by the real pipeline for the same purpose).
Loads every card where `doc_type == "textbook"` from every course's shard
(`indexer.index_card.list_courses` / `load_shard`) and scores each against
the incoming PDF.

A card itself only stores `title` -- not `author`/`year` as separate
fields. The candidate side of the comparison instead reads:
- `title`: the card's own `title` field directly (the real
  LLM-or-regex-derived title already on record -- more reliable than
  re-deriving one from a filename a second time).
- `author`/`year`: parsed from the candidate's own output folder name,
  which `textbook.bib_info.derive_folder_name` already always writes as
  `<AuthorLastName>_<SanitizedTitle>_<Year>` -- the folder name is
  `os.path.basename(os.path.dirname(card["path"]))`; author is
  everything before the first `_`, year is everything after the last
  `_` (both single tokens by construction, unlike the sanitized title
  portion in between, which is not used here since `card["title"]`
  already gives the real title).

Scoring:
- `title_score`: `difflib.SequenceMatcher(None, norm(a), norm(b)).ratio()`
  on lowercased, punctuation-stripped titles (`norm()` reuses
  `bib_info.sanitize_filename`-style normalization).
- `author_bonus`: +0.15 if the incoming author's last token
  case-insensitively matches a token in the candidate's author.
- `year_bonus`: +0.1 if years match exactly, +0.05 if within 1 (edition
  reprints).
- `combined = min(1.0, title_score + author_bonus + year_bonus)`

Candidates with `combined >= 0.6` are surfaced; below that, never
mentioned (avoids noise from genuinely unrelated books). Multiple
candidates above threshold are all shown, highest score first -- the user
picks the right one or rejects all.

This threshold is intentionally loose (a confirmation gate at 0.6, not a
higher auto-trust bar) precisely because Tier 2 never auto-skips
regardless of score -- see §4.

## 4. Confirmation & dismissal

Every Tier 2 candidate is printed with both books' resolved paths, the
component scores, and the combined score, then a plain y/n prompt. This
step being interactive is why it must run before Steps 3.2-3.3 (GCS
upload / VM conversion) rather than being folded into `convert_textbook.py`
itself, which runs unattended in a detached tmux session on the VM.

- **Confirmed match (Tier 1, or Tier 2 + yes):** the book is added to a
  `to_skip` list (§5) instead of `PDF_FILENAMES` carrying it forward to
  Step 3.2.
- **Tier 2 + no:** recorded in
  `academic-hub/.index/duplicates/dismissals.json` as a flat list of
  `{"file_id_a": ..., "file_id_b": ..., "dismissed_at": ...}` entries
  (sorted pair so order doesn't matter). Future runs check this file
  before ever surfacing that exact pair again. Deleting the file resets
  all dismissals.

The dismissals file lives under `.index/` rather than inside any one
course's shard, since a dismissal is inherently a cross-course fact —
but **nested one level down**, in `.index/duplicates/`, rather than
directly in `.index/` beside `courses.json`/`tags.json`:
`indexer.index_card.list_courses()` treats every `*.json` that is a
*direct child* of `.index/` (bar those two) as a course shard, so a
top-level `duplicate_dismissals.json` would surface as a phantom course
named `duplicate_dismissals` — and `index_search.py`'s `rebuild --prune`
would then walk that "shard", find none of its entries backed by a real
file, and delete every recorded dismissal. `list_courses()` never
descends into subdirectories, so `.index/duplicates/` is structurally
outside its namespace.

A malformed or hand-edited dismissals file is never fatal: it logs a
warning and degrades to "nothing was ever dismissed" (a pair may get
re-asked) rather than aborting the batch, per §6's error-handling rule.

## 5. Copying artifacts + index representation

For each confirmed duplicate, before Step 3.2 runs:

1. Copy `processed_outputs/<BookDir>/` (the `.md`, `.rag.md` if present,
   `images/`, `<BookDir>_metadata.json`, `run_config.json`, and any
   `*_image_descriptions.json` cache) byte-for-byte from the canonical
   course into the current course's `processed_outputs/`, creating the
   folder if needed.
2. Clone the canonical index card (title/summary/tags/level/embedding
   copied as-is -- no LLM re-call) with:
   - `file_id = indexer.index_card.compute_id_from_parts([canonical_file_id, new_course])`
     -- this existing helper is documented for exactly this "identity
     isn't a single file's bytes" case, and salting with `new_course`
     guarantees no collision with the canonical card's own `file_id`,
     preserving every other reader's "one card per file_id" assumption.
   - `course`, `path`, `source_pdf_path` rewritten to the new course's
     location. `path` and the destination directory are derived from the
     incoming PDF's own relative path (`os.path.dirname(new_source_pdf_path)`
     + `/processed_outputs/<BookDir>/<BookDir>.md`), exactly as
     `convert_textbook.py` derives its own `rel_md_path` — *not* rebuilt
     from `<course>/<category>`, which would drop the leading
     `academic_resources/` segment that every real card carries and that
     `index_search.py`'s `_textbook_book_dirs` walk requires.
   - a new field `duplicate_of_file_id` (the canonical card's `file_id`)
     -- lets a future run of this same check recognize "already
     resolved" instantly (skip re-scoring), and gives a human a
     traceable link when auditing the index later.
3. Append the cloned card to the new course's shard via
   `indexer.index_card.save_shard` (direct append, not
   `reconcile_and_write` -- this path is deliberately not the
   single-owner move/reconcile flow used elsewhere in that module) and
   call `recompute_course_entry` for the new course.
4. Remove the duplicate's filename from the list that Step 3.2 onward
   acts on.

The copied `<BookDir>_metadata.json` is additionally rewritten in place
(in the *new* course's copy only) so its `source_pdf_path` /
`source_pdf_file_id` name the new course's PDF and the clone's own
`file_id`, keeping the file internally consistent with the new card (and
correct for `describe_images.py`, which keys off `source_pdf_file_id`).
This does **not**, however, reliably prevent `index_search.py rebuild`
from disturbing the canonical card — see Known Limitations below, which
covers this in the depth it deserves rather than overstating what the
rewrite achieves.

The canonical course's own card and files are never modified.

## 5a. Emitting the converted-file list

A confirmed duplicate's **source PDF is deliberately never deleted or
moved** — this module only ever adds files. That makes "re-glob
`TEXTBOOK_SUBDIR` for `*.pdf` afterward" an actively wrong way for the
calling instructions to rebuild `PDF_FILENAMES`: the glob returns the
identical list as before the check, so the book that was just resolved
gets uploaded and reconverted anyway, defeating the entire feature.

Instead, `--emit-to-convert <path>` writes the final `to_convert` list
(one filename per line) to a file, in addition to the normal
human-readable stdout report. Both instructions documents read it back
with `mapfile -t PDF_FILENAMES < <path>`. An empty `to_convert` writes an
empty file, which yields a zero-length array — the existing
"nothing left to convert, no VM needed" branch.

## 6. Output / reporting

Before returning, prints a summary in three sections so the whole picture
is visible before any GPU time is spent:

```
[Duplicate check] TEXTBOOK_SUBDIR: academic_resources/microecon/textbooks

  To convert (2):
    - Microeconomic Theory ... Mas-Colell... .pdf
    - Rubenstein_Microeconomic_Theory.pdf

  Skipped -- duplicate found, artifacts copied (1):
    - Real Analysis with Economic Applications... .pdf
      -> matches academic_resources/econometrics/textbooks/processed_outputs/Ok_RealAnalysisWithEconomicApplications_2007
      (tier: exact)

  Dismissed candidates, not re-asked (0):
```
Exits 0 always (never fails the run outright) -- a duplicate-check error
on one candidate degrades to "treat as no match" per the error-handling
rule below, not a hard stop.

**Error handling:** a missing/corrupt shard, an unreadable card, or an
exception while scoring one candidate logs a warning to stderr and treats
*that one candidate* as no-match -- consistent with `index_card.py`'s
existing failure-isolation philosophy (`make_failure_card`,
`reconcile_and_write`'s try/except around card generation). Failing
toward "convert it" rather than "silently skip it" is the safe direction
here.

## 6a. Known limitations

**Update (2026-09-20): fixed.** The corruption risk described below is
resolved as of
`docs/superpowers/specs/2026-09-20-pipeline-autonomy-policies-design.md`
Component 3 — `copy_duplicate_artifacts` now marks a clone's on-disk
`_metadata.json` with `duplicate_of_file_id`, and `index_search.py`'s
`rebuild()` recognizes that marker and skips re-hashing the directory
entirely instead of colliding with the canonical card's file_id.
`rebuild`/`--prune` are now safe to run over a course holding a clone
created after this fix shipped. The mechanism section below is kept as
the historical record of the original bug and why the fix works, not as
a still-open warning.

**Duplicate-clone cards are outside `index_search.py`'s file_id
reconciliation model.** That module assumes one card per real file, with
`file_id` derived from that file's own bytes. A clone deliberately breaks
both halves of that assumption: its `file_id` is
`compute_id_from_parts([canonical_file_id, new_course])` (not a hash of
any file), and its `.md`/`images/` are byte-identical to another course's.
Consequences to be aware of:

- **Do not run `index_search.py rebuild` — with or without `--prune` —
  over a course that has received clones, until this limitation is
  addressed.** This is stronger than "check before pruning": `rebuild`
  itself (no `--prune` needed) can silently evict the *canonical* card
  from its own course shard. `rebuild`'s textbook backfill locates a file
  via a card's `source_pdf_path`, hashes it with `compute_file_id()`, and
  derives `course_name` from that same path string — it never trusts a
  stored `file_id`, so §5's `_metadata.json` rewrite (which only changes
  which path is *named*) cannot make this safe in general:
  - **Tier 1 (byte-identical) clones are the worse case.** The new
    course's own copy of the PDF is, by definition, byte-identical to the
    canonical one, so hashing it yields the *same* `file_id` as the
    canonical card no matter which course's path `source_pdf_path` names.
    Once §5's rewrite points that field at the new course, `rebuild` sees
    a `file_id` match against the canonical card but a *different*
    `course_name` (the new one) — its existing-card-found-in-a-different-
    course branch fires, and it moves the canonical card out of its own
    shard into the new course. Confirmed live: a plain `rebuild` (no
    `--prune`) over a course holding a Tier 1 clone leaves the canonical
    course's shard empty for that book.
  - **Tier 2 (different-scan) clones fare no better, differently.** The
    new course's own PDF hashes to a *different*, real `file_id` that no
    existing card carries (a clone's own `file_id` is always the derived
    `compute_id_from_parts` value, never a real hash) — so `rebuild`
    treats it as genuinely new content and generates a brand-new card via
    a fresh LLM call, alongside the clone card already sitting in that
    shard. Two cards, one book, one avoidable API cost.
  - Net effect: §5's metadata rewrite is worth doing anyway (it keeps
    `_metadata.json` self-consistent and correct for
    `describe_images.py`), but treat it as bookkeeping, not a safety
    guarantee against `rebuild`.
- **The only real fix is out of scope for this module.** `index_search.py`
  would need to recognize `duplicate_of_file_id` and either skip clone
  folders entirely during backfill or resolve identity through it instead
  of re-hashing — both `index_search.py` and `index_card.py` are excluded
  by this plan's Global Constraints, which forbid editing either file. Until
  that lands, `duplicate_of_file_id` is a forensic marker for a human
  auditing the index, not something any tooling in this repository honors.
- `duplicate_of_file_id` is the marker for all of this: every clone has
  it, no normally-converted card does.

## 7. Files touched

- New: `indexer/duplicate_check.py` (the module itself, CLI entry point).
- New: `academic-hub/.index/duplicates/dismissals.json` (created on first
  dismissal; nested one level down deliberately -- see §4). Per the root
  `.gitignore`, `.index/` card shards are tracked normally (only
  `.index/chunks/` is ignored, for copyright reasons that don't apply
  here) -- this file is tracked too, same as `courses.json`.
- Modified: `convert_textbook_instructions.md` -- insert Step 0.4.
- New: agent-facing instructions file (separate task, see chat -- not
  part of this spec).
- No changes to `textbook/convert_textbook.py`, `indexer/index_card.py`,
  or any existing card schema field -- purely additive (`duplicate_of_file_id`
  is a new optional field, absent on every existing card).

## 8. Testing

Pure-Python, no GPU/network dependency -- fully unit-testable:
- Tier 1: two fabricated shards with the same `file_id` in different
  courses -> detected, no prompt.
- Tier 2 scoring: known title/author/year pairs at various similarity
  levels -> correct combined score, correct threshold behavior
  (Mas-Colell's *Microeconomic Theory* vs. Rubinstein's *Lecture Notes
  in Microeconomic Theory* as the concrete worked example -- title
  similarity alone actually clears the 0.6 floor here, so it *does*
  surface as a Tier 2 candidate; the test asserts it is only ever
  surfaced for confirmation, never auto-skipped, which is exactly the
  scenario the always-confirm policy in §4 exists to catch).
- Dismissal round-trip: dismiss a pair, rerun, confirm no prompt.
- Copy + card-clone: confirm new card's `file_id` differs from
  canonical's, `duplicate_of_file_id` set correctly, files land in the
  right place, canonical untouched.
- Error-injection: corrupt one course's shard, confirm that course's
  candidates are skipped-with-warning rather than crashing the whole
  check; likewise a corrupt/wrong-shaped dismissals file, which must warn
  and degrade to "nothing dismissed" while the rest of the run (including
  an exact-match skip+copy) still completes.
- Path realism: fixtures must fabricate cards with the full
  `academic_resources/<course>/<cat>/processed_outputs/<Book>/<Book>.md`
  shape real cards have. Un-prefixed fixtures are what let the §5
  destination-path bug pass 38 tests unnoticed.
- Same-course masking: a `file_id` present in both the current course's
  shard *and* an alphabetically-earlier other course's must resolve to
  "not a cross-course duplicate", not to the earlier course
  (`find_card_by_file_id` returns the first match in sorted order).
- `--emit-to-convert`: after an exact-match skip, the emitted file
  contains only the unskipped PDF even though the skipped book's source
  PDF is still sitting in the folder.
