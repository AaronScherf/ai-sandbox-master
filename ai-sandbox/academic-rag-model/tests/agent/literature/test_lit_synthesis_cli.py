import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from agent.literature.cli import main
from core.agent_tasks.work import load_run
from lit_helpers import fill_card, write_vocab_dir
from synth_helpers import _answer, build, three_papers


def run_cli(root, vocab_dir, *args):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = main(["--index-root", root, "--vocab-dir", vocab_dir, *args])
    return code, out.getvalue()


class TestSynthesisCli(unittest.TestCase):
    def test_define_annotate_synthesize_render_end_to_end(self):
        with tempfile.TemporaryDirectory() as root:
            build(root, three_papers())
            vocab_dir = Path(root) / "vocab"
            vocab_dir.mkdir()
            write_vocab_dir(vocab_dir)
            v = str(vocab_dir)
            code, out = run_cli(root, v, "cluster", "define", "demo", "--where", "sector=social protection")
            self.assertEqual(code, 0)
            self.assertIn("2 papers", out)
            self.assertEqual(run_cli(root, v, "cluster", "define", "demo", "--where", "sector=nope")[0], 2)

            self.assertEqual(run_cli(root, v, "annotate", "demo", "--run-id", "ann1")[0], 0)
            run = load_run(Path(root) / ".agent_work", "ann1")
            for entry in run.tasks:
                fill_card(run.card_path(entry["id"]), _answer())
            code, out = run_cli(root, v, "submit", "ann1")
            self.assertEqual(code, 0)
            self.assertEqual(run_cli(root, v, "render", "demo")[0], 2)  # no synthesis yet

            self.assertEqual(run_cli(root, v, "synthesize", "demo", "--run-id", "syn1")[0], 0)
            run = load_run(Path(root) / ".agent_work", "syn1")
            fill_card(run.card_path("synth-final"), {"sections": [{"heading": "Findings", "paragraphs": [
                {"text": "Transfers raised food consumption by 12% in treated districts.", "cites": ["P1.R1", "P2.R1"]}]}]})
            run_cli(root, v, "submit", "syn1")
            code, out = run_cli(root, v, "render", "demo")
            self.assertEqual(code, 0)
            self.assertTrue((Path(root) / "literature_reviews" / "demo" / "review.md").is_file())


if __name__ == "__main__":
    unittest.main()
