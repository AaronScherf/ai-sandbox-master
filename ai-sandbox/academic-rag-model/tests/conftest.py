"""Suite-wide pin of the hub vocabulary.

The shipped academic-hub/hub_config.json changes whenever the owner confirms a folder. Every test
reads the frozen seed instead, so a hub-config edit cannot break or select the suite. The one test
that validates the shipped file is tests/core/env/test_shipped_hub_config.py; it unsets this.
A test that needs a different vocabulary sets ACADEMIC_HUB_CONFIG itself.
"""
from pathlib import Path

import pytest

SEED_HUB_CONFIG = Path(__file__).parent / "core" / "env" / "seed_hub_config.json"


@pytest.fixture(autouse=True)
def _pin_hub_config_to_seed(monkeypatch):
    monkeypatch.setenv("ACADEMIC_HUB_CONFIG", str(SEED_HUB_CONFIG))
