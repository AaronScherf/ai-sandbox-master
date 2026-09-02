"""
relevance.py
Local (sentence-transformers, no Gemini API spend) relevance scoring for
discovery candidates against a user-supplied prompt, plus the two-layer
volume control from spec S1/S3: a similarity threshold as the primary
filter, a numeric ceiling as backstop.

Deliberately does not import indexer.index_card.cosine_similarity even
though an equivalent function exists there -- journal_discovery never
imports from indexer/ (spec S2), and this embedding space is private to
this one scoring step, never compared against anything indexer/ produces
(spec S3, S9).
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Iterable

from journal_discovery.discovery import Work

_DEFAULT_MODEL_NAME = "all-MiniLM-L6-v2"
_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


def _normalize_title(title: str) -> str:
    """Confirmed real 2026-09-02: the same paper legitimately appears
    under multiple DOIs (an SSRN working-paper revision vs. its journal
    version) -- normalizing catches an exact title match regardless of
    case or punctuation, without the false-positive risk a fuzzy/edit-
    distance match would carry between genuinely different papers."""
    return _NON_ALNUM_RE.sub("", title.lower())


@dataclass
class ScoredWork:
    work: Work
    score: float | None  # None only if neither an abstract nor a title was available to score
    scored_from: str = "abstract"  # "title" flags a weaker, title-only signal


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def load_relevance_model(model_name: str = _DEFAULT_MODEL_NAME):
    """Import is local to this function (not module-level) so importing
    journal_discovery.relevance never requires sentence-transformers to be
    installed unless this is actually called -- matches common/gemini_utils.py's
    own get_gemini_client() pattern of deferring the heavy import."""
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_name)


def embed_text(model, text: str) -> list[float]:
    return model.encode(text, normalize_embeddings=True).tolist()


def score_work(model, prompt_embedding: list[float], work: Work) -> tuple[float, str] | tuple[None, None]:
    """Falls back to the title when there's no abstract to score --
    confirmed real 2026-09-02 that closed-access Elsevier articles often
    have no abstract_inverted_index in OpenAlex at all (a publisher
    licensing gap, not a parsing bug); a title-based score is a real,
    if weaker, signal, flagged via the returned scored_from so callers
    can show reduced confidence rather than treating it as unscorable."""
    if work.abstract:
        return cosine_similarity(prompt_embedding, embed_text(model, work.abstract)), "abstract"
    if work.title:
        return cosine_similarity(prompt_embedding, embed_text(model, work.title)), "title"
    return None, None


def select_relevant_works(
    works: Iterable[Work],
    model,
    relevance_prompt: str,
    threshold: float,
    max_results: int,
    max_examined: int,
) -> list[ScoredWork]:
    """Consumes `works` lazily (spec S4 step 2): stops examining candidates
    once max_examined have been scored, or once max_results have passed
    the threshold, whichever comes first. Every candidate -- abstract- or
    title-scored -- goes through the same threshold check; nothing is
    admitted just because it couldn't be scored well (confirmed real
    2026-09-02: the old no-abstract-fills-leftover-slots behavior let
    completely off-topic candidates flood the worklist whenever one
    heavily-cited seed paper's citers mostly lacked abstracts)."""
    prompt_embedding = embed_text(model, relevance_prompt)
    scored: list[ScoredWork] = []
    seen_titles: set[str] = set()
    examined = 0

    for work in works:
        if examined >= max_examined:
            break
        examined += 1

        normalized_title = _normalize_title(work.title)
        if normalized_title in seen_titles:
            continue

        score, scored_from = score_work(model, prompt_embedding, work)
        if score is not None and score >= threshold:
            scored.append(ScoredWork(work=work, score=score, scored_from=scored_from))
            seen_titles.add(normalized_title)
            if len(scored) >= max_results:
                break

    return scored
