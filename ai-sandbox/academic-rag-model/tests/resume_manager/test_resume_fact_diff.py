import unittest

from resume_manager.fact_diff import extract_known_entities, extract_metrics, entities_not_traceable, metrics_not_traceable


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


class TestExtractKnownEntities(unittest.TestCase):
    def test_finds_vocabulary_terms_present_in_text(self):
        vocabulary = ["Python", "Presidential Volunteer Service Award", "MBA"]
        text = "Used Python and SQL to win the Presidential Volunteer Service Award."
        self.assertEqual(
            extract_known_entities(text, vocabulary),
            {"Python", "Presidential Volunteer Service Award"},
        )

    def test_is_case_insensitive(self):
        self.assertEqual(extract_known_entities("built tools with python", ["Python"]), {"Python"})

    def test_does_not_match_a_substring_inside_another_word(self):
        # "R" as a vocabulary term shouldn't match inside "Grew".
        self.assertEqual(extract_known_entities("Grew revenue significantly", ["R"]), set())

    def test_empty_vocabulary_term_is_ignored(self):
        self.assertEqual(extract_known_entities("Some text", ["", "Python"]), set())

    def test_no_matches_returns_empty_set(self):
        self.assertEqual(extract_known_entities("Managed a team", ["Python", "MBA"]), set())


class TestEntitiesNotTraceable(unittest.TestCase):
    def test_entity_in_both_is_not_flagged(self):
        vocabulary = ["Python", "Tableau"]
        source = "Built dashboards using Python and Tableau."
        candidate = "Built interactive dashboards using Python and Tableau for leadership."
        self.assertEqual(entities_not_traceable(candidate, source, vocabulary), [])

    def test_entity_dropped_from_candidate_is_flagged(self):
        vocabulary = ["Python", "Tableau"]
        source = "Built dashboards using Python and Tableau."
        candidate = "Built dashboards using Python for leadership."
        self.assertEqual(entities_not_traceable(candidate, source, vocabulary), ["Tableau"])

    def test_entity_not_present_in_source_is_not_flagged(self):
        # Vocabulary term never appears in the original bullet at all --
        # nothing to have "dropped" for this entry.
        vocabulary = ["Tableau"]
        source = "Grew revenue 30%."
        candidate = "Grew revenue 30% via new pricing."
        self.assertEqual(entities_not_traceable(candidate, source, vocabulary), [])
