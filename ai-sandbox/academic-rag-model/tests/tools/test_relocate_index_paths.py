"""Relocation proofs and interrupted writes use only temporary corpus fixtures."""
import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest

from tools import relocate_index_paths as relocate


def _hash(data):
    return hashlib.sha256(data).hexdigest()[:16]


def _write(root, rel, data):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data if isinstance(data, bytes) else data.encode())
    return path


@pytest.mark.parametrize("extension", ["svg", "png"])
def test_source_image_root_correction_proof(tmp_path, monkeypatch, extension):
    root = tmp_path
    rel = f"lecture_notes/Scene.excalidraw.{extension}"
    old_image = f"academic_notes/econometrics/{rel}"
    new_image = f"academic_resources/econometrics/part_1/{rel}"
    _write(root, new_image, b"image")
    old = ("---\nsource_excalidraw: academic_notes/econometrics/lecture_notes/Scene.excalidraw.md\n"
           f"source_image: {old_image}\n---\n\nBody").encode()
    new = ("---\nsource_excalidraw: academic_notes/econometrics/part_1/lecture_notes/Scene.excalidraw.md\n"
           f"source_image: {new_image}\n---\n\nBody").encode()
    card = {"source_asset_path": f"academic_resources/econometrics/{rel}"}
    monkeypatch.setattr(relocate, "_absent_from_baseline", lambda *_: True)
    assert relocate._frontmatter_proof(old, new, _hash(old), "econometrics", card, root, "base") == (True, True)
    assert relocate._frontmatter_proof(old, new, _hash(old.replace(b"\n", b"\r\n")),
                                       "econometrics", card, root, "base") == (True, True)
    assert relocate._frontmatter_proof(old, new + b" edit", _hash(old), "econometrics", card, root, "base") == (False, False)
    for bad_card in ({}, {"source_asset_path": old_image}):
        assert relocate._frontmatter_proof(old, new, _hash(old), "econometrics", bad_card, root, "base") == (False, False)
    monkeypatch.setattr(relocate, "_absent_from_baseline", lambda *_: False)
    assert relocate._frontmatter_proof(old, new, _hash(old), "econometrics", card, root, "base") == (False, False)
    monkeypatch.setattr(relocate, "_absent_from_baseline", lambda *_: True)
    assert relocate._frontmatter_proof(old, new.replace(f"Scene.excalidraw.{extension}".encode(),
                                                       f"Other.excalidraw.{extension}".encode()),
                                       _hash(old), "econometrics", card, root, "base") == (False, False)
    assert relocate._frontmatter_proof(old, new.replace(b"Scene.excalidraw.md", b"Other.excalidraw.md"),
                                       _hash(old), "econometrics", card, root, "base") == (False, False)
    for key in (b"source_pdf", b"source_excalidraw", b"duplicate_of_path"):
        bad_old = old.replace(b"source_image", key)
        bad_new = new.replace(b"source_image", key)
        assert relocate._frontmatter_proof(bad_old, bad_new, _hash(bad_old),
                                           "econometrics", card, root, "base") == (False, False)
    assert relocate._frontmatter_proof(new, old, _hash(new), "econometrics", card, root, "base") == (False, False)


def test_root_correction_missing_or_live_conflict(tmp_path, monkeypatch):
    rel = "lecture_notes/A.excalidraw.svg"
    old = f"academic_notes/econometrics/{rel}"
    new = f"academic_resources/econometrics/part_1/{rel}"
    fields = {"source_excalidraw": "academic_notes/econometrics/lecture_notes/A.excalidraw.md"}
    card = {"source_asset_path": f"academic_resources/econometrics/{rel}"}
    monkeypatch.setattr(relocate, "_absent_from_baseline", lambda *_: True)
    assert not relocate._source_image_root_proof(old, new, fields, card, tmp_path, "econometrics", "base")
    _write(tmp_path, new, b"image")
    _write(tmp_path, old, b"old")
    assert not relocate._source_image_root_proof(old, new, fields, card, tmp_path, "econometrics", "base")
    (tmp_path / old).unlink()
    part_old = old.replace("econometrics/", "econometrics/part_1/")
    _write(tmp_path, part_old, b"old")
    assert not relocate._source_image_root_proof(old, new, fields, card, tmp_path, "econometrics", "base")


def test_baseline_tree_git_error_is_not_absence(tmp_path, monkeypatch):
    class Failed:
        returncode = 128
        stderr = b"fatal"
        stdout = b""
    monkeypatch.setattr(relocate.subprocess, "run", lambda *a, **k: Failed())
    with pytest.raises(ValueError, match="git ls-tree failed"):
        relocate._absent_from_baseline(tmp_path, "bad", "academic_notes/econometrics/old.svg")


def test_frontmatter_exact_insertion_rejects_wrong_value_extra_key_and_body(tmp_path):
    old = b"---\nsource_pdf: academic_resources/econometrics/problem_sets/one.pdf\n---\n\nBody"
    good = old.replace(b"econometrics/problem_sets", b"econometrics/part_1/problem_sets")
    card = {"source_asset_path": "academic_resources/econometrics/problem_sets/one.pdf"}
    proof = lambda current: relocate._frontmatter_proof(
        old, current, _hash(old), "econometrics", card, tmp_path, "base")
    assert proof(good) == (True, False)
    assert proof(good.replace(b"part_1", b"part_2")) == (False, False)
    assert proof(good.replace(b"---\n\nBody", b"extra: value\n---\n\nBody")) == (False, False)
    assert proof(good + b" edited") == (False, False)


def test_catalog_paths_chunks_and_clone_survive_interrupted_apply(tmp_path, monkeypatch):
    root = tmp_path
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    monkeypatch.setattr(relocate, "_index_baseline_unchanged", lambda *_: None)
    notes = root / "academic_notes"
    old = "academic_notes/econometrics/problem_sets/processed_outputs/one.md"
    new = relocate.moved(old, "econometrics")
    clone_old = "academic_notes/econometrics/problem_sets/processed_outputs/one-copy.md"
    clone_new = relocate.moved(clone_old, "econometrics")
    old_bytes = b"---\nsource_pdf: academic_resources/econometrics/problem_sets/one.pdf\n---\n\nBody"
    new_bytes = old_bytes.replace(b"econometrics/problem_sets", b"econometrics/part_1/problem_sets")
    _write(root, old, old_bytes)
    _write(root, clone_old, b"Clone")
    micro_old = "academic_notes/microecon/lecture_notes/one.md"
    micro_new = relocate.moved(micro_old, "microecon")
    _write(root, micro_old, b"micro body")
    subprocess.run(["git", "init", "-q", str(notes)], check=True)
    subprocess.run(["git", "-C", str(notes), "add", "econometrics/problem_sets/processed_outputs/one.md",
                    "econometrics/problem_sets/processed_outputs/one-copy.md",
                    "microecon/lecture_notes/one.md"], check=True)
    subprocess.run(["git", "-C", str(notes), "-c", "user.name=Fixture", "-c", "user.email=fixture@example.test",
                    "commit", "-qm", "baseline"], check=True)
    baseline = subprocess.check_output(["git", "-C", str(notes), "rev-parse", "HEAD"], text=True).strip()
    (root / old).unlink()
    _write(root, new, new_bytes)
    (root / clone_old).unlink()
    _write(root, clone_new, b"Clone")
    (root / micro_old).unlink()
    _write(root, micro_new, b"micro body")
    _write(root, "academic_resources/econometrics/part_1/problem_sets/one.pdf", b"pdf")
    card = {"file_id": "id-one", "path": old, "source_pdf_path": "academic_resources/econometrics/problem_sets/one.pdf",
            "source_asset_path": "academic_resources/econometrics/problem_sets/one.pdf", "rag_md_path": None,
            "content_hash": _hash(old_bytes), "offering_label": "Fall", "embedding": [1, 2]}
    clone = {"file_id": "clone-id", "path": clone_old, "duplicate_of_file_id": "id-one",
             "duplicate_of_path": old, "content_hash": _hash(b"Clone"), "embedding": [5, 6],
             "source_pdf_path": None, "source_asset_path": None, "rag_md_path": None}
    chunk = {"file_id": "id-one", "content_hash": _hash(old_bytes), "embedding": [3, 4]}
    _write(root, ".index/econometrics.json", json.dumps([card, clone], indent=2))
    _write(root, ".index/chunks/econometrics.json", json.dumps([chunk], indent=2))
    _write(root, ".index/microecon.json", json.dumps([{
        "file_id": "micro-id", "path": micro_old, "content_hash": _hash(b"micro body"),
        "embedding": [1, 2], "source_pdf_path": None, "source_asset_path": None,
    }]))
    material = {"path": old, "role": "problem_set", "format": "typeset", "offering": "2024",
                "date": "2024-09-01", "book": None, "order": [1, "a", "b"],
                "confidence": 0.8, "flagged": False, "evidence": ["kept"], "decided_by": "owner"}
    catalog = {"course": "econometrics", "materials": [material],
               "excluded": [old], "unknown_decisions": []}
    catalog_raw = json.dumps(catalog, indent=1) + "\n"
    decisions_raw = json.dumps({old: {"role": "problem_set"},
        "academic_notes/econometrics/problem_sets/": {"role": "problem_set"}}, indent=1) + "\n"
    _write(root, ".index/materials/econometrics.json", catalog_raw)
    _write(root, ".index/materials/econometrics.decisions.json", decisions_raw)
    (root / "academic_notes/econometrics/part_1/problem_sets").mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "-C", str(root), "add", ".index/econometrics.json",
                    ".index/microecon.json", ".index/chunks/econometrics.json", ".index/materials/econometrics.json",
                    ".index/materials/econometrics.decisions.json"], check=True)
    subprocess.run(["git", "-C", str(root), "-c", "user.name=Fixture", "-c", "user.email=fixture@example.test",
                    "commit", "-qm", "index baseline"], check=True)
    index_base = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    monkeypatch.setattr(relocate, "INDEX_BASELINE", index_base)
    report, _ = relocate.plan(str(root), "econometrics", baseline)
    assert report["counts"]["moved_frontmatter"] == 1
    original_replace = relocate.os.replace
    def interrupted(source, destination):
        if str(destination).endswith(".index\\econometrics.json") or str(destination).endswith(".index/econometrics.json"):
            raise OSError("interrupted before card shard")
        return original_replace(source, destination)
    monkeypatch.setattr(relocate.os, "replace", interrupted)
    with pytest.raises(OSError, match="interrupted"):
        relocate.apply(str(root), "econometrics", baseline)
    assert json.loads((root / ".index/chunks/econometrics.json").read_text())[0]["content_hash"] == _hash(new_bytes)
    monkeypatch.setattr(relocate.os, "replace", original_replace)
    unrelated = _write(root, ".index/unrelated.json", "{}")
    with pytest.raises(ValueError, match="unrelated .index"):
        relocate._validate_backup_manifest(root, "econometrics", baseline,
                                           relocate._backup_location(root, "econometrics"))
    unrelated.unlink()
    applied = relocate.apply(str(root), "econometrics", baseline)
    assert applied["status"] == "applied" and applied["post_run_audit"] is True
    cards_after = json.loads((root / ".index/econometrics.json").read_text())
    after = cards_after[0]
    assert after["path"] == new and after["content_hash"] == _hash(new_bytes)
    assert after["embedding"] == [1, 2] and after["offering_label"] == "Fall"
    assert cards_after[1] == {**clone, "path": clone_new, "duplicate_of_path": new}
    assert cards_after[1]["file_id"] == "clone-id"
    assert json.loads((root / ".index/chunks/econometrics.json").read_text())[0] == {
        **chunk, "content_hash": _hash(new_bytes)}
    catalog_after = json.loads((root / ".index/materials/econometrics.json").read_text())
    assert catalog_after["materials"] == [{**material, "path": new}]
    assert catalog_after["excluded"] == [new]
    decisions_after = json.loads((root / ".index/materials/econometrics.decisions.json").read_text())
    assert decisions_after == {new: {"role": "problem_set"},
                               "academic_notes/econometrics/part_1/problem_sets/": {"role": "problem_set"}}
    catalog_path = root / ".index/materials/econometrics.json"
    decisions_path = root / ".index/materials/econometrics.decisions.json"
    assert catalog_path.read_bytes() == catalog_raw.replace(old, new).encode()
    assert decisions_path.read_bytes() == decisions_raw.replace(old, new).replace(
        "academic_notes/econometrics/problem_sets/",
        "academic_notes/econometrics/part_1/problem_sets/").encode()
    for rel in (".index/econometrics.json", ".index/chunks/econometrics.json"):
        data = (root / rel).read_bytes()
        assert b"\n  {" in data and not data.endswith(b"\n")
    manifest = json.loads((relocate._backup_location(root, "econometrics") / "manifest.json").read_text())
    for rel in manifest["files"]:
        assert manifest["files"][rel]["after"] == relocate._full_hash((root / rel).read_bytes())
    assert relocate.apply(str(root), "econometrics", baseline)["status"] == "unchanged"
    assert relocate.apply(str(root), "microecon", baseline)["status"] == "applied"
    assert json.loads((root / ".index/microecon.json").read_text())[0]["path"] == micro_new


def test_catalog_missing_target_blocks_all_writes(tmp_path, monkeypatch):
    root = tmp_path
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    notes = root / "academic_notes"
    notes.mkdir()
    subprocess.run(["git", "init", "-q", str(notes)], check=True)
    _write(root, "academic_notes/README", b"baseline")
    subprocess.run(["git", "-C", str(notes), "add", "README"], check=True)
    subprocess.run(["git", "-C", str(notes), "-c", "user.name=Fixture", "-c", "user.email=fixture@example.test",
                    "commit", "-qm", "baseline"], check=True)
    baseline = subprocess.check_output(["git", "-C", str(notes), "rev-parse", "HEAD"], text=True).strip()
    catalog_path = root / ".index/materials/econometrics.json"
    raw = json.dumps({"course": "econometrics", "materials": [
        {"path": "academic_notes/econometrics/problem_sets/missing.md", "role": "problem_set"}]})
    _write(root, ".index/materials/econometrics.json", raw)
    monkeypatch.setattr(relocate, "_changed_index_paths", lambda *_: set())
    monkeypatch.setattr(relocate, "_index_baseline_unchanged", lambda *_: None)
    report = relocate.apply(str(root), "econometrics", baseline)
    assert report["status"] == "blocked"
    assert report["catalog"][0]["action"] == "missing_target"
    assert catalog_path.read_text() == raw
