"""The git reads must not execute programs named by a nested repo's own config."""
from __future__ import annotations

import os
import subprocess

from core.indexer import reconcile_git
from core.indexer.reconcile_git import find_repo_roots


def test_every_git_call_is_hardened(tmp_path, monkeypatch):
    seen = {}

    def fake_run(cmd, **kwargs):
        seen["cmd"], seen["env"] = cmd, kwargs["env"]
        return subprocess.CompletedProcess(cmd, 0, stdout=b"", stderr=b"")

    monkeypatch.setattr(reconcile_git.subprocess, "run", fake_run)
    monkeypatch.setattr(reconcile_git.shutil, "which", lambda _: "git")
    monkeypatch.setenv("GIT_EXTERNAL_DIFF", "evil")
    reconcile_git._git(str(tmp_path), "diff", "-M", "HEAD")
    cmd = seen["cmd"]
    assert "core.fsmonitor=false" in cmd
    assert f"core.hooksPath={os.devnull}" in cmd
    assert "diff.external=" in cmd
    assert cmd[cmd.index("diff") + 1:cmd.index("diff") + 3] == ["--no-ext-diff", "--no-textconv"]
    assert "GIT_EXTERNAL_DIFF" not in seen["env"]


def test_non_diff_command_gets_no_driver_flags():
    assert "--no-ext-diff" not in reconcile_git._git_command(("rev-parse", "--show-prefix"))


def test_gitdir_pointer_outside_hub_is_not_a_repo_root(tmp_path):
    hub = tmp_path / "hub"
    (hub / "inside").mkdir(parents=True)
    (hub / "outside").mkdir()
    (hub / "real").mkdir()
    (hub / "real" / ".git").mkdir()
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (hub / "outside" / ".git").write_text(f"gitdir: {elsewhere}\n", encoding="utf-8")
    (hub / "inside" / ".git").write_text("gitdir: ../real/.git\n", encoding="utf-8")
    roots = find_repo_roots(str(hub))
    assert str(hub / "real") in roots
    assert str(hub / "inside") in roots
    assert str(hub / "outside") not in roots


def test_signature_display_is_disabled_for_log_and_show_only():
    assert "log.showSignature=false" in reconcile_git._git_command(("rev-parse",))
    for sub in ("log", "show"):
        assert "--no-show-signature" in reconcile_git._git_command((sub, "HEAD"))
    assert "--no-show-signature" not in reconcile_git._git_command(("diff", "HEAD"))
