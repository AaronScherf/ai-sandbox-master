import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from agent.literature import cli
from agent.literature.proposals import Proposals
from agent.literature.vocab import load_vocabulary
from lit_helpers import write_vocab_dir


def _setup(d):
    vocab_dir = Path(d) / "vocabs"
    vocab_dir.mkdir()
    write_vocab_dir(vocab_dir)
    props = Proposals(Path(d) / "records")
    props.add("0123456789abcdef", "study_design", "synthetic control", "a quote long enough", 3)
    return vocab_dir, props


class TestAccept(unittest.TestCase):
    def test_accept_appends_a_valid_local_term_and_bumps_the_version(self):
        with tempfile.TemporaryDirectory() as d:
            vocab_dir, props = _setup(d)
            before = load_vocabulary(vocab_dir / "study_design.yaml")
            props.accept("P0001", "study_design.synthetic_control", "Synthetic control",
                         definition="Weighted comparison units.", vocab_dir=vocab_dir)
            after = load_vocabulary(vocab_dir / "study_design.yaml")
            self.assertEqual(after.version, before.version + 1)
            self.assertEqual(after.provenance, before.provenance)
            self.assertEqual(set(after.terms) - set(before.terms), {"study_design.synthetic_control"})
            self.assertEqual(after.terms["study_design.synthetic_control"].source, "local")
            self.assertEqual(after.find("synthetic control").id, "study_design.synthetic_control")
            self.assertEqual(props.all()[0]["status"], "accepted")
            self.assertEqual(props.all()[0]["term_id"], "study_design.synthetic_control")

    def test_a_bad_term_changes_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            vocab_dir, props = _setup(d)
            text = (vocab_dir / "study_design.yaml").read_text(encoding="utf-8")
            for bad in ("outcome.wrong_prefix", "study_design.panel"):
                with self.subTest(bad=bad), self.assertRaises(ValueError):
                    props.accept("P0001", bad, "X", vocab_dir=vocab_dir)
            self.assertEqual((vocab_dir / "study_design.yaml").read_text(encoding="utf-8"), text)
            self.assertEqual(props.all()[0]["status"], "open")

    def test_unknown_or_decided_ids_raise(self):
        with tempfile.TemporaryDirectory() as d:
            vocab_dir, props = _setup(d)
            with self.assertRaises(ValueError):
                props.accept("P9999", "study_design.x", "X", vocab_dir=vocab_dir)
            props.reject("P0001", "not needed")
            with self.assertRaises(ValueError):
                props.accept("P0001", "study_design.x", "X", vocab_dir=vocab_dir)
            with self.assertRaises(ValueError):
                props.reject("P0001")


class TestRejectAndList(unittest.TestCase):
    def test_reject_records_the_reason_and_drops_it_from_open(self):
        with tempfile.TemporaryDirectory() as d:
            _, props = _setup(d)
            props.reject("P0001", "duplicate of panel")
            self.assertEqual(props.open(), [])
            self.assertEqual(props.all()[0]["reason"], "duplicate of panel")

    def test_rejected_keys_includes_only_rejected_proposals(self):
        with tempfile.TemporaryDirectory() as d:
            _, props = _setup(d)
            props.add("0123456789abcdef", "outcome", "too vague a topic", "a quote long enough", 1)
            props.reject("P0002", "triage: too vague")
            self.assertEqual(props.rejected_keys(), {("0123456789abcdef", "outcome", "too vague a topic")})
            # P0001 is still open, so it must not show up as rejected
            props.reject("P0001", "duplicate of panel")
            self.assertEqual(props.rejected_keys(),
                              {("0123456789abcdef", "outcome", "too vague a topic"),
                               ("0123456789abcdef", "study_design", "synthetic control")})

    def test_list_shows_open_proposals(self):
        with tempfile.TemporaryDirectory() as d:
            records = Path(d) / ".index" / "study_records"
            Proposals(records).add("0123456789abcdef", "study_design", "synthetic control", "a quote long enough", 3)
            (Path(d) / "vocabs").mkdir()
            write_vocab_dir(Path(d) / "vocabs")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = cli.main(["--index-root", d, "--vocab-dir", str(Path(d) / "vocabs"), "proposals", "list"])
        self.assertEqual(code, 0)
        for needle in ("P0001", "study_design", "synthetic control", "0123456789abcdef", "page 3"):
            self.assertIn(needle, out.getvalue())

    def test_listing_with_no_proposals_does_not_crash(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "vocabs").mkdir()
            write_vocab_dir(Path(d) / "vocabs")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = cli.main(["--index-root", d, "--vocab-dir", str(Path(d) / "vocabs"), "proposals", "list"])
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
