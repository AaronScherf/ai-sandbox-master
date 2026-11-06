"""Corpus-health findings for folder names the owner has not classified yet (read-only).

Never writes hub_config.json: a name is stored only when the owner accepts it in `tools.hub_review`.
"""
from __future__ import annotations

from pathlib import Path

from core.env.hub_vocab_learn import propose_vocabulary
from core.env.hub_vocabulary import load_vocabulary
from core.indexer.review_envelope import proposal_items
from tools.corpus_health.finding import Finding

CONFIG_NAME = "hub_config.json"


def vocab_findings(hub_root: str) -> list[Finding]:
    config = Path(hub_root) / CONFIG_NAME
    if not config.is_file():  # without a vocabulary file `confirm` has nowhere to write
        return []
    items = proposal_items(propose_vocabulary(Path(hub_root), load_vocabulary(config)))
    findings = []
    for item in items:
        name = item.subject_ids[0]
        proposed = next((c["kind"] for c in item.candidates if c["proposed"]), None)
        courses = ", ".join(item.candidates[0]["courses"]) or "no course"
        findings.append(Finding(
            "vocab_name", "hub_config", CONFIG_NAME, name,
            f"folder name {name!r} is not in the vocabulary; seen in: {courses}"
            + (f"; proposed: {proposed}" if proposed else ""),
            suggested_action="python -m tools.hub_review page --hub-root HUB (accept a kind, or decline)",
            fingerprint=item.item_id, severity="actionable", cost_category="local_only",
            scope="vocab:" + name.casefold()))
    return findings
