# Video Lecture Notes: Real End-to-End Validation

Real-world validation of `video_notes/` (spec:
`docs/superpowers/specs/2026-09-06-video-lecture-notes-design.md`, plan:
`docs/superpowers/plans/2026-09-06-video-lecture-notes.md`), run against
a real 105-video YouTube playlist ("All Math Camp Lectures, in order")
with real download, transcription, and local Ollama synthesis — not the
mocked unit tests. Two real bugs were found and fixed; one real
capability limitation was found and is recorded below as known, not
fixed (a model/prompt limitation, not a code defect).

## Setup

- Course: `math-camp`, already indexed with 30 real cards (textbooks,
  TA notes, problem sets) before this test.
- `ffmpeg` was not on `PATH` in this environment; Chocolatey required
  admin rights this session didn't have, so it was installed via
  `winget install --id Gyan.FFmpeg` instead (user-scope, no elevation
  needed) — worth defaulting to winget over choco in this repo's docs
  for any future non-admin ffmpeg setup.
- Ollama: confirmed running locally, with `qwen2-math:7b`,
  `qwen2.5-coder:7b`, and `nomic-embed-text` already pulled from prior
  `problem_gen`/`viz` work, but not the design's chosen synthesis
  default, `qwen2.5:7b-instruct` — pulled fresh mid-test (~4-5GB,
  `ollama pull qwen2.5:7b-instruct`).
- Scope: rather than the full 105-video playlist, resolved the
  playlist's first 2 videos' individual URLs and ran them via `--urls`
  (not `--playlist`) for a fast first validation pass, per the design
  spec's own §9 recommendation to validate on 1-2 real videos before
  trusting the pipeline at scale.

## Bug #1: lecture notes got classified into the shared corpus's four-type vocabulary

**Symptom:** both real notes were indexed with `doc_type:
"handwritten_notes"` instead of anything lecture-note-specific.

**Root cause:** the design spec (§6) assumed `generate_index_card()`
falls back to `folder_category` whenever the LLM's returned `doc_type`
isn't recognized — modeled on how non-`KNOWN_DOC_TYPES` folders like
`articles`/`briefings` were believed to behave. That assumption was
wrong: `generate_index_card()`'s own prompt only ever offers the LLM
the `known_doc_types` it's given as valid choices ("doc_type (one of:
{doc_type_options})"), so the LLM always picks one of those — it never
returns something outside the set that would trigger the
folder-category fallback in practice.

**Fix:** added `LECTURE_NOTE_DOC_TYPES = frozenset({"lecture_notes"})`
to `indexer/index_card.py`, threaded through both places that index a
lecture note (`video_notes/note_indexing.py`'s direct
`reconcile_and_write()` call, and `indexer/index_search.py`'s
`rebuild()` lecture-notes loop via a new `known_doc_types` param on
`_reconcile_one()`). Verified live: both real cards now show
`doc_type: "lecture_notes"` after re-indexing. Regression tests added
in `tests/test_note_indexing.py` and `tests/test_index_search.py`
(including one confirming a lecture note is never classified into
`textbook`/`problem_set`/`ta_notes`/`handwritten_notes`, and one
confirming it lands on `"lecture_notes"` when the model complies).

## Known limitation: local models don't reliably cite timestamps

**Finding:** three different local Ollama models — `qwen2-math:7b`,
`qwen2.5-coder:7b`, and `qwen2.5:7b-instruct` (the design's own default)
— were each tried against the same real, verified-correct synthesis
prompt (confirmed to contain properly formed
`[label @ timestamp](url)` lines throughout, ~16,700 chars /
~4,200 tokens for a single ~13-minute lecture). All three produced
factually accurate, reasonably well-organized Markdown — but **none of
them included a single timestamp citation**, despite it being an
explicit, numbered instruction in the prompt (spec §6's whole reason
for embedding per-segment links in the first place).

**Ruled out:** context-window truncation. `qwen2-math:7b`'s 4096-token
window plausibly explained *its* complete lack of any formatting at all
(headers, LaTeX, bullets were also entirely absent for that model) —
but `qwen2.5-coder:7b` (32K context) and `qwen2.5:7b-instruct` both had
enormous headroom, produced proper headers/bullets/bold text and
mathematically accurate LaTeX-style notation (`\(...\)`/`\[...\]`, not
quite the requested `$...$`/`$$...$$` delimiter but structurally
correct), and *still* dropped every citation. This rules out context
size as the cause for the citation gap specifically — it's model/prompt
instruction-following, not truncation.

**Working theory:** citation instructions asked the model to weave
literal URLs into freely-generated prose as bullet point #3 of 3 in a
numbered list — a harder, more easily-dropped task for 7B-class local
models than pure stylistic formatting (headers/bullets), which all
three models did follow.

**Decision (user, 2026-09-06):** ship without citations for now, revisit
later. Two concrete directions already identified for that future work,
not implemented:
1. Redesign the prompt to isolate the citation instruction and give a
   concrete few-shot example of an already-cited sentence, rather than
   listing it as the last of three general formatting rules.
2. Insert citations programmatically instead of relying on the LLM:
   let the model write clean, citation-free prose, then attach the
   nearest matching timestamp to each generated sentence afterward via
   text-similarity matching against the original transcript segments —
   removes the instruction-following burden entirely for a task three
   different local models all failed at.

The two real notes committed to the corpus from this test
(`academic_notes/math-camp/lecture-notes/2021-introductory-remarks.md`,
`.../lecture-1-a-sets-and-n-tuples.md`) were generated with
`qwen2.5:7b-instruct` (the best of the three real trials) and reflect
this known gap — no timestamp links, otherwise accurate and reasonably
structured.

## What this confirms end-to-end

Metadata fetch, audio download (`yt-dlp` + winget-installed `ffmpeg`),
local CPU transcription (`faster-whisper`, `small`/`int8`, real
timestamped text confirmed correct against the real audio), grouping
(correctly produced 2 separate singleton groups, since `--urls` carries
no playlist context — the playlist-merge default tier wasn't exercised
by this test), local Ollama synthesis, note writing, and Source Indexer
registration all work end-to-end against real YouTube content. The
100+-video full-playlist run, and the playlist-merge grouping tier, are
both still unvalidated against real data — natural next real-world
checks once the citation question above is revisited.
