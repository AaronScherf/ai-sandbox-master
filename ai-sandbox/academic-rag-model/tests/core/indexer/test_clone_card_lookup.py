from core.indexer.index_card import compute_id_from_parts, find_clone_card
from core.indexer.index_search import _clone_card_id


def _clone(file_id, path, dup="canon"):
    return {"file_id": file_id, "path": path, "duplicate_of_file_id": dup}


def test_prefers_exact_path():
    a, b = _clone("a", "notes/a.md"), _clone("b", "notes/b.md")
    assert find_clone_card([a, b], "canon", "notes/b.md") is b


def test_find_clone_card_prefers_hub_id_over_path():
    a = dict(_clone("a", "notes/a.md"), hub_id="h1")
    b = dict(_clone("b", "notes/b.md"), hub_id="h2")
    assert find_clone_card([a, b], "canon", "notes/a.md", hub_id="h2") is b


def test_moved_clone_with_hub_id_keeps_its_card():
    a = dict(_clone("a", "notes/old/a.md"), hub_id="h1")
    assert find_clone_card([a, {"file_id": "c", "path": "x.md"}], "canon", "notes/part_1/a.md", hub_id="h1") is a


def test_moved_clone_without_hub_id_returns_none_even_if_single_candidate():
    a = _clone("a", "notes/old/a.md")
    assert find_clone_card([a], "canon", "notes/part_1/a.md") is None


def test_two_clones_of_one_canonical_without_hub_id_returns_none():
    cards = [_clone("a", "notes/one/a.md"), _clone("b", "notes/two/b.md")]
    assert find_clone_card(cards, "canon", "notes/three/c.md") is None


def test_normalizes_windows_separators():
    a = _clone("a", "notes" + chr(92) + "a.md")
    assert find_clone_card([a], "other", "notes/a.md") is a


def test_clone_card_id_keeps_existing_id_after_move():
    stats = {"clone_card_unresolved": 0}
    cards = [dict(_clone("existing-id", "notes/old/a.md"), hub_id="h1")]
    assert _clone_card_id(cards, "canon", "notes/new/a.md", "res/new/a.pdf", stats, hub_id="h1") == "existing-id"
    assert stats["clone_card_unresolved"] == 0


def test_clone_card_id_falls_back_and_counts_when_ambiguous():
    stats = {"clone_card_unresolved": 0}
    cards = [_clone("a", "notes/one/a.md"), _clone("b", "notes/two/b.md")]
    got = _clone_card_id(cards, "canon", "notes/three/c.md", "res/c.pdf", stats)
    assert got == compute_id_from_parts(["canon", "res/c.pdf"])
    assert stats["clone_card_unresolved"] == 1
