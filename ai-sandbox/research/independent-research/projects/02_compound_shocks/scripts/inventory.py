"""Print a stable JSON inventory of files under data/raw (standard library only)."""

import hashlib
import json
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
RAW = PROJECT / "data" / "raw"


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def main() -> None:
    records = []
    if RAW.exists():
        for path in sorted(RAW.rglob("*")):
            if path.is_file() and path.name != ".gitkeep":
                records.append(
                    {
                        "path": path.relative_to(PROJECT).as_posix(),
                        "bytes": path.stat().st_size,
                        "sha256": digest(path),
                    }
                )
    print(json.dumps(records, indent=2))


if __name__ == "__main__":
    main()
