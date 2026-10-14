"""Review files from the viewer, and merging them into the graph YAML without silent overwrites."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .schema import EDITABLE_EDGE_FIELDS, EDITABLE_NODE_FIELDS, edge_id, field_hash
from .proposals import (NAME_MAX, NOTE_MAX, EdgeProposal, NodeProposal, check_edge, check_node, cluster, find_similar_existing,
                        merge_cluster, merge_edges, slug_from_name)
from .store import GraphStore


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Target(_Model):
    kind: Literal["node", "edge"]
    id: str


class Decision(_Model):
    target: Target | None = None
    action: Literal["accept", "reject", "edit", "comment", "add_node", "add_edge"]
    field: str | None = None
    base_hash: str | None = None
    new_value: str | None = None
    comment: str | None = None
    proposal: NodeProposal | EdgeProposal | None = None

    @model_validator(mode="after")
    def _check(self):
        if self.action in ("add_node", "add_edge"):
            want = NodeProposal if self.action == "add_node" else EdgeProposal
            if not isinstance(self.proposal, want) or self.target is not None:
                raise ValueError(f"{self.action} needs a matching proposal and no target")
            return self
        if self.target is None or self.proposal is not None:
            raise ValueError(f"{self.action} needs a target and no proposal")
        if self.action == "edit":
            allowed = EDITABLE_NODE_FIELDS if self.target.kind == "node" else EDITABLE_EDGE_FIELDS
            if self.field not in allowed:
                raise ValueError(f"cannot edit field {self.field!r} of a {self.target.kind}; allowed: {allowed}")
            if self.base_hash is None or self.new_value is None:
                raise ValueError("an edit needs base_hash and new_value")
        if self.action == "comment" and not (self.comment or "").strip():
            raise ValueError("a comment needs text")
        return self


class Reviewer(_Model):
    name: str = Field(min_length=1)


class ReviewFile(_Model):
    schema_version: Literal[1, 2]
    graph_version: str
    reviewer: Reviewer
    created: str
    decisions: list[Decision]

    @model_validator(mode="after")
    def _proposals_need_version_2(self):
        if self.schema_version == 1 and any(d.action in ("add_node", "add_edge") for d in self.decisions):
            raise ValueError("proposals need schema_version 2")
        return self


@dataclass
class ApplyReport:
    applied: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    comments: list[str] = field(default_factory=list)


def _find(store: GraphStore, kind: str, item_id: str):
    graph = store.read_all()
    pool = graph.nodes if kind == "node" else graph.edges
    return next((i for i in pool if i.id == item_id), None)


def _append(path: Path, line: str) -> None:
    line = re.sub(r"[\r\n]+", " ", line)  # reviewer-supplied text must not start lines of its own
    with path.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(line + "\n")


def apply_review(store: GraphStore, review: ReviewFile, today: str) -> ApplyReport:
    report = ApplyReport()
    who = review.reviewer.name
    for d in review.decisions:
        if d.action in ("add_node", "add_edge"):
            continue  # handled once per round by apply_proposals
        kind, item_id = d.target.kind, d.target.id
        label = f"{kind} {item_id}"
        current = _find(store, kind, item_id)
        if current is None:
            report.skipped.append(f"{label}: not found (the graph may have changed since the review was made)")
            continue

        if d.action == "accept":
            if current.status == "verified":
                report.skipped.append(f"{label}: already verified")
                continue
            store.update_item(kind, item_id, {"status": "verified", "reviewed_by": who, "reviewed_on": today})
            report.applied.append(f"{label}: accepted")

        elif d.action == "reject":
            if current.status == "verified":
                # The viewer only offers Reject on unreviewed items, so a reject arriving for a verified one means
                # someone accepted or edited it after this review was made. Disagreements are the maintainer's call.
                msg = (f"{who} {today}: {label}: rejected, but it has since been verified by someone else; "
                       f"left unchanged for you to decide")
                _append(store.root / "review-conflicts.md", "- " + msg)
                report.conflicts.append(msg)
                continue
            taken = []
            if kind == "node":
                graph = store.read_all()
                for e in graph.edges:
                    if item_id in (e.source, e.target):
                        store.remove_item("edge", e.id)
                        store.add_rejected("edge", e.id)
                        taken.append(e.id + (" (verified)" if e.status == "verified" else ""))
                    elif e.via == item_id:
                        store.update_item("edge", e.id, {"via": None})
                        report.applied.append(f"edge {e.id}: via cleared because theorem {item_id} was rejected")
            store.remove_item(kind, item_id)
            store.add_rejected(kind, item_id)
            report.applied.append(f"{label}: rejected" + (f" (also removed edges: {', '.join(taken)})" if taken else ""))

        elif d.action == "edit":
            existing = getattr(current, d.field)
            if field_hash(existing) == d.base_hash:
                store.update_item(kind, item_id, {d.field: d.new_value, "status": "verified", "reviewed_by": who, "reviewed_on": today})
                report.applied.append(f"{label}.{d.field}: edited")
            elif (d.new_value or "").strip() == (existing or "").strip():
                report.skipped.append(f"{label}.{d.field}: already has this value")
            else:
                msg = (f"{who} {today}: {label}.{d.field}: the field changed since the review was made "
                       f"(reviewer saw {d.base_hash}, now {field_hash(existing)}); proposed text: {d.new_value!r}")
                _append(store.root / "review-conflicts.md", "- " + msg)
                report.conflicts.append(msg)

        elif d.action == "comment":
            _append(store.root / "review-comments.md", f"- {who} {today} on {label}: {d.comment.strip()}")
            report.comments.append(f"{label}: comment recorded")
    return report


def archive_review(root: Path, review: ReviewFile, today: str) -> Path:
    folder = Path(root) / "reviews" / "applied"
    folder.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", review.reviewer.name.lower()).strip("-") or "reviewer"
    path = folder / f"{today}-{slug}.json"
    n = 2
    while path.exists():
        path = folder / f"{today}-{slug}-{n}.json"
        n += 1
    path.write_text(json.dumps(review.model_dump(mode="json", exclude_none=True), indent=2) + "\n", encoding="utf-8", newline="\n")
    return path


def apply_proposals(store: GraphStore, reviews: list[ReviewFile], today: str) -> ApplyReport:
    """One pass over every review in the round: cluster duplicate concepts, validate, write proposed items."""
    report = ApplyReport()
    node_items: list[tuple[NodeProposal, str]] = []
    edge_items: list[tuple[EdgeProposal, str]] = []
    too_long: list[tuple[str, str]] = []
    for r in reviews:
        for d in r.decisions:
            if d.action == "add_node":
                if len(d.proposal.name) > NAME_MAX or len(d.proposal.note or "") > NOTE_MAX:
                    # checked before any name comparison, which is quadratic in the name length
                    too_long.append((r.reviewer.name, d.proposal.name[:60]))
                    continue
                node_items.append((d.proposal, r.reviewer.name))
            elif d.action == "add_edge":
                edge_items.append((d.proposal, r.reviewer.name))
    if not node_items and not edge_items and not too_long:
        return report
    graph = store.read_all()
    conflicts_file = store.root / "review-conflicts.md"

    def conflict(who: list[str], label: str, reason: str) -> None:
        msg = f"{'; '.join(who)} {today}: proposal {label}: {reason}"
        _append(conflicts_file, "- " + msg)
        report.conflicts.append(msg)

    for who_name, label_name in too_long:
        conflict([who_name], f"concept {label_name!r}",
                 f"name is longer than {NAME_MAX} characters or note is longer than {NOTE_MAX}; shorten it and "
                 f"propose again")
    new_nodes: list[dict] = []
    new_ids: set[str] = set()
    pending_edges: list[tuple[EdgeProposal, str]] = list(edge_items)
    for group in cluster(node_items):
        merged = merge_cluster(group)
        label = f"concept {merged.name!r}"
        for line in merged.decisions:
            conflict(merged.reviewers, label, line)
        if len(group) > 1:
            report.applied.append(f"{label}: merged {len(group)} proposals from {', '.join(merged.reviewers)}")
        existing = find_similar_existing(graph, merged.name)
        if existing is not None:
            who = merged.reviewers
            if merged.note:
                _append(store.root / "review-comments.md",
                        f"- {'; '.join(who)} {today} on node {existing.id}: proposed as a new concept "
                        f"({merged.name}): {merged.note}")
                report.comments.append(f"node {existing.id}: proposal note recorded")
            conflict(who, label, f"treated as proposals about existing concept {existing.id!r}: confirm, or "
                                 f"re-propose it as a separate concept")
            for c in merged.connections:
                src, dst = (existing.id, c.other) if c.direction == "out" else (c.other, existing.id)
                pending_edges += [(EdgeProposal(source=src, type=c.type, target=dst, condition=c.condition,
                                                note=c.note), w) for w in who]
            continue
        problems = check_node(graph, merged.name, merged.kind, merged.section, merged.topic, merged.note)
        slug = slug_from_name(merged.name)
        if slug in new_ids:
            problems.append(f"{slug!r} was proposed twice in this round")
        if problems:
            conflict(merged.reviewers, label, "; ".join(problems))
            continue
        new_ids.add(slug)
        new_nodes.append({"id": slug, "name": merged.name, "kind": merged.kind, "section": merged.section,
                          "topic": merged.topic, "gist": merged.note, "explanation": "", "status": "proposed",
                          "provenance": {"driver": "reviewer", "agent": "; ".join(merged.reviewers), "run": today}})
        report.applied.append(f"node {slug}: proposed by {', '.join(merged.reviewers)}")
        for c in merged.connections:
            src, dst = (slug, c.other) if c.direction == "out" else (c.other, slug)
            pending_edges += [(EdgeProposal(source=src, type=c.type, target=dst, condition=c.condition,
                                            note=c.note), w) for w in merged.reviewers]

    staged: list[tuple[str, str, str]] = []
    new_edges: list[dict] = []
    for e, who in sorted(merge_edges(pending_edges), key=lambda i: edge_id(i[0].source, i[0].type, i[0].target)):
        eid = edge_id(e.source, e.type, e.target)
        errs, warns = check_edge(graph, e.source, e.type, e.target, e.condition, e.note, new_ids=new_ids,
                                 staged=staged)
        if errs:
            conflict(who, f"connection {eid}", "; ".join(errs))
            continue
        staged.append((e.source, e.type, e.target))
        new_edges.append({"id": eid, "source": e.source, "type": e.type, "target": e.target,
                          "condition": e.condition, "explanation": e.note, "status": "proposed",
                          "provenance": {"driver": "reviewer", "agent": "; ".join(who), "run": today}})
        report.applied.append(f"edge {eid}: proposed by {', '.join(who)}" +
                              (f" (warning: {'; '.join(warns)})" if warns else ""))
    by_section: dict[str, list[dict]] = {}
    for n in new_nodes:
        by_section.setdefault(n["section"], []).append(n)
    for section_id, nodes in by_section.items():
        store.add_nodes(section_id, nodes)
    if new_edges:
        store.add_edges(new_edges)
    return report
