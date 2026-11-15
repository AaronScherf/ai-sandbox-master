# Handoff to Codex: reference checker review ledger (v9)

From: Claude, 2026-11-15. To: Codex.
State: v8 fixes landed on `main` as `872d66e3`, `a3d2690e`, `0121872b` (cherry-picked from `codex/reference-checker-v8-fix`; that branch and worktree can be removed). Checker suite on `main`: 76 passed, 1 skipped.
Scope: build the ledger that turns checker rows needing a human decision into review items, and applies decisions. **Do not build the review page in this pass** (section 6).

Read first, by absolute path under `C:\Users\theaa\ai-sandbox-master\ai-sandbox\`:
- Decisions: `research\independent-research\docs\superpowers\plans\2026-11-14-reference-checker-identity-tiers-decision - v2.md`
- Plan and owner decisions on it: `...\plans\2026-11-14-reference-checker-review-artifact-plan.md` and `... - v2.md`
- Existing review infrastructure to reuse: `academic-rag-model\core\indexer\review_envelope.py` (`ReviewItem`, deterministic `item_id`, statuses `pending | accepted | declined | deferred`) and `academic-rag-model\tools\hub_review.py` (decision records `{item_id, action: accept|decline|defer, chosen, ts}`; `apply_decisions`; dispatch to each ledger's own resolve/reject). Ledger pattern: `core\indexer\offering_links.py` (`review.json`, `resolve_pending`, `reject_pending`, dismissals).

## 1. Design decisions already made (not reopened)

- Review unit: **one item per distinct DOI per note**, listing all of that DOI's mentions.
- **"Same work" carries across notes**, keyed on (DOI, normalized citation text). "Wrong work" does not carry; it is a defect in one note.
- Only CONFIRMED passes without a human. Claim pre-sorting by an agent is approved in principle but out of scope.
- One page, separate ledgers (the `review_envelope` convention): reuse `ReviewItem` and the `hub_review` decision record shape so this ledger can join the shared page later. Keep it in its own module and CLI for now (section 6 explains why).

## 2. What becomes a review item

| Checker row (DOI rows only) | Item? | Why |
|---|---|---|
| CONFIRMED | no | passes |
| REVIEW (includes AMBIGUOUS) | yes | human decides |
| PLAUSIBLE | yes | always reviewed (owner decision) |
| UNCHECKED on a DOI row (parse failure, for example DellaVigna in Summary v3) | yes, reason "checker could not judge" | otherwise it passes silently |
| WRONG_WORK, NOT_FOUND | no; written to a per-note defects list, report only (like `orphan` in the envelope) | needs a fix in the note, not a decision |
| URL rows (no DOI) | no | separate URL check, decided out of this tool |

Within one note, a DOI with several mentions takes the worst tier (existing `identity_counts` rank).

## 3. Ledger

- Module: `tools/reference_review.py`. Storage: `academic-rag-model/.reference_checker_review/` with `review.json`, `dismissals.json`, `defects.json`. Add the folder to `academic-rag-model/.gitignore` next to the two existing `.reference_checker_*` entries. Atomic writes, same approach as the checker cache.
- Contents are metadata only: note path (repo-relative), line numbers, cited text as extracted, DOI, tier, reason, `evidence`, and the registry's title, authors, year, venue. No note bodies, no abstracts.
- `item_id` = `_digest("reference_check", note_rel_path, doi.lower())` (16 hex, matching `review_envelope`). Same question asked twice is the same item.
- `ReviewItem` mapping: `type = "reference_check"`, `subject_ids = [note_rel_path, doi]`, `candidates = [{registry record summary, mentions: [{line, cited_text, normalized_citation}], tier, reason, evidence}]`.
- Dismissal key: (`doi.lower()`, `normalized(citation)`) using the checker's `normalized`. A raise skips an item only when **every** mention's key is dismissed. A changed citation text is a new question and re-queues.

## 4. Functions and CLI

- `raise_items(note_paths, client) -> list[ReviewItem]`: run `check_note` per note, write new pending items, update existing items whose mentions changed, write defects, never duplicate. Idempotent.
- `resolve(item_id)` ("Same work"): mark accepted, write a dismissal for each mention key.
- `reject(item_id, reason)` with `reason` in {`wrong_work`, `not_citation`}: mark declined; `wrong_work` also writes a defect for that note only; `not_citation` records an extractor false positive (append to a `false_positives` list so it can become a test fixture).
- `defer(item_id)` ("Can't tell"): status deferred, stays in the queue next run.
- `apply_decisions(decisions)`: accepts the `hub_review` record shape; `action` accept, decline (with `chosen` carrying the reason) or defer. Unknown item ids are reported, not fatal.
- `is_human_confirmed(doi, citation) -> bool`: for a later gate. Not wired anywhere in this pass.
- CLI: `python -m tools.reference_review raise <notes...> [--offline] [--cache ...]`, `list [--status pending]`, `apply <decisions.json> [--dry-run]`. The tool never edits a note.

## 5. Tests (offline, recorded registry answers only)

1. Deterministic `item_id`; raising twice creates no duplicates.
2. Item selection follows section 2 exactly, including an UNCHECKED DOI row queued and a WRONG_WORK row written to defects, not queued.
3. Per-DOI unit: two mentions of one DOI in one note make one item with two mentions; worst tier wins.
4. Cross-note carry: "Same work" in note A dismisses the same (DOI, citation) in note B; a changed citation text in B re-queues.
5. "Wrong work" does not carry to another note.
6. Defer keeps the item pending-on-next-run; apply is idempotent; `--dry-run` writes nothing.
7. Unknown item id in decisions is reported and does not abort the batch.
8. The ledger writes only inside `.reference_checker_review/`.

## 6. Why no page yet

`tools.hub_review` already renders one page for the hub ledgers, but that page has not been published or validated end to end (P3 status doc, `docs/status/indexer/2026-11-03-hub-path-resilience-p3-status.md`), and it is rooted in the academic hub, not the research notes. Building the ledger with the same item and decision shape means the page step is a small, separate change once Aaron chooses between joining `hub_review` and a sibling page.

## 7. Acceptance run (report, do not tune to it)

Raise on `Novelty Check - RQ1 Knowledge Audit - v4.md`, `RQ2 Decision Space - v4.md`, `RQ3 Transfer - v5.md` and `Summary - v3.md` (online refresh for DOIs only is fine). Expected from the v8 run: about 14 items (4 REVIEW: Brown, Lopez, Rosenzweig and Udry, White/Saran/Welch; 9 PLAUSIBLE in Summary v3; 1 UNCHECKED DellaVigna), zero defects. Report the actual counts per note. If Memo v2 is on `main` by then (PR #37), also raise it: expected 7 PLAUSIBLE.

## 8. Out of scope

The review page or Artifact, any LLM call or pre-sort, gate wiring (`verify-sources`, agent procedure), the URL check, editing notes.

## 9. Reporting back

Per step: commit hash, tests passed and skipped, evidence type (fixture, cached registry, fresh registry, unverified), and what was not run. One commit per step: ledger and ids; selection; resolve, reject and defer; apply and CLI; acceptance run.
