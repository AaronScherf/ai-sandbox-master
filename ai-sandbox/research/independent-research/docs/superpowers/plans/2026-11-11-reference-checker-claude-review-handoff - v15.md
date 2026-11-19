# Handoff to Codex: optional reference check in literature discovery (v15)

From: Claude, 2026-11-18. To: Codex. Aaron approved adding this.
Independent of v14. Both edit different files (`tools/reference_review.py` versus `discovery/`), so they can run in parallel on separate branches. If you do both, land v14 first. Start from current `origin/main` in a new worktree, run `tools.active_work` before you start and again before you ask to land, and report back before landing.

## 1. Why

`discovery/discover_journal_articles/fetch_dois.py` (Route 4) fetches exactly the DOIs it is given. Those lists are often copied from agent-written notes, and the novelty-check notes are where this project found 13 of 38 DOIs pointing at the wrong paper. An invented DOI today downloads a real but unrelated paper, which then gets a sidecar, a manifest entry and, through `run_all`, an index card. That paper is then cited as evidence.

`discover.py` and `snowball.py` take DOIs from OpenAlex itself, so the expected yield there is low. The check still cross-checks OpenAlex against the registry that issued the DOI, which catches the occasional OpenAlex record whose DOI and title do not match.

## 2. Behaviour

Add the flag `--check-references` to `fetch_dois`, `discover`, `snowball` and `run_all` (which passes it through). It is off by default; with it off, behaviour must be byte-identical to today.

**Citation text to check** (reuse the checker's own JSON-input path, `{citation, identifier}`, instead of building a second parser):
- **`fetch_dois`:** the DOI's `#` label from `--doi-file`, which is where a list taken from a note carries "Author (Year). Title. Venue". A bare DOI with no label can only be checked for registration.
- **`discover` and `snowball`:** a citation assembled from the OpenAlex work: authors, year, title and venue.

**Routing per DOI,** before any download:

| Checker result | Action | Report outcome |
|---|---|---|
| CONFIRMED, AUTHOR_YEAR | fetch as today | unchanged, plus `checked` |
| NOT_FOUND, WRONG_WORK, TITLE_WRONG | do not fetch; no manifest entry | `reference_defect` with tier and registry title |
| REVIEW, PLAUSIBLE, AMBIGUOUS, UNRESOLVED, UNCHECKED | do not fetch; no manifest entry | `reference_held` with reason |
| Bare DOI (no label) that is registered | fetch | `registered_only` |
| OpenAlex work with no DOI | fetch | `no_doi_unchecked` |

Not writing a manifest entry for a held DOI is deliberate. The next run re-checks it, so it is never mistaken for `seen`.

**Human review route.** When any DOI is held or defective, write `.discovery/reference_check.md` beside `doi_fetch_report.md`, with one line per DOI: the citation text followed by its `https://doi.org/...` link. The point is that `python -m tools.reference_review raise <that file>` turns the held rows into ordinary review items on the existing review page, with no new review surface. The report's footer prints that command. Verify that `raise` parses the file with one item per DOI; if the checker's parser needs a different line shape, choose the shape it already reads rather than changing the parser.

**`--dry-run` together with `--check-references`** runs the check and reports, but writes nothing, not even `reference_check.md`.

**Data sent:** only what the checker already sends (see its README, "Data sent to outside services"). Do not pass `OPENALEX_CONTACT_EMAIL` or any user identifier to the checker's client. Use the shared checker cache.

## 3. Tests (recorded answers only, no network)

1. With the flag off, an existing `fetch_dois` fixture run produces identical results and report.
2. `fetch_dois --check-references`: a labelled DOI whose label names a different paper ends as `reference_defect`, with no download and no manifest entry.
3. A labelled DOI that matches its label is fetched and marked `checked`.
4. A label with a low title score is held, and `reference_check.md` lists it in a shape `reference_review raise` reads as one item.
5. A bare registered DOI ends as `registered_only` and is fetched; a bare unregistered DOI ends as `reference_defect` NOT_FOUND.
6. `discover --check-references`: an OpenAlex work whose DOI's registry title disagrees is held; a matching work is fetched; a work with no DOI is fetched as `no_doi_unchecked`.
7. `run_all` passes the flag through.
8. Dry run with the flag writes no files.

## 4. Acceptance (report; do not tune)

1. The focused discovery suite and checker suite pass, with counts.
2. Live, at no cost and with no download: run `fetch_dois --dry-run --check-references` on a DOI file built from the reference list of `Novelty Check - RQ1 Knowledge Audit - v4.md`, labelled with each citation's text. Expected: Brown and Lopez come back as `reference_defect` TITLE_WRONG, and the other nine DOIs as `checked`. Then run it on the same list taken from v5, where all eleven should be `checked`. Report both.
3. The README has a short "Reference check" subsection under Route 4 and a one-line mention in Route 1 and Route 3.

## 5. Out of scope

Making the flag the default. Checking already-fetched papers (`tools.audit_metadata` covers PDF-to-metadata identity). Any change to the checker or the ledger. The review page.

## 6. Reporting back

Per step: commit hash, tests passed and skipped, evidence type, and what was not run. Then the formal `land_branch check` result and the change ID.
