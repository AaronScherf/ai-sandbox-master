# Project Steering and To-Do Review: Implementation Plan

**Status:** Draft plan; no project-steering code, ID migration, or scheduled job has been run.
**Date:** 2026-10-09
**Spec:** [2026-10-09 project-steering design](../../specs/academic_hub/2026-10-09-project-steering-design.md)
**Scope:** One tracker-backed, model-free ranked view and interactive local review flow. The tutoring-packet prompt linked in the request is unrelated and outside the read and write set.

**Design review gate:** The spec's dated-bullet eligibility rule omits several genuine undated textbook work items around tracker lines 272–278. Before claiming full tracker coverage or migrating IDs, Claude must decide whether to add those items to the convention with an explicit unknown-date representation, or keep them as a separately visible `needs_review` queue. The generated-view choice, invisible ID marker syntax, and deterministic shortlist tie rule below are also proposals for that review. Implementation may start on the read-only scanner, but no silent promotion or exclusion of these items is authorized by this draft plan.

## Goal and release boundary

The owner wants a short, current list of work to consider next, with categories, priority reasons, dependencies, and effort, refreshed without an LLM call. The source tracker remains the canonical narrative. A generated ranked view is the automatic update; scheduled runs do not reorder or commit the tracker.

Deliver this in three independently verifiable milestones:

1. **M1 — useful scanner:** parse the live tracker, report exclusions and uncertain entries, and atomically refresh a provisional ranked view. It runs manually or unattended with no browser, model, persistent decisions, or tracker write. Unknown scores and effort remain visibly unknown; it cannot claim a personalized top three yet.
2. **M2 — reliable work selection:** introduce stable IDs through a reviewed migration, local decision state, explicit dependency validation, deterministic scoring, and an interactive review page. This makes the shortlist personal and lets defer/decline choices persist.
3. **M3 — daily operation:** add and trial a Windows Task Scheduler entry point that runs only `scan`; measure runtime and inspect daily results. The local page is opened separately when a person is available.

No always-on server, database service, corpus writer lock, automatic Git commit, or corpus-health integration is needed for these releases. Importing status documents and separate bug lists can add value later but requires a source inventory and deduplication design first.

## Verified inputs and boundaries

- The code location follows the package `README.md` convention: a standalone `tools/project_steering/` module, invoked with `python -m tools.project_steering` from `academic-rag-model/`. The tracker is `docs/trackers/academic_hub_to_do.md` in the outer monorepo. `academic-hub/` shares that monorepo; the live `academic-hub/academic_notes/` is a separate nested Git checkout and is not needed by this tool.
- The tracker currently has `##` subproject headings, long multiline bullets, a nested bullet, some tasks with `(added YYYY-MM-DD; updated YYYY-MM-DD)`, a Git-workflow brainstorm, and pasted textbook examples near EOF. Parsing by line or sorting all Markdown bullets would lose or misclassify content. `docs/trackers/academic_hub_to_do.md` already records the project-steering request.
- `tools/corpus_health/` supplies verified examples for an atomic local ledger (`state.py`), loopback review server (`review_server.py`), and scheduled runner (`run_daily_scan.ps1`). Its state schema and repair decisions do not fit task selection, so use its operational pattern without importing its domain types. `docs/status/academic_hub/2026-10-08-corpus-health-capability-inventory.md` and `docs/superpowers/plans/academic_hub/2026-10-08-corpus-health-orchestrator.md` explicitly keep project steering separate.
- `academic-rag-model/CLAUDE.md` requires an interactive Artifact for human decisions by default. A scheduled process cannot publish a Claude-hosted Artifact. As the project-steering spec proposes, an on-demand loopback page is the local interactive equivalent; machine JSON is never the owner's editing surface.
- `docs/WORKTREE_WORKFLOW.md` governs tracked changes. Its 2026-10-10 amendment permits omitting `--full` from the landing check only when the whole branch diff is Markdown. The implementation branches, which change Python or scripts, still use the full landing gate.

| Operation | Discovery and scope | Cost and side effects | Output and idempotency | Acceptance evidence |
|---|---|---|---|---|
| Parse tracker | One explicit `.md` file; top-level dated tasks under `##` | O(file bytes), no API or write to source | Same bytes yield same tasks and warnings | Fixture cases plus varied live source-span comparison |
| Generate ranked view | Parsed tasks and reviewed state, when present | Local atomic report write only | Same snapshot/state yields same order and explanation | Golden examples, repeat-run byte comparison |
| Review decisions | Current snapshot and one task ID per edit | Local state write under process lock; no Git/API | Decisions persist and stale edits reject | Restart, concurrent-write, stale-snapshot tests |
| Assign IDs | Exact eligible task spans in one reviewed tracker revision | One tracked outer-monorepo edit in its own worktree | Re-running proposes no additional IDs | Previewed diff, reparse, no wording/order change |
| Scheduled scan | One tracker and local state directory | Local CPU/disk only; no browser or network | Replaces report atomically; failures leave last good report | Manual scheduled launch, logs, then observed runs |

## Global contracts and requirement traceability

| Requirement or constraint | Planned work | Evidence before calling it done |
|---|---|---|
| Categorize all eligible tasks and expose omissions | Tasks 1–2 | Live sample truth table, counts by section, warnings with line spans |
| Explain a ranked next-work shortlist and effort | Tasks 2, 4–5 | Fixed score/tie examples and UI displaying score terms and effort provenance |
| Respect actual dependencies, including cycles and vanished targets | Tasks 4–5 | Graph fixtures; only confirmed edges block; invalid graph excluded from ready list |
| Preserve decisions and suppress unchanged deferred/declined items | Tasks 3–5 | Restart/changed-text/expiry tests and repeated live scans |
| Interactive human decision surface | Task 5 | Browser smoke test, durable decisions, loopback/security tests |
| Unattended, no model/API/corpus/Git writes | Tasks 2, 3, 6 | Static call-path review, scheduled-run log, unchanged tracker and Git status |
| Stable source identity and safe tracked-file coordination | Task 3 | ID migration preview; one-writer worktree; stale-hash rejection; reparse |
| Atomic reports/state, failure and retry behavior | Tasks 2–3, 6 | Interrupted-write fixture; last good report preserved; next trigger retries |
| Keep corpus-health and nested notes repo separate | All tasks | Diff contains only project-steering files and deliberate tracker ID migration |

Each milestone must update this plan's status with **implemented behavior**, **fixture-tested behavior**, **live read-only observations**, and **remaining unverified operation** separately. Passing unit tests does not validate the live parser's classifications or the quality of the owner's rankings.

## Task 1 — Establish a parser truth set from the live tracker

**Files:** Read `docs/trackers/academic_hub_to_do.md`; create a small, synthetic `tests/tools/project_steering/fixtures/` set and a classification table in the implementation handoff or focused status note. Do not copy the linked packet or nested notes content.

**Steps:** Record the exact boundaries for a short task, multiline task, nested bullet, urgent item, paused/deferred item, updated-date marker, section transition, Git-workflow brainstorm, undated textbook work item, and pasted textbook example. Count eligible tasks and ambiguous bullets manually from those spans. Specify the accepted date grammar, including `(added YYYY-MM-DD; updated YYYY-MM-DD)`. Treat a malformed or undated bullet as a warning or `needs_review` candidate, never a silently dropped task. Confirm that the `##` heading and continuation indentation rules work on this varied sample before trusting whole-file counts.

**Acceptance:** A reviewed table maps each chosen source span to `task`, `continuation`, or `excluded/needs_review` with a reason. It explicitly records the fate of the undated textbook bullets; until the design gate resolves them, no report claims complete coverage. No aggregate count is labeled reliable until the parser agrees with this sample. This task is read-only against the live tracker.

## Task 2 — Ship the independently useful scanner and generated view (M1)

**Files:** Create `tools/project_steering/{__init__,__main__,cli,parser,ranking,report}.py`, `tools/project_steering/README.md`, and focused `tests/tools/project_steering/` tests. Add a package entry to the main `README.md` only when the command exists.

**Steps:** Read the tracker as UTF-8 once and compute a snapshot hash before and after parsing; refuse to publish a complete report if the source changed mid-read. Parse top-level `- ` bullets under `##` headings with dated endings and preserve multiline body text. Report every excluded/ambiguous bullet and source line. Before ID migration, give eligible tasks deterministic **provisional** identities from section plus normalized body hash, labeled unstable after edits. Group by section and readiness; show unknown impact/urgency/effort explicitly. A literal `URGENT` marker can create a suggested urgency value only, and pause wording can create a suggested deferred label only. Do not infer confirmed dependencies or estimates from prose. Sort provisional items reproducibly, with a separate "score next" queue; never claim an unreviewed top three is authoritative.

Expose `scan --tracker <absolute path> --state-dir <absolute path>` and `--format json|markdown` for stdout, while writing one JSON snapshot and one ranked Markdown view to the chosen local report directory. The Markdown is a generated review summary, not a hand-editable decision file. Use temp files in the destination, flush and atomically replace; preserve the previous complete report on source/read/write error. A parse with unresolved but bounded ambiguity publishes a **partial** report with `coverage_complete=false`, task/warning counts, and the `needs_review` entries; it must never publish it as a complete queue. Exit `0` only for complete coverage and `2` for partial coverage or operational failure, distinguishing these reasons in the JSON/log. Record file bytes, tasks considered, warnings, and duration. No import from corpus-health domain code and no model-client import.

**Acceptance:** Parser and report fixtures cover Task 1 cases, malformed dates, duplicate/provisional identities, Unicode, source-change detection, stable order, and interrupted output. A read-only live scan produces a report; compare at least the Task 1 source spans with its entries and record false positives/negatives. Verify that the tracked source and Git status are unchanged. M1 can be used manually even if M2 is deferred.

## Task 3 — Add explicit IDs and durable local state

**Files:** Add `tools/project_steering/{identity,state}.py` and focused tests. The only planned tracked data edit is `docs/trackers/academic_hub_to_do.md`, in a separate one-writer worktree for the ID migration.

**Steps:** Subject to the design review gate, use an invisible marker at the start of an eligible bullet body, `- <!-- TODO-0001 --> Text ...`, so the rendered task wording remains the same. `preview-ids` shows an exact unified diff for only eligible bullets lacking IDs; `apply-ids` requires the source hash seen by preview, verifies the exact target path is the intended outer-monorepo tracker, writes atomically, and reparses before success. Never renumber, duplicate, or reuse IDs. Run migration separately from scheduled `scan`, coordinate with the tracker owner and existing direct-to-main additions, and follow the worktree/landing procedure. If an ID cannot be assigned unambiguously, leave that item in `needs_id` for review.

Store a versioned state file under `<outer Git common dir>/project-steering/`, separate from corpus-health state, with an OS process lock and atomic replacement. The source tracker remains canonical for wording; local state holds scores, effort, explicit dependency IDs, status, deferral date, and reviewed fingerprint. A changed body or section retains its ID and scores but enters `recheck` and loses any suppression from an old decline/deferral. Whitespace-only edits do not invalidate it. A missing ID does not inherit another item's decision by fuzzy text matching. Missing tasks become `vanished` rather than being discarded; reappearing unchanged IDs retain history and require review if their content changed. A scan and review process cannot overwrite each other's ledger updates.

**Acceptance:** Preview is exact and repeatable; migration changes marker bytes only, preserves task order/body, and a second preview is empty. Tests cover duplicate/missing IDs, stale source hash, moved/edited/vanished/reappearing tasks, state version rejection, competing writers, interruption, and restart persistence. A post-migration live read-only scan reports all assigned IDs and no new false task classifications before any rankings are trusted. This one-time migration is a tracked write and is not performed by the scheduled task.

## Task 4 — Deterministic priority and dependency engine

**Files:** Complete `ranking.py`; add graph and state-transition tests under `tests/tools/project_steering/`.

**Steps:** Implement the spec's `3*impact + 3*urgency + 2*min(unlock_count,3) - effort_penalty` only for active tasks whose impact, urgency, and effort were reviewed. Define effort penalties as 0/1/2/3 for `<2h`, `half_day`, `1_2_days`, and `larger`. Keep `unknown` outside the scored shortlist. Sort the full display by score, lower effort, earlier added date, then ID; as a proposed shortlist-only rule, prefer an unrepresented subproject among equal-scored candidates before applying those tie breaks. Confirm that interpretation at design review. Show every score term and field provenance. Generate suggested edges from narrow phrases with quoted task-local evidence but require the owner to confirm the target ID. Validate no self-edge, cycle, or vanished target; affected tasks move to `needs_review` rather than `ready`. A task is blocked until each confirmed prerequisite is marked `done`. Deferred/declined/done items are excluded from ready recommendations; an expired defer returns to review, not silently to the top three.

**Acceptance:** Fixtures prove exact score arithmetic, tie order, chained dependencies, direct unlock counts, cycles, missing targets, unknown estimates, edited-task invalidation, decline suppression, and defer expiry. Two runs on the same tracker and state yield the same ranking bytes. A small reviewed live sample agrees with the displayed readiness and dependency reasons. Ranking quality remains a human judgment, not a test claim.

## Task 5 — On-demand interactive review page (M2)

**Files:** Add `tools/project_steering/{review_server.py,static/review.html,static/review.js}` and focused HTTP/UI tests; document `review` in `README.md`.

**Steps:** `review` refreshes or validates one scan snapshot, then starts a short-lived standard-library HTTP server on `127.0.0.1`. Reuse the corpus-health page's proven token, Origin/Host, CSP, size-limit, and shutdown pattern without sharing its finding schema. Render task text as escaped text, not executable HTML. Show the shortlist, score terms, effort, source link, dependency path, `needs_estimate`, `blocked`, `deferred`, and parse-warning groups. Provide individual controls for impact, urgency, effort, suggested-edge confirmation/rejection, explicit dependency add/remove, in-progress/done, defer date, decline, and restore. POST decisions by task ID plus expected fingerprint/state revision; reject stale revisions and invalid transitions. Decisions change local state only, not tracker text or Git history. After a save, recompute the preview from the same snapshot and explain any changed shortlist.

**Acceptance:** Browser smoke test against local fixtures shows a decision surviving restart and affecting the shortlist. Tests cover input validation, stale snapshot, concurrency, content escaping, CSRF/origin checks, non-loopback inaccessibility, and no unexpected task execution. A real local review of a small task sample confirms that the owner can supply scores and dependencies without editing raw JSON or Markdown. M2 completes the original requested human decision flow.

## Task 6 — Scheduled discovery and observed operation (M3)

**Files:** Add `tools/project_steering/run_daily_scan.ps1`, scheduler setup instructions in the package README, and wrapper tests where practical. Do not install a task from the Python CLI.

**Steps:** The PowerShell wrapper accepts absolute interpreter, tracker, state, and log paths; fixes the package working directory and UTF-8 mode; calls `scan` only; writes a dated exit/error log; and returns the CLI exit code. Validate the output path is outside tracked source and the nested notes repo. Document a Task Scheduler trigger under the user's account, missed-run behavior, and "do not start a new instance." Measure one manual live scan's elapsed time and input size before choosing a timeout. A nonzero run keeps the previous report and is retried by the next scheduled trigger or a manual command. No reviewer present means no state decision or tracker mutation. Install a daily trigger only as a separately authorized operational step, then inspect several scheduled logs/reports and compare a varied sample of live results before calling recurring operation reliable.

**Acceptance:** A manual wrapper invocation exits `0` for a complete scan, produces matching report/log timestamps, and leaves tracked files and Git status unchanged. Missing tracker, malformed content, and unwritable state cause nonzero exit and preserve the last good report. A successful manual Task Scheduler launch establishes installation only; multiple observed scheduled runs establish ongoing behavior. Record any missed-run or signed-out limits rather than assuming the job runs without an interactive session.

## Deferred work and handoff

- Do not auto-reorder the canonical tracker or make daily Git commits. If requested later, first define a writer/merge policy for the agents that append tasks and a stale-source/atomic-write contract for exact reviewed spans.
- Do not ingest `docs/status/`, bugs, resumable branch state, the academic notes checkout, or the linked tutoring packet in v1. Adding them needs explicit identity and duplicate rules so one real task is not recommended twice.
- Do not reuse corpus-health acceptance or repair actions; selecting work never executes a pipeline. No API or cloud-cost policy is needed for the daily tool because it makes no such calls.
- After the M2 live review, revisit the original request and the smallest usable release: keep M1 available on its own; M2 is required for personalized recommendations and durable choices; M3 changes convenience, not ranking correctness. Reassess whether any further service, store, or rollout phase is actually necessary before adding it.

The implementation handoff should record branch/path, changed files, focused and landing-gate results, live sample classification, measured scan runtime, and which milestone is merely implemented versus exercised on live data. Update this plan's status after each milestone rather than treating fixture tests as proof of a working daily workflow.
