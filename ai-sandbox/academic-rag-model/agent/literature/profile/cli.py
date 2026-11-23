"""Command line for the research-profile pipeline: metadata, classify, tag, folders, summary, queue, eval.

Every command takes `--index-root` (the research index: `.index/` shards plus transcripts). Agent stages use the
shared task-card loop: `collect` writes private cards under `<index-root>/.agent_work/<run>/`, the agent fills them in,
`submit` validates and applies them. `api` sends the cards to the paid Gemini key behind the usual cost gate.
Nothing here moves a file unless `folders apply` is given explicit approvals."""

import argparse
import json
import sys
from pathlib import Path

from agent.literature.profile import classify, evaluate, folders, metadata, review, summary, tagging
from agent.literature.profile.profiles import DEFAULT_DIR, load_profile
from agent.literature.vocab import load_vocabularies
from core.agent_tasks.loop import BudgetError, api_run, collect_run, provenance, submit_run
from core.agent_tasks.work import load_run
from core.indexer.research_profile import set_research_profile

_DEFAULT_ROOT = Path(__file__).resolve().parents[3].parent / "research"
KINDS = tagging.KINDS


def _work_root(args) -> Path:
    return Path(args.work_root) if args.work_root else Path(args.index_root) / ".agent_work"


def _cards(args) -> list[dict]:
    cards = review.all_cards(args.index_root)
    wanted = set(getattr(args, "file_id", None) or [])
    return [c for c in cards if c.get("file_id") and (not wanted or c["file_id"] in wanted)]


def _vocabs(args) -> dict:
    """The 3ie intervention and outcome trees. They are git-ignored data, so they come from --vocab-dir."""
    path = Path(args.vocab_dir) if args.vocab_dir else Path(args.index_root) / "resources" / "3ie" / "vocab"
    loaded = load_vocabularies(path)
    missing = [k for k in KINDS if k not in loaded]
    if missing:
        raise SystemExit(f"no {', '.join(missing)} vocabulary in {path}; pass --vocab-dir")
    return {k: loaded[k] for k in KINDS}


def _collect(args, command: str, stage_name: str, tasks: list, skipped: dict) -> int:
    for fid, why in skipped.items():
        print(f"skipped {fid}: {why}")
    if not tasks:
        print(f"nothing to do ({len(skipped)} skipped)")
        return 0
    run = collect_run(stage_name, tasks, _work_root(args), Path(args.index_root) / ".index", run_id=args.run_id,
                      repo_label="index")
    assert run is not None
    print(f"run {run.run_id}: {len(tasks)} cards in {run.root / 'cards'}")
    print(f"Fill each card's ## Result block (see worklist.md), then: "
          f"python -m agent.literature.profile.cli {command} submit {run.run_id}")
    return 0


def _load(args):
    try:
        return load_run(_work_root(args), args.run_id)
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc))
        return None


def _module(name: str):
    return classify if name == "classify" else tagging


def _target(args):
    return tagging.Target(args.index_root, _vocabs(args)) if args.command == "tag" else classify.Target(args.index_root)


def _print_report(report) -> None:
    print(f"applied {len(report.applied)}, bounced {len(report.bounced)}, skipped {len(report.skipped)}, "
          f"untouched {len(report.untouched)}")
    for task_id, reasons in report.bounced.items():
        print(f"bounced {task_id}: " + " | ".join(reasons))
    for task_id, reason in report.skipped.items():
        print(f"skipped {task_id}: {reason}")


def cmd_metadata(args, lookup=None) -> int:
    lookup = lookup or (metadata.openalex_lookup if args.source == "openalex" else metadata.crossref_lookup)
    checked = 0
    for card in _cards(args):
        profile = card.get("research_profile") or {}
        if not card.get("doi") or (profile.get("doi_verified", {}).get("match") in ("match", "mismatch") and not args.redo):
            continue
        result = metadata.verify_bibliography(card, lookup, source=args.source)
        fields = {**result["fields"], "doi_verified": result["doi_verified"]}
        if result["mismatches"]:
            fields["bibliography_mismatches"] = result["mismatches"]
        set_research_profile(args.index_root, card["file_id"], fields)
        checked += 1
    print(f"checked {checked} documents")
    return 0


def cmd_collect_classify(args) -> int:
    tasks, skipped = classify.make_tasks(classify.Target(args.index_root), _cards(args), variant=args.variant,
                                         redo=args.redo)
    return _collect(args, "classify", classify.STAGE, tasks, skipped)


def _prior(cards: list[dict], kind: str, level: int) -> dict[str, list[str]]:
    return {c["file_id"]: [t["term_id"] for t in (c.get("research_profile") or {}).get(f"{kind}_tags", [])
                           if t["level"] == level - 1] for c in cards}


def cmd_collect_tag(args) -> int:
    cards = _cards(args)
    target = tagging.Target(args.index_root, _vocabs(args))
    tasks, skipped = tagging.make_round_tasks(target, cards, args.kind, args.level, _prior(cards, args.kind, args.level),
                                              redo=args.redo)
    return _collect(args, "tag", tagging.STAGE, tasks, skipped)


def cmd_submit(args) -> int:
    run = _load(args)
    if run is None:
        return 2
    report = submit_run(run, _module(args.command), _target(args), args.agent_name, provenance_fn=provenance,
                        target_label="index cards")
    _print_report(report)
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
        report = api_run(run, _module(args.command), _target(args), complete or _gemini_complete(args.model),
                         args.approve_cost, provenance_fn=provenance, target_label="index cards")
    except BudgetError as exc:
        print(str(exc))
        return 2
    _print_report(report)
    return 0


def cmd_folders(args) -> int:
    cards = review.all_cards(args.index_root)  # the plan counts every paper; --file-id only narrows what is approved
    if args.action == "undo":
        log = json.loads(Path(folders.log_path(args.index_root)).read_text(encoding="utf-8")) \
            if Path(folders.log_path(args.index_root)).exists() else []
        entries = [e for e in log if not args.file_id or e["file_id"] in args.file_id]
        try:
            folders.undo_moves(args.index_root, entries)
        except ValueError as exc:
            print(str(exc))
            return 2
        print(f"undid {len(entries)} moves")
        return 0
    moves = folders.plan_moves(cards, args.index_root, min_papers=args.min_papers)
    if args.action == "plan":
        for m in moves:
            print(f"{m.file_id}: {m.from_folder} -> {m.to_folder} ({m.reason})")
        print(f"{len(moves)} moves planned; nothing was moved")
        return 0
    wanted = set(args.file_id or [])
    approved = {m.file_id for m in moves if not wanted or m.file_id in wanted} if args.all else set(args.approve)
    if not approved:
        print("nothing approved: pass --approve FILE_ID (repeatable) or --all after reviewing `folders plan`")
        return 2
    done = folders.apply_moves(args.index_root, moves, approved)
    print(f"moved {len(done)} documents")
    return 0


def cmd_summary(args) -> int:
    profile = load_profile(args.profile) if args.profile else None
    result = summary.summarize(_cards(args), profile, _vocabs(args), args.index_root)
    print(json.dumps(result, indent=2, ensure_ascii=False) if args.json else summary.render_summary(result))
    return 0


def cmd_refresh_discipline(args) -> int:
    """Recompute primary, secondary and fit from the stored readings and OpenAlex topics. No agent run needed."""
    target = classify.Target(args.index_root)
    count = 0
    for card in _cards(args):
        if (card.get("research_profile") or {}).get("discipline_primary"):
            classify._refresh_discipline(target, card["file_id"])
            count += 1
    print(f"refreshed {count} disciplines")
    return 0


def cmd_project(args) -> int:
    """Tag every paper currently in a folder (its course) with a project slug. Adds to any projects it already has."""
    count = 0
    for card in _cards(args):
        if card.get("course") == args.folder:
            projects = list((card.get("research_profile") or {}).get("projects") or [])
            if args.project not in projects:
                set_research_profile(args.index_root, card["file_id"], {"projects": projects + [args.project]})
            count += 1
    print(f"{count} papers in folder {args.folder!r} are tagged with project {args.project!r}")
    return 0 if count else 2


def cmd_queue(args) -> int:
    items = review.review_queue(args.index_root)
    for item in items:
        print(f"{item['file_id']} [{item['field']}] {item['title']}: " + " | ".join(item["reasons"]))
    print(f"{len(items)} open review items")
    return 0


def cmd_eval(args) -> int:
    cards = _cards(args)
    key, predicted = [], []
    by_doi = {c["doi"].casefold(): c for c in cards if c.get("doi")}
    for row in evaluate.load_3ie_csv(args.answer_key):
        card = by_doi.get(row["doi"] or "")
        if card is None:
            continue
        profile = card.get("research_profile") or {}
        key.append({"file_id": card["file_id"], "title": row["title"], "doi": row["doi"],
                    "report_type": row["publication_type"], "stratum": row["publication_type"] or "unscored"})
        predicted.append({"file_id": card["file_id"], "title": card.get("title"), "doi": card.get("doi"),
                          "report_type": profile.get("report_type")})
    strata = {k["file_id"]: k["stratum"] for k in key}
    print(json.dumps(evaluate.score_records(predicted, key, lambda r: strata[r["file_id"]]), indent=2))
    print(f"matched {len(key)} corpus documents to the answer key by DOI")
    return 0


def _add_run_options(p, redo_help="Run again even if the prompt version already ran.") -> None:
    p.add_argument("--file-id", action="append", default=[], help="Only this document (repeatable).")
    p.add_argument("--run-id", default=None)
    p.add_argument("--redo", action="store_true", help=redo_help)


def _add_submit_commands(sp) -> None:
    s = sp.add_parser("submit", help="Validate and apply the filled-in cards of a run.")
    s.add_argument("run_id")
    s.add_argument("--agent-name", default="antigravity")
    a = sp.add_parser("api", help="Send a run's cards to the paid Gemini key (cost-gated).")
    a.add_argument("run_id")
    a.add_argument("--model", default="gemini-3.8-flash")
    a.add_argument("--approve-cost", type=float, default=None, help="Dollars you approve for this call.")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="agent.literature.profile.cli", description=__doc__)
    p.add_argument("--index-root", default=str(_DEFAULT_ROOT), help="Research index root (holds .index/).")
    p.add_argument("--vocab-dir", default=None,
                   help="Directory holding the 3ie intervention.yaml and outcome.yaml (default: <index-root>/resources/3ie/vocab).")
    p.add_argument("--work-root", default=None, help="Private card directory (default: <index-root>/.agent_work).")
    top = p.add_subparsers(dest="command", required=True)

    m = top.add_parser("metadata", help="Check each DOI against Crossref or OpenAlex and fill missing bibliography.")
    m.add_argument("--source", choices=["crossref", "openalex"], default="crossref")
    m.add_argument("--file-id", action="append", default=[])
    m.add_argument("--redo", action="store_true")

    c = top.add_parser("classify", help="Report type, discipline and design flags.")
    cs = c.add_subparsers(dest="action", required=True)
    cc = cs.add_parser("collect")
    cc.add_argument("--variant", choices=["a", "b"], default="a", help="a: full classification; b: discipline check.")
    _add_run_options(cc)
    _add_submit_commands(cs)

    t = top.add_parser("tag", help="3ie intervention and outcome tagging, one taxonomy level per round.")
    ts = t.add_subparsers(dest="action", required=True)
    tc = ts.add_parser("collect")
    tc.add_argument("--kind", choices=list(KINDS), required=True)
    tc.add_argument("--level", type=int, choices=[1, 2, 3], required=True)
    _add_run_options(tc)
    _add_submit_commands(ts)

    f = top.add_parser("folders", help="Plan, apply or undo discipline-folder moves.")
    f.add_argument("action", choices=["plan", "apply", "undo"])
    f.add_argument("--min-papers", type=int, default=folders.DEFAULT_MIN_PAPERS)
    f.add_argument("--approve", action="append", default=[], help="file_id to move (repeatable).")
    f.add_argument("--all", action="store_true", help="Approve every planned move.")
    f.add_argument("--file-id", action="append", default=[])

    s = top.add_parser("summary", help="Counts per profile field and 3ie term.")
    s.add_argument("--profile", default=None, help=f"Inclusion profile YAML (see {DEFAULT_DIR}).")
    s.add_argument("--json", action="store_true")
    s.add_argument("--file-id", action="append", default=[])

    top.add_parser("queue", help="Open human-review items.")

    r = top.add_parser("refresh-discipline", help="Recompute primary/secondary discipline and fit from stored readings.")
    r.add_argument("--file-id", action="append", default=[])

    pj = top.add_parser("project", help="Tag every paper in a folder with a project slug (project papers are not moved).")
    pj.add_argument("folder", help="The folder (course) the papers sit in now.")
    pj.add_argument("project", help="Project slug, e.g. an independent-research/projects folder name.")
    pj.add_argument("--file-id", action="append", default=[])

    e = top.add_parser("eval", help="Score against a 3ie all_study_record CSV (matched by DOI).")
    e.add_argument("answer_key")
    return p


def main(argv: list[str] | None = None, *, lookup=None, complete=None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "metadata":
        return cmd_metadata(args, lookup)
    if args.command in ("classify", "tag"):
        if args.action == "collect":
            return cmd_collect_classify(args) if args.command == "classify" else cmd_collect_tag(args)
        return cmd_submit(args) if args.action == "submit" else cmd_api(args, complete)
    return {"folders": cmd_folders, "summary": cmd_summary, "queue": cmd_queue, "eval": cmd_eval,
            "refresh-discipline": cmd_refresh_discipline, "project": cmd_project}[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
