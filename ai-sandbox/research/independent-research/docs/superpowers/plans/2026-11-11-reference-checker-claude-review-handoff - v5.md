# Reference checker review, round 4 (v5)

From: Claude review session, 2026-11-14.
Reviewed: Codex commit `5b33b1bf` on `codex/reference-checker` (worktree `.worktrees/codex-reference-checker`). Read-only: no Codex files, Gemini notes or Memo changed.
Supersedes the work order in `... - v4.md`. v4's defects 1 to 4 are closed (section 2).

## 1. Verdict

The checker is ready for a landing decision as an advisory tool. It should not be wired into any gate yet. No blocking defects remain. Three small follow-ups are listed in section 3; none needs to hold the merge.

## 2. What was checked

Evidence type is labelled: **run** = Claude ran it, **read** = Claude read the code or output, **reported** = Codex's claim only.

| Item | Result | Evidence |
|---|---|---|
| Branch state | clean, one commit, 7 files (checker, tests, 3 fixtures, new raw Memo fixture, `.gitignore`) | run |
| Offline tests | 45 passed, 1 skipped (the opt-in online smoke test) | run |
| Memo `v4-final.json` | 18 mentions = 8 SAME_WORK, 8 WRONG_WORK, 2 UNCHECKED (FAO, ACLED URLs); by DOI 4 SAME_WORK, 5 WRONG_WORK; 9 of 9 DOIs attached | read (cached registry results in the report) |
| v4 defect 1 (table cell picks claim cell) | fixed: author-year cell preferred (`extract`, lines 96-103); second Abushama mention is now WRONG_WORK | read, run |
| v4 defect 3 (journal read as title) | fixed: four correct Memo mentions now `NO_TITLE` | read |
| v4 defect 4 (tests did not pin the Memo) | fixed: `reference_checker_memo_registry_raw.json` plus tests at `test_memo_ground_truth_counts_from_recorded_registry_results` and `test_memo_doi_ground_truth_against_recorded_raw_registry_answers` | read (test names; fixture contents not independently diffed against fresh Crossref) |
| Work order step 6 (abbreviated pages, "In:" venues, exit code 2) | present in code (`expand_pages`, venue filter, `return 2`) | read |
| Per-DOI worst-identity aggregation | present (`identity_counts`; rank WRONG_WORK > NOT_FOUND > AMBIGUOUS > SAME_WORK) | read |
| v2 notes: 31 SAME_WORK / 1 AMBIGUOUS / 7 WRONG_WORK / 3 NOT_FOUND | **not re-run by Claude** | reported |
| Full chunked package suite (8 chunks) | **not re-run by Claude** | reported |
| Online smoke test | **not run** | none |

The five wrong Memo DOIs are still wrong. They were verified fresh against Crossref on 2026-11-13 and listed in v4 section 3. Nothing changed in the registry facts.

## 3. Defects and limits found this round (none blocking)

1. **A table row with several DOIs for one reference gives all of them the same citation (limitation, not a regression).** Probe: `| Hjort & Poulsen (2019), *AER* | [paper](doi) · [data](doi) |` returns both DOIs with "Hjort & Poulsen (2019)". A dataset DOI is then compared with the paper's authors, and DataCite or Crossref would return different authors, so a legitimate dataset DOI can come out WRONG_WORK. The Memo has no such row; other notes were not checked. Also, markup leaks into one of the two citations (`Hjort & Poulsen (2019), *AER`), so citation cleaning is inconsistent between the two DOIs. Suggested handling: document it as a known limit, and prefer `AMBIGUOUS` over `WRONG_WORK` when one row carries more than one DOI. This is small and can follow the merge.
2. **Dead code.** `check()` returns rows without a `kind` key, so `identity_counts` always falls back to the `startswith("10.")` test. Counts are right today (arXiv rows are rewritten to a 10.48550 DOI), but the `kind` branch never fires. Either carry `kind` through or delete the branch.
3. **Cosmetic: `reference-checker-v4-diff.md` shows `?` where an arrow should be** (54 question marks, no U+FFFD, so the file is clean UTF-8 and the arrows were lost at generation). Regenerate with UTF-8 stdout. The Memo section's counts and DOI list are correct (checked against `v4-final.json`).
4. **Surname test is fragile for multi-word surnames** (`sorted(first_cited)[-1]` takes the alphabetically last token, not the last name). The failure direction is safe: it falls to `AMBIGUOUS`, not `WRONG_WORK`. Note for the next edit of `compare()`, no change needed now.

## 4. Remaining risks (carried from v4, unchanged, not for this pass)

- `SAME_WORK` needs only a first-author match even with an unrelated title. Proposed for the future gate, needing Aaron's confirmation: `SAME_WORK` with `TITLE_DIFFERS` below 0.5 goes to human review, never an automatic pass.
- Title-search fallback sends up to 200 characters to Crossref for identifier-free references (documented, not opt-in).
- `--offline` ignores stale 404 cache entries.
- Coverage counts DOI strings only; references with no DOI or URL are not counted.

## 5. Landing and next steps

1. **Before merge (optional, small):** Codex regenerates the v4 diff with UTF-8 output (item 3) and adds the known-limit note for item 1. Claude suggests merging without waiting for item 2 or 4.
2. **Merge:** `codex/reference-checker` to `main` by the integrator. Claude does not merge Codex's branch.
3. **Aaron:** five Memo DOIs need replacing (v4 section 3 lists them; replacement candidates are unverified). Claude has not edited the Memo.
4. **Not started and not requested:** gate placement (inferred from filenames; evidence-map design docs never read), the interactive review artifact for `AMBIGUOUS` rows (design decided, not built), any pipeline or CI wiring, any LLM use.

## 6. Sources

- Checker and tests: `C:\Users\theaa\ai-sandbox-master\.worktrees\codex-reference-checker\ai-sandbox\academic-rag-model\tools\reference_checker.py` and `...\tests\tools\test_reference_checker.py`
- Reports: `...\academic-rag-model\.reference_checker_reports\Literature Gap Memo - v4-final.json` and `reference-checker-v4-diff.md`
- Earlier handoffs: same folder as this file, `... - v1.md` to `... - v4.md`.
