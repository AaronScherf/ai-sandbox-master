import json

from core.indexer.hub_identity import read_hub_id
from core.indexer.index_card import compute_content_hash, load_shard, save_shard
from tests.core.indexer.hub_fixture import make_hub, write_note
from tools import write_hub_ids


def _setup(tmp_path):
    hub = make_hub(tmp_path)
    note = write_note(hub, "academic_notes/econ/lecture_notes/a.md", {"title": "A"}, "body\n")
    bare = hub / "academic_notes/econ/problem_sets/b.md"
    bare.write_text("no frontmatter\n", encoding="utf-8", newline="\n")
    rag = write_note(hub, "academic_notes/econ/lecture_notes/a.rag.md", {"title": "R"}, "x\n")
    res = write_note(hub, "academic_resources/econ/r.md", {"title": "R"}, "x\n")
    card = {"file_id": "f1", "path": "academic_notes/econ/lecture_notes/a.md",
            "content_hash": compute_content_hash(str(note))}
    save_shard(str(hub), "econ", [card])
    return hub, note, bare, rag, res


def test_dry_run_writes_nothing(tmp_path):
    hub, note, bare, rag, res = _setup(tmp_path)
    before = note.read_bytes()
    summary = write_hub_ids.plan(str(hub))
    assert summary["would_write"] == {"econ": 2}
    assert note.read_bytes() == before
    assert read_hub_id(str(bare)) is None
    assert "hub_id" not in load_shard(str(hub), "econ")[0]


def test_apply_writes_ids_and_card_hub_id(tmp_path):
    hub, note, bare, rag, res = _setup(tmp_path)
    old_hash = load_shard(str(hub), "econ")[0]["content_hash"]
    summary = write_hub_ids.apply(str(hub))
    assert summary["written"] == 2
    hid = read_hub_id(str(note))
    assert hid and read_hub_id(str(bare))
    card = load_shard(str(hub), "econ")[0]
    assert card["hub_id"] == hid
    assert card["content_hash"] == old_hash == compute_content_hash(str(note))
    assert read_hub_id(str(rag)) is None and read_hub_id(str(res)) is None


def test_apply_is_idempotent(tmp_path):
    hub, note, bare, rag, res = _setup(tmp_path)
    write_hub_ids.apply(str(hub))
    first = note.read_bytes()
    again = write_hub_ids.apply(str(hub))
    assert again["written"] == 0
    assert note.read_bytes() == first


def test_plain_excalidraw_json_skipped_unless_opted_in(tmp_path):
    hub = make_hub(tmp_path)
    scene = hub / "academic_notes/econ/lecture_notes/s.excalidraw"
    scene.write_text(json.dumps({"elements": []}), encoding="utf-8")
    md = write_note(hub, "academic_notes/econ/lecture_notes/s.excalidraw.md", {"x": "1"}, "b\n")
    write_hub_ids.apply(str(hub))
    assert read_hub_id(str(scene)) is None
    assert read_hub_id(str(md))
    write_hub_ids.apply(str(hub), include_excalidraw_json=True)
    assert read_hub_id(str(scene))


def test_empty_frontmatter_is_skipped_and_reported(tmp_path):
    hub = make_hub(tmp_path)
    empty = hub / "academic_notes/econ/lecture_notes/e.md"
    empty.write_bytes(b"---\n---\nbody\n")
    ok = write_note(hub, "academic_notes/econ/lecture_notes/ok.md", {"t": "1"}, "b\n")
    summary = write_hub_ids.apply(str(hub))
    assert summary["written"] == 1
    assert len(summary["skipped"]) == 1
    assert summary["skipped"][0][0].endswith("e.md") and "empty frontmatter" in summary["skipped"][0][1]
    assert empty.read_bytes() == b"---\n---\nbody\n"
    assert read_hub_id(str(ok))
