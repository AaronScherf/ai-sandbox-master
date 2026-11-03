"""Callers that compared a stored card hash directly must accept legacy hashes."""
from core.indexer.audit import MarkdownIndexTarget, audit_markdown_index
from core.indexer.index_card import compute_legacy_content_hash, load_shard, save_shard
from core.indexer.index_search import _flag_or_prune_orphans, markdown_preview
from test_audit import _card, _write_index

NOTE = "---\nsource_pdf: academic_resources/econometrics/problem_sets/n.pdf\n---\n\n# Problem 1\n\nEstimate beta.\n"


def _note(root, rel):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(NOTE, encoding="utf-8", newline="\n")
    return path


def test_audit_treats_legacy_card_and_chunk_hash_as_current(tmp_path):
    root = tmp_path / "hub"
    rel = "academic_notes/econ/summaries/one.md"
    md = _note(root, rel)
    legacy = compute_legacy_content_hash(str(md))
    _write_index(root, "econ", _card(rel, legacy), [{"file_id": "file-a", "content_hash": legacy}])
    record = audit_markdown_index(root, [MarkdownIndexTarget(md, rel)]).records[0]
    assert (record.card_status, record.chunks_status) == ("current", "current")


def _preview_row(root, rel):
    return next(r for r in markdown_preview(str(root), "econometrics", rel) if r["path"] == rel)


def test_markdown_preview_does_not_refresh_card_with_legacy_hash(tmp_path):
    rel = "academic_notes/econometrics/problem_sets/processed_outputs/n.md"
    md = _note(tmp_path, rel)
    first = _preview_row(tmp_path, rel)
    save_shard(str(tmp_path), "econometrics", [{
        "file_id": first["file_id"], "path": rel, "course": "econometrics",
        "source_kind": first["source_kind"], "content_hash": compute_legacy_content_hash(str(md)),
        "embedding": [1.0, 0.0],
    }])
    assert _preview_row(tmp_path, rel)["action"] != "refresh"


def test_markdown_preview_detects_move_with_legacy_stored_hash(tmp_path):
    old_rel = "academic_notes/econometrics/problem_sets/processed_outputs/old.md"
    new_rel = "academic_notes/econometrics/problem_sets/processed_outputs/new.md"
    md = _note(tmp_path, new_rel)
    first = _preview_row(tmp_path, new_rel)
    save_shard(str(tmp_path), "econometrics", [{
        "file_id": first["file_id"], "path": old_rel, "course": "econometrics",
        "source_kind": first["source_kind"], "content_hash": compute_legacy_content_hash(str(md)),
        "embedding": [1.0, 0.0],
    }])
    assert _preview_row(tmp_path, new_rel)["action"] == "move"


def test_prune_is_skipped_when_a_clone_card_could_not_be_resolved(tmp_path):
    save_shard(str(tmp_path), "econ", [
        {"file_id": "kept", "path": "a.md"}, {"file_id": "moved-clone", "path": "old/b.md"},
    ])
    stats = {"pruned": 0, "orphaned": 0, "clone_card_unresolved": 1}
    _flag_or_prune_orphans(str(tmp_path), {"kept"}, None, True, stats)
    cards = {c["file_id"]: c for c in load_shard(str(tmp_path), "econ")}
    assert set(cards) == {"kept", "moved-clone"}
    assert stats["pruned"] == 0 and cards["moved-clone"].get("orphaned") is True
