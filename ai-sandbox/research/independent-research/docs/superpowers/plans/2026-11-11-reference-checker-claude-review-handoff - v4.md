# Handoff to Codex: reference checker review, round 3 (v4)

From: Claude review session, 2026-11-13.
To: the Codex session on `codex/reference-checker` (worktree `.worktrees/codex-reference-checker`).
Supersedes `... - v3.md` (v1 to v3 kept unchanged). Scope: findings, one correction to Claude's earlier expectation, and a work order. Claude changed no Codex files, no Gemini notes, and not the Literature Gap Memo.

Read the sources in section 7 by absolute path; this file lives on local `main`, not in your worktree.

## 0. Correction to v2 and v3

v2 and v3 (section 4, step 1) said the 16 Literature Gap Memo rows "must not return WRONG_WORK". That was overbroad: Claude had not checked those DOIs. The DOI-string-as-citation bug was real and is fixed. But **five of the Memo's nine distinct DOIs are genuinely wrong**, and WRONG_WORK is the correct label for them. Do not weaken that. The expected Memo results are in section 3.

Decisions from v3 section 6 stand and are not reopened: identity and `text_fidelity` stay separate; author-year-only citations stay `NO_TITLE`; `AMBIGUOUS` rows route to the review artifact (design only, not built).

## 1. Status of round 3

Reproduced by Claude: 39 passed, 1 skipped offline. Reports show, for the three v2 notes, 31 SAME_WORK, 7 WRONG_WORK, 3 NOT_FOUND, 1 AMBIGUOUS (White/Saran/Welch), 42 of 42 DOIs attached. Classification totals across the 42 DOIs: 21 MATCH, 11 PARTIAL, 7 MISMATCH, 3 NOT_FOUND.

Confirmed fixed since round 2: Mueller/Müller; Crossref organization `name`; unwritable cache; negative-cache expiry, `--refresh`, atomic replace and exit codes now tested; venue and pages artifacts gone from the v3 diff; identifier-only table citations; any-date year rule; `AMBIGUOUS` implemented.

Not re-run by Claude: the online smoke test.

## 2. Defects to fix (observed)

1. **Table cell selection can hide a wrong DOI (blocking).** In `extract()` the table branch takes the first cell whose text contains a year-like number (`YEAR.search(DOI.sub("", cell))`). In the Memo, the claim cell "Economywide CGE modeling of Sudan 2023 conflict disruptions" contains "2023", so the second Abushama mention gets that text as its citation and comes out `UNCHECKED`, although `10.2499/p15738coll2.137021` is wrong. Result: the DOI-level tally drops from 5 WRONG_WORK to 4, and `reference-checker-v3-diff.md` repeats the 4. Fix: prefer a cell matching an author-year pattern (`Name … (YYYY)`); fall back only if none; and aggregate per DOI using the worst identity (WRONG_WORK beats SAME_WORK beats UNCHECKED), reporting both mention and DOI counts.
2. **Several DOIs in one table row share one citation.** Reproduced with a synthetic row: a dataset DOI and a paper DOI both inherit "Hjort (2021)…", and the citation keeps link markup. A dataset DOI compared with a paper's authors would be flagged WRONG_WORK. The Memo has no such row; other notes were not checked. Fix: bind each DOI to its nearest preceding text, as the non-table branch does, and strip link markup from the citation.
3. **Journal name is read as the title.** For "Author (YYYY), *Journal* ([doi](url))" the segment after the year becomes the title. Four correct Memo mentions (Thalheimer, Harari, Maystadt, Raleigh) show `TITLE_DIFFERS` with scores 0.06 to 0.35. Identity is unaffected, but `text_fidelity` is wrong; expected is `NO_TITLE`. Fix: when the text after the year starts with a comma or an italic span and has no sentence break, treat it as venue, not title.
4. **Tests do not pin the Memo.** None of the five wrong DOIs appears in any fixture or test, and the expected labels for the 42 v2 rows equal the tool's own output (31/1/7/3), so only the recorded raw registry answers, the addendum's 10 rows and Montiel Olea are independent evidence. Add recorded raw registry answers (from your client, unedited) for the nine Memo DOIs and pin the section 3 expectations. Do not copy tool output into expected values; use the registry facts in section 3.

## 3. Memo ground truth (fresh Crossref and doi.org checks by Claude, 2026-11-13)

Wrong DOIs, expected `WRONG_WORK` / `MISMATCH` on every mention:

| Memo cites | DOI | Registry (Crossref) says |
|---|---|---|
| Marchiori, Maystadt, & Schumacher (2012) | 10.1016/j.jenvman.2012.03.046 | Lowe, "Improving the performance of power plant cooling ponds", J Environ Manage 2012 |
| McGuirk & Burke (2020) | 10.1086/709977 | Gallia, *Os columnatum* Again: Plautus *Miles Gloriosus* 211, Classical Philology 2020 |
| Flores (2024) | 10.1088/1748-9326/ad13b8 | Lee, Kim, Seo et al., global sea level in 2050, Environ Res Lett 2023 |
| Zens & Thalheimer (2025) | 10.1214/24-AOAS1921 | Zhang, Kuha, Steele, "Modelling correlation matrices in multivariate data…", Ann Appl Stat 2024 |
| Abushama, Resnick, Siddig, & Kirui (2023) | 10.2499/p15738coll2.137021 | Alderman, Gilligan, Hidrobo et al., "Men can cook…", 2023 |

Correct DOIs, expected `SAME_WORK` (and, after fix 3, `NO_TITLE`): `10.1016/j.gloenvcha.2023.102641` (Thalheimer, Schwarz, Pretis 2023), `10.1093/ajae/aau010` (Maystadt, Ecker 2014), `10.1162/rest_a_00730` (Harari, Ferrara 2018), `10.1016/j.gloenvcha.2015.03.005` (Raleigh, Choi, Kniveton 2015).

Expected counts after fixes 1 to 3: 18 mentions = 8 SAME_WORK, 8 WRONG_WORK, 2 UNCHECKED (the two URL rows: FAO/SIDA, ACLED EULA). By distinct DOI: 4 SAME_WORK, 5 WRONG_WORK, plus 2 URL entries. Report both views. Correct `reference-checker-v3-diff.md`'s Memo section in the same pass (a regenerated report, not a hand edit).

Do not edit the Memo and do not add replacement DOIs to it. Replacements are Aaron's call. Crossref bibliographic search returned two close candidates (unverified as replacements): Marchiori et al. `10.1016/j.jeem.2012.02.001` and Zens & Thalheimer `10.1214/24-aoas1959`. None returned for Flores or McGuirk & Burke JPE; the Abushama search was rate-limited and not completed.

## 4. Work order (tests first; one commit per step; offline tests green each step)

1. Fix 2.1 and 2.3 together with tests built from section 3 (recorded registry answers plus the Abushama double-mention case).
2. Fix 2.2 with a synthetic dataset-plus-paper table row test.
3. Per-DOI aggregation and mention-level plus DOI-level counts in the JSON and markdown report.
4. Regenerate `Literature Gap Memo - v3-final.json` as a new versioned report (`v4-final`) and regenerate the v3 diff as a v4 diff. Do not overwrite earlier reports.
5. Rerun the three v2 notes. Expected: 31/1/7/3 unchanged, and the four journal-as-title Memo mentions now `NO_TITLE`.
6. Small, any order: treat page ranges with abbreviated end pages (`1055–68`) as matching `1055-1068`; ignore "In:" chapter venues; give the coverage failure (unattached DOIs) a different exit code from `--exit-nonzero-on-findings`.

## 5. Remaining risks (not for this pass; do not build)

- `SAME_WORK` needs only a first-author match even with an unrelated title (crafted probe: title score 0.29 still SAME_WORK). 4 of the 31 real SAME_WORK rows have real title scores under 0.5 (Brown, Lopez, Montiel Olea, Rosenzweig and Udry). **Proposed for the future gate, needs Aaron's confirmation:** `SAME_WORK` with `TITLE_DIFFERS` below 0.5 goes to human review, never an automatic pass.
- Title-search fallback sends up to 200 characters to Crossref for identifier-free references; documented, not opt-in.
- `--offline` ignores stale 404 entries.
- Coverage counts DOI strings only; references with no DOI or URL are not counted.

## 6. Out of scope

Pipeline, evidence-map or CI wiring; the review artifact; any LLM call; editing the Gemini notes or the Memo; replacement DOIs.

## 7. Sources (absolute paths)

- Memo: `C:\Users\theaa\ai-sandbox-master\ai-sandbox\research\independent-research\notes\01_compound-shocks-panel\review-gate\Literature Gap Memo.md` (table rows 1 to 9; source list lines 291 to 296)
- Addendum: `C:\Users\theaa\ai-sandbox-master\.worktrees\codex-nexus-presentation-strategy-v3\ai-sandbox\research\independent-research\docs\superpowers\plans\2026-11-11-reference-checker-regression-addendum.md`
- Earlier handoffs: same folder as this file, `... - v1.md` to `... - v3.md`.
