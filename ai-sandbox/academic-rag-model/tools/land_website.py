"""Check and land an approved website branch without touching other worktrees."""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Callable

from tools import land_branch, reference_review
from tools.git_workflow import current_branch, dirty_files, is_ancestor, main_checkout
from tools.reference_checker import DEFAULT_CACHE, RegistryClient, shared_project_root

run_git = land_branch.run_git
LandingError = land_branch.LandingError
WEBSITE_REMOTE = re.compile(r"AaronScherf/AaronScherf\.github\.io(?:\.git)?/?$", re.I)


def _step(name: str, reason: str) -> LandingError:
    return LandingError(f"{name}: {reason}")


def _root(worktree: Path) -> Path:
    return Path(run_git(["rev-parse", "--show-toplevel"], worktree).strip())


def changed_pages(worktree: Path) -> list[str]:
    return land_branch.changed_research_notes(worktree, prefix="content/", base_ref="origin/main")


def _overlaps(worktree: Path, branch: str, own: set[str]) -> tuple[list[str], list[str]]:
    conflicts, retired = [], []
    refs = run_git(["for-each-ref", "--format=%(refname:short)", "refs/heads"], worktree).splitlines()
    for other in refs:
        if other in ("main", branch):
            continue
        if is_ancestor(worktree, other, "origin/main"):
            retired.append(other)
            continue
        paths = set(run_git(["diff", "--name-only", f"origin/main...{other}"], worktree).splitlines())
        shared = sorted(own & paths)
        if shared:
            conflicts.append(f"{other}: {', '.join(shared)}")
    return conflicts, retired


def _build(worktree: Path, main: Path, build_command: Callable[[Path, Path, dict], tuple[int, str]] | None) -> None:
    bin_dir = main / "node_modules" / ".bin"
    if not bin_dir.is_dir():
        raise _step("Hugo build", f"run npm install in {main}")
    env = os.environ.copy()
    env["PATH"] = str(bin_dir) + os.pathsep + env.get("PATH", "")
    with tempfile.TemporaryDirectory(prefix="website-gate-") as destination:
        output = Path(destination)
        if build_command:
            code, message = build_command(worktree, output, env)
        else:
            proc = subprocess.run(["hugo", "--minify", "--quiet", "--destination", str(output)],
                                  cwd=worktree, env=env, text=True, capture_output=True, errors="replace")
            code, message = proc.returncode, proc.stdout + proc.stderr
        if code:
            raise _step("Hugo build", f"exit {code}\n" + "\n".join(message.splitlines()[-20:]))


def check(worktree: Path, *, build_command=None, repo_root: Path | None = None,
          client_factory: Callable[[], object] | None = None) -> dict:
    started = time.perf_counter()
    worktree = _root(Path(worktree))
    branch = current_branch(worktree)
    try:
        origin = run_git(["remote", "get-url", "origin"], worktree).strip()
        if not WEBSITE_REMOTE.search(origin):
            raise _step("Repo", f"unexpected origin: {origin}")
        if not branch or branch == "main":
            raise _step("Repo", "branch must be a non-main branch")
        dirty = dirty_files(worktree)
        if dirty:
            raise _step("Repo", "dirty worktree: " + ", ".join(sorted(dirty)))
        try:
            run_git(["fetch", "origin"], worktree)
        except land_branch.GitError as exc:
            raise _step("Fast-forward", str(exc)) from exc
        if not is_ancestor(worktree, "origin/main", "HEAD"):
            raise _step("Fast-forward", "origin/main is not an ancestor of HEAD")
        own = set(run_git(["diff", "--name-only", "origin/main...HEAD"], worktree).splitlines())
        conflicts, retired = _overlaps(worktree, branch, own)
        if conflicts:
            raise _step("Overlaps", " | ".join(conflicts))
        main = main_checkout(worktree).path
        _build(worktree, main, build_command)
        pages = changed_pages(worktree)
        gate = reference_review.GateResult([])
        if pages:
            client = client_factory() if client_factory else RegistryClient(DEFAULT_CACHE, online=True)
            root = repo_root or shared_project_root().parents[1]
            note_keys = {(worktree / page).resolve():
                         "ai-sandbox/personal-website/AaronScherf.github.io/" + page for page in pages}
            gate = reference_review.gate([worktree / page for page in pages], client,
                                         repo_root=root, note_keys=note_keys)
            if gate.blocked:
                raise _step("Citation gate", str(land_branch.citation_gate_error(gate)))
        cid = land_branch.change_id(worktree, base_ref="origin/main")
        result = {"branch": branch, "sha": run_git(["rev-parse", "HEAD"], worktree).strip(),
                  "change_id": cid, "base": run_git(["rev-parse", "origin/main"], worktree).strip(),
                  "checks": "passed", "pages": pages, "retirement_candidates": retired,
                  "seconds": round(time.perf_counter() - started, 3)}
        land_branch.append_log(worktree, {"event": "check", **result})
        print(f"Branch: {branch}\nChange ID: {cid}\nPages: {', '.join(pages) or 'none'}")
        print("Overlaps: none")
        print("Retirement candidates: " + (", ".join(retired) or "none"))
        print(f"Check time: {result['seconds']}s")
        print(f"Nothing has been merged or pushed. Ask the user to approve change {cid}.")
        return result
    except (LandingError, land_branch.GitError) as exc:
        if not isinstance(exc, LandingError):
            exc = _step("Repo", str(exc))
        raise exc


def land(worktree: Path, cid: str, *, build_command=None, repo_root: Path | None = None,
         client_factory: Callable[[], object] | None = None) -> dict:
    worktree = _root(Path(worktree))
    branch = current_branch(worktree) or ""
    try:
        land_branch.approved_check(worktree, branch, cid)
        result = check(worktree, build_command=build_command, repo_root=repo_root,
                       client_factory=client_factory)
        if result["change_id"] != cid:
            raise LandingError(f"change ID changed; approved {cid}, current {result['change_id']}")
        main = main_checkout(worktree).path
        if current_branch(main) != "main":
            raise LandingError("website main checkout is not on main")
        if not is_ancestor(worktree, "main", branch):
            raise LandingError("main moved; rerun check and request approval")
        touched = set(run_git(["diff", "--name-only", "main", branch], worktree).splitlines())
        tracked = set(run_git(["diff", "--name-only", "HEAD"], main).splitlines())
        shared = sorted(touched & tracked)
        if shared:
            raise LandingError("main has tracked changes to merged paths: " + ", ".join(shared))
        run_git(["merge", "--ff-only", branch], main)
        try:
            run_git(["push", "origin", "main"], main)
        except land_branch.GitError as exc:
            raise LandingError(f"main was fast-forwarded locally but not pushed: {exc}") from exc
        land_branch.append_log(worktree, {"event": "land", "branch": branch,
                                          "change_id": cid, "result": "landed", "sha": result["sha"]})
        return result
    except (LandingError, land_branch.GitError) as exc:
        land_branch.append_log(worktree, {"event": "land", "branch": branch,
                                          "change_id": cid, "result": str(exc)})
        raise LandingError(str(exc)) from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    for name in ("check", "land"):
        sub = subs.add_parser(name)
        sub.add_argument("website_worktree", type=Path)
        if name == "land":
            sub.add_argument("--change-id", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "check":
            check(args.website_worktree)
        else:
            land(args.website_worktree, args.change_id)
        return 0
    except LandingError as exc:
        print(f"STOP: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
