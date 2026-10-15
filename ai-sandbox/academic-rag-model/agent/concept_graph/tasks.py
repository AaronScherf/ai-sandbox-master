"""Compatibility shim: task cards now live in core.agent_tasks.tasks. Import paths here keep working."""
from __future__ import annotations

from core.agent_tasks.tasks import (  # noqa: F401
    Passage,
    ResultError,
    Task,
    _FENCE,
    _plain,
    extract_result,
    parse_result_text,
    render_card,
    result_from_response,
)
