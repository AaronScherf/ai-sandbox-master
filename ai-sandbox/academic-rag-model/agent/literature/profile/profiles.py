"""Inclusion profiles: which papers a map view includes. Criteria are parameters in a YAML file per map protocol."""

from dataclasses import dataclass
from pathlib import Path

import yaml

DEFAULT_DIR = Path(__file__).resolve().parent / "profiles"


@dataclass(frozen=True)
class InclusionProfile:
    name: str
    framework: str
    require_intervention: bool
    require_any_tag: bool
    evidence_roles: tuple[str, ...]
    study_designs: tuple[str, ...]
    orientations: tuple[str, ...]
    income_groups: tuple[str, ...]
    min_year: int | None
    include_unclear: bool


def load_profile(path: Path | str) -> InclusionProfile:
    d = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return InclusionProfile(
        name=d["name"], framework=d.get("framework", ""),
        require_intervention=bool(d.get("require_intervention")), require_any_tag=bool(d.get("require_any_tag")),
        evidence_roles=tuple(d.get("evidence_roles") or ()), study_designs=tuple(d.get("study_designs") or ()),
        orientations=tuple(d.get("orientations") or ()), income_groups=tuple(d.get("income_groups") or ()),
        min_year=d.get("min_year"), include_unclear=bool(d.get("include_unclear", True)))


def matches(profile: InclusionProfile, record: dict) -> tuple[bool, str]:
    """(included, reason). `record` holds research-profile fields plus publication_year. A criterion whose value is
    unknown makes the paper "unclear"; unclear papers are included when the profile says so."""
    has_i, has_o = bool(record.get("intervention_tags")), bool(record.get("outcome_tags"))
    if profile.require_intervention and not has_i:
        return False, "excluded: no intervention tag"
    if profile.require_any_tag and not (has_i or has_o):
        return False, "excluded: no intervention or outcome tag"
    unclear = []
    for allowed, key, label in ((profile.evidence_roles, "evidence_role", "evidence role"),
                                (profile.study_designs, "study_design", "study design"),
                                (profile.orientations, "orientation", "orientation"),
                                (profile.income_groups, "country_income_group", "income group")):
        if not allowed:
            continue
        value = record.get(key)
        if value is None:
            unclear.append(f"{label} unknown")
        elif value not in allowed:
            return False, f"excluded: {label} {value!r} not in {list(allowed)}"
    if profile.min_year is not None:
        year = record.get("publication_year")
        if year is None:
            unclear.append("year unknown")
        elif year < profile.min_year:
            return False, f"excluded: published {year}, before {profile.min_year}"
    if unclear:
        reason = "unclear: " + ", ".join(unclear)
        return (profile.include_unclear, reason if profile.include_unclear else "excluded: " + reason)
    return True, "included"
