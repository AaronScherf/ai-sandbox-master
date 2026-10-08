import os
import tempfile
import unittest

from agent.tutor.events import Event
from agent.tutor.packet import Packet, Part
from agent.tutor.profile import SCHEMA_VERSION, load_profile, open_gaps, render_profile_md, save_profile, update_profile
from agent.tutor.render import render_summary, render_transcript, write_session_docs

DEV, PROF = "Developing / Needs Review", "Proficient"


def ev(i, type, part="q1", **kw):
    data = kw.pop("data", {})
    return Event(id=i, ts="t", type=type, part=part, data=data, **kw)


def ratings(conc, rigor, direct, evidence):
    return {"conceptual": {"rating": conc, "evidence": evidence}, "rigor": {"rating": rigor, "evidence": evidence},
            "directness": {"rating": direct, "evidence": evidence}}


PACKET = Packet("microecon", "homework_4", [
    Part("q1", "S1", ["random-consideration-set"], ["e"], label="Question 1"),
    Part("q2", "S2", ["concavity"], ["e"], label="Question 2"),
], {}, {})
EVENTS = [
    ev(1, "student", text="I think the set is bounded", intent="attempt"),
    ev(2, "tutor_say", text="What does closed mean here?"),
    ev(3, "misconception", data={"tag": "closed-implies-bounded", "axis": "all"}),
    ev(4, "close_part", data={"ratings": ratings(DEV, DEV, PROF, [1])}),
    ev(5, "student", part="q2", text="ok next", intent="confirm_advance"),
    ev(6, "close_part", part="q2", data={"ratings": ratings(PROF, PROF, PROF, [5])}),
]


class TestRender(unittest.TestCase):
    def test_transcript_lists_student_and_tutor_turns_only(self):
        t = render_transcript(EVENTS)
        self.assertIn("**Student:** I think the set is bounded", t)
        self.assertIn("**Tutor:** What does closed mean here?", t)
        self.assertNotIn("closed-implies-bounded", t)

    def test_summary_has_four_sections_with_calibrated_ratings(self):
        s = render_summary(EVENTS, PACKET, "Big picture prose.", ["concavity"], "2026-10-08")
        for heading in ("## 1. Diagnostic", "## 2. Big Picture", "## 3. Tri-Axial Rubric", "## 4. Action Menu"):
            self.assertIn(heading, s)
        self.assertIn("Big picture prose.", s)
        self.assertIn("Conceptual Fluency", s)
        self.assertIn("I think the set is bounded", s)  # event-id evidence rendered as the quote
        self.assertIn("random-consideration-set", s.split("## 4. Action Menu")[1])  # Developing part -> review item
        self.assertIn("concavity", s.split("## 4. Action Menu")[1])  # previously flagged gap carried forward

    def test_write_session_docs(self):
        with tempfile.TemporaryDirectory() as tmp:
            t, s = write_session_docs(tmp, EVENTS, PACKET, "bp", [], "2026-10-08")
            self.assertTrue(os.path.exists(t) and os.path.exists(s))


class TestProfile(unittest.TestCase):
    def test_missing_profile_is_empty_versioned(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = load_profile(os.path.join(tmp, "nope.json"))
            self.assertEqual(p, {"schema_version": SCHEMA_VERSION, "concepts": {}})

    def test_update_records_history_and_open_misconceptions(self):
        p = update_profile(load_profile("/nonexistent"), session_id="2026-10-08-1000", date="2026-10-08", events=EVENTS, packet=PACKET)
        hist = p["concepts"]["random-consideration-set"]["history"]
        self.assertEqual({(h["axis"], h["rating"]) for h in hist}, {("conceptual", DEV), ("rigor", DEV), ("directness", PROF)})
        self.assertEqual(p["concepts"]["random-consideration-set"]["open_misconceptions"], ["closed-implies-bounded"])
        self.assertEqual(p["concepts"]["concavity"]["open_misconceptions"], [])

    def test_resolved_misconception_is_not_left_open(self):
        events = EVENTS + [ev(7, "misconception_resolved", data={"tag": "closed-implies-bounded"})]
        p = update_profile(load_profile("/nonexistent"), session_id="s", date="d", events=events, packet=PACKET)
        self.assertEqual(p["concepts"]["random-consideration-set"]["open_misconceptions"], [])

    def test_open_gaps_uses_latest_session_and_open_misconceptions(self):
        p = update_profile(load_profile("/nonexistent"), session_id="2026-10-01-1000", date="2026-10-01", events=EVENTS, packet=PACKET)
        self.assertEqual(open_gaps(p), ["random-consideration-set"])
        better = [ev(1, "close_part", data={"ratings": ratings(PROF, PROF, PROF, [1])})]
        p2 = update_profile(p, session_id="2026-10-08-1000", date="2026-10-08", events=better, packet=PACKET)
        # Latest rating is fine but the misconception from the earlier session is still open.
        self.assertEqual(open_gaps(p2), ["random-consideration-set"])
        fixed = better + [ev(2, "misconception_resolved", data={"tag": "closed-implies-bounded"})]
        p3 = update_profile(p, session_id="2026-10-09-1000", date="2026-10-09", events=fixed, packet=PACKET)
        self.assertEqual(open_gaps(p3), [])

    def test_save_and_reload_round_trip_and_md(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = update_profile(load_profile("/nonexistent"), session_id="s", date="d", events=EVENTS, packet=PACKET)
            jp, mp = os.path.join(tmp, "p.json"), os.path.join(tmp, "p.md")
            save_profile(jp, mp, p)
            self.assertEqual(load_profile(jp), p)
            with open(mp, encoding="utf-8") as f:
                self.assertIn("random-consideration-set", f.read())
            self.assertIn("random-consideration-set", render_profile_md(p))
