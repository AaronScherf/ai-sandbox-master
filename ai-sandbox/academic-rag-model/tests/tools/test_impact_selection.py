"""tools.impact_selection: which test files can a change affect (rules 2 and 3 of the
landing-test-selection proposal). Projects here are tiny temp trees."""
from pathlib import Path

import pytest

from tools.impact_selection import select_tests


def make_project(tmp_path: Path, files: dict[str, str]) -> Path:
    for rel, text in files.items():
        target = tmp_path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    return tmp_path


def files_for(tmp_path, project, changed):
    return select_tests(set(changed), make_project(tmp_path, project))


def test_selects_only_tests_that_import_the_changed_module(tmp_path):
    selection = files_for(tmp_path, {
        "core/a.py": "x = 1\n",
        "core/b.py": "from core.a import x\n",
        "tests/core/test_b.py": "from core.b import x\n",
        "tests/core/test_other.py": "import json\n",
    }, {"core/a.py"})
    assert selection.files == ["tests/core/test_b.py"]
    assert selection.run_all_reason is None


def test_follows_imports_through_several_modules_and_packages(tmp_path):
    selection = files_for(tmp_path, {
        "core/__init__.py": "",
        "core/env/__init__.py": "",
        "core/env/paths.py": "ROOT = 1\n",
        "agent/__init__.py": "",
        "agent/tool.py": "import core.env.paths as p\n",
        "agent/cli.py": "from agent import tool\n",
        "tests/agent/test_cli.py": "import agent.cli\n",
        "tests/agent/test_unrelated.py": "import os\n",
    }, {"core/env/paths.py"})
    assert selection.files == ["tests/agent/test_cli.py"]


def test_resolves_relative_imports(tmp_path):
    selection = files_for(tmp_path, {
        "pkg/__init__.py": "",
        "pkg/y.py": "V = 1\n",
        "pkg/x.py": "from . import y\n",
        "tests/pkg/test_x.py": "import pkg.x\n",
    }, {"pkg/y.py"})
    assert selection.files == ["tests/pkg/test_x.py"]


def test_resolves_bare_sibling_helper_imports_in_tests(tmp_path):
    selection = files_for(tmp_path, {
        "tests/tools/git_fixture.py": "V = 1\n",
        "tests/tools/test_a.py": "from git_fixture import V\n",
        "tests/tools/test_b.py": "import os\n",
    }, {"tests/tools/git_fixture.py"})
    assert selection.files == ["tests/tools/test_a.py"]


def test_changed_test_file_selects_itself(tmp_path):
    selection = files_for(tmp_path, {
        "tests/core/test_a.py": "def test_a():\n    pass\n",
        "tests/core/test_b.py": "def test_b():\n    pass\n",
    }, {"tests/core/test_a.py"})
    assert selection.files == ["tests/core/test_a.py"]


def test_reads_files_with_a_byte_order_mark(tmp_path):
    root = make_project(tmp_path, {"core/a.py": "x = 1\n"})
    (root / "tests" / "core").mkdir(parents=True)
    (root / "tests" / "core" / "test_a.py").write_bytes(b"\xef\xbb\xbffrom core.a import x\n")
    assert select_tests({"core/a.py"}, root).files == ["tests/core/test_a.py"]


def test_unparsable_test_files_are_always_selected(tmp_path):
    selection = files_for(tmp_path, {
        "core/a.py": "x = 1\n",
        "tests/core/test_broken.py": "def (:\n",
    }, {"core/a.py"})
    assert "tests/core/test_broken.py" in selection.files


def test_data_file_named_by_a_test_selects_that_test(tmp_path):
    selection = files_for(tmp_path, {
        "guide_specs/econ/wald.toml": "a = 1\n",
        "tests/agent/test_guide.py": "P = 'guide_specs' + '/econ/wald.toml'\n",
        "tests/agent/test_other.py": "import os\n",
    }, {"guide_specs/econ/wald.toml"})
    assert selection.files == ["tests/agent/test_guide.py"]


def test_data_file_read_by_a_module_selects_that_modules_tests(tmp_path):
    selection = files_for(tmp_path, {
        "agent/loader.py": "NAME = 'rules.json'\n",
        "agent/data/rules.json": "{}\n",
        "tests/agent/test_loader.py": "import agent.loader\n",
        "tests/agent/test_other.py": "import os\n",
    }, {"agent/data/rules.json"})
    assert selection.files == ["tests/agent/test_loader.py"]


def test_data_file_nothing_references_selects_no_tests(tmp_path):
    selection = files_for(tmp_path, {
        "docs/trackers/unused_table.json": "{}\n",
        "tests/core/test_a.py": "import os\n",
    }, {"docs/trackers/unused_table.json"})
    assert selection.files == []
    assert selection.run_all_reason is None


def test_changed_package_also_runs_its_mirror_test_directory(tmp_path):
    # A test that only runs the code in a subprocess imports nothing, so the
    # mirror directory under tests/ is the only link to it.
    selection = files_for(tmp_path, {
        "core/indexer/a.py": "x = 1\n",
        "tests/core/indexer/test_cli_subprocess.py": "import subprocess\n",
        "tests/core/other/test_elsewhere.py": "import os\n",
    }, {"core/indexer/a.py"})
    assert selection.files == ["tests/core/indexer/test_cli_subprocess.py"]


def test_top_level_package_file_matches_tests_by_name(tmp_path):
    selection = files_for(tmp_path, {
        "tools/land_branch.py": "x = 1\n",
        "tests/tools/test_land_branch_cli.py": "import subprocess\n",
        "tests/tools/test_unrelated.py": "import os\n",
    }, {"tools/land_branch.py"})
    assert selection.files == ["tests/tools/test_land_branch_cli.py"]


@pytest.mark.parametrize("path", ["conftest.py", "tests/conftest.py", "tests/helpers.py",
                                  "pytest.ini", "requirements.txt", "requirements-dev.txt",
                                  "pyproject.toml", "tox.ini", "setup.cfg"])
def test_helpers_pins_and_config_run_everything(tmp_path, path):
    selection = files_for(tmp_path, {"tests/core/test_a.py": "import os\n", path: "x\n"}, {path})
    assert selection.run_all_reason in ("helper_change", "config_change")


def test_a_subfolder_conftest_runs_only_the_tests_below_it(tmp_path):
    selection = files_for(tmp_path, {
        "tests/core/conftest.py": "import pytest\n",
        "tests/core/test_a.py": "import os\n",
        "tests/agent/test_b.py": "import os\n",
    }, {"tests/core/conftest.py"})
    assert selection.files == ["tests/core/test_a.py"]
    assert selection.run_all_reason is None


def test_deleted_or_renamed_python_file_runs_everything(tmp_path):
    selection = files_for(tmp_path, {"core/b.py": "x = 1\n"}, {"core/a.py", "core/b.py"})
    assert selection.run_all_reason == "moved_or_deleted_file"


def test_code_with_no_tests_at_all_runs_everything(tmp_path):
    selection = files_for(tmp_path, {"core/a.py": "x = 1\n", "tests/core/test_b.py": "import os\n"},
                          {"core/a.py"})
    assert selection.run_all_reason == "no_tests_for_code"


def test_markdown_is_ignored_next_to_code(tmp_path):
    selection = files_for(tmp_path, {
        "core/a.py": "x = 1\n",
        "tests/core/test_a.py": "from core.a import x\n",
        "docs/note.md": "hi\n",
    }, {"core/a.py", "docs/note.md"})
    assert selection.files == ["tests/core/test_a.py"]


def test_skips_virtualenv_archive_and_model_directories(tmp_path):
    selection = files_for(tmp_path, {
        "core/a.py": "x = 1\n",
        ".venv/lib/core_user.py": "from core.a import x\n",
        "archive/old_attempts/old.py": "from core.a import x\n",
        "tests/core/test_a.py": "from core.a import x\n",
    }, {"core/a.py"})
    assert selection.files == ["tests/core/test_a.py"]


def test_a_changed_test_helper_runs_the_tests_in_its_folder(tmp_path):
    selection = files_for(tmp_path, {
        "tests/core/fixture.py": "VALUE = 1\n",
        "tests/core/test_a.py": "import os\n",
        "tests/agent/test_b.py": "import os\n",
    }, {"tests/core/fixture.py"})
    assert selection.files == ["tests/core/test_a.py"]
    assert selection.run_all_reason is None


def test_a_folder_name_many_files_mention_does_not_select_them_all(tmp_path):
    project = {"docs/trackers/unused.json": "{}\n"}
    for n in range(12):
        project[f"tests/core/test_{n}.py"] = "NOTE = 'see docs/trackers for status'\n"
    assert files_for(tmp_path, project, {"docs/trackers/unused.json"}).files == []


def test_a_rarely_mentioned_folder_name_selects_the_tests_that_read_that_folder(tmp_path):
    selection = files_for(tmp_path, {
        "agent/concept_graph/sample_data/case.json": "{}\n",
        "tests/agent/graph/test_reads_folder.py": "SAMPLE = 'sample_data'\n",
        "tests/agent/graph/test_other.py": "import os\n",
    }, {"agent/concept_graph/sample_data/case.json"})
    assert selection.files == ["tests/agent/graph/test_reads_folder.py"]


def test_a_data_file_also_runs_its_nearest_mirror_test_folder(tmp_path):
    selection = files_for(tmp_path, {
        "tools/corpus_health/example.json": "{}\n",
        "tests/tools/corpus_health/test_scanner.py": "import os\n",
        "tests/tools/test_elsewhere.py": "import os\n",
    }, {"tools/corpus_health/example.json"})
    assert selection.files == ["tests/tools/corpus_health/test_scanner.py"]


def test_edits_between_calls_are_seen(tmp_path):
    root = make_project(tmp_path, {
        "core/a.py": "x = 1\n",
        "tests/core/test_a.py": "from core.a import x\n",
        "tests/core/test_b.py": "import os\n",
    })
    assert select_tests({"core/a.py"}, root).files == ["tests/core/test_a.py"]
    (root / "tests/core/test_b.py").write_text("from core.a import x  # now imports it\n", encoding="utf-8")
    assert select_tests({"core/a.py"}, root).files == ["tests/core/test_a.py", "tests/core/test_b.py"]
