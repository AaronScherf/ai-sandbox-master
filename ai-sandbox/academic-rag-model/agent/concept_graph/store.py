"""Read and update a graph repo's YAML (round-trip safe) as pydantic models."""
from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Literal

from pydantic import ValidationError
from ruamel.yaml import YAML
from ruamel.yaml.scalarstring import LiteralScalarString

from .schema import Edge, Graph, Node, Rejected, Section, Site, Vocab


class GraphDataError(Exception):
    """A graph data file is missing or malformed; the message names the file."""


def _yaml() -> YAML:
    y = YAML()
    y.preserve_quotes = True
    y.width = 4096
    y.indent(mapping=2, sequence=4, offset=2)
    return y


def _plain(obj):
    if isinstance(obj, dict):
        return {str(k): _plain(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_plain(v) for v in obj]
    if isinstance(obj, (dt.datetime, dt.date)):
        return obj.isoformat()
    if isinstance(obj, str):
        return str(obj)
    return obj


class GraphStore:
    def __init__(self, root: str | Path):
        self.root = Path(root)

    # -- low-level file access ------------------------------------------------
    def _load(self, path: Path):
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as fh:
            return _yaml().load(fh)

    def _save(self, path: Path, data) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="\n") as fh:
            _yaml().dump(data, fh)

    def _files(self, kind: Literal["node", "edge"]) -> list[Path]:
        folder = self.root / "data" / ("nodes" if kind == "node" else "edges")
        return sorted(folder.glob("*.yaml")) if folder.is_dir() else []

    @staticmethod
    def _model(cls, raw, path: Path):
        try:
            return cls(**_plain(raw))
        except (ValidationError, TypeError) as exc:
            raise GraphDataError(f"{path}: {exc}") from exc

    # -- reading ---------------------------------------------------------------
    def read_all(self) -> Graph:
        vocab_path = self.root / "config" / "vocab.yaml"
        raw_vocab = self._load(vocab_path)
        if raw_vocab is None:
            raise GraphDataError(f"missing vocab file: {vocab_path}")
        vocab = self._model(Vocab, raw_vocab, vocab_path)
        site_path = self.root / "config" / "site.yaml"
        site = self._model(Site, self._load(site_path) or {}, site_path).model_dump()

        sections_path = self.root / "data" / "sections.yaml"
        sections = [self._model(Section, s, sections_path) for s in (self._load(sections_path) or [])]

        nodes: list[Node] = []
        node_files: dict[str, str] = {}
        for path in self._files("node"):
            for raw in self._load(path) or []:
                node = self._model(Node, raw, path)
                nodes.append(node)
                node_files[node.id] = path.stem

        edges: list[Edge] = []
        for path in self._files("edge"):
            for raw in self._load(path) or []:
                edges.append(self._model(Edge, raw, path))

        rejected_path = self.root / "data" / "rejected.yaml"
        rejected = [self._model(Rejected, r, rejected_path) for r in (self._load(rejected_path) or [])]
        return Graph(
            sections=sections, nodes=nodes, edges=edges, rejected=rejected,
            vocab=vocab, site=site, node_files=node_files,
        )

    # -- writing ---------------------------------------------------------------
    def update_item(self, kind: Literal["node", "edge"], item_id: str, changes: dict) -> None:
        for path in self._files(kind):
            data = self._load(path) or []
            for item in data:
                if item.get("id") == item_id:
                    for key, value in changes.items():
                        item[key] = LiteralScalarString(value) if isinstance(value, str) and "\n" in value else value
                    self._save(path, data)
                    return
        raise KeyError(f"{kind} {item_id!r} not found")

    def remove_item(self, kind: Literal["node", "edge"], item_id: str) -> None:
        for path in self._files(kind):
            data = self._load(path) or []
            for index, item in enumerate(data):
                if item.get("id") == item_id:
                    del data[index]
                    self._save(path, data)
                    return
        raise KeyError(f"{kind} {item_id!r} not found")

    # -- adding new items (used by the drafting stages) ----------------------------
    @staticmethod
    def _prepare(item: dict) -> dict:
        """A plain, YAML-ready copy: None values dropped, multi-line strings kept as literal blocks."""
        out = {}
        for key, value in item.items():
            if value is None:
                continue
            if isinstance(value, dict):
                value = GraphStore._prepare(value)
            elif isinstance(value, list):
                value = [GraphStore._prepare(v) if isinstance(v, dict) else v for v in value]
            elif isinstance(value, str) and "\n" in value:
                value = LiteralScalarString(value if value.endswith("\n") else value + "\n")
            out[key] = value
        return out

    def _append_items(self, path: Path, items: list[dict]) -> None:
        data = self._load(path)
        if data is None:
            data = []
        for item in items:
            data.append(self._prepare(item))
        if hasattr(data, "fa"):
            data.fa.set_block_style()
        self._save(path, data)

    def add_sections(self, sections: list[dict]) -> None:
        existing = {s.id for s in self.read_all().sections}
        for s in sections:
            if s["id"] in existing:
                raise ValueError(f"section {s['id']!r} already exists")
            existing.add(s["id"])
        self._append_items(self.root / "data" / "sections.yaml", sections)

    def add_nodes(self, section_id: str, nodes: list[dict]) -> None:
        existing = {n.id for n in self.read_all().nodes}
        for n in nodes:
            if n["id"] in existing:
                raise ValueError(f"node {n['id']!r} already exists")
            if n.get("section") != section_id:
                raise ValueError(f"node {n['id']!r} has section {n.get('section')!r}, expected {section_id!r}")
            existing.add(n["id"])
        self._append_items(self.root / "data" / "nodes" / f"{section_id}.yaml", nodes)

    def add_edges(self, edges: list[dict]) -> None:
        graph = self.read_all()
        order = {s.id: s.order for s in graph.sections}
        section_of = {n.id: n.section for n in graph.nodes}
        existing = {e.id for e in graph.edges}
        by_file: dict[str, list[dict]] = {}
        for e in edges:
            if e["id"] in existing:
                raise ValueError(f"edge {e['id']!r} already exists")
            for end in (e["source"], e["target"]):
                if end not in section_of:
                    raise ValueError(f"edge {e['id']!r} refers to unknown node {end!r}")
            existing.add(e["id"])
            home = max((section_of[e["source"]], section_of[e["target"]]), key=lambda s: order.get(s, 0))
            by_file.setdefault(home, []).append(e)
        for section_id, items in by_file.items():
            self._append_items(self.root / "data" / "edges" / f"{section_id}.yaml", items)

    def add_vocab(self, kinds=(), topics=()) -> None:
        path = self.root / "config" / "vocab.yaml"
        data = self._load(path)
        if data is None:
            raise GraphDataError(f"missing vocab file: {path}")
        for key, wanted in (("kinds", kinds), ("topics", topics)):
            for entry in wanted:
                if entry not in data[key]:
                    data[key].append(entry)
        self._save(path, data)

    def add_rejected(self, kind: Literal["node", "edge"], item_id: str) -> None:
        path = self.root / "data" / "rejected.yaml"
        data = self._load(path)
        if data is None:
            data = []
        data.append({"kind": kind, "id": item_id})
        if hasattr(data, "fa"):  # a file that started as "[]" loads as a flow-style list; keep the file readable
            data.fa.set_block_style()
        self._save(path, data)
