import copy
import unittest

from agent.literature.validate import check_result
from lit_helpers import PAGES, VOCABS, good


def problems(result):
    return check_result(result, VOCABS, PAGES)


class TestValid(unittest.TestCase):
    def test_a_complete_result_passes(self):
        self.assertEqual(problems(good()), [])

    def test_a_proposed_term_passes_when_not_in_the_vocabulary(self):
        r = good()
        r["core"]["study_design"] = [{"value": "synthetic control", "proposed": True,
                                      "quote": "using a panel of 1,200 households", "locator": 1}]
        self.assertEqual(problems(r), [])

    def test_modules_are_optional_and_validated_when_present(self):
        r = good()
        r["modules"] = {"disaster_conflict": {"hazard_types": [
            {"value": "drought", "vocab_id": "hazard_type.drought",
             "quote": "rural Somalia using a panel", "locator": 1}],
            "conflict_setting": None, "social_protection_modality": "cash"}}
        self.assertEqual(problems(r), [])


class TestProblems(unittest.TestCase):
    def _expect(self, mutate, needle):
        r = good()
        mutate(r)
        msgs = problems(r)
        self.assertTrue(any(needle in m for m in msgs), msgs)

    def test_unknown_keys(self):
        self._expect(lambda r: r.update(extra=1), "extra")
        self._expect(lambda r: r["core"]["outcome"][0].update(colour="x"), "colour")

    def test_missing_pieces(self):
        self._expect(lambda r: r.pop("appraisal"), "appraisal")
        self._expect(lambda r: r["core"].pop("outcome"), "core.outcome")
        self._expect(lambda r: r["core"].update(results=[]), "core.results")

    def test_vocabulary_membership(self):
        self._expect(lambda r: r["core"]["outcome"][0].update(vocab_id="outcome.nonsense"), "core.outcome[0].vocab_id")

    def test_vocab_id_and_proposed_are_exclusive_and_one_is_required(self):
        self._expect(lambda r: r["core"]["outcome"][0].update(proposed=True), "core.outcome[0]")
        self._expect(lambda r: r["core"]["outcome"][0].pop("vocab_id"), "core.outcome[0]")

    def test_proposing_an_existing_term_is_refused_and_names_it(self):
        def m(r):
            r["core"]["study_design"] = [{"value": "Panel", "proposed": True,
                                          "quote": "using a panel of 1,200 households", "locator": 1}]
        self._expect(m, "study_design.panel")

    def test_quote_problems_carry_the_field_path(self):
        self._expect(lambda r: r["core"]["outcome"][0].update(quote="reduced hunger by forty percent"),
                     "core.outcome[0].quote")
        self._expect(lambda r: r["core"]["outcome"][0].update(locator=99), "core.outcome[0].locator")

    def test_enums(self):
        self._expect(lambda r: r["core"]["results"][0].update(effect_direction="up"), "effect_direction")
        self._expect(lambda r: r["appraisal"].update(confidence="certain"), "appraisal.confidence")
        self._expect(lambda r: r["core"]["geography"].update(scale="galactic"), "geography.scale")

    def test_countries_must_be_iso_alpha2(self):
        self._expect(lambda r: r["core"]["geography"].update(countries=["Somalia"]), "geography.countries")
        self._expect(lambda r: r["core"]["geography"].update(countries=["so"]), "geography.countries")

    def test_geography_with_places_needs_a_quote(self):
        self._expect(lambda r: r["core"]["geography"].pop("quote"), "geography")

    def test_not_stated_geography_needs_no_quote(self):
        r = good()
        r["core"]["geography"] = {"countries": [], "regions": [], "scale": "not_stated"}
        self.assertEqual(problems(r), [])

    def test_a_vocabulary_missing_at_validation_time_is_reported_not_crashed(self):
        r = good()
        vocabs = {k: v for k, v in VOCABS.items() if k != "outcome"}
        msgs = check_result(r, vocabs, PAGES)
        self.assertTrue(any("outcome" in m and "vocabulary" in m for m in msgs), msgs)

    def test_a_non_mapping_result_is_one_clear_problem(self):
        self.assertEqual(len(check_result([], VOCABS, PAGES)), 1)

    def test_inputs_are_not_mutated(self):
        r = good()
        snapshot = copy.deepcopy(r)
        problems(r)
        self.assertEqual(r, snapshot)


if __name__ == "__main__":
    unittest.main()
