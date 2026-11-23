"""OpenAlex domain / field / subfield lists (committed in reference_data) and 3ie tree helpers."""

from dataclasses import dataclass
from pathlib import Path

import yaml

from agent.literature.vocab import Vocabulary

DATA_FILE = Path(__file__).resolve().parents[1] / "reference_data" / "openalex_taxonomy.yaml"


@dataclass(frozen=True)
class OpenAlexTaxonomy:
    domains: dict[str, str]
    fields: dict[str, str]
    subfields: dict[str, str]
    _field_domain: dict[str, str]
    _subfield_field: dict[str, str]
    retrieved: str

    def field_domain(self, field_id: str) -> str:
        return self._field_domain[field_id]

    def subfield_field(self, subfield_id: str) -> str:
        return self._subfield_field[subfield_id]


def load_openalex(path: Path | str | None = None) -> OpenAlexTaxonomy:
    data = yaml.safe_load(Path(path or DATA_FILE).read_text(encoding="utf-8"))
    domains = {str(k): v for k, v in data["domains"].items()}
    fields = {str(k): v["label"] for k, v in data["fields"].items()}
    subfields = {str(k): v["label"] for k, v in data["subfields"].items()}
    return OpenAlexTaxonomy(
        domains, fields, subfields,
        {str(k): str(v["domain"]) for k, v in data["fields"].items()},
        {str(k): str(v["field"]) for k, v in data["subfields"].items()},
        str(data.get("retrieved", "")),
    )


def ancestors(vocab: Vocabulary, term_id: str) -> list[str]:
    """Parent chain of a term, nearest first, excluding the term itself."""
    chain: list[str] = []
    seen = {term_id}
    parent = vocab.terms[term_id].parent
    while parent and parent not in seen:
        chain.append(parent)
        seen.add(parent)
        parent = vocab.terms[parent].parent
    return chain


def rollup(vocab: Vocabulary, term_ids: list[str]) -> set[str]:
    """The terms plus all their ancestors. A branch-level id never expands to its leaves."""
    out: set[str] = set()
    for tid in term_ids:
        out.add(tid)
        out.update(ancestors(vocab, tid))
    return out
