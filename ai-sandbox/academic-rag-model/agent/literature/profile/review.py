"""Human-decision ledger and review queue for research profiles.

Decisions live in `<index_root>/.index/research_profile/decisions.json`, keyed by `file_id` then field, separate
from the cards. A decision overrides the model's value (`effective_value`), survives a model rewrite of the field
and a prompt-version change, and removes its item from the queue. The review Artifact reads `review_queue` and
applies the owner's choices with `resolve_item`.
"""

import datetime
import json
import os
import tempfile

from agent.literature.profile.taxonomy import load_openalex
from core.indexer.research_profile import METHOD_CLASSES, REPORT_TYPES

RESOLVABLE = frozenset({"discipline", "method_class", "bibliography", "report_type"})
_QUANT_DESIGNS = {
    "randomized_controlled_trial", "cluster_randomized_trial", "difference_in_differences", "regression_discontinuity",
    "instrumental_variables", "propensity_score_matching", "synthetic_control", "panel_fixed_effects",
    "interrupted_time_series", "natural_experiment", "cross_sectional_regression", "machine_learning_models",
    "structural_equation_modeling",
}


def ledger_path(index_root: str) -> str:
    return os.path.join(index_root, ".index", "research_profile", "decisions.json")


def _load(index_root: str) -> dict:
    try:
        with open(ledger_path(index_root), encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def _save(index_root: str, data: dict) -> None:
    atomic_write_json(ledger_path(index_root), data)


def atomic_write_json(path: str, data) -> None:
    """Writes JSON through a temp file in the same directory and os.replace, so a failure leaves the old file."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix="decisions-", suffix=".tmp", dir=os.path.dirname(path))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def record_decision(index_root: str, file_id: str, field: str, value, who: str) -> None:
    data = _load(index_root)
    data.setdefault(file_id, {})[field] = {"value": value, "who": who,
                                           "at": datetime.datetime.now(datetime.timezone.utc).isoformat()}
    _save(index_root, data)


def decision_for(index_root: str, file_id: str, field: str) -> dict | None:
    return _load(index_root).get(file_id, {}).get(field)


def effective_value(index_root: str, card: dict, field: str):
    """The human decision for this card and field if there is one, else the card's own research-profile value."""
    decision = decision_for(index_root, card["file_id"], field)
    if decision is not None:
        return decision["value"]
    return (card.get("research_profile") or {}).get(field)


def effective_profile(index_root: str, card: dict) -> dict:
    """The card's research profile with every human decision laid over the model's values."""
    profile = dict(card.get("research_profile") or {})
    for field, decision in _load(index_root).get(card["file_id"], {}).items():
        profile[field] = decision["value"]
    return profile


def all_cards(index_root: str) -> list[dict]:
    folder = os.path.join(index_root, ".index")
    cards: list[dict] = []
    for name in sorted(os.listdir(folder)) if os.path.isdir(folder) else []:
        if not name.endswith(".json") or name in ("courses.json", "tags.json"):
            continue
        with open(os.path.join(folder, name), encoding="utf-8") as f:
            data = json.load(f)
        cards += [c for c in data if isinstance(c, dict)] if isinstance(data, list) else []
    return cards


def method_disagrees(profile: dict) -> bool:
    design = str(profile.get("study_design") or "").removeprefix("study_design.")
    method = profile.get("method_class")
    return (design in _QUANT_DESIGNS and method == "qualitative") or (design == "qualitative" and method == "quantitative")


def review_queue(index_root: str) -> list[dict]:
    """Open review items: {file_id, title, field, reasons, current}. One item per card and field."""
    decisions = _load(index_root)
    items = []
    for card in all_cards(index_root):
        profile = card.get("research_profile")
        if not profile:
            continue
        fid, found = card["file_id"], []
        reasons = [r for r in profile.get("review_reasons", []) if r.startswith("discipline:")]
        if profile.get("needs_review") and reasons:
            found.append(("discipline", reasons, profile.get("discipline")))
        if method_disagrees(profile):
            found.append(("method_class", [f"study_design {profile['study_design']} vs method_class {profile['method_class']}"],
                          profile.get("method_class")))
        if (profile.get("doi_verified") or {}).get("match") == "mismatch":
            found.append(("bibliography", list(profile.get("bibliography_mismatches", [])), profile.get("title")))
        for field, why, current in found:
            if field not in decisions.get(fid, {}):
                items.append({"file_id": fid, "title": card.get("title"), "field": field, "reasons": why, "current": current})
    return items


def resolve_item(index_root: str, file_id: str, field: str, value, who: str) -> None:
    if field not in RESOLVABLE:
        raise ValueError(f"{field!r} is not a reviewable field; choose one of {sorted(RESOLVABLE)}")
    if field == "discipline" and value != "other" and value not in load_openalex().fields.values():
        raise ValueError(f"discipline {value!r} is not an OpenAlex field name or 'other'")
    if field == "method_class" and value not in METHOD_CLASSES:
        raise ValueError(f"method_class {value!r} must be one of {sorted(METHOD_CLASSES)}")
    if field == "report_type" and value not in REPORT_TYPES:
        raise ValueError(f"report_type {value!r} must be one of {sorted(REPORT_TYPES)}")
    if field == "bibliography" and value not in ("accepted", "corrected"):
        raise ValueError("bibliography decision must be 'accepted' or 'corrected'")
    record_decision(index_root, file_id, field, value, who)
