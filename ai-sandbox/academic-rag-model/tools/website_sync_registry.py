"""Local, read-only validation for the website-sync registry (M1 Task 1).

The audit CLI will consume this module in later tasks. Missing targets are
reported separately from invalid registry data: planned website pages may be
absent while the registry remains well formed.
"""

from __future__ import annotations

import json
import re
from pathlib import Path, PurePosixPath
from typing import Any

from jsonschema import Draft202012Validator


SCHEMA_NAME = "subproject_registry.schema.json"
_DRIVE = re.compile(r"^[A-Za-z]:")
_PATHSPEC = re.compile(r"[\[\]*?]|^:|/:")


class RegistryError(ValueError):
    """The registry or its adjacent schema violates the local contract."""


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise RegistryError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=_unique_pairs)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RegistryError(f"cannot read JSON {path}: {exc}") from exc


def _reject_nonlocal_references(node: Any) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            if key in {"$ref", "$dynamicRef"} and (
                not isinstance(value, str) or not value.startswith("#/")
            ):
                raise RegistryError(f"schema reference must be local: {value!r}")
            _reject_nonlocal_references(value)
    elif isinstance(node, list):
        for value in node:
            _reject_nonlocal_references(value)


def _check_path(path: str, root: Path, label: str, prefix: str | None = None) -> None:
    if (
        not path
        or path.startswith(("/", "\\"))
        or "\\" in path
        or _DRIVE.match(path)
        or _PATHSPEC.search(path)
        or any(part in {"", ".", ".."} for part in path.split("/"))
    ):
        raise RegistryError(f"invalid {label} path: {path!r}")
    if prefix and not path.startswith(prefix):
        raise RegistryError(f"{label} path must start with {prefix!r}: {path!r}")
    candidate = root.joinpath(*PurePosixPath(path).parts).resolve(strict=False)
    if not candidate.is_relative_to(root.resolve()):
        raise RegistryError(f"{label} path escapes repository: {path!r}")


def _no_case_collisions(paths: list[str], label: str) -> None:
    seen: dict[str, str] = {}
    for path in paths:
        key = path.casefold()
        if key in seen:
            raise RegistryError(f"duplicate/case-colliding {label}: {seen[key]!r}, {path!r}")
        seen[key] = path


def validate_registry(
    registry: dict[str, Any], schema: dict[str, Any], monorepo_root: Path,
    website_root: Path | None = None,
) -> None:
    """Validate schema plus cross-entry identity, references and safe paths."""
    if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema" or schema.get("$id") != SCHEMA_NAME:
        raise RegistryError("schema must declare the local Draft 2020-12 contract")
    _reject_nonlocal_references(schema)
    Draft202012Validator.check_schema(schema)
    errors = list(Draft202012Validator(schema).iter_errors(registry))
    if errors:
        error = min(errors, key=lambda item: (len(item.absolute_path), str(item.absolute_path), item.message))
        where = "/".join(map(str, error.absolute_path)) or "<root>"
        raise RegistryError(f"schema error at {where}: {error.message}")

    root = monorepo_root.resolve()
    site = website_root.resolve() if website_root else root
    projects = registry["subprojects"]
    pages: dict[str, str] = {}
    global_paths: dict[str, str] = {}
    shared_status_roles: dict[str, str] = {}
    owned_code: set[str] = set()

    def check(path: str, label: str, *, website: bool = False, prefix: str | None = None) -> None:
        _check_path(path, site if website else root, label, prefix)
        key = path.casefold()
        if key in global_paths and global_paths[key] != path:
            raise RegistryError(f"Windows case collision: {global_paths[key]!r}, {path!r}")
        global_paths[key] = path

    for component_id, entry in projects.items():
        kind = entry["kind"]
        status_paths = [row["path"] for row in entry["status_docs"]]
        _no_case_collisions(status_paths, f"{component_id} status docs")
        _no_case_collisions(entry["code_paths"], f"{component_id} code paths")
        for path in entry["code_paths"]:
            check(path, f"{component_id} code")
            owned_code.add(path.casefold())
        if entry["readme_path"]:
            check(entry["readme_path"], f"{component_id} README", prefix="ai-sandbox/academic-rag-model/")
        for row in entry["status_docs"]:
            check(row["path"], f"{component_id} status", prefix="ai-sandbox/academic-rag-model/docs/status/")
            status_key = row["path"].casefold()
            prior_role = shared_status_roles.get(status_key)
            if prior_role is not None and prior_role != row["role"]:
                raise RegistryError(f"conflicting role for shared status: {row['path']}")
            shared_status_roles[status_key] = row["role"]
        website = entry["website"]
        if website["page"]:
            page = website["page"]
            check(page, f"{component_id} page", website=True, prefix="content/projects/")
            if not page.endswith("/index.md"):
                raise RegistryError(f"page must be an index.md: {page}")
            key = page.casefold()
            if key in pages:
                raise RegistryError(f"page claimed by both {pages[key]} and {component_id}: {page}")
            pages[key] = component_id
        if kind == "overview":
            for member in entry["members"]:
                if member not in projects or member == component_id:
                    raise RegistryError(f"invalid {component_id} member: {member}")
                target = projects[member]
                if (target["kind"] == "overview" or target["lifecycle"] != "active"
                        or target["website"]["policy"] != "required"):
                    raise RegistryError(f"nonpublic {component_id} member: {member}")
        records = entry["lifecycle_records"]
        for row in entry["status_docs"]:
            for revision_id in row["lifecycle_ids"]:
                if revision_id not in records:
                    raise RegistryError(f"dangling {component_id} status lifecycle ID: {revision_id}")
        for revision_id, revision in records.items():
            for previous in revision["supersedes"]:
                if previous not in records or previous == revision_id:
                    raise RegistryError(f"invalid {component_id} supersedes ID: {previous}")
            for field in ("specs", "implementation_plans", "test_paths"):
                _no_case_collisions(revision[field], f"{component_id}/{revision_id}/{field}")
                for path in revision[field]:
                    check(path, f"{component_id} {field}", prefix="ai-sandbox/academic-rag-model/")
                    if field != "test_paths" and not path.endswith(".md"):
                        raise RegistryError(f"{field} must point to Markdown: {path}")

        visited: set[str] = set()
        visiting: set[str] = set()

        def visit(revision_id: str) -> None:
            if revision_id in visiting:
                raise RegistryError(f"supersession cycle in {component_id}: {revision_id}")
            if revision_id in visited:
                return
            visiting.add(revision_id)
            for previous in records[revision_id]["supersedes"]:
                visit(previous)
            visiting.remove(revision_id)
            visited.add(revision_id)

        for revision_id in records:
            visit(revision_id)

    exclusions = [row["path"] for row in registry["discovery_exclusions"]]
    _no_case_collisions(exclusions, "discovery exclusions")
    for path in exclusions:
        check(path, "discovery exclusion")
        if any(code == path.casefold() or code.startswith(path.casefold() + "/") for code in owned_code):
            raise RegistryError(f"discovery exclusion conflicts with registered code: {path}")


def load_registry(path: Path, monorepo_root: Path, website_root: Path | None = None) -> dict[str, Any]:
    """Read only the named registry and its adjacent, fixed-name schema."""
    if path.name != "subproject_registry.json":
        raise RegistryError("registry filename must be subproject_registry.json")
    if not path.resolve().is_relative_to(monorepo_root.resolve()):
        raise RegistryError("registry must be inside the selected monorepo")
    registry = _read_json(path)
    schema = _read_json(path.with_name(SCHEMA_NAME))
    validate_registry(registry, schema, monorepo_root, website_root)
    return registry


def missing_monorepo_targets(registry: dict[str, Any], monorepo_root: Path) -> list[str]:
    """Inventory absent configured source/doc/test paths; website pages are M3 work."""
    missing: set[str] = set()
    for entry in registry["subprojects"].values():
        targets = [(path, None) for path in entry["code_paths"]]
        if entry["readme_path"]:
            targets.append((entry["readme_path"], "file"))
        targets.extend((row["path"], "file") for row in entry["status_docs"])
        for revision in entry["lifecycle_records"].values():
            for field in ("specs", "implementation_plans", "test_paths"):
                kind = None if field == "test_paths" else "file"
                targets.extend((path, kind) for path in revision[field])
        for path, kind in targets:
            target = monorepo_root.joinpath(*PurePosixPath(path).parts)
            if not target.exists() or (kind == "file" and not target.is_file()):
                missing.add(path)
    return sorted(missing)
