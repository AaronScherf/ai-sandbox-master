"""Reads an existing RAG summary and resolves the exact indexer chunks it
cites. No similarity search: each `indexer_source_refs` entry is looked up
by (file_id, chunk_id) in the course's chunk store. The corpus root is
derived from the guide's own path (ancestor of academic_notes/) rather
than from the refs' stored `root`, which can be stale.

Extra sources (a study_guide source plan) can add chunks beyond the guide's own refs, each tied
to the topic that may cite it."""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

from core.indexer.chunk_index import load_chunks

_FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n\n?", re.DOTALL)


class SourceError(Exception):
    pass


class MissingSourcesError(SourceError):
    def __init__(self, missing: list[str]):
        self.missing = missing
        super().__init__(
            "indexed chunks referenced by the guide were not found (stale index or "
            f"wrong file_id): {', '.join(missing)}"
        )


@dataclass(frozen=True)
class SourceChunk:
    label: str
    chunk_id: str
    file_id: str
    path: str
    citation: str
    text: str
    doc_type: str = ""
    offering: str = ""


@dataclass(frozen=True)
class ExtraSource:
    """A passage a topic may cite beyond the guide's own refs (from a study_guide source plan)."""
    topic: str
    chunk_id: str
    file_id: str
    path: str
    citation: str
    doc_type: str = ""
    offering: str = ""


def _norm_title(title: str) -> str:
    return " ".join(title.split()).casefold()


@dataclass
class GuideInput:
    path: Path
    root: Path
    course: str
    title: str
    body: str
    sha256: str
    rel_path: str
    sources: list[SourceChunk]
    topic_labels: dict[str, frozenset[str]] = field(default_factory=dict)

    def labels_for(self, title: str) -> set[str]:
        """The labels this topic may cite: its own planned set if it has one, else every label."""
        mapped = self.topic_labels.get(_norm_title(title))
        return set(mapped) if mapped is not None else {s.label for s in self.sources}


def locate_vault(guide_path: Path) -> tuple[Path, str]:
    """Returns (corpus root, course) from .../<root>/academic_notes/<course>/.../guide.md."""
    parts = guide_path.parts
    idxs = [i for i, p in enumerate(parts) if p.lower() == "academic_notes"]
    if not idxs or len(parts) - idxs[-1] < 3:
        raise SourceError(
            f"{guide_path} is not inside <corpus>/academic_notes/<course>/; cannot locate the corpus root"
        )
    i = idxs[-1]
    return Path(*parts[:i]), parts[i + 1]


def _field(front: str, key: str) -> str | None:
    m = re.search(rf"^{re.escape(key)}:[ \t]*(.*?)[ \t]*$", front, re.MULTILINE)
    return m.group(1) if m else None


def _parse_refs(raw: str | None) -> list[dict]:
    if raw is None:
        raise SourceError("guide frontmatter has no indexer_source_refs; it was not produced by the RAG report writer")
    try:
        refs = json.loads(raw)
    except json.JSONDecodeError as err:
        raise SourceError(f"indexer_source_refs is not valid JSON: {err}") from err
    if not isinstance(refs, list) or not refs:
        raise SourceError("indexer_source_refs must be a non-empty JSON list")
    for ref in refs:
        if not isinstance(ref, dict) or not all(isinstance(ref.get(k), str) and ref[k]
                                               for k in ("file_id", "chunk_id", "path")):
            raise SourceError("each indexer_source_refs entry needs string file_id, chunk_id and path")
    return refs


def load_guide(guide_path: str | Path, extra_sources: Sequence[ExtraSource] | None = None) -> GuideInput:
    path = Path(guide_path).resolve()
    if not path.is_file():
        raise SourceError(f"guide not found: {path}")
    raw_bytes = path.read_bytes()
    text = path.read_text(encoding="utf-8")  # universal newlines: CRLF -> LF
    match = _FRONTMATTER_RE.match(text)
    if not match:
        raise SourceError("guide has no YAML frontmatter")
    front, body = match.group(1), text[match.end():]

    refs = _parse_refs(_field(front, "indexer_source_refs"))
    root, course = locate_vault(path)

    title_raw = _field(front, "title")
    title = path.stem
    if title_raw:
        try:
            decoded = json.loads(title_raw)
            title = decoded if isinstance(decoded, str) and decoded else title
        except json.JSONDecodeError:
            title = title_raw

    by_id = {c["chunk_id"]: c for c in load_chunks(str(root), course)}
    sources: list[SourceChunk] = []
    missing: list[str] = []
    seen: set[tuple[str, str]] = set()
    for ref in refs:
        key = (ref["file_id"], ref["chunk_id"])
        if key in seen:
            continue
        seen.add(key)
        chunk = by_id.get(ref["chunk_id"])
        if chunk is None or chunk.get("file_id") != ref["file_id"]:
            missing.append(ref["chunk_id"])
            continue
        sources.append(SourceChunk(
            label=f"S{len(sources) + 1}", chunk_id=ref["chunk_id"], file_id=ref["file_id"],
            path=ref["path"], citation=str(ref.get("citation", "")), text=chunk["text"],
        ))

    topic_labels: dict[str, set[str]] = {}
    label_by_chunk = {s.chunk_id: s.label for s in sources}
    for extra in extra_sources or ():
        chunk = by_id.get(extra.chunk_id)
        if chunk is None or chunk.get("file_id") != extra.file_id:
            missing.append(extra.chunk_id)
            continue
        label = label_by_chunk.get(extra.chunk_id)
        if label is None:
            label = f"S{len(sources) + 1}"
            sources.append(SourceChunk(
                label=label, chunk_id=extra.chunk_id, file_id=extra.file_id, path=extra.path,
                citation=extra.citation, text=chunk["text"], doc_type=extra.doc_type, offering=extra.offering,
            ))
            label_by_chunk[extra.chunk_id] = label
        topic_labels.setdefault(_norm_title(extra.topic), set()).add(label)
    if missing:
        raise MissingSourcesError(missing)

    return GuideInput(
        path=path, root=root, course=course, title=title, body=body.strip("\n") + "\n",
        sha256=hashlib.sha256(raw_bytes).hexdigest(),
        rel_path=path.relative_to(root).as_posix(), sources=sources,
        topic_labels={k: frozenset(v) for k, v in topic_labels.items()},
    )
