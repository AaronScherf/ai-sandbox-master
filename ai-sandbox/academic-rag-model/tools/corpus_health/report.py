from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone

from tools.corpus_health.finding import Finding


@dataclass
class ScanReport:
    run_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    duration_seconds: float = 0.0
    roots: dict = field(default_factory=dict)
    findings: list[Finding] = field(default_factory=list)
    files_considered: int = 0
    files_hashed: int = 0
    errors: list[str] = field(default_factory=list)
    complete: bool = True

    def to_dict(self) -> dict:
        result = asdict(self)
        result["findings"] = [finding.to_dict() for finding in self.findings]
        return result

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False, sort_keys=True)

    def to_text(self) -> str:
        lines = [
            f"Corpus health scan: {'complete' if self.complete else 'INCOMPLETE'}",
            f"Run: {self.run_at} ({self.duration_seconds:.2f}s)",
            f"Files considered: {self.files_considered}; content hashes: {self.files_hashed}",
        ]
        for name, root in self.roots.items():
            status = root.get("availability", "unknown")
            repo = root.get("git")
            suffix = f"; branch={repo.get('branch')} dirty={repo.get('dirty_count')}" if repo else ""
            lines.append(f"Root {name}: {status}{suffix}")
            if repo and repo.get("upstream_divergence"):
                divergence = repo["upstream_divergence"]
                lines.append(f"  upstream {divergence['upstream']}: ahead={divergence['ahead']} behind={divergence['behind']}")
            elif repo and repo.get("upstream_status") == "unavailable":
                lines.append(f"  upstream comparison unavailable: {repo.get('upstream_reason')}")
            if repo and repo.get("worktree_report"):
                lines.extend(f"  {line}" for line in repo["worktree_report"])
        if not self.findings:
            lines.append("No configured gaps found.")
        else:
            lines.append(f"Findings: {len(self.findings)}")
            for item in self.findings:
                target = f" -> {item.expected_output}" if item.expected_output else ""
                lines.append(f"- [{item.severity}] {item.kind}: {item.path}{target} ({item.evidence})")
        for error in self.errors:
            lines.append(f"ERROR: {error}")
        return "\n".join(lines)
