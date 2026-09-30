# Audio Generator: Real End-to-End Validation

Real-world validation of `audio_generator/` (spec:
`docs/superpowers/specs/2026-09-06-audio-generator-design.md`, plan:
`docs/superpowers/plans/2026-09-06-audio-generator.md`), run against one
real, genuinely difficult file
(`academic_notes/math-camp/ta_notes/processed_outputs/LN_Probability.md`,
121,637 raw chars, equation-dense) rather than the mocked unit tests. This
single file drove three successive revisions of the design (v2 local LLM
→ v3 Gemini API → §3.2 episode splitting), each triggered by a real
measurement the mocked tests couldn't have surfaced.

## Important scope note: this test is the hard case, not the common case

`LN_Probability.md` is raw, unedited TA notes — dense LaTeX, no
authorial concession to "this might become audio someday." It was
deliberately chosen to stress-test `narrate.py`'s LaTeX-to-prose
correctness under worst-case conditions, and it did its job (surfacing
real bugs and real limits at every stage below).

**It is not representative of the pipeline's primary intended future
use.** The actual planned consumer is different: **LLM-generated summary
text** (e.g., a weekly per-course summary synthesized from multiple
notes/textbook chapters — see the still-undecided "notes + textbook
chapters → weekly summary → mp3" pipeline discussed but not yet
designed). That text is already plain, spoken-friendly prose by
construction — an LLM writing an explanatory summary doesn't emit raw
`$\mathbb{E}[X]$`-style LaTeX unless asked to. **Feeding LLM-generated
summary text through `narrate.py`'s Gemini rewrite step would be a
second, unnecessary API call** — the primary use case should likely skip
straight from `cleaner.clean_markdown_for_speech()` to
`engine.synthesize_speech()`, bypassing `narrate.py` entirely. `narrate.py`'s
tiered Gemini narration remains the right tool for the *secondary* use
case this test exercised (turning raw, already-existing LaTeX-heavy
notes/textbook content into audio directly, e.g. "make this whole
textbook chapter into an mp3"), not the primary one. Not designed or
built yet — flagged here so it isn't lost, and recorded in spec §9.

## v2 → v3: why local Ollama narration was abandoned

**v2 (local `qwen2-math:7b`, spec §3.1 v2):** fixed a real correctness bug
(the original regex wrap read raw LaTeX commands aloud verbatim), but
real CPU timing against `LN_Probability.md` came back at **21,758.5s
(~6h 2m) for one file** — three attempts were needed to even get a clean
measurement, the first two killed by memory pressure (one genuine OOM at
under 500MB free, one a false alarm from the Claude Code harness's own
background-task memory guard rather than real Windows OOM). Impractical
for any real batch use at the intended volume (3-4 files/week).

**v3 (tiered Gemini API, spec §3.1 v3):** replaced the local model with
`gemini-3.1-flash-lite`/`gemini-2.5-flash`, tiered by per-chunk LaTeX
density (no-math chunks make zero API calls). Same file: **777.3s (13.0
min)**, ~28x faster. Rough cost: $0.08-$0.13/file, ~$1-2/month at the
target volume. Both model names were confirmed live against the actual
Gemini API rather than assumed from documentation or third-party pricing
pages (which returned different, non-matching model names — `gemini-2.5-flash`/
`gemini-3.7-flash` — that don't reflect what this project's own
`common/gemini_utils.py`-based subprojects actually call).

**Narration concurrency bug found and fixed:** the first cross-section
design (§3.2, below) called `narrate_for_speech()` once per section in a
sequential loop — each call had its own internal concurrency across that
section's chunks, but sections were processed one after another,
confining parallelism to one section's batch at a time. Fixed by
exposing `narrate.chunk_for_narration()`/`narrate.narrate_chunks()` as
public functions and flattening every section's chunks into one list
before dispatching a single shared concurrent call. Fully
backward-compatible — all 20 existing `narrate.py` tests passed unchanged
after the refactor.

## v3 → §3.2: why episode splitting was added

Running v3 end-to-end (not just the isolated timing script) produced a
technically-correct **3h22m single MP3** for one source file — no length
cap was an explicit v1 non-goal, but a real listening test made clear
"one file per source note" and "actually useful for a commute" are
different goals once a note is long enough.

**Design:** split the raw `.md` at every header level (not a fixed
depth — `LN_Probability.md` has only 4 top-level headers, each spanning
hundreds of lines, so splitting only at `#` would still yield 30-60+
minute files), narrate/clean each section, then greedily group
consecutive sections into 10-20 minute episodes using a real measured
calibration: 196,109 narrated chars → 202.5 min of Piper audio, ≈969
chars/minute.

## Real end-to-end run, 2026-09-09 (post-fix, fully parallelized)

Same file, full pipeline (split → flatten-and-narrate → group → parallel
synthesize):

- **Narration: 227.1s (3.8 min)** for 74 header-delimited sections — down
  from 13.0 min (the single-whole-file v3 measurement) and dramatically
  down from the per-section-serialized bug's would-be time.
- **Grouped into 9 episodes.**
- **Synthesis: 1165.3s (19.4 min) wall-clock** across 3 concurrent Piper
  workers, vs. 3353.0s (55.9 min) summed sequentially — ~2.9x speedup,
  close to the theoretical ceiling given one oversized episode dominates
  (see below).
- **Total: 1392.5s (23.2 min) end to end** — vs. the original v3
  whole-file run's combined ~37 min (13 min narrate + ~24 min single
  giant synthesis), while now producing 9 separately listenable files
  instead of one 3h22m blob.

Per-episode breakdown:

| Part | Chars | Sections (titles) | Synth time |
|---|---|---|---|
| 01 | 18,257 | Introduction, 1, 1.1, 1.2 | 352.1s |
| 02 | 60,389 | Example 1.3, 1.3, Def 1.4, 1.4, 1.5 | 1067.3s |
| 03 | 17,835 | 4, 4.1-4.8, 5, 5.1, 5.2 | 341.2s |
| 04 | 14,522 | 5.3-5.7, 6, 6.1 | 280.4s |
| 05 | 23,079 | 6.2 (alone) | 405.4s |
| 06 | 19,430 | 8.3-8.7, 9, 9.1-9.9 | 338.2s |
| 07 | 19,116 | 10, 10.1-10.4, 11, 11.1-11.3, 12, 12.1-12.4 | 323.8s |
| 08 | 19,310 | 12.5-12.8, 13, 13.1-13.8 | 205.5s |
| 09 | 3,188 | 14 (References) | 39.1s |

Output files: `LN_Probability__part01.mp3` .. `__part09.mp3` and matching
`.narrated.md` siblings, plus `LN_Probability__index.md`, all in
`academic_notes/math-camp/ta_notes/processed_outputs/`.

## Known issue, confirmed real (not fixed yet — deferred pending listening review)

**Part 02 came out at 60,389 chars (~62 min), 3x the 20-minute target.**
Root cause: source section "1.5 Probability measures" spans raw lines
372-1083 (711 lines) with **zero sub-headers** — one genuinely undivided
block of content. A few small preceding sections (Example 1.3, 1.3, Def
1.4, 1.4) hadn't yet reached the 10-minute floor, so the algorithm
correctly held them over per spec §3.2's design ("never split inside one
section") and merged them with 1.5 — which then turned out to be huge.

This is exactly the edge case spec §9 flagged as "expected to be rare...
but unverified against a broad sample of the actual corpus" — now
**confirmed to occur on the very first real file tested, not rare here.**
A natural fix: when a leaf section alone exceeds the target, fall back to
splitting it on paragraph boundaries (not headers) instead of accepting
it whole. **Not implemented yet** — the user wants to listen to the 9
real files and compare against the source content first, before deciding
whether/how to fix this.

## Next steps (not yet done)

- Listen to all 9 real MP3s and spot-check against `LN_Probability.md`'s
  actual content for narration/synthesis quality.
- Decide whether to fix the oversized-Part-02 case (paragraph-level
  fallback splitting) based on how much it actually matters after
  listening.
- Design the primary use case (LLM-generated summary text → audio,
  skipping `narrate.py` entirely) once the "notes + textbook chapters →
  weekly summary → mp3" pipeline itself is designed — not started.
- `textbook` chapter-boundary reuse via `textbook/chapter_index.py`
  remains unexplored (spec §9).
