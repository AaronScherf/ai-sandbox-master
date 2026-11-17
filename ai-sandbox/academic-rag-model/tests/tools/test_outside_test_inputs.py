"""Guard for tools.land_branch.OUTSIDE_TEST_INPUTS.

The landing check skips tests for changes outside the project unless the path is in
OUTSIDE_TEST_INPUTS. A test that starts reading a new outside path would silently stop
being run for changes to it. This test finds tests that reach above the project root and
requires each one to be registered here against an allowlist entry.

Limits: it sees a test's own `Path(__file__)` parent chains and the `MONOREPO_ROOT`
constant. A path built any other way is invisible, so keep READERS current in review.
"""
import re
from pathlib import Path

from tools.land_branch import OUTSIDE_TEST_INPUTS

PROJECT = Path(__file__).resolve().parents[2]
TESTS = PROJECT / "tests"
NOVELTY = ("ai-sandbox/research/independent-research/notes/00_overview-and-strategy/"
           "03_novelty-check/Novelty Check - Summary - v3.md")

# test file name -> the OUTSIDE_TEST_INPUTS entry it depends on
READERS: dict[str, str] = {
    "test_lit_gap_report.py": ".gitignore",
    "test_audit_website_sync.py": "ai-sandbox/.obsidian",  # registry code_paths entry
    "test_reference_checker.py": NOVELTY,
}

_OWN_FILE = r"Path\(__file__\)(?:\.resolve\(\))?"
_PARENTS = re.compile(_OWN_FILE + r"\.parents\[(\d+)\]")
_PARENT_CHAIN = re.compile(_OWN_FILE + r"((?:\.parent)+)")


def _reaches_outside(path: Path, text: str) -> bool:
    for match in _PARENTS.finditer(text):
        if not path.parents[int(match.group(1))].is_relative_to(PROJECT):
            return True
    for match in _PARENT_CHAIN.finditer(text):
        depth = match.group(1).count(".parent")
        if not path.parents[depth - 1].is_relative_to(PROJECT):
            return True
    return "MONOREPO_ROOT" in text


def _outside_readers() -> set[str]:
    found = set()
    for path in TESTS.rglob("test_*.py"):
        if path.resolve() == Path(__file__).resolve():
            continue
        if _reaches_outside(path.resolve(), path.read_text(encoding="utf-8", errors="replace")):
            found.add(path.name)
    return found


def test_scanner_finds_the_known_outside_readers():
    # Without this, a scanner that matched nothing would pass vacuously.
    assert {"test_lit_gap_report.py", "test_reference_checker.py",
            "test_audit_website_sync.py"} <= _outside_readers()


def test_every_test_that_reads_outside_the_project_is_registered():
    unregistered = sorted(_outside_readers() - set(READERS))
    assert not unregistered, (
        f"{unregistered} read paths above the project root. Add each outside path to "
        "tools.land_branch.OUTSIDE_TEST_INPUTS and register the test in READERS here, or "
        "changes to those paths will land without running the test.")


def test_registered_readers_still_exist_and_point_at_the_allowlist():
    for name, entry in READERS.items():
        assert list(TESTS.rglob(name)), f"{name} no longer exists; drop it from READERS"
        assert entry in OUTSIDE_TEST_INPUTS, f"{name} depends on {entry!r}, not in OUTSIDE_TEST_INPUTS"
