"""Deterministic views and atomic publication for tracker scans."""

from __future__ import annotations

import json
import os
import tempfile
import uuid
from datetime import datetime, timezone
from html import escape
from pathlib import Path

from tools.project_steering.parser import ParsedTracker, Task


def make_report(parsed: ParsedTracker, *, tracker: Path, source_hash: str, source_bytes: int,
                duration_seconds: float, ranking: dict | None = None, revision: int = 0) -> dict:
    ordered = sorted(parsed.tasks, key=lambda task: (
        not task.urgent_suggestion, task.section.casefold(), task.title.casefold(), task.task_id
    ))
    return {
        "version": 1,
        "run_at": datetime.now(timezone.utc).isoformat(),
        "tracker": str(tracker.resolve()),
        "source_sha256": source_hash,
        "source_bytes": source_bytes,
        "duration_seconds": round(duration_seconds, 3),
        "coverage_complete": parsed.coverage_complete,
        "state_revision": revision,
        "task_count": len(ordered),
        "warning_count": len(parsed.warnings),
        "excluded_count": len(parsed.excluded),
        "tasks": [task.to_dict() for task in ordered],
        "warnings": [warning.to_dict() for warning in parsed.warnings],
        "excluded": [item.to_dict() for item in parsed.excluded],
        "notices": [item.to_dict() for item in parsed.notices],
        "ranking": ranking,
    }


def _task_line(task: dict) -> str:
    flags = []
    if task["urgent_suggestion"]:
        flags.append("URGENT wording; unreviewed")
    if task["deferred_suggestion"]:
        flags.append("defer wording; unreviewed")
    suffix = f" — {', '.join(flags)}" if flags else ""
    return f"- **{escape(task['title'])}** ({task['task_id']}, source line {task['first_line']}){suffix}"


def render_markdown(report: dict) -> str:
    lines = [
        "# Generated project work view",
        "",
        f"Source: `{report['tracker']}` at SHA-256 `{report['source_sha256']}`.",
        f"Coverage: {'complete' if report['coverage_complete'] else 'PARTIAL'}; "
        f"{report['task_count']} tasks; {report['warning_count']} unresolved entries; "
        f"{report['excluded_count']} structured exclusions.",
        "",
        ("Owner-reviewed rankings appear below where available; unknown fields stay unranked."
         if report.get("ranking") else
         "This provisional view has no owner-reviewed scores, effort estimates, or confirmed dependencies. "
         "The order below is a reading order, not an authoritative priority ranking."),
        "",
    ]
    ranking = report.get("ranking")
    if ranking:
        lines.extend(["## Next three for review", ""])
        for node in ranking["shortlist"]:
            task = node["task"]
            lines.append(f"- **{escape(task['title'])}** ({task['task_id']}; score {node['score']}; "
                         f"impact +{node['terms']['impact']}, urgency +{node['terms']['urgency']}, "
                         f"unlock +{node['terms']['unlock']}, effort -{node['terms']['effort_penalty']})")
        if not ranking["shortlist"]:
            lines.append("- No owner-scored ready tasks yet.")
        lines.extend(["", "## Full scored order", ""])
        for node in ranking["ready"]:
            lines.append(f"- {escape(node['task']['title'])} ({node['task']['task_id']}; score {node['score']})")
        lines.append("")
        for group, nodes in ranking["groups"].items():
            if nodes:
                lines.extend([f"## {group.replace('_', ' ').title()}", ""])
                for node in nodes:
                    lines.append(f"- {escape(node['task']['title'])} ({node['task']['task_id']})")
                lines.append("")
    urgent = [task for task in report["tasks"] if task["urgent_suggestion"]]
    if urgent:
        lines.extend(["## Explicit urgency signals to review", ""])
        lines.extend(_task_line(task) for task in urgent)
        lines.append("")
    sections: dict[str, list[dict]] = {}
    for task in report["tasks"]:
        sections.setdefault(task["section"], []).append(task)
    for section in sorted(sections, key=str.casefold):
        lines.extend([f"## {escape(section)}", ""])
        lines.extend(_task_line(task) for task in sections[section])
        lines.append("")
    if report["warnings"]:
        lines.extend(["## Needs classification", ""])
        for warning in report["warnings"]:
            lines.append(f"- Line {warning['first_line']} ({warning['kind']}): {escape(warning['excerpt'])}")
        lines.append("")
    if report.get("notices"):
        lines.extend(["## Classification notes", ""])
        for notice in report["notices"]:
            lines.append(f"- Line {notice['first_line']} ({notice['kind']}): {escape(notice['excerpt'])}")
        lines.append("")
    if report["excluded"]:
        lines.extend(["## Structured notes excluded from task ranking", ""])
        for item in report["excluded"]:
            lines.append(f"- Line {item['first_line']} ({item['kind']}): {escape(item['excerpt'])}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _write_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def publish_report(state_dir: Path, report: dict, markdown: str) -> dict:
    """Publish a complete pair, then atomically point readers to that pair."""
    generation = uuid.uuid4().hex
    json_name = f"runs/scan-{generation}.json"
    markdown_name = f"runs/ranked-{generation}.md"
    _write_atomic(state_dir / json_name, json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    _write_atomic(state_dir / markdown_name, markdown)
    latest = {
        "version": 1,
        "snapshot": json_name,
        "ranked_view": markdown_name,
        "source_sha256": report["source_sha256"],
        "run_at": report["run_at"],
    }
    _write_atomic(state_dir / "latest.json", json.dumps(latest, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return latest
