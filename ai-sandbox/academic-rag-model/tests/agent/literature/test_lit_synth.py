import unittest

from agent.literature import synth

ALLOWED = {"P1": {"year": 2019, "results": {"R1": "Cash transfers raised food consumption 12% raised household food consumption"}},
           "P2": {"year": 2020, "results": {"R1": "Vouchers had no effect 0.5 points"}}}


def paragraph(text, *cites):
    return {"sections": [{"heading": "Findings", "paragraphs": [{"text": text, "cites": list(cites)}]}]}


class TestCheckSections(unittest.TestCase):
    def check(self, doc, cover=("P1",)):
        return synth.check_sections(doc["sections"] if isinstance(doc, dict) else doc, ALLOWED, list(cover))

    def test_a_cited_paragraph_with_traceable_numbers_passes(self):
        doc = paragraph("Transfers raised food consumption by 12% in the treated districts.", "P1.R1")
        self.assertEqual(self.check(doc), [])
        self.assertEqual(self.check(paragraph("Work published in 2019 found gains.", "P1"), cover=("P1",)), [])

    def test_a_number_only_in_prose_or_only_in_an_uncited_paper_bounces_naming_it(self):
        msgs = self.check(paragraph("Transfers raised food consumption by 15% in treated districts.", "P1.R1"))
        self.assertTrue(any("15" in m for m in msgs), msgs)
        msgs = self.check(paragraph("Vouchers moved scores by 0.5 points in the sample.", "P1.R1"))
        self.assertTrue(any("0.5" in m for m in msgs), msgs)

    def test_citations_must_exist_and_every_paragraph_needs_one(self):
        self.assertTrue(any("P9" in m for m in self.check(paragraph("Some evidence points the same way here.", "P9"))))
        self.assertTrue(any("P1.R7" in m for m in self.check(paragraph("Some evidence points the same way here.", "P1.R7"))))
        self.assertTrue(self.check(paragraph("Some evidence points the same way here.")))

    def test_raw_ids_in_prose_and_uncovered_papers_bounce(self):
        self.assertTrue(any("P1" in m for m in self.check(paragraph("As P1 shows, evidence points the same way.", "P1"))))
        msgs = self.check(paragraph("Some evidence points the same way here.", "P1"), cover=("P1", "P2"))
        self.assertTrue(any("P2" in m and "not cited" in m for m in msgs), msgs)

    def test_the_shape_is_checked(self):
        self.assertTrue(self.check([]))
        self.assertTrue(self.check([{"heading": "x", "paragraphs": "no"}]))


DIRECTED = {"P1": {"year": 2019, "directions": {"R1": "positive", "R2": "negative"},
                   "results": {"R1": "Cash transfers raised food consumption", "R2": "Transfers crowded out remittances"}},
            "P2": {"year": 2020, "directions": {"R1": "negative"}, "results": {"R1": "Heat cut crop yields"}},
            "P3": {"year": 2021, "directions": {"R1": "null"}, "results": {"R1": "Vouchers had no effect"}},
            "P4": {"year": 2022, "directions": {"R1": "not_reported"}, "results": {"R1": "Programme was described"}}}


class TestDirectionWords(unittest.TestCase):
    def check(self, text, *cites):
        return synth.check_sections(paragraph(text, *cites)["sections"], DIRECTED, [])

    def test_a_positive_word_needs_a_positive_or_mixed_cited_result(self):
        msgs = self.check("Heat improved crop yields across the sampled districts.", "P2.R1")
        self.assertTrue(any("improved" in m and "negative" in m for m in msgs), msgs)
        self.assertEqual(self.check("Transfers improved food consumption in the sampled districts.", "P1.R1"), [])

    def test_a_negative_word_needs_a_negative_or_mixed_cited_result(self):
        msgs = self.check("Transfers harmed food consumption in the sampled districts.", "P1.R1")
        self.assertTrue(any("harmed" in m and "positive" in m for m in msgs), msgs)
        self.assertEqual(self.check("Heat had adverse effects on yields in the sampled districts.", "P2.R1"), [])

    def test_a_paper_level_cite_is_supported_by_any_of_its_results(self):
        self.assertEqual(self.check("Transfers harmed remittances in the sampled districts.", "P1"), [])
        self.assertEqual(self.check("Transfers improved food consumption in the sampled districts.", "P1"), [])

    def test_a_null_result_supports_neither_direction(self):
        self.assertTrue(self.check("Vouchers improved outcomes in the sampled districts.", "P3.R1"))
        self.assertTrue(self.check("Vouchers worsened outcomes in the sampled districts.", "P3.R1"))

    def test_unknown_directions_are_not_checked(self):
        self.assertEqual(self.check("The programme improved outcomes in the sampled districts.", "P4.R1"), [])
        self.assertEqual(synth.check_sections(paragraph("Heat improved crop yields across the sampled districts.", "P1.R1")["sections"],
                                              {"P1": {"year": 2019, "results": {"R1": "Heat cut crop yields"}}}, []), [])

    def test_negation_and_mitigation_wording_is_not_flagged(self):
        self.assertEqual(self.check("Vouchers did not improve outcomes in the sampled districts.", "P3.R1"), [])
        self.assertEqual(self.check("Transfers helped households mitigate the harm of shocks in the districts.", "P1.R1"), [])

    def test_increase_and_decrease_words_are_not_checked(self):
        self.assertEqual(self.check("Heat reduced crop yields across the sampled districts.", "P2.R1"), [])
        self.assertEqual(self.check("Transfers reduced the poverty rate across the sampled districts.", "P1.R1"), [])

    def test_allowed_for_carries_each_results_direction(self):
        ann = {"identity": {"publication_year": 2019},
               "results": [{"id": "R1", "claim": "c", "magnitude": "1%", "quote": "q", "effect_direction": "negative"}]}
        out = synth.allowed_for({"f" * 16: ann}, {"f" * 16: "P1"})
        self.assertEqual(out["P1"]["directions"], {"R1": "negative"})


VALUES = {"P1": {"year": 2019, "results": {"R1": "Transfers reached 1,200 households and cut costs by 12.50 percent",
                                           "R2": "Coverage rose 8.0 points to 45"}}}


class TestNumberForms(unittest.TestCase):
    def check(self, text, *cites):
        return synth.check_sections(paragraph(text, *cites)["sections"], VALUES, [])

    def test_numbers_match_by_value_not_by_spelling(self):
        self.assertEqual(self.check("Transfers reached 1200 households in the sampled districts.", "P1.R1"), [])
        self.assertEqual(self.check("Transfers reached 1,200 households in the sampled districts.", "P1.R1"), [])
        self.assertEqual(self.check("Costs fell by 12.5 percent in the sampled districts.", "P1.R1"), [])
        self.assertEqual(self.check("Coverage rose 8 points to 45 in the sampled districts.", "P1.R2"), [])

    def test_a_different_value_still_bounces_and_names_the_number_as_written(self):
        msgs = self.check("Transfers reached 1,300 households in the sampled districts.", "P1.R1")
        self.assertTrue(any("1,300" in m for m in msgs), msgs)
        msgs = self.check("Costs fell by 12.6 percent in the sampled districts.", "P1.R1")
        self.assertTrue(any("12.6" in m for m in msgs), msgs)


class TestNumberWords(unittest.TestCase):
    def check(self, text):
        return synth.check_sections(paragraph(text, "P1.R1")["sections"], VALUES, [])

    def test_a_spelled_out_figure_bounces_and_names_the_word(self):
        for text, word in [("Costs fell by about twelve percent in the sampled districts.", "twelve"),
                           ("Coverage rose by five percentage points in the sampled districts.", "five"),
                           ("Roughly twenty households per village were reached in the sampled districts.", "twenty"),
                           ("Transfers reached three thousand households in the sampled districts.", "thousand")]:
            with self.subTest(word=word):
                msgs = self.check(text)
                self.assertTrue(any(word in m and "digits" in m for m in msgs), msgs)

    def test_study_counts_in_words_and_ordinary_uses_pass(self):
        for text in ("Three studies found that transfers reached households in the sampled districts.",
                     "Across the twenty papers reviewed, transfers reached households in the districts.",
                     "One mechanism is that transfers reached households in the sampled districts.",
                     "Transfers reached households in two countries and a third setting in the districts."):
            with self.subTest(text=text):
                self.assertEqual(self.check(text), [])

    def test_a_word_the_cited_result_itself_uses_is_allowed(self):
        allowed = {"P1": {"year": 2019, "results": {"R1": "Droughts displaced over three million people since 2016",
                                                    "R2": "Aid reached many households"}}}
        doc = paragraph("Droughts displaced over three million people in the region.", "P1.R1")["sections"]
        self.assertEqual(synth.check_sections(doc, allowed, []), [])
        doc = paragraph("Droughts displaced over three million people in the region.", "P1.R2")["sections"]
        self.assertTrue(any("three" in m or "million" in m for m in synth.check_sections(doc, allowed, [])))


if __name__ == "__main__":
    unittest.main()
