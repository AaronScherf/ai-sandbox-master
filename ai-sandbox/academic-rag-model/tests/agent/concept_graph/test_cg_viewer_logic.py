import shutil
import subprocess
from pathlib import Path

import pytest

TEST_FILE = Path(__file__).resolve().parents[3] / "agent" / "concept_graph" / "viewer" / "tests" / "logic.test.js"


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_viewer_logic_unit_tests_pass():
    result = subprocess.run(["node", "--test", str(TEST_FILE)], capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr
