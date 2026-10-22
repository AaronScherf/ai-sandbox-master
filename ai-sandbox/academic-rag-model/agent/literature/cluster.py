"""A cluster of papers chosen by facet constraints on their tier A/B facts."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from . import schema
from .compare import _ancestors
from .tiers import at_least, tiered_facts
from .transcript import normalize

FACETS = tuple(schema.FACETS) + ("countries",)
_NAME = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}")


class ClusterError(ValueError):
    pass


@dataclass
class Cluster:
    name: str
    constraints: list
    floor: str
    file_ids: list


def topic_dir(index_root, name: str) -> Path:
    if not _NAME.fullmatch(name or ""):
        raise ClusterError(f"topic name {name!r}: use lowercase letters, digits, - and _ (up to 64 characters)")
    return Path(index_root) / "literature_reviews" / name


def parse_constraint(text: str) -> dict:
    facet, sep, value = text.partition("=")
    facet, value = facet.strip(), value.strip()
    if not sep or not value or facet not in FACETS:
        raise ClusterError(f"{text!r}: write facet=value with a facet from {', '.join(FACETS)}")
    return {"facet": facet, "value": value}


def _matcher(constraint: dict, vocabs: dict):
    facet, value = constraint["facet"], constraint["value"]
    if facet == "countries":
        code = value.upper()
        return lambda i: i["facet"] == "countries" and i["shown"].upper() == code
    vocab = vocabs.get(schema.FACETS[facet])
    term = (vocab.terms.get(value) or vocab.find(value)) if vocab is not None else None
    if term is None:
        raise ClusterError(f"{value!r} is not a term of the {schema.FACETS[facet]} vocabulary")
    label = normalize(term.label)
    return lambda i: i["facet"] == facet and (i["shown"] == term.id or normalize(i["label"]) == label
                                                or term.id in _ancestors(i["shown"], vocab))


def define_cluster(records, vocabs: dict, name: str, where: list, floor: str = "B") -> Cluster:
    topic_dir("", name)  # validates the name
    if not where:
        raise ClusterError("give at least one facet=value constraint")
    constraints = [parse_constraint(w) for w in where]
    matchers = [_matcher(c, vocabs) for c in constraints]
    members = []
    for fid in sorted(records.ids()):
        items = at_least(tiered_facts(records, fid, vocabs), floor)
        if items and all(any(m(i) for i in items) for m in matchers):
            members.append(fid)
    if not members:
        raise ClusterError("no paper has tier A/B facts matching every constraint; check the values or lower --floor")
    return Cluster(name, constraints, floor, members)


def save_cluster(index_root, cluster: Cluster) -> Path:
    path = topic_dir(index_root, cluster.name) / "cluster.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {"name": cluster.name, "constraints": cluster.constraints, "floor": cluster.floor, "file_ids": cluster.file_ids}
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8", newline="\n")
    return path


def load_cluster(index_root, name: str) -> Cluster:
    path = topic_dir(index_root, name) / "cluster.yaml"
    if not path.is_file():
        raise ClusterError(f"no cluster {name!r}: run `cluster define {name} --where facet=value` first")
    d = yaml.safe_load(path.read_text(encoding="utf-8"))
    return Cluster(d["name"], d["constraints"], d["floor"], d["file_ids"])
