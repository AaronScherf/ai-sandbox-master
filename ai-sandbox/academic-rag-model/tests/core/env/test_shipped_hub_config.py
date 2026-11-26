"""The only test that reads the live academic-hub/hub_config.json.

tools.land_branch.OUTSIDE_TEST_TARGETS maps a change to that file to this test alone; every other
test reads the frozen seed (tests/conftest.py).
"""
from core.env.hub_vocabulary import default_config_path, load_vocabulary
from tests.core.env.test_hub_vocabulary import SEED_CATEGORIES


def test_shipped_config_has_the_seed(monkeypatch):
    monkeypatch.delenv("ACADEMIC_HUB_CONFIG")
    path = default_config_path()
    assert path.parts[-2:] == ("academic-hub", "hub_config.json")
    vocab = load_vocabulary(path)
    for name in SEED_CATEGORIES:
        assert vocab.kind_of(name) == "category", name
    for name in ("processed_outputs", "images", "assets"):
        assert vocab.kind_of(name) == "ignore", name
    # Owner answers (past_exams, summaries, ...) are added over time, so this only pins the seed.
    assert vocab.textbook_folders == ("textbooks", "textbooks-and-papers")
