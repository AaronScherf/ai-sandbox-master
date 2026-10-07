# agent/study_guide/spec.py
"""Guide spec: the declarative description of one study guide (topics, source rules,
per-stage models, prompt). Specs are code configuration, not study content: they hold
topics, instructions and section labels, never source text. Format: TOML."""
from __future__ import annotations

import hashlib
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

DEFAULT_MODEL = "gemini-3.8-flash"
VALID_PROMPTS = ("tutor_v1", "guide_v1")
VALID_LABEL_MATCH = ("heading-prefix", "citation-substring")
_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_]*$")


class SpecError(Exception):
    pass


@dataclass(frozen=True)
class SourceRule:
    kind: str
    book: str = ""
    labels: tuple[str, ...] = ()
    exclude_labels: tuple[str, ...] = ()
    file: str = ""
    query: str = ""
    max: int = 12
    doc_types: tuple[str, ...] = ("textbook",)
    exclude_guide: str = ""
    min_score: float = 0.0
    max_per_file: int = 0


@dataclass(frozen=True)
class TopicSpec:
    title: str
    instruction: str
    sources: tuple[SourceRule, ...]


@dataclass(frozen=True)
class ComparisonSpec:
    title: str
    instruction: str
    from_topics: tuple[str, ...]
    take: int = 3


@dataclass(frozen=True)
class NoteSpec:
    heading: str
    body: str


@dataclass(frozen=True)
class GuideSpec:
    id: str
    title: str
    course: str
    draft_model: str
    enhance_model: str
    prompt: str
    label_match: str
    top_k: int
    file_top_k: int
    notes: tuple[NoteSpec, ...]
    topics: tuple[TopicSpec, ...]
    comparisons: tuple[ComparisonSpec, ...]
    path: str
    sha256: str


_RULE_KEYS = {
    "section": {"kind", "book", "labels", "exclude_labels", "query", "max"},
    "file": {"kind", "file", "query", "max"},
    "discover": {"kind", "query", "doc_types", "exclude_guide", "max", "min_score", "max_per_file"},
}


def _check_keys(table: dict, allowed: set[str], where: str) -> None:
    extra = set(table) - allowed
    if extra:
        raise SpecError(f"{where}: unknown key(s) {sorted(extra)}")


def _str(table: dict, key: str, where: str, default: str | None = None) -> str:
    if key not in table:
        if default is None:
            raise SpecError(f"{where}: missing '{key}'")
        return default
    value = table[key]
    if not isinstance(value, str) or not value.strip():
        raise SpecError(f"{where}: '{key}' must be a non-empty string")
    return value


def _int(table: dict, key: str, where: str, default: int, minimum: int = 1) -> int:
    value = table.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise SpecError(f"{where}: '{key}' must be an integer >= {minimum}")
    return value


def _strs(table: dict, key: str, where: str, default: tuple[str, ...] = (), required: bool = False) -> tuple[str, ...]:
    if key not in table:
        if required:
            raise SpecError(f"{where}: missing '{key}'")
        return default
    value = table[key]
    ok = isinstance(value, list) and all(isinstance(x, str) and x.strip() for x in value)
    if not ok or (required and not value):
        raise SpecError(f"{where}: '{key}' must be a list of non-empty strings" + (" (at least one)" if required else ""))
    return tuple(value)


def _optional_str(table: dict, key: str, where: str) -> str:
    value = table.get(key, "")
    if not isinstance(value, str):
        raise SpecError(f"{where}: '{key}' must be a string")
    return value


def _parse_rule(raw: object, where: str) -> SourceRule:
    if not isinstance(raw, dict):
        raise SpecError(f"{where}: must be a table")
    kind = raw.get("kind")
    if kind not in _RULE_KEYS:
        raise SpecError(f"{where}: 'kind' must be one of {sorted(_RULE_KEYS)}")
    _check_keys(raw, _RULE_KEYS[kind], where)
    maximum = _int(raw, "max", where, 12)
    if kind == "section":
        return SourceRule(
            kind, book=_str(raw, "book", where), labels=_strs(raw, "labels", where, required=True),
            exclude_labels=_strs(raw, "exclude_labels", where), query=_str(raw, "query", where), max=maximum)
    if kind == "file":
        return SourceRule(kind, file=_str(raw, "file", where), query=_optional_str(raw, "query", where), max=maximum)
    min_score = raw.get("min_score", 0.0)
    if isinstance(min_score, bool) or not isinstance(min_score, (int, float)) or not 0 <= min_score <= 1:
        raise SpecError(f"{where}: 'min_score' must be a number between 0 and 1")
    doc_types = _strs(raw, "doc_types", where, default=("textbook",))
    if not doc_types:
        raise SpecError(f"{where}: 'doc_types' must not be empty")
    return SourceRule(
        kind, query=_str(raw, "query", where), doc_types=doc_types,
        exclude_guide=_optional_str(raw, "exclude_guide", where), max=maximum,
        min_score=float(min_score), max_per_file=_int(raw, "max_per_file", where, 0, minimum=0))


def load_spec(path: str | Path) -> GuideSpec:
    p = Path(path)
    if not p.is_file():
        raise SpecError(f"guide spec not found: {p}")
    raw_bytes = p.read_bytes()
    try:
        data = tomllib.loads(raw_bytes.decode("utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as err:
        raise SpecError(f"{p.name}: invalid TOML: {err}") from err
    _check_keys(data, {"guide", "models", "draft", "note", "topic", "comparison"}, "spec")

    guide = data.get("guide")
    if not isinstance(guide, dict):
        raise SpecError("spec: missing [guide] table")
    _check_keys(guide, {"id", "title", "course"}, "[guide]")
    guide_id = _str(guide, "id", "[guide]")
    if not _ID_RE.match(guide_id):
        raise SpecError(f"[guide]: id {guide_id!r} must be lowercase letters, digits and underscores")

    models = data.get("models", {})
    _check_keys(models, {"draft", "enhance"}, "[models]")
    draft = data.get("draft", {})
    _check_keys(draft, {"prompt", "label_match", "top_k", "file_top_k"}, "[draft]")
    prompt = _str(draft, "prompt", "[draft]", "tutor_v1")
    if prompt not in VALID_PROMPTS:
        raise SpecError(f"[draft]: prompt must be one of {VALID_PROMPTS}")
    label_match = _str(draft, "label_match", "[draft]", "heading-prefix")
    if label_match not in VALID_LABEL_MATCH:
        raise SpecError(f"[draft]: label_match must be one of {VALID_LABEL_MATCH}")

    notes = []
    for i, n in enumerate(data.get("note", []), 1):
        _check_keys(n, {"heading", "body"}, f"[[note]] {i}")
        notes.append(NoteSpec(_str(n, "heading", f"[[note]] {i}"), _str(n, "body", f"[[note]] {i}")))

    topics, seen = [], set()
    for i, t in enumerate(data.get("topic", []), 1):
        where = f"[[topic]] {i}"
        _check_keys(t, {"title", "instruction", "source"}, where)
        title = _str(t, "title", where)
        if title in seen:
            raise SpecError(f"duplicate topic title {title!r}")
        seen.add(title)
        sources = t.get("source", [])
        if not sources:
            raise SpecError(f"{where} ({title!r}): needs at least one [[topic.source]]")
        topics.append(TopicSpec(title, _str(t, "instruction", where),
                                tuple(_parse_rule(s, f"{where} source {j}") for j, s in enumerate(sources, 1))))
    if not topics:
        raise SpecError("spec needs at least one topic")

    comparisons = []
    for i, c in enumerate(data.get("comparison", []), 1):
        where = f"[[comparison]] {i}"
        _check_keys(c, {"title", "instruction", "from", "take"}, where)
        title = _str(c, "title", where)
        if title in seen:
            raise SpecError(f"duplicate title {title!r} (comparison titles must differ from topic titles)")
        seen.add(title)
        sources = _strs(c, "from", where, required=True)
        for name in sources:
            if name not in {t.title for t in topics}:
                raise SpecError(f"{where}: 'from' names unknown topic {name!r}")
        comparisons.append(ComparisonSpec(title, _str(c, "instruction", where), sources, _int(c, "take", where, 3)))

    course = _str(guide, "course", "[guide]")
    if not _ID_RE.match(course):
        raise SpecError(f"[guide]: course {course!r} must be a plain folder name (lowercase letters, digits, underscores)")
    return GuideSpec(
        id=guide_id, title=_str(guide, "title", "[guide]"), course=course,
        draft_model=_str(models, "draft", "[models]", DEFAULT_MODEL),
        enhance_model=_str(models, "enhance", "[models]", DEFAULT_MODEL),
        prompt=prompt, label_match=label_match, top_k=_int(draft, "top_k", "[draft]", 180),
        file_top_k=_int(draft, "file_top_k", "[draft]", 80), notes=tuple(notes), topics=tuple(topics),
        comparisons=tuple(comparisons), path=str(p), sha256=hashlib.sha256(raw_bytes).hexdigest())
