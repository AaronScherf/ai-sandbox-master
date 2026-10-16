"""Shared fixtures for the literature tests: synthetic pages, vocabularies and a valid agent result."""
from pathlib import Path

import yaml

from agent.literature.vocab import Term, Vocabulary
from core.indexer.index_card import load_shard, save_shard

PAGES = {
    1: "We study cash transfers in rural Somalia using a panel of 1,200 households from 2015 to 2019.",
    2: "Data come from FSNAU food security surveys collected at district level across Gedo region.",
    3: "Cash transfers raised household food consumption by twelve percent in the treated districts.",
    4: "Our confidence in these estimates is moderate given attrition between survey waves.",
}


def vocab(name, *term_ids, version=1):
    return Vocabulary(name, version, "provisional", "test fixture",
                      {t: Term(id=t, label=t.split(".", 1)[1].replace("_", " ")) for t in term_ids})


VOCABS = {
    "intervention": vocab("intervention", "intervention.cash_transfer", "intervention.voucher"),
    "outcome": vocab("outcome", "outcome.food_consumption"),
    "study_design": vocab("study_design", "study_design.panel"),
    "sector": vocab("sector", "sector.social_protection"),
    "population": vocab("population", "population.households"),
    "data_source": vocab("data_source", "data_source.fsnau"),
    "hazard_type": vocab("hazard_type", "hazard_type.drought"),
}


def good():
    return {
        "core": {
            "intervention": [{"value": "cash transfers", "vocab_id": "intervention.cash_transfer",
                              "quote": "We study cash transfers in rural Somalia", "locator": 1}],
            "outcome": [{"value": "food consumption", "vocab_id": "outcome.food_consumption",
                         "quote": "raised household food consumption by twelve percent", "locator": 3}],
            "study_design": [{"value": "panel", "vocab_id": "study_design.panel",
                              "quote": "using a panel of 1,200 households", "locator": 1}],
            "sector": [], "population": [],
            "data_sources": [{"value": "FSNAU", "vocab_id": "data_source.fsnau", "resolution": "district",
                              "quote": "FSNAU food security surveys collected at district level", "locator": 2}],
            "geography": {"countries": ["SO"], "regions": ["Gedo"], "scale": "subnational",
                          "quote": "across Gedo region", "locator": 2},
            "results": [{"claim": "Cash transfers raised food consumption", "effect_direction": "positive",
                         "magnitude": "12%", "quote": "raised household food consumption by twelve percent",
                         "locator": 3}],
        },
        "appraisal": {"confidence": "medium", "rationale": "Attrition between waves.",
                      "quote": "given attrition between survey waves", "locator": 4},
    }


def make_index(root, file_id="0123456789abcdef", *, md_text=None, card_extra=None, write_md=True, title="Cash transfers in Somalia"):
    """An index root (research-style) holding one converted journal paper. Appends to the 'economics' shard."""
    rel = f"journal-articles/economics/processed_outputs/{file_id}.md"
    if md_text is None:
        md_text = "\n\n".join(f"<!-- page {n} -->\n\n{text}" for n, text in sorted(PAGES.items()))
    if write_md:
        path = Path(root) / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(md_text, encoding="utf-8", newline="\n")
    card = {"file_id": file_id, "doc_type": "journal_article", "title": title, "path": rel, "course": "economics"}
    card.update(card_extra or {})
    save_shard(str(root), "economics", load_shard(str(root), "economics") + [card])
    return rel


def write_vocab_dir(directory, vocabs=None):
    """Writes the fixture vocabularies as vocab_data-style YAML files."""
    for name, v in (vocabs or VOCABS).items():
        data = {"vocabulary": name, "version": v.version, "provenance": v.provenance, "source": v.source,
                "terms": [{"id": t.id, "label": t.label, **({"definition": t.definition} if t.definition else {})}
                          for t in v.terms.values()]}
        (Path(directory) / f"{name}.yaml").write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
                                                       encoding="utf-8", newline="\n")


def fill_card(card_path, result):
    """Writes `result` into the empty yaml fence under '## Result', as the agent would."""
    p = Path(card_path)
    text = p.read_text(encoding="utf-8")
    marker = "```yaml\n```"
    assert text.count(marker) == 1, "card has no empty result fence"
    p.write_text(text.replace(marker, "```yaml\n" + yaml.safe_dump(result, sort_keys=False, allow_unicode=True) + "```"),
                 encoding="utf-8", newline="\n")
