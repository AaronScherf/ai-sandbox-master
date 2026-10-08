from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Finding:
    kind: str
    root: str
    path: str
    title: str
    evidence: str
    expected_output: str | None = None
    suggested_action: str | None = None
    fingerprint: str | None = None
    severity: str = "actionable"
    finding_id: str | None = None
    cost_category: str = "unknown"
    batch_approval_allowed: bool = False
    scope: str = ""

    def to_dict(self) -> dict:
        return asdict(self)
