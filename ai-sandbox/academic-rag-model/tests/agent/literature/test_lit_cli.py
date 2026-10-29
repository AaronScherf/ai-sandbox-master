import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path

import yaml

from agent.literature import cli
from lit_helpers import good, fill_card, make_index, write_vocab_dir

FID = "0123456789abcdef"


def _run(argv, **kw):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = cli.main(argv, **kw)
    return code, out.getvalue()


class Env:
    def __init__(self, root: str):
        self.root = root
        self.vocabs = str(Path(root) / "vocabs")
        Path(self.vocabs).mkdir()
        write_vocab_dir(self.vocabs)
        make_index(root)
        make_index(root, file_id="fedcba9876543210", card_extra={"needs_indexing": True})

    def args(self, *more):
        return ["--index-root", self.root, "--vocab-dir", self.vocabs, *more]

    def card(self, run_id, name):
        return Path(self.root) / ".agent_work" / run_id / "cards" / f"{name}.md"


class TestCollect(unittest.TestCase):
    def test_collect_writes_a_card_per_eligible_paper_and_reports_skips(self):
        with tempfile.TemporaryDirectory() as root:
            env = Env(root)
            code, out = _run(env.args("collect", "--run-id", "r1"))
            self.assertEqual(code, 0)
            self.assertTrue(env.card("r1", f"extract-{FID}").is_file())
            self.assertIn("fedcba9876543210", out)
            self.assertIn("needs indexing", out)

    def test_collect_again_with_the_same_run_id_is_reported_not_a_traceback(self):
        with tempfile.TemporaryDirectory() as root:
            env = Env(root)
            _run(env.args("collect", "--run-id", "r1"))
            code, out = _run(env.args("collect", "--run-id", "r1", "--redo"))
            self.assertEqual(code, 2)
            self.assertIn("r1", out)

    def test_double_also_stages_a_pass_b_card(self):
        with tempfile.TemporaryDirectory() as root:
            env = Env(root)
            _run(env.args("collect", "--run-id", "r1", "--double"))
            self.assertTrue(env.card("r1", f"extract-{FID}-b").is_file())

    def test_unknown_file_id_is_reported(self):
        with tempfile.TemporaryDirectory() as root:
            env = Env(root)
            code, out = _run(env.args("collect", "--file-id", "deadbeefdeadbeef"))
            self.assertIn("deadbeefdeadbeef", out)

    def test_a_work_root_inside_the_records_folder_is_refused(self):
        with tempfile.TemporaryDirectory() as root:
            env = Env(root)
            bad = str(Path(root) / ".index" / "study_records" / "work")
            code, out = _run(env.args("--work-root", bad, "collect", "--run-id", "r1"))
            self.assertEqual(code, 2)
            self.assertIn("inside", out)


class TestSubmit(unittest.TestCase):
    def test_a_filled_card_becomes_a_record_and_a_bad_one_bounces_with_its_reason(self):
        with tempfile.TemporaryDirectory() as root:
            env = Env(root)
            make_index(root, file_id="1111111111111111", title="A different paper")
            _run(env.args("collect", "--run-id", "r1"))
            fill_card(env.card("r1", f"extract-{FID}"), good())
            bad = good()
            bad["core"]["outcome"][0]["quote"] = "hunger fell by forty percent everywhere"
            fill_card(env.card("r1", "extract-1111111111111111"), bad)
            code, out = _run(env.args("submit", "r1"))
            self.assertEqual(code, 0)
            self.assertTrue((Path(root) / ".index" / "study_records" / f"{FID}.json").is_file())
            self.assertFalse((Path(root) / ".index" / "study_records" / "1111111111111111.json").exists())
            self.assertIn("core.outcome[0].quote", out)

    def test_an_unfilled_run_reports_untouched(self):
        with tempfile.TemporaryDirectory() as root:
            env = Env(root)
            _run(env.args("collect", "--run-id", "r1"))
            code, out = _run(env.args("submit", "r1"))
            self.assertIn("untouched", out)

    def test_an_unknown_run_is_a_clear_error(self):
        with tempfile.TemporaryDirectory() as root:
            env = Env(root)
            code, out = _run(env.args("submit", "nope"))
            self.assertEqual(code, 2)
            self.assertIn("nope", out)


class TestBootstrapAndStatus(unittest.TestCase):
    def test_bootstrap_names_the_run_and_the_result_block(self):
        with tempfile.TemporaryDirectory() as root:
            env = Env(root)
            code, out = _run(env.args("bootstrap", "r7"))
            self.assertIn("r7", out)
            self.assertIn("## Result", out)
            self.assertIn("submit r7", out)

    def test_status_counts_papers_records_and_proposals(self):
        with tempfile.TemporaryDirectory() as root:
            env = Env(root)
            _, before = _run(env.args("status"))
            self.assertIn("eligible papers: 1", before)
            self.assertIn("records: 0", before)
            _run(env.args("collect", "--run-id", "r1"))
            fill_card(env.card("r1", f"extract-{FID}"), good())
            _run(env.args("submit", "r1"))
            _, after = _run(env.args("status"))
            self.assertIn("records: 1", after)


    def test_exclude_hides_a_paper_from_tiers_but_status_still_counts_its_record(self):
        with tempfile.TemporaryDirectory() as root:
            env = Env(root)
            _run(env.args("collect", "--run-id", "r1"))
            fill_card(env.card("r1", f"extract-{FID}"), good())
            _run(env.args("submit", "r1"))
            _, out = _run(env.args("exclude", FID))
            self.assertIn("excluded: 1", out)
            _, status = _run(env.args("status"))
            self.assertIn("records: 1", status)
            self.assertIn("excluded papers: 1", status)
            self.assertIn("open vocabulary proposals: 0", status)
            _, collected = _run(env.args("collect", "--run-id", "r2"))
            self.assertNotIn("collected 1", collected)
            _, undone = _run(env.args("exclude", FID, "--undo"))
            self.assertIn("excluded: 0", undone)


class TestBackfillYears(unittest.TestCase):
    def test_reports_outcomes_and_a_total(self):
        with tempfile.TemporaryDirectory() as root:
            env = Env(root)
            real = cli.backfill_years
            cli.backfill_years = lambda index_root, mailto, **kw: {FID: "backfilled"}
            try:
                code, out = _run(env.args("backfill-years", "--mailto", "me@example.com"))
            finally:
                cli.backfill_years = real
            self.assertEqual(code, 0)
            self.assertIn(f"{FID}\tbackfilled", out)
            self.assertIn("1 of 1 backfilled", out)

    def test_no_mailto_is_a_clear_error(self):
        with tempfile.TemporaryDirectory() as root:
            env = Env(root)
            old = os.environ.pop("OPENALEX_CONTACT_EMAIL", None)
            try:
                code, out = _run(env.args("backfill-years"))
            finally:
                if old is not None:
                    os.environ["OPENALEX_CONTACT_EMAIL"] = old
            self.assertEqual(code, 2)
            self.assertIn("mailto", out)


class TestApi(unittest.TestCase):
    def test_over_budget_sends_nothing(self):
        calls = []
        with tempfile.TemporaryDirectory() as root:
            env = Env(root)
            _run(env.args("collect", "--run-id", "r1"))
            code, out = _run(env.args("api", "r1", "--approve-cost", "0.0000001"), complete=lambda p: calls.append(p) or "")
        self.assertEqual(code, 2)
        self.assertEqual(calls, [])
        self.assertIn("exceeds the approved", out)

    def test_an_approved_run_applies_the_reply(self):
        with tempfile.TemporaryDirectory() as root:
            env = Env(root)
            _run(env.args("collect", "--run-id", "r1"))
            reply = "```yaml\n" + yaml.safe_dump(good(), sort_keys=False, allow_unicode=True) + "```"
            code, out = _run(env.args("api", "r1", "--approve-cost", "5"), complete=lambda p: reply)
            self.assertEqual(code, 0)
            self.assertTrue((Path(root) / ".index" / "study_records" / f"{FID}.json").is_file())


class TestEval(unittest.TestCase):
    def _gold(self, root, papers):
        path = Path(root) / "gold_set.yaml"
        path.write_text(yaml.safe_dump({"version": 1, "papers": papers}), encoding="utf-8")
        return str(path)

    def test_eval_scores_a_submitted_record_and_reports_aggregates_only(self):
        with tempfile.TemporaryDirectory() as root:
            env = Env(root)
            _run(env.args("collect", "--run-id", "r1"))
            fill_card(env.card("r1", f"extract-{FID}"), good())
            _run(env.args("submit", "r1"))
            gold = self._gold(root, [{"file_id": FID, "expect": {"countries": ["SO"], "study_design": ["study_design.panel"]}}])
            code, out = _run(env.args("eval", "--gold", gold))
            report = json.loads(out)
        self.assertEqual(code, 0)
        self.assertEqual((report["facet_precision"], report["facet_recall"]), (1.0, 1.0))
        self.assertEqual(report["papers_missing_a_record"], [])
        self.assertEqual(report["bounce_rate"], 0.0)
        self.assertNotIn("Somalia", out)

    def test_a_gold_paper_without_a_record_counts_against_recall(self):
        with tempfile.TemporaryDirectory() as root:
            env = Env(root)
            gold = self._gold(root, [{"file_id": FID, "expect": {"countries": ["SO"]}}])
            code, out = _run(env.args("eval", "--gold", gold))
            report = json.loads(out)
        self.assertEqual(code, 0)
        self.assertEqual(report["facet_recall"], 0.0)
        self.assertEqual(report["papers_missing_a_record"], [FID])

    def test_a_missing_gold_file_is_reported_not_a_traceback(self):
        with tempfile.TemporaryDirectory() as root:
            env = Env(root)
            code, out = _run(env.args("eval", "--gold", str(Path(root) / "nope.yaml")))
        self.assertEqual(code, 2)
        self.assertIn("nope.yaml", out)


class TestRefineGrain(unittest.TestCase):
    def _collected(self, root):
        env = Env(root)
        _run(env.args("collect", "--run-id", "c1", "--double"))
        fill_card(env.card("c1", f"extract-{FID}"), good())
        fill_card(env.card("c1", f"extract-{FID}-b"), good())
        _run(env.args("submit", "c1"))
        return env

    def test_stages_a_card_for_each_pass(self):
        with tempfile.TemporaryDirectory() as root:
            env = self._collected(root)
            code, out = _run(env.args("refine-grain", "--run-id", "r1"))
            self.assertEqual(code, 0)
            self.assertTrue(env.card("r1", f"refine-{FID}").is_file())
            self.assertTrue(env.card("r1", f"refine-{FID}-b").is_file())

    def test_submit_merges_the_filled_card_without_disturbing_other_fields(self):
        with tempfile.TemporaryDirectory() as root:
            env = self._collected(root)
            before = json.loads((Path(root) / ".index" / "study_records" / f"{FID}.json").read_text(encoding="utf-8"))
            _run(env.args("refine-grain", "--run-id", "r1"))
            fill_card(env.card("r1", f"refine-{FID}"), {"intervention": [], "outcome": []})
            fill_card(env.card("r1", f"refine-{FID}-b"), {"intervention": [], "outcome": []})
            code, _ = _run(env.args("submit", "r1"))
            after = json.loads((Path(root) / ".index" / "study_records" / f"{FID}.json").read_text(encoding="utf-8"))
        self.assertEqual(code, 0)
        self.assertEqual(after["core"]["intervention"], [])
        self.assertEqual(after["core"]["study_design"], before["core"]["study_design"])
        self.assertEqual(after["core"]["data_sources"], before["core"]["data_sources"])

    def test_file_id_filters_to_one_paper(self):
        with tempfile.TemporaryDirectory() as root:
            env = self._collected(root)
            make_index(root, file_id="1111111111111111", title="A different paper")
            _run(env.args("collect", "--run-id", "c2", "--file-id", "1111111111111111"))
            fill_card(env.card("c2", "extract-1111111111111111"), good())
            _run(env.args("submit", "c2"))
            code, out = _run(env.args("refine-grain", "--run-id", "r1", "--file-id", FID))
            self.assertEqual(code, 0)
            self.assertTrue(env.card("r1", f"refine-{FID}").is_file())
            self.assertFalse(env.card("r1", "refine-1111111111111111").is_file())

    def test_the_scoped_listing_reaches_the_card_through_real_vocab_files_on_disk(self):
        from lit_helpers import VOCABS, write_vocab_dir
        from test_lit_refine_grain import _hierarchical_vocabs

        with tempfile.TemporaryDirectory() as root:
            vocab_dir = Path(root) / "vocabs"
            vocab_dir.mkdir()
            # good()'s other facets (study_design, data_sources) need VOCABS' flat terms for those vocabularies;
            # only intervention/outcome/sector are overridden with the hierarchical fixture under test here.
            write_vocab_dir(vocab_dir, {**VOCABS, **_hierarchical_vocabs()})
            make_index(root)
            result = good()
            result["core"]["intervention"] = [{"value": "crop diversification",
                                                "vocab_id": "intervention.crop_diversification",
                                                "quote": "We study cash transfers in rural Somalia", "locator": 1}]
            result["core"]["outcome"] = [{"value": "crop production", "vocab_id": "outcome.crop_production",
                                           "quote": "raised household food consumption by twelve percent", "locator": 3}]
            argv_base = ["--index-root", root, "--vocab-dir", str(vocab_dir)]
            _run([*argv_base, "collect", "--run-id", "c1"])
            fill_card(Path(root) / ".agent_work" / "c1" / "cards" / f"extract-{FID}.md", result)
            _run([*argv_base, "submit", "c1"])
            _run([*argv_base, "refine-grain", "--run-id", "r1"])
            card_text = (Path(root) / ".agent_work" / "r1" / "cards" / f"refine-{FID}.md").read_text(encoding="utf-8")
        # the scoped listing must show the sibling child term, not just the root the paper already had
        self.assertIn("intervention.climate_adaption_mitigation_strategies", card_text)
        self.assertNotIn("intervention.land_titling_reform", card_text)


if __name__ == "__main__":
    unittest.main()
