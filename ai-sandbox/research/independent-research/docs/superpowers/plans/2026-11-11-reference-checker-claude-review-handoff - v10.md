# Handoff to Codex: AUTHOR_YEAR tier and same-team guard (v10)

From: Claude, 2026-11-16. To: Codex.
State: the review ledger (`tools/reference_review.py`, v9) is on `main`. Memo v2 is merged (PR #37, `44eecde3`) and raised: the main-checkout ledger holds 21 items (2 accepted, 19 deferred after Aaron's first review). Claude publishes the review page and syncs it; its source is `tools/reference_review_page.html` (committed with this handoff, not imported by any code).
Scope: implement the decision in `research\independent-research\docs\superpowers\plans\2026-11-14-reference-checker-identity-tiers-decision - v3.md` (read it first; not reopened). Start from current `origin/main` in a new per-task worktree.

## 1. Rule to implement

New tier **AUTHOR_YEAR**: passes without a human, like CONFIRMED, but reported separately. A SAME_WORK row gets it only when all hold, otherwise it stays PLAUSIBLE:
1. no title (citation or linking pass);
2. every cited surname is in the registered author list (for "et al.", the cited first surname is the registered first author);
3. cited year equals a registered year exactly;
4. registration agency is Crossref;
5. the same-team guard (section 2) completed and found no sibling.

Rank: CONFIRMED 0, AUTHOR_YEAR 1, PLAUSIBLE 2, then the existing order shifted by one. Define the rank once in `reference_checker.py` and import it in `reference_review.py` (removes the duplicated `TIER_RANK` from v9's review). Update the module docstring's tier mapping.

## 2. Same-team guard

- Request through `RegistryClient.get` (cache, retries): `https://api.crossref.org/works?query.author=<up to 4 registered author names, space-joined>&filter=from-pub-date:<y-1>-01-01,until-pub-date:<y+1>-12-31&rows=100&select=DOI,title,author,issued,type`.
- Sibling: first author family name (checker's `normalized`, last token) equals the registered first author's; DOI differs; `type` not in {dataset, peer-review, component, grant}; shares at least one co-author family name with the registered list when that list has more than one author; title `similarity` to the registered title < 0.5.
- Completeness: when `total-results` exceeds the page and the page still contains first-author matches near its end, follow Crossref's `cursor=*` paging up to 3 pages. Still unsettled: incomplete, the row stays PLAUSIBLE.
- Fail closed: lookup error, 429 after retries, or `--offline` without a cached answer keeps PLAUSIBLE. Claude's probe hit 429 after four quick `rows=100` queries at the client's 0.2 s pace: pace these queries at 1 s or more and honour `Retry-After`.
- Store up to 5 siblings on the row as `siblings: [{doi, title, year, type}]` and say so in `reason` (for example "same team: 3 other works 2007 to 2009"). The ledger copies `siblings` into the item's candidate so the page can show them.
- Document the new outbound data (registered family names and a year range to Crossref) next to the existing note on what is sent.

## 3. Ledger

AUTHOR_YEAR is not queued. On the next `raise`, items whose rows now pass drop out of `review.json` (existing behaviour for items no longer current); keep that, and add a test for a deferred item dropping.

## 4. Tests (offline, recorded Crossref answers; expected values from the cases, not tool output)

1. All cited authors, exact year, no siblings: AUTHOR_YEAR.
2. Same-team sibling (record Brok et al. 2008, `10.1093/ije/dyn188`): PLAUSIBLE with siblings listed.
3. Another version of the same paper (Maystadt SSRN "Extreme Weather and Civil War in Somalia ..." against `10.1093/ajae/aau010`): ignored, AUTHOR_YEAR.
4. Same surname, different people (Hjort 2021 search noise): ignored because no co-author is shared.
5. Single author with other works in range (Allcott 2015): PLAUSIBLE.
6. Cited year one off a registered year: PLAUSIBLE.
7. A cited co-author missing from the registered list: PLAUSIBLE.
8. Incomplete result set, lookup failure, offline without cache: PLAUSIBLE.
9. DataCite DOI: PLAUSIBLE.
10. Ledger: AUTHOR_YEAR not queued; a previously deferred item drops; rank imported from the checker.

## 5. Acceptance run (report; do not tune to it)

Re-raise the five notes in the main checkout's ledger (`RQ1 v4`, `RQ2 v4`, `RQ3 v5`, `Summary v3`, `Literature Gap Memo - v2`). Claude's hand probe (decision v3, Evidence) expects 9 PLAUSIBLE to become AUTHOR_YEAR, 5 to stay with siblings (Allcott, Vivalt and Coville, Groh, Raleigh, Brok), and Butler and Broockman plus Harari and La Ferrara to depend on paging. Report each row's result and any difference from that probe with the Crossref facts. Rule 2 (all cited surnames) was not part of the probe, so differences there are expected findings, not failures.

## 6. Out of scope

Titled rows (CONFIRMED and REVIEW rules unchanged, including Rosenzweig and Udry and Lopez), the review page (Claude syncs it), the claim check, any LLM call, editing notes.

## 7. Reporting back

Per step: commit hash, tests passed and skipped, evidence type (fixture, cached registry, fresh registry), and what was not run. One commit per step: rank and tier constant; guard query with tests; tier rule; ledger; acceptance run. Report before landing; do not push to `main` yourself.
