# pipelines/transcribe_notes/framed_explainer/identity.py
"""Stable card/section keys, input fingerprints and state transitions."""
from __future__ import annotations

import hashlib
import json
from enum import Enum


class State(str, Enum):
    pending = "pending"
    generated = "generated"
    validated = "validated"
    applied = "applied"
    verified = "verified"
    needs_review = "needs_review"
    placement_conflict = "placement_conflict"
    declined = "declined"
    skipped_existing = "skipped_existing"
    stale = "stale"


def card_key(namespace: str, frame_id: str, slide_id: str) -> str:
    return f"{namespace}|{frame_id}|{slide_id}"


def section_key(namespace: str, anchor_slide_id: str | None, seq: int) -> str:
    return f"{namespace}|{anchor_slide_id or 'standalone'}|{seq}"


def input_fingerprint(slide_sha1: str | None, ink: list[dict], frame_id: str | None,
                      prompt_version: str, context_version: str) -> str:
    """sha1 over slide bytes hash, ink identity+geometry, frame association (id,
    not size), prompt version and context version."""
    ink_rows = sorted(([e["id"], e["version"], e["x"], e["y"], e["width"], e["height"]]
                       for e in ink), key=lambda r: r[0])
    payload = json.dumps([slide_sha1, ink_rows, frame_id, prompt_version, context_version],
                         separators=(",", ":"))
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def next_state(current: State | None, stored_fp: str | None, new_fp: str) -> State:
    if current is None:
        return State.pending
    same = stored_fp == new_fp
    if current is State.verified:
        return State.verified if same else State.stale
    if current is State.declined:
        return State.declined if same else State.pending
    return current if same else State.pending
