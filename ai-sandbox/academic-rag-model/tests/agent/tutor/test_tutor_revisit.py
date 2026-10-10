# tests/agent/tutor/test_tutor_revisit.py
import os
import tempfile
import unittest

from agent.tutor.render import render_summary
from agent.tutor.status import attempt_records, final_status
from skip_support import CHECKIN, CHECKIN_OFFER, DEV, MAST, PROF, close_q1, close_q2, cover_q1, make, park_q1

LAUNCH_Q2 = "Question 2. How would you like to approach this problem?"


def revisit_q1(s, deferred=False):
    park_q1(s, with_attempt=deferred)
    s.say(LAUNCH_Q2)
    close_q2(s)
    s.say(CHECKIN_OFFER)
    return s.turn("revisit", "yes let's go back to the first question")


class TestRevisitScoring(unittest.TestCase):
    def test_a_clean_revisit_is_capped_at_proficient_everywhere(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            b = revisit_q1(s)
            self.assertEqual((b["part_id"], b["state"], b["attempt"]), ("q1", "WORKING", 2))
            closed = close_q1(s)
            ratings = s.log.load()[-1].data["ratings"]
            self.assertTrue(closed["closed"])
            self.assertEqual({r["rating"] for r in ratings.values()}, {PROF})
            self.assertEqual(s.log.load()[-1].data["attempt"], 2)
            revisit_id = next(e.id for e in s.log.load() if e.type == "student" and e.intent == "revisit")
            self.assertTrue(all(revisit_id in r["evidence"] for r in ratings.values()))

    def test_a_part_never_parked_keeps_mastered(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            close_q1(s)
            ratings = s.log.load()[-1].data["ratings"]
            self.assertEqual({r["rating"] for r in ratings.values()}, {MAST})
            self.assertEqual(s.log.load()[-1].data["attempt"], 1)

    def test_the_revisited_part_keeps_its_claims_and_hint_level(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            s.turn("stuck", "I am stuck")                           # hint level 1
            s.turn("attempt", "walking away is whatever is left over when nothing else is chosen")   # C2
            s.turn("other", "skip", skip=True)
            s.say("What is the first thing you would try here?")
            s.turn("other", "skip it please", skip=True)
            s.say(LAUNCH_Q2)
            close_q2(s)
            s.say(CHECKIN_OFFER)
            b = s.turn("revisit", "go back to the first one")
            self.assertEqual((b["hint_level"], b["claims_established"]), (1, ["C2"]))


class TestStatusAndSummary(unittest.TestCase):
    def test_attempt_records_and_final_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            revisit_q1(s, deferred=True)
            close_q1(s)
            events = s.log.load()
            recs = [(r["part"], r["attempt"], r["status"]) for r in attempt_records(events)]
            self.assertEqual(recs, [("q1", 1, "deferred"), ("q2", 1, "rated"), ("q1", 2, "rated")])
            self.assertEqual(final_status(events, "q1"), "rated")
            self.assertIsNone(final_status(events[:1], "q1"))

    def test_final_status_while_parked_and_revisiting(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            park_q1(s)
            self.assertEqual(final_status(s.log.load(), "q1"), "skipped")
            s.say(LAUNCH_Q2)
            close_q2(s)
            s.say(CHECKIN_OFFER)
            s.turn("revisit", "let's go back")
            self.assertEqual(final_status(s.log.load(), "q1"), "revisiting")

    def test_summary_marks_parked_parts_and_lists_them_in_the_action_menu(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            park_q1(s, with_attempt=True)
            s.say(LAUNCH_Q2)
            close_q2(s)
            s.say(CHECKIN_OFFER)
            events = s.log.load()
            text = render_summary(events, s.packet, "Big picture.", [], "2026-10-09")
            self.assertIn("| Question 1 |", text)
            self.assertIn("deferred", text)
            self.assertIn("Revisit `random-consideration-set`", text)
            skipped = make(tempfile.mkdtemp())[1]
            park_q1(skipped)
            text2 = render_summary(skipped.log.load(), skipped.packet, "Big picture.", [], "2026-10-09")
            self.assertIn("not covered", text2)
            self.assertNotIn("Revisit `random-consideration-set`", text2)


if __name__ == "__main__":
    unittest.main()
