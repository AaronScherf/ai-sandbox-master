# agent/tutor/claims.py
"""claims.py -- vocabulary of the v1.1 claim ledger (spec §3): the tokenizer,
the group-window Recognizer, the claims.json schema and the samples self-test.
Recognizers are prep-authored and deterministic: no regex, no model call."""
from __future__ import annotations

import bisect
import re
from dataclasses import dataclass

AXES_ALL = ("conceptual", "rigor", "directness", "all")
_TOKEN = re.compile(r"[^\W_]+", re.UNICODE)


class ClaimsError(ValueError):
    pass


def tokenize(text: str) -> list[str]:
    t = text.lower().replace("’", "'")
    t = re.sub(r"n't\b", " not", t)
    return _TOKEN.findall(t)


def _group_hits(tokens: list[str], group: tuple[str, ...]) -> list[int]:
    exact = {g for g in group if not g.endswith("*")}
    prefixes = tuple(g[:-1] for g in group if g.endswith("*") and len(g) > 1)
    return [i for i, tok in enumerate(tokens)
            if tok in exact or (prefixes and tok.startswith(prefixes))]


@dataclass(frozen=True)
class Recognizer:
    groups: tuple
    window: int

    def matches_tokens(self, tokens: list[str]) -> bool:
        positions = [_group_hits(tokens, g) for g in self.groups]
        if any(not p for p in positions):
            return False
        for start in range(max(1, len(tokens) - self.window + 1)):
            end = start + self.window
            ok = True
            for p in positions:
                i = bisect.bisect_left(p, start)
                if i >= len(p) or p[i] >= end:
                    ok = False
                    break
            if ok:
                return True
        return False

    def matches(self, text: str) -> bool:
        return self.matches_tokens(tokenize(text))


def parse_recognizer(raw, where: str = "recognizer") -> Recognizer:
    if not isinstance(raw, dict) or set(raw) - {"all", "window"}:
        raise ClaimsError(f"{where}: must be an object with only 'all' and 'window'")
    groups, window = raw.get("all"), raw.get("window")
    if not isinstance(groups, list) or not groups:
        raise ClaimsError(f"{where}: 'all' must be a non-empty list of groups")
    parsed = []
    for g in groups:
        if not isinstance(g, list) or not g or not all(isinstance(x, str) and x.strip() for x in g):
            raise ClaimsError(f"{where}: each group must be a non-empty list of non-empty strings")
        parsed.append(tuple(x.strip().lower() for x in g))
    if not isinstance(window, int) or isinstance(window, bool) or window < 2:
        raise ClaimsError(f"{where}: 'window' must be an integer of at least 2")
    return Recognizer(tuple(parsed), window)


MIN_LEAK, MIN_STUDENT, MIN_NEUTRAL, MIN_PITFALL = 10, 5, 5, 3
LEAK_RECALL, STUDENT_RECALL = 0.9, 0.8


@dataclass(frozen=True)
class Claim:
    id: str
    text: str
    object_terms: tuple
    recognizer: Recognizer


@dataclass(frozen=True)
class Pitfall:
    id: str
    tag: str
    axis: str
    recognizer: Recognizer
    repair_question: str
    resolved_by: str | None


@dataclass(frozen=True)
class PartClaims:
    claims: tuple
    routes: dict
    pitfalls: tuple
    final_answer: Recognizer | None


def _req_str(d: dict, key: str, where: str) -> str:
    v = d.get(key)
    if not isinstance(v, str) or not v.strip():
        raise ClaimsError(f"{where}: '{key}' must be a non-empty string")
    return v.strip()


def _parse_part(pid: str, raw) -> PartClaims:
    if not isinstance(raw, dict):
        raise ClaimsError(f"{pid}: must be an object")
    claims_raw = raw.get("claims")
    if not isinstance(claims_raw, list) or not claims_raw:
        raise ClaimsError(f"{pid}: 'claims' must be a non-empty list")
    claims, ids = [], []
    for i, c in enumerate(claims_raw):
        w = f"{pid}.claims[{i}]"
        if not isinstance(c, dict):
            raise ClaimsError(f"{w}: must be an object")
        cid = _req_str(c, "id", w)
        if cid in ids:
            raise ClaimsError(f"{w}: duplicate claim id {cid!r}")
        terms = c.get("object_terms", [])
        if not isinstance(terms, list) or not all(isinstance(t, str) for t in terms):
            raise ClaimsError(f"{w}: 'object_terms' must be a list of strings")
        claims.append(Claim(cid, _req_str(c, "text", w), tuple(terms),
                            parse_recognizer(c.get("recognizer"), f"{w}.recognizer")))
        ids.append(cid)
    routes_raw = raw.get("routes")
    if not isinstance(routes_raw, dict) or not routes_raw:
        raise ClaimsError(f"{pid}: 'routes' must be a non-empty object")
    routes = {}
    for name, seq in routes_raw.items():
        if not isinstance(seq, list) or not seq or any(x not in ids for x in seq):
            raise ClaimsError(f"{pid}: routes[{name!r}] must list known claim ids")
        routes[name] = list(seq)
    pitfalls, tags = [], []
    for i, p in enumerate(raw.get("pitfalls", [])):
        w = f"{pid}.pitfalls[{i}]"
        if not isinstance(p, dict):
            raise ClaimsError(f"{w}: must be an object")
        tag = _req_str(p, "tag", w)
        if tag in tags:
            raise ClaimsError(f"{w}: duplicate tag {tag!r}")
        axis = p.get("axis")
        if axis not in AXES_ALL:
            raise ClaimsError(f"{w}: axis must be one of {list(AXES_ALL)}")
        resolved_by = p.get("resolved_by")
        if resolved_by is not None and resolved_by not in ids:
            raise ClaimsError(f"{w}: resolved_by must be a known claim id")
        pitfalls.append(Pitfall(_req_str(p, "id", w), tag, axis,
                                parse_recognizer(p.get("recognizer"), f"{w}.recognizer"),
                                _req_str(p, "repair_question", w), resolved_by))
        tags.append(tag)
    final = raw.get("final_answer")
    final_rec = parse_recognizer(final, f"{pid}.final_answer") if final is not None else None
    return PartClaims(tuple(claims), routes, tuple(pitfalls), final_rec)


def parse_claims(raw, part_ids: list[str]) -> tuple[dict, list[str]]:
    if not isinstance(raw, dict):
        return {}, ["claims.json must be an object keyed by part id"]
    errors, out = [], {}
    for pid in part_ids:
        if pid not in raw:
            errors.append(f"claims.json has no entry for part {pid}")
            continue
        try:
            out[pid] = _parse_part(pid, raw[pid])
        except ClaimsError as err:
            errors.append(str(err))
    for pid in raw:
        if pid not in part_ids:
            errors.append(f"claims.json has an entry for unknown part {pid}")
    return out, errors


def _unmatched(rec: Recognizer, samples: list) -> list[str]:
    return [s for s in samples if not rec.matches(s)]


def self_test(claims: dict, samples) -> list[str]:
    errors: list[str] = []
    samples = samples if isinstance(samples, dict) else {}
    for pid, pc in claims.items():
        ps = samples.get(pid)
        if not isinstance(ps, dict):
            errors.append(f"samples.json has no entry for {pid}")
            continue
        neutral = ps.get("neutral_samples", [])
        if len(neutral) < MIN_NEUTRAL:
            errors.append(f"{pid}: needs at least {MIN_NEUTRAL} neutral_samples")
        recs = [(f"claim {c.id}", c.recognizer) for c in pc.claims] + \
               [(f"pitfall {p.id}", p.recognizer) for p in pc.pitfalls]
        for sample in neutral:
            for label, rec in recs:
                if rec.matches(sample):
                    errors.append(f"{pid}: neutral sample matches {label}: {sample[:70]!r}")
        for c in pc.claims:
            cs = ps.get("claims", {}).get(c.id, {})
            for key, minimum, ratio in (("leak_samples", MIN_LEAK, LEAK_RECALL), ("student_samples", MIN_STUDENT, STUDENT_RECALL)):
                got = cs.get(key, [])
                if len(got) < minimum:
                    errors.append(f"{pid}.{c.id}: needs at least {minimum} {key} (has {len(got)})")
                    continue
                missed = _unmatched(c.recognizer, got)
                if (len(got) - len(missed)) / len(got) < ratio:
                    kind = "leak" if key == "leak_samples" else "student"
                    errors.append(f"{pid}.{c.id}: recognizer matches only {len(got) - len(missed)}/{len(got)} {kind} samples "
                                  f"(needs {int(ratio * 100)}%); unmatched e.g. {missed[0][:70]!r}")
        for p in pc.pitfalls:
            got = ps.get("pitfalls", {}).get(p.id, {}).get("student_samples", [])
            if len(got) < MIN_PITFALL:
                errors.append(f"{pid}.{p.id}: pitfall needs at least {MIN_PITFALL} student_samples")
                continue
            missed = _unmatched(p.recognizer, got)
            if (len(got) - len(missed)) / len(got) < STUDENT_RECALL:
                errors.append(f"{pid}: pitfall {p.id} recognizer matches only {len(got) - len(missed)}/{len(got)} "
                              f"student samples; unmatched e.g. {missed[0][:70]!r}")
    return errors
