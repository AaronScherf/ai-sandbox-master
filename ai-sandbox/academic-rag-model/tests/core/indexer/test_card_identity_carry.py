"""I5 (hub-path-resilience P3 final wave): a card keeps its note identity (hub_id, link_state) when it
is regenerated. tmp_path only; the model client is a MagicMock (no API call)."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from core.indexer.hub_identity import write_hub_id
from core.indexer.index_card import (
    compute_content_hash, compute_file_id, find_card_by_file_id, reconcile_and_write, save_shard,
)
from core.indexer.index_search import _apply_markdown_row, rebuild


def _fake_client():
    client = MagicMock()
    gen = MagicMock()
    gen.text = ('{"title": "T", "doc_type": "ta_notes", "summary": "S.", '
                '"level": "introductory", "has_solutions": false}')
    client.models.generate_content.return_value = gen
    emb = MagicMock()
    emb.values = [0.1, 0.2]
    resp = MagicMock()
    resp.embeddings = [emb]
    client.models.embed_content.return_value = resp
    return client


def _hub(tmp_path: Path, card_extra: dict | None = None, stamp: str | None = None) -> tuple[Path, Path, str]:
    root = tmp_path / "hub"
    pdf = root / "academic_resources/econometrics/problem_sets/hw.pdf"
    pdf.parent.mkdir(parents=True)
    pdf.write_bytes(b"%PDF-1.4 homework")
    md = root / "academic_notes/econometrics/problem_sets/processed_outputs/hw.md"
    md.parent.mkdir(parents=True)
    md.write_text("---\ntitle: hw\n---\n\nFirst transcription.\n", encoding="utf-8", newline="\n")
    if stamp:
        write_hub_id(str(md), stamp)
    fid = compute_file_id(str(pdf))
    rel_pdf = pdf.relative_to(root).as_posix()
    save_shard(str(root), "econometrics", [{
        "file_id": fid, "path": md.relative_to(root).as_posix(), "source_pdf_path": rel_pdf,
        "source_asset_path": rel_pdf, "course": "econometrics", "embedding": [1, 0],
        "content_hash": compute_content_hash(str(md)), **(card_extra or {}),
    }])
    return root, md, fid


def _edit(md: Path) -> None:
    with open(md, "a", encoding="utf-8", newline="\n") as f:
        f.write("A corrected paragraph.\n")


def _card(root: Path, fid: str) -> dict:
    return find_card_by_file_id(str(root), fid)[1]


def test_edited_stamped_note_keeps_hub_id_after_rebuild(tmp_path):
    root, md, fid = _hub(tmp_path, {"hub_id": "abc123def456"}, stamp="abc123def456")
    _edit(md)
    stats = rebuild(str(root), _fake_client(), course="econometrics")
    assert stats["updated"] == 1
    assert _card(root, fid)["hub_id"] == "abc123def456"


def test_regenerated_card_carries_hub_id_and_link_state_when_file_lost_the_id(tmp_path):
    root, md, fid = _hub(tmp_path, {"hub_id": "abc123def456", "link_state": "unresolved"})
    _edit(md)
    rebuild(str(root), _fake_client(), course="econometrics")
    card = _card(root, fid)
    assert card["hub_id"] == "abc123def456"
    assert card["link_state"] == "unresolved"


def test_note_stamped_after_first_indexing_gets_hub_id_on_regeneration(tmp_path):
    root, md, fid = _hub(tmp_path)
    assert "hub_id" not in _card(root, fid)
    write_hub_id(str(md), "fedcba987654")
    _edit(md)
    rebuild(str(root), _fake_client(), course="econometrics")
    assert _card(root, fid)["hub_id"] == "fedcba987654"


def test_patch_path_fills_missing_hub_id_from_the_file(tmp_path):
    root, md, fid = _hub(tmp_path, stamp="0123456789ab")
    rel = md.relative_to(root).as_posix()
    reconcile_and_write(str(root), file_id=fid, path=rel, source_pdf_path=None, course="econometrics",
                        folder_category="problem_sets", content_sample="", page_count=None, client=None,
                        content_hash=compute_content_hash(str(md)))
    assert _card(root, fid)["hub_id"] == "0123456789ab"


def test_markdown_refresh_row_keeps_hub_id(tmp_path):
    root = tmp_path / "hub"
    md = root / "academic_notes/econometrics/lecture_notes/notes.md"
    md.parent.mkdir(parents=True)
    md.write_text("---\ntitle: n\n---\n\nLecture body.\n", encoding="utf-8", newline="\n")
    write_hub_id(str(md), "aaaabbbbcccc")
    rel = md.relative_to(root).as_posix()
    save_shard(str(root), "econometrics", [{
        "file_id": "md1", "path": rel, "course": "econometrics", "embedding": [1, 0],
        "content_hash": "stale", "hub_id": "aaaabbbbcccc", "link_state": "unresolved",
        "source_pdf_path": None, "source_asset_path": None,
    }])
    row = {"action": "refresh", "path": rel, "content_hash": compute_content_hash(str(md)),
           "companion_role": None, "file_id": "md1", "course": "econometrics",
           "folder_category": "lecture_notes", "source_kind": None, "companion_of_file_id": None,
           "relationship_basis": None}
    result = _apply_markdown_row(str(root), row, _fake_client())
    assert result["status"] != "generation_failed"
    card = _card(root, "md1")
    assert card["hub_id"] == "aaaabbbbcccc"
    assert card["link_state"] == "unresolved"
