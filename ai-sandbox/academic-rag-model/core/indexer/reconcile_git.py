"""Git rename evidence for the reconcile engine (hub-path-resilience P3).

Read-only: runs `git diff`, `git log`, `git show` and `git rev-parse`, never anything that writes the
index or the tree. Every failure (no git on PATH, not a repo, no commits yet) degrades to "no evidence".

The hub can be several nested repos (`academic_notes/` is its own repo), so callers pass each repo
directory and map the returned paths, which are relative to that directory, back to hub-relative.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys

_STATUS = re.compile(r"^[A-Z]\d*$")
_SKIP_DIRS = frozenset({".git", ".index", ".obsidian", ".trash", "node_modules"})
GIT_TIMEOUT_SECONDS = 120


# A nested repo under the hub is data, not trusted code: its own `.git/config` must not be able to run
# programs while we read history. `-c` on the command line overrides repo config, `--no-ext-diff` and
# `--no-textconv` disable configured diff drivers, and GIT_EXTERNAL_DIFF is dropped from the environment.
_HARDENING_CONFIG = ("-c", "core.quotePath=false", "-c", "core.fsmonitor=false",
                     "-c", f"core.hooksPath={os.devnull}", "-c", "diff.external=",
                     "-c", "log.showSignature=false")
_DIFF_COMMANDS = frozenset({"diff", "log", "show"})
_NO_DRIVER_FLAGS = ("--no-ext-diff", "--no-textconv")
_SIGNATURE_COMMANDS = frozenset({"log", "show"})  # `diff` has no signature display to disable


def _git_command(args: tuple[str, ...]) -> list[str]:
    if args and args[0] in _DIFF_COMMANDS:
        extra = _NO_DRIVER_FLAGS + (("--no-show-signature",) if args[0] in _SIGNATURE_COMMANDS else ())
        args = (args[0], *extra, *args[1:])
    return ["git", *_HARDENING_CONFIG, *args]


def _git(repo_root: str, *args: str) -> str | None:
    if shutil.which("git") is None:
        return None
    env = {k: v for k, v in os.environ.items() if k != "GIT_EXTERNAL_DIFF"}
    env["GIT_OPTIONAL_LOCKS"] = "0"  # a read must not take the index lock or refresh the index
    try:
        result = subprocess.run(_git_command(args), cwd=repo_root, env=env,
                                capture_output=True, timeout=GIT_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        print(f"WARNING: reconcile: `git {' '.join(args[:2])}` timed out after {GIT_TIMEOUT_SECONDS}s in "
              f"{repo_root}; git rename evidence from it is lost for this run", file=sys.stderr)
        return None
    except OSError:
        return None
    if result.returncode != 0:
        return None
    return result.stdout.decode("utf-8", "replace")


def _renames_in(output: str) -> list[tuple[str, str]]:
    """(old, new) pairs from `--name-status -z` output, in output order."""
    tokens = [t.lstrip("\n") for t in output.split("\0")]
    pairs: list[tuple[str, str]] = []
    i = 0
    while i < len(tokens):
        status = tokens[i]
        if not _STATUS.match(status):
            i += 1
            continue
        if status[0] in "RC":
            if status[0] == "R" and i + 2 < len(tokens):
                pairs.append((tokens[i + 1], tokens[i + 2]))
            i += 3
        else:
            i += 2
    return pairs


def git_renames(repo_root: str) -> dict[str, str]:
    """Map every old path to the path the file has now, relative to `repo_root`, `/`-separated.

    Committed renames come from `git log -M` over the whole history (oldest first, chained, so
    a->b then b->c gives a->c and b->c); renames staged but not committed come from
    `git diff -M --name-status HEAD` and are applied last. Both are limited to `repo_root` with the
    pathspec `-- .` (the hub can be a subdirectory of a much larger monorepo). `git log --follow` only walks backwards
    from a path that exists now, so it cannot say where a vanished card path went; the full-history
    rename log answers that in one call. A move done outside git and not yet staged shows as a delete
    plus an untracked file and is not reported (the hash and similarity passes cover it).
    """
    prefix = _git(repo_root, "rev-parse", "--show-prefix")
    if prefix is None:
        return {}
    prefix = prefix.strip()
    events: list[tuple[str, str]] = []
    log = _git(repo_root, "log", "--reverse", "-M", "--diff-filter=R", "--name-status", "-z", "--format=",
               "--", ".")
    if log:
        events += _renames_in(log)
    diff = _git(repo_root, "diff", "-M", "--diff-filter=R", "--name-status", "-z", "HEAD", "--", ".")
    if diff:
        events += _renames_in(diff)
    renames: dict[str, str] = {}
    for old, new in events:
        if not (old.startswith(prefix) and new.startswith(prefix)):
            continue
        old, new = old[len(prefix):], new[len(prefix):]
        for key, value in renames.items():
            if value == old:
                renames[key] = new
        renames[old] = new
    return {old: new for old, new in renames.items() if old != new}


def git_last_text(repo_root: str, rel_path: str) -> str | None:
    """The last committed text of `rel_path` (relative to `repo_root`), even if it is gone now."""
    text = _git(repo_root, "show", f"HEAD:./{rel_path}")
    if text is not None:
        return text
    last = _git(repo_root, "rev-list", "-1", "HEAD", "--", rel_path)
    if not last or not last.strip():
        return None
    return _git(repo_root, "show", f"{last.strip()}^:./{rel_path}")


def _git_pointer_stays_inside(dirpath: str, hub_root: str) -> bool:
    """A `.git` directory is always fine. A `.git` FILE is a `gitdir: <path>` pointer; accept it only when
    the target is inside the hub, so a nested folder cannot aim git at a repo (and config) elsewhere."""
    marker = os.path.join(dirpath, ".git")
    if os.path.isdir(marker):
        return True
    try:
        with open(marker, "r", encoding="utf-8", errors="replace") as f:
            first = f.readline().strip()
    except OSError:
        return False
    if not first.startswith("gitdir:"):
        return False
    target = os.path.realpath(os.path.join(dirpath, first[len("gitdir:"):].strip()))
    base = os.path.realpath(hub_root)
    return os.path.commonpath([target, base]) == base if os.path.splitdrive(target)[0] == os.path.splitdrive(base)[0] else False


def find_repo_roots(hub_root: str, max_depth: int = 2) -> list[str]:
    """`hub_root` plus every directory up to `max_depth` levels below it that is its own repo.

    A nested `.git` file whose `gitdir:` pointer leads outside the hub is not treated as a repo root."""
    roots = [hub_root]
    base_depth = hub_root.rstrip("\\/").count(os.sep)
    for dirpath, dirnames, _ in os.walk(hub_root):
        depth = dirpath.rstrip("\\/").count(os.sep) - base_depth
        if (dirpath != hub_root and os.path.exists(os.path.join(dirpath, ".git"))
                and _git_pointer_stays_inside(dirpath, hub_root)):
            roots.append(dirpath)
        if depth >= max_depth:
            dirnames[:] = []
        else:
            dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS and not d.startswith(".")]
    return roots
