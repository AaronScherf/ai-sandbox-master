"""Loading and validating user-confirmed facts scoped to resume entries."""
from __future__ import annotations

from pathlib import Path

import yaml


def validate_user_facts(facts: list[dict] | None, master: dict) -> list[dict]:
    """Validate the small YAML contract used by --facts-file.

    Each fact has an entry_id, fact text, and required_concepts. Each
    required concept is a list of acceptable phrases; every concept group
    must appear in the final tailored entry for coverage to pass.
    """
    if facts is None:
        return []
    if not isinstance(facts, list):
        raise ValueError("facts file must contain a top-level YAML list")
    ids = {entry.get("id") for entry in master.get("work_experience") or []}
    validated = []
    for index, fact in enumerate(facts):
        if not isinstance(fact, dict):
            raise ValueError(f"fact #{index + 1} must be a YAML mapping")
        entry_id = fact.get("entry_id")
        statement = fact.get("fact")
        concepts = fact.get("required_concepts")
        if not isinstance(entry_id, str) or entry_id not in ids:
            raise ValueError(f"fact #{index + 1} references unknown work_experience id {entry_id!r}")
        if not isinstance(statement, str) or not statement.strip():
            raise ValueError(f"fact #{index + 1} must have non-empty 'fact' text")
        if not isinstance(concepts, list) or not concepts:
            raise ValueError(f"fact #{index + 1} must define non-empty 'required_concepts'")
        normalized_concepts = []
        for concept_index, alternatives in enumerate(concepts):
            if isinstance(alternatives, str):
                alternatives = [alternatives]
            if not isinstance(alternatives, list) or not alternatives or not all(
                isinstance(term, str) and term.strip() for term in alternatives
            ):
                raise ValueError(
                    f"fact #{index + 1} required_concepts item #{concept_index + 1} "
                    "must be a non-empty phrase or list of alternative phrases"
                )
            normalized_concepts.append([term.strip() for term in alternatives])
        validated.append({
            "entry_id": entry_id,
            "fact": statement.strip(),
            "required_concepts": normalized_concepts,
        })
    return validated


def load_user_facts(path: str | Path, master: dict) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        facts = yaml.safe_load(f)
    return validate_user_facts(facts, master)
