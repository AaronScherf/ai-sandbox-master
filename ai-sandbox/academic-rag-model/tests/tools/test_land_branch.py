import tempfile
import unittest
from pathlib import Path

from git_fixture import git, make_repo, write_and_commit
from tools.git_workflow import dirty_files
from tools.land_branch import (
    LandingError,
    check,
    find_overlaps,
    preflight,
    project_relative,
    rebase_onto_main,
    select_test_targets,
)


class LandBranchTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.repo = make_repo(self.tmp / "repo")
        self.wt = self.tmp / "wt"
        git(self.repo, "worktree", "add", "-q", "-b", "claude/t", str(self.wt), "main")

    def tearDown(self):
        self._tmp.cleanup()

    def test_preflight_refuses_main(self):
        with self.assertRaisesRegex(LandingError, "on main"):
            preflight(self.repo)

    def test_preflight_refuses_detached_head(self):
        git(self.wt, "checkout", "-q", "--detach")
        with self.assertRaisesRegex(LandingError, "detached"):
            preflight(self.wt)

    def test_preflight_refuses_dirty_worktree(self):
        (self.wt / "scratch.txt").write_text("x", encoding="utf-8")
        with self.assertRaisesRegex(LandingError, "uncommitted"):
            preflight(self.wt)

    def test_rebase_is_noop_when_branch_already_has_main(self):
        self.assertFalse(rebase_onto_main(self.wt))

    def test_rebase_onto_moved_main_changes_sha(self):
        write_and_commit(self.wt, {"core/branch.py": "b = 1\n"}, "branch work")
        write_and_commit(self.repo, {"core/other.py": "o = 1\n"}, "main work")
        before = git(self.wt, "rev-parse", "HEAD").strip()
        self.assertTrue(rebase_onto_main(self.wt))
        self.assertNotEqual(git(self.wt, "rev-parse", "HEAD").strip(), before)

    def test_conflicting_rebase_is_aborted_and_named(self):
        write_and_commit(self.wt, {"core/a.py": "x = 2\n"}, "branch edit")
        write_and_commit(self.repo, {"core/a.py": "x = 3\n"}, "main edit")
        before = git(self.wt, "rev-parse", "HEAD").strip()
        with self.assertRaises(LandingError) as ctx:
            rebase_onto_main(self.wt)
        self.assertIn("core/a.py", str(ctx.exception))
        self.assertEqual(git(self.wt, "rev-parse", "HEAD").strip(), before)
        self.assertEqual(dirty_files(self.wt), set())

    def test_overlap_ignores_paths_only_main_changed(self):
        write_and_commit(self.wt, {"core/branch.py": "b = 1\n"}, "branch work")
        write_and_commit(self.repo, {"core/main_only.py": "m = 1\n"}, "main work")
        self.assertEqual(find_overlaps(self.wt, {"core/branch.py"}), [])

    def test_overlap_reports_uncommitted_main_checkout_edit(self):
        write_and_commit(self.wt, {"core/a.py": "x = 2\n"}, "branch edit")
        (self.repo / "core" / "a.py").write_text("x = 9\n", encoding="utf-8")
        self.assertEqual(find_overlaps(self.wt, {"core/a.py"}), ["core/a.py"])

    def test_test_targets_maps_changed_packages(self):
        (self.repo / "tests" / "core").mkdir(parents=True)
        (self.repo / "tests" / "core" / "test_x.py").write_text("", encoding="utf-8")
        self.assertEqual(
            select_test_targets({"core/a.py", "docs/readme.md"}, self.repo),
            ["tests/core"],
        )

    def test_project_relative_strips_subproject_prefix(self):
        self.assertEqual(
            project_relative({"ai-sandbox/academic-rag-model/core/a.py", "docs/x.md"},
                             "ai-sandbox/academic-rag-model"),
            {"core/a.py"},
        )

    def test_check_passes_with_passing_mapped_tests(self):
        write_and_commit(self.wt, {"core/a.py": "x = 2\n"}, "branch edit")
        write_and_commit(self.wt, {"tests/core/test_ok.py": "def test_ok():\n    assert True\n"}, "add test")
        result = check(self.wt, subdir="")
        self.assertEqual(result.checks, "passed")
        self.assertEqual(result.check_targets, ["tests/core"])
        self.assertEqual(result.branch, "claude/t")

    def test_check_fails_with_failing_test(self):
        write_and_commit(self.wt, {"tests/core/test_bad.py": "def test_bad():\n    assert False\n"}, "add bad test")
        result = check(self.wt, subdir="")
        self.assertEqual(result.checks, "failed")

    def test_check_skips_docs_only_branch(self):
        write_and_commit(self.wt, {"docs/note.md": "hi\n"}, "docs only")
        result = check(self.wt, subdir="")
        self.assertEqual(result.checks, "skipped")
        self.assertEqual(result.check_targets, [])


if __name__ == "__main__":
    unittest.main()
