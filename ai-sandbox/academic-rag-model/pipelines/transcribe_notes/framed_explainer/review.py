# pipelines/transcribe_notes/framed_explainer/review.py
"""Owner-decision items for the explainer pipeline and the decision store the
collector consults. The interactive Artifact page renders ReviewItems; its
decisions come back through apply_decisions. Raw JSON is for code, not review."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

LOW_CONFIDENCE = 0.6


@dataclass
class ReviewItem:
    item_id: str
    kind: str
    target_key: str
    summary: str
    options: list[str] = field(default_factory=list)


@dataclass
class DecisionReport:
    declined: list[str]
    replace: list[str]
    expand: list[str]
    path: str


def decisions_path(hub_root: str, namespace: str) -> str:
    return os.path.join(hub_root, ".agent_work", "decisions", f"{namespace}.json")


def load_declined(hub_root: str, namespace: str) -> dict[str, str]:
    """{target_key: fingerprint} of cards the owner declined."""
    path = decisions_path(hub_root, namespace)
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f).get("declined", {})


def _item(kind: str, key: str, summary: str, options: list[str], extra: str = "") -> ReviewItem:
    return ReviewItem(f"{kind}:{key}:{extra}", kind, key, summary, options)


def build_review_items(resolved: dict, apply_results: list[dict]) -> list[ReviewItem]:
    items: list[ReviewItem] = []
    for s in resolved.get("slides", []):
        sid = s["slide_id"]
        for ink in s.get("ink", []):
            if ink["disposition"] == "fallback_nearest":
                items.append(_item("fallback_nearest", sid,
                                   f"Ink {ink['region_id']} attached to slide {sid} by distance only",
                                   ["accept", "make_section"], ink["region_id"]))
            elif ink.get("confidence") is not None and ink["confidence"] < LOW_CONFIDENCE:
                items.append(_item("low_confidence", sid,
                                   f"Ink {ink['region_id']} assigned to {sid} at "
                                   f"confidence {ink['confidence']}",
                                   ["accept", "make_section"], ink["region_id"]))
        if (s.get("card") or {}).get("status") == "needs_review":
            items.append(_item("needs_review", sid,
                               f"Card for slide {sid} needs review: {s['card'].get('reason')}",
                               ["accept_no_card", "decline"]))
    for sec in resolved.get("sections", []):
        key = sec.get("region_id") or sec["section_id"]
        if sec.get("also_near"):
            items.append(_item("anchor_tie", key,
                               f"Section {sec['section_id']} sits between "
                               f"{sec.get('anchor_slide_id')} and {sec['also_near']}",
                               [sec.get("anchor_slide_id") or "", sec["also_near"]], sec["section_id"]))
        if (sec.get("card") or {}).get("status") == "needs_review":
            items.append(_item("needs_review", key,
                               f"Section card {sec['section_id']} needs review: "
                               f"{sec['card'].get('reason')}", ["accept_no_card", "decline"]))
    for r in apply_results:
        if r.get("action") == "placement_conflict":
            items.append(_item("placement_conflict", r["key"],
                               f"No collision-free slot for {r['key']}", ["skip", "expand"]))
        elif r.get("action") == "skipped_existing":
            items.append(_item("replace_existing", r["key"],
                               f"{r['key']} already has a manual explanation", ["keep", "replace"]))
    return items


def apply_decisions(decisions: dict[str, str], items: list[ReviewItem],
                    run_dir: str) -> DecisionReport:
    with open(os.path.join(run_dir, "facts.json"), "r", encoding="utf-8") as f:
        facts = json.load(f)
    hub_root = os.path.dirname(os.path.dirname(os.path.dirname(run_dir)))
    fingerprints = {(t["slide_id"] or t["region_id"]): t["fingerprint"] for t in facts["targets"]}
    path = decisions_path(hub_root, facts["namespace"])
    stored = {"declined": {}, "choices": {}}
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            stored = json.load(f)
    by_id = {i.item_id: i for i in items}
    report = DecisionReport([], [], [], path)
    for item_id, choice in decisions.items():
        item = by_id[item_id]
        stored["choices"][item_id] = choice
        if choice == "decline" and item.target_key in fingerprints:
            stored["declined"][item.target_key] = fingerprints[item.target_key]
            report.declined.append(item.target_key)
        elif choice == "replace":
            report.replace.append(item.target_key)
        elif choice == "expand":
            report.expand.append(item.target_key)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(stored, indent=2, sort_keys=True) + "\n")
    return report
