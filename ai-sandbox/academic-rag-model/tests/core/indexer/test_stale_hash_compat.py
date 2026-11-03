import time

from core.indexer.index_card import compute_content_hash, compute_legacy_content_hash
from core.indexer.index_search import _is_stale


def _note(tmp_path, name, pdf, body="body\n"):
    p = tmp_path / name
    p.write_text(f"---\nsource_pdf: {pdf}\n---\n\n{body}", encoding="utf-8", newline="\n")
    return str(p)


def _stale(card, path):
    return _is_stale(card, time.time(), compute_content_hash(path),
                     legacy_content_hash=compute_legacy_content_hash(path))


def test_fresh_when_stored_hash_is_new_hash_after_move(tmp_path):
    old = _note(tmp_path, "old.md", "a/x.pdf")
    moved = _note(tmp_path, "moved.md", "a/part_1/x.pdf")
    assert _stale({"content_hash": compute_content_hash(old)}, moved) is False


def test_fresh_when_stored_hash_is_legacy_hash_of_current_file(tmp_path):
    p = _note(tmp_path, "n.md", "a/x.pdf")
    assert _stale({"content_hash": compute_legacy_content_hash(p)}, p) is False


def test_stale_when_stored_legacy_hash_is_of_old_bytes(tmp_path):
    # The limit of the compatibility shim: handled by relocate_index_paths, not here.
    old = _note(tmp_path, "old.md", "a/x.pdf")
    moved = _note(tmp_path, "moved.md", "a/part_1/x.pdf")
    assert _stale({"content_hash": compute_legacy_content_hash(old)}, moved) is True


def test_stale_when_body_changed(tmp_path):
    old = _note(tmp_path, "old.md", "a/x.pdf")
    edited = _note(tmp_path, "edited.md", "a/x.pdf", body="edited\n")
    assert _stale({"content_hash": compute_content_hash(old)}, edited) is True
