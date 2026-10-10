import unittest

from agent.tutor.events import Event
from agent.tutor.fsm import (
    AWAITING_ADVANCE, DEFERRED, DONE, LAUNCH, PAUSED, SKIPPED, SYNTHESIS, VERIFIED, WORKING,
    FsmState, IllegalTransition, checkin_event, fresh_index, offerable, pause_event, replay, resume_event,
    status_of, student_event, verify_clean_event,
)


def ev(i, type, **kw):
    return Event(id=i, ts="t", type=type, **kw)


def skip_twice(s, n=3, real_first=False):
    s, _ = student_event(s, "attempt" if real_first else "other", n, made_progress=False,
                         skip=True, real_attempt=real_first)
    return student_event(s, "other", n, skip=True)


class TestSkip(unittest.TestCase):
    def test_first_request_keeps_the_part_and_counts(self):
        s, info = student_event(FsmState(), "other", 3, skip=True)
        self.assertEqual((s.part_index, s.state, s.skip_requests), (0, WORKING, 1))
        self.assertEqual(info["skip_count"], 1)
        self.assertNotIn("skip_ended", info)

    def test_second_request_with_no_real_attempt_parks_as_skipped_and_launches_next(self):
        s, info = skip_twice(FsmState())
        self.assertEqual((s.part_index, s.state, s.skip_requests, s.queue, s.cursor), (1, LAUNCH, 0, (0,), 2))
        self.assertEqual((info["skip_ended"], info["part_status"], info["had_real_attempt"]), (True, SKIPPED, False))
        self.assertEqual(status_of(s, 0), SKIPPED)

    def test_a_real_attempt_before_the_second_request_makes_it_deferred(self):
        s, _ = student_event(FsmState(), "attempt", 3, made_progress=False, real_attempt=True)
        s, _ = student_event(s, "other", 3, skip=True)
        s, info = student_event(s, "other", 3, skip=True)
        self.assertEqual((info["part_status"], info["had_real_attempt"]), (DEFERRED, True))

    def test_the_real_attempt_may_be_in_the_ending_message_itself(self):
        s, _ = student_event(FsmState(), "other", 3, skip=True)
        s, info = student_event(s, "attempt", 3, skip=True, real_attempt=True)
        self.assertEqual(info["part_status"], DEFERRED)

    def test_hint_level_is_saved_for_the_revisit(self):
        s, _ = student_event(FsmState(), "stuck", 3)
        s, _ = skip_twice(s)
        self.assertEqual(s.saved, ((0, 1, 0, SKIPPED),))

    def test_skipping_the_last_fresh_part_goes_to_synthesis_with_the_queue(self):
        s = FsmState(part_index=2, state=WORKING, cursor=3)
        s, _ = skip_twice(s)
        self.assertEqual((s.state, s.queue, s.part_index), (SYNTHESIS, (2,), 2))

    def test_skip_is_ignored_once_the_part_is_closed(self):
        s = verify_clean_event(FsmState(state=WORKING))
        s2, info = student_event(s, "other", 3, skip=True)
        self.assertEqual((s2, "skip_count" in info), (s, False))


def parked_then_closed(n=3):
    s, _ = student_event(FsmState(), "stuck", n)            # hint level 1 on part 0
    s, _ = skip_twice(s, n)                                  # part 0 parked, part 1 in LAUNCH
    s, _ = student_event(s, "attempt", n)
    return verify_clean_event(s)


class TestOfferAndRevisit(unittest.TestCase):
    def test_a_parked_part_becomes_offerable_at_the_next_completed_parts_checkin_only(self):
        s = parked_then_closed()
        self.assertEqual((s.state, s.ripe, offerable(s)), (VERIFIED, (0,), (0,)))
        s = checkin_event(s)
        self.assertEqual((s.state, s.offered, offerable(s)), (AWAITING_ADVANCE, (0,), ()))

    def test_nothing_is_offerable_mid_part(self):
        s, _ = skip_twice(FsmState())
        self.assertEqual(offerable(s), ())

    def test_revisit_reopens_the_part_at_its_saved_hint_level(self):
        s = checkin_event(parked_then_closed())
        s, info = student_event(s, "revisit", 3, revisit=0)
        self.assertEqual((s.part_index, s.state, s.hint_level, s.queue, s.skip_requests), (0, WORKING, 1, (), 0))
        self.assertEqual(info["revisited"], 0)

    def test_advance_after_a_revisit_goes_to_the_next_fresh_part_not_index_plus_one(self):
        s = checkin_event(parked_then_closed())
        s, _ = student_event(s, "revisit", 3, revisit=0)
        s = checkin_event(verify_clean_event(s))
        self.assertEqual(fresh_index(s), 2)
        s, _ = student_event(s, "confirm_advance", 3)
        self.assertEqual((s.part_index, s.state), (2, LAUNCH))

    def test_declined_offer_is_made_once_more_at_synthesis(self):
        s = checkin_event(parked_then_closed())
        s, _ = student_event(s, "confirm_advance", 3)          # move on to part 2
        s, _ = skip_twice(s)                                    # last part parked too
        self.assertEqual((s.state, s.queue), (SYNTHESIS, (0, 2)))
        self.assertEqual(offerable(s), (0, 2))

    def test_revisit_is_refused_while_working_and_for_unparked_parts(self):
        with self.assertRaises(IllegalTransition):
            student_event(FsmState(state=WORKING), "revisit", 3, revisit=0)
        s = checkin_event(parked_then_closed())
        with self.assertRaises(IllegalTransition):
            student_event(s, "revisit", 3, revisit=1)
        with self.assertRaises(IllegalTransition):
            student_event(s, "revisit", 3)

    def test_a_revisit_that_is_skipped_again_stays_deferred_if_it_ever_was(self):
        s = FsmState(part_index=0, state=WORKING)
        s, _ = student_event(s, "attempt", 3, made_progress=False, real_attempt=True)
        s, _ = skip_twice(s)                                    # deferred
        s = checkin_event(verify_clean_event(student_event(s, "attempt", 3)[0]))
        s, _ = student_event(s, "revisit", 3, revisit=0)
        s, info = skip_twice(s)                                 # no real attempt this time
        self.assertEqual(info["part_status"], DEFERRED)


class TestPauseAndReplay(unittest.TestCase):
    def test_pause_and_resume_restore_the_state(self):
        s = FsmState(state=WORKING, hint_level=2)
        p = pause_event(s)
        self.assertEqual((p.state, p.resume_state), (PAUSED, WORKING))
        self.assertEqual(resume_event(p), s)

    def test_nothing_runs_while_paused_or_after_done(self):
        p = pause_event(FsmState(state=WORKING))
        with self.assertRaises(IllegalTransition):
            student_event(p, "attempt", 3)
        with self.assertRaises(IllegalTransition):
            pause_event(p)
        with self.assertRaises(IllegalTransition):
            pause_event(FsmState(state=DONE))
        with self.assertRaises(IllegalTransition):
            resume_event(FsmState(state=WORKING))

    def test_replay_reads_the_new_event_data(self):
        events = [ev(1, "student", intent="other", data={"skip": True}),
                  ev(2, "student", intent="other", data={"skip": True, "real_attempt": False}),
                  ev(3, "paused"), ev(4, "resumed")]
        s = replay(events, 3)
        self.assertEqual((s.part_index, s.state, s.queue), (1, LAUNCH, (0,)))

    def test_replay_of_a_partial_end_is_done_from_any_state(self):
        events = [ev(1, "student", intent="attempt", data={}), ev(2, "session_end", data={"partial": True})]
        self.assertEqual(replay(events, 2).state, DONE)

    def test_replay_revisit_uses_the_logged_index(self):
        events = [ev(1, "student", intent="other", data={"skip": True}),
                  ev(2, "student", intent="other", data={"skip": True}),
                  ev(3, "student", intent="attempt", data={}),
                  ev(4, "verify", data={"clean": True}),
                  ev(5, "tutor_say", data={"checkin": True}),
                  ev(6, "student", intent="revisit", data={"revisit": 0})]
        s = replay(events, 3)
        self.assertEqual((s.part_index, s.state), (0, WORKING))

    def test_old_v1_style_logs_still_replay_with_the_same_numbers(self):
        events = [ev(1, "student", intent="attempt", data={"made_progress": True}),
                  ev(2, "verify", data={"clean": True}), ev(3, "tutor_say", data={"checkin": True}),
                  ev(4, "student", intent="confirm_advance", data={})]
        s = replay(events, 2)
        self.assertEqual((s.part_index, s.state, s.hint_level), (1, LAUNCH, 0))


if __name__ == "__main__":
    unittest.main()
