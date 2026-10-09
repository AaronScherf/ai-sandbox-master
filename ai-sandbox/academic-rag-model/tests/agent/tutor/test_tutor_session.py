import datetime
import os
import tempfile
import unittest

from agent.tutor.events import EventLog
from agent.tutor.fsm import IllegalTransition
from agent.tutor.paths import TutorPaths
from agent.tutor.ratings import RatingRejected
from agent.tutor.sample_packet import write_sample_packet
from agent.tutor.session import Session

NOW = datetime.datetime(2026, 10, 8, 10, 0)
DEV, PROF, MAST = "Developing / Needs Review", "Proficient", "Mastered"


def make(tmp):
    paths = TutorPaths(tmp, "microecon", "homework_4")
    write_sample_packet(paths)
    return paths, Session.start(paths, now=NOW)


def rate(rating, evidence):
    return {a: {"rating": rating, "evidence": evidence} for a in ("conceptual", "rigor", "directness")}


def solve_part(s, attempt="my answer"):
    s.student("attempt", attempt)
    s.verdict("correct")


class TestStartAndResume(unittest.TestCase):
    def test_start_creates_session_and_shows_verbatim_launch(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths, s = make(tmp)
            v = s.view()
            self.assertEqual((v["state"], v["part_id"], v["session"]), ("LAUNCH", "q1", "2026-10-08-1000"))
            self.assertTrue(v["launch_text"].endswith("How would you like to approach this problem?"))
            self.assertTrue(os.path.exists(os.path.join(paths.sessions_dir, "2026-10-08-1000", "events.jsonl")))

    def test_restart_resumes_same_session_with_identical_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths, s = make(tmp)
            s.student("stuck", "no idea")
            again = Session.start(paths, now=NOW + datetime.timedelta(hours=1))
            self.assertEqual(again.view()["session"], s.view()["session"])
            self.assertEqual((again.view()["state"], again.view()["hint_level"]), ("WORKING", 1))

    def test_new_session_after_finished_one_gets_new_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths, s = make(tmp)
            sid = s.view()["session"]
            EventLog(os.path.join(paths.sessions_dir, sid, "events.jsonl")).append("session_end", state="DONE")
            s2 = Session.start(paths, now=NOW)
            self.assertEqual(s2.view()["session"], sid + "-2")

    def test_unvalidated_packet_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = TutorPaths(tmp, "microecon", "homework_4")
            write_sample_packet(paths)
            with open(os.path.join(paths.packet_dir, "sealed", "solution.md"), "a", encoding="utf-8") as f:
                f.write("\nedit")
            with self.assertRaises(Exception) as ctx:
                Session.start(paths, now=NOW)
            self.assertIn("prep-submit", str(ctx.exception))

    def test_open_without_any_session_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = TutorPaths(tmp, "microecon", "homework_4")
            write_sample_packet(paths)
            with self.assertRaises(ValueError):
                Session.open(paths)


class TestStudentAndSay(unittest.TestCase):
    def test_say_launch_text_ok_and_extra_text_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            launch = s.view()["launch_text"]
            self.assertTrue(s.say(launch)["ok"])
            r = s.say(launch + " Assume the first option is better.")
            self.assertFalse(r["ok"])
            self.assertEqual(r["violations"][0]["code"], "LAUNCH_NOT_VERBATIM")

    def test_rejected_draft_is_logged_but_not_in_transcript_events(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths, s = make(tmp)
            s.student("attempt", "hm")
            s.say("Use contradiction here.")
            types = [e.type for e in s.log.load()]
            self.assertIn("lint_reject", types)
            self.assertNotIn("tutor_say", types)

    def test_hint_level_rises_only_on_student_request(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            s.student("attempt", "first try")
            self.assertEqual(s.view()["hint_level"], 0)
            self.assertEqual(s.student("stuck", "I'm stuck")["hint_level"], 1)
            self.assertEqual(s.student("attempt", "another try")["hint_level"], 1)

    def test_define_flow_returns_glossary_text_and_say_must_stay_neutral(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            s.student("define_request", "what is choice overload?")
            d = s.define("Choice Overload")
            self.assertTrue(d["ok"])
            self.assertTrue(s.say(d["definition"])["ok"])
            self.assertFalse(s.say("It means d gets chosen more.")["ok"])
            self.assertFalse(s.define("nonexistent term")["ok"])

    def test_empty_student_text_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            with self.assertRaises(ValueError):
                s.student("attempt", "   ")


class TestSealed(unittest.TestCase):
    def test_refused_before_first_attempt_then_allowed_and_logged(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            self.assertFalse(s.sealed("solution")["ok"])
            s.student("attempt", "first try")
            r = s.sealed("solution")
            self.assertTrue(r["ok"])
            self.assertIn("one minus the total probability", r["text"])
            self.assertIn("sealed", [e.type for e in s.log.load()])
            self.assertFalse(s.sealed("secret")["ok"])


class TestAdvanceGating(unittest.TestCase):
    def test_full_two_part_flow(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths, s = make(tmp)
            solve_part(s)
            self.assertEqual(s.view()["state"], "VERIFIED")
            ev_id = [e for e in s.log.load() if e.type == "student"][0].id
            self.assertFalse(s.say("Correct.")["ok"])  # no check-in question
            s.close_part(rate(MAST, [ev_id]))
            r = s.say("Correct. Do you have any lingering questions, or are you ready to move on?")
            self.assertTrue(r["ok"])
            self.assertEqual((r["state"], r["part_id"]), ("AWAITING_ADVANCE", "q1"))  # tutor cannot advance
            v = s.student("confirm_advance", "ready, next please")
            self.assertEqual((v["state"], v["part_id"], v["hint_level"]), ("LAUNCH", "q2", 0))
            solve_part(s, "part two answer")
            e2 = [e for e in s.log.load() if e.type == "student"][-1].id
            s.close_part(rate(MAST, [e2]))
            s.say("Correct. Do you have any lingering questions, or are you ready to move on?")
            self.assertEqual(s.student("confirm_advance", "done")["state"], "SYNTHESIS")
            out = s.end("Big picture text.")
            self.assertTrue(os.path.exists(out["summary"]))
            self.assertTrue(os.path.exists(out["profile"]))
            self.assertEqual(s.log.load()[-1].type, "session_end")
            with self.assertRaises(IllegalTransition):
                s.student("attempt", "more")

    def test_say_in_verified_cannot_mention_next_part(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            solve_part(s)
            r = s.say("Correct. Ready for Question 2, or any lingering questions?")
            self.assertFalse(r["ok"])
            self.assertEqual(r["violations"][0]["code"], "NEXT_PART_REFERENCE")

    def test_confirm_advance_before_close_part_or_while_working_fails_and_logs_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            s.student("attempt", "try")
            n = len(s.log.load())
            with self.assertRaises(IllegalTransition):
                s.student("confirm_advance", "ready to move on")  # still WORKING
            self.assertEqual(len(s.log.load()), n)
            s.verdict("correct")
            n = len(s.log.load())
            with self.assertRaises(IllegalTransition) as ctx:
                s.student("confirm_advance", "ready to move on")  # VERIFIED but not closed
            self.assertIn("close-part", str(ctx.exception))
            self.assertEqual(len(s.log.load()), n)

    def test_end_requires_synthesis(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            with self.assertRaises(IllegalTransition):
                s.end("too early")


class TestClosePart(unittest.TestCase):
    def test_inflated_rating_rejected_with_misconception_on_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            s.student("attempt", "a closed set must be bounded", misconceptions=(("closed-implies-bounded", "all"),))
            s.verdict("correct")
            att = [e for e in s.log.load() if e.type == "student"][0].id
            with self.assertRaises(RatingRejected):
                s.close_part(rate(PROF, [att]))
            s.close_part(rate(DEV, [att]))
            with self.assertRaises(IllegalTransition):
                s.close_part(rate(DEV, [att]))  # already closed

    def test_close_part_only_when_verified(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            s.student("attempt", "try")
            with self.assertRaises(IllegalTransition):
                s.close_part(rate(DEV, [2]))

    def test_misconception_resolved_event_and_student_admits_gap(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            s.student("attempt", "I don't get concavity", admits_gap="conceptual")
            s.misconception("secant-chords", axis="rigor")
            s.misconception("secant-chords", resolved=True)
            types = [e.type for e in s.log.load()]
            self.assertIn("misconception", types)
            self.assertIn("misconception_resolved", types)
            s.verdict("correct")
            att = [e for e in s.log.load() if e.type == "student"][0].id
            with self.assertRaises(RatingRejected):
                s.close_part({**rate(MAST, [att]), "conceptual": {"rating": PROF, "evidence": [att]}})


class TestFixPassFromFinalReview(unittest.TestCase):
    def test_misconception_sent_with_confirm_advance_belongs_to_the_part_being_left(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            solve_part(s)
            att = [e for e in s.log.load() if e.type == "student"][0].id
            s.close_part(rate(MAST, [att]))
            s.student("confirm_advance", "ready, next", misconceptions=(("late-tag", "all"),))
            miscs = [e for e in s.log.load() if e.type == "misconception"]
            self.assertEqual([e.part for e in miscs], ["q1"])

    def test_commands_refuse_on_an_ended_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths, s = make(tmp)
            for _ in range(2):
                solve_part(s)
                att = [e for e in s.log.load() if e.type == "student"][-1].id
                s.close_part(rate(MAST, [att]))
                s.student("confirm_advance", "ready, next")
            s.end("bp")
            reopened = Session.open(paths, s.view()["session"])
            n = len(reopened.log.load())
            for call in (lambda: reopened.sealed("solution"), lambda: reopened.say("hello"),
                         lambda: reopened.define("choice overload"), lambda: reopened.misconception("t")):
                with self.assertRaises(IllegalTransition):
                    call()
            self.assertEqual(len(reopened.log.load()), n)
