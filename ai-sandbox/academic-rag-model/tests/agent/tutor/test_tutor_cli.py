# tests/agent/tutor/test_tutor_cli.py  (replace the whole file)
import contextlib
import io
import json
import os
import tempfile
import unittest
from unittest import mock

from agent.tutor import cli
from agent.tutor.paths import TutorPaths
from agent.tutor.sample_packet import write_sample_packet

M2 = "walking away is whatever is left over when nothing else is chosen"
M3 = "so it is one minus the sum of the others"
N1 = "all the non-positive numbers are indifferent to each other"
N2 = "so any representing function is flat up to zero and then strictly increasing"
N3 = "a flat then increasing function cannot be concave"
GOOD_Q = "You said walking away is whatever is left over. What else is true?"
CHECKIN = "Right. Do you have any lingering questions, or are you ready to move on?"


def run(tmp, *args, stdin=None):
    out = io.StringIO()
    argv = ["--hub-root", tmp, "--course", "microecon", "--problem-set", "homework_4", *args]
    with contextlib.redirect_stdout(out):
        if stdin is None:
            code = cli.main(argv)
        else:
            with mock.patch("sys.stdin", io.StringIO(stdin)):
                code = cli.main(argv)
    return code, json.loads(out.getvalue())


def events(tmp, session):
    path = os.path.join(TutorPaths(tmp, "microecon", "homework_4").sessions_dir, session, "events.jsonl")
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


class TestCli(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.t = self.tmp.name
        write_sample_packet(TutorPaths(self.t, "microecon", "homework_4"))

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, name, content):
        path = os.path.join(self.t, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    def test_start_shows_the_short_launch(self):
        code, v = run(self.t, "start")
        self.assertEqual((code, v["state"]), (0, "LAUNCH"))
        self.assertEqual(v["launch_text"], "Question 1. How would you like to approach this problem?")

    def test_turn_via_stdin_round_trips_unicode_quotes_and_latex_and_strips_the_newline(self):
        run(self.t, "start")
        msg = 'Is $x \\succeq y$ transitive? She said "maybe" — ≽ γ(b)'
        code, v = run(self.t, "turn", "--intent", "attempt", "--stdin", stdin=msg + "\r\n")
        self.assertEqual((code, v["state"]), (0, "WORKING"))
        logged = [e for e in events(self.t, v["session"]) if e["type"] == "student"][0]
        self.assertEqual(logged["text"], msg)

    def test_turn_via_text_file_accepts_a_bom(self):
        run(self.t, "start")
        path = os.path.join(self.t, "m.txt")
        with open(path, "w", encoding="utf-8-sig") as f:
            f.write("≽ with a byte order mark\n")
        code, v = run(self.t, "turn", "--intent", "attempt", "--text-file", path)
        self.assertEqual(code, 0)
        logged = [e for e in events(self.t, v["session"]) if e["type"] == "student"][0]
        self.assertEqual(logged["text"], "≽ with a byte order mark")

    def test_say_violation_exits_2_and_check_logs_nothing(self):
        _, v = run(self.t, "start")
        run(self.t, "turn", "--intent", "attempt", "--stdin", stdin="hm")
        n = len(events(self.t, v["session"]))
        code, r = run(self.t, "say", "--stdin", "--check", stdin="Try proof by contradiction.")
        self.assertEqual(code, 2)
        self.assertFalse(r["ok"])
        self.assertIn("TECHNIQUE", {x["code"] for x in r["violations"]})
        self.assertEqual(len(events(self.t, v["session"])), n)              # --check logs nothing
        code, r = run(self.t, "say", "--stdin", stdin="Try proof by contradiction.")
        self.assertEqual(code, 2)
        self.assertIn("lint_reject", [e["type"] for e in events(self.t, v["session"])])

    def test_errors_carry_a_next_list(self):
        run(self.t, "start")
        code, v = run(self.t, "turn", "--intent", "confirm_advance", "--stdin", stdin="next")
        self.assertEqual(code, 2)
        self.assertFalse(v["ok"])
        self.assertIn("confirm_advance", v["error"])
        self.assertTrue(v["next"])
        code, v = run(self.t, "turn", "--intent", "attempt", "--stdin", "--establish", "C9", "--establish-quote", "x", stdin="x y")
        self.assertEqual(code, 2)
        self.assertIn("unknown claim id", v["error"])
        self.assertTrue(v["next"])

    def test_define_flow(self):
        run(self.t, "start")
        code, v = run(self.t, "turn", "--intent", "define_request", "--stdin", "--define", "choice overload",
                      stdin="what is choice overload?")
        self.assertEqual(code, 0)
        self.assertIn("less likely to choose anything", v["definition"])

    def test_removed_v1_commands_are_gone(self):
        for old in ("student", "verdict", "misconception", "define", "sealed", "close-part"):
            with self.subTest(command=old):
                with contextlib.redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit):
                        run(self.t, old)

    def test_two_part_session_through_verify_and_end(self):
        _, v = run(self.t, "start")
        sid = v["session"]
        self.assertEqual(run(self.t, "say", "--stdin", stdin=v["launch_text"])[0], 0)
        run(self.t, "turn", "--intent", "attempt", "--stdin", stdin=M2)
        self.assertEqual(run(self.t, "say", "--stdin", stdin=GOOD_Q)[0], 0)
        _, b = run(self.t, "turn", "--intent", "attempt", "--stdin", stdin=M3)
        self.assertTrue(b["verify_available"])
        code, rel = run(self.t, "verify")
        self.assertEqual((code, len(rel["steps"])), (0, 2))
        check = self.write("check1.json", json.dumps([{"step": 1, "status": "confirmed", "quote": M3},
                                                      {"step": 2, "status": "confirmed", "quote": M2}]))
        code, done = run(self.t, "verify", "--check-file", check, "--downgrade", "rigor=proficient", "--why", "notation was loose")
        self.assertEqual((code, done["closed"]), (0, True))
        close = [e for e in events(self.t, sid) if e["type"] == "close_part"][0]
        self.assertEqual(close["data"]["ratings"]["rigor"]["rating"], "Proficient")
        self.assertEqual(close["data"]["ratings"]["rigor"]["why"], "notation was loose")
        self.assertEqual(run(self.t, "say", "--stdin", stdin=CHECKIN)[1]["state"], "AWAITING_ADVANCE")
        _, b = run(self.t, "turn", "--intent", "confirm_advance", "--stdin", stdin="ready, next one")
        self.assertEqual((b["state"], b["part_id"]), ("LAUNCH", "q2"))
        self.assertEqual(run(self.t, "say", "--stdin", stdin=b["launch_text"])[0], 0)
        for msg in (N1, N2, N3):
            run(self.t, "turn", "--intent", "attempt", "--stdin", stdin=msg)
        run(self.t, "verify")
        check2 = self.write("check2.json", json.dumps([{"step": 1, "status": "confirmed", "quote": N1},
                                                       {"step": 2, "status": "confirmed", "quote": N2},
                                                       {"step": 3, "status": "confirmed", "quote": N3}]))
        self.assertTrue(run(self.t, "verify", "--check-file", check2)[1]["closed"])
        run(self.t, "say", "--stdin", stdin=CHECKIN)
        self.assertEqual(run(self.t, "turn", "--intent", "confirm_advance", "--stdin", stdin="done")[1]["state"], "SYNTHESIS")
        bp = self.write("bp.md", "The big picture.")
        code, out = run(self.t, "end", "--big-picture-file", bp)
        self.assertEqual(code, 0)
        self.assertTrue(os.path.exists(out["summary"]))
        self.assertEqual(run(self.t, "audit")[0], 0)

    def test_downgrade_errors_are_reported(self):
        run(self.t, "start")
        run(self.t, "turn", "--intent", "attempt", "--stdin", stdin=M2)
        run(self.t, "turn", "--intent", "attempt", "--stdin", stdin=M3)
        run(self.t, "verify")
        check = self.write("c.json", json.dumps([{"step": 1, "status": "confirmed", "quote": M3},
                                                 {"step": 2, "status": "confirmed", "quote": M2}]))
        code, v = run(self.t, "verify", "--check-file", check, "--downgrade", "rigor=proficient")
        self.assertEqual(code, 2)
        self.assertIn("--why", v["error"])
        code, v = run(self.t, "verify", "--check-file", check, "--downgrade", "rigor")
        self.assertEqual(code, 2)

    def test_prep_submit_validates_the_packet(self):
        code, v = run(self.t, "prep-submit")
        self.assertEqual((code, v), (0, {"ok": True}))

    def test_bootstrap_fills_placeholders(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cli.main(["--hub-root", "/H", "--course", "microecon", "--problem-set", "homework_4", "bootstrap"])
        text = out.getvalue()
        self.assertEqual(code, 0)
        self.assertIn("/H", text)
        self.assertIn("homework_4", text)
        for placeholder in ("{HUB_ROOT}", "{PYTHON}", "{RAG_DIR}", "{COURSE}", "{PROBLEM_SET}"):
            self.assertNotIn(placeholder, text)
        for must in ("turn", "say", "verify", "--stdin", "Set-Location"):
            self.assertIn(must, text)
