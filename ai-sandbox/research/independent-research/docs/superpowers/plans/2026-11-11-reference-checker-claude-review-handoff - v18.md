# Handoff to Codex: the writer names the work, not the reviewer (v18)

From: Claude, 2026-11-23. To: Codex. Aaron approved this direction on 2026-11-23.

v17 is on main. Start from current `origin/main` in a new worktree. Run `tools.active_work` before you start and again before you ask to land, and report back before landing.

This touches:
- `tools/reference_checker.py`, `tools/reference_review.py` and their tests;
- the checker README;
- the "Citing literature" section of the root `CLAUDE.md`, `AGENTS.md` and `GEMINI.md` (rule 5).

DOIs are left out of this file on purpose, because the landing gate checks Markdown under `ai-sandbox/research/`. The evidence, with DOIs, is in `ai-sandbox/academic-rag-model/docs/status/tools/2026-11-23-reference-checker-v17-review.md`.

**Order:** `claude/citation-error-fixes` should land before this does. Its Narrative cites "Meager (2019, AEJ: Applied)" with no title, and under rule 1 that would stop the branch.

## 1. Why

v17 passes a title-less row as AUTHOR_YEAR when the DOI's registered authors and year match the citation. Aaron reviewed the 20 rows left after v17 and found that this evidence does not show what the writer meant:
- Some DOIs were plainly unrelated to the claim.
- Some citations matched a real paper by the same authors and year that the DOI did not point to. One example: the Abushama, Resnick, Siddig & Kirui (2023) paper the Literature Gap Memo meant is on CGSpace, but the memo attached a different DOI.
- Gemini appears to invent a DOI when it cannot find one, and sometimes attaches unrelated work.

So "the DOI is by these authors in this year" shows the DOI is real. It does not show that it is the intended work. With only a name and a year, a reviewer cannot tell either. Only the writer knows.

**Decision (Aaron, 2026-11-23).** In a note a branch adds or edits, every DOI citation must carry the title of the work the writer means. A citation without one is a defect for the writer to fix, not a review item. Notes nobody touches keep v17's behavior. This reverses v17's AUTHOR_YEAR pass for edited notes only.

**The trap this must avoid.** A writer told "add the title" will read the title off the DOI's own record. That makes the title match by construction and launders a wrong DOI. The lookup must go from the work to the DOI: search for the work by title and authors, then take the DOI from that record. Rule 2 keeps the checker from inviting the copy, and rule 5 states the order in every agent's instructions.

## 2. Rules

1. **New defect tier TITLE_MISSING, in strict mode.**
   - The tier ranks with TITLE_WRONG and belongs to `DEFECT_TIERS`.
   - In strict mode, a DOI item (one note, one DOI) with no cited title on any of its mentions is TITLE_MISSING. This applies whatever tier v17 would have given it: AUTHOR_YEAR, PLAUSIBLE, REVIEW or UNCHECKED.
   - "Cited title" means what `_cited_title` returns: at least two words, not the venue.
   - An item counts as titled if **any** mention carries a title. A short in-text "Meager (2019)" next to a full reference-list entry for the same DOI is fine.
   - An item with a title goes through the normal title path (CONFIRMED, TITLE_WRONG, REVIEW and so on), unchanged.
   - DESCRIBED stays a pass. Its link text shares content words with the registered title, which is evidence of what was meant.
   - Rows with no DOI are out of scope.
2. **Message.**
   - The TITLE_MISSING reason must not contain the registered title. Suggested wording: "no title: write the title of the work you mean, found by searching for that work, then take its DOI from that record; do not copy this DOI's registered title".
   - The `raise` output for these rows must not print the registry title either. The page card may still show it, since the reviewer needs it.
   - Also change TITLE_WRONG's "use the registered title" to "confirm which work you meant; if it is this DOI's work, use its registered title".
3. **Which mode runs when.**
   - `gate()` is always strict.
   - `reference_review raise` is strict by default, because writers run it on their own notes before handoff.
   - `raise --sweep` uses v17 behavior. It is for maintenance sweeps of notes nobody is editing.
   - A sweep neither creates nor clears TITLE_MISSING defects.
   - In strict mode, TITLE_MISSING is re-evaluated on every raise. It clears when the citation gains a title, or when a reviewer marks that exact citation text `quoted`, as other defects do.
4. **Earlier human accepts do not exempt a row.** An accepted, title-less item in a strict-mode note becomes TITLE_MISSING. Those accepts were made on author-and-year evidence, which this handoff rules insufficient.
5. **Instruction files.** In the "Citing literature" section of the root `CLAUDE.md`, `AGENTS.md` and `GEMINI.md`, add one bullet in each file's existing style. It should say:
   - every citation names the work's title;
   - find the work in a registry by title and authors, then take its DOI from that record;
   - never fill in a title by reading a DOI's record.

   Claude will make the matching edit to the website's `GEMINI.md`, which is a separate repository.
6. **README.**
   - Add TITLE_MISSING to the tier table.
   - Describe strict and sweep modes, and say AUTHOR_YEAR now applies only to sweeps.
   - State the trap from section 1 in one sentence.

## 3. Tests (recorded answers only)

1. **Strict:** a note citing "Meager (2019)" with a DOI and no title anywhere gives TITLE_MISSING, and `gate()` counts it as a defect.
2. **Strict:** the same note plus a reference-list entry for the same DOI, carrying the registered title, gives CONFIRMED and no defect.
3. **Strict:** a cited title that belongs to a different real work than the DOI does not pass. It keeps its existing non-pass tier.
4. **Sweep:** case 1 gives AUTHOR_YEAR, as in v17.
5. **Strict descriptive links:** "Springer chapter 14" gives TITLE_MISSING, and the v17 Yemen description still gives DESCRIBED.
6. The TITLE_MISSING reason and the `raise` output do not contain the registered title.
7. A `quoted` decision clears TITLE_MISSING for that citation text in that note only. Changed text reopens it.
8. A ledger item already `accepted` for a title-less row gives TITLE_MISSING when its note is raised in strict mode.
9. A sweep leaves an existing TITLE_MISSING defect unchanged.
10. **Regression:** all v16 and v17 tests pass, including the four Brown invented-title shapes, Lin, "AEA P&P" and the venue-less sibling case.

## 4. Acceptance (report; do not tune)

Use a copy of the main ledger and the same 24 notes as v17:
- the 22 on `main`;
- Context Distance Cases v2 and Adversarial Scan v2 from `claude/citation-error-fixes` if it has landed, otherwise their v1.

Report:
- **Sweep mode:** defects and open items per note. This should match the ledger after Aaron's 2026-11-23 decisions: 12 deferred items open.
- **Strict mode:** TITLE_MISSING count per note, and the total. This is the work a writer faces when they next edit each note. Aaron uses it to judge the cost.
- **Strict mode on Literature Gap Memo - Verification Review:** which rows the existing `quoted` decisions already cover.

## 5. Out of scope

- Editing notes.
- Narrowing strict mode to changed lines instead of the whole note.
- Rows with no DOI.
- The review page. Claude adds the TITLE_MISSING chip after this lands.
- Checking whether a paper supports the claim it is cited for. That is a separate design, recorded under `## Claim Support Check` in `ai-sandbox/academic-rag-model/docs/trackers/academic_hub_to_do.md`.
