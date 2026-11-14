# Handoff to Codex: reference checker tiers and linking pass (v6)

From: Claude, 2026-11-14. To: Codex.
Supersedes the work order in `... - v5.md` (v1 to v5 kept unchanged). Scope: implement the owner's decisions on identity tiers and the reference-list linking pass. Claude changes no checker code.

Start from current `origin/main` in a new per-task worktree and branch (`docs/WORKTREE_WORKFLOW.md`). The round-3 fixes (`cc889db6`) and the multi-DOI limitation note (`0ba4ae0f`) are already on `main`; `tools/reference_checker.py` there has no tier or linking code.

Read these by absolute path first (they live on `main`, not in an old worktree):
- Decisions: `C:\Users\theaa\ai-sandbox-master\ai-sandbox\research\independent-research\docs\superpowers\plans\2026-11-14-reference-checker-identity-tiers-decision - v2.md`
- Where the checker sits and the review ledger shape: `...\plans\2026-11-14-reference-checker-review-artifact-plan.md` and `... - v2.md` (design only; do not build the artifact).
- Corrected Memo: `...\notes\01_compound-shocks-panel\review-gate\Literature Gap Memo - v2.md` (on branch `claude/memo-doi-corrections`, `42c636e4`, pushed; not on `main` yet).

## 1. Decisions to implement (owner-approved, not reopened)

1. `SAME_WORK` splits into three tiers; nothing passes automatically except CONFIRMED.
   - **CONFIRMED:** title score >= 0.92, or >= 0.5 with the cited year agreeing with the registry (any registered year, as the existing year rule).
   - **PLAUSIBLE:** first author and year agree but no title is available for the citation. Always reviewed.
   - **REVIEW:** title score < 0.5, or the year differs.
2. A linking pass runs before PLAUSIBLE is assigned: if the note has a title elsewhere, use it.
3. Identity and `text_fidelity` stay separate. Author-year-only citations are never `MATCH`. `AMBIGUOUS` rows go to the review artifact. 0.5 is a starting cut; keep both thresholds as named constants.

## 2. Work order (tests first; one commit per step; offline tests green at each step)

**Step 1: tier field.**
- Add `tier` per row. Define it for every identity: SAME_WORK maps to CONFIRMED, PLAUSIBLE or REVIEW per section 1; AMBIGUOUS maps to REVIEW; WRONG_WORK, NOT_FOUND and UNCHECKED keep their identity as the tier (they are defects or unchecked, not review decisions). Document the full mapping in the module docstring.
- Decide and document the fate of the legacy `classification` field. Propose a mapping and keep it for one release so existing consumers (none known, checker is unwired) do not break.
- Add `tier` counts to `identity_counts`, both at mention level and per distinct DOI (worst tier per DOI; define the rank, CONFIRMED lowest risk, WRONG_WORK highest).
- JSON and markdown output both carry `tier`.

**Step 2: tier tests with independent expected values.** Do not copy tool output into expectations.
- Brown, Lopez, Montiel Olea, and Rosenzweig and Udry are correct citations with title scores under 0.5 (from v5 section 4): expect REVIEW.
- The crafted probe with title score 0.29 and an unrelated paper: expect REVIEW.
- `Literature Gap Memo - v2.md`: its seven DOI rows have no titles, so expect all seven PLAUSIBLE and zero CONFIRMED (the two URL rows stay UNCHECKED). Use recorded registry answers; do not hit the network in the offline suite.
- Report the CONFIRMED / PLAUSIBLE / REVIEW split across the 31 SAME_WORK rows in the three v2 notes.

**Step 3: reference-list parsing.** Parse each reference-list entry into author(s), year, suffix (`a`/`b`), title and DOI, kept separate from inline mentions. Reuse `citation_fields` where it fits; do not read a journal name as a title (the round-3 rule).

**Step 4: inline author-year parsing.** Handle "Smith (2020)", "Smith & Jones (2020)", "Smith et al. (2020)", "Smith 2020", "(Smith, 2020)", and `2020a`/`2020b`.

**Step 5: linking rules.** Key = normalized first-author surname plus year (co-author surnames when given).
- Exactly one list entry matches: link it, then compare its title with the registry title and apply the tier rules.
- A list entry contains the same DOI: link by DOI (strongest).
- Two or more entries match: compare the DOI's registry title with each entry; if exactly one scores >= 0.92, that entry resolves it; otherwise REVIEW.
- No match or no reference list with titles: stays PLAUSIBLE.
- Add an `evidence` field: `title_in_citation`, `list_entry`, `doi_in_list`.
- Safety property to test: a wrong link yields a title mismatch and REVIEW, never CONFIRMED.

**Step 6: linking tests.** Synthetic notes: two same-author same-year papers (both cited); a deliberately mislinked entry (expect REVIEW); a list entry carrying the same DOI; a note with no reference list; a single clean match (expect CONFIRMED with `evidence: list_entry`).

**Step 7: acceptance metric.** Run the three v2 notes and the Memo before and after the linking pass. Report how many rows leave PLAUSIBLE and by which `evidence` value. If almost none move, say so; that is a finding, not a failure.

**Step 8: small carry-overs, any order.**
- Remove or use the dead `kind` branch in `identity_counts` (rows lack a `kind` key).
- Replace `sorted(first_cited)[-1]` as the "surname" in `compare()` with the last name token (it fails safe today, to AMBIGUOUS).
- Regenerate the diff report as UTF-8 if arrows still show as `?`, as a new versioned file (`v5-diff`), never overwriting earlier reports.

## 3. Remaining risks (carried, not for this pass)

- Title-search fallback sends up to 200 characters to Crossref for identifier-free references (documented, not opt-in).
- `--offline` ignores stale 404 entries.
- Coverage counts DOI strings only.
- A correct list entry paired with the wrong claim is not caught; that needs the quote-anchored claim check (design not yet written).
- Multi-DOI table rows (dataset plus paper) still share one citation (documented in `0ba4ae0f`).

## 4. Out of scope

The review artifact, its ledger, any LLM call, pipeline or CI wiring (including `reprokit verify-sources`), editing notes or the Memo, replacement DOIs.

## 5. Reporting back

For each step: commit hash, tests passed and skipped, and which evidence type each result is (fixture, cached registry, fresh registry, or unverified). State plainly what was not run.
