import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from git_fixture import git, make_repo, write_and_commit
from tools.git_workflow import dirty_files
from tools.land_branch import (
    LandingError,
    check,
    find_overlaps,
    preflight,
    project_relative,
    rebase_onto_main,
    run_checks,
    select_test_targets,
)
from tools.run_tests_chunked import ChunkResult


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

    def test_preflight_refuses_published_branch(self):
        write_and_commit(self.wt, {"core/b.py": "b = 1\n"}, "branch work")
        git(self.repo, "update-ref", "refs/remotes/origin/claude/t", "claude/t")
        with self.assertRaisesRegex(LandingError, "published"):
            preflight(self.wt)

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

    def test_conflicting_rebase_names_files_with_spaces_whole(self):
        write_and_commit(self.wt, {"core/a b.py": "x = 2\n"}, "branch edit")
        write_and_commit(self.repo, {"core/a b.py": "x = 3\n"}, "main edit")
        with self.assertRaises(LandingError) as ctx:
            rebase_onto_main(self.wt)
        self.assertIn("core/a b.py", str(ctx.exception))

    def test_rebase_abort_failure_does_not_replace_the_conflict_error(self):
        from unittest.mock import patch
        import tools.land_branch as land_branch
        write_and_commit(self.wt, {"core/a.py": "x = 2\n"}, "branch edit")
        write_and_commit(self.repo, {"core/a.py": "x = 3\n"}, "main edit")
        real_run_git = land_branch.run_git

        def fake_run_git(args, cwd):
            if args[0] == "rebase" and args[-1] != "--abort":
                raise land_branch.GitError("conflict")
            if args == ["rebase", "--abort"]:
                raise land_branch.GitError("abort also failed")
            return real_run_git(args, cwd)

        with patch("tools.land_branch.run_git", side_effect=fake_run_git):
            with self.assertRaises(LandingError):
                rebase_onto_main(self.wt)

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

    def test_check_run_from_subfolder_uses_worktree_root(self):
        write_and_commit(self.wt, {"core/a.py": "x = 2\n"}, "branch edit")
        result = check(self.wt / "core", subdir="")
        self.assertEqual(result.overlaps, [])
        self.assertEqual(result.branch, "claude/t")
        # "run everything" now goes through the chunked runner (final
        # review, Important), which reports the real chunks it found
        # instead of the literal "tests/" placeholder -- this fixture has
        # no tests/ directory at all, so that's an empty chunk list.
        self.assertEqual(result.check_targets, [])

    def test_check_maps_test_helper_only_change_to_its_directory(self):
        (self.repo / "tests" / "core").mkdir(parents=True)
        write_and_commit(
            self.repo,
            {"tests/core/test_existing.py": "def test_existing():\n    assert True\n"},
            "seed existing passing test",
        )
        wt2 = self.tmp / "wt2"
        git(self.repo, "worktree", "add", "-q", "-b", "claude/t2", str(wt2), "main")
        write_and_commit(wt2, {"tests/core/fixture.py": "VALUE = 1\n"}, "add helper fixture")
        result = check(wt2, subdir="")
        self.assertEqual(result.checks, "passed")
        self.assertEqual(result.check_targets, ["tests/core"])

    def test_check_skips_docs_only_branch(self):
        write_and_commit(self.wt, {"docs/note.md": "hi\n"}, "docs only")
        result = check(self.wt, subdir="")
        self.assertEqual(result.checks, "skipped")
        self.assertEqual(result.check_targets, [])

    def test_check_runs_full_suite_for_non_py_non_doc_change(self):
        # A dependency pin, lockfile, or test fixture can change what the
        # suite does without touching a .py file -- must not be treated as
        # skippable the way a Markdown-only branch is.
        (self.repo / "tests" / "core").mkdir(parents=True)
        write_and_commit(
            self.repo, {"tests/core/test_existing.py": "def test_existing():\n    assert True\n"},
            "seed existing passing test",
        )
        wt2 = self.tmp / "wt2"
        git(self.repo, "worktree", "add", "-q", "-b", "claude/t2", str(wt2), "main")
        write_and_commit(wt2, {"requirements.txt": "pytest==9\n"}, "pin a dependency")
        result = check(wt2, subdir="")
        self.assertEqual(result.checks, "passed")
        # Real chunk list (this fixture has tests/core/), not the literal
        # "tests/" placeholder -- see test_check_run_from_subfolder_uses_worktree_root.
        self.assertEqual(result.check_targets, ["tests/core"])

    def test_check_runs_full_suite_for_docs_mixed_with_other_change(self):
        write_and_commit(self.wt, {"docs/note.md": "hi\n", "requirements.txt": "pytest==9\n"}, "mixed")
        result = check(self.wt, subdir="")
        self.assertNotEqual(result.checks, "skipped")
        # This fixture has no tests/ directory, so the real chunk list is empty.
        self.assertEqual(result.check_targets, [])


class LandingLogTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.repo = make_repo(self.tmp / "repo")
        self.wt = self.tmp / "wt"
        git(self.repo, "worktree", "add", "-q", "-b", "claude/t", str(self.wt), "main")

    def tearDown(self):
        self._tmp.cleanup()

    def _entries(self):
        import json
        from tools.land_branch import log_path
        return [json.loads(line) for line in log_path(self.wt).read_text(encoding="utf-8").splitlines()]

    def test_log_lives_in_shared_git_dir(self):
        from tools.land_branch import log_path
        from tools.git_workflow import git_common_dir
        self.assertEqual(log_path(self.wt).parent.resolve(), git_common_dir(self.wt).resolve())

    def test_refused_check_is_logged_then_raised(self):
        from tools.land_branch import LandingError, check
        (self.wt / "scratch.txt").write_text("x", encoding="utf-8")
        with self.assertRaises(LandingError):
            check(self.wt, subdir="")
        entries = self._entries()
        self.assertEqual(entries[-1]["event"], "refused")
        self.assertIn("uncommitted", entries[-1]["reason"])

    def test_successful_check_is_logged(self):
        from tools.land_branch import check
        write_and_commit(self.wt, {"core/a.py": "x = 2\n"}, "branch edit")
        check(self.wt, subdir="")
        entry = self._entries()[-1]
        self.assertEqual(entry["event"], "check")
        self.assertEqual(entry["branch"], "claude/t")
        self.assertIn("rebased", entry)
        self.assertIn("check_seconds", entry)

    def test_record_writes_outcome_for_sha(self):
        from tools.land_branch import record
        record(self.wt, "abc123", "landed")
        entry = self._entries()[-1]
        self.assertEqual(entry["event"], "outcome")
        self.assertEqual(entry["sha"], "abc123")
        self.assertEqual(entry["outcome"], "landed")

    def test_record_rejects_unknown_outcome(self):
        from tools.land_branch import record
        with self.assertRaises(ValueError):
            record(self.wt, "abc123", "merged")


class RunChecksFullSuiteTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_full_run_uses_chunked_runner_and_reports_failure(self):
        fake_results = [
            ChunkResult(name="agent", returncode=0, seconds=1.0, stdout="ok"),
            ChunkResult(name="core", returncode=1, seconds=2.0, stdout="boom"),
        ]
        with patch(
            "tools.land_branch.run_all",
            return_value=("failed", fake_results, 3.0),
        ) as mock_run_all:
            status, targets, seconds = run_checks(self.tmp, changed=set(), full=True)

        mock_run_all.assert_called_once_with(self.tmp)
        self.assertEqual(status, "failed")
        self.assertEqual(targets, ["tests/agent", "tests/core"])
        self.assertEqual(seconds, 3.0)

    def test_full_run_reports_failure_for_a_non_one_exit_code(self):
        """Final review, Critical: a collection error (exit 2) or a crash
        must still fail the gate, not just exit code 1."""
        fake_results = [ChunkResult(name="tools", returncode=2, seconds=1.0, stdout="ImportError")]
        with patch("tools.land_branch.run_all", return_value=("failed", fake_results, 1.0)):
            status, targets, seconds = run_checks(self.tmp, changed=set(), full=True)

        self.assertEqual(status, "failed")

    def test_non_full_run_with_no_mapped_targets_also_uses_chunked_runner(self):
        """Final review, Important: `full=False` with no mapped test targets
        falls back to running tests/ as a whole -- that fallback must go
        through the chunked runner too, or a routine incremental
        `land_branch check` (e.g. after a requirements.txt pin, which maps
        to no test directory) can OOM the same way `--full` used to."""
        fake_results = [ChunkResult(name="agent", returncode=0, seconds=1.0, stdout="ok")]
        with patch(
            "tools.land_branch.run_all",
            return_value=("passed", fake_results, 1.0),
        ) as mock_run_all:
            status, targets, seconds = run_checks(
                self.tmp, changed={"requirements.txt"}, full=False
            )

        mock_run_all.assert_called_once_with(self.tmp)
        self.assertEqual(status, "passed")
        self.assertEqual(targets, ["tests/agent"])


class LandByChangeIdTests(unittest.TestCase):
    """`land` lands an approved change, re-checking only what main's movement could affect."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.repo = make_repo(self.tmp / "repo")
        self.origin = self.tmp / "origin.git"
        git(self.tmp, "init", "-q", "--bare", str(self.origin))
        git(self.repo, "remote", "add", "origin", str(self.origin))
        git(self.repo, "push", "-q", "origin", "main")
        self.wt = self.tmp / "wt"
        git(self.repo, "worktree", "add", "-q", "-b", "claude/t", str(self.wt), "main")

    def tearDown(self):
        self._tmp.cleanup()

    def _head(self, cwd, ref="HEAD"):
        return git(cwd, "rev-parse", ref).strip()

    def _approve(self, checks="passed"):
        from tools.land_branch import check
        with patch("tools.land_branch.run_checks", return_value=(checks, ["tests/core"], 0.1)):
            return check(self.wt, subdir="")

    def _entries(self):
        import json
        from tools.land_branch import log_path
        return [json.loads(l) for l in log_path(self.wt).read_text(encoding="utf-8").splitlines()]

    def test_change_id_is_stable_across_clean_rebase(self):
        from tools.land_branch import change_id
        write_and_commit(self.wt, {"core/a.py": "x = 2\n"}, "branch edit")
        before = change_id(self.wt)
        write_and_commit(self.repo, {"docs/n.md": "note\n"}, "unrelated docs on main")
        rebase_onto_main(self.wt)
        self.assertEqual(change_id(self.wt), before)

    def test_change_id_differs_for_whitespace_only_edit(self):
        from tools.land_branch import change_id
        write_and_commit(self.wt, {"core/a.py": "x = 2\n"}, "branch edit")
        before = change_id(self.wt)
        write_and_commit(self.wt, {"core/a.py": "x =  2\n"}, "whitespace")
        self.assertNotEqual(change_id(self.wt), before)

    def test_check_reports_change_id_and_base(self):
        from tools.land_branch import change_id
        write_and_commit(self.wt, {"core/a.py": "x = 2\n"}, "branch edit")
        result = self._approve()
        self.assertEqual(result.change_id, change_id(self.wt))
        self.assertEqual(result.base, self._head(self.repo, "main"))
        self.assertEqual(self._entries()[-1]["change_id"], result.change_id)

    def test_land_after_docs_only_main_commit_skips_retest_and_pushes(self):
        from tools.land_branch import land
        write_and_commit(self.wt, {"core/a.py": "x = 2\n"}, "branch edit")
        cid = self._approve().change_id
        write_and_commit(self.repo, {"docs/n.md": "note\n"}, "docs on main")
        with patch("tools.land_branch.run_checks") as rerun:
            result = land(self.wt, cid, subdir="")
        rerun.assert_not_called()
        self.assertFalse(result.retested)
        self.assertEqual(self._head(self.repo, "main"), self._head(self.wt))
        self.assertEqual(git(self.origin, "rev-parse", "main").strip(), self._head(self.wt))

    def test_land_reruns_tests_when_main_gains_code_and_stops_on_failure(self):
        from tools.land_branch import LandingError, land
        write_and_commit(self.wt, {"core/a.py": "x = 2\n"}, "branch edit")
        cid = self._approve().change_id
        write_and_commit(self.repo, {"core/b.py": "y = 1\n"}, "code on main")
        main_before = self._head(self.repo, "main")
        with patch("tools.land_branch.run_checks", return_value=("failed", ["tests/core"], 0.1)) as rerun:
            with self.assertRaisesRegex(LandingError, "tests failed"):
                land(self.wt, cid, subdir="")
        rerun.assert_called_once()
        self.assertEqual(self._head(self.repo, "main"), main_before)

    def test_land_stops_when_main_touched_a_branch_file_without_conflict(self):
        from tools.land_branch import LandingError, land
        lines = "".join(f"line {i}\n" for i in range(20))
        write_and_commit(self.repo, {"docs/guide.md": lines}, "seed guide")
        rebase_onto_main(self.wt)
        write_and_commit(self.wt, {"docs/guide.md": "edited\n" + lines[len("line 0\n"):]}, "branch edits top")
        cid = self._approve(checks="skipped").change_id
        write_and_commit(self.repo, {"docs/guide.md": lines.replace("line 19\n", "main edit\n")}, "main edits bottom")
        with self.assertRaisesRegex(LandingError, "docs/guide.md"):
            land(self.wt, cid, subdir="")

    def test_land_stops_when_change_id_differs(self):
        from tools.land_branch import LandingError, land
        write_and_commit(self.wt, {"core/a.py": "x = 2\n"}, "branch edit")
        cid = self._approve().change_id
        write_and_commit(self.wt, {"core/c.py": "z = 3\n"}, "more work after approval")
        with self.assertRaisesRegex(LandingError, "change"):
            land(self.wt, cid, subdir="")

    def test_land_refuses_a_change_with_no_passing_check(self):
        from tools.land_branch import LandingError, land
        write_and_commit(self.wt, {"core/a.py": "x = 2\n"}, "branch edit")
        with self.assertRaisesRegex(LandingError, "no passing check"):
            land(self.wt, "0" * 64, subdir="")

    def test_untracked_main_checkout_file_does_not_block(self):
        from tools.land_branch import land
        write_and_commit(self.wt, {"core/a.py": "x = 2\n"}, "branch edit")
        cid = self._approve().change_id
        (self.repo / "stray.svg").write_text("<svg/>", encoding="utf-8")
        land(self.wt, cid, subdir="")
        self.assertEqual(self._head(self.repo, "main"), self._head(self.wt))

    def test_dirty_tracked_branch_file_in_main_checkout_blocks(self):
        from tools.land_branch import LandingError, land
        write_and_commit(self.wt, {"core/a.py": "x = 2\n"}, "branch edit")
        cid = self._approve().change_id
        (self.repo / "core" / "a.py").write_text("x = 99\n", encoding="utf-8")
        with self.assertRaisesRegex(LandingError, "core/a.py"):
            land(self.wt, cid, subdir="")

    def _move_main_then_ff(self, files_for_call):
        """Wrap _ff_main so main gains a commit before each of the first len(files_for_call) tries."""
        import tools.land_branch as lb
        real, calls = lb._ff_main, []
        def wrapped(main_path, branch):
            if len(calls) < len(files_for_call):
                write_and_commit(self.repo, files_for_call[len(calls)], f"move {len(calls)}")
            calls.append(1)
            return real(main_path, branch)
        return wrapped, calls

    def test_markdown_only_main_movement_is_retried_past_three_attempts(self):
        from tools.land_branch import land
        write_and_commit(self.wt, {"core/a.py": "x = 2\n"}, "branch edit")
        cid = self._approve().change_id
        wrapped, calls = self._move_main_then_ff([{f"docs/n{i}.md": f"{i}\n"} for i in range(5)])
        with patch("tools.land_branch._ff_main", side_effect=wrapped), \
             patch("tools.land_branch.run_checks") as rerun:
            result = land(self.wt, cid, subdir="")
        rerun.assert_not_called()
        self.assertEqual(result.attempts, 6)
        self.assertEqual(self._head(self.repo, "main"), self._head(self.wt))

    def test_code_movement_gives_up_after_three_test_reruns(self):
        from tools.land_branch import LandingError, land
        write_and_commit(self.wt, {"core/a.py": "x = 2\n"}, "branch edit")
        cid = self._approve().change_id
        wrapped, _ = self._move_main_then_ff([{f"core/m{i}.py": f"v = {i}\n"} for i in range(10)])
        with patch("tools.land_branch._ff_main", side_effect=wrapped), \
             patch("tools.land_branch.run_checks", return_value=("passed", ["tests/core"], 0.1)) as rerun:
            # the first try sees no code delta (main has not moved yet), so no
            # re-test; each later try follows a .py commit and re-tests.
            with self.assertRaisesRegex(LandingError, "main kept moving"):
                land(self.wt, cid, subdir="")
        self.assertEqual(rerun.call_count, 3)

    def test_land_logs_land_and_outcome(self):
        from tools.land_branch import land
        write_and_commit(self.wt, {"core/a.py": "x = 2\n"}, "branch edit")
        cid = self._approve().change_id
        result = land(self.wt, cid, subdir="")
        events = {e["event"]: e for e in self._entries()}
        self.assertEqual(events["land"]["result"], "landed")
        self.assertEqual(events["land"]["change_id"], cid)
        self.assertEqual(events["outcome"], {**events["outcome"], "outcome": "landed", "sha": result.sha})

    def test_cli_land_prints_landed_or_stop(self):
        import contextlib
        import io
        from tools.land_branch import main
        write_and_commit(self.wt, {"core/a.py": "x = 2\n"}, "branch edit")
        cid = self._approve().change_id
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            bad = main(["land", "--worktree", str(self.wt), "--change-id", "0" * 64, "--subdir", ""])
            good = main(["land", "--worktree", str(self.wt), "--change-id", cid, "--subdir", ""])
        self.assertEqual((bad, good), (1, 0))
        self.assertIn("STOP:", err.getvalue())
        self.assertIn(f"LANDED {self._head(self.wt)}", out.getvalue())

    def test_stopped_land_is_logged_with_reason(self):
        from tools.land_branch import LandingError, land
        write_and_commit(self.wt, {"core/a.py": "x = 2\n"}, "branch edit")
        cid = self._approve().change_id
        write_and_commit(self.wt, {"core/c.py": "z = 3\n"}, "more work")
        with self.assertRaises(LandingError):
            land(self.wt, cid, subdir="")
        last = self._entries()[-1]
        self.assertEqual(last["event"], "land")
        self.assertIn("change", last["result"])


if __name__ == "__main__":
    unittest.main()
