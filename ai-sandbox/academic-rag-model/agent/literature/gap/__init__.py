"""Stage 5: gap analysis over the literature database (slice 1: offline, no LLM in the core)."""

# Fixed verdict categories. found_externally_not_in_corpus is reserved for slice 2 (OpenAlex) and never produced offline.
VERDICTS = ("tried_directly", "tried_adjacent", "found_externally_not_in_corpus", "no_evidence_in_corpus")
