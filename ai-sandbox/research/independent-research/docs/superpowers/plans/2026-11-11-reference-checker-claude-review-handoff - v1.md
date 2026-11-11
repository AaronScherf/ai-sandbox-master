# Handoff to Codex: reference checker review, round 1 (v1)

From: Claude review session, 2026-11-11.
To: the Codex session on `codex/reference-checker` (worktree `.worktrees/codex-reference-checker`).
Scope of this document: findings and a work order. Claude changed no Codex files, no Gemini notes and no pipeline code.

Inputs reviewed:
- `ai-sandbox/academic-rag-model/tools/reference_checker.py`, its test file and `fixtures/reference_checker.json`.
- Your cached v1 outputs (`.reference_checker_cache/`).
- Claude's own online run of the checker on the three v2 notes (RQ1, RQ2, RQ3), using a scratch cache outside the repo. Only DOIs were sent to registries.
- The regression addendum `2026-11-11-reference-checker-regression-addendum.md`. It sits in the `codex-nexus-presentation-strategy-v3` worktree, not yours. Read it by absolute path:
  `C:\Users\theaa\ai-sandbox-master\.worktrees\codex-nexus-presentation-strategy-v3\ai-sandbox\research\independent-research\docs\superpowers\plans\2026-11-11-reference-checker-regression-addendum.md`
- Gemini's notes live in the `gemini-nexus-novelty-check` worktree under `notes/00_overview-and-strategy/Novelty Check - * - v1.md` and `v2.md`. Do not edit them.

## 1. What is verified

| Claim | Status |
|---|---|
| v1 counts (9 MATCH, 4 PARTIAL, 14 MISMATCH, 11 UNRESOLVED, 10 NO_IDENTIFIER) | Reproduced offline from your cache. |
| All 11 v1 UNRESOLVED rows are DOIs that doi.org reports as "DOI does not exist", with Crossref and DataCite both returning 404 | Verified in the cache. |
| Offline tests: 7 passed, 1 skipped | Reproduced. |
| Correct wrong-work detection (author differs): Allcott, Brok, Egger, Groh, Butler, Vivalt and Coville, Bongers | v2 run agrees with addendum rows 1-7. |
| Not-found DOIs: Hjort `aer.20191834`, DellaVigna-Pope-Vivalt Science, Pearl and Bareinboim | v2 run agrees with the addendum (UNRESOLVED today; see change 2). |
| Gemini's "44 verified, 0 unverified" is wrong | Checker disagrees, as the addendum requires. |

## 2. Defects, ranked

Rows 1-3 produce false accusations or hide real failures. Do these first.

1. **False MISMATCH from surname handling.**
   - Hotz 2005 (`10.1016/j.jeconom.2004.04.009`): Crossref `family` is "Joseph Hotz".
   - Montiel Olea 2024 (`10.48550/arXiv.2408.09187`): DataCite `familyName` is "Olea". The addendum expects MATCH and the checker says MISMATCH. This is a required case.
   - Cause: `compare()` tests the citation's first token against the record's first family token only.
   - White, Saran and Welch (`10.1002/cl2.1075`) shows the same brittleness. The record's first author is Saran, so first-author-only comparison cannot decide it.
2. **Title-only gaps are labeled MISMATCH, which reads as "wrong DOI".** Meager v1 (0.56), Brown `pandp.20251021` v2 (0.37), Lopez `wace.2018.03.006` v2 (0.44) and Barbrook-Johnson (0.39) have DOIs that resolve to the cited work. The note's title text is wrong or paraphrased. The addendum expects MATCH for Brown and Lopez; as written, the checker says MISMATCH.
3. **Silent extraction misses.**
   - Table rows and inline links are not extracted. The Correction Log has 51 DOI strings and yields 0 rows. The Literature Gap Memo (16) and Verification Review also yield 0.
   - `identifiers()` returns the first DOI on a line only. Multi-DOI bullets lose the rest. The v2 run found 42 DOI rows against the addendum's 43 distinct DOIs; the missing one is probably a multi-DOI line (assumption, not traced).
   - The exit code is 0 with an empty table.
4. **UNRESOLVED merges different situations.** "DOI does not exist", "not cached", network failure and "unsupported registration agency" (mEDRA, JaLC and others) share one label and one reason string. "DOI does not exist" is the strongest signal in the dataset.
5. **Year logic is online-date biased.** `registry_record` takes Crossref `published or issued`. `published` is the earlier of print and online, so Rosenzweig and Udry (online 2019, cited 2020), Tennant (online 2020, cited 2021) and Fenwick (online 2007, cited 2008) lean on the online year.
6. **Pacing is not enforced across rows.** `main` builds a new `RegistryClient` per row (`reference_checker.py:297`), so `last_request` resets.
7. **Cache hygiene.** Negative answers are cached forever with no `--refresh`. Writes are non-atomic. A corrupt file reports as "lookup unavailable" and never heals. Five Gemini-check report JSONs with a BOM sit in the cache directory. The `.gitignore` entry is uncommitted.
8. **Privacy gap, minor.** The title-search fallback `query = title or citation` (line 248) sends the whole citation string, which for JSON-string input can include prose. Cap it to the extracted title or the first 200 characters.
9. **Test gaps.** `FixtureClient` has no 404 path, so not-found, unsupported agency, retry, offline miss, corrupt cache, tables, multi-DOI lines and compound surnames are untested.

## 3. Where the addendum and this review disagree

Resolve these explicitly before coding. The first two are design decisions; Claude's recommendation is given.

- **Two questions, not one.** The addendum's ground truth is identity-level (does the DOI resolve to the cited work?). The checker also tests citation-text fidelity (is the title as the note states it?). Recommendation: report both. Identity: `SAME_WORK`, `WRONG_WORK`, `NOT_FOUND`, `UNRESOLVED`, `UNCHECKED`. Text fidelity: `OK`, `TITLE_DIFFERS`, `NO_TITLE`, `YEAR_DIFFERS`, `VENUE_DIFFERS`. Brown and Lopez then read `SAME_WORK` with `TITLE_DIFFERS`, which satisfies the addendum's "MATCH" at identity level without hiding that the note's title is invented.
- **Identity evidence should use author sets, not first author plus title.** Crossref and DataCite return full author lists. Count overlap of surname tokens between the citation text and all record authors (either direction, tokens, case and diacritics folded). That fixes Hotz, Olea and White/Saran/Welch, and lets Lopez and Brown resolve without relying on the title. Treat zero overlap as `WRONG_WORK`.
- **Year rule: the addendum contradicts itself.** It expects Gechter, Rosenzweig and Udry to match under a one-year tolerance, but expects Fenwick (2007 online vs 2008) to be PARTIAL "on year". Recommendation: collect all Crossref year fields (`published-online`, `published-print`, `issued`, `published`). Accept the citation year if it equals any. A one-year gap with none equal is `YEAR_DIFFERS` (note, not failure). More than one year is PARTIAL. Update the addendum's Fenwick expectation accordingly or document why not.
- **Author-year-only citations cannot earn MATCH today.** Most v2 RQ3 citations are labels like "Allcott (2015)", so the checker returns PARTIAL "no explicit title". The addendum lists about 20 expected MATCH rows. Investigate before changing anything: do the v2 notes carry full references elsewhere (a reference section) that `extract()` should prefer over the link label? That is not verified. If full citations exist, fix extraction. If not, keep `NO_TITLE` and do not promote.
- **Lopez malformed string.** The addendum asks that the quoted v1 error `10.1016/wace.2018.03.006` in a "what changed" line not become a separate reference. A cheap rule: skip DOI-like strings inside backticks on lines that contain "was", "changed", "→", "corrected" or "v1". Test with that line. If it proves fragile, exclude and record a count instead.
- **Books and entities.** Agree with the addendum: empty venue or volume on the record is never a difference (Barbrook-Johnson and Penn, Bowen et al.). Run `html.unescape` and Windows-1252 repair on record titles before comparing (also on the citation side; the notes contain `308�312` page corruption).

## 4. Work order for Codex (one commit per step, tests first)

Work only in `.worktrees/codex-reference-checker`. Offline tests must pass at every step. Do not edit the Gemini notes or review files.

1. **Regression fixtures from real records.** Add to `tests/tools/fixtures/` small offline records for Hotz, Montiel Olea (DataCite, Crossref 404), Meager, Brown 20251021, Lopez, White/Saran/Welch, a book with empty venue, and a title containing `&amp;`. Use registry-shaped JSON. Add a FixtureClient 404 path. Expected outcomes follow section 3.
2. **Author-set identity** (defect 1, 2). Add a `record["authors"]` list for both registries. Identity: `WRONG_WORK` iff the citation has surname tokens and zero overlap with any record author; title only breaks ties when the record has no authors. Keep MISMATCH as the label for `WRONG_WORK` for now so downstream consumers do not change this step.
3. **Status split** (defect 4). `NOT_FOUND` when doi.org says "DOI does not exist" and the registries 404. `UNRESOLVED` for network, offline-miss and corrupt cache. `UNSUPPORTED_AGENCY: <name>` for other registration agencies. Keep reason strings distinct.
4. **Title-only gaps** (defect 2). Move them to `TITLE_DIFFERS` under text fidelity; PARTIAL overall. Record the score. Do not tune the 0.3 or 0.6 thresholds further without more labeled rows; the current numbers come from about 60 rows.
5. **Year logic** (defect 5). See section 3.
6. **Extraction** (defect 3). Tables and inline links, one row per DOI with its own nearest citation text, multi-DOI bullets, the Lopez quoted-error rule. Add a coverage line to the report: "N DOI-like strings in source, M attached to references, K unattached", and exit 1 when K > 0.
7. **Housekeeping** (defects 6-8). One `RegistryClient` per run; atomic writes (write temp then replace); treat a corrupt cache entry as a miss; `--refresh` and a negative-cache TTL; cap the title-search query; add `.gitignore` for the cache; keep reports out of the cache directory.
8. **Rerun** the v2 notes and compare to the addendum's expected rows. The target is all 7 wrong-work and 3 not-found rows exactly right, Montiel Olea as a DataCite match, and no `WRONG_WORK` outside those 7. The two addendum rows that remain ambiguous (White/Saran/Welch and Lopez) should be reported, not forced.

## 5. Out of scope for this pass

- Wiring into any pipeline, the evidence-map flow or a CI gate.
- Any LLM call.
- Editing the Gemini notes.

## 6. Future gate (design only, for later)

- **Rule.** Identifiers and bibliographic metadata come from a registry or a source file. An LLM never types a DOI. It may emit a locator (title query), and a deterministic match plus a human choice selects the registry record. Display citations are rendered from the registry record, so a paraphrased title cannot persist. Claims carry a verbatim quote span that is substring-checked against stored source text. Where text cannot be stored (paywalled, public repo), store a hash and a short quote.
- **Limit.** A registry proves the work exists and is identified. It says nothing about whether the work supports the claim.
- **Placement.** At record creation in the study catalogue, and as a pre-merge check on LLM-authored notes. Not yet wired because the evidence-map design docs were not read by this review (filenames only).
- **Gate verdicts.** `SAME_WORK` with `OK` or `NO_TITLE` passes. `SAME_WORK` with `TITLE_DIFFERS` passes only after the registry title replaces the note's. `WRONG_WORK`, `NOT_FOUND` and unattached DOIs block pending a human decision. `UNRESOLVED` means retry and never counts as a pass.

## 7. Open questions for Aaron

- Confirm the identity vs text-fidelity split (section 3) before step 2.
- Confirm that author-year-only citations should stay `NO_TITLE` unless a fuller citation exists.
