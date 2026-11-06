# reprokit v0.3 handoff (for a codex session focused on reprokit)

Written 2026-11-03 by the Claude session that ran Phase A of Project 02. This is a brief, not an approved plan: the session picking it up should confirm scope with Aaron before building. Nothing below is built.

## Where things are

| Thing | Location |
| --- | --- |
| Framework repo (validators, schemas, template) | `C:\Users\theaa\reprokit`, tags `v0.1.0`, `v0.2.0` (standalone git repo, MIT) |
| First project built on it | `C:\Users\theaa\compound-shocks-panel`, tags `v0.1.0` to `v0.1.2`, GitHub `AaronScherf/compound-shocks-panel` |
| Evidence and ratings | `ai-sandbox/research/independent-research/notes/05_reprokit-reproducibility-framework/Pipeline Review - Reproducible Research Framework after Phase A.md` (monorepo, on `main`) |
| Gemini's structure audit | `.agent-reports/reviews/20261102-133500-reprokit-structure-audit/review.md` |
| Design doc and addendum | `ai-sandbox/research/independent-research/docs/superpowers/specs/2026-10-31-reproducible-research-framework-design.md` (sections 1 to 9 are original intent; the addendum at the bottom records Phase A) |

Read the pipeline review first. It has the evidence behind each item.

## Goal

Make the next project built on reprokit start with fewer of the problems Phase A hit. Success is measured by the template and validators catching, by default, the kinds of error that got through this time.

## Items, in priority order

Each item has an acceptance check. Schema changes follow `reprokit/AGENTS.md`: version bump plus a test.

1. **`validate` checks claims, not just shape.** Fail (or warn, your design call) when: a descriptor's `reuse_terms`, `access_class` or similar free-text field contains "confirm", "unverified", "tbd" or is empty; a descriptor's `coverage_time` does not cover the config `period` and no explanation field says why; `verification_status` is `run on acquired data` or higher but no verification note references the current code version. *Accept:* the Phase A defects reproduce as failures when replayed on a copy of `compound-shocks-panel` at `v0.1.0` (placeholder licence on COD-PS; stale periods) and pass on a corrected copy.
2. **Run card.** `reproduce` (project side) writes a short generated file of window, row counts, output hashes, per-step timings and peak memory, from `manifest.json` and `run_report.json`. Provide the helper in reprokit; the template README and verification-note stub quote or link it. *Accept:* no run time, count or window in the template's docs is typed by hand.
3. **`smoke` command in the template.** Runs a synthetic fixture instance end to end in under 60 seconds with no network, and is what CI and a newcomer run first. *Accept:* fresh clone, `uv sync --locked`, one command, under 60 seconds, on Windows and Linux CI.
4. **Fix path drift in the template.** Offer single-instance and multi-instance layouts as a template option, and generate `AGENTS.md` and README paths from the choice. Add a researcher's orientation table at the top of the generated README (developer file to research concept). *Accept:* a generated project's docs name only paths that exist.
5. **Record measured cost.** Compare measured runtime and memory per step with `compute.yaml`. *Accept:* the run card flags a step that exceeds the declared RAM.
6. **Template stub for a harmonization record**, and a short "adding a second source type" section for the template docs (core changes are expected; same-kind swaps are config only).
7. **Charter schema: add an exploratory purpose.** Phase A used `side_project` as a workaround. Version bump and test.
8. **Narrating `reproduce`.** One readable line per step (reads, main rule, rows in and out) from the run report, plus a lineage diagram stub in `protocol.md`. (Gemini Proposal C.)
9. **`pip` path.** Document a `venv` plus `pip install -e .` route only after testing it on a clean machine. (Gemini Proposal D.) Do not document it untested.
10. **Scaffolding.** Do not ship empty folders (`comms/`, empty instance folders) unless a step needs them. (Gemini Finding 5.)

Items 1 to 3 matter most. 4 to 7 are next. 8 to 10 are lower priority.

## Decisions already made (do not reopen without Aaron)

- The original design doc text is not edited. Add to the addendum at its bottom if the design changes.
- No outside reproduction attempt yet; it waits until the project has data worth reproducing.
- Two displacement measures (Somalia flow, Sudan stock) stay separate; nothing here changes that.
- Phase B research work (modelling, the research question) is out of scope here.

## Rules

- `reprokit` is a standalone repo. Work on a branch, push, and tag only with Aaron's explicit approval (as with `compound-shocks-panel` `v0.1.0`). Commit messages end with the Co-Authored-By line from your system reminder.
- `compound-shocks-panel` is the test target. Do not change it except to bump the pinned `reprokit` requirement after a release, and do that only if Aaron asks.
- Changes to monorepo files (this brief, the design addendum) follow `docs/WORKTREE_WORKFLOW.md` and the landing procedure; do not land on `main` without Aaron's approval.
- No raw ACLED rows anywhere. No credentials in files.
- Warn Aaron before any step estimated over $1.

## Suggested first message to Aaron

"I've read the pipeline review and the v0.3 handoff. I'll start with items 1 to 3. Confirm or change the scope, and tell me whether item 1 should fail or warn on a placeholder licence."
