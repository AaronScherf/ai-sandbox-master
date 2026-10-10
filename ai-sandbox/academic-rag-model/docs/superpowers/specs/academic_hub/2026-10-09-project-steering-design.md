# Project Steering and To-Do Review: Design

**Status:** Draft for design review. This document specifies behavior; no script or scheduled task has been implemented.
**Date:** 2026-10-09
**Source request:** Categorize, sort, and rank the growing to-do list; identify dependencies and effort; recommend what to tackle next; refresh a review artifact without an LLM call on each run.

## Requirements and constraints

1. Preserve the existing to-do descriptions and subproject grouping while producing a current, sorted work-selection view.
2. Make priority and effort judgments inspectable and adjustable by the owner. Do not present keyword guesses as established facts.
3. Represent dependencies explicitly; never silently infer a blocking edge from prose. Recommend only ready work, with a separate view of blocked work and tasks needing estimates.
4. Run locally and unattended without an agent, model API, cloud service, or Git write. Refresh the review material even if nobody opens it that day.
5. Keep decisions stable across runs. A declined or deferred item must not reappear as new until its relevant content changes or its deferral expires.
6. Provide an interactive decision surface, following `academic-rag-model/CLAUDE.md`'s Artifact convention. The scheduled process cannot publish or operate a Claude-hosted Artifact, so the proposed equivalent is a local interactive page opened by a separate `review` command.
7. Keep this project-work queue separate from the corpus-health scanner. It may share small local page and atomic-state utilities after those are extracted, but it must not reuse corpus findings, repair states, or `apply` semantics.

The initial source is `docs/trackers/academic_hub_to_do.md`. The existing tracker request under "Project Steering and Work Selection" also mentions resumable work and bugs. Those are not yet a complete machine-readable source; v1 reports only tasks actually present in the tracker. Importing other status documents or bug reports requires an explicit source inventory and deduplication rules later.

## Verified repository facts and adjacent work

- `README.md` describes `tools/` as the home for small standalone bridge scripts; `python -m` is the package command convention.
- The tracker is in the **outer monorepo** under `academic-rag-model/docs/trackers/`. It is currently organized by `##` subproject headings, mostly with `-` tasks and `(added YYYY-MM-DD)` dates. It has multiline bullets, a nested bullet, a Git-workflow brainstorm section, and pasted textbook examples after the final task section. A line-based "sort every bullet" transform would misclassify content. The tracker itself says new sections go below the title, not at EOF.
- `docs/trackers/academic_hub_to_do.md` already contains this project idea. `docs/status/academic_hub/2026-10-08-corpus-health-capability-inventory.md` and `docs/superpowers/plans/academic_hub/2026-10-08-corpus-health-orchestrator.md` explicitly keep work selection separate from corpus health.
- `tools/corpus_health/README.md`, `state.py`, `review_server.py`, and `run_daily_scan.ps1` demonstrate a model-free scan, atomic local decision storage, a loopback review page, and a Windows Task Scheduler entry point. They do not parse or rank to-dos. Its scheduled runner has passed a manual launch; the documented multi-day trial remains unverified.
- `academic-hub/` is part of the outer monorepo. The linked `academic-hub/academic_notes/.../gemini_reprep_b_prompt.md` is in a separate nested Git checkout in the live workspace and concerns a tutoring-packet sample task, not this design. It is neither a source to ingest nor an instruction to execute. An outer worktree may not contain that nested checkout.
- The root `CLAUDE.md` allows direct-to-main manual additions to the tracker when asked to log a pending item. That narrow exemption does not establish a safe unattended rewrite policy. `docs/WORKTREE_WORKFLOW.md` governs implementation and reviewed tracked-file changes.

## Scope and capability inventory

| Capability | Discovery and scope | Side effects / cost | Output and idempotency | Verification |
|---|---|---|---|---|
| Tracker parse, proposed | One configured Markdown file; only eligible top-level task bullets under `##` headings | Local read, proportional to file size; no API | Parsed task snapshot and explicit diagnostics; repeatable for unchanged input | Compare a varied sample against source spans, including multiline and example text |
| Metadata and decisions, proposed | Stable task IDs, owner scores, effort, dependency edges, defer/decline state | Atomic writes to ignored local state; no Git write | Same input and decisions produce the same state and rank | Restart and repeat-run checks; stale edit and cycle checks |
| Ranked view, proposed | All parsed tasks, with ready/blocked/needs-review groups | Atomic local report write; no API | Replaces one generated report, retaining the last good report on failure | Inspect ranking reasons and deterministic tie breaks |
| Interactive review, proposed | Current scan snapshot, individual task decisions | Short-lived loopback process; local state writes only | Reopening preserves decisions; no task execution | Browser interaction, stale-snapshot rejection, and non-loopback access checks |
| Tracked tracker edit, later | Exact reviewed IDs and source spans only | Outer-monorepo write and normal Git worktree/landing process | Previewed patch; rejects stale source hash | Review diff, reparse, and verify only targeted spans changed |
| Corpus-health scanner, existing | Corpus output/index/Git findings, not work-selection tasks | Its own local state; some separate accepted repairs can incur API cost | Different finding and decision model | Its own tests and reports; no dependency for this tool |

No source pipeline, index search, or tutoring command is needed for daily ranking. The linked packet and nested notes repository are outside the read set.

## Data model and parsing

The tracker remains the canonical narrative list. The automatically refreshed **ranked to-do view** is the daily list used for selection; it is generated locally and never asks the owner to edit raw JSON or Markdown by hand. The tool does not reorder the canonical tracker on every run, which would cause Git churn and collide with agents adding items.

Each eligible task has `id`, `section`, `title`, full Markdown body, added date if valid, source line span, and a content fingerprint. A task starts at a top-level `- ` under a `##` heading and includes its indented continuation lines. Nested bullets are part of the parent body. Heading changes end a task. The parser recognizes a task only if it has the tracker convention's added-date marker at the end of its body; text such as the Git-workflow brainstorm and pasted textbook examples remains outside automatic ranking unless reviewed and converted to tasks. Diagnostics include source line numbers for ambiguous bullets, missing dates, duplicate IDs, and malformed boundaries. An incomplete parse cannot be reported as a complete queue.

Stable IDs use an explicit `TODO-####` marker on eligible bullets, introduced in a separately reviewed, one-time tracker migration. The migration previews every changed line and does not alter task wording or order. Before migration, scan may produce a useful provisional report keyed by section plus exact normalized body hash; its decisions are not durable across text edits. A new eligible bullet without an ID appears in `needs_id`, not silently merged with an older item. IDs are never reused. Deleted tasks become `vanished` in local history, and moved tasks retain their ID.

State is versioned and stored in an ignored local directory under the outer Git common directory, separate from corpus-health state. It contains user-entered `impact` and `urgency` (0-3), effort band (`<2h`, `half_day`, `1_2_days`, `larger`, or `unknown`), explicit `depends_on` task IDs, status (`candidate`, `ready`, `in_progress`, `deferred`, `declined`, `done`), optional defer-until date, last reviewed fingerprint, and decision timestamps. The generated report contains source links and brief task excerpts; it does not copy linked notes or copyrighted material.

An unchanged item keeps its metadata and decision. A change to the task body or section preserves the ID and user scores but marks them `recheck`; the prior decline/deferral does not suppress a materially changed task. A whitespace-only change is normalized away. A dependency target that vanishes, a self-edge, or a dependency cycle produces a review error and makes the affected task ineligible for the ready list. A deferred task stays out of daily recommendations until its date or a changed fingerprint; a declined task stays out until changed or manually restored. `done` is a human decision in v1; the script does not infer completion from Git commits.

## Ranking and recommendation

The tool does not claim to estimate effort from prose. On import, an explicit `URGENT` label may seed urgency 3, and text such as "paused at user request" may seed a suggested deferred state; both are marked provisional until reviewed. All other scores and effort start unknown. Added date is a tie breaker, not a proxy for importance. Phrase matches such as "after", "first", or "requires" create dependency suggestions for review only, with source excerpts and candidate target IDs. Only confirmed `depends_on` edges block a task.

For fully scored, active tasks, use the transparent v1 score `3*impact + 3*urgency + 2*unlock_count - effort_penalty`, where `unlock_count` is the number of active tasks directly waiting on this task, capped at 3, and effort penalty is 0/1/2/3 for the four effort bands. Show each term in the review page. Tasks with an unresolved dependency are `blocked`; tasks with unknown impact, urgency, or effort are `needs_estimate` and can be shown as provisional suggestions, not asserted as the best work. Within equal scores, use lower effort, earlier added date, then stable ID. Recommend up to three ready tasks, favoring distinct subprojects only when scores tie. The owner can override scores and pick a task regardless of the algorithm.

The review page shows the next-three shortlist, why each scored as it did, a dependency chain, effort band, source link, and separate `blocked`, `needs_estimate`, `deferred`, and parse-warning views. It supports changing scores/effort, confirming or rejecting suggested edges, marking in progress/done, and deferring or declining. Decisions save immediately to local state; they do not invoke a pipeline or edit Git history. The local page follows the existing corpus-health pattern: bind to `127.0.0.1`, use a per-run token and origin checks, reject stale scan fingerprints, escape task Markdown as untrusted content, and stop on close or timeout.

## Commands, scheduling, and outputs

Proposed entry point: `python -m tools.project_steering` from `academic-rag-model/`.

| Command | Behavior |
|---|---|
| `scan --tracker <path> --state-dir <path>` | Parse, reconcile state, compute ranks, and atomically refresh a JSON snapshot and generated ranked Markdown/HTML view; exit nonzero with diagnostics on incomplete parse or write failure. No browser or API. |
| `review --tracker <path> --state-dir <path>` | Start the short-lived local review page from a current scan snapshot and save decisions. No canonical tracker write. |
| `preview-ids --tracker <path>` | Produce a diff for the one-time stable-ID migration; no write. |
| `apply-ids --tracker <path>` | Future explicit command run only in an assigned worktree after diff review; verify original hash before atomic replacement and reparse afterward. |

The first scheduled mode calls only `scan`. On Windows, Task Scheduler launches a PowerShell wrapper with explicit Python, tracker, state, and log paths, using the same no-overlap setting as the corpus-health daily runner. It can run at logon or while signed in under the user's account; actual signed-out behavior depends on the chosen Task Scheduler account and must be tested before claiming it works. One tracker scan is O(file bytes plus task/dependency count), with no corpus walk, hashing of linked files, network request, or model call. Record input size, task counts, warnings, runtime, output paths, and exit code to a dated local log. Measure first on the live tracker before setting a timeout.

The local state and report should be outside tracked source and the nested notes repo; the report is a disposable view and state is the durable record. Write temp files in the destination directory, flush, then replace atomically. A failed scan leaves the previous complete report in place and writes an error log. There is no automatic retry loop; the next scheduled trigger retries, and a manual run can diagnose the error. With no human available, the refreshed shortlist and warnings wait for review; no decision is inferred from silence. The local review server starts only on demand, so unattended scans require neither an open browser nor a persistent server.

## Release boundary and verification

The smallest useful release is a manual or scheduled `scan` that parses the existing tracker, emits diagnostics, and refreshes a provisional ranked view. This can deliver an organized list before ID migration or an interactive page exists. It must clearly label unknown estimates and unconfirmed dependencies. The next release adds the one-time ID migration, persistent owner metadata, and the local interactive review page; those are necessary for stable decline/defer decisions and dependable personalized recommendations. Canonical tracker edits beyond inserting IDs, ingestion of status/bug sources, a cross-project dashboard, and automatic Git commits belong to later work.

Before accepting aggregate counts or recommendations, compare a small varied live sample with the tracker: short and multiline tasks, an `URGENT` entry, a deferred entry, a nested bullet, the Git-workflow brainstorm, and pasted textbook examples. Record missed tasks and false positives, then correct parsing rules. Test ranking with fixed fixtures for tie breaks, unknown scores, dependency chains/cycles, changed text, expired deferrals, and repeat-run idempotency. Test atomic report replacement and a failed write. Once the page exists, test that decisions persist, stale snapshots cannot overwrite newer state, and the page is reachable only on loopback. These are fixture tests and local observations; they do not establish that the ranking reflects the owner's true priorities until the owner reviews real items.

## Open review point

The first release defines "automatically updates the to-do list" as refreshing a generated ranked view while retaining the tracker as the canonical narrative source. If the owner wants the canonical Markdown itself reordered on each run, that would require a separate write and concurrency policy with the other agents that append to it. The generated-view approach avoids making that policy a prerequisite for useful daily recommendations.
