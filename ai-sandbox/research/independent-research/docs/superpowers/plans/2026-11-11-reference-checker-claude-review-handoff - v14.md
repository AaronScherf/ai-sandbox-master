# Handoff to Codex: a failed lookup must not reopen a decided item (v14)

From: Claude, 2026-11-18. To: Codex.
State: v12 and v13 landed (`ca422ff0`), and the README and history landed (`b0f0b47e`). This is a small fix to `tools/reference_review.py`; the checker and the gate are otherwise unchanged. Start from current `origin/main` in a new worktree, run `tools.active_work` before you start and again before you ask to land, and report back before landing.

## 1. The defect

**Observed 2026-11-18, main-checkout ledger.** After v13 landed, Claude raised the five notes again. The Rosenzweig & Udry item in `Novelty Check - RQ3 Transfer - v5.md` came back `pending`, although Aaron had already decided it and its human TITLE_WRONG defect was still in `defects.json`. Its reason read `author overlap; TITLE_DIFFERS (title score 0.47); title search unavailable`. A second `raise` of that note completed the search, and the item dropped out of the open list.

**Cause** (read, `raise_items`): an item keeps its prior status only if `prior.candidates == item.candidates`. The suffix that `_apply_title_search` appends when a lookup is incomplete changes the candidate's reason, so a transient registry failure looks like a material change and the item resets to `pending`.

**Same mechanism elsewhere** (inferred, not observed): checker defects for a note are rebuilt on every raise. If Brown's title search fails transiently, Brown's checker TITLE_WRONG defect disappears and is replaced by a pending REVIEW item. The gate still stops either way, because it counts an open item or an unresolved lookup, so this is not a safety hole. But it loses state, sends a decided citation back to Aaron, and makes ledger counts flicker between runs.

## 2. Ruling

An incomplete lookup is not evidence. When a row's lookup was incomplete (tier `UNRESOLVED`, or `unavailable` in its reason; reuse the gate's own test, factored out as one helper), `raise_items` must leave that (note, DOI) exactly as the ledger already has it:

1. **Prior item exists:** keep its status and its stored candidates; do not set `updated`.
2. **No prior item, but a prior checker defect** for the same note and DOI whose mention texts equal the current ones: keep that defect.
3. **Neither:** behave as today. A new pending item with the "unavailable" reason is correct, and it fails closed.

The gate's `unresolved` count is still computed from the fresh rows, so a run with a failed lookup still stops. Only the ledger stops churning.

A real change still reopens an item or replaces a defect as it does today: changed citation text, a changed registry record, or a changed tier on a complete lookup.

`raise` output: add a one-line count of incomplete lookups that kept their prior state, with "retry later", so a person can see why nothing changed.

## 3. Tests (recorded answers only)

1. A declined item with a human TITLE_WRONG defect, re-raised with the title search failing: the item stays declined, the defect stays, `list --status open` is empty, and `gate` reports `unresolved == 1`.
2. A checker TITLE_WRONG defect, re-raised with the title search failing: the defect is kept, and no pending item is created.
3. An accepted item, re-raised with a DOI lookup failure (tier UNRESOLVED): it stays accepted.
4. The same failing setup on a note with no prior state creates a pending item, as today.
5. A changed citation text on a decided item, with a complete lookup, still reopens it.
6. The `raise` output reports the kept-state count.

## 4. Acceptance (report; do not tune)

1. The focused review suite and checker suite pass, with counts.
2. Against a copy of the main ledger in the worktree, raise the five current notes twice: once with the registry client forced to fail every title search, then normally. Report open items and defects after each run. Expected: identical to the current ledger both times, with the first run's gate showing unresolved lookups.

## 5. Out of scope

Everything else in the checker and gate; the notes; the review page; `docs/AGENT_ROUTING.md` and `GEMINI.md`.

## 6. Reporting back

Per step: commit hash, tests passed and skipped, evidence type, and what was not run. Then the formal `land_branch check` result and the change ID.
