import unittest

from resume_manager.fact_diff import (
    Entry, entries_not_traceable, extract_entries, extract_metrics, metrics_not_traceable,
)

_MASTER = """## Experience

### Acme Corp — Engineer (2020 – Present)
- Grew revenue 30% by shipping the new pricing model, worth $2M annually.

### Old Co — Analyst (2015 – 2018)
- Built reports.
"""


class TestExtractEntries(unittest.TestCase):
    def test_parses_every_entry_heading(self):
        entries = extract_entries(_MASTER)
        self.assertEqual(entries, [
            Entry(org="Acme Corp", role="Engineer", dates="2020 – Present"),
            Entry(org="Old Co", role="Analyst", dates="2015 – 2018"),
        ])

    def test_ignores_non_matching_lines(self):
        text = "## Experience\nSome prose that is not a heading at all.\n"
        self.assertEqual(extract_entries(text), [])


class TestExtractMetrics(unittest.TestCase):
    def test_finds_percent_dollar_and_x_tokens(self):
        text = "Grew revenue 30% worth $2M, a 10x improvement."
        self.assertEqual(extract_metrics(text), {"30%", "$2M", "10x"})

    def test_plain_number_with_no_suffix_is_not_a_metric(self):
        # A known heuristic limitation (spec §10) -- documented, not fixed here.
        self.assertEqual(extract_metrics("Managed a team of 12 people."), set())


class TestEntriesNotTraceable(unittest.TestCase):
    def test_matching_entry_is_not_flagged(self):
        candidate = "### Acme Corp — Engineer (2020 – Present)\n- did stuff"
        self.assertEqual(entries_not_traceable(candidate, _MASTER), [])

    def test_fabricated_entry_is_flagged(self):
        candidate = "### New Corp — Director (2022 – Present)\n- did stuff"
        result = entries_not_traceable(candidate, _MASTER)
        self.assertEqual(result, [Entry(org="New Corp", role="Director", dates="2022 – Present")])

    def test_dropping_a_source_entry_is_not_flagged(self):
        # Only checks the candidate direction -- a tailored resume
        # omitting an old role is expected behavior (spec §5).
        candidate = "### Acme Corp — Engineer (2020 – Present)\n- did stuff"
        self.assertEqual(entries_not_traceable(candidate, _MASTER), [])


class TestMetricsNotTraceable(unittest.TestCase):
    def test_metric_present_in_source_is_not_flagged(self):
        candidate = "Grew revenue 30%."
        self.assertEqual(metrics_not_traceable(candidate, _MASTER), [])

    def test_metric_absent_from_source_is_flagged(self):
        candidate = "Grew revenue 75%."
        self.assertEqual(metrics_not_traceable(candidate, _MASTER), ["75%"])
