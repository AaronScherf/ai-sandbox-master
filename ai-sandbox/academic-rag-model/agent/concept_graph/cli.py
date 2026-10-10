"""Command line for the concept graph: python -m agent.concept_graph.cli --graph-repo PATH <command>."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .build import BuildError, build
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


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="concept_graph", description=__doc__)
    p.add_argument("--graph-repo", required=True, help="path to the graph repo checkout")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("validate", help="check the graph data; exit 1 on errors")
    sub.add_parser("build", help="write build/graph.json and index.html")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    args.graph_repo = Path(args.graph_repo)
    handlers = {"validate": _cmd_validate, "build": _cmd_build}
    try:
        return handlers[args.cmd](args)
    except (GraphDataError, BuildError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
