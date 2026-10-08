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


def codes(findings):
    return [f.code for f in findings]


def ev(i, type, part="q1", **kw):
    data = kw.pop("data", {})
    return Event(id=i, ts="t", type=type, part=part, data=data, **kw)


class TestAudit(unittest.TestCase):
    def _session(self, tmp):
        paths = TutorPaths(tmp, "microecon", "homework_4")
        write_sample_packet(paths)
        return Session.start(paths, now=NOW)

    def test_clean_session_has_no_findings(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = self._session(tmp)
            s.say(s.view()["launch_text"])
            s.student("attempt", "my try")
            s.say("What made you choose that?")
            self.assertEqual(audit(s.log.load(), s.packet), [])

    def test_unanswered_student_turn_flags_possible_bypass(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = self._session(tmp)
            s.student("attempt", "first")
            s.student("attempt", "second")  # no tutor say in between
            # Only the first turn is flagged: the second is still pending and the session has not ended.
            self.assertEqual(codes(audit(s.log.load(), s.packet)), ["UNANSWERED_STUDENT_TURN"])

    def test_tampered_log_findings(self):
        events = [
            ev(1, "session_start"),
            ev(2, "sealed", data={"kind": "solution"}),                                  # before any attempt
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
