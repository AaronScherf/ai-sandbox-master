# agent/study_guide/revise/run.py
"""Orchestrate the revise stages into an edit report; apply accepted edits to produce the revised guide."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from agent.study_guide.draft import DraftError, validate_tag
from agent.study_guide.plan import PlanError
from dataclasses import asdict

from agent.study_guide.revise.apply import apply_edits, changelog
from agent.study_guide.revise.audit import audit_section, build_audit_prompt
from agent.study_guide.revise.checkpoint import Checkpoint
from agent.study_guide.revise.cost import CostCapReached, cost_usd, estimate_cost
from agent.study_guide.revise.dedup import dedup_edits, find_duplicate_clusters
from agent.study_guide.revise.inline import inline_candidates, inline_edits
from agent.study_guide.revise.judge import judge_candidates, judge_edits
from agent.study_guide.revise.edits import (
    Edit, EditReport, ReviseError, load_report, mark_conflicts, save_report, validate_report,
)
from agent.study_guide.revise.organize import organize_edits
from agent.study_guide.revise.relevance import Relevance, relevance_edits, score_blocks
from agent.study_guide.revise.review import accepted_ids, write_review_items
from agent.study_guide.revise.segment import segment, split_frontmatter
from agent.study_guide.spec import GuideSpec, SpecError, load_spec
from agent.summary_enhance.llm import usage_line

STAGES = ("relevance", "dedup", "correctness", "organization", "inline")
EXIT_OK, EXIT_INPUT, EXIT_CAP, EXIT_LLM = 0, 2, 3, 4


def report_path(root: str, spec: GuideSpec, guide_path: str, tag: str) -> Path:
    name = Path(guide_path).stem + (f".{tag}" if tag else "") + ".revise.json"
    return Path(root) / "academic_notes" / spec.course / "guide_plans" / name


def revised_path(guide_path: str, tag: str) -> Path:
    p = Path(guide_path)
    return p.with_name(f"{p.stem}.revised{'.' + tag if tag else ''}.md")


def section_passages(plan, spec: GuideSpec, chunks: list[dict], section_title: str) -> list[tuple[str, str, str]]:
    """The plan passages that back one guide section (a topic, or a comparison's source topics)."""
    from agent.study_guide.plan import accepted
    norm = " ".join(section_title.split()).casefold()
    titles = [t.title for t in spec.topics if " ".join(t.title.split()).casefold() == norm]
    titles = titles or [x for c in spec.comparisons if " ".join(c.title.split()).casefold() == norm for x in c.from_topics]
    text_by_id = {c["chunk_id"]: c["text"] for c in chunks}
    seen, out = set(), []
    for title in titles:
        for e in accepted(plan, title):
            if e.chunk_id not in seen and e.chunk_id in text_by_id:
                seen.add(e.chunk_id)
                out.append((f"S{len(out) + 1}", e.citation, text_by_id[e.chunk_id]))
    return out


def _retrying(embed, attempts: int = 5, wait: float = 15.0):
    """Wrap an embedder so a burst of rate-limit errors is waited out instead of aborting the run."""
    import time

    def call(text: str) -> list[float]:
        for i in range(attempts):
            try:
                return embed(text)
            except Exception:
                if i == attempts - 1:
                    raise
                time.sleep(wait * (i + 1))
        raise AssertionError("unreachable")
    return call


def _memoized(embed):
    cache: dict[str, list[float]] = {}

    def cached(text: str) -> list[float]:
        if text not in cache:
            cache[text] = embed(text)
        return cache[text]
    return cached


def _edits(rows: list[dict]) -> list[Edit]:
    return [Edit(**row) for row in rows]


def _relevance(row: dict) -> Relevance:
    return Relevance(row["block_id"], row["score"], tuple((c, s) for c, s in row["nearest"]), tuple(row["nearest_text"]))


def build_report(spec: GuideSpec, guide_path: str, plan, *, stages, llm, embed, evidence, chunks, now: str | None = None,
                 checkpoint: Checkpoint | None = None, max_cost: float | None = None,
                 audit_cache: Checkpoint | None = None) -> EditReport:
    if spec.revise is None:
        raise ReviseError("the spec has no [revise] table")
    bad = [s for s in stages if s not in STAGES or s not in spec.revise.criteria]
    if bad:
        raise ReviseError(f"stage(s) {bad} are not enabled by the spec's [revise] criteria {list(spec.revise.criteria)}")
    raw = Path(guide_path).read_bytes()
    _, body = split_frontmatter(raw.decode("utf-8").replace("\r\n", "\n"))
    blocks = segment(body)
    embed = _memoized(embed)
    r, edits, protected, scores = spec.revise, [], [], {}
    usage: dict[str, dict] = {}
    cheap = llm.with_thinking(r.light_thinking) if hasattr(llm, "with_thinking") else llm  # audit keeps full thinking

    def unit(name, compute):
        """Run one unit of work, or reuse its saved result from an earlier run of the same inputs.
        The tokens a unit spent are saved with it, so a resumed run still reports the whole cost."""
        saved = checkpoint.get(name) if checkpoint else None
        if saved is not None:
            usage[name] = saved.get("_usage", {})
            return saved
        before = dict(getattr(llm, "usage", None) or {})
        payload = compute()
        after = getattr(llm, "usage", None) or {}
        payload["_usage"] = usage[name] = {k: after[k] - before.get(k, 0) for k in after}
        if checkpoint:
            checkpoint.put(name, payload)
        if max_cost and cost_usd(getattr(llm, "usage", None) or {}, r.model) > max_cost:
            raise CostCapReached(f"spend passed the ${max_cost:.2f} cap after {name!r}; finished work is saved, "
                                 f"so rerun with a higher --max-cost to resume")
        return payload

    if "relevance" in stages:
        def do_relevance():
            sc = score_blocks(blocks, evidence, embed, min_words=r.min_block_words)
            found, prot = relevance_edits(blocks, sc, low=r.relevance_low, high=r.relevance_high)
            if r.judge_fraction > 0:
                ask = judge_candidates(blocks, sc, fraction=r.judge_fraction, protected=prot,
                                       skip=[t for e in found for t in e.targets])
                found = found + judge_edits(cheap, r.scope, {b.id: b for b in blocks}, ask, sc, start=len(found) + 1)
            return {"edits": [asdict(e) for e in found], "protected": prot, "scores": {k: asdict(v) for k, v in sc.items()}}

        saved = unit("relevance", do_relevance)
        edits += _edits(saved["edits"])
        protected = saved["protected"]
        scores = {k: _relevance(v) for k, v in saved["scores"].items()}
    flags: dict[str, list[str]] = {}
    if "dedup" in stages:
        def do_dedup():
            fl: dict[str, list[str]] = {}
            for cluster in find_duplicate_clusters(blocks, embed, similarity=r.dedup_similarity, min_words=r.min_block_words):
                for bid in cluster:
                    fl.setdefault(bid, []).append("duplicate")
            found = dedup_edits(cheap, blocks, embed, similarity=r.dedup_similarity, min_words=r.min_block_words, start=1)
            return {"edits": [asdict(e) for e in found], "flags": fl}

        saved = unit("dedup", do_dedup)
        edits += _edits(saved["edits"])
        flags = saved["flags"]
    if "correctness" in stages:
        for title in dict.fromkeys(b.heading_path[1] for b in blocks if len(b.heading_path) > 1):
            passages = section_passages(plan, spec, chunks, title)
            section = [b for b in blocks if len(b.heading_path) > 1 and b.heading_path[1] == title]
            if passages and section:
                start = len([e for e in edits if e.stage == "correctness"]) + 1

                def do_audit(title=title, section=section, passages=passages, start=start):
                    # An audit depends only on the section text, its source passages and the model, so a section that
                    # did not change since an earlier run (of any version of the guide) is not paid for again.
                    key = hashlib.sha256((r.model + build_audit_prompt(title, section, passages)).encode()).hexdigest()
                    hit = audit_cache.get(key) if audit_cache else None
                    if hit is not None:
                        rows = [{**row, "id": f"cor-{start + i:03d}"} for i, row in enumerate(hit["edits"])]
                        return {"edits": rows, "problems": hit["problems"]}
                    found, problems = audit_section(llm, title, section, passages, start=start)
                    result = {"edits": [asdict(e) for e in found], "problems": problems}
                    if audit_cache:
                        audit_cache.put(key, result)
                    return result

                saved = unit(f"correctness:{title}", do_audit)
                edits += _edits(saved["edits"])
                for p in saved["problems"]:
                    print(f"WARNING: audit of {title!r}: {p}")
    if "inline" in stages:
        if not r.scope_terms:
            raise ReviseError("the inline stage needs [revise] scope_terms")

        def do_inline():
            found, problems = inline_edits(cheap, r.scope, blocks, r.scope_terms)
            return {"edits": [asdict(e) for e in found], "problems": problems}

        saved = unit("inline", do_inline)
        edits += _edits(saved["edits"])
        for p in saved["problems"]:
            print(f"WARNING: inline sweep: {p}")
    if "organization" in stages:
        saved = unit("organization", lambda: {"edits": [asdict(e) for e in organize_edits(cheap, blocks, flags)]})
        edits += _edits(saved["edits"])
    for e in edits:
        e.protected = bool(set(e.targets) & set(protected)) and e.type in ("delete", "shrink", "merge")
    report = EditReport(
        guide_path=Path(guide_path).name, guide_sha256=hashlib.sha256(raw).hexdigest(),
        created_at=now or datetime.now(timezone.utc).isoformat(timespec="seconds"),
        blocks=[{"id": b.id, "heading_path": list(b.heading_path), "words": b.words,
                 "relevance": round(scores[b.id].score, 3) if b.id in scores else None} for b in blocks],
        edits=edits, protected_blocks=protected, usage=usage)
    mark_conflicts(report)
    problems = validate_report(report, blocks)
    if problems:
        raise ReviseError("the edit report is invalid: " + "; ".join(problems))
    return report


def _paid_llm(env_file, model):
    from agent.study_guide.cli import _paid_client
    from agent.summary_enhance.llm import GeminiClient
    client = _paid_client(env_file)
    return None if client is None else (GeminiClient(client, model), client)


def cmd_revise(spec_path: str, root: str, *, guide_path: str, plan_path: str | None = None, stages=None, tag: str = "",
               dry_run: bool = False, force: bool = False, env_file: str | None = None, llm=None, embed=None,
               client=None, chunks=None, cards=None, search=None, evidence=None, resume: bool = True,
               max_cost: float | None = None) -> int:
    from agent.study_guide.cli import _load_plan_for
    try:
        validate_tag(tag)
        spec = load_spec(spec_path)
        if spec.revise is None:
            raise ReviseError("the spec has no [revise] table")
        if not Path(guide_path).is_file():
            raise ReviseError(f"guide not found: {guide_path}")
        stages = list(stages or spec.revise.criteria)
        out = report_path(root, spec, guide_path, tag)
        if out.exists() and not force:
            raise ReviseError(f"{out} already exists; pass --force to replace it")
        plan, _, chunks = _load_plan_for(spec, root, plan_path, chunks, cards)
        _, body = split_frontmatter(Path(guide_path).read_text(encoding="utf-8"))
        blocks = segment(body)
        cap = spec.revise.max_cost if max_cost is None else max_cost
        estimate = estimate_cost(estimated_calls(spec, blocks, stages), spec.revise.model, _prior_usage(out))
        cost_line = f"estimated cost ${estimate:.2f} (rough" + (f"; cap ${cap:.2f})" if cap else "; no cap)")
        if dry_run:
            sections = len({b.heading_path[1] for b in blocks if len(b.heading_path) > 1})
            calls = {"relevance": "judge batches of 12 over the lowest-scored and unscored blocks" if spec.revise.judge_fraction > 0 else 0, "dedup": "1 per duplicate cluster", "correctness": f"{sections} audit calls + 1 per worked block",
                     "organization": 1, "inline": "1 per 8 blocks that mention a scope term"}
            print(f"DRY RUN: {len(blocks)} blocks, {sum(b.words for b in blocks)} words, stages {stages}, "
                  f"{len(spec.revise.evidence)} evidence rule(s) (resolved at run time)")
            print("DRY RUN: model calls: " + ", ".join(f"{s}: {calls[s]}" for s in stages))
            print(f"DRY RUN: {cost_line}")
            print(f"DRY RUN: would write {out}")
            return EXIT_OK
        if cap and estimate > cap:
            raise ReviseError(f"{cost_line} is over the cap; raise --max-cost, drop stages with --stages, or trim the spec")
        if llm is None or embed is None or evidence is None:
            paid = _paid_llm(env_file, spec.revise.model)
            if paid is None:
                from agent.study_guide.cli import EXIT_NO_CLIENT
                return EXIT_NO_CLIENT
            llm, client = llm or paid[0], client or paid[1]
            if embed is None:
                from core.indexer.index_search import _embed_query
                embed = _retrying(lambda text: _embed_query(text[:8000], client))
            if evidence is None:
                from agent.study_guide.revise.evidence import load_evidence
                evidence = load_evidence(spec, root, client=client, search=search, chunks=chunks, cards=cards) if "relevance" in stages else []
        checkpoint = Checkpoint(out.with_name(out.name.replace(".revise.json", ".revise.partial.json")),
                                hashlib.sha256((spec.sha256 + Path(guide_path).read_bytes().hex()).encode()).hexdigest())
        if not resume:
            checkpoint.clear()
        audit_cache = Checkpoint(out.with_name("revise.audit-cache.json"), "audit-cache-v1")
        report = build_report(spec, guide_path, plan, stages=stages, llm=llm, embed=embed, evidence=evidence, chunks=chunks,
                              checkpoint=checkpoint, max_cost=cap or None, audit_cache=audit_cache)
        if checkpoint.used:
            print(f"Resumed from a saved partial run: reused {', '.join(dict.fromkeys(checkpoint.used))}")
        save_report(report, out)
        checkpoint.clear()
        write_review_items(report, body, out.with_name(out.name.replace(".revise.json", ".revise.review.json")))
    except (SpecError, ReviseError, PlanError, DraftError, OSError) as err:
        print(f"ERROR: {err}")
        _print_usage(llm)
        return EXIT_INPUT
    except CostCapReached as err:
        print(f"STOPPED: {err}")
        _print_usage(llm)
        return EXIT_CAP
    except Exception as err:  # API failure after the client's own retries
        print(f"ERROR: model or embedding call failed: {err}")
        _print_usage(llm)
        return EXIT_LLM
    by_stage: dict[str, int] = {}
    for e in report.edits:
        by_stage[e.stage] = by_stage.get(e.stage, 0) + 1
    print(f"Wrote {out}: {len(report.edits)} proposed edits {by_stage}; review them in the Artifact, then apply-revise.")
    _print_stage_usage(report.usage)
    _print_usage(llm)
    return EXIT_OK


def estimated_calls(spec: GuideSpec, blocks, stages) -> dict[str, int]:
    """Rough model-call counts per stage, from the guide's shape alone (no embeddings, so dedup clusters are a guess)."""
    r = spec.revise
    sections = len({b.heading_path[1] for b in blocks if len(b.heading_path) > 1})
    counts = {"relevance": -(-int(len(blocks) * r.judge_fraction) // 12) + (1 if r.judge_fraction > 0 else 0),
              "dedup": 10, "correctness": sections, "organization": 1,
              "inline": -(-len(inline_candidates(blocks, r.scope_terms)) // 8)}
    return {s: counts[s] for s in stages}


def _prior_usage(out: Path) -> dict[str, dict] | None:
    """Per-stage usage recorded by an earlier run of this guide, from its report or its partial file."""
    try:
        data = json.loads(out.read_text(encoding="utf-8"))
        return usage_by_stage(data.get("usage") or {}) or None
    except (OSError, ValueError, AttributeError):
        return None


def usage_by_stage(usage: dict[str, dict]) -> dict[str, dict]:
    """Sum per-unit usage into per-stage totals (every audited section counts toward `correctness`)."""
    out: dict[str, dict] = {}
    for unit_name, u in usage.items():
        total = out.setdefault(unit_name.split(":")[0], {})
        for k, v in u.items():
            total[k] = total.get(k, 0) + v
    return out


def _print_stage_usage(usage: dict[str, dict]) -> None:
    for stage, u in usage_by_stage(usage).items():
        print(f"  {stage}: {u.get('calls', 0)} calls, {u.get('prompt_tokens', 0)} prompt, "
              f"{u.get('output_tokens', 0)} output, {u.get('thinking_tokens', 0)} thinking tokens")


def _print_usage(llm) -> None:
    usage = getattr(llm, "usage", None)
    if usage:
        print(usage_line(usage))


def cmd_apply_revise(spec_path: str, root: str, *, guide_path: str, decisions_path: str, tag: str = "", force: bool = False) -> int:
    try:
        validate_tag(tag)
        spec = load_spec(spec_path)
        report = load_report(report_path(root, spec, guide_path, tag))
        raw = Path(guide_path).read_bytes()
        if hashlib.sha256(raw).hexdigest() != report.guide_sha256:
            raise ReviseError("the guide changed since the report was made; run revise again")
        out = revised_path(guide_path, tag)
        if out.exists() and not force:
            raise ReviseError(f"{out} already exists; pass --force to replace it")
        decisions = json.loads(Path(decisions_path).read_text(encoding="utf-8"))
        if not isinstance(decisions, dict):
            raise ReviseError("the decisions file must be a JSON object of edit id -> accept|reject")
        accepted = accepted_ids(report, decisions)
        front, body = split_frontmatter(raw.decode("utf-8").replace("\r\n", "\n"))
        revised = apply_edits(body, report, accepted)
        count = len([e for e in report.edits if e.id in accepted and e.type != "note"])
        if front:
            extra = (f"revised_from: {json.dumps({'path': report.guide_path, 'sha256': report.guide_sha256})}\n"
                     f"revise_edits_applied: {count}\n")
            front = front.replace("\n---\n", "\n" + extra + "---\n", 1)
        out.write_text(front + revised, encoding="utf-8", newline="\n")
        out.with_name(out.stem + ".changelog.md").write_text(changelog(report, accepted), encoding="utf-8", newline="\n")
    except (SpecError, ReviseError, DraftError, OSError, json.JSONDecodeError) as err:
        print(f"ERROR: {err}")
        return EXIT_INPUT
    print(f"Wrote {out} ({count} edits applied)")
    return EXIT_OK
