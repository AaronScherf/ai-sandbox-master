"""End-to-end local repository fixtures for website-sync findings."""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import subprocess

import pytest
import yaml

from tools import audit_website_sync as cli
from tools.website_sync_scan import GITHUB, Scan


PACKAGE = "ai-sandbox/academic-rag-model"
CODE = f"{PACKAGE}/agent/demo"
STATUS = f"{PACKAGE}/docs/status/demo.md"
SPEC = f"{PACKAGE}/docs/superpowers/specs/demo.md"
PLAN = f"{PACKAGE}/docs/superpowers/plans/demo.md"
TEST = f"{PACKAGE}/tests/demo.py"
PAGE = "content/projects/academic-hub/demo/index.md"
REGISTRY = f"{PACKAGE}/docs/trackers/subproject_registry.json"


def git(root: Path, *args: str, timestamp: int = 1_700_000_000) -> str:
    env = os.environ.copy()
    env.update(GIT_AUTHOR_DATE=f"@{timestamp}", GIT_COMMITTER_DATE=f"@{timestamp}")
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True,
                          text=True, check=True, env=env).stdout.strip()


def put(root: Path, path: str, content: str) -> None:
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def commit(root: Path, *, timestamp: int = 1_700_000_000) -> None:
    git(root, "add", "--all", timestamp=timestamp)
    git(root, "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
        "commit", "-qm", "fixture", timestamp=timestamp)


def entry() -> dict:
    return {
        "name": "Demo", "kind": "code", "category": "academic-hub", "lifecycle": "active",
        "package": "agent/demo", "code_paths": [CODE], "readme_path": None,
        "readme_absence_reason": "Fixture", "status_docs": [
            {"path": STATUS, "role": "current", "lifecycle_ids": ["v1"]}],
        "status_absence_reason": None,
        "lifecycle_records": {"v1": {"state": "current", "supersedes": [],
                                     "specs": [SPEC], "implementation_plans": [PLAN], "test_paths": [TEST],
                                     "absence_reasons": {"specs": None, "implementation_plans": None, "test_paths": None}}},
        "website": {"policy": "required", "page": PAGE, "reason": None},
        "members": [], "archive_reason": None,
    }


def page(entry_data: dict | None = None) -> str:
    item = entry_data or entry()
    block = {
        "id": "demo", "package": item["package"], "code_paths": item["code_paths"],
        "readme_path": item["readme_path"], "status_docs": item["status_docs"],
        "members": item["members"],
    }
    frontmatter = {
        "title": "Demo", "params": {"subproject": block},
        "links": [{"url": f"{GITHUB}/tree/main/{CODE}"},
                  {"url": f"{GITHUB}/blob/main/{STATUS}"}],
    }
    return "---\n" + yaml.safe_dump(frontmatter, sort_keys=False) + "---\nbody\n"


@pytest.fixture
def fixture(tmp_path: Path) -> tuple[Path, Path, dict]:
    monorepo = tmp_path / "outer repo"
    website = tmp_path / "website repo"
    monorepo.mkdir()
    website.mkdir()
    subprocess.run(["git", "init", "-q", str(monorepo)], check=True)
    subprocess.run(["git", "init", "-q", str(website)], check=True)
    put(monorepo, f"{PACKAGE}/tools/website_sync_registry.py", "# marker\n")
    put(monorepo, CODE + "/__init__.py", "")
    put(monorepo, STATUS, "# Status\n")
    put(monorepo, SPEC, "# Spec\n")
    put(monorepo, PLAN, "# Plan\n")
    put(monorepo, TEST, "# Test\n")
    put(monorepo, REGISTRY, "{}")
    put(monorepo, f"{PACKAGE}/docs/trackers/subproject_registry.schema.json", "{}")
    put(website, PAGE, page())
    commit(monorepo)
    commit(website)
    return monorepo, website, {"subprojects": {"demo": entry()}, "discovery_exclusions": []}


def scan(fixture_data: tuple[Path, Path, dict], tolerance: int = 3600) -> dict:
    monorepo, website, registry = fixture_data
    return Scan(registry, cli.GitRepository(monorepo, kind="monorepo"),
                cli.GitRepository(website, kind="website"), monorepo / REGISTRY,
                tolerance).run()


def kinds(report: dict) -> set[str]:
    return {row["kind"] for row in report["findings"]}


def test_complete_warning_only_scan_and_format_exit_policy(fixture: tuple[Path, Path, dict],
                                                           monkeypatch: pytest.MonkeyPatch,
                                                           capsys: pytest.CaptureFixture[str]) -> None:
    result = scan(fixture)
    assert result["coverage_complete"] is True, result["findings"]
    assert kinds(result) == {"LIFECYCLE_BACKFILL_PENDING"}
    assert result["counts"] == {"error": 0, "warning": 2, "info": 0}
    assert result["components"][0]["targets"][CODE]["tracked"]
    assert all(row["blocks_strict"] is False for row in result["findings"])

    monkeypatch.setattr(cli, "load_registry", lambda *_: fixture[2])
    for format_name in ("json", "text", "markdown"):
        code = cli.main(["--monorepo-root", str(fixture[0]), "--website-root", str(fixture[1]),
                         "--format", format_name, "--strict"])
        rendered = capsys.readouterr().out
        assert code == 0
        assert "LIFECYCLE_BACKFILL_PENDING" in rendered
        if format_name == "json":
            assert json.loads(rendered)["counts"] == result["counts"]


def test_missing_page_unknown_claim_and_strict_blocker(fixture: tuple[Path, Path, dict]) -> None:
    monorepo, website, registry = fixture
    (website / PAGE).unlink()
    put(website, "content/projects/other/index.md", "---\nparams:\n  subproject:\n    id: stranger\n---\n")
    commit(website)
    result = scan((monorepo, website, registry))
    assert result["coverage_complete"] is True
    assert {"MISSING_WEBSITE_PAGE", "ORPHANED_PAGE"} <= kinds(result)
    assert any(row["blocks_strict"] for row in result["findings"])
    assert result["findings"] == sorted(result["findings"],
                                        key=lambda row: (row["component_id"], row["kind"], row["target"], row["detail"]))


def test_missing_page_strict_cli_returns_one(fixture: tuple[Path, Path, dict],
                                             monkeypatch: pytest.MonkeyPatch,
                                             capsys: pytest.CaptureFixture[str]) -> None:
    monorepo, website, registry = fixture
    (website / PAGE).unlink()
    commit(website)
    monkeypatch.setattr(cli, "load_registry", lambda *_: registry)
    args = ["--monorepo-root", str(monorepo), "--website-root", str(website), "--format", "json"]
    assert cli.main(args) == 0
    capsys.readouterr()
    assert cli.main(args + ["--strict"]) == 1
    assert json.loads(capsys.readouterr().out)["coverage_complete"] is True


def test_duplicate_yaml_key_is_structured_incomplete_error(fixture: tuple[Path, Path, dict],
                                                            monkeypatch: pytest.MonkeyPatch,
                                                            capsys: pytest.CaptureFixture[str]) -> None:
    _, website, registry = fixture
    put(website, PAGE, "---\nparams:\n  subproject: {id: demo}\nparams: {}\n---\n")
    monkeypatch.setattr(cli, "load_registry", lambda *_: registry)
    code = cli.main(["--monorepo-root", str(fixture[0]), "--website-root", str(website),
                     "--format", "json", "--strict"])
    result = json.loads(capsys.readouterr().out)
    assert code == 2
    assert result["coverage_complete"] is False
    assert "duplicate YAML key" in result["error"]
    assert result["findings"][0]["kind"] == "SCAN_ERROR"


def test_observed_change_is_structured_input_changed(fixture: tuple[Path, Path, dict],
                                                      monkeypatch: pytest.MonkeyPatch,
                                                      capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(cli, "load_registry", lambda *_: fixture[2])
    def changed(*_: object) -> None:
        raise cli.InputChanged("fixture changed")
    monkeypatch.setattr(cli.GitRepository, "assert_unchanged", changed)
    code = cli.main(["--monorepo-root", str(fixture[0]), "--website-root", str(fixture[1]),
                     "--format", "json"])
    result = json.loads(capsys.readouterr().out)
    assert code == 2
    assert result["findings"][0]["kind"] == "INPUT_CHANGED"


def test_normalized_lifecycle_links_and_mismatch(fixture: tuple[Path, Path, dict]) -> None:
    monorepo, website, registry = fixture
    status = monorepo / STATUS
    plan = monorepo / PLAN
    rel = lambda source, target: os.path.relpath(monorepo / target, source.parent).replace("\\", "/")
    put(monorepo, STATUS,
        "## Lifecycle references\n### Specs\n- [Spec](" + rel(status, SPEC) + ")\n"
        "### Implementation plans\n- [Plan](" + rel(status, PLAN) + ")\n"
        "### Tests\n- [Test](" + rel(status, TEST) + ")\n")
    put(monorepo, PLAN,
        "## Lifecycle references\n### Specs\n- [Spec](" + rel(plan, SPEC) + ")\n"
        "### Tests\n- [Test](" + rel(plan, TEST) + ")\n")
    commit(monorepo)
    assert "LIFECYCLE_BACKFILL_PENDING" not in kinds(scan(fixture))
    assert "LIFECYCLE_BACKLINK_MISMATCH" not in kinds(scan(fixture))
    put(monorepo, STATUS, status.read_text(encoding="utf-8").replace(rel(status, SPEC), "../missing.md"))
    commit(monorepo)
    assert "LIFECYCLE_BACKLINK_MISMATCH" in kinds(scan(fixture))


@pytest.mark.parametrize("seconds,expected", [(3599, False), (3600, False), (3601, True)])
def test_history_gap_is_strictly_greater_than_tolerance(fixture: tuple[Path, Path, dict],
                                                        seconds: int, expected: bool) -> None:
    monorepo, website, registry = fixture
    put(monorepo, CODE + "/__init__.py", f"# changed {seconds}\n")
    commit(monorepo, timestamp=1_700_000_000 + seconds)
    report = scan((monorepo, website, registry))
    assert ("WEBSITE_HISTORY_GAP" in kinds(report)) is expected
    assert ("STATUS_HISTORY_GAP" in kinds(report)) is expected
    assert report["coverage_complete"] is True


def test_dirty_relevant_input_takes_exit_two_precedence(fixture: tuple[Path, Path, dict]) -> None:
    monorepo, website, registry = fixture
    put(monorepo, CODE + "/new.py", "# untracked\n")
    report = scan((monorepo, website, registry))
    assert report["coverage_complete"] is False
    assert "DIRTY_INPUT" in kinds(report)
    assert "WEBSITE_HISTORY_GAP" not in kinds(report)


def test_unregistered_candidate_requires_no_readme_and_exclusion_is_respected(fixture: tuple[Path, Path, dict]) -> None:
    monorepo, website, registry = fixture
    candidate = f"{PACKAGE}/agent/new_package"
    put(monorepo, candidate + "/__init__.py", "")
    commit(monorepo)
    report = scan((monorepo, website, registry))
    assert any(row["kind"] == "UNREGISTERED_COMPONENT" and row["target"] == candidate
               for row in report["findings"])
    registry["discovery_exclusions"].append({"path": candidate, "reason": "fixture"})
    assert "UNREGISTERED_COMPONENT" not in kinds(scan((monorepo, website, registry)))


def test_wrong_projection_links_and_duplicate_claims(fixture: tuple[Path, Path, dict]) -> None:
    monorepo, website, registry = fixture
    broken = page().replace("agent/demo", "agent/other").replace(f"{GITHUB}/blob/main/{STATUS}", GITHUB)
    put(website, PAGE, broken)
    duplicate = "content/projects/other/index.md"
    put(website, duplicate, "---\nparams:\n  subproject:\n    id: demo\n---\n")
    commit(website)
    report = scan((monorepo, website, registry))
    assert report["coverage_complete"] is True
    assert len([row for row in report["findings"] if row["kind"] == "METADATA_MISMATCH"]) == 2
    assert any(row["kind"] == "ORPHANED_PAGE" and row["target"] == duplicate for row in report["findings"])


def test_missing_lifecycle_target_and_superseded_status_are_distinct(fixture: tuple[Path, Path, dict]) -> None:
    monorepo, website, registry = fixture
    modified = copy.deepcopy(registry)
    modified["subprojects"]["demo"]["lifecycle_records"]["v1"]["state"] = "superseded"
    (monorepo / TEST).unlink()
    commit(monorepo)
    report = scan((monorepo, website, modified))
    assert report["coverage_complete"] is True
    assert {"MISSING_TEST_PATH", "LIFECYCLE_REVIEW_REQUIRED"} <= kinds(report)


def test_operational_record_uses_status_as_source_without_code_clock(fixture: tuple[Path, Path, dict]) -> None:
    monorepo, website, registry = fixture
    operational = copy.deepcopy(entry())
    operational.update(kind="operational", package="agent/problem_sets", code_paths=[],
                       website={"policy": "required", "page": "content/projects/academic-hub/guided/index.md", "reason": None})
    registry["subprojects"]["guided"] = operational
    frontmatter = page(operational).replace("id: demo", "id: guided")
    put(website, operational["website"]["page"], frontmatter)
    commit(website)
    report = scan((monorepo, website, registry))
    guided = next(row for row in report["components"] if row["id"] == "guided")
    assert guided["freshness_state"] == "heuristic_checked"
    assert not any(row["kind"] == "STATUS_HISTORY_GAP" and row["component_id"] == "guided"
                   for row in report["findings"])


def test_historical_status_does_not_produce_age_warning(fixture: tuple[Path, Path, dict]) -> None:
    monorepo, website, registry = fixture
    modified = copy.deepcopy(registry)
    modified["subprojects"]["demo"]["status_docs"][0]["role"] = "historical"
    put(website, PAGE, page(modified["subprojects"]["demo"]))
    commit(website)
    put(monorepo, STATUS, "# newer historical note\n")
    commit(monorepo, timestamp=1_700_010_000)
    report = scan((monorepo, website, modified))
    assert "STATUS_HISTORY_GAP" not in kinds(report)
    assert "WEBSITE_HISTORY_GAP" not in kinds(report)
