import unittest

from resume_manager.fact_diff import extract_metrics, metrics_not_traceable


class TestExtractMetrics(unittest.TestCase):
    def test_finds_percent_dollar_and_x_tokens(self):
        text = "Grew revenue 30% worth $2M, a 10x improvement."
        self.assertEqual(extract_metrics(text), {"30%", "$2M", "10x"})

    def test_plain_number_with_no_suffix_is_not_a_metric(self):
        # A known heuristic limitation (spec §10) -- documented, not fixed here.
        self.assertEqual(extract_metrics("Managed a team of 12 people."), set())


class TestMetricsNotTraceable(unittest.TestCase):
    def test_metric_present_in_source_is_not_flagged(self):
        self.assertEqual(metrics_not_traceable("Grew revenue 30%.", "Grew revenue 30% via pricing."), [])

    def test_metric_absent_from_source_is_flagged(self):
        self.assertEqual(metrics_not_traceable("Grew revenue 75%.", "Grew revenue 30%."), ["75%"])
