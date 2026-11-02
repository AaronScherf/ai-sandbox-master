"""Prove and preview one-level part_1 index relocation; --apply is opt-in."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from core.env.corpus_write_lock import CorpusWriteLockError, corpus_write_lock
from core.env.frontmatter import parse_frontmatter

ALLOWED = frozenset({"source_pdf", "source_excalidraw", "source_image", "duplicate_of_path"})
PATH_FIELDS = ("path", "source_pdf_path", "source_asset_path", "rag_md_path", "duplicate_of_path")
INDEX_BASELINE = "f1cf14e0"


def moved(path: str | None, course: str) -> str | None:
    if not path:
        return path
    parts = path.replace("\\", "/").split("/")
    if len(parts) < 4 or parts[:2] not in (["academic_notes", course], ["academic_resources", course]):
        return path
    if re.fullmatch(r"part_\d+", parts[2]):
        return path
    return "/".join(parts[:2] + ["part_1"] + parts[2:])


def _hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:16]


def _full_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _baseline_blob(notes: Path, baseline: str, rel: str) -> bytes | None:
    if not rel.startswith("academic_notes/"):
        return None
    result = subprocess.run(["git", "-C", str(notes), "show", f"{baseline}:{rel[len('academic_notes/'):]}"] ,
                            capture_output=True, check=False)
    return result.stdout if result.returncode == 0 else None


def _absent_from_baseline(notes: Path, baseline: str, rel: str) -> bool:
    """Distinguish an absent tree entry from a failed git command."""
    if not rel.startswith("academic_notes/"):
        return False
    result = subprocess.run(["git", "-C", str(notes), "ls-tree", baseline, "--",
                             rel[len("academic_notes/"):]], capture_output=True, check=False)
    if result.returncode != 0:
        raise ValueError(f"git ls-tree failed for {rel}: {result.stderr.decode(errors='replace').strip()}")
    return not result.stdout


def _source_image_root_proof(old_value: str, new_value: str, old_fields: dict,
                             card: dict, root: Path, course: str, baseline: str) -> bool:
    prefix = f"academic_notes/{course}/"
    if not old_value.startswith(prefix):
        return False
    rel = old_value[len(prefix):]
    if not rel or rel.split("/", 1)[0].startswith("part_"):
        return False
    if not rel.endswith((".excalidraw.svg", ".excalidraw.png")):
        return False
    expected_new = f"academic_resources/{course}/part_1/{rel}"
    if new_value != expected_new or card.get("source_asset_path") != f"academic_resources/{course}/{rel}":
        return False
    scene = rel.rsplit(".", 1)[0] + ".md"
    if old_fields.get("source_excalidraw") != prefix + scene:
        return False
    target = root / expected_new
    if not target.is_file() or target.is_symlink():
        return False
    if (root / old_value).exists() or (root / f"academic_notes/{course}/part_1/{rel}").exists():
        return False
    return _absent_from_baseline(root / "academic_notes", baseline, old_value)


def _frontmatter_proof(old: bytes, current: bytes, expected_hash: str, course: str,
                       card: dict, root: Path, baseline: str) -> tuple[bool, bool]:
    normalized_old = old.replace(b"\r\n", b"\n")
    if expected_hash not in (_hash(normalized_old), _hash(normalized_old.replace(b"\n", b"\r\n"))):
        return False, False
    try:
        old_fields, old_body = parse_frontmatter(old.decode("utf-8").replace("\r\n", "\n"))
        new_fields, new_body = parse_frontmatter(current.decode("utf-8").replace("\r\n", "\n"))
    except UnicodeDecodeError:
        return False, False
    if old_body != new_body or set(old_fields) != set(new_fields):
        return False, False
    differing = {key for key in old_fields if old_fields[key] != new_fields[key]}
    if not differing or not differing <= ALLOWED:
        return False, False
    corrected = False
    for key in differing:
        if new_fields[key] == moved(old_fields[key], course):
            continue
        if key != "source_image" or not _source_image_root_proof(
                old_fields[key], new_fields[key], old_fields, card, root, course, baseline):
            return False, False
        corrected = True
    return True, corrected


def _json(path: Path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else default


def _uncarded_markdown(root: Path, course: str, baseline: str, cards: list[dict]) -> list[dict]:
    notes = root / "academic_notes"
    listing = subprocess.run(["git", "-C", str(notes), "ls-tree", "-r", "--name-only", baseline,
                              "--", course], capture_output=True, check=False)
    if listing.returncode != 0:
        raise ValueError(f"git ls-tree failed for uncarded Markdown: {listing.stderr.decode(errors='replace').strip()}")
    baseline_paths = set(listing.stdout.decode("utf-8", errors="replace").splitlines())
    card_paths = {moved(card.get("path"), course) for card in cards if card.get("path")}
    rows = []
    part = notes / course / "part_1"
    if not part.is_dir():
        return rows
    for path in sorted(part.rglob("*.md")):
        if not path.is_file() or path.is_symlink():
            continue
        new = path.relative_to(root).as_posix()
        if new in card_paths:
            continue
        old_rel = f"{course}/{path.relative_to(part).as_posix()}"
        old = f"academic_notes/{old_rel}"
        rows.append({"path": new, "old_path": old,
                     "action": "ambiguous" if (root / old).exists() else
                     "moved_uncarded" if old_rel in baseline_paths else "new_since_baseline"})
    return rows


def _changed_index_paths(root: Path, commit: str | None = None) -> set[str]:
    commit = commit or INDEX_BASELINE
    outer = subprocess.run(["git", "-C", str(root), "rev-parse", "--show-toplevel"],
                           capture_output=True, text=True, check=True).stdout.strip()
    base = root.relative_to(Path(outer).resolve()).as_posix()
    relative = (base + "/" if base != "." else "") + ".index"
    changed = subprocess.run(["git", "-C", outer, "diff", "--name-only", commit, "--", relative],
                             capture_output=True, text=True, check=False)
    untracked = subprocess.run(["git", "-C", outer, "ls-files", "--others", "--exclude-standard", "--", relative],
                               capture_output=True, text=True, check=False)
    if changed.returncode or untracked.returncode:
        raise ValueError("cannot compare .index/ with its pinned baseline")
    prefix = base + "/" if base != "." else ""
    return {line[len(prefix):] for line in (changed.stdout + untracked.stdout).splitlines()
            if line.startswith(prefix)}


def _index_baseline_unchanged(root: Path, commit: str | None = None) -> None:
    if _changed_index_paths(root, commit):
        raise ValueError(".index/ changed since f1cf14e0 or has uncommitted changes; relocation blocked")


def _backup_location(root: Path, course: str) -> Path:
    identity = _full_hash((str(root.resolve()).casefold() + ":" + course).encode())[:20]
    return Path(tempfile.gettempdir()) / f"index-relocation-backup-{identity}"


def _json_bytes(data: object, original: bytes | None = None) -> bytes:
    """Serialize with the existing file's indent, line endings and final newline."""
    if original is None:
        return json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
    match = re.search(rb"(?m)^([ \t]+)\S", original)
    indent = match.group(1).decode("ascii") if match else None
    line_ending = "\r\n" if b"\r\n" in original else "\n"
    final_newlines = re.search(rb"(?:\r?\n)+$", original)
    result = json.dumps(data, indent=indent, ensure_ascii=False)
    if line_ending != "\n":
        result = result.replace("\n", line_ending)
    return result.encode("utf-8") + (final_newlines.group() if final_newlines else b"")


def _write_bytes_atomic(path: Path, data: bytes) -> None:
    fd, temp = tempfile.mkstemp(prefix="relocate-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def _write_order(path: Path, course: str) -> tuple[int, str]:
    if path.parent.name == "chunks":
        priority = 0
    elif path.parent.name == ".index" and path.name == f"{course}.json":
        priority = 2
    else:
        priority = 1
    return priority, str(path)


def _validate_backup_manifest(root: Path, course: str, baseline: str, backup: Path,
                              check_changes: bool = True) -> dict:
    manifest = _json(backup / "manifest.json", None)
    if not isinstance(manifest, dict) or manifest.get("root") != str(root) or \
            manifest.get("course") != course or manifest.get("baseline") != baseline:
        raise ValueError("relocation backup manifest is missing or does not match this corpus")
    entries = manifest.get("files")
    if not isinstance(entries, dict):
        raise ValueError("relocation backup manifest has no file hashes")
    if check_changes and not _changed_index_paths(root) <= set(entries):
        raise ValueError("unrelated .index/ changes detected since relocation backup")
    states = []
    for relative, hashes in sorted(entries.items(), key=lambda item: _write_order(root / item[0], course)):
        path = root / relative
        if not path.is_file():
            raise ValueError(f"index file differs from both backed-up states: {relative}")
        current = _full_hash(path.read_bytes())
        if current not in (hashes.get("before"), hashes.get("after")):
            raise ValueError(f"index file differs from both backed-up states: {relative}")
        states.append(current == hashes.get("after"))
    if any(not earlier and later for earlier, later in zip(states, states[1:])):
        raise ValueError("relocation backup files are not in write order")
    return manifest


def _course_for_index_path(path: str) -> str | None:
    parts = path.split("/")
    if len(parts) == 2 and parts[0] == ".index" and parts[1].endswith(".json"):
        name = parts[1][:-5]
        return name if name not in ("courses", "tags") else None
    if len(parts) == 3 and parts[0] == ".index" and parts[1] in ("chunks", "materials"):
        name = parts[2]
        if name.endswith(".decisions.json"):
            return name[:-len(".decisions.json")]
        return name[:-5] if name.endswith(".json") else None
    return None


def _validate_index_state(root: Path, course: str, baseline: str) -> dict | None:
    changed = _changed_index_paths(root)
    journals: dict[str, dict] = {}
    for path in changed:
        owner = _course_for_index_path(path)
        if owner is None:
            raise ValueError(f"unrelated .index/ change detected: {path}")
        if owner not in journals:
            backup = _backup_location(root, owner)
            journals[owner] = _validate_backup_manifest(root, owner, baseline, backup, check_changes=False)
        if path not in journals[owner]["files"]:
            raise ValueError(f"index change is outside relocation backup: {path}")
    current_backup = _backup_location(root, course)
    if (current_backup / "manifest.json").is_file():
        return journals.get(course) or _validate_backup_manifest(
            root, course, baseline, current_backup, check_changes=False)
    if not changed:
        _index_baseline_unchanged(root)
    return None


def _catalog_plan(root: Path, course: str) -> tuple[list[dict], dict[Path, object]]:
    base = root / ".index" / "materials"
    catalog_path, decisions_path = base / f"{course}.json", base / f"{course}.decisions.json"
    catalog = _json(catalog_path, {})
    decisions = _json(decisions_path, {})
    rows: list[dict] = []
    updated: dict[Path, object] = {}

    def transform(path: str) -> str:
        new = moved(path, course)
        if new != path:
            target = root / new.rstrip("/")
            exists = target.is_dir() if path.endswith("/") else target.is_file()
            rows.append({"path": path, "new_path": new, "action": "remap" if exists else "missing_target",
                         "reason": "target_exists" if exists else "target_missing"})
        return new

    if catalog:
        copy = json.loads(json.dumps(catalog))
        for material in copy.get("materials", []):
            if material.get("path"):
                material["path"] = transform(material["path"])
        for key in ("excluded", "unknown_decisions"):
            if copy.get(key):
                copy[key] = [transform(path) for path in copy[key]]
        if copy != catalog:
            updated[catalog_path] = copy
    if decisions:
        copy = {transform(path): value for path, value in decisions.items()}
        if len(copy) != len(decisions):
            rows.append({"action": "collision", "path": str(decisions_path)})
        if copy != decisions:
            updated[decisions_path] = copy
    return rows, updated


def plan(root: str, course: str, baseline: str = "ca3b286") -> tuple[dict, dict[Path, object]]:
    hub = Path(root).resolve()
    notes = hub / "academic_notes"
    shard = hub / ".index" / f"{course}.json"
    chunks_path = hub / ".index" / "chunks" / f"{course}.json"
    cards = _json(shard, [])
    chunks = _json(chunks_path, [])
    new_cards = json.loads(json.dumps(cards))
    new_chunks = json.loads(json.dumps(chunks))
    rows: list[dict] = []
    for card in new_cards:
        old = card.get("path")
        new = moved(old, course)
        if not old or new == old:
            continue
        old_file, new_file = hub / old, hub / new
        row = {"path": old, "new_path": new, "file_id": card.get("file_id"),
               "action": "edited", "reason": "proof_failed_or_missing"}
        if old_file.exists() and new_file.exists():
            row.update(action="ambiguous", reason="old_and_new_exist")
        elif new_file.is_file():
            current = new_file.read_bytes()
            if _hash(current) == card.get("content_hash"):
                row.update(action="path_only", reason="hash_match")
            else:
                old_blob = _baseline_blob(notes, baseline, old)
                if old_blob is not None:
                    proven, corrected = _frontmatter_proof(
                        old_blob, current, card.get("content_hash"), course, card, hub, baseline)
                    if proven:
                        row.update(action="moved_frontmatter", reason="proved_frontmatter")
                        if corrected:
                            row["proof"] = "source_image_root_corrected"
        rows.append(row)
        if row["action"] in ("path_only", "moved_frontmatter"):
            old_hash = card.get("content_hash")
            card["content_hash"] = _hash(new_file.read_bytes())
            for field in PATH_FIELDS:
                if card.get(field):
                    card[field] = moved(card[field], course)
            for chunk in new_chunks:
                if chunk.get("file_id") == card.get("file_id") and chunk.get("content_hash") == old_hash:
                    chunk["content_hash"] = card["content_hash"]
    catalog_rows, catalog_updates = _catalog_plan(hub, course)
    updated: dict[Path, object] = dict(catalog_updates)
    if new_cards != cards:
        updated[shard] = new_cards
    if new_chunks != chunks:
        updated[chunks_path] = new_chunks
    uncarded = _uncarded_markdown(hub, course, baseline, cards)
    report = {"course": course, "baseline": baseline, "cards": rows, "catalog": catalog_rows,
              "uncarded_markdown": uncarded,
              "counts": {action: sum(r["action"] == action for r in rows)
                         for action in ("path_only", "moved_frontmatter", "edited", "ambiguous")}}
    return report, updated


def apply(root: str, course: str, baseline: str = "ca3b286") -> dict:
    with corpus_write_lock([root], "index path relocation"):
        hub = Path(root).resolve()
        backup = _backup_location(hub, course)
        manifest = _validate_index_state(hub, course, baseline)
        report, updated = plan(root, course, baseline)
        blockers = [r for r in report["cards"] if r["action"] in ("edited", "ambiguous")]
        blockers += [r for r in report["catalog"] if r["action"] in ("missing_target", "collision")]
        if blockers:
            report["status"] = "blocked"
            return report
        if not updated:
            report["status"] = "unchanged"
            return report
        originals = {path: path.read_bytes() for path in updated}
        encoded = {path: _json_bytes(data, originals[path]) for path, data in updated.items()}
        if manifest is None:
            backup.mkdir(parents=True, exist_ok=True)
            entries = {}
            for path, data in updated.items():
                relative = path.relative_to(hub)
                target = backup / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, target)
                entries[relative.as_posix()] = {"before": _full_hash(originals[path]),
                                               "after": _full_hash(encoded[path])}
            manifest = {"root": str(hub), "course": course, "baseline": baseline, "files": entries}
            _write_bytes_atomic(backup / "manifest.json", _json_bytes(manifest))
        else:
            for path in updated:
                entry = manifest["files"].get(path.relative_to(hub).as_posix())
                if entry is None or entry["after"] != _full_hash(encoded[path]):
                    raise ValueError(f"rerun target differs from relocation backup: {path}")
        # A rerun treats the moved card path as the completion marker. Write
        # matching chunk hashes first so interruption cannot expose a moved
        # card with stale chunks.
        ordered = sorted(updated.items(), key=lambda item: _write_order(item[0], course))
        for path, _ in ordered:
            _write_bytes_atomic(path, encoded[path])
        audit, _ = plan(root, course, baseline)
        verified = (all(_json(path, None) == data for path, data in updated.items())
                    and not audit["cards"] and not audit["catalog"])
        report.update(status="applied" if verified else "audit_failed", backup=str(backup),
                      post_run_audit=verified)
        return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    parser.add_argument("--course", required=True)
    parser.add_argument("--baseline", default="ca3b286")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--writer-coordinated", action="store_true")
    args = parser.parse_args()
    if args.apply and not args.writer_coordinated:
        parser.error("--apply requires --writer-coordinated")
    try:
        report = apply(args.root, args.course, args.baseline) if args.apply else plan(args.root, args.course, args.baseline)[0]
    except (OSError, ValueError, CorpusWriteLockError) as exc:
        print(json.dumps({"course": args.course, "status": "blocked", "reason": str(exc)}, sort_keys=True))
        raise SystemExit(1) from exc
    print(json.dumps(report, sort_keys=True))
    if args.apply and report.get("status") not in ("applied", "unchanged"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
