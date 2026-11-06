"""Corpus-health findings for duplicate hub_ids (read-only)."""
from __future__ import annotations

from core.indexer.duplicate_ids import find_duplicate_hub_ids
from tools.corpus_health.finding import Finding


def duplicate_findings(hub_root: str) -> list[Finding]:
    return [
        Finding("duplicate_hub_id", "academic_notes", paths[0], hub_id,
                f"hub_id {hub_id} is shared by: {', '.join(paths)}",
                suggested_action="python -m tools.write_hub_ids --hub-root HUB --fix-duplicates (dry run), then --apply",
                fingerprint="dup:" + hub_id + ":" + "|".join(paths), severity="actionable",
                cost_category="local_only")
        for hub_id, paths in find_duplicate_hub_ids(hub_root).items()
    ]
