"""python -m agent.literature <command>: extract study records from converted journal papers."""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
from pathlib import Path

from core.agent_tasks.loop import BudgetError, api_run, collect_run, provenance, submit_run
from core.agent_tasks.work import load_run

from . import cluster as clusters, contribute, db as litdb, refine_grain, review, stage, synth, tiers, verify
from .backfill_years import backfill_years
from .remap import remap_record
from .gold import DEFAULT_PATH, load_gold, score_record, summarize
from .papers import drop_duplicate_titles, eligible_papers
from .proposals import Proposals
from .store import RecordStore
from .vocab import DATA_DIR, load_vocabularies

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
    return stage.Target(str(args.index_root), records, load_vocabularies(args.vocab_dir), Proposals(records.dir))


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
    if not args.include_duplicates:
        papers, dupes = drop_duplicate_titles(papers, set(target.records.all_ids()))
        skipped = {**skipped, **dupes}
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
    module = {verify.STAGE: verify, contribute.STAGE: contribute, synth.STAGE: synth,
              refine_grain.STAGE: refine_grain}.get(run.stage, stage)
    report = submit_run(run, module, _target(args), args.agent_name, provenance_fn=provenance, target_label="study records")
    _print_report(report)
    return 0


def cmd_verify(args) -> int:
    target = _target(args)
    papers, _ = eligible_papers(args.index_root)
    if args.file_id:
        papers = [p for p in papers if p.file_id in set(args.file_id)]
    tasks, skips = verify.make_tasks(target, papers, redo=args.redo, full_paper=args.full_paper)
    for fid, reason in skips.items():
        print(f"skipped {fid}: {reason}")
    try:
        run = collect_run(verify.STAGE, tasks, _work_root(args), target.records.dir, run_id=args.run_id, repo_label="records")
    except (ValueError, FileExistsError) as exc:
        print(f"cannot create the run: {exc}")
        return 2
    if run is None:
        print("nothing to verify")
        return 0
    print(f"collected {len(tasks)} verification card(s) in run {run.run_id}: {run.root}")
    return 0


def cmd_refine_grain(args) -> int:
    target = _target(args)
    papers, _ = eligible_papers(args.index_root)
    if args.file_id:
        papers = [p for p in papers if p.file_id in set(args.file_id)]
    tasks, skipped = refine_grain.make_tasks(target, papers, pass_label="a", redo=args.redo)
    b_tasks, b_skipped = refine_grain.make_tasks(target, papers, pass_label="b", redo=args.redo)
    tasks += b_tasks
    skipped.update({f"{k} (pass b)": v for k, v in b_skipped.items()})
    for fid, reason in skipped.items():
        print(f"skipped {fid}: {reason}")
    try:
        run = collect_run(refine_grain.STAGE, tasks, _work_root(args), target.records.dir, run_id=args.run_id, repo_label="records")
    except (ValueError, FileExistsError) as exc:
        print(f"cannot create the run: {exc}")
        return 2
    if run is None:
        print("nothing to refine")
        return 0
    print(f"collected {len(tasks)} refine-grain card(s) in run {run.run_id}: {run.root}")
    return 0


def cmd_silver(args) -> int:
    target = _target(args)
    totals = {"agreed": 0, "confirmed": 0, "open": 0}
    for fid in target.records.ids():
        split = verify.silver_split(target.records, fid, target.vocabs)
        if not any(split.values()):
            continue
        for k in totals:
            totals[k] += len(split[k])
        print(f"{fid}  agreed {len(split['agreed'])}  confirmed {len(split['confirmed'])}  open {len(split['open'])}")
    print(f"total  agreed {totals['agreed']}  confirmed {totals['confirmed']}  open {totals['open']}")
    return 0


def cmd_tiers(args) -> int:
    """Count facts by confidence tier and write the derived `_tiers.json` next to the records."""
    target = _target(args)
    papers = {}
    for fid in target.records.ids():
        if items := tiers.tiered_facts(target.records, fid, target.vocabs, target.proposals):
            papers[fid] = items
    count = {t: sum(1 for items in papers.values() for i in items if i["tier"] == t) for t in tiers.ORDER}
    for t in tiers.ORDER:
        print(f"tier {t}: {count[t]:4d}  {tiers.LEGEND[t]}")
    facets = sorted({i["facet"] for items in papers.values() for i in items})
    for facet in facets:
        row = {t: sum(1 for items in papers.values() for i in items if i["facet"] == facet and i["tier"] == t) for t in tiers.ORDER}
        print(f"  {facet:14s} A {row['A']:3d}  B {row['B']:3d}  C {row['C']:3d}")
    out = Path(target.records.dir) / "_tiers.json"
    out.write_text(json.dumps({"legend": tiers.LEGEND, "papers": papers}, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n")
    print(f"{len(papers)} papers written to {out}")
    return 0


def cmd_cluster(args) -> int:
    target = _target(args)
    try:
        if args.action == "show":
            c = clusters.load_cluster(args.index_root, args.name)
        else:
            c = clusters.define_cluster(target.records, target.vocabs, args.name, args.where, args.floor, target.proposals)
            clusters.save_cluster(args.index_root, c)
    except clusters.ClusterError as exc:
        print(f"cluster: {exc}")
        return 2
    print(f"cluster {c.name}: {len(c.file_ids)} papers at tier {c.floor} or better")
    for fid in c.file_ids:
        print(f"  {fid}")
    return 0


def _collect(args, stage_name, tasks, skips, label) -> int:
    for fid, reason in skips.items():
        print(f"skipped {fid}: {reason}")
    try:
        run = collect_run(stage_name, tasks, _work_root(args), clusters.topic_dir(args.index_root, args.name),
                          run_id=args.run_id, repo_label="literature review folder")
    except (ValueError, FileExistsError) as exc:
        print(f"cannot create the run: {exc}")
        return 2
    if run is None:
        print(f"nothing to {label}")
        return 0
    print(f"collected {len(tasks)} {label} card(s) in run {run.run_id}: {run.root}")
    return 0


def cmd_annotate(args) -> int:
    target = _target(args)
    try:
        cluster = clusters.load_cluster(args.index_root, args.name)
    except clusters.ClusterError as exc:
        print(f"annotate: {exc}")
        return 2
    papers, _ = eligible_papers(args.index_root)
    tasks, skips = contribute.make_tasks(target, cluster, papers, redo=args.redo, limit=args.limit)
    return _collect(args, contribute.STAGE, tasks, skips, "annotation")


def cmd_synthesize(args) -> int:
    target = _target(args)
    try:
        cluster = clusters.load_cluster(args.index_root, args.name)
        tasks, skips = synth.make_tasks(target, cluster, max_papers=args.max_papers, merge=args.merge)
    except (clusters.ClusterError, ValueError) as exc:
        print(f"synthesize: {exc}")
        return 2
    return _collect(args, synth.STAGE, tasks, skips, "synthesis")


def cmd_db(args) -> int:
    path = litdb.db_path(args.index_root)
    if args.action == "build":
        counts = litdb.build(_target(args), path, args.floor)
        print(f"built {path}: " + ", ".join(f"{n} {t.replace('_', ' ')}" for t, n in counts.items()))
        return 0
    if not path.is_file():
        print("db: no database yet; run `db build` first")
        return 2
    conn = sqlite3.connect(path)
    try:
        if args.action == "matrix":
            for r in litdb.matrix(conn):
                print(f"{r['intervention']}	{r['outcome']}	{r['study_design']}	{r['papers']}")
        elif args.action == "dist":
            for label, n in litdb.distribution(conn, args.facet):
                print(f"{label}	{n}")
        elif args.action == "cooccur":
            for a, b, n in litdb.cooccurrence(conn):
                print(f"{a}	{b}	{n}")
        elif args.action == "query":
            for r in litdb.query(conn, _target(args).vocabs, args.where):
                print(f"{r['file_id']}	{r['year'] or ''}	{r['title']}")
        else:
            out = args.out or Path(args.index_root) / "literature_db" / "evidence_matrix.md"
            print(f"wrote {litdb.export_markdown(conn, out)}")
    except (ValueError, clusters.ClusterError) as exc:
        print(f"db: {exc}")
        return 2
    finally:
        conn.close()
    return 0


def _gap_items(args, run_dir: Path):
    """(facet, phrase, pick, resolved_by) for each constraint, plus the question text and unmapped phrases."""
    if args.where:
        items = [(c["facet"], c["value"], None, "user") for c in map(clusters.parse_constraint, args.where)]
        return items, "; ".join(args.where), []
    saved = run_dir / "constraints.json"
    if not saved.is_file():
        raise ValueError("give at least one --where facet=value constraint, or submit a `gap question` card first "
                         "(no constraints.json in the run folder)")
    data = json.loads(saved.read_text(encoding="utf-8"))
    return ([(c["facet"], c["phrase"], c["value"], "card") for c in data["constraints"]],
            data.get("question", ""), data.get("unmapped", []))


def cmd_gap(args) -> int:
    from dataclasses import asdict

    from .gap import classify as gclassify, coverage as gcoverage, report as greport, resolve as gresolve
    from .gap.corpus import load_corpus
    from .gap.subregions import load_subregions

    path = litdb.db_path(args.index_root)
    if not path.is_file():
        print("gap: no database yet; run `db build` first")
        return 2
    report_root = Path(args.report_root) if args.report_root else Path(args.index_root) / "literature_gap"
    target = _target(args)
    subregions = load_subregions()
    try:
        run_dir = greport.gap_dir(report_root, args.run_id)
        items, question, unmapped = _gap_items(args, run_dir)
        picks = {c["facet"]: c["value"] for c in map(clusters.parse_constraint, args.pick)}
        conn = sqlite3.connect(path)
        try:
            corpus = load_corpus(conn)
        finally:
            conn.close()
        constraints, stopped = [], []
        for facet, phrase, pick, by in items:
            res = gresolve.resolve(corpus, target.vocabs, facet, phrase, pick=pick, resolved_by=by, subregions=subregions)
            if res.constraint is None and pick is None and facet in picks:
                res = gresolve.resolve(corpus, target.vocabs, facet, phrase, pick=picks.pop(facet), subregions=subregions)
            if res.constraint is not None:
                constraints.append(res.constraint)
            else:
                stopped.append({"facet": facet, "phrase": phrase, "message": res.message,
                                "candidates": [asdict(c) for c in res.candidates]})
        if stopped:
            run_dir.mkdir(parents=True, exist_ok=True)
            (run_dir / "candidates.json").write_text(json.dumps({"constraints": stopped}, indent=2, ensure_ascii=False) + "\n",
                                                     encoding="utf-8", newline="\n")
            for s in stopped:
                print(f"gap: {s['facet']}={s['phrase']}: {s['message']}")
                for c in s["candidates"]:
                    print(f"  {c['term_id']}\t{c['label']} (level {c['level']}, {c['children']} children, {c['papers']} papers)"
                          f"\t--pick {s['facet']}={c['term_id']}")
            print(f"stopped; candidates in {run_dir / 'candidates.json'}")
            return 2
        result = gclassify.classify(corpus, constraints, target.vocabs, subregions)
        cov = gcoverage.coverage(corpus, result, constraints, gcoverage.read_sidecar(target, args.index_root, path))
        report = greport.build_report(question, constraints, target.vocabs, result, cov, corpus,
                                      unmapped=unmapped, include_quotes=args.quotes)
        js, md = greport.write_report(report, run_dir)
    except (ValueError, clusters.ClusterError, KeyError) as exc:
        print(f"gap: {exc}")
        return 2
    print(f"verdict: {result.verdict}\n{result.rule}")
    print(f"direct {len(result.direct)}, adjacent {len(result.adjacent)}, partial {len(result.partial)}")
    print(f"wrote {js}\nwrote {md}")
    return 0


def cmd_render(args) -> int:
    try:
        review_path, bib_path = review.render(_target(args), args.name)
    except (clusters.ClusterError, ValueError) as exc:
        print(f"render: {exc}")
        return 2
    print(f"wrote {review_path}\nwrote {bib_path}")
    return 0


def cmd_bootstrap(args) -> int:
    print(BOOTSTRAP.format(run=args.run_id))
    return 0


def cmd_status(args) -> int:
    papers, skipped = eligible_papers(args.index_root)
    target = _target(args)
    have = set(target.records.all_ids())
    print(f"eligible papers: {len(papers)}")
    print(f"skipped papers: {len(skipped)}")
    print(f"records: {len(have & {p.file_id for p in papers})}")
    print(f"papers without a record: {len([p for p in papers if p.file_id not in have])}")
    copies = sum(1 for fid in have & {p.file_id for p in papers}
                 if any("may not be independent" in m for m in ((target.records.read(fid, "a") or {}).get("review") or {}).get("items_flagged", [])))
    print(f"open vocabulary proposals: {len([p for p in target.proposals.open() if p['file_id'] not in target.records.excluded()])}")
    print(f"pairs that may not be independent: {copies}")
    print(f"excluded papers: {len(target.records.excluded())}")
    return 0


def cmd_exclude(args) -> int:
    records = _target(args).records
    (records.include if args.undo else records.exclude)(args.file_ids)
    print(f"excluded: {len(records.excluded())}")
    return 0


def cmd_remap(args) -> int:
    target = _target(args)
    papers, _ = eligible_papers(args.index_root)
    changed = {p.file_id: n for p in papers if (n := remap_record(target.records, target.proposals, target.vocabs, p.file_id))}
    print(f"facts re-pointed to vocabulary terms: {sum(changed.values())} in {len(changed)} papers")
    return 0


def cmd_backfill_years(args) -> int:
    mailto = args.mailto or os.environ.get("OPENALEX_CONTACT_EMAIL")
    if not mailto:
        print("backfill-years: no --mailto and OPENALEX_CONTACT_EMAIL is not set")
        return 2
    outcomes = backfill_years(args.index_root, mailto, records=_target(args).records)
    for fid, outcome in sorted(outcomes.items()):
        print(f"{fid}\t{outcome}")
    print(f"{sum(o == 'backfilled' for o in outcomes.values())} of {len(outcomes)} backfilled")
    return 0


def cmd_proposals(args) -> int:
    target = _target(args)
    out = target.records.excluded()
    for p in target.proposals.open():
        if p["file_id"] in out:
            continue
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
    c.add_argument("--include-duplicates", action="store_true", help="Also extract extra copies of a title already kept.")
    v = sub.add_parser("verify", help="Write cards that ask for an independent check of facts only one pass found.")
    v.add_argument("--file-id", action="append", default=[], help="Only this paper (repeatable).")
    v.add_argument("--run-id", default=None)
    v.add_argument("--redo", action="store_true", help="Verify again even if the paper was already verified.")
    v.add_argument("--full-paper", action="store_true", help="Second look: offer the whole paper for facts the first check did not support.")
    rg = sub.add_parser("refine-grain", help="Re-extract only intervention/outcome, scoped to each paper's own vocabulary branch (TODO-0085).")
    rg.add_argument("--file-id", action="append", default=[], help="Only this paper (repeatable).")
    rg.add_argument("--run-id", default=None)
    rg.add_argument("--redo", action="store_true", help="Refine again even if the paper was already refined.")
    sub.add_parser("silver", help="Per paper: facts both passes agree on, facts the verifier confirmed, facts still open.")
    s = sub.add_parser("submit", help="Validate filled cards and write records.")
    s.add_argument("run_id")
    s.add_argument("--agent-name", default="antigravity")
    b = sub.add_parser("bootstrap", help="Print the agent's operating contract.")
    b.add_argument("run_id")
    sub.add_parser("status", help="Counts of papers, records and open proposals.")
    p_ex = sub.add_parser("exclude", help="Set off-topic papers aside: tiers, clusters, silver, eval and the db skip them; records stay on disk.")
    p_ex.add_argument("file_ids", nargs="+")
    p_ex.add_argument("--undo", action="store_true", help="Put the papers back.")
    sub.add_parser("tiers", help="Count facts by confidence tier (A both passes, B checker-supported, C open) and write _tiers.json.")
    sub.add_parser("remap", help="Point facts whose proposal was accepted or merged at the vocabulary term.")
    by = sub.add_parser("backfill-years", help="Fill publication_year on journal_article cards that lack it, from OpenAlex (no LLM).")
    by.add_argument("--mailto", default=None, help="Contact email for OpenAlex's polite pool (default: $OPENALEX_CONTACT_EMAIL).")
    pr = sub.add_parser("proposals", help="Terms the agent proposed that no vocabulary term covered.")
    pr.add_argument("action", choices=["list"])
    cl = sub.add_parser("cluster", help="Choose the papers of a review by facet constraints on tier A/B facts.")
    cl.add_argument("action", choices=["define", "show"])
    cl.add_argument("name")
    cl.add_argument("--where", action="append", default=[], help="facet=value, repeatable (facet: intervention, outcome, study_design, sector, population, data_sources, countries).")
    cl.add_argument("--floor", choices=["A", "B", "C"], default="B")
    an = sub.add_parser("annotate", help="Cards for a contribution and limitation note per paper of a cluster.")
    an.add_argument("name")
    an.add_argument("--run-id", default=None)
    an.add_argument("--redo", action="store_true")
    an.add_argument("--limit", type=int, default=None, help="At most this many cards, so a large cluster is annotated in batches.")
    sy = sub.add_parser("synthesize", help="Cards that write the cluster review; --merge joins chunk answers.")
    sy.add_argument("name")
    sy.add_argument("--run-id", default=None)
    sy.add_argument("--merge", action="store_true")
    sy.add_argument("--max-papers", type=int, default=synth.MAX_PAPERS)
    rd = sub.add_parser("render", help="Write review.md and bibliography.md under literature_reviews/<name>/.")
    rd.add_argument("name")
    d = sub.add_parser("db", help="Derived SQLite database: build it, then matrix, dist, cooccur, query or export.")
    d.add_argument("action", choices=["build", "matrix", "dist", "cooccur", "query", "export"])
    d.add_argument("facet", nargs="?", default=None, help="For dist: the facet to count.")
    d.add_argument("--where", action="append", default=[], help="For query: facet=value, repeatable.")
    d.add_argument("--floor", choices=["A", "B", "C"], default="B", help="For build: lowest confidence tier to load.")
    d.add_argument("--out", default=None, help="For export: the Markdown file to write.")
    g = sub.add_parser("gap", help="Gap analysis over the database: has this been studied, and in what context? (offline)")
    g.add_argument("action", choices=["run"])
    g.add_argument("--run-id", required=True)
    g.add_argument("--where", action="append", default=[], help="facet=value, repeatable (a term id, label, alias or country code).")
    g.add_argument("--pick", action="append", default=[], help="facet=term_id: choose from the candidates a stopped run printed.")
    g.add_argument("--quotes", action="store_true", help="Include verbatim quotes in the report (default: claims and directions only).")
    g.add_argument("--report-root", default=None, help="Where reports are written (default: <index-root>/literature_gap).")
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
    return {"collect": cmd_collect, "verify": cmd_verify, "silver": cmd_silver, "submit": cmd_submit, "bootstrap": cmd_bootstrap, "status": cmd_status,
            "proposals": cmd_proposals, "eval": cmd_eval, "remap": cmd_remap, "tiers": cmd_tiers, "backfill-years": cmd_backfill_years,
            "cluster": cmd_cluster, "annotate": cmd_annotate, "synthesize": cmd_synthesize, "render": cmd_render, "db": cmd_db,
            "gap": cmd_gap, "refine-grain": cmd_refine_grain, "exclude": cmd_exclude}[args.command](args)
