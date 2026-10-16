# Question-resolver agent driver — design spec

**Status:** implemented (branch `claude/question-resolver-agent-driver`, 2026-10-16). See `docs/superpowers/plans/2026-10-16-question-resolver-agent-driver.md` for the task breakdown; full test suite green (3715 passed, 41 subtests passed).
**Branch:** `claude/question-resolver-agent-driver`.
**Follows:** `docs/superpowers/specs/transcribe_notes/
2026-10-15-consolidated-pipeline-design.md`'s Stage 3, first half ("Agent-
driver `resolve_questions.py`"). The second half of Stage 3 (a consolidated
per-course orchestrator) is deliberately out of scope here — scoped down the
same way Stage 2 was its own piece, per owner decision this session. The
orchestrator becomes its own follow-up once this driver exists for it to call.

## Goal

Extend the collect/submit/manifest pattern already shipped for PDF
transcription (`agent_driver.py`/`agent_work.py`) and Excalidraw transcription
+ expansion (`excalidraw_agent_driver.py`/`excalidraw_agent_work.py`) to
`agent/rag/resolve_questions.py`'s two generative call sites: key-term
extraction and answer generation. Retrieval stays off the agent driver
entirely, same reasoning as Excalidraw's grounding retrieval in Stage 1/2.

## Verified current state (this session, commit `b43cb09`)

- `resolve_note()` (`agent/rag/resolve_questions.py:173`) is the per-note
  entry point: for each tag not already answered in the note's sidecar, it
  computes local context (`question_context`, pure text slicing), then calls
  `resolve_question()`, which makes exactly two generative calls:
  1. `_extract_key_terms(question, client)` (`agent/rag/rag_agent.py:243`) —
     builds its own prompt internally from `_KEY_TERM_PROMPT_TEMPLATE`, calls
     `client.models.generate_content`, parses a comma-separated list.
  2. The answer call inside `resolve_question` itself
     (`agent/rag/resolve_questions.py:113`) — `build_answer_prompt(...)` then
     `client.models.generate_content`.
- `retrieve_passages()` (`agent/rag/rag_agent.py:286`) sits between those two
  calls and is **retrieval only** — two `search_passages()` calls, which are
  embedding lookups, not generation. It must stay on the direct API path
  always, exactly like Excalidraw's `_retrieve_grounding`/`search_passages`
  reasoning in the Stage 1 and Stage 2 specs.
- `_extract_key_terms` is **shared** with `rag_agent.py`'s `/hint` handler and
  the tutor's answer flow (confirmed by reading both call sites) — it must
  not be modified in place or given driver-awareness; any agent-driven
  routing for key-term extraction has to live entirely inside
  `resolve_questions.py`, as new code, not a change to the shared helper.
- The per-note sidecar (`core/indexer/questions.py`'s `read_sidecar`/
  `write_sidecar`, keyed by stable `qid`) already is the persisted "already
  answered" record — it plays the same role the chunk/expansion caches play
  for Excalidraw. No new persisted store is needed for final answers.
- There is **no existing intermediate store** for key terms between the two
  generative calls — today both calls happen back-to-back inside one
  synchronous Python call (`resolve_question`), so nothing persists a
  question's extracted key terms independently of also having its answer.
  An agent-driven run needs exactly this: key terms must survive between a
  `--collect` that stages key-term cards and a later `--submit` that stages
  answer cards once they're filled.
- `question_id(ordinal, text)` (`core/indexer/questions.py:33`) is a stable,
  content-derived id (`q<ordinal>-<8-hex-digest-of-normalized-text>`),
  already used as the natural per-question key — reused directly as the
  cache key instead of inventing a new indexing scheme (unlike Excalidraw's
  chunks/segments, which only have a position, not stable identity text).

## Decisions already made (owner, this session)

1. **Question-resolver driver only, not the consolidated orchestrator.**
   Matches Stage 2's own scoping; the orchestrator is its own task once this
   driver exists.
2. **Two-stage pipeline per note**, mirroring Excalidraw's transcribe→expand
   split exactly: key-term extraction for every pending question in a note
   must fully complete before the answer stage for that note becomes
   reachable (retrieval for a question needs that question's own key terms
   to boost/validate its search).
3. **One task card per note per stage** (not one card per question),
   matching Stage 2's bundling: a key-term card lists every pending
   question's key-term prompt; once all are submitted, an answer card lists
   every pending question's answer prompt.

## Architecture

### New persisted cache: key terms only

`<base_name>.excalidraw.keyterms_cache.json`, next to the sidecar and raw
transcript (same directory, same naming convention —
`sidecar_path_for`/`rag_path_for` already live in `core/indexer/questions.py`
as the precedent). Keyed by `qid` (stable, content-derived — not an ordinal
index, since `rekey_entries` already proves `qid` survives re-transcription
and the Excalidraw ordinal-index precedent doesn't apply here). Read/written
with the same `core.env.gemini_utils.load_json_cache`/`save_json_cache`
helpers every other cache in this codebase uses.

No new cache is needed for answers — the sidecar already serves that role.

### New module: `agent/rag/resolve_questions_driver.py`

One protocol, mirroring `ExcalidrawDriver`'s shape exactly, in its own module
(not `agent_driver.py` or `excalidraw_agent_driver.py` — a third domain, same
reasoning each previous stage used: it needs prompt/parsing helpers specific
to this call site and must not create an import cycle back into
`resolve_questions.py`):

```python
class QuestionResolverDriver(Protocol):
    def extract_key_terms(self, note_key: str, qid: str, prompt: str) -> str: ...
    def generate_answer(self, note_key: str, qid: str, prompt: str) -> str: ...
    def stage_key_terms(
        self, note_key: str, missing: list[tuple[str, str]],  # (qid, prompt)
    ) -> dict[str, str]: ...  # qid -> raw key-term response text
    def stage_answers(
        self, note_key: str, missing: list[tuple[str, str]],  # (qid, prompt)
    ) -> dict[str, str]: ...  # qid -> raw answer text
```

Driver methods return **raw text** — comma-list parsing for key terms and
any answer post-processing stay in `resolve_questions.py`, same division of
labor Stage 2 used (`ExcalidrawApiDriver.expand` returns raw text; assembly
and formatting stay in `transcribe_excalidraw.py`).

`QuestionResolverApiDriver(client)`: `extract_key_terms` wraps
`client.models.generate_content` with the same config
`_extract_key_terms` already uses (`temperature=0,
thinking_level="minimal"`, same model constant, imported from
`rag_agent.py` — reused, not duplicated). `generate_answer` wraps the same
call `resolve_question` makes today (`temperature=0.2`, `RESOLVER_MODEL`).
`stage_key_terms`/`stage_answers` loop and call the singular method per
missing item, matching `ExcalidrawApiDriver.stage_chunks`/`stage_segments`.

`QuestionResolverNullDriver`: all four methods raise `NullDriverFired`
(reused from `pipelines.transcribe_notes.agent_driver` — already generic,
no import-cycle risk since that module has no dependency on `agent/rag/`).

`QuestionResolverAgentDriver(hub_root, run_id, agent_name="antigravity")`:
writes task cards via `pipelines.transcribe_notes.agent_work`'s generic
primitives (`doc_slug_for`, `doc_work_dir`, `ManifestEntry`, `load_manifest`,
`save_manifest`, `render_worklist` — none of them PDF-specific, confirmed
reused unmodified by both prior stages). `doc_slug_for` needs a stable
file-identity string; since there's no single PDF/image file this domain
revolves around, slug off the **raw transcript path** via
`compute_file_id(raw_path)`, same convention Excalidraw used for its own
`.excalidraw.md` path. Card format: `## <qid> — <question text>` sections
(instead of `## Chunk N`/`## Segment N`), `--- ANSWER <qid> ---` (or
`--- KEYTERMS <qid> ---`) as the expected-output delimiter, since `qid` is
the natural identity here, not a position.

### Where retrieval and card staging actually happen

New functions in `resolve_questions.py` (not in the driver module — same
division of labor as Excalidraw, where `process_excalidraw_note` owns
orchestration and the driver module only wraps individual calls):

- `_build_key_term_prompt(question: str) -> str` — thin wrapper around
  `rag_agent._KEY_TERM_PROMPT_TEMPLATE.format(question=question)`, imported
  (not duplicated) so the two call sites' prompts can never drift apart.
- `_parse_key_terms(text: str) -> list[str]` — the same comma-split logic
  `_extract_key_terms` already has, extracted so both the driver-routed path
  and (if ever needed) a direct call share one implementation. Given
  `_extract_key_terms` must stay unmodified (shared with `/hint`/tutor), this
  is a **new, parallel** function with identical logic — a small, deliberate
  duplication, same tradeoff Stage 2 accepted for
  `_EXPANSION_MODEL_GEMINI`/`_EXPANSION_MODEL_OLLAMA` (flagged as a known,
  accepted minor in that stage's final review) rather than risk coupling
  `resolve_questions.py` to `rag_agent.py`'s internals changing out from
  under it.
- `resolve_note`'s restructure: given a loaded `keyterms_cache` (dict,
  `qid -> list[str]`), the pending-questions loop splits into two phases:
  1. **Key-term phase.** For every tag not yet in the sidecar and not yet in
     `keyterms_cache`, build its key-term prompt. If `collect_mode`, build
     the `missing` list and call `driver.stage_key_terms(note_key, missing)`
     once for the whole note (same single-call-per-note-per-stage shape as
     `transcribe_chunks`'s collect branch) — raises `AgentPending` if
     anything was missing; returns control if nothing was. If not
     `collect_mode`, loop calling `driver.extract_key_terms(...)` per
     question sequentially (same shape as the existing non-collect
     sequential path for chunks/segments).
  2. **Answer phase**, reachable only once every pending tag has key terms
     cached: for each pending tag, run `retrieve_passages` locally (using
     its now-cached key terms) to build the grounding block, then the full
     answer prompt via `build_answer_prompt`. Same `collect_mode` branch
     shape as phase 1, calling `stage_answers`/`generate_answer`.
  3. A submitted answer is validated and written straight into the sidecar
     via `read_sidecar`/`write_sidecar` (unchanged) — no separate "answers
     cache" file, per the Architecture section above.

### Collect-mode retrieval exception (this stage's one real deviation)

Every prior agent driver's `--collect` needed no live API client (PDF:
`process_pdf(pdf_path, None, ...)`; Excalidraw: `process_excalidraw_note(...,
None, ...)`). Here, **the answer-stage collect call still needs a real
client**, because `retrieve_passages` makes embedding calls to build the
grounding block the staged answer card shows the agent — collect cannot
defer retrieval to submit time without either re-running it twice (wasteful,
and risks the agent and the final write seeing different passages if the
corpus changed between collect and submit) or shipping the agent a card with
no grounding context at all (defeats the purpose of grounding). The
key-term-stage collect call still needs no client (pure text generation,
deferred to the driver).

This means the CLI's `--collect` branch for this driver must build a real
`get_gemini_client(...)` even when `--driver agent`, unlike the Excalidraw
and PDF collect branches which pass `client=None`. This is called out
explicitly so the implementation plan doesn't silently copy the
`client=None` convention from the other two drivers where it would break
retrieval.

### CLI integration (resolve_questions.py's own `main()`)

Mirrors `transcribe_notes.py`'s and `route_notes_transcribe.py`'s existing
`--driver {api,agent}` / `--collect` / `--run-id` / `--submit RUN_ID` /
`--allow-api-fallback` / `--bootstrap RUN_ID` flags, with the **same
default-is-agent decision** from the consolidated-pipeline spec's amendment
— `--driver` defaults to `"agent"`, `--driver api` is the explicit opt-out,
`--allow-api-fallback` is submit-time-only and explicit. No separate
orchestrator-level flag surface is introduced here since this is a
standalone CLI, same as `transcribe_notes.py` is today; wiring this into
`route_notes_transcribe.py`'s own CLI is explicitly out of scope (that's the
future consolidated-orchestrator task this spec deferred).

## Guardrails (carried over, unchanged)

- No hidden generative fallback: a note with a pending key-term or answer
  card reports "pending agent work," never silently retried against the
  metered API. `--allow-api-fallback` at `--submit` time is the one
  sanctioned, explicit exception, same as both prior stages.
- Retrieval (`retrieve_passages`) never routes through any driver, in either
  mode — it's embedding calls, not generation, same reasoning as Excalidraw
  grounding.
- `--dry-run` previews (notes/questions pending per stage) without writing
  cards or cache files.

## Acceptance evidence

Unit tests for: the key-terms cache round-trip and resumability (a qid
already in the cache is never re-requested), `QuestionResolverApiDriver`'s
four methods, `QuestionResolverAgentDriver`'s card writing for both stages
(mirroring `tests/pipelines/transcribe_notes/test_excalidraw_agent_work.py`'s
style), the two-phase restructure of `resolve_note` (key-term phase gates
the answer phase), and submit's validation + cross-stage restage. No live
API calls in tests. Run via `python -m pytest tests/agent/rag/`.

## Open items for the implementation plan

- Exact validator rules for a filled key-term card (a comma list with no
  obviously-malformed entries) vs. an answer card (reuse the
  repetition-loop/unclosed-fence/unbalanced-math checks `agent_submit.py`
  and `excalidraw_agent_submit.py` already have, since an answer is prose
  markdown same as those).
- Whether `QuestionResolverAgentDriver`'s task-card directory structure
  needs anything beyond text (no images here, unlike both prior drivers) —
  likely a pure-markdown card with no `images/` subdirectory at all.
- Confirm `--bootstrap`'s printed contract text for this CLI explains the
  `--- KEYTERMS <qid> ---` / `--- ANSWER <qid> ---` format distinction
  clearly, since this is the first driver where a note's two stages use
  different delimiter keywords rather than the same one (`PAGE`/`CHUNK`/
  `SEGMENT` were each single-purpose per driver; this driver has two).
