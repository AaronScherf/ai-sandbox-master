"""Retrieval over the hub's index, as a small protocol so stages and tests do not depend on the network."""
from __future__ import annotations

import json
import math
import os
import re
import sys
from collections import Counter
from typing import Callable, Protocol

from .sources import Passage, classify_passage, near_duplicate, shingles

OVERFETCH = 4  # extra index hits asked for, so dropping excluded files and second copies still fills top_k


class Retriever(Protocol):
    def retrieve(self, query: str, top_k: int) -> list[Passage]: ...


class _Distinct:
    """Accepts a passage unless its file was excluded in the course-materials review or its text repeats one already
    accepted (the index holds both copies of a duplicated file)."""

    def __init__(self, catalog):
        self.catalog, self.offered = catalog, []

    def accept(self, path: str, text: str) -> bool:
        if (self.catalog is not None and self.catalog.is_excluded(path)) or near_duplicate(text, self.offered):
            return False
        self.offered.append(shingles(text))
        return True


class IndexRetriever:
    """Wraps the repo's passage search. The only network call is the Gemini query embedding it makes.

    Not unit-tested (it needs the live index and a key); the stages are tested with a fake retriever."""

    def __init__(self, hub_root: str, course: str, client, catalog=None):
        self.hub_root, self.course, self.client, self.catalog = hub_root, course, client, catalog

    def retrieve(self, query: str, top_k: int = 6) -> list[Passage]:
        from agent.rag.rag_agent import retrieve_passages  # heavy import, kept lazy

        found = retrieve_passages([self.hub_root], query, self.client, course=self.course, top_k=top_k + OVERFETCH)
        out, distinct = [], _Distinct(self.catalog)
        for r in found:
            if not distinct.accept(r.path, r.text):
                continue
            source, ref = classify_passage(r.path, r.citation, self.catalog)
            out.append(Passage(id="", source=source, ref=ref, text=r.text, path=r.path))
            if len(out) >= top_k:
                break
        return out


_WORD = re.compile(r"[a-z0-9]+")
_STOP = frozenset("a an and are as at be by for from has have in is it its of on or that the this to was which with "
                  "implies equivalent necessary sufficient".split())


def _terms(text: str) -> list[str]:
    return [w for w in _WORD.findall((text or "").lower()) if len(w) > 1 and w not in _STOP]


class LexicalRetriever:
    """Keyword search over the same chunks the embedding search ranks, with no network call.

    The last resort when no Gemini key can embed a query. It scores each chunk by TF-IDF overlap with the query and
    keeps at most `max_per_file` per file so one long document cannot fill a card. It has no notion of synonyms, so it
    is weaker than the embedding search."""

    def __init__(self, hub_root: str, course: str, max_per_file: int = 3, catalog=None):
        self.hub_root, self.course, self.max_per_file, self.catalog = hub_root, course, max_per_file, catalog
        self._chunks: list[dict] | None = None
        self._idf: dict[str, float] = {}
        self._paths: dict[str, str] = {}

    def _load(self) -> None:
        from core.indexer.chunk_index import load_chunks  # lazy: only the fallback path needs it

        chunks = load_chunks(self.hub_root, self.course)
        cards_file = os.path.join(self.hub_root, ".index", f"{self.course}.json")
        if os.path.exists(cards_file):
            with open(cards_file, "r", encoding="utf-8") as f:
                self._paths = {c["file_id"]: c.get("path", "") for c in json.load(f) if c.get("file_id")}
        document_frequency: Counter = Counter()
        for c in chunks:
            c["_tf"] = Counter(_terms(c.get("text", "")))
            c["_len"] = max(sum(c["_tf"].values()), 1)
            document_frequency.update(c["_tf"].keys())
        n = max(len(chunks), 1)
        self._idf = {t: math.log(1 + n / (1 + d)) for t, d in document_frequency.items()}
        self._chunks = chunks

    def retrieve(self, query: str, top_k: int = 6) -> list[Passage]:
        from core.indexer.index_search import _render_citation

        if self._chunks is None:
            self._load()
        wanted = set(_terms(query))
        scored = []
        for c in self._chunks or []:
            hit = sum(self._idf.get(t, 0.0) * (1 + math.log(c["_tf"][t])) for t in wanted if t in c["_tf"])
            if hit > 0:
                scored.append((hit / math.sqrt(c["_len"]), c))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        out, per_file, distinct = [], Counter(), _Distinct(self.catalog)
        for _, c in scored:
            if per_file[c["file_id"]] >= self.max_per_file:
                continue
            path = self._paths.get(c["file_id"], "")
            if not distinct.accept(path, c.get("text", "")):
                continue
            per_file[c["file_id"]] += 1
            source, ref = classify_passage(path, _render_citation(c), self.catalog)
            out.append(Passage(id="", source=source, ref=ref, text=c.get("text", ""), path=path))
            if len(out) >= top_k:
                break
        return out


_QUOTA = re.compile(r"429|RESOURCE_EXHAUSTED|spending cap|quota|rate.?limit", re.I)


class ResilientRetriever:
    """Tries each backend in order and moves on, for the rest of the run, when one is out of quota.

    Only a quota or rate-limit failure moves on; any other error (a bad key, a missing index) is raised, because
    falling back would hide it."""

    def __init__(self, backends: list[tuple[str, Retriever]], notify: Callable[[str], None] | None = None):
        if not backends:
            raise ValueError("ResilientRetriever needs at least one backend")
        self.backends = backends
        self.notify = notify or (lambda message: print(message, file=sys.stderr))
        self.active = 0

    @property
    def label(self) -> str:
        return self.backends[self.active][0]

    def retrieve(self, query: str, top_k: int = 6) -> list[Passage]:
        while True:
            label, backend = self.backends[self.active]
            try:
                return backend.retrieve(query, top_k)
            except Exception as exc:  # noqa: BLE001 - the quota pattern below decides what is retryable
                if self.active + 1 >= len(self.backends) or not _QUOTA.search(str(exc)):
                    raise
                self.active += 1
                self.notify(f"retrieval via {label} is out of quota; continuing with {self.label}"
                            + (" (keyword search: weaker matches, check the cards)" if self.label == "keyword" else ""))


def make_gemini_client(key_env_var: str = "PAID_GEMINI_KEY"):
    """A Gemini client for query embeddings (the free key has a tiny daily quota; the paid key can hit its cap)."""
    from core.env.gemini_utils import get_gemini_client, load_dotenv_override

    load_dotenv_override()
    client = get_gemini_client(key_env_var)
    if client is None:
        raise RuntimeError(f"{key_env_var} is not available; cannot embed retrieval queries")
    return client


def make_resilient_retriever(hub_root: str, course: str, notify: Callable[[str], None] | None = None,
                             catalog=None) -> ResilientRetriever:
    """paid key, then the free key, then local keyword search. Keys that are not set are skipped. `catalog` (the
    course's materials catalog) decides each passage's citation key."""
    backends: list[tuple[str, Retriever]] = []
    for label, env in (("paid key", "PAID_GEMINI_KEY"), ("free key", "GEMINI_API_KEY")):
        try:
            backends.append((label, IndexRetriever(hub_root, course, make_gemini_client(env), catalog=catalog)))
        except RuntimeError:
            continue
    backends.append(("keyword", LexicalRetriever(hub_root, course, catalog=catalog)))
    return ResilientRetriever(backends, notify)
