from core.indexer.index_card import (
    LOCATION_FIELDS,
    compute_content_hash,
    compute_legacy_content_hash,
    content_hash_matches,
)


def _w(tmp_path, name, data):
    p = tmp_path / name
    p.write_bytes(data if isinstance(data, bytes) else data.encode("utf-8"))
    return str(p)


def _note(pdf="a/x.pdf", title="T", body="body\n"):
    return f"---\nsource_pdf: {pdf}\ntitle: {title}\n---\n\n{body}"


def test_location_fields_constant():
    assert LOCATION_FIELDS == ("source_pdf", "source_excalidraw", "source_image", "duplicate_of_path")


def test_move_only_location_change_keeps_hash(tmp_path):
    a = _w(tmp_path, "a.md", _note(pdf="a/x.pdf"))
    b = _w(tmp_path, "b.md", _note(pdf="a/part_1/x.pdf"))
    assert compute_content_hash(a) == compute_content_hash(b)
    assert compute_legacy_content_hash(a) != compute_legacy_content_hash(b)


def test_body_edit_changes_hash(tmp_path):
    a = _w(tmp_path, "a.md", _note())
    b = _w(tmp_path, "b.md", _note(body="edited\n"))
    assert compute_content_hash(a) != compute_content_hash(b)


def test_non_location_field_edit_changes_hash(tmp_path):
    a = _w(tmp_path, "a.md", _note(title="T"))
    b = _w(tmp_path, "b.md", _note(title="Other"))
    assert compute_content_hash(a) != compute_content_hash(b)


def test_no_location_fields_equals_legacy_hash(tmp_path):
    with_fm = _w(tmp_path, "a.md", "---\ntitle: T\n---\n\nbody\n")
    no_fm = _w(tmp_path, "b.md", "just a body\n")
    for p in (with_fm, no_fm):
        assert compute_content_hash(p) == compute_legacy_content_hash(p)


def test_crlf_and_bom_note_keeps_hash_on_move(tmp_path):
    def raw(pdf):
        return (b"\xef\xbb\xbf---\r\nsource_pdf: " + pdf + b"\r\ntitle: T\r\n---\r\n\r\nbody\r\n")
    a = _w(tmp_path, "a.md", raw(b"a/x.pdf"))
    b = _w(tmp_path, "b.md", raw(b"a/part_1/x.pdf"))
    assert compute_content_hash(a) == compute_content_hash(b)


def test_location_key_in_body_is_not_removed(tmp_path):
    a = _w(tmp_path, "a.md", _note(body="source_pdf: one\n"))
    b = _w(tmp_path, "b.md", _note(body="source_pdf: two\n"))
    assert compute_content_hash(a) != compute_content_hash(b)


def test_content_hash_matches_accepts_legacy_and_new(tmp_path):
    p = _w(tmp_path, "a.md", _note())
    assert content_hash_matches(p, compute_content_hash(p))
    assert content_hash_matches(p, compute_legacy_content_hash(p))
    assert not content_hash_matches(p, None)
    assert not content_hash_matches(p, "0" * 16)
