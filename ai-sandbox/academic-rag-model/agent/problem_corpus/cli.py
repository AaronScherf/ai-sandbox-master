"""Collect subscription task cards, submit them, or explicitly use the paid API."""
from __future__ import annotations

import argparse
from pathlib import Path

from core.agent_tasks.loop import BudgetError, api_run, collect_run, submit_run
from core.agent_tasks.work import load_run
from core.indexer.index_card import list_courses, load_shard

from . import stage
from .extractor import _DEFAULT_ROOT, _PROBLEM_BEARING_FOLDER_CATEGORIES, _folder_category_from_path, _single_root
from .store import corpus_dir, load_records

BOOTSTRAP = """Problem corpus subscription contract for run '{run}':

1. Open {work}/worklist.md and read the pending or bounced cards under {work}/cards/.
2. Read every offered passage in each card. Write only the YAML mapping requested by the card
   inside its ```yaml fence under ## Result. Do not edit the rest of the card.
3. Run: python -m agent.problem_corpus.extractor --root {root} submit {run}
4. Fix any bounced card in its existing YAML fence, then submit again. Stop when none remain.
"""


def _work_root(args, root: str) -> Path:
    return Path(args.work_root) if args.work_root else Path(root) / ".agent_work"


def _load(args, root: str):
    try:
        run = load_run(_work_root(args, root), args.run_id)
    except (FileNotFoundError, ValueError) as exc:
        print(f"cannot load run {args.run_id}: {exc}")
        return None
    if run.stage != stage.STAGE or Path(run.data["graph_repo"]).resolve() != Path(corpus_dir(root)).resolve():
        print(f"run {args.run_id} belongs to another stage or corpus root")
        return None
    return run


def _print_report(report) -> None:
    print(f"applied {len(report.applied)}, bounced {len(report.bounced)}, "
          f"skipped {len(report.skipped)}, untouched {len(report.untouched)}")
    for task_id, reasons in report.bounced.items():
        print(f"{task_id}: {'; '.join(reasons)}")
    for task_id, reason in report.skipped.items():
        print(f"skipped {task_id}: {reason}")


def cmd_collect(args, root: str) -> int:
    tasks, skipped = stage.make_tasks(stage.Target(root), course=args.course, file=args.file, redo=args.redo)
    for path, reason in skipped.items():
        print(f"skipped {path}: {reason}")
    try:
        run = collect_run(stage.STAGE, tasks, _work_root(args, root), corpus_dir(root),
                          run_id=args.run_id, repo_label="problem corpus")
    except (ValueError, FileExistsError) as exc:
        print(f"cannot create the run: {exc}")
        return 2
    if run is None:
        print("nothing to collect")
    else:
        print(f"collected {len(tasks)} card(s) in run {run.run_id}: {run.root}")
    return 0


def cmd_submit(args, root: str) -> int:
    run = _load(args, root)
    if run is None:
        return 2
    _print_report(submit_run(run, stage, stage.Target(root), args.agent_name,
                             target_label="problem corpus"))
    return 0


def cmd_status(args, root: str) -> int:
    cards = records = 0
    for course in list_courses(root):
        if args.course is not None and course != args.course:
            continue
        cards += sum(not c.get("orphaned") and not c.get("needs_indexing")
                     and _folder_category_from_path(c["path"]) in _PROBLEM_BEARING_FOLDER_CATEGORIES
                     for c in load_shard(root, course))
        records += len(load_records(root, course))
    print(f"eligible index cards: {cards}; stored problems: {records}")
    work = _work_root(args, root)
    for manifest in sorted(work.glob("*/manifest.json")) if work.is_dir() else []:
        try:
            run = load_run(work, manifest.parent.name)
        except (OSError, ValueError):
            continue
        if run.stage == stage.STAGE and Path(run.data["graph_repo"]).resolve() == Path(corpus_dir(root)).resolve():
            counts = {name: sum(t["status"] == name for t in run.tasks)
                      for name in ("pending", "bounced", "applied", "skipped")}
            print(f"run {run.run_id}: {counts}")
    return 0


def _gemini_complete(model: str):
    from core.env.gemini_utils import call_with_retries, get_gemini_client, load_dotenv_override

    load_dotenv_override()
    client = get_gemini_client("PAID_GEMINI_KEY")
    if client is None:
        raise SystemExit(1)
    return lambda prompt: call_with_retries(
        lambda: client.models.generate_content(model=model, contents=prompt, config={"temperature": 0}).text or "")


def cmd_api(args, root: str, complete=None) -> int:
    run = _load(args, root)
    if run is None:
        return 2
    try:
        report = api_run(run, stage, stage.Target(root), complete or _gemini_complete(args.model),
                         args.approve_cost, target_label="problem corpus")
    except BudgetError as exc:
        print(str(exc))
        return 2
    _print_report(report)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m agent.problem_corpus.extractor",
                                     description="Extract a structured problem corpus from indexed course content.")
    parser.add_argument("--root", action="append", default=None,
                        help=f"Corpus root (default: {_DEFAULT_ROOT}). Exactly one root.")
    parser.add_argument("--work-root", default=None, help="Private task-card directory (default: <root>/.agent_work).")
    sub = parser.add_subparsers(dest="command", required=True)
    collect = sub.add_parser("collect", help="Create subscription task cards; no API calls.")
    collect.add_argument("--course", default=None)
    collect.add_argument("--file", default=None)
    collect.add_argument("--run-id", default=None)
    collect.add_argument("--redo", action="store_true")
    submit = sub.add_parser("submit", help="Validate filled cards and store records.")
    submit.add_argument("run_id")
    submit.add_argument("--agent-name", default="antigravity")
    bootstrap = sub.add_parser("bootstrap", help="Print the subscription agent contract.")
    bootstrap.add_argument("run_id")
    status = sub.add_parser("status", help="Show stored records and task runs.")
    status.add_argument("--course", default=None)
    api = sub.add_parser("api", help="Send pending cards to the paid API (explicit opt-in, cost-gated).")
    api.add_argument("run_id")
    api.add_argument("--approve-cost", type=float, default=None)
    api.add_argument("--model", default="gemini-3.8-flash")
    return parser


def main(argv: list[str] | None = None, *, complete=None) -> int:
    args = build_parser().parse_args(argv)
    root = _single_root(args)
    if args.command == "collect":
        return cmd_collect(args, root)
    if args.command == "submit":
        return cmd_submit(args, root)
    if args.command == "bootstrap":
        run = _load(args, root)
        if run is None:
            return 2
        print(BOOTSTRAP.format(run=run.run_id, work=run.root, root=root))
        return 0
    if args.command == "status":
        return cmd_status(args, root)
    return cmd_api(args, root, complete)
