"""
state.py
Content-hash idempotency tracking for audio_generator: which source .md
files already have up-to-date audio, so a re-run only (re)generates what
changed. Spec §2, §5 -- code-repo-local, gitignored (a flat file, since
there's no per-item pipeline stage to track here beyond "is this .mp3
current", unlike video_notes's richer per-video/per-group state).
"""
from __future__ import annotations

import hashlib
import json
import os


def _state_dir(audio_generator_root: str) -> str:
    return os.path.join(audio_generator_root, ".cache")


def _state_path(audio_generator_root: str) -> str:
    return os.path.join(_state_dir(audio_generator_root), "state.json")


def compute_content_hash(md_path: str) -> str:
    with open(md_path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def load_state(audio_generator_root: str) -> dict:
    """Maps a source's rel_md_path to the content hash it had when its
    .mp3 was last (re)generated."""
    path = _state_path(audio_generator_root)
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(audio_generator_root: str, state: dict) -> None:
    path = _state_path(audio_generator_root)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def needs_regeneration(state: dict, source, current_hash: str) -> bool:
    """True if source's .mp3 is missing, or its .md content hash has
    changed since the .mp3 was last (re)generated (spec §5)."""
    if not os.path.exists(source.abs_mp3_path):
        return True
    return state.get(source.rel_md_path) != current_hash


def episode_state_key(rel_md_path: str, part_number: int) -> str:
    """Key for one episode's state entry (spec §3.2) -- part_number is
    1-indexed, matching the __partNN filename suffix. Still hashed on the
    whole source file's content, not per-section (a deliberate
    simplification, spec §3.2/§9): a change anywhere in the source
    regenerates every episode for that file, not just the changed one."""
    return f"{rel_md_path}::part{part_number:02d}"
