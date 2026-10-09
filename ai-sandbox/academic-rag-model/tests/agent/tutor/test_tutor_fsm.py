# tests/agent/tutor/test_tutor_fsm.py
import unittest

from agent.tutor.events import Event
from agent.tutor.fsm import (
    AWAITING_ADVANCE, DONE, LAUNCH, SYNTHESIS, VERIFIED, WORKING,
    FsmState, IllegalTransition, checkin_event, finish_event, replay, student_event,
    verdict_event, verify_clean_event,
)


def S(**kw):
    return FsmState(**kw)


class TestStudentEvents(unittest.TestCase):
    def test_first_attempt_moves_launch_to_working(self):
        s, _ = student_event(S(), "attempt", 2)
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

    def test_attempt_that_makes_progress_never_raises_or_fails(self):
        s, _ = student_event(S(state=WORKING, hint_level=1), "attempt", 2, made_progress=True)
        self.assertEqual((s.hint_level, s.failed_at_level), (1, 0))

    def test_attempts_without_progress_count_as_failures_until_level_three_opens(self):
        s = S(state=WORKING, hint_level=2)
        for _ in range(2):
            s, _ = student_event(s, "attempt", 2, made_progress=False)
        self.assertEqual(s.failed_at_level, 2)
        s, info = student_event(s, "stuck", 2)
        self.assertEqual((s.hint_level, s.failed_at_level, info["hint_capped"]), (3, 0, False))

    def test_first_attempt_without_progress_is_a_failure_at_level_zero(self):
        s, _ = student_event(S(), "attempt", 2, made_progress=False)
        self.assertEqual((s.state, s.failed_at_level), (WORKING, 1))

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

    def test_closed_part_stays_closed_for_questions_and_hint_requests(self):
        for st in (VERIFIED, AWAITING_ADVANCE):
            for intent in ("has_questions", "other", "attempt", "stuck", "hint_request", "define_request"):
                s, _ = student_event(S(state=st, hint_level=1), intent, 2, made_progress=False)
                self.assertEqual((s.state, s.hint_level, s.failed_at_level), (st, 1, 0), (st, intent))

    def test_unknown_intent_and_done_state_rejected(self):
        with self.assertRaises(IllegalTransition):
            student_event(S(), "dance", 2)
        with self.assertRaises(IllegalTransition):
            student_event(S(state=DONE), "attempt", 2)


class TestTutorSideEvents(unittest.TestCase):
    def test_verdict_event_is_kept_for_v1_logs(self):
        s = verdict_event(S(state=WORKING), "off_track")
        self.assertEqual((s.state, s.failed_at_level), (WORKING, 1))
        self.assertEqual(verdict_event(s, "correct").state, VERIFIED)
        with self.assertRaises(IllegalTransition):
            verdict_event(S(state=LAUNCH), "correct")

    def test_verify_clean_event_only_while_working(self):
        self.assertEqual(verify_clean_event(S(state=WORKING)).state, VERIFIED)
        for st in (LAUNCH, VERIFIED, AWAITING_ADVANCE):
            with self.assertRaises(IllegalTransition):
                verify_clean_event(S(state=st))

    def test_checkin_only_moves_verified(self):
        self.assertEqual(checkin_event(S(state=VERIFIED)).state, AWAITING_ADVANCE)
        self.assertEqual(checkin_event(S(state=WORKING)).state, WORKING)

    def test_finish_requires_synthesis(self):
        self.assertEqual(finish_event(S(state=SYNTHESIS)).state, DONE)
        with self.assertRaises(IllegalTransition):
            finish_event(S(state=WORKING))


class TestReplay(unittest.TestCase):
    def test_replay_reproduces_state_with_verify_events(self):
        ev = lambda i, t, **kw: Event(id=i, ts="t", type=t, **kw)
        events = [
            ev(1, "session_start"),
            ev(2, "student", intent="attempt", data={"made_progress": True}),
            ev(3, "verify", data={"clean": False}),
            ev(4, "student", intent="attempt", data={"made_progress": False}),
            ev(5, "verify", data={"clean": True}),
            ev(6, "close_part", data={"ratings": {}}),
            ev(7, "tutor_say", data={"checkin": True}),
            ev(8, "student", intent="has_questions"),
            ev(9, "student", intent="confirm_advance"),
        ]
        s = replay(events[:5], 2)
        self.assertEqual((s.state, s.failed_at_level), (VERIFIED, 1))
        s = replay(events[:8], 2)
        self.assertEqual((s.part_index, s.state), (0, AWAITING_ADVANCE))
        s = replay(events, 2)
        self.assertEqual((s.part_index, s.state), (1, LAUNCH))

    def test_replay_still_understands_v1_verdict_logs(self):
        ev = lambda i, t, **kw: Event(id=i, ts="t", type=t, **kw)
        events = [ev(1, "student", intent="attempt"), ev(2, "verdict", data={"assessment": "correct"})]
        self.assertEqual(replay(events, 2).state, VERIFIED)
