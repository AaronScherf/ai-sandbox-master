# tests/agent/tutor/test_tutor_ratings.py  (replace the whole file)
import unittest

from agent.tutor.events import Event
from agent.tutor.ratings import AXES, RatingRejected, build_ratings, cap_evidence, ceiling

DEV, PROF, MAST = "Developing / Needs Review", "Proficient", "Mastered"


def ev(i, type, hint=0, text=None, **data):
    return Event(id=i, ts="t", type=type, part="q1", hint_level=hint, text=text, intent=data.pop("intent", None), data=data)


class TestCeiling(unittest.TestCase):
    def test_clean_part_can_be_mastered(self):
        self.assertEqual(ceiling([ev(1, "student", text="my answer", intent="attempt")], "rigor")[0], MAST)

    def test_hint_level_one_caps_at_proficient(self):
        self.assertEqual(ceiling([ev(1, "student", hint=1, text="a", intent="stuck")], "rigor")[0], PROF)

    def test_hint_level_two_caps_at_developing(self):
        rating, reasons = ceiling([ev(1, "student", hint=2, text="a", intent="stuck")], "rigor")
        self.assertEqual(rating, DEV)
        self.assertTrue(any("hint level" in r for r in reasons))

    def test_unresolved_misconception_caps_at_developing(self):
        events = [ev(1, "student", text="a", intent="attempt"), ev(2, "misconception", tag="closed-implies-bounded")]
        self.assertEqual(ceiling(events, "conceptual")[0], DEV)

    def test_resolved_misconception_caps_at_proficient_not_mastered(self):
        events = [ev(1, "misconception", tag="t"), ev(2, "misconception_resolved", tag="t")]
        self.assertEqual(ceiling(events, "conceptual")[0], PROF)

    def test_axis_scoped_misconception_only_caps_that_axis(self):
        events = [ev(1, "misconception", tag="t", axis="rigor")]
        self.assertEqual(ceiling(events, "rigor")[0], DEV)
        self.assertEqual(ceiling(events, "conceptual")[0], MAST)

    def test_student_admitted_gap_caps_axis(self):
        events = [ev(1, "student", text="I don't understand concavity", intent="other", admits_gap=True, gap_axis="conceptual")]
        self.assertEqual(ceiling(events, "conceptual")[0], DEV)
        self.assertEqual(ceiling(events, "rigor")[0], MAST)


class TestCapEvidence(unittest.TestCase):
    def test_hint_misconception_and_gap_events_are_the_evidence(self):
        events = [
            ev(1, "student", hint=0, text="try", intent="attempt", established=["C1"]),
            ev(2, "student", hint=1, text="stuck", intent="stuck"),
            ev(3, "misconception", tag="t", axis="rigor"),
            ev(4, "student", hint=1, text="idk", intent="other", admits_gap=True, gap_axis="conceptual"),
        ]
        self.assertEqual(cap_evidence(events, "rigor"), [2, 3])
        self.assertEqual(cap_evidence(events, "conceptual"), [2, 4])
        self.assertEqual(cap_evidence(events, "directness"), [2])

    def test_uncapped_axis_cites_the_turns_that_established_claims(self):
        events = [ev(1, "student", text="a", intent="attempt"),
                  ev(2, "student", text="b", intent="attempt", established=["C1"]),
                  ev(3, "student", text="c", intent="attempt", established=["C2"])]
        self.assertEqual(cap_evidence(events, "rigor"), [2, 3])

    def test_falls_back_to_the_last_student_event(self):
        events = [ev(1, "student", text="a", intent="attempt"), ev(2, "student", text="b", intent="attempt")]
        self.assertEqual(cap_evidence(events, "rigor"), [2])


class TestBuildRatings(unittest.TestCase):
    def _events(self):
        return [
            ev(1, "student", text="a closed set must be bounded", intent="attempt", established=[]),
            ev(2, "misconception", hint=0, tag="closed-implies-bounded", axis="conceptual"),
            ev(3, "student", hint=1, text="a hint please", intent="hint_request"),
            ev(4, "student", hint=1, text="so it is compact", intent="attempt", established=["C1"]),
        ]

    def test_defaults_to_the_ceiling_with_cli_attached_evidence(self):
        r = build_ratings(self._events())
        self.assertEqual(set(r), set(AXES))
        self.assertEqual(r["conceptual"]["rating"], DEV)          # unresolved misconception on the conceptual axis
        self.assertEqual(r["rigor"]["rating"], PROF)              # hint level 1 only
        self.assertEqual(r["conceptual"]["evidence"], [2, 3])
        self.assertEqual(r["rigor"]["evidence"], [3])

    def test_agent_can_lower_but_not_raise(self):
        events = self._events()
        r = build_ratings(events, {"rigor": (DEV, "sloppy notation throughout")})
        self.assertEqual(r["rigor"]["rating"], DEV)
        self.assertEqual(r["rigor"]["why"], "sloppy notation throughout")
        with self.assertRaises(RatingRejected) as ctx:
            build_ratings(events, {"conceptual": (PROF, "they got there in the end")})
        self.assertIn("cannot raise", str(ctx.exception))

    def test_unknown_axis_and_rating_rejected(self):
        with self.assertRaises(RatingRejected):
            build_ratings(self._events(), {"style": (DEV, "x")})
        with self.assertRaises(RatingRejected):
            build_ratings(self._events(), {"rigor": ("Excellent", "x")})
