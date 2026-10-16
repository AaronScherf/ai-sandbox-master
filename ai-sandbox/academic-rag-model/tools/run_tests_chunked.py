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

# pytest exit codes that are not a real failure of the tests themselves:
# 0 = all passed, 5 = no tests were collected for that target.
# Everything else (1 = test failures, 2 = collection error, 3 = internal
# error, 4 = usage error, or a crash/kill code) counts as failed -- the
# chunked gate must not be weaker than a plain `pytest tests/ -q` run,
# whose caller already treated `returncode != 0` as failed.
_NON_FAILING_RETURNCODES = {0, 5}


def chunk_failed(returncode: int) -> bool:
    return returncode not in _NON_FAILING_RETURNCODES


def discover_chunks(tests_dir: Path) -> list[str]:
    if not tests_dir.is_dir():
        return []
    return sorted(
        p.name
        for p in tests_dir.iterdir()
        if p.is_dir() and p.name != "__pycache__"
    )


def discover_root_test_files(tests_dir: Path) -> list[str]:
    """Loose tests/test_*.py files that discover_chunks (directories only)
    would otherwise silently drop."""
    if not tests_dir.is_dir():
        return []
    return sorted(
        f"tests/{p.name}"
        for p in tests_dir.iterdir()
        if p.is_file() and p.name.startswith("test_") and p.suffix == ".py"
    )


@dataclass
class ChunkResult:
    name: str
    returncode: int
    seconds: float
    stdout: str


# Sentinel returncode for a subprocess that never ran at all (e.g. the
# interpreter path was wrong) -- not in _NON_FAILING_RETURNCODES, so
# chunk_failed() correctly flags it, and distinct from any real pytest
# exit code.
_COULD_NOT_START = -1


def _run_one(name: str, cmd: list[str], project_root: Path, runner) -> ChunkResult:
    started = time.monotonic()
    try:
        proc = runner(
            cmd,
            cwd=project_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError as exc:
        return ChunkResult(
            name=name,
            returncode=_COULD_NOT_START,
            seconds=time.monotonic() - started,
            stdout=f"could not start subprocess for {cmd!r}: {exc}",
        )
    return ChunkResult(
        name=name,
        returncode=proc.returncode,
        seconds=time.monotonic() - started,
        stdout=proc.stdout,
    )


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
        cmd = [sys.executable, "-m", "pytest", f"tests/{chunk}", "-q", "-m", "not local_llm"]
        results.append(_run_one(chunk, cmd, project_root, runner))

    root_files = discover_root_test_files(tests_dir)
    if root_files:
        cmd = [sys.executable, "-m", "pytest", *root_files, "-q", "-m", "not local_llm"]
        results.append(_run_one("(root)", cmd, project_root, runner))

    if include_local_llm:
        cmd = [sys.executable, "-m", "pytest", "tests/", "-q", "-m", "local_llm"]
        results.append(_run_one("local_llm (opt-in)", cmd, project_root, runner))

    status = "failed" if any(chunk_failed(r.returncode) for r in results) else "passed"
    return status, results, time.monotonic() - total_started


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
        outcome = "FAILED" if chunk_failed(r.returncode) else "passed"
        print(f"[{outcome}] tests/{r.name} ({r.seconds:.1f}s)")
        if chunk_failed(r.returncode):
            print(r.stdout[-4000:])

    print(f"=== {status} in {total_seconds:.1f}s across {len(results)} chunk(s) ===")
    return 1 if status == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
