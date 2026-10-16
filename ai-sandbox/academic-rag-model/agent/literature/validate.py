"""Every rule an agent's extraction result must satisfy before it becomes a record."""
from __future__ import annotations

from . import schema
from .transcript import check_quote
from .vocab import Vocabulary, is_country

_FACT_KEYS = {"value", "vocab_id", "proposed", "quote", "locator"}
_TOP_KEYS = {"core", "appraisal", "modules"}
_CORE_KEYS = set(schema.FACETS) | {"geography", "results"}


def _fact(path: str, fact, vocab: Vocabulary | None, vocab_name: str, pages, extra_keys=()) -> list[str]:
    if not isinstance(fact, dict):
        return [f"{path}: must be a mapping with value, vocab_id (or proposed), quote and locator"]
    out: list[str] = []
    for k in sorted(set(fact) - _FACT_KEYS - set(extra_keys)):
        out.append(f"{path}: unknown key {k!r}")
    value = fact.get("value")
    if not isinstance(value, str) or not value.strip():
        out.append(f"{path}.value: required text")
    for k in extra_keys:
        if k in fact and fact[k] is not None and not isinstance(fact[k], str):
            out.append(f"{path}.{k}: must be text")
    has_id = fact.get("vocab_id") is not None
    proposed = fact.get("proposed") is True
    if "proposed" in fact and not isinstance(fact["proposed"], bool):
        out.append(f"{path}.proposed: must be true or omitted")
    if has_id == proposed:
        out.append(f"{path}: give exactly one of vocab_id (a term from the list) or proposed: true")
    elif vocab is None:
        out.append(f"{path}: the {vocab_name!r} vocabulary is not loaded, so this fact cannot be checked")
    elif has_id and not vocab.contains(fact["vocab_id"]):
        out.append(f"{path}.vocab_id: {fact['vocab_id']!r} is not a term in the {vocab_name} vocabulary")
    elif proposed and isinstance(value, str) and (hit := vocab.find(value)) is not None:
        out.append(f"{path}: {value!r} is already in the vocabulary as {hit.id}; use vocab_id instead of proposed")
    problem = check_quote(fact.get("quote"), fact.get("locator"), pages)
    if problem:
        out.append(f"{path}.{problem}")
    return out


def _facts(path: str, facts, vocabs, vocab_name: str, pages, extra_keys=()) -> list[str]:
    if not isinstance(facts, list):
        return [f"{path}: must be a list (write [] when the paper gives nothing)"]
    out: list[str] = []
    for i, f in enumerate(facts):
        out += _fact(f"{path}[{i}]", f, vocabs.get(vocab_name), vocab_name, pages, extra_keys)
    return out


def _geography(geo, pages) -> list[str]:
    if not isinstance(geo, dict):
        return ["core.geography: must be a mapping (countries, regions, scale, quote, locator)"]
    out = [f"core.geography: unknown key {k!r}" for k in sorted(set(geo) - {"countries", "regions", "scale", "quote", "locator"})]
    countries, regions = geo.get("countries", []), geo.get("regions", [])
    if not isinstance(countries, list) or not all(is_country(c) for c in countries):
        out.append("core.geography.countries: a list of upper-case ISO 3166-1 alpha-2 codes such as SO")
        countries = []
    if not isinstance(regions, list) or not all(isinstance(r, str) and r.strip() for r in regions):
        out.append("core.geography.regions: a list of text")
        regions = []
    if geo.get("scale") not in schema.SCALES:
        out.append(f"core.geography.scale: must be one of {schema.SCALES}")
    if countries or regions:
        problem = check_quote(geo.get("quote"), geo.get("locator"), pages)
        if problem:
            out.append(f"core.geography.{problem}")
    return out


def _results(results, pages) -> list[str]:
    if not isinstance(results, list) or not results:
        return ["core.results: give at least one result, with a quote"]
    out: list[str] = []
    for i, r in enumerate(results):
        path = f"core.results[{i}]"
        if not isinstance(r, dict):
            out.append(f"{path}: must be a mapping")
            continue
        out += [f"{path}: unknown key {k!r}" for k in sorted(set(r) - {"claim", "effect_direction", "magnitude", "quote", "locator"})]
        if not isinstance(r.get("claim"), str) or not r["claim"].strip():
            out.append(f"{path}.claim: required text")
        if r.get("effect_direction") not in schema.EFFECT_DIRECTIONS:
            out.append(f"{path}.effect_direction: must be one of {schema.EFFECT_DIRECTIONS}")
        if r.get("magnitude") is not None and not isinstance(r["magnitude"], str):
            out.append(f"{path}.magnitude: must be text such as '12%' (quote it) or omitted")
        problem = check_quote(r.get("quote"), r.get("locator"), pages)
        if problem:
            out.append(f"{path}.{problem}")
    return out


def _appraisal(a, pages) -> list[str]:
    if not isinstance(a, dict):
        return ["appraisal: required mapping (confidence, rationale)"]
    out = [f"appraisal: unknown key {k!r}" for k in sorted(set(a) - {"confidence", "rationale", "quote", "locator"})]
    if a.get("confidence") not in schema.CONFIDENCE:
        out.append(f"appraisal.confidence: must be one of {schema.CONFIDENCE}")
    if not isinstance(a.get("rationale"), str) or not a["rationale"].strip():
        out.append("appraisal.rationale: required text")
    if a.get("quote") is not None or a.get("locator") is not None:
        problem = check_quote(a.get("quote"), a.get("locator"), pages)
        if problem:
            out.append(f"appraisal.{problem}")
    return out


def _modules(modules, vocabs, pages) -> list[str]:
    if not isinstance(modules, dict):
        return ["modules: must be a mapping"]
    out: list[str] = []
    for name, body in modules.items():
        if name not in schema.MODULE_FACETS:
            out.append(f"modules: unknown module {name!r}")
            continue
        if not isinstance(body, dict):
            out.append(f"modules.{name}: must be a mapping")
            continue
        allowed = set(schema.MODULE_FACETS[name]) | {"conflict_setting", "social_protection_modality"}
        out += [f"modules.{name}: unknown key {k!r}" for k in sorted(set(body) - allowed)]
        for facet, vocab_name in schema.MODULE_FACETS[name].items():
            if facet in body:
                out += _facts(f"modules.{name}.{facet}", body[facet], vocabs, vocab_name, pages)
        for key in ("conflict_setting", "social_protection_modality"):
            if body.get(key) is not None and not isinstance(body[key], str):
                out.append(f"modules.{name}.{key}: must be text or null")
    return out


def check_result(result, vocabs: dict[str, Vocabulary], pages: dict[int, str]) -> list[str]:
    if not isinstance(result, dict):
        return ["the result must be a YAML mapping with core, appraisal and optional modules"]
    out = [f"unknown top-level key {k!r}" for k in sorted(set(result) - _TOP_KEYS)]
    core = result.get("core")
    if not isinstance(core, dict):
        return out + ["core: required mapping"]
    out += [f"core: unknown key {k!r}" for k in sorted(set(core) - _CORE_KEYS)]
    for facet, vocab_name in schema.FACETS.items():
        if facet not in core:
            out.append(f"core.{facet}: required list (write [] when the paper gives nothing)")
            continue
        out += _facts(f"core.{facet}", core[facet], vocabs, vocab_name, pages,
                      extra_keys=("resolution",) if facet == "data_sources" else ())
    out += _geography(core.get("geography"), pages) if "geography" in core else ["core.geography: required mapping"]
    out += _results(core.get("results"), pages)
    out += _appraisal(result.get("appraisal"), pages)
    if "modules" in result:
        out += _modules(result["modules"], vocabs, pages)
    return out
