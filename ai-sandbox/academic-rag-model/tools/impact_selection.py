"""Which test files can a change affect? Rules 2 and 3 of the landing test selection
(docs/superpowers/specs/2026-11-11-landing-test-selection-proposal.md).

A changed Python file affects the tests that import it, directly or through other
modules (reverse import closure), plus the tests in its mirror directory under
tests/ (catches tests that only run the code in a subprocess). A changed data file
affects the Python files that name it (its path, its file name, or its folder), and
then the same closure. Static analysis only: an import built at run time is invisible,
so the scheduled full run of `main` remains the backstop.

`select_tests` never guesses: whenever it cannot bound the impact it returns a
`run_all_reason` and the caller runs the full suite.
"""
from __future__ import annotations

import ast
import os
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

SKIP_DIRS = {".venv", "__pycache__", "archive", "node_modules"}
CONFIG_NAMES = {"pytest.ini", "pyproject.toml", "tox.ini", "setup.cfg", "setup.py"}
# Folder names that say nothing about which file a test reads.
GENERIC_DIRS = {"docs", "data", "tests", "tools", "core", "agent", "pipelines", "assets", "config"}


@dataclass(frozen=True)
class Selection:
    files: list[str] = field(default_factory=list)  # project-relative test files, sorted
    run_all_reason: str | None = None  # set when impact cannot be bounded


def _python_files(root: Path):
    for current, dirs, names in os.walk(root):
        rel_dir = Path(current).relative_to(root)
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")
                   and rel_dir.parts + (d,) != ("audio_generator", "models")]
        for name in names:
            if name.endswith(".py"):
                yield rel_dir / name


def _module_name(rel: Path) -> str:
    parts = list(rel.with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _is_test_file(rel: str) -> bool:
    parts = PurePosixPath(rel).parts
    return parts[0] == "tests" and parts[-1].startswith("test_") and parts[-1].endswith(".py")


class ImportGraph:
    def __init__(self, root: Path):
        self.rel_by_module: dict[str, str] = {}
        self.text: dict[str, str] = {}
        for rel in _python_files(root):
            module = _module_name(rel)
            self.rel_by_module[module] = rel.as_posix()
            self.text[module] = (root / rel).read_text(encoding="utf-8-sig", errors="replace")
        self.unparsed_tests: set[str] = set()
        self.importers: dict[str, set[str]] = {}
        for module, rel in self.rel_by_module.items():
            try:
                tree = ast.parse(self.text[module])
            except (SyntaxError, ValueError):
                if _is_test_file(rel):
                    self.unparsed_tests.add(module)
                continue
            for dependency in self._dependencies(rel, tree):
                if dependency != module:
                    self.importers.setdefault(dependency, set()).add(module)

    def _known_prefixes(self, parts: list[str]) -> set[str]:
        out = set()
        for i in range(1, len(parts) + 1):
            candidate = ".".join(parts[:i])
            if candidate in self.rel_by_module:
                out.add(candidate)
        return out

    def _resolve(self, dotted: str, level: int, package: list[str]) -> set[str]:
        if level:
            base = package[: len(package) - (level - 1)]
            parts = base + (dotted.split(".") if dotted else [])
            return self._known_prefixes(parts)
        parts = dotted.split(".")
        found = self._known_prefixes(parts)
        if not found:  # bare sibling import (pytest prepends the test's own folder)
            found = self._known_prefixes([*package, *parts])
        return found

    def _dependencies(self, rel: str, tree: ast.AST) -> set[str]:
        package = list(PurePosixPath(rel).parent.parts)
        out: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    out |= self._resolve(alias.name, 0, package)
            elif isinstance(node, ast.ImportFrom):
                base = node.module or ""
                out |= self._resolve(base, node.level, package)
                for alias in node.names:
                    out |= self._resolve(f"{base}.{alias.name}" if base else alias.name,
                                         node.level, package)
        return out

    def dependents(self, seeds: set[str]) -> set[str]:
        seen, stack = set(seeds), list(seeds)
        while stack:
            for importer in self.importers.get(stack.pop(), ()):
                if importer not in seen:
                    seen.add(importer)
                    stack.append(importer)
        return seen


def _needles(rel: str) -> set[str]:
    path = PurePosixPath(rel)
    needles = {rel, path.name}
    parent = path.parent.name
    if parent and parent not in GENERIC_DIRS and len(parent) >= 4:
        needles.add(parent)
    return needles


def _mirror_tests(rel: str, test_files: list[str]) -> set[str]:
    parts = PurePosixPath(rel).parts
    if len(parts) >= 3:  # pkg/sub/x.py -> everything under tests/pkg/sub/
        folder = "tests/" + "/".join(parts[:-1]) + "/"
        return {t for t in test_files if t.startswith(folder)}
    stem = PurePosixPath(rel).stem  # tools/x.py or x.py -> tests named test_x*
    folder = "tests/" + (parts[0] + "/" if len(parts) == 2 else "")
    return {t for t in test_files
            if t.startswith(folder) and "/" not in t[len(folder):]
            and PurePosixPath(t).name.startswith(f"test_{stem}")}


def _run_all_reason(path: str) -> str | None:
    pure = PurePosixPath(path)
    name = pure.name
    if name in CONFIG_NAMES or (name.endswith(".txt") and name.startswith(("requirements", "constraints"))):
        return "config_change"
    if name == "conftest.py" and len(pure.parts) <= 2:  # conftest.py or tests/conftest.py
        return "helper_change"
    if pure.parts[0] == "tests" and len(pure.parts) == 2 and not name.startswith("test_"):
        return "helper_change"  # top-level test helper
    return None


def select_tests(changed: set[str], project_root: Path) -> Selection:
    changed = {p for p in changed if not p.endswith(".md")}
    if not changed:
        return Selection()
    for path in sorted(changed):
        reason = _run_all_reason(path)
        if reason:
            return Selection([], reason)

    graph = ImportGraph(project_root)
    test_files = sorted(rel for rel in graph.rel_by_module.values() if _is_test_file(rel))
    module_by_rel = {rel: module for module, rel in graph.rel_by_module.items()}
    seeds: set[str] = set()
    selected: set[str] = {graph.rel_by_module[m] for m in graph.unparsed_tests}
    saw_code = False
    for path in sorted(changed):
        if path.endswith(".py"):
            saw_code = True
            if not (project_root / path).is_file():
                return Selection([], "moved_or_deleted_file")
            seeds.add(module_by_rel[path])
            pure = PurePosixPath(path)
            if pure.name == "conftest.py":  # fixtures for everything below its folder
                folder = pure.parent.as_posix() + "/"
                selected |= {t for t in test_files if t.startswith(folder)}
            elif not _is_test_file(path):
                selected |= _mirror_tests(path, test_files)
        else:
            needles = _needles(path)
            seeds |= {m for m, text in graph.text.items() if any(n in text for n in needles)}
    affected = graph.dependents(seeds)
    selected |= {graph.rel_by_module[m] for m in affected if _is_test_file(graph.rel_by_module[m])}
    if saw_code and not selected:
        return Selection([], "no_tests_for_code")
    return Selection(sorted(selected))
