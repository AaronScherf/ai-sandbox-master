# Video Lecture Notes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `video_notes/`, a subproject that turns a batch of YouTube lecture URLs into synthesized Markdown notes under `academic_notes/<course>/lecture-notes/`, using local transcription and local synthesis — no paid API call except the existing indexer's own per-note classification step.

**Architecture:** Six local stages (fetch metadata → download+extract audio → transcribe via faster-whisper → group automatically → synthesize via a local Ollama model → save+index), each resumable via per-course JSON state files. Grouping is a three-tier automatic algorithm (playlist-as-default → title-series subdivision → content-clustering fallback on local Ollama embeddings). Indexing reuses the existing Source Indexer's `reconcile_and_write()`, plus one small additive discovery function in `indexer/index_search.py` so a corpus-wide `rebuild()`/prune never treats these notes as orphans.

**Tech Stack:** Python 3, `unittest` + `unittest.mock` (this project's existing test stack), `yt-dlp`, `faster-whisper` (new dependencies), `scikit-learn`/`numpy` (already installed, used for tier-3 clustering), Ollama's local HTTP API (via `common/ollama_utils.py`), the existing `indexer` package.

**Spec:** `docs/superpowers/specs/2026-09-06-video-lecture-notes-design.md`

## Global Constraints

- No paid API call for transcription or synthesis — local `faster-whisper` and local Ollama only (spec §1, §7). The existing indexer's per-note Gemini classification+embedding call (`indexer/index_card.py`'s `generate_index_card()`) is unchanged, existing behavior, reused as-is (spec §6).
- No manual per-batch grouping config — grouping is fully automatic (spec §1, §4).
- Never merges videos across different playlists or channels, even when content is topically similar (spec §4) — every grouping tier operates within one playlist/channel scope.
- A playlist whose videos show no genuine title-series subdivision (fewer than 2 distinct multi-member stems) stays one group by default — subdivision is opt-in when detected, not the default for every playlist (spec §4, refined during planning from the brainstormed algorithm to match the user's actual ask: subdivide playlists that *have* subgroups, keep the rest as one group).
- CPU-only defaults: `faster-whisper` `small`/`int8`; Ollama synthesis model `qwen2.5:7b-instruct` (general-purpose, not `problem_gen`'s math-only `qwen2-math:7b`, since lecture content spans math and economics) — both overridable via env vars (spec §7).
- Resumable per course: a video already `transcribed` is never re-downloaded/re-transcribed; a group only gets re-synthesized when its `member_content_hash` (membership + transcript content) changes (spec §5).
- A failing video or group is recorded in state and skipped — never blocks the rest of the batch, and is retried automatically on the next run (spec §8).
- `doc_type` for a lecture note falls back to its folder name, `"lecture-notes"` — no change to `indexer/index_card.py`'s `KNOWN_DOC_TYPES` (spec §6).
- A lecture note's identity (`file_id`) is derived from its group's member video IDs, not its Markdown content — the content is the mutable, re-synthesizable artifact, exactly parallel to how a textbook's identity is its PDF's bytes, not its derived `.md` (spec §6).

---

### Task 1: Package scaffolding and new dependencies

**Files:**
- Create: `video_notes/__init__.py`
- Modify: `.gitignore`
- Test: `tests/test_video_notes_package.py`

**Interfaces:**
- Produces: the `video_notes` package (empty for now); `yt-dlp` and `faster-whisper` installed in `.venv`. Every later task imports from `video_notes.*`.

- [ ] **Step 1: Install the new dependencies**

Run: `./.venv/Scripts/python.exe -m pip install yt-dlp faster-whisper`
Expected: both install successfully (this repo has no `requirements.txt` — every subproject documents its own dependencies in its README, per the existing `problem_gen`/`viz` convention; Task 12 adds `video_notes`'s own README entry).

- [ ] **Step 2: Write the failing test**

Create `tests/test_video_notes_package.py`:

```python
import importlib
import unittest


class TestVideoNotesPackageScaffolding(unittest.TestCase):
    def test_package_imports(self):
        module = importlib.import_module("video_notes")
        self.assertIsNotNone(module)

    def test_yt_dlp_is_installed(self):
        import yt_dlp  # noqa: F401

    def test_faster_whisper_is_installed(self):
        import faster_whisper  # noqa: F401
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `python -m unittest tests.test_video_notes_package -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'video_notes'`

- [ ] **Step 4: Create the package**

Create `video_notes/__init__.py` (empty file).

- [ ] **Step 5: Add pipeline-internal state/cache dirs to `.gitignore`**

In `.gitignore`, add:

```
video_notes/.state/
video_notes/.cache/
```

- [ ] **Step 6: Run the test to verify it passes**

Run: `python -m unittest tests.test_video_notes_package -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add video_notes/__init__.py .gitignore tests/test_video_notes_package.py
git commit -m "$(cat <<'EOF'
feat(video_notes): scaffold package, add yt-dlp/faster-whisper deps

First step of the video-lecture-notes pipeline: an empty package plus
the two new local-processing dependencies it needs (no paid API for
download/transcription, per the design spec).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01RSVwgCfAbdoph7ua8uziz8
EOF
)"
```

---

### Task 2: `youtube_metadata.py` — metadata-only lookups

**Files:**
- Create: `video_notes/youtube_metadata.py`
- Test: `tests/test_youtube_metadata.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `VideoMetadata` (dataclass: `video_id: str, url: str, title: str, channel_id: str, playlist_id: str | None, playlist_title: str | None, playlist_index: int | None, upload_date: str | None, duration: float | None`), `fetch_video_metadata(url: str) -> VideoMetadata`, `fetch_playlist_metadata(playlist_url: str) -> list[VideoMetadata]`. Every later task that touches videos uses this exact `VideoMetadata` shape.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_youtube_metadata.py`:

```python
import unittest
from unittest.mock import MagicMock, patch

from video_notes.youtube_metadata import VideoMetadata, fetch_playlist_metadata, fetch_video_metadata

_FAKE_VIDEO_INFO = {
    "id": "AAAA111", "title": "Lecture 3: Convexity", "channel_id": "UC123",
    "playlist_id": "PL999", "playlist_title": "Math Camp 2026",
    "playlist_index": 3, "upload_date": "20260101", "duration": 3600.0,
}


class TestFetchVideoMetadata(unittest.TestCase):
    @patch("video_notes.youtube_metadata.yt_dlp.YoutubeDL")
    def test_extracts_fields_from_yt_dlp_info(self, mock_ydl_cls):
        mock_ydl = MagicMock()
        mock_ydl.extract_info.return_value = _FAKE_VIDEO_INFO
        mock_ydl_cls.return_value.__enter__.return_value = mock_ydl

        result = fetch_video_metadata("https://youtube.com/watch?v=AAAA111")

        self.assertEqual(result, VideoMetadata(
            video_id="AAAA111", url="https://youtube.com/watch?v=AAAA111",
            title="Lecture 3: Convexity", channel_id="UC123",
            playlist_id="PL999", playlist_title="Math Camp 2026",
            playlist_index=3, upload_date="20260101", duration=3600.0,
        ))

    @patch("video_notes.youtube_metadata.yt_dlp.YoutubeDL")
    def test_missing_playlist_fields_default_to_none(self, mock_ydl_cls):
        mock_ydl = MagicMock()
        mock_ydl.extract_info.return_value = {"id": "BBBB222", "title": "Standalone video", "channel_id": "UC456"}
        mock_ydl_cls.return_value.__enter__.return_value = mock_ydl

        result = fetch_video_metadata("https://youtube.com/watch?v=BBBB222")

        self.assertIsNone(result.playlist_id)
        self.assertIsNone(result.duration)


class TestFetchPlaylistMetadata(unittest.TestCase):
    @patch("video_notes.youtube_metadata.yt_dlp.YoutubeDL")
    def test_returns_one_video_metadata_per_entry(self, mock_ydl_cls):
        mock_ydl = MagicMock()
        mock_ydl.extract_info.return_value = {
            "entries": [
                {"id": "AAAA111", "title": "Lecture 1", "channel_id": "UC123", "playlist_id": "PL999",
                 "playlist_title": "Math Camp 2026", "playlist_index": 1, "upload_date": "20260101", "duration": 100.0},
                {"id": "BBBB222", "title": "Lecture 2", "channel_id": "UC123", "playlist_id": "PL999",
                 "playlist_title": "Math Camp 2026", "playlist_index": 2, "upload_date": "20260102", "duration": 200.0},
            ]
        }
        mock_ydl_cls.return_value.__enter__.return_value = mock_ydl

        results = fetch_playlist_metadata("https://youtube.com/playlist?list=PL999")

        self.assertEqual([r.video_id for r in results], ["AAAA111", "BBBB222"])
        self.assertTrue(all(r.playlist_id == "PL999" for r in results))
        self.assertEqual(results[0].url, "https://www.youtube.com/watch?v=AAAA111")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m unittest tests.test_youtube_metadata -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'video_notes.youtube_metadata'`

- [ ] **Step 3: Implement**

Create `video_notes/youtube_metadata.py`:

```python
"""
youtube_metadata.py
Cheap metadata-only lookups (no download) for a single YouTube video or
an entire playlist, via yt-dlp's own info extraction. Spec:
docs/superpowers/specs/2026-09-06-video-lecture-notes-design.md §3 step 1.
"""
from __future__ import annotations

from dataclasses import dataclass

import yt_dlp

_YDL_OPTS = {"quiet": True, "skip_download": True}


@dataclass
class VideoMetadata:
    video_id: str
    url: str
    title: str
    channel_id: str
    playlist_id: str | None
    playlist_title: str | None
    playlist_index: int | None
    upload_date: str | None
    duration: float | None


def _from_info(info: dict, url: str) -> VideoMetadata:
    return VideoMetadata(
        video_id=info["id"],
        url=url,
        title=info.get("title", ""),
        channel_id=info.get("channel_id") or info.get("uploader_id") or "",
        playlist_id=info.get("playlist_id"),
        playlist_title=info.get("playlist_title"),
        playlist_index=info.get("playlist_index"),
        upload_date=info.get("upload_date"),
        duration=info.get("duration"),
    )


def fetch_video_metadata(url: str) -> VideoMetadata:
    """One yt-dlp info-extraction call, no download. playlist_* fields
    are only populated when `url` itself carries playlist context (e.g.
    a `&list=...` query param) -- a bare video URL yields None for all
    three, which is the correct input to grouping.py's tier-1 scoping
    (spec §4)."""
    with yt_dlp.YoutubeDL(_YDL_OPTS) as ydl:
        info = ydl.extract_info(url, download=False)
    return _from_info(info, url)


def fetch_playlist_metadata(playlist_url: str) -> list[VideoMetadata]:
    """One yt-dlp info-extraction call against the playlist URL itself;
    yt-dlp resolves every entry's full metadata internally, so this
    needs no further per-video network calls."""
    with yt_dlp.YoutubeDL(_YDL_OPTS) as ydl:
        info = ydl.extract_info(playlist_url, download=False)
    videos = []
    for entry in info.get("entries") or []:
        video_url = f"https://www.youtube.com/watch?v={entry['id']}"
        videos.append(_from_info(entry, video_url))
    return videos
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m unittest tests.test_youtube_metadata -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add video_notes/youtube_metadata.py tests/test_youtube_metadata.py
git commit -m "$(cat <<'EOF'
feat(video_notes): add YouTube metadata fetching (no download)

Wraps yt-dlp's info extraction for a single video or a whole playlist
into one VideoMetadata shape -- the input every later grouping/
synthesis step in this pipeline builds on.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01RSVwgCfAbdoph7ua8uziz8
EOF
)"
```

---

### Task 3: `audio_download.py` — download + extract audio

**Files:**
- Create: `video_notes/audio_download.py`
- Test: `tests/test_audio_download.py`

**Interfaces:**
- Consumes: nothing new (plain `video_id: str, url: str` args).
- Produces: `download_audio(video_id: str, url: str, video_notes_root: str) -> str` (returns the mp3 path), `delete_audio(audio_path: str) -> None`. Task 11's `pipeline.py` calls both.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_audio_download.py`:

```python
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from video_notes.audio_download import delete_audio, download_audio


class TestDownloadAudio(unittest.TestCase):
    @patch("video_notes.audio_download.yt_dlp.YoutubeDL")
    def test_returns_expected_mp3_path_and_invokes_download(self, mock_ydl_cls):
        mock_ydl = MagicMock()
        mock_ydl_cls.return_value.__enter__.return_value = mock_ydl
        with tempfile.TemporaryDirectory() as tmp:
            result = download_audio("AAAA111", "https://youtube.com/watch?v=AAAA111", tmp)
            expected = os.path.join(tmp, ".cache", "audio", "AAAA111.mp3")
            self.assertEqual(result, expected)
            mock_ydl.download.assert_called_once_with(["https://youtube.com/watch?v=AAAA111"])


class TestDeleteAudio(unittest.TestCase):
    def test_deletes_existing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "a.mp3")
            with open(path, "w", encoding="utf-8") as f:
                f.write("fake audio")
            delete_audio(path)
            self.assertFalse(os.path.exists(path))

    def test_missing_file_is_a_no_op(self):
        delete_audio(os.path.join(tempfile.gettempdir(), "definitely-does-not-exist.mp3"))  # must not raise
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m unittest tests.test_audio_download -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'video_notes.audio_download'`

- [ ] **Step 3: Implement**

Create `video_notes/audio_download.py`:

```python
"""
audio_download.py
Downloads a video's audio track and extracts it to mp3 via yt-dlp +
ffmpeg -- the one step of the pipeline that needs ffmpeg on PATH. Spec
§3 step 2.
"""
from __future__ import annotations

import os

import yt_dlp


def download_audio(video_id: str, url: str, video_notes_root: str) -> str:
    """Downloads `url`'s audio to
    `<video_notes_root>/.cache/audio/<video_id>.mp3` and returns that
    path. Raises whatever yt-dlp raises on failure -- pipeline.py
    catches this per-video so one bad download doesn't stop the batch
    (spec §8)."""
    audio_dir = os.path.join(video_notes_root, ".cache", "audio")
    os.makedirs(audio_dir, exist_ok=True)
    output_base = os.path.join(audio_dir, video_id)
    ydl_opts = {
        "format": "bestaudio/best",
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
        "outtmpl": output_base,
        "quiet": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    return f"{output_base}.mp3"


def delete_audio(audio_path: str) -> None:
    """Deletes the extracted audio file if present -- audio is
    deliberately not kept once transcribed (spec §3 step 3)."""
    if os.path.exists(audio_path):
        os.remove(audio_path)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m unittest tests.test_audio_download -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add video_notes/audio_download.py tests/test_audio_download.py
git commit -m "$(cat <<'EOF'
feat(video_notes): add audio download/extraction and cleanup

yt-dlp downloads a video's audio and extracts it to mp3 via ffmpeg;
delete_audio removes it once transcription no longer needs it, per the
design spec's "don't keep audio, it's cheap to re-fetch" call.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01RSVwgCfAbdoph7ua8uziz8
EOF
)"
```

---

### Task 4: `transcribe.py` — local CPU transcription

**Files:**
- Create: `video_notes/transcribe.py`
- Test: `tests/test_transcribe.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `TranscriptSegment` (dataclass: `start: float, end: float, text: str`), `transcribe_audio(audio_path: str, model_size: str = ..., device: str = "cpu", compute_type: str = ...) -> list[TranscriptSegment]`, `save_transcript(path: str, segments: list[TranscriptSegment]) -> None`, `load_transcript(path: str) -> list[TranscriptSegment]`. Every later task that touches transcripts uses this exact `TranscriptSegment` shape.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_transcribe.py`:

```python
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from video_notes.transcribe import TranscriptSegment, load_transcript, save_transcript, transcribe_audio


class TestTranscribeAudio(unittest.TestCase):
    @patch("faster_whisper.WhisperModel")
    def test_converts_whisper_segments_to_transcript_segments(self, mock_model_cls):
        fake_segment = MagicMock(start=1.5, end=3.0, text=" hello world ")
        mock_model = MagicMock()
        mock_model.transcribe.return_value = ([fake_segment], MagicMock())
        mock_model_cls.return_value = mock_model

        result = transcribe_audio("fake.mp3", model_size="small", device="cpu", compute_type="int8")

        self.assertEqual(result, [TranscriptSegment(start=1.5, end=3.0, text="hello world")])
        mock_model_cls.assert_called_once_with("small", device="cpu", compute_type="int8")


class TestTranscriptRoundTrip(unittest.TestCase):
    def test_save_then_load_preserves_segments(self):
        segments = [TranscriptSegment(start=0.0, end=1.0, text="a"), TranscriptSegment(start=1.0, end=2.5, text="b")]
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "sub", "AAAA111.json")
            save_transcript(path, segments)
            self.assertEqual(load_transcript(path), segments)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m unittest tests.test_transcribe -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'video_notes.transcribe'`

- [ ] **Step 3: Implement**

Create `video_notes/transcribe.py`:

```python
"""
transcribe.py
Local CPU transcription via faster-whisper -- no cloud call. Spec §3
step 3, §7 for model defaults. `faster_whisper` is imported lazily
inside transcribe_audio(), matching indexer/index_card.py's own
"no heavy import at module load time" convention, so importing this
module never requires faster-whisper's model-loading machinery to
succeed.
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass

VIDEONOTES_WHISPER_MODEL = os.environ.get("VIDEONOTES_WHISPER_MODEL", "small")
VIDEONOTES_WHISPER_COMPUTE_TYPE = os.environ.get("VIDEONOTES_WHISPER_COMPUTE_TYPE", "int8")


@dataclass
class TranscriptSegment:
    start: float
    end: float
    text: str


def transcribe_audio(
    audio_path: str, model_size: str = VIDEONOTES_WHISPER_MODEL,
    device: str = "cpu", compute_type: str = VIDEONOTES_WHISPER_COMPUTE_TYPE,
) -> list[TranscriptSegment]:
    from faster_whisper import WhisperModel
    model = WhisperModel(model_size, device=device, compute_type=compute_type)
    segments, _info = model.transcribe(audio_path, beam_size=5)
    return [TranscriptSegment(start=s.start, end=s.end, text=s.text.strip()) for s in segments]


def save_transcript(path: str, segments: list[TranscriptSegment]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump([asdict(s) for s in segments], f, indent=2, ensure_ascii=False)


def load_transcript(path: str) -> list[TranscriptSegment]:
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return [TranscriptSegment(**item) for item in raw]
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m unittest tests.test_transcribe -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add video_notes/transcribe.py tests/test_transcribe.py
git commit -m "$(cat <<'EOF'
feat(video_notes): add local CPU transcription via faster-whisper

CPU-only defaults (small model, int8 compute), overridable via
VIDEONOTES_WHISPER_MODEL/VIDEONOTES_WHISPER_COMPUTE_TYPE, plus a JSON
transcript cache so a video is never re-transcribed once done.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01RSVwgCfAbdoph7ua8uziz8
EOF
)"
```

---

### Task 5: `pipeline_state.py` — resumable per-course state

**Files:**
- Create: `video_notes/pipeline_state.py`
- Test: `tests/test_pipeline_state.py`

**Interfaces:**
- Consumes: `TranscriptSegment` from Task 4 (`video_notes.transcribe`).
- Produces: `now_iso() -> str`, `load_video_states(video_notes_root, course) -> dict[str, dict]`, `save_video_state(video_notes_root, course, video_id, **fields) -> None`, `load_group_states(video_notes_root, course) -> dict[str, dict]`, `save_group_states(video_notes_root, course, groups: dict[str, dict]) -> None`, `compute_member_content_hash(member_video_ids: list[str], transcripts_by_id: dict[str, list[TranscriptSegment]]) -> str`. Task 11's `pipeline.py` uses all of these.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_pipeline_state.py`:

```python
import tempfile
import unittest

from video_notes.pipeline_state import (
    compute_member_content_hash, load_group_states, load_video_states,
    save_group_states, save_video_state,
)
from video_notes.transcribe import TranscriptSegment


class TestVideoState(unittest.TestCase):
    def test_save_then_load_round_trips(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_video_state(tmp, "math-camp", "AAAA111", stage="transcribed", url="https://x")
            states = load_video_states(tmp, "math-camp")
            self.assertEqual(states["AAAA111"]["stage"], "transcribed")

    def test_repeated_saves_merge_not_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_video_state(tmp, "math-camp", "AAAA111", url="https://x")
            save_video_state(tmp, "math-camp", "AAAA111", stage="transcribed")
            states = load_video_states(tmp, "math-camp")
            self.assertEqual(states["AAAA111"]["url"], "https://x")
            self.assertEqual(states["AAAA111"]["stage"], "transcribed")

    def test_missing_state_file_returns_empty_dict(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(load_video_states(tmp, "math-camp"), {})


class TestGroupState(unittest.TestCase):
    def test_save_then_load_round_trips(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_group_states(tmp, "math-camp", {"g_0001": {"slug": "real-analysis"}})
            self.assertEqual(load_group_states(tmp, "math-camp"), {"g_0001": {"slug": "real-analysis"}})


class TestComputeMemberContentHash(unittest.TestCase):
    def test_member_order_does_not_affect_the_hash(self):
        transcripts = {"A": [TranscriptSegment(0.0, 1.0, "hello")], "B": [TranscriptSegment(0.0, 1.0, "world")]}
        self.assertEqual(
            compute_member_content_hash(["A", "B"], transcripts),
            compute_member_content_hash(["B", "A"], transcripts),
        )

    def test_changed_transcript_text_changes_the_hash(self):
        transcripts_a = {"A": [TranscriptSegment(0.0, 1.0, "hello")]}
        transcripts_b = {"A": [TranscriptSegment(0.0, 1.0, "hello there")]}
        self.assertNotEqual(
            compute_member_content_hash(["A"], transcripts_a),
            compute_member_content_hash(["A"], transcripts_b),
        )
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m unittest tests.test_pipeline_state -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'video_notes.pipeline_state'`

- [ ] **Step 3: Implement**

Create `video_notes/pipeline_state.py`:

```python
"""
pipeline_state.py
Per-course, resumable pipeline state -- which video is at which stage,
and which group was last synthesized against which member set. Spec §5.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone


def _state_dir(video_notes_root: str) -> str:
    return os.path.join(video_notes_root, ".state")


def _video_state_path(video_notes_root: str, course: str) -> str:
    return os.path.join(_state_dir(video_notes_root), f"{course}.json")


def _group_state_path(video_notes_root: str, course: str) -> str:
    return os.path.join(_state_dir(video_notes_root), f"{course}_groups.json")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_video_states(video_notes_root: str, course: str) -> dict[str, dict]:
    path = _video_state_path(video_notes_root, course)
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_video_state(video_notes_root: str, course: str, video_id: str, **fields) -> None:
    """Merges `fields` into this video's existing record (if any) and
    writes the whole course state file back -- one video's update never
    discards another's."""
    states = load_video_states(video_notes_root, course)
    states.setdefault(video_id, {})
    states[video_id].update(fields)
    path = _video_state_path(video_notes_root, course)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(states, f, indent=2, ensure_ascii=False)


def load_group_states(video_notes_root: str, course: str) -> dict[str, dict]:
    path = _group_state_path(video_notes_root, course)
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_group_states(video_notes_root: str, course: str, groups: dict[str, dict]) -> None:
    """Full overwrite, not a merge -- grouping.group_videos() recomputes
    every group from scratch each run; pipeline.py carries forward the
    still-valid previous record for any group whose membership/content
    is unchanged before calling this (spec §5)."""
    path = _group_state_path(video_notes_root, course)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(groups, f, indent=2, ensure_ascii=False)


def compute_member_content_hash(member_video_ids: list[str], transcripts_by_id: dict) -> str:
    """A group's re-synthesis trigger (spec §5): changes whenever its
    membership or any member's transcript content changes, so adding
    one new lecture to an existing group re-synthesizes just that
    group -- and an unrelated group's note/card is never touched."""
    parts = []
    for video_id in sorted(member_video_ids):
        segments = transcripts_by_id.get(video_id, [])
        text = "".join(segment.text for segment in segments)
        parts.append(f"{video_id}:{hashlib.sha256(text.encode('utf-8')).hexdigest()}")
    joined = "|".join(parts)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:16]
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m unittest tests.test_pipeline_state -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add video_notes/pipeline_state.py tests/test_pipeline_state.py
git commit -m "$(cat <<'EOF'
feat(video_notes): add resumable per-course pipeline state

Per-video stage tracking and per-group member-content-hash tracking so
a crashed or extended batch only (re-)does the work that's missing or
actually changed, never a full re-run.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01RSVwgCfAbdoph7ua8uziz8
EOF
)"
```

---

### Task 6: `grouping.py` — playlist default + title-series subdivision + singleton

**Files:**
- Create: `video_notes/grouping.py`
- Test: `tests/test_grouping.py`

**Interfaces:**
- Consumes: `VideoMetadata` from Task 2 (`video_notes.youtube_metadata`).
- Produces: `Group` (dataclass: `group_id: str, member_video_ids: list[str], slug: str, tier: str`), `slugify(text: str) -> str`, `group_videos(videos: list[VideoMetadata], embeddings: dict[str, list[float] | None] | None = None, similarity_threshold: float = 0.75) -> list[Group]`. Task 7 extends `group_videos`'s tier-3 branch (currently a no-op singleton fallback); Task 8/9/11 consume `Group`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_grouping.py`:

```python
import unittest

from video_notes.grouping import group_videos, slugify
from video_notes.youtube_metadata import VideoMetadata


def _video(video_id, title, playlist_id=None, playlist_title=None, playlist_index=None,
           channel_id="UC1", upload_date="20260101"):
    return VideoMetadata(
        video_id=video_id, url=f"https://youtube.com/watch?v={video_id}", title=title,
        channel_id=channel_id, playlist_id=playlist_id, playlist_title=playlist_title,
        playlist_index=playlist_index, upload_date=upload_date, duration=100.0,
    )


class TestSlugify(unittest.TestCase):
    def test_lowercases_and_hyphenates(self):
        self.assertEqual(slugify("Real Analysis Lectures!"), "real-analysis-lectures")

    def test_empty_input_falls_back_to_untitled(self):
        self.assertEqual(slugify("   "), "untitled")


class TestGroupVideosPlaylistDefault(unittest.TestCase):
    def test_playlist_with_no_numbered_titles_becomes_one_group(self):
        videos = [
            _video("A", "Introduction to Real Analysis", playlist_id="PL1", playlist_title="Real Analysis", playlist_index=1),
            _video("B", "Continuity and Limits", playlist_id="PL1", playlist_title="Real Analysis", playlist_index=2),
        ]
        groups = group_videos(videos)
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].tier, "playlist")
        self.assertEqual(groups[0].member_video_ids, ["A", "B"])


class TestGroupVideosTitleSeriesSubdivision(unittest.TestCase):
    def test_playlist_with_two_distinct_lecture_series_subdivides(self):
        videos = [
            _video("A", "Unit 1: Sets, Lecture 1", playlist_id="PL1", playlist_index=1),
            _video("B", "Unit 1: Sets, Lecture 2", playlist_id="PL1", playlist_index=2),
            _video("C", "Unit 2: Metric Spaces, Lecture 1", playlist_id="PL1", playlist_index=3),
            _video("D", "Unit 2: Metric Spaces, Lecture 2", playlist_id="PL1", playlist_index=4),
        ]
        groups = group_videos(videos)
        self.assertEqual(len(groups), 2)
        member_sets = sorted(tuple(g.member_video_ids) for g in groups)
        self.assertEqual(member_sets, [("A", "B"), ("C", "D")])
        self.assertTrue(all(g.tier == "title_series" for g in groups))

    def test_a_single_multi_member_stem_is_not_real_subdivision(self):
        # Only one distinct series detected (plus one non-matching
        # video) -- not "2+ distinct series", so the whole playlist
        # stays one group instead of splitting off the numbered videos.
        videos = [
            _video("A", "Real Analysis, Lecture 1", playlist_id="PL1", playlist_index=1),
            _video("B", "Real Analysis, Lecture 2", playlist_id="PL1", playlist_index=2),
            _video("C", "Course Introduction", playlist_id="PL1", playlist_index=3),
        ]
        groups = group_videos(videos)
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].tier, "playlist")
        self.assertEqual(set(groups[0].member_video_ids), {"A", "B", "C"})


class TestGroupVideosNoPlaylistScope(unittest.TestCase):
    def test_non_playlisted_videos_with_no_series_pattern_become_singletons(self):
        videos = [
            _video("A", "A Talk About Eigenvalues", channel_id="UC1"),
            _video("B", "A Different Talk", channel_id="UC1"),
        ]
        groups = group_videos(videos)
        self.assertEqual({g.tier for g in groups}, {"singleton"})
        self.assertEqual(len(groups), 2)

    def test_non_playlisted_videos_with_series_pattern_still_group(self):
        videos = [
            _video("A", "Econometrics Lecture 1", channel_id="UC1"),
            _video("B", "Econometrics Lecture 2", channel_id="UC1"),
        ]
        groups = group_videos(videos)
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].tier, "title_series")


class TestGroupVideosScopeIsolation(unittest.TestCase):
    def test_same_title_pattern_in_different_playlists_never_merges(self):
        videos = [
            _video("A", "Lecture 1", playlist_id="PL1", playlist_index=1),
            _video("B", "Lecture 2", playlist_id="PL1", playlist_index=2),
            _video("C", "Lecture 1", playlist_id="PL2", playlist_index=1),
            _video("D", "Lecture 2", playlist_id="PL2", playlist_index=2),
        ]
        groups = group_videos(videos)
        self.assertEqual(len(groups), 2)
        member_sets = sorted(tuple(g.member_video_ids) for g in groups)
        self.assertEqual(member_sets, [("A", "B"), ("C", "D")])
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m unittest tests.test_grouping -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'video_notes.grouping'`

- [ ] **Step 3: Implement**

Create `video_notes/grouping.py`:

```python
"""
grouping.py
Fully automatic grouping of a course's videos into logical lecture
series -- no manual per-batch config (spec §4). Tried in order, per
playlist/channel scope: playlist-as-one-group (the default, unless
real title-series subdivision is detected), title-series subdivision,
then content-clustering fallback (added by Task 7), then singleton.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from video_notes.youtube_metadata import VideoMetadata

_SERIES_PATTERN = re.compile(r"(?i)\b(?:lecture|lec|part|week)\.?\s*#?\s*(\d+)\b")
_SLUG_STRIP_RE = re.compile(r"[^a-z0-9]+")


@dataclass
class Group:
    group_id: str
    member_video_ids: list[str]
    slug: str
    tier: str  # "playlist" | "title_series" | "content_cluster" | "singleton"


def slugify(text: str) -> str:
    slug = _SLUG_STRIP_RE.sub("-", text.strip().lower()).strip("-")
    return slug or "untitled"


def _title_stem(title: str) -> str | None:
    """Strips a `Lecture N` / `Part N` / `Week N` marker and returns the
    remaining text as the series stem, or None if no such marker is
    present (spec §4 tier 2)."""
    match = _SERIES_PATTERN.search(title)
    if not match:
        return None
    stem = title[:match.start()] + title[match.end():]
    stem = re.sub(r"[\s:,\-]+", " ", stem).strip().lower()
    return stem or None


def _scope_key(video: VideoMetadata) -> tuple:
    """Playlist membership scopes videos together; a video with no
    playlist is scoped by channel instead, so tier-3 clustering (Task 7)
    never compares videos across unrelated channels (spec §4)."""
    if video.playlist_id:
        return ("playlist", video.playlist_id)
    return ("channel", video.channel_id)


def _bucket_by_scope(videos: list[VideoMetadata]) -> dict[tuple, list[VideoMetadata]]:
    scopes: dict[tuple, list[VideoMetadata]] = {}
    for video in videos:
        scopes.setdefault(_scope_key(video), []).append(video)
    return scopes


def _subdivide_by_title_series(
    videos: list[VideoMetadata],
) -> tuple[dict[str, list[VideoMetadata]], list[VideoMetadata]]:
    """Returns (real_stems, unmatched): real_stems holds only stems with
    2+ members (a genuine subdivision signal); everything else --
    no-pattern titles and one-off stems with a single member -- is
    returned as unmatched, for tier 3 / singleton to handle."""
    buckets: dict[str, list[VideoMetadata]] = {}
    unmatched: list[VideoMetadata] = []
    for video in videos:
        stem = _title_stem(video.title)
        if stem is None:
            unmatched.append(video)
        else:
            buckets.setdefault(stem, []).append(video)

    real_stems = {stem: members for stem, members in buckets.items() if len(members) >= 2}
    for stem, members in buckets.items():
        if len(members) < 2:
            unmatched.extend(members)
    return real_stems, unmatched


def _order_members(videos: list[VideoMetadata]) -> list[VideoMetadata]:
    return sorted(
        videos,
        key=lambda v: (v.playlist_index if v.playlist_index is not None else 10**9, v.upload_date or ""),
    )


def _make_group(group_id: str, members: list[VideoMetadata], slug_source: str, tier: str) -> Group:
    ordered = _order_members(members)
    return Group(group_id=group_id, member_video_ids=[v.video_id for v in ordered], slug=slugify(slug_source), tier=tier)


def group_videos(
    videos: list[VideoMetadata], embeddings: dict[str, list[float] | None] | None = None,
    similarity_threshold: float = 0.75,
) -> list[Group]:
    groups: list[Group] = []
    counter = 0

    for scope_key, scope_videos in _bucket_by_scope(videos).items():
        is_playlist_scope = scope_key[0] == "playlist"
        real_stems, unmatched = _subdivide_by_title_series(scope_videos)

        if is_playlist_scope and len(real_stems) < 2:
            # No genuine subdivision signal -- trust the playlist itself
            # as one group (the common case: a coherent lecture series
            # whose titles aren't necessarily numbered). This is the
            # whole-playlist default for playlists that DON'T have
            # subgroups, while the branch below subdivides the ones
            # that do.
            counter += 1
            slug_source = scope_videos[0].playlist_title or scope_videos[0].title
            groups.append(_make_group(f"g_{counter:04d}", scope_videos, slug_source, "playlist"))
            continue

        for stem, members in real_stems.items():
            counter += 1
            groups.append(_make_group(f"g_{counter:04d}", members, stem, "title_series"))

        for video in unmatched:
            # Tier 3 (content clustering) is added by Task 7; until
            # then every leftover becomes its own singleton group.
            counter += 1
            groups.append(_make_group(f"g_{counter:04d}", [video], video.title, "singleton"))

    return groups
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m unittest tests.test_grouping -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add video_notes/grouping.py tests/test_grouping.py
git commit -m "$(cat <<'EOF'
feat(video_notes): add automatic grouping (playlist default + title-series)

Playlist membership scopes videos together and is trusted as one group
by default; a title-series pattern (Lecture/Part/Week N) subdivides a
scope only when 2+ distinct series are actually detected. Every scope
is isolated -- the same title pattern in two different playlists never
merges. Content-clustering fallback lands in the next task.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01RSVwgCfAbdoph7ua8uziz8
EOF
)"
```

---

### Task 7: Content-clustering fallback (tier 3) + local Ollama embeddings

**Files:**
- Modify: `common/ollama_utils.py`
- Modify: `video_notes/grouping.py`
- Test: `tests/test_ollama_utils.py` (extend)
- Test: `tests/test_grouping.py` (extend)

**Interfaces:**
- Consumes: `TranscriptSegment` from Task 4.
- Produces: `common.ollama_utils.call_ollama_embeddings(text: str, model: str, request_timeout: int, url: str = OLLAMA_EMBEDDINGS_URL) -> list[float] | None | OllamaTimeout`; `video_notes.grouping.embed_transcripts(transcripts_by_id: dict[str, list[TranscriptSegment]], model: str = VIDEONOTES_EMBED_MODEL) -> dict[str, list[float] | None]`. `group_videos`'s `embeddings` param (already accepted since Task 6) now actually drives clustering. Task 11's `pipeline.py` calls `embed_transcripts()` then passes its result into `group_videos()`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_ollama_utils.py` (new import `call_ollama_embeddings` alongside the existing `call_ollama, OLLAMA_TIMEOUT` import, new test class at the end):

```python
class TestCallOllamaEmbeddings(unittest.TestCase):
    @patch("common.ollama_utils.urllib.request.urlopen")
    def test_returns_embedding_vector_on_success(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"embedding": [0.1, 0.2, 0.3]}).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_response
        result = call_ollama_embeddings("some text", "nomic-embed-text", 30)
        self.assertEqual(result, [0.1, 0.2, 0.3])

    @patch("common.ollama_utils.urllib.request.urlopen", side_effect=OSError("connection refused"))
    def test_returns_none_on_connection_failure(self, mock_urlopen):
        self.assertIsNone(call_ollama_embeddings("some text", "nomic-embed-text", 30))

    @patch("common.ollama_utils.urllib.request.urlopen", side_effect=TimeoutError("timed out"))
    def test_returns_timeout_sentinel_on_timeout(self, mock_urlopen):
        self.assertIs(call_ollama_embeddings("some text", "nomic-embed-text", 30), OLLAMA_TIMEOUT)
```

Add to `tests/test_grouping.py` (new imports `from unittest.mock import patch`, `from video_notes.grouping import embed_transcripts` alongside the existing `group_videos, slugify` import, `from video_notes.transcribe import TranscriptSegment`, and these new test classes at the end):

```python
class TestClusterByContent(unittest.TestCase):
    def test_similar_embeddings_cluster_together(self):
        videos = [_video("A", "Talk 1", channel_id="UC1"), _video("B", "Talk 2", channel_id="UC1")]
        embeddings = {"A": [1.0, 0.0], "B": [0.99, 0.01]}
        groups = group_videos(videos, embeddings=embeddings, similarity_threshold=0.9)
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].tier, "content_cluster")
        self.assertEqual(set(groups[0].member_video_ids), {"A", "B"})

    def test_dissimilar_embeddings_stay_separate(self):
        videos = [_video("A", "Talk 1", channel_id="UC1"), _video("B", "Talk 2", channel_id="UC1")]
        embeddings = {"A": [1.0, 0.0], "B": [0.0, 1.0]}
        groups = group_videos(videos, embeddings=embeddings, similarity_threshold=0.9)
        self.assertEqual({g.tier for g in groups}, {"singleton"})
        self.assertEqual(len(groups), 2)

    def test_a_video_with_no_embedding_falls_back_to_singleton(self):
        videos = [_video("A", "Talk 1", channel_id="UC1"), _video("B", "Talk 2", channel_id="UC1")]
        embeddings = {"A": [1.0, 0.0], "B": None}
        groups = group_videos(videos, embeddings=embeddings, similarity_threshold=0.9)
        self.assertEqual(len(groups), 2)
        self.assertEqual({g.tier for g in groups}, {"singleton"})


class TestEmbedTranscripts(unittest.TestCase):
    @patch("video_notes.grouping.call_ollama_embeddings")
    def test_maps_each_video_to_its_embedding(self, mock_call):
        mock_call.return_value = [0.1, 0.2]
        transcripts = {"A": [TranscriptSegment(0.0, 1.0, "hello")]}
        result = embed_transcripts(transcripts, model="nomic-embed-text")
        self.assertEqual(result, {"A": [0.1, 0.2]})

    @patch("video_notes.grouping.call_ollama_embeddings")
    def test_failed_call_maps_to_none(self, mock_call):
        mock_call.return_value = None
        transcripts = {"A": [TranscriptSegment(0.0, 1.0, "hello")]}
        result = embed_transcripts(transcripts, model="nomic-embed-text")
        self.assertIsNone(result["A"])
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m unittest tests.test_ollama_utils tests.test_grouping -v`
Expected: FAIL — `ImportError: cannot import name 'call_ollama_embeddings'` and `ImportError: cannot import name 'embed_transcripts'`

- [ ] **Step 3: Add `call_ollama_embeddings` to `common/ollama_utils.py`**

Append to `common/ollama_utils.py` (after the existing `call_ollama` function):

```python
OLLAMA_EMBEDDINGS_URL = "http://localhost:11434/api/embeddings"


def call_ollama_embeddings(
    text: str, model: str, request_timeout: int, url: str = OLLAMA_EMBEDDINGS_URL,
) -> list[float] | None | OllamaTimeout:
    """Same error-handling contract as call_ollama (spec:
    docs/superpowers/specs/2026-09-06-video-lecture-notes-design.md
    §7) -- POSTs to Ollama's embeddings endpoint instead of its
    generate endpoint."""
    payload = json.dumps({"model": model, "prompt": text}).encode("utf-8")
    request = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=request_timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
        return body.get("embedding")
    except Exception as err:
        timed_out = isinstance(err, TimeoutError) or (
            isinstance(err, urllib.error.URLError) and isinstance(err.reason, TimeoutError)
        )
        if timed_out:
            print(f"WARNING: Ollama embeddings call to model '{model}' timed out after {request_timeout}s -- "
                  f"the model may just be slow on this request")
            return OLLAMA_TIMEOUT
        print(f"WARNING: Ollama embeddings call to model '{model}' failed ({err}) -- is `ollama serve` running and "
              f"has `ollama pull {model}` been run?")
        return None
```

- [ ] **Step 4: Add clustering + `embed_transcripts` to `video_notes/grouping.py`**

Add these imports to the top of `video_notes/grouping.py`:

```python
import os

import numpy as np
from sklearn.cluster import AgglomerativeClustering

from common.ollama_utils import call_ollama_embeddings
```

Add below `_order_members`/`_make_group` (before `group_videos`):

```python
VIDEONOTES_EMBED_MODEL = os.environ.get("VIDEONOTES_EMBED_MODEL", "nomic-embed-text")
VIDEONOTES_EMBED_TIMEOUT_SECONDS = int(os.environ.get("VIDEONOTES_EMBED_TIMEOUT", "60"))


def embed_transcripts(transcripts_by_id: dict, model: str = VIDEONOTES_EMBED_MODEL) -> dict[str, list[float] | None]:
    """One local Ollama embedding call per video's transcript text. A
    video whose call fails/times out maps to None -- treated as
    un-clusterable, falling back to its own singleton group rather than
    being silently excluded or force-merged (spec §8)."""
    embeddings: dict[str, list[float] | None] = {}
    for video_id, segments in transcripts_by_id.items():
        text = " ".join(segment.text for segment in segments)[:8000]
        result = call_ollama_embeddings(text, model, VIDEONOTES_EMBED_TIMEOUT_SECONDS)
        embeddings[video_id] = result if isinstance(result, list) else None
    return embeddings


def _cluster_by_content(
    videos: list[VideoMetadata], embeddings: dict[str, list[float] | None], similarity_threshold: float,
) -> list[list[VideoMetadata]]:
    embeddable = [v for v in videos if embeddings.get(v.video_id) is not None]
    non_embeddable = [v for v in videos if embeddings.get(v.video_id) is None]
    clusters: list[list[VideoMetadata]] = [[v] for v in non_embeddable]

    if len(embeddable) == 1:
        clusters.append(embeddable)
    elif len(embeddable) > 1:
        vectors = np.array([embeddings[v.video_id] for v in embeddable])
        labels = AgglomerativeClustering(
            n_clusters=None, distance_threshold=1 - similarity_threshold, metric="cosine", linkage="average",
        ).fit_predict(vectors)
        buckets: dict[int, list[VideoMetadata]] = {}
        for video, label in zip(embeddable, labels):
            buckets.setdefault(label, []).append(video)
        clusters.extend(buckets.values())

    return clusters
```

Replace `group_videos`'s singleton-only leftover handling:

```python
        for video in unmatched:
            # Tier 3 (content clustering) is added by Task 7; until
            # then every leftover becomes its own singleton group.
            counter += 1
            groups.append(_make_group(f"g_{counter:04d}", [video], video.title, "singleton"))
```

with:

```python
        if unmatched:
            for cluster_members in _cluster_by_content(unmatched, embeddings or {}, similarity_threshold):
                counter += 1
                tier = "content_cluster" if len(cluster_members) > 1 else "singleton"
                slug_source = cluster_members[0].playlist_title or cluster_members[0].title
                groups.append(_make_group(f"g_{counter:04d}", cluster_members, slug_source, tier))
```

(When `embeddings` is `None` — every Task 6 test's default call — `embeddings or {}` becomes `{}`, so every leftover has no embedding and `_cluster_by_content` puts each in its own singleton cluster: identical behavior to before, so every Task 6 test still passes unmodified.)

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python -m unittest tests.test_ollama_utils tests.test_grouping -v`
Expected: all PASS (including every Task 6 test, unmodified)

- [ ] **Step 6: Commit**

```bash
git add common/ollama_utils.py video_notes/grouping.py tests/test_ollama_utils.py tests/test_grouping.py
git commit -m "$(cat <<'EOF'
feat(video_notes): add content-clustering grouping fallback

A video with no title-series match gets clustered against other
leftovers in the same playlist/channel scope by transcript-embedding
cosine similarity (local Ollama embeddings, nomic-embed-text default --
no paid API call). A video whose embedding call fails falls back to
its own singleton group rather than being silently merged or dropped.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01RSVwgCfAbdoph7ua8uziz8
EOF
)"
```

---

### Task 8: `synthesize.py` — timestamp-linked prompt + local Ollama synthesis

**Files:**
- Create: `video_notes/synthesize.py`
- Test: `tests/test_synthesize.py`

**Interfaces:**
- Consumes: `VideoMetadata` (Task 2), `TranscriptSegment` (Task 4), `common.ollama_utils.call_ollama`/`OLLAMA_TIMEOUT` (existing).
- Produces: `build_synthesis_prompt(group_title: str, member_video_ids: list[str], videos_by_id: dict[str, VideoMetadata], transcripts_by_id: dict[str, list[TranscriptSegment]]) -> str`, `synthesize_group_note(prompt: str, model: str = VIDEONOTES_OLLAMA_MODEL, request_timeout: int = VIDEONOTES_OLLAMA_TIMEOUT_SECONDS) -> str | None`. Task 11's `pipeline.py` calls both.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_synthesize.py`:

```python
import unittest
from unittest.mock import patch

from common.ollama_utils import OLLAMA_TIMEOUT
from video_notes.synthesize import build_synthesis_prompt, synthesize_group_note
from video_notes.transcribe import TranscriptSegment
from video_notes.youtube_metadata import VideoMetadata


def _video(video_id, title, url):
    return VideoMetadata(
        video_id=video_id, url=url, title=title, channel_id="UC1", playlist_id=None,
        playlist_title=None, playlist_index=None, upload_date="20260101", duration=100.0,
    )


class TestBuildSynthesisPrompt(unittest.TestCase):
    def test_single_video_uses_its_own_title_as_label(self):
        videos_by_id = {"A": _video("A", "Intro to Eigenvalues", "https://youtube.com/watch?v=A")}
        transcripts_by_id = {"A": [TranscriptSegment(75.0, 80.0, "an eigenvalue is")]}
        prompt = build_synthesis_prompt("Intro to Eigenvalues", ["A"], videos_by_id, transcripts_by_id)
        self.assertIn("[Intro to Eigenvalues @ 01:15](https://youtube.com/watch?v=A?t=75s):", prompt)

    def test_multi_video_group_labels_lectures_in_order(self):
        videos_by_id = {
            "A": _video("A", "Real Analysis 1", "https://youtube.com/watch?v=A"),
            "B": _video("B", "Real Analysis 2", "https://youtube.com/watch?v=B"),
        }
        transcripts_by_id = {
            "A": [TranscriptSegment(0.0, 1.0, "first")],
            "B": [TranscriptSegment(65.0, 70.0, "second")],
        }
        prompt = build_synthesis_prompt("Real Analysis", ["A", "B"], videos_by_id, transcripts_by_id)
        self.assertIn("[Lecture 1 @ 00:00](https://youtube.com/watch?v=A?t=0s): first", prompt)
        self.assertIn("[Lecture 2 @ 01:05](https://youtube.com/watch?v=B?t=65s): second", prompt)


class TestSynthesizeGroupNote(unittest.TestCase):
    @patch("video_notes.synthesize.call_ollama")
    def test_returns_model_output_on_success(self, mock_call):
        mock_call.return_value = "# Notes\n..."
        self.assertEqual(synthesize_group_note("prompt", model="qwen2.5:7b-instruct"), "# Notes\n...")

    @patch("video_notes.synthesize.call_ollama", return_value=None)
    def test_returns_none_when_ollama_unreachable(self, mock_call):
        self.assertIsNone(synthesize_group_note("prompt"))

    @patch("video_notes.synthesize.call_ollama", return_value=OLLAMA_TIMEOUT)
    def test_returns_none_on_timeout(self, mock_call):
        self.assertIsNone(synthesize_group_note("prompt"))
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m unittest tests.test_synthesize -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'video_notes.synthesize'`

- [ ] **Step 3: Implement**

Create `video_notes/synthesize.py`:

```python
"""
synthesize.py
Builds the per-group synthesis prompt (multi-video, timestamp-linked)
and calls a local Ollama model to produce the final Markdown note. No
paid API call. Spec §3 step 5, §6, §7.
"""
from __future__ import annotations

import os

from common.ollama_utils import OLLAMA_TIMEOUT, call_ollama

VIDEONOTES_OLLAMA_MODEL = os.environ.get("VIDEONOTES_OLLAMA_MODEL", "qwen2.5:7b-instruct")
VIDEONOTES_OLLAMA_TIMEOUT_SECONDS = int(os.environ.get("VIDEONOTES_OLLAMA_TIMEOUT", "1800"))

_PROMPT_TEMPLATE = """You are an expert pedagogue. Review the following raw lecture transcript(s) \
for "{group_title}", embedded with chronological timeline links back to their source video(s).

Synthesize the core theoretical framework, main results, and structural takeaways into a polished, \
scannable academic report covering all the lectures together as one cohesive whole.

STRICT FORMATTING RULES:
1. Use clear Markdown headers and bullet points.
2. Wrap all mathematical variables, expressions, and formulas in LaTeX delimiters \
(inline `$x^2$`, block `$$ ... $$`).
3. Cite the provided timestamp links inline at the end of the sentence introducing each key concept, \
theorem, or step transition, exactly as given (they already identify which lecture they come from), \
so the reader can click through to that exact moment.

--- TRANSCRIPT START ---
{transcript_block}
--- TRANSCRIPT END ---"""


def _format_timestamp(seconds: int) -> str:
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}" if hours else f"{minutes:02d}:{secs:02d}"


def _timestamp_url(video_url: str, seconds: int) -> str:
    separator = "&" if "?" in video_url else "?"
    return f"{video_url}{separator}t={seconds}s"


def build_synthesis_prompt(
    group_title: str, member_video_ids: list, videos_by_id: dict, transcripts_by_id: dict,
) -> str:
    """Every transcript line is tagged with its own video's label and
    timestamp link, so a group spanning multiple videos can still cite
    the correct source video, not just a bare second count (spec §6)."""
    multi_video = len(member_video_ids) > 1
    lines = []
    for index, video_id in enumerate(member_video_ids, start=1):
        video = videos_by_id[video_id]
        label = f"Lecture {index}" if multi_video else video.title
        for segment in transcripts_by_id[video_id]:
            seconds = int(segment.start)
            timestamp = _format_timestamp(seconds)
            url = _timestamp_url(video.url, seconds)
            lines.append(f"[{label} @ {timestamp}]({url}): {segment.text.strip()}")
    return _PROMPT_TEMPLATE.format(group_title=group_title, transcript_block="\n".join(lines))


def synthesize_group_note(
    prompt: str, model: str = VIDEONOTES_OLLAMA_MODEL, request_timeout: int = VIDEONOTES_OLLAMA_TIMEOUT_SECONDS,
) -> str | None:
    result = call_ollama(prompt, model, request_timeout)
    if result is None:
        print(f"WARNING: could not reach Ollama to synthesize lecture notes (model={model}).")
        return None
    if result is OLLAMA_TIMEOUT:
        print(f"WARNING: Ollama synthesis call timed out after {request_timeout}s (model={model}).")
        return None
    return result
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m unittest tests.test_synthesize -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add video_notes/synthesize.py tests/test_synthesize.py
git commit -m "$(cat <<'EOF'
feat(video_notes): add timestamp-linked synthesis prompt + local Ollama call

Each transcript line carries its own source video's label and a
per-video YouTube timestamp link, so a group spanning multiple videos
can still cite the correct originating video. Synthesis itself is a
local Ollama call, no paid API.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01RSVwgCfAbdoph7ua8uziz8
EOF
)"
```

---

### Task 9: `note_indexing.py` + shared `compute_id_from_parts` helper

**Files:**
- Modify: `indexer/index_card.py`
- Create: `video_notes/note_indexing.py`
- Test: `tests/test_index_card.py` (extend)
- Test: `tests/test_note_indexing.py`

**Interfaces:**
- Consumes: `indexer.index_card.reconcile_and_write`/`compute_content_hash` (existing).
- Produces: `indexer.index_card.compute_id_from_parts(parts: list[str]) -> str` (new, generic — also consumed by Task 10); `video_notes.note_indexing.write_group_note(academic_hub_root: str, course: str, slug: str, markdown: str, sidecar: dict) -> tuple[str, str]` (returns `(rel_md_path, rel_meta_path)`); `video_notes.note_indexing.index_group_note(academic_hub_root: str, course: str, member_video_ids: list[str], rel_md_path: str, rel_meta_path: str, client) -> dict`. Task 11's `pipeline.py` calls both `write_group_note` and `index_group_note`.

- [ ] **Step 1: Write the failing test for `compute_id_from_parts`**

Add to `tests/test_index_card.py` (add `compute_id_from_parts` to the existing `from indexer.index_card import (...)` block, new test class at the end):

```python
class TestComputeIdFromParts(unittest.TestCase):
    def test_order_independent(self):
        self.assertEqual(compute_id_from_parts(["b", "a"]), compute_id_from_parts(["a", "b"]))

    def test_different_parts_produce_different_ids(self):
        self.assertNotEqual(compute_id_from_parts(["a"]), compute_id_from_parts(["b"]))

    def test_returns_16_char_hex_string(self):
        result = compute_id_from_parts(["a", "b", "c"])
        self.assertEqual(len(result), 16)
        int(result, 16)  # raises ValueError if not valid hex
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m unittest tests.test_index_card.TestComputeIdFromParts -v`
Expected: FAIL with `ImportError: cannot import name 'compute_id_from_parts'`

- [ ] **Step 3: Add `compute_id_from_parts` to `indexer/index_card.py`**

Add directly below `compute_content_hash` in `indexer/index_card.py`:

```python
def compute_id_from_parts(parts: list[str]) -> str:
    """Truncated SHA-256 of sorted, joined string parts -- the same
    content-addressed-identity idea as compute_file_id, for content
    whose stable identity isn't a single file's bytes (e.g. a
    lecture-notes group's identity is its member video IDs, not its
    derived, re-synthesizable Markdown -- see
    video_notes/note_indexing.py)."""
    joined = ",".join(sorted(parts))
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:16]
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python -m unittest tests.test_index_card.TestComputeIdFromParts -v`
Expected: PASS

- [ ] **Step 5: Write the failing tests for `note_indexing.py`**

Create `tests/test_note_indexing.py`:

```python
import json
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from video_notes.note_indexing import index_group_note, write_group_note


class TestWriteGroupNote(unittest.TestCase):
    def test_writes_markdown_and_sidecar_under_lecture_notes(self):
        with tempfile.TemporaryDirectory() as tmp:
            rel_md, rel_meta = write_group_note(tmp, "math-camp", "real-analysis", "# Notes", {"member_video_ids": ["A"]})
            self.assertEqual(rel_md, "academic_notes/math-camp/lecture-notes/real-analysis.md")
            self.assertEqual(rel_meta, "academic_notes/math-camp/lecture-notes/real-analysis.meta.json")
            with open(os.path.join(tmp, rel_md), "r", encoding="utf-8") as f:
                self.assertEqual(f.read(), "# Notes")
            with open(os.path.join(tmp, rel_meta), "r", encoding="utf-8") as f:
                self.assertEqual(json.load(f), {"member_video_ids": ["A"]})


class TestIndexGroupNote(unittest.TestCase):
    @patch("video_notes.note_indexing.reconcile_and_write")
    def test_calls_reconcile_and_write_with_group_identity_file_id(self, mock_reconcile):
        mock_reconcile.return_value = {"file_id": "x"}
        with tempfile.TemporaryDirectory() as tmp:
            rel_md, rel_meta = write_group_note(tmp, "math-camp", "real-analysis", "# Notes", {"member_video_ids": ["A", "B"]})
            result = index_group_note(tmp, "math-camp", ["A", "B"], rel_md, rel_meta, MagicMock())
            self.assertEqual(result, {"file_id": "x"})
            _, kwargs = mock_reconcile.call_args
            self.assertEqual(kwargs["folder_category"], "lecture-notes")
            self.assertEqual(kwargs["content_sample"], "# Notes")
            self.assertEqual(kwargs["path"], rel_md)
            self.assertEqual(kwargs["source_pdf_path"], rel_meta)
```

- [ ] **Step 6: Run the tests to verify they fail**

Run: `python -m unittest tests.test_note_indexing -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'video_notes.note_indexing'`

- [ ] **Step 7: Implement**

Create `video_notes/note_indexing.py`:

```python
"""
note_indexing.py
Writes a synthesized group note (+ sidecar) to
academic_notes/<course>/lecture-notes/ and registers it with the
existing Source Indexer, the same way notes/transcribe_notes.py calls
reconcile_and_write() inline right after writing its own output. Spec
§6.
"""
from __future__ import annotations

import json
import os

from indexer.index_card import compute_content_hash, compute_id_from_parts, reconcile_and_write


def write_group_note(academic_hub_root: str, course: str, slug: str, markdown: str, sidecar: dict) -> tuple[str, str]:
    """Writes the note + its `.meta.json` sidecar, returns their paths
    relative to academic_hub_root (what reconcile_and_write expects)."""
    lecture_notes_dir = os.path.join(academic_hub_root, "academic_notes", course, "lecture-notes")
    os.makedirs(lecture_notes_dir, exist_ok=True)

    md_path = os.path.join(lecture_notes_dir, f"{slug}.md")
    meta_path = os.path.join(lecture_notes_dir, f"{slug}.meta.json")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(markdown)
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(sidecar, f, indent=2, ensure_ascii=False)

    rel_md_path = os.path.relpath(md_path, academic_hub_root).replace(os.sep, "/")
    rel_meta_path = os.path.relpath(meta_path, academic_hub_root).replace(os.sep, "/")
    return rel_md_path, rel_meta_path


def index_group_note(
    academic_hub_root: str, course: str, member_video_ids: list, rel_md_path: str,
    rel_meta_path: str, client,
) -> dict:
    """Registers the note with the shared Source Indexer. file_id is
    derived from the group's member video IDs (its stable identity),
    not the Markdown content (the mutable, re-synthesizable artifact) --
    the same "hash the immutable source" idea compute_file_id already
    applies to a textbook's PDF bytes. content_hash is read back from
    the just-written file (not hashed from the in-memory `markdown`
    string) to avoid a mismatch with what a later rebuild() pass would
    independently recompute from disk (e.g. newline translation on a
    text-mode write)."""
    md_path = os.path.join(academic_hub_root, rel_md_path)
    with open(md_path, "r", encoding="utf-8") as f:
        content_sample = f.read()
    file_id = compute_id_from_parts(member_video_ids)
    content_hash = compute_content_hash(md_path)
    return reconcile_and_write(
        academic_hub_root, file_id=file_id, path=rel_md_path, source_pdf_path=rel_meta_path,
        course=course, folder_category="lecture-notes", content_sample=content_sample,
        page_count=None, client=client, content_hash=content_hash,
    )
```

- [ ] **Step 8: Run the tests to verify they pass**

Run: `python -m unittest tests.test_note_indexing tests.test_index_card -v`
Expected: all PASS

- [ ] **Step 9: Commit**

```bash
git add indexer/index_card.py video_notes/note_indexing.py tests/test_index_card.py tests/test_note_indexing.py
git commit -m "$(cat <<'EOF'
feat(video_notes,indexer): write+index synthesized lecture notes

Adds compute_id_from_parts() to index_card.py -- the same
content-addressed-identity idea as compute_file_id, for a lecture-notes
group whose stable identity is its member video IDs, not its derived
Markdown. note_indexing.py writes the note + sidecar and registers it
with reconcile_and_write(), same as notes/transcribe_notes.py's own
inline indexing call.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01RSVwgCfAbdoph7ua8uziz8
EOF
)"
```

---

### Task 10: `indexer/index_search.py` — discover lecture notes so `rebuild()`/prune never orphans them

**Files:**
- Modify: `indexer/index_search.py`
- Test: `tests/test_index_search.py` (extend)

**Interfaces:**
- Consumes: `indexer.index_card.compute_id_from_parts` (Task 9).
- Produces: `_video_lecture_note_paths(academic_hub_root: str, course_filter: str | None)` (generator yielding `(course, md_path, meta_path)`); `rebuild()`'s existing public signature is unchanged, but it now also reconciles cards for anything `_video_lecture_note_paths` yields.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_index_search.py` (new helper function after the existing `_make_textbook`, new test class at the end):

```python
def _make_video_lecture_note(academic_hub_root, course, slug, member_video_ids,
                              markdown="# Real Analysis\n\nSome content."):
    lecture_notes_dir = os.path.join(academic_hub_root, "academic_notes", course, "lecture-notes")
    os.makedirs(lecture_notes_dir, exist_ok=True)
    md_path = os.path.join(lecture_notes_dir, f"{slug}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(markdown)
    with open(os.path.join(lecture_notes_dir, f"{slug}.meta.json"), "w", encoding="utf-8") as f:
        json.dump({"member_video_ids": member_video_ids}, f)
    return md_path


class TestRebuildVideoLectureNotes(unittest.TestCase):
    def test_generates_a_card_for_a_lecture_note_with_a_sidecar(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_video_lecture_note(tmp, "math-camp", "real-analysis", ["A", "B"])
            stats = rebuild(tmp, client=_fake_client())
            self.assertEqual(stats["generated"], 1)
            cards = load_shard(tmp, "math-camp")
            self.assertEqual(len(cards), 1)
            self.assertEqual(cards[0]["source_pdf_path"], "academic_notes/math-camp/lecture-notes/real-analysis.meta.json")

    def test_missing_sidecar_is_skipped_not_crashed(self):
        with tempfile.TemporaryDirectory() as tmp:
            lecture_notes_dir = os.path.join(tmp, "academic_notes", "math-camp", "lecture-notes")
            os.makedirs(lecture_notes_dir)
            with open(os.path.join(lecture_notes_dir, "orphaned.md"), "w", encoding="utf-8") as f:
                f.write("# No sidecar")
            stats = rebuild(tmp, client=_fake_client())
            self.assertEqual(stats["generated"], 0)

    def test_unchanged_note_is_not_regenerated_on_second_rebuild(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_video_lecture_note(tmp, "math-camp", "real-analysis", ["A", "B"])
            rebuild(tmp, client=_fake_client())
            stats = rebuild(tmp, client=_fake_client())
            self.assertEqual(stats["unchanged"], 1)
            self.assertEqual(stats["generated"], 0)

    def test_a_lecture_note_survives_prune_when_still_on_disk(self):
        # Regression guard for the bug this task exists to prevent: before
        # _video_lecture_note_paths() existed, a lecture note's card was
        # invisible to rebuild()'s file-discovery walk and would have been
        # flagged/pruned as an orphan even though the note was still there.
        with tempfile.TemporaryDirectory() as tmp:
            _make_video_lecture_note(tmp, "math-camp", "real-analysis", ["A", "B"])
            rebuild(tmp, client=_fake_client())
            stats = rebuild(tmp, client=_fake_client(), prune=True)
            self.assertEqual(stats["pruned"], 0)
            self.assertEqual(len(load_shard(tmp, "math-camp")), 1)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m unittest tests.test_index_search.TestRebuildVideoLectureNotes -v`
Expected: FAIL — `test_generates_a_card_for_a_lecture_note_with_a_sidecar` and the "unchanged"/"survives prune" tests fail with `stats["generated"] == 0`/`KeyError`-shaped assertion failures (the lecture note isn't discovered yet); the "missing sidecar" test happens to pass already (nothing is discovered either way) — confirm the other three fail before continuing.

- [ ] **Step 3: Implement**

In `indexer/index_search.py`, add `compute_id_from_parts` to the existing `from indexer.index_card import (...)` block (alongside `compute_content_hash`, `compute_file_id`, etc.).

Add this function directly after `_textbook_book_dirs` (around line 217):

```python
def _video_lecture_note_paths(academic_hub_root: str, course_filter: str | None):
    notes_root = os.path.join(academic_hub_root, "academic_notes")
    if not os.path.isdir(notes_root):
        return
    for course in sorted(os.listdir(notes_root)):
        if course_filter and course != course_filter:
            continue
        lecture_notes_dir = os.path.join(notes_root, course, "lecture-notes")
        if not os.path.isdir(lecture_notes_dir):
            continue
        for name in sorted(os.listdir(lecture_notes_dir)):
            if not name.lower().endswith(".md"):
                continue
            slug = name[:-3]
            meta_path = os.path.join(lecture_notes_dir, f"{slug}.meta.json")
            if not os.path.exists(meta_path):
                print(f"WARNING: {os.path.join(lecture_notes_dir, name)} has no sidecar "
                      f"{slug}.meta.json -- skipping.")
                continue
            yield course, os.path.join(lecture_notes_dir, name), meta_path
```

In `rebuild()`, add a third loop right after the existing textbook loop (after the block ending `set_rag_md_path(academic_hub_root, file_id, rag_md_path)`, before `_flag_or_prune_orphans(...)`):

```python
    for course_name, md_path, meta_path in _video_lecture_note_paths(academic_hub_root, course):
        with open(meta_path, "r", encoding="utf-8") as f:
            sidecar = json.load(f)
        member_video_ids = sidecar.get("member_video_ids") or []
        if not member_video_ids:
            print(f"WARNING: {meta_path} has no member_video_ids -- skipping.")
            continue

        file_id = compute_id_from_parts(member_video_ids)
        seen_file_ids.add(file_id)
        rel_md_path = os.path.relpath(md_path, academic_hub_root).replace(os.sep, "/")
        rel_meta_path = os.path.relpath(meta_path, academic_hub_root).replace(os.sep, "/")

        with open(md_path, "r", encoding="utf-8") as f:
            content_sample = f.read()

        _reconcile_one(academic_hub_root, course_name, "lecture-notes", file_id, rel_md_path,
                       rel_meta_path, content_sample, None, client, force, stats,
                       source_mtime=os.path.getmtime(md_path),
                       content_hash=compute_content_hash(md_path))
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m unittest tests.test_index_search -v`
Expected: all PASS, including every pre-existing test (this only adds a new discovery loop; it never touches `_notes_pdf_paths`/`_textbook_book_dirs`)

- [ ] **Step 5: Commit**

```bash
git add indexer/index_search.py tests/test_index_search.py
git commit -m "$(cat <<'EOF'
feat(indexer): discover lecture-notes in rebuild() so prune never orphans them

A synthesized lecture note has no source PDF, so it fit neither of
rebuild()'s two existing discovery shapes -- without this, its index
card would eventually be flagged/pruned as an orphan by any corpus-wide
rebuild --prune, even while the note itself is still on disk. Narrow,
additive third discovery path, parallel to _notes_pdf_paths()/
_textbook_book_dirs(); no change to indexer's shared embedding space or
doc_type vocabulary.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01RSVwgCfAbdoph7ua8uziz8
EOF
)"
```

---

### Task 11: `pipeline.py` — CLI + end-to-end orchestration

**Files:**
- Create: `video_notes/pipeline.py`
- Test: `tests/test_pipeline.py`

**Interfaces:**
- Consumes: every function/dataclass produced by Tasks 2–9 (`fetch_video_metadata`, `fetch_playlist_metadata`, `download_audio`, `delete_audio`, `transcribe_audio`, `save_transcript`, `load_transcript`, `load_video_states`, `save_video_state`, `load_group_states`, `save_group_states`, `compute_member_content_hash`, `now_iso`, `group_videos`, `embed_transcripts`, `build_synthesis_prompt`, `synthesize_group_note`, `write_group_note`, `index_group_note`).
- Produces: `run_pipeline(course: str, urls: list[str], playlists: list[str], academic_hub_root: str, video_notes_root: str, client) -> dict` (a summary dict); `main()` (CLI entry point, `python -m video_notes.pipeline`).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_pipeline.py`:

```python
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from video_notes.grouping import Group
from video_notes.pipeline import run_pipeline
from video_notes.transcribe import TranscriptSegment
from video_notes.youtube_metadata import VideoMetadata


def _video(video_id, title="Lecture 1"):
    return VideoMetadata(
        video_id=video_id, url=f"https://youtube.com/watch?v={video_id}", title=title,
        channel_id="UC1", playlist_id=None, playlist_title=None, playlist_index=None,
        upload_date="20260101", duration=100.0,
    )


class TestRunPipeline(unittest.TestCase):
    @patch("video_notes.pipeline.index_group_note")
    @patch("video_notes.pipeline.write_group_note")
    @patch("video_notes.pipeline.synthesize_group_note")
    @patch("video_notes.pipeline.embed_transcripts", return_value={})
    @patch("video_notes.pipeline.group_videos")
    @patch("video_notes.pipeline.transcribe_audio")
    @patch("video_notes.pipeline.download_audio", return_value="/tmp/A.mp3")
    @patch("video_notes.pipeline.delete_audio")
    @patch("video_notes.pipeline.fetch_video_metadata")
    def test_synthesizes_and_indexes_a_new_group(
        self, mock_fetch, mock_delete, mock_download, mock_transcribe,
        mock_group, mock_embed, mock_synthesize, mock_write, mock_index,
    ):
        mock_fetch.return_value = _video("A")
        mock_transcribe.return_value = [TranscriptSegment(0.0, 1.0, "hello")]
        mock_group.return_value = [Group(group_id="g_0001", member_video_ids=["A"], slug="lecture-1", tier="singleton")]
        mock_synthesize.return_value = "# Notes"
        mock_write.return_value = ("academic_notes/math-camp/lecture-notes/lecture-1.md",
                                    "academic_notes/math-camp/lecture-notes/lecture-1.meta.json")

        with tempfile.TemporaryDirectory() as video_notes_root:
            summary = run_pipeline(
                course="math-camp", urls=["https://youtube.com/watch?v=A"], playlists=[],
                academic_hub_root="/fake/hub", video_notes_root=video_notes_root, client=MagicMock(),
            )

        self.assertEqual(summary["groups_synthesized"], 1)
        self.assertEqual(summary["videos_transcribed"], 1)
        mock_index.assert_called_once()

    @patch("video_notes.pipeline.group_videos", return_value=[])
    @patch("video_notes.pipeline.embed_transcripts", return_value={})
    @patch("video_notes.pipeline.download_audio", side_effect=RuntimeError("network down"))
    @patch("video_notes.pipeline.fetch_video_metadata")
    def test_a_failed_video_is_recorded_and_does_not_raise(self, mock_fetch, mock_download, mock_embed, mock_group):
        mock_fetch.return_value = _video("A")
        with tempfile.TemporaryDirectory() as video_notes_root:
            summary = run_pipeline(
                course="math-camp", urls=["https://youtube.com/watch?v=A"], playlists=[],
                academic_hub_root="/fake/hub", video_notes_root=video_notes_root, client=MagicMock(),
            )
        self.assertEqual(summary["videos_failed"], 1)
        self.assertEqual(summary["videos_transcribed"], 0)

    @patch("video_notes.pipeline.index_group_note")
    @patch("video_notes.pipeline.write_group_note")
    @patch("video_notes.pipeline.synthesize_group_note")
    @patch("video_notes.pipeline.embed_transcripts", return_value={})
    @patch("video_notes.pipeline.group_videos")
    @patch("video_notes.pipeline.transcribe_audio")
    @patch("video_notes.pipeline.download_audio", return_value="/tmp/A.mp3")
    @patch("video_notes.pipeline.delete_audio")
    @patch("video_notes.pipeline.fetch_video_metadata")
    def test_unchanged_group_is_not_resynthesized_on_second_run(
        self, mock_fetch, mock_delete, mock_download, mock_transcribe,
        mock_group, mock_embed, mock_synthesize, mock_write, mock_index,
    ):
        mock_fetch.return_value = _video("A")
        mock_transcribe.return_value = [TranscriptSegment(0.0, 1.0, "hello")]
        mock_group.return_value = [Group(group_id="g_0001", member_video_ids=["A"], slug="lecture-1", tier="singleton")]
        mock_synthesize.return_value = "# Notes"
        mock_write.return_value = ("academic_notes/math-camp/lecture-notes/lecture-1.md",
                                    "academic_notes/math-camp/lecture-notes/lecture-1.meta.json")

        with tempfile.TemporaryDirectory() as video_notes_root:
            run_pipeline(course="math-camp", urls=["https://youtube.com/watch?v=A"], playlists=[],
                          academic_hub_root="/fake/hub", video_notes_root=video_notes_root, client=MagicMock())
            summary = run_pipeline(course="math-camp", urls=["https://youtube.com/watch?v=A"], playlists=[],
                                    academic_hub_root="/fake/hub", video_notes_root=video_notes_root, client=MagicMock())

        self.assertEqual(summary["groups_unchanged"], 1)
        self.assertEqual(summary["groups_synthesized"], 0)
        mock_synthesize.assert_called_once()
        mock_download.assert_called_once()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m unittest tests.test_pipeline -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'video_notes.pipeline'`

- [ ] **Step 3: Implement**

Create `video_notes/pipeline.py`:

```python
"""
pipeline.py
CLI entry point + orchestration for the video-lecture-notes pipeline:
fetch metadata -> download+transcribe -> group -> synthesize -> save+index.
Spec: docs/superpowers/specs/2026-09-06-video-lecture-notes-design.md.

Run as a module from academic-rag-model/:
    python -m video_notes.pipeline --course econometrics --urls URL1 URL2
    python -m video_notes.pipeline --course math-camp --playlist PLAYLIST_URL
"""
from __future__ import annotations

import argparse
import dataclasses
import os
import shutil

from video_notes.audio_download import delete_audio, download_audio
from video_notes.grouping import embed_transcripts, group_videos
from video_notes.note_indexing import index_group_note, write_group_note
from video_notes.pipeline_state import (
    compute_member_content_hash, load_group_states, load_video_states,
    now_iso, save_group_states, save_video_state,
)
from video_notes.synthesize import build_synthesis_prompt, synthesize_group_note
from video_notes.transcribe import load_transcript, save_transcript, transcribe_audio
from video_notes.youtube_metadata import fetch_playlist_metadata, fetch_video_metadata

DEFAULT_ACADEMIC_HUB_ROOT = "../academic-hub"


def _transcript_cache_path(video_notes_root: str, video_id: str) -> str:
    return os.path.join(video_notes_root, ".cache", "transcripts", f"{video_id}.json")


def _ensure_transcribed(video, course: str, video_notes_root: str, transcripts_by_id: dict) -> None:
    """Downloads + transcribes one video if it isn't already, updating
    its state. Any failure propagates to the caller, which records it
    and skips just this video without stopping the batch (spec §8)."""
    existing = load_video_states(video_notes_root, course).get(video.video_id, {})
    if existing.get("stage") == "transcribed":
        transcripts_by_id[video.video_id] = load_transcript(existing["transcript_path"])
        return

    audio_path = download_audio(video.video_id, video.url, video_notes_root)
    try:
        segments = transcribe_audio(audio_path)
    finally:
        delete_audio(audio_path)

    transcript_path = _transcript_cache_path(video_notes_root, video.video_id)
    save_transcript(transcript_path, segments)
    transcripts_by_id[video.video_id] = segments
    save_video_state(
        video_notes_root, course, video.video_id, url=video.url,
        metadata=dataclasses.asdict(video), stage="transcribed",
        transcript_path=transcript_path, error=None,
    )


def run_pipeline(
    course: str, urls: list, playlists: list, academic_hub_root: str, video_notes_root: str, client,
) -> dict:
    videos = [fetch_video_metadata(url) for url in urls]
    for playlist_url in playlists:
        videos.extend(fetch_playlist_metadata(playlist_url))
    videos_by_id = {video.video_id: video for video in videos}

    transcripts_by_id: dict = {}
    summary = {
        "videos_transcribed": 0, "videos_failed": 0,
        "groups_synthesized": 0, "groups_unchanged": 0, "groups_failed": 0,
    }

    for video in videos_by_id.values():
        try:
            _ensure_transcribed(video, course, video_notes_root, transcripts_by_id)
            summary["videos_transcribed"] += 1
        except Exception as err:
            print(f"WARNING: failed to process {video.url}: {err}")
            save_video_state(
                video_notes_root, course, video.video_id, url=video.url,
                metadata=dataclasses.asdict(video), stage="failed", error=str(err),
            )
            summary["videos_failed"] += 1

    transcribed_videos = [videos_by_id[vid] for vid in transcripts_by_id]
    embeddings = embed_transcripts(transcripts_by_id)
    groups = group_videos(transcribed_videos, embeddings=embeddings)

    group_states = load_group_states(video_notes_root, course)
    new_group_states: dict = {}

    for group in groups:
        member_hash = compute_member_content_hash(group.member_video_ids, transcripts_by_id)
        existing = group_states.get(group.group_id)
        if existing and existing.get("member_content_hash") == member_hash:
            new_group_states[group.group_id] = existing
            summary["groups_unchanged"] += 1
            continue

        prompt = build_synthesis_prompt(group.slug, group.member_video_ids, videos_by_id, transcripts_by_id)
        markdown = synthesize_group_note(prompt)
        if markdown is None:
            summary["groups_failed"] += 1
            if existing:
                new_group_states[group.group_id] = existing
            continue

        sidecar = {
            "member_video_ids": group.member_video_ids,
            "member_urls": [videos_by_id[vid].url for vid in group.member_video_ids],
            "member_titles": [videos_by_id[vid].title for vid in group.member_video_ids],
            "tier": group.tier,
            "synthesized_at": now_iso(),
        }
        rel_md_path, rel_meta_path = write_group_note(academic_hub_root, course, group.slug, markdown, sidecar)
        index_group_note(academic_hub_root, course, group.member_video_ids, rel_md_path, rel_meta_path, client)

        new_group_states[group.group_id] = {
            "member_video_ids": group.member_video_ids,
            "slug": group.slug,
            "member_content_hash": member_hash,
            "last_synthesized_at": sidecar["synthesized_at"],
            "note_path": rel_md_path,
        }
        summary["groups_synthesized"] += 1

    save_group_states(video_notes_root, course, new_group_states)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Turn a batch of YouTube lecture videos into synthesized Markdown notes.",
    )
    parser.add_argument("--course", required=True, help="Matches an existing academic_notes/<course>/ folder.")
    parser.add_argument("--urls", nargs="+", default=[], help="Individual YouTube video URLs.")
    parser.add_argument("--playlist", action="append", default=[], dest="playlists", help="A YouTube playlist URL (repeatable).")
    parser.add_argument("--academic-hub-root", default=DEFAULT_ACADEMIC_HUB_ROOT)
    args = parser.parse_args()

    if not args.urls and not args.playlists:
        parser.error("pass at least one --urls URL or --playlist URL")

    if shutil.which("ffmpeg") is None:
        print("WARNING: ffmpeg not found on PATH -- audio extraction will fail. Install ffmpeg and retry.")

    from common.gemini_utils import get_gemini_client, load_dotenv_override
    load_dotenv_override()
    client = get_gemini_client()
    if client is None:
        parser.error("GEMINI_API_KEY is required to index the synthesized notes -- see ../.env.example")

    video_notes_root = os.path.dirname(os.path.abspath(__file__))
    summary = run_pipeline(args.course, args.urls, args.playlists, args.academic_hub_root, video_notes_root, client)
    print(f"Done: {summary}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m unittest tests.test_pipeline -v`
Expected: PASS

- [ ] **Step 5: Run the full test suite to check for regressions**

Run: `python -m unittest discover tests -v`
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add video_notes/pipeline.py tests/test_pipeline.py
git commit -m "$(cat <<'EOF'
feat(video_notes): add CLI + end-to-end pipeline orchestration

Wires metadata fetch -> download+transcribe -> group -> synthesize ->
save+index into one resumable run_pipeline(), plus a CLI entry point
(python -m video_notes.pipeline --course ... --urls/--playlist ...).
A per-video failure is recorded and skipped, never stops the batch; a
group only re-synthesizes when its membership/content actually changed.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01RSVwgCfAbdoph7ua8uziz8
EOF
)"
```

---

### Task 12: Documentation

**Files:**
- Create: `video_notes/README.md`
- Modify: `README.md` (repository layout list + Requirements section)

**Interfaces:** none (documentation only).

- [ ] **Step 1: Create `video_notes/README.md`**

```markdown
# Video Lecture Notes

Turns a batch of YouTube lecture videos into synthesized Markdown notes
under `academic_notes/<course>/lecture-notes/` — fully local: audio
download (`yt-dlp`), transcription (`faster-whisper`, CPU), and
synthesis (a local Ollama model) all run on your own machine. The only
API call anywhere in this pipeline is the existing indexer's own
per-note classification+embedding call, the same one every other
indexed document in this corpus already gets.

Run directly:

```powershell
.\.venv\Scripts\python.exe -m video_notes.pipeline --course econometrics --urls "https://youtube.com/watch?v=..." "https://youtube.com/watch?v=..."
.\.venv\Scripts\python.exe -m video_notes.pipeline --course math-camp --playlist "https://youtube.com/playlist?list=..."
```

## Requirements

- `ffmpeg` on your system `PATH` (audio extraction).
- `yt-dlp` and `faster-whisper` (`pip install yt-dlp faster-whisper` — already installed in this repo's `.venv`).
- A local Ollama install (`ollama serve`) with `qwen2.5:7b-instruct` pulled (`ollama pull qwen2.5:7b-instruct`) for synthesis, and `nomic-embed-text` pulled (`ollama pull nomic-embed-text`) for the content-clustering grouping fallback — override either via `VIDEONOTES_OLLAMA_MODEL`/`VIDEONOTES_EMBED_MODEL`.
- `GEMINI_API_KEY` in `../.env` — only used for the existing indexer's per-note classification+embedding call, same as every other document type in this corpus.

## Key files

- `youtube_metadata.py` — `fetch_video_metadata()`/`fetch_playlist_metadata()`, no download.
- `audio_download.py` — `download_audio()`/`delete_audio()`.
- `transcribe.py` — `transcribe_audio()` (faster-whisper, CPU) + a transcript JSON cache so a video is never re-transcribed once done.
- `pipeline_state.py` — per-course resumable state (`.state/<course>.json`, `.state/<course>_groups.json`).
- `grouping.py` — the fully-automatic three-tier grouping algorithm: playlist-as-default → title-series subdivision (only when a playlist genuinely bundles multiple series) → content-clustering fallback (local Ollama embeddings) → singleton. No manual per-batch config.
- `synthesize.py` — builds the timestamp-linked synthesis prompt and calls a local Ollama model.
- `note_indexing.py` — writes the note + `.meta.json` sidecar and registers it with the existing Source Indexer.
- `pipeline.py` — CLI + `run_pipeline()` orchestration.

See the design spec for the full reasoning:
`../docs/superpowers/specs/2026-09-06-video-lecture-notes-design.md`.
```

- [ ] **Step 2: Add `video_notes` to the root `README.md`'s repository layout list**

In `README.md`, add this bullet to the "Repository layout" list, after the existing `problem_gen` bullet:

```markdown
- [`video_notes/`](video_notes/README.md) — turns a batch of YouTube lecture videos into synthesized Markdown notes under `academic_notes/<course>/lecture-notes/`: local audio download + transcription (`yt-dlp`, `faster-whisper`), fully automatic grouping into logical lecture series, and synthesis via a local Ollama model (`qwen2.5:7b-instruct`). No paid API call except the existing indexer's own per-note classification step.
```

- [ ] **Step 3: Add a `video_notes` bullet to the root `README.md`'s Requirements section**

In `README.md`, add this bullet to the "Requirements" list, after the existing `problem_gen` bullet:

```markdown
- **Video lecture notes only** (`video_notes/`): `ffmpeg` on `PATH`, plus `pip install yt-dlp faster-whisper`. A local Ollama install (`ollama serve`) with `qwen2.5:7b-instruct` pulled for synthesis and `nomic-embed-text` pulled for its grouping fallback — no `GEMINI_API_KEY` needed for those steps, though a key is still needed for the existing indexer's own per-note classification call once notes are written. See [`video_notes/README.md`](video_notes/README.md).
```

- [ ] **Step 4: Commit**

```bash
git add video_notes/README.md README.md
git commit -m "$(cat <<'EOF'
docs(video_notes): add subproject README and root README entries

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01RSVwgCfAbdoph7ua8uziz8
EOF
)"
```
