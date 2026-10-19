import unittest

from agent.literature.compare import diff_records
from agent.literature.vocab import Term, Vocabulary
from lit_helpers import VOCABS, good


def _record(result):
    return {"core": result["core"], "appraisal": result["appraisal"], "identity": {"file_id": "x"}}


def _twin_vocabs():
    terms = {
        "intervention.cash_transfer": Term(id="intervention.cash_transfer", label="Cash transfer"),
        "intervention.cash_transfer_social_protection": Term(id="intervention.cash_transfer_social_protection",
                                                             label="Cash  Transfer"),
        "intervention.voucher": Term(id="intervention.voucher", label="Voucher"),
    }
    return dict(VOCABS, intervention=Vocabulary("intervention", 1, "3ie", "test", terms))


class TestTwinTerms(unittest.TestCase):
    def test_two_ids_with_the_same_label_are_one_fact_when_vocabularies_are_given(self):
        b = good()
        b["core"]["intervention"][0]["vocab_id"] = "intervention.cash_transfer_social_protection"
        a, b = _record(good()), _record(b)
        self.assertEqual(diff_records(a, b, _twin_vocabs()), [])
        self.assertEqual(len(diff_records(a, b)), 1)  # without vocabularies, ids are compared as before

    def test_different_labels_still_disagree(self):
        b = good()
        b["core"]["intervention"][0]["vocab_id"] = "intervention.voucher"
        self.assertEqual(len(diff_records(_record(good()), _record(b), _twin_vocabs())), 1)


if __name__ == "__main__":
    unittest.main()
