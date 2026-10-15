"""The drafting stages. Each module exposes make_tasks, validate_result and apply_result."""
from __future__ import annotations

import importlib

STAGES = ("seed", "fill", "link", "critic", "summary")


def get(name: str):
    if name not in STAGES:
        raise ValueError(f"unknown stage {name!r}; expected one of {STAGES}")
    return importlib.import_module(f"{__name__}.{name}")
