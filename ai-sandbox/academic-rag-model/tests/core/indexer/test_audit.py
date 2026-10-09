from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from core.indexer.audit import MarkdownIndexTarget, audit_markdown_index
from core.indexer.chunk_index import chunks_path
from core.indexer.index_card import save_shard


def _write_index(root: Path, course: str, card: dict, chunks: list[dict] | None = None) -> None:
    save_shard(str(root), course, [card])
    if chunks is not None:
        path = Path(chunks_path(str(root), course))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(chunks), encoding="utf-8")


def _card(path: str, content_hash: str = "hash-a", file_id: str = "file-a") -> dict:
    return {"path": path, "content_hash": content_hash, "file_id": file_id, "needs_indexing": False}


def test_audit_reports_current_card_and_chunks_without_writing(tmp_path):
    root = tmp_path / "hub"
    md = root / "academic_notes" / "econ" / "summaries" / "one.md"
    md.parent.mkdir(parents=True)
    md.write_text("summary", encoding="utf-8")
    from core.indexer.index_card import compute_content_hash

    digest = compute_content_hash(str(md))
    path = "academic_notes/econ/summaries/one.md"
    _write_index(root, "econ", _card(path, digest), [{"file_id": "file-a", "content_hash": digest}])
    before = {p.relative_to(root): p.read_bytes() for p in (root / ".index").rglob("*") if p.is_file()}

    result = audit_markdown_index(root, [MarkdownIndexTarget(md, path)])

    assert result.complete
    assert result.records[0].card_status == "current"
    assert result.records[0].chunks_status == "current"
    after = {p.relative_to(root): p.read_bytes() for p in (root / ".index").rglob("*") if p.is_file()}
    assert after == before


def test_audit_distinguishes_missing_and_stale_records(tmp_path):
    root = tmp_path / "hub"
    root.joinpath(".index").mkdir(parents=True)
    md = tmp_path / "summary.md"
    md.write_text("new content", encoding="utf-8")
    stale_path = "academic_notes/econ/summaries/stale.md"
    missing_path = "academic_notes/econ/summaries/missing.md"
    stale = tmp_path / "stale.md"
    stale.write_text("new content", encoding="utf-8")
    _write_index(root, "econ", _card(stale_path, "old-hash"), [])

    result = audit_markdown_index(root, [
        MarkdownIndexTarget(stale, stale_path), MarkdownIndexTarget(md, missing_path),
    ])

    assert [record.card_status for record in result.records] == ["stale_card", "missing_card"]
    assert result.records[0].chunks_status == "missing_chunks"


def test_orphaned_historical_card_does_not_conflict_with_current_card(tmp_path):
    root = tmp_path / "hub"
    md = root / "academic_notes" / "econ" / "lecture_notes" / "one.md"
    md.parent.mkdir(parents=True)
    md.write_text("current content", encoding="utf-8")
    from core.indexer.index_card import compute_content_hash

    digest = compute_content_hash(str(md))
    path = "academic_notes/econ/lecture_notes/one.md"
    save_shard(str(root), "econ", [
        _card(path, "old-hash", "old-file-id") | {"orphaned": True},
        _card(path, digest, "current-file-id"),
    ])
    chunks_file = Path(chunks_path(str(root), "econ"))
    chunks_file.parent.mkdir(parents=True, exist_ok=True)
    chunks_file.write_text(json.dumps([
        {"file_id": "current-file-id", "content_hash": digest},
    ]), encoding="utf-8")

    result = audit_markdown_index(root, [MarkdownIndexTarget(md, path)])

    assert result.complete
    assert result.records[0].card_status == "current"
    assert result.records[0].chunks_status == "current"


def test_missing_or_malformed_index_is_incomplete(tmp_path):
    md = tmp_path / "a.md"
    md.write_text("body", encoding="utf-8")
    target = MarkdownIndexTarget(md, "academic_notes/econ/a.md")

    missing = audit_markdown_index(tmp_path / "missing", [target])
    assert not missing.complete
    assert "unavailable" in missing.errors[0]

    root = tmp_path / "hub"
    index = root / ".index"
    index.mkdir(parents=True)
    (index / "econ.json").write_text("{bad", encoding="utf-8")
    malformed = audit_markdown_index(root, [target])
    assert not malformed.complete
    assert malformed.errors


def test_large_file_is_not_hashed_and_is_reported_unverified(tmp_path):
    root = tmp_path / "hub"
    (root / ".index").mkdir(parents=True)
    md = tmp_path / "large.md"
    md.write_text("0123456789", encoding="utf-8")
    path = "academic_notes/econ/large.md"
    _write_index(root, "econ", _card(path), [{"file_id": "file-a", "content_hash": "hash-a"}])

    with patch("core.indexer.audit.compute_content_hash") as hash_file:
        result = audit_markdown_index(root, [MarkdownIndexTarget(md, path)], max_hash_bytes=4)

    hash_file.assert_not_called()
    assert result.records[0].card_status == "unverified_large"
    assert result.records[0].chunks_status == "unverified_large"
