import tempfile
import unittest

from agent.tutor.session import Refused
from agent.tutor.skip import (
    MIN_ATTEMPT_WORDS, counts_as_skip, is_real_attempt, mentions_skip, words_outside_skip,
)
from skip_support import M1, M2, make, park_q1


class TestDetectors(unittest.TestCase):
    def test_phrases(self):
        for text in ("can we skip this", "let's move on", "next question please", "I'll come back to it", "skipping"):
            self.assertTrue(mentions_skip(text), text)
        for text in ("I think it is the sum", "the next step is to add them"):
            self.assertFalse(mentions_skip(text), text)

    def test_words_outside_skip_phrases(self):
        self.assertEqual(words_outside_skip("please skip this one, let's move on"), 4)
        self.assertGreaterEqual(MIN_ATTEMPT_WORDS, 1)

    def test_real_attempt_rules(self):
        long = "I think the answer has to do with how the other options are treated here"
        self.assertTrue(is_real_attempt("attempt", long, False, False))
        self.assertFalse(is_real_attempt("attempt", "I do not know where to start", False, False))
        self.assertFalse(is_real_attempt("other", long, False, False))              # only attempt turns by length
        self.assertTrue(is_real_attempt("other", "short", True, False))              # a recognizer matched
        self.assertFalse(is_real_attempt("attempt", long, False, True))              # an admitted gap is not an attempt
        self.assertFalse(is_real_attempt("attempt", "skip skip skip skip move on please next question " * 2, False, False))

    def test_counts_as_skip(self):
        self.assertTrue(counts_as_skip("other", "whatever", True, True))             # explicit flag
        self.assertTrue(counts_as_skip("other", "let's move on", False, True))       # phrase, non-attempt intent
        self.assertFalse(counts_as_skip("attempt", "then move on to the next step by adding", False, True))
        self.assertTrue(counts_as_skip("attempt", "whatever", True, True))
        self.assertFalse(counts_as_skip("other", "let's move on", False, False))     # closed part: confirm_advance's job
        self.assertFalse(counts_as_skip("confirm_advance", "move on", True, True))


class TestTurnSkip(unittest.TestCase):
    def test_first_request_counts_and_keeps_the_part(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            b = s.turn("other", "I would rather skip this one")
            self.assertEqual((b["part_id"], b["state"], b["skip_requests"]), ("q1", "WORKING", 1))
            ev = s.log.load()[-1]
            self.assertTrue(ev.data["skip"])
            self.assertEqual(ev.data["skip_count"], 1)

    def test_an_attempt_that_merely_contains_a_skip_phrase_is_not_a_skip(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            b = s.turn("attempt", "first I move on to the next step and multiply the probabilities")
            self.assertEqual(b["skip_requests"], 0)
            self.assertFalse(s.log.load()[-1].data.get("skip"))

    def test_the_flag_counts_even_with_an_attempt_intent(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            self.assertEqual(s.turn("attempt", "no idea", skip=True)["skip_requests"], 1)

    def test_second_request_parks_the_part_and_launches_the_next(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            b = park_q1(s)
            self.assertEqual((b["part_id"], b["state"]), ("q2", "LAUNCH"))
            self.assertEqual(b["launch_text"], "Question 2. How would you like to approach this problem?")
            self.assertEqual(b["deferred_queue"], [{"part_id": "q1", "label": "Question 1", "status": "skipped"}])
            self.assertEqual(b["parked"], {"part_id": "q1", "label": "Question 1", "status": "skipped"})
            events = s.log.load()
            ending = [e for e in events if e.type == "student"][-1]
            self.assertEqual((ending.part, ending.data["skip_ended"]), ("q1", True))   # logged under the parked part
            status = [e for e in events if e.type == "part_status"][-1]
            self.assertEqual((status.part, status.data["status"], status.data["attempt"], status.data["real_attempt"]),
                             ("q1", "skipped", 1, False))
            self.assertEqual(s.turn("attempt", "just a first try at the new one")["claims_established"], [])

    def test_a_recognized_claim_before_skipping_makes_it_deferred(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            b = park_q1(s, with_attempt=True)
            self.assertEqual(b["deferred_queue"][0]["status"], "deferred")
            self.assertTrue([e for e in s.log.load() if e.type == "part_status"][-1].data["real_attempt"])

    def test_a_long_attempt_is_real_but_an_admitted_gap_is_not(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            s.turn("attempt", "I really am not sure but I think the others somehow matter here", admits_gap="all")
            self.assertFalse(s.log.load()[-1].data["real_attempt"])
            s.turn("attempt", "I think it is about how the other options are treated in the model")
            self.assertTrue(s.log.load()[-1].data["real_attempt"])

    def test_words_in_the_ending_message_still_count_for_the_parked_part(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            s.turn("other", "skip please", skip=True)
            s.say(NUDGE_TEXT)
            s.turn("attempt", M2 + " but let us skip it", skip=True)
            b = s.view()
            self.assertEqual(b["part_id"], "q2")
            self.assertEqual(b["deferred_queue"][0]["status"], "deferred")   # the claim in the ending message was a real attempt
            self.assertEqual(s.turn("attempt", "something about the preference")["claims_established"], [])


NUDGE_TEXT = "What is the first thing you would try here?"


class TestRevisitTurn(unittest.TestCase):
    def test_revisit_needs_a_parked_part_and_the_right_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            with self.assertRaises(Exception):
                s.turn("revisit", "go back to question one")                 # state LAUNCH: illegal

    def test_ambiguous_or_unknown_part_is_refused_with_the_options(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            park_q1(s)
            s.turn("other", "skip this too", skip=True)
            s.say(NUDGE_TEXT)
            s.turn("other", "skip", skip=True)                                  # both parked -> SYNTHESIS
            self.assertEqual(s.view()["state"], "SYNTHESIS")
            with self.assertRaises(Refused) as ctx:
                s.turn("revisit", "go back please")
            self.assertIn("q1", str(ctx.exception))
            self.assertIn("q2", str(ctx.exception))
            with self.assertRaises(Refused):
                s.turn("revisit", "go back please", revisit_part="q9")
            b = s.turn("revisit", "go back please", revisit_part="Question 2")
            self.assertEqual((b["part_id"], b["state"], b["attempt"]), ("q2", "WORKING", 2))


if __name__ == "__main__":
    unittest.main()
