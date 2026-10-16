"""python -m agent.literature <command>: extract study records from converted journal papers."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from core.agent_tasks.loop import BudgetError, api_run, collect_run, provenance, submit_run
from core.agent_tasks.work import load_run

from . import stage
from .gold import DEFAULT_PATH, load_gold, score_record, summarize
from .papers import eligible_papers
from .proposals import Proposals
from .store import RecordStore
from .vocab import DATA_DIR, load_vocab_dir

_DEFAULT_ROOT = Path(__file__).resolve().parent.parent.parent.parent / "research"

BOOTSTRAP = """Agent contract for study-record extraction, run '{run}':

1. Open <index-root>/.agent_work/{run}/cards/ and read worklist.md to see which cards are pending.
2. For each pending card: read every page under "Offered passages", then write ONLY the YAML mapping described in the
   card's Instructions inside the ```yaml fence under "## Result". Do not edit any other part of the card or any other file.
3. Copy every quote exactly from the page text and cite its page number as the locator.
4. When you have filled one or more cards, run:
   python -m agent.literature submit {run}
5. If a card comes back marked bounced, fix only what the listed reasons name, in the same fence, and run submit again.
6. Stop when nothing is pending or bounced.
"""


def _target(args) -> stage.Target:
    records = RecordStore(Path(args.index_root) / ".index" / "study_records")
    return stage.Target(str(args.index_root), records, load_vocab_dir(args.vocab_dir), Proposals(records.dir))


def _work_root(args) -> Path:
    return Path(args.work_root) if args.work_root else Path(args.index_root) / ".agent_work"


def cmd_collect(args) -> int:
    target = _target(args)
    papers, skipped = eligible_papers(args.index_root)
    if args.file_id:
        known = {p.file_id for p in papers}
        for fid in args.file_id:
            if fid not in known:
                print(f"{fid}: not an eligible paper ({skipped.get(fid, 'not found in the index')})")
        papers = [p for p in papers if p.file_id in set(args.file_id)]
    tasks, task_skips = stage.make_tasks(target, papers, redo=args.redo)
    if args.double:
        b_tasks, b_skips = stage.make_tasks(target, papers, pass_label="b", redo=args.redo)
        tasks += b_tasks
        task_skips.update({f"{k} (pass b)": v for k, v in b_skips.items()})
    for fid, reason in {**skipped, **task_skips}.items():
        print(f"skipped {fid}: {reason}")
    try:
        run = collect_run(stage.STAGE, tasks, _work_root(args), target.records.dir, run_id=args.run_id, repo_label="records")
    except (ValueError, FileExistsError) as exc:
        print(f"cannot create the run: {exc}")
        return 2
    if run is None:
        print("nothing to collect")
        return 0
    print(f"collected {len(tasks)} card(s) in run {run.run_id}: {run.root}")
    return 0


def _load(args):
    try:
        return load_run(_work_root(args), args.run_id)
    except (FileNotFoundError, ValueError) as exc:
        print(f"cannot load run {args.run_id}: {exc}")
        return None


def _print_report(report) -> None:
    print(f"applied {len(report.applied)}, bounced {len(report.bounced)}, skipped {len(report.skipped)}, "
          f"untouched {len(report.untouched)}")
    for task_id, reasons in report.bounced.items():
        print(task_id)
        for r in reasons:
            print(f"  - {r}")
    for task_id, reason in report.skipped.items():
        print(f"skipped {task_id}: {reason}")


def cmd_submit(args) -> int:
    run = _load(args)
    if run is None:
        return 2
    report = submit_run(run, stage, _target(args), args.agent_name, provenance_fn=provenance, target_label="study records")
    _print_report(report)
    return 0


def cmd_bootstrap(args) -> int:
    print(BOOTSTRAP.format(run=args.run_id))
    return 0


def cmd_status(args) -> int:
    papers, skipped = eligible_papers(args.index_root)
    target = _target(args)
    have = set(target.records.ids())
    print(f"eligible papers: {len(papers)}")
    print(f"skipped papers: {len(skipped)}")
    print(f"records: {len(have & {p.file_id for p in papers})}")
    print(f"papers without a record: {len([p for p in papers if p.file_id not in have])}")
    print(f"open vocabulary proposals: {len(target.proposals.open())}")
    return 0


def cmd_proposals(args) -> int:
    for p in _target(args).proposals.open():
        loc = p["locator"]
        page = f"pages {', '.join(map(str, loc))}" if isinstance(loc, list) else f"page {loc}"
        print(f"{p['id']}  {p['vocabulary']}  {p['value']!r}  paper {p['file_id']}  {page}")
    return 0


def _extract_manifests(work_root: Path) -> list[dict]:
    out = []
    for path in sorted(work_root.glob("*/manifest.json")) if work_root.is_dir() else []:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(data, dict) and data.get("stage") == stage.STAGE:
            out.append(data)
    return out


def cmd_eval(args) -> int:
    path = Path(args.gold) if args.gold else DEFAULT_PATH
    try:
        papers = load_gold(path)
    except (OSError, ValueError) as exc:
        print(f"cannot load the gold set {path}: {exc}")
        return 2
    target = _target(args)
    per_paper, expects = {}, {}
    for paper in papers:
        fid = paper["file_id"]
        expects[fid] = paper.get("expect") or {}
        record = target.records.read(fid)
        per_paper[fid] = score_record(record, expects[fid], target.vocabs) if record else None
    compared = agreed = 0
    for fid in target.records.ids():
        if target.records.read(fid, "b") is not None:
            compared += 1
            agreed += (target.records.read(fid) or {}).get("review", {}).get("double_pass") == "agreed"
    report = summarize(per_paper, expects=expects, proposals=target.proposals.all(), records=len(target.records.ids()),
                       manifests=_extract_manifests(_work_root(args)), double={"compared": compared, "agreed": agreed})
    print(json.dumps(report, indent=2))
    return 0


def _gemini_complete(model: str):
    """A complete(prompt) -> reply using the paid key. The only place this package can spend money; not unit-tested."""
    from core.env.gemini_utils import call_with_retries, get_gemini_client

    client = get_gemini_client("PAID_GEMINI_KEY")
    if client is None:
        raise SystemExit(1)
    return lambda prompt: call_with_retries(
        lambda: client.models.generate_content(model=model, contents=prompt, config={"temperature": 0}).text or "")


def cmd_api(args, complete=None) -> int:
    run = _load(args)
    if run is None:
        return 2
    try:
        report = api_run(run, stage, _target(args), complete or _gemini_complete(args.model), args.approve_cost,
                         provenance_fn=provenance, target_label="study records")
    except BudgetError as exc:
        print(str(exc))
        return 2
    _print_report(report)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m agent.literature", description=__doc__)
    p.add_argument("--index-root", default=str(_DEFAULT_ROOT), help="Research index root (holds .index/ and .agent_work/).")
    p.add_argument("--vocab-dir", default=str(DATA_DIR), help="Directory of vocabulary YAML files.")
    p.add_argument("--work-root", default=None, help="Private card directory (default: <index-root>/.agent_work).")
    sub = p.add_subparsers(dest="command", required=True)
    c = sub.add_parser("collect", help="Write extraction cards (no API calls).")
    c.add_argument("--file-id", action="append", default=[], help="Only this paper (repeatable).")
    c.add_argument("--run-id", default=None)
    c.add_argument("--redo", action="store_true", help="Extract again even if a current record exists.")
    c.add_argument("--double", action="store_true", help="Also stage an independent second pass for each paper.")
    s = sub.add_parser("submit", help="Validate filled cards and write records.")
    s.add_argument("run_id")
    s.add_argument("--agent-name", default="antigravity")
    b = sub.add_parser("bootstrap", help="Print the agent's operating contract.")
    b.add_argument("run_id")
    sub.add_parser("status", help="Counts of papers, records and open proposals.")
    pr = sub.add_parser("proposals", help="Terms the agent proposed that no vocabulary term covered.")
    pr.add_argument("action", choices=["list"])
    ev = sub.add_parser("eval", help="Score the records against the gold set (aggregates only).")
    ev.add_argument("--gold", default=None, help=f"Gold set YAML (default: {DEFAULT_PATH}).")
    a = sub.add_parser("api", help="Send pending cards to the paid API (explicit opt-in, cost-gated).")
    a.add_argument("run_id")
    a.add_argument("--approve-cost", type=float, default=None, help="Approve up to this many dollars.")
    a.add_argument("--model", default="gemini-3.8-flash")
    return p


def main(argv: list[str] | None = None, *, complete=None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "api":
        return cmd_api(args, complete)
    return {"collect": cmd_collect, "submit": cmd_submit, "bootstrap": cmd_bootstrap, "status": cmd_status,
            "proposals": cmd_proposals, "eval": cmd_eval}[args.command](args)
