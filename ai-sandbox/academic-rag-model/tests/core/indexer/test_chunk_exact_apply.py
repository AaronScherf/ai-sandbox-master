from __future__ import annotations

import json
import subprocess
import sys

import pytest

from core.indexer import chunk_index, index_card, index_search


def test_file_id_selector_touches_exactly_one_suffix_colliding_card(tmp_path, monkeypatch):
    root = tmp_path / "hub"
    paths = ["academic_notes/econ/summaries/exam1.md",
             "academic_notes/econ/summaries/old_exam1.md"]
    cards = []
    for index, path in enumerate(paths):
        source = root / path
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text(f"# Exam {index}\n", encoding="utf-8")
        cards.append({"file_id": f"id-{index}", "path": path,
                      "content_hash": index_card.compute_content_hash(str(source)),
                      "embedding": [0.1], "needs_indexing": False})
    index_card.save_shard(str(root), "econ", cards)
    touched = []
    monkeypatch.setattr(chunk_index, "generate_chunks_for_file",
                        lambda _, course, card, client: touched.append(card["file_id"]) or {"chunks_written": 1})

    result = chunk_index.chunk(str(root), object(), course="econ", file_id="id-0")
    assert result == {"file_id": "id-0", "matched": True, "chunks_written": 1,
                      "card_status": "current", "failed": 0}
    assert touched == ["id-0"]


def test_duplicate_file_id_fails_before_any_chunk_write(tmp_path, monkeypatch):
    root = tmp_path / "hub"
    index_card.save_shard(str(root), "econ", [
        {"file_id": "same", "path": "academic_notes/econ/a.md"},
        {"file_id": "same", "path": "academic_notes/econ/b.md"},
    ])
    monkeypatch.setattr(chunk_index, "generate_chunks_for_file", lambda *args: pytest.fail("write attempted"))
    with pytest.raises(ValueError, match="multiple cards"):
        chunk_index.chunk(str(root), object(), course="econ", file_id="same")


@pytest.mark.parametrize("module,save_name,filename", [
    (chunk_index, "save_chunks", "chunks/econ.json"),
    (index_card, "save_shard", "econ.json"),
])
def test_interrupted_json_save_preserves_existing_shard(tmp_path, monkeypatch, module, save_name, filename):
    root = tmp_path / "hub"
    save = getattr(module, save_name)
    save(str(root), "econ", [{"old": True}])
    destination = root / ".index" / filename
    before = destination.read_bytes()

    def interrupted_dump(value, stream, **kwargs):
        stream.write("[partial")
        raise RuntimeError("interrupted")

    monkeypatch.setattr(module.json, "dump", interrupted_dump)
    with pytest.raises(RuntimeError, match="interrupted"):
        save(str(root), "econ", [{"new": True}])
    assert destination.read_bytes() == before
    assert not list(destination.parent.glob("*.tmp"))


def test_chunk_cli_file_id_json_is_target_scoped(tmp_path, monkeypatch, capsys):
    root = tmp_path / "hub"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    monkeypatch.setattr(sys, "argv", ["index_search", "--root", str(root), "chunk",
                                   "--course", "econ", "--file-id", "absent", "--json"])
    monkeypatch.setattr(index_search, "load_dotenv_override", lambda: None)
    monkeypatch.setattr(index_search, "get_gemini_client", lambda: object())
    index_search.main()
    assert json.loads(capsys.readouterr().out)["matched"] is False
