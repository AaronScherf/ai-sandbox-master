import json

from test_cm_classify import COURSE, N, build_course

from core.course_materials.cli import main


def run(capsys, hub, *args):
    code = main(["--hub-root", str(hub), "--course", COURSE, *args])
    return code, capsys.readouterr()


def test_classify_prints_counts_and_flagged_files_with_their_evidence(tmp_path, capsys):
    code, out = run(capsys, build_course(tmp_path), "classify")
    assert code == 0
    assert "demo: 7 materials" in out.out
    assert "instructor:" in out.out and "flagged (" in out.out
    assert "092126.md" in out.out and "path word 'professor'" in out.out


def test_flagged_prints_json_rows(tmp_path, capsys):
    hub = build_course(tmp_path)
    run(capsys, hub, "classify")
    code, out = run(capsys, hub, "flagged")
    rows = json.loads(out.out)
    assert code == 0 and any(r["path"].endswith("092126.md") for r in rows)
    assert set(rows[0]) == {"path", "role", "format", "offering", "book", "confidence", "evidence"}


def test_decide_records_and_bad_values_exit_one(tmp_path, capsys):
    hub = build_course(tmp_path)
    code, out = run(capsys, hub, "decide", f"{N}/professor_notes/processed_outputs/092126.md", "--role", "instructor")
    assert code == 0 and "recorded" in out.out
    _, out = run(capsys, hub, "flagged")
    assert not any(r["path"].endswith("092126.md") for r in json.loads(out.out))
    code, out = run(capsys, hub, "decide", "C:/elsewhere/x.md", "--role", "exam")
    assert code == 1 and "error:" in out.err
