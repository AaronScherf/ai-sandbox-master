"""Keep heavy and copyrighted files out of the public repo.

Rules (spec 2026-11-03-hub-binary-guard-design.md), applied to added or
modified paths only, never to deletions:

  R1  hub binaries: pdf/svg/png/jpg/jpeg/epub/docx/pptx under ai-sandbox/academic-hub/
  R2  any blob over 1 MB
  R3  textbook text: non-metadata files under textbooks*/ folders, and *.rag.md.bak

Callers: `land_branch` (authoritative), `.githooks/pre-commit`, and the CLI:

    python -m tools.guard_binaries --staged
    python -m tools.guard_binaries --range main...HEAD
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

HUB_PREFIX = "ai-sandbox/academic-hub/"
HUB_EXEMPT_PREFIX = "ai-sandbox/academic-hub/obsidian_styles/"
HUB_BINARY_EXTENSIONS = frozenset(
    {".pdf", ".svg", ".png", ".jpg", ".jpeg", ".epub", ".docx", ".pptx"}
)
SIZE_LIMIT = 1_000_000  # 1 MB
TEXTBOOK_DIRS = frozenset({"textbooks", "textbooks-and-papers"})
ALLOWLIST_PATH = Path(__file__).with_name("guard_binaries_allow.txt")
ALLOWLIST_REPO_PATH = "ai-sandbox/academic-rag-model/tools/guard_binaries_allow.txt"


@dataclass(frozen=True)
class Violation:
    rule: str
    path: str
    fix: str

    def __str__(self) -> str:
        return f"{self.rule}: {self.path} -- {self.fix}"


def _glob_to_regex(pattern: str) -> re.Pattern[str]:
    """`**` crosses folders, `*` and `?` do not."""
    out, i = [], 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    return re.compile("".join(out) + r"\Z")


def load_allowlist(path: Path = ALLOWLIST_PATH) -> list[re.Pattern[str]]:
    """One glob per line followed by `# reason`. A glob without a reason is an error."""
    if not path.exists():
        return []
    return parse_allowlist(path.read_text(encoding="utf-8"), path.name)


def parse_allowlist(text: str, name: str = "allowlist") -> list[re.Pattern[str]]:
    patterns: list[re.Pattern[str]] = []
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        glob, _, reason = line.partition("#")
        if not glob.strip() or not reason.strip():
            raise ValueError(f"{name}:{number}: every entry needs `glob  # reason`")
        if glob.strip().strip("/") in ("*", "**", "**/*") or glob.strip().startswith("**"):
            raise ValueError(f"{name}:{number}: glob `{glob.strip()}` is too broad")
        patterns.append(_glob_to_regex(glob.strip()))
    return patterns


def check_entries(
    entries: list[tuple[str, int]], allowlist: list[re.Pattern[str]] | None = None
) -> list[Violation]:
    """`entries` are (repo-relative posix path, size in bytes) for added/modified files."""
    allow = load_allowlist() if allowlist is None else allowlist
    found: list[Violation] = []
    for path, size in entries:
        if any(p.match(path) for p in allow):
            continue
        parts = PurePosixPath(path).parts
        lower = path.lower()
        suffix = PurePosixPath(lower).suffix
        if (
            lower.startswith(HUB_PREFIX)
            and not lower.startswith(HUB_EXEMPT_PREFIX)
            and suffix in HUB_BINARY_EXTENSIONS
        ):
            found.append(Violation(
                "R1", path,
                "hub binary; keep it in academic_resources/ untracked, or add it to "
                "tools/guard_binaries_allow.txt with a reason"))
        if size > SIZE_LIMIT:
            found.append(Violation(
                "R2", path,
                f"{size / 1e6:.1f} MB is over the 1 MB limit; keep it untracked, or add it "
                "to tools/guard_binaries_allow.txt with a reason"))
        if lower.endswith(".rag.md.bak"):
            found.append(Violation(
                "R3", path, "textbook conversion backup; keep it untracked or allowlist it"))
        elif any(p.lower() in TEXTBOOK_DIRS for p in parts[:-1]):
            index = next(i for i, p in enumerate(parts[:-1]) if p.lower() in TEXTBOOK_DIRS)
            rest = parts[index + 1:]
            if not (rest and rest[0] == "processed_outputs" and suffix == ".json"):
                found.append(Violation(
                    "R3", path,
                    "textbook source or text is copyrighted; only processed_outputs/**/*.json "
                    "metadata may be tracked (or allowlist it with a reason)"))
    return found


def _git(args: list[str], cwd: Path) -> str:
    proc = subprocess.run(
        ["git", "-c", "core.quotePath=false", *args],
        cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout


def _changed(cwd: Path, diff_args: list[str], blob_rev: str) -> list[tuple[str, int]]:
    """Added/copied/modified/renamed paths (new path for renames) with blob sizes."""
    out = _git(["diff", "--name-status", "--diff-filter=ACMR", "-z", *diff_args], cwd)
    fields = out.split("\0")
    entries: list[tuple[str, int]] = []
    i = 0
    while i < len(fields) and fields[i]:
        status = fields[i]
        step = 3 if status[0] in "RC" else 2
        path = fields[i + step - 1]
        i += step
        size = int(_git(["cat-file", "-s", f"{blob_rev}:{path}"], cwd).strip())
        entries.append((path, size))
    return entries


def check_staged(cwd: Path) -> list[Violation]:
    return check_entries(_changed(cwd, ["--cached"], ""))


def _base_allowlist(cwd: Path, base: str) -> list[re.Pattern[str]]:
    """Allowlist as it exists on `base` (main), so a branch cannot exempt itself."""
    try:
        text = _git(["show", f"{base}:{ALLOWLIST_REPO_PATH}"], cwd)
    except RuntimeError:
        return []
    return parse_allowlist(text, f"{base}:guard_binaries_allow.txt")


def check_range(cwd: Path, base: str, head: str = "HEAD") -> list[Violation]:
    """Check every commit in base..head (history is published too), against base's allowlist."""
    allow = _base_allowlist(cwd, base)
    seen: set[tuple[str, str]] = set()
    found: list[Violation] = []
    for commit in _git(["rev-list", "--reverse", "--no-merges", f"{base}..{head}"], cwd).split():
        for v in check_entries(_changed(cwd, [f"{commit}^", commit], commit), allow):
            if (v.rule, v.path) not in seen:
                seen.add((v.rule, v.path))
                found.append(v)
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--staged", action="store_true", help="check staged changes")
    group.add_argument("--range", metavar="BASE...HEAD", help="check a commit range")
    args = parser.parse_args(argv)
    cwd = Path.cwd()
    if args.staged:
        violations = check_staged(cwd)
    else:
        base, _, head = args.range.partition("...")
        violations = check_range(cwd, base, head or "HEAD")
    for violation in violations:
        print(violation, file=sys.stderr)
    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
