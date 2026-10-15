# Consolidated notes pipeline + SVG backup — design spec

**Status:** draft, Stage 1 (below) implemented in this branch; Stages 2-4 are future work.
**Branch:** `claude/notes-pipeline-consolidation`.
**Follows:** `docs/status/transcribe_notes/2026-10-14-subscription-pipeline-investigation.md`
(Codex's investigation; code-verified, no implementation). This spec turns its
"Recommended next design scope" into a staged plan and adds two owner-requested
items it didn't cover: a single consolidated entry point, and a persistent
Excalidraw SVG backup.

## Goals

1. Move the notes pipeline's generative (token-metered) work onto the Antigravity
   Pro subscription wherever the investigation found it safe to do so, without
   silently falling back to metered API calls when the agent is unavailable.
2. Let the owner trigger the whole update for a course with one command/request
   ("update my notes for econometrics") instead of running transcribe, chunk,
   index, and question-resolution as separate invocations.
3. Stop losing Excalidraw plugin auto-export SVGs: keep a persistent copy in
   `academic_resources/` even though the note-adjacent copy in `academic_notes/`
   is overwritten on every note open.

## Verified current state (this session, commit `730c7c2`)

- `route_notes_transcribe.py` already is the "check the whole corpus" orchestrator
  the owner asked about: `build_plan()` walks every course under `academic_notes/`
  (plus marked prior-offering subsets), finds PDFs and Excalidraw pairs with no
  output yet, and `run_plan()` dispatches each to its pipeline. It has no agent-
  driver flags today even though `transcribe_notes.py`'s PDF path (`process_pdf`,
  `AgentDriver`, `agent_submit.submit_doc`) already implements collect/submit
  against `.agent_work/<run-id>/`.
- Per-file index-card generation **is already wired into the transcription path**
  for both PDF and Excalidraw (`_write_markdown_and_index` /
  `transcribe_excalidraw.py`'s own call both call `core.indexer.index_card.
  reconcile_and_write` inline). The investigation's "separate index-card metadata
  from embedding" recommendation is about splitting the *one call inside
  `reconcile_and_write`→`generate_index_card`* into a text step (agent-capable)
  and a numeric embedding step (stays API) — not about wiring indexing into the
  pipeline, which already happened.
- **Not** wired into the transcription path: passage/chunk indexing
  (`core.indexer.chunk_index`, invoked today only via
  `index_search.py chunk --course <course>`) and tagged-question resolution
  (`agent/rag/resolve_questions.py`, a separate CLI scoped by `--course`/`--note`).
  Both are per-course batch operations with no per-file hook, so folding them into
  one command is a call-after-transcription, not a design change to either.
- Excalidraw plugin auto-export: opening a canvas in Obsidian re-writes
  `<name>.excalidraw.svg` (or `.png`) next to the `.excalidraw.md` note under
  `academic_notes/<course>/<category>/`. Nothing copies it to
  `academic_resources/<course>/<category>/` today — confirmed by the untracked
  SVGs sitting in `academic_resources/econometrics/lecture_notes/` in the working
  tree, which only exist because they were moved there by hand. `core.env.
  academic_hub_paths.to_resources_root()` already does exactly the path rewrite
  (`academic_notes/` → `academic_resources/`, same course/category/filename)
  needed to compute the backup destination; no new path convention is needed.
- `agent/study_guide` (`plan` → `draft` → `enhance`/`revise`) is a **separate,
  per-assignment-curated** pipeline: a guide is built from a hand-authored TOML
  spec under `guide_specs/<course>/`, its source plan has a human-review gate for
  discovered (non-pinned) passages, and `enhance`/`revise` operate on an already-
  drafted guide, not directly on a transcribed lecture note. There is no existing
  mapping from "this lecture note changed" to "re-run this guide spec."

## Scope decision: what "update my notes for `<course>`" runs by default

Everything below is per-file or per-course with no human-curation dependency, so
it's safe to fully automate behind one command:

```
discover  →  transcribe (PDF + Excalidraw, agent driver where available)
          →  expand (Excalidraw)
          →  sync SVG/PNG backups to academic_resources/
          →  resolve tagged [Question] markers
          →  chunk + embed into the passage index
```

**Study-guide drafting/enhancement is explicitly out of the default run.** It has
a human-review gate (`plan`'s discovered-passage review Artifact) and a cost cap
built in on purpose; auto-invoking `draft`/`enhance` from "update my notes" would
either skip that review or require guessing which guide spec (if any) a changed
note belongs to, which nothing in the repo currently derives. The consolidated
command's optional `--maintain-guides` (Stage 4, see below) only *re-enhances
guides that already exist* for the course; it never authors a new guide spec or
runs `plan`/`draft` unattended. If the owner wants guides for new material,
that stays its own explicit `agent.study_guide` invocation.

This also answers "get all the way through enhance by default": the default
terminus is a current, searchable corpus (through chunk/embed), not an enhanced
study guide — enhance only applies to guides that already exist, so it can't be
a universal default step for arbitrary lecture notes.

## Guardrails (apply to every stage below)

- **No hidden generative fallback.** If `--driver agent` is requested and the
  agent step for a file hasn't been submitted yet, that file's status is
  "pending agent work" — never silently retried against the metered API.
- **Warn over $1.** Any stage that estimates or falls back to a metered run over
  $1 stops and asks first (per [[feedback_warn_api_calls_over_one_dollar]]).
- **Per-stage call counters**, printed in the run summary, so a real run can
  show actual savings instead of the static estimate this spec and the
  investigation are limited to.
- **Resumability carries through.** Each stage keeps its own existing freshness
  check (manifest status, content hash, chunk hash) so a second invocation of
  the consolidated command only advances what's new, not everything.

## Stage 1 — implemented in this branch

1. **Expose the agent driver on `route_notes_transcribe.py`**, for PDFs only
   (Excalidraw has no agent driver yet — Stage 2). Adds `--driver {api,agent}`,
   `--collect`, `--run-id`, `--submit RUN_ID`, `--bootstrap RUN_ID`, mirroring
   `transcribe_notes.py`'s flags and reusing its `AgentDriver`/`agent_submit.
   submit_doc`/`dedupe_by_file_id` — no new collect/submit mechanics. When
   `--driver agent` is given, Excalidraw items in the plan are left untouched
   and reported as "deferred: Excalidraw has no agent driver yet," so a
   subscription-mode run never silently spends metered Excalidraw API calls.
   `--bootstrap` prints the same operating contract as `transcribe_notes.py`,
   pointed at the router's own `--submit` command.
2. **Excalidraw SVG/PNG resource backup**, independent of transcription state
   (runs for every discovered Excalidraw pair, todo *and* already-transcribed,
   since the plugin re-exports on every note open regardless of transcription
   status): for each `(md_path, image_path)` pair, copy `image_path` to
   `to_resources_root(image_path)` when the destination is missing or older
   than the source (`shutil.copy2`, so mtime comparison stays meaningful
   between runs). Duplication between `academic_notes/` and
   `academic_resources/` is intentional (owner confirmed). No API cost, no new
   lock: writes land under `academic_hub_dir`, already covered by the lock
   `main()` takes for the batch. `--dry-run` previews copies without writing.

## Stage 2 — Excalidraw agent driver (future work)

Extend the same collect/submit/manifest pattern to
`transcribe_excalidraw.py`'s chunk transcription and `expand_transcription`,
per the investigation's seam notes (`_expand_slide_note` already takes
generation through a local callback). Needs its own task-card design (chunk
image + trailing-context text, not a page image) — tracked separately, not
designed here.

## Stage 3 — question resolution agent driver + consolidated orchestrator (future work)

- Agent-driver `resolve_questions.py` (key-term generation and answer
  generation as two card types, retrieval between them stays local/code).
- A thin orchestrator (new `pipelines/transcribe_notes/run_pipeline.py`, or a
  mode on `route_notes_transcribe.py`) that calls, per course: transcribe →
  expand → SVG backup → resolve-questions → `chunk_index.chunk`. Must be
  re-entrant: a course with agent work still pending advances only what's
  ready and reports the rest as pending, since collect/submit is multi-session
  by nature (human relay to Antigravity).

## Stage 4 — opt-in guide maintenance (future work)

`--maintain-guides`: for guide specs that already exist under
`guide_specs/<course>/` and already have a draft, re-run `enhance` (not
`plan`/`draft`) when the draft is older than its cited source chunks. Never
authors a new spec or draft unattended.

## Acceptance evidence

Stage 1: unit tests for the new CLI flags/dispatch and the backup copy
function (mirroring `tests/pipelines/transcribe_notes/test_route_notes_
transcribe.py`'s existing `tmp_path`-based style), run via
`python -m pytest tests/pipelines/transcribe_notes/test_route_notes_
transcribe.py`. No live API calls in tests. A real-corpus dry run
(`--dry-run`) before the first non-dry-run use, per existing convention.
