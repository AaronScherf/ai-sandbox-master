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
.\.venv\Scripts\python.exe -m video_notes.pipeline --course math-camp --urls-file video_notes/urls.txt
```

`--urls-file` points at a plain text file, one URL per line (blank
lines and `#`-comments skipped) — a `video_notes/urls.txt` template is
included to drop links into. Individual video links and playlist links
can both go in the same file; a playlist link (`youtube.com/playlist?list=...`)
is detected and expanded to every video in it, same as `--playlist`.

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
