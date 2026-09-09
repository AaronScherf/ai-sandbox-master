# Excalidraw Notes Transcription & Expansion: Design

## Motivation and history

`transcribe_notes.py`'s Tier 3 (full-Gemini, page-by-page vision
transcription) already handles handwritten/messy PDF exports
(Nebo/MyScript/OneNote), but real investigation of
`academic_notes/math-camp/handwritten_notes/` found the problem wasn't in
that code: the user's OneNote capture workflow (screenshot handwriting ->
paste into web Gemini -> copy its LaTeX/markdown output back into OneNote
-> export to PDF) bakes redundant, colored `$$...$$` blocks directly onto
the page, which Tier 3 then faithfully (and correctly) transcribes. The
fix belongs upstream, in capture, not in transcription logic. Full
diagnosis: `docs/status/2026-08-24-notes-transcription-status.md`'s
"2026-09-07" section.

The replacement capture tool is Excalidraw notes in the user's Obsidian
vault, synced via a new standalone git repo,
`academic-hub/academic_notes/` (remote: `academic-notes-vault` on GitHub,
**private** -- a better IP posture than the main `ai-sandbox-master` repo,
which is public), gitignored from the main project root so the two repos
never conflict. Confirmed clean: the outer repo tracks zero files under
`academic_notes/` as of this writing.

Two real examples were pulled and a chunking approach was spiked against
them (`docs/status/2026-08-24-notes-transcription-status.md`'s "2026-09-09"
section) before this spec was written:

- `math_methods/lecture_notes/Drawing 2026-09-08 11.51.12.excalidraw.{md,png}`
  (785x13,860px canvas)
- `microecon/lecture_notes/Drawing 2026-09-07 19.53.03.excalidraw.{md,png}`
  (786x7,049px canvas)

Findings that shape this spec directly:
- The `.excalidraw.md` file is **not usable as an input**: both real files
  have an empty `## Text Elements` section (100% freedraw ink, no typed
  Excalidraw text elements) and a `## Drawing` section that's an opaque
  `compressed-json` blob -- not parseable without reimplementing
  Excalidraw's own decompression. The plugin's auto-exported `.png`
  (already written on every save, no configuration needed) is the real
  input.
- Excalidraw canvases are **unbounded-height infinite scrolls**, not
  fixed-size pages -- nothing like a PDF page boundary exists to chunk on
  naturally.
- A **whitespace-gap scan directly on the rendered PNG** (near-white row
  detection, cut at the gap closest to a ~3000px target height, 4500px
  cap) was spiked against both real files with **zero hard cuts** -- every
  cut landed inside real whitespace, never through content. 84 gaps / 5
  chunks (heights 1893-3086px) on the 13,860px file; 28 gaps / 3 chunks
  (heights 1032-3063px) on the 7,049px file.
- Both canvases are only 785-786px **wide** (tablet portrait width) --
  already narrower than the ~1700px+ textbook-page renders Tier 3 sends
  today, which matters for the compression discussion below.

**A real naming trap to avoid:** `academic_notes/math-camp/lecture-notes/`
(hyphenated) is `video_notes`' synthesized-lecture output. The Excalidraw
tablet-sync folders are `academic_notes/<course>/lecture_notes/`
(underscored) -- e.g. `math_methods/lecture_notes/`,
`microecon/lecture_notes/`. These are different folders one character
apart. Any code or docs referencing either must not conflate them.

## Scope

**In scope:** a new module, `notes/transcribe_excalidraw.py` (same package
as `transcribe_notes.py`), that discovers `.excalidraw.md`/`.png` pairs
under `academic_notes/<course>/lecture_notes/`, chunks each PNG, transcribes
each chunk via Gemini vision with cross-chunk context, assembles a raw
per-document transcription, then expands it into cohesive prose --
optionally grounded in existing textbook content via the indexer's
existing retrieval.

**Out of scope for v1** (explicitly deferred, not forgotten):
- Low-confidence-chunk detection/flagging (see "Deferred items" below).
- Any `postprocess_notes.py`-style correction pass over the expanded
  output -- may or may not ever apply; not decided.
- Combining transcription and expansion into a single vision call (a real
  alternative, not ruled out -- just not what v1 builds; see "Why two
  stages, not one").
- Updating `docs/trackers/2026-08-30-academic-hub-status.md`'s "IP and
  security posture" section, which was written assuming `academic_notes/`
  stayed in the public main repo. Now stale; flagged here, fixed
  separately.

## Architecture: five stages

```
.excalidraw.md + .excalidraw.png  (discovery)
  |
  v
Stage 1: Chunk        -- whitespace-gap scan on the PNG
  |
  v
Stage 2: Transcribe    -- Gemini vision per chunk, trailing-context window
  |
  v
Stage 3: Assemble      -- concatenate chunk transcriptions -> one raw doc
  |
  v
Stage 4: Expand        -- LLM rewrites raw doc into cohesive prose,
  |                        optionally grounded in retrieved textbook passages
  v
Stage 5: Write         -- <name>.md (raw) + <name>.rag.md (expanded)
```

### Stage 1: Chunk

Reuses the spiked algorithm directly, promoted from throwaway script to
real, unit-tested code:
- Load PNG, convert to grayscale, compute per-row minimum pixel value.
- A row is "blank" if its darkest pixel is >= `INK_ROW_THRESHOLD` (245 in
  the spike).
- A contiguous blank run of >= `MIN_GAP_ROWS` (8) rows is a candidate gap.
- Walk down the image; at each step, cut at the gap whose midpoint is
  closest to `last_cut + TARGET_CHUNK_HEIGHT` (3000px), among gaps within
  `MAX_CHUNK_HEIGHT` (4500px) of the last cut. If no gap exists in that
  window, cut hard at `MAX_CHUNK_HEIGHT` (never observed on real data so
  far, but must be handled, not assumed impossible).
- These three constants (`INK_ROW_THRESHOLD`, `MIN_GAP_ROWS`,
  `TARGET_CHUNK_HEIGHT`/`MAX_CHUNK_HEIGHT`) are starting points from two
  real files, not finalized -- the implementation plan should re-validate
  against a larger real sample as more tablet notes accumulate, the same
  way `_MAX_DEFECT_RATIO_FOR_HYBRID` and other thresholds elsewhere in this
  project were tuned against real corpus data rather than fixed once and
  trusted.

**Image compression, not decided numerically here.** Width is already
modest (785-786px on real data), so the token/cost savings from
downscaling may be smaller than generic vision-LLM advice assumes for
typical (roughly square) images. The implementation plan should run a
small real experiment -- 2-3 resize/format settings (e.g. no resize + PNG,
no resize + JPEG q85, width-capped + JPEG q80) against a handful of real
chunks, comparing Gemini's reported token usage against spot-checked
transcription accuracy -- before picking a default, rather than guessing
one now.

### Stage 2: Transcribe

One Gemini vision call per chunk, reusing `common/gemini_utils.py`
(`get_gemini_client`, `call_with_retries`, `extract_retry_delay_seconds`)
exactly as `transcribe_notes.py` already does. Carries a trailing-context
window across chunks -- structurally the same idea as
`transcribe_notes.py`'s `_ACCUMULATION_WINDOW = 3` /
`build_accumulated_context()`, just keyed by chunk index instead of PDF
page number, since a gap-detected cut can still land mid-derivation the
same way a OneNote page boundary used to.

Prompt asks for a faithful, terse transcription -- shorthand preserved,
LaTeX for math notation, no expansion or explanation at this stage. This
is Stage 4's job, kept separate (see "Why two stages, not one" below).

### Stage 3: Assemble

Pure Python, no API call: concatenate chunk transcriptions in order into
one raw document string. This is also the natural point to persist an
intermediate cache (mirroring `_pages_cache.json`'s convention) so a
failure in Stage 4 doesn't require re-paying for Stage 2's API calls.

### Stage 4: Expand

A second LLM pass rewrites the assembled raw document into cohesive prose
-- the step this whole redesign exists for, since raw shorthand next to
LaTeX was confirmed to add little to the RAG corpus on its own once
expanded (user's own call, from the original brainstorm).

**Backend: configurable, default Gemini, opt-in local Ollama** -- matching
the existing `VIZ_BACKEND`/`PROBLEMGEN_BACKEND` pattern in this project
(env var, e.g. `EXCALIDRAW_EXPAND_BACKEND=ollama`). Real precedent for the
local option working: `video_notes` already ships a production local
Ollama synthesis step (`qwen2.5:7b-instruct`, via `common/ollama_utils.py`'s
`call_ollama`) that turns a rough transcript into a coherent note. Whether
Ollama holds up for this specific task (expansion grounded in retrieved
textbook context, not just video-transcript synthesis) is untested --
default to Gemini until real-corpus testing says otherwise, same
house pattern as everywhere else in this project.

**Textbook grounding, optional:** the indexer's existing
`indexer/chunk_index.py`/`indexer/index_search.py` passage-level search can
retrieve textbook passages relevant to the raw transcription's content
before the expansion call, the same retrieval machinery `rag_agent.py`
already uses. Not required for v1 to produce output, but should be wired
in if available, since it's the difference between "expand this shorthand"
and "expand this shorthand *and* connect it to the course's own textbook
material" -- the latter is closer to what the user actually asked for.

### Stage 5: Write

Reuses the existing `.rag.md` naming precedent from `describe_images.py`
(the established way this project marks "the enriched, RAG-indexable
artifact," distinct from a plainer `.md`) rather than inventing a new
convention:

- `<name>.md` -- Stage 3's assembled raw transcription. Shorthand,
  faithful to what's on the canvas. Human-readable on its own (e.g. a
  quick on-device reference), not the file the indexer treats as
  canonical.
- `<name>.rag.md` -- Stage 4's expanded prose. The RAG-indexable artifact.

Both live in `processed_outputs/`, a sibling of `lecture_notes/`, inside
the tablet-sync repo (`academic_notes/<course>/lecture_notes/processed_outputs/`)
-- matching every other subproject's `processed_outputs/` convention, and
confirmed safe given the outer/inner repo split above.

**Frontmatter**, both files:
```yaml
source_excalidraw: <name>.excalidraw.md
source_png: <name>.excalidraw.png
folder_category: excalidraw_notes   # new value, distinct from handwritten_notes
routing: excalidraw_chunked         # new value, so postprocess_discovery.py
                                     # and the indexer can tell these apart
                                     # from PDF-derived notes if that ever matters
chunks: <int>
model: <transcription model id>
tags: []
```
The `.rag.md` additionally carries:
```yaml
expansion_model: <expansion model id>
expansion_backend: gemini | ollama
grounded: true | false   # whether textbook retrieval was used
```

## Why two stages, not one

A single combined call (one vision prompt per chunk that both transcribes
*and* expands) is a real, cheaper alternative -- fewer API round-trips --
and is explicitly not ruled out. It's not what v1 builds, for a structural
reason distinct from cost: transcription is bounded by chunk (image size
forces this), but expansion should see the *whole* assembled document plus
retrieval-grounded textbook context -- a different granularity than any
single chunk has access to. Combining them per-chunk would mean expansion
only ever sees one chunk's local context, undercutting the textbook-
grounding goal above. Whether combining also risks lower transcription
fidelity (a model asked to both faithfully transcribe and creatively
expand in one turn) is untested, not assumed -- worth a real A/B in the
implementation plan if the two-stage cost turns out to matter in practice.

## Deferred items (explicitly out of v1, not forgotten)

**Low-confidence chunk detection.** A signal that a chunk's transcription
might not match what's actually on the page -- e.g. a chunk with heavy ink
density (from the same row-scan Stage 1 already computes) but a
suspiciously short returned transcription, or the model explicitly hedging
("illegible," "unclear"). Unlike `postprocess_notes.py`'s recheck (which
re-verifies against an already-cached, trusted page), there's no
independent ground truth to auto-correct against here, so this could only
ever flag for manual review, never auto-fix. Given this project's history
with exactly this shape of heuristic (`_CAUSAL_ZSCORE_THRESHOLD`'s
still-open precision problem took real, unfinished effort to tune), this
is deferred to v2 rather than built speculatively now.

**Correction/postprocessing on the expanded output.** Not decided whether
`postprocess_notes.py`'s pattern should ever apply to `.rag.md` output;
out of scope here.

## Testing plan

- Stage 1 (chunking): pure-function unit tests against small synthetic
  images (no PIL/numpy mocking needed, this is genuinely fast local
  compute) covering: no gaps found (hard-cut path), a gap exactly at the
  target height, a gap outside the max-height window, and the two real
  example files themselves as fixtures (regression-testing the exact
  chunk counts/heights already observed in the spike).
- Stage 2/4 (API calls): mocked at the `call_with_retries`/`call_ollama`
  boundary, matching every other subproject's test convention in this
  project -- no real network calls in the test suite.
- Real-corpus validation (not just unit tests, per this project's
  standing pattern): run end-to-end against the two real files already in
  hand before considering this done, and spot-check the `.rag.md` output's
  faithfulness against the source PNGs the way image-description and
  notes-transcription were validated.

## Open questions carried into the implementation plan

1. Final chunking constants, re-validated against more real notes as they
   accumulate.
2. Compression/resize setting, chosen from a real small experiment (see
   Stage 1).
3. Whether Ollama is viable for Stage 4 in practice, or whether Gemini
   stays the only real option (undetermined, matches this project's
   general finding that local-model viability varies a lot by task).
4. Whether textbook-retrieval grounding is wired in for v1 or added right
   after.
