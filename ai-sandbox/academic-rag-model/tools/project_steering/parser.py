"""Read the narrative tracker without treating every Markdown bullet as a task."""

from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass
from datetime import date


_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_ADDED = re.compile(r"\(added (\d{4}-\d{2}-\d{2})(?:[;,] updated (\d{4}-\d{2}-\d{2}))?\)\s*$")
_SPACE = re.compile(r"\s+")


@dataclass(frozen=True)
class Task:
    task_id: str
    section: str
    title: str
    body: str
    added: str
    updated: str | None
    first_line: int
    last_line: int
    fingerprint: str
    provisional: bool = True
    urgent_suggestion: bool = False
    deferred_suggestion: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class Diagnostic:
    kind: str
    first_line: int
    last_line: int
    section: str
    excerpt: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class ParsedTracker:
    tasks: tuple[Task, ...]
    warnings: tuple[Diagnostic, ...]
    excluded: tuple[Diagnostic, ...]

    @property
    def coverage_complete(self) -> bool:
        return not self.warnings


def _normalize(text: str) -> str:
    return _SPACE.sub(" ", text).strip()


def parse_tracker(text: str) -> ParsedTracker:
    """Recognize dated top-level bullets; surface uncertain entries explicitly.

    Subsections and the pasted textbook example are retained as exclusions,
    never fed into the provisional ranked queue.
    """
    lines = text.splitlines()
    tasks: list[Task] = []
    warnings: list[Diagnostic] = []
    excluded: list[Diagnostic] = []
    section = ""
    in_subsection = False
    in_example = False
    pending: list[str] = []
    pending_start = 0
    pending_exclusion: str | None = None
    seen_identity: dict[str, int] = {}

    def finish() -> None:
        nonlocal pending, pending_start, pending_exclusion
        if not pending:
            return
        while pending and not pending[-1].strip():
            pending.pop()
        body = "\n".join(pending)
        end = pending_start + len(pending) - 1
        excerpt = _normalize(pending[0][2:])[:150]
        match = _ADDED.search(body)
        if pending_exclusion is not None:
            if pending_exclusion == "subsection" and match is not None:
                warnings.append(Diagnostic("dated_subsection_bullet", pending_start, end, section, excerpt))
            else:
                excluded.append(Diagnostic(pending_exclusion, pending_start, end, section, excerpt))
        elif match is None:
            warnings.append(Diagnostic("undated_bullet", pending_start, end, section, excerpt))
        else:
            try:
                added = date.fromisoformat(match.group(1)).isoformat()
                updated = date.fromisoformat(match.group(2)).isoformat() if match.group(2) else None
            except ValueError:
                warnings.append(Diagnostic("invalid_date", pending_start, end, section, excerpt))
            else:
                normalized = _normalize(body)
                fingerprint = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
                identity = hashlib.sha256((section + "\0" + normalized).encode("utf-8")).hexdigest()[:12]
                count = seen_identity.get(identity, 0) + 1
                seen_identity[identity] = count
                if count > 1:
                    warnings.append(Diagnostic("duplicate_body", pending_start, end, section, excerpt))
                task_id = f"P-{identity}" if count == 1 else f"P-{identity}-{count}"
                title = _ADDED.sub("", pending[0][2:]).strip()
                title = _normalize(title).strip(" *")[:150]
                lower_body = normalized.casefold()
                tasks.append(Task(
                    task_id=task_id,
                    section=section,
                    title=title,
                    body=body,
                    added=added,
                    updated=updated,
                    first_line=pending_start,
                    last_line=end,
                    fingerprint=fingerprint,
                    urgent_suggestion=bool(re.search(r"\burgent\b", pending[0], re.IGNORECASE)),
                    deferred_suggestion=("paused at user request" in lower_body or "deferred by the user" in lower_body),
                ))
        pending = []
        pending_start = 0
        pending_exclusion = None

    for number, line in enumerate(lines, start=1):
        heading = _HEADING.match(line)
        if heading:
            finish()
            depth = len(heading.group(1))
            if depth == 2:
                section = heading.group(2)
                in_subsection = False
                in_example = False
            elif depth > 2:
                in_subsection = True
            else:
                section = ""
            continue
        if line.startswith("- "):
            finish()
            pending = [line]
            pending_start = number
            pending_exclusion = "example" if in_example else "subsection" if in_subsection else "outside_section" if not section else None
            continue
        if pending:
            if not line.strip() or line[:1].isspace():
                pending.append(line)
                continue
            finish()
        if line.strip().casefold().startswith("example from "):
            in_example = True
    finish()
    return ParsedTracker(tuple(tasks), tuple(warnings), tuple(excluded))
