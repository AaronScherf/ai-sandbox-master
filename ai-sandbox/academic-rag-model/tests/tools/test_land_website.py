import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from git_fixture import git, make_repo, write_and_commit
from tools import land_website as site, reference_checker, reference_review


class Registry:
    def get(self, url):
        if "/doiRA/" in url:
            if "10.5555%2F123456" in url:
                return {"status": 200, "data": [{"status": "DOI does not exist"}]}
            return {"status": 200, "data": [{"RA": "Crossref"}]}
        if "/works/" in url:
            if "10.5555%2F123456" in url:
                return {"status": 404, "data": None}
            return {"status": 200, "data": {"message": {
                "title": ["A Registered Paper Title"], "author": [{"family": "Smith"}],
                "published": {"date-parts": [[2020]]}}}}
        if "api.datacite.org/dois/" in url:
            return {"status": 404, "data": None}
        if "api.crossref.org/works?" in url:
            return {"status": 200, "data": {"message": {"items": []}}}
        if "api.openalex.org/works?" in url:
            return {"status": 200, "data": {"results": []}}
        raise AssertionError(url)


class WebsiteLandingTests(unittest.TestCase):
    def setUp(self):
        self.tmp_obj = tempfile.TemporaryDirectory()
        self.tmp = Path(self.tmp_obj.name)
        self.main = make_repo(self.tmp / "site")
        self.remote = self.tmp / "remote.git"
        git(self.main, "init", "--bare", "-q", str(self.remote))
        git(self.main, "remote", "add", "origin", str(self.remote))
        git(self.main, "push", "-q", "-u", "origin", "main")
        self.wt = self.tmp / "branch"
        git(self.main, "worktree", "add", "-q", "-b", "codex/page", str(self.wt), "main")
        (self.main / "node_modules" / ".bin").mkdir(parents=True)
        self.store = self.tmp / "review"
        self.real_gate = reference_review.gate
        self.origin_patch = patch.object(site, "WEBSITE_REMOTE", re.compile(".*"))
        self.origin_patch.start()

    def tearDown(self):
        self.origin_patch.stop()
        self.tmp_obj.cleanup()

    def build(self, worktree, destination, env):
        self.assertEqual(worktree, self.wt)
        self.assertTrue(str(self.main / "node_modules" / ".bin") in env["PATH"])
        return 0, ""

    def gate(self, paths, client, *, repo_root, note_keys):
        return self.real_gate(paths, client, repo_root=repo_root,
                              note_keys=note_keys, store=self.store)

    def check(self):
        with patch.object(site.reference_review, "gate", side_effect=self.gate):
            return site.check(self.wt, build_command=self.build,
                              repo_root=self.tmp, client_factory=Registry)

    def test_page_selection(self):
        write_and_commit(self.main, {"content/old.md": "old", "content/pure.md": "pure",
                                     "content/deleted.md": "delete"}, "base pages")
        git(self.main, "push", "-q", "origin", "main")
        git(self.wt, "merge", "--ff-only", "main")
        git(self.wt, "mv", "content/pure.md", "content/renamed.md")
        git(self.wt, "rm", "content/deleted.md")
        write_and_commit(self.wt, {"content/new.md": "new", "content/caps.MD": "caps",
                                   "content/old.md": "updated", "docs/out.md": "out",
                                   "content/image.png": "png"}, "pages")
        self.assertEqual(site.changed_pages(self.wt),
                         ["content/caps.MD", "content/new.md", "content/old.md"])
        self.assertEqual(len(reference_checker.extract("---\ntitle: A Registered Paper Title\ndoi: 10.1234/paper\n---\n")), 1)

    def test_repo_and_tree_failures(self):
        with self.assertRaisesRegex(site.LandingError, "Repo.*non-main"):
            site.check(self.main, build_command=self.build)
        (self.wt / "untracked.txt").write_text("x")
        with self.assertRaisesRegex(site.LandingError, "Repo.*dirty"):
            self.check()
        (self.wt / "untracked.txt").unlink()
        (self.wt / "core/a.py").write_text("changed")
        with self.assertRaisesRegex(site.LandingError, "Repo.*dirty"):
            self.check()

    def test_fast_forward_and_overlap(self):
        write_and_commit(self.main, {"content/conflict.md": "base"}, "ahead")
        git(self.main, "push", "-q", "origin", "main")
        with self.assertRaisesRegex(site.LandingError, "Fast-forward"):
            self.check()
        git(self.wt, "merge", "--ff-only", "main")
        write_and_commit(self.wt, {"content/shared.md": "ours"}, "ours")
        other = self.tmp / "other"
        git(self.main, "worktree", "add", "-q", "-b", "codex/other", str(other), "main")
        write_and_commit(other, {"content/shared.md": "other"}, "other")
        with self.assertRaisesRegex(site.LandingError, "Overlaps.*codex/other.*content/shared.md"):
            self.check()

    def test_build_failures(self):
        with patch.object(site, "_build", side_effect=site.LandingError("Hugo build: failed")):
            with self.assertRaisesRegex(site.LandingError, "Hugo build"):
                self.check()
        (self.main / "node_modules" / ".bin").rmdir()
        with self.assertRaisesRegex(site.LandingError, "Hugo build.*npm install"):
            self.check()

    def test_gate_tiers_and_ledger_key(self):
        pages = [
            ("---\ntitle: Bad Example\ndoi: 10.5555/123456\n---\n", "NOT_FOUND"),
            ("# References\n- 10.1234/paper\n", "UNCHECKED"),
            ("---\ntitle: A Registered Paper Title\ndoi: 10.1234/paper\n---\n", "CONFIRMED"),
            ("---\ntitle: An Invented Paper Title\ndoi: 10.1234/paper\n---\n", "TITLE_WRONG"),
        ]
        for text, tier in pages:
            row = reference_checker.check_note(text, Registry())[0]
            self.assertEqual(row["tier"], tier)
        write_and_commit(self.wt, {"content/test.md": pages[0][0]}, "bad page")
        with self.assertRaisesRegex(site.LandingError, "Citation gate.*defects=1"):
            self.check()
        defects = reference_review.load_defects(self.store)
        self.assertEqual(defects[0]["note"],
                         "ai-sandbox/personal-website/AaronScherf.github.io/content/test.md")
        self.assertNotEqual(defects[0]["note"], "ai-sandbox/research/content/test.md")

    def test_strict_gate_accepts_front_matter_title_and_rejects_untitled_body(self):
        write_and_commit(self.wt, {"content/test.md":
                         "---\ntitle: A Registered Paper Title\ndoi: 10.1234/paper\n---\n"}, "page")
        self.assertEqual(self.check()["pages"], ["content/test.md"])
        write_and_commit(self.wt, {"content/test.md": "# References\n- 10.1234/paper\n"}, "untitled")
        with self.assertRaisesRegex(site.LandingError, "Citation gate.*defects=1"):
            self.check()
        self.assertEqual(reference_review.load_defects(self.store)[0]["tier"], "TITLE_MISSING")

    def test_reference_review_cli_path_uses_stable_website_key(self):
        page = self.wt / "content" / "test.md"
        page.parent.mkdir(parents=True)
        page.write_text("# Page\n")
        git(self.wt, "remote", "set-url", "origin",
            "https://github.com/AaronScherf/AaronScherf.github.io.git")
        _, key = reference_review._note_path(page, self.tmp)
        self.assertEqual(key, "ai-sandbox/personal-website/AaronScherf.github.io/content/test.md")

    def test_no_pages_and_land_with_untracked_main_file(self):
        write_and_commit(self.wt, {"docs/change.txt": "text"}, "docs")
        result = self.check()
        self.assertEqual(result["pages"], [])
        (self.main / "content" / "blog" / "drafts").mkdir(parents=True)
        (self.main / "content" / "blog" / "drafts" / "note.md").write_text("draft")
        with patch.object(site.reference_review, "gate", side_effect=self.gate):
            site.land(self.wt, result["change_id"], build_command=self.build,
                      repo_root=self.tmp, client_factory=Registry)
        self.assertEqual(git(self.main, "rev-parse", "HEAD"), git(self.wt, "rev-parse", "HEAD"))

    def test_land_refuses_unknown_and_stale_id(self):
        write_and_commit(self.wt, {"docs/change.txt": "one"}, "first")
        with self.assertRaisesRegex(site.LandingError, "no passing check"):
            site.land(self.wt, "unknown", build_command=self.build)
        cid = self.check()["change_id"]
        write_and_commit(self.wt, {"docs/change.txt": "two"}, "second")
        with self.assertRaisesRegex(site.LandingError, "change ID changed"):
            site.land(self.wt, cid, build_command=self.build)

    def test_land_refuses_main_tracked_overlap(self):
        write_and_commit(self.wt, {"core/a.py": "changed"}, "change")
        cid = self.check()["change_id"]
        (self.main / "core/a.py").write_text("local")
        with self.assertRaisesRegex(site.LandingError, "tracked changes"):
            site.land(self.wt, cid, build_command=self.build)

    def test_failed_push_reports_local_merge(self):
        write_and_commit(self.wt, {"docs/change.txt": "text"}, "docs")
        cid = self.check()["change_id"]
        git(self.main, "remote", "set-url", "--push", "origin", str(self.tmp / "missing.git"))
        with self.assertRaisesRegex(site.LandingError, "fast-forwarded locally but not pushed"):
            site.land(self.wt, cid, build_command=self.build)


if __name__ == "__main__":
    unittest.main()
