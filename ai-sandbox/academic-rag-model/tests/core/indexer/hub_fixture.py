"""Fixture hub helpers for path-resilience tests: tmp_path only, no model client."""
from __future__ import annotations

from pathlib import Path


def make_hub(tmp_path: Path) -> Path:
    hub = tmp_path / "hub"
    for rel in (
        "academic_notes/econ/lecture_notes",
        "academic_notes/econ/problem_sets",
        "academic_resources/econ",
    ):
        (hub / rel).mkdir(parents=True)
    return hub


def write_note(hub: Path, rel: str, frontmatter: dict[str, str], body: str) -> Path:
    path = hub / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"{key}: {value}" for key, value in frontmatter.items()]
    path.write_text("---\n" + "\n".join(lines) + "\n---\n\n" + body, encoding="utf-8", newline="\n")
    return path
