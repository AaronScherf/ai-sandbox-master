# Handoff to Codex: wrong-title decision and invented-title check (v12)

From: Claude, 2026-11-18. To: Codex.
State: AUTHOR_YEAR and the OpenAlex guard landed (`49d6a703`). Aaron reviewed the remaining 10 items: 8 accepted, 2 declined as "wrong paper". Those two (Rosenzweig and Udry in `RQ3 Transfer - v5.md`, `10.1093/restud/rdz021`; Lopez et al. in `RQ1 Knowledge Audit - v4.md`, `10.1016/j.wace.2018.03.006`) are not wrong papers: authors, year, journal and DOI are right, and the title in the note does not exist. Claude searched Crossref (`query.bibliographic` plus `query.author`) and OpenAlex (`search`) on 2026-11-18: neither cited title was found; the nearest hits were the registry titles (and, for Rosenzweig and Udry, the 2016 NBER and SSRN versions titled "External Validity in a Stochastic World"). Aaron found the same by hand. Claude then rewrote the `reason` of those two `defects.json` entries by hand, through `save_defects`, because "WRONG_WORK: wrong work" would lead a fixer to replace a correct DOI.
Scope: two changes, below. Start from current `origin/main` in a new worktree. Report before landing.

## 1. A "title wrong, DOI right" decision

- `reject(item_id, reason)`: add `wrong_title` to the allowed reasons. It marks the item declined and writes a per-note defect `{note, doi, tier: "TITLE_WRONG", reason, mentions, source: "human", registry_title}`, where `reason` says the DOI is correct and names the registered title to use. It does not carry across notes (same as `wrong_work`).
- `apply_decisions`: accept `{action: "decline", chosen: "wrong_title"}`; `reject_reason_matches` covers it.
- `wrong_work` keeps its meaning: the DOI points at a different work.
- Migration: convert the two hand-annotated entries above from `tier: "WRONG_WORK"` to `TITLE_WRONG` with `registry_title` set. Do it with a small, tested function (`relabel_defect`) run once, not by hand, and record the run in the acceptance report.
- Page: add a fifth button "Title wrong, DOI right" to `tools/reference_review_page.html`, sending `{action: "decline", chosen: "wrong_title"}`, with a footer line explaining it. Claude publishes the page after landing.

## 2. Invented-title check in the checker

When a row is SAME_WORK, the citation has a title, and the title scores below 0.5 against the registry (today these become REVIEW), search for the cited title itself before tiering:
- Crossref: `works?query.bibliographic=<cited title>&query.author=<cited surnames>&rows=5&select=DOI,title,author,issued`.
- OpenAlex: `works?search=<cited title>&per-page=5&select=doi,title,publication_year,authorships`.
- Found: any result whose title scores >= 0.92 against the cited title. Record it as `cited_title_found: {doi, title, year, source}`. The row stays REVIEW: the note may mean that other work (a working-paper version or a different paper), and the page shows it.
- Not found in both sources, with both answers complete and successful: set `text_fidelity` to include `TITLE_NOT_FOUND` and give the row tier **TITLE_WRONG**. The checker writes it to the defects list, not the review queue, with `reason` "cited title not found in Crossref or OpenAlex; DOI and authors match; use the registered title" and `registry_title`.
- Fail closed: any lookup error, rate limit, or offline miss leaves the row REVIEW with reason "title search unavailable".
- Rank: TITLE_WRONG sits with the defects (above REVIEW, below NOT_FOUND). Update the shared `TIER_RANK` and docstring.
- Outbound data: the cited title (cap at 200 characters, as the existing title-search fallback) and cited surnames, to Crossref and OpenAlex. Document it next to the other outbound notes.
- Pace and cache through `RegistryClient` like the guard queries.

## 3. Tests (offline, recorded answers; expected values from the cases, not tool output)

1. `reject(..., "wrong_title")` writes a TITLE_WRONG defect with `registry_title`, marks the item declined, does not carry to another note; `apply_decisions` accepts it and is idempotent.
2. `relabel_defect` converts a hand-annotated WRONG_WORK defect and is idempotent.
3. Rosenzweig and Udry and Lopez et al.: recorded searches find nothing, so TITLE_WRONG defect, not queued.
4. A cited title that exists as another work (record the Rosenzweig and Udry NBER version `10.3386/w22449` cited under its own title against the REStud DOI): REVIEW with `cited_title_found`.
5. A lookup failure in either source: REVIEW, "title search unavailable".
6. Rows at title score >= 0.5 and title-less rows are not searched.

## 4. Acceptance run (report; do not tune to it)

Run the checker, not the ledger, on the five notes (`RQ1 v4`, `RQ2 v4`, `RQ3 v5`, `Summary v3`, `Literature Gap Memo - v2`) with fresh lookups, and report every row that reaches the title search, with its result. Expected: Rosenzweig and Udry and Lopez et al. become TITLE_WRONG. Brown et al. (`10.1257/pandp.20251021`, title score 0.37, accepted by Aaron as same work) also reaches the search; report what it finds either way. Then raise the five notes in the worktree's own ledger copy only; do not touch the main checkout's ledger (Claude re-raises it after landing).

## 5. Out of scope

Gate wiring (separate decision pending with Aaron), editing notes (Gemini or Aaron fix the two titles), the claim check, any LLM call.

## 6. Reporting back

Per step: commit hash, tests passed and skipped, evidence type, what was not run. One commit per step: wrong_title decision and migration; page button; title search; tier and ledger routing; acceptance run.
