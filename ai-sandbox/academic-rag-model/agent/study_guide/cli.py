# agent/study_guide/cli.py
"""Command line for the study guide pipeline.

    python -m agent.study_guide plan   <spec> [--root R] [--force] [--env-file F]
    python -m agent.study_guide apply-review <plan> --decisions <file>
    python -m agent.study_guide draft  <spec> [--root R] [--plan P] [--model M] [--tag T] [--force]
                                       [--dry-run] [--accept-unreviewed] [--env-file F]
    python -m agent.study_guide run    <spec> [--yes]         (plan; with --yes also draft)

Design: docs/superpowers/specs/agent/2026-10-05-study-guide-pipeline-design.md. From a git
worktree pass --root <main checkout>/ai-sandbox/academic-hub and --env-file <main>/ai-sandbox/.env.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from agent.study_guide.draft import DraftError, draft_guide, output_path
from agent.study_guide.plan import (
    PlanError, apply_decisions, build_plan, check_fresh, load_plan, pending_entries, plan_sha256,
    save_plan, write_review_items,
)
from agent.study_guide.spec import SpecError, load_spec
from agent.summary_enhance.llm import GeminiClient

EXIT_OK, EXIT_NO_CLIENT, EXIT_INPUT, EXIT_LLM = 0, 1, 2, 4


def default_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "academic-hub"))


def _vault_dir(root: str, spec) -> Path:
    return Path(root) / "academic_notes" / spec.course


def plan_path_for(root: str, spec) -> Path:
    return _vault_dir(root, spec) / "guide_plans" / f"{spec.id}.plan.json"


def review_path_for(root: str, spec) -> Path:
    return _vault_dir(root, spec) / "guide_plans" / f"{spec.id}.review.json"


def _paid_client(env_file: str | None):
    from core.env.gemini_utils import get_gemini_client, load_dotenv_override
    if env_file:
        from dotenv import load_dotenv
        load_dotenv(env_file, override=True)
    else:
        load_dotenv_override()
    return get_gemini_client("PAID_GEMINI_KEY")


def _summary(plan) -> list[str]:
    lines = []
    for topic in plan.topics:
        counts = {s: sum(1 for e in topic.entries if e.status == s) for s in ("accepted", "pending", "dropped")}
        lines.append(f"  {topic.title}: {counts['accepted']} accepted, {counts['pending']} pending"
                     + (f", {counts['dropped']} dropped" if counts["dropped"] else ""))
    return lines


def cmd_plan(spec_path: str, root: str, *, client=None, search=None, force: bool = False,
             chunks=None, cards=None) -> int:
    try:
        spec = load_spec(spec_path)
    except SpecError as err:
        print(f"ERROR: {err}")
        return EXIT_INPUT
    out = plan_path_for(root, spec)
    if out.exists() and not force:
        print(f"ERROR: {out} already exists; pass --force to replace it (this discards earlier review decisions)")
        return EXIT_INPUT
    if client is None and search is None:
        print("ERROR: no Gemini client available (PAID_GEMINI_KEY)")
        return EXIT_NO_CLIENT
    try:
        plan = build_plan(spec, root, client=client, search=search, chunks=chunks, cards=cards)
    except PlanError as err:
        print(f"ERROR: {err}")
        return EXIT_INPUT
    save_plan(plan, out)
    write_review_items(plan, review_path_for(root, spec))
    print(f"Wrote {out}")
    print(f"Review items: {review_path_for(root, spec)}")
    print("\n".join(_summary(plan)))
    pending = len(pending_entries(plan))
    if pending:
        print(f"{pending} discovered passage(s) need review (publish the review Artifact, then apply-review).")
    return EXIT_OK


def cmd_apply_review(plan_path: str, decisions_path: str) -> int:
    try:
        plan = load_plan(plan_path)
        decisions = json.loads(Path(decisions_path).read_text(encoding="utf-8"))
        if not isinstance(decisions, dict):
            raise PlanError("decisions file must be a JSON object of key -> keep|drop")
        new = apply_decisions(plan, decisions)
    except (PlanError, OSError, json.JSONDecodeError) as err:
        print(f"ERROR: {err}")
        return EXIT_INPUT
    save_plan(new, plan_path)
    print("\n".join(_summary(new)))
    return EXIT_OK


def _load_plan_for(spec, root, plan_path, chunks, cards):
    path = Path(plan_path) if plan_path else plan_path_for(root, spec)
    plan = load_plan(path)
    if plan.spec_id != spec.id:
        raise PlanError(f"plan {path.name} is for guide {plan.spec_id!r}, not {spec.id!r}")
    if chunks is None:
        from core.indexer.chunk_index import load_chunks
        chunks = load_chunks(root, spec.course)
    if cards is None:
        from core.indexer.index_card import load_shard
        cards = load_shard(root, spec.course)
    stale = check_fresh(plan, chunks=chunks, cards=cards)
    if stale:
        raise PlanError("the plan is stale (re-run plan --force):\n  " + "\n  ".join(stale))
    return plan, path, chunks


def cmd_draft(spec_path: str, root: str, *, plan_path: str | None = None, llm=None, model: str | None = None,
              tag: str = "", force: bool = False, dry_run: bool = False, accept_unreviewed: bool = False,
              env_file: str | None = None, chunks=None, cards=None) -> int:
    try:
        spec = load_spec(spec_path)
        plan, path, chunks = _load_plan_for(spec, root, plan_path, chunks, cards)
        if dry_run:
            from agent.study_guide.plan import accepted
            counts = [len(accepted(plan, t.title, accept_unreviewed=accept_unreviewed)) for t in spec.topics]
            calls = len(spec.topics) + len(spec.comparisons)
            print(f"DRY RUN: {calls} call{'s' if calls != 1 else ''} to {model or spec.draft_model}, "
                  f"{sum(counts)} passages across {len(counts)} topics ({', '.join(map(str, counts))}), "
                  f"prompt {spec.prompt}")
            print(f"DRY RUN: would write {output_path(root, spec, tag)}")
            return EXIT_OK
        if llm is None:
            client = _paid_client(env_file)
            if client is None:
                return EXIT_NO_CLIENT
            llm = GeminiClient(client, model or spec.draft_model)
        out = draft_guide(spec, plan, root=root, llm=llm, chunks=chunks, tag=tag, force=force,
                          accept_unreviewed=accept_unreviewed, plan_path=str(path), plan_sha256=plan_sha256(path))
    except (SpecError, PlanError, DraftError) as err:
        print(f"ERROR: {err}")
        return EXIT_INPUT
    except Exception as err:  # network/API failure after the client's own retries
        print(f"ERROR: model call failed: {err}")
        return EXIT_LLM
    print(f"Wrote {out}")
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m agent.study_guide", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="command", required=True)

    def common(sp, spec=True):
        if spec:
            sp.add_argument("spec", help="path to a guide spec (.toml)")
        sp.add_argument("--root", default=default_root(), help="academic-hub root (corpus)")
        sp.add_argument("--env-file", help="load PAID_GEMINI_KEY from this .env")

    sp = sub.add_parser("plan")
    common(sp)
    sp.add_argument("--force", action="store_true", help="replace an existing plan")

    sp = sub.add_parser("apply-review")
    sp.add_argument("plan")
    sp.add_argument("--decisions", required=True, help="JSON object: 'Topic|chunk_id' -> keep|drop")

    sp = sub.add_parser("draft")
    common(sp)
    sp.add_argument("--plan", help="plan file (default: the spec's plan in the vault)")
    sp.add_argument("--model", help="override [models].draft")
    sp.add_argument("--tag", default="", help="name an output variant (<id>.<tag>.md)")
    sp.add_argument("--force", action="store_true")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--accept-unreviewed", action="store_true")

    sp = sub.add_parser("run")
    common(sp)
    sp.add_argument("--yes", action="store_true", help="after planning, draft using the plan as it is")

    args = p.parse_args(argv)
    if args.command == "apply-review":
        return cmd_apply_review(args.plan, args.decisions)
    if args.command in ("plan", "run"):
        client = _paid_client(args.env_file)
        code = cmd_plan(args.spec, args.root, client=client, force=getattr(args, "force", False))
        if args.command == "plan" or code != EXIT_OK or not args.yes:
            return code
        return cmd_draft(args.spec, args.root, accept_unreviewed=True, env_file=args.env_file)
    return cmd_draft(args.spec, args.root, plan_path=args.plan, model=args.model, tag=args.tag, force=args.force,
                     dry_run=args.dry_run, accept_unreviewed=args.accept_unreviewed, env_file=args.env_file)


if __name__ == "__main__":
    sys.exit(main())
