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

from core.indexer.index_card import strip_location_lines


def _state_dir(audio_generator_root: str) -> str:
    return os.path.join(audio_generator_root, ".cache")


def _state_path(audio_generator_root: str) -> str:
    return os.path.join(_state_dir(audio_generator_root), "state.json")


def compute_content_hash(md_path: str) -> str:
    """Canonical, location-neutral full sha256: frontmatter source_*/hub_id
    lines are stripped first, so moving a note's source PDF (which rewrites
    those lines) does not regenerate its audio. Equals legacy_content_hash
    whenever nothing is stripped."""
    with open(md_path, "rb") as f:
        return hashlib.sha256(strip_location_lines(f.read())).hexdigest()


def legacy_content_hash(md_path: str) -> str:
    """The pre-canonical raw-bytes full sha256, still accepted when
    comparing against states written before the canonical hash existed."""
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


def needs_regeneration(state: dict, source, current_hash: str, legacy_hash: str | None = None) -> bool:
    """True if source's .mp3 is missing, or its .md content hash has
    changed since the .mp3 was last (re)generated (spec §5). A stored hash
    equal to legacy_hash (the old raw-bytes hash) also counts as current."""
    if not os.path.exists(source.abs_mp3_path):
        return True
    stored = state.get(source.rel_md_path)
    return stored != current_hash and (legacy_hash is None or stored != legacy_hash)


def upgrade_legacy_entry(state: dict, source, current_hash: str, legacy_hash: str | None) -> bool:
    """If source's stored hash is the legacy one (and differs from the
    canonical one), rewrite it to the canonical hash so the entry survives
    a later location-line rewrite. Mutates state; returns True if changed.
    The caller persists state (never call this on a dry run)."""
    stored = state.get(source.rel_md_path)
    if legacy_hash is not None and stored == legacy_hash and stored != current_hash:
        state[source.rel_md_path] = current_hash
        return True
    return False


def episode_state_key(rel_md_path: str, part_number: int) -> str:
    """Key for one episode's state entry (spec §3.2) -- part_number is
    1-indexed, matching the __partNN filename suffix. Still hashed on the
    whole source file's content, not per-section (a deliberate
    simplification, spec §3.2/§9): a change anywhere in the source
    regenerates every episode for that file, not just the changed one."""
    return f"{rel_md_path}::part{part_number:02d}"


def chapter_state_key(rel_md_path: str, chapter_number: int) -> str:
    """Key for one textbook chapter's state entry (TODO-0057) -- mirrors
    episode_state_key's per-part keys exactly, but with a "ch" infix
    (matching the __chNN output filename suffix) so a textbook chapter
    and a notes episode can never collide in state.json even if they
    happened to share the same number. Still hashed on the whole source
    file's content, the same deliberate simplification episode_state_key
    documents: editing any part of a textbook regenerates every chapter
    for that book, not just the changed one."""
    return f"{rel_md_path}::ch{chapter_number:02d}"
