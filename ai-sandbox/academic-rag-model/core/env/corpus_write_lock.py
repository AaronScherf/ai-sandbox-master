"""Cooperative, cross-process write lease for corpus repositories.

Every participating writer must hold this lease for its entire write action.
The lock is local to this machine; it cannot coordinate Obsidian Git sync or
remote GCP/GCS writers. Those destinations need separate gates.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Sequence

RUN_TOKEN_ENV = "CORPUS_WRITE_RUN_TOKEN"


class CorpusWriteLockError(RuntimeError):
    """A writer could not establish exclusive ownership of its repositories."""


@dataclass(frozen=True)
class CorpusWriteLease:
    token: str
    action: str
    roots: tuple[Path, ...]

    def child_env(self) -> dict[str, str]:
        """Environment for a child writer that joins this still-live lease."""
        return {**os.environ, RUN_TOKEN_ENV: self.token}


def _repository_identity(path: str | Path) -> tuple[Path, Path]:
    source = Path(path).resolve(strict=True)
    if not source.is_dir():
        source = source.parent
    try:
        root = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"], cwd=source,
            check=True, text=True, capture_output=True,
        ).stdout.strip()
        common = subprocess.run(
            ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
            cwd=source, check=True, text=True, capture_output=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise CorpusWriteLockError(f"cannot resolve repository for {source}: {exc}") from exc
    return Path(root).resolve(), Path(common).resolve()


def _lock_paths(common: Path, state_dir: Path | None) -> tuple[Path, Path]:
    # The Git common directory is shared by all worktrees of one repository.
    # A caller-supplied state directory is only useful for isolated fixtures.
    directory = state_dir or common / "corpus-write-locks"
    key = hashlib.sha256(os.path.normcase(str(common)).encode("utf-8")).hexdigest()[:24]
    return directory / f"{key}.lock", directory / f"{key}.owner.json"


def _try_lock(handle) -> bool:
    if os.name == "nt":
        import msvcrt

        if os.fstat(handle.fileno()).st_size == 0:
            handle.seek(0)
            handle.write(b"0")
            handle.flush()
        try:
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            return True
        except OSError:
            return False
    import fcntl

    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except BlockingIOError:
        return False


def _unlock(handle) -> None:
    if os.name == "nt":
        import msvcrt

        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _owner(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def _describe(owner: dict, roots: tuple[Path, ...]) -> str:
    return (
        f"active owner pid={owner.get('pid', 'unknown')} "
        f"action={owner.get('action', 'unknown')} "
        f"roots={owner.get('roots', [str(root) for root in roots])}"
    )


def _write_owner(path: Path, owner: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix="owner-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(owner, stream, sort_keys=True)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@contextmanager
def corpus_write_lock(
    roots: Sequence[str | Path], action: str, *,
    run_token: str | None = None, state_dir: str | Path | None = None,
) -> Iterator[CorpusWriteLease]:
    """Acquire one exclusive lock per Git repository, or join a live run.

    Nested writers must receive the parent's random token explicitly or via
    ``CorpusWriteLease.child_env()``. Joining checks both metadata and the OS
    lock. The parent must keep its lease open until every child has exited.
    A dead owner's metadata never grants ownership: the OS lock is authoritative.
    """
    if not roots or not action.strip():
        raise ValueError("nonempty roots and action are required")
    repositories: dict[Path, Path] = {}
    for path in roots:
        root, common = _repository_identity(path)
        repositories.setdefault(common, root)
    ordered = sorted(repositories.items(), key=lambda item: os.path.normcase(str(item[0])))
    canonical_roots = tuple(root for _, root in ordered)
    directory = Path(state_dir).resolve() if state_dir is not None else None
    inherited = run_token or os.environ.get(RUN_TOKEN_ENV)
    if inherited is not None and (len(inherited) != 32 or any(c not in "0123456789abcdef" for c in inherited)):
        raise CorpusWriteLockError("invalid corpus write run token")
    token = inherited or uuid.uuid4().hex
    held: list[tuple[object, Path]] = []
    try:
        for common, _ in ordered:
            lock_path, owner_path = _lock_paths(common, directory)
            lock_path.parent.mkdir(parents=True, exist_ok=True)
            handle = lock_path.open("a+b")
            acquired = _try_lock(handle)
            if inherited:
                owner = _owner(owner_path)
                if acquired:
                    _unlock(handle)
                    handle.close()
                    raise CorpusWriteLockError(f"run token has no live owner for {common}")
                handle.close()
                # A child may target one repository of a multi-root parent.
                # The token and live OS lock establish ownership; the parent
                # recorded its full root set for diagnostics.
                if owner.get("token") != token or owner.get("status") != "active":
                    raise CorpusWriteLockError(f"cannot join writer for {common}: {_describe(owner, canonical_roots)}")
                continue
            if not acquired:
                handle.close()
                raise CorpusWriteLockError(f"writer already active for {common}: {_describe(_owner(owner_path), canonical_roots)}")
            held.append((handle, owner_path))
            _write_owner(owner_path, {
                "token": token, "pid": os.getpid(), "action": action,
                "roots": [str(root) for root in canonical_roots],
                "status": "active",
                "started_at": datetime.now(timezone.utc).isoformat(),
            })
        yield CorpusWriteLease(token, action, canonical_roots)
    finally:
        for handle, owner_path in reversed(held):
            try:
                owner = _owner(owner_path)
                if owner.get("token") == token:
                    owner["status"] = "released"
                    owner["released_at"] = datetime.now(timezone.utc).isoformat()
                    _write_owner(owner_path, owner)
            finally:
                _unlock(handle)
                handle.close()
