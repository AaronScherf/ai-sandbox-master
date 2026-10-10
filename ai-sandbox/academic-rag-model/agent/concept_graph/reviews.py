"""Review files from the viewer, and merging them into the graph YAML without silent overwrites."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .schema import EDITABLE_EDGE_FIELDS, EDITABLE_NODE_FIELDS, field_hash
from .store import GraphStore


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Target(_Model):
    kind: Literal["node", "edge"]
    id: str


class Decision(_Model):
    target: Target
    action: Literal["accept", "reject", "edit", "comment"]
    field: str | None = None
    base_hash: str | None = None
    new_value: str | None = None
    comment: str | None = None

    @model_validator(mode="after")
    def _check(self):
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
    schema_version: Literal[1]
    graph_version: str
    reviewer: Reviewer
    created: str
    decisions: list[Decision]


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
    with path.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(line + "\n")


def apply_review(store: GraphStore, review: ReviewFile, today: str) -> ApplyReport:
    report = ApplyReport()
    who = review.reviewer.name
    for d in review.decisions:
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
