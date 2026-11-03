import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from git_fixture import git, make_repo, write_and_commit
from tools import guard_binaries as g

PROJECT = Path(__file__).resolve().parents[2]
HUB = "ai-sandbox/academic-hub/"


def rules(entries, allow=()):
    return [(v.rule, v.path) for v in g.check_entries(entries, [g._glob_to_regex(a) for a in allow])]


class CheckEntriesTests(unittest.TestCase):
    def test_hub_pdf_fails_r1_any_case(self):
        self.assertEqual(rules([(HUB + "x/a.pdf", 10)]), [("R1", HUB + "x/a.pdf")])
        self.assertEqual(rules([(HUB + "x/A.PDF", 10)]), [("R1", HUB + "x/A.PDF")])

    def test_each_hub_extension_blocked(self):
        for ext in ("pdf", "svg", "png", "jpg", "jpeg", "epub", "docx", "pptx"):
            self.assertEqual(len(rules([(f"{HUB}c/f.{ext}", 1)])), 1, ext)

    def test_pdf_outside_hub_passes_r1_but_fails_r2_when_big(self):
        self.assertEqual(rules([("research/p/x.pdf", 10)]), [])
        self.assertEqual(rules([("research/p/x.pdf", 2_000_000)]), [("R2", "research/p/x.pdf")])

    def test_obsidian_styles_exempt_from_r1(self):
        self.assertEqual(rules([(HUB + "obsidian_styles/icon.svg", 10)]), [])

    def test_size_boundary(self):
        self.assertEqual(rules([("a.txt", 1_000_000)]), [])
        self.assertEqual(rules([("a.txt", 1_000_001)]), [("R2", "a.txt")])

    def test_r3_textbook_text_and_bak(self):
        t = HUB + "academic_resources/micro/textbooks/"
        self.assertEqual(rules([(t + "book.md", 1)]), [("R3", t + "book.md")])
        self.assertEqual(rules([(t + "processed_outputs/B/_metadata.json", 1)]), [])
        self.assertEqual(rules([(t + "processed_outputs/B/B.rag.md", 1)]),
                         [("R3", t + "processed_outputs/B/B.rag.md")])
        self.assertEqual(rules([("x/y.rag.md.bak", 1)]), [("R3", "x/y.rag.md.bak")])
        self.assertEqual(rules([("textbooks-and-papers/a.txt", 1)]),
                         [("R3", "textbooks-and-papers/a.txt")])

    def test_allowlist_globs(self):
        self.assertEqual(rules([(HUB + ".index/m.json", 5_000_000)], [HUB + ".index/*.json"]), [])
        self.assertEqual(rules([(HUB + ".index/sub/m.json", 5_000_000)], [HUB + ".index/*.json"]),
                         [("R2", HUB + ".index/sub/m.json")])
        self.assertEqual(rules([("a/b/c/main.js", 5_000_000)], ["a/**/main.js"]), [])

    def test_allowlist_requires_reason(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "allow.txt"
            p.write_text("# c\nfoo/*.pdf\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                g.load_allowlist(p)
            p.write_text("# c\nfoo/*.pdf  # why\n", encoding="utf-8")
            self.assertEqual(len(g.load_allowlist(p)), 1)

    def test_overbroad_globs_rejected(self):
        for glob in ("**", "*", "**/*.pdf", "ai-sandbox/**", "ai-sandbox/academic-hub/**", "*/*.pdf"):
            with self.assertRaises(ValueError):
                g.parse_allowlist(f"{glob}  # why\n")

    def test_shipped_allowlist_loads(self):
        patterns = g.load_allowlist()
        self.assertTrue(any(p.match(HUB + ".index/microecon.json") for p in patterns))


class GitIntegrationTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = make_repo(Path(self._tmp.name) / "repo")
        write_and_commit(self.repo, {HUB + "academic_resources/c/old.pdf": "x"}, "tracked pdf")

    def tearDown(self):
        self._tmp.cleanup()

    def stage(self, rel, text="data"):
        f = self.repo / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(text, encoding="utf-8")
        git(self.repo, "add", "-f", rel)

    def test_staged_added_pdf_fails(self):
        self.stage(HUB + "academic_resources/c/new.pdf")
        self.assertEqual([v.rule for v in g.check_staged(self.repo)], ["R1"])

    def test_staged_deletion_passes(self):
        git(self.repo, "rm", "-q", "--cached", HUB + "academic_resources/c/old.pdf")
        self.assertEqual(g.check_staged(self.repo), [])

    def test_staged_modification_of_tracked_pdf_fails(self):
        self.stage(HUB + "academic_resources/c/old.pdf", "changed")
        self.assertEqual([v.rule for v in g.check_staged(self.repo)], ["R1"])

    def test_staged_rename_checked_by_new_path(self):
        git(self.repo, "mv", HUB + "academic_resources/c/old.pdf", HUB + "academic_resources/c/moved.pdf")
        self.assertEqual([v.path for v in g.check_staged(self.repo)],
                         [HUB + "academic_resources/c/moved.pdf"])

    def test_range_flags_branch_additions_only(self):
        git(self.repo, "checkout", "-q", "-b", "claude/t")
        write_and_commit(self.repo, {HUB + "course/f.svg": "<svg/>", "ok.py": "x=1\n"}, "add")
        self.assertEqual([v.path for v in g.check_range(self.repo, "main")], [HUB + "course/f.svg"])

    def test_range_flags_file_added_then_deleted_in_branch(self):
        git(self.repo, "checkout", "-q", "-b", "claude/t")
        write_and_commit(self.repo, {HUB + "course/f.svg": "<svg/>"}, "add")
        git(self.repo, "rm", "-q", HUB + "course/f.svg")
        git(self.repo, "commit", "-q", "-m", "remove")
        self.assertEqual([v.path for v in g.check_range(self.repo, "main")], [HUB + "course/f.svg"])

    def test_range_checks_merge_commits(self):
        git(self.repo, "checkout", "-q", "-b", "claude/side")
        write_and_commit(self.repo, {HUB + "course/f.svg": "<svg/>"}, "side")
        git(self.repo, "checkout", "-q", "main")
        git(self.repo, "checkout", "-q", "-b", "claude/t")
        write_and_commit(self.repo, {"ok.py": "x=1\n"}, "own")
        git(self.repo, "merge", "-q", "--no-ff", "-m", "merge side", "claude/side")
        self.assertEqual([v.path for v in g.check_range(self.repo, "main")], [HUB + "course/f.svg"])

    def test_branch_cannot_allowlist_itself(self):
        git(self.repo, "checkout", "-q", "-b", "claude/t")
        write_and_commit(self.repo, {
            g.ALLOWLIST_REPO_PATH: HUB + "course/*.svg  # trust me\n",
            HUB + "course/f.svg": "<svg/>"}, "self-exempt")
        self.assertEqual([v.rule for v in g.check_range(self.repo, "main")], ["R1"])

    def test_allowlist_on_base_is_honoured(self):
        write_and_commit(self.repo, {g.ALLOWLIST_REPO_PATH: HUB + "course/*.svg  # approved\n"}, "allow")
        git(self.repo, "checkout", "-q", "-b", "claude/t")
        write_and_commit(self.repo, {HUB + "course/f.svg": "<svg/>"}, "add")
        self.assertEqual(g.check_range(self.repo, "main"), [])

    def test_hook_script_exits_nonzero_for_staged_hub_pdf(self):
        # Run the guard CLI directly (not through git) as the hook does.
        self.stage(HUB + "academic_resources/c/new.pdf")
        env_path = str(PROJECT)
        proc = subprocess.run(
            [sys.executable, "-c",
             f"import sys; sys.path.insert(0, {env_path!r}); "
             "from tools.guard_binaries import main; raise SystemExit(main(['--staged']))"],
            cwd=self.repo, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("R1:", proc.stderr)


if __name__ == "__main__":
    unittest.main()
