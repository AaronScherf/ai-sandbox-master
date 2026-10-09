# tests/agent/tutor/test_tutor_session.py  (replace the whole file)
import datetime
import json
import os
import tempfile
import unittest

from agent.tutor.events import EventLog
from agent.tutor.paths import TutorPaths
from agent.tutor.sample_packet import write_sample_packet
from agent.tutor.session import Refused, Session, split_steps

NOW = datetime.datetime(2026, 10, 8, 10, 0)
DEV, PROF, MAST = "Developing / Needs Review", "Proficient", "Mastered"

M1 = "the probabilities of everything in the set sum to 1"                    # q1 C1
M2 = "walking away is whatever is left over when nothing else is chosen"       # q1 C2
M3 = "so it is one minus the sum of the others"                                # q1 C3 (and C1)
PM = "I would multiply the probabilities of the other options"                 # q1 pitfall P1
N1 = "all the non-positive numbers are indifferent to each other"              # q2 C1
N2 = "so any representing function is flat up to zero and then strictly increasing"   # q2 C2
N3 = "a flat then increasing function cannot be concave"                       # q2 C3
CHECK_Q1 = [{"step": 1, "status": "confirmed", "quote": M3}, {"step": 2, "status": "confirmed", "quote": M2}]
CHECK_Q2 = [{"step": 1, "status": "confirmed", "quote": N1}, {"step": 2, "status": "confirmed", "quote": N2},
            {"step": 3, "status": "confirmed", "quote": N3}]
CHECKIN = "Right. Do you have any lingering questions, or are you ready to move on?"


def make(tmp):
    paths = TutorPaths(tmp, "microecon", "homework_4")
    write_sample_packet(paths)
    return paths, Session.start(paths, now=NOW)


def codes(result):
    return {v["code"] for v in result.get("violations", [])}


def cover_q1(s):
    s.turn("attempt", M2)
    return s.turn("attempt", M3)


def to_level_three(s):
    s.turn("stuck", "I am stuck")              # level 1
    s.turn("hint_request", "a hint please")    # level 2
    s.turn("attempt", "I do not know")         # failed attempt 1
    s.turn("attempt", "still not sure")        # failed attempt 2
    return s.turn("stuck", "please help")      # level 3


class TestSplitSteps(unittest.TestCase):
    def test_headings_paragraphs_and_preamble(self):
        self.assertEqual(split_steps("### Step 1\na\n\n### Step 2\nb"), ["### Step 1\na", "### Step 2\nb"])
        self.assertEqual(split_steps("first para\n\nsecond para"), ["first para", "second para"])
        self.assertEqual(split_steps("intro\n### Step 1\na"), ["intro", "### Step 1\na"])


class TestStartAndResume(unittest.TestCase):
    def test_start_shows_the_short_launch_the_statement_and_no_claim_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths, s = make(tmp)
            v = s.view()
            self.assertEqual((v["state"], v["part_id"], v["session"]), ("LAUNCH", "q1", "2026-10-08-1000"))
            self.assertEqual(v["launch_text"], "Question 1. How would you like to approach this problem?")
            self.assertIn("Choice overload", v["statement"])
            blob = json.dumps(v)
            for claim in s.packet.claims["q1"].claims:
                self.assertNotIn(claim.text, blob)          # claim texts never appear in the brief at level 0
            self.assertTrue(os.path.exists(os.path.join(paths.sessions_dir, "2026-10-08-1000", "events.jsonl")))

    def test_restart_mid_part_gives_an_identical_brief(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths, s = make(tmp)
            s.turn("stuck", "no idea")
            s.turn("attempt", "nobody else picks it so it is the default", establish="C2", establish_quote="nobody else picks it")
            s.turn("attempt", M1)
            again = Session.start(paths, now=NOW + datetime.timedelta(hours=1))
            self.assertEqual(again._brief(), s._brief())
            self.assertEqual(again.view()["claims_established"], ["C2", "C1"])
            self.assertEqual(again.view()["hint_level"], 1)

    def test_new_session_after_finished_one_gets_new_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths, s = make(tmp)
            sid = s.view()["session"]
            EventLog(os.path.join(paths.sessions_dir, sid, "events.jsonl")).append("session_end", state="DONE")
            self.assertEqual(Session.start(paths, now=NOW).view()["session"], sid + "-2")

    def test_unvalidated_packet_refused_and_open_without_session_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = TutorPaths(tmp, "microecon", "homework_4")
            write_sample_packet(paths)
            with self.assertRaises(ValueError):
                Session.open(paths)
            with open(os.path.join(paths.packet_dir, "sealed", "solution.md"), "a", encoding="utf-8") as f:
                f.write("\nedit")
            with self.assertRaises(Exception) as ctx:
                Session.start(paths, now=NOW)
            self.assertIn("prep-submit", str(ctx.exception))


class TestTurn(unittest.TestCase):
    def test_turn_updates_state_ledger_and_progress_flags(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            b = s.turn("attempt", "I really am not sure where to begin")
            self.assertEqual((b["state"], b["claims_established"]), ("WORKING", []))
            self.assertFalse(s.log.load()[-1].data["made_progress"])
            b = s.turn("attempt", M2)
            self.assertEqual(b["claims_established"], ["C2"])
            self.assertEqual(b["route_coverage"], {"A": "1/3"})
            self.assertEqual(s.log.load()[-1].data["established"], ["C2"])
            self.assertFalse(b["verify_available"])

    def test_hint_level_rises_only_on_student_request_and_is_capped(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            self.assertEqual(s.turn("attempt", "first try")["hint_level"], 0)
            self.assertEqual(s.turn("stuck", "I'm stuck")["hint_level"], 1)
            self.assertEqual(s.turn("attempt", "another try")["hint_level"], 1)
            self.assertEqual(s.turn("hint_request", "a hint?")["hint_level"], 2)
            self.assertEqual(s.turn("stuck", "more please")["hint_level"], 2)      # level 3 not yet open
            self.assertTrue(s.log.load()[-1].data["hint_capped"])

    def test_level_two_and_three_briefs_release_only_what_the_level_allows(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            s.turn("stuck", "I am stuck")
            b = s.turn("hint_request", "a hint please")
            self.assertEqual(b["object_terms"], ["the probabilities in the menu"])
            self.assertNotIn("next_claim_text", b)
            s.turn("attempt", "I do not know")
            s.turn("attempt", "still not sure")
            b = s.turn("stuck", "please help")
            self.assertEqual(b["hint_level"], 3)
            self.assertEqual(b["next_claim_text"], "the choice probabilities in a menu sum to one")

    def test_pitfall_is_logged_surfaced_and_auto_resolved_by_the_resolving_claim(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            b = s.turn("attempt", PM)
            self.assertEqual([p["tag"] for p in b["pitfalls_hit"]], ["multiplies-instead-of-subtracting"])
            self.assertIn("add up to", b["pitfalls_hit"][0]["repair_question"])
            self.assertIn("Socratically", b["rules"])
            miscs = [e for e in s.log.load() if e.type == "misconception"]
            self.assertEqual((miscs[0].data["pitfall"], miscs[0].data["axis"]), ("P1", "rigor"))
            b = s.turn("attempt", M3)
            self.assertEqual(b["pitfalls_hit"], [])
            resolved = [e for e in s.log.load() if e.type == "misconception_resolved"]
            self.assertTrue(resolved[0].data["auto"])

    def test_a_slip_after_the_resolving_claim_is_not_auto_resolved(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            s.turn("attempt", M3)
            b = s.turn("attempt", PM)
            self.assertEqual(len(b["pitfalls_hit"]), 1)

    def test_define_request_returns_the_glossary_entry_and_is_not_a_claim(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            b = s.turn("define_request", "what is the sum of choice overload, one total?", define_term="Choice Overload")
            self.assertIn("less likely to choose anything", b["definition"])
            self.assertEqual(b["claims_established"], [])
            self.assertTrue(s.say(b["definition"])["ok"])
            self.assertFalse(s.say("It means d gets chosen more.")["ok"])
            b = s.turn("define_request", "what is a flurb?", define_term="flurb")
            self.assertIn("flurb", b["definition_error"])
            self.assertIn("choice overload", b["terms"])

    def test_empty_text_and_bad_manual_actions_log_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            s.turn("attempt", "some words about nobody picking it")
            n = len(s.log.load())
            for kwargs in (
                dict(text="   "),
                dict(text="x y z", establish="C9", establish_quote="x y"),
                dict(text="x y z", establish="C2", establish_quote="words nobody wrote"),
                dict(text="x y z", flag_slip="oops", slip_quote="words nobody wrote"),
                dict(text="x y z", resolve="never-flagged", resolve_quote="x y"),
                dict(text="ready", intent="confirm_advance", establish="C2", establish_quote="ready"),
            ):
                kwargs.setdefault("intent", "attempt")
                with self.subTest(kwargs=kwargs):
                    with self.assertRaises(ValueError):
                        s.turn(**kwargs)
                    self.assertEqual(len(s.log.load()), n)

    def test_manual_establish_slip_and_resolve_are_logged_with_quotes(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            s.turn("attempt", "nobody else picks it so it is the default")
            b = s.turn("other", "I mean exactly that", establish="C2", establish_quote="nobody else picks it")
            self.assertEqual(b["claims_established"], ["C2"])
            b = s.turn("attempt", "walking away is just sort of unknown", flag_slip="invented-tag:conceptual", slip_quote="sort of unknown")
            self.assertEqual([p["tag"] for p in b["pitfalls_hit"]], ["invented-tag"])
            self.assertIsNone(b["pitfalls_hit"][0]["repair_question"])
            b = s.turn("attempt", "oh I see now", resolve="invented-tag", resolve_quote="I see now")
            self.assertEqual(b["pitfalls_hit"], [])
            kinds = [(e.type, bool(e.data.get("manual"))) for e in s.log.load() if e.type in ("establish", "misconception", "misconception_resolved")]
            self.assertEqual(kinds, [("establish", False), ("misconception", True), ("misconception_resolved", True)])

    def test_confirm_advance_before_the_part_is_closed_is_refused_with_next_steps(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            s.turn("attempt", "working on it")
            n = len(s.log.load())
            with self.assertRaises(Refused) as ctx:
                s.turn("confirm_advance", "ready to move on")
            self.assertTrue(ctx.exception.next_commands)
            self.assertNotIn("verify first", str(ctx.exception))
            self.assertEqual(len(s.log.load()), n)
            cover_q1(s)
            with self.assertRaises(Refused) as ctx:
                s.turn("confirm_advance", "ready to move on")
            self.assertIn("Run verify", str(ctx.exception))


class TestSay(unittest.TestCase):
    def test_launch_line_ok_and_extras_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            launch = s.view()["launch_text"]
            self.assertTrue(s.say(launch)["ok"])
            r = s.say(launch + " Assume the first option is better.")
            self.assertFalse(r["ok"])
            self.assertEqual(r["violations"][0]["code"], "LAUNCH_NOT_VERBATIM")

    def test_unreached_claim_is_blocked_until_the_student_reaches_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            s.turn("attempt", M1)
            leak = "Walking away is whatever remains when nothing else is chosen."
            r = s.say(leak, check=True)
            self.assertIn("REVEALS_CLAIM", codes(r))
            self.assertTrue(any("C2" in v["detail"] for v in r["violations"]))
            self.assertFalse(any("probabilities in a menu" in v["detail"] for v in r["violations"]))   # ids only, never claim text
            good = "You said the probabilities of everything in the set sum to 1. What happens when she walks away?"
            self.assertTrue(s.say(good, check=True)["ok"])

    def test_question_form_at_level_zero_and_one_but_not_at_level_three(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            s.turn("attempt", "I think we start from the menu")
            self.assertIn("QUESTION_FORM", codes(s.say("What do you mean? And why?", check=True)))
            to_level_three(s)
            self.assertNotIn("QUESTION_FORM", codes(s.say("What do you mean? And why?", check=True)))

    def test_level_three_exempts_only_the_next_claim(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            to_level_three(s)
            ok = s.say("The probabilities of everything in the set sum to 1, so what comes next?", check=True)
            self.assertTrue(ok["ok"])
            bad = s.say("So it is one minus the sum of the others.", check=True)
            self.assertIn("REVEALS_CLAIM", codes(bad))
            self.assertTrue(any("C3" in v["detail"] for v in bad["violations"]))
            self.assertFalse(any("C1" in v["detail"] for v in bad["violations"]))

    def test_check_logs_nothing_and_a_rejection_is_logged_but_not_a_tutor_turn(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            s.turn("attempt", "hm")
            n = len(s.log.load())
            self.assertEqual(s.say("What did you try?", check=True), {"ok": True, "checked": True})
            self.assertEqual(len(s.log.load()), n)
            s.say("Use contradiction here.")
            types = [e.type for e in s.log.load()]
            self.assertIn("lint_reject", types)
            self.assertNotIn("tutor_say", types)


class TestVerify(unittest.TestCase):
    def test_refused_before_coverage_and_nothing_is_released(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            s.turn("attempt", M2)
            with self.assertRaises(Refused) as ctx:
                s.verify()
            self.assertIn("every claim on one route", str(ctx.exception))
            self.assertNotIn("verify_release", [e.type for e in s.log.load()])

    def test_release_once_then_check_file_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            b = cover_q1(s)
            self.assertTrue(b["verify_available"])
            r = s.verify()
            self.assertEqual([st["n"] for st in r["steps"]], [1, 2])
            self.assertIn("none of the other alternatives", r["steps"][1]["text"])
            self.assertTrue(s.view()["solution_released"])
            with self.assertRaises(Refused) as ctx:
                s.verify()
            self.assertIn("already released", str(ctx.exception))

    def test_check_before_release_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            cover_q1(s)
            with self.assertRaises(Refused):
                s.verify(CHECK_Q1)

    def test_bad_check_files_are_refused_and_close_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            cover_q1(s)
            s.verify()
            n = len(s.log.load())
            bad_files = [
                [{"step": 1, "status": "confirmed", "quote": M3}],                                         # step 2 missing
                [{"step": 1, "status": "confirmed", "quote": "words the student never wrote"}, CHECK_Q1[1]],  # fabricated quote
                [{"step": 1, "status": "confirmed"}, CHECK_Q1[1]],                                          # no quote
                [{"step": 1, "status": "wrong"}, CHECK_Q1[1]],                                              # defect without a note
                [{"step": 1, "status": "fine", "quote": M3}, CHECK_Q1[1]],                                  # unknown status
                [CHECK_Q1[0], CHECK_Q1[0], CHECK_Q1[1]],                                                    # duplicate step
                [{"step": 3, "status": "confirmed", "quote": M3}, CHECK_Q1[1]],                             # out-of-range step
                "not a list",
            ]
            for check in bad_files:
                with self.subTest(check=check):
                    with self.assertRaises(ValueError):
                        s.verify(check)
                    self.assertEqual(len(s.log.load()), n)
            self.assertEqual(s.view()["state"], "WORKING")

    def test_clean_check_closes_the_part_with_ceiling_ratings_and_cli_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            cover_q1(s)
            s.verify()
            r = s.verify(CHECK_Q1)
            self.assertTrue(r["closed"])
            self.assertEqual(r["state"], "VERIFIED")
            close = [e for e in s.log.load() if e.type == "close_part"][0]
            ratings = close.data["ratings"]
            self.assertEqual({a: v["rating"] for a, v in ratings.items()}, {"conceptual": MAST, "rigor": MAST, "directness": MAST})
            self.assertTrue(all(v["evidence"] for v in ratings.values()))
            self.assertEqual([e.type for e in s.log.load()][-2:], ["verify", "close_part"])

    def test_agent_can_lower_a_rating_but_not_raise_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            s.turn("stuck", "I am stuck")                                  # hint level 1: ceiling is Proficient
            cover_q1(s)
            s.verify()
            with self.assertRaises(ValueError):
                s.verify(CHECK_Q1, {"rigor": (MAST, "they were great")})
            self.assertEqual(s.view()["state"], "WORKING")
            r = s.verify(CHECK_Q1, {"rigor": (DEV, "uneven notation")})
            self.assertTrue(r["closed"])
            close = [e for e in s.log.load() if e.type == "close_part"][0]
            self.assertEqual(close.data["ratings"]["rigor"]["rating"], DEV)
            self.assertEqual(close.data["ratings"]["rigor"]["why"], "uneven notation")
            self.assertEqual(close.data["ratings"]["conceptual"]["rating"], PROF)

    def test_a_defect_reopens_work_and_a_resolved_defect_caps_at_proficient(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            cover_q1(s)
            s.verify()
            bad = [CHECK_Q1[0], {"step": 2, "status": "wrong", "note": "treats the others as multiplied",
                                 "tag": "multiplied-others", "axis": "rigor"}]
            r = s.verify(bad)
            self.assertFalse(r["closed"])
            self.assertEqual((r["state"], [d["step"] for d in r["defects"]]), ("WORKING", [2]))
            types = [e.type for e in s.log.load()]
            self.assertIn("defect", types)
            miscs = [e for e in s.log.load() if e.type == "misconception"]
            self.assertTrue(miscs[-1].data["defect"])
            with self.assertRaises(Refused):
                s.verify()                                              # the solution is released only once
            r2 = s.verify(CHECK_Q1)                                     # all steps confirmed but the defect is unresolved
            self.assertFalse(r2["closed"])
            self.assertEqual(r2["unresolved"], ["multiplied-others"])
            s.turn("attempt", "ah the others are subtracted not multiplied", resolve="multiplied-others",
                   resolve_quote="subtracted not multiplied")
            r3 = s.verify(CHECK_Q1)
            self.assertTrue(r3["closed"])
            close = [e for e in s.log.load() if e.type == "close_part"][0]
            self.assertEqual(close.data["ratings"]["rigor"]["rating"], PROF)

    def test_manual_establish_can_cover_a_route_but_needs_a_real_quote(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            s.turn("attempt", M3)                                       # C1, C3
            s.turn("attempt", "nobody else picks it so it is the default")
            self.assertFalse(s.view()["verify_available"])
            s.turn("other", "as I said", establish="C2", establish_quote="nobody else picks it")
            self.assertTrue(s.view()["verify_available"])
            self.assertEqual(len(s.verify()["steps"]), 2)


class TestFullFlow(unittest.TestCase):
    def test_two_parts_to_end_with_check_in_and_cross_part_quote_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths, s = make(tmp)
            self.assertTrue(s.say(s.view()["launch_text"])["ok"])
            cover_q1(s)
            s.verify()
            self.assertTrue(s.verify(CHECK_Q1)["closed"])
            self.assertFalse(s.say("Correct.")["ok"])                   # no check-in question
            r = s.say(CHECKIN)
            self.assertEqual((r["ok"], r["state"], r["part_id"]), (True, "AWAITING_ADVANCE", "q1"))
            b = s.turn("has_questions", "why does this matter for microeconomics?")
            self.assertEqual(b["state"], "AWAITING_ADVANCE")            # a side question does not reopen the closed part
            b = s.turn("confirm_advance", "ready, next one")
            self.assertEqual((b["state"], b["part_id"], b["hint_level"]), ("LAUNCH", "q2", 0))
            self.assertEqual(b["claims_established"], [])               # the confirm message is not a claim
            self.assertTrue(s.say(b["launch_text"])["ok"])
            for msg in (N1, N2, N3):
                s.turn("attempt", msg)
            s.verify()
            with self.assertRaises(ValueError):                         # a quote from part 1 does not count in part 2
                s.verify([dict(CHECK_Q2[0], quote=M3), CHECK_Q2[1], CHECK_Q2[2]])
            self.assertTrue(s.verify(CHECK_Q2)["closed"])
            self.assertTrue(s.say(CHECKIN)["ok"])
            self.assertEqual(s.turn("confirm_advance", "done, thanks")["state"], "SYNTHESIS")
            out = s.end("Big picture text.")
            for key in ("transcript", "summary", "profile"):
                self.assertTrue(os.path.exists(out[key]), key)
            with open(out["summary"], encoding="utf-8") as f:
                summary = f.read()
            self.assertIn("Verified steps", summary)
            self.assertEqual(s.log.load()[-1].type, "session_end")
            with self.assertRaises(Refused):
                s.turn("attempt", "more")
            with self.assertRaises(Refused):
                s.say("hello")

    def test_end_requires_synthesis(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            with self.assertRaises(Refused):
                s.end("too early")


class TestFixPassFromFinalReview(unittest.TestCase):
    def test_vacuous_quotes_cannot_establish_resolve_or_confirm(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            s.turn("attempt", "I am not sure where to start with this one")
            n = len(s.log.load())
            for quote in ("a", "am not"):
                with self.assertRaises(ValueError) as ctx:
                    s.turn("other", "as I said", establish="C1", establish_quote=quote)
                self.assertIn("at least 3 words", str(ctx.exception))
            self.assertEqual(len(s.log.load()), n)
            s.turn("attempt", PM)                                   # a real, auto-detected slip
            n = len(s.log.load())
            with self.assertRaises(ValueError):
                s.turn("attempt", "ok then", resolve="multiplies-instead-of-subtracting", resolve_quote="o")
            self.assertEqual(len(s.log.load()), n)
            cover_q1(s)
            s.verify()
            n = len(s.log.load())
            with self.assertRaises(ValueError):
                s.verify([{"step": 1, "status": "confirmed", "quote": "a"}, {"step": 2, "status": "confirmed", "quote": "e"}])
            self.assertEqual(len(s.log.load()), n)
            self.assertEqual(s.view()["state"], "WORKING")

    def test_a_short_whole_message_is_an_acceptable_quote(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            s.turn("attempt", "two words")
            b = s.turn("other", "as I said", establish="C1", establish_quote="two words")
            self.assertEqual(b["claims_established"], ["C1"])

    def test_admits_gap_and_slip_axes_must_be_known_axes(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            s.turn("attempt", "some words here too")
            n = len(s.log.load())
            for kwargs in (dict(admits_gap="Conceptual"), dict(admits_gap="style"),
                           dict(flag_slip="oops:style", slip_quote="some words here")):
                with self.subTest(kwargs=kwargs):
                    with self.assertRaises(ValueError):
                        s.turn("attempt", "some words here too", **kwargs)
                    self.assertEqual(len(s.log.load()), n)
            b = s.turn("attempt", "I really do not understand this", admits_gap="conceptual")
            self.assertEqual(b["state"], "WORKING")
