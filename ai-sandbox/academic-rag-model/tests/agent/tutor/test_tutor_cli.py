import contextlib
import io
import json
import os
import tempfile
import unittest

from agent.tutor import cli
from agent.tutor.paths import TutorPaths
from agent.tutor.sample_packet import write_sample_packet


def run(tmp, *args):
    out = io.StringIO()
    argv = ["--hub-root", tmp, "--course", "microecon", "--problem-set", "homework_4", *args]
    with contextlib.redirect_stdout(out):
        code = cli.main(argv)
    return code, json.loads(out.getvalue())


class TestCli(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        write_sample_packet(TutorPaths(self.tmp.name, "microecon", "homework_4"))

    def tearDown(self):
        self.tmp.cleanup()

    def test_start_then_student_via_text_file_with_math_and_unicode(self):
        code, v = run(self.tmp.name, "start")
        self.assertEqual((code, v["state"]), (0, "LAUNCH"))
        text_file = os.path.join(self.tmp.name, "msg.txt")
        msg = 'Is $x \\succeq y$ transitive? She said "maybe" — ≽'
        with open(text_file, "w", encoding="utf-8") as f:
            f.write(msg)
        code, v = run(self.tmp.name, "student", "--intent", "attempt", "--text-file", text_file)
        self.assertEqual((code, v["state"]), (0, "WORKING"))
        log = os.path.join(TutorPaths(self.tmp.name, "microecon", "homework_4").sessions_dir, v["session"], "events.jsonl")
        with open(log, encoding="utf-8") as f:
            self.assertIn("≽", f.read())

    def test_say_violation_exits_2_with_violations(self):
        run(self.tmp.name, "start")
        run(self.tmp.name, "student", "--intent", "attempt", "--text", "hm")
        code, v = run(self.tmp.name, "say", "--text", "Try proof by contradiction.")
        self.assertEqual(code, 2)
        self.assertFalse(v["ok"])
        self.assertEqual(v["violations"][0]["code"], "TECHNIQUE")

    def test_illegal_transition_is_reported_as_error_json_not_traceback(self):
        run(self.tmp.name, "start")
        code, v = run(self.tmp.name, "student", "--intent", "confirm_advance", "--text", "next")
        self.assertEqual(code, 2)
        self.assertFalse(v["ok"])
        self.assertIn("confirm_advance", v["error"])

    def test_misconception_flag_and_admits_gap(self):
        run(self.tmp.name, "start")
        code, v = run(self.tmp.name, "student", "--intent", "attempt", "--text", "closed means bounded",
                      "--misconception", "closed-implies-bounded:conceptual", "--admits-gap", "conceptual")
        self.assertEqual(code, 0)

    def test_define_sealed_verdict_and_audit_commands(self):
        run(self.tmp.name, "start")
        run(self.tmp.name, "student", "--intent", "define_request", "--text", "what is choice overload?")
        code, d = run(self.tmp.name, "define", "choice overload")
        self.assertTrue(d["ok"])
        code, s = run(self.tmp.name, "sealed", "hint")
        self.assertEqual(code, 2)  # no attempt yet
        run(self.tmp.name, "student", "--intent", "attempt", "--text", "try")
        code, s = run(self.tmp.name, "sealed", "hint")
        self.assertEqual(code, 0)
        code, v = run(self.tmp.name, "verdict", "--assessment", "correct")
        self.assertEqual(v["state"], "VERIFIED")
        code, a = run(self.tmp.name, "audit")
        self.assertIn("findings", a)

    def test_close_part_and_end_via_files(self):
        run(self.tmp.name, "start")
        for _ in range(2):
            run(self.tmp.name, "student", "--intent", "attempt", "--text", "answer")
            _, v = run(self.tmp.name, "verdict", "--assessment", "correct")
            rf = os.path.join(self.tmp.name, "r.json")
            with open(rf, "w", encoding="utf-8") as f:
                json.dump({a: {"rating": "Mastered", "evidence": ["answer"]} for a in ("conceptual", "rigor", "directness")}, f)
            code, _ = run(self.tmp.name, "close-part", "--ratings-file", rf)
            self.assertEqual(code, 0)
            run(self.tmp.name, "say", "--text", "Right. Any lingering questions, or ready to move on?")
            run(self.tmp.name, "student", "--intent", "confirm_advance", "--text", "ready, next")
        bp = os.path.join(self.tmp.name, "bp.md")
        with open(bp, "w", encoding="utf-8") as f:
            f.write("The big picture.")
        code, out = run(self.tmp.name, "end", "--big-picture-file", bp)
        self.assertEqual(code, 0)
        self.assertTrue(os.path.exists(out["summary"]))

    def test_bootstrap_fills_placeholders(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cli.main(["--hub-root", "/H", "--course", "microecon", "--problem-set", "homework_4", "bootstrap"])
        text = out.getvalue()
        self.assertEqual(code, 0)
        self.assertIn("/H", text)
        self.assertIn("homework_4", text)
        self.assertNotIn("{HUB_ROOT}", text)
        self.assertNotIn("{PYTHON}", text)
