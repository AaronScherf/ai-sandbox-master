from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import time
from pathlib import Path
from pathlib import PurePosixPath
from dataclasses import replace

from core.indexer.audit import MarkdownIndexTarget, audit_markdown_index
from core.indexer.index_card import compute_content_hash, compute_file_id, list_courses, load_shard
from tools.corpus_health.config import MarkdownPolicy, ScanConfig
from tools.corpus_health.finding import Finding
from tools.corpus_health.report import ScanReport
from tools.git_workflow import GitError, current_branch, dirty_files
from tools.active_work import build_report as active_work_report

_PRUNED_DIRS = {".git", ".index", ".obsidian", "__pycache__", "processed_outputs"}
_TEXTBOOK_DIRS = {"textbooks", "textbooks-and-papers"}
_FIELD_RE = re.compile(r"^([A-Za-z0-9_-]+)\s*:")
_POLICY_PRUNED_DIRS = {".git", ".index", ".obsidian", "__pycache__"}


def _walk_files(root: Path, on_error) -> list[Path]:
    found: list[Path] = []

    def handle_error(exc: OSError) -> None:
        on_error(str(exc))

    for directory, dirnames, filenames in os.walk(root, onerror=handle_error):
        dirnames[:] = sorted(name for name in dirnames
                             if name not in _PRUNED_DIRS and not name.startswith("."))
        for filename in sorted(filenames):
            if filename.startswith("."):
                continue
            found.append(Path(directory) / filename)
    return found


def _walk_policy_files(root: Path, on_error) -> list[Path]:
    found: list[Path] = []
    for directory, dirnames, filenames in os.walk(root, onerror=lambda exc: on_error(str(exc))):
        dirnames[:] = sorted(name for name in dirnames
                             if name not in _POLICY_PRUNED_DIRS and not name.startswith("."))
        found.extend(Path(directory) / filename for filename in sorted(filenames)
                     if not filename.startswith("."))
    return found


def _relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _fingerprint(path: Path, limit: int) -> tuple[str, bool]:
    stat = path.stat()
    if stat.st_size <= limit:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        return f"sha256:{digest}", True
    return f"stat:{stat.st_size}:{stat.st_mtime_ns}", False


def _safe_fingerprint(path: Path, limit: int, on_error) -> tuple[str | None, bool]:
    try:
        return _fingerprint(path, limit)
    except OSError as exc:
        on_error(f"cannot fingerprint {path}: {exc}")
        return None, False


def _nonempty_file(path: Path, on_error) -> bool:
    try:
        return path.is_file() and path.stat().st_size > 0
    except OSError as exc:
        on_error(f"cannot inspect expected output {path}: {exc}")
        return False


def _is_textbook(path: Path, resources_root: Path) -> bool:
    try:
        relative = path.relative_to(resources_root)
    except ValueError:
        return False
    return any(part.casefold() in _TEXTBOOK_DIRS for part in relative.parts[:-1])


def _has_valid_subset_marker(path: Path, resources_root: Path, on_error=None) -> bool:
    try:
        relative = path.relative_to(resources_root)
    except ValueError:
        return False
    if not relative.parts:
        return False
    if any(part.casefold() in _TEXTBOOK_DIRS for part in relative.parts[:-1]):
        return False
    course_root = resources_root / relative.parts[0]
    current = path.parent
    while current == course_root or course_root in current.parents:
        marker = current / ".notes_subset.json"
        try:
            if marker.is_file():
                payload = json.loads(marker.read_text(encoding="utf-8-sig"))
                return isinstance(payload, dict)
        except (OSError, json.JSONDecodeError) as exc:
            if on_error:
                on_error(f"cannot read subset marker {marker}: {exc}")
            return False
        if current == course_root:
            break
        current = current.parent
    return False


def _eligible_resource_note_pdf(path: Path, resources_root: Path, notes_root: Path, on_error=None) -> bool:
    if _is_textbook(path, resources_root):
        return False
    relative = path.relative_to(resources_root)
    if len(relative.parts) < 3:
        return False
    course, category = relative.parts[0], relative.parts[1]
    notes_course = notes_root / course
    return (notes_course / category).is_dir() or _has_valid_subset_marker(path, resources_root, on_error)


def _expected_note_output(source: Path, resources_root: Path, notes_root: Path) -> Path:
    try:
        relative = source.relative_to(resources_root)
    except ValueError:
        relative = source.relative_to(notes_root)
    return notes_root / relative.parent / "processed_outputs" / f"{source.stem}.md"


def _converted_textbook_outputs(resources_root: Path, hub_root: Path, on_error) -> dict[str, list[Path]]:
    """Resolve converted Markdown by the source PDF's content ID, not its name."""
    by_source_id: dict[str, list[Path]] = {}
    for metadata in resources_root.glob("*/**/processed_outputs/*/*_metadata.json"):
        if not _is_textbook(metadata, resources_root):
            continue
        try:
            data = json.loads(metadata.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            on_error(f"cannot read textbook metadata {metadata}: {exc}")
            continue
        source_id = data.get("source_pdf_file_id") if isinstance(data, dict) else None
        if isinstance(source_id, str):
            book_dir = metadata.parent
            by_source_id.setdefault(source_id, []).append(book_dir / f"{book_dir.name}.md")

    try:
        for course in list_courses(str(hub_root)):
            for card in load_shard(str(hub_root), course):
                if not isinstance(card, dict):
                    continue
                source_id = card.get("file_id")
                index_path = card.get("path")
                if not isinstance(source_id, str) or not isinstance(index_path, str):
                    continue
                candidate = (hub_root / Path(index_path.replace("\\", "/"))).resolve()
                if (candidate.is_relative_to(resources_root)
                        and _is_textbook(candidate, resources_root)
                        and "processed_outputs" in candidate.parts
                        and candidate.suffix.casefold() == ".md"
                        and not candidate.name.casefold().endswith(".rag.md")):
                    by_source_id.setdefault(source_id, []).append(candidate)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        on_error(f"cannot read textbook index cards: {exc}")
    return by_source_id


def _frontmatter_status(path: Path, required_fields: tuple[str, ...]) -> tuple[bool, str]:
    try:
        with path.open("r", encoding="utf-8-sig") as stream:
            if stream.readline().strip() != "---":
                return False, "YAML frontmatter block is missing"
            fields: set[str] = set()
            for line in stream:
                if line.strip() == "---":
                    missing = [name for name in required_fields if name not in fields]
                    return (not missing, f"missing frontmatter fields: {', '.join(missing)}" if missing else "")
                match = _FIELD_RE.match(line)
                if match:
                    fields.add(match.group(1))
    except (OSError, UnicodeError) as exc:
        return False, f"cannot read frontmatter: {exc}"
    return False, "frontmatter closing delimiter is missing"


def _git_facts(root: Path, ignored_paths: tuple[str, ...] = (), *, require_exact_root: bool = False) -> dict:
    try:
        top = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=root,
                             capture_output=True, text=True, check=True).stdout.strip()
        repo = Path(top)
        if require_exact_root and os.path.normcase(str(repo.resolve())) != os.path.normcase(str(root.resolve())):
            return {"error": f"configured notes path is not its own Git checkout (Git root: {repo})"}
        try:
            branch = current_branch(repo)
        except GitError:
            # ``rev-parse --abbrev-ref HEAD`` fails for a brand-new repository
            # with no commit yet; symbolic-ref still reports its unborn branch.
            symbolic = subprocess.run(["git", "symbolic-ref", "--short", "HEAD"], cwd=repo,
                                      capture_output=True, text=True)
            branch = symbolic.stdout.strip() if symbolic.returncode == 0 else None
        dirty = dirty_files(repo)
        ignored = set(ignored_paths)
        suppressed = sorted(path for path in dirty if path.replace("\\", "/") in ignored)
        visible = sorted(dirty - set(suppressed))
        upstream_proc = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"],
            cwd=repo, capture_output=True, text=True,
        )
        divergence = None
        upstream_status = "unavailable"
        upstream_reason = "no local upstream is configured"
        upstream = upstream_proc.stdout.strip()
        if upstream_proc.returncode == 0 and upstream:
            upstream_status = "configured"
            upstream_reason = "upstream ref is unavailable locally"
            counts = subprocess.run(["git", "rev-list", "--left-right", "--count", f"HEAD...{upstream}"],
                                    cwd=repo, capture_output=True, text=True)
            if counts.returncode == 0:
                ahead, behind = (int(value) for value in counts.stdout.split())
                divergence = {"upstream": upstream, "ahead": ahead, "behind": behind}
                upstream_status = "available"
                upstream_reason = None
        return {"repository": str(repo), "branch": branch,
                "dirty_count": len(visible), "dirty_paths": visible,
                "suppressed_known_sync_paths": suppressed,
                "upstream_divergence": divergence, "upstream_status": upstream_status,
                "upstream_reason": upstream_reason,
                "worktree_report": active_work_report(repo)}
    except (OSError, subprocess.CalledProcessError, GitError) as exc:
        return {"error": str(exc)}


def scan(config: ScanConfig) -> ScanReport:
    started = time.monotonic()
    report = ScanReport()

    def scan_error(message: str) -> None:
        report.errors.append(message)
        report.complete = False

    hub_root = config.academic_hub_root
    notes_root = config.academic_notes_root
    resources_root = hub_root / "academic_resources"

    roots = {
        "hub": hub_root,
        "resources": resources_root,
        "notes": notes_root,
    }
    for name, root in roots.items():
        if root is None:
            report.roots[name] = {"availability": "unavailable", "reason": "not configured"}
            if name in config.required_roots:
                report.complete = False
                report.errors.append(f"required root not configured: {name}")
            continue
        exists = root.is_dir()
        report.roots[name] = {"availability": "available" if exists else "unavailable",
                              "path": str(root)}
        if not exists and name in config.required_roots:
            report.complete = False
            report.errors.append(f"required root unavailable: {name} ({root})")
        elif not exists and name == "resources":
            report.complete = False
            report.errors.append(f"hub resources directory unavailable: {root}")

    if hub_root.is_dir():
        report.roots["hub"]["git"] = _git_facts(hub_root)
        if "error" in report.roots["hub"]["git"]:
            scan_error(f"cannot inspect hub repository: {report.roots['hub']['git']['error']}")
    if notes_root and notes_root.is_dir():
        report.roots["notes"]["git"] = _git_facts(notes_root, config.ignored_notes_git_paths,
                                                   require_exact_root=True)
        if "error" in report.roots["notes"]["git"]:
            scan_error(f"cannot inspect notes repository: {report.roots['notes']['git']['error']}")

    if not resources_root.is_dir():
        report.duration_seconds = time.monotonic() - started
        return report

    note_files: list[Path] = []
    resource_files = _walk_files(resources_root, scan_error)
    if notes_root and notes_root.is_dir():
        note_files = _walk_files(notes_root, scan_error)

    courses = set(config.courses)
    all_files = resource_files + note_files
    report.files_considered = len(all_files)
    textbook_outputs = _converted_textbook_outputs(resources_root, hub_root, scan_error)
    for source in sorted(all_files):
        if source.suffix.casefold() == ".pdf":
            if _is_textbook(source, resources_root):
                if courses and source.relative_to(resources_root).parts[0] not in courses:
                    continue
                try:
                    source_id = compute_file_id(str(source))
                    report.files_hashed += 1
                except OSError as exc:
                    scan_error(f"cannot hash textbook PDF {source}: {exc}")
                    continue
                candidates = textbook_outputs.get(source_id, [])
                if not any(_nonempty_file(path, scan_error) for path in candidates):
                    fingerprint, hashed = _safe_fingerprint(source, config.max_hash_bytes, scan_error)
                    report.files_hashed += int(hashed)
                    report.findings.append(Finding(
                        "textbook_conversion_missing", "academic_resources", str(source), source.stem,
                        ("linked converted textbook Markdown is missing or empty" if candidates
                         else "no converted textbook Markdown is linked to this PDF's content ID"),
                        str(candidates[0]) if candidates else None,
                        "textbook conversion (manual GCP/VM workflow; no adapter)", fingerprint,
                        cost_category="cloud_manual",
                    ))
                continue
            if not notes_root:
                continue
            if source.is_relative_to(resources_root) and not _eligible_resource_note_pdf(source, resources_root, notes_root, scan_error):
                fingerprint, hashed = _safe_fingerprint(source, config.max_hash_bytes, scan_error)
                report.files_hashed += int(hashed)
                report.findings.append(Finding(
                    "unknown_input", "academic_resources", str(source), source.name,
                    "PDF is outside a recognized notes category or marked subset",
                    suggested_action="classify this PDF or add an explicit notes-subset marker",
                    fingerprint=fingerprint, severity="informational", cost_category="unknown",
                ))
                continue
            course = source.relative_to(resources_root).parts[0] if source.is_relative_to(resources_root) else source.relative_to(notes_root).parts[0]
            if courses and course not in courses:
                continue
            output = _expected_note_output(source, resources_root, notes_root)
            if not _nonempty_file(output, scan_error):
                fingerprint, hashed = _safe_fingerprint(source, config.max_hash_bytes, scan_error)
                report.files_hashed += int(hashed)
                report.findings.append(Finding(
                    "note_transcription_missing", "academic_notes" if source.is_relative_to(notes_root) else "academic_resources",
                    str(source), source.stem, "eligible PDF has no non-empty processed Markdown",
                    str(output), "transcribe this PDF", fingerprint,
                    cost_category="cost_routed_api",
                ))
        elif source.name.casefold().endswith(".excalidraw.md"):
            if not notes_root:
                continue
            if source.is_relative_to(resources_root) and not _has_valid_subset_marker(source, resources_root, scan_error):
                fingerprint, hashed = _safe_fingerprint(source, config.max_hash_bytes, scan_error)
                report.files_hashed += int(hashed)
                report.findings.append(Finding(
                    "unknown_input", "academic_resources", str(source), source.name,
                    "Excalidraw scene is outside a marked prior-offering subset",
                    suggested_action="classify this scene or add a valid notes-subset marker",
                    fingerprint=fingerprint, severity="informational", cost_category="unknown",
                ))
                continue
            course = source.relative_to(notes_root).parts[0] if source.is_relative_to(notes_root) else source.relative_to(resources_root).parts[0]
            if courses and course not in courses:
                continue
            image_stem = Path(str(source)[:-len(".md")])
            image_candidates = [Path(str(image_stem) + ext) for ext in (".png", ".svg")]
            if source.is_relative_to(notes_root):
                rel = source.relative_to(notes_root)
                image_candidates.extend(resources_root / rel.parent / (image_stem.name + ext) for ext in (".png", ".svg"))
            image = next((candidate for candidate in image_candidates if candidate.is_file()), None)
            output = _expected_note_output(source, resources_root, notes_root)
            output = output.with_name(source.name[:-len(".md")] + ".rag.md")
            if image is None:
                fingerprint, hashed = _safe_fingerprint(source, config.max_hash_bytes, scan_error)
                report.files_hashed += int(hashed)
                report.findings.append(Finding("excalidraw_export_missing", "academic_notes", str(source),
                                               source.stem, "scene has no sibling .png/.svg export",
                                               None, "export the Excalidraw canvas", fingerprint,
                                               severity="informational", cost_category="local_manual"))
            elif not _nonempty_file(output, scan_error):
                fingerprint, hashed = _safe_fingerprint(source, config.max_hash_bytes, scan_error)
                report.files_hashed += int(hashed)
                report.findings.append(Finding("note_transcription_missing", "academic_notes", str(source),
                                               source.stem, "Excalidraw scene has no non-empty expanded output",
                                               str(output), "transcribe and expand this Excalidraw note", fingerprint,
                                               cost_category="paid_api"))

    index_targets: list[MarkdownIndexTarget] = []
    for policy in config.markdown_policies:
        root = hub_root if policy.root == "hub" else notes_root
        if root is None or not root.is_dir():
            continue
        try:
            matches = sorted(path for path in _walk_policy_files(root, scan_error)
                             if path.is_file() and PurePosixPath(path.relative_to(root).as_posix()).match(policy.glob))
        except OSError as exc:
            scan_error(f"cannot enumerate Markdown policy {policy.name}: {exc}")
            continue
        for path in matches:
            relative = path.relative_to(root).as_posix()
            if any(PurePosixPath(relative).match(pattern) for pattern in policy.exclude_globs):
                continue
            if courses:
                relative_parts = path.relative_to(root).parts
                course = relative_parts[0] if relative_parts else ""
                if course not in courses:
                    continue
            if policy.require_frontmatter:
                valid, evidence = _frontmatter_status(path, policy.required_fields)
                if not valid:
                    fingerprint, hashed = _safe_fingerprint(path, config.max_hash_bytes, scan_error)
                    report.files_hashed += int(hashed)
                    report.findings.append(Finding(
                        "markdown_frontmatter_missing", policy.name, str(path), path.name,
                        evidence, suggested_action="add required frontmatter", fingerprint=fingerprint,
                        cost_category="local_manual",
                    ))
            if policy.check_index:
                rel = relative
                index_path = (f"academic_notes/{rel}" if policy.root == "notes" else rel)
                index_targets.append(MarkdownIndexTarget(path, index_path))

    if index_targets:
        try:
            audit = audit_markdown_index(hub_root, index_targets, max_hash_bytes=config.max_hash_bytes)
            for target in index_targets:
                try:
                    report.files_hashed += int(target.file_path.stat().st_size <= config.max_hash_bytes)
                except OSError as exc:
                    scan_error(f"cannot inspect indexed Markdown {target.file_path}: {exc}")
            for error in audit.errors:
                scan_error(error)
            if not audit.complete:
                report.complete = False
            for record in audit.records:
                if record.card_status in {"missing_card", "stale_card", "needs_indexing", "course_mismatch"}:
                    report.findings.append(Finding(
                        "index_card_missing" if record.card_status == "missing_card" else "index_card_stale",
                        "academic-hub-index", record.index_path, Path(record.index_path).name,
                        record.evidence, suggested_action="index this Markdown file",
                        fingerprint=record.content_hash,
                        cost_category="paid_api",
                    ))
                if record.chunks_status in {"missing_chunks", "stale_chunks"} and record.card_status != "missing_card":
                    report.findings.append(Finding(
                        "index_chunks_missing_or_stale", "academic-hub-index", record.index_path,
                        Path(record.index_path).name, record.chunks_status,
                        suggested_action="rebuild passage chunks", fingerprint=record.content_hash,
                        cost_category="paid_api",
                    ))
                if record.card_status.startswith("unverified") or record.chunks_status.startswith("unverified"):
                    report.findings.append(Finding(
                        "index_state_unverified", "academic-hub-index", record.index_path,
                        Path(record.index_path).name, record.evidence, severity="informational",
                    ))
        except (OSError, ValueError, TypeError) as exc:
            scan_error(f"index audit failed: {exc}")

    # Converted book folders can outlive their original local PDF (for example,
    # a GCS-backed conversion), so audit their tablet output independently.
    if notes_root and resources_root.is_dir():
        for book_md in resources_root.glob("*/**/processed_outputs/*/*.md"):
            if not book_md.is_file() or book_md.name.endswith(".rag.md"):
                continue
            if not _is_textbook(book_md, resources_root):
                continue
            rel = book_md.relative_to(resources_root)
            course = rel.parts[0]
            if courses and course not in courses:
                continue
            book_dir = book_md.parent
            if book_md.stem != book_dir.name:
                continue
            rag_md = notes_root / rel.parent / f"{book_dir.name}.rag.md"
            if not rag_md.is_file() or rag_md.stat().st_size == 0:
                book_fingerprint, hashed = _safe_fingerprint(book_md, config.max_hash_bytes, scan_error)
                report.files_hashed += int(hashed)
                report.findings.append(Finding(
                    "textbook_rag_output_missing", "academic_notes", str(book_md), book_dir.name,
                    "converted textbook has no non-empty tablet .rag.md", str(rag_md),
                    "describe textbook images (manual review required)", book_fingerprint,
                    cost_category="paid_api",
                ))

    approved_categories = set(config.batch_approval_cost_categories)
    scoped_findings: list[Finding] = []
    for finding in report.findings:
        path = Path(finding.path)
        scope = ""
        for root_name, root in (("notes", notes_root), ("resources", resources_root), ("hub", hub_root)):
            if root is None:
                continue
            try:
                relative = path.relative_to(root)
            except ValueError:
                continue
            parts = relative.parts
            if parts:
                scope = "/".join((root_name, *parts[:2]))
                break
        if not scope:
            parts = finding.path.replace("\\", "/").split("/")
            if len(parts) > 2 and parts[0] in {"academic_notes", "academic_resources"}:
                scope = "/".join(parts[:3])
        scoped_findings.append(replace(
            finding,
            scope=scope or finding.root,
            batch_approval_allowed=(finding.severity == "actionable" and finding.cost_category in approved_categories),
        ))
    report.findings = scoped_findings
    report.duration_seconds = time.monotonic() - started
    return report
