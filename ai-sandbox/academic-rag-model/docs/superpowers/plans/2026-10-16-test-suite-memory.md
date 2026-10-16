# Test Suite Memory / OOM Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop the pytest suite from OOMing by running it as per-package subprocesses instead of
one long-lived process, and add a default-excluded `local_llm` marker so any future tests that
load real local-model backends don't silently join the default run.

**Architecture:** A new `tools/run_tests_chunked.py` runs `pytest tests/<dir> -q -m "not local_llm"`
as a separate subprocess per top-level `tests/` directory, sequentially, so the OS reclaims memory
between chunks; it aggregates pass/fail/timing across chunks. `tools/land_branch.py:run_checks()`'s
`full=True` path calls this instead of its current single `pytest tests/ -q` subprocess. A new
`pytest.ini` registers the `local_llm` marker (unused today, but available). Separately, the venv's
missing `jsonschema` package is installed so `tools/` test collection isn't broken.

**Tech Stack:** Python 3.13, pytest, `subprocess` (stdlib) — no new dependencies.

**Spec:** `docs/superpowers/specs/2026-10-16-test-suite-memory.md`

## Global Constraints

- No `pytest-xdist` and no parallel chunk execution — chunks run sequentially (spec §3: parallel
  would multiply peak memory, the opposite of the goal).
- `tools/run_tests_chunked.py` must not hardcode the list of `tests/` subdirectories — it
  discovers them so new packages are picked up automatically (spec §4).
- `run_checks()`'s existing `(status, targets, seconds)` return contract and its `full=False`
  changed-package-subset path are unchanged (spec §5) — only the `full=True` branch's internal
  mechanism changes.
- The `local_llm` marker is infrastructure only in this plan — no test in this repo gets marked
  `local_llm` as part of this work (spec §2: zero current tests exercise the real local-model
  path; nothing exists to mark).
- This work happens in a dedicated `claude/<task>` worktree/branch per the root `CLAUDE.md`
  worktree procedure — it touches `tools/` and `pytest.ini`, both code, not the to-do-tracker
  exemption.

## Review Focus

- A chunk directory that exists but currently collects zero tests (e.g. an empty or
  `__pycache__`-only entry under `tests/`) should not be reported as a failure — pytest's exit
  code 5 ("no tests collected") must be treated as a distinct, non-failing outcome, not folded
  into "failed" alongside a real test failure (exit code 1).
- A chunk whose subprocess itself cannot start (e.g. bad `sys.executable` path) must surface as a
  clear failure with the attempted command, not a silent empty result.
- `land_branch.py`'s existing behavior of printing a failing run's stdout tail
  (`proc.stdout[-4000:]`) must be preserved per-chunk when the chunked path is used — a landing
  failure needs to show which chunk failed and why, not just "failed" with no detail.
- Running the chunked runner from a directory other than the project root must still work — it is
  invoked by `land_branch.py` with an explicit `project_root`, and should also work when a human
  runs `python tools/run_tests_chunked.py` directly from `academic-rag-model/`.
- The `-m "not local_llm"` marker expression must not raise if `pytest.ini`'s marker registration
  is ever absent/misconfigured — pytest treats an unregistered marker as a warning, not an error,
  but the plan's own test should pin that `-m "not local_llm"` selects everything when nothing is
  marked, so a future typo in the marker name doesn't silently deselect real tests.

---

## Task 1: Fix the `jsonschema` venv drift

No repository files change — this is a local environment fix so the `tools/` chunk can collect
all its tests (3 files currently fail collection with `ModuleNotFoundError: No module named
'jsonschema'`, confirmed live 2026-10-16). `.venv/` is gitignored, so there is nothing to commit.

**Files:**
- None (environment only).
- Test: `tests/tools/test_audit_website_sync.py`, `tests/tools/test_audit_website_sync_git.py`,
  `tests/tools/test_website_sync_scan.py` (existing files; currently fail at collection, not at
  assertion).

- [ ] **Step 1: Confirm the current failure**

Run: `.venv\Scripts\python.exe -m pytest tests/tools/test_audit_website_sync.py --collect-only -q`
Expected: `ModuleNotFoundError: No module named 'jsonschema'`

- [ ] **Step 2: Install from the pinned requirements**

Run: `.venv\Scripts\python.exe -m pip install -r requirements.txt`
This installs `jsonschema>=4.23,<5` (already pinned in `requirements.txt:20`) along with
re-confirming every other pin is satisfied; it's a no-op for packages already present.

- [ ] **Step 3: Verify collection now succeeds**

Run: `.venv\Scripts\python.exe -m pytest tests/tools/test_audit_website_sync.py tests/tools/test_audit_website_sync_git.py tests/tools/test_website_sync_scan.py -q`
Expected: tests run (pass or fail on their own merits) instead of a collection error.

No commit for this task — nothing in the repo changed.

## Task 2: Register the `local_llm` marker

**Files:**
- Create: `pytest.ini` (project root, `academic-rag-model/pytest.ini` — none exists today).
- Test: `tests/test_pytest_ini_markers.py` (new).

**Interfaces:**
- Produces: a registered `local_llm` pytest marker, usable as `@pytest.mark.local_llm` by future
  tests, and the marker-expression contract `-m "not local_llm"` selects everything when no test
  is marked (verified in Step 2 below, since there are zero `local_llm`-marked tests in this repo
  today to test the positive case against).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_pytest_ini_markers.py
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
```

- [ ] **Step 2: Run it to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/test_pytest_ini_markers.py -v`
Expected: `test_local_llm_marker_is_registered_without_warning` FAILs (`local_llm` not in
`--markers` output, since `pytest.ini` doesn't exist yet).

- [ ] **Step 3: Create `pytest.ini`**

```ini
[pytest]
markers =
    local_llm: exercises a real local-model backend (transformers, faster-whisper, piper, kokoro_onnx) instead of a mocked call site. Excluded from the default and tools/run_tests_chunked.py runs; opt in with -m local_llm.
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv\Scripts\python.exe -m pytest tests/test_pytest_ini_markers.py -v`
Expected: both tests PASS.

- [ ] **Step 5: Commit**

```bash
git add pytest.ini tests/test_pytest_ini_markers.py
git commit -m "test(pytest): register local_llm marker, excluded by default"
```

## Task 3: Build the chunked test runner

**Files:**
- Create: `tools/run_tests_chunked.py`
- Test: `tests/tools/test_run_tests_chunked.py` (new)

**Interfaces:**
- Consumes: nothing from earlier tasks (standalone module); reads `pytest.ini`'s `local_llm`
  marker indirectly via the `-m` flag it passes to pytest (no direct code dependency).
- Produces, for Task 4 to consume:
  - `discover_chunks(tests_dir: Path) -> list[str]` — sorted list of directory names directly
    under `tests_dir` (e.g. `["agent", "audio_generator", "core", "discovery", "pipelines",
    "resume_manager", "tools"]`), skipping `__pycache__` and anything that isn't a directory.
  - `@dataclass class ChunkResult: name: str; returncode: int; seconds: float; stdout: str`
  - `run_all(project_root: Path, *, include_local_llm: bool = False, runner=subprocess.run) -> tuple[str, list[ChunkResult], float]` — returns `(status, results, total_seconds)` where
    `status` is `"passed"` or `"failed"` (`"failed"` if any `ChunkResult.returncode` is 1; a
    chunk returning 5 — pytest's "no tests collected" — does not count as failed per Review
    Focus). `runner` is injectable (defaults to `subprocess.run`) so tests don't shell out to a
    real nested pytest.
  - `main(argv: list[str] | None = None) -> int` — CLI entry point; `--include-local-llm` flag;
    prints one summary line per chunk and, for any failed chunk, its `stdout[-4000:]`.

- [ ] **Step 1: Write the failing test for `discover_chunks`**

```python
# tests/tools/test_run_tests_chunked.py
from pathlib import Path

from tools.run_tests_chunked import ChunkResult, discover_chunks, main, run_all


def test_discover_chunks_lists_immediate_subdirs_only(tmp_path):
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "agent").mkdir()
    (tests_dir / "core").mkdir()
    (tests_dir / "__pycache__").mkdir()
    (tests_dir / "conftest.py").write_text("", encoding="utf-8")

    assert discover_chunks(tests_dir) == ["agent", "core"]
```

- [ ] **Step 2: Run it to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/tools/test_run_tests_chunked.py::test_discover_chunks_lists_immediate_subdirs_only -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tools.run_tests_chunked'`

- [ ] **Step 3: Write `discover_chunks`**

```python
# tools/run_tests_chunked.py
"""Run the pytest suite as one subprocess per top-level tests/ package, so
memory is released between chunks instead of accumulating across one long
process (see docs/superpowers/specs/2026-10-16-test-suite-memory.md).
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
NO_TESTS_COLLECTED = 5


def discover_chunks(tests_dir: Path) -> list[str]:
    return sorted(
        p.name
        for p in tests_dir.iterdir()
        if p.is_dir() and p.name != "__pycache__"
    )
```

- [ ] **Step 4: Run it to verify it passes**

Run: `.venv\Scripts\python.exe -m pytest tests/tools/test_run_tests_chunked.py::test_discover_chunks_lists_immediate_subdirs_only -v`
Expected: PASS

- [ ] **Step 5: Write the failing test for `run_all`'s aggregation and sequencing**

```python
def test_run_all_runs_one_subprocess_per_chunk_and_aggregates_failure(tmp_path):
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "agent").mkdir()
    (tests_dir / "core").mkdir()

    calls = []

    class FakeCompleted:
        def __init__(self, returncode, stdout):
            self.returncode = returncode
            self.stdout = stdout

    def fake_runner(cmd, **kwargs):
        calls.append(cmd)
        if "tests/agent" in cmd:
            return FakeCompleted(1, "FAILED agent test")
        return FakeCompleted(0, "ok")

    status, results, seconds = run_all(tmp_path, runner=fake_runner)

    assert status == "failed"
    assert [r.name for r in results] == ["agent", "core"]
    assert [r.returncode for r in results] == [1, 0]
    assert len(calls) == 2
    assert all("-m" in cmd and "not local_llm" in cmd for cmd in calls)


def test_run_all_treats_no_tests_collected_as_not_failed(tmp_path):
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "empty_pkg").mkdir()

    class FakeCompleted:
        returncode = NO_TESTS_COLLECTED
        stdout = "no tests ran"

    status, results, seconds = run_all(tmp_path, runner=lambda cmd, **kw: FakeCompleted())

    assert status == "passed"
    assert results[0].returncode == NO_TESTS_COLLECTED


def test_run_all_passes_when_every_chunk_passes(tmp_path):
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "agent").mkdir()

    class FakeCompleted:
        returncode = 0
        stdout = "ok"

    status, results, seconds = run_all(tmp_path, runner=lambda cmd, **kw: FakeCompleted())

    assert status == "passed"
```

- [ ] **Step 6: Run to verify these fail**

Run: `.venv\Scripts\python.exe -m pytest tests/tools/test_run_tests_chunked.py -v`
Expected: the three new tests FAIL (`ImportError: cannot import name 'run_all'` /
`ChunkResult`), the `discover_chunks` test still PASSes.

- [ ] **Step 7: Implement `ChunkResult` and `run_all`**

```python
@dataclass
class ChunkResult:
    name: str
    returncode: int
    seconds: float
    stdout: str


def run_all(
    project_root: Path,
    *,
    include_local_llm: bool = False,
    runner=subprocess.run,
) -> tuple[str, list[ChunkResult], float]:
    tests_dir = project_root / "tests"
    results: list[ChunkResult] = []
    total_started = time.monotonic()

    for chunk in discover_chunks(tests_dir):
        started = time.monotonic()
        proc = runner(
            [
                sys.executable, "-m", "pytest", f"tests/{chunk}", "-q",
                "-m", "not local_llm",
            ],
            cwd=project_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        results.append(ChunkResult(
            name=chunk,
            returncode=proc.returncode,
            seconds=time.monotonic() - started,
            stdout=proc.stdout,
        ))

    if include_local_llm:
        started = time.monotonic()
        proc = runner(
            [sys.executable, "-m", "pytest", "tests/", "-q", "-m", "local_llm"],
            cwd=project_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        results.append(ChunkResult(
            name="local_llm (opt-in)",
            returncode=proc.returncode,
            seconds=time.monotonic() - started,
            stdout=proc.stdout,
        ))

    status = "failed" if any(r.returncode == 1 for r in results) else "passed"
    return status, results, time.monotonic() - total_started
```

Note: real `subprocess.run` calls always supply `cwd`/`capture_output`/`text`/`encoding`/`errors`
as keyword arguments, which is why the test fakes accept `**kwargs` and ignore them, and why the
`"-m" in cmd and "not local_llm" in cmd` assertion checks the positional `cmd` list, not kwargs.

- [ ] **Step 8: Run to verify they pass**

Run: `.venv\Scripts\python.exe -m pytest tests/tools/test_run_tests_chunked.py -v`
Expected: all four tests PASS.

- [ ] **Step 9: Write the failing test for the CLI entry point**

```python
def test_main_returns_nonzero_and_prints_failing_chunk_stdout(monkeypatch, capsys):
    # Patches run_all itself, not subprocess.run: run_all's `runner=subprocess.run`
    # default is bound once at import time, so patching the subprocess module's
    # attribute afterward would not reach it -- main() looks up `run_all` as a
    # bare module-global name on every call, so patching that name does.
    fake_results = [ChunkResult(name="agent", returncode=1, seconds=1.0, stdout="AssertionError: boom")]
    monkeypatch.setattr(
        "tools.run_tests_chunked.run_all",
        lambda project_root, include_local_llm=False: ("failed", fake_results, 1.0),
    )

    exit_code = main([])

    assert exit_code == 1
    captured = capsys.readouterr()
    assert "agent" in captured.out
    assert "boom" in captured.out
```

- [ ] **Step 10: Run to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/tools/test_run_tests_chunked.py::test_main_returns_nonzero_and_prints_failing_chunk_stdout -v`
Expected: FAIL (`AttributeError`/`ImportError` — `main` not defined yet).

- [ ] **Step 11: Implement `main`**

```python
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--include-local-llm",
        action="store_true",
        help="also run local_llm-marked tests as one additional pass",
    )
    args = parser.parse_args(argv)

    status, results, total_seconds = run_all(
        PROJECT_ROOT, include_local_llm=args.include_local_llm
    )

    for r in results:
        outcome = "FAILED" if r.returncode == 1 else "passed"
        print(f"[{outcome}] tests/{r.name} ({r.seconds:.1f}s)")
        if r.returncode == 1:
            print(r.stdout[-4000:])

    print(f"=== {status} in {total_seconds:.1f}s across {len(results)} chunk(s) ===")
    return 1 if status == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 12: Run to verify it passes**

Run: `.venv\Scripts\python.exe -m pytest tests/tools/test_run_tests_chunked.py -v`
Expected: all five tests PASS.

- [ ] **Step 13: Commit**

```bash
git add tools/run_tests_chunked.py tests/tools/test_run_tests_chunked.py
git commit -m "feat(tools): run the pytest suite as one subprocess per package

Frees memory between packages instead of accumulating across one long
pytest process; fixes the OOM reproduced running the full suite directly."
```

## Task 4: Wire the chunked runner into `land_branch.py`'s full-suite gate

**Files:**
- Modify: `tools/land_branch.py:167-186` (`run_checks`)
- Test: `tests/tools/test_land_branch.py` (add to existing file)

**Interfaces:**
- Consumes: `tools.run_tests_chunked.run_all` and `ChunkResult` from Task 3.
- Produces: `run_checks` keeps its existing signature and return type
  (`tuple[str, list[str], float]`) unchanged — `_run_check` (`tools/land_branch.py:201+`), which
  calls it, needs no changes.

- [ ] **Step 1: Write the failing test**

Add to `tests/tools/test_land_branch.py` (alongside the existing imports — add
`from unittest.mock import patch` and `from tools.run_tests_chunked import ChunkResult` to its
import block):

```python
class RunChecksFullSuiteTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_full_run_uses_chunked_runner_and_reports_failure(self):
        from tools.land_branch import run_checks

        fake_results = [
            ChunkResult(name="agent", returncode=0, seconds=1.0, stdout="ok"),
            ChunkResult(name="core", returncode=1, seconds=2.0, stdout="boom"),
        ]
        with patch(
            "tools.land_branch.run_all",
            return_value=("failed", fake_results, 3.0),
        ) as mock_run_all:
            status, targets, seconds = run_checks(self.tmp, changed=set(), full=True)

        mock_run_all.assert_called_once_with(self.tmp)
        self.assertEqual(status, "failed")
        self.assertEqual(targets, ["tests/agent", "tests/core"])
        self.assertEqual(seconds, 3.0)
```

- [ ] **Step 2: Run it to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/tools/test_land_branch.py::RunChecksFullSuiteTests -v`
Expected: FAIL — `run_checks` still shells out to a single real `pytest tests/` subprocess, so
`mock_run_all` (patching a name that doesn't exist yet in `land_branch`) raises
`AttributeError: <module 'tools.land_branch'> does not have the attribute 'run_all'`.

- [ ] **Step 3: Import and call the chunked runner**

In `tools/land_branch.py`, add to the existing import block (near the top, after the `import
time` line):

```python
from tools.run_tests_chunked import run_all
```

Replace the body of `run_checks` (`tools/land_branch.py:167-186`):

```python
def run_checks(project_root: Path, changed: set[str], full: bool) -> tuple[str, list[str], float]:
    if not full and _is_documentation_only(changed):
        return "skipped", [], 0.0
    if full:
        status, results, seconds = run_all(project_root)
        targets = [f"tests/{r.name}" for r in results]
        for r in results:
            if r.returncode == 1:
                print(f"[FAILED] tests/{r.name}")
                print(r.stdout[-4000:])
        return status, targets, seconds
    targets = select_test_targets(changed, project_root)
    if not targets:
        targets = ["tests/"]  # code changed but no mapped tests: run everything
    started = time.monotonic()
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", *targets, "-q"],
        cwd=project_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    seconds = time.monotonic() - started
    if proc.returncode != 0:
        print(proc.stdout[-4000:])
        return "failed", targets, seconds
    return "passed", targets, seconds
```

- [ ] **Step 4: Run to verify the new test passes and nothing else broke**

Run: `.venv\Scripts\python.exe -m pytest tests/tools/test_land_branch.py -v`
Expected: all tests in the file PASS, including the pre-existing ones (the `full=False` path is
untouched).

- [ ] **Step 5: Commit**

```bash
git add tools/land_branch.py tests/tools/test_land_branch.py
git commit -m "fix(tools): land_branch's full-suite gate uses the chunked runner

Was a single pytest tests/ -q subprocess, which OOMs on this machine.
Delegates to tools/run_tests_chunked.run_all instead."
```

## Task 5: Document the chunked runner, and caution the stale `pytest-xdist` to-do

**Files:**
- Modify: `academic-rag-model/CLAUDE.md` (the "Commands" section's "Tests:" line)
- Modify: `academic-rag-model/docs/trackers/academic_hub_to_do.md:170` (the existing
  `pytest-xdist` candidate-change item)

No test — documentation-only changes, bundled with Task 1-4's code changes so they land in the
same review.

- [ ] **Step 1: Caution the `pytest-xdist` to-do item (spec §6)**

Current text (`docs/trackers/academic_hub_to_do.md:170`):
```
4. **Faster tests:** install `pytest-xdist` (`-n auto`) and/or a path-to-tests mapper so iteration runs
   only affected packages; keep the full suite for landing. Not measured; the ~25 s figure is a guess.
```

New text:
```
4. **Faster tests:** install `pytest-xdist` (`-n auto`) and/or a path-to-tests mapper so iteration runs
   only affected packages; keep the full suite for landing. Not measured; the ~25 s figure is a guess.
   **Caution (2026-10-16):** the full suite's problem turned out to be memory, not CPU
   (`docs/superpowers/specs/2026-10-16-test-suite-memory.md`) -- `tools/run_tests_chunked.py`
   already fixes that by running chunks sequentially. Parallel `-n auto` workers would each
   re-import and hold their own copy of everything, making memory *worse*. If this is picked up,
   measure peak memory with a small fixed `-n` first, not `auto`.
```

- [ ] **Step 2: Edit the Tests line**

Current text (`CLAUDE.md:7`):
```
- Tests: `python -m pytest tests/` — prefer a single file or `-k` filter over the full suite. `tests/` mirrors the package tree (`tests/pipelines/...`, `tests/agent/...`, `tests/core/...`, etc.).
```

New text:
```
- Tests: `python -m pytest tests/` for a single file or `-k` filter while iterating. `tests/` mirrors the package tree (`tests/pipelines/...`, `tests/agent/...`, `tests/core/...`, etc.). For the full suite, use `python tools/run_tests_chunked.py` instead of `pytest tests/` directly — it runs one subprocess per top-level package so memory is freed between them; a single long-lived `pytest tests/` process has OOM'd on this machine. Pass `--include-local-llm` to also run tests marked `local_llm` (none exist yet; see `pytest.ini`).
```

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md docs/trackers/academic_hub_to_do.md
git commit -m "docs(academic-rag-model): point full-suite runs at the chunked runner

Also cautions the existing pytest-xdist to-do item: the suite's problem
is memory, not CPU, so -n auto would make it worse, not better."
```

## Task 6: End-to-end verification

**Files:** none (verification only).

- [ ] **Step 1: Run the full suite via the new entry point**

Run: `.venv\Scripts\python.exe tools/run_tests_chunked.py`
Expected: it runs 7 chunks (`agent`, `audio_generator`, `core`, `discovery`, `pipelines`,
`resume_manager`, `tools`) sequentially, prints a per-chunk summary line, and exits 0 if the
suite as a whole is green (fix any real test failures surfaced here before landing — they are
pre-existing and out of scope for this plan, but must not be silently hidden by it).

- [ ] **Step 2: Confirm the `tools/` chunk no longer fails on `jsonschema`**

Check the printed summary for `tests/tools` — it must show `passed`, not the
`ModuleNotFoundError` from before Task 1.

- [ ] **Step 3: Confirm `land_branch.py`'s full-suite path calls the same runner**

Run: `.venv\Scripts\python.exe -m pytest tests/tools/test_land_branch.py tests/tools/test_run_tests_chunked.py tests/test_pytest_ini_markers.py -v`
Expected: all PASS. This is the full set of tests this plan added or touched.
