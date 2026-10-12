"""Deterministic website-sync findings over two local, pinned Git checkouts."""

from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
from pathlib import Path
import re
from typing import Any
from urllib.parse import unquote

import yaml

from tools.audit_website_sync import AuditError, GitRepository, InputChanged, _registry_paths


PACKAGE = "ai-sandbox/academic-rag-model"
GITHUB = "https://github.com/AaronScherf/ai-sandbox-master"
SEVERITY = {
    "UNREGISTERED_COMPONENT": "error", "MISSING_WEBSITE_PAGE": "error",
    "MISSING_SOURCE_PATH": "error", "MISSING_README": "error",
    "MISSING_STATUS_DOC": "error", "MISSING_SPEC": "error",
    "MISSING_IMPLEMENTATION_PLAN": "error", "MISSING_TEST_PATH": "error",
    "LIFECYCLE_BACKLINK_MISMATCH": "error", "METADATA_MISMATCH": "error",
    "ORPHANED_PAGE": "error", "LIFECYCLE_UNMAPPED": "warning",
    "LIFECYCLE_BACKFILL_PENDING": "warning", "LIFECYCLE_REVIEW_REQUIRED": "warning",
    "WEBSITE_HISTORY_GAP": "warning", "STATUS_HISTORY_GAP": "warning",
    "DIRTY_INPUT": "error", "HISTORY_UNAVAILABLE": "error",
    "INPUT_CHANGED": "error", "SCAN_ERROR": "error",
    "INTERNAL_COMPONENT": "info", "ARCHIVED_COMPONENT": "info",
    "FRESHNESS_NOT_APPLICABLE": "info",
}
INCOMPLETE_KINDS = {"DIRTY_INPUT", "HISTORY_UNAVAILABLE", "INPUT_CHANGED", "SCAN_ERROR"}
NONBLOCKING_ERRORS = INCOMPLETE_KINDS
SECTION = re.compile(r"^## Lifecycle references\s*$", re.I | re.M)
HEADING = re.compile(r"^### (Specs|Implementation plans|Tests)\s*$", re.I)
MARKDOWN_LINK = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")


class _UniqueLoader(yaml.SafeLoader):
    pass


def _unique_mapping(loader: _UniqueLoader, node: yaml.nodes.MappingNode) -> dict[Any, Any]:
    result: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=True)
        if not isinstance(key, (str, int, float, bool)):
            raise AuditError("unsupported YAML mapping key")
        if key in result:
            raise AuditError(f"duplicate YAML key: {key}")
        result[key] = loader.construct_object(value_node, deep=True)
    return result


_UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _unique_mapping)


def _frontmatter(path: Path) -> dict[str, Any]:
    try:
        data = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError) as exc:
        raise AuditError(f"cannot read website page {path}: {exc}") from exc
    lines = data.splitlines()
    if not lines or lines[0] != "---":
        return {}
    try:
        closing = next(i for i, line in enumerate(lines[1:], start=1) if line in {"---", "..."})
    except StopIteration as exc:
        raise AuditError(f"unclosed YAML frontmatter: {path}") from exc
    try:
        parsed = yaml.load("\n".join(lines[1:closing]), Loader=_UniqueLoader)
    except (yaml.YAMLError, AuditError) as exc:
        raise AuditError(f"invalid YAML frontmatter {path}: {exc}") from exc
    if parsed is None:
        return {}
    if not isinstance(parsed, dict):
        raise AuditError(f"frontmatter must be an object: {path}")
    return parsed


def _claimed_id(frontmatter: dict[str, Any]) -> str | None:
    params = frontmatter.get("params")
    canonical = params.get("subproject") if isinstance(params, dict) else None
    legacy = frontmatter.get("subproject")
    for block in (canonical, legacy):
        if isinstance(block, dict) and isinstance(block.get("id"), str):
            return block["id"]
    return None


def _page_candidates(root: Path, registered: set[str]) -> dict[str, dict[str, Any]]:
    pages: dict[str, dict[str, Any]] = {}
    base = root / "content/projects"
    if base.is_symlink() or not base.resolve().is_relative_to(root):
        raise AuditError(f"website projects directory escapes root: {base}")
    try:
        candidates = sorted(base.rglob("index.md"))
    except OSError as exc:
        raise AuditError(f"cannot enumerate website pages: {exc}") from exc
    for path in candidates:
        resolved = path.resolve()
        if not resolved.is_relative_to(root) or path.is_symlink():
            raise AuditError(f"website page escapes root: {path}")
        relative = path.relative_to(root).as_posix()
        # Unrelated portfolio pages need no YAML parse. A legacy or canonical
        # claim has an explicit subproject key in its frontmatter.
        if relative not in registered:
            try:
                initial = path.read_text(encoding="utf-8-sig")
            except (OSError, UnicodeError) as exc:
                raise AuditError(f"cannot read website page {path}: {exc}") from exc
            lines = initial.splitlines()
            if not lines or lines[0] != "---":
                continue
            closing = next((i for i, line in enumerate(lines[1:], start=1) if line in {"---", "..."}), len(lines))
            if not re.search(r"^\s*subproject\s*:", "\n".join(lines[1:closing]), re.M):
                continue
        pages[relative] = _frontmatter(path)
    return pages


def _projection(component_id: str, entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": component_id, "package": entry["package"],
        "code_paths": sorted(entry["code_paths"]), "readme_path": entry["readme_path"],
        "status_docs": sorted(
            ({"path": row["path"], "role": row["role"], "lifecycle_ids": sorted(row["lifecycle_ids"])}
             for row in entry["status_docs"]), key=lambda row: row["path"]),
        "members": sorted(entry["members"]),
    }


def _normalize_projection(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict) or set(raw) != {"id", "package", "code_paths", "readme_path", "status_docs", "members"}:
        return None
    if not isinstance(raw["code_paths"], list) or not isinstance(raw["status_docs"], list) or not isinstance(raw["members"], list):
        return None
    if any(not isinstance(row, dict) or set(row) != {"path", "role", "lifecycle_ids"}
           or not isinstance(row["lifecycle_ids"], list) for row in raw["status_docs"]):
        return None
    if (len(set(map(str, raw["code_paths"]))) != len(raw["code_paths"])
            or len(set(map(str, raw["members"]))) != len(raw["members"])):
        return None
    statuses = [row["path"] for row in raw["status_docs"]]
    if len(set(map(str, statuses))) != len(statuses):
        return None
    if any(len(set(map(str, row["lifecycle_ids"]))) != len(row["lifecycle_ids"]) for row in raw["status_docs"]):
        return None
    try:
        return {
            "id": raw["id"], "package": raw["package"],
            "code_paths": sorted(raw["code_paths"]), "readme_path": raw["readme_path"],
            "status_docs": sorted(
                ({"path": row["path"], "role": row["role"], "lifecycle_ids": sorted(row["lifecycle_ids"])}
                 for row in raw["status_docs"]), key=lambda row: row["path"]),
            "members": sorted(raw["members"]),
        }
    except TypeError:
        return None


def _expected_link(path: str, root: Path) -> str:
    kind = "tree" if (root / path).is_dir() else "blob"
    return f"{GITHUB}/{kind}/main/{path}"


def _has_link(urls: set[str], path: str, root: Path) -> bool:
    expected = _expected_link(path, root)
    return expected in urls or any(url.startswith("obsidian://") and path in unquote(url) for url in urls)


def _lifecycle_section(path: Path, root: Path, headings: set[str]) -> tuple[str, dict[str, set[str]], dict[str, str]]:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError) as exc:
        raise AuditError(f"cannot read lifecycle document {path}: {exc}") from exc
    matches = list(SECTION.finditer(text))
    if not matches:
        return "absent", {}, {}
    if len(matches) != 1:
        return "invalid", {}, {}
    tail = text[matches[0].end():]
    tail = re.split(r"^## (?!#)", tail, maxsplit=1, flags=re.M)[0]
    found: dict[str, set[str]] = defaultdict(set)
    prose: dict[str, str] = {}
    current: str | None = None
    invalid = False
    for line in tail.splitlines():
        if line.startswith("### "):
            match = HEADING.fullmatch(line.strip())
            if not match or match.group(1).lower() not in headings:
                invalid = True
                current = None
            else:
                current = match.group(1).lower()
                if current in prose:
                    invalid = True
                prose[current] = ""
            continue
        if current:
            prose[current] += line + "\n"
            for raw in MARKDOWN_LINK.findall(line):
                if raw.startswith(("/", "\\", "#")) or re.match(r"^[A-Za-z][\w+.-]*:", raw) or "?" in raw or "#" in raw:
                    invalid = True
                    continue
                target = (path.parent / unquote(raw)).resolve(strict=False)
                if not target.is_relative_to(root) or not target.exists():
                    invalid = True
                    continue
                found[current].add(target.relative_to(root).as_posix())
    if set(prose) != headings:
        invalid = True
    return ("invalid" if invalid else "present"), found, prose


class Scan:
    def __init__(self, registry: dict[str, Any], monorepo: GitRepository, website: GitRepository,
                 registry_path: Path, tolerance: int):
        self.registry = registry
        self.monorepo = monorepo
        self.website = website
        self.registry_path = registry_path
        self.tolerance = tolerance
        self.findings: list[dict[str, Any]] = []
        self.components: dict[str, dict[str, Any]] = {}
        self._seen: set[tuple[str, str, str, str]] = set()
        self._before_m: dict[str, dict[str, Any]] = {}
        self._before_w: dict[str, dict[str, Any]] = {}

    def add(self, component_id: str, kind: str, target: str, detail: str = "",
            evidence: dict[str, Any] | None = None) -> None:
        key = (component_id, kind, target, detail)
        if key in self._seen:
            return
        self._seen.add(key)
        severity = SEVERITY[kind]
        fingerprints = {}
        for referenced in (target.split(" -> ") if " -> " in target else [target]):
            row = self._before_m.get(referenced) or self._before_w.get(referenced)
            if row:
                fingerprints[referenced] = {"content": row["content_fingerprint"],
                                             "status": row["status_fingerprint"]}
        finding = {
            "component_id": component_id, "kind": kind, "target": target,
            "severity": severity, "blocks_strict": severity == "error" and kind not in NONBLOCKING_ERRORS,
            "detail": detail, "evidence": evidence or {}, "input_fingerprints": fingerprints,
        }
        self.findings.append(finding)
        if component_id in self.components:
            self.components[component_id]["findings"].append(finding)

    def _check_input(self, component_id: str, path: str, kind: str, snapshot: dict[str, dict[str, Any]],
                     *, archived_source: bool = False) -> None:
        row = snapshot[path]
        if not row["exists"]:
            if archived_source:
                self.add(component_id, "ARCHIVED_COMPONENT", path, "Historical source is absent")
            else:
                self.add(component_id, kind, path, "Configured target is absent")
        elif row["dirty"]:
            self.add(component_id, "DIRTY_INPUT", path, "Relevant input has staged, unstaged or untracked changes")
        elif not row["tracked"] or row["timestamp"] is None:
            self.add(component_id, "HISTORY_UNAVAILABLE", path, "Present input lacks committed local history")

    def _backlink(self, path: str, owners: set[str], expected: dict[str, set[str]],
                  reasons: dict[str, set[str]], headings: set[str]) -> None:
        if not (self.monorepo.root / path).is_file():
            return
        state, found, prose = _lifecycle_section(self.monorepo.root / path, self.monorepo.root, headings)
        for owner in sorted(owners):
            self.components[owner]["backlinks"].append({
                "path": path, "state": state,
                "expected": {key: sorted(expected.get(key, set())) for key in sorted(headings)},
                "found": {key: sorted(found.get(key, set())) for key in sorted(headings)},
            })
            if state == "absent":
                self.add(owner, "LIFECYCLE_BACKFILL_PENDING", path, "Normalized Lifecycle references section is absent")
            elif state == "invalid" or any(found.get(heading, set()) != expected.get(heading, set())
                                           or (not expected.get(heading) and not all(reason in prose.get(heading, "") for reason in reasons.get(heading, set())))
                                           for heading in headings):
                self.add(owner, "LIFECYCLE_BACKLINK_MISMATCH", path, "Normalized lifecycle references differ from registry or contain invalid links",
                         {"expected": {key: sorted(value) for key, value in expected.items()},
                          "found": {key: sorted(value) for key, value in found.items()}})

    def _history_gap(self, component_id: str, kind: str, source: str, target: str,
                     before: dict[str, dict[str, Any]], after: dict[str, dict[str, Any]]) -> None:
        earlier, later = before[source], after[target]
        if (not earlier["exists"] or not later["exists"] or earlier["dirty"] or later["dirty"]
                or not earlier["tracked"] or not later["tracked"]):
            return
        if earlier["timestamp"] is None or later["timestamp"] is None:
            return
        gap = earlier["timestamp"] - later["timestamp"]
        if gap > self.tolerance:
            self.add(component_id, kind, f"{source} -> {target}",
                     f"Pinned-HEAD history gap of {gap} seconds exceeds {self.tolerance}",
                     {"source_timestamp": earlier["timestamp"], "target_timestamp": later["timestamp"],
                      "gap_seconds": gap})

    def run(self) -> dict[str, Any]:
        projects = self.registry["subprojects"]
        registered_pages = {entry["website"]["page"] for entry in projects.values() if entry["website"]["page"]}
        pages = _page_candidates(self.website.root, registered_pages)
        monorepo_paths, website_paths = _registry_paths(self.registry)
        monorepo_paths.update({self.registry_path.relative_to(self.monorepo.root).as_posix(),
                               self.registry_path.with_name("subproject_registry.schema.json").relative_to(self.monorepo.root).as_posix()})
        website_paths.update(pages)
        candidates = self._discover()
        monorepo_paths.update(candidates)
        before_m = self.monorepo.snapshot(monorepo_paths)
        before_w = self.website.snapshot(website_paths)
        self._before_m, self._before_w = before_m, before_w
        for path in (self.registry_path.relative_to(self.monorepo.root).as_posix(),
                     self.registry_path.with_name("subproject_registry.schema.json").relative_to(self.monorepo.root).as_posix()):
            self._check_input("<registry>", path, "SCAN_ERROR", before_m)
        for component_id in sorted(projects):
            entry = projects[component_id]
            self.components[component_id] = {"id": component_id, "kind": entry["kind"],
                                              "page": entry["website"]["page"], "findings": [],
                                              "lifecycle_records": entry["lifecycle_records"],
                                              "targets": {}, "backlinks": [], "metadata_state": "not_applicable",
                                              "freshness_state": "not_assessed"}
            self._component(component_id, entry, before_m, before_w, pages)
        self._discover_findings(candidates, projects, before_m)
        self._page_claims(pages, projects)
        self._backlinks(projects)
        if self._discover() != candidates or _page_candidates(self.website.root, registered_pages) != pages:
            raise InputChanged("discovered package or claiming website page changed during scan")
        self.monorepo.assert_unchanged(before_m)
        self.website.assert_unchanged(before_w)
        self.findings.sort(key=lambda row: (row["component_id"], row["kind"], row["target"], row["detail"]))
        for component in self.components.values():
            component["findings"].sort(key=lambda row: (row["kind"], row["target"], row["detail"]))
        counts = Counter(row["severity"] for row in self.findings)
        incomplete = any(row["kind"] in INCOMPLETE_KINDS for row in self.findings)
        return {
            "report_version": "1.0.0", "coverage_complete": not incomplete,
            "monorepo_root": str(self.monorepo.root), "website_root": str(self.website.root),
            "monorepo_head": self.monorepo.head, "website_head": self.website.head,
            "registry_fingerprint": hashlib.sha256(self.registry_path.read_bytes()).hexdigest(),
            "tolerance_seconds": self.tolerance,
            "dirty": {"monorepo": sorted(path for path, row in before_m.items() if row["dirty"]),
                      "website": sorted(path for path, row in before_w.items() if row["dirty"])},
            "components": [self.components[key] for key in sorted(self.components)],
            "findings": self.findings,
            "counts": {key: counts[key] for key in ("error", "warning", "info")},
        }

    def _discover(self) -> set[str]:
        root = self.monorepo.root / PACKAGE
        found: set[str] = set()
        for parent in ("core", "pipelines", "discovery", "agent", "tools"):
            base = root / parent
            if base.is_symlink() or not base.is_dir():
                continue
            for child in base.iterdir():
                if (child.is_dir() and not child.is_symlink() and not child.name.startswith(".")
                        and child.name not in {"__pycache__", ".venv", "tests", "archive"}
                        and (child / "__init__.py").is_file()):
                    found.add(child.relative_to(self.monorepo.root).as_posix())
        for app in ("audio_generator", "resume_manager"):
            candidate = root / app
            if candidate.is_dir() and not candidate.is_symlink():
                found.add(candidate.relative_to(self.monorepo.root).as_posix())
        return found

    def _discover_findings(self, candidates: set[str], projects: dict[str, Any], before: dict[str, dict[str, Any]]) -> None:
        owned = {path for entry in projects.values() for path in entry["code_paths"]}
        excluded = {row["path"] for row in self.registry["discovery_exclusions"]}
        for path in sorted(candidates):
            if path in owned or any(path == item or path.startswith(item + "/") for item in excluded):
                continue
            if before[path]["dirty"]:
                self.add("<discovery>", "DIRTY_INPUT", path, "Discovered package candidate has uncommitted changes")
            self.add("<discovery>", "UNREGISTERED_COMPONENT", path, "Package candidate lacks a registry entry or exclusion",
                     {"untracked": before[path]["untracked"]})

    def _component(self, component_id: str, entry: dict[str, Any], before_m: dict[str, dict[str, Any]],
                   before_w: dict[str, dict[str, Any]], pages: dict[str, dict[str, Any]]) -> None:
        result = self.components[component_id]
        archived = entry["lifecycle"] == "archived"
        for path in entry["code_paths"]:
            self._check_input(component_id, path, "MISSING_SOURCE_PATH", before_m, archived_source=archived)
            result["targets"][path] = before_m[path]
        if entry["readme_path"]:
            path = entry["readme_path"]
            self._check_input(component_id, path, "MISSING_README", before_m, archived_source=archived)
            result["targets"][path] = before_m[path]
        for status in entry["status_docs"]:
            path = status["path"]
            self._check_input(component_id, path, "MISSING_STATUS_DOC", before_m)
            result["targets"][path] = before_m[path]
            if not status["lifecycle_ids"]:
                self.add(component_id, "LIFECYCLE_UNMAPPED", path, "Status record has no lifecycle mapping")
            elif (status["role"] == "current" and all(entry["lifecycle_records"][revision]["state"] == "superseded"
                                                       for revision in status["lifecycle_ids"])):
                self.add(component_id, "LIFECYCLE_REVIEW_REQUIRED", path, "Current status references only superseded revisions")
        if not entry["lifecycle_records"]:
            self.add(component_id, "LIFECYCLE_UNMAPPED", component_id, "Component has no lifecycle records")
        for revision in entry["lifecycle_records"].values():
            for field, kind in (("specs", "MISSING_SPEC"), ("implementation_plans", "MISSING_IMPLEMENTATION_PLAN"),
                                ("test_paths", "MISSING_TEST_PATH")):
                for path in revision[field]:
                    self._check_input(component_id, path, kind, before_m)
                    result["targets"][path] = before_m[path]
        if entry["website"]["policy"] == "internal":
            self.add(component_id, "INTERNAL_COMPONENT", component_id, entry["website"]["reason"])
            return
        page = entry["website"]["page"]
        if archived:
            self.add(component_id, "ARCHIVED_COMPONENT", component_id, entry["archive_reason"])
        if not before_w[page]["exists"]:
            if not archived:
                self.add(component_id, "MISSING_WEBSITE_PAGE", page, "Required page is absent")
            result["metadata_state"] = "missing_page"
            return
        self._check_input(component_id, page, "MISSING_WEBSITE_PAGE", before_w)
        result["targets"][page] = before_w[page]
        metadata = pages.get(page, {})
        raw = metadata.get("params", {})
        block = raw.get("subproject") if isinstance(raw, dict) else None
        if "subproject" in metadata or _normalize_projection(block) != _projection(component_id, entry):
            self.add(component_id, "METADATA_MISMATCH", page, "params.subproject differs from canonical registry projection")
            result["metadata_state"] = "mismatch"
        else:
            result["metadata_state"] = "matched"
        links = metadata.get("links", [])
        urls = {row.get("url") for row in links if isinstance(row, dict) and isinstance(row.get("url"), str)} if isinstance(links, list) else set()
        sources = entry["code_paths"] or ([entry["readme_path"]] if entry["readme_path"] else
                                           [entry["status_docs"][0]["path"]] if entry["status_docs"] else [])
        required_links = set(sources) | {row["path"] for row in entry["status_docs"]}
        missing_links = sorted(path for path in required_links if before_m[path]["exists"] and not _has_link(urls, path, self.monorepo.root))
        if missing_links:
            self.add(component_id, "METADATA_MISMATCH", page, "Visible source/status links are missing or generic",
                     {"missing_links": missing_links})
            result["metadata_state"] = "mismatch"
        if entry["kind"] == "overview":
            self.add(component_id, "FRESHNESS_NOT_APPLICABLE", page, "Overview has no component freshness clock")
            result["freshness_state"] = "not_applicable"
            return
        if archived:
            result["freshness_state"] = "not_applicable"
            return
        code = [path for path in entry["code_paths"] if before_m[path]["exists"] and before_m[path]["timestamp"] is not None]
        if code:
            newest = max(code, key=lambda path: before_m[path]["timestamp"])
            self._history_gap(component_id, "WEBSITE_HISTORY_GAP", newest, page, before_m, before_w)
        else:
            newest = None
        for status in entry["status_docs"]:
            if status["role"] != "current":
                continue
            path = status["path"]
            self._history_gap(component_id, "WEBSITE_HISTORY_GAP", path, page, before_m, before_w)
            if newest:
                self._history_gap(component_id, "STATUS_HISTORY_GAP", newest, path, before_m, before_m)
        result["freshness_state"] = "heuristic_checked"

    def _page_claims(self, pages: dict[str, dict[str, Any]], projects: dict[str, Any]) -> None:
        owners: dict[str, list[str]] = defaultdict(list)
        for path, metadata in pages.items():
            claimed = _claimed_id(metadata)
            if path not in {entry["website"]["page"] for entry in projects.values()}:
                self._check_input(claimed or "<unknown>", path, "SCAN_ERROR", self._before_w)
            if not claimed:
                params = metadata.get("params")
                if "subproject" in metadata or (isinstance(params, dict) and "subproject" in params):
                    self.add("<unknown>", "ORPHANED_PAGE", path, "Subproject claim lacks a valid ID")
                continue
            owners[claimed].append(path)
            if claimed not in projects or projects[claimed]["website"]["page"] != path:
                self.add(claimed, "ORPHANED_PAGE", path, "Unknown ID or page conflicts with registry ownership")
        for claimed, paths in owners.items():
            if len(paths) > 1:
                for path in paths:
                    self.add(claimed, "ORPHANED_PAGE", path, "Duplicate claimed owner")

    def _backlinks(self, projects: dict[str, Any]) -> None:
        status_requirements: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
        plan_requirements: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
        status_reasons: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
        plan_reasons: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
        status_owners: dict[str, set[str]] = defaultdict(set)
        plan_owners: dict[str, set[str]] = defaultdict(set)
        for component_id, entry in projects.items():
            records = entry["lifecycle_records"]
            for status in entry["status_docs"]:
                path = status["path"]
                if not status["lifecycle_ids"]:
                    continue
                status_owners[path].add(component_id)
                for revision_id in status["lifecycle_ids"]:
                    revision = records[revision_id]
                    for heading, field in (("specs", "specs"), ("implementation plans", "implementation_plans"),
                                           ("tests", "test_paths")):
                        status_requirements[path][heading].update(revision[field])
                        if not revision[field]:
                            status_reasons[path][heading].add(revision["absence_reasons"][field])
            for revision in records.values():
                for plan in revision["implementation_plans"]:
                    plan_owners[plan].add(component_id)
                    for heading, field in (("specs", "specs"), ("tests", "test_paths")):
                        plan_requirements[plan][heading].update(revision[field])
                        if not revision[field]:
                            plan_reasons[plan][heading].add(revision["absence_reasons"][field])
        for path, owners in status_owners.items():
            self._backlink(path, owners, status_requirements[path], status_reasons[path],
                           {"specs", "implementation plans", "tests"})
        for path, owners in plan_owners.items():
            self._backlink(path, owners, plan_requirements[path], plan_reasons[path], {"specs", "tests"})
