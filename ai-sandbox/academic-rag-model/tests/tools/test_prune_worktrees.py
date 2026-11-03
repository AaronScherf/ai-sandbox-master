import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

from git_fixture import git, make_repo, write_and_commit
from tools.prune_worktrees import main, run


class PruneWorktreesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = make_repo(Path(self.temp.name) / "repo")
        (self.repo / ".worktrees").mkdir()

    def add(self, name, *, old=True, outside=False):
        path = self.repo / ("outside" if outside else ".worktrees") / name
        git(self.repo, "worktree", "add", "-q", "-b", name, str(path), "main")
        if old:
            stamp = time.time() - 172800
            os.utime(path / ".git", (stamp, stamp))
        return path

    def report(self, *args, cwd=None):
        return run(self.repo, cwd or self.repo, list(args))

    def test_age_and_unmerged(self):
        self.add("old")
        self.add("new", old=False)
        ahead = self.add("ahead")
        write_and_commit(ahead, {"extra.txt": "extra\n"}, "extra")
        code, lines = self.report()
        self.assertEqual(code, 0)
        self.assertIn("removable  old", "\n".join(lines))
        self.assertIn("recent  new", "\n".join(lines))
        self.assertIn("unmerged  ahead", "\n".join(lines))
        self.assertIn("ahead 1", "\n".join(lines))
        self.report("--apply")
        self.assertTrue(ahead.exists())
        self.assertIn("ahead", git(self.repo, "branch"))

    def test_dirty_and_ignored(self):
        untracked = self.add("untracked")
        (untracked / "scratch.txt").write_text("x")
        cache = self.add("cache")
        (self.repo / ".git" / "info" / "exclude").write_text("__pycache__/\n*.log\n")
        (cache / "__pycache__").mkdir()
        (cache / "__pycache__" / "x.pyc").write_text("x")
        other = self.add("other")
        (other / "build.log").write_text("x")
        _, lines = self.report()
        text = "\n".join(lines)
        self.assertIn("dirty  untracked", text)
        self.assertIn("removable  cache", text)
        self.assertIn("dirty  other", text)

    def test_locked_outside_detached_and_current(self):
        locked = self.add("locked")
        git(self.repo, "worktree", "lock", str(locked))
        self.add("external", outside=True)
        detached = self.add("detached")
        git(detached, "checkout", "--detach", "-q")
        current = self.add("current")
        _, lines = self.report(cwd=current)
        text = "\n".join(lines)
        for category, name in [("locked", "locked"), ("main-checkout", "external"),
                               ("detached-or-missing-branch", "detached"), ("current", "current")]:
            self.assertIn(f"{category}  {name if name != 'detached' else '-'}", text)
        code, _ = self.report("--apply", cwd=current)
        self.assertEqual(code, 2)
        self.assertTrue(current.exists())

    def test_apply_and_orphans(self):
        removable = self.add("removable")
        recent = self.add("recent", old=False)
        empty = self.repo / ".worktrees" / "empty"
        (empty / "nested").mkdir(parents=True)
        full = self.repo / ".worktrees" / "full"
        full.mkdir()
        (full / "file.txt").write_text("x")
        before = (git(self.repo, "worktree", "list"), git(self.repo, "branch"))
        code, lines = self.report()
        self.assertEqual(code, 0)
        self.assertEqual(before, (git(self.repo, "worktree", "list"), git(self.repo, "branch")))
        self.assertIn("empty", "\n".join(lines))
        self.assertIn("has files (1)", "\n".join(lines))
        code, lines = self.report("--apply")
        self.assertEqual(code, 0)
        self.assertFalse(removable.exists())
        self.assertNotIn("removable", git(self.repo, "branch"))
        self.assertTrue(recent.exists())
        self.assertFalse(empty.exists())
        self.assertTrue(full.exists())
        self.assertIn("git branch -d removable", "\n".join(lines))
        self.assertIn("git worktree prune", "\n".join(lines))

    def test_child_repo_categories_and_apply(self):
        child = make_repo(Path(self.temp.name) / "child")
        old = self.repo / ".worktrees" / "child-old"
        new = self.repo / ".worktrees" / "child-new"
        dirty = self.repo / ".worktrees" / "child-dirty"
        ahead = self.repo / ".worktrees" / "child-ahead"
        for name, path in [("old", old), ("new", new), ("dirty", dirty), ("ahead", ahead)]:
            git(child, "worktree", "add", "-q", "-b", name, str(path), "main")
        for path in (old, dirty, ahead):
            stamp = time.time() - 172800
            os.utime(path / ".git", (stamp, stamp))
        (dirty / "scratch.txt").write_text("dirty")
        write_and_commit(ahead, {"extra.txt": "extra\n"}, "extra")
        code, lines = self.report()
        report = "\n".join(lines)
        self.assertEqual(code, 0)
        self.assertIn(f"repo: {child}", report)
        for category, name in [("removable", "old"), ("recent", "new"),
                               ("dirty", "dirty"), ("unmerged", "ahead")]:
            self.assertIn(f"{category}  {name}", report)
        outer_before = git(self.repo, "worktree", "list")
        code, _ = self.report("--apply")
        self.assertEqual(code, 0)
        self.assertFalse(old.exists())
        self.assertNotIn(str(old), git(child, "worktree", "list"))
        self.assertNotIn("old", git(child, "branch"))
        self.assertEqual(outer_before, git(self.repo, "worktree", "list"))

    def test_child_without_main(self):
        child = make_repo(Path(self.temp.name) / "child")
        path = self.repo / ".worktrees" / "child"
        git(child, "worktree", "add", "-q", "-b", "topic", str(path), "main")
        git(child, "branch", "-m", "main", "trunk")
        code, lines = self.report("--apply")
        self.assertEqual(code, 0)
        self.assertIn("unknown-base  topic", "\n".join(lines))
        self.assertTrue(path.exists())

    def test_stale_remains(self):
        write_and_commit(self.repo, {"same.txt": "same\n"}, "same")
        paths = [self.repo / ".worktrees" / name for name in ("same", "extra", "_kept", "linked")]
        for path in paths:
            path.mkdir()
            (path / "same.txt").write_text("same\n")
            (path / ".git").write_text("gitdir: /missing/repo/.git/worktrees/gone\n")
        (paths[1] / "extra.txt").write_text("unique")
        try:
            (paths[3] / "link").symlink_to(paths[0], target_is_directory=True)
        except OSError:
            self.skipTest("symlinks unavailable")
        code, lines = self.report()
        report = "\n".join(lines)
        for category, name in [("identical-to-main", "same"), ("differs", "extra"),
                               ("kept-by-name", "_kept"), ("manual-review", "linked")]:
            self.assertIn(f"{category}  {self.repo / '.worktrees' / name}", report)
        self.assertIn("extra.txt", report)
        code, _ = self.report("--apply")
        self.assertEqual(code, 0)
        self.assertFalse(paths[0].exists())
        for path in paths[1:]:
            self.assertTrue(path.exists())

    def test_main_finds_root_from_worktree(self):
        path = self.add("current")
        import contextlib
        import io
        original = Path.cwd()
        try:
            os.chdir(self.repo)
            with contextlib.redirect_stdout(io.StringIO()) as main_output:
                self.assertEqual(main([]), 0)
            os.chdir(path)
            with contextlib.redirect_stdout(io.StringIO()) as worktree_output:
                self.assertEqual(main([]), 0)
            self.assertEqual(main_output.getvalue(), worktree_output.getvalue())
        finally:
            os.chdir(original)


if __name__ == "__main__":
    unittest.main()
