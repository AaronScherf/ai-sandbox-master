from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MarkdownPolicy:
    name: str
    root: str
    glob: str
    require_frontmatter: bool = True
    required_fields: tuple[str, ...] = ()
    check_index: bool = True
    exclude_globs: tuple[str, ...] = ()


@dataclass(frozen=True)
class ScanConfig:
    academic_hub_root: Path
    academic_notes_root: Path | None
    courses: tuple[str, ...]
    markdown_policies: tuple[MarkdownPolicy, ...]
    required_roots: tuple[str, ...] = ("hub",)
    max_hash_bytes: int = 8 * 1024 * 1024
    batch_approval_cost_categories: tuple[str, ...] = ()
    ignored_notes_git_paths: tuple[str, ...] = (
        ".gitignore",
        ".obsidian/plugins/fit/main.js",
        ".obsidian/plugins/fit/styles.css",
    )


def _path_from_config(base: Path, value: str | None) -> Path | None:
    if value is None or value == "":
        return None
    path = Path(value).expanduser()
    return (base / path).resolve() if not path.is_absolute() else path.resolve()


def load_config(path: str | Path) -> ScanConfig:
    config_path = Path(path).expanduser().resolve()
    data = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("version") != 1:
        raise ValueError("config must be a JSON object with version: 1")
    if not isinstance(data.get("academic_hub_root"), str):
        raise ValueError("academic_hub_root must be a path string")
    if data.get("academic_notes_root") is not None and not isinstance(data.get("academic_notes_root"), str):
        raise ValueError("academic_notes_root must be a path string or null")
    if not isinstance(data.get("markdown_policies", []), list):
        raise ValueError("markdown_policies must be a list")
    if not isinstance(data.get("courses", []), list):
        raise ValueError("courses must be a list")
    if not isinstance(data.get("required_roots", ["hub"]), list):
        raise ValueError("required_roots must be a list")
    if not isinstance(data.get("batch_approval_cost_categories", []), list):
        raise ValueError("batch_approval_cost_categories must be a list")
    hub_root = _path_from_config(config_path.parent, data.get("academic_hub_root"))
    if hub_root is None:
        raise ValueError("academic_hub_root is required")
    notes_root = _path_from_config(config_path.parent, data.get("academic_notes_root"))
    policies: list[MarkdownPolicy] = []
    for item in data.get("markdown_policies", []):
        if not isinstance(item, dict) or not isinstance(item.get("root"), str) or item.get("root") not in {"hub", "notes"}:
            raise ValueError("each markdown policy needs root: 'hub' or 'notes'")
        if not isinstance(item.get("glob"), str):
            raise ValueError("each markdown policy needs a glob string")
        if not isinstance(item.get("exclude_globs", []), list):
            raise ValueError("markdown policy exclude_globs must be a list")
        if item["root"] == "notes" and notes_root is None:
            raise ValueError(f"policy {item.get('name', '<unnamed>')} requires academic_notes_root")
        policies.append(MarkdownPolicy(
            name=str(item.get("name") or item["glob"]),
            root=item["root"],
            glob=str(item["glob"]),
            require_frontmatter=bool(item.get("require_frontmatter", True)),
            required_fields=tuple(str(field) for field in item.get("required_fields", [])),
            check_index=bool(item.get("check_index", True)),
            exclude_globs=tuple(str(pattern) for pattern in item.get("exclude_globs", [])),
        ))
    max_hash_bytes = int(data.get("max_hash_bytes", 8 * 1024 * 1024))
    if max_hash_bytes < 0:
        raise ValueError("max_hash_bytes must be non-negative")
    if any(not isinstance(root, str) for root in data.get("required_roots", ["hub"])):
        raise ValueError("required_roots entries must be strings")
    required_roots = tuple(data.get("required_roots", ["hub"]))
    if any(root not in {"hub", "notes"} for root in required_roots):
        raise ValueError("required_roots entries must be 'hub' or 'notes'")
    return ScanConfig(
        academic_hub_root=hub_root,
        academic_notes_root=notes_root,
        courses=tuple(str(course) for course in data.get("courses", [])),
        markdown_policies=tuple(policies),
        required_roots=required_roots,
        max_hash_bytes=max_hash_bytes,
        batch_approval_cost_categories=tuple(str(value) for value in data.get("batch_approval_cost_categories", [])),
        ignored_notes_git_paths=tuple(str(value) for value in data.get("ignored_notes_git_paths", [
            ".gitignore", ".obsidian/plugins/fit/main.js", ".obsidian/plugins/fit/styles.css",
        ])),
    )
