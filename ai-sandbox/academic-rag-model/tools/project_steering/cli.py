"""Command-line entry point for the first, read-only steering milestone."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

from tools.git_workflow import GitError, git_common_dir, run_git
from tools.project_steering.parser import parse_tracker
from tools.project_steering.report import make_report, publish_report, render_markdown


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Scan the project to-do tracker without model calls or tracker writes.")
    commands = parser.add_subparsers(dest="command", required=True)
    scan = commands.add_parser("scan", help="refresh a provisional, locally generated work view")
    scan.add_argument("--tracker", type=Path, required=True, help="absolute path to the Markdown to-do tracker")
    scan.add_argument("--state-dir", type=Path, required=True, help="local operational report directory")
    scan.add_argument("--format", choices=("json", "markdown"), default="markdown", help="stdout format")
    return parser


def _state_dir_is_safe(tracker: Path, state_dir: Path) -> bool:
    tracker = tracker.resolve()
    state_dir = state_dir.resolve()
    if state_dir == tracker or state_dir == tracker.parent:
        return False
    if not tracker.parent.exists():
        return True  # Reading the missing tracker will produce the scan error.
    try:
        repo_root = Path(run_git(["rev-parse", "--show-toplevel"], tracker.parent).strip()).resolve()
        common_dir = git_common_dir(tracker.parent).resolve()
    except GitError:
        return True  # Standalone tracker outside a Git checkout.
    except OSError:
        return False  # Unable to establish a safe repository boundary.
    return not state_dir.is_relative_to(repo_root) or state_dir.is_relative_to(common_dir)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.tracker.is_absolute() or not args.state_dir.is_absolute():
        print("tracker and state-dir must be absolute paths", file=sys.stderr)
        return 2
    if not _state_dir_is_safe(args.tracker, args.state_dir):
        print("state-dir must be outside tracked source (the Git common directory is allowed)", file=sys.stderr)
        return 2
    started = time.monotonic()
    try:
        source = args.tracker.read_bytes()
        parsed = parse_tracker(source.decode("utf-8-sig"))
        if args.tracker.read_bytes() != source:
            print("tracker changed during scan; no report published", file=sys.stderr)
            return 2
        report = make_report(
            parsed, tracker=args.tracker, source_hash=hashlib.sha256(source).hexdigest(),
            source_bytes=len(source), duration_seconds=time.monotonic() - started,
        )
        markdown = render_markdown(report)
        latest = publish_report(args.state_dir, report, markdown)
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"scan failed: {exc}", file=sys.stderr)
        return 2
    output = json.dumps({**report, "published": latest}, ensure_ascii=False, indent=2, sort_keys=True) if args.format == "json" else markdown
    print(output, end="" if output.endswith("\n") else "\n")
    return 0 if report["coverage_complete"] else 2
