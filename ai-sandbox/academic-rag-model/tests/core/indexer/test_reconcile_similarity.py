"""Similarity evidence for relink candidates: length-aware body score, shared passage, excerpts."""
from __future__ import annotations

import shutil
import subprocess

import pytest

from core.indexer import reconcile as rc
from core.indexer.index_card import compute_content_hash, save_shard
from core.indexer.reconcile import Candidate, Difference, reconcile
from core.indexer.review_envelope import difference_to_item
from tests.core.indexer.hub_fixture import make_hub, write_note

LN = "academic_notes/econ/lecture_notes"
PS = "academic_notes/econ/problem_sets"


def _words(prefix: str, n: int) -> str:
    return " ".join(f"{prefix}{i}" for i in range(n))


def test_extended_file_that_keeps_the_old_text_scores_high():
    old = rc._shingles(_words("w", 60))
    new = rc._shingles(_words("w", 60) + " " + _words("extra", 600))
    assert rc._jaccard(old, new) < 0.15            # plain jaccard would miss it
    assert rc._body_score(old, new) >= 0.9


def test_short_coincidental_overlap_scores_low():
    old = rc._shingles("the quick brown fox jumps over")      # 4 shingles
    new = rc._shingles("the quick brown fox jumps over " + _words("z", 500))
    assert rc._body_score(old, new) < 0.5          # all of old is shared, but too little to trust


def test_unrelated_text_scores_zero():
    assert rc._body_score(rc._shingles(_words("a", 50)), rc._shingles(_words("b", 50))) == 0.0


def test_body_score_with_empty_side_is_zero():
    assert rc._body_score(set(), rc._shingles(_words("a", 50))) == 0.0


def test_shared_passage_is_longest_common_run_capped():
    old = "intro words here. " + _words("k", 100) + " trailing old stuff"
    new = "completely different start " + _words("k", 100) + " and a new ending"
    passage = rc._shared_passage(old, new, max_words=30)
    assert passage.startswith("k0 k1 k2") and len(passage.split()) == 30


def test_shared_passage_empty_when_run_is_short():
    assert rc._shared_passage("one two three four", "one two three five") == ""


def test_opening_skips_frontmatter_and_collapses_whitespace():
    text = "---\ntitle: x\n---\n\n# Heading\n\n  some    body\ntext " + "y" * 400
    out = rc._opening(text, 50)
    assert out.startswith("# Heading some body text") and len(out) <= 51


def test_deleted_note_is_not_matched_to_unrelated_file_sharing_a_name_fragment(tmp_path):
    """Regression (trial hub 2026-11-05): with no old text to compare, the score used to be rescaled so a
    shared name fragment ("one") in the same course reached 0.6 and offered a deleted note a wrong link."""
    hub = make_hub(tmp_path)
    write_note(hub, f"{LN}/gone.md", {"title": "g"}, "# Gone\n\nThis note will be deleted entirely.\n")
    save_shard(str(hub), "econ", [{"file_id": "f1", "path": f"{LN}/gone.md", "course": "econ",
                                    "content_hash": compute_content_hash(str(hub / f"{LN}/gone.md"))}])
    (hub / LN / "gone.md").unlink()
    write_note(hub, f"{PS}/twin_one.md", {"title": "t"}, "# Twin\n\nAbout duality.\n")
    [d] = reconcile(str(hub))
    assert (d.kind, d.candidates) == ("orphan", [])


@pytest.mark.skipif(shutil.which("git") is None, reason="git executable not on PATH")
def test_heavily_extended_and_renamed_note_is_a_candidate_with_evidence(tmp_path):
    """Moved to a different name AND grown tenfold: name evidence is weak and jaccard is ~0.1, but the old
    text survives verbatim, so the match must still be offered, with the shared passage for the reviewer."""
    hub = make_hub(tmp_path)
    old_body = "# Duality\n\n" + _words("dual", 80) + "\n"
    write_note(hub, f"{LN}/week4.md", {"title": "w"}, old_body)
    for args in (["init", "-q"], ["config", "user.name", "T"], ["config", "user.email", "t@e.x"],
                 ["config", "commit.gpgsign", "false"], ["add", "--", "."], ["commit", "-q", "-m", "i"]):
        subprocess.run(["git", *args], cwd=hub, check=True, capture_output=True)
    save_shard(str(hub), "econ", [{"file_id": "f1", "path": f"{LN}/week4.md", "course": "econ",
                                    "content_hash": compute_content_hash(str(hub / f"{LN}/week4.md"))}])
    (hub / LN / "week4.md").unlink()
    write_note(hub, f"{PS}/complete_study_guide.md", {"title": "g"}, "# Guide\n\n" + _words("new", 700)
               + "\n" + _words("dual", 80) + "\n")
    [d] = reconcile(str(hub))
    assert d.kind == "ambiguous"
    [c] = d.candidates
    assert c.path == f"{PS}/complete_study_guide.md" and c.basis == "similarity"
    assert c.evidence["shared"].startswith("dual0 dual1") and c.evidence["old_opening"].startswith("# Duality")


def test_candidate_carries_evidence_into_review_item():
    c = Candidate("p.md", "similarity", 0.7, {"shared": "a b c d e f", "old_opening": "x", "new_opening": "y"})
    item = difference_to_item(Difference("ambiguous", "f1", "old.md", [c]))
    assert item.candidates[0]["evidence"]["shared"] == "a b c d e f"


def test_candidate_without_evidence_serializes_unchanged():
    item = difference_to_item(Difference("ambiguous", "f1", "old.md", [Candidate("p.md", "byte_hash", 1.0)]))
    assert item.candidates == [{"path": "p.md", "basis": "byte_hash", "score": 1.0}]
