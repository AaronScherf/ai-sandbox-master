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

## Bug #2 (superseding the "known limitation" originally recorded here): `call_ollama` silently truncated every prompt to ~2048 tokens

**Original, incorrect conclusion (2026-09-06, pass 1):** three different
local Ollama models — `qwen2-math:7b`, `qwen2.5-coder:7b`, and
`qwen2.5:7b-instruct` — were each tried against the same real synthesis
prompt (~16,700 chars / ~4,200 tokens for a single ~13-minute lecture).
All three produced accurate Markdown but **none included a single
timestamp citation**. Context-window size looked ruled out at the time
because `qwen2.5-coder:7b` (32K) and `qwen2.5:7b-instruct` (32K) both
had, on paper, enormous headroom over a 4,200-token prompt — so this was
initially written up as a model/prompt instruction-following limitation
and shipped as a known, unfixed gap.

**That conclusion was wrong, and pass 2 is what caught it.** A 3-video
group's combined synthesis prompt (~89,000 chars / ~22,000 estimated
tokens) came back as a note whose content matched only the *last*
video's material — the other two videos' content was entirely absent,
despite `qwen2.5:7b-instruct`'s advertised 32K context comfortably
covering the real prompt size. Querying Ollama's raw
`/api/generate` response directly (not through `call_ollama`) exposed
the actual mechanism: **`prompt_eval_count` came back `2050`** for that
~22,000-token prompt. `common/ollama_utils.py`'s `call_ollama()` never
set `options.num_ctx` in its request — Ollama silently defaults to
~2048 tokens of context when it's omitted, *regardless of the model's
real maximum*, and llama.cpp keeps the **tail** of a prompt that
overflows `num_ctx`, not the head. That single mechanism explains both
findings at once: pass 1's citation/formatting instructions sit at the
very *top* of every prompt, so a ~4,200-token prompt truncated to its
last ~2,048 tokens would drop those instructions before the model ever
saw them; pass 2's 3-video prompt truncated to its last ~2,048 tokens
kept only a fragment of the final video's transcript, explaining why
the note only reflected that video's content.

**Fix:** `call_ollama()`/`call_ollama_embeddings()` now default
`num_ctx` to an estimate sized to the actual prompt (`_estimate_num_ctx`
in `common/ollama_utils.py`: ~4 chars/token, plus response headroom,
rounded up to a 2048-token step), overridable via an explicit `num_ctx`
argument. This is a **shared-infrastructure fix** — `problem_gen/` and
`viz/` call the same `call_ollama()` and were silently exposed to the
same truncation for any prompt over ~2048 tokens; neither had reported
symptoms, most likely because their prompts (a style/content retrieval
pool, a viz code-gen request) typically run smaller than a full lecture
transcript. Full test suite (1017 tests, including new coverage in
`tests/test_ollama_utils.py` for the estimate scaling/rounding and the
request payload actually carrying `num_ctx`) passes with the fix in.

**Re-verification of the citation question, now that the real bug is
fixed, is in progress** (a single-video, ~4,200-token re-run against
`qwen2.5:7b-instruct` with the fix applied) — results below once it
completes. The original "ship without citations, revisit later" user
decision may no longer be the right call once this is confirmed; the
two committed notes from pass 1 will be regenerated if so.

**New finding from the fix itself: CPU cost scales badly with the
now-correct larger `num_ctx`.** The 3-video, ~22,000-token prompt from
pass 2, re-run with a correctly-sized `num_ctx` (24,576, set manually
for this diagnostic), did not complete within a 1200s (20-minute)
timeout on CPU-only Ollama — correctness and speed are in real tension
here: the *previous*, buggy behavior was fast specifically because it
was silently discarding nearly all of the input. A multi-video group
whose combined transcript is large may simply not be practical to
synthesize in one shot on CPU-only hardware; worth revisiting as a
map-reduce-style synthesis (summarize each video individually first,
then combine the short per-video summaries in a second, much
smaller-context pass) rather than one giant concatenated prompt, if
large multi-video groups turn out to be common in practice.

## What pass 1 confirms end-to-end

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

## Pass 2: next 6 videos from the same playlist (in progress, 2026-09-06)

Started once pass 1's fixes landed, to check the pipeline holds up at a
larger batch size (2 → 6 videos in one run) and against a title pattern
pass 1 didn't cover: `Lecture 1(B)`, `Lecture 2(A)`, `Lecture 2(B)`,
`Lecture 3(A)`, `Lecture 3(B)`, `Lecture 4(A)` — every title here
matches the `Lecture N` series regex (spec §4 tier 2), unlike pass 1's
"2021 Introductory Remarks" (no match at all).

- Run via `--urls` again (6 individually-resolved video URLs), not
  `--playlist` — same reason as pass 1 (avoid pulling the full 105-video
  playlist) and still means the playlist-merge default tier (§4 tier 1)
  stays unexercised by real data.
- Because none of these 6 titles share the *same* `(A)`/`(B)` suffix
  combination twice (`_title_stem()` keeps `(A)`/`(B)` in the stem, so
  `Lecture 1(B)` and `Lecture 2(B)` produce different stems, not a
  shared 2+-member one), and there's no playlist context to trigger the
  playlist-default rule either, every video here is expected to land in
  tier 3 (content-clustering) or tier 4 (singleton) rather than tier 2
  (title-series) — worth checking whether that matches what actually
  happens once results are in, since these lectures *are* genuinely
  sequential/related content that a human would probably group.
- Model: `qwen2.5:7b-instruct` (now the locally-pulled default, no
  re-pull needed this time).

## Pass 2 results

All 6 videos downloaded and transcribed with zero failures
(`{'videos_transcribed': 6, 'videos_failed': 0, 'groups_synthesized': 3,
'groups_unchanged': 0, 'groups_failed': 0}`).

**Grouping:** the hypothesis above was wrong in an interesting way — 6
videos produced **3 groups**, not 6 singletons:
- `{Lecture 1(B), Lecture 4(A), Lecture 2(B)}` — three videos with
  different lecture numbers, clustered by transcript-embedding
  similarity (tier 3).
- `{Lecture 2(A)}` — alone (its own `(B)` counterpart landed in the
  group above instead of with it).
- `{Lecture 3(A), Lecture 3(B)}` — correctly paired, the same lecture's
  two parts.

Tier 3 clustering is doing *something* real (it's not random), but the
first group's membership doesn't match the naive expectation that
`(A)`/`(B)` pairs of the *same* lecture number should cluster together
— instead it grouped across different lecture numbers, and split one
genuine `(A)`/`(B)` pair (`2(A)`/`2(B)`) across two different groups.
Plausible explanation: this is foundational math content where
"sets," "functions," and "n-tuples" are recurring vocabulary across
many consecutive lectures (a review-heavy math camp), so whole-transcript
embedding similarity may be picking up shared terminology-density rather
than "these two videos are parts of the same lecture." This is exactly
the empirical tuning the original design spec (§10) flagged as needed
for the `0.75` similarity threshold, now with a concrete real example
to tune against — not fixed here.

**Synthesis quality:** this is what surfaced Bug #2 above — the 3-video
group's note only reflected one video's content, traced to `call_ollama`
silently truncating the ~22,000-token combined prompt to its last
~2,048 tokens. The two smaller groups (1 and 2 videos respectively, both
comfortably under the old silent 2048-token ceiling once headroom is
accounted for) were less affected by truncation but still relevant to
the citation question being re-verified above.

**Indexing:** all 3 new cards correctly landed as `doc_type:
"lecture_notes"` (Bug #1's fix holding up under a second, larger real
run).
