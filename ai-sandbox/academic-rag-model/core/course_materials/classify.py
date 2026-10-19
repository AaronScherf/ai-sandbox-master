"""Build, store and reload a course's material catalog, with the owner's decisions applied on top."""
from __future__ import annotations

import json
import re
from pathlib import Path

from core.env.academic_hub_paths import find_containing_offering_label, to_resources_root
from core.env.frontmatter import parse_frontmatter

from .model import DECIDABLE, FORMATS, ROLES, Catalog, CatalogError, Material, normalize, rag_twin
from .signals import Facts, decide, pdf_shape

# Folders other pipelines write into a course (study guides, guide plans, tutoring logs): outputs, not materials.
GENERATED_DIRS = frozenset({"summaries", "guide_plans", "tutoring"})
_RAW_SCENE = re.compile(r"(?m)^excalidraw-plugin:")
_ISO_DATE = re.compile(r"20\d\d-\d\d-\d\d")
_MMDDYY = re.compile(r"^(\d\d)(\d\d)(\d\d)$")
_LEADING_NUMBER = re.compile(r"^(\d{1,3})[._ \-]")
_HEAD_CHARS = 20000


def catalog_path(hub_root, course: str) -> Path:
    return Path(hub_root) / ".index" / "materials" / f"{course}.json"


def decisions_path(hub_root, course: str) -> Path:
    return Path(hub_root) / ".index" / "materials" / f"{course}.decisions.json"


def _course_dir(hub_root, course: str) -> Path:
    return Path(hub_root) / "academic_notes" / course


def _read(path: Path, limit: int = _HEAD_CHARS) -> str:
    return path.read_text(encoding="utf-8", errors="ignore").replace("\r\n", "\n")[:limit]


def discover(hub_root, course: str) -> list[Path]:
    """Every converted .md in the course: one per source (the .rag.md when both exist), without raw Excalidraw
    scene files or other pipelines' output folders."""
    base = _course_dir(hub_root, course)
    found: dict[str, Path] = {}
    for f in sorted(base.rglob("*.md")):
        if set(f.relative_to(base).parts[:-1]) & GENERATED_DIRS:
            continue
        key = str(f)[: -len(".rag.md")] if f.name.endswith(".rag.md") else str(f)[: -len(".md")]
        if key in found and not f.name.endswith(".rag.md"):
            continue
        found[key] = f
    return [f for f in found.values() if not _RAW_SCENE.search(_read(f, 400))]


def date_from_stem(stem: str) -> str | None:
    m = _ISO_DATE.search(stem)
    if m:
        return m.group(0)
    m = _MMDDYY.match(stem)
    if m and 1 <= int(m.group(1)) <= 12 and 1 <= int(m.group(2)) <= 31:
        return f"20{m.group(3)}-{m.group(1)}-{m.group(2)}"
    return None


def _order(stem: str, date: str | None) -> list:
    m = _LEADING_NUMBER.match(stem)
    return [int(m.group(1)) if m else 1_000_000, date or "", stem.lower()]


def _book(path: str) -> str:
    """Short key for a textbook: the first word of its folder, e.g. Hansen_ECONOMETRICS_2022 -> hansen."""
    parts = path.split("/")
    if "chapters" in parts:
        folder = parts[parts.index("chapters") - 1]
    elif "processed_outputs" in parts and parts.index("processed_outputs") + 2 < len(parts):
        folder = parts[parts.index("processed_outputs") + 1]
    else:
        folder = parts[-2] if len(parts) > 1 else "book"
    return re.sub(r"[^a-z0-9]", "", re.split(r"[_\s\-]+", folder.strip())[0].lower()) or "book"


def _cards(hub_root, course: str) -> dict[str, str]:
    """Index-card doc_type by normalised path. The index belongs to another pipeline: a bad file only costs this signal."""
    p = Path(hub_root) / ".index" / f"{course}.json"
    try:
        cards = json.loads(p.read_text(encoding="utf-8")) if p.is_file() else []
    except ValueError:
        return {}
    out: dict[str, str] = {}
    for c in cards if isinstance(cards, list) else []:
        if not isinstance(c, dict) or not c.get("doc_type"):
            continue
        for key in (c.get("path"), c.get("rag_md_path")):
            norm = normalize(key or "")
            if norm:
                out[norm] = c["doc_type"]
    return out


def _source_pdf(hub_root, frontmatter: dict) -> Path | None:
    raw = (frontmatter.get("source_pdf") or "").strip().strip('"')
    if not raw.lower().endswith(".pdf"):
        return None
    p = Path(raw)
    return p if p.is_absolute() else Path(hub_root) / raw


def _offering(path: Path) -> str | None:
    try:
        return find_containing_offering_label(to_resources_root(str(path)))
    except ValueError:
        return None


def _material(norm: str, facts: Facts, offering: str | None) -> Material:
    d = decide(facts)
    stem = Material(path=norm).stem
    date = date_from_stem(stem)
    return Material(path=norm, role=d.role, format=d.format, offering=offering, date=date,
                    book=_book(norm) if d.role == "textbook" else None, order=_order(stem, date),
                    confidence=d.confidence, flagged=d.flagged,
                    evidence=[[v.signal, v.field, v.value, v.weight] for v in d.votes])


def classify_file(hub_root, path: Path, cards: dict | None = None) -> Material:
    norm = normalize(str(path)) or str(path).replace("\\", "/")
    fm, body = parse_frontmatter(_read(path)) if path.is_file() else ({}, "")
    pdf = _source_pdf(hub_root, fm)
    facts = Facts(path=norm, frontmatter=fm, body=body, card_doc_type=(cards or {}).get(norm),
                  pdf_shape=pdf_shape(pdf) if pdf else None)
    return _material(norm, facts, _offering(path))


def classify_path(path: str) -> Material:
    """Path-only classification for a path that is not in the catalog: no file read, no offering."""
    norm = normalize(path) or (path or "").replace("\\", "/")
    return _material(norm, Facts(path=norm, frontmatter={}, body=""), None)


def load_decisions(hub_root, course: str) -> dict[str, dict]:
    p = decisions_path(hub_root, course)
    if not p.is_file():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise CatalogError(f"decisions file is not valid JSON: {p} ({exc})") from exc
    if not isinstance(data, dict):
        raise CatalogError(f"decisions file must be a JSON object keyed by path: {p}")
    return data


def record_decision(hub_root, course: str, path: str, **fields) -> str:
    """Store the owner's decision for one file, or for every file under a folder. Returns the key used."""
    norm = normalize(path)
    if norm is None:
        raise CatalogError(f"not a path under the hub's academic_notes/ or academic_resources/: {path}")
    unknown = sorted(set(fields) - set(DECIDABLE) - {"exclude"})
    if unknown:
        raise ValueError(f"unknown decision field(s) {unknown}; allowed: {[*DECIDABLE, 'exclude']}")
    if fields.get("role") is not None and fields["role"] not in ROLES:
        raise ValueError(f"role must be one of {ROLES}")
    if fields.get("format") is not None and fields["format"] not in FORMATS:
        raise ValueError(f"format must be one of {FORMATS}")
    key = norm.rstrip("/") + "/" if (Path(hub_root) / norm).is_dir() else norm
    data = load_decisions(hub_root, course)
    data[key] = {**data.get(key, {}), **{k: v for k, v in fields.items() if v is not None and v is not False}}
    p = decisions_path(hub_root, course)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    return key


def _decision_for(path: str, decisions: dict) -> dict:
    """Folder decisions from the outermost in, then the file's own (or its .rag twin's)."""
    merged: dict = {}
    for key in sorted((k for k in decisions if k.endswith("/") and path.startswith(k)), key=len):
        merged.update(decisions[key])
    merged.update(decisions.get(path) or decisions.get(rag_twin(path)) or {})
    return merged


def _apply(m: Material, decision: dict) -> None:
    for key in DECIDABLE:
        if key in decision:
            setattr(m, key, decision[key])
    if m.role == "textbook" and not m.book:
        m.book = _book(m.path)
    m.flagged, m.decided_by = False, "review"


def classify_course(hub_root, course: str, *, write: bool = True) -> Catalog:
    if not _course_dir(hub_root, course).is_dir():
        return Catalog(course=course, materials=[])
    decisions = load_decisions(hub_root, course)
    cards = _cards(hub_root, course)
    files = discover(hub_root, course)
    materials: list[Material] = []
    for f in files:
        m = classify_file(hub_root, f, cards)
        decision = _decision_for(m.path, decisions)
        if decision.get("exclude"):
            continue
        if decision:
            _apply(m, decision)
        materials.append(m)
    seen = {p for p in (normalize(str(f)) for f in files) if p}
    seen |= {rag_twin(p) for p in seen}
    unknown = sorted(k for k in decisions
                     if not (any(p.startswith(k) for p in seen) if k.endswith("/") else k in seen))
    catalog = Catalog(course=course, materials=materials, unknown_decisions=unknown)
    if write:
        p = catalog_path(hub_root, course)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(catalog.to_json(), indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return catalog


def _stale(hub_root, course: str) -> bool:
    p = catalog_path(hub_root, course)
    if not p.is_file():
        return True
    built = p.stat().st_mtime
    d = decisions_path(hub_root, course)
    if d.is_file() and d.stat().st_mtime > built:
        return True
    return any(f.stat().st_mtime > built for f in _course_dir(hub_root, course).rglob("*.md"))


def load_catalog(hub_root, course: str, *, refresh: str = "if_stale") -> Catalog:
    """The stored catalog, rebuilt first when missing or older than the course's files or decisions."""
    if refresh == "always" or (refresh == "if_stale" and _stale(hub_root, course)):
        return classify_course(hub_root, course)
    p = catalog_path(hub_root, course)
    if not p.is_file():
        raise CatalogError(f"no catalog for {course}: run python -m core.course_materials.cli --course {course} classify")
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise CatalogError(f"catalog is not valid JSON: {p} ({exc})") from exc
    return Catalog.from_json(data, source=str(p))
