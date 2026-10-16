import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_local_llm_marker_is_registered_without_warning():
    """`pytest.ini` must register `local_llm`; an unregistered marker emits
    a PytestUnknownMarkWarning, which this pins against."""
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "--markers"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )
    assert "local_llm" in proc.stdout


def test_not_local_llm_selects_everything_when_nothing_is_marked():
    """With zero `local_llm`-marked tests in the repo, `-m "not local_llm"`
    must still collect this very test file's items -- a typo'd marker name
    silently deselecting real tests is the failure mode this guards."""
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", __file__, "-q", "-m", "not local_llm", "--collect-only"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )
    assert "no tests ran" not in proc.stdout.lower()
    assert proc.returncode == 0
