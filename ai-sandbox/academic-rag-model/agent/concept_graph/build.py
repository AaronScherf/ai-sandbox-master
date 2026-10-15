"""Validate a graph repo and build graph.json plus a single self-contained index.html."""
from __future__ import annotations

import hashlib
import html
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path

from .schema import EDITABLE_EDGE_FIELDS, EDITABLE_NODE_FIELDS, Graph, field_hash
from .store import GraphStore
from .validate import Issue, errors, validate

PACKAGE_DIR = Path(__file__).resolve().parent
VIEWER_DIR = PACKAGE_DIR / "viewer"
VENDOR_FILES = ("cytoscape.min.js", "katex.min.js")


class BuildError(Exception):
    pass


@dataclass
class BuildResult:
    graph_json: Path
    index_html: Path
    graph_version: str
    warnings: list[Issue]


def graph_payload(graph: Graph, layouts: list[dict] | None = None) -> dict:
    section_order = {s.id: s.order for s in graph.sections}
    sections = [s.model_dump(mode="json") for s in sorted(graph.sections, key=lambda s: s.order)]

    nodes = []
    for n in sorted(graph.nodes, key=lambda n: (section_order.get(n.section, 0), n.name.lower())):
        d = n.model_dump(mode="json", exclude_none=True)
        d["hashes"] = {f: field_hash(getattr(n, f)) for f in EDITABLE_NODE_FIELDS}
        nodes.append(d)

    edges = []
    for e in sorted(graph.edges, key=lambda e: e.id):
        d = e.model_dump(mode="json", exclude_none=True)
        d["hashes"] = {f: field_hash(getattr(e, f)) for f in EDITABLE_EDGE_FIELDS}
        edges.append(d)

    body = {
        "sections": sections,
        "nodes": nodes,
        "edges": edges,
        "vocab": graph.vocab.model_dump(mode="json"),
        "site": graph.site,
        "layouts": layouts or [],
    }
    canonical = json.dumps(body, sort_keys=True, ensure_ascii=False)
    version = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:12]
    return {"graph_version": version, **body}


def _script_safe(text: str) -> str:
    """Make text safe to place inside an inline <script> element."""
    return re.sub(r"</(script)", r"<\\/\1", text, flags=re.IGNORECASE)


def _read_vendor(vendor_dir: Path) -> str:
    parts = []
    for name in VENDOR_FILES:
        path = vendor_dir / name
        if not path.is_file():
            raise BuildError(f"missing vendored library {path}; run `python -m agent.concept_graph.vendor_fetch`")
        parts.append(path.read_text(encoding="utf-8"))
    return "\n;\n".join(parts)


def _read_layouts(root: Path, node_ids: set[str]) -> list[dict]:
    """config/layouts/*.json: shared layout presets, validated against the graph's concept ids."""
    folder = root / "config" / "layouts"
    out = []
    for path in sorted(folder.glob("*.json")) if folder.is_dir() else []:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            name, positions = raw["name"], raw["positions"]
            clean = {}
            for node_id, point in positions.items():
                x, y = float(point["x"]), float(point["y"])
                if not (math.isfinite(x) and math.isfinite(y)):
                    raise ValueError(f"position of {node_id!r} is not a finite number")
                clean[node_id] = {"x": x, "y": y}
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
            raise BuildError(f"{path.name}: not a valid layout file ({exc}); expected "
                             f'{{"name": ..., "positions": {{id: {{"x": n, "y": n}}}}}}') from exc
        unknown = sorted(set(clean) - node_ids)
        if unknown:
            raise BuildError(f"{path.name}: unknown concept id(s) {unknown[:5]}; rebuild the layout from the current graph")
        out.append({"id": path.stem, "name": str(name), "positions": clean})
    return out


def build(root: str | Path, vendor_dir: str | Path | None = None) -> BuildResult:
    root = Path(root)
    graph = GraphStore(root).read_all()
    issues = validate(graph)
    bad = errors(issues)
    if bad:
        raise BuildError("graph has errors:\n" + "\n".join(f"  [{i.code}] {i.message}" for i in bad))

    payload = graph_payload(graph, _read_layouts(root, {n.id for n in graph.nodes}))
    vendor = _read_vendor(Path(vendor_dir) if vendor_dir else VIEWER_DIR / "vendor")
    graph_json_text = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    inline_json = json.dumps(payload, ensure_ascii=False, sort_keys=True)

    parts = {
        "TITLE": html.escape(str(graph.site.get("title") or "Concept graph")),
        "STYLE": (VIEWER_DIR / "style.css").read_text(encoding="utf-8"),
        "GRAPH": _script_safe(inline_json),
        "VENDOR": _script_safe(vendor),
        "LOGIC": _script_safe((VIEWER_DIR / "logic.js").read_text(encoding="utf-8")),
        "APP": _script_safe((VIEWER_DIR / "app.js").read_text(encoding="utf-8")),
    }
    template = (VIEWER_DIR / "template.html").read_text(encoding="utf-8")
    page = re.sub(r"\{\{\{(\w+)\}\}\}", lambda m: parts[m.group(1)], template)

    out_dir = root / "build"
    out_dir.mkdir(parents=True, exist_ok=True)
    graph_json = out_dir / "graph.json"
    index_html = root / "index.html"
    graph_json.write_text(graph_json_text, encoding="utf-8", newline="\n")
    index_html.write_text(page, encoding="utf-8", newline="\n")
    return BuildResult(graph_json, index_html, payload["graph_version"], [i for i in issues if i.level == "warning"])
