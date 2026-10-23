"""Publish a private graph's built page into a separate local site repository."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from .build import BuildResult, build
from .store import GraphStore


class PublishError(Exception):
    pass


@dataclass(frozen=True)
class PublishResult:
    graph_sha: str
    site_sha: str
    changed: bool
    push_command: str
    build_result: BuildResult


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
    if result.returncode:
        raise PublishError(f"git {args[0]} failed in {root}: {result.stderr.strip()}")
    return result.stdout.strip()


def _repo_root(path: Path, label: str) -> Path:
    if not path.is_dir():
        raise PublishError(f"{label} repo does not exist: {path}")
    root = Path(_git(path, "rev-parse", "--show-toplevel")).resolve()
    if str(root).casefold() != str(path.resolve()).casefold():
        raise PublishError(f"{label} path must be the Git repository root: {path}")
    return root


def _github_repo(remote: str) -> str | None:
    if remote.startswith("git@github.com:"):
        path = remote[len("git@github.com:"):]
    else:
        parsed = urlparse(remote)
        if parsed.scheme not in ("https", "ssh") or parsed.hostname != "github.com":
            return None
        if parsed.username not in (None, "git") or parsed.password or parsed.port or parsed.query or parsed.fragment:
            return None
        path = parsed.path.lstrip("/")
    path = path.removesuffix(".git")
    return path if re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", path) else None


def _copy_atomic(source: Path, target: Path) -> None:
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="wb", delete=False, dir=target.parent,
                                         prefix=f".{target.name}.", suffix=".tmp") as fh:
            temp_path = Path(fh.name)
            with source.open("rb") as original:
                shutil.copyfileobj(original, fh)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(temp_path, target)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def _powershell_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def publish(graph_repo: str | Path, site_repo: str | Path) -> PublishResult:
    graph = _repo_root(Path(graph_repo), "graph")
    site = _repo_root(Path(site_repo), "site")
    if graph == site:
        raise PublishError("graph and site must be separate Git repositories")
    if _git(graph, "status", "--porcelain", "--untracked-files=all", "--", "data", "config"):
        raise PublishError("graph data or config has uncommitted changes; commit them before publishing a graph SHA")
    graph_sha = _git(graph, "rev-parse", "HEAD")
    expected = GraphStore(graph).read_all().site.get("repo")
    actual = _github_repo(_git(site, "remote", "get-url", "origin"))
    if not expected or not actual or expected.casefold() != actual.casefold():
        raise PublishError(f"config/site.yaml repo {expected!r} does not match the site repo's GitHub origin remote")
    branch = _git(site, "branch", "--show-current")
    if not branch:
        raise PublishError("site repo must be on a branch before publishing")
    if _git(site, "status", "--porcelain", "--", "index.html"):
        raise PublishError("site index.html has uncommitted changes; resolve them before publishing")

    built = build(graph)
    destination = site / "index.html"
    push_command = f"git -C {_powershell_quote(str(site))} push origin {branch}"
    if destination.is_file() and destination.read_bytes() == built.index_html.read_bytes():
        return PublishResult(graph_sha, _git(site, "rev-parse", "HEAD"), False, push_command, built)
    _copy_atomic(built.index_html, destination)
    if destination.read_bytes() != built.index_html.read_bytes():
        raise PublishError(f"page copy failed post-write audit: {destination}")
    _git(site, "commit", "--only", "-q", "-m", f"publish: graph {graph_sha}", "--", "index.html")
    site_sha = _git(site, "rev-parse", "HEAD")
    if _git(site, "show", "--format=", "--name-only", "HEAD") != "index.html":
        raise PublishError(f"site commit {site_sha} includes unexpected paths")
    return PublishResult(graph_sha, site_sha, True, push_command, built)
