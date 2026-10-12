"""Read-only, offline website-sync audit over independent local Git checkouts."""

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


class InputChanged(AuditError):
    """A selected HEAD or relevant disk input changed during the audit."""


def _git_environment() -> dict[str, str]:
    # Git may inherit an index, object store, worktree, config injection, or a
    # remote transport from the caller. Never pass any inherited GIT_* setting.
    environment = {key: value for key, value in os.environ.items() if not key.upper().startswith("GIT_")}
    environment.update(
        GIT_OPTIONAL_LOCKS="0",
        GIT_NO_LAZY_FETCH="1",
        GIT_TERMINAL_PROMPT="0",
    )
    return environment


def _git(root: Path, *args: str) -> bytes:
    command = ["git", "--no-optional-locks", "--literal-pathspecs", "-C", str(root),
               "-c", "core.fsmonitor=false", *args]
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
        status = self._content_status([relative])
        return self._build_evidence(relative, [p for p in tracked if p], [p for p in untracked if p], status)

    def _content_status(self, paths: list[str]) -> bytes:
        # `status --porcelain` may report racily-clean files as modified when
        # optional locks prohibit an index refresh. Content diffs avoid that
        # false incomplete result without writing the selected checkout.
        status = bytearray()
        for label, flags in ((b"S", ("--cached",)), (b"U", ())):
            names = _git(self.root, "diff", "--no-ext-diff", "--no-textconv", "--no-renames",
                         "--name-only", "-z", *flags, "--", *paths)
            for name in names.split(b"\0"):
                if name:
                    status.extend(label + b" " + name + b"\0")
        names = _git(self.root, "ls-files", "--others", "--exclude-standard", "-z", "--", *paths)
        for name in names.split(b"\0"):
            if name:
                status.extend(b"? " + name + b"\0")
        return bytes(status)

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
        raw_status = self._content_status(ordered)
        status_rows: list[tuple[str, bytes]] = []
        for row in raw_status.split(b"\0"):
            if not row:
                continue
            if len(row) < 3 or row[1:2] != b" ":
                raise AuditError(f"invalid Git content-status record in {self.root}")
            status_rows.append((row[2:].decode("utf-8"), row + b"\0"))
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
            raise InputChanged(f"HEAD changed during scan: {self.root}")
        current = self.snapshot(set(snapshot))
        for path, original in snapshot.items():
            if current[path] != original:
                raise InputChanged(f"relevant input changed during scan: {self.root / path}")


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
    # Imported after the evidence classes are defined to avoid importing YAML
    # or scanner logic in low-level Git fixture tests.
    from tools.website_sync_scan import Scan

    try:
        if args.tolerance_seconds < 0:
            raise AuditError("tolerance-seconds must be nonnegative")
        monorepo_root = _resolve_input(args.monorepo_root or Path(__file__).resolve().parents[3])
        website_root = _resolve_input(args.website_root)
        registry_path = _resolve_input(args.registry or monorepo_root / DEFAULT_REGISTRY)
        monorepo, website = select_repositories(monorepo_root, website_root)
        registry = load_registry(registry_path, monorepo.root, website.root)
        result = Scan(registry, monorepo, website, registry_path, args.tolerance_seconds).run()
    except (AuditError, RegistryError, OSError, ValueError, UnicodeError) as exc:
        kind = "INPUT_CHANGED" if isinstance(exc, InputChanged) else "SCAN_ERROR"
        result = {"report_version": "1.0.0", "coverage_complete": False,
                  "error": str(exc), "findings": [{"component_id": "<scan>", "kind": kind,
                                                   "target": "<scan>", "severity": "error",
                                                   "blocks_strict": False, "detail": str(exc),
                                                   "evidence": {}, "input_fingerprints": {}}],
                  "counts": {"error": 1, "warning": 0, "info": 0}}
    if args.format == "json":
        print(json.dumps(result, sort_keys=True))
    elif args.format == "markdown":
        print("# Website sync audit\n\nCoverage: " + ("complete" if result["coverage_complete"] else "incomplete"))
        if "error" in result:
            print(f"\n**{result['findings'][0]['kind']}**: {result['error']}")
        else:
            print(f"\nFindings: {len(result['findings'])} "
                  f"(errors {result['counts']['error']}, warnings {result['counts']['warning']}, info {result['counts']['info']})")
            for row in result["findings"]:
                print(f"- **{row['severity']}** `{row['component_id']}` `{row['kind']}` `{row['target']}`: {row['detail']}")
    else:
        print("Website sync audit: " + ("complete" if result["coverage_complete"] else "incomplete"))
        if "error" in result:
            print(f"{result['findings'][0]['kind']}: {result['error']}")
        else:
            print(f"Findings: {len(result['findings'])} "
                  f"(errors {result['counts']['error']}, warnings {result['counts']['warning']}, info {result['counts']['info']})")
            for row in result["findings"]:
                print(f"{row['severity'].upper()} {row['component_id']} {row['kind']} {row['target']}: {row['detail']}")
    if not result["coverage_complete"]:
        return 2
    return 1 if args.strict and any(row["blocks_strict"] for row in result["findings"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
