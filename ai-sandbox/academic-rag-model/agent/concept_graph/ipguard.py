"""The own-words tripwire: reject drafted prose that repeats a run of words from an offered passage.

A tripwire, not a legal guarantee: it catches copying and near-copying of source text, which the public graph
must never contain."""
from __future__ import annotations

import re

IP_RUN_WORDS = 8

_WORD = re.compile(r"[a-z0-9]+(?:'[a-z]+)?")


def _words(text: str) -> list[str]:
    return _WORD.findall((text or "").lower())


def _longest_common_run(a: list[str], b: list[str]) -> tuple[int, int]:
    """Length of the longest common contiguous run, and its end index in `a`."""
    best = end = 0
    previous = [0] * (len(b) + 1)
    for i in range(1, len(a) + 1):
        current = [0] * (len(b) + 1)
        for j in range(1, len(b) + 1):
            if a[i - 1] == b[j - 1]:
                current[j] = previous[j - 1] + 1
                if current[j] > best:
                    best, end = current[j], i
        previous = current
    return best, end


def longest_shared_run(text: str, passages: list[str]) -> tuple[int, str]:
    """The longest run of consecutive words (case, punctuation and markdown ignored) that `text` shares with
    any passage, as (length, the shared words)."""
    mine = _words(text)
    best, best_words = 0, ""
    for passage in passages:
        n, end = _longest_common_run(mine, _words(passage))
        if n > best:
            best, best_words = n, " ".join(mine[end - n:end])
    return best, best_words


def check_prose(fields: dict[str, str], passages: list[str], limit: int = IP_RUN_WORDS) -> list[str]:
    """One message per field that shares `limit` or more consecutive words with an offered passage."""
    problems = []
    for name, text in fields.items():
        if not (text or "").strip():
            continue
        n, run = longest_shared_run(text, passages)
        if n >= limit:
            problems.append(f"{name}: shares {n} consecutive words with an offered passage ({run[:90]!r}); "
                            f"reword it in your own words")
    return problems
