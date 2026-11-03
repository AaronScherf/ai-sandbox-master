import json
import re

from core.indexer.hub_identity import new_hub_id, read_hub_id, write_hub_id
from core.indexer.index_card import compute_content_hash


def _w(tmp_path, name, data: bytes):
    p = tmp_path / name
    p.write_bytes(data)
    return str(p)


def test_new_hub_id_shape():
    assert re.fullmatch(r"[0-9a-f]{12}", new_hub_id())


def test_write_then_read_roundtrip(tmp_path):
    p = _w(tmp_path, "a.md", b"---\ntitle: A\n---\nbody\n")
    assert read_hub_id(p) is None
    hid = write_hub_id(p)
    assert read_hub_id(p) == hid
    assert write_hub_id(p, "ffffffffffff") == hid  # explicit id does not overwrite
    assert read_hub_id(p) == hid


def test_explicit_id_used(tmp_path):
    p = _w(tmp_path, "a.md", b"---\ntitle: A\n---\nbody\n")
    assert write_hub_id(p, "abcabcabcabc") == "abcabcabcabc"


def test_second_write_keeps_id(tmp_path):
    p = _w(tmp_path, "a.md", b"---\ntitle: A\n---\nbody\n")
    first = write_hub_id(p)
    before = open(p, "rb").read()
    assert write_hub_id(p) == first
    assert open(p, "rb").read() == before


def test_crlf_and_bom_preserved(tmp_path):
    orig = b"\xef\xbb\xbf---\r\ntitle: A\r\n---\r\nbody\r\n"
    p = _w(tmp_path, "a.md", orig)
    hid = write_hub_id(p)
    new = open(p, "rb").read()
    assert new.startswith(b"\xef\xbb\xbf---\r\n")
    assert new.count(b"\n") == orig.count(b"\n") + 1
    assert new.count(b"\r\n") == new.count(b"\n")
    assert f"hub_id: {hid}\r\n".encode() in new
    assert new.replace(f"hub_id: {hid}\r\n".encode(), b"") == orig


def test_no_frontmatter_gets_block(tmp_path):
    p = _w(tmp_path, "a.md", b"just body\n")
    hid = write_hub_id(p)
    assert open(p, "rb").read() == f"---\nhub_id: {hid}\n---\njust body\n".encode()
    assert read_hub_id(p) == hid


def test_excalidraw_md_uses_frontmatter(tmp_path):
    p = _w(tmp_path, "d.excalidraw.md", b"---\nexcalidraw-plugin: parsed\n---\nx\n")
    hid = write_hub_id(p)
    assert read_hub_id(p) == hid
    assert b"hub_id: " in open(p, "rb").read()


def test_excalidraw_json_gets_top_level_key(tmp_path):
    scene = {"type": "excalidraw", "version": 2, "elements": [], "appState": {"a": 1}}
    p = _w(tmp_path, "d.excalidraw", json.dumps(scene, indent=2).encode())
    hid = write_hub_id(p)
    data = json.load(open(p, encoding="utf-8"))
    assert data.pop("hub_id") == hid
    assert data == scene
    assert read_hub_id(p) == hid
    before = open(p, "rb").read()
    assert write_hub_id(p) == hid
    assert open(p, "rb").read() == before


def test_excalidraw_json_empty_object(tmp_path):
    p = _w(tmp_path, "d.excalidraw", b"{}")
    hid = write_hub_id(p)
    assert json.load(open(p, encoding="utf-8")) == {"hub_id": hid}


def test_hub_id_line_does_not_change_content_hash(tmp_path):
    p = _w(tmp_path, "a.md", b"---\ntitle: A\nsource_pdf: x.pdf\n---\nbody\n")
    before = compute_content_hash(p)
    write_hub_id(p)
    assert compute_content_hash(p) == before
