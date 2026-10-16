"""Carries the discovery sidecar's OpenAlex identity onto a paper's index card (spec section 7)."""
from __future__ import annotations

import json
from pathlib import Path

from core.indexer.index_card import compute_file_id, set_card_fields


def _sidecar(pdf_path) -> Path:
    # Same rule as discovery's metadata_sidecar.sidecar_path (a test pins them equal); kept local so the
    # converter does not import the discovery package at runtime.
    return Path(pdf_path).with_suffix(".meta.json")


def identity_fields(pdf_path) -> dict | None:
    """Card fields from the paper's discovery sidecar, or None when there is nothing usable (no sidecar,
    unreadable or malformed JSON, or no identity keys). Never raises."""
    try:
        data = json.loads(_sidecar(pdf_path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    topics = [t for t in (data.get("topics") or []) if isinstance(t, dict) and t.get("id")]
    fields = {
        "openalex_id": data.get("openalex_id"), "doi": data.get("doi"),
        "publication_year": data.get("year"), "openalex_topics": topics or None,
    }
    fields = {k: v for k, v in fields.items() if v is not None}
    return fields or None


def attach_identity(pdf_path, index_root) -> bool:
    """Stamps the sidecar's identity onto this PDF's index card. False when there is no sidecar or no card yet."""
    fields = identity_fields(pdf_path)
    if not fields:
        return False
    return set_card_fields(str(index_root), compute_file_id(str(pdf_path)), fields)
