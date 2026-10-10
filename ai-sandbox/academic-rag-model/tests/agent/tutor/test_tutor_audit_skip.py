# tests/agent/tutor/test_tutor_audit_skip.py
import tempfile
import unittest

from agent.tutor.audit import audit
from agent.tutor.events import Event
from skip_support import CHECKIN, CHECKIN_OFFER, NUDGE, Q, close_q1_said, close_q2, close_q2_said, make, park_q1

LAUNCH_Q2 = "Question 2. How would you like to approach this problem?"


def codes(findings):
    return [f.code for f in findings]


class TestHonestFlowIsClean(unittest.TestCase):
    def test_skip_revisit_flow_through_the_gate_has_no_findings(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            park_q1(s)
            s.say(LAUNCH_Q2)
            close_q2_said(s)
            s.say(CHECKIN_OFFER)
            s.turn("revisit", "yes let's go back to the first question")
            s.say(Q)
            close_q1_said(s)
            s.say(CHECKIN)
            s.turn("confirm_advance", "ready to move on")
            self.assertEqual(codes(audit(s.log.load(), s.packet)), [])


class TestFindings(unittest.TestCase):
    def test_uncounted_skip_phrase_in_an_attempt_is_listed(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            s.turn("attempt", "I will skip the algebra and move on to the idea of the default")
            self.assertIn("SKIP_PHRASE_UNCOUNTED", codes(audit(s.log.load(), s.packet)))

    def test_ending_skip_without_any_tutor_reply_in_between(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            s.turn("other", "skip this", skip=True)
            s.turn("other", "skip it please", skip=True)                    # no say between the two requests
            self.assertIn("SKIP_WITHOUT_NUDGE", codes(audit(s.log.load(), s.packet)))

    def test_part_status_with_fewer_than_two_requests(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            park_q1(s)
            events = s.log.load()
            for e in events:
                if e.type == "part_status":
                    e.data["skip_requests"] = 1
            self.assertIn("SKIP_TOO_EARLY", codes(audit(events, s.packet)))

    def test_checkin_without_the_offer_is_found_even_if_the_log_was_written_around_the_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            park_q1(s)
            s.say(LAUNCH_Q2)
            close_q2(s)
            last = s.log.load()[-1]
            events = s.log.load() + [Event(id=last.id + 1, ts="t", type="tutor_say", part="q2", state="AWAITING_ADVANCE",
                                           text=CHECKIN, data={"checkin": True, "offer": []})]
            self.assertIn("REVISIT_OFFER_MISSING", codes(audit(events, s.packet)))

    def test_a_parked_part_mentioned_while_another_is_worked(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            park_q1(s)
            s.say(LAUNCH_Q2)
            s.turn("attempt", "the preference looks flat for the negative numbers to me")
            last = s.log.load()[-1]
            events = s.log.load() + [Event(id=last.id + 1, ts="t", type="tutor_say", part="q2", state="WORKING",
                                           text="Should we go back to Question 1?", data={})]
            self.assertIn("REVISIT_MID_PART", codes(audit(events, s.packet)))


if __name__ == "__main__":
    unittest.main()
