"""Shared fixtures for tests/core."""
from pathlib import Path

import pytest

SEED_HUB_CONFIG = Path(__file__).parent / "env" / "seed_hub_config.json"


@pytest.fixture
def seed_hub_config(monkeypatch):
    """Point the hub vocabulary at a frozen, seed-only config.

    The shipped academic-hub/hub_config.json changes whenever the owner confirms a folder, so tests that pin
    "unconfirmed folders keep their legacy behavior" must not read it. The frozen copy is the config as it
    was before the first owner answers (commit fff259ee^).
    """
    monkeypatch.setenv("ACADEMIC_HUB_CONFIG", str(SEED_HUB_CONFIG))
    return SEED_HUB_CONFIG
