# Handoff to Codex: optional reference check in literature discovery (v15.1)

From: Claude, 2026-11-27. To: Codex. Aaron approved this on 2026-11-27.

This replaces [v15](2026-11-11-reference-checker-claude-review-handoff%20-%20v15.md), which was never started. Build from this file only. v15 predates v18, so it fetched citations that have no title (AUTHOR_YEAR) and bare DOIs. Since v18, the project's rule is that a name, year and DOI alone don't show which work was meant: Gemini has invented DOIs and attached real but unrelated papers to them. A list copied from a note must name each work before anything is downloaded.

Start from the latest `origin/main` in a new worktree on the branch `codex/discovery-check-references`. Run `python -m tools.active_work` from `ai-sandbox/academic-rag-model/` before you start and again before you ask to land. Report back before landing.

## 1. Why

`discovery/discover_journal_articles/fetch_dois.py` (Route 4) fetches exactly the DOIs it is given. Those lists are often copied from agent-written notes, and the novelty-check notes are where this project found 13 of 38 DOIs pointing at the wrong paper. Today an invented DOI downloads a real but unrelated paper. The paper then gets a sidecar, a manifest entry and, through `run_all`, an index card, and gets cited as evidence.

`discover.py` and `snowball.py` take DOIs from OpenAlex itself, so the expected yield there is low. The check still compares each OpenAlex record against the registry that issued its DOI, which catches the occasional record whose DOI and title don't match.

## 2. Behaviour

Add the flag `--check-references` to `fetch_dois`, `discover`, `snowball` and `run_all` (which passes it through). It is off by default. With it off, behaviour must be byte-identical to today: the owner's own deliberate DOI lists keep working unchanged.

**Citation text to check.** Reuse the checker's own JSON-input path (`{citation, identifier}`) instead of building a second parser:
- **`fetch_dois`:** the DOI's `#` label from `--doi-file` (see `parse_doi_text`). A list taken from a note carries "Author (Year). Title. Venue" there.
- **`discover` and `snowball`:** a citation built from the OpenAlex work's authors, year, title and venue.

**Strict mode.** Judge each citation the way `reference_review`'s strict mode does: a citation with no title is TITLE_MISSING, not AUTHOR_YEAR. Use the checker's own functions for this (`tools.reference_checker.check` plus the same `_cited_title` test that `reference_review._selected` applies). Don't add a second title rule. If that logic can only be reached through private helpers, add one small public function to `tools/reference_checker.py` that returns the strict tier for a single `{citation, identifier}` row, and use it in both places.

**What happens to each DOI,** decided before any download:

| Strict checker result | Action | Report outcome |
|---|---|---|
| CONFIRMED, DESCRIBED | fetch as today | unchanged, plus `checked` |
| NOT_FOUND, WRONG_WORK, TITLE_WRONG | don't fetch; no manifest entry | `reference_defect`, with tier and registry title |
| TITLE_MISSING (label without a title, including AUTHOR_YEAR) | don't fetch; no manifest entry | `reference_held`, reason "no title: name the work" |
| Bare DOI (no label at all) | don't fetch; no manifest entry | `reference_held`, reason "no citation text: name the work" |
| REVIEW, PLAUSIBLE, AMBIGUOUS, UNRESOLVED, UNCHECKED | don't fetch; no manifest entry | `reference_held`, with reason |
| OpenAlex work with no DOI | fetch | `no_doi_unchecked` |

Changes from v15:
- AUTHOR_YEAR is no longer fetched.
- A bare DOI is held instead of fetched as `registered_only`. That outcome no longer exists.
- With the flag on, a DOI is fetched only when its citation names a work the registry confirms. To fetch an unlabelled list on purpose, run without the flag.

Not writing a manifest entry for a held DOI is deliberate. The next run checks it again, so it is never mistaken for `seen`.

**Human review route.** When any DOI is held or defective, write `.discovery/reference_check.md` next to `doi_fetch_report.md`, with one line per DOI: the citation text (or "(no citation text)") followed by its `https://doi.org/...` link. Then `python -m tools.reference_review raise <that file>` turns those rows into ordinary review items and defects on the existing review page, with no new review surface. The report's footer prints that command.
- Check that `raise` reads the file as one item or defect per DOI. If the checker's parser needs a different line shape, use a shape it already reads; don't change the parser.
- Check that `raise` accepts the file's path. `articles_dir` sits inside the monorepo, so `reference_review._note_path` should key it relative to the monorepo root. If it doesn't, report it rather than working around it.

**`--dry-run` together with `--check-references`** runs the check and the report but writes nothing, not even `reference_check.md`.

**Data sent:** only what the checker already sends (see its README, "Data sent to outside services"). Don't pass `OPENALEX_CONTACT_EMAIL` or any user identifier to the checker's client. Use the shared checker cache (`DEFAULT_CACHE`).

## 3. Tests (recorded answers only, no network)

1. With the flag off, an existing `fetch_dois` fixture run gives identical results and an identical report, including for bare and title-less labels.
2. `fetch_dois --check-references`, one test per row of the table:
   - a labelled DOI whose label names a different paper ends as `reference_defect`, with no download and no manifest entry;
   - a labelled DOI whose title matches its label is fetched and marked `checked`;
   - a label giving authors and year but no title ends as `reference_held` with "no title", even though the plain checker would call it AUTHOR_YEAR;
   - a bare registered DOI ends as `reference_held` with "no citation text";
   - a bare unregistered DOI is also held, and is not fetched;
   - a label with a low title score (REVIEW) is held.
3. `reference_check.md` lists every held or defective DOI, and `reference_review raise` on it (using a temporary store) gives one item or defect per DOI.
4. `discover --check-references`:
   - an OpenAlex work whose DOI's registry title disagrees is held or marked defective;
   - a matching work is fetched;
   - a work with no DOI is fetched as `no_doi_unchecked`.
5. `run_all` passes the flag through.
6. A dry run with the flag writes no files.
7. The strict tier for one row agrees with `reference_review`'s strict result for the same citation in a note. One shared function means one rule.

## 4. Acceptance (report; don't tune)

1. The focused discovery suite and the checker and review suites pass. Report the counts.
2. Live, at no cost and with no download: build a DOI file from the reference list of `notes/00_overview-and-strategy/03_novelty-check/Novelty Check - RQ1 Knowledge Audit - v4.md`, one line per DOI, labelled with the citation's full text. Run `fetch_dois --dry-run --check-references` on it.
   - Expected for v4: Brown and Lopez come back `reference_defect` TITLE_WRONG, and the other nine DOIs come back `checked`.
   - Then build the same file from v5; all eleven should come back `checked`.
   - Claude confirmed both expectations on 2026-11-27 with the strict note check (`reference_review` strict mode on a copy of the ledger).
3. Live, same conditions: take the v5 file and cut three labels down to "Author (Year)", and strip one label entirely. Expected: those four come back `reference_held`, with the reasons from the table, and the other seven come back `checked`.
4. The README has a short "Reference check" subsection under "Route 4: Fetch an explicit DOI list", and a one-line mention under Step 2 (Route 1, `discover`) and under "Route 3: Citation snowball sampling". The subsection says that with the flag on, a DOI is fetched only when its citation names a work the registry confirms.

## 5. Out of scope

- Making the flag the default.
- Checking papers that are already fetched (`tools.audit_metadata` covers PDF-to-metadata identity).
- Any change to the ledger or the review page.
- Changes to the checker beyond the one optional public strict-tier function in section 2.
- Claim support: whether the paper supports what the note says is the separate to-do "Claim Support Check".

## 6. Reporting back

Report:
- the branch and commit;
- the `land_branch check` change ID, paths, overlaps and test counts;
- the acceptance outputs from section 4, items 2 and 3, as tables of DOI label (shortened), outcome and tier;
- whether you added the public strict-tier function, and its signature;
- anything in this handoff you changed or think is wrong.

Don't land; the owner approves each change ID.
