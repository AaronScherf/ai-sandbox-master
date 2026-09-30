import unittest

from resume_manager.validate import format_report, validate_tailored

_MASTER = {
    "work_experience": [
        {"id": "acme-1", "bullets": ["Grew revenue 30%"]},
        {"id": "globex-1", "bullets": ["Built reports"]},
    ],
}


def _tailored(entries):
    return {"work_experience": entries}


class TestValidateTailored(unittest.TestCase):
    def test_matching_metric_is_not_flagged(self):
        tailored = _tailored([{"id": "acme-1", "bullets": ["Grew revenue 30% via new pricing"]}])
        self.assertEqual(validate_tailored(_MASTER, tailored), [])

    def test_invented_metric_is_flagged(self):
        tailored = _tailored([{"id": "acme-1", "bullets": ["Grew revenue 75%"]}])
        problems = validate_tailored(_MASTER, tailored)
        self.assertTrue(any("75%" in p for p in problems))

    def test_metric_is_checked_against_its_own_entry_only_not_the_whole_master(self):
        # "30%" belongs to acme-1's original bullets, not globex-1's --
        # globex-1's rewrite claiming it must still be flagged.
        tailored = _tailored([{"id": "globex-1", "bullets": ["Grew revenue 30%"]}])
        problems = validate_tailored(_MASTER, tailored)
        self.assertTrue(any("30%" in p for p in problems))

    def test_dropped_metric_is_flagged(self):
        # Real, confirmed case (2026-09-09): a rewrite compressed three
        # bullets into two and lost every one of their $ figures along the
        # way. validate.py's original design only checked for INVENTED
        # metrics; this checks the other direction too.
        tailored = _tailored([{"id": "acme-1", "bullets": ["Grew revenue via new pricing"]}])
        problems = validate_tailored(_MASTER, tailored)
        self.assertTrue(any("dropped" in p and "30%" in p for p in problems))

    def test_metric_present_in_at_least_one_rewritten_bullet_is_not_flagged_as_dropped(self):
        master = {"work_experience": [{"id": "acme-1", "bullets": ["Grew revenue 30%", "Cut costs 10%"]}]}
        tailored = _tailored([{
            "id": "acme-1",
            "bullets": ["Grew revenue 30% via new pricing", "Cut costs 10% via automation"],
        }])
        self.assertEqual(validate_tailored(master, tailored), [])

    def test_repeated_bullet_opening_across_different_entries_is_flagged(self):
        # Real, confirmed case (2026-09-09): a real tailoring run's first
        # bullet for two different roles both opened with "Researches,
        # analyzes, consolidates, and presents information..." -- echoing
        # the job description's own repeated phrasing rather than varying
        # language across bullets. tailor.py already sends every entry in
        # one prompt/one call, so this isn't a missing-context problem.
        master = {"work_experience": [
            {"id": "acme-1", "bullets": ["Did thing one"]},
            {"id": "globex-1", "bullets": ["Did thing two"]},
        ]}
        tailored = _tailored([
            {"id": "acme-1", "bullets": ["Researches, analyzes, consolidates, and presents information on topic A."]},
            {"id": "globex-1", "bullets": ["Researches, analyzes, consolidates, and presents information on topic B."]},
        ])
        problems = validate_tailored(master, tailored)
        self.assertTrue(any("repeated" in p.lower() and "opening" in p.lower() for p in problems))

    def test_repeated_opening_within_the_same_entry_is_also_flagged(self):
        master = {"work_experience": [{"id": "acme-1", "bullets": ["Did thing one", "Did thing two"]}]}
        tailored = _tailored([{"id": "acme-1", "bullets": [
            "Led the design and development of program A for the region.",
            "Led the design and development of program B for the region.",
        ]}])
        problems = validate_tailored(master, tailored)
        self.assertTrue(any("repeated" in p.lower() and "opening" in p.lower() for p in problems))

    def test_short_generic_shared_start_is_not_flagged(self):
        # Two bullets both starting with a common short action verb
        # shouldn't be flagged as "repetitive" -- only a long, specific
        # shared opening phrase is a real signal.
        master = {"work_experience": [{"id": "acme-1", "bullets": ["Did thing one", "Did thing two"]}]}
        tailored = _tailored([{"id": "acme-1", "bullets": [
            "Led the design of a new evaluation framework for the region.",
            "Led a cross-functional team of six analysts on a separate initiative.",
        ]}])
        problems = validate_tailored(master, tailored)
        self.assertFalse(any("repeated" in p.lower() and "opening" in p.lower() for p in problems))

    def test_distinct_openings_are_not_flagged(self):
        master = {"work_experience": [{"id": "acme-1", "bullets": ["Did thing one", "Did thing two"]}]}
        tailored = _tailored([{"id": "acme-1", "bullets": [
            "Led the design and development of program A for the region.",
            "Coordinated implementation of program B across three countries.",
        ]}])
        problems = validate_tailored(master, tailored)
        self.assertFalse(any("repeated" in p.lower() and "opening" in p.lower() for p in problems))

    def test_entry_with_no_matching_master_source_does_not_crash(self):
        # Defense in depth: apply_tailoring should never produce an entry
        # whose id isn't in the master, but validate_tailored shouldn't
        # crash even if it somehow did -- just nothing to compare against.
        tailored = _tailored([{"id": "nonexistent", "bullets": ["Some bullet"]}])
        self.assertEqual(validate_tailored(_MASTER, tailored), [])

    def test_tagged_fact_missing_from_final_entry_is_reported(self):
        facts = [{
            "entry_id": "acme-1", "fact": "Managed asset inventories across 16+ projects.",
            "required_concepts": [["inventory", "inventories"], ["asset database", "asset tracking"],
                                  ["16+ projects", "more than 16 projects"]],
        }]
        tailored = _tailored([{"id": "acme-1", "bullets": ["Grew revenue 30%"]}])
        problems = validate_tailored(_MASTER, tailored, user_facts=facts)
        self.assertTrue(any("[user fact coverage]" in p and "asset database" in p for p in problems))

    def test_tagged_fact_paraphrase_with_all_required_concepts_is_covered(self):
        facts = [{
            "entry_id": "acme-1", "fact": "Managed asset inventories across 16+ projects.",
            "required_concepts": [["inventory", "inventories"], ["asset database", "asset tracking"],
                                  ["16+ projects", "more than 16 projects"]],
        }]
        tailored = _tailored([{
            "id": "acme-1",
            "bullets": ["Managed inventories and asset tracking for more than 16 projects while growing revenue 30%"],
        }])
        self.assertEqual(validate_tailored(_MASTER, tailored, user_facts=facts), [])

    def test_near_duplicate_bullets_are_flagged_at_output_time(self):
        first = "Managed portfolio of 20 program evaluations, including leading design of a $1.5M randomized control trial to evaluate impact and cost effectiveness of $450M credit facilitation program for small farmers."
        second = "Supervised implementation of 20 program evaluations, including leading design of a $1.5M randomized control trial to evaluate impact of $450M credit facilitation program for small businesses."
        tailored = _tailored([{"id": "acme-1", "bullets": [first, second]}])
        problems = validate_tailored(_MASTER, tailored)
        self.assertTrue(any("[duplicate bullets]" in p for p in problems))

    def test_new_responsibility_verb_is_advisory(self):
        tailored = _tailored([{"id": "acme-1", "bullets": ["Supervised a regional team and grew revenue 30%"]}])
        problems = validate_tailored(_MASTER, tailored)
        self.assertTrue(any("[responsibility wording]" in p for p in problems))

    def test_verb_present_in_another_source_bullet_is_not_reported_as_unsupported(self):
        master = {"work_experience": [{
            "id": "acme-1", "bullets": ["Grew revenue 30%", "Supervised a separate program team"],
        }]}
        tailored = _tailored([{"id": "acme-1", "bullets": ["Supervised a project and grew revenue 30%"]}])
        problems = validate_tailored(master, tailored)
        self.assertFalse(any("[responsibility wording]" in p for p in problems))


class TestFormatReport(unittest.TestCase):
    def test_empty_problems_reports_clean(self):
        self.assertIn("no discrepancies", format_report([]))

    def test_problems_are_listed(self):
        report = format_report(["issue one", "issue two"])
        self.assertIn("issue one", report)
        self.assertIn("issue two", report)

    def test_report_groups_qualitative_coverage_and_records_brainstorm_status(self):
        report = format_report(
            ["[metrics] dropped $413", "[user fact coverage] usa-entry: not reflected"],
            brainstorm_status="failed; local tailoring continued without Gemini brainstorm",
        )
        self.assertIn("Relevance brainstorm: failed", report)
        self.assertIn("Numeric traceability:", report)
        self.assertIn("User-provided fact coverage:", report)
