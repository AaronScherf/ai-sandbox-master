import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _collected_count(stdout: str) -> int:
    # pytest --collect-only -q ends with a line like "2/2 tests collected"
    # or, pre-filter, just "2 tests collected" -- pull the first number.
    for line in stdout.splitlines():
        if "collected" in line or "selected" in line:
            return int(line.split()[0].split("/")[0])
    return 0


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
    """With zero `local_llm`-marked tests in this file, `-m "not local_llm"`
    must collect the exact same count as an unfiltered run -- a typo'd
    marker name silently deselecting real tests is the failure mode this
    guards, so this checks the count matches, not just "some ran"."""
    unfiltered = subprocess.run(
        [sys.executable, "-m", "pytest", __file__, "-q", "--collect-only"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )
    filtered = subprocess.run(
        [sys.executable, "-m", "pytest", __file__, "-q", "-m", "not local_llm", "--collect-only"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )
    assert filtered.returncode == 0
    assert _collected_count(filtered.stdout) == _collected_count(unfiltered.stdout) > 0


def test_not_local_llm_does_not_raise_without_a_pytest_ini(tmp_path):
    """Review Focus: `-m "not local_llm"` must not error out if a future
    `pytest.ini` edit ever drops the marker registration -- pytest treats
    an unregistered marker expression as a warning, not a failure, and
    this pins that down rather than assuming it."""
    (tmp_path / "test_something.py").write_text(
        "def test_it():\n    assert True\n", encoding="utf-8"
    )
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", str(tmp_path), "-q", "-m", "not local_llm"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert "1 passed" in proc.stdout
