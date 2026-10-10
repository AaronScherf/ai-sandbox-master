# tests/agent/tutor/test_tutor_profile_v2.py
import json
import os
import tempfile
import unittest

from agent.tutor.profile import SCHEMA_VERSION, load_profile, open_gaps, render_profile_md, save_profile, update_profile
from skip_support import CHECKIN_OFFER, DEV, close_q1, close_q2, make, park_q1

LAUNCH_Q2 = "Question 2. How would you like to approach this problem?"
V1 = {"schema_version": 1, "concepts": {
    "concavity": {"history": [{"session": "2026-09-01-1000", "date": "2026-09-01", "part": "q2", "axis": "rigor",
                               "rating": DEV}], "open_misconceptions": []}}}


def entries(profile, tag):
    return profile["concepts"][tag]["history"]


class TestProfileV2(unittest.TestCase):
    def test_a_v1_file_loads_as_v2_with_every_entry_rated(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, "learner_profile.json")
            with open(p, "w", encoding="utf-8") as f:
                json.dump(V1, f)
            prof = load_profile(p)
            self.assertEqual(prof["schema_version"], SCHEMA_VERSION)
            self.assertEqual(SCHEMA_VERSION, 2)
            h = entries(prof, "concavity")[0]
            self.assertEqual((h["status"], h["attempt"], h["rating"]), ("rated", 1, DEV))
            self.assertEqual(open_gaps(prof), ["concavity"])

    def test_skipped_and_deferred_attempts_are_recorded_without_ratings(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            park_q1(s, with_attempt=True)             # q1 deferred
            s.say(LAUNCH_Q2)
            close_q2(s)
            prof = update_profile(load_profile(s.paths.profile_json), session_id=s.session_id, date="2026-10-09",
                                  events=s.log.load(), packet=s.packet)
            q1 = [h for h in entries(prof, "random-consideration-set")]
            self.assertEqual([(h["part"], h["status"], h["attempt"]) for h in q1], [("q1", "deferred", 1)])
            self.assertNotIn("rating", q1[0])
            self.assertEqual(open_gaps(prof), ["default-alternative", "random-consideration-set"])

    def test_a_skipped_part_is_not_a_gap(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            park_q1(s)
            prof = update_profile(load_profile(s.paths.profile_json), session_id=s.session_id, date="2026-10-09",
                                  events=s.log.load(), packet=s.packet)
            self.assertEqual(entries(prof, "random-consideration-set")[0]["status"], "skipped")
            self.assertEqual(open_gaps(prof), [])

    def test_a_later_rated_revisit_closes_the_deferred_gap_and_both_attempts_stay(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            park_q1(s, with_attempt=True)
            s.say(LAUNCH_Q2)
            close_q2(s)
            s.say(CHECKIN_OFFER)
            s.turn("revisit", "go back to the first question")
            close_q1(s)
            prof = update_profile(load_profile(s.paths.profile_json), session_id=s.session_id, date="2026-10-09",
                                  events=s.log.load(), packet=s.packet)
            q1 = [(h["status"], h["attempt"]) for h in entries(prof, "random-consideration-set")
                  if h["part"] == "q1" and h.get("axis", "conceptual") == "conceptual"]
            self.assertEqual(q1, [("deferred", 1), ("rated", 2)])
            self.assertNotIn("random-consideration-set", open_gaps(prof))

    def test_updating_twice_for_the_same_session_does_not_duplicate_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            close_q1(s)
            args = dict(session_id=s.session_id, date="2026-10-09", events=s.log.load(), packet=s.packet)
            once = update_profile(load_profile(s.paths.profile_json), **args)
            twice = update_profile(once, **args)
            self.assertEqual(once, twice)

    def test_markdown_renders_all_statuses_without_crashing(self):
        prof = {"schema_version": 2, "concepts": {"t": {"history": [
            {"session": "s1", "date": "2026-10-09", "part": "q1", "status": "deferred", "attempt": 1},
            {"session": "s1", "date": "2026-10-09", "part": "q2", "status": "skipped", "attempt": 1},
            {"session": "s1", "date": "2026-10-09", "part": "q1", "status": "rated", "attempt": 2, "axis": "rigor", "rating": DEV}],
            "open_misconceptions": []}}}
        text = render_profile_md(prof)
        self.assertIn("deferred", text)
        self.assertIn("skipped", text)
        self.assertIn("(attempt 2)", text)


if __name__ == "__main__":
    unittest.main()
