import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from agent.literature import cli
from lit_helpers import fill_card, good, make_index, write_vocab_dir

FID = "0123456789abcdef"


def _run(argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = cli.main(argv)
    return code, out.getvalue()


class TestVerifyCli(unittest.TestCase):
    def test_verify_collect_then_submit_writes_the_verification(self):
        with tempfile.TemporaryDirectory() as root:
            vocabs = str(Path(root) / "vocabs")
            Path(vocabs).mkdir()
            write_vocab_dir(vocabs)
            make_index(root)
            base = ["--index-root", root, "--vocab-dir", vocabs]
            _run(base + ["collect", "--run-id", "x1", "--double"])
            b = good()
            b["core"]["intervention"][0]["vocab_id"] = "intervention.voucher"
            b["core"]["intervention"][0]["value"] = "vouchers"
            fill_card(Path(root) / ".agent_work" / "x1" / "cards" / f"extract-{FID}.md", good())
            fill_card(Path(root) / ".agent_work" / "x1" / "cards" / f"extract-{FID}-b.md", b)
            _run(base + ["submit", "x1"])
            code, out = _run(base + ["verify", "--run-id", "v1"])
            self.assertEqual(code, 0, out)
            card = Path(root) / ".agent_work" / "v1" / "cards" / f"verify-{FID}.md"
            self.assertTrue(card.is_file())
            fill_card(card, {"verdicts": [
                {"item": 1, "verdict": "unclear", "reason": "not settled"},
                {"item": 2, "verdict": "unclear", "reason": "not settled"}]})
            code, out = _run(base + ["submit", "v1"])
            self.assertIn("applied 1", out)
            rec = json.loads((Path(root) / ".index" / "study_records" / f"{FID}.json").read_text(encoding="utf-8"))
            self.assertEqual(len(rec["verification"]["items"]), 2)

    def test_silver_reports_counts_per_paper(self):
        with tempfile.TemporaryDirectory() as root:
            vocabs = str(Path(root) / "vocabs")
            Path(vocabs).mkdir()
            write_vocab_dir(vocabs)
            make_index(root)
            base = ["--index-root", root, "--vocab-dir", vocabs]
            _run(base + ["collect", "--run-id", "x1", "--double"])
            for name in (f"extract-{FID}", f"extract-{FID}-b"):
                fill_card(Path(root) / ".agent_work" / "x1" / "cards" / f"{name}.md", good())
            _run(base + ["submit", "x1"])
            code, out = _run(base + ["silver"])
        self.assertEqual(code, 0)
        self.assertIn(FID, out)
        self.assertIn("agreed", out)


if __name__ == "__main__":
    unittest.main()
