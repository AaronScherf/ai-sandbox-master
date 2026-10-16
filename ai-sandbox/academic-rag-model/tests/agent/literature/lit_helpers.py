"""Shared fixtures for the literature tests: synthetic pages, vocabularies and a valid agent result."""
from agent.literature.vocab import Term, Vocabulary

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
