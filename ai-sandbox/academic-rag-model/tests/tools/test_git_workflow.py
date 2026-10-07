import tempfile
import unittest
from pathlib import Path

from git_fixture import git, make_repo, write_and_commit
from tools.git_workflow import (
    changed_since_merge_base,
    current_branch,
    dirty_files,
    list_worktrees,
    main_checkout,
)


class GitWorkflowTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.repo = make_repo(self.tmp / "repo")

    def tearDown(self):
        self._tmp.cleanup()

    def test_list_worktrees_reports_branch_and_detached(self):
        wt = self.tmp / "wt"
        git(self.repo, "worktree", "add", "-q", "-b", "claude/t", str(wt), "main")
        detached = self.tmp / "det"
        git(self.repo, "worktree", "add", "-q", "--detach", str(detached), "main")
        entries = list_worktrees(self.repo)
        self.assertEqual(entries[0].branch, "main")
        self.assertEqual(main_checkout(wt).path.resolve(), self.repo.resolve())
        branches = {e.path.resolve(): e.branch for e in entries}
        self.assertEqual(branches[wt.resolve()], "claude/t")
        self.assertIsNone(branches[detached.resolve()])

    def test_current_branch_none_when_detached(self):
        git(self.repo, "checkout", "-q", "--detach")
        self.assertIsNone(current_branch(self.repo))

    def test_dirty_files_lists_untracked_and_renamed_paths(self):
        (self.repo / "core" / "new file.py").write_text("y = 2\n", encoding="utf-8")
        git(self.repo, "mv", "core/a.py", "core/renamed.py")
        self.assertEqual(
            dirty_files(self.repo),
            {"core/new file.py", "core/renamed.py"},
        )

    def test_changed_since_merge_base_ignores_main_only_changes(self):
        wt = self.tmp / "wt"
        git(self.repo, "worktree", "add", "-q", "-b", "claude/t", str(wt), "main")
        write_and_commit(wt, {"core/branch.py": "b = 1\n"}, "branch work")
        write_and_commit(self.repo, {"core/main_only.py": "m = 1\n"}, "main work")
        self.assertEqual(
            changed_since_merge_base(self.repo, "main", "claude/t"),
            {"core/branch.py"},
        )


if __name__ == "__main__":
    unittest.main()
