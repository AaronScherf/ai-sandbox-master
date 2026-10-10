"""Command-line entry point for the first, read-only steering milestone."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

from tools.git_workflow import GitError, git_common_dir, run_git
from tools.corpus_health.state import StateError
from tools.project_steering.parser import parse_tracker
from tools.project_steering.report import make_report, publish_report, render_markdown
from tools.project_steering.identity import apply_ids, preview_ids
from tools.project_steering.ranking import rank
from tools.project_steering.state import DecisionStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Scan the project to-do tracker without model calls or tracker writes.")
    commands = parser.add_subparsers(dest="command", required=True)
    scan = commands.add_parser("scan", help="refresh a provisional, locally generated work view")
    scan.add_argument("--tracker", type=Path, required=True, help="absolute path to the Markdown to-do tracker")
    scan.add_argument("--state-dir", type=Path, required=True, help="local operational report directory")
    scan.add_argument("--format", choices=("json", "markdown"), default="markdown", help="stdout format")
    for name in ("preview-ids", "apply-ids"):
        command = commands.add_parser(name, help="preview or apply a one-time stable-ID migration")
        command.add_argument("--tracker", type=Path, required=True)
        if name == "apply-ids":
            command.add_argument("--source-sha256", required=True, help="hash printed by preview-ids")
    review = commands.add_parser("review", help="open the local owner-decision page")
    review.add_argument("--tracker", type=Path, required=True)
    review.add_argument("--state-dir", type=Path, required=True)
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
    if not args.tracker.is_absolute() or (hasattr(args, "state_dir") and not args.state_dir.is_absolute()):
        print("tracker and state-dir must be absolute paths", file=sys.stderr)
        return 2
    if hasattr(args, "state_dir") and not _state_dir_is_safe(args.tracker, args.state_dir):
        print("state-dir must be outside tracked source (the Git common directory is allowed)", file=sys.stderr)
        return 2
    if args.command in {"preview-ids", "apply-ids"}:
        try:
            if args.command == "preview-ids":
                preview = preview_ids(args.tracker.read_bytes().decode("utf-8"))
            else:
                preview = apply_ids(args.tracker, args.source_sha256)
        except (OSError, UnicodeError, ValueError, GitError) as exc:
            print(f"ID migration failed: {exc}", file=sys.stderr)
            return 2
        print(f"source_sha256: {preview.source_sha256}\nassigned: {preview.assigned}\nneeds_id: {list(preview.needs_id)}")
        print(preview.diff, end="")
        return 0 if not preview.needs_id else 2
    if args.command == "review":
        from tools.project_steering.review_server import serve_review
        try:
            serve_review(args.tracker, args.state_dir)
        except (OSError, ValueError, StateError) as exc:
            print(f"review failed: {exc}", file=sys.stderr)
            return 2
        return 0
    started = time.monotonic()
    try:
        source = args.tracker.read_bytes()
        parsed = parse_tracker(source.decode("utf-8-sig"))
        if args.tracker.read_bytes() != source:
            print("tracker changed during scan; no report published", file=sys.stderr)
            return 2
        state = DecisionStore(args.state_dir).reconcile(parsed.tasks)
        ranking = rank(parsed.tasks, state)
        report = make_report(
            parsed, tracker=args.tracker, source_hash=hashlib.sha256(source).hexdigest(),
            source_bytes=len(source), duration_seconds=time.monotonic() - started,
            ranking=ranking, revision=state["revision"],
        )
        markdown = render_markdown(report)
        latest = publish_report(args.state_dir, report, markdown)
    except (OSError, UnicodeError, ValueError, StateError) as exc:
        print(f"scan failed: {exc}", file=sys.stderr)
        return 2
    output = json.dumps({**report, "published": latest}, ensure_ascii=False, indent=2, sort_keys=True) if args.format == "json" else markdown
    print(output, end="" if output.endswith("\n") else "\n")
    return 0 if report["coverage_complete"] else 2
