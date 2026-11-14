import json
import os

from framed_explainer_helpers import el, slide, stroke, write_scene
from pipelines.transcribe_notes.framed_explainer.cli import main


def _scene(tmp_path):
    lec = tmp_path / "academic_notes" / "econometrics" / "part_2" / "lecture_notes"
    lec.mkdir(parents=True)
    return write_scene(lec / "Econometrics 2026-11-04 t.excalidraw.md", [
        slide("s1", 0, 0), el("f1", "frame", -10, -10, 2200, 700, name="001 Slide 1"),
        stroke("k1", 1000, 50), stroke("k2", 1040, 60)])


def _collect(tmp_path, capsys):
    code = main(["collect", "--scene", _scene(tmp_path), "--hub-root", str(tmp_path),
                 "--run-id", "r1"])
    out = capsys.readouterr().out
    run_dir = next(ln.split(": ", 1)[1] for ln in out.splitlines() if ln.startswith("run-dir: "))
    return code, run_dir


def test_collect_then_submit_roundtrip_exit_zero(tmp_path, capsys):
    code, run_dir = _collect(tmp_path, capsys)
    assert code == 0
    facts = json.load(open(os.path.join(run_dir, "facts.json"), encoding="utf-8"))
    result = {"schema": 1, "scene": facts["scene"], "scene_sha1": facts["scene_sha1"],
              "slides": [{"slide_id": "s1", "frame_id": "f1", "ink": [],
                          "card": {"paragraphs": ["One.", "Two."], "status": "ok", "reason": None}}],
              "sections": []}
    with open(os.path.join(run_dir, "result.json"), "w", encoding="utf-8") as f:
        json.dump(result, f)
    assert main(["submit", "--run-dir", run_dir]) == 0
    assert "fallback_nearest" in capsys.readouterr().out
    assert main(["status", "--run-dir", run_dir]) == 0
    assert "submitted" in capsys.readouterr().out


def test_submit_invalid_result_exits_2_with_code(tmp_path, capsys):
    _, run_dir = _collect(tmp_path, capsys)
    with open(os.path.join(run_dir, "result.json"), "w", encoding="utf-8") as f:
        json.dump({"schema": 2}, f)
    assert main(["submit", "--run-dir", run_dir]) == 2
    assert "schema" in capsys.readouterr().err


def test_collect_missing_scene_exits_nonzero(tmp_path, capsys):
    assert main(["collect", "--scene", str(tmp_path / "nope.excalidraw.md"),
                 "--hub-root", str(tmp_path)]) == 1
    assert "not found" in capsys.readouterr().err
