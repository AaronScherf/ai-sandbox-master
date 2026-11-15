# Reference checker: real-note findings and the linking pass (v8)

From: Claude, 2026-11-15. To: Codex.
Context: tiers and linking pass landed on `main` (`ff3c914f`, includes v7). Claude then ran the checker on real notes to find a sample for the linking pass. Read-only; no checker code, notes or Memo changed. Evidence type for every number below: **fresh registry** (online run on 2026-11-15, DOIs only sent) unless stated.

## 1. Results on the latest Gemini novelty notes (clean)

| Note | DOIs attached | Tiers (mentions) |
|---|---|---|
| RQ1 Knowledge Audit v4 | 11 of 11 | 9 CONFIRMED, 2 REVIEW (Brown; Lopez, both correct citations with low title scores), 4 UNCHECKED URL rows |
| RQ2 Decision Space v4 | 8 of 8 | 8 CONFIRMED, 5 UNCHECKED URL rows |
| RQ3 Transfer v5 | 23 of 23 | 21 CONFIRMED, 2 REVIEW (Rosenzweig and Udry; White, Saran and Welch) |

No WRONG_WORK or NOT_FOUND in the latest versions: the correction rounds worked. Every row carries its own title, so every `evidence` value is `title_in_citation`.

## 2. The linking pass still has no real sample

Scanned every note under `research/independent-research` (excluding processed outputs and journal articles) for title-less DOI rows alongside a titled reference list: 27 files have title-less DOI rows, **none has titled list entries**. The linking pass is correct on synthetic tests and unused on the real corpus. Keep it; do not extend it until a real case exists.

## 3. Defects found on real notes (these matter more than linking)

1. **False NOT_FOUND on a parenthesized DOI (blocking).** `notes/01_compound-shocks-panel/literature_review.md` contains `[https://doi.org/10.31499/2616-5236.2(28).2024.300402](...)`. The checker extracts `10.31499/2616-5236.2(28` (truncated at the first `)` of the markdown link target), the registry says "does not exist", and the row is NOT_FOUND. The real DOI is registered: doi.org says Crossref, and Crossref returns 200 for it. Coverage correctly flagged it unattached (exit 2), but a false NOT_FOUND is a false accusation. Fix the markdown link pattern to allow balanced parentheses in the target; add a test with this exact link and with a SICI-style DOI inside a link.
2. **Every DOI in four `literature_review.md` files is UNCHECKED, so nothing is verified (15, 15, 15 and 13 DOIs; 58 in all).** These notes use entry blocks: a heading or quoted reference line, then a `DOI / Link:` bullet. The row's citation is the bare URL, so there is no author or title to compare. Files: `notes/01_compound-shocks-panel/literature_review.md`, and `projects/{systems-dynamics,data-fusion-toolkit,transferability}/literature_review.md`. Likely fix, subject to what the blocks actually look like (read three entries first): bind each `DOI / Link` bullet to its entry's heading and any blockquoted reference line above or below it, and use that text as the citation.
3. **`Author (YYYY, *Journal*, vol(issue): pages)` is not parsed (10 DOIs in `Novelty Check - Summary - v3.md`).** The year pattern requires `(YYYY)`; with a comma after the year the cited authors come out empty and every row is UNCHECKED. Rows are also truncated (`Broockman (2011, *AJPS*, DOI`), which looks like a second parsing issue in the same lines. Allow `YYYY` followed by `,` or `;` inside the parentheses, and take the author block from the full text before the parenthesis, not the link label.

## 4. Work order (tests first; one commit per step; offline tests green)

1. Defect 3.1, with the two tests above and a regression check that the Claxton SICI fixture still passes.
2. Defect 3.3, with a test built from three real `Summary v3` lines. Expected: those rows produce an identity (SAME_WORK or WRONG_WORK per the registry), not UNCHECKED. Do not copy tool output into expected values; check each against Crossref.
3. Defect 3.2: read the entry blocks in the four literature reviews, then propose the binding rule to Claude before implementing if the blocks are not uniform.
4. Rerun the six files above online and report tiers and any WRONG_WORK, NOT_FOUND or REVIEW rows with the registry facts. Report every row that is still UNCHECKED and why.

## 5. Out of scope

Review ledger and artifact, any LLM call, editing notes or the Memo, replacement DOIs, extending the linking pass.
