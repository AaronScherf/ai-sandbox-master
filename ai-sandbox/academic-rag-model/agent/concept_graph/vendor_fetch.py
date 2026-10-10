"""One-time downloader for the vendored viewer libraries (run by hand; output is committed)."""
from __future__ import annotations

import hashlib
import json
import urllib.request
from pathlib import Path

VIEWER_DIR = Path(__file__).resolve().parent / "viewer"


def fetch_all(vendor_dir: Path, lock_path: Path, opener=urllib.request.urlopen) -> None:
    """Download every file in the lock; verify known hashes, record unknown ones (trust on first use)."""
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    downloaded = []
    for entry in lock["files"]:
        data = opener(entry["url"]).read()
        digest = hashlib.sha256(data).hexdigest()
        if entry.get("sha256") and entry["sha256"] != digest:
            raise ValueError(f"{entry['file']}: downloaded hash {digest} does not match the locked {entry['sha256']}")
        downloaded.append((entry, data, digest))
    vendor_dir.mkdir(parents=True, exist_ok=True)
    for entry, data, digest in downloaded:
        (vendor_dir / entry["file"]).write_bytes(data)
        entry["sha256"] = digest
    lock_path.write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    fetch_all(VIEWER_DIR / "vendor", VIEWER_DIR / "vendor.lock.json")
    print("vendored libraries written to", VIEWER_DIR / "vendor")
