# Notes pipeline subscription-agent investigation

Date: 2026-10-14. Code inspected at monorepo commit `f9e3f3d`.
Scope: investigation and recommendations for Claude's design review; no implementation or live pipeline run.

## Outcome and requirements

Much of the generative work can use Gemini in Antigravity through the existing collect / agent-fill / submit pattern. PDF transcription already implements it. Excalidraw, correction, question resolution and index metadata still need integration. Embeddings are a separate numeric-model service, not a text-generation task an agent can perform compatibly by writing numbers.

The requested option should preserve API operation, replace as much generative API work as practical, keep deterministic processing local, retain provenance and resumability, and avoid hidden generative API fallback. Subscription execution means the IDE agent reads task files and images and authors results. Existing code does not launch Antigravity as an API replacement or authenticate a Python client with the Pro subscription.

## Verified code map

Paths below are relative to `academic-rag-model/`.

| Stage / discovery | Current scope and API cost | Output / side effects | Existing resume behavior | Candidate seam and verification requirement |
|---|---|---|---|---|
| PDF CLI; selected directory and optional file | Local extraction is free; batch repair and handwriting vision have an implemented agent driver | Collect: private task cards/images. Submit: caches, Markdown, index card | Manifest pending/filled/submitted/bounced; page cache; fully complete output short circuit | Already implemented at `process_pdf` driver calls. Validate pages and inspect equations against images; structural checks alone do not establish fidelity |
| Course router; PDFs and Excalidraw sources | Deterministic discovery, but calls PDF default API driver and Excalidraw API path | Normal transcription outputs; verifies expected files exist | Skips existing output unless forced | `route_notes_transcribe.py` lacks agent driver flags. Pending agent work needs an explicit status rather than being mistaken for failed or finished transcription |
| Excalidraw image chunks | `transcribe_chunks` calls shared vision helper | Raw transcript subsequently written by `write_outputs` | No equivalent persistent task-card workflow | Add a chunk-level collect/submit option preserving trailing context, slide/handwriting labels and question markers |
| Excalidraw expansion / re-expansion | `expand_transcription`: Gemini or Ollama; Ollama failure falls back to Gemini. Optional grounding embeds a retrieval query | Expanded `.excalidraw.rag.md`, metadata and index card | Re-expansion can reuse the saved raw transcript | Agent-authored expansion is a text-only candidate. `_expand_slide_note` already takes generation through a local callback; preserve verbatim slides and validate content coverage |
| PDF postprocessing; flagged pages | Local detection/scoring then `repair_page_individually` API verification | Corrected Markdown, logs and unresolved findings | Existing output/log behavior, no agent manifest | Collect exact source-image/page/text tasks; submit through correction bookkeeping. Must not merely edit the transcript and bypass logs |
| Tagged question resolver; course/note selection | `resolve_question`: key-term generation, retrieval/query embedding, answer generation | Question sidecar and resolved markers | Stable question IDs and existing-answer handling | Agent key-term and answer steps, with retrieval between them. Preserve source exclusions, citations and grounded/ungrounded distinction |
| Per-file indexing; conversion hook or rebuild | `generate_index_card`: one structured generation call, then one embedding call | Card/shard plus course rollup | `reconcile_and_write` uses source identity/content hash | Separate agent metadata authoring from numeric embedding. Validate title, summary, document type, level and solution flag; tags are not generated here |
| Corpus retagging | Candidate and fallback tag generation; tag embeddings; local similarity/coverage checks | Tag definitions, assignments and Markdown frontmatter | Existing vocabulary matching/assignment; no agent task protocol | Replace `_propose_candidate_tags` and `_propose_fallback_tag`; keep empirical validation and minimum coverage |
| Passage indexing and search | Deterministic chunking plus `embed_content`; queries also embed | Chunk index; search returns ranked passages | Chunk freshness currently keyed by content hash | Retain embedding API initially. A local model is a separate migration involving every compatible vector consumer |

Key source files: `pipelines/transcribe_notes/{transcribe_notes,agent_driver,agent_work,agent_submit,transcribe_excalidraw,route_notes_transcribe}.py`, `pipelines/postprocess_notes/postprocess_notes.py`, `agent/rag/resolve_questions.py`, and `core/indexer/{index_card,chunk_index,index_search,retag}.py`.

## What already exists

PDF CLI supports `--driver agent --collect`, `--run-id`, `--bootstrap RUN_ID`, and `--submit RUN_ID`. Collection passes `client=None` and suppresses final corpus output. `AgentDriver` writes images, prompts, worklists and manifests under `<hub>/.agent_work/<run-id>/`. Handwriting is staged in six-page cards with continuity requirements; submission stages the next card when needed. `NullDriver` prevents accidental transcription API calls during finalization.

Submission still initializes a Gemini client and invokes normal indexing: agent transcription is not end-to-end API-free. Validation checks missing/empty pages, repetition, duplicate text, unclosed fences and display-math delimiters. It cannot prove visual accuracy or completeness. The bootstrap also remains a manual handoff and contains a placeholder directory in the submit command.

The October 9 spec still says draft and the plan has unchecked steps; these are stale indicators. The October 12 status addendum explicitly records implementation landing (`8a0cc81`, `d933aed`, `e272757`), corroborated by current source. Tracker TODO-0069 records a prior real-corpus run and a remaining duplicate-PDF no-op submit issue that creates empty cache sidecars. This investigation did not reproduce that run or rerun tests.

The concept graph's `collect/bootstrap/submit` workflow is the closest reusable precedent. `agent/concept_graph/prompts.py` supplies ready-to-paste prompts; its README documents validation, private work storage, retry and idempotency. Tutor preparation similarly uses collect/submit; live tutoring uses a local state-machine CLI. These establish agent-authored work followed by deterministic validation, not a general callable subscription transport. The October 14 bulk-drafting report describes about 190 cards processed and human-relay overhead; that is historical operational evidence, not a performance measurement from this investigation.

## Embeddings boundary

The index uses `gemini-embedding-001` with 768 dimensions. File cards embed title plus summary, chunks embed passage text, tags embed definitions, and queries embed search text. Course vectors are derived locally from cards. Google's documentation describes a dedicated embedding model/API: https://ai.google.dev/gemini-api/docs/models/gemini-embedding-001 .

No subscription embedding adapter was found in the inspected pipelines. Having the agent invoke today's embedding script would still spend API quota. Having it invent vectors would break retrieval. Keeping embedding API calls while moving generative work is the smallest compatible change. Eliminating them requires a real local embedding backend and coordinated rebuilding of cards, chunks, tags and course rollups, plus query-side switching and retrieval evaluation. Content-hash-only skip logic must not silently retain old-model vectors. Matching vector dimensions does not establish matching vector spaces.

## Existing constraints and adjacent work

- `docs/trackers/academic_hub_to_do.md` TODO-0030 already identifies Excalidraw expansion omissions and stale/unpaired question markers. Preserve substantive themes and diagrams and audit all question markers after resolution. A backend switch cannot be reported as fixing those defects without evidence.
- TODO-0075 and `docs/trackers/pending_updates/2026-10-14-shifting-bulk-drafting-to-subscription-agents.md` cover project-wide subscription drafting and prompt generation. Reuse this work rather than creating a competing relay system.
- `docs/superpowers/specs/transcribe_notes/2026-10-09-agent-driven-transcription-design.md` and its implementation plan intentionally excluded Excalidraw and indexing generation. The current gaps are outside that original scope.
- `tools/` contains corpus-health and steering tooling. Existing writer locks do not coordinate every writer or external Obsidian sync; agent support does not authorize enabling unattended repair adapters.

Git root checks confirm `academic-hub` belongs to the outer monorepo, while `academic-hub/academic_notes` is a separate nested repository. Source assets are under `academic_resources`; transcripts, expanded notes, sidecars and page caches land in mirrored `academic_notes/.../processed_outputs`; index data is under `<hub>/.index`; temporary agent work is under `<hub>/.agent_work`. The concept graph's published data checkout is a separate destination by its documented workflow and is not needed for this feature. No corpus or index was written during this investigation.

## Recommended next design scope

For Claude review: extend Excalidraw transcription, expansion and question resolution as one coherent agent workflow, and separate index-card metadata generation from embedding. These address the remaining note-specific generation calls while preserving the existing retrieval space. PDF router integration and stronger ready-to-paste prompts improve access to functionality already built. Correction and retagging can follow independently.

A smaller independently useful increment is agent re-expansion of already-transcribed Excalidraw notes, with question-resolution handling and coverage audits. It needs no new server or headless agent launcher. Use existing local task files and explicit handoff. Human semantic decisions should use the project's interactive Artifact convention; task files are machine work/state, not a replacement owner-decision ledger.

Before implementation, the design should specify exact source selectors; task identity including source/image/transcript, prompt version and grounding hashes; transitions from pending through validated/submitted or bounced; invalidation when inputs change; atomic output and writer coordination; per-target completion results; and post-run content/question/index audits. Retry only rejected or incomplete work. Stop pending when the agent is unavailable or quota is exhausted; do not silently use metered generation. Scheduled collection may be possible later, but unattended Antigravity execution was not established here.

Acceptance evidence should include fixture tests for routing, invalidation and no-hidden-generation calls, then a small live sample spanning handwritten math, slides with handwriting, question-bearing notes and typed PDF repair. Compare outputs with source images and compare retrieval before/after. Record API calls by stage and subscription handoff effort; no savings percentage or throughput estimate is established by static inspection.

## Investigation verification

Read package guidance and READMEs; traced call sites and CLI options; checked existing specs, plans, status, tracker and adjacent tools; verified repository roots. No model requests using workspace credentials, tests, corpus processing, account changes or implementation edits were performed. Only this investigation document was added in a dedicated worktree. Architecture choices remain recommendations for Claude, not approved decisions.
