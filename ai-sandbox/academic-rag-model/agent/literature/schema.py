"""Constants for the study record and the agent's result shape (stage 2). Versioned: bump SCHEMA_VERSION when a
record's shape changes incompatibly, PROMPT_VERSION when the card instructions change."""
SCHEMA_VERSION = 1
PROMPT_VERSION = "extract-v2"

# result facet -> vocabulary name (vocab/<name>.yaml)
FACETS = {
    "intervention": "intervention", "outcome": "outcome", "study_design": "study_design",
    "sector": "sector", "population": "population", "data_sources": "data_source",
}
# optional extension modules: module -> {facet -> vocabulary name}
MODULE_FACETS = {"disaster_conflict": {"hazard_types": "hazard_type"}}

EFFECT_DIRECTIONS = ("positive", "negative", "null", "mixed", "not_reported")
CONFIDENCE = ("low", "medium", "high")
SCALES = ("local", "subnational", "national", "multi_country", "global", "not_stated")
MIN_QUOTE_CHARS = 8
MAX_QUOTE_CHARS = 300
