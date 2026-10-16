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


def discover_chunks(tests_dir: Path) -> list[str]:
    return sorted(
        p.name
        for p in tests_dir.iterdir()
        if p.is_dir() and p.name != "__pycache__"
    )


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
