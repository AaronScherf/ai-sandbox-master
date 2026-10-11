"""Read-only, offline website-sync audit (Git evidence foundation, M1 T2).

The T3 scanner will consume this module's pinned, independently verified Git
snapshots. Until then the CLI deliberately reports incomplete audit coverage.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

from tools.website_sync_registry import RegistryError, load_registry


PACKAGE_RELATIVE = Path("ai-sandbox/academic-rag-model")
DEFAULT_REGISTRY = PACKAGE_RELATIVE / "docs/trackers/subproject_registry.json"
GIT_TIMEOUT_SECONDS = 20


class AuditError(RuntimeError):
    """Input or Git evidence is unavailable, so audit coverage is incomplete."""


def _git_environment() -> dict[str, str]:
    # Git may inherit an index, object store, worktree, config injection, or a
    # remote transport from the caller. Never pass any inherited GIT_* setting.
    environment = {key: value for key, value in os.environ.items() if not key.upper().startswith("GIT_")}
    environment.update(
        GIT_OPTIONAL_LOCKS="0",
        GIT_NO_LAZY_FETCH="1",
        GIT_TERMINAL_PROMPT="0",
        GIT_CONFIG_NOSYSTEM="1",
        GIT_CONFIG_GLOBAL=os.devnull,
    )
    return environment


def _git(root: Path, *args: str) -> bytes:
    command = ["git", "--no-optional-locks", "--literal-pathspecs", "-C", str(root), *args]
    try:
        result = subprocess.run(
            command, env=_git_environment(), stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, timeout=GIT_TIMEOUT_SECONDS, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise AuditError(f"Git unavailable at {root}: {exc}") from exc
    if result.returncode:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise AuditError(f"Git failed at {root} ({' '.join(args)}): {detail or result.returncode}")
    return result.stdout


def _git_text(root: Path, *args: str) -> str:
    return _git(root, *args).decode("utf-8", errors="strict").strip()


def _resolve_input(value: str | Path) -> Path:
    return Path(value).expanduser().resolve(strict=False)


class GitRepository:
    """One selected checkout, with a pinned HEAD and per-path evidence cache."""

    def __init__(self, root: Path, *, kind: str):
        self.root = _resolve_input(root)
        if not self.root.is_dir():
            raise AuditError(f"{kind} root is not a directory: {self.root}")
        try:
            top = _resolve_input(_git_text(self.root, "rev-parse", "--show-toplevel"))
            common = _git_text(self.root, "rev-parse", "--path-format=absolute", "--git-common-dir")
            self.common_dir = _resolve_input(common)
            self.head = _git_text(self.root, "rev-parse", "--verify", "HEAD^{commit}")
            shallow = _git_text(self.root, "rev-parse", "--is-shallow-repository")
            if top != self.root:
                raise AuditError(f"{kind} root must be the exact Git toplevel: {self.root} (found {top})")
            if shallow != "false":
                raise AuditError(f"{kind} history is shallow or cannot be verified: {self.root}")
            _git(self.root, "cat-file", "-e", f"{self.head}^{{commit}}")
        except (UnicodeError, ValueError) as exc:
            raise AuditError(f"invalid {kind} Git identity: {exc}") from exc
        self._history: dict[str, int | None] = {}

    def _safe_path(self, relative: str) -> Path:
        # Registry validation rejects Git pathspec syntax and traversal. This
        # second check also protects callers using the evidence API directly.
        if (not relative or "\\" in relative or relative.startswith("/")
                or ":" in relative or any(part in {"", ".", ".."} for part in relative.split("/"))):
            raise AuditError(f"unsafe repository path: {relative!r}")
        target = self.root.joinpath(*relative.split("/")).resolve(strict=False)
        if not target.is_relative_to(self.root):
            raise AuditError(f"repository path escapes root: {relative!r}")
        return target

    def timestamp(self, relative: str) -> int | None:
        """Last commit time at this checkout's pinned HEAD; None means no history."""
        self._safe_path(relative)
        if relative not in self._history:
            value = _git_text(self.root, "log", "-1", "--format=%ct", self.head, "--", relative)
            if value and not value.isdecimal():
                raise AuditError(f"invalid Git timestamp for {relative}: {value!r}")
            self._history[relative] = int(value) if value else None
        return self._history[relative]

    def evidence(self, relative: str) -> dict[str, Any]:
        """Disk, index and committed-history evidence for one literal path."""
        tracked = _git(self.root, "ls-files", "-z", "--", relative).decode("utf-8").split("\0")
        untracked = _git(self.root, "ls-files", "--others", "--exclude-standard", "-z", "--", relative).decode("utf-8").split("\0")
        status = _git(self.root, "status", "--porcelain=v1", "-z", "--untracked-files=all", "--", relative)
        return self._build_evidence(relative, [p for p in tracked if p], [p for p in untracked if p], status)

    def _build_evidence(self, relative: str, tracked: list[str], untracked: list[str], status: bytes) -> dict[str, Any]:
        target = self._safe_path(relative)
        tracked = sorted(tracked)
        untracked = sorted(untracked)
        # Rename records contain a second NUL path. The raw byte fingerprint is
        # enough for change detection; T3 can decode it for reporting.
        digest = hashlib.sha256()
        for path in sorted(set(tracked + untracked + ([relative] if target.is_file() else []))):
            file = self._safe_path(path)
            digest.update(path.encode("utf-8"))
            digest.update(b"\0")
            if file.is_file():
                try:
                    digest.update(file.read_bytes())
                except OSError as exc:
                    raise AuditError(f"cannot read relevant input {file}: {exc}") from exc
            elif file.exists() and file.is_symlink():
                raise AuditError(f"unsupported relevant symlink: {file}")
            else:
                digest.update(b"<missing>")
            digest.update(b"\0")
        return {
            "path": relative,
            "exists": target.exists(),
            "tracked": tracked,
            "untracked": untracked,
            "dirty": bool(status),
            "status_fingerprint": hashlib.sha256(status).hexdigest(),
            "content_fingerprint": digest.hexdigest(),
            "timestamp": self.timestamp(relative),
        }

    def snapshot(self, paths: set[str]) -> dict[str, dict[str, Any]]:
        ordered = sorted(paths)
        for path in ordered:
            self._safe_path(path)
        if not ordered:
            return {}
        tracked = [part.decode("utf-8") for part in _git(self.root, "ls-files", "-z", "--", *ordered).split(b"\0") if part]
        untracked = [part.decode("utf-8") for part in _git(self.root, "ls-files", "--others", "--exclude-standard", "-z", "--", *ordered).split(b"\0") if part]
        raw_status = _git(self.root, "status", "--porcelain=v1", "-z", "--untracked-files=all", "--", *ordered)
        status_rows: list[tuple[str, bytes]] = []
        chunks = raw_status.split(b"\0")
        index = 0
        while index < len(chunks) and chunks[index]:
            row = chunks[index]
            if len(row) < 4 or row[2:3] != b" ":
                raise AuditError(f"invalid Git status record in {self.root}")
            name = row[3:].decode("utf-8")
            status_rows.append((name, row + b"\0"))
            if b"R" in row[:2] or b"C" in row[:2]:
                index += 1
                if index >= len(chunks) or not chunks[index]:
                    raise AuditError(f"incomplete Git rename record in {self.root}")
                status_rows.append((chunks[index].decode("utf-8"), row + b"\0" + chunks[index] + b"\0"))
            index += 1
        def applies(name: str, path: str) -> bool:
            return name == path or name.startswith(path + "/")
        return {
            path: self._build_evidence(
                path,
                [name for name in tracked if applies(name, path)],
                [name for name in untracked if applies(name, path)],
                b"".join(record for name, record in status_rows if applies(name, path)),
            )
            for path in ordered
        }

    def assert_unchanged(self, snapshot: dict[str, dict[str, Any]]) -> None:
        if _git_text(self.root, "rev-parse", "--verify", "HEAD^{commit}") != self.head:
            raise AuditError(f"HEAD changed during scan: {self.root}")
        current = self.snapshot(set(snapshot))
        for path, original in snapshot.items():
            if current[path] != original:
                raise AuditError(f"relevant input changed during scan: {self.root / path}")


def select_repositories(monorepo_root: Path, website_root: Path) -> tuple[GitRepository, GitRepository]:
    monorepo = GitRepository(monorepo_root, kind="monorepo")
    website = GitRepository(website_root, kind="website")
    if not (monorepo.root / PACKAGE_RELATIVE / "tools/website_sync_registry.py").is_file():
        raise AuditError(f"monorepo root lacks expected academic-rag-model package: {monorepo.root}")
    if not (website.root / "content/projects").is_dir():
        raise AuditError(f"website root lacks content/projects: {website.root}")
    if monorepo.common_dir == website.common_dir:
        raise AuditError("monorepo and website must have distinct Git common directories")
    return monorepo, website


def _registry_paths(registry: dict[str, Any]) -> tuple[set[str], set[str]]:
    monorepo: set[str] = set()
    website: set[str] = set()
    for entry in registry["subprojects"].values():
        monorepo.update(entry["code_paths"])
        if entry["readme_path"]:
            monorepo.add(entry["readme_path"])
        monorepo.update(row["path"] for row in entry["status_docs"])
        for revision in entry["lifecycle_records"].values():
            for field in ("specs", "implementation_plans", "test_paths"):
                monorepo.update(revision[field])
        if entry["website"]["page"]:
            website.add(entry["website"]["page"])
    return monorepo, website


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read-only local website-sync audit")
    parser.add_argument("--website-root", type=Path, required=True)
    parser.add_argument("--monorepo-root", type=Path)
    parser.add_argument("--registry", type=Path)
    parser.add_argument("--format", choices=("text", "json", "markdown"), default="text")
    parser.add_argument("--tolerance-seconds", type=int, default=3600)
    parser.add_argument("--strict", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.tolerance_seconds < 0:
        print("tolerance-seconds must be nonnegative", file=sys.stderr)
        return 2
    monorepo_root = _resolve_input(args.monorepo_root or Path(__file__).resolve().parents[3])
    website_root = _resolve_input(args.website_root)
    registry_path = _resolve_input(args.registry or monorepo_root / DEFAULT_REGISTRY)
    try:
        monorepo, website = select_repositories(monorepo_root, website_root)
        registry = load_registry(registry_path, monorepo.root, website.root)
        monorepo_paths, website_paths = _registry_paths(registry)
        monorepo_paths.add(registry_path.relative_to(monorepo.root).as_posix())
        monorepo_paths.add(registry_path.with_name("subproject_registry.schema.json").relative_to(monorepo.root).as_posix())
        before_m = monorepo.snapshot(monorepo_paths)
        before_w = website.snapshot(website_paths)
        monorepo.assert_unchanged(before_m)
        website.assert_unchanged(before_w)
        result = {
            "report_version": "0.1.0-t2",
            "coverage_complete": False,
            "reason": "T3 discovery, metadata and findings are not implemented",
            "monorepo_root": str(monorepo.root),
            "website_root": str(website.root),
            "monorepo_head": monorepo.head,
            "website_head": website.head,
            "monorepo_paths": len(before_m),
            "website_paths": len(before_w),
            "relevant_dirty_paths": sum(row["dirty"] for row in before_m.values()) + sum(row["dirty"] for row in before_w.values()),
        }
    except (AuditError, RegistryError, OSError, ValueError, UnicodeError) as exc:
        result = {"report_version": "0.1.0-t2", "coverage_complete": False, "error": str(exc)}
    if args.format == "json":
        print(json.dumps(result, sort_keys=True))
    elif args.format == "markdown":
        print("# Website sync audit\n\nCoverage: incomplete\n\n" + result.get("error", result.get("reason", "")))
    else:
        print("Website sync audit: incomplete — " + result.get("error", result.get("reason", "")))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
