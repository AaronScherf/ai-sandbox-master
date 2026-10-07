import subprocess
from pathlib import Path


def git(cwd: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout


def write_and_commit(root: Path, files: dict[str, str], message: str) -> None:
    for rel, text in files.items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        git(root, "add", rel)
    git(root, "commit", "-q", "-m", message)


def make_repo(root: Path) -> Path:
    root.mkdir(parents=True)
    git(root, "init", "-q", "-b", "main")
    write_and_commit(root, {"core/a.py": "x = 1\n"}, "init")
    return root
