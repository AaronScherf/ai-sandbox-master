from core.indexer.index_card import compute_id_from_parts, find_clone_card
from core.indexer.index_search import _clone_card_id


def _clone(file_id, path, dup="canon"):
    return {"file_id": file_id, "path": path, "duplicate_of_file_id": dup}


def test_prefers_exact_path():
    a, b = _clone("a", "notes/a.md"), _clone("b", "notes/b.md")
    assert find_clone_card([a, b], "canon", "notes/b.md") is b


def test_after_move_uses_duplicate_id():
    a = _clone("a", "notes/old/a.md")
    assert find_clone_card([a, {"file_id": "c", "path": "x.md"}], "canon", "notes/part_1/a.md") is a


def test_ambiguous_returns_none():
    cards = [_clone("a", "notes/one/a.md"), _clone("b", "notes/two/b.md")]
    assert find_clone_card(cards, "canon", "notes/three/c.md") is None


def test_normalizes_windows_separators():
    a = _clone("a", "notes" + chr(92) + "a.md")
    assert find_clone_card([a], "other", "notes/a.md") is a


def test_clone_card_id_keeps_existing_id_after_move():
    stats = {"clone_card_unresolved": 0}
    cards = [_clone("existing-id", "notes/old/a.md")]
    assert _clone_card_id(cards, "canon", "notes/new/a.md", "res/new/a.pdf", stats) == "existing-id"
    assert stats["clone_card_unresolved"] == 0


def test_clone_card_id_falls_back_and_counts_when_ambiguous():
    stats = {"clone_card_unresolved": 0}
    cards = [_clone("a", "notes/one/a.md"), _clone("b", "notes/two/b.md")]
    got = _clone_card_id(cards, "canon", "notes/three/c.md", "res/c.pdf", stats)
    assert got == compute_id_from_parts(["canon", "res/c.pdf"])
    assert stats["clone_card_unresolved"] == 1
