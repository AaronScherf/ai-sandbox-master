# Codex handoff: real-use check of the faster landing for simple PDF transcriptions (2026-11-25)

From Claude (design), to Codex (Git mechanics and measurement). Use a `codex/<task>` branch and worktree per `docs/WORKTREE_WORKFLOW.md`; stage explicit paths. **Do not land.** The owner approves one change ID at a time and lands.

## Why

The owner's daily changes are mostly non-code: transcribed notes and hub data. A landing for those should not run the chunked test suite (about 15 minutes). On 2026-11-22 a two-file hub index landing reran the entire suite at land time (1,045.5 s) even though `check` had skipped, because `approved_check` preferred an older `non_py_file` pass over a newer `outside_project_only` skip. Three changes since then are meant to fix that. Nobody has yet confirmed this on a real transcription landing.

| Change | Commit | Effect |
|---|---|---|
| Newest check wins unless `--full` | `deef46a0` | A stale pass can no longer outrank a newer skip for the same change ID. Land logs and prints the selected check and any retest reason. |
| Judge by `main`'s guard; `full-main` | `1bb346ee` | Guard runs from `main`'s copy; `land` refuses a guard-policy edit the approved check did not flag. |
| Selection rules (earlier) | `79be34ba`, `8b7a5cec` | `outside_project_only`, `data_unreferenced`, import-closure targeting. See `docs/WORKTREE_LANDING.md`. |

Background: `docs/handoffs/2026-11-22-landing-stale-check-selection-claude-handoff.md` (the incident, with its log evidence).

## Task

Measure a real landing of a simple PDF transcription and report whether it was fast.

1. **Pick the change.** Use the owner's next real transcription branch (`pipelines.transcribe_notes` output under `ai-sandbox/academic-hub/`, usually Markdown plus `.index/*.json`). Do not start a transcription run yourself and do not make paid API calls to create test material; the owner's rule is to warn before any call estimated over $1. If no real branch exists, build a fixture branch that changes one hub Markdown file and one `.index` JSON file, and say it is a fixture.
2. **Pre-flight.** From `ai-sandbox/academic-rag-model/`: `python -m tools.active_work`. Resolve overlaps before the check (an overlap blocks landing).
3. **Check.** `python -m tools.land_branch check`. Record the printed `Checks:` line, `Change ID`, and wall time.
4. **Ask the owner** to approve the change ID in one message (ID, paths, overlaps, `git push origin main`), as in `docs/WORKTREE_LANDING.md`. Wait for a yes; do not land without it.
5. **Land** only on approval: `python -m tools.land_branch land --change-id <ID>`. Record the console output.
6. **Read the log.** `<monorepo>/.git/agent-landing-log.jsonl` (shared Git common directory, append-only; do not edit). Filter by branch and change ID.

## What to verify

Check each item and quote the evidence (log field or console line):

- `check` event: `checks` is `skipped`, `selection_reason` is `outside_project_only` (or `data_unreferenced` / `doc_only`), `check_seconds` is about 0, `check_targets` is empty.
- `land` console shows `Approved check: <at> base <sha> skipped reason <reason>` for that same check, and **no** `Retesting:` line.
- `land` event: `retested` is false, `retest_chunk_timings` is empty, `approved_reason` equals the check's reason, `retest_reason` is empty.
- Wall time from the first `check` to `LANDED`, excluding the time spent waiting for the owner's approval. Compare against the baselines: 912.8 s (full check, 2026-11-16) and 1,045.5 s (unexpected land-time retest, 2026-11-22). Expected: under a minute for the check plus a few seconds for the land.
- Optional: `python -m tools.landing_metrics --since 2026-11-25` for the aggregate view.

## If it is not fast

Do not change `tools/land_branch.py` or work around `land`. Report the evidence and route it to Claude (selection policy is a design decision). Cases worth separating:

- `check` itself ran tests: record the `selection_reason`; compare against `selection_reason` in `tools/land_branch.py`. A path in `OUTSIDE_TEST_INPUTS` (`.gitignore`, `ai-sandbox/.obsidian`, `ai-sandbox/academic-hub/hub_config.json`, the Novelty Check note) deliberately selects the full suite. TODO-0100 covers making `hub_config.json` hermetic; confirm whether the transcription touched it.
- `check` skipped but `land` retested: this would be a regression of the 2026-11-22 bug. Capture the `Approved check:` line and the log records, and compare with the incident table.
- Binary guard refused: a PDF or other binary was staged under the hub. PDFs are not tracked; only the transcribed text and index files should be on the branch. Report the path.
- Another landing check failed on an unrelated test: per `CLAUDE.md`, run that test alone on `main` and on the branch, report both, and re-run the check; do not land on a failed check.

## Report back

Branch and commit, whether it was a real change or a fixture, the change ID, the `check` and `land` console output, the log records quoted, the timings against the baselines, and a verdict: fast / not fast / inconclusive. Put it in a new versioned report under `docs/status/tools/` (`- v1`; never edit in place) and give the owner a clickable link. Leave the existing handoffs alone.

## Not in scope

The `full-main` schedule (the owner decides; Task Scheduler command is in `docs/WORKTREE_LANDING.md`), TODO-0100, and TODO-0101.
