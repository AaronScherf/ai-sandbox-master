"""Retrieval over the hub's index, as a small protocol so stages and tests do not depend on the network."""
from __future__ import annotations

from typing import Protocol

from .sources import Passage, classify_passage


class Retriever(Protocol):
    def retrieve(self, query: str, top_k: int) -> list[Passage]: ...


class IndexRetriever:
    """Wraps the repo's passage search. The only network call is the Gemini query embedding it makes.

    Not unit-tested (it needs the live index and a key); the stages are tested with a fake retriever."""

    def __init__(self, hub_root: str, course: str, client):
        self.hub_root, self.course, self.client = hub_root, course, client

    def retrieve(self, query: str, top_k: int = 6) -> list[Passage]:
        from agent.rag.rag_agent import retrieve_passages  # heavy import, kept lazy

        found = retrieve_passages([self.hub_root], query, self.client, course=self.course, top_k=top_k)
        out = []
        for r in found:
            source, ref = classify_passage(r.path, r.citation)
            out.append(Passage(id="", source=source, ref=ref, text=r.text, path=r.path))
        return out


def make_gemini_client():
    """The paid key, as the repo's pipelines use (the free key has a tiny daily quota)."""
    from core.env.gemini_utils import get_gemini_client, load_dotenv_override

    load_dotenv_override()
    client = get_gemini_client("PAID_GEMINI_KEY")
    if client is None:
        raise RuntimeError("PAID_GEMINI_KEY is not available; cannot embed retrieval queries")
    return client
