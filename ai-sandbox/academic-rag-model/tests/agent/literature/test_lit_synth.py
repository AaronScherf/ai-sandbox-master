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


if __name__ == "__main__":
    unittest.main()
