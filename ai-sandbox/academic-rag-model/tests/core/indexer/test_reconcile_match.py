"""Reconcile engine, read-only core (hub-path-resilience P3 Task 3).

tmp_path hubs only. Git tests build real throwaway repos and skip when `git` is missing.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from core.indexer.hub_identity import write_hub_id
from core.indexer.index_card import compute_content_hash, compute_file_id, save_shard
from core.indexer.reconcile import Candidate, Difference, reconcile, snapshot
from core.indexer.reconcile_git import git_renames
from tests.core.indexer.hub_fixture import make_hub, write_note

LN = "academic_notes/econ/lecture_notes"
BODY = "# Regression\n\nOrdinary least squares minimizes the sum of squared residuals.\n" * 3

needs_git = pytest.mark.skipif(shutil.which("git") is None, reason="git executable not on PATH")


def _card(file_id: str, path: str, **extra) -> dict:
    return {"file_id": file_id, "path": path, "course": "econ", **extra}


def _md_card(hub: Path, rel: str, file_id: str = "f1", **extra) -> dict:
    return _card(file_id, rel, content_hash=compute_content_hash(str(hub / rel)), **extra)


def _move(hub: Path, old: str, new: str) -> None:
    (hub / new).parent.mkdir(parents=True, exist_ok=True)
    os.replace(hub / old, hub / new)


def _tree_digest(root: Path) -> dict[str, str]:
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob("*")) if p.is_file()}


def _by_id(diffs: list[Difference]) -> dict[str, Difference]:
    return {d.file_id: d for d in diffs}


# --- snapshot ---------------------------------------------------------------------------------------


def test_snapshot_keys_are_casefolded_and_keep_disk_spelling(tmp_path):
    hub = make_hub(tmp_path)
    write_note(hub, f"{LN}/Week_One.md", {"title": "a"}, BODY)
    (hub / ".index").mkdir()
    (hub / ".index" / "econ.json").write_text("[]", encoding="utf-8")
    snap = snapshot(str(hub))
    key = f"{LN}/week_one.md"
    assert key in snap
    assert snap[key].path == f"{LN}/Week_One.md"
    assert snap[key].size == (hub / LN / "Week_One.md").stat().st_size
    assert not any(k.startswith(".index/") for k in snap)


# --- matching ---------------------------------------------------------------------------------------


def test_unchanged_card_is_no_difference(tmp_path):
    hub = make_hub(tmp_path)
    write_note(hub, f"{LN}/a.md", {"title": "a"}, BODY)
    save_shard(str(hub), "econ", [_md_card(hub, f"{LN}/a.md")])
    assert reconcile(str(hub)) == []


def test_renamed_file_same_content_is_moved(tmp_path):
    hub = make_hub(tmp_path)
    write_note(hub, f"{LN}/a.md", {"title": "a"}, BODY)
    save_shard(str(hub), "econ", [_md_card(hub, f"{LN}/a.md")])
    _move(hub, f"{LN}/a.md", f"{LN}/renamed.md")
    [d] = reconcile(str(hub))
    assert (d.kind, d.file_id, d.old_path) == ("moved", "f1", f"{LN}/a.md")
    assert [c.path for c in d.candidates] == [f"{LN}/renamed.md"]
    assert d.candidates[0].basis == "byte_hash"


def test_nested_one_layer_is_moved(tmp_path):
    hub = make_hub(tmp_path)
    write_note(hub, f"{LN}/a.md", {"title": "a", "source_pdf": "x/a.pdf"}, BODY)
    save_shard(str(hub), "econ", [_md_card(hub, f"{LN}/a.md")])
    new = "academic_notes/econ/part_1/lecture_notes/a.md"
    _move(hub, f"{LN}/a.md", new)
    # the move tool rewrote the location hint; the canonical hash ignores it
    text = (hub / new).read_text(encoding="utf-8").replace("x/a.pdf", "part_1/x/a.pdf")
    (hub / new).write_text(text, encoding="utf-8", newline="\n")
    [d] = reconcile(str(hub))
    assert d.kind == "moved"
    assert [c.path for c in d.candidates] == [new]


def test_moved_pdf_card_matched_by_byte_hash(tmp_path):
    hub = make_hub(tmp_path)
    pdf = hub / "academic_resources/econ/paper.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake bytes")
    save_shard(str(hub), "econ", [_card(compute_file_id(str(pdf)), "academic_resources/econ/paper.pdf")])
    (hub / "academic_resources/econ/other.pdf").write_bytes(b"%PDF-1.4 different")
    _move(hub, "academic_resources/econ/paper.pdf", "academic_resources/econ/papers/paper_renamed.pdf")
    [d] = reconcile(str(hub))
    assert d.kind == "moved"
    assert [(c.path, c.basis) for c in d.candidates] == [("academic_resources/econ/papers/paper_renamed.pdf",
                                                          "byte_hash")]


def test_identical_copies_after_move_are_ambiguous(tmp_path):
    hub = make_hub(tmp_path)
    write_note(hub, f"{LN}/a.md", {"title": "a"}, BODY)
    save_shard(str(hub), "econ", [_md_card(hub, f"{LN}/a.md")])
    _move(hub, f"{LN}/a.md", f"{LN}/copy_one.md")
    shutil.copyfile(hub / LN / "copy_one.md", hub / "academic_notes/econ/problem_sets/copy_two.md")
    [d] = reconcile(str(hub))
    assert d.kind == "ambiguous"
    assert sorted(c.path for c in d.candidates) == [f"{LN}/copy_one.md", "academic_notes/econ/problem_sets/copy_two.md"]
    assert {c.basis for c in d.candidates} == {"byte_hash"}


def test_rename_and_edit_is_ambiguous_with_similarity_candidate_ranked_first(tmp_path):
    hub = make_hub(tmp_path)
    write_note(hub, f"{LN}/lecture_03_regression.md", {"title": "a"}, BODY)
    write_note(hub, f"{LN}/syllabus.md", {"title": "s"}, "# Syllabus\n\nOffice hours.\n")
    save_shard(str(hub), "econ", [_md_card(hub, f"{LN}/lecture_03_regression.md"),
                                  _md_card(hub, f"{LN}/syllabus.md", file_id="f2")])
    _move(hub, f"{LN}/lecture_03_regression.md", f"{LN}/lecture_03_regression_v2.md")
    with open(hub / LN / "lecture_03_regression_v2.md", "a", encoding="utf-8", newline="\n") as f:
        f.write("\nAn added paragraph on heteroskedasticity.\n")
    write_note(hub, f"{LN}/unrelated_topic.md", {"title": "u"}, "# Game theory\n")
    [d] = reconcile(str(hub))
    assert (d.kind, d.file_id) == ("ambiguous", "f1")
    assert d.candidates[0].path == f"{LN}/lecture_03_regression_v2.md"
    assert {c.basis for c in d.candidates} == {"similarity"}
    assert all(0 < c.score <= 1 for c in d.candidates)
    assert [c.score for c in d.candidates] == sorted((c.score for c in d.candidates), reverse=True)


def test_deleted_file_is_orphan_and_nothing_removed(tmp_path):
    hub = make_hub(tmp_path)
    write_note(hub, f"{LN}/doomed.md", {"title": "a"}, BODY)
    write_note(hub, "academic_notes/econ/problem_sets/hw1.md", {"title": "h"}, "# Homework\n")
    cards = [_md_card(hub, f"{LN}/doomed.md")]
    save_shard(str(hub), "econ", cards)
    (hub / LN / "doomed.md").unlink()
    before = _tree_digest(hub)
    [d] = reconcile(str(hub))
    assert (d.kind, d.file_id, d.old_path, d.candidates) == ("orphan", "f1", f"{LN}/doomed.md", [])
    assert d.evidence
    assert _tree_digest(hub) == before


def test_case_only_rename_is_not_orphan(tmp_path):
    hub = make_hub(tmp_path)
    write_note(hub, f"{LN}/week1.md", {"title": "a"}, BODY)
    save_shard(str(hub), "econ", [_md_card(hub, f"{LN}/week1.md")])
    os.rename(hub / LN / "week1.md", hub / LN / "tmp_case.md")
    os.rename(hub / LN / "tmp_case.md", hub / LN / "Week1.md")
    # Chosen behavior: the card path still resolves case-insensitively, so it is no difference.
    assert reconcile(str(hub)) == []


def test_authored_note_matched_by_hub_id_after_edit(tmp_path):
    hub = make_hub(tmp_path)
    note = write_note(hub, f"{LN}/mine.md", {"title": "mine"}, BODY)
    hub_id = write_hub_id(str(note))
    save_shard(str(hub), "econ", [_md_card(hub, f"{LN}/mine.md", hub_id=hub_id)])
    _move(hub, f"{LN}/mine.md", "academic_notes/econ/problem_sets/renamed_entirely.md")
    with open(hub / "academic_notes/econ/problem_sets/renamed_entirely.md", "a", encoding="utf-8") as f:
        f.write("\nCompletely new paragraph.\n")
    [d] = reconcile(str(hub))
    assert d.kind == "moved"
    assert [(c.path, c.basis) for c in d.candidates] == [("academic_notes/econ/problem_sets/renamed_entirely.md",
                                                          "hub_id")]


def test_authored_note_edited_in_place_is_no_difference(tmp_path):
    hub = make_hub(tmp_path)
    note = write_note(hub, f"{LN}/mine.md", {"title": "mine"}, BODY)
    hub_id = write_hub_id(str(note))
    save_shard(str(hub), "econ", [_md_card(hub, f"{LN}/mine.md", hub_id=hub_id)])
    with open(note, "a", encoding="utf-8") as f:
        f.write("\nedit\n")
    assert reconcile(str(hub)) == []


def test_different_note_at_card_path_is_not_accepted(tmp_path):
    hub = make_hub(tmp_path)
    note = write_note(hub, f"{LN}/mine.md", {"title": "mine"}, BODY)
    hub_id = write_hub_id(str(note))
    save_shard(str(hub), "econ", [_md_card(hub, f"{LN}/mine.md", hub_id=hub_id)])
    _move(hub, f"{LN}/mine.md", f"{LN}/elsewhere.md")
    other = write_note(hub, f"{LN}/mine.md", {"title": "other"}, "# Other\n")
    write_hub_id(str(other))
    [d] = reconcile(str(hub))
    assert d.kind == "moved"
    assert [c.path for c in d.candidates] == [f"{LN}/elsewhere.md"]


def test_file_claimed_by_another_card_is_not_a_candidate(tmp_path):
    hub = make_hub(tmp_path)
    write_note(hub, f"{LN}/a.md", {"title": "a"}, BODY)
    shutil.copyfile(hub / LN / "a.md", hub / LN / "b.md")
    save_shard(str(hub), "econ", [_md_card(hub, f"{LN}/a.md"), _md_card(hub, f"{LN}/b.md", file_id="f2")])
    (hub / LN / "a.md").unlink()
    [d] = reconcile(str(hub))
    assert (d.file_id, d.kind) == ("f1", "orphan")


def test_two_cards_never_both_moved_to_one_file(tmp_path):
    hub = make_hub(tmp_path)
    write_note(hub, f"{LN}/a.md", {"title": "a"}, BODY)
    shutil.copyfile(hub / LN / "a.md", hub / LN / "b.md")
    save_shard(str(hub), "econ", [_md_card(hub, f"{LN}/a.md"), _md_card(hub, f"{LN}/b.md", file_id="f2")])
    _move(hub, f"{LN}/a.md", f"{LN}/c.md")
    (hub / LN / "b.md").unlink()
    diffs = _by_id(reconcile(str(hub)))
    assert {d.kind for d in diffs.values()} == {"ambiguous"}
    for d in diffs.values():
        assert [c.path for c in d.candidates] == [f"{LN}/c.md"]
        assert "several cards" in d.evidence


def test_clone_with_its_own_hub_id_is_not_moved_onto_original_card(tmp_path):
    hub = make_hub(tmp_path)
    note = write_note(hub, f"{LN}/mine.md", {"title": "mine"}, BODY)
    hub_id = write_hub_id(str(note))
    save_shard(str(hub), "econ", [_md_card(hub, f"{LN}/mine.md", hub_id=hub_id)])
    clone = write_note(hub, f"{LN}/clone.md", {"title": "mine"}, BODY)
    write_hub_id(str(clone), "OTHERID000")
    note.unlink()
    [d] = reconcile(str(hub))
    assert d.kind == "ambiguous"
    assert [c.path for c in d.candidates] == [f"{LN}/clone.md"]
    assert "different hub_id" in d.evidence


def test_hub_id_card_matches_file_whose_id_was_lost_by_content(tmp_path):
    hub = make_hub(tmp_path)
    note = write_note(hub, f"{LN}/mine.md", {"title": "mine"}, BODY)
    hub_id = write_hub_id(str(note))
    save_shard(str(hub), "econ", [_md_card(hub, f"{LN}/mine.md", hub_id=hub_id)])
    write_note(hub, f"{LN}/moved_without_id.md", {"title": "mine"}, BODY)
    note.unlink()
    [d] = reconcile(str(hub))
    assert d.kind == "moved"
    assert [c.path for c in d.candidates] == [f"{LN}/moved_without_id.md"]


def test_casefold_only_lookalike_name_is_not_the_card_file(tmp_path):
    # str.casefold maps "ß" to "ss"; NTFS and case-sensitive filesystems treat them as different names.
    hub = make_hub(tmp_path)
    write_note(hub, f"{LN}/strasse.md", {"title": "a"}, BODY)
    save_shard(str(hub), "econ", [_md_card(hub, f"{LN}/strasse.md")])
    (hub / LN / "strasse.md").unlink()
    write_note(hub, f"{LN}/straße.md", {"title": "b"}, "# Different\n")
    [d] = reconcile(str(hub))
    assert d.old_path == f"{LN}/strasse.md"
    assert d.kind != "moved"


def test_case_variant_collision_keeps_both_files_and_never_guesses(tmp_path, monkeypatch):
    import core.indexer.reconcile as reconcile_module

    hub = make_hub(tmp_path)
    write_note(hub, f"{LN}/Week1.md", {"title": "a"}, BODY)
    try:
        write_note(hub, f"{LN}/week1.md", {"title": "b"}, BODY + "different\n")
        real = len([p for p in (hub / LN).iterdir() if p.name.casefold() == "week1.md"]) == 2
    except OSError:
        real = False
    if not real:
        # Case-insensitive filesystem (Windows/macOS default) cannot hold both names: simulate a
        # case-sensitive directory listing; os.stat resolves both spellings to the one real file.
        (hub / LN / "Week1.md").write_text("---\ntitle: a\n---\n\n" + BODY, encoding="utf-8", newline="\n")
        real_walk = os.walk

        def walk(top):
            for dirpath, dirnames, filenames in real_walk(top):
                if Path(dirpath) == hub / LN:
                    filenames = sorted(set(filenames) | {"week1.md"})
                yield dirpath, dirnames, filenames

        monkeypatch.setattr(reconcile_module.os, "walk", walk)
    snap = snapshot(str(hub))
    assert {e.path for e in snap.values() if e.path.casefold().endswith("week1.md")} == {
        f"{LN}/Week1.md", f"{LN}/week1.md"}
    # The card's spelling is neither on-disk name, and its hash matches the Week1.md content.
    save_shard(str(hub), "econ", [_card("f1", f"{LN}/WEEK1.md",
                                        content_hash=compute_content_hash(str(hub / LN / "Week1.md")))])
    [d] = reconcile(str(hub))
    assert d.old_path == f"{LN}/WEEK1.md"
    if real:
        # Two distinct files: only the one whose hash matches is proven; the other is never chosen.
        assert d.kind == "moved"
        assert [c.path for c in d.candidates] == [f"{LN}/Week1.md"]
    else:
        # Both names list the same bytes: picking one spelling would be a guess.
        assert d.kind == "ambiguous"
        assert sorted(c.path for c in d.candidates) == [f"{LN}/Week1.md", f"{LN}/week1.md"]


def test_clone_candidate_does_not_veto_clones_own_proven_move(tmp_path):
    hub = make_hub(tmp_path)
    original = write_note(hub, f"{LN}/o.md", {"title": "o"}, BODY)
    clone = write_note(hub, f"{LN}/c.md", {"title": "o"}, BODY)
    write_hub_id(str(original), "ORIGINAL0001")
    write_hub_id(str(clone), "CLONE0000001")
    cards = [_md_card(hub, f"{LN}/o.md", file_id="O", hub_id="ORIGINAL0001"),
             _md_card(hub, f"{LN}/c.md", file_id="C", hub_id="CLONE0000001")]
    original.unlink()
    _move(hub, f"{LN}/c.md", f"{LN}/c2.md")
    for order in (cards, cards[::-1]):
        save_shard(str(hub), "econ", order)
        diffs = _by_id(reconcile(str(hub)))
        assert diffs["C"].kind == "moved"
        assert [c.path for c in diffs["C"].candidates] == [f"{LN}/c2.md"]
        assert diffs["O"].kind != "moved"


def test_idless_twin_card_does_not_demote_hub_id_proven_move(tmp_path):
    hub = make_hub(tmp_path)
    note = write_note(hub, f"{LN}/h.md", {"title": "h"}, BODY)
    write_hub_id(str(note), "HUBID0000001")
    write_note(hub, f"{LN}/t.md", {"title": "h"}, BODY)  # same canonical hash, no hub_id
    cards = [_md_card(hub, f"{LN}/h.md", file_id="H", hub_id="HUBID0000001"),
             _md_card(hub, f"{LN}/t.md", file_id="T")]
    (hub / LN / "t.md").unlink()
    _move(hub, f"{LN}/h.md", f"{LN}/h2.md")
    for order in (cards, cards[::-1]):
        save_shard(str(hub), "econ", order)
        diffs = _by_id(reconcile(str(hub)))
        assert diffs["H"].kind == "moved"
        assert [(c.path, c.basis) for c in diffs["H"].candidates] == [(f"{LN}/h2.md", "hub_id")]
        assert diffs["T"].kind == "ambiguous"


def test_reconcile_makes_no_api_call(tmp_path, monkeypatch):
    import core.env.gemini_utils as gemini_utils
    from google import genai

    def boom(*args, **kwargs):
        raise AssertionError("reconcile must not construct a model client")

    monkeypatch.setattr(gemini_utils, "get_gemini_client", boom)
    monkeypatch.setattr(genai, "Client", boom)
    hub = make_hub(tmp_path)
    write_note(hub, f"{LN}/a.md", {"title": "a"}, BODY)
    save_shard(str(hub), "econ", [_md_card(hub, f"{LN}/a.md"), _card("gone", f"{LN}/gone.md", content_hash="x")])
    _move(hub, f"{LN}/a.md", f"{LN}/b.md")
    kinds = sorted(d.kind for d in reconcile(str(hub)))
    assert kinds == ["moved", "orphan"]


def test_candidate_and_difference_shapes():
    c = Candidate(path="p", basis="similarity", score=0.5)
    d = Difference(kind="ambiguous", file_id="f", old_path="o", candidates=[c], evidence="e")
    assert d.candidates[0].basis == "similarity"


# --- git renames ------------------------------------------------------------------------------------


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True).stdout


def _init_repo(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init", "-q")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "commit.gpgsign", "false")


def _commit_all(repo: Path, message: str) -> None:
    _git(repo, "add", "--", ".")
    _git(repo, "commit", "-q", "-m", message)


@needs_git
def test_git_renames_reports_staged_and_committed_renames(tmp_path):
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "dir").mkdir()
    (repo / "dir" / "a.md").write_text(BODY, encoding="utf-8")
    (repo / "dir" / "z.md").write_text(BODY + "z\n", encoding="utf-8")
    _commit_all(repo, "init")
    _git(repo, "mv", "dir/a.md", "dir/b.md")
    _commit_all(repo, "rename a->b")
    _git(repo, "mv", "dir/b.md", "dir/c.md")  # staged, not committed
    _git(repo, "mv", "dir/z.md", "dir/y.md")
    renames = git_renames(str(repo))
    assert renames["dir/a.md"] == "dir/c.md"
    assert renames["dir/b.md"] == "dir/c.md"
    assert renames["dir/z.md"] == "dir/y.md"


@needs_git
def test_git_renames_of_non_repo_is_empty(tmp_path):
    assert git_renames(str(tmp_path)) == {}


@needs_git
def test_git_rename_with_edit_in_nested_repo_is_ambiguous_with_git_basis(tmp_path):
    hub = make_hub(tmp_path)
    notes = hub / "academic_notes"  # its own repo, as in the real hub; the hub root is not a repo
    _init_repo(notes)
    write_note(hub, f"{LN}/a.md", {"title": "a"}, BODY)
    _commit_all(notes, "init")
    save_shard(str(hub), "econ", [_md_card(hub, f"{LN}/a.md")])
    _git(notes, "mv", "econ/lecture_notes/a.md", "econ/problem_sets/qq.md")
    with open(hub / "academic_notes/econ/problem_sets/qq.md", "a", encoding="utf-8") as f:
        f.write("one more line\n")
    [d] = reconcile(str(hub))
    assert d.kind == "ambiguous"
    assert d.candidates[0].path == "academic_notes/econ/problem_sets/qq.md"
    assert d.candidates[0].basis == "git_rename"


@needs_git
def test_git_rename_target_with_matching_hash_is_moved(tmp_path):
    # A hub that is itself one repo; a plain `git mv` resolves as moved.
    hub = make_hub(tmp_path)
    _init_repo(hub)
    write_note(hub, f"{LN}/a.md", {"title": "a"}, BODY)
    _commit_all(hub, "init")
    save_shard(str(hub), "econ", [_md_card(hub, f"{LN}/a.md")])
    _git(hub, "mv", f"{LN}/a.md", f"{LN}/b.md")
    [d] = reconcile(str(hub))
    assert d.kind == "moved"
    assert d.candidates[0].path == f"{LN}/b.md"
