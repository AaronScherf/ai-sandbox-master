# Academic Hub Corpus Health Orchestrator: Implementation Plan

**Status:** IMPLEMENTATION IN PROGRESS; the user authorized implementation on 2026-10-08. Tasks 1–5 are implemented in the task worktree; repair execution and scheduler installation remain gated.
**Date:** 2026-10-08
**Spec:** `docs/superpowers/specs/academic_hub/2026-10-07-corpus-health-orchestrator-design.md`
**Related review:** `docs/brainstorms/2026-10-07-corpus-orchestrator-codex-plan-review.md`

## Goal

Build one Python CLI that scans the academic-hub corpus for missing or stale expected outputs, reports Git state, and eventually lets the user approve and apply narrowly scoped repairs through existing pipelines. The daily scan must run without an agent, make no API calls, and make no corpus writes. Later phases add durable decisions, a local review page, writer coordination, and selected repair adapters.

The first shipped milestone is a useful read-only report. It can be approved and used on its own; the full review and repair system is not a prerequisite for getting value from the scan.

## Architecture

Expose a single command entry point, `python -m tools.corpus_health`, with separate `scan`, `review`, and `apply` commands. Start with the scan command and keep it useful without a browser, decision ledger, or repair support. Add these capabilities only in later milestones.

Keep the orchestration package under `tools/corpus_health/`. Its planned modules are `cli.py`, `discovery.py`, `finding.py`, `report.py`, and later `state.py`, `review_server.py`, `writer_lock.py`, and `actions.py`. The package calls public helpers in existing pipelines/indexer where those helpers provide a read-only contract; it must not parse `.index/` files independently. Add a narrow read-only index audit API if the current public functions cannot answer the needed questions.

Store local operational state under a directory derived from the monorepo Git common directory, for example `<git-common-dir>/corpus-health/`. This keeps reports and decisions outside tracked files and shared across outer-repository worktrees. Store root-specific manifests, findings, and append-only run reports there using atomic replacement. The scanner must still work if the state directory is unavailable by printing a read-only report and returning a clear partial-status code.

The local review page is served only when `review` is invoked. A scheduled `scan` updates the pending queue and exits. `review` starts a short-lived Python standard-library HTTP server bound to `127.0.0.1`, opens the browser, validates its per-run token and request origin, and records each accepted/declined/deferred choice in local state. `apply` is a separate invocation, so reviewing an item never starts a pipeline implicitly.

## Verified constraints and capability inventory

This is the current understanding from the package READMEs and code paths. Task 1 must verify exact flags, destinations, and behavior against implementation before any adapter is enabled.

| Operation | Safe discovery today | Scope and side effects | Plan treatment |
|---|---|---|---|
| `route_notes_transcribe` / `transcribe_notes` | `route_notes_transcribe --dry-run` lists eligible files; direct transcription also supports `--dry-run` and `--file` | Cost-routed local extraction/Gemini; writes Markdown and index artifacts. Outputs are under the separate `academic_notes/` repository for the hub. | Scan expected outputs in MVP. Keep apply disabled until `academic_notes/` sync quiescence and shared writer coordination are established. |
| Excalidraw transcription | `transcribe_excalidraw --dry-run`, with `--file` | Gemini vision/expansion; writes raw and RAG Markdown under `academic_notes/` and indexes results. | Same notes-repository write gate as transcription. |
| Notes postprocessing | `postprocess_notes` has `--dry-run` and `--file` | May call Gemini; edits existing Markdown and its change log. | Discover only initially; require shared lock and sync gate before apply. |
| Textbook conversion | Duplicate precheck can identify exact/fuzzy matches; image description supports `--dry-run` and `--book` | Main conversion is a documented GCP/VM batch with multiple PDFs. Image description uses Gemini and writes the final `.rag.md` to `academic_notes/`. | Report missing conversion/output. Do not automate cloud/VM conversion in v1; it lacks a suitable end-to-end single-item local action boundary and sync-safe final destination. |
| Essay conversion | `convert_essays --dry-run` and `--file` | DOCX conversion is local; indexing adds Gemini calls unless `--no-index`. Defaults to `research/`, outside the hub. | Out of the hub scanner's initial corpus scope unless a configured hub root explicitly includes it. Inventory only; no adapter in MVP. |
| Journal-article conversion | `convert_journal_articles --dry-run` and `--file` | Cost-routed transcription and index hook; defaults to `research/`, outside the hub. | Out of the initial corpus scope; do not scan all research folders by accident. |
| Index `rebuild` | No non-mutating preview identified; `rebuild` supports course, force, and prune options | May generate/update cards and aggregates; `force`/`prune` are broad mutations. | Never use for discovery. First add/use a read-only index audit API. No apply until scope and lock behavior are verified. |
| Index `retag` / `chunk` | Both expose dry-run behavior; chunk can be file-scoped | Actual work can update index data and Markdown frontmatter, and can call models/embeddings. | Inventory exact side effects and costs. Do not infer that dry-run output is a per-file action API. |
| `duplicate_check` / `audit_metadata` | Duplicate check is local and can build a conversion list; metadata audit has targeted/recheck behavior | Duplicate review or audit can update ledgers, cards, folders, or Markdown; the metadata audit is primarily for journal articles. | Treat as specialized follow-up operations, not generic scan primitives. |

`academic-hub/` belongs to the outer monorepo. `academic_notes/` is a separate nested repository and is not populated in an outer worktree. Resolve both roots explicitly and report a missing live notes checkout as unavailable. Do not access or stage the user’s untracked `academic_resources/` content during development tests.

The academic-rag-model guidance says not to inspect `.index/` directly. Use or add a supported read-only index API for card/chunk freshness. `index_search rebuild` is a mutation, not an audit operation.

## Global constraints

- Discovery is read-only and performs no API or cloud calls. It must report scan failures and inaccessible roots rather than claiming the corpus is healthy.
- An extension is not enough to classify arbitrary Markdown. Use an explicit category/policy map or pipeline marker; put ambiguous files in an informational group, not in automatic repair proposals.
- A finding records the root, course/category, kind, source fingerprint, current path, expected output, evidence, and suggested action. Path is a location; a content fingerprint is used to notice renames and invalidate stale decisions.
- Do not copy source-document text into reports. Use paths, hashes, metadata, and short titles only.
- No action may write outside configured roots. No action stages or commits files or touches Git history.
- No cloud/VM textbook conversion in v1. Paid/API actions require an explicit decision tied to the exact source fingerprint. Until the user approves batch cost policy, accept costly actions per source.
- v1 does not write to `academic_notes/`. An action targeting that repository stays blocked until sync quiescence is designed and the user approves the write boundary.
- The local UI binds only to loopback, uses a per-run token and Origin validation, exposes no cross-origin endpoint, serves no source content, and shuts down after review or timeout.
- Do not add a third-party web dependency for the first review-page implementation.
- Tests use synthetic fixtures and temporary repositories. Never use the live corpus as a write target in tests.

## Rollout and tasks

## Implementation progress (2026-10-08)

- **Tasks 1–5 implemented:** recorded the pipeline capability inventory; added a read-only Markdown index audit API; implemented configured source/output, frontmatter/index, and Git-state scanning; added a persistent local decision ledger; and added a loopback-only local review page with per-item and homogeneous-group decisions.
- **Verification:** 24 focused audit/orchestrator tests pass; the full `tests/core/indexer` suite passes (457 tests); the full `tests/tools` suite passes (96 tests); package compilation passes. The scanner has not yet been run against the live corpus, and no scheduler task was installed.
- **Task 6 local coordination implemented for selected writers:** the shared OS lock now covers the direct note PDF, Excalidraw, and router CLIs; academic-hub notes postprocessing; local textbook image description; and index `rebuild`, `chunk`, `retag`, and standalone subset-linking CLIs. Multiprocess lock tests and CLI contention tests cover the protocol. Other direct writers remain unsupported for overlapping repair adapters until adopted or separately excluded; the remote converter and Obsidian sync are outside the local lock.
- **Task 7 implemented on `codex/corpus-health-apply` (pending landing):** `apply --accepted` rechecks the current scan and records blocked, failed, and verified applied outcomes. Its only executing adapter runs an exact-`file_id` index chunk command under the shared writer lease and confirms the result with the read-only index audit. Card reconciliation, note writes, and remote textbook conversion remain disabled. Review acceptance still records intent only and never starts a pipeline.
- **Task 7 notes-adapter deferral (2026-10-09):** the user wants note transcription,
  Excalidraw, enhancement, question-resolution, and postprocessing repairs kept out
  of this apply rollout. Continue reporting their gaps, but do not invoke the
  current source pipeline from `apply`: first fix its known content/visual/question
  quality failures, reprocess and review affected outputs, then revisit a notes
  adapter. The `academic_notes/` sync-quiescence gate also remains mandatory.
- **Task 8 partially documented:** the package README documents direct discovery-only invocation for manual scheduling. Actual scan duration and a live-corpus observation period remain outstanding.

### Task 1: Verify the pipeline capability matrix and source/output policies

**Files:**

- Create: `docs/status/academic_hub/2026-10-08-corpus-health-capability-inventory.md` —
  `academic_hub` is a new status subfolder name, not an existing package. It groups
  this cross-cutting effort rather than mapping to one existing package the way
  other `docs/status/<package>/` subfolders do. Confirm this is intended, or rename
  to `docs/status/corpus_health/` to match the new `tools/corpus_health/` package
  before this doc accumulates history under it.
- Read: the package READMEs and entry points named in the spec and matrix above.

**Steps:**

- Record exact discovery flags, file-selection limits, output paths, API/cloud behavior, idempotency/caching, and verification for each operation.
- Confirm the actual Markdown categories that require frontmatter/index cards, including summaries and enhanced guides such as `wald_lm_lr_tests.enhanced.e1.md`.
- Identify exact source-to-output path rules from `core/env/academic_hub_paths.py`; list exclusions such as raw textbook assets and generated sidecars.
- Record which proposed repairs are unavailable because they lack file scope, preview, or a safe write destination.
- Keep `convert_essays` and `convert_journal_articles` out of the default hub roots; document how an explicit additional corpus root would opt them in later.

**Acceptance:** The inventory distinguishes verified behavior from assumptions and is sufficient to decide which findings the scanner can report without running a pipeline.

### Task 2: Add a read-only index audit contract

**Files:**

- Modify: `core/indexer/index_search.py` or a small adjacent public audit module, based on the API inventory.
- Add: focused tests under `tests/core/indexer/`.

**Steps:**

- Expose a function that compares eligible Markdown/source identities with existing index-card and chunk state without writing, embedding, or making API calls.
- Return typed status records (indexed/current, missing card, stale card, missing/stale chunks, unreadable/unknown) and evidence sufficient for the report.
- Reuse `compute_file_id()` and existing card lookup/schema helpers rather than duplicating identity rules.
  `compute_file_id()` is currently typed and named for PDFs (`pdf_path: str` in
  `core/indexer/index_card.py`); verify it actually generalizes to Excalidraw and
  Markdown sources before relying on it as *the* content-fingerprint source across
  all finding kinds, or add a parallel identity function for non-PDF sources rather
  than assuming one identity rule already covers every root this scanner touches.
- Keep this API independent of private JSON layout so later index schema changes do not require the orchestrator to parse `.index/` itself.

**Acceptance:** Tests against temporary synthetic roots show accurate status, no writes, no client creation, and no model calls. A missing or malformed index is reported as incomplete, not silently treated as an empty healthy index.

### Task 3: Ship the read-only scanner MVP

**Files:**

- Create: `tools/corpus_health/__init__.py`, `tools/corpus_health/__main__.py`, `tools/corpus_health/cli.py`, `tools/corpus_health/discovery.py`, `tools/corpus_health/finding.py`, `tools/corpus_health/report.py`, and `tools/corpus_health/README.md`.
- Add: focused tests under `tests/tools/corpus_health/`.

**Steps:**

- Implement `python -m tools.corpus_health scan --config <path> [--format text|json] [--output <path>]`.
- Walk only configured `academic_resources/` and available `academic_notes/` roots; match known source categories to expected output conventions and skip ignored/hidden/cache/resource paths as determined by Task 1.
- Report missing transcription and textbook outputs, frontmatter/index gaps only for configured Markdown categories, ambiguous pairings, scan errors, and each root’s availability.
- Check output existence and metadata first. Do not call every pipeline’s `--dry-run`; do not hash entire large textbooks. The MVP may report current missing outputs each run without retaining decision history.
- For hub index facts, call the read-only API from Task 2. For Git facts, reuse `tools.git_workflow` helpers for the outer monorepo and use separate read-only Git commands for the configured nested notes repo.
- Exempt only the verified device-local `academic_notes/` churn: its generated `.gitignore` and the Fit plugin's own `main.js`/`styles.css` at exact configured relative paths. Do not suppress all files with those names. Keep exception decisions in a named configuration constant and report their occurrence in an informational count.
- Print a useful summary even when optional roots are absent. Return a distinct nonzero status when required roots are unavailable or the scan was incomplete.
- Document a direct Windows Task Scheduler command that invokes `scan`; do not install a scheduled task from the CLI.

**Acceptance:** The scanner produces a deterministic text and JSON report on a synthetic corpus; is idempotent; makes no writes under the corpus; uses no credentials/network/model; reports absent roots and scan errors; and has a small-course manual comparison procedure. This milestone is usable without the local page, decision ledger, or repair system.

The `scan` command is ready to schedule as soon as this task passes. Do not wait for the ledger, review page, writer lock, or repair adapters before using the read-only report daily.

### Task 4: Add durable finding state and recurrence rules

**Files:**

- Create: `tools/corpus_health/state.py` and `tests/tools/corpus_health/test_state.py`.
- Store runtime state under `<git-common-dir>/corpus-health/` (not in tracked docs or the vault).

**Steps:**

- Version the local manifest and decision ledger; write updates with temp-file plus atomic replace.
- Use a finding key based on root, course/category, finding kind, and source fingerprint; preserve the current relative path separately. If identical content appears at a new path while its prior path is absent, keep the new location pending and flag a possible rename-or-duplicate ambiguity instead of inheriting the old decision. Matching bytes alone cannot distinguish a rename from a reused or duplicated source.
- Record statuses `pending_review`, `accepted`, `declined`, `deferred`, `applied`, `failed`, and `vanished` with timestamps and evidence.
- Keep unchanged declined items out of the new-items view until the source fingerprint changes. Keep deferred items visible in their own view but do not label them new on each scan. Make showing dismissed/deferred items explicit.
- On changed source, destination, or action parameters, invalidate acceptance and return the finding to pending review. On disappearance, mark vanished without deleting history.
- Allow the scanner MVP to run if state is unreadable or unavailable, but clearly report that it cannot classify new versus recurring findings.

**Acceptance:** Tests cover repeat scans, identical content at a new path without decision inheritance, changed content, unchanged declines, deferrals, disappeared sources, malformed state recovery, and serialized concurrent writes with an intact atomic ledger.

### Task 5: Add the local review page

**Files:**

- Create: `tools/corpus_health/review_server.py`, `tools/corpus_health/static/review.html`, and `tests/tools/corpus_health/test_review_server.py`.
- Modify: `tools/corpus_health/cli.py`.

**Steps:**

- Implement `review [--group <kind>] [--timeout <seconds>]` to load pending entries from state, start the local server on an ephemeral port bound to `127.0.0.1`, and open the browser.
- Display source, destination, finding evidence, proposed action, API/cloud tier, and expected writes without embedding document contents.
- Support accept, decline, and defer per item, homogeneous group, and all items in the current group. Do not offer one-click batch acceptance across cost tiers.
- Run one corpus scan when the review session starts, then validate all submitted finding ids, action signatures, and fingerprints against that snapshot. Do not rescan the corpus for each click; later source changes are caught by the next scan and must be revalidated immediately before any future apply action.
- POST decisions to the server; validate the run token and Host/Origin before persisting a decision.
- Shut down cleanly on completion, timeout, Ctrl-C, or an explicit close request from the page. If the server cannot start, provide a clear diagnostic without editing the ledger.
- Keep review separate from apply: acceptance updates state only.

**Acceptance:** Local HTTP tests prove valid decisions persist; missing/invalid token, bad Origin/Host, stale fingerprint, and unknown finding are rejected; server binds to loopback; shutdown clears the listener; and no source contents are served.

### Task 6: Implement shared writer coordination before enabling repairs

**Files:**

- Create: `core/env/corpus_write_lock.py` and `tests/core/env/test_corpus_write_lock.py`.
- Modify only the writer entry points selected by the capability inventory; likely candidates include note transcription/router, Excalidraw transcription, postprocessing, relevant index mutations, and image description.
- Do not adapt the remote textbook conversion path in this task unless a real lock protocol can cover its GCP/GCS writer lifecycle.
- This task touches up to five separate pipelines plus the new lock module. Land the lock module and its tests first, then adopt it into one pipeline at a time as separate commits (or separate task branches) rather than one large diff, so each adoption gets its own full-suite landing check and review surface.

**Steps:**

- Define the shared lock identity from canonical repository roots and store lock records in local operational state, not tracked corpus directories.
- Implement an OS-level exclusive lock with owner/run metadata. A second writer fails with the active owner/action/roots instead of racing.
- Support nested calls within one run using a random run token passed through the child process environment; verify that token against the held lock before allowing a child command to join.
- Make every supported standalone writer acquire the same lock before its first write. Cover both the outer monorepo corpus/index and any enabled nested repository separately.
- Keep an orchestrator-only lock from being treated as sufficient. If an existing manual pipeline has not adopted the protocol, disable its apply adapter.
- External Obsidian sync cannot be serialized by this local lock. Leave `academic_notes/` writes disabled until an explicit sync-quiescence process is agreed and can be enforced or reliably acknowledged for each run. Require the same for any target affected by a live Obsidian Git sync.

**Acceptance:** Multiprocess tests show two supported writers cannot overlap; a same-run child can safely join; stale lock recovery is conservative; and all enabled command entry points refuse an uncoordinated concurrent write. Unsupported external sync remains an explicit gate, not a false claim of lock coverage.

### Task 7: Add the `apply` dispatcher and the first safe repair adapters

**Files:**

- Create: `tools/corpus_health/actions.py` and focused tests.
- Modify: `tools/corpus_health/cli.py` and only adapters approved by the inventory and writer/sync gates.

**Steps:**

- Implement `apply --accepted` to select accepted, still-current findings only; verify source fingerprint, configured root, action parameters, cost category, output destination, and writer lock immediately before execution.
- Invoke module entry points with `subprocess.run([...])`, never shell-concatenated commands. Pass explicit roots and file names; capture redacted logs and exact exit status.
- Start with deterministic, low-cost actions that have precise scope and supported verification. Expose no action whose current pipeline only supports a broad batch.
- Keep paid/API actions per item by default; add homogeneous batch acceptance only after the user chooses that policy. Never auto-run textbook GPU/VM conversion in v1.
- Defer note/Excalidraw/enhancement/question-resolution/postprocess actions for this
  rollout. Keep their findings discoverable, but explain that the source pipeline
  must first be fixed, affected outputs reprocessed and reviewed, and the
  `academic_notes/` sync-quiescence gate resolved before these adapters return.
- After each action, invoke the read-only scanner/audit for the affected item and mark `applied` only when the expected output and index state are verified.
- Continue unrelated accepted actions after one failure; record each independently.

**Acceptance:** Fixture tests verify stale approval rejection, exact input selection, no shell execution, no call without lock, no call outside configured roots, per-action error recording, and post-action verification. Integration tests use stub commands, not paid APIs or GCP.

### Task 8: Schedule discovery-only operation and observe it

This task is independent of Tasks 4-7 and can be done immediately after Task 3. It is listed after the repair design here to keep the implementation stages together, not as a prerequisite to daily scanning.

**Files:**

- Modify: `tools/corpus_health/README.md` or package documentation and root package map.
- Optional: provide a documented PowerShell `schtasks` example; do not create the user's task automatically.

**Steps:**

- Measure scan time, roots/files visited, metadata checks, and any content hashing on the configured corpus.
- Document a Windows Task Scheduler command with an absolute interpreter, fixed working directory, explicit config, and log destination.
- Configure discovery-only execution first. The task must have no review UI interaction and no apply rights.
- Observe reports across a trial period, compare findings with manual review, and tune only from evidence. Consider scheduled automatic actions only in a later policy decision.

**Acceptance:** A scheduled run completes without an agent or interactive desktop, reports failures through exit status/log, does not start a browser, and does not mutate corpus or Git state.

## Proposed defaults and decisions to confirm

- **Cloud approval:** per source for any API/cloud action until the user explicitly approves homogeneous batch decisions.
- **Nested notes writes:** disabled in the first scanner milestone and while sync quiescence cannot be established. Decide later whether the local page may enable those actions during a controlled sync pause.
- **Markdown rules:** only categories in the explicit inventory/config are eligible for frontmatter/index findings; unknown Markdown is informational.
- **Decline retention:** suppress an unchanged declined source until its content or expected action changes; deferred findings remain reviewable but are not re-announced as new.
- **Pipeline overlap:** repair adapters remain unavailable until the participating direct CLI writers honor the shared lock. An orchestrator lock alone does not satisfy this gate.

These defaults are intentionally conservative and can be changed during plan review without changing the independent value of Tasks 1-3.

## Out of scope

- Implementing the project-wide `what_to_do_today`/project-steering workflow. It is a separate to-do item and may reuse a future generic local review-page pattern, but it has different data, ranking, and decision semantics.
- Modifying Obsidian plugin settings or sync rules.
- Changing Git commit/merge/push behavior or automatically cleaning branches/files.
- Reading or copying third-party source text into reports.
- Running this plan against the live corpus or invoking paid/cloud pipelines during development.
