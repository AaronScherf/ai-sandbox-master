import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "core" / "indexer"))

from core.indexer.chunk_index import generate_chunks_for_file, load_chunks, save_chunks
from core.indexer.index_card import (
    compute_content_hash, compute_current_content_hash, compute_legacy_content_hash, load_shard, save_shard,
)
from hub_fixture import make_hub, write_note
from tools import rehash_content_hashes as tool

REL = "academic_notes/econ/lecture_notes/n.md"


def _hub(tmp_path, body="body\n", stored="legacy"):
    hub = make_hub(tmp_path)
    note = write_note(hub, REL, {"source_pdf": "academic_resources/econ/lecture_notes/n.pdf"}, body)
    old = compute_legacy_content_hash(str(note)) if stored == "legacy" else stored
    save_shard(str(hub), "econ", [{"file_id": "f1", "path": REL, "course": "econ", "content_hash": old}])
    save_chunks(str(hub), "econ", [{"file_id": "f1", "content_hash": old, "text": "x"}])
    return hub, note, old


def test_plan_lists_card_whose_hash_changes(tmp_path):
    hub, note, old = _hub(tmp_path)
    plan = tool.plan(str(hub))
    assert [r["file_id"] for r in plan["rewrite"]] == ["f1"]
    assert plan["rewrite"][0]["old"] == old
    assert plan["rewrite"][0]["new"] == compute_content_hash(str(note))


def test_stale_card_stays_stale(tmp_path):
    hub, note, _ = _hub(tmp_path, stored="deadbeefdeadbeef")
    plan = tool.plan(str(hub))
    assert plan["rewrite"] == [] and [r["file_id"] for r in plan["stale"]] == ["f1"]
    assert tool.apply(str(hub))["applied"] == 0
    assert load_shard(str(hub), "econ")[0]["content_hash"] == "deadbeefdeadbeef"


def test_apply_rewrites_card_and_chunks_and_is_idempotent(tmp_path):
    hub, note, old = _hub(tmp_path)
    new = compute_content_hash(str(note))
    assert tool.apply(str(hub))["applied"] == 1
    card = load_shard(str(hub), "econ")[0]
    assert card["content_hash"] == new
    assert load_chunks(str(hub), "econ")[0]["content_hash"] == new
    # chunks still count as current: no re-embedding (client is never touched)
    assert generate_chunks_for_file(str(hub), "econ", card, client=None) == {"chunks_written": 0}
    assert tool.apply(str(hub))["applied"] == 0


def test_rerun_after_interrupted_apply_heals_chunks(tmp_path):
    hub, note, old = _hub(tmp_path)
    new = compute_content_hash(str(note))
    save_chunks(str(hub), "econ", [{"file_id": "f1", "content_hash": new, "text": "x"}])  # chunks done, card not
    assert tool.apply(str(hub))["applied"] == 1
    assert load_shard(str(hub), "econ")[0]["content_hash"] == new


def test_missing_file_is_reported_not_raised(tmp_path):
    hub, note, _ = _hub(tmp_path)
    note.unlink()
    assert tool.plan(str(hub))["missing"] == [REL]



def _crlf_hub(tmp_path):
    """A card stored under the EOL-preserving scheme while the note had CRLF; the note is LF now."""
    hub = make_hub(tmp_path)
    note = write_note(hub, REL, {"source_pdf": "academic_resources/econ/lecture_notes/n.pdf"}, "body\n")
    note.write_bytes(note.read_bytes().replace(b"\n", b"\r\n"))
    old = compute_current_content_hash(str(note))
    note.write_bytes(note.read_bytes().replace(b"\r\n", b"\n"))  # the line-ending flip
    assert old != compute_content_hash(str(note))
    save_shard(str(hub), "econ", [{"file_id": "f1", "path": REL, "course": "econ", "content_hash": old}])
    save_chunks(str(hub), "econ", [{"file_id": "f1", "content_hash": old, "text": "x"}])
    return hub, note, old


def test_plan_and_apply_migrate_a_card_stored_before_a_line_ending_flip(tmp_path):
    hub, note, old = _crlf_hub(tmp_path)
    new = compute_content_hash(str(note))
    plan = tool.plan(str(hub))
    assert [(r["old"], r["new"]) for r in plan["rewrite"]] == [(old, new)] and plan["stale"] == []
    assert tool.apply(str(hub))["applied"] == 1
    card = load_shard(str(hub), "econ")[0]
    assert card["content_hash"] == new and load_chunks(str(hub), "econ")[0]["content_hash"] == new
    assert generate_chunks_for_file(str(hub), "econ", card, client=None) == {"chunks_written": 0}
    assert tool.plan(str(hub))["rewrite"] == []


def test_genuinely_changed_note_is_never_rewritten_across_a_line_ending_flip(tmp_path):
    hub, note, old = _crlf_hub(tmp_path)
    note.write_bytes(note.read_bytes().replace(b"body", b"edited"))
    plan = tool.plan(str(hub))
    assert plan["rewrite"] == [] and [r["file_id"] for r in plan["stale"]] == ["f1"]
