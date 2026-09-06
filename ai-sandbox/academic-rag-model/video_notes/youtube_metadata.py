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
