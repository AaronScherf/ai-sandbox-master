import json

import pytest

from core.indexer.index_card import save_shard
from tools.hub_vocabulary import impact, main

CONFIG = {"version": 1, "textbook_folders": ["textbooks"], "group_patterns": [r"^class_\d{4}$"],
          "names": {"problem_sets": {"kind": "category", "source": "seed"},
                    "processed_outputs": {"kind": "ignore", "source": "seed"}}}


def _hub(tmp_path):
    hub = tmp_path / "hub"
    hub.mkdir()
    (hub / "hub_config.json").write_text(json.dumps(CONFIG, indent=2) + "\n", encoding="utf-8")
    for rel in ("academic_notes/econ/class_2024/problem_sets/a.md", "academic_notes/econ/problem_sets/b.md",
                "academic_notes/micro/problem_sets/c.md", "academic_notes/econ/Odd Folder/d.md"):
        path = hub / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x", encoding="utf-8")
    return hub


def _config(hub):
    return json.loads((hub / "hub_config.json").read_text(encoding="utf-8"))


def test_propose_prints_json_and_writes_nothing(tmp_path, capsys):
    hub = _hub(tmp_path)
    before = sorted(p.name for p in hub.rglob("*"))
    raw = (hub / "hub_config.json").read_bytes()
    assert main(["propose", "--hub-root", str(hub)]) == 0
    out = json.loads(capsys.readouterr().out)
    assert {"category_candidates", "group_candidates", "ignore_candidates", "unclassified"} <= set(out)
    assert sorted(p.name for p in hub.rglob("*")) == before and (hub / "hub_config.json").read_bytes() == raw


def test_impact_lists_paths_whose_parse_changes_and_counts_cards(tmp_path):
    hub = _hub(tmp_path)
    save_shard(str(hub), "econ", [
        {"file_id": "1", "path": "academic_notes/econ/class_2024/problem_sets/a.md"},
        {"file_id": "2", "path": "academic_notes/econ/problem_sets/b.md"},
    ])
    result = impact(str(hub), hub / "hub_config.json", limit=10)
    assert result["changed"] == 1 and result["cards_changed"] == 1
    assert result["by_course"] == {"econ": 1}
    sample = result["samples"][0]
    assert sample["path"].endswith("class_2024/problem_sets/a.md")
    assert (sample["legacy_category"], sample["category"]) == ("class_2024", "problem_sets")


def test_confirm_writes_an_owner_entry_and_is_idempotent(tmp_path, capsys):
    hub = _hub(tmp_path)
    assert main(["confirm", "exam_kits", "category", "--hub-root", str(hub)]) == 0
    assert _config(hub)["names"]["exam_kits"] == {"kind": "category", "source": "owner"}
    raw = (hub / "hub_config.json").read_bytes()
    assert main(["confirm", "exam_kits", "category", "--hub-root", str(hub)]) == 0
    assert (hub / "hub_config.json").read_bytes() == raw


def test_confirm_refuses_to_change_an_earlier_answer_without_replace(tmp_path, capsys):
    hub = _hub(tmp_path)
    assert main(["confirm", "Exam Kits", "category", "--hub-root", str(hub)]) == 0
    assert main(["confirm", "exam kits", "group", "--hub-root", str(hub)]) == 1
    assert "category" in capsys.readouterr().err
    assert _config(hub)["names"]["Exam Kits"]["kind"] == "category"
    assert main(["confirm", "Exam Kits", "group", "--replace", "--hub-root", str(hub)]) == 0
    assert _config(hub)["names"]["Exam Kits"]["kind"] == "group"


def test_confirm_alias_needs_an_existing_category_target(tmp_path):
    hub = _hub(tmp_path)
    assert main(["confirm", "Problem Sets", "category", "--alias-of", "problem_sets", "--hub-root", str(hub)]) == 0
    assert _config(hub)["names"]["Problem Sets"]["alias_of"] == "problem_sets"
    assert main(["confirm", "Homeworks", "category", "--alias-of", "nonexistent", "--hub-root", str(hub)]) == 2
    assert main(["confirm", "Homeworks", "group", "--alias-of", "problem_sets", "--hub-root", str(hub)]) == 2


def test_confirm_rejects_an_unknown_kind_and_a_missing_config(tmp_path, capsys):
    hub = _hub(tmp_path)
    with pytest.raises(SystemExit) as exc:
        main(["confirm", "x", "weird", "--hub-root", str(hub)])
    assert exc.value.code == 2
    bare = tmp_path / "bare"
    bare.mkdir()
    assert main(["confirm", "x", "category", "--hub-root", str(bare)]) == 2
    assert "hub_config.json" in capsys.readouterr().err
