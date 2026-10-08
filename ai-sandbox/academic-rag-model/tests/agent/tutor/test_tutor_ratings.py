import unittest

from agent.tutor.events import Event
from agent.tutor.ratings import RatingRejected, ceiling, validate_close_part

DEV, PROF, MAST = "Developing / Needs Review", "Proficient", "Mastered"


def ev(i, type, hint=0, text=None, **data):
    return Event(id=i, ts="t", type=type, part="q1", hint_level=hint, text=text, intent=data.pop("intent", None), data=data)


class TestCeiling(unittest.TestCase):
    def test_clean_part_can_be_mastered(self):
        events = [ev(1, "student", text="my answer", intent="attempt")]
        self.assertEqual(ceiling(events, "rigor")[0], MAST)

    def test_hint_level_one_caps_at_proficient(self):
        events = [ev(1, "student", hint=1, text="a", intent="stuck")]
        self.assertEqual(ceiling(events, "rigor")[0], PROF)

    def test_hint_level_two_caps_at_developing(self):
        events = [ev(1, "student", hint=2, text="a", intent="stuck")]
        rating, reasons = ceiling(events, "rigor")
        self.assertEqual(rating, DEV)
        self.assertTrue(any("hint level" in r for r in reasons))

    def test_unresolved_misconception_caps_at_developing(self):
        events = [ev(1, "student", text="a", intent="attempt"), ev(2, "misconception", tag="closed-implies-bounded")]
        self.assertEqual(ceiling(events, "conceptual")[0], DEV)

    def test_resolved_misconception_caps_at_proficient_not_mastered(self):
        events = [
            ev(1, "misconception", tag="t"),
            ev(2, "misconception_resolved", tag="t"),
        ]
        self.assertEqual(ceiling(events, "conceptual")[0], PROF)

    def test_axis_scoped_misconception_only_caps_that_axis(self):
        events = [ev(1, "misconception", tag="t", axis="rigor")]
        self.assertEqual(ceiling(events, "rigor")[0], DEV)
        self.assertEqual(ceiling(events, "conceptual")[0], MAST)

    def test_student_admitted_gap_caps_axis(self):
        events = [ev(1, "student", text="I don't understand concavity", intent="other", admits_gap=True, gap_axis="conceptual")]
        self.assertEqual(ceiling(events, "conceptual")[0], DEV)
        self.assertEqual(ceiling(events, "rigor")[0], MAST)


class TestValidateClosePart(unittest.TestCase):
    def _events(self):
        return [
            ev(1, "student", hint=2, text="a closed set must be bounded", intent="attempt"),
            ev(2, "misconception", hint=2, tag="closed-implies-bounded"),
        ]

    def _ratings(self, rating, evidence=(2,)):
        return {a: {"rating": rating, "evidence": list(evidence)} for a in ("conceptual", "rigor", "directness")}

    def test_rating_above_ceiling_rejected_with_reason(self):
        with self.assertRaises(RatingRejected) as ctx:
            validate_close_part(self._ratings(PROF), self._events())
        self.assertIn("ceiling", str(ctx.exception))
        self.assertIn("Developing", str(ctx.exception))

    def test_rating_at_ceiling_with_evidence_accepted(self):
        validate_close_part(self._ratings(DEV), self._events())

    def test_missing_axis_empty_evidence_and_bad_rating_rejected(self):
        events = self._events()
        r = self._ratings(DEV)
        del r["rigor"]
        with self.assertRaises(RatingRejected):
            validate_close_part(r, events)
        r = self._ratings(DEV, evidence=())
        with self.assertRaises(RatingRejected):
            validate_close_part(r, events)
        with self.assertRaises(RatingRejected):
            validate_close_part(self._ratings("Excellent"), events)

    def test_evidence_must_reference_real_event_ids_or_student_quotes(self):
        events = self._events()
        with self.assertRaises(RatingRejected):
            validate_close_part(self._ratings(DEV, evidence=(99,)), events)
        validate_close_part(self._ratings(DEV, evidence=("closed set must be  bounded",)), events)  # whitespace-normalized quote
        with self.assertRaises(RatingRejected):
            validate_close_part(self._ratings(DEV, evidence=("the student said something never said",)), events)
