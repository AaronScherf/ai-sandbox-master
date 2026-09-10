import unittest

from resume_manager.validate import format_report, validate_tailored

_MASTER = {
    "work_experience": [
        {"id": "acme-1", "bullets": ["Grew revenue 30%"]},
        {"id": "globex-1", "bullets": ["Built reports"]},
    ],
}


class TestValidateTailored(unittest.TestCase):
    def test_matching_metric_is_not_flagged(self):
        tailoring_result = {"included_ids": ["acme-1"], "bullets_by_id": {"acme-1": ["Grew revenue 30% via new pricing"]}}
        self.assertEqual(validate_tailored(_MASTER, tailoring_result), [])

    def test_invented_metric_is_flagged(self):
        tailoring_result = {"included_ids": ["acme-1"], "bullets_by_id": {"acme-1": ["Grew revenue 75%"]}}
        problems = validate_tailored(_MASTER, tailoring_result)
        self.assertTrue(any("75%" in p for p in problems))

    def test_metric_is_checked_against_its_own_entry_only_not_the_whole_master(self):
        # "30%" belongs to acme-1's original bullets, not globex-1's --
        # globex-1's rewrite claiming it must still be flagged.
        tailoring_result = {"included_ids": ["globex-1"], "bullets_by_id": {"globex-1": ["Grew revenue 30%"]}}
        problems = validate_tailored(_MASTER, tailoring_result)
        self.assertTrue(any("30%" in p for p in problems))

    def test_unknown_included_id_is_flagged(self):
        tailoring_result = {"included_ids": ["nonexistent"], "bullets_by_id": {}}
        problems = validate_tailored(_MASTER, tailoring_result)
        self.assertTrue(any("nonexistent" in p for p in problems))

    def test_dropped_metric_is_flagged(self):
        # Real, confirmed case (2026-09-09): a rewrite compressed three
        # bullets into two and lost every one of their $ figures along the
        # way. validate.py's original design only checked for INVENTED
        # metrics; this checks the other direction too.
        tailoring_result = {"included_ids": ["acme-1"], "bullets_by_id": {"acme-1": ["Grew revenue via new pricing"]}}
        problems = validate_tailored(_MASTER, tailoring_result)
        self.assertTrue(any("dropped" in p and "30%" in p for p in problems))

    def test_metric_present_in_at_least_one_rewritten_bullet_is_not_flagged_as_dropped(self):
        master = {"work_experience": [{"id": "acme-1", "bullets": ["Grew revenue 30%", "Cut costs 10%"]}]}
        tailoring_result = {
            "included_ids": ["acme-1"],
            "bullets_by_id": {"acme-1": ["Grew revenue 30% via new pricing", "Cut costs 10% via automation"]},
        }
        self.assertEqual(validate_tailored(master, tailoring_result), [])


class TestFormatReport(unittest.TestCase):
    def test_empty_problems_reports_clean(self):
        self.assertIn("no discrepancies", format_report([]))

    def test_problems_are_listed(self):
        report = format_report(["issue one", "issue two"])
        self.assertIn("issue one", report)
        self.assertIn("issue two", report)
