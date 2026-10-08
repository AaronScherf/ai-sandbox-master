# Academic Hub Corpus Health Orchestrator: Design

**Status:** DRAFT, for user review; no implementation or scheduled task is authorized by this document alone.
**Date:** 2026-10-07
**Scope:** discovery, review, and explicitly accepted repair of gaps across the academic-hub corpus and its related Git checkouts.
**Source brainstorm:** `docs/brainstorms/2026-10-07-corpus-orchestrator-codex-plan-review.md`.

## Motivation

The academic corpus is maintained by multiple independent pipelines. Notes may need transcription or postprocessing; textbooks may need conversion and image description; generated Markdown may need frontmatter or index cards; index records can become stale; and repository state can drift. Today these checks are run as needed by an agent or manually through each pipeline.

The goal is a normal Python program that can run a cheap daily scan without starting an agent, identify only new or unresolved gaps, and present concrete repair proposals. A human decides which proposals to apply. Accepted work is delegated to existing pipeline entry points, then checked again. The tool must not silently spend API or cloud budget, write to ambiguous destinations, or modify Git history.

This design incorporates the findings in the Codex plan review: reuse existing Git and reconciliation helpers, establish a per-pipeline capability inventory before implementation, make daily discovery manifest-first, keep durable decision state, and distinguish the code repository from the corpus and notes repositories.

## Goals

- Detect unprocessed sources and incomplete generated outputs across configured courses.
- Detect missing or stale Markdown frontmatter and index records where the existing index data can establish that state.
- Report repository cleanliness and branch state for each repository that is actually available to the run.
- Avoid re-presenting unchanged declined or deferred findings as new on every daily scan.
- Let a human review proposed work before any repair is run.
- Apply only selected, still-current proposals through existing pipeline entry points.
- Verify outcomes and retain an auditable local run history.
- Support Windows Task Scheduler or an equivalent OS scheduler invoking Python directly; no agent turn is required for discovery.

## Non-goals

- Commit, push, merge, rebase, delete branches, clean files, or synchronize repositories.
- Decide ambiguous source-to-output relationships automatically.
- Replace the conversion, transcription, metadata, or indexer implementations.
- Convert every new textbook automatically or authorize recurring API/cloud spend.
- Make unattended repairs the default. A later policy may explicitly enable a narrow, deterministic repair class.
- Treat the contents of third-party source documents as instructions to the orchestrator.

## Repository boundaries

The tool treats these roots separately and reports their status independently:

| Root | Role | Orchestrator behavior in v1 |
|---|---|---|
| `ai-sandbox/academic-rag-model/` | Python code and orchestrator | Read code/config; store local operational state outside tracked source; no Git mutations. |
| `ai-sandbox/academic-hub/` | Corpus resources and tracked `.index/`; this directory is part of the outer monorepo, not a separate Git repository | Read sources and index records during discovery. Write only outputs from explicitly accepted repairs, subject to the pipeline inventory and writer coordination. No commits. |
| `ai-sandbox/academic-hub/academic_notes/` | Separate nested Git repository, tablet-synced Obsidian vault | Report its state when the live checkout is available. In v1, do not write to, commit, or trigger sync in this repository until coordination with the sync process is designed and implemented. |

An outer Git worktree does not contain the ignored `academic_notes/` checkout. The orchestrator must resolve its configured live path explicitly and must report “unavailable” rather than silently treating a missing nested checkout as an empty vault. `tools/git_workflow.py` and `tools/active_work.py` provide reusable outer-monorepo worktree and dirty-file reporting. They do not, by themselves, model the nested notes repository or determine whether two corpus trees are semantically synchronized.

The daily run is read-only with respect to corpus outputs. An orchestrator-only lock is not sufficient for later repairs: a manually launched pipeline does not know about it and could write the same output concurrently. Before enabling any apply adapter, every participating local writer must honor a shared corpus-write lock (or the adapter must have another verified exclusion mechanism). The lock must cover the whole action, identify its owner and target roots, and fail clearly rather than allowing a second writer to proceed. An external sync process cannot honor that lock unless specifically integrated; `academic_notes/` therefore remains read/report-only until a safe sync-quiescence protocol is established. A write adapter must be disabled when it cannot establish exclusive ownership of its destination.

## User workflow

The workflow has four explicit phases:

1. **Discover:** perform the cheap, read-only manifest scan and produce typed findings. Optionally run a heavier validation scan when requested.
2. **Review:** open the locally hosted review page for pending proposals. The reviewer can accept, decline, or defer each item, a homogeneous group, or all items in a group. The page writes decisions directly to the orchestrator ledger; raw state is not edited by hand.
3. **Apply:** revalidate each accepted finding against its current source identity and destination, then invoke the existing command with explicit paths/options. A changed source invalidates the old acceptance and returns the item to review.
4. **Verify:** re-scan affected items, mark successful work applied, and record failures or remaining gaps.

Manual invocation should support discovery-only, review refresh, and application of already accepted items as distinct operations. A scheduled invocation performs discovery and refreshes pending review state only; it never interprets absence of a reviewer as approval.

### Local interactive review page

The user clarified that the required behavior is an interactive webpage, not dependence on a Claude-hosted Artifact. The orchestrator will generate and serve a local review page when the user invokes its review mode. The daily scheduled scan only updates pending findings; it does not need an agent or an open browser. A later `review` invocation starts a short-lived Python server, opens the browser, and loads pending findings from the local ledger.

The first implementation can use Python's standard-library HTTP server and generated HTML/JavaScript, avoiding a new web framework. It binds only to `127.0.0.1`, uses a per-run token for decision requests, validates the request origin, exposes no cross-origin API, serves no source-document contents, and shuts down after review or timeout. Decisions are POSTed to the local process, validated against current finding fingerprints, and persisted directly into the local ledger. The UI shows each item and supports individual choices plus accept/decline/defer for a homogeneous group and accept/decline/defer all within the displayed group. Applying accepted actions remains a separate command, so clicking accept records approval but does not start potentially costly pipelines unexpectedly.

The page groups items by repair type and shows source, expected output, reason, current fingerprint, proposed command, destination, estimated API/cloud use, and expected writes. A batch control applies only to the displayed, homogeneous action group; it cannot combine free/local and paid/cloud work. Each accepted item is bound to the exact finding fingerprint and expires when its source, destination, or action parameters change. The run record stores who/when only to the extent available locally (for example, OS account and timestamp); it does not transmit data to an external service.

This is a local analogue of the project’s interactive Artifact convention, not a Claude Artifact. The user’s clarification authorizes this substitution for the standalone orchestrator. The review interaction must remain usable without launching an agent.

## Discovery and findings

### Cheap daily pass

The default scan uses directory enumeration, file metadata, known output conventions, manifests, and index-card metadata. It must not invoke model APIs, cloud conversion, or expensive pipeline dry-runs. It maintains a per-root manifest containing normalized relative path, file type, size, modification time, and last verified content fingerprint. New or changed candidates receive a content hash before they are proposed. A metadata-only change can trigger revalidation without automatically implying a content change.

Candidate matching uses explicit pipeline output conventions and stable source identifiers where available (for example, the indexer's content-derived file identity). Findings retain the current path as a location, not as the sole identity, so a rename can update the location for unchanged content. If two sources or outputs could match, report an ambiguity instead of selecting one. The scan records scan errors and inaccessible roots; an incomplete scan cannot be reported as healthy.

The manifest is an optimization, not the authority for whether an output is valid. Existing source files, outputs, manifests, and index records remain the evidence. A periodic or on-demand deeper pass may invoke supported read-only checks to catch cases that file metadata alone cannot detect.

### Finding kinds

Initial finding types are:

- `note_transcription_missing`: eligible PDF/image/Excalidraw source without its expected processed output.
- `textbook_conversion_missing`: eligible textbook source without a converted resource-side Markdown output.
- `textbook_rag_output_missing`: converted textbook missing expected tablet-side `.rag.md` output.
- `markdown_frontmatter_missing`: generated Markdown known to require frontmatter but missing it or required fields.
- `index_card_missing` / `index_card_stale`: index record absent or inconsistent with its source/output identity.
- `index_chunks_missing_or_stale`: passage data missing or stale where this can be verified cheaply.
- `metadata_mismatch`: a specific known metadata inconsistency supported by an existing audit.
- `git_state`: dirty/uncommitted files, branch divergence, detached state, or unavailable checkout.
- `ambiguous_pairing`, `unknown_input`, `scan_error`: findings requiring classification or operator attention, never automatic repair.

The linked `wald_lm_lr_tests.enhanced.e1.md` is a useful concrete example of generated study-guide Markdown. Its presence demonstrates why file extension alone cannot determine whether frontmatter/indexing is expected: the scan needs a configurable category/policy or an explicit source marker, and should report uncertain classifications rather than infer that every Markdown file needs repair.

For the nested `academic_notes/` Git report, status handling must recognize the specific device-local sync churn recorded in `docs/status/2026-09-21-obsidian-git-sync-status.md` and `docs/trackers/academic_hub_to_do.md`: the generated `.gitignore` can be rewritten from each device's Direct Git Sync settings, and the Fit sync plugin may leave its own `main.js` and `styles.css` out of sync. These are informational/exempt from actionable drift findings only at the verified plugin paths; do not suppress every file with those basenames. Confirm the exact plugin-relative paths from repository facts available to the implementation without reading prohibited private settings. Keep the exception list narrow, documented, and testable.

### Durable decision state

Maintain a local, versioned ledger and append-only run records under an ignored operational-state directory owned by the orchestrator. Do not put ephemeral decisions in tracked code docs or hand-editable vault Markdown. The exact state path and backup policy are implementation-plan decisions; it must survive normal code updates and be excluded from commits.

Each finding has a stable kind, root identifier, source fingerprint, current relative path, expected output, first/last seen time, last observed evidence, status, and any decision/apply metadata. Status transitions are:

`new -> pending_review -> accepted | declined | deferred -> applied`

Failures return to `pending_review` or `deferred` with the failure recorded. A finding whose source disappears is marked resolved/vanished rather than deleted from history. Declines suppress the same unchanged finding; a changed source fingerprint creates a new reviewable finding. Deferred items remain visible in a deferred view without being presented as new each day. An accepted item is invalidated if its fingerprint, destination, or action parameters change.

## Pipeline capability inventory prerequisite

Before orchestrator implementation, create a checked-in inventory for each supported pipeline/operation. For each entry record: non-mutating discovery support; explicit-file versus whole-batch scope; expected inputs and outputs; local/API/cloud behavior and likely cost; writes and side effects; idempotency/restart behavior; and verification method. Confirm behavior from code and package README, not only command help.

The first inventory should cover:

| Operation | Existing entry point to assess |
|---|---|
| Note transcription and Excalidraw transcription | `pipelines.transcribe_notes.transcribe_notes`, `route_notes_transcribe`, and `transcribe_excalidraw` |
| Postprocessing | `pipelines.postprocess_notes` |
| Textbook conversion and follow-up outputs | `pipelines.convert_textbook.convert_textbook`, `describe_images`, and relevant output preparation |
| Essay conversion | `pipelines.convert_essays.convert_essays` |
| Journal-article conversion | `pipelines.convert_journal_articles.convert_journal_articles` |
| Index reconciliation and metadata | `core.indexer.index_search` (`rebuild`, `retag`, `chunk`), `core.indexer.duplicate_check`, and `tools.audit_metadata` |

An operation without safe preview or explicit scope is not called by the orchestrator until a narrowly scoped, non-mutating interface is added and reviewed. The orchestrator must not fake per-file scope by invoking a broad batch and hoping existing outputs are skipped.

## Applying accepted work

Application uses Python subprocess argument arrays with explicit working directory, roots, and file selection; it does not interpolate shell strings. It calls documented module entry points rather than duplicating pipeline logic. Before invocation it verifies:

- the exact source fingerprint still matches the reviewed proposal;
- output roots resolve to the intended configured repositories;
- the operation's cost/side-effect category matches the acceptance;
- the shared writer lock is held for the target roots and no competing supported writer is active;
- the target repository is available and, for writes, meets the v1 writer/sync constraints.

The application step records command, selected inputs, start/end time, exit code, output paths, and redacted logs. It must not capture or print secrets. Each action is restartable and idempotent to the degree the underlying pipeline supports; partial failure is retained and does not cause unrelated accepted actions to be marked successful.

No Git operation is part of apply. An accepted indexing action may write index artifacts as documented by the indexer, but does not stage or commit them. Actions whose only available implementation mutates a broad corpus, writes outside configured roots, cannot acquire the shared writer lock, or cannot establish sync quiescence remain blocked findings with a concrete prerequisite. The lock cannot protect against tools that have not adopted it; such tools must be adapted before they are allowed to overlap an orchestrator write. Cloud/VM textbook conversion remains outside automated apply until its remote writes can participate in the same single-writer protocol.

## Git status checks

Reuse `tools/git_workflow.py` and `tools/active_work.py` for the monorepo’s worktree, dirty-file, and branch comparison facts instead of implementing parallel Git parsing. Extend them only if the orchestrator needs a repository-neutral read-only helper. Use Git status separately for the live nested `academic_notes/` repo when it exists.

The current `academic-hub/` directory is not a separate Git repository; it is tracked within the outer monorepo. Report its content changes as part of that repository’s status, not as an independent branch. Repository-level divergence is not proof that generated content is synchronized across roots. Any semantic comparison between resources and notes must use the established path mapping and content identities, and must report expected exclusions (such as textbook raw sources) explicitly.

Git findings are diagnostic. The orchestrator never repairs them, and branch staleness requires a declared base/remote and policy before it can be meaningfully reported. Missing remote data or an unavailable notes checkout must be explicit in the report.

## Proportional rollout

The full design adds a local HTTP review server, persistent decision state, shared writer coordination, and multiple pipeline adapters. Those are follow-on infrastructure, not prerequisites for the first useful result. The first independently usable milestone is a read-only scan command that prints and saves a current report of missing expected outputs and repository status; it requires no review server, action ledger, or repair execution. It can be run manually or scheduled as a simple daily report. Later phases add deduplication of recurring findings, interactive decisions, and only then safe repairs. Each phase should be reviewable and useful on its own; approval of the full repair system is not required to use the scanner.

## Scheduling and operation

On Windows, the intended scheduler is Windows Task Scheduler invoking the repository’s Python entry point directly with a fixed working directory and explicit config. It is not an agent-dispatched schedule. The first rollout schedules discovery-only runs. Scheduler installation, credentials, and run-as-user permissions are documented separately and are not performed by the application itself.

Daily work is bounded: enumerate configured roots, compare source/output existence and indexer-provided status, and write a concise report. Once the ledger phase exists, it also updates local finding state; the separate review command serves the pending queue when requested. Deeper validation is explicitly opt-in until measured scan-time and resource cost are known. Every report includes duration, roots scanned, files considered, fingerprint work, and incomplete/error counts so the daily scan's actual cost can be assessed.

## Configuration and reports

Roots and scan policies are explicit configuration, not inferred from whichever checkout happens to be current. Configuration includes the academic-hub root, live notes-repo path, enabled courses/categories, source/output rules, excluded paths, scheduler mode, and supported action policies. Secrets remain in the existing environment configuration and are never copied into the ledger or reports.

The run report summarizes findings by type and state, repository availability/status, actions proposed/applied/failed, scan duration, and identifiers for review items. Machine-readable state is for program use; human decisions happen in the local review page. Reports must avoid copying copyrighted source text; paths, hashes, metadata, and short non-content labels are sufficient.

## Rollout

1. **Inventory:** verify each operation's safety, scope, cost, output, and verification properties; map source categories and expected-output rules, including generated summaries such as enhanced study guides.
2. **Read-only scanner MVP:** implement a current-state report for missing expected outputs and repository status. This milestone is independently useful and can be run daily before review UI or repairs exist; compare its findings with manual checks on a small set of courses.
3. **Local review page:** implement the loopback-only page and verify decisions persist to the ledger, stale approvals are rejected, and the server is inaccessible from non-loopback interfaces.
4. **Ledger and policy:** implement stable identity, decision states, fingerprint invalidation, and state migration/version behavior.
5. **Shared writer coordination:** establish a lock contract honored by each local writer the orchestrator may invoke; document external sync quiescence and keep unsupported writers disabled.
6. **Repair adapters:** add one operation at a time, starting with the least costly and most precisely scoped, then verify against fixtures and a controlled corpus sample. No repair adapter ships ahead of the writer coordination required for its destination.
7. **Schedule:** measure scan runtime, install a discovery-only Windows Task Scheduler job, inspect reports through a trial period, and only then consider any unattended deterministic repairs.

## Open decisions

1. **Cloud approval granularity:** may a human accept a homogeneous batch of paid/API or cloud actions, or must each textbook/source be accepted individually? The UI supports group actions, but the policy for costly groups needs confirmation.
2. **Notes-repo writes:** v1 keeps `academic_notes/` read/report-only. Is that acceptable even though it delays automatic application of transcriptions whose outputs belong there, or should a separately designed sync-aware writer be included before v1?
3. **Finding policy:** which generated Markdown categories (including summaries, problem sets, and enhanced guides) require frontmatter and indexing, and where should those rules be configured?
4. **State retention:** should unchanged declined findings be suppressed indefinitely until the source changes, or should they reappear after a user-selected interval?

## Next step

Resolve the remaining policy decisions, especially cloud approval granularity and the notes-repo write boundary. The read-only scanner may be approved and delivered as an independent first milestone; later phases require their own scope and safety decisions. The implementation plan should begin with the pipeline capability inventory and preserve this staged approval boundary.
