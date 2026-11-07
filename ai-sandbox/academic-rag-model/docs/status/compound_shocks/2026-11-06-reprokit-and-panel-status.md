# Compound shocks panel and reprokit: status as of 2026-11-06

Project 02 builds a district-month panel for Somalia and Sudan (conflict, rainfall, food prices, displacement). `reprokit` is the
reproducibility framework and project template it uses. Both are **separate Git repositories**, git-ignored by this monorepo and
kept at `ai-sandbox/research/independent-research/projects/compound-shocks-panel/` and `.../reprokit/` (moved here on 2026-11-06).
URLs and pinned commits are in `projects/repositories.json`. The older `projects/02_compound_shocks/` folder is a superseded
placeholder and is not touched.

## Where things stand

| Item | State |
| --- | --- |
| reprokit | `main` = `1df3791`, tag **v0.3.2** (tags v0.3.0, v0.3.1, v0.3.2 all reachable from `main`); CI green on Ubuntu and Windows; 131 tests |
| compound-shocks-panel | `main` = `2e1c84b`, pins `reprokit@v0.3.2`; CI green; 199 tests (Windows) |
| Real-data rerun, 2026-11-06 | Somalia `panel.csv` `785f6c1d`, aggregates `d7ff4f77`; Sudan `panel.csv` `ff16c5bc`, aggregates `d3030e1b`. All match the recorded hashes. Somalia 4 min 4 s, Sudan 13 min 48 s (about 90% is the rainfall step) |
| Fresh project from the v0.3.2 tag | Quick check, `validate` and `pytest` pass; the generated CI passed on Ubuntu and Windows in a throwaway private repo (since deleted) |
| Branches | All `codex/*` branches in both repos merged and deleted (local and GitHub). Only `main` plus tags remain |

## What was built this session

**reprokit**
- **v0.3.0:** descriptor and charter schema 0.2.0; `reprokit quick-check` (a made-up-data self-test with plain PASS and FAIL text); `RUN_SUMMARY.md`
  (row counts, time, memory, file checksums); a plain-language template README for non-developers; Windows added to CI.
- **v0.3.1:** fixes for Windows line endings. Git's `core.autocrlf` rewrote LF to CRLF in committed fixtures and changed their SHA-256. The
  template now ships a `.gitattributes` (`data/**` and `tests/**` data files marked `-text`), and a checksum mismatch that is only CRLF is
  explained in plain words.
- **v0.3.2:** `reprokit.env.load_project_env(root)` reads a project `.env` (UTF-8 BOM accepted, `export` lines skipped, real environment variables win,
  values never logged); template guidance for multi-source `fetch` (try every source, report each failure, exit non-zero, never overwrite a raw file, document a
  manual fallback); `reprokit validate` warns (exit code unchanged) when an `account_required` or `request_required` source has no README guidance.

**compound-shocks-panel**
- Line endings: `.gitattributes` (`*.py`, `*.yaml`, `*.csv`, `*.geojson` as `text eol=lf`; `*.xlsx`, `*.tif` as `-text`) and `tests/test_fixture_bytes.py`, which pins the fixture hashes.
- Adopted reprokit: `project.yaml` schema 0.2.0, root `quick_check.py` (runs the real `reproduce` on committed fixtures; about 6 s), `run_metrics.py`, `RUN_SUMMARY.md` per run.
- Licence fields: the five placeholder `reuse_terms` are written (see below). README units and period restored (Somalia 74 districts, Sudan 189 localities, 2021-01 to 2025-10, 58 months).
- Accounts and keys: `.env` loading, `.env.example`, README section.
- **ACLED now downloads through `fetch`** (`fetch --instance <name>`), saving to the git-ignored `data/raw/conflict_events/` with a `.fetch.json` record, printing only counts and a short hash. Verified on 2026-11-06: Somalia 18,789 events and Sudan 23,441 events, event-ID sets **identical** to the manual exports (no differences either way); the Somalia pipeline run on the API file alone reproduced the recorded hashes. The manual export still works. The manual export repeats an event once per actor row (35,757 rows for 18,789 Somalia events); the adapter already de-duplicates.
- `fetch` keeps going when one source fails (for example, no ACLED login), reports each failure, and exits 1 at the end.

## Licence and data-use state

| Source | Terms | Status |
| --- | --- | --- |
| PRMN displacement, Sudan population (COD-PS) | CC BY | recorded |
| CHIRPS | public domain per the Climate Hazards Center page | recorded; the Funk et al. 2015 citation (doi:10.1038/sdata.2015.66) was written from memory, **check it** |
| Sudan DTM displacement | HDX "Other": non-commercial use only; no redistribution or derivative works; credit line required. DTM website terms add that extraction, reproduction and distribution need IOM's prior written permission | Aaron's reading is that non-commercial student research is allowed; **IOM permission request drafted, Aaron sends it; reply not yet recorded** |
| ACLED | account terms; raw event rows are never committed, shared or sent to an outside AI | only district-month totals are publishable |
| DTM API subscriber terms | not yet read | open |

The DTM website terms were read through a page summary, so the wording needs a human re-check.

## Rules still in force

- No raw ACLED event rows committed or sent to an outside AI; every check prints counts and hashes only.
- No tag or push without Aaron's approval; warn before any step estimated over $1; stage explicit paths only; one writer per worktree.
- Stocks and flows stay separate columns (the harmonization decision). The original design-doc text is not edited.

## Known gaps and risks

1. **Older checkouts keep CRLF.** A checkout made before `.gitattributes` landed stays CRLF after a fast-forward, and `tests/test_fixture_bytes.py` fails with a message that does not name line endings. Seen on the moved panel checkout; fixed there by re-checking out the six `eol=lf` files. A README note is not yet written.
2. **Memory figure understates the run.** `RUN_SUMMARY.md` reports 0.1 to 0.2 GB, labelled "main process only"; real raster work likely uses more. A later reprokit wording or measurement fix.
3. **Account check is a word match.** The new `validate` warning only looks for the role or provider name in the "Getting the data" or "Accounts and keys" README sections.
4. **Existing projects get new template text only through `copier update`.** `copier copy` must run from a local clone (`copier copy template <dir>`), not from the repo URL, which copies the whole repo root. A README line for this is not yet written.
5. **12 descriptors are still on schema 0.1.0**, so coverage and note checks do not run for them (`validate` prints a notice).
6. **Sudan COD-PS has 188 of 189 level-2 units** (no Abyei records on the HDX record). How the panel treats the missing unit is unchecked.
7. **Sudan ACLED** was compared at the event-ID level only; no Sudan pipeline run on the API file.

## Open and next

- **Owner:** send the IOM email; record IOM's reply in `instances/sudan/data/descriptors/displacement.yaml`; read the DTM API subscriber terms; check the Funk et al. citation and the DTM website wording.
- **Codex or Claude:** the Abyei check; the README notes for gaps 1 and 4; a reprokit v0.3.3 for the memory wording if wanted.
- **Data wish list (next stage, tracker items):** DTM Household Needs Assessment indicators (Sudan 2022, 2024, 2025: food consumption, hunger scale, rCSI, reason for displacement; 112 indicators); cross-border and refugee flows (DTM cross-border monitoring, UNHCR Refugee Data Finder and operational data portal, IOM Migration Data Portal; GMDAC was down); Google Earth Engine as an optional later extension. See `docs/trackers/academic_hub_to_do.md`.
- **Gated:** the review gate and the Gemini literature memo. The memo review is done in a separate session; planning for the phases after the gate is in another session.

## Where to look

- Reprokit changelog: `projects/reprokit/CHANGELOG.md`. Panel changelog: `projects/compound-shocks-panel/CHANGELOG.md`.
- Verification notes with hashes: `projects/compound-shocks-panel/docs/verification/somalia-2026-11-02.md` and `sudan-2026-11-02.md`.
- Panel README sections "Accounts and keys" and "Getting the data" (ACLED, DTM, and the other sources).
