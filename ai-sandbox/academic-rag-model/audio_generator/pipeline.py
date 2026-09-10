"""
pipeline.py
CLI entry point + orchestration for audio_generator: discover source .md
files for a course -> skip ones already up to date -> clean -> synthesize ->
write the sibling .mp3 -> update state. Spec:
docs/superpowers/specs/2026-09-06-audio-generator-design.md.

Run as a module from academic-rag-model/:
    python -m audio_generator.pipeline --course math-camp
    python -m audio_generator.pipeline --course math-camp --content-type textbook --engine kokoro
    python -m audio_generator.pipeline --course math-camp --dry-run
"""
from __future__ import annotations

import argparse
import dataclasses
import os
import shutil

from audio_generator.cleaner import clean_markdown_for_speech
from audio_generator.discovery import CONTENT_TYPES, discover_source_files
from audio_generator.engine import ENGINES, synthesize_speech
from audio_generator.narrate import narrate_for_speech
from audio_generator.sections import (
    AUDIOGEN_SECTIONS_CHARS_PER_MINUTE,
    group_sections_into_episodes,
    narrate_sections,
    split_into_sections,
)
from audio_generator.state import compute_content_hash, episode_state_key, load_state, needs_regeneration, save_state

DEFAULT_ACADEMIC_HUB_ROOT = "../academic-hub"


def _narrated_md_path(abs_md_path: str) -> str:
    base, _ext = os.path.splitext(abs_md_path)
    return f"{base}.narrated.md"


def _write_index_manifest(base: str, episodes: list) -> None:
    """Writes <base>__index.md, a plain-text manifest mapping each part to
    the section titles it contains and its estimated duration (spec §3.2)
    -- a listening aid, not audio metadata (embedding real MP3 chapter
    markers via ID3 tags was considered and deferred as unnecessary
    complexity for v1)."""
    lines = ["# Episode index", ""]
    for i, episode in enumerate(episodes, start=1):
        minutes = len(episode.text) / AUDIOGEN_SECTIONS_CHARS_PER_MINUTE
        titles = ", ".join(episode.section_titles) if episode.section_titles else "(untitled)"
        lines.append(f"- Part {i:02d} (~{minutes:.0f} min): {titles}")
    with open(f"{base}__index.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def _run_notes_source(source, state: dict, engine: str, summary: dict) -> None:
    """Episode-aware path for notes sources (spec §3.2): splits the raw
    .md at every header level, narrates/cleans each section
    independently, then groups sections into 10-20 minute episodes,
    writing one <name>__partNN.mp3 per episode. Idempotency is tracked
    per-episode but still hashed on the whole source file (a deliberate
    simplification -- spec §3.2/§9)."""
    current_hash = compute_content_hash(source.abs_md_path)
    with open(source.abs_md_path, "r", encoding="utf-8") as f:
        md_text = f.read()

    sections = split_into_sections(md_text)
    narrated_sections = narrate_sections(sections)
    episodes = group_sections_into_episodes(narrated_sections)

    base, _ext = os.path.splitext(source.abs_md_path)
    for i, episode in enumerate(episodes, start=1):
        key = episode_state_key(source.rel_md_path, i)
        abs_mp3_path = f"{base}__part{i:02d}.mp3"
        episode_source = dataclasses.replace(source, rel_md_path=key, abs_mp3_path=abs_mp3_path)

        if not needs_regeneration(state, episode_source, current_hash):
            summary["skipped_unchanged"] += 1
            continue
        if not episode.text:
            summary["skipped_empty"] += 1
            continue

        try:
            synthesize_speech(episode.text, abs_mp3_path, engine=engine)
        except Exception as err:
            print(f"WARNING: failed to synthesize {key}: {err}")
            summary["failed"] += 1
            continue

        with open(f"{base}__part{i:02d}.narrated.md", "w", encoding="utf-8") as f:
            f.write(episode.text)

        state[key] = current_hash
        summary["generated"] += 1

    _write_index_manifest(base, episodes)


def _run_textbook_source(source, state: dict, engine: str, summary: dict) -> None:
    """Unchanged one-file-one-MP3 path (spec §3.2's scope is notes-only;
    textbook chapter-boundary reuse via chapter_index.py is a separate,
    unstarted investigation, spec §9)."""
    current_hash = compute_content_hash(source.abs_md_path)
    if not needs_regeneration(state, source, current_hash):
        summary["skipped_unchanged"] += 1
        return

    with open(source.abs_md_path, "r", encoding="utf-8") as f:
        md_text = f.read()
    narrated_md = narrate_for_speech(md_text)
    text = clean_markdown_for_speech(narrated_md)
    if not text:
        print(f"WARNING: {source.rel_md_path} has no speakable text after cleaning -- skipping.")
        summary["skipped_empty"] += 1
        return

    try:
        synthesize_speech(text, source.abs_mp3_path, engine=engine)
    except Exception as err:
        print(f"WARNING: failed to synthesize {source.rel_md_path}: {err}")
        summary["failed"] += 1
        return

    with open(_narrated_md_path(source.abs_md_path), "w", encoding="utf-8") as f:
        f.write(text)

    state[source.rel_md_path] = current_hash
    summary["generated"] += 1


def run_pipeline(
    course: str, academic_hub_root: str, audio_generator_root: str, content_types: list, engine: str = "piper",
) -> dict:
    sources = discover_source_files(academic_hub_root, course, content_types)
    state = load_state(audio_generator_root)
    summary = {"generated": 0, "skipped_unchanged": 0, "skipped_empty": 0, "failed": 0}

    for source in sources:
        if source.content_type == "notes":
            _run_notes_source(source, state, engine, summary)
        else:
            _run_textbook_source(source, state, engine, summary)

    save_state(audio_generator_root, state)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert a course's Markdown notes/textbooks into local TTS audio (MP3s).",
    )
    parser.add_argument("--course", required=True, help="Matches an existing academic_notes/<course>/ or academic_resources/<course>/ folder.")
    parser.add_argument("--academic-hub-root", default=DEFAULT_ACADEMIC_HUB_ROOT)
    parser.add_argument(
        "--content-type", default=",".join(CONTENT_TYPES),
        help=f"Comma-separated subset of {CONTENT_TYPES}. Defaults to both.",
    )
    parser.add_argument("--engine", choices=ENGINES, default="piper")
    parser.add_argument("--dry-run", action="store_true", help="List what would be (re)generated without synthesizing anything.")
    args = parser.parse_args()

    content_types = [c.strip() for c in args.content_type.split(",") if c.strip()]
    audio_generator_root = os.path.dirname(os.path.abspath(__file__))

    if shutil.which("ffmpeg") is None:
        print(
            "WARNING: ffmpeg not found on PATH -- MP3 encoding will fail for every file. "
            "Install ffmpeg (e.g. `winget install ffmpeg` or https://ffmpeg.org/download.html) and retry.",
        )

    if args.dry_run:
        sources = discover_source_files(args.academic_hub_root, args.course, content_types)
        state = load_state(audio_generator_root)
        for source in sources:
            current_hash = compute_content_hash(source.abs_md_path)
            status = "regenerate" if needs_regeneration(state, source, current_hash) else "up to date"
            print(f"{status}: {source.rel_md_path}")
        return

    summary = run_pipeline(args.course, args.academic_hub_root, audio_generator_root, content_types, args.engine)
    print(f"Done: {summary}")


if __name__ == "__main__":
    main()
