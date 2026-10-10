"""The private work directory: task cards and a manifest for one run.

Cards and the manifest hold retrieved source text, so the work directory must never sit inside a graph repo."""
from __future__ import annotations

import datetime as dt
import json
import os
from dataclasses import dataclass
from pathlib import Path

from .tasks import Task, render_card

STATUSES = ("pending", "filled", "applied", "bounced", "skipped")


@dataclass
class Run:
    root: Path
    data: dict

    @property
    def run_id(self) -> str:
        return self.data["run_id"]

    @property
    def stage(self) -> str:
        return self.data["stage"]

    @property
    def tasks(self) -> list[dict]:
        return self.data["tasks"]

    def task(self, task_id: str) -> dict:
        for t in self.data["tasks"]:
            if t["id"] == task_id:
                return t
        raise KeyError(f"task {task_id!r} is not in run {self.run_id}")

    def card_path(self, task_id: str) -> Path:
        return self.root / "cards" / f"{task_id}.md"

    def _save(self) -> None:
        path = self.root / "manifest.json"
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(self.data, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n")
        os.replace(tmp, path)
        (self.root / "worklist.md").write_text(render_worklist(self), encoding="utf-8", newline="\n")

    def set_status(self, task_id: str, status: str, reasons: list[str] | None = None) -> None:
        if status not in STATUSES:
            raise ValueError(f"unknown status {status!r}; expected one of {STATUSES}")
        entry = self.task(task_id)
        entry["status"] = status
        entry["reasons"] = list(reasons or [])
        self._save()

    def bounce(self, task_id: str, reasons: list[str]) -> None:
        entry = self.task(task_id)
        entry["attempts"] = entry.get("attempts", 0) + 1
        path = self.card_path(task_id)
        text = path.read_text(encoding="utf-8")
        cut = text.find("\n## Bounced")
        if cut != -1:
            text = text[:cut]
        note = "\n## Bounced\nFix only what is listed, in the same ```yaml block above, then ask for a re-submit.\n" + \
               "\n".join(f"- {r}" for r in reasons) + "\n"
        path.write_text(text.rstrip("\n") + "\n" + note, encoding="utf-8", newline="\n")
        self.set_status(task_id, "bounced", reasons)


def render_worklist(run: Run) -> str:
    lines = [f"# Worklist: run {run.run_id} (stage: {run.stage})", "",
             "Fill the yaml block under `## Result` in each card listed as pending or bounced.", "",
             "| task | status | attempts | note |", "|---|---|---|---|"]
    for t in run.tasks:
        note = "; ".join(t.get("reasons") or [])
        lines.append(f"| {t['id']} | {t['status']} | {t.get('attempts', 0)} | {note} |")
    return "\n".join(lines) + "\n"


def _inside(child: Path, parent: Path) -> bool:
    child, parent = child.resolve(), parent.resolve()
    return child == parent or parent in child.parents


def create_run(work_root: str | Path, graph_repo: str | Path, stage: str, tasks: list[Task],
               run_id: str | None = None) -> Run:
    work_root, graph_repo = Path(work_root), Path(graph_repo)
    if _inside(work_root, graph_repo):
        raise ValueError(f"the work directory {work_root} is inside the graph repo {graph_repo}; "
                         f"cards hold source text and must stay private")
    if run_id is None:
        base = f"{stage}-{dt.datetime.now():%Y%m%d-%H%M%S}"
        run_id, n = base, 1
        while (work_root / run_id).exists():
            n += 1
            run_id = f"{base}-{n}"
    root = work_root / run_id
    (root / "cards").mkdir(parents=True, exist_ok=False)
    data = {
        "run_id": run_id, "stage": stage, "created": dt.datetime.now().isoformat(timespec="seconds"),
        "graph_repo": str(graph_repo),
        "tasks": [{
            "id": t.id, "subject": t.subject, "status": "pending", "attempts": 0, "reasons": [],
            "offered": [list(p.offered) for p in t.passages],
            "passages": [{"id": p.id, "source": p.source, "ref": p.ref, "text": p.text, "path": p.path} for p in t.passages],
        } for t in tasks],
    }
    run = Run(root, data)
    for t in tasks:
        run.card_path(t.id).write_text(render_card(t), encoding="utf-8", newline="\n")
    run._save()
    return run


def load_run(work_root: str | Path, run_id: str) -> Run:
    root = Path(work_root) / run_id
    path = root / "manifest.json"
    if not path.is_file():
        raise FileNotFoundError(f"no run {run_id!r} under {work_root}")
    return Run(root, json.loads(path.read_text(encoding="utf-8")))
