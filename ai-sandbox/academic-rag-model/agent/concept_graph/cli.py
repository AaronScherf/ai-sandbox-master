"""Command line for the concept graph: python -m agent.concept_graph.cli --graph-repo PATH <command>."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

from pydantic import ValidationError

from . import scaffold as scaffold_mod
from .build import BuildError, build
from .gh_issues import close_issue, fetch_review_issues
from .reviews import ReviewFile, apply_review, archive_review
from .store import GraphDataError, GraphStore
from .validate import errors, validate


def _cmd_validate(args) -> int:
    graph = GraphStore(args.graph_repo).read_all()
    issues = validate(graph)
    for i in issues:
        print(f"{i.level.upper():7} [{i.code}] {i.message}")
    bad = errors(issues)
    print(f"{len(bad)} error(s), {len(issues) - len(bad)} warning(s)")
    return 1 if bad else 0


def _cmd_build(args) -> int:
    result = build(args.graph_repo)
    for w in result.warnings:
        print(f"WARNING [{w.code}] {w.message}")
    print(f"built {result.index_html} and {result.graph_json} (graph_version {result.graph_version})")
    return 0


def _git_commit(root: Path, who: str) -> None:
    paths = [p for p in ("data", "review-comments.md", "review-conflicts.md", "reviews") if (root / p).exists()]
    subprocess.run(["git", "-C", str(root), "add", "--", *paths], check=True, capture_output=True)
    done = subprocess.run(["git", "-C", str(root), "commit", "-q", "-m", f"review: apply {who}"], capture_output=True, text=True)
    if done.returncode != 0:
        print(f"note: nothing committed for {who} ({done.stdout.strip() or done.stderr.strip()})")


def _cmd_apply_review(args) -> int:
    store = GraphStore(args.graph_repo)
    today = args.today or dt.date.today().isoformat()
    inputs: list[tuple[str, ReviewFile, int | None]] = []
    failed = False
    for name in args.files:
        try:
            inputs.append((name, ReviewFile.model_validate(json.loads(Path(name).read_text(encoding="utf-8"))), None))
        except (OSError, ValueError, ValidationError) as exc:
            print(f"error: {name}: {exc}", file=sys.stderr)
            failed = True
    if args.from_issues:
        found, problems = fetch_review_issues(args.from_issues)
        inputs.extend((f"issue #{n}", review, n) for n, review in found)
        for p in problems:
            print(f"error: {p}", file=sys.stderr)
            failed = True

    for label, review, issue_number in inputs:
        report = apply_review(store, review, today)
        archive_review(args.graph_repo, review, today)
        print(f"{label} ({review.reviewer.name}): {len(report.applied)} applied, {len(report.conflicts)} conflict(s), "
              f"{len(report.skipped)} skipped, {len(report.comments)} comment(s)")
        for line in report.applied + report.skipped:
            print("   ", line)
        if report.conflicts:
            print(f"    conflicts need your decision: see {args.graph_repo / 'review-conflicts.md'}")
        if args.commit:
            _git_commit(args.graph_repo, review.reviewer.name)
        if args.close_applied and issue_number is not None:
            close_issue(args.from_issues, issue_number)
    return 1 if failed else 0


def _cmd_scaffold(args) -> int:
    created = scaffold_mod.scaffold(
        args.graph_repo, args.repo, args.holder, dt.date.today().year,
        with_sample=args.with_sample, contact=args.contact,
    )
    print(f"scaffolded {args.graph_repo}:")
    for rel in created:
        print("   ", rel)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="concept_graph", description=__doc__)
    p.add_argument("--graph-repo", required=True, help="path to the graph repo checkout")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("validate", help="check the graph data; exit 1 on errors")
    sub.add_parser("build", help="write build/graph.json and index.html")
    ar = sub.add_parser("apply-review", help="merge review files or GitHub review issues into the graph")
    ar.add_argument("files", nargs="*", help="review JSON files downloaded from the viewer")
    ar.add_argument("--from-issues", metavar="OWNER/REPO", help="also read open issues labelled 'review' via gh")
    ar.add_argument("--commit", action="store_true", help="commit the result in the graph repo, one commit per reviewer")
    ar.add_argument("--close-applied", action="store_true", help="close each GitHub issue after applying it")
    ar.add_argument("--today", help="override today's date (YYYY-MM-DD), for tests")
    sc = sub.add_parser("scaffold", help="create a new graph repo skeleton at --graph-repo")
    sc.add_argument("--repo", required=True, metavar="OWNER/NAME", help="the GitHub repository this graph will live in")
    sc.add_argument("--holder", required=True, help="copyright holder name for LICENSE-CODE")
    sc.add_argument("--with-sample", action="store_true", help="include the 17-node sample graph")
    sc.add_argument("--contact", help="takedown contact text; defaults to the repo's GitHub issues page")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    args.graph_repo = Path(args.graph_repo)
    handlers = {"validate": _cmd_validate, "build": _cmd_build, "apply-review": _cmd_apply_review,
                "scaffold": _cmd_scaffold}
    try:
        return handlers[args.cmd](args)
    except (GraphDataError, BuildError, FileExistsError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
