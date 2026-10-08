"""packet.py -- the contract between offline prep and the live session
(spec §3.1). Anything that produces a valid packet can drive a session."""
from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass

from agent.tutor.lint import lint_glossary
from agent.tutor.paths import TutorPaths
from agent.tutor.ratings import AXES, RATINGS

LAUNCH_SUFFIX = "How would you like to approach this problem?"
_HASHED = ("parts.json", "glossary.json", "rubric.json", os.path.join("sealed", "hints.md"), os.path.join("sealed", "solution.md"))


class PacketError(ValueError):
    pass


@dataclass
class Part:
    part_id: str
    statement: str
    concept_tags: list[str]
    expected_evidence: list[str]
    label: str | None = None
    chat_statement: str | None = None

    def launch_text(self) -> str:
        return f"{(self.chat_statement or self.statement).strip()}\n\n{LAUNCH_SUFFIX}"


@dataclass
class Packet:
    course: str
    problem_set: str
    parts: list[Part]
    glossary: dict
    rubric: dict


def sealed_section(markdown: str, part_id: str) -> str | None:
    m = re.search(rf"^##\s+{re.escape(part_id)}\s*$", markdown, re.M)
    if not m:
        return None
    rest = markdown[m.end():]
    nxt = re.search(r"^##\s+", rest, re.M)
    body = rest[:nxt.start()] if nxt else rest
    return body.strip() or None


def _read(packet_dir: str, rel: str) -> str:
    with open(os.path.join(packet_dir, rel), "r", encoding="utf-8") as f:
        return f.read()


def _load_json(packet_dir: str, rel: str):
    return json.loads(_read(packet_dir, rel))


def validate_packet(packet_dir: str) -> list[str]:
    errors: list[str] = []
    for rel in _HASHED:
        if not os.path.exists(os.path.join(packet_dir, rel)):
            errors.append(f"{rel.replace(os.sep, '/')} missing")
    if errors:
        return errors
    try:
        parts = _load_json(packet_dir, "parts.json")
        glossary = _load_json(packet_dir, "glossary.json")
        rubric = _load_json(packet_dir, "rubric.json")
    except json.JSONDecodeError as err:
        return [f"invalid JSON: {err}"]
    if not isinstance(parts, list) or not parts:
        return ["parts.json must be a non-empty list"]
    ids = [p.get("part_id") for p in parts]
    if len(set(ids)) != len(ids) or not all(ids):
        errors.append("parts.json: part_id values must be present and unique")
    hints, solution = _read(packet_dir, os.path.join("sealed", "hints.md")), _read(packet_dir, os.path.join("sealed", "solution.md"))
    for p in parts:
        pid = p.get("part_id", "?")
        if not str(p.get("statement", "")).strip():
            errors.append(f"{pid}: statement is empty")
        if not p.get("concept_tags"):
            errors.append(f"{pid}: concept_tags must be non-empty")
        if not p.get("expected_evidence"):
            errors.append(f"{pid}: expected_evidence must be non-empty")
        for axis in AXES:
            for rating in RATINGS:
                if not str(rubric.get(pid, {}).get(axis, {}).get(rating, "")).strip():
                    errors.append(f"rubric {pid}.{axis} missing '{rating}'")
        for name, text in (("hints.md", hints), ("solution.md", solution)):
            if sealed_section(text, pid) is None:
                errors.append(f"sealed/{name} has no '## {pid}' section")
    if not isinstance(glossary, dict) or not glossary:
        errors.append("glossary.json must be a non-empty object")
    else:
        for v in lint_glossary(glossary, [p.get("statement", "") for p in parts]):
            errors.append(f"{v.code}: {v.detail}")
    return errors


def compute_hash(packet_dir: str) -> str:
    h = hashlib.sha256()
    for rel in _HASHED:
        with open(os.path.join(packet_dir, rel), "rb") as f:
            h.update(rel.encode())
            h.update(f.read().replace(b"\r\n", b"\n"))
    return h.hexdigest()


def write_validated(packet_dir: str) -> None:
    with open(os.path.join(packet_dir, "validated.json"), "w", encoding="utf-8") as f:
        json.dump({"sha256": compute_hash(packet_dir)}, f)


def is_validated(packet_dir: str) -> bool:
    marker = os.path.join(packet_dir, "validated.json")
    try:
        with open(marker, "r", encoding="utf-8") as f:
            return json.load(f)["sha256"] == compute_hash(packet_dir)
    except (OSError, KeyError, json.JSONDecodeError):
        return False


def load_packet(paths: TutorPaths) -> Packet:
    if not is_validated(paths.packet_dir):
        raise PacketError(
            f"packet at {paths.packet_dir} is missing or changed since validation; run prep-submit first"
        )
    parts = [Part(**p) for p in _load_json(paths.packet_dir, "parts.json")]
    return Packet(
        course=paths.course, problem_set=paths.problem_set, parts=parts,
        glossary=_load_json(paths.packet_dir, "glossary.json"), rubric=_load_json(paths.packet_dir, "rubric.json"),
    )


def read_sealed(packet_dir: str) -> tuple[str, str]:
    return _read(packet_dir, os.path.join("sealed", "hints.md")), _read(packet_dir, os.path.join("sealed", "solution.md"))
