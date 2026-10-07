# agent/study_guide/plan.py
"""Source plan: resolves a guide spec's source rules into a concrete, ordered, de-duplicated
list of indexed passages per topic, recorded in a ledger file (ids, paths, citations, scores,
rule provenance; never passage text). Pinned rules (section, file) are accepted; discovered
candidates start pending and need a human decision (see the review functions, Task 3)."""
from __future__ import annotations

import json
import os
import re
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from agent.study_guide.spec import GuideSpec, SourceRule, TopicSpec

PLAN_FORMAT = 1
ACCEPTED, PENDING, DROPPED = "accepted", "pending", "dropped"
_KIND_RANK = {"section": 0, "file": 1, "discover": 2}
_FRONT_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)


class PlanError(Exception):
    pass


class PendingReviewError(PlanError):
    pass


@dataclass
class PlanEntry:
    chunk_id: str
    file_id: str
    path: str
    citation: str
    doc_type: str
    offering: str
    score: float
    rule: str
    content_hash: str
    status: str = ACCEPTED


@dataclass
class TopicPlan:
    title: str
    entries: list[PlanEntry]


@dataclass
class Plan:
    spec_id: str
    spec_file: str
    spec_sha256: str
    course: str
    generated_at: str
    topics: list[TopicPlan]


# ---- label matching -------------------------------------------------------------------

def heading_numbers(heading_path: list[str]) -> list[str]:
    """The leading section number of each heading element, e.g. '**7.2.** Wald' -> '7.2'."""
    numbers = []
    for element in heading_path:
        m = re.match(r"(\d+(?:\.\d+)*)", re.sub(r"^[\s*#§_]+", "", element))
        if m:
            numbers.append(m.group(1))
    return numbers


def _matches(chunk: dict, citation: str, labels: tuple[str, ...], mode: str) -> bool:
    if not labels:
        return False
    heading_path = chunk.get("heading_path")
    if mode == "citation-substring" or not heading_path:
        return any(label in citation for label in labels)
    numbers = heading_numbers(heading_path)
    return any(n == label or n.startswith(label + ".") for n in numbers for label in labels)


# ---- helpers --------------------------------------------------------------------------

def _rel(root: str, path: str) -> str:
    if not os.path.isabs(path):
        return path.replace("\\", "/")
    try:
        rel = os.path.relpath(path, root)
    except ValueError:
        return path.replace("\\", "/")
    return path.replace("\\", "/") if rel.startswith("..") else rel.replace("\\", "/")


def _offering(card: dict, root: str) -> str:
    try:
        from core.indexer.offering_links import derive_offering_for_card
        return derive_offering_for_card(card, root) or ""
    except Exception:  # a label is optional provenance; never block planning on it
        return ""


def guide_chunk_ids(root: str, rel_path: str) -> set[str]:
    """Chunk ids a guide used, from its `indexer_source_refs` (drafts) or `source_map` (enhanced)."""
    path = Path(rel_path) if os.path.isabs(rel_path) else Path(root) / rel_path
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as err:
        raise PlanError(f"exclude_guide not readable: {path} ({err})") from err
    match = _FRONT_RE.match(text.replace("\r\n", "\n"))
    if not match:
        raise PlanError(f"{path} has no frontmatter")
    ids: set[str] = set()
    for key in ("indexer_source_refs", "source_map"):
        m = re.search(rf"^{key}:[ \t]*(.*)$", match.group(1), re.MULTILINE)
        if not m:
            continue
        try:
            items = json.loads(m.group(1))
        except json.JSONDecodeError as err:
            raise PlanError(f"{path}: {key} is not valid JSON: {err}") from err
        ids |= {i["chunk_id"] for i in items if isinstance(i, dict) and "chunk_id" in i}
    if not ids:
        raise PlanError(f"{path} lists no source chunks (no indexer_source_refs or source_map)")
    return ids


def _find_card(cards: list[dict], ref: str) -> dict | None:
    wanted = ref.replace("\\", "/")
    for card in cards:
        if card["file_id"] == ref:
            return card
        for key in ("rag_md_path", "path"):
            value = (card.get(key) or "").replace("\\", "/")
            if value and value.endswith(wanted):
                return card
    return None


class _Context:
    def __init__(self, spec, root, search, chunks, cards):
        self.spec, self.root, self.search = spec, root, search
        self.chunks = chunks
        self.chunks_by_id = {c["chunk_id"]: c for c in chunks}
        self.cards = cards
        self.cards_by_file = {c["file_id"]: c for c in cards}

    def entry(self, result, rule: str, status: str) -> PlanEntry:
        card = self.cards_by_file.get(result.file_id, {})
        return PlanEntry(
            chunk_id=result.chunk_id, file_id=result.file_id, path=_rel(self.root, result.path),
            citation=result.citation, doc_type=card.get("doc_type", ""), offering=_offering(card, self.root) if card else "",
            score=round(float(result.score), 4), rule=rule, content_hash=card.get("content_hash", ""), status=status)


# ---- rules ----------------------------------------------------------------------------

def _resolve_section(ctx: _Context, topic: TopicSpec, rule: SourceRule) -> list[PlanEntry]:
    text = f"{ctx.spec.course.capitalize()} textbook: {rule.query}. {topic.instruction}"
    results = ctx.search(text, doc_type="textbook", top_k=ctx.spec.top_k, file_top_k=ctx.spec.file_top_k)
    picked: list[PlanEntry] = []
    for r in results:
        if rule.book not in os.path.basename(r.path):
            continue
        chunk = ctx.chunks_by_id.get(r.chunk_id, {})
        if not _matches(chunk, r.citation, rule.labels, ctx.spec.label_match):
            continue
        if _matches(chunk, r.citation, rule.exclude_labels, ctx.spec.label_match):
            continue
        picked.append(ctx.entry(r, "section", ACCEPTED))
        if len(picked) == rule.max:
            break
    return picked


def _pseudo_result(ctx: _Context, chunk: dict):
    from types import SimpleNamespace
    from core.indexer.index_search import _render_citation
    card = ctx.cards_by_file[chunk["file_id"]]
    return SimpleNamespace(chunk_id=chunk["chunk_id"], file_id=chunk["file_id"],
                           path=card.get("rag_md_path") or card["path"], score=0.0,
                           citation=_render_citation(chunk) or chunk["chunk_id"])


def _resolve_file(ctx: _Context, topic: TopicSpec, rule: SourceRule) -> list[PlanEntry]:
    card = _find_card(ctx.cards, rule.file)
    if card is None:
        raise PlanError(f"file not found in the {ctx.spec.course} index: {rule.file}")
    file_chunks = [c for c in ctx.chunks if c["file_id"] == card["file_id"]]
    if not file_chunks:
        raise PlanError(f"{rule.file} has no chunks; run the chunk step on it first")
    ranked: list = []
    if rule.query:
        results = ctx.search(f"{rule.query}. {topic.instruction}", doc_type=card.get("doc_type"),
                             top_k=3000, file_top_k=200)
        ranked = [r for r in results if r.file_id == card["file_id"]]
    have = {r.chunk_id for r in ranked}
    rest = [_pseudo_result(ctx, c) for c in file_chunks if c["chunk_id"] not in have]
    return [ctx.entry(r, "file", ACCEPTED) for r in (ranked + rest)[:rule.max]]


def _resolve_discover(ctx: _Context, topic: TopicSpec, rule: SourceRule, taken: set[str]) -> list[PlanEntry]:
    excluded = set(taken)
    if rule.exclude_guide:
        excluded |= guide_chunk_ids(ctx.root, rule.exclude_guide)
    pool: list = []
    for doc_type in rule.doc_types:
        pool += ctx.search(f"{rule.query}. {topic.instruction}", doc_type=doc_type,
                           top_k=max(60, rule.max * 8), file_top_k=40)
    pool.sort(key=lambda r: -r.score)
    per_file: Counter = Counter()
    picked: list[PlanEntry] = []
    for r in pool:
        if r.chunk_id in excluded or r.score < rule.min_score:
            continue
        if rule.max_per_file and per_file[r.file_id] >= rule.max_per_file:
            continue
        per_file[r.file_id] += 1
        excluded.add(r.chunk_id)
        picked.append(ctx.entry(r, "discover", PENDING))
        if len(picked) == rule.max:
            break
    return picked


def build_plan(spec: GuideSpec, root: str, *, client=None, search: Callable | None = None,
               chunks: list[dict] | None = None, cards: list[dict] | None = None, now: str | None = None) -> Plan:
    if search is None:
        if client is None:
            raise PlanError("a Gemini client (or an explicit search function) is required")
        from core.indexer.index_search import search_passages

        def search(query, *, doc_type, top_k, file_top_k):
            return search_passages([root], query, client, course=spec.course, top_k=top_k,
                                   file_top_k=file_top_k, doc_type=doc_type)
    if chunks is None:
        from core.indexer.chunk_index import load_chunks
        chunks = load_chunks(root, spec.course)
    if cards is None:
        from core.indexer.index_card import load_shard
        cards = load_shard(root, spec.course)

    ctx = _Context(spec, root, search, chunks, cards)
    topics: list[TopicPlan] = []
    for topic in spec.topics:
        entries: list[PlanEntry] = []
        taken: set[str] = set()
        for rule in sorted(topic.sources, key=lambda r: _KIND_RANK[r.kind]):
            if rule.kind == "section":
                found = _resolve_section(ctx, topic, rule)
            elif rule.kind == "file":
                found = _resolve_file(ctx, topic, rule)
            else:
                found = _resolve_discover(ctx, topic, rule, taken)
            for entry in found:
                if entry.chunk_id not in taken:
                    taken.add(entry.chunk_id)
                    entries.append(entry)
        if not entries:
            raise PlanError(f"no passages resolved for topic {topic.title!r}")
        topics.append(TopicPlan(topic.title, entries))
    return Plan(spec_id=spec.id, spec_file=Path(spec.path).name, spec_sha256=spec.sha256, course=spec.course,
                generated_at=now or datetime.now(timezone.utc).isoformat(timespec="seconds"), topics=topics)


# ---- ledger ---------------------------------------------------------------------------

def save_plan(plan: Plan, path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    data = {"format": PLAN_FORMAT, **asdict(plan)}
    tmp = p.with_name(p.name + ".tmp")
    try:
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n")
        os.replace(tmp, p)
    finally:
        tmp.unlink(missing_ok=True)


def load_plan(path: str | Path) -> Plan:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as err:
        raise PlanError(f"cannot read plan {path}: {err}") from err
    if data.get("format") != PLAN_FORMAT:
        raise PlanError(f"unsupported plan format {data.get('format')!r} (expected {PLAN_FORMAT})")
    try:
        return Plan(
            spec_id=data["spec_id"], spec_file=data["spec_file"], spec_sha256=data["spec_sha256"],
            course=data["course"], generated_at=data["generated_at"],
            topics=[TopicPlan(t["title"], [PlanEntry(**e) for e in t["entries"]]) for t in data["topics"]])
    except (KeyError, TypeError) as err:
        raise PlanError(f"malformed plan {path}: {err}") from err


def plan_sha256(path: str | Path) -> str:
    import hashlib
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check_fresh(plan: Plan, *, chunks: list[dict], cards: list[dict]) -> list[str]:
    """Problems that make a plan stale: a planned chunk is gone, or its file's content changed."""
    by_id = {c["chunk_id"]: c for c in chunks}
    hashes = {c["file_id"]: c.get("content_hash", "") for c in cards}
    problems = []
    for topic in plan.topics:
        for e in topic.entries:
            chunk = by_id.get(e.chunk_id)
            if chunk is None or chunk.get("file_id") != e.file_id:
                problems.append(f"{topic.title}: chunk {e.chunk_id} no longer exists in the index")
            elif e.content_hash and hashes.get(e.file_id) and hashes[e.file_id] != e.content_hash:
                problems.append(f"{topic.title}: {e.path} changed since the plan was built")
    return problems

# ---- review ---------------------------------------------------------------------------

def decision_key(topic_title: str, chunk_id: str) -> str:
    return f"{topic_title}|{chunk_id}"


def review_items(plan: Plan) -> list[dict]:
    """One item per planned passage for the review Artifact. Pinned entries are `locked`
    (shown, not decidable); discovered ones carry the decision."""
    items = []
    for topic in plan.topics:
        for e in topic.entries:
            items.append({
                "key": decision_key(topic.title, e.chunk_id), "topic": topic.title, "chunk_id": e.chunk_id,
                "book": os.path.basename(e.path), "citation": e.citation, "doc_type": e.doc_type,
                "offering": e.offering, "score": e.score, "rule": e.rule, "status": e.status,
                "locked": e.rule != "discover",
            })
    return items


def write_review_items(plan: Plan, path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(review_items(plan), indent=2, ensure_ascii=False), encoding="utf-8", newline="\n")


def apply_decisions(plan: Plan, decisions: dict[str, str]) -> Plan:
    """Returns a new plan with each decided pending entry set to accepted (keep) or dropped (drop)."""
    import copy
    new = copy.deepcopy(plan)
    index = {decision_key(t.title, e.chunk_id): e for t in new.topics for e in t.entries}
    for key, value in decisions.items():
        entry = index.get(key)
        if entry is None:
            raise PlanError(f"unknown decision key: {key!r}")
        if value not in ("keep", "drop"):
            raise PlanError(f"decision for {key!r} must be 'keep' or 'drop', got {value!r}")
        if entry.rule != "discover":
            raise PlanError(f"{key!r} is pinned by a section or file rule and cannot be dropped")
        if entry.status != PENDING:
            raise PlanError(f"{key!r} is already decided ({entry.status})")
        entry.status = ACCEPTED if value == "keep" else DROPPED
    return new


def pending_entries(plan: Plan) -> list[tuple[str, PlanEntry]]:
    return [(t.title, e) for t in plan.topics for e in t.entries if e.status == PENDING]


def accepted(plan: Plan, topic_title: str, *, accept_unreviewed: bool = False) -> list[PlanEntry]:
    topic = next((t for t in plan.topics if t.title == topic_title), None)
    if topic is None:
        raise PlanError(f"topic {topic_title!r} is not in the plan; re-run plan")
    pending = [e for e in topic.entries if e.status == PENDING]
    if pending and not accept_unreviewed:
        raise PendingReviewError(
            f"topic {topic_title!r} has {len(pending)} discovered passage(s) awaiting review; review them "
            "(or pass --accept-unreviewed to use them as they are)")
    return [e for e in topic.entries if e.status in (ACCEPTED, PENDING if accept_unreviewed else ACCEPTED)]
