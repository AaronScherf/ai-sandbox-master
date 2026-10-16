"""Controlled vocabularies as data files (see vocab_data/README.md for the format)."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

import yaml

PROVENANCES = ("3ie", "provisional", "local")
DATA_DIR = Path(__file__).resolve().parent / "vocab_data"
_NAME = re.compile(r"^[a-z][a-z_]*$")
_TERM_KEYS = {"id", "label", "parent", "definition", "aliases", "source"}


class VocabularyError(ValueError):
    pass


@dataclass(frozen=True)
class Term:
    id: str
    label: str
    parent: str | None = None
    definition: str = ""
    aliases: tuple[str, ...] = ()
    source: str | None = None


def _key(text) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", str(text)).casefold()).strip()


@dataclass
class Vocabulary:
    name: str
    version: int
    provenance: str
    source: str
    terms: dict[str, Term]
    _by_key: dict[str, str] = field(default_factory=dict, repr=False)

    def __post_init__(self):
        for t in self.terms.values():
            for k in (t.id, t.label, *t.aliases):
                self._by_key.setdefault(_key(k), t.id)

    def contains(self, term_id: str) -> bool:
        return term_id in self.terms

    def find(self, value) -> Term | None:
        tid = self._by_key.get(_key(value))
        return self.terms.get(tid) if tid else None


def validate_vocabulary(data) -> list[str]:
    if not isinstance(data, dict):
        return ["the file must be a YAML mapping"]
    problems: list[str] = []
    name = data.get("vocabulary")
    if not isinstance(name, str) or not _NAME.match(name):
        problems.append("name: `vocabulary` must be lower_snake_case text")
        name = None
    if not isinstance(data.get("version"), int) or isinstance(data.get("version"), bool) or data["version"] < 1:
        problems.append("version: must be an integer of at least 1")
    if data.get("provenance") not in PROVENANCES:
        problems.append(f"provenance: must be one of {PROVENANCES}")
    if not isinstance(data.get("source"), str) or not data["source"].strip():
        problems.append("source: say where this list comes from")
    terms = data.get("terms")
    if not isinstance(terms, list):
        return problems + ["terms: must be a list"]
    ids: list[str] = []
    for i, t in enumerate(terms):
        where = f"terms[{i}]"
        if not isinstance(t, dict):
            problems.append(f"{where}: must be a mapping")
            continue
        extra = sorted(set(t) - _TERM_KEYS)
        if extra:
            problems.append(f"{where}: unknown key(s) {extra}")
        tid = t.get("id")
        if not isinstance(tid, str) or not tid:
            problems.append(f"{where}: id is required")
            continue
        if name and not tid.startswith(f"{name}."):
            problems.append(f"{where}: id {tid!r} must start with '{name}.'")
        if tid in ids:
            problems.append(f"{where}: duplicate id {tid!r}")
        ids.append(tid)
        if not isinstance(t.get("label"), str) or not t["label"].strip():
            problems.append(f"{where}: label is required")
        if "aliases" in t and not (isinstance(t["aliases"], list) and all(isinstance(a, str) for a in t["aliases"])):
            problems.append(f"{where}: aliases must be a list of text")
    parents = {t["id"]: t.get("parent") for t in terms if isinstance(t, dict) and isinstance(t.get("id"), str)}
    for tid, parent in parents.items():
        if parent is not None and parent not in parents:
            problems.append(f"{tid}: parent {parent!r} is not a term in this vocabulary")
    for tid in parents:
        seen, cur = set(), tid
        while cur is not None and cur in parents:
            if cur in seen:
                problems.append(f"{tid}: parent cycle")
                break
            seen.add(cur)
            cur = parents[cur]
    return problems


def load_vocabulary(path) -> Vocabulary:
    path = Path(path)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    problems = validate_vocabulary(data)
    if problems:
        raise VocabularyError(f"{path.name}: " + "; ".join(problems))
    terms = {
        t["id"]: Term(id=t["id"], label=t["label"], parent=t.get("parent"), definition=t.get("definition", ""),
                      aliases=tuple(t.get("aliases", [])), source=t.get("source"))
        for t in data["terms"]
    }
    return Vocabulary(data["vocabulary"], data["version"], data["provenance"], data["source"], terms)


def load_vocab_dir(path=None) -> dict[str, Vocabulary]:
    out: dict[str, Vocabulary] = {}
    for p in sorted(Path(path or DATA_DIR).glob("*.yaml")):
        if p.stem == "countries":
            continue
        v = load_vocabulary(p)
        if v.name != p.stem:
            raise VocabularyError(f"{p.name}: the vocabulary is named {v.name!r}; the file must be {v.name}.yaml")
        out[v.name] = v
    return out


_COUNTRIES: dict[str, frozenset[str]] = {}


def load_countries(path=None) -> frozenset[str]:
    p = Path(path or DATA_DIR / "countries.yaml")
    key = str(p)
    if key not in _COUNTRIES:
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
        _COUNTRIES[key] = frozenset(c["code"] for c in data["countries"])
    return _COUNTRIES[key]


def is_country(code) -> bool:
    return isinstance(code, str) and len(code) == 2 and code.isupper() and code in load_countries()
