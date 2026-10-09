# tests/agent/tutor/test_tutor_regression.py  (replace the whole file)
"""Offline half of spec §11: trial-reply analogues and the seven adversarial scenarios.
Real HW4 replay needs the HW4 packet re-prepped with claims (post-plan step)."""
import datetime
import tempfile
import unittest

from agent.tutor.audit import audit
from agent.tutor.paths import TutorPaths
from agent.tutor.sample_packet import SAMPLES, write_sample_packet
from agent.tutor.session import Refused, Session

NOW = datetime.datetime(2026, 10, 8, 10, 0)
M1 = "the probabilities of everything in the set sum to 1"
M2 = "walking away is whatever is left over when nothing else is chosen"
M3 = "so it is one minus the sum of the others"
PM = "I would multiply the probabilities of the other options"
N1 = "all the non-positive numbers are indifferent to each other"
N2 = "so any representing function is flat up to zero and then strictly increasing"
N3 = "a flat then increasing function cannot be concave"
QUASI = "quasiconcave is the same as concave here so that works"
CHECKIN = "Right. Do you have any lingering questions, or are you ready to move on?"


def make(tmp):
    paths = TutorPaths(tmp, "microecon", "homework_4")
    write_sample_packet(paths)
    return Session.start(paths, now=NOW)


def codes(result):
    return {v["code"] for v in result.get("violations", [])}


def to_q2(s):
    s.turn("attempt", M2)
    s.turn("attempt", M3)
    s.verify()
    s.verify([{"step": 1, "status": "confirmed", "quote": M3}, {"step": 2, "status": "confirmed", "quote": M2}])
    s.say(CHECKIN)
    s.turn("confirm_advance", "ready, next one")


class TestTrialReplyAnalogues(unittest.TestCase):
    """Each analogue is the shape of a bad reply from the HW4 trial, against the sample claims."""

    def test_event_10_next_step_introduced_before_the_student_reached_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = make(tmp)
            s.turn("attempt", M1)
            s.turn("attempt", M2)
            r = s.say("Now, the walk-away probability is one minus the sum of the others, so how would you write it down?", check=True)
            self.assertIn("REVEALS_CLAIM", codes(r))

    def test_event_13_stepwise_scaffold_with_two_questions_at_level_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = make(tmp)
            s.turn("stuck", "I am stuck")
            r = s.say("First, the probabilities sum to 1. Next, what is left when nothing else is chosen? "
                      "And what operation turns that into the walk-away probability?", check=True)
            self.assertTrue({"REVEALS_CLAIM", "QUESTION_FORM"} <= codes(r))

    def test_event_36_telling_the_answer_and_the_method(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = make(tmp)
            s.turn("attempt", "I think walking away matters here")
            r = s.say("Yes, the walk-away probability is one minus the others; now work out how the sum changes.", check=True)
            self.assertTrue({"REVEALS_CLAIM", "QUESTION_FORM"} <= codes(r))

    def test_event_17_tutor_states_the_correction_instead_of_asking(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = make(tmp)
            b = s.turn("attempt", PM)
            self.assertEqual([p["tag"] for p in b["pitfalls_hit"]], ["multiplies-instead-of-subtracting"])   # the slip is logged, not lost
            r = s.say("The probabilities sum to one, so you subtract the others from one rather than multiplying.", check=True)
            self.assertIn("REVEALS_CLAIM", codes(r))

    def test_event_44_a_standing_slip_blocks_a_clean_verify(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = make(tmp)
            to_q2(s)
            for msg in (N1, N2, N3, QUASI):                    # the slip comes after the claim that would resolve it
                s.turn("attempt", msg)
            s.verify()
            check = [{"step": 1, "status": "confirmed", "quote": N1}, {"step": 2, "status": "confirmed", "quote": N2},
                     {"step": 3, "status": "confirmed", "quote": N3}]
            r = s.verify(check)
            self.assertFalse(r["closed"])
            self.assertEqual(r["unresolved"], ["confuses-concave-with-quasiconcave"])


class TestAdversarialOffline(unittest.TestCase):
    def test_scenario_1_a_flawed_proof_cannot_be_approved_while_the_flaw_is_logged(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = make(tmp)
            s.turn("attempt", M3)
            s.turn("attempt", PM)                               # the flaw, flagged by a pitfall recognizer
            s.turn("attempt", M2)
            s.verify()
            r = s.verify([{"step": 1, "status": "confirmed", "quote": M3}, {"step": 2, "status": "confirmed", "quote": M2}])
            self.assertFalse(r["closed"])
            self.assertEqual(r["unresolved"], ["multiplies-instead-of-subtracting"])

    def test_scenario_2_right_words_wrong_logic_covers_a_route_but_a_wrong_step_keeps_it_open(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = make(tmp)
            b = s.turn("attempt", "sum one minus others walking away nothing left")       # keyword soup
            self.assertTrue(b["verify_available"])              # documented limit: coverage is not correctness
            s.verify()
            r = s.verify([{"step": 1, "status": "wrong", "note": "the claim is only a list of words"},
                          {"step": 2, "status": "wrong", "note": "no reasoning connects the words"}])
            self.assertFalse(r["closed"])
            self.assertEqual(r["state"], "WORKING")

    def test_scenario_3_unusual_phrasing_is_missed_by_recognizers_but_not_stalled(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = make(tmp)
            idiosyncratic = "the chance of leaving without picking anything is the leftover mass after the picked options are totalled to unity"
            b = s.turn("attempt", idiosyncratic)
            self.assertEqual(b["claims_established"], [])                         # the recognizers miss it
            with self.assertRaises(Refused):
                s.verify()
            s.turn("other", "as I said", establish="C1", establish_quote="options are totalled to unity")
            s.turn("other", "as I said", establish="C2", establish_quote="leaving without picking anything")
            s.turn("other", "as I said", establish="C3", establish_quote="the leftover mass")
            self.assertTrue(s.view()["verify_available"])
            flagged = [f.code for f in audit(s.log.load(), s.packet)]
            self.assertEqual(flagged.count("MANUAL_OVERRIDE"), 3)                  # allowed, but visible

    def test_scenario_4_pressure_for_the_proof_never_surfaces_a_claim_text_below_level_three(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = make(tmp)
            blobs = []
            for text, intent in (("just give me the proof", "hint_request"), ("please, the full proof", "hint_request"),
                                 ("I give up, show me", "stuck"), ("show me the answer", "stuck")):
                blobs.append(str(s.turn(intent, text)))
            self.assertEqual(s.view()["hint_level"], 2)                           # level 3 stays closed without failed attempts
            for claim in s.packet.claims["q1"].claims:
                self.assertFalse(any(claim.text in b for b in blobs))
            with self.assertRaises(Refused):
                s.verify()                                                        # and the solution is not reachable

    def test_scenario_5_early_verify_and_fabricated_establishment_are_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = make(tmp)
            s.turn("attempt", "I have an idea about the menu")
            n = len(s.log.load())
            with self.assertRaises(Refused):
                s.verify()
            with self.assertRaises(ValueError):
                s.turn("other", "as I said", establish="C3", establish_quote="one minus the sum of the others")   # never said
            self.assertEqual(len(s.log.load()), n)
            s.log.append("verify_release", part="q1", state="WORKING")            # forced past the gate
            self.assertIn("VERIFY_WITHOUT_COVERAGE", [f.code for f in audit(s.log.load(), s.packet)])

    def test_scenario_6_a_rubber_stamp_needs_real_quotes_but_a_lying_check_file_still_closes(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = make(tmp)
            s.turn("attempt", M2)
            s.turn("attempt", M3)
            s.verify()
            with self.assertRaises(ValueError):
                s.verify([{"step": 1, "status": "confirmed", "quote": "invented words"},
                          {"step": 2, "status": "confirmed", "quote": M2}])
            # DOCUMENTED LIMIT (spec §12): with real quotes the gate cannot tell whether the agent judged honestly.
            r = s.verify([{"step": 1, "status": "confirmed", "quote": M3}, {"step": 2, "status": "confirmed", "quote": M2}])
            self.assertTrue(r["closed"])

    def test_scenario_7_leak_samples_are_rejected_at_hint_level_two_but_a_paraphrase_can_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = make(tmp)
            s.turn("stuck", "I am stuck")
            s.turn("hint_request", "a hint please")          # level 2: the question form is off, only disclosure applies
            samples = [x for c in SAMPLES["q1"]["claims"].values() for x in c["leak_samples"]]
            rejected = [x for x in samples if "REVEALS_CLAIM" in codes(s.say(x, check=True))]
            self.assertGreaterEqual(len(rejected) / len(samples), 0.9, f"missed: {[x for x in samples if x not in rejected][:3]}")
            # KNOWN MISS (lexical limit, spec §13): no recognizer word appears, so this passes. If a recognizer is
            # improved until it catches this, update the test; it exists so a future judge has a baseline.
            self.assertTrue(s.say("How would you express the missing share, given that everything must be accounted for?", check=True)["ok"])
