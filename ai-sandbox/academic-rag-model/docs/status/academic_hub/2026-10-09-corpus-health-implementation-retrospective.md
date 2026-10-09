# Corpus-health orchestrator: implementation and trial handoff

**Date:** 2026-10-09

**Status:** Tasks 1-7 and the Task 8 runner are implemented and landed. The seven-day discovery-only trial is installed; Task 8's multi-day observation is still open.

**Plan:** [2026-10-08 implementation plan](../../superpowers/plans/academic_hub/2026-10-08-corpus-health-orchestrator.md) and [2026-10-07 design](../../superpowers/specs/academic_hub/2026-10-07-corpus-health-orchestrator-design.md).

## What shipped relative to the plan

| Planned work | Delivered behavior | Remaining limit |
|---|---|---|
| Tasks 1-3: capability inventory, read-only audit, scanner | A verified [capability inventory](2026-10-08-corpus-health-capability-inventory.md), public read-only index audit, and `python -m tools.corpus_health scan`. The scanner checks configured source/output, frontmatter, index, and Git-state rules without a model call or corpus write. | Its policy map is intentionally narrower than “every Markdown file”; unknown categories and unavailable roots are reported rather than guessed. |
| Tasks 4-5: recurring findings and review | An atomic local decision ledger tracks pending, accepted, declined, deferred, and vanished findings. A short-lived loopback review page records per-item and homogeneous-group decisions. Review uses one scan snapshot per session, not a full corpus scan per click. | A decision is only intent. Review does not execute a repair; changed inputs must be rechecked at apply time. |
| Task 6: shared writer coordination | A cooperative OS lock was added to the selected direct note and index writer CLIs, with contention coverage. | Obsidian sync, remote textbook conversion, unadapted direct writers, and programmatic calls outside those CLIs do not participate. The lock alone does not authorize `academic_notes/` writes. |
| Task 7: accepted-work dispatcher | `apply --accepted` revalidates findings and records `blocked`, `failed`, or post-audit `applied`. Its sole executing adapter targets one current index card by exact `file_id`, calls the indexer CLI under the shared lock, and verifies the resulting chunks. Index shard/chunk writes were made atomic. | This adapter can use the configured Gemini embedding API and requires a per-source review decision. Card reconciliation, transcription/Excalidraw, enhancement/question resolution, postprocessing, and cloud textbook conversion remain blocked. |
| Task 8: daily discovery | `run_daily_scan.ps1` runs only `scan`, writes timestamped reports/logs outside the corpus, and returns the scanner's exit status. A Windows Task Scheduler trial is registered for 7:00 a.m. local time on October 10-16. | The installed task uses an interactive user logon: it can catch up after a missed run when the user signs in, but it cannot run while signed out. The plan's stronger “without an interactive desktop” scheduler acceptance has not been demonstrated. No automatic retry or repair is enabled. |

The implementation followed the plan's staged value boundary: the scanner is usable independently of review and apply. One deliberate narrowing was Task 7's first adapter. The [adapter decision](2026-10-09-corpus-health-apply-first-adapter-decision.md) found that broad index rebuilds and note writes did not meet the plan's exact-scope, writer, and verification gates. The user's separate note-pipeline quality concerns also make automated note repair premature until enhancement, questions, and visuals are fixed and affected outputs are reprocessed and reviewed.

## Verification so far

Synthetic scanner, state, review-server, writer-lock, and apply tests passed, including concurrent ledger writers, vanished sources, exact index-card selection, lock contention, interrupted atomic writes, stale approvals, blocked actions, and post-action auditing. The full repository test gate passed at the Task 7 and Task 8 landings (218.0 and 232.3 seconds respectively, with no worktree overlaps reported). These tests establish behavior on fixtures; they do not prove that every live corpus finding is correctly classified.

Three pre-installation read-only live scans on October 9 took 21.1-27.7 seconds of scanner time, considered 693-694 files, hashed 444-445, reported 305-306 findings, and reported zero scan errors. A manual launch of the installed scheduled task also exited `0`: 20.25 seconds, 696 files considered, 445 hashed, 306 findings, zero errors. The report does not expose an exact filesystem-metadata-check count. The task's next scheduled run was October 10 at 7:00 a.m.; a separate one-time reminder is set for October 17 at 9:00 a.m. local time. Neither a successful exit nor the finding count establishes that all 306 findings are actionable.

## Revisit after the trial

After the October 10-16 run window, inspect each scheduled task result and JSON/log pair for completion, runtime, root availability, and changes in finding counts. Manually sample findings from different courses and kinds, including textbook identity, generated-file exclusions, frontmatter, and intentionally deferred Math Camp PDFs; classify true gaps versus scanner false positives. Confirm that declined/deferred findings remain stable across days and that a changed source returns for review. Record any missed-run/catch-up behavior observed on this machine. Only then assess whether the scanner's policies and operating mode are reliable enough for continued daily use.

Do not interpret the end of the trial as approval for unattended fixes. Any additional apply adapter needs its own exact input selector, cost and destination policy, participating writer coverage, and target-level postcondition check. Revisit note repairs only after the source pipeline and `academic_notes/` sync-quiescence work are complete.
