"""Pydantic models and shared constants for the concept graph (see the design spec)."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SLUG = r"^[a-z0-9][a-z0-9-]*$"

EDGE_TYPES = (
    "is_a",
    "has_property",
    "defined_on",
    "component_of",
    "implies",
    "iff",
    "hypothesis_of",
    "yields",
    "counterexample_to",
)
CONDITION_REQUIRED = ("implies", "iff")
VIA_ALLOWED = ("implies", "iff")
VIA_KINDS = ("theorem", "lemma")
DEFINITIONAL_TYPES = ("is_a", "defined_on", "has_property", "component_of")
LOGICAL_TYPES = ("implies", "hypothesis_of", "yields")
EDITABLE_NODE_FIELDS = ("gist", "explanation", "formal", "example")
EDITABLE_EDGE_FIELDS = ("condition", "explanation")

Status = Literal["proposed", "verified"]
SectionState = Literal["taught", "in_progress", "planned"]


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Citation(_Model):
    source: str
    ref: str


class Critic(_Model):
    verdict: Literal["supports", "weak", "unsupported"]
    note: str = ""


class Provenance(_Model):
    driver: str
    agent: str | None = None
    model: str | None = None
    run: str | None = None


class _Item(_Model):
    """Review bookkeeping shared by nodes and edges."""

    citations: list[Citation] = Field(default_factory=list)
    status: Status = "proposed"
    critic: Critic | None = None
    provenance: Provenance | None = None
    reviewed_by: str | None = None
    reviewed_on: str | None = None


class Section(_Model):
    id: str = Field(pattern=SLUG)
    title: str
    order: float
    state: SectionState
    lectures: list[str] = Field(default_factory=list)
    syllabus_ref: str | None = None
    topic: str | None = None
    short: str | None = None
    summary: str | None = None
    summary_hash: str | None = None


class Node(_Item):
    id: str = Field(pattern=SLUG)
    name: str
    kind: str
    section: str
    topic: str
    introduced_in: str | None = None
    gist: str = ""
    explanation: str = ""
    formal: str | None = None
    example: str | None = None


class Edge(_Item):
    id: str
    source: str = Field(pattern=SLUG)
    type: str
    target: str = Field(pattern=SLUG)
    condition: str | None = None
    via: str | None = None
    explanation: str = ""


class Vocab(_Model):
    kinds: list[str]
    topics: list[str]


class Site(_Model):
    """config/site.yaml: the only per-site settings, shipped into the public page, so validated like the rest."""

    title: str = "Concept graph"
    repo: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


class SeedConfig(_Model):
    """config/seed.yaml (optional): what the owner knows about a course that its files cannot say.

    scope:             free text, shown on the seed card (what is in and out of this graph)
    must_include:      concepts that must end up as nodes; an entry is a name or a list of aliases
    textbook_chapters: source key or textbook folder name -> chapter numbers whose section headings should be shown
    min_nodes_per_section: every section must end up with at least this many nodes (the required list is a floor,
                       not the target; raise this to demand a fuller skeleton)
    fill_hints:        node id -> what the owner wants that node's explanation to cover (shown on its fill card)"""

    scope: str = ""
    must_include: list[str | list[str]] = Field(default_factory=list)
    textbook_chapters: dict[str, list[int]] = Field(default_factory=dict)
    min_nodes_per_section: int = Field(default=1, ge=1)
    fill_hints: dict[str, str] = Field(default_factory=dict)


class Rejected(_Model):
    kind: Literal["node", "edge"]
    id: str


@dataclass
class Graph:
    sections: list[Section]
    nodes: list[Node]
    edges: list[Edge]
    rejected: list[Rejected]
    vocab: Vocab
    site: dict = field(default_factory=dict)
    node_files: dict[str, str] = field(default_factory=dict)


def edge_id(source: str, type_: str, target: str) -> str:
    return f"{source}--{type_}--{target}"


def member_hash(ids: list[str]) -> str:
    """Stable hash of a section's membership; a summary drafted for other members is stale."""
    return hashlib.sha256(("\n").join(sorted(ids)).encode("utf-8")).hexdigest()[:16]


def field_hash(value: str | None) -> str:
    """Stable 16-hex-char hash of an editable field; used to detect stale edits."""
    return hashlib.sha256((value or "").strip().encode("utf-8")).hexdigest()[:16]
