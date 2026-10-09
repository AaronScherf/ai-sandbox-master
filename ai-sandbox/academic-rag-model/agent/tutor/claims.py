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
