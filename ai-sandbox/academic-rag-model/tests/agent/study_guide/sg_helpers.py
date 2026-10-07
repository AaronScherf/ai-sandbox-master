# tests/agent/study_guide/sg_helpers.py
"""Shared helpers for the study_guide tests (imported as `sg_helpers`)."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from agent.study_guide.spec import load_spec

CAMERON = "academic_notes/econ/textbooks/processed_outputs/Cameron_Micro_2013/Cameron_Micro_2013.rag.md"
HANSEN = "academic_notes/econ/textbooks/processed_outputs/Hansen_Econ_2022/Hansen_Econ_2022.rag.md"
SLIDES = "academic_notes/econ/class_2024/Class Notes/Slides/processed_outputs/slidesASYM.md"
RECIT = "academic_notes/econ/class_2024/Recitations/processed_outputs/Recitation 5.md"
EMPTY = "academic_notes/econ/class_2024/Recitations/processed_outputs/Empty.md"

CHUNKS = [
    {"chunk_id": "cam-1", "file_id": "cam", "text": "Cameron: the Wald statistic.",
     "heading_path": ["Chapter 7", "**7.2.** Wald Test", "§7.2.3. Wald Test Statistic"], "page_range": [249, 249]},
    {"chunk_id": "cam-2", "file_id": "cam", "text": "Cameron: the likelihood ratio test.",
     "heading_path": ["7.3.1. Wald, Likelihood Ratio, and LM Tests", "Likelihood Ratio Test"], "page_range": [257, 257]},
    {"chunk_id": "cam-3", "file_id": "cam", "text": "Cameron: the LM test.",
     "heading_path": ["7.3.5. Interpretation and Computation of the LM test"], "page_range": [262, 262]},
    {"chunk_id": "cam-4", "file_id": "cam", "text": "Cameron: an unrelated section.",
     "heading_path": ["7.30 Something else"], "page_range": [300, 300]},
    {"chunk_id": "han-1", "file_id": "han", "text": "Hansen: Wald tests.",
     "heading_path": ["9.10 WALD TESTS"], "page_range": [268, 268]},
    {"chunk_id": "han-2", "file_id": "han", "text": "Hansen: an intro.",
     "heading_path": ["9.1 Introduction"], "page_range": [250, 250]},
    {"chunk_id": "sl-1", "file_id": "sl", "text": "Slides: first."},
    {"chunk_id": "sl-2", "file_id": "sl", "text": "Slides: second."},
    {"chunk_id": "rec-1", "file_id": "rec", "text": "Recitation: Wald of nonlinear hypothesis."},
]

CARDS = [
    {"file_id": "cam", "doc_type": "textbook", "path": CAMERON.replace(".rag.md", ".md"), "rag_md_path": CAMERON, "content_hash": "h-cam"},
    {"file_id": "han", "doc_type": "textbook", "path": HANSEN.replace(".rag.md", ".md"), "rag_md_path": HANSEN, "content_hash": "h-han"},
    {"file_id": "sl", "doc_type": "ta_notes", "path": SLIDES, "rag_md_path": None, "content_hash": "h-sl"},
    {"file_id": "rec", "doc_type": "ta_notes", "path": RECIT, "rag_md_path": None, "content_hash": "h-rec"},
    {"file_id": "empty", "doc_type": "ta_notes", "path": EMPTY, "rag_md_path": None, "content_hash": "h-empty"},
]


def cite(chunk: dict) -> str:
    hp = chunk.get("heading_path")
    if not hp:
        return chunk["chunk_id"]
    page = chunk["page_range"][0]
    return f"§{hp[-1]}, p. {page}"


def hit(chunk_id: str, score: float):
    chunk = next(c for c in CHUNKS if c["chunk_id"] == chunk_id)
    card = next(c for c in CARDS if c["file_id"] == chunk["file_id"])
    return SimpleNamespace(chunk_id=chunk_id, file_id=chunk["file_id"], path=card.get("rag_md_path") or card["path"],
                           score=score, citation=cite(chunk), text=chunk["text"])


class StubSearch:
    """Stands in for search_passages: returns canned hits per doc_type and records calls."""

    def __init__(self, by_doc_type: dict):
        self.by_doc_type = by_doc_type
        self.calls: list[dict] = []

    def __call__(self, query, *, doc_type, top_k, file_top_k):
        self.calls.append({"query": query, "doc_type": doc_type, "top_k": top_k, "file_top_k": file_top_k})
        return list(self.by_doc_type.get(doc_type, []))


HEADER = '[guide]\nid = "demo"\ntitle = "Demo guide"\ncourse = "econ"\n\n'

WALD_TOPIC = """
[[topic]]
title = "Wald"
instruction = "Explain Wald."

  [[topic.source]]
  kind = "section"
  book = "Cameron"
  labels = ["7.2"]
  query = "wald"
"""


class FakeLLM:
    model = "fake-draft"

    def __init__(self, replies=()):
        self.replies = list(replies)
        self.calls: list[str] = []

    def generate_text(self, prompt, *, code_execution=False):
        self.calls.append(prompt)
        reply = self.replies.pop(0) if self.replies else f"ANSWER {len(self.calls)}"
        if isinstance(reply, Exception):
            raise reply
        return reply

    def generate_structured(self, prompt, schema):
        raise AssertionError("the draft stage must not request structured output")


# Fixtures live here (not in a conftest.py) so this folder does not collide with the
# summary_enhance conftest when both are collected in one run; test modules import them.
@pytest.fixture
def make_spec(tmp_path):
    def make(body, header=HEADER):
        path = tmp_path / "spec.toml"
        path.write_text(header + body, encoding="utf-8")
        return load_spec(path)
    return make


@pytest.fixture
def root(tmp_path):
    hub = tmp_path / "hub"
    (hub / "academic_notes" / "econ" / "summaries").mkdir(parents=True)
    return str(hub)
