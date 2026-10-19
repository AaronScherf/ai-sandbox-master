import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from agent.literature import cli
from agent.literature.papers import Paper, drop_duplicate_titles
from lit_helpers import make_index, write_vocab_dir


def _p(fid, title):
    return Paper(fid, f"x/{fid}.md", title, {"file_id": fid, "title": title})


class TestDropDuplicates(unittest.TestCase):
    def test_one_copy_of_a_title_is_kept_and_the_rest_name_it(self):
        kept, skipped = drop_duplicate_titles([_p("b2", "Behavior Revealed in Phone Usage"),
                                               _p("a1", "behavior revealed in phone usage!"), _p("c3", "Other")], set())
        self.assertEqual([p.file_id for p in kept], ["a1", "c3"])
        self.assertIn("a1", skipped["b2"])

    def test_a_copy_that_already_has_a_record_is_the_one_kept(self):
        kept, skipped = drop_duplicate_titles([_p("a1", "Same Paper"), _p("b2", "Same Paper")], {"b2"})
        self.assertEqual([p.file_id for p in kept], ["b2"])
        self.assertIn("a1", skipped)

    def test_papers_without_a_title_are_never_treated_as_duplicates(self):
        kept, skipped = drop_duplicate_titles([_p("a1", ""), _p("b2", "")], set())
        self.assertEqual(len(kept), 2)
        self.assertEqual(skipped, {})


class TestCollectSkipsDuplicates(unittest.TestCase):
    def _run(self, argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cli.main(argv)
        return code, out.getvalue()

    def test_collect_skips_duplicate_titles_unless_told_not_to(self):
        with tempfile.TemporaryDirectory() as root:
            vocabs = str(Path(root) / "vocabs")
            Path(vocabs).mkdir()
            write_vocab_dir(vocabs)
            make_index(root, file_id="1111111111111111")
            make_index(root, file_id="2222222222222222")
            base = ["--index-root", root, "--vocab-dir", vocabs]
            code, out = self._run(base + ["collect", "--run-id", "r1"])
            self.assertIn("duplicate", out)
            cards = list((Path(root) / ".agent_work" / "r1" / "cards").glob("extract-*.md"))
            self.assertEqual(len(cards), 1)
            self._run(base + ["collect", "--run-id", "r2", "--include-duplicates"])
            self.assertEqual(len(list((Path(root) / ".agent_work" / "r2" / "cards").glob("extract-*.md"))), 2)


if __name__ == "__main__":
    unittest.main()
