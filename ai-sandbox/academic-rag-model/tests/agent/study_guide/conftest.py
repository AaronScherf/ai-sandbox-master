# tests/agent/study_guide/conftest.py
import pytest

from agent.study_guide.spec import load_spec
from sg_helpers import HEADER


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
