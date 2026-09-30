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
