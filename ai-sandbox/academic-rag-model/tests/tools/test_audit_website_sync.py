"""M1 Task 1 registry/schema fixtures; CLI behavior arrives in later tasks."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from tools.website_sync_registry import (
    RegistryError,
    load_registry,
    missing_monorepo_targets,
    validate_registry,
)


PACKAGE_ROOT = Path(__file__).resolve().parents[2]
MONOREPO_ROOT = PACKAGE_ROOT.parents[1]
REGISTRY_PATH = PACKAGE_ROOT / "docs/trackers/subproject_registry.json"
SCHEMA_PATH = REGISTRY_PATH.with_name("subproject_registry.schema.json")


@pytest.fixture
def source() -> tuple[dict, dict]:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8")), json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def check(data: dict, schema: dict, *, root: Path = MONOREPO_ROOT) -> None:
    validate_registry(data, schema, root)


def test_live_inventory_is_complete_and_paths_exist(source: tuple[dict, dict]) -> None:
    data, schema = source
    check(data, schema)
    assert len(data["subprojects"]) == 26
    assert data["subprojects"]["core_env"]["website"]["policy"] == "internal"
    assert data["subprojects"]["guided_solutions"]["code_paths"] == []
    assert len(data["subprojects"]["study_guide"]["status_docs"]) == 4
    assert len(data["subprojects"]["source_indexer"]["status_docs"]) == 3
    study_roles = {row["path"].split("/")[-1]: row["role"] for row in data["subprojects"]["study_guide"]["status_docs"]}
    assert study_roles["2026-10-05-quiz-study-guide-generation-status.md"] == "historical"
    assert study_roles["2026-10-07-study-guide-comparison-status.md"] == "current"
    rag_report = data["subprojects"]["rag"]["lifecycle_records"]["combined-report"]
    viz_report = data["subprojects"]["visualization"]["lifecycle_records"]["combined-report"]
    assert rag_report["specs"] == viz_report["specs"]
    assert rag_report["implementation_plans"] == viz_report["implementation_plans"]
    assert missing_monorepo_targets(data, MONOREPO_ROOT) == []


def test_missing_planned_page_does_not_invalidate_registry(source: tuple[dict, dict], tmp_path: Path) -> None:
    data, schema = source
    assert not (tmp_path / data["subprojects"]["concept_graph"]["website"]["page"]).exists()
    validate_registry(data, schema, MONOREPO_ROOT, tmp_path)


@pytest.mark.parametrize("field,suffix", [
    ("specs", "docs/superpowers/specs/nonexistent.md"),
    ("implementation_plans", "docs/superpowers/plans/nonexistent.md"),
    ("test_paths", "tests/nonexistent.py"),
])
def test_missing_configured_document_is_a_finding_not_a_schema_error(source: tuple[dict, dict], field: str, suffix: str) -> None:
    data, schema = copy.deepcopy(source)
    missing = "ai-sandbox/academic-rag-model/" + suffix
    data["subprojects"]["rag"]["lifecycle_records"]["rag-agent"][field].append(missing)
    check(data, schema)
    assert missing in missing_monorepo_targets(data, MONOREPO_ROOT)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda d: d.update(version="2.0.0"),
        lambda d: d.update(unknown_key=True),
        lambda d: d["subprojects"]["guided_solutions"].update(code_paths=["fake"]),
        lambda d: d["subprojects"]["core_env"].update(readme_absence_reason=None),
        lambda d: d["subprojects"]["source_indexer"]["website"].update(page=None),
        lambda d: d["subprojects"]["source_indexer"]["lifecycle_records"]["source-indexer-core"]["absence_reasons"].update(specs="reason despite nonempty specs"),
        lambda d: d["subprojects"]["rag"]["status_docs"][0].update(role="unknown"),
        lambda d: d["subprojects"]["rag"]["status_docs"][0].update(lifecycle_ids=["rag-agent", "rag-agent"]),
    ],
)
def test_strict_schema_rejects_contract_changes(source: tuple[dict, dict], mutate) -> None:
    data, schema = copy.deepcopy(source)
    mutate(data)
    with pytest.raises(RegistryError, match="schema error"):
        check(data, schema)


def test_duplicate_json_keys_rejected(tmp_path: Path, source: tuple[dict, dict]) -> None:
    _, schema = source
    (tmp_path / "subproject_registry.schema.json").write_text(json.dumps(schema), encoding="utf-8")
    (tmp_path / "subproject_registry.json").write_text('{"version":"1.0.0","version":"2.0.0"}', encoding="utf-8")
    with pytest.raises(RegistryError, match="duplicate JSON key"):
        load_registry(tmp_path / "subproject_registry.json", tmp_path)


def test_duplicate_lifecycle_record_keys_rejected(tmp_path: Path, source: tuple[dict, dict]) -> None:
    data, schema = source
    (tmp_path / "subproject_registry.schema.json").write_text(json.dumps(schema), encoding="utf-8")
    payload = json.dumps(data).replace('"rag-agent": {', '"rag-agent": {}, "rag-agent": {', 1)
    (tmp_path / "subproject_registry.json").write_text(payload, encoding="utf-8")
    with pytest.raises(RegistryError, match="duplicate JSON key: rag-agent"):
        load_registry(tmp_path / "subproject_registry.json", tmp_path)


@pytest.mark.parametrize("path", ["../outside", "C:/escape", "//server/share", "foo\\bar", "foo/./bar", "foo//bar", ":(glob)foo", "foo/*.md"])
def test_unsafe_paths_rejected(source: tuple[dict, dict], path: str) -> None:
    data, schema = copy.deepcopy(source)
    data["subprojects"]["source_indexer"]["code_paths"][0] = path
    with pytest.raises(RegistryError, match="path"):
        check(data, schema)


def test_status_lifecycle_ids_and_supersession_graph_are_checked(source: tuple[dict, dict]) -> None:
    original, schema = source
    data = copy.deepcopy(original)
    data["subprojects"]["rag"]["status_docs"][0]["lifecycle_ids"] = ["missing-revision"]
    with pytest.raises(RegistryError, match="dangling"):
        check(data, schema)

    data = copy.deepcopy(original)
    records = data["subprojects"]["summary_enhancement"]["lifecycle_records"]
    records["summary-enhancement-v1"]["supersedes"] = ["summary-enhancement-v2"]
    with pytest.raises(RegistryError, match="cycle"):
        check(data, schema)

    data = copy.deepcopy(original)
    data["subprojects"]["summary_enhancement"]["lifecycle_records"]["summary-enhancement-v2"]["supersedes"] = ["not-there"]
    with pytest.raises(RegistryError, match="invalid .* supersedes"):
        check(data, schema)


def test_page_owner_status_duplication_and_members_are_checked(source: tuple[dict, dict]) -> None:
    original, schema = source
    data = copy.deepcopy(original)
    data["subprojects"]["rag"]["website"]["page"] = data["subprojects"]["tutor_diagnosis"]["website"]["page"]
    with pytest.raises(RegistryError, match="page claimed"):
        check(data, schema)

    data = copy.deepcopy(original)
    data["subprojects"]["rag"]["status_docs"].append(copy.deepcopy(data["subprojects"]["rag"]["status_docs"][0]))
    data["subprojects"]["rag"]["status_docs"][-1]["role"] = "historical"
    with pytest.raises(RegistryError, match="duplicate/case-colliding"):
        check(data, schema)

    data = copy.deepcopy(original)
    data["subprojects"]["tutor_diagnosis"]["status_docs"][0]["path"] = data["subprojects"]["rag"]["status_docs"][0]["path"]
    data["subprojects"]["tutor_diagnosis"]["status_docs"][0]["role"] = "historical"
    with pytest.raises(RegistryError, match="conflicting role"):
        check(data, schema)

    data = copy.deepcopy(original)
    data["subprojects"]["academic_hub_overview"]["members"].append("core_env")
    with pytest.raises(RegistryError, match="nonpublic"):
        check(data, schema)


def test_windows_case_and_exclusion_conflicts(source: tuple[dict, dict]) -> None:
    original, schema = source
    data = copy.deepcopy(original)
    data["subprojects"]["rag"]["readme_path"] = "ai-sandbox/academic-rag-model/Agent/Rag/README.md"
    with pytest.raises(RegistryError, match="Windows case collision"):
        check(data, schema)

    data = copy.deepcopy(original)
    data["discovery_exclusions"].append({"path": data["subprojects"]["rag"]["code_paths"][0], "reason": "wrong"})
    with pytest.raises(RegistryError, match="conflicts with registered code"):
        check(data, schema)

    data = copy.deepcopy(original)
    data["discovery_exclusions"].append({"path": "ai-sandbox/academic-rag-model/agent", "reason": "wrong parent"})
    with pytest.raises(RegistryError, match="conflicts with registered code"):
        check(data, schema)


def test_schema_never_resolves_remote_refs(source: tuple[dict, dict]) -> None:
    data, schema = copy.deepcopy(source)
    schema["$defs"]["path"]["$ref"] = "https://example.invalid/schema.json"
    with pytest.raises(RegistryError, match="must be local"):
        check(data, schema)


def test_registry_cannot_be_loaded_from_outside_selected_root(tmp_path: Path, source: tuple[dict, dict]) -> None:
    data, schema = source
    (tmp_path / "subproject_registry.schema.json").write_text(json.dumps(schema), encoding="utf-8")
    (tmp_path / "subproject_registry.json").write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(RegistryError, match="inside the selected monorepo"):
        load_registry(tmp_path / "subproject_registry.json", MONOREPO_ROOT)


def test_symlink_escape_rejected(tmp_path: Path, source: tuple[dict, dict]) -> None:
    data, schema = copy.deepcopy(source)
    root = tmp_path / "repo"
    root.mkdir()
    link = root / "escape"
    try:
        link.symlink_to(tmp_path, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation unavailable")
    data["subprojects"]["rag"]["code_paths"] = ["escape/outside"]
    with pytest.raises(RegistryError, match="escapes repository"):
        check(data, schema, root=root)
