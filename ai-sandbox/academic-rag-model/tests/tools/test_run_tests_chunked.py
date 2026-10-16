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
