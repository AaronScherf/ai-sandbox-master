import unittest

from agent.tutor.events import Event
from agent.tutor.fsm import (
    AWAITING_ADVANCE, DONE, LAUNCH, SYNTHESIS, VERIFIED, WORKING,
    FsmState, IllegalTransition, checkin_event, finish_event, replay, student_event, verdict_event,
)


def S(**kw):
    return FsmState(**kw)


class TestStudentEvents(unittest.TestCase):
    def test_first_attempt_moves_launch_to_working(self):
        s, info = student_event(S(), "attempt", 2)
        self.assertEqual((s.state, s.hint_level), (WORKING, 0))

    def test_define_request_never_changes_state_or_hint_level(self):
        s, _ = student_event(S(state=WORKING, hint_level=2), "define_request", 2)
        self.assertEqual((s.state, s.hint_level), (WORKING, 2))
        s, _ = student_event(S(), "define_request", 2)
        self.assertEqual(s.state, LAUNCH)

    def test_stuck_raises_hint_one_level_at_a_time(self):
        s, _ = student_event(S(state=WORKING), "stuck", 2)
        self.assertEqual(s.hint_level, 1)
        s, _ = student_event(s, "hint_request", 2)
        self.assertEqual(s.hint_level, 2)

    def test_level_three_requires_two_failed_attempts_at_level_two(self):
        s, info = student_event(S(state=WORKING, hint_level=2, failed_at_level=1), "stuck", 2)
        self.assertEqual(s.hint_level, 2)
        self.assertTrue(info["hint_capped"])
        s, info = student_event(S(state=WORKING, hint_level=2, failed_at_level=2), "stuck", 2)
        self.assertEqual(s.hint_level, 3)
        self.assertFalse(info["hint_capped"])

    def test_attempt_alone_never_raises_hint_level(self):
        s, _ = student_event(S(state=WORKING, hint_level=1), "attempt", 2)
        self.assertEqual(s.hint_level, 1)

    def test_confirm_advance_illegal_while_working_or_launch(self):
        for st in (LAUNCH, WORKING):
            with self.assertRaises(IllegalTransition):
                student_event(S(state=st), "confirm_advance", 2)

    def test_confirm_advance_from_awaiting_goes_to_next_part_launch_and_resets_hints(self):
        s, _ = student_event(S(part_index=0, state=AWAITING_ADVANCE, hint_level=2, failed_at_level=1), "confirm_advance", 2)
        self.assertEqual(s, FsmState(part_index=1, state=LAUNCH, hint_level=0, failed_at_level=0))

    def test_confirm_advance_from_verified_is_allowed(self):
        s, _ = student_event(S(state=VERIFIED), "confirm_advance", 2)
        self.assertEqual(s.part_index, 1)

    def test_confirm_on_last_part_goes_to_synthesis(self):
        s, _ = student_event(S(part_index=1, state=AWAITING_ADVANCE), "confirm_advance", 2)
        self.assertEqual((s.part_index, s.state), (1, SYNTHESIS))

    def test_questions_after_verification_return_to_working_same_part(self):
        s, _ = student_event(S(state=AWAITING_ADVANCE), "has_questions", 2)
        self.assertEqual((s.part_index, s.state), (0, WORKING))

    def test_unknown_intent_and_done_state_rejected(self):
        with self.assertRaises(IllegalTransition):
            student_event(S(), "dance", 2)
        with self.assertRaises(IllegalTransition):
            student_event(S(state=DONE), "attempt", 2)


class TestTutorSideEvents(unittest.TestCase):
    def test_verdict_correct_verifies_and_other_verdicts_count_failures(self):
        s = verdict_event(S(state=WORKING), "off_track")
        self.assertEqual((s.state, s.failed_at_level), (WORKING, 1))
        s = verdict_event(s, "correct")
        self.assertEqual(s.state, VERIFIED)

    def test_verdict_only_while_working(self):
        with self.assertRaises(IllegalTransition):
            verdict_event(S(state=LAUNCH), "correct")
        with self.assertRaises(IllegalTransition):
            verdict_event(S(state=WORKING), "great")

    def test_checkin_only_moves_verified(self):
        self.assertEqual(checkin_event(S(state=VERIFIED)).state, AWAITING_ADVANCE)
        self.assertEqual(checkin_event(S(state=WORKING)).state, WORKING)

    def test_finish_requires_synthesis(self):
        self.assertEqual(finish_event(S(state=SYNTHESIS)).state, DONE)
        with self.assertRaises(IllegalTransition):
            finish_event(S(state=WORKING))


class TestReplay(unittest.TestCase):
    def test_replay_reproduces_state(self):
        ev = lambda i, t, **kw: Event(id=i, ts="t", type=t, **kw)
        events = [
            ev(1, "session_start"),
            ev(2, "student", intent="attempt"),
            ev(3, "verdict", data={"assessment": "correct"}),
            ev(4, "tutor_say", data={"checkin": True}),
            ev(5, "student", intent="confirm_advance"),
        ]
        s = replay(events, 2)
        self.assertEqual((s.part_index, s.state), (1, LAUNCH))
