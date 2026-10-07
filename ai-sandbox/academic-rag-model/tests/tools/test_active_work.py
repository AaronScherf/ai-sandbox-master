import tempfile
import unittest
from pathlib import Path

from git_fixture import git, make_repo, write_and_commit
from tools.active_work import build_report


class ActiveWorkTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.repo = make_repo(self.tmp / "repo")

    def tearDown(self):
        self._tmp.cleanup()

    def test_flags_merged_branch_as_retirement_candidate(self):
        wt = self.tmp / "merged"
        git(self.repo, "worktree", "add", "-q", "-b", "claude/done", str(wt), "main")
        report = "\n".join(build_report(self.repo))
        self.assertIn("claude/done", report)
        self.assertIn("retirement candidate", report)

    def test_flags_overlap_between_two_branches(self):
        a = self.tmp / "a"
        b = self.tmp / "b"
        git(self.repo, "worktree", "add", "-q", "-b", "claude/a", str(a), "main")
        git(self.repo, "worktree", "add", "-q", "-b", "codex/b", str(b), "main")
        write_and_commit(a, {"core/a.py": "x = 2\n"}, "a edit")
        write_and_commit(b, {"core/a.py": "x = 3\n"}, "b edit")
        report = "\n".join(build_report(self.repo))
        self.assertIn("OVERLAP claude/a <-> codex/b: core/a.py", report)

    def test_flags_overlap_with_main_checkout_edit(self):
        a = self.tmp / "a"
        git(self.repo, "worktree", "add", "-q", "-b", "claude/a", str(a), "main")
        write_and_commit(a, {"core/a.py": "x = 2\n"}, "a edit")
        (self.repo / "core" / "a.py").write_text("x = 9\n", encoding="utf-8")
        report = "\n".join(build_report(self.repo))
        self.assertIn("OVERLAP claude/a <-> main checkout uncommitted: core/a.py", report)

    def test_worktree_with_only_uncommitted_work_is_not_retirement_candidate(self):
        wt = self.tmp / "dirty"
        git(self.repo, "worktree", "add", "-q", "-b", "claude/dirty", str(wt), "main")
        (wt / "core" / "scratch.py").write_text("s = 1\n", encoding="utf-8")
        report = "\n".join(build_report(self.repo))
        self.assertNotIn("retirement candidate", report)
        self.assertIn("claude/dirty", report)

    def test_flags_overlap_with_other_worktree_uncommitted_edit(self):
        a = self.tmp / "a"
        b = self.tmp / "b"
        git(self.repo, "worktree", "add", "-q", "-b", "claude/a", str(a), "main")
        git(self.repo, "worktree", "add", "-q", "-b", "codex/b", str(b), "main")
        write_and_commit(a, {"core/a.py": "x = 2\n"}, "a edit")
        (b / "core" / "a.py").write_text("x = 3\n", encoding="utf-8")
        report = "\n".join(build_report(self.repo))
        self.assertIn("OVERLAP claude/a <-> codex/b: core/a.py", report)

    def test_reports_nothing_to_flag_for_clean_repo(self):
        report = "\n".join(build_report(self.repo))
        self.assertIn("no open worktrees", report)


if __name__ == "__main__":
    unittest.main()
