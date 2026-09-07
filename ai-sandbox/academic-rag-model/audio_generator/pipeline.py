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
import os
import shutil

from audio_generator.cleaner import clean_markdown_for_speech
from audio_generator.discovery import CONTENT_TYPES, discover_source_files
from audio_generator.engine import ENGINES, synthesize_speech
from audio_generator.narrate import narrate_for_speech
from audio_generator.state import compute_content_hash, load_state, needs_regeneration, save_state

DEFAULT_ACADEMIC_HUB_ROOT = "../academic-hub"


def _narrated_md_path(abs_md_path: str) -> str:
    base, _ext = os.path.splitext(abs_md_path)
    return f"{base}.narrated.md"


def run_pipeline(
    course: str, academic_hub_root: str, audio_generator_root: str, content_types: list, engine: str = "piper",
) -> dict:
    sources = discover_source_files(academic_hub_root, course, content_types)
    state = load_state(audio_generator_root)
    summary = {"generated": 0, "skipped_unchanged": 0, "skipped_empty": 0, "failed": 0}

    for source in sources:
        current_hash = compute_content_hash(source.abs_md_path)
        if not needs_regeneration(state, source, current_hash):
            summary["skipped_unchanged"] += 1
            continue

        with open(source.abs_md_path, "r", encoding="utf-8") as f:
            md_text = f.read()
        narrated_md = narrate_for_speech(md_text)
        text = clean_markdown_for_speech(narrated_md)
        if not text:
            print(f"WARNING: {source.rel_md_path} has no speakable text after cleaning -- skipping.")
            summary["skipped_empty"] += 1
            continue

        try:
            synthesize_speech(text, source.abs_mp3_path, engine=engine)
        except Exception as err:
            print(f"WARNING: failed to synthesize {source.rel_md_path}: {err}")
            summary["failed"] += 1
            continue

        with open(_narrated_md_path(source.abs_md_path), "w", encoding="utf-8") as f:
            f.write(text)

        state[source.rel_md_path] = current_hash
        summary["generated"] += 1

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
