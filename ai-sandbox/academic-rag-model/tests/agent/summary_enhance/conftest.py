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


def write_guide(path, refs, newline="\n", extra_front=""):
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


@pytest.fixture
def good_response():
    return {"topics": [
        {"title": "Wald test",
         "grounded": [{"text": "Both books define the Wald statistic from the unrestricted fit.",
                       "sources": ["S1", "S3"]}],
         "elaboration": [{"kind": "intuition", "text": "Think of it as a distance in estimate space."}]},
        {"title": "LM test",
         "grounded": [{"text": "The LM test needs only the restricted estimator.", "sources": ["S2"]}],
         "elaboration": []},
    ]}


class FakeLLM:
    model = "fake-model"

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def generate_structured(self, prompt, schema):
        self.calls.append(prompt)
        item = self._responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return copy.deepcopy(item)


@pytest.fixture
def make_llm():
    return lambda *responses: FakeLLM(responses)
