"""The content hash and its matching are insensitive to line endings; older stored hashes stay valid."""
import hashlib
import time

import pytest

from core.indexer.audit import MarkdownIndexTarget, audit_markdown_index
from core.indexer.chunk_index import save_chunks
from core.indexer.index_card import (
    accepted_content_hashes, compute_content_hash, compute_current_content_hash,
    compute_legacy_content_hash, content_hash_matches, save_shard,
)
from core.indexer.index_search import _is_stale
from core.indexer.index_search import markdown_preview

FRONT = "---\ntitle: Lecture\nsource_pdf: academic_resources/econ/lecture_notes/n.pdf\nhub_id: abc123\n---\n\n"
BODY = "# Heading\n\nFirst line.\nSecond line.\n"
CRLF = b"\r\n"


def _write(path, text, ending):
    data = text.replace("\n", "\r\n" if ending == "crlf" else "\n").encode("utf-8")
    if ending == "mixed":
        lines = text.split("\n")
        data = "\n".join(line if i % 2 or i == len(lines) - 1 else line + "\r" for i, line in enumerate(lines)).encode("utf-8")
    path.write_bytes(data)
    return str(path)


def _hashes(tmp_path, text=FRONT + BODY):
    out = {}
    for ending in ("lf", "crlf", "mixed"):
        out[ending] = _write(tmp_path / f"{ending}.md", text, ending)
    return out


def test_characterization_old_schemes_differ_across_a_line_ending_flip(tmp_path):
    files = _hashes(tmp_path)
    assert compute_legacy_content_hash(files["lf"]) != compute_legacy_content_hash(files["crlf"])
    assert compute_current_content_hash(files["lf"]) != compute_current_content_hash(files["crlf"])


def test_canonical_hash_is_identical_for_lf_crlf_and_mixed(tmp_path):
    files = _hashes(tmp_path)
    assert len({compute_content_hash(p) for p in files.values()}) == 1


def test_canonical_hash_still_ignores_location_and_identity_lines(tmp_path):
    a = _write(tmp_path / "a.md", FRONT + BODY, "crlf")
    moved = FRONT.replace("lecture_notes/n.pdf", "part_1/lecture_notes/n.pdf").replace("abc123", "zzz999")
    b = _write(tmp_path / "b.md", moved + BODY, "lf")
    assert compute_content_hash(a) == compute_content_hash(b)


def test_canonical_hash_distinguishes_real_changes_in_every_form(tmp_path):
    base = compute_content_hash(_write(tmp_path / "x.md", FRONT + BODY, "lf"))
    for ending in ("lf", "crlf", "mixed"):
        changed = _write(tmp_path / f"c_{ending}.md", FRONT + BODY.replace("First", "Third"), ending)
        assert compute_content_hash(changed) != base


def test_bom_and_lone_cr_are_handled(tmp_path):
    bom = tmp_path / "bom.md"
    bom.write_bytes(b"\xef\xbb\xbf" + (FRONT + BODY).encode("utf-8"))
    bom_crlf = tmp_path / "bom_crlf.md"
    bom_crlf.write_bytes(b"\xef\xbb\xbf" + (FRONT + BODY).replace("\n", "\r\n").encode("utf-8"))
    assert compute_content_hash(str(bom)) == compute_content_hash(str(bom_crlf))
    lone = tmp_path / "lone.md"
    lone.write_bytes(b"line\rother\n")  # a lone CR is not a line ending: bytes unchanged apart from CRLF
    assert compute_content_hash(str(lone)) == hashlib.sha256(b"line\rother\n").hexdigest()[:16]


def test_accepted_hashes_lead_with_the_canonical_one(tmp_path):
    p = _write(tmp_path / "n.md", FRONT + BODY, "crlf")
    accepted = accepted_content_hashes(p)
    assert accepted[0] == compute_content_hash(p)
    assert len(accepted) == len(set(accepted))


@pytest.mark.parametrize("stored_form", ["lf", "crlf", "mixed"])
@pytest.mark.parametrize("file_form", ["lf", "crlf", "mixed"])
@pytest.mark.parametrize("scheme", ["legacy", "current", "canonical"])
def test_stored_hash_of_any_scheme_and_ending_matches_the_file_in_any_ending(tmp_path, scheme, file_form, stored_form):
    stored_file = _write(tmp_path / "stored.md", FRONT + BODY, stored_form)
    stored = {"legacy": compute_legacy_content_hash, "current": compute_current_content_hash,
              "canonical": compute_content_hash}[scheme](stored_file)
    if stored_form == "mixed" and scheme != "canonical":
        pytest.skip("an EOL-preserving hash of a mixed-ending file is not reproducible; see the limit test below")
    current = _write(tmp_path / "now.md", FRONT + BODY, file_form)
    assert content_hash_matches(current, stored)
    # ...but never when the content actually changed
    edited = _write(tmp_path / "edited.md", FRONT + BODY.replace("Second", "Other"), file_form)
    assert not content_hash_matches(edited, stored)


def test_content_hash_matches_rejects_missing_and_garbage(tmp_path):
    p = _write(tmp_path / "n.md", FRONT + BODY, "lf")
    assert not content_hash_matches(p, None)
    assert not content_hash_matches(p, "")
    assert not content_hash_matches(p, "deadbeefdeadbeef")


def test_is_stale_through_reconcile_path_ignores_a_line_ending_flip(tmp_path):
    """The rebuild staleness check: a card hashed under the old CRLF-preserving scheme stays current
    after the file is converted to LF (what a bulk sync or `.gitattributes` would do)."""
    crlf = _write(tmp_path / "n.md", FRONT + BODY, "crlf")
    card = {"content_hash": compute_current_content_hash(crlf)}
    lf = _write(tmp_path / "n.md", FRONT + BODY, "lf")
    canonical = compute_content_hash(lf)
    alias = card["content_hash"] if content_hash_matches(lf, card["content_hash"]) else None
    assert _is_stale(card, time.time(), canonical, alias) is False
    assert _is_stale(card, time.time(), canonical, None) is True  # without the alias the old check would say stale


def test_markdown_preview_does_not_refresh_after_a_bulk_line_ending_flip(tmp_path):
    hub = tmp_path
    rel = "academic_notes/econ/part_1/problem_sets/processed_outputs/n.md"
    path = hub / rel
    path.parent.mkdir(parents=True)
    _write(path, FRONT + BODY, "crlf")
    old = compute_current_content_hash(str(path))
    from core.indexer.index_card import compute_id_from_parts
    card = {"file_id": compute_id_from_parts(["fixture", rel]), "path": rel, "course": "econ",
            "content_hash": old, "source_kind": "markdown_only", "needs_indexing": False,
            "source_pdf_path": rel, "folder_category": "problem_sets"}
    save_shard(str(hub), "econ", [card])
    before = markdown_preview(str(hub), "econ", rel)[0]
    _write(path, FRONT + BODY, "lf")  # the flip
    after = markdown_preview(str(hub), "econ", rel)[0]
    assert after["action"] == before["action"]
    assert after["action"] != "refresh"
    assert old in after["accepted_content_hashes"]


def test_audit_treats_a_card_and_chunks_stored_under_the_old_scheme_as_current_after_a_flip(tmp_path):
    hub = tmp_path / "hub"
    rel = "academic_notes/econ/part_1/problem_sets/processed_outputs/n.md"
    path = hub / rel
    path.parent.mkdir(parents=True)
    _write(path, FRONT + BODY, "crlf")
    old = compute_current_content_hash(str(path))
    save_shard(str(hub), "econ", [{"path": rel, "content_hash": old, "file_id": "f1", "needs_indexing": False}])
    save_chunks(str(hub), "econ", [{"file_id": "f1", "content_hash": old, "text": "x"}])
    _write(path, FRONT + BODY, "lf")  # the flip
    assert old != compute_content_hash(str(path))
    record = audit_markdown_index(hub, [MarkdownIndexTarget(path, rel)]).records[0]
    assert record.card_status == "current"
    assert record.chunks_status == "current"


def test_documented_limit_old_scheme_hash_of_a_mixed_ending_file_is_not_recoverable(tmp_path):
    """A card whose file had *mixed* endings under an EOL-preserving scheme cannot be matched once the file
    is normalized to pure LF or CRLF: the exact mixture is gone. Such a file looks changed (one re-index,
    the same outcome as before this change). The canonical hash of a mixed file has no such limit."""
    mixed = _write(tmp_path / "mixed.md", FRONT + BODY, "mixed")
    legacy, current, canonical = (f(mixed) for f in (compute_legacy_content_hash, compute_current_content_hash,
                                                     compute_content_hash))
    lf = _write(tmp_path / "lf.md", FRONT + BODY, "lf")
    assert not content_hash_matches(lf, legacy)
    assert not content_hash_matches(lf, current)
    assert content_hash_matches(lf, canonical)
