"""Pure, model-free views of proposed and owner-approved agent routes."""

from __future__ import annotations

from datetime import date

from tools.project_steering.parser import Task

FIELDS = ("agent", "complexity", "difficulty", "context")
VALUES = {
    "agent": frozenset({"claude", "gemini", "codex", "needs_human"}),
    "complexity": frozenset({"trivial", "moderate", "complex"}),
    "difficulty": frozenset({"low", "medium", "high"}),
    "context": frozenset({"self_contained", "needs_repo_context", "needs_external_context"}),
}
AGENTS = ("claude", "gemini", "codex", "needs_human")


def route_for(task: Task, entry: dict) -> dict:
    """Resolve only approved values; keep Claude suggestions visibly separate."""
    stale = bool(entry.get("suggested_fingerprint") and
                 entry["suggested_fingerprint"] != task.fingerprint)
    approved = {field: entry.get(field) for field in FIELDS}
    proposed = {field: entry.get(field + "_suggested") for field in FIELDS}
    fully_approved = all(approved[field] in VALUES[field] and entry.get(field + "_source") == "owner"
                         for field in FIELDS)
    has_proposal = any(proposed.values())
    return {
        "task_id": task.task_id,
        "agent": approved["agent"] if fully_approved else "needs_human",
        "agent_source": "owner" if fully_approved else "fallback",
        "approved": approved,
        "proposed": proposed,
        "proposal_status": "stale" if stale and has_proposal else "unapproved" if has_proposal else "none",
        "suggested_batch": entry.get("suggested_batch"),
        "not_before": entry.get("not_before"),
        "fully_approved": fully_approved,
    }


def route_view(tasks: tuple[Task, ...], state: dict, ranking: dict, *, today: date | None = None) -> dict:
    """Build actual and proposed batches without treating drafts as assignments."""
    today = today or date.today()
    decisions = state.get("tasks", {})
    rows = {task.task_id: route_for(task, decisions.get(task.task_id, {})) for task in tasks}
    approved = {agent: [] for agent in AGENTS}
    proposed = {agent: [] for agent in AGENTS}
    blocked_groups = {"blocked", "needs_review", "deferred", "declined", "done", "not_before"}
    groups = {node["task"]["task_id"]: group
              for group, nodes in ranking["groups"].items() for node in nodes}
    for task in tasks:
        task_id = task.task_id
        entry = decisions.get(task_id, {})
        row = rows[task_id]
        if entry.get("vanished") or entry.get("recheck") or groups.get(task_id) in blocked_groups:
            continue
        if entry.get("not_before") and entry["not_before"] > today.isoformat():
            continue
        if entry.get("status", "candidate") not in {"candidate", "in_progress"}:
            continue
        if row["fully_approved"]:
            approved[row["agent"]].append(task_id)
        elif row["proposal_status"] == "unapproved":
            proposed[row["proposed"].get("agent") or "needs_human"].append(task_id)
        else:
            approved["needs_human"].append(task_id)
    return {"tasks": rows, "approved_batches": approved, "proposed_batches": proposed}
