"""Markdown-only and companion indexing in an isolated academic-hub fixture."""
import json
import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from core.indexer.chunk_index import chunk, load_chunks
from core.indexer.index_card import compute_content_hash, compute_file_id, compute_id_from_parts, load_shard, save_shard
from core.indexer.index_search import (
    apply_markdown_plan, build_arg_parser, main, markdown_preview, rebuild, search, search_passages,
    rebuild_plan, retry_file, retry_file_plan,
)
from core.indexer.markdown_sources import exact_markdown_path


def _client():
    client = MagicMock()
    client.models.generate_content.return_value.text = json.dumps({
        "title": "Fixture note", "doc_type": "problem_set", "summary": "A problem about estimation.",
        "level": "intermediate", "has_solutions": False,
    })
    client.models.embed_content.return_value.embeddings[0].values = [1.0, 0.0]
    return client


def _md(root, rel, text="# Problem 1\n\nEstimate beta."):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_rebuild_exact_retry_preserves_source_and_other_cards(tmp_path, monkeypatch, capsys):
    root = tmp_path
    rel = "academic_notes/econometrics/part_1/problem_sets/processed_outputs/pset3.md"
    _md(root, rel)
    pdf = root / "academic_resources/econometrics/part_1/problem_sets/pset3.pdf"
    pdf.parent.mkdir(parents=True)
    pdf.write_bytes(b"source")
    source = "academic_resources/econometrics/part_1/problem_sets/pset3.pdf"
    card = {"file_id": compute_file_id(str(pdf)), "path": rel, "source_pdf_path": source,
            "source_asset_path": source, "offering_label": "Fall 2026", "needs_indexing": True,
            "content_hash": "old", "course": "econometrics", "source_kind": None}
    other = {"file_id": "other", "path": "other.md", "embedding": [7, 8]}
    save_shard(str(root), "econometrics", [card, other])
    assert retry_file_plan(str(root), "econometrics", rel)["estimated_paid_cards"] == 1
    import core.indexer.index_search as search_module
    def unrelated_pass(*_args, **_kwargs):
        pytest.fail("exact retry ran an unrelated pass")
    for name in ("markdown_preview", "_flag_or_prune_orphans", "_link_subsets_safely"):
        monkeypatch.setattr(search_module, name, unrelated_pass)
    monkeypatch.setattr(search_module, "get_gemini_client", lambda: pytest.fail("plan created client"))
    monkeypatch.setattr("sys.argv", ["index_search", "--root", str(root), "rebuild", "--course",
                                    "econometrics", "--file", rel, "--plan", "--json"])
    main()
    assert json.loads(capsys.readouterr().out)["file_id"] == card["file_id"]
    client = _client()
    assert retry_file(str(root), "econometrics", rel, client)["status"] == "applied"
    cards = load_shard(str(root), "econometrics")
    assert cards[1] == other
    assert cards[0]["file_id"] == card["file_id"]
    assert cards[0]["source_pdf_path"] == source
    assert cards[0]["source_asset_path"] == source
    assert cards[0]["offering_label"] == "Fall 2026"
    assert not cards[0]["needs_indexing"]


def test_rebuild_exact_retry_refuses_invalid_targets_and_preserves_failure(tmp_path):
    root = tmp_path
    rel = "academic_notes/econometrics/problem_sets/processed_outputs/failed.md"
    _md(root, rel)
    pdf = root / "academic_resources/econometrics/problem_sets/failed.pdf"
    pdf.parent.mkdir(parents=True)
    pdf.write_bytes(b"pdf")
    card = {"file_id": compute_file_id(str(pdf)), "path": rel,
            "source_pdf_path": "academic_resources/econometrics/problem_sets/failed.pdf",
            "needs_indexing": True, "course": "econometrics"}
    save_shard(str(root), "econometrics", [card])
    for bad in ("academic_notes/econometrics/problem_sets/missing.md",
                "academic_notes/other/problem_sets/processed_outputs/failed.md"):
        with pytest.raises(ValueError):
            retry_file_plan(str(root), "econometrics", bad)
    for change in ({"needs_indexing": False}, {"source_kind": "markdown_only"},
                   {"source_pdf_path": None}, {"file_id": "wrong"}):
        save_shard(str(root), "econometrics", [{**card, **change}])
        with pytest.raises(ValueError):
            retry_file_plan(str(root), "econometrics", rel)
    save_shard(str(root), "econometrics", [card])
    client = _client()
    client.models.generate_content.side_effect = RuntimeError("fixture generation failure")
    assert retry_file(str(root), "econometrics", rel, client)["status"] == "generation_failed"
    assert load_shard(str(root), "econometrics") == [card]


def test_rebuild_plan_never_creates_client_and_cap_covers_producers(tmp_path, monkeypatch, capsys):
    pdf = tmp_path / "academic_notes/econometrics/problem_sets/new.pdf"
    pdf.parent.mkdir(parents=True)
    pdf.write_bytes(b"pdf")
    _md(tmp_path, "academic_notes/econometrics/problem_sets/processed_outputs/new.md")
    assert rebuild_plan(str(tmp_path), "econometrics")["estimated_paid_cards"] >= 1
    import core.indexer.index_search as search_module
    monkeypatch.setattr(search_module, "get_gemini_client", lambda: pytest.fail("client constructed"))
    monkeypatch.setattr("sys.argv", ["index_search", "--root", str(tmp_path), "rebuild",
                                    "--course", "econometrics", "--plan", "--json"])
    main()
    assert json.loads(capsys.readouterr().out)["would_refuse"] is False
    monkeypatch.setattr("sys.argv", ["index_search", "--root", str(tmp_path), "rebuild",
                                    "--course", "econometrics", "--max-paid", "0",
                                    "--ignore-unresolved"])
    with pytest.raises(SystemExit, match="cap is 0"):
        main()


@pytest.mark.parametrize("relative,category", [
    ("problem_sets/one.md", "problem_sets"),
    ("part_1/problem_sets/one.md", "problem_sets"),
    ("part_12/lecture_notes/deep/one.md", "lecture_notes"),
])
def test_part_is_never_markdown_folder_category(tmp_path, relative, category):
    rel = "academic_notes/econometrics/" + relative
    _md(tmp_path, rel)
    row = markdown_preview(str(tmp_path), "econometrics", rel)[0]
    assert row["folder_category"] == category


def test_stray_markdown_under_part_is_reported_but_not_indexed(tmp_path):
    rel = "academic_notes/econometrics/part_1/stray.md"
    _md(tmp_path, rel)
    row = markdown_preview(str(tmp_path), "econometrics", rel)[0]
    assert row["classification"] == "uncategorized"
    assert not row["index_separately"] and row["estimated_paid_cards"] == 0


def test_part_markdown_invalid_doc_type_falls_back_to_content_category(tmp_path):
    rel = "academic_notes/econometrics/part_1/problem_sets/one.md"
    _md(tmp_path, rel)
    client = _client()
    client.models.generate_content.return_value.text = json.dumps({
        "title": "One", "doc_type": "invalid", "summary": "Summary", "level": "introductory",
        "has_solutions": False})
    rows = markdown_preview(str(tmp_path), "econometrics", rel)
    assert apply_markdown_plan(str(tmp_path), rows, client)[0]["status"] == "applied"
    assert load_shard(str(tmp_path), "econometrics")[0]["doc_type"] == "problem_sets"


def test_solution_links_only_same_folder_after_processed_outputs(tmp_path):
    parent = "academic_notes/econometrics/part_1/problem_sets/processed_outputs/problem_set_1.md"
    solution = "academic_notes/econometrics/part_1/problem_sets/problem_set_1_solutions.md"
    old_copy = "academic_notes/econometrics/part_1/problem_sets/old/homework_1_solutions.md"
    no_parent = "academic_notes/econometrics/part_1/problem_sets/no_parent_solutions.md"
    for path in (parent, solution, old_copy, no_parent):
        _md(tmp_path, path, path)
    save_shard(str(tmp_path), "econometrics", [
        {"file_id": "parent", "path": parent, "course": "econometrics", "embedding": [1, 0]},
        {"file_id": "other", "path": "academic_notes/econometrics/part_1/problem_sets/processed_outputs/homework_1.md",
         "course": "econometrics", "embedding": [1, 0]},
    ])
    rows = {r["path"]: r for r in markdown_preview(str(tmp_path), "econometrics")}
    assert rows[solution]["classification"] == "linked_auxiliary"
    assert rows[solution]["companion_of_file_id"] == "parent"
    for path in (old_copy, no_parent):
        assert rows[path]["classification"] == "unlinked_auxiliary"
        assert rows[path]["companion_of_file_id"] is None
        assert rows[path]["companion_of_path"] is None
        assert rows[path]["index_separately"] and rows[path]["action"] == "new"


def test_part_book_chapter_and_hint_link_to_relocated_parents(tmp_path):
    book = "academic_notes/econometrics/part_1/textbooks/Bonus/processed_outputs/Book/Book.rag.md"
    chapter = "academic_notes/econometrics/part_1/textbooks/Bonus/processed_outputs/Book/chapters/01_intro.rag.md"
    parent = "academic_notes/econometrics/part_1/problem_sets/processed_outputs/problem_set_1.md"
    hint = "academic_notes/econometrics/part_1/problem_sets/problem_set_1_hints.md"
    for path in (book, chapter, parent, hint):
        _md(tmp_path, path, path)
    save_shard(str(tmp_path), "econometrics", [
        {"file_id": "book", "path": "academic_resources/econometrics/part_1/textbooks/Bonus/processed_outputs/Book/Book.md",
         "rag_md_path": book, "doc_type": "textbook", "course": "econometrics", "embedding": [1, 0]},
        {"file_id": "problem", "path": parent, "course": "econometrics", "embedding": [1, 0]},
    ])
    rows = {r["path"]: r for r in markdown_preview(str(tmp_path), "econometrics")}
    assert rows[chapter]["classification"] == "generated_companion"
    assert rows[chapter]["companion_of_file_id"] == "book"
    assert rows[hint]["classification"] == "linked_auxiliary"
    assert rows[hint]["companion_of_file_id"] == "problem"


def test_recursive_discovery_and_producer_ownership(tmp_path):
    root = tmp_path
    unknown = _md(root, "academic_notes/econometrics/problem_sets/processed_outputs/problem_set_1.md")
    pdf = root / "academic_notes/econometrics/problem_sets/pset2.pdf"
    pdf.write_bytes(b"pdf")
    _md(root, "academic_notes/econometrics/problem_sets/processed_outputs/pset2.md")
    _md(root, "academic_notes/econometrics/lecture_notes/raw.excalidraw.md", "raw canvas")
    _md(root, "academic_notes/econometrics/audio/__index.md", "machine manifest")
    rows = markdown_preview(str(root), "econometrics")
    by_name = {r["path"].split("/")[-1]: r for r in rows}
    assert by_name[unknown.name]["classification"] == "unknown_origin"
    assert by_name[unknown.name]["action"] == "new"
    assert by_name["pset2.md"]["classification"] == "producer_owned"
    assert by_name["raw.excalidraw.md"]["classification"] == "non_content_auxiliary"
    assert by_name["__index.md"]["classification"] == "non_content_auxiliary"


def test_attached_rendering_and_chapter_companion(tmp_path):
    root = tmp_path
    book = "academic_notes/econometrics/textbooks/processed_outputs/Book/Book.rag.md"
    chapter = "academic_notes/econometrics/textbooks/processed_outputs/Book/chapters/01_intro.rag.md"
    _md(root, book, "whole book")
    _md(root, chapter, "distinct chapter")
    save_shard(str(root), "econometrics", [{
        "file_id": "book-id", "path": "academic_resources/econometrics/textbooks/processed_outputs/Book/Book.md",
        "rag_md_path": book, "doc_type": "textbook", "course": "econometrics",
        "embedding": [1.0, 0.0], "content_hash": "old",
    }])
    rows = markdown_preview(str(root), "econometrics")
    attached = next(r for r in rows if r["path"] == book)
    child = next(r for r in rows if r["path"] == chapter)
    assert attached["action"] == "attach" and not attached["index_separately"]
    assert child["source_kind"] == "generated_companion"
    assert child["companion_of_file_id"] == "book-id"
    assert child["companion_role"] == "chapter"
    assert child["action"] == "new"


def test_identical_chapter_rendering_is_not_a_second_card(tmp_path):
    book = "academic_notes/econometrics/textbooks/processed_outputs/Book/Book.rag.md"
    chapter = "academic_notes/econometrics/textbooks/processed_outputs/Book/chapters/01_intro.rag.md"
    _md(tmp_path, book, "identical whole-book text")
    _md(tmp_path, chapter, "identical whole-book text")
    save_shard(str(tmp_path), "econometrics", [{
        "file_id": "book-id", "path": "academic_resources/econometrics/textbooks/processed_outputs/Book/Book.md",
        "rag_md_path": book, "doc_type": "textbook", "course": "econometrics",
        "embedding": [1.0, 0.0], "content_hash": "old",
    }])
    row = markdown_preview(str(tmp_path), "econometrics", chapter)[0]
    assert row["classification"] == "attached_rendering"
    assert row["companion_of_file_id"] == "book-id"
    assert row["companion_of_path"].endswith("/Book.md")
    assert row["action"] == "attach" and row["estimated_paid_calls"] == 0


def test_exact_apply_edit_move_and_orphan_search(tmp_path):
    root = tmp_path
    rel = "academic_notes/econometrics/problem_sets/processed_outputs/problem_set_1.md"
    path = _md(root, rel)
    client = _client()
    rows = markdown_preview(str(root), "econometrics", rel)
    assert rows[0]["estimated_paid_cards"] == 1
    with pytest.raises(ValueError, match="cap"):
        apply_markdown_plan(str(root), rows, client, max_paid=0)
    assert load_shard(str(root), "econometrics") == []
    assert apply_markdown_plan(str(root), rows, client)[0]["status"] == "applied"
    card = load_shard(str(root), "econometrics")[0]
    first_id = card["file_id"]
    assert card["source_kind"] == "markdown_only"
    assert card["source_pdf_path"] is None and card["source_asset_path"] is None
    assert markdown_preview(str(root), "econometrics", rel)[0]["action"] == "unchanged"
    path.write_text("# Problem 1\n\nEstimate the intercept.", encoding="utf-8")
    changed = markdown_preview(str(root), "econometrics", rel)
    assert changed[0]["action"] == "refresh" and changed[0]["file_id"] == first_id
    apply_markdown_plan(str(root), changed, client)
    assert load_shard(str(root), "econometrics")[0]["content_hash"] == compute_content_hash(str(path))
    moved_rel = "academic_notes/econometrics/problem_sets/processed_outputs/renamed.md"
    moved = root / moved_rel
    path.rename(moved)
    move_plan = markdown_preview(str(root), "econometrics", moved_rel)
    assert move_plan[0]["action"] == "move" and move_plan[0]["file_id"] == first_id
    apply_markdown_plan(str(root), move_plan, client)
    assert load_shard(str(root), "econometrics")[0]["path"] == moved_rel
    moved.unlink()
    rebuild(str(root), client)
    assert load_shard(str(root), "econometrics")[0]["orphaned"]
    assert search([str(root)], "estimate", client, course="econometrics") == []


def test_rebuild_indexes_unknown_note_and_keeps_legacy_pdf_card(tmp_path):
    root = tmp_path
    _md(root, "academic_notes/econometrics/problem_sets/processed_outputs/problem_set_1.md")
    pdf = root / "academic_notes/econometrics/problem_sets/pset2.pdf"
    pdf.write_bytes(b"pdf")
    _md(root, "academic_notes/econometrics/problem_sets/processed_outputs/pset2.md")
    client = _client()
    first = rebuild(str(root), client, course="econometrics")
    cards = load_shard(str(root), "econometrics")
    assert first["generated"] == 2
    assert len(cards) == 2
    assert {c.get("source_kind") for c in cards} == {None, "markdown_only"}
    client.models.generate_content.reset_mock()
    second = rebuild(str(root), client, course="econometrics")
    assert second["generated"] == 0
    client.models.generate_content.assert_not_called()


def test_exact_selector_and_cli_flags(tmp_path):
    rel = "academic_notes/econometrics/problem_sets/pset.md"
    _md(tmp_path, rel)
    assert exact_markdown_path(str(tmp_path), "econometrics", rel).endswith("pset.md")
    with pytest.raises(ValueError):
        exact_markdown_path(str(tmp_path), "econometrics", "academic_notes/econometrics/../other.md")
    parser = build_arg_parser()
    args = parser.parse_args(["index-md", "--course", "econometrics", "--file", rel, "--apply", "--writer-coordinated"])
    assert args.apply and args.writer_coordinated and args.file == rel


def test_cli_preview_needs_no_api_client(tmp_path, monkeypatch, capsys):
    import sys
    rel = "academic_notes/econometrics/problem_sets/pset.md"
    _md(tmp_path, rel)
    monkeypatch.setattr(sys, "argv", ["index_search", "--root", str(tmp_path), "index-md",
                                  "--course", "econometrics", "--file", rel, "--json"])
    monkeypatch.setattr("core.indexer.index_search.get_gemini_client",
                        lambda: pytest.fail("read-only preview requested an API client"))
    main()
    rows = json.loads(capsys.readouterr().out)
    assert len(rows) == 1 and rows[0]["action"] == "new"
    assert rows[0]["estimated_paid_calls"] == 2
    assert not (tmp_path / ".index").exists()


def test_two_new_copies_do_not_claim_one_old_id(tmp_path):
    old_rel = "academic_notes/econometrics/problem_sets/old.md"
    old = _md(tmp_path, old_rel)
    client = _client()
    apply_markdown_plan(str(tmp_path), markdown_preview(str(tmp_path), "econometrics", old_rel), client)
    old_id = load_shard(str(tmp_path), "econometrics")[0]["file_id"]
    a = tmp_path / "academic_notes/econometrics/problem_sets/a.md"
    b = tmp_path / "academic_notes/econometrics/problem_sets/b.md"
    old.rename(a)
    b.write_bytes(a.read_bytes())
    rows = markdown_preview(str(tmp_path), "econometrics")
    moved = [r for r in rows if r["path"].endswith(("/a.md", "/b.md"))]
    assert len(moved) == 2
    assert all(r["classification"] == "ambiguous_move" and r["action"] == "new" for r in moved)
    assert len({r["file_id"] for r in moved}) == 2
    assert old_id not in {r["file_id"] for r in moved}


def test_reclassification_preserves_card_id(tmp_path):
    child = "academic_notes/econometrics/textbooks/processed_outputs/Book/chapters/01_intro.rag.md"
    _md(tmp_path, child, "A long enough chapter about statistical estimation and regression to be a useful standalone passage.")
    client = _client()
    apply_markdown_plan(str(tmp_path), markdown_preview(str(tmp_path), "econometrics", child), client)
    original = load_shard(str(tmp_path), "econometrics")[0]
    assert original["source_kind"] == "markdown_only"
    book = "academic_notes/econometrics/textbooks/processed_outputs/Book/Book.rag.md"
    _md(tmp_path, book, "whole book")
    save_shard(str(tmp_path), "econometrics", [original, {
        "file_id": "book-id", "path": "academic_resources/econometrics/textbooks/processed_outputs/Book/Book.md",
        "rag_md_path": book, "doc_type": "textbook", "course": "econometrics",
        "embedding": [1.0, 0.0], "content_hash": "old",
    }])
    row = markdown_preview(str(tmp_path), "econometrics", child)[0]
    assert row["action"] == "update_metadata" and row["file_id"] == original["file_id"]
    assert row["source_kind"] == "generated_companion"
    apply_markdown_plan(str(tmp_path), [row], client)
    cards = load_shard(str(tmp_path), "econometrics")
    child_cards = [c for c in cards if c["path"] == child]
    assert len(child_cards) == 1 and child_cards[0]["file_id"] == original["file_id"]
    assert child_cards[0]["companion_of_file_id"] == "book-id"


def test_rebuild_links_hint_after_parent_card_is_created(tmp_path):
    _md(tmp_path, "academic_notes/econometrics/problem_sets/processed_outputs/problem_set_1.md")
    _md(tmp_path, "academic_notes/econometrics/problem_sets/problem_set_1_hints.md", "# Hint\n\nConsider the sample mean.")
    _md(tmp_path, "academic_notes/econometrics/problem_sets/problem_set_1_gemini_solutions.md", "# Solution\n\nThe estimate is consistent.")
    rebuild(str(tmp_path), _client(), course="econometrics")
    cards = {Path(c["path"]).name: c for c in load_shard(str(tmp_path), "econometrics")}
    assert cards["problem_set_1_hints.md"]["source_kind"] == "markdown_only"
    assert cards["problem_set_1_hints.md"]["companion_of_file_id"] == cards["problem_set_1.md"]["file_id"]
    assert cards["problem_set_1_gemini_solutions.md"]["companion_of_file_id"] == cards["problem_set_1.md"]["file_id"]
    assert cards["problem_set_1_gemini_solutions.md"]["companion_role"] == "solutions"


def test_present_question_sidecar_survives_missing_parent(tmp_path):
    rel = "academic_notes/econometrics/lecture_notes/processed_outputs/note.excalidraw.questions.md"
    path = _md(tmp_path, rel, "---\nsource_note_file_id: parent-id\n---\n# Question and answer")
    save_shard(str(tmp_path), "econometrics", [{
        "file_id": "question-id", "path": rel, "source_pdf_path": "academic_notes/econometrics/lecture_notes/note.excalidraw.md",
        "source_asset_path": None, "course": "econometrics", "doc_type": "excalidraw_questions",
        "embedding": [1.0, 0.0], "content_hash": compute_content_hash(str(path)),
        "title": "Question", "summary": "An answer", "needs_indexing": False,
    }])
    rebuild(str(tmp_path), _client(), course="econometrics")
    card = load_shard(str(tmp_path), "econometrics")[0]
    assert card["file_id"] == "question-id" and not card.get("orphaned")
    assert card["source_kind"] == "generated_companion"
    assert card["companion_of_file_id"] == "parent-id"


def test_question_sidecar_keeps_producer_id_when_rag_arrives_later(tmp_path):
    raw_rel = "academic_notes/econometrics/lecture_notes/note.excalidraw.md"
    raw = _md(tmp_path, raw_rel, "raw canvas")
    parent_id = compute_file_id(str(raw))
    question_rel = "academic_notes/econometrics/lecture_notes/processed_outputs/note.excalidraw.questions.md"
    _md(tmp_path, question_rel, f"---\nsource_note_file_id: {parent_id}\n---\n# Answer\n\nA useful answer.")
    first_plan = markdown_preview(str(tmp_path), "econometrics")
    question_row = next(r for r in first_plan if r["path"] == question_rel)
    assert question_row["file_id"] == compute_id_from_parts(["excalidraw_questions", parent_id])
    rebuild(str(tmp_path), _client(), course="econometrics")
    assert len(load_shard(str(tmp_path), "econometrics")) == 1
    _md(tmp_path, "academic_notes/econometrics/lecture_notes/processed_outputs/note.excalidraw.rag.md",
        "# Transcript\n\nThis is a useful long note about econometric analysis and estimation.")
    rebuild(str(tmp_path), _client(), course="econometrics")
    cards = load_shard(str(tmp_path), "econometrics")
    assert len(cards) == 2
    assert len([c for c in cards if c["file_id"] == question_row["file_id"]]) == 1


def test_failed_generation_is_retryable(tmp_path, monkeypatch):
    rel = "academic_notes/econometrics/problem_sets/pset.md"
    _md(tmp_path, rel)
    plan = markdown_preview(str(tmp_path), "econometrics", rel)
    def fail(**_kwargs):
        raise RuntimeError("offline")
    monkeypatch.setattr("core.indexer.index_card.generate_index_card", fail)
    result = apply_markdown_plan(str(tmp_path), plan, _client())
    assert result[0]["status"] == "needs_indexing"
    card = load_shard(str(tmp_path), "econometrics")[0]
    assert card["needs_indexing"] and card["source_kind"] == "markdown_only"
    monkeypatch.undo()
    retry = markdown_preview(str(tmp_path), "econometrics", rel)
    assert retry[0]["action"] == "refresh"
    assert apply_markdown_plan(str(tmp_path), retry, _client())[0]["status"] == "applied"


def test_failed_refresh_keeps_previous_card(tmp_path, monkeypatch):
    rel = "academic_notes/econometrics/problem_sets/pset.md"
    path = _md(tmp_path, rel)
    apply_markdown_plan(str(tmp_path), markdown_preview(str(tmp_path), "econometrics", rel), _client())
    original = load_shard(str(tmp_path), "econometrics")[0]
    path.write_text("# Revised problem\n\nEstimate a different parameter.", encoding="utf-8")
    plan = markdown_preview(str(tmp_path), "econometrics", rel)
    assert plan[0]["action"] == "refresh"
    monkeypatch.setattr("core.indexer.index_search.generate_index_card",
                        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("offline")))
    assert apply_markdown_plan(str(tmp_path), plan, _client())[0]["status"] == "generation_failed"
    assert load_shard(str(tmp_path), "econometrics")[0] == original


def test_exact_apply_leaves_other_cards_and_missing_file_reappears(tmp_path):
    one = "academic_notes/econometrics/problem_sets/one.md"
    two = "academic_notes/econometrics/problem_sets/two.md"
    first_path = _md(tmp_path, one)
    _md(tmp_path, two)
    client = _client()
    apply_markdown_plan(str(tmp_path), markdown_preview(str(tmp_path), "econometrics", one), client)
    first_card = load_shard(str(tmp_path), "econometrics")[0]
    apply_markdown_plan(str(tmp_path), markdown_preview(str(tmp_path), "econometrics", two), client)
    assert first_card in load_shard(str(tmp_path), "econometrics")
    first_path.unlink()
    rebuild(str(tmp_path), client, course="econometrics")
    assert next(c for c in load_shard(str(tmp_path), "econometrics")
                if c["file_id"] == first_card["file_id"])["orphaned"]
    _md(tmp_path, one)
    rebuild(str(tmp_path), client, course="econometrics")
    restored = next(c for c in load_shard(str(tmp_path), "econometrics")
                    if c["file_id"] == first_card["file_id"])
    assert not restored.get("orphaned")
    assert any(r.file_id == first_card["file_id"]
               for r in search([str(tmp_path)], "estimation", client, course="econometrics"))


def test_generated_companion_is_separate_and_stale_chunks_are_hidden(tmp_path):
    root = tmp_path
    book = "academic_notes/econometrics/textbooks/processed_outputs/Book/Book.rag.md"
    child = "academic_notes/econometrics/textbooks/processed_outputs/Book/chapters/01_intro.rag.md"
    _md(root, book, "whole book")
    _md(root, child, "# Introduction\n\nThis chapter explains estimation and regression in detail, with enough examples and derivations to support a useful passage citation.")
    save_shard(str(root), "econometrics", [{
        "file_id": "book-id", "path": "academic_resources/econometrics/textbooks/processed_outputs/Book/Book.md",
        "rag_md_path": book, "doc_type": "textbook", "course": "econometrics",
        "embedding": [1.0, 0.0], "content_hash": "old", "title": "Book", "summary": "Whole book",
    }])
    client = _client()
    plan = markdown_preview(str(root), "econometrics", child)
    assert apply_markdown_plan(str(root), plan, client)[0]["status"] == "applied"
    card = next(c for c in load_shard(str(root), "econometrics") if c.get("source_kind") == "generated_companion")
    assert card["companion_of_file_id"] == "book-id"
    assert any(r.file_id == card["file_id"] for r in search([str(root)], "regression", client, course="econometrics"))
    assert chunk(str(root), client, course="econometrics", file_id=card["file_id"])["chunks_written"] > 0
    assert any(r.file_id == card["file_id"] for r in search_passages([str(root)], "regression", client, course="econometrics"))
    child_path = root / child
    child_path.write_text("# Revised\n\nA different chapter about regression, with a new explanation and many details that require the old passage embedding to be retired.", encoding="utf-8")
    apply_markdown_plan(str(root), markdown_preview(str(root), "econometrics", child), client)
    assert all(r.file_id != card["file_id"] for r in search_passages([str(root)], "regression", client, course="econometrics"))
    assert load_chunks(str(root), "econometrics")  # old chunks exist until chunk is rerun


def _scene(root, name="Lecture 2026-09-07", course="microecon"):
    base = f"academic_notes/{course}/part_1/lecture_notes"
    scene = _md(root, f"{base}/{name}.excalidraw.md", "scene bytes")
    rag = f"{base}/processed_outputs/{name}.excalidraw.rag.md"
    questions = f"{base}/processed_outputs/{name}.excalidraw.questions.md"
    _md(root, rag, "# Lecture\n\nUtility maximization.")
    _md(root, questions, "# Questions\n\n1. What is a budget set?")
    return scene, rag, questions


def test_rebuild_file_creates_card_for_one_cardless_scene_output(tmp_path):
    root = tmp_path
    scene, rag, questions = _scene(root)
    other = {"file_id": "other", "path": "other.md", "embedding": [7, 8]}
    save_shard(str(root), "microecon", [other])
    plan = retry_file_plan(str(root), "microecon", rag)
    assert (plan["action"], plan["reason"], plan["estimated_paid_cards"]) == ("new", "no_card", 1)
    assert plan["file_id"] == compute_file_id(str(scene))
    client = _client()
    assert retry_file(str(root), "microecon", rag, client)["status"] == "applied"
    cards = load_shard(str(root), "microecon")
    assert other in cards and len(cards) == 2
    card = next(c for c in cards if c["file_id"] == plan["file_id"])
    assert card["path"] == rag and card["source_pdf_path"].endswith("Lecture 2026-09-07.excalidraw.md")
    assert not card.get("needs_indexing")
    # the sibling question sidecar was NOT carded by the rag run
    assert all(c["path"] != questions for c in cards)


def test_rebuild_file_questions_sidecar_is_a_companion_of_its_scene(tmp_path):
    root = tmp_path
    scene, _rag, questions = _scene(root)
    save_shard(str(root), "microecon", [])
    plan = retry_file_plan(str(root), "microecon", questions)
    assert plan["file_id"] == compute_id_from_parts(["excalidraw_questions", compute_file_id(str(scene))])
    assert retry_file(str(root), "microecon", questions, _client())["status"] == "applied"
    card = load_shard(str(root), "microecon")[0]
    assert card["source_kind"] == "generated_companion"
    assert card["companion_of_file_id"] == compute_file_id(str(scene))
    assert card["companion_role"] == "questions"


def test_rebuild_file_refuses_unsuitable_cardless_targets(tmp_path):
    root = tmp_path
    scene, rag, _questions = _scene(root)
    save_shard(str(root), "microecon", [])
    plain = _md(root, "academic_notes/microecon/part_1/tutoring/notes.md")
    with pytest.raises(ValueError):  # not a scene output: still needs an existing card
        retry_file_plan(str(root), "microecon", "academic_notes/microecon/part_1/tutoring/notes.md")
    orphan = "academic_notes/microecon/part_1/lecture_notes/processed_outputs/Gone.excalidraw.rag.md"
    _md(root, orphan)
    with pytest.raises(ValueError, match="no matching Excalidraw scene"):
        retry_file_plan(str(root), "microecon", orphan)
    (root / rag).write_text("", encoding="utf-8")
    with pytest.raises(ValueError, match="empty"):
        retry_file_plan(str(root), "microecon", rag)
    (root / rag).write_text("# Lecture", encoding="utf-8")
    assert retry_file(str(root), "microecon", rag, _client())["status"] == "applied"
    with pytest.raises(ValueError, match="needs_indexing producer card"):  # now carded: normal rule applies
        retry_file_plan(str(root), "microecon", rag)
    # a card with the same identity at another path (a moved note) must not get a duplicate
    save_shard(str(root), "microecon", [{"file_id": compute_file_id(str(scene)), "path": "elsewhere.md"}])
    with pytest.raises(ValueError, match="already has a card"):
        retry_file_plan(str(root), "microecon", rag)
