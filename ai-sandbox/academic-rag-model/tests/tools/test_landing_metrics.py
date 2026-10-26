import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path

from git_fixture import git, make_repo, write_and_commit
from tools.landing_metrics import commit_stats, landings, main, summarize, worktree_stats


def check(at, branch, sha, checks="passed", change_id=None):
    entry = {"at": at, "event": "check", "branch": branch, "sha": sha, "checks": checks}
    if change_id:
        entry["change_id"] = change_id
    return entry


def landed(at, sha):
    return {"at": at, "event": "outcome", "outcome": "landed", "sha": sha}


T0 = "2026-10-20T10:00:00+00:00"
T1 = "2026-10-20T10:30:00+00:00"
T2 = "2026-10-20T11:00:00+00:00"


class LandingsTests(unittest.TestCase):
    def test_one_passing_check_is_one_approval(self):
        rows = landings([check(T0, "claude/a", "s1"), landed(T1, "s1")])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].branch, "claude/a")
        self.assertEqual(rows[0].approvals, 1)
        self.assertEqual(rows[0].minutes, 30)

    def test_each_new_passing_sha_is_another_approval(self):
        rows = landings([check(T0, "claude/a", "s1"), check(T1, "claude/a", "s2"), landed(T2, "s2")])
        self.assertEqual(rows[0].approvals, 2)
        self.assertEqual(rows[0].minutes, 60)

    def test_same_change_id_across_rebases_is_one_approval(self):
        rows = landings([
            check(T0, "claude/a", "s1", change_id="c1"),
            check(T1, "claude/a", "s2", change_id="c1"),
            landed(T2, "s2"),
        ])
        self.assertEqual(rows[0].approvals, 1)

    def test_land_stop_counts_as_another_approval(self):
        rows = landings([
            check(T0, "claude/a", "s1", change_id="c1"),
            {"at": T1, "event": "land", "branch": "claude/a", "result": "main changed app.py"},
            landed(T2, "s1"),
        ])
        self.assertEqual(rows[0].approvals, 2)

    def test_failed_checks_and_later_checks_are_ignored(self):
        rows = landings([
            check(T0, "claude/a", "s0", checks="failed"),
            check(T1, "claude/a", "s1", checks="skipped"),
            landed(T2, "s1"),
            check("2026-10-21T00:00:00+00:00", "claude/a", "s9"),
        ])
        self.assertEqual(rows[0].approvals, 1)
        self.assertEqual(rows[0].minutes, 30)

    def test_since_drops_earlier_landings(self):
        entries = [check(T0, "claude/a", "s1"), landed(T1, "s1"),
                   check(T0, "claude/b", "s2"), landed("2026-10-27T00:00:00+00:00", "s2")]
        rows = landings(entries, since=datetime(2026, 10, 26, tzinfo=timezone.utc))
        self.assertEqual([r.branch for r in rows], ["claude/b"])

    def test_summarize(self):
        rows = landings([
            check(T0, "claude/a", "s1"), landed(T1, "s1"),
            check(T0, "claude/b", "s2"), check(T1, "claude/b", "s3"), landed(T2, "s3"),
        ])
        s = summarize(rows)
        self.assertEqual(s["landed"], 2)
        self.assertEqual(s["multi_approval"], 1)
        self.assertEqual(s["extra_rounds"], 1)
        self.assertEqual(s["median_minutes"], 45)


class GitStatsTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.repo = make_repo(self.tmp / "repo")

    def tearDown(self):
        self._tmp.cleanup()

    def test_commit_stats_counts_merges_and_todo_commits(self):
        git(self.repo, "checkout", "-q", "-b", "side")
        write_and_commit(self.repo, {"core/s.py": "s = 1\n"}, "side work")
        git(self.repo, "checkout", "-q", "main")
        write_and_commit(self.repo, {"docs/t.md": "t\n"}, "todo: add item")
        git(self.repo, "merge", "-q", "--no-ff", "-m", "Merge branch 'side'", "side")
        s = commit_stats(self.repo, "2000-01-01", "2090-01-01")
        self.assertEqual(s["commits"], 4)
        self.assertEqual(s["merges"], 1)
        self.assertEqual(s["todo"], 1)

    def test_worktree_stats_counts_merged_worktrees(self):
        git(self.repo, "worktree", "add", "-q", "-b", "claude/done", str(self.tmp / "done"), "main")
        git(self.repo, "worktree", "add", "-q", "-b", "claude/open", str(self.tmp / "open"), "main")
        write_and_commit(self.tmp / "open", {"core/o.py": "o = 1\n"}, "open work")
        self.assertEqual(worktree_stats(self.repo), {"worktrees": 2, "merged": 1})

    def test_cli_prints_landing_summary(self):
        log = Path(git(self.repo, "rev-parse", "--path-format=absolute", "--git-common-dir").strip())
        lines = [check(T0, "claude/a", "s1"), landed(T1, "s1")]
        (log / "agent-landing-log.jsonl").write_text(
            "".join(json.dumps(e) + "\n" for e in lines), encoding="utf-8")
        out = io.StringIO()
        with redirect_stdout(out):
            code = main(["--repo", str(self.repo), "--since", "2026-10-01"])
        self.assertEqual(code, 0)
        self.assertIn("landed 1", out.getvalue())
        self.assertIn("needing >1 approval 0", out.getvalue())


if __name__ == "__main__":
    unittest.main()
