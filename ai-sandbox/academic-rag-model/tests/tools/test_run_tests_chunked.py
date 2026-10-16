from pathlib import Path

from tools.run_tests_chunked import (
    ChunkResult,
    discover_chunks,
    discover_root_test_files,
    main,
    run_all,
)


def test_discover_chunks_lists_immediate_subdirs_only(tmp_path):
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "agent").mkdir()
    (tests_dir / "core").mkdir()
    (tests_dir / "__pycache__").mkdir()
    (tests_dir / "conftest.py").write_text("", encoding="utf-8")

    assert discover_chunks(tests_dir) == ["agent", "core"]


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
        returncode = 5  # pytest's "no tests collected"
        stdout = "no tests ran"

    status, results, seconds = run_all(tmp_path, runner=lambda cmd, **kw: FakeCompleted())

    assert status == "passed"
    assert results[0].returncode == 5


def test_run_all_passes_when_every_chunk_passes(tmp_path):
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "agent").mkdir()

    class FakeCompleted:
        returncode = 0
        stdout = "ok"

    status, results, seconds = run_all(tmp_path, runner=lambda cmd, **kw: FakeCompleted())

    assert status == "passed"


def test_run_all_treats_collection_error_as_failed(tmp_path):
    """Finding (final review, Critical): pytest exit code 2 is a collection
    error -- e.g. this branch's own jsonschema ModuleNotFoundError. Only
    checking `returncode == 1` let that pass as green."""
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "broken").mkdir()

    class FakeCompleted:
        returncode = 2
        stdout = "ImportError: No module named 'jsonschema'"

    status, results, seconds = run_all(tmp_path, runner=lambda cmd, **kw: FakeCompleted())

    assert status == "failed"


def test_run_all_treats_a_crash_exit_code_as_failed(tmp_path):
    """Finding (final review, Critical): a crashed/killed subprocess (e.g.
    Windows access-violation 0xC0000005, or an internal pytest error = 3)
    returns a code that is neither 0, 1 nor 5 -- must still count as
    failed, which is the exact scenario the OOM this branch fixes used to
    produce."""
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "crashy").mkdir()

    class FakeCompleted:
        returncode = 0xC0000005
        stdout = ""

    status, results, seconds = run_all(tmp_path, runner=lambda cmd, **kw: FakeCompleted())

    assert status == "failed"


def test_discover_root_test_files_lists_top_level_test_py_only(tmp_path):
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_a.py").write_text("", encoding="utf-8")
    (tests_dir / "test_b.py").write_text("", encoding="utf-8")
    (tests_dir / "conftest.py").write_text("", encoding="utf-8")
    (tests_dir / "agent").mkdir()

    assert discover_root_test_files(tests_dir) == ["tests/test_a.py", "tests/test_b.py"]


def test_run_all_also_runs_top_level_test_files(tmp_path):
    """Finding (final review, Important): discover_chunks only lists
    directories, so a loose tests/test_*.py file (this branch added one:
    tests/test_pytest_ini_markers.py) was silently dropped by both the
    chunked runner and, through it, the land_branch landing gate."""
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_root.py").write_text("", encoding="utf-8")

    calls = []

    class FakeCompleted:
        returncode = 0
        stdout = "ok"

    def fake_runner(cmd, **kwargs):
        calls.append(cmd)
        return FakeCompleted()

    status, results, seconds = run_all(tmp_path, runner=fake_runner)

    assert any("tests/test_root.py" in cmd for cmd in calls)
    assert any(r.name == "(root)" for r in results)


def test_run_all_reports_a_chunk_whose_subprocess_cannot_start(tmp_path):
    """Review Focus: a subprocess that can't start (bad interpreter path,
    permissions, etc.) must surface as a clear failure naming the attempted
    command, not an uncaught traceback with no chunk name."""
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "agent").mkdir()

    def broken_runner(cmd, **kwargs):
        raise OSError("[WinError 2] The system cannot find the file specified")

    status, results, seconds = run_all(tmp_path, runner=broken_runner)

    assert status == "failed"
    assert results[0].name == "agent"
    assert "cannot find the file" in results[0].stdout
    assert "pytest" in results[0].stdout  # names the attempted command


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
