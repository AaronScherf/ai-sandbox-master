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
