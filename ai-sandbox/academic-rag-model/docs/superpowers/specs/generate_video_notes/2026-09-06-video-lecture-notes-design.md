# Video Lecture Notes — Design Spec

Date: 2026-09-06
Status: approved in brainstorming, not yet planned/implemented

## 1. Problem & goals

Today the hub's per-course resources include an empty `lecture-recordings/`
folder under `academic_resources/<course>/` (e.g. `econometrics/`,
`env-science/`) — recorded lectures aren't yet processed into anything.
This spec designs **`video_notes`**: a new subproject that turns a batch of
YouTube lecture URLs into synthesized Markdown notes under
`academic_notes/<course>/lecture-notes/`, complementing the existing
textbook and note resources the same way `problem_gen` and `journal_discovery`
complement them.

Adapted from a Gemini-suggested script (single-video download → transcribe →
one Gemini API call for Markdown synthesis), with two changes driven by this
project's existing conventions: batch/multi-video input, and a **local**
Ollama model for synthesis instead of a paid API call — the pipeline should
cost network bandwidth and CPU time, not per-lecture API spend, matching
`problem_gen`'s local-generation approach (`common/ollama_utils.py`).

**Goals**
- Given a batch of YouTube URLs (individual videos or playlist URLs) and a
  `--course` (matching an existing `academic_notes/<course>/` folder), download
  audio, transcribe locally, group videos into logical lecture series
  automatically (no manual per-batch config — see §4), and synthesize one
  cohesive Markdown note per group using a local Ollama model.
- Preserve clickable YouTube timestamp links in the synthesized notes so a
  concept can be traced back to the exact moment it was covered in its
  source video.
- Resumable: a batch interrupted partway through, or extended later with more
  URLs for the same course, only (re-)does the work that's missing or
  affected, never a full re-run from scratch.
- Register each synthesized note with the existing Source Indexer
  (`doc_type="lecture-notes"`) so the RAG tutor can retrieve it, same as
  textbooks and problem sets.
- Never touch the corpus's existing embedding space, doc_type vocabulary, or
  file-identity scheme in a way that risks other content types (see §6).

**Non-goals**
- No manual grouping config (YAML/manifest) — explicitly ruled out during
  brainstorming in favor of automatic grouping.
- No cloud transcription or paid summarization API — CPU-only local Whisper
  and local Ollama throughout (embeddings used for grouping are also local,
  §4).
- No re-implementation of indexing/chunking/RAG — reuses `indexer/` and
  `rag/` exactly as `journal_discovery` and `problem_gen` already do.
- No automatic course inference — the user names the course per batch
  (approved during brainstorming); only *grouping within* a course batch is
  automatic.

## 2. Architecture

A new sibling package, `video_notes/`, alongside `problem_gen/`, `indexer/`,
`journal_discovery/`, `textbook/`, `notes/` in `academic-rag-model/`. Depends
on `common/ollama_utils.py` (reused unchanged for the synthesis call) and, for
the indexer-integration step only, `indexer/index_search.py` (extended, §6).
Run as a module from the `academic-rag-model/` root, matching every other
subproject:

```powershell
python -m video_notes.pipeline --course econometrics `
  --urls "https://youtube.com/watch?v=AAAA" "https://youtube.com/watch?v=BBBB" ...
python -m video_notes.pipeline --course math-camp --playlist "https://youtube.com/playlist?list=XXXX"
```

Both `--urls` (repeatable / space-separated) and `--playlist` are accepted in
the same run and merged before processing; `--course` is required.

## 3. Pipeline stages

Each stage is idempotent per video, keyed by video ID, and checked against
per-course state (§5) before running — a re-run of the same command only
does what's missing.

1. **Fetch metadata** (`metadata.py`) — `yt-dlp --dump-json`, no download:
   video ID, title, channel ID, playlist ID/title/index, duration, upload
   date. Always re-fetched (cheap, no state needed) so grouping always sees
   current playlist membership even if the user edited a playlist since the
   last run.
2. **Download + extract audio** (`audio.py`) — yt-dlp → mp3, same
   `FFmpegExtractAudio` postprocessor as the Gemini draft. Skipped if this
   video's state already shows `transcribed`.
3. **Transcribe locally** (`transcribe.py`) — faster-whisper, CPU
   (`small`, `compute_type="int8"` by default — see §7 for override), segment
   list with start times preserved. Written to
   `video_notes/.cache/transcripts/<video_id>.json` (segments + metadata);
   audio file deleted immediately after (matches the Gemini draft — audio is
   the one artifact deliberately not kept, since re-fetching + re-extracting
   is cheap next to re-transcribing).
4. **Group** (`grouping.py`) — three-tier automatic algorithm, run once per
   pipeline invocation across all of this course's videos with metadata
   fetched so far (not just this batch's new URLs — see §5). Detailed in §4.
5. **Synthesize** (`synthesize.py`) — for each group whose membership or
   member transcripts changed since its last synthesis (§5), build one
   ordered, timestamped transcript payload spanning all its member videos and
   send it to a local Ollama model in one prompt (adapted from the Gemini
   draft's pedagogy/timestamp-citation prompt, §7), producing one Markdown
   note.
6. **Save + index** (`pipeline.py` orchestrates; `indexer/index_search.py`
   does the indexing) — Markdown + a `.meta.json` sidecar written to
   `academic_notes/<course>/lecture-notes/`; the course's index is then
   rebuilt via `indexer.index_search rebuild --course <course>` (§6).

A video whose download, transcription, or metadata fetch fails is recorded
`failed` in state with the error, skipped for the rest of this run, and
retried automatically on the next invocation (not permanently excluded) —
consistent with the resumability goal.

## 4. Grouping algorithm

Runs across **all** of a course's videos with fetched metadata (state file,
§5), not just newly-added URLs, so a new video can join an existing group and
correctly trigger its re-synthesis (§5) — and so groups stay consistent
regardless of which run first introduced which member.

1. **Scope by playlist.** Partition videos into buckets by `playlist_id`
   (videos with no playlist form a `(no playlist, channel_id)` bucket
   instead — see rationale below).
2. **Subdivide by title-series, within each scope.** Inside each playlist
   bucket (or no-playlist/channel bucket), detect a `Lecture N` / `Part N` /
   `Week N` (etc.) numbering pattern in titles via regex; videos sharing the
   same title *stem* (title with the number and surrounding lecture/part/week
   word stripped) become one group. This is the step that subdivides a
   playlist containing multiple distinct lecture series (e.g. "Unit 1: Sets,
   Lecture 1-3" and "Unit 2: Metric Spaces, Lecture 1-3") into separate
   groups instead of merging the whole playlist into one.
3. **Content-clustering fallback, same scope.** Videos in a scope that don't
   match any sibling by title pattern get embedded (their transcript text,
   via a local Ollama embedding model — `nomic-embed-text` by default, §7)
   and clustered by cosine similarity above a threshold (tunable, default
   `0.75` — flagged in §9 as needing empirical tuning against real lecture
   transcripts, the same way `journal_discovery`'s relevance threshold was).
   Clustering is scoped to the *same* playlist/channel bucket from step 1 —
   never merges videos across unrelated playlists or channels, even if their
   content happens to be topically similar.
4. **Singletons.** A video matched by neither step 2 nor step 3 becomes its
   own one-video group.

Groups are ordered internally by `playlist_index` when set, else
`upload_date`, so synthesis always sees lectures in viewing order regardless
of the order URLs were passed to the CLI.

**Why bucket a channel's non-playlisted videos together (step 1):**
narrows step 3's clustering candidate pool to one channel's lectures rather
than the whole course's corpus of videos, which both keeps runtime down (no
quadratic all-pairs comparison across every video ever added to a course) and
avoids two different lecturers' unrelated videos on a shared topic (e.g. two
different "Introduction to Eigenvalues" videos from different channels)
getting merged into one synthesized note.

## 5. State & resumability

`video_notes/.state/<course>.json`, keyed by video ID:

```json
{
  "AAAA111": {
    "url": "https://youtube.com/watch?v=AAAA111",
    "metadata": { "title": "...", "channel_id": "...", "playlist_id": "...", "playlist_index": 1, "upload_date": "20260101" },
    "stage": "transcribed",
    "transcript_path": ".cache/transcripts/AAAA111.json",
    "group_id": "g_7f3a",
    "error": null
  }
}
```

`video_notes/.state/<course>_groups.json`, keyed by a group ID (stable across
re-grouping runs by content — see below):

```json
{
  "g_7f3a": {
    "member_video_ids": ["AAAA111", "BBBB222", "CCCC333"],
    "slug": "real-analysis-lectures",
    "member_content_hash": "sha256-of-sorted-member-ids-and-their-transcript-hashes",
    "last_synthesized_at": "2026-09-06T00:00:00Z",
    "note_path": "academic_notes/math-camp/lecture-notes/real-analysis-lectures.md"
  }
}
```

- **Group identity vs. content:** a group's `member_content_hash` combines
  its sorted member video IDs and each member's transcript content hash.
  Re-running §4's grouping regenerates the *membership*; a group only gets
  re-synthesized (stage 5, §3) when this hash differs from what's stored —
  so adding one new lecture to a 5-lecture playlist re-synthesizes just that
  one group, not the whole course, and doesn't touch groups whose membership
  and transcripts are unchanged.
- **Video-level stages:** `metadata_fetched → downloaded → transcribed`.
  Grouping and synthesis are tracked at the group level (above), not
  per-video, since synthesis output is inherently a function of the whole
  group.
- A crashed run simply leaves some videos below `transcribed` and some
  groups with a stale/missing `member_content_hash` — the next invocation's
  per-stage checks naturally pick up exactly the remaining work.

## 6. Output location & indexer integration

Each group's Markdown note is written to
`academic_notes/<course>/lecture-notes/<slug>.md`, with a sidecar
`academic_notes/<course>/lecture-notes/<slug>.meta.json` (source video URLs/
IDs/titles, group tier that matched in §4, synthesis timestamp) — same
sidecar pattern `journal_discovery` uses for bibliographic metadata it
doesn't want to force into the shared card schema.

**Why this needs one small, additive change to `indexer/index_search.py`:**
`rebuild()` today discovers indexable content two ways — `_notes_pdf_paths()`
(a `.pdf` under any `academic_notes/<course>/<category>/`, with a sibling
`processed_outputs/<basename>.md`) and `_textbook_book_dirs()` (a
`_metadata.json` + `.md` pair under `academic_resources/<course>/textbooks-and-papers/processed_outputs/`).
A synthesized lecture note has no source PDF at all, so it fits neither
shape — without a third discovery path, `rebuild()`'s orphan-pruning pass
(`_flag_or_prune_orphans`, working off files it actually walked) would
eventually flag or delete these notes' index cards as orphans, since they'd
never appear in `seen_file_ids`. This is a narrow, additive parallel to the
existing two functions, not a change to indexer's shared embedding space or
`KNOWN_DOC_TYPES` vocabulary (a lecture note's doc_type just falls back to
its folder name, `"lecture-notes"`, exactly like `"articles"` or
`"briefings"` do today when the LLM classifier doesn't pick one of the four
specially-known types — see `index_card.py:258-260`).

- **New `_video_lecture_note_paths(academic_hub_root, course_filter)`** in
  `index_search.py`, mirroring `_textbook_book_dirs()`'s shape: walks
  `academic_notes/<course>/lecture-notes/`, yielding
  `(course, "lecture-notes", md_path, meta_json_path)` for every `.md` with a
  sidecar present.
- **`rebuild()` gets a third loop** over this generator, computing
  `file_id` as a truncated SHA-256 of the *sidecar's* `member_video_ids`
  (sorted, joined) rather than hashing the `.md` file itself or a
  nonexistent PDF — this is the correct analogue of "hash the immutable
  source, not the derived output" that `compute_file_id` already does for
  PDFs (`index_card.py:44-49`): a group's identity is its video membership,
  and its `.md` content is the mutable, re-synthesizable artifact, exactly
  parallel to how a textbook's PDF bytes are its identity while its `.md` is
  re-derivable. `source_pdf_path` on the resulting card stores the sidecar's
  relative path (a repurposed-but-unvalidated string field already, per
  `_reconcile_one` (`index_search.py:313-317`), which never checks it resolves to a real PDF).
  `content_hash` (staleness signal) stays exactly what it already is
  elsewhere: a hash of the `.md` file's own bytes.
- Existing staleness (`_is_stale`) and orphan-pruning logic then apply
  unmodified — a re-synthesized note (changed `.md` content, same member
  video IDs) is correctly seen as "updated," and a note whose group was later
  deleted entirely is correctly prunable.
- After the pipeline finishes writing notes for a course, it shells out to
  `python -m indexer.index_search rebuild --course <course>` (or calls
  `rebuild()` directly, whichever `problem_gen`/`journal_discovery` convention
  turns out to match — resolved during planning) exactly the way textbook/
  notes conversion already treats indexing as a separate, explicit step
  from conversion itself (`chunk_index.py`'s existing design rationale,
  §2 of that spec).
- Passage-level chunking (`index_search.py chunk`) picks up the new cards on
  its own next run, using the default heading-based chunking tier (lecture
  notes use Markdown headers the same as any other synthesized note) — no
  change needed there.

## 7. Models & configuration

- **faster-whisper**: `small`, `device="cpu"`, `compute_type="int8"` by
  default (int8 quantization trades a little accuracy for materially faster
  CPU inference than float32) — override via `VIDEONOTES_WHISPER_MODEL` /
  `VIDEONOTES_WHISPER_COMPUTE_TYPE`.
- **Ollama synthesis model**: default a general-purpose instruct model, not
  `problem_gen`'s math-only `qwen2-math:7b`, since lecture content here spans
  math *and* economics (`qwen2.5:7b-instruct` as the starting default) —
  override via `VIDEONOTES_OLLAMA_MODEL`, same override pattern as
  `PROBLEMGEN_OLLAMA_MODEL`. Uses `common.ollama_utils.call_ollama` unchanged.
- **Ollama embedding model** (grouping fallback only, §4, tier 3):
  `nomic-embed-text`, overridable via `VIDEONOTES_EMBED_MODEL`. This is a
  private, run-scoped embedding space (grouping candidates within one
  course/scope), never written to `.index/` and never compared against
  `chunk_index.py`/`index_card.py`'s embeddings — same non-interference
  argument `journal_discovery`'s `relevance.py` makes for its own local
  embedding model (`2026-08-31-journal-discovery-design.md` §3, §9).
- **Synthesis prompt** carries over the Gemini draft's pedagogy + LaTeX +
  timestamp-citation instructions, adapted for multi-video input: each
  transcript line is tagged with its source video's title and per-video
  YouTube timestamp link (`[Lecture 2 @ 05:12](https://youtu.be/BBBB222&t=312s)`)
  so a group-spanning synthesis can still cite the correct originating video,
  not just a bare second count.

## 8. Error handling

- A yt-dlp download failure, a corrupt/unreadable audio file, or a network
  error during metadata fetch marks that video `failed` in state (with the
  error message) and the pipeline continues with the rest of the batch — one
  bad video never blocks the others, per the resumability goal.
- `common.ollama_utils.call_ollama` already distinguishes "server
  unreachable" (`None`) from "request timed out" (`OLLAMA_TIMEOUT`) — reused
  unchanged; a synthesis failure for one group is recorded and retried on the
  next invocation, same as `problem_gen`'s retry behavior, rather than
  failing the whole run.
- A group whose synthesis repeatedly fails (LLM output doesn't parse as
  usable Markdown) is left `needs_indexing`-equivalent — flagged in its
  group record, surfaced in the run summary — rather than silently retried
  forever or silently producing a broken note on disk.
- `_video_lecture_note_paths()` skips (with a warning, not a hard failure) a
  `.md` file whose sidecar is missing or unparsable, matching
  `_textbook_book_dirs()`'s existing "no `_metadata.json` → skip" behavior
  (`index_search.py:368-378`).

## 9. Testing

Mirrors the existing flat `tests/` convention (package-qualified imports via
the root `conftest.py`), mocking every external boundary — no real network,
whisper model, or Ollama calls in tests:

- `metadata.py` / `audio.py`: mocked yt-dlp responses/downloads.
- `transcribe.py`: mocked faster-whisper segment output (transcription
  correctness is Whisper's own concern, not this pipeline's).
- `grouping.py`: the highest-value test target — synthetic metadata fixtures
  exercising all three tiers independently (shared playlist ID; title-series
  regex match within a scope; content-clustering fallback with mocked
  embedding vectors and a known similarity threshold) and the
  "never merges across scopes" invariant from §4.
- `synthesize.py`: mocked `call_ollama`, testing prompt construction
  (per-video timestamp tagging) and re-synthesis triggering off
  `member_content_hash` changes, not real model output.
- `indexer/index_search.py` additions: unit tests for
  `_video_lecture_note_paths()` and the new `rebuild()` branch's file_id/
  staleness/orphan behavior, parallel to existing tests for
  `_textbook_book_dirs()`/`_notes_pdf_paths()` if any exist today.
- Real end-to-end run against 1-2 short real lecture videos as manual
  validation before trusting the pipeline on a large batch — CPU timing for
  the combined whisper+ollama workload is unproven (flagged in §9 below as
  the first thing to measure once built, the same way `problem_gen`'s status
  doc records real measured Ollama timings before it was trusted at scale).

## 10. Open questions / follow-on (not decided by this spec)

- **Real CPU timing is unmeasured.** `problem_gen`'s CPU-only Ollama calls
  took minutes each; this pipeline runs both Whisper transcription *and* an
  Ollama synthesis call per group. The plan should measure real timings on a
  couple of real lecture videos early, the same way `problem_gen`'s status
  doc did, before assuming a large batch is practical to run in one sitting.
- **Content-clustering similarity threshold (§4, tier 3) needs empirical
  tuning** against real lecture transcripts, exactly as flagged for
  `journal_discovery`'s relevance threshold — the `0.75` default here is a
  starting point, not a validated value.
- **Rebuild invocation mechanics** (subprocess shell-out vs. direct
  `rebuild()` call from within `video_notes`) should follow whatever
  convention the planning phase finds `problem_gen`/`journal_discovery`
  actually use for their own indexer hand-off, rather than being decided
  speculatively here.
- **Title-series regex coverage (§4, tier 2)** is necessarily heuristic —
  lecture titles in the wild vary a lot ("Lecture 3", "Lec 3", "Part III",
  "Week 4 - Session 1"). The plan should collect a handful of real playlist
  title sets during implementation to validate the pattern set against,
  rather than guessing patterns without real examples.
