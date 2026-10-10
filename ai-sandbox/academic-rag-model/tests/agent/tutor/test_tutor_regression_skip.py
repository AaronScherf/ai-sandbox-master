# tests/agent/tutor/test_tutor_regression_skip.py
import tempfile
import unittest

from agent.tutor.audit import audit
from agent.tutor.profile import load_profile, open_gaps
from skip_support import (
    CHECKIN, CHECKIN_OFFER, PROF, Q, close_q1_said, close_q2_said, codes, make,
)

LAUNCH_Q2 = "Question 2. How would you like to approach this problem?"


class TestTrialAnalogueStudentAsksToMoveOn(unittest.TestCase):
    """Live trial 1: the student asked three times to move on and the tutor kept forcing the problem."""

    def test_two_requests_are_enough_and_the_part_can_be_revisited_for_a_capped_rating(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths, s = make(tmp)
            s.say("Question 1. How would you like to approach this problem?")
            s.turn("attempt", "I think it is the default minus something but I am not sure what")        # 14 words: real
            self.assertTrue(s.say("What does the default stand for in your sentence?")["ok"])
            s.turn("other", "I would like to move on to the next question please", skip=True)
            bad = s.say("Let's keep going, you can do this. Think about the probabilities.", check=True)
            self.assertIn("SKIP_NUDGE", codes(bad))
            self.assertTrue(s.say("What is the first thing you would try writing down about the default?")["ok"])
            b = s.turn("other", "no really, can we skip this one", skip=True)
            self.assertEqual((b["part_id"], b["state"]), ("q2", "LAUNCH"))
            self.assertEqual(b["deferred_queue"][0]["status"], "deferred")
            self.assertTrue(s.say("We can come back to it. " + LAUNCH_Q2)["ok"])
            close_q2_said(s)
            self.assertIn("REVISIT_OFFER_MISSING", codes(s.say(CHECKIN, check=True)))
            s.say(CHECKIN_OFFER)
            b = s.turn("revisit", "yes, go back to the first question")
            self.assertEqual((b["part_id"], b["attempt"]), ("q1", 2))
            s.say(Q)
            close_q1_said(s)
            self.assertEqual({r["rating"] for r in s.log.load()[-1].data["ratings"].values()}, {PROF})
            s.say(CHECKIN)
            s.turn("confirm_advance", "yes, I am done, thanks")
            out = s.end("Big picture text.")
            self.assertTrue(out["ok"])
            self.assertEqual([f.code for f in audit(s.log.load(), s.packet)], [])
            prof = load_profile(paths.profile_json)
            statuses = [(h["status"], h["attempt"]) for h in prof["concepts"]["random-consideration-set"]["history"]
                        if h.get("axis", "conceptual") == "conceptual"]
            self.assertEqual(statuses, [("deferred", 1), ("rated", 2)])
            self.assertNotIn("random-consideration-set", open_gaps(prof))

    def test_declining_the_offer_still_ends_cleanly_after_one_last_offer(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            s.turn("other", "skip this", skip=True)
            s.say("What is the first thing you would try here?")
            s.turn("other", "skip", skip=True)
            s.say(LAUNCH_Q2)
            close_q2_said(s)
            s.say(CHECKIN_OFFER)
            s.turn("confirm_advance", "ok, no thanks, let's finish")
            self.assertEqual(s.view()["state"], "SYNTHESIS")
            self.assertEqual(s.view()["revisit_offer"][0]["part_id"], "q1")
            s.say("That is everything for today. Do you want to go back to Question 1 before we stop?")
            out = s.end("Big picture text.")
            self.assertTrue(out["ok"])
            self.assertEqual([f.code for f in audit(s.log.load(), s.packet)], [])


if __name__ == "__main__":
    unittest.main()
