"""Replays the five HW4 beta failures (tutoring_pipeline_meta_lessons_learned.md §2).
Each must be blocked by the FSM, `say` lint, or `close-part`."""
import datetime
import tempfile
import unittest

from agent.tutor.fsm import IllegalTransition
from agent.tutor.paths import TutorPaths
from agent.tutor.ratings import RatingRejected
from agent.tutor.sample_packet import write_sample_packet
from agent.tutor.session import Session

NOW = datetime.datetime(2026, 10, 8, 10, 0)
CHECKIN = "Correct. Do you have any lingering questions, or are you ready to move on?"


def make(tmp):
    paths = TutorPaths(tmp, "microecon", "homework_4")
    write_sample_packet(paths)
    return Session.start(paths, now=NOW)


def codes(result):
    return {v["code"] for v in result.get("violations", [])}


class TestHw4Deviations(unittest.TestCase):
    def test_1_premature_scaffolding_is_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = make(tmp)
            launch = s.view()["launch_text"]
            roadmap = launch + " Assume the first option is better, then cancel the ratio and find an intermediate option."
            self.assertIn("LAUNCH_NOT_VERBATIM", codes(s.say(roadmap)))
            s.student("attempt", "not sure where to begin")
            leak = "Notice it equals one minus the total probability of choosing any item."
            self.assertIn("SEALED_OVERLAP", codes(s.say(leak)))

    def test_2_unsolicited_advancement_is_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = make(tmp)
            s.student("attempt", "answer")
            s.verdict("correct")
            self.assertIn("NEXT_PART_REFERENCE", codes(s.say("Correct. Now on to Question 2!")))
            att = [e for e in s.log.load() if e.type == "student"][0].id
            s.close_part({a: {"rating": "Mastered", "evidence": [att]} for a in ("conceptual", "rigor", "directness")})
            self.assertTrue(s.say(CHECKIN)["ok"])
            self.assertEqual(s.view()["part_id"], "q1")  # still on the same part until the student confirms
            self.assertEqual(s.student("confirm_advance", "ready")["part_id"], "q2")

    def test_3_over_bridging_a_definition_is_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = make(tmp)
            s.student("define_request", "what is choice overload?")
            s.define("choice overload")
            bridged = "Choice overload is when people walk away, which is your default alternative d from Part 1."
            self.assertIn("NOTATION_BRIDGE", codes(s.say(bridged)))

    def test_4_prescribing_a_proof_technique_is_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = make(tmp)
            s.student("attempt", "I'm not sure how to start the non-concavifiability proof")
            prescribe = "Suppose, for the sake of contradiction, that f is concave.\n1. What if x is at most 0?\n2. What if x is positive?"
            self.assertTrue({"TECHNIQUE", "SUBQUESTION_LIST"} <= codes(s.say(prescribe)))
            s.student("other", "maybe contradiction works?")
            self.assertTrue(s.say("Contradiction is a fine option. What would you assume?")["ok"])

    def test_5_grade_inflation_is_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = make(tmp)
            s.student("attempt", "closed sets must be bounded", misconceptions=(("closed-implies-bounded", "all"),))
            s.student("stuck", "I'm stuck")
            s.student("hint_request", "can I get a hint?")
            s.verdict("correct")
            att = [e for e in s.log.load() if e.type == "student"][0].id
            inflated = {a: {"rating": "Proficient", "evidence": [att]} for a in ("conceptual", "rigor", "directness")}
            with self.assertRaises(RatingRejected):
                s.close_part(inflated)
            frank = {a: {"rating": "Developing / Needs Review", "evidence": [att]} for a in ("conceptual", "rigor", "directness")}
            s.close_part(frank)

    def test_confirm_cannot_be_smuggled_in_mid_problem(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = make(tmp)
            s.student("attempt", "working on it")
            with self.assertRaises(IllegalTransition):
                s.student("confirm_advance", "ok next")
