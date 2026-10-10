# Project steering and to-do review: current status

**Date:** 2026-10-10
**Package:** [`tools/project_steering`](../../../tools/project_steering/README.md)
**Plan:** [project-steering implementation](../../superpowers/plans/academic_hub/2026-10-09-project-steering.md)

The model-free tracker scan, stable task IDs, local owner decisions, deterministic ranking, and on-demand review page are on `main`. Routing tags and score drafts remain suggestions until individually or batch-approved by the owner. The review page edits scores, dependencies, status, time gates, and routes; its scored table supports sorting and filtering, and Next three/Needs Estimate details can be collapsed. Reviewing a task does not execute it.

The canonical pending list is [`academic_hub_to_do.md`](../../trackers/academic_hub_to_do.md); completed tasks move to [`academic_hub_completed.md`](../../trackers/academic_hub_completed.md). `TODO-0058` was fixed in `f7062e9` and archived in `a186d70` (landed with the review-command header at `bad40f3`). The tracker header now gives a one-line PowerShell command for opening the review page without an agent. It prints a tokenized `127.0.0.1` URL; the server stops after 15 minutes. Opening review performs a fresh scan. The M3 scheduled scan is not implemented by this package.

## Evidence and current queue

- The full repository landing gate passed for the review-page changes and for the `TODO-0058` test fix. The audio test also passed in a focused `pytest -n 2` run. These checks verify code and fixtures, not the accuracy of every owner priority or agent assignment.
- A live `scan` on 2026-10-10 after the archive published a complete report: 69 active tasks, zero unresolved warnings, and 29 structured exclusions. Its local state revision is 18; `TODO-0058` is marked vanished from the pending source. The scan makes no model or network calls and did not edit either tracker.
- The current tracker plus local owner ledger yield 18 ready tasks with approved scores, 50 in Needs Estimate, and one behind a `not_before` gate. There are 18 owner-approved Codex routes in an actionable batch. Another 10 Codex, 29 Claude, 7 Gemini, and 2 Needs Human Review routes remain proposed; two additional unassigned tasks fall back to Needs Human Review. These counts describe this machine's local ledger, not decisions committed to Git.
- Prior local browser checks exercised the scored table, filters, and collapsible details. The freshly archived tracker was parser-checked and scanned; a new browser session after that archive has not been observed.

## Remaining work

Owner review of the remaining score and route proposals, dependency judgments, and the plan's full M2 acceptance evidence are still open. M3 unattended scheduling is not implemented. Bugs and resumable branch work remain outside this tracker-backed v1 until they have stable identity and deduplication rules.
