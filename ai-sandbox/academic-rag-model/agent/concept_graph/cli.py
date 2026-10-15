"""Command line for the concept graph: python -m agent.concept_graph.cli --graph-repo PATH <command>."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

from pydantic import ValidationError

from . import drivers, stages
from . import scaffold as scaffold_mod
from .build import BuildError, build
from .gh_issues import close_issue, fetch_review_issues
from .prompts import agent_prompt
from .retrieval import make_resilient_retriever
from .reviews import ReviewFile, apply_proposals, apply_review, archive_review
from .store import GraphDataError, GraphStore
from .validate import errors, validate
from .work import load_run, render_worklist


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

    to_close: list[int] = []  # closed only after proposals are written, so a failure leaves them open
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
            to_close.append(issue_number)
    if inputs:
        round_report = apply_proposals(store, [r for _, r, _ in inputs], args.today or dt.date.today().isoformat())
        if round_report.applied or round_report.conflicts or round_report.comments:
            print(f"proposals: {len(round_report.applied)} applied, {len(round_report.conflicts)} conflict(s), "
                  f"{len(round_report.comments)} comment(s)")
            for line in round_report.applied:
                print("   ", line)
            if round_report.conflicts:
                print(f"    conflicts need your decision: see {args.graph_repo / 'review-conflicts.md'}")
            if args.commit:
                _git_commit(args.graph_repo, "proposals")
    for number in to_close:
        close_issue(args.from_issues, number)
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


def _work_root(args) -> Path:
    if args.work_dir:
        return Path(args.work_dir)
    if args.hub_root:
        return Path(args.hub_root) / ".agent_work" / "concept_graph"
    raise ValueError("pass --work-dir (or --hub-root, which implies <hub-root>/.agent_work/concept_graph)")


def _default_retriever(args):
    if not args.hub_root or not args.course:
        raise ValueError("retrieval needs --hub-root and --course")
    return make_resilient_retriever(args.hub_root, args.course)


def _collect_run(args):
    store = GraphStore(args.graph_repo)
    retriever = None if args.stage == "seed" else args.retriever_factory(args)
    nodes, redo, top_k = args.node or None, args.redo, args.top_k
    if args.orphans:
        # a node with no edges at all: ask again with every candidate and a wider retrieval
        graph = store.read_all()
        linked = {end for e in graph.edges for end in (e.source, e.target, e.via)}
        nodes = [n.id for n in graph.nodes if n.id not in linked and n.explanation.strip()]
        if not nodes:
            return store, None
        redo, top_k = True, max(top_k, 10)
    run = drivers.collect(args.stage, store, retriever, _work_root(args), run_id=args.run_id, section=args.section,
                          nodes=nodes, redo=redo, top_k=top_k, hub_root=args.hub_root, course=args.course)
    return store, run


def _print_report(report: drivers.SubmitReport) -> None:
    for task_id in report.applied:
        print(f"applied {task_id}")
    for task_id, reasons in report.bounced.items():
        for reason in reasons:
            print(f"BOUNCED {task_id}: {reason}")
    for task_id, reason in report.skipped.items():
        print(f"skipped {task_id}: {reason}")
    print(f"{len(report.applied)} applied, {len(report.bounced)} bounced, {len(report.skipped)} skipped, "
          f"{len(report.untouched)} not filled in yet")


def _cmd_collect(args) -> int:
    _, run = _collect_run(args)
    if run is None:
        print("Nothing to do: no items need this stage right now.")
        return 0
    print(f"run {run.run_id}: {len(run.tasks)} card(s) in {run.root}")
    print(f"Fill each card's result block (see {run.root / 'worklist.md'}), then run: submit {run.run_id}")
    prompt = agent_prompt(run)
    (run.root / "PROMPT.md").write_text(prompt, encoding="utf-8", newline="\n")
    print(f"\nPrompt for the agent (also saved as {run.root / 'PROMPT.md'}):\n")
    print(prompt)
    return 0


def _cmd_submit(args) -> int:
    run = load_run(_work_root(args), args.run_id)
    _print_report(drivers.submit(run, GraphStore(args.graph_repo), args.agent_name))
    return 0


def _cmd_status(args) -> int:
    root = _work_root(args)
    if args.run_id:
        print(render_worklist(load_run(root, args.run_id)))
        return 0
    runs = sorted(p.parent.name for p in root.glob("*/manifest.json")) if root.is_dir() else []
    print("\n".join(runs) if runs else f"no runs under {root}")
    return 0


BOOTSTRAP = """\
Concept graph drafting: agent contract{run_line}
Work directory: {work}
{paths}
1. Open worklist.md. For each task listed as pending or bounced, open its card in the cards folder.
2. Read ## Instructions, ## Subject and ## Offered passages. Use only the offered passages as evidence.
3. Write ONLY the YAML mapping inside the ```yaml fence under ## Result. Do not edit any other part of the card,
   and do not edit any other file.
4. Write in your own words: 8 or more consecutive words shared with a passage is rejected. Cite only the
   (source, ref) pairs shown in the passage headers.
5. When the cards are done, run:
   python -m agent.concept_graph.cli --graph-repo "{repo}" submit {run_id} --work-dir "{work}" --agent-name YOUR-NAME
6. A card that bounces gets a ## Bounced section listing why. Fix only those cards, then run submit again.
Never copy source text, never edit the graph's data files directly, and never mark anything verified: a person does that.
"""


def _cmd_bootstrap(args) -> int:
    work = _work_root(args)
    run_id = args.run_id or "<run-id>"
    paths = (f"Cards: {work / run_id / 'cards'}\nWorklist: {work / run_id / 'worklist.md'}" if args.run_id
             else "(run `collect <stage>` first; it prints the run id)")
    print(BOOTSTRAP.format(run_line=f" (run {args.run_id})" if args.run_id else "", work=work, paths=paths,
                           repo=args.graph_repo, run_id=run_id))
    return 0


def _cmd_api(args) -> int:
    store, run = _collect_run(args)
    if run is None:
        print("Nothing to do: no items need this stage right now.")
        return 0
    report = drivers.api_run(args.stage, run, store, args.complete_factory(args), args.approve_cost, agent_name=args.model)
    print(f"run {run.run_id}")
    _print_report(report)
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

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--hub-root", help="the academic-hub folder (retrieval, outline, default work directory)")
    common.add_argument("--course", help="course folder name, e.g. microecon")
    common.add_argument("--work-dir", help="private folder for task cards (never inside the graph repo); "
                                           "default <hub-root>/.agent_work/concept_graph")
    staged = argparse.ArgumentParser(add_help=False)
    staged.add_argument("stage", choices=stages.STAGES)
    staged.add_argument("--section", help="only this course section id")
    staged.add_argument("--node", action="append", help="only this node id (repeatable)")
    staged.add_argument("--orphans", action="store_true",
                        help="only nodes that have no edges yet (implies --redo and at least --top-k 10)")
    staged.add_argument("--redo", action="store_true", help="regenerate proposed items that already have a draft")
    staged.add_argument("--top-k", type=int, default=6, help="passages retrieved per card")
    staged.add_argument("--run-id", help="name for this run (default: <stage>-<timestamp>)")
    sub.add_parser("collect", parents=[common, staged], help="write task cards for an agent to fill in")
    sm = sub.add_parser("submit", parents=[common], help="validate and apply the cards an agent has filled in")
    sm.add_argument("run_id")
    sm.add_argument("--agent-name", default="ide-agent", help="recorded as the drafter in each item's provenance")
    st = sub.add_parser("status", parents=[common], help="show a run's worklist, or list runs")
    st.add_argument("run_id", nargs="?")
    bs = sub.add_parser("bootstrap", parents=[common], help="print the contract an agent should follow")
    bs.add_argument("run_id", nargs="?")
    ap = sub.add_parser("api", parents=[common, staged], help="draft through the metered Gemini API (cost-gated)")
    ap.add_argument("--approve-cost", type=float, help="maximum dollars you approve; required above $1")
    ap.add_argument("--model", default="gemini-3.8-flash")
    return p


def main(argv: list[str] | None = None, *, retriever_factory=None, complete_factory=None) -> int:
    args = build_parser().parse_args(argv)
    args.graph_repo = Path(args.graph_repo)
    args.retriever_factory = retriever_factory or _default_retriever
    args.complete_factory = complete_factory or (lambda a: drivers.gemini_complete(a.model))
    handlers = {"validate": _cmd_validate, "build": _cmd_build, "apply-review": _cmd_apply_review,
                "scaffold": _cmd_scaffold, "collect": _cmd_collect, "submit": _cmd_submit, "status": _cmd_status,
                "bootstrap": _cmd_bootstrap, "api": _cmd_api}
    try:
        return handlers[args.cmd](args)
    except drivers.BudgetError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except (GraphDataError, BuildError, FileExistsError, FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
