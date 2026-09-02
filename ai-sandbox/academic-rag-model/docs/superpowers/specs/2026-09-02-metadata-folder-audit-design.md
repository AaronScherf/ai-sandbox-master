# Journal Articles: Metadata & Folder Audit — Design Spec

Date: 2026-09-02
Status: approved in brainstorming, not yet planned/implemented

## 1. Problem & goals

Flagged as an open gap in `docs/2026-09-01-journal-discovery-status.md` point
6. Two real problems exist today, both confirmed against the live code
rather than assumed:

1. **`.meta.json` sidecars are write-once.** `metadata_sidecar.write_sidecar()`
   captures title/authors/year/DOI/concepts/relevance score from OpenAlex
   *before* the full text even exists, and nothing ever revisits that data
   once a paper is actually converted. Real cases already found where this
   matters: an OpenAlex title that didn't match the article's own printed
   subtitle; two Björkegren "papers" that plausibly belong to a different,
   OpenAlex-merged author.
2. **Folder correctness is reviewed, never enforced.** `reconcile_needs_manual.py`
   prints a folder/content preview for every converted paper (`main`, lines
   111-115) purely for a human to eyeball — nothing re-derives or re-files a
   mis-routed paper. The one time this was actually fixed for real (the
   "grasp"/"competition-biology" folder cleanup, commit `82e9883`) used a
   one-off script that was never committed — not a repeatable tool.

Brainstormed 2026-09-02. The user's own scoping decisions, already settled,
drive this design directly:

- Auto-correct what has a mechanically well-defined right answer (folder
  placement, tag-frontmatter sync); flag everything else (title, authors,
  DOI) for human resolution, since there is no safe automatic replacement
  value for those without either trusting possibly-stale OpenAlex data or
  guessing at raw text.
- Also check a paper's tags against the shared academic-hub indexer/tag
  system — confirmed during brainstorming that this is *one* shared system,
  not two: `retag.py`'s `_load_all_cards()` already loads every course
  shard under `research/.index/` (journal-article topic folders included)
  in a single pass, and Obsidian reads the exact same `tags:` frontmatter
  property `retag.py` writes. So "compare against academic-hub tags" and
  "compare against Obsidian tags" are the same check.
- Only audit papers not yet audited by default, tracked via a new
  `audited_at` field on each manifest entry (an override flag re-runs
  everything).
- **Run automatically, not as a separate step to remember.** Revisited
  during spec review: the audit has no LLM/Gemini calls (only a free,
  keyless OpenAlex lookup for the folder check), so it's genuinely cheap
  -- there's no real reason to make it a fully separate manual habit.
  Chained onto the end of `reconcile_needs_manual.py`'s own run rather
  than `convert_journal_articles.py`'s: reconcile is the one point where
  *every* paper's manifest `status` and on-disk path are guaranteed
  resolvable together (a manually-downloaded paper doesn't flip from
  `needs_manual` to `downloaded`, with `matched_md_path` recorded, until
  reconcile's own content-matching runs). This also keeps
  `convert_journal_articles.py` itself free of any new network
  dependency, and avoids moving a file mid-conversion while `os.walk`
  might still be traversing the tree.

**Goals**
- A new root-level script, `audit_metadata.py`, importable as a function
  (`audit()`) that `reconcile_needs_manual.py` calls automatically as its
  own final step, and runnable standalone
  (`python -m audit_metadata --recheck-all`) for a full forced re-audit.
  Re-checks each converted paper's folder, tags, title, authors, and DOI
  against its real full text and fresh OpenAlex data.
- Auto-apply corrections that have a well-defined right answer (folder
  re-routing, tag-frontmatter sync); write everything else to a new
  checkbox worklist, `metadata_audit_flags.md`, with evidence.
- Skip papers already audited (`audited_at` set) unless `--recheck-all` is
  passed -- this is what keeps the automatic per-reconcile invocation
  cheap: a run where nothing new was converted does effectively no work.
- Retire `reconcile_needs_manual.py`'s now-redundant read-only
  folder/content preview loop — this script supersedes it with a real
  fresh-OpenAlex source of truth and actual correction, not just a preview.

**Non-goals**
- No LLM-based title/author extraction or correction — considered during
  brainstorming and explicitly declined for this round (new cost, new
  failure mode: the LLM itself could misread a title). Title/author
  mismatches stay flag-only.
- No new tag-generation or tag-clustering logic — this reads and syncs
  what `retag.py`/the index cards already produce; it never proposes a tag
  itself.
- No automatic re-verification of a flagged paper. Resolving a flag is a
  human act (fix the sidecar, re-file by hand, etc.); a flag only clears
  on a later `--recheck-all` run that no longer finds the mismatch.
- Doesn't touch `relevance_score` — that's a discovery-time scoring
  artifact, not a bibliographic fact to verify.

## 2. Architecture

A new root-level script, `audit_metadata.py`, alongside
`reconcile_needs_manual.py` — same precedent: a top-level script bridging
`journal_discovery`'s manifest, `journal_articles`' converted output, and
(new for this script) the academic-hub indexer under `indexer/`.

Two entry points, both exercising the same `audit()` function:

- **Automatic:** `reconcile_needs_manual.py`'s own `main()` calls
  `audit_metadata.audit(articles_dir, index_root, mailto, recheck_all=False)`
  as its last step, after saving the manifest and regenerating
  `needs_manual_downloads.md`. This is the normal way the audit runs day
  to day — no separate command to remember.
- **Manual:** `python -m audit_metadata [--recheck-all]` — for an
  out-of-band run, and the only way to force a full re-check (e.g. after
  fixing a flagged paper by hand, or after changing detection logic
  itself).

```powershell
python -m reconcile_needs_manual          # runs reconcile, then audit automatically
python -m audit_metadata --recheck-all    # forced full re-audit, standalone
```

## 3. New and changed components

- **`audit_metadata.py` (new).** Core functions:
  - `select_audit_targets(manifest, recheck_all) -> list[tuple[str, dict]]`
    — entries with `status` in `{"fetched", "downloaded"}` and (if not
    `recheck_all`) no `audited_at` yet.
  - `resolve_paper_paths(articles_dir, key, entry) -> tuple[Path, Path]`
    — returns `(pdf_path, md_path)`. For a `fetched` entry: pdf path is
    `<folder>/<sanitize_topic_name(key)[:80]>.pdf` (mirrors
    `topic_routing.pdf_filename()`'s own derivation from the manifest key,
    which is already `work.doi or work.openalex_id`); md path is
    `<folder>/processed_outputs/<same-stem>.md` (`transcribe_notes.process_pdf()`'s
    own output convention). For a `downloaded` entry: `matched_md_path` is
    already recorded by `reconcile_needs_manual.py`; pdf path is derived
    as `matched_md_path.parent.parent / f"{matched_md_path.stem}.pdf"`,
    since `process_pdf()` names a manually-downloaded file's `.md` after
    that PDF's own (arbitrary) stem.
  - `check_folder(articles_dir, key, entry, mailto) -> FolderCheckResult`
    — calls `discovery.resolve_work_by_doi()` (existing, unchanged) when
    `key` is a DOI; compares the fresh top concept's
    `topic_routing.sanitize_topic_name()` against the entry's current
    `folder`. Skipped (not flagged) when `key` isn't a DOI (bare OpenAlex
    ID entries) — noted explicitly in run output, per §7.
  - `check_tag_sync(index_root, pdf_path, md_path) -> TagSyncResult`
    — `index_card.compute_file_id(pdf_path)` +
    `index_card.find_card_by_file_id()` to get the index's real tags;
    compares against the `.md`'s current frontmatter `tags:` line.
  - `check_title(entry, text) -> AuditFlag | None`,
    `check_authors(entry, text) -> AuditFlag | None`,
    `check_doi(key, entry, text) -> AuditFlag | None` — text-only checks,
    the same substring-match approach `is_confirmed_downloaded()` already
    uses for titles/DOIs, built on `journal_discovery.text_match.normalize()`
    (new, see below) rather than importing from `reconcile_needs_manual.py`
    — needed to avoid a circular import now that `reconcile_needs_manual.py`
    itself imports `audit_metadata` (see that bullet below).
  - `apply_folder_correction(...)` — moves `.pdf`, `.meta.json` (if
    present — only `fetched` entries have one; manual `downloaded` entries
    never got a sidecar written), `processed_outputs/*.md`, and
    `*_pages_cache.json` (if present) to the new folder; calls
    `index_card.move_card()` (new, see below); updates the manifest
    entry's `folder`.
  - `apply_tag_sync(md_path, tags)` — rewrites the frontmatter `tags:`
    line to match the index card, same rendering
    (`"[" + ", ".join(tags) + "]"`) `retag.write_tags_to_frontmatter()`
    already uses, reused rather than reimplemented.
  - `audit(articles_dir, index_root, mailto, recheck_all) -> dict`
    — orchestrates all of the above per selected entry, sets `audited_at`
    (only after both the filesystem move and the index-card update
    succeed, per §7), collects `audit_flags`, saves the manifest, calls
    `worklist.write_metadata_audit_flags_worklist()`. Returns counts for
    CLI reporting, matching `reconcile()`'s and `discover.run()`'s own
    return-dict shape. `index_root` here is the same generic parameter
    `convert_journal_articles.py`'s own `--index-root` already passes
    positionally as `academic_hub_root` into `index_card.*` functions
    (confirmed via `tests/test_convert_journal_articles.py`'s own
    comment) — not literally the `academic-hub/` folder, despite that
    parameter name inside `index_card.py`.
  - `main()` — thin CLI wrapper: `--articles-dir` and `--index-root`
    (same default as `convert_journal_articles.py`'s own —
    `research/`, sibling of `academic-hub/`), `--recheck-all`, and
    `mailto` read from `OPENALEX_CONTACT_EMAIL` the same way
    `discover.py`/`snowball.py` already do.

- **`journal_discovery/text_match.py` (new).** `normalize(text) -> str`
  — the same lowercase/strip-non-alphanumeric normalization
  `reconcile_needs_manual.py`'s private `_normalize()` already does,
  promoted to a small shared module (mirrors how `manifest.py`'s
  `skip_already_seen()` was promoted out of `discover.py` for
  `snowball.py` to share, per that spec's own precedent) so both
  `reconcile_needs_manual.py` and `audit_metadata.py` can depend on it
  without depending on *each other* in the wrong direction.

- **`journal_discovery/discovery.py`, `journal_discovery/topic_routing.py`:**
  no changes — `resolve_work_by_doi()` and `sanitize_topic_name()` are
  reused exactly as they already exist.

- **`journal_discovery/manifest.py`:** no schema changes. `audited_at`
  (ISO timestamp) and `audit_flags` (list of `{"type", "detail"}` dicts)
  ride on `record_outcome()`'s existing generic `metadata` dict parameter
  — the same mechanism `snowball.py` used for its own new fields, so
  `manifest.py` itself doesn't need to know these keys exist.

- **`journal_discovery/worklist.py`:** new
  `write_metadata_audit_flags_worklist(manifest, articles_dir) -> Path`.
  Structurally similar to the existing writers but filtered by *presence
  of a non-empty `audit_flags` list* rather than `status` (an audited
  paper keeps its original `status`; only newly-added `audit_flags` marks
  it as needing review) — so it does not go through the generic
  `_write_checkbox_worklist(..., status_filter=...)` helper, which assumes
  one manifest status per worklist. Reuses `_link_for()` and
  `_read_checked_links()` (both already generic) so checkbox-preservation
  behaves identically to the other two worklists.

- **`indexer/index_card.py`:** new
  `move_card(academic_hub_root, file_id, new_course) -> bool`. Uses
  `find_card_by_file_id()` to locate the current `(course, card)`; if
  `new_course` differs, removes the card from the old shard, updates its
  `course`/`path`/`source_pdf_path` fields, appends it to the new shard,
  `save_shard()`s both, and `recompute_course_entry()`s both old and new
  courses (so each course's centroid/`predominant_tags` in `courses.json`
  stays correct). No one-off script to reuse — the earlier folder-fix
  cleanup that did this by hand was never committed (confirmed via `git
  log`), so this is new, but genuinely reusable beyond this one script.

- **`reconcile_needs_manual.py` (changed):**
  - Remove the "Folder/content review" print loop (current lines 111-115)
    and its docstring mention — superseded by `audit_metadata.py`'s real
    fresh-OpenAlex comparison and actual correction. `reconcile()`'s own
    job (confirming `needs_manual` -> `downloaded` by content match) is
    unchanged.
  - Its private `_normalize()` is removed in favor of importing
    `journal_discovery.text_match.normalize()`.
  - Gains a new `--index-root` CLI argument (same default
    `convert_journal_articles.py` already uses), and reads `mailto` from
    `OPENALEX_CONTACT_EMAIL` the same way `discover.py`/`snowball.py` do.
  - `main()` calls `audit_metadata.audit(args.articles_dir,
    args.index_root, mailto, recheck_all=False)` as its final step (see
    §7 for what happens if `OPENALEX_CONTACT_EMAIL` isn't set), and
    prints its returned counts alongside reconcile's own
    confirmed/still-pending output.
  - `reconcile()` itself (the importable function, distinct from `main()`)
    stays audit-free — only `main()` chains the two, so any code already
    calling `reconcile()` directly (e.g. tests) is unaffected by this
    change.

- **`journal_discovery_instructions.md` / `journal_articles_instructions.md`:**
  update Step 3 to describe the audit as automatic (running right after
  reconciliation, not a separate step), remove the folder/content-review
  mention, and add one short note on `python -m audit_metadata --recheck-all`
  for a forced full re-audit.

## 4. Checks and correction behavior

| Check | Compares | Mismatch action | Evidence recorded |
|---|---|---|---|
| Folder / concept | Current folder vs. fresh OpenAlex top level-0 concept (`resolve_work_by_doi()`) | **Auto-correct**: move files, update index card's course, update manifest `folder` | Logged to stdout: old folder -> new folder |
| Tag sync | `.md` frontmatter `tags:` vs. index card's `tags` (via `file_id`) | **Auto-correct**: rewrite frontmatter to match index | Logged to stdout: old tags -> new tags |
| Title | `.meta.json`/manifest title vs. text (substring match, normalized) | **Flag** | Stored title + a short text excerpt |
| Authors | Stored author surnames vs. text | **Flag** (triggers only when *none* of the stored authors appear at all — the mis-attribution signal) | Stored authors list |
| DOI | Stored DOI vs. text | **Flag** | Stored DOI |

Folder and tag-sync are auto-corrected because the "right" value is
mechanically derivable (a fresh OpenAlex lookup; the index card's own
tags). Title/authors/DOI have no such well-defined replacement — flagging
with evidence, and leaving the decision to a human, matches how the
"Nature title mismatch" and "SSRN duplicate-listing" cases were actually
resolved in practice (`reconcile_needs_manual.py`'s own doc history).

## 5. Data flow

```
audit_metadata.audit(articles_dir, index_root, mailto, recheck_all):
  1. manifest = load_manifest(manifest_path(articles_dir))
  2. targets = select_audit_targets(manifest, recheck_all)
  3. for key, entry in targets:
       pdf_path, md_path = resolve_paper_paths(articles_dir, key, entry)
       if not md_path.exists(): skip (log a warning; leave audited_at unset)
       text = md_path.read_text(...)

       folder_result = check_folder(articles_dir, key, entry, mailto)
       if folder_result.mismatch:
           apply_folder_correction(...)   # updates pdf_path/md_path too

       tag_result = check_tag_sync(index_root, pdf_path, md_path)
       if tag_result.mismatch:
           apply_tag_sync(md_path, tag_result.index_tags)

       flags = [f for f in (check_title(...), check_authors(...), check_doi(...)) if f]

       entry["audited_at"] = now_iso()
       if flags:
           entry["audit_flags"] = [f.to_dict() for f in flags]
       elif "audit_flags" in entry:
           del entry["audit_flags"]   # a --recheck-all run that no longer
                                       # finds a prior mismatch clears it
  4. save_manifest(...)
  5. worklist.write_metadata_audit_flags_worklist(manifest, articles_dir)
  6. return counts (folder_corrections, tag_syncs, flagged, skipped, audited)
```

**Caller, automatic path:**

```
reconcile_needs_manual.main():
  1. result = reconcile(args.articles_dir)          # unchanged
  2. print reconcile's own confirmed/still-pending summary   # unchanged
  3. mailto = os.environ.get("OPENALEX_CONTACT_EMAIL")
     if mailto:
         audit_result = audit_metadata.audit(args.articles_dir, args.index_root, mailto, recheck_all=False)
         print audit_result's summary
     else:
         print a warning that the audit step was skipped, and why
```

## 6. State model (manifest field additions)

```json
{
  "10.1234/some-paper": {
    "status": "fetched",
    "fetched_at": "2026-09-01T12:00:00+00:00",
    "folder": "business",
    "title": "...",
    "audited_at": "2026-09-03T10:00:00+00:00",
    "audit_flags": [
      {"type": "title_mismatch", "detail": "stored title not found in text (excerpt: \"...\")"},
      {"type": "author_mismatch", "detail": "none of ['A. Smith', 'B. Jones'] found in text"}
    ]
  }
}
```

An entry with no mismatches gets `audited_at` set and no `audit_flags` key
at all (not an empty list) — keeps `write_metadata_audit_flags_worklist()`'s
filter (`entry.get("audit_flags")`) a plain truthiness check.

## 7. Error handling

- **`resolve_work_by_doi()` network failure** (folder check only): log a
  warning, skip the folder check for that paper *this run*, but still run
  the other checks and still set `audited_at` — a transient network error
  shouldn't block title/author/DOI/tag checks that don't need it. A folder
  mismatch caused this way will simply be re-evaluated in a future
  `--recheck-all` run, same as any other resolved flag.
- **A key that isn't a DOI** (bare OpenAlex-ID-keyed entries — rare but
  possible per `manifest_key()`'s fallback): both the folder check (needs
  `resolve_work_by_doi()`, which has no ID-based equivalent today) and the
  DOI-sanity check (nothing to look for in the text) are skipped entirely
  — not flagged, not treated as an error — logged plainly in run output so
  it's visible, not silently dropped. Title/author/tag-sync checks are
  unaffected and still run.
- **Folder correction partially fails** (e.g. a file-move permission
  error mid-move, or `move_card()` fails after files already moved):
  logged with full detail (which files moved, which didn't); `audited_at`
  is deliberately **not** set for that paper, so it's retried
  automatically on the very next run (whether or not `--recheck-all` is
  passed) rather than silently left half-migrated.
- **No index card found** (`index_card.find_card_by_file_id()` returns
  `None` — e.g. conversion ran but the indexing hook failed, or hasn't run
  yet): tag-sync check is skipped for that paper this run, logged
  plainly; other checks still run, `audited_at` is still set (nothing
  about this is expected to change on its own between runs the way a
  network error might, so there's no retry value in leaving it unset).
- **Missing converted `.md`** (shouldn't happen for a `status="fetched"`/
  `"downloaded"` entry, but the filesystem could have changed since):
  logged, skipped, `audited_at` left unset so it's retried.
- **`OPENALEX_CONTACT_EMAIL` not set** when `reconcile_needs_manual.py`
  runs: this is new as of automatic chaining — reconcile's own job never
  needed this env var before, and shouldn't start hard-failing over it.
  `main()` prints a clear warning ("audit step skipped: set
  OPENALEX_CONTACT_EMAIL to enable it") and skips calling `audit()`
  entirely for that run; `reconcile()`'s own matching/worklist-regen
  output is printed and the command still exits successfully. The
  standalone `python -m audit_metadata` CLI, by contrast, still hard-fails
  on a missing `mailto` (matching `discover.py`/`snowball.py`'s existing
  convention for a command whose entire purpose needs it).

## 8. Testing

Mirrors the existing flat `tests/` convention (`test_reconcile_needs_manual.py`,
`test_index_card.py`, `test_worklist.py`, `test_discovery.py` as direct
precedent):

- `tests/test_audit_metadata.py` (new): `select_audit_targets()` (honors
  `audited_at`/`recheck_all`), `resolve_paper_paths()` for both `fetched`
  and `downloaded` shapes, each `check_*()` function against
  hand-constructed text/manifest-entry fixtures (a title present, a title
  absent, an author present, no authors present, a DOI present/absent,
  a folder match/mismatch via a mocked `resolve_work_by_doi`), and
  `audit()`'s end-to-end orchestration via `tmp_path` fixtures (mirrors
  `test_reconcile_needs_manual.py`'s own fixture style) confirming:
  auto-corrections actually move files/rewrite frontmatter,
  `audit_flags`/`audited_at` land correctly in the saved manifest, a
  paper with `audited_at` already set is skipped without `--recheck-all`
  and re-processed with it, and a resolved flag is cleared on a
  `--recheck-all` pass that no longer reproduces it.
- `tests/test_index_card.py` (extended): `move_card()` — moves a card
  between two shards correctly (old shard loses it, new shard gains it
  with updated `course`/`path`), and `recompute_course_entry()` is called
  for both courses (old course's centroid/tags recomputed without the
  moved card; new course's centroid/tags recomputed with it). A
  `move_card()` call where `new_course == old_course` is a no-op.
- `tests/test_worklist.py` (extended): `write_metadata_audit_flags_worklist()`
  — only entries with a non-empty `audit_flags` appear; checkbox
  preservation works independently of the other two worklist files (same
  per-file-independence test already covering
  `write_needs_manual_worklist`/`write_snowball_candidates_worklist`).
- `tests/test_reconcile_needs_manual.py` (updated): remove/adjust any
  assertion covering the retired folder/content-preview print loop; new
  tests confirming `main()` calls `audit_metadata.audit()` (mocked) after
  `reconcile()` when `OPENALEX_CONTACT_EMAIL` is set, skips it with a
  printed warning (and still exits successfully) when it isn't, and that
  `reconcile()` itself — called directly, not through `main()` — never
  touches `audit_metadata` at all.
- `tests/test_text_match.py` (new): `normalize()` — same cases
  `test_reconcile_needs_manual.py` already covers for the old private
  `_normalize()` (case folding, punctuation stripping), moved here rather
  than duplicated.

## 9. Follow-on discussion (open, not decided by this spec)

- **Targeted re-check** (`--recheck-doi <doi>`, repeatable, mirroring
  `--seed-doi` in `snowball.py`) — a cheaper way to re-verify one flagged
  paper after fixing it by hand, instead of `--recheck-all` re-scanning
  the whole corpus. Not included in v1; add if `--recheck-all`'s full
  rescan proves annoying in practice at real corpus size.
- **LLM-based title/author correction** — explicitly declined during
  brainstorming for this round (new cost, new failure mode); could be
  revisited later as an opt-in flag if flag volume turns out to be high
  enough that manual resolution becomes the bottleneck.
- **CORE.ac.uk as a third OA-discovery tier**, and the **author-profile
  mis-attribution check** (comparing a candidate's concepts against the
  querying faculty member's own dominant concept profile at *discovery*
  time, before a paper ever enters the corpus) — both already tracked as
  open ideas in `docs/2026-09-01-journal-discovery-status.md`, distinct
  from this audit (which only runs *after* conversion) and not
  duplicated here.
