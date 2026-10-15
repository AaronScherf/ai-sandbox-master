"""Compatibility shim: run manifests now live in core.agent_tasks.work. Import paths here keep working.

create_run keeps its graph-flavored signature and error text by passing repo_label."""
from __future__ import annotations

from pathlib import Path

from core.agent_tasks import work as _core_work
from core.agent_tasks.work import (  # noqa: F401
    STATUSES,
    Run,
    _check_run_id,
    _inside,
    load_run,
    render_worklist,
    task_entry,
)

from .tasks import Task


def create_run(work_root: str | Path, graph_repo: str | Path, stage: str, tasks: list[Task],
               run_id: str | None = None) -> Run:
    return _core_work.create_run(work_root, graph_repo, stage, tasks, run_id=run_id, repo_label="graph repo")
