# tests/agent/tutor/test_tutor_ledger.py
import unittest

from agent.tutor.claims import parse_claims
from agent.tutor.events import Event
from agent.tutor.ledger import build_ledger, next_claim

RAW = {"p1": {
    "claims": [
        {"id": "C1", "text": "considered", "object_terms": [],
         "recognizer": {"all": [["consider*"], ["chosen", "best"]], "window": 12}},
        {"id": "C2", "text": "others excluded", "object_terms": [],
         "recognizer": {"all": [["consider*"], ["better", "higher"], ["not", "never", "fail*"]], "window": 14}},
        {"id": "C3", "text": "product", "object_terms": [],
         "recognizer": {"all": [["independen*"], ["multipl*", "product", "together"]], "window": 12}},
        {"id": "D1", "text": "alt route claim", "object_terms": [],
         "recognizer": {"all": [["complement*"]], "window": 4}}],
    "routes": {"A": ["C1", "C2", "C3"], "B": ["C1", "D1"]},
    "pitfalls": [{"id": "P1", "tag": "adds", "axis": "rigor", "resolved_by": "C3",
                  "recognizer": {"all": [["independen*"], ["add", "sum"]], "window": 12},
                  "repair_question": "add or multiply?"}]}}
PC = parse_claims(RAW, ["p1"])[0]["p1"]


def student(i, text, intent="attempt"):
    return Event(id=i, ts="t", type="student", part="p1", intent=intent, text=text)


class TestBuildLedger(unittest.TestCase):
    def test_claims_are_established_in_event_order(self):
        events = [student(1, "a must be considered to be chosen"),
                  student(2, "higher items must not be considered")]
        led = build_ledger(PC, events)
        self.assertEqual(led.established, ["C1", "C2"])
        self.assertEqual(led.manual, [])
        self.assertEqual(led.route_progress, {"A": (2, 3), "B": (1, 2)})
        self.assertIsNone(led.covered_route)
        self.assertFalse(led.covered)

    def test_a_route_covers_the_part(self):
        events = [student(1, "considered and chosen"), student(2, "independent so multiply")]
        led = build_ledger(PC, events + [Event(id=3, ts="t", type="establish", part="p1",
                                               data={"claim": "C2", "quote": "x"})])
        self.assertEqual(led.established, ["C1", "C3", "C2"])
        self.assertEqual(led.manual, ["C2"])
        self.assertEqual(led.covered_route, "A")
        self.assertTrue(led.covered)

    def test_alternative_route_also_covers(self):
        led = build_ledger(PC, [student(1, "it is considered and chosen"), student(2, "take the complement")])
        self.assertEqual(led.covered_route, "B")

    def test_pitfalls_are_detected_once(self):
        led = build_ledger(PC, [student(1, "independent events so we add them"), student(2, "independent so I sum")])
        self.assertEqual(led.pitfalls_hit, ["P1"])

    def test_confirm_advance_define_request_and_tutor_events_are_ignored(self):
        events = [student(1, "considered and chosen", intent="confirm_advance"),
                  student(3, "what does considered mean for the chosen item", intent="define_request"),
                  Event(id=2, ts="t", type="tutor_say", part="p1", text="independent so multiply")]
        self.assertEqual(build_ledger(PC, events).established, [])

    def test_extra_student_text_is_a_virtual_last_message(self):
        led = build_ledger(PC, [], extra_student_text="considered and chosen")
        self.assertEqual(led.established, ["C1"])

    def test_final_answer_is_required_for_coverage_when_defined(self):
        raw = {"p1": {**RAW["p1"], "final_answer": {"all": [["answer"]], "window": 4}}}
        pc = parse_claims(raw, ["p1"])[0]["p1"]
        events = [student(1, "considered and chosen"), student(2, "complement")]
        self.assertFalse(build_ledger(pc, events).covered)
        self.assertTrue(build_ledger(pc, events + [student(3, "the answer is 3")]).covered)


class TestNextClaim(unittest.TestCase):
    def test_follows_the_route_with_most_progress(self):
        led = build_ledger(PC, [student(1, "considered and chosen"), student(2, "independent so multiply")])
        self.assertEqual(next_claim(PC, led).id, "C2")          # route A has 2/3, B has 1/2

    def test_ties_go_to_the_first_listed_route_and_covered_returns_none(self):
        self.assertEqual(next_claim(PC, build_ledger(PC, [])).id, "C1")
        led = build_ledger(PC, [student(1, "considered and chosen"), student(2, "complement")])
        self.assertIsNone(next_claim(PC, led))
