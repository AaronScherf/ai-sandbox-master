import os

import pytest

from framed_explainer_helpers import MD_C, el, slide, stroke, write_scene
from pipelines.transcribe_notes.framed_explainer.scene import (
    SceneFormatError, classify, load_scene)


def _elements():
    return [
        slide("s1", 0, 0), slide("s2", 0, 900, file_id="b" * 40),
        el("e1", "image", 1000, 0, 950, 500, fileId=MD_C,
           customData={"markdownImage": {"schemaVersion": 1}}),
        stroke("k1", 10, 10), stroke("k2", 30, 30), stroke("k3", 50, 50),
        el("f1", "frame", -10, -10, 1000, 600),
        el("gone", "freedraw", 0, 0, 5, 5, isDeleted=True),
        el("r1", "rectangle", 0, 0, 5, 5),
    ]


def test_load_scene_decodes_compressed_json(tmp_path):
    p = write_scene(tmp_path / "a.excalidraw.md", _elements())
    scene = load_scene(p)
    assert len(scene.elements) == 9
    assert scene.registry["a" * 40] == "slide-1.png"
    assert scene.registry[MD_C] == "markdown-image"


def test_load_scene_sha1_is_line_ending_insensitive(tmp_path):
    a = load_scene(write_scene(tmp_path / "a.excalidraw.md", _elements()))
    b = load_scene(write_scene(tmp_path / "b.excalidraw.md", _elements(), newline="\r\n"))
    assert a.sha1 == b.sha1


def test_classify_buckets(tmp_path):
    scene = load_scene(write_scene(tmp_path / "a.excalidraw.md", _elements()))
    c = classify(scene)
    assert [e["id"] for e in c.slides] == ["s1", "s2"]
    assert [e["id"] for e in c.explanations] == ["e1"]
    assert sorted(e["id"] for e in c.ink) == ["k1", "k2", "k3"]
    assert [e["id"] for e in c.frames] == ["f1"]
    assert [e["id"] for e in c.other] == ["r1"]


def test_load_scene_never_writes(tmp_path):
    p = write_scene(tmp_path / "a.excalidraw.md", _elements())
    before = (open(p, "rb").read(), os.stat(p).st_mtime_ns)
    load_scene(p)
    assert (open(p, "rb").read(), os.stat(p).st_mtime_ns) == before


def test_scene_without_compressed_json_raises(tmp_path):
    p = tmp_path / "x.excalidraw.md"
    p.write_text("# nothing here\n", encoding="utf-8")
    with pytest.raises(SceneFormatError):
        load_scene(str(p))
