# tests/agent/tutor/test_tutor_say_skip.py
import tempfile
import unittest

from agent.tutor.session import Refused
from skip_support import (
    CHECKIN, CHECKIN_OFFER, CHECK_Q1, M2, NUDGE, close_q1, close_q2, codes, cover_q2, make, park_q1,
)

LAUNCH_Q2 = "Question 2. How would you like to approach this problem?"


class TestSkipNudge(unittest.TestCase):
    def test_the_reply_to_a_first_skip_request_must_be_one_inviting_question(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            s.turn("other", "I would rather skip this one", skip=True)
            self.assertIn("SKIP_NUDGE", codes(s.say("Sure, we can skip it. What would you like to do?", check=True)))
            self.assertIn("SKIP_NUDGE", codes(s.say("Walking away is the complement of picking anything else.", check=True)))
            self.assertIn("NEXT_PART_REFERENCE", codes(s.say("What have you tried? Otherwise we could go to Question 2.", check=True)))
            r = s.say(NUDGE)
            self.assertTrue(r["ok"])

    def test_after_the_nudge_a_normal_reply_has_no_nudge_requirement(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            s.turn("other", "I would rather skip this one", skip=True)
            s.say(NUDGE)
            s.turn("attempt", "I guess I could start with the default option here")
            self.assertTrue(s.say("What do you mean by the default option?", check=True)["ok"])


class TestLaunchAck(unittest.TestCase):
    def test_one_short_acknowledgement_may_precede_the_launch_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            park_q1(s)
            ok = s.say("We can come back to the earlier one later. " + LAUNCH_Q2, check=True)
            self.assertTrue(ok["ok"], ok)
            self.assertTrue(s.say(LAUNCH_Q2, check=True)["ok"])

    def test_the_acknowledgement_may_not_carry_content_or_be_long(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            park_q1(s)
            leak = "Remember that the default is whatever is left when nothing else is picked. " + LAUNCH_Q2
            self.assertIn("REVEALS_CLAIM", codes(s.say(leak, check=True)))
            long = ("We can certainly come back to the earlier question another time once you have had a bit of a "
                    "break and a fresh look at everything else we have covered today. ") + LAUNCH_Q2
            self.assertIn("LAUNCH_ACK", codes(s.say(long, check=True)))
            self.assertIn("LAUNCH_ACK", codes(s.say("Want to come back later? " + LAUNCH_Q2, check=True)))
            self.assertIn("LAUNCH_NOT_VERBATIM", codes(s.say("Q2: pick an approach.", check=True)))

    def test_no_acknowledgement_is_allowed_without_a_skip(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            self.assertIn("LAUNCH_NOT_VERBATIM", codes(s.say("Welcome! Question 1. How would you like to approach this problem?", check=True)))


class TestRevisitOffer(unittest.TestCase):
    def test_the_checkin_after_the_next_completed_part_must_offer_the_parked_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            park_q1(s)
            s.say(LAUNCH_Q2)
            close_q2(s)
            self.assertIn("REVISIT_OFFER_MISSING", codes(s.say(CHECKIN, check=True)))
            r = s.say(CHECKIN_OFFER)
            self.assertTrue(r["ok"])
            self.assertEqual(s.log.load()[-1].data, {"checkin": True, "offer": ["q1"]})
            self.assertEqual(r["state"], "AWAITING_ADVANCE")
            self.assertEqual(r["revisit_options"], [{"part_id": "q1", "label": "Question 1", "status": "skipped"}])

    def test_no_offer_is_required_when_nothing_is_parked(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            close_q1(s)
            self.assertTrue(s.say(CHECKIN, check=True)["ok"])

    def test_a_parked_part_may_not_be_mentioned_while_another_part_is_being_worked(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            park_q1(s)
            s.say(LAUNCH_Q2)
            s.turn("attempt", "I think the preference is flat for the negative numbers")
            self.assertIn("REVISIT_MID_PART", codes(s.say("Would you like to go back to Question 1 now?", check=True)))
            self.assertTrue(s.say("What makes it flat there?", check=True)["ok"])

    def test_the_closing_message_must_offer_the_parked_parts_and_end_waits_for_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            park_q1(s)
            s.say(LAUNCH_Q2)
            s.turn("other", "skip this too", skip=True)
            s.say(NUDGE)
            s.turn("other", "skip it", skip=True)                   # SYNTHESIS, both parked
            self.assertEqual(s.view()["state"], "SYNTHESIS")
            self.assertEqual({o["part_id"] for o in s.view()["revisit_offer"]}, {"q1", "q2"})
            with self.assertRaises(Refused) as ctx:
                s.end("big picture")
            self.assertIn("offer", str(ctx.exception))
            self.assertIn("REVISIT_OFFER_MISSING", codes(s.say("That is all for today. Great work.", check=True)))
            self.assertTrue(s.say("That is all for today. Want to go back to Question 1 or Question 2 first?")["ok"])
            out = s.end("Big picture text.")
            self.assertTrue(out["ok"])

    def test_end_is_unaffected_when_nothing_is_parked(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            close_q1(s)
            s.say(CHECKIN)
            s.turn("confirm_advance", "ready to move on")
            s.say("Question 2. How would you like to approach this problem?")
            close_q2(s)
            s.say(CHECKIN)
            s.turn("confirm_advance", "ready to move on")
            self.assertTrue(s.end("Big picture text.")["ok"])


if __name__ == "__main__":
    unittest.main()
