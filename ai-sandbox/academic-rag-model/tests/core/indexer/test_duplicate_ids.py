"""Duplicate hub_id detection and repair (hub-path-resilience P4). tmp_path only; no model client."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

from core.indexer.duplicate_ids import find_duplicate_hub_ids, restamp_duplicates
from core.indexer.hub_identity import read_hub_id
from core.indexer.index_card import compute_content_hash, load_shard, save_shard
from core.indexer.reconcile import reconcile
from tests.core.indexer.hub_fixture import make_hub, write_note
from tools.corpus_health.report import ScanReport

LN = "academic_notes/econ/lecture_notes"
BODY_A = "# Regression\n\nOLS minimizes squared residuals.\n" * 3
BODY_B = "# Demand\n\nA different note about consumer demand.\n" * 3


@pytest.fixture(autouse=True)
def _no_model_client(monkeypatch):
    import core.env.gemini_utils as gemini_utils
    from google import genai

    def boom(*args, **kwargs):
        raise AssertionError("no model client may be constructed or called")

    monkeypatch.setattr(gemini_utils, "get_gemini_client", boom)
    monkeypatch.setattr(genai, "Client", boom)


def _digest(hub: Path) -> dict[str, str]:
    return {str(p.relative_to(hub)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(hub.rglob("*")) if p.is_file()}


def _card(hub: Path, rel: str, fid: str, **extra) -> dict:
    return {"file_id": fid, "path": rel, "course": "econ",
            "content_hash": compute_content_hash(str(hub / rel)), **extra}


def _dup_hub(tmp_path):
    hub = make_hub(tmp_path)
    write_note(hub, f"{LN}/a.md", {"hub_id": "dup000000001"}, BODY_A)
    write_note(hub, f"{LN}/b.md", {"hub_id": "dup000000001"}, BODY_B)
    write_note(hub, f"{LN}/c.md", {"hub_id": "uniq00000001"}, "# C\n\nOther.\n")
    save_shard(str(hub), "econ", [_card(hub, f"{LN}/a.md", "f1", hub_id="dup000000001"),
                                  _card(hub, f"{LN}/b.md", "f2", hub_id="dup000000001"),
                                  _card(hub, f"{LN}/c.md", "f3", hub_id="uniq00000001")])
    return hub


def test_two_files_same_id_reported(tmp_path):
    hub = _dup_hub(tmp_path)
    assert find_duplicate_hub_ids(str(hub)) == {"dup000000001": [f"{LN}/a.md", f"{LN}/b.md"]}


def test_derived_outputs_are_not_reported(tmp_path):
    hub = _dup_hub(tmp_path)
    write_note(hub, f"{LN}/a.rag.md", {"hub_id": "dup000000001"}, BODY_A)
    assert find_duplicate_hub_ids(str(hub))["dup000000001"] == [f"{LN}/a.md", f"{LN}/b.md"]


def test_two_cards_same_id_reported(tmp_path):
    hub = make_hub(tmp_path)
    write_note(hub, f"{LN}/a.md", {"hub_id": "aaaaaaaaaaaa"}, BODY_A)
    write_note(hub, f"{LN}/b.md", {"hub_id": "bbbbbbbbbbbb"}, BODY_B)
    save_shard(str(hub), "econ", [_card(hub, f"{LN}/a.md", "f1", hub_id="cccccccccccc"),
                                  _card(hub, f"{LN}/b.md", "f2", hub_id="cccccccccccc")])
    assert find_duplicate_hub_ids(str(hub)) == {"cccccccccccc": [f"{LN}/a.md", f"{LN}/b.md"]}


def test_dry_run_writes_nothing(tmp_path):
    hub = _dup_hub(tmp_path)
    before = _digest(hub)
    [(path, old, new)] = restamp_duplicates(str(hub), {}, apply=False)
    assert old == "dup000000001" and new != old and path in (f"{LN}/a.md", f"{LN}/b.md")
    assert _digest(hub) == before


def test_apply_restamps_only_the_loser_and_updates_its_card(tmp_path):
    hub = _dup_hub(tmp_path)
    c_before = (hub / LN / "c.md").read_bytes()
    a_before = (hub / LN / "a.md").read_bytes()
    [(path, old, new)] = restamp_duplicates(str(hub), {"dup000000001": f"{LN}/a.md"}, apply=True)
    assert path == f"{LN}/b.md"
    assert (hub / LN / "a.md").read_bytes() == a_before
    assert (hub / LN / "c.md").read_bytes() == c_before
    assert read_hub_id(str(hub / path)) == new != old
    cards = {c["path"]: c for c in load_shard(str(hub), "econ")}
    assert cards[path]["hub_id"] == new
    assert cards[path]["content_hash"] == compute_content_hash(str(hub / path))
    assert cards[f"{LN}/a.md"]["hub_id"] == old
    assert find_duplicate_hub_ids(str(hub)) == {}


def test_default_keeper_is_the_file_its_card_points_at(tmp_path):
    hub = make_hub(tmp_path)
    write_note(hub, f"{LN}/a.md", {"hub_id": "dup000000001"}, BODY_A)
    write_note(hub, f"{LN}/b.md", {"hub_id": "dup000000001"}, BODY_B)
    save_shard(str(hub), "econ", [_card(hub, f"{LN}/b.md", "f2", hub_id="dup000000001")])
    [(path, _, _)] = restamp_duplicates(str(hub), {}, apply=False)
    assert path == f"{LN}/a.md"


def test_move_with_duplicate_id_is_ambiguous_not_moved(tmp_path):
    """Documents current reconcile behaviour: safe, never silently picks a duplicate."""
    hub = make_hub(tmp_path)
    write_note(hub, f"{LN}/a.md", {"hub_id": "dup000000001"}, BODY_A)
    write_note(hub, f"{LN}/b.md", {"hub_id": "dup000000001"}, BODY_B)
    save_shard(str(hub), "econ", [_card(hub, f"{LN}/a.md", "f1", hub_id="dup000000001")])
    os.replace(hub / LN / "a.md", hub / LN / "a_renamed.md")
    diffs = reconcile(str(hub))
    assert diffs and all(d.kind == "ambiguous" for d in diffs)
    assert not any(d.kind == "moved" for d in diffs)


def test_duplicate_reported_in_scan_text(tmp_path):
    from tools.corpus_health.duplicates import duplicate_findings

    hub = _dup_hub(tmp_path)
    findings = duplicate_findings(str(hub))
    assert [f.kind for f in findings] == ["duplicate_hub_id"]
    text = ScanReport(findings=findings).to_text()
    assert "duplicate_hub_id" in text and "dup000000001" in text and f"{LN}/b.md" in text


def test_cli_fix_duplicates_dry_run_then_apply(tmp_path, capsys, monkeypatch):
    import contextlib
    import tools.write_hub_ids as w

    hub = _dup_hub(tmp_path)
    monkeypatch.setattr(w, "corpus_write_lock", lambda *a, **k: contextlib.nullcontext())
    before = _digest(hub)
    monkeypatch.setattr("sys.argv", ["x", "--hub-root", str(hub), "--fix-duplicates"])
    w.main()
    assert f"{LN}/b.md: dup000000001 ->" in capsys.readouterr().out
    assert _digest(hub) == before
    monkeypatch.setattr("sys.argv", ["x", "--hub-root", str(hub), "--fix-duplicates", "--apply"])
    w.main()
    assert find_duplicate_hub_ids(str(hub)) == {}


def test_first_commit_lookup_uses_hardened_git(tmp_path, monkeypatch):
    import subprocess
    from core.indexer import duplicate_ids, reconcile_git

    calls = []

    def fake_run(cmd, **kwargs):
        calls.append((cmd, kwargs["env"]))
        out = str(tmp_path).encode() if "rev-parse" in cmd else b"100\n"
        return subprocess.CompletedProcess(cmd, 0, stdout=out, stderr=b"")

    monkeypatch.setattr(reconcile_git.subprocess, "run", fake_run)
    monkeypatch.setattr(reconcile_git.shutil, "which", lambda _: "git")
    monkeypatch.setenv("GIT_EXTERNAL_DIFF", "evil")
    assert duplicate_ids._first_commit_time(str(tmp_path), "academic_notes/econ/a.md") == 100.0
    assert calls
    for cmd, env in calls:
        assert "core.fsmonitor=false" in cmd and f"core.hooksPath={os.devnull}" in cmd
        assert "GIT_EXTERNAL_DIFF" not in env and env["GIT_OPTIONAL_LOCKS"] == "0"
    log = [c for c, _ in calls if "log" in c][0]
    assert "--no-show-signature" in log and "--no-ext-diff" in log
    assert log[-2:] == ["--", ":(literal)academic_notes/econ/a.md"]


def test_first_commit_time_cross_drive_relpath_falls_back_to_none(tmp_path, monkeypatch):
    from core.indexer import duplicate_ids, reconcile_git

    monkeypatch.setattr(reconcile_git, "_git", lambda *a, **k: str(tmp_path))

    def no_relpath(*a, **k):
        raise ValueError("path is on mount 'C:', start on mount 'D:'")

    monkeypatch.setattr(duplicate_ids.os.path, "relpath", no_relpath)
    assert duplicate_ids._first_commit_time(str(tmp_path), "a.md") is None


def test_first_commit_time_pathspec_is_literal(tmp_path, monkeypatch):
    from core.indexer import duplicate_ids
    from tests.tools.git_fixture import git

    git(tmp_path, "init", "-q")
    for name, when in (("a.md", "1000000000"), ("[ab].md", "1100000000")):
        (tmp_path / name).write_text(name, encoding="utf-8")
        git(tmp_path, "add", "--", f":(literal){name}")
        monkeypatch.setenv("GIT_COMMITTER_DATE", f"{when} +0000")
        monkeypatch.setenv("GIT_AUTHOR_DATE", f"{when} +0000")
        git(tmp_path, "commit", "-q", "-m", name)
    # an unescaped "[ab].md" would also match a.md and report its older commit
    assert duplicate_ids._first_commit_time(str(tmp_path), "[ab].md") == 1100000000.0


def test_git_ordered_keeper_oldest_first_commit_wins(tmp_path):
    from tests.tools.git_fixture import git

    hub = make_hub(tmp_path)
    git(hub, "init", "-q", "-b", "main")
    env = {"GIT_COMMITTER_DATE": "2020-01-01T00:00:00", "GIT_AUTHOR_DATE": "2020-01-01T00:00:00"}
    import subprocess
    write_note(hub, f"{LN}/z_old.md", {"hub_id": "dup000000001"}, BODY_A)
    git(hub, "add", ".")
    subprocess.run(["git", "-c", "user.name=T", "-c", "user.email=t@e.x", "commit", "-q", "-m", "old"],
                   cwd=hub, env={**os.environ, **env}, check=True)
    write_note(hub, f"{LN}/a_new.md", {"hub_id": "dup000000001"}, BODY_B)
    git(hub, "add", ".")
    git(hub, "-c", "commit.gpgsign=false", "commit", "-q", "-m", "new")
    [(path, _, _)] = restamp_duplicates(str(hub), {}, apply=False)
    assert path == f"{LN}/a_new.md"  # z_old is oldest, so it keeps the id (lexicographic order would pick a_new)


def test_interrupted_apply_is_self_healing(tmp_path, monkeypatch):
    from core.indexer import duplicate_ids

    hub = make_hub(tmp_path)
    for name in "abc":
        write_note(hub, f"{LN}/{name}.md", {"hub_id": "dup000000001"}, BODY_A + name)
    save_shard(str(hub), "econ", [_card(hub, f"{LN}/{n}.md", f"f{n}", hub_id="dup000000001") for n in "abc"])
    real, count = duplicate_ids.replace_hub_id, {"n": 0}

    def flaky(path):
        count["n"] += 1
        if count["n"] == 2:
            raise OSError("disk")
        return real(path)

    monkeypatch.setattr(duplicate_ids, "replace_hub_id", flaky)
    keep = {"dup000000001": f"{LN}/a.md"}
    with pytest.raises(OSError):
        restamp_duplicates(str(hub), keep, apply=True)
    cards = {c["path"]: c for c in load_shard(str(hub), "econ")}
    assert cards[f"{LN}/b.md"]["hub_id"] == read_hub_id(str(hub / LN / "b.md")) != "dup000000001"
    assert cards[f"{LN}/c.md"]["hub_id"] == "dup000000001"
    monkeypatch.setattr(duplicate_ids, "replace_hub_id", real)
    restamp_duplicates(str(hub), keep, apply=True)
    assert find_duplicate_hub_ids(str(hub)) == {}


def test_dry_run_and_apply_report_the_same_set_and_skip_missing_files(tmp_path):
    hub = _dup_hub(tmp_path)
    save_shard(str(hub), "econ", load_shard(str(hub), "econ")
               + [{"file_id": "f9", "path": f"{LN}/gone.md", "course": "econ", "hub_id": "dup000000001"}])
    keep = {"dup000000001": f"{LN}/a.md"}
    dry = restamp_duplicates(str(hub), keep, apply=False)
    applied = restamp_duplicates(str(hub), keep, apply=True)
    assert [p for p, _, _ in dry] == [p for p, _, _ in applied] == [f"{LN}/b.md"]


def test_card_only_duplicate_stamps_unstamped_file_and_hash_stays_valid(tmp_path):
    hub = make_hub(tmp_path)
    write_note(hub, f"{LN}/a.md", {"hub_id": "aaaaaaaaaaaa"}, BODY_A)
    write_note(hub, f"{LN}/b.md", {"title": "b"}, BODY_B)
    save_shard(str(hub), "econ", [_card(hub, f"{LN}/a.md", "f1", hub_id="cccccccccccc"),
                                  _card(hub, f"{LN}/b.md", "f2", hub_id="cccccccccccc")])
    [(path, _, new)] = restamp_duplicates(str(hub), {"cccccccccccc": f"{LN}/a.md"}, apply=True)
    card = {c["path"]: c for c in load_shard(str(hub), "econ")}[path]
    assert card["hub_id"] == new == read_hub_id(str(hub / path))
    assert card["content_hash"] == compute_content_hash(str(hub / path))  # stamping is hash-neutral


def test_keep_not_among_holders_raises(tmp_path):
    hub = _dup_hub(tmp_path)
    with pytest.raises(ValueError):
        restamp_duplicates(str(hub), {"dup000000001": f"{LN}/c.md"}, apply=False)


def _cli_config(tmp_path, hub):
    import json
    cfg = tmp_path / "cfg.json"
    cfg.write_text(json.dumps({"version": 1, "academic_hub_root": str(hub), "academic_notes_root": None,
                               "required_roots": [], "markdown_policies": []}), encoding="utf-8")
    return cfg


def test_scan_cli_reports_duplicate_and_clears_after_fix(tmp_path, capsys):
    from tools.corpus_health.cli import main

    hub = _dup_hub(tmp_path)
    cfg, state = _cli_config(tmp_path, hub), tmp_path / "state"
    main(["scan", "--config", str(cfg), "--state-dir", str(state)])
    assert "duplicate_hub_id" in capsys.readouterr().out
    main(["scan", "--config", str(cfg), "--no-state"])
    assert "duplicate_hub_id" in capsys.readouterr().out
    restamp_duplicates(str(hub), {"dup000000001": f"{LN}/a.md"}, apply=True)
    main(["scan", "--config", str(cfg), "--state-dir", str(state)])
    assert "duplicate_hub_id" not in capsys.readouterr().out
    from tools.corpus_health.state import StateStore
    assert not [e for e in StateStore(state).pending() if e.get("finding", {}).get("kind") == "duplicate_hub_id"]
