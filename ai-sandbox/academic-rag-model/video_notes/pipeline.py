"""
pipeline.py
CLI entry point + orchestration for the video-lecture-notes pipeline:
fetch metadata -> download+transcribe -> group -> synthesize -> save+index.
Spec: docs/superpowers/specs/2026-09-06-video-lecture-notes-design.md.

Run as a module from academic-rag-model/:
    python -m video_notes.pipeline --course econometrics --urls URL1 URL2
    python -m video_notes.pipeline --course math-camp --playlist PLAYLIST_URL
    python -m video_notes.pipeline --course math-camp --urls-file video_notes/urls.txt
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


def _read_urls_file(path: str) -> list[str]:
    """Reads one video URL per line, skipping blank lines and lines
    starting with `#` (a comment) -- lets a batch be edited as a plain
    unstructured list rather than typed on the command line each time.
    Playlist URLs don't belong in this file -- use --playlist instead,
    since a playlist URL routed through fetch_video_metadata() (what
    these get merged into) doesn't resolve the same way."""
    with open(path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f]
    return [line for line in lines if line and not line.startswith("#")]


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
    parser.add_argument("--urls-file", help="A text file with one video URL per line, not playlists (blank lines and #-comments are skipped).")
    parser.add_argument("--academic-hub-root", default=DEFAULT_ACADEMIC_HUB_ROOT)
    args = parser.parse_args()

    urls = list(args.urls)
    if args.urls_file:
        urls.extend(_read_urls_file(args.urls_file))

    if not urls and not args.playlists:
        parser.error("pass at least one --urls URL, --urls-file path, or --playlist URL")

    if shutil.which("ffmpeg") is None:
        print("WARNING: ffmpeg not found on PATH -- audio extraction will fail. Install ffmpeg and retry.")

    from common.gemini_utils import get_gemini_client, load_dotenv_override
    load_dotenv_override()
    client = get_gemini_client()
    if client is None:
        parser.error("GEMINI_API_KEY is required to index the synthesized notes -- see ../.env.example")

    video_notes_root = os.path.dirname(os.path.abspath(__file__))
    summary = run_pipeline(args.course, urls, args.playlists, args.academic_hub_root, video_notes_root, client)
    print(f"Done: {summary}")


if __name__ == "__main__":
    main()
