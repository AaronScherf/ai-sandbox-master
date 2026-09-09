import unittest

from resume_manager.validate import format_report, validate_tailored

_MASTER = """## Experience

### Acme Corp — Engineer (2020 – Present)
- Grew revenue 30%.

### Old Co — Analyst (2015 – 2018)
- Built reports.
"""


class TestValidateTailored(unittest.TestCase):
    def test_matching_entry_and_metric_not_flagged(self):
        tailored = "## Experience\n### Acme Corp — Engineer (2020 – Present)\n- Grew revenue 30%.\n"
        self.assertEqual(validate_tailored(_MASTER, tailored), [])

    def test_dropping_a_master_entry_is_not_flagged(self):
        # "Old Co" is entirely absent from `tailored` -- expected
        # behavior for a shorter, targeted resume (spec §5).
        tailored = "## Experience\n### Acme Corp — Engineer (2020 – Present)\n- Grew revenue 30%.\n"
        self.assertEqual(validate_tailored(_MASTER, tailored), [])

    def test_fabricated_entry_is_flagged(self):
        tailored = "## Experience\n### New Corp — Director (2022 – Present)\n- Led team.\n"
        problems = validate_tailored(_MASTER, tailored)
        self.assertTrue(any("New Corp" in p for p in problems))

    def test_invented_metric_is_flagged(self):
        tailored = "## Experience\n### Acme Corp — Engineer (2020 – Present)\n- Grew revenue 75%.\n"
        problems = validate_tailored(_MASTER, tailored)
        self.assertTrue(any("75%" in p for p in problems))


class TestFormatReport(unittest.TestCase):
    def test_empty_problems_reports_clean(self):
        self.assertIn("no discrepancies", format_report([]))

    def test_problems_are_listed(self):
        report = format_report(["issue one", "issue two"])
        self.assertIn("issue one", report)
        self.assertIn("issue two", report)
