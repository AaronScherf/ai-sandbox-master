# tests/agent/summary_enhance/conftest.py
import copy
import json
from types import SimpleNamespace

import pytest

CHUNKS = [
    {"chunk_id": "cam-1", "file_id": "cam", "text": "Cameron: the Wald statistic uses the unrestricted estimator."},
    {"chunk_id": "cam-2", "file_id": "cam", "text": "Cameron: the LM test uses the restricted estimator."},
    {"chunk_id": "han-1", "file_id": "han", "text": "Hansen: a Wald test of H0 uses the covariance estimator."},
    {"chunk_id": "unused-1", "file_id": "cam", "text": "Cameron: unrelated passage, not cited by the guide."},
]

REFS = [
    {"root": "STALE-ROOT", "path": "academic_notes/econ/textbooks/cam.rag.md", "file_id": "cam",
     "chunk_id": "cam-1", "citation": "§7.2.3 Wald Test Statistic, p. 249"},
    {"root": "STALE-ROOT", "path": "academic_notes/econ/textbooks/cam.rag.md", "file_id": "cam",
     "chunk_id": "cam-2", "citation": "§7.3.5 LM test, p. 262"},
    {"root": "STALE-ROOT", "path": "academic_notes/econ/textbooks/han.rag.md", "file_id": "han",
     "chunk_id": "han-1", "citation": "§9.10 WALD TESTS, p. 268"},
]

PLAN_JSON = {"topics": ["Wald test", "Likelihood ratio test", "LM test"]}
WORKED_TEXT = " ".join(["Compute $t=2$ here."] * 60)  # 180 words (3 per repeat), has inline math


def words(n):
    return " ".join(["word"] * n)


def make_topic_json(title, labels=("S1",), per_section=40, sections=3, external_words=10):
    secs = [{"heading": f"{title} part {i + 1}",
             "blocks": [{"type": "grounded", "text": words(per_section), "sources": list(labels)}]}
            for i in range(sections)]
    if external_words:
        secs[-1]["blocks"].append({"type": "external", "text": words(external_words), "sources": []})
    return {"title": title, "sections": secs}


def write_guide(path, refs, newline="\n"):
    front = ["---", 'title: "Wald and LM tests"', "llm_generated: true",
             "content_kind: derived_summary"]
    if refs is not None:
        front.append("indexer_source_refs: " + (refs if isinstance(refs, str)
                     else json.dumps(refs, separators=(",", ":"))))
    front.append("---")
    text = newline.join(front) + newline + newline + "# Wald and LM tests" + newline + newline + "Body text." + newline
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)


@pytest.fixture
def vault(tmp_path):
    root = tmp_path / "hub"
    course = "econ"
    chunks_file = root / ".index" / "chunks" / f"{course}.json"
    chunks_file.parent.mkdir(parents=True)
    chunks_file.write_text(json.dumps(CHUNKS), encoding="utf-8")
    guide = root / "academic_notes" / course / "summaries" / "guide.md"
    refs = copy.deepcopy(REFS)
    write_guide(guide, refs)
    return SimpleNamespace(root=root, guide=guide, course=course, refs=refs)


class FakeLLM:
    model = "fake-model"

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []
        self.kinds = []
        self.code_execution = []

    def _next(self):
        item = self._responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return copy.deepcopy(item)

    def generate_structured(self, prompt, schema):
        self.calls.append(prompt)
        self.kinds.append("structured")
        return self._next()

    def generate_text(self, prompt, *, code_execution=False):
        self.calls.append(prompt)
        self.kinds.append("text")
        self.code_execution.append(code_execution)
        return self._next()


@pytest.fixture
def make_llm():
    return lambda *responses: FakeLLM(responses)
