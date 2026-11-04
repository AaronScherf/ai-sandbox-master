import json
from pathlib import Path

import pytest

from tools import sync_folders


@pytest.fixture
def config(tmp_path):
    path = tmp_path / "hub_config.json"
    path.write_text(json.dumps({"names": {
        "professor_notes": {"kind": "category"}, "syllabus": {"kind": "category"},
        "Recitation Slides": {"kind": "category", "alias_of": "recitation_slides"},
        "recitation_slides": {"kind": "category"},
    }}), encoding="utf-8")
    return path


def _pdf(root, rel, size=10):
    path = Path(root, rel)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x" * size)
    return path


def _hub(tmp_path):
    hub = tmp_path / "hub"
    (hub / "academic_notes" / "econometrics" / "part_1" / "syllabus").mkdir(parents=True)
    _pdf(hub, "academic_resources/econometrics/part_1/syllabus/a.pdf")           # mirror exists
    _pdf(hub, "academic_resources/econometrics/part_2/professor_notes/p.pdf", 30)  # creatable
    _pdf(hub, "academic_resources/econometrics/part_2/professor_notes/q.pdf", 70)
    _pdf(hub, "academic_resources/econometrics/part_3/PS1/s.pdf")                # unconfirmed name
    _pdf(hub, "academic_resources/econometrics/part_2/textbooks/book.pdf")       # never touched
    return hub


def test_plan_lists_only_missing_confirmed_folders(tmp_path, config):
    plan = sync_folders.build_plan(str(_hub(tmp_path)), config)
    assert [(e["folder"], e["pdf_count"], e["total_bytes"]) for e in plan["folders"]] == [
        ("econometrics/part_2/professor_notes", 2, 100)]
    assert [e["folder"] for e in plan["unconfirmed"]] == ["econometrics/part_3/PS1"]
    assert plan["unconfirmed"][0]["unknown_names"] == ["PS1"]


def test_apply_is_dry_run_by_default_and_creates_only_approved(tmp_path, config):
    hub = _hub(tmp_path)
    approvals = {"folders": ["econometrics/part_2/professor_notes"], "max_pdf_mb": 5}
    target = hub / "academic_notes" / "econometrics" / "part_2" / "professor_notes"
    result = sync_folders.apply_approvals(str(hub), approvals, config)
    assert result["would_create"] == ["econometrics/part_2/professor_notes"] and not target.exists()
    sync_folders.apply_approvals(str(hub), approvals, config, create=True)
    assert target.is_dir() and list(target.iterdir()) == []
    assert not (hub / "academic_notes" / "econometrics" / "part_3").exists()


def test_apply_rejects_unconfirmed_or_unknown_keys_before_creating(tmp_path, config):
    hub = _hub(tmp_path)
    with pytest.raises(ValueError):
        sync_folders.apply_approvals(str(hub), {"folders": ["econometrics/part_2/professor_notes",
                                                            "econometrics/part_3/PS1"]}, config, create=True)
    assert not (hub / "academic_notes" / "econometrics" / "part_2").exists()


def test_apply_never_invents_a_course(tmp_path, config):
    hub = _hub(tmp_path)
    _pdf(hub, "academic_resources/newcourse/part_1/syllabus/z.pdf")
    result = sync_folders.apply_approvals(str(hub), {"folders": ["newcourse/part_1/syllabus"]}, config, create=True)
    assert result["skipped_no_course"] == ["newcourse/part_1/syllabus"]
    assert not (hub / "academic_notes" / "newcourse").exists()


def test_created_folder_makes_pdfs_discoverable_and_size_cap_holds_back_big_ones(tmp_path, config, monkeypatch):
    from pipelines.transcribe_notes.route_notes_transcribe import build_plan
    monkeypatch.setenv("ACADEMIC_HUB_CONFIG", str(config))
    hub = _hub(tmp_path)
    sync_folders.apply_approvals(str(hub), {"folders": ["econometrics/part_2/professor_notes"]}, config, create=True)
    names = lambda ps: sorted(Path(p).name for p in ps)
    assert "p.pdf" in names(build_plan(str(hub), courses=["econometrics"]).pdf_todo)
    capped = build_plan(str(hub), courses=["econometrics"], max_pdf_mb=0.00005)  # 50 bytes
    assert "q.pdf" in names(capped.pdf_oversize) and "q.pdf" not in names(capped.pdf_todo)
    assert "p.pdf" in names(capped.pdf_todo)


def test_cli_plan_and_apply(tmp_path, config, capsys):
    hub = _hub(tmp_path)
    approve = tmp_path / "approve.json"
    approve.write_text(json.dumps({"folders": ["econometrics/part_2/professor_notes"], "max_pdf_mb": 20}))
    assert sync_folders.main(["plan", "--hub-root", str(hub), "--config", str(config)]) == 0
    assert sync_folders.main(["apply", "--hub-root", str(hub), "--config", str(config), "--approve", str(approve)]) == 0
    out = capsys.readouterr().out
    assert "dry run" in out and "--max-pdf-mb 20" in out
    assert not (hub / "academic_notes" / "econometrics" / "part_2").exists()


def test_plan_flags_pdfs_nested_below_a_category_folder(tmp_path, config):
    hub = _hub(tmp_path)
    _pdf(hub, "academic_resources/econometrics/part_2/professor_notes/student answers/x.pdf")
    entry = sync_folders.build_plan(str(hub), config)["folders"][0]
    assert entry["pdf_count"] == 3 and entry["nested_pdf_count"] == 1 and entry["nested_dirs"] == ["student answers"]
