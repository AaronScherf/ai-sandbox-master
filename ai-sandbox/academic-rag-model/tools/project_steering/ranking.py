"""Transparent deterministic priority and dependency ordering."""

from __future__ import annotations

from datetime import date
import re

from tools.project_steering.parser import Task

PENALTY = {"<2h": 0, "half_day": 1, "1_2_days": 2, "larger": 3}


def rank(tasks: tuple[Task, ...], state: dict) -> dict:
    by_id = {task.task_id: task for task in tasks}
    decisions = state.get("tasks", {})
    active = {"candidate", "in_progress"}
    nodes: dict[str, dict] = {}
    for task in tasks:
        entry = decisions.get(task.task_id, {})
        suggestions = []
        for match in re.finditer(r"\b(after|requires|first)\s+(TODO-\d{4,})\b", task.body, re.IGNORECASE):
            target = match.group(2).upper()
            if target in by_id and target != task.task_id and target not in entry.get("depends_on", []) and target not in entry.get("rejected_suggestions", []):
                suggestions.append({"target": target, "evidence": match.group(0)})
        nodes[task.task_id] = {
            "task": task.to_dict(), "decision": entry,
            "score": None, "terms": None, "group": "needs_estimate", "reasons": [], "suggestions": suggestions,
        }
    invalid: set[str] = set()
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(task_id: str, path: list[str]) -> None:
        if task_id in visiting:
            invalid.update(path[path.index(task_id):])
            return
        if task_id in visited:
            return
        visiting.add(task_id)
        for dep in decisions.get(task_id, {}).get("depends_on", []):
            if dep == task_id or dep not in by_id:
                invalid.add(task_id)
            else:
                visit(dep, [*path, dep])
        visiting.remove(task_id)
        visited.add(task_id)

    for task_id in by_id:
        visit(task_id, [task_id])
    for task_id, node in nodes.items():
        entry = node["decision"]
        status = entry.get("status", "candidate")
        if entry.get("recheck") or task_id in invalid:
            node["group"] = "needs_review"
            node["reasons"].append("changed task or invalid dependency graph")
        elif status in {"done", "declined"}:
            node["group"] = status
        elif status == "deferred":
            until = entry.get("defer_until")
            node["group"] = "needs_review" if until and until <= date.today().isoformat() else "deferred"
            node["reasons"].append("deferral expired" if node["group"] == "needs_review" else "deferred until " + str(until))
        elif any(decisions.get(dep, {}).get("status") != "done" for dep in entry.get("depends_on", [])):
            node["group"] = "blocked"
            node["reasons"].append("confirmed dependency incomplete")
        elif entry.get("impact") is None or entry.get("urgency") is None or entry.get("effort") not in PENALTY:
            node["group"] = "needs_estimate"
            node["reasons"].append("owner scores or effort missing")
        else:
            node["group"] = "ready"
            unlock = sum(1 for other_id, other in decisions.items()
                         if other_id in by_id and other.get("status") in active
                         and task_id in other.get("depends_on", []))
            terms = {"impact": 3 * entry["impact"], "urgency": 3 * entry["urgency"],
                     "unlock": 2 * min(unlock, 3), "effort_penalty": PENALTY[entry["effort"]]}
            node["terms"] = terms
            node["score"] = terms["impact"] + terms["urgency"] + terms["unlock"] - terms["effort_penalty"]

    def date_key(node: dict) -> str:
        value = node["task"]["added"]
        return value if value != "unknown" else date.max.isoformat()

    def remainder_key(node: dict) -> tuple:
        return (PENALTY[node["decision"]["effort"]], date_key(node), node["task"]["task_id"])

    ready = sorted((node for node in nodes.values() if node["group"] == "ready"),
                   key=lambda node: (-node["score"], *remainder_key(node)))
    remaining = ready.copy()
    shortlist: list[dict] = []
    while remaining and len(shortlist) < 3:
        best_score = remaining[0]["score"]
        tied = [node for node in remaining if node["score"] == best_score]
        represented = {node["task"]["section"] for node in shortlist}
        novel = [node for node in tied if node["task"]["section"] not in represented]
        chosen = min(novel or tied, key=remainder_key)
        ordinary = min(tied, key=remainder_key)
        shortlist.append({**chosen, "selection_reason": (
            "Equal score; preferred a section not yet in the shortlist"
            if chosen is not ordinary else "Highest remaining score and ordinary tie-break")})
        remaining.remove(chosen)
    return {"ready": ready, "shortlist": shortlist,
            "groups": {group: [node for node in nodes.values() if node["group"] == group]
                       for group in ("blocked", "needs_estimate", "needs_review", "deferred", "declined", "done")}}
