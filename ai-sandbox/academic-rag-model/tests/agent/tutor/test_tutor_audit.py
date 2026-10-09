# tests/agent/tutor/test_tutor_audit.py  (replace the whole file)
import datetime
import tempfile
import unittest

from agent.tutor.audit import audit
from agent.tutor.events import Event
from agent.tutor.packet import Packet, Part
from agent.tutor.paths import TutorPaths
from agent.tutor.sample_packet import write_sample_packet
from agent.tutor.session import Session

NOW = datetime.datetime(2026, 10, 8, 10, 0)
M2 = "walking away is whatever is left over when nothing else is chosen"
M3 = "so it is one minus the sum of the others"


def codes(findings):
    return [f.code for f in findings]


def ev(i, type, part="q1", **kw):
    data = kw.pop("data", {})
    return Event(id=i, ts="t", type=type, part=part, data=data, **kw)


def make(tmp):
    paths = TutorPaths(tmp, "microecon", "homework_4")
    write_sample_packet(paths)
    return Session.start(paths, now=NOW)


class TestAudit(unittest.TestCase):
    def test_clean_session_has_no_findings(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = make(tmp)
            s.say(s.view()["launch_text"])
            s.turn("attempt", M2)
            s.say("You said walking away is whatever is left over. What else is true?")
            self.assertEqual(audit(s.log.load(), s.packet), [])

    def test_unanswered_student_turn_flags_possible_bypass(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = make(tmp)
            s.turn("attempt", "first")
            s.turn("attempt", "second")            # no tutor say in between
            self.assertEqual(codes(audit(s.log.load(), s.packet)), ["UNANSWERED_STUDENT_TURN"])

    def test_manual_overrides_are_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = make(tmp)
            s.turn("attempt", "nobody else picks it so it is the default", establish="C2", establish_quote="nobody else picks it")
            s.say("You said nobody else picks it, so it is the default. What follows?")
            s.turn("attempt", "walking away is sort of unknown", flag_slip="invented", slip_quote="sort of unknown")
            s.say("You said walking away is sort of unknown. What do you mean?")
            s.turn("attempt", "oh I see now", resolve="invented", resolve_quote="I see now")
            found = audit(s.log.load(), s.packet)
            self.assertEqual(codes(found).count("MANUAL_OVERRIDE"), 3)

    def test_verify_release_without_coverage_is_flagged_and_with_coverage_is_not(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = make(tmp)
            s.turn("attempt", M2)
            s.say("You said walking away is whatever is left over. What else is true?")
            s.log.append("verify_release", part="q1", state="WORKING")          # forced past the gate
            self.assertIn("VERIFY_WITHOUT_COVERAGE", codes(audit(s.log.load(), s.packet)))
        with tempfile.TemporaryDirectory() as tmp:
            s = make(tmp)
            s.turn("attempt", M2)
            s.say("You said walking away is whatever is left over. What else is true?")
            s.turn("attempt", M3)
            s.say("You said it is one minus the sum of the others. Why does that hold?")
            s.verify()
            self.assertNotIn("VERIFY_WITHOUT_COVERAGE", codes(audit(s.log.load(), s.packet)))

    def test_tampered_log_findings(self):
        events = [
            ev(1, "session_start"),
            ev(2, "sealed", data={"kind": "solution"}),                                  # v1 log: before any attempt
            ev(3, "student", text="I like pizza", intent="confirm_advance"),            # label contradicts text
            ev(4, "tutor_say", text="ok"),
            ev(5, "student", part="q2", text="hmm", intent="attempt"),                   # part change without confirm_advance
            ev(6, "tutor_say", part="q2", text="ok"),
            ev(7, "student", part="q2", text="a", intent="attempt", hint_level=2),       # hint 0 -> 2 on an attempt
            ev(8, "tutor_say", part="q2", text="ok"),
            ev(9, "close_part", part="q2", hint_level=2, data={"ratings": {
                a: {"rating": "Mastered", "evidence": [7]} for a in ("conceptual", "rigor", "directness")}}),
        ]
        packet = Packet("c", "p", [Part("q1", "s", ["t"], ["e"]), Part("q2", "s", ["t"], ["e"])], {}, {})
        found = codes(audit(events, packet))
        for expected in ("SEALED_EARLY", "INTENT_MISMATCH", "ADVANCE_WITHOUT_CONFIRM", "HINT_JUMP", "RATING_OVER_CEILING"):
            self.assertIn(expected, found)


class TestAuditShowsManualQuotes(unittest.TestCase):
    def test_manual_override_findings_include_the_quote(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = make(tmp)
            s.turn("attempt", "nobody else picks it so it is the default", establish="C2", establish_quote="nobody else picks it")
            details = [f.detail for f in audit(s.log.load(), s.packet) if f.code == "MANUAL_OVERRIDE"]
            self.assertEqual(len(details), 1)
            self.assertIn("nobody else picks it", details[0])
