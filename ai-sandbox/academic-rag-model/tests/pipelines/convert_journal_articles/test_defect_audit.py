import unittest

from pipelines.convert_journal_articles.defect_audit import SIGNALS, signals_for, summarize
from pipelines.transcribe_notes.transcribe_notes import page_looks_defective

PUA_RUN = "Results  table"
LIGATURE_RUN = "significant ﬁﬁﬁﬁﬁ effect"
COLLAPSED = "Thecoefficientonprogramparticipationispositiveandsignificantacrossspecifications"
LOST_EXPONENT = "The fit is R2 = 0.43 and hypothesis H1 holds."
CLEAN = "We estimate the effect of the program on household income using a difference-in-differences design."


class TestSignalsFor(unittest.TestCase):
    def test_each_defect_fixture_trips_its_own_signal(self):
        self.assertIn("unexpected_chars", signals_for(PUA_RUN))
        self.assertIn("repeated_char_run", signals_for(LIGATURE_RUN))
        self.assertIn("collapsed_prose", signals_for(COLLAPSED))
        self.assertIn("lost_exponent", signals_for(LOST_EXPONENT))

    def test_clean_prose_trips_nothing(self):
        self.assertEqual(signals_for(CLEAN), set())

    def test_signals_agree_with_page_looks_defective(self):
        # Drift guard: if page_looks_defective gains or loses a signal, this audit must follow.
        for text in (PUA_RUN, LIGATURE_RUN, COLLAPSED, LOST_EXPONENT, CLEAN):
            with self.subTest(text=text[:30]):
                self.assertEqual(bool(signals_for(text)), page_looks_defective(text))
                self.assertEqual(
                    bool(signals_for(text) - {"lost_exponent"}),
                    page_looks_defective(text, check_math_notation=False),
                )

    def test_signal_names_are_the_four_known(self):
        self.assertEqual(set(SIGNALS), {"collapsed_prose", "unexpected_chars", "repeated_char_run", "lost_exponent"})


class TestSummarize(unittest.TestCase):
    def test_rate_and_hybrid_threshold_count(self):
        rows = [
            {"pages": 10, "reliable": True, "defective_pages": 0, "by_signal": {}},
            {"pages": 10, "reliable": True, "defective_pages": 2, "by_signal": {"lost_exponent": 2}},
            {"pages": 10, "reliable": False, "defective_pages": 0, "by_signal": {}},
        ]
        s = summarize(rows)
        self.assertEqual(s["documents"], 3)
        self.assertEqual(s["pages"], 30)
        self.assertEqual(s["defective_pages"], 2)
        self.assertAlmostEqual(s["defect_rate"], 2 / 20)  # only reliably-paginated docs are scored
        self.assertEqual(s["by_signal"], {"lost_exponent": 2})
        self.assertEqual(s["docs_over_hybrid_threshold"], 1)  # 2/10 = 20% > 10%


if __name__ == "__main__":
    unittest.main()
