# tests/agent/tutor/test_tutor_pause.py
import datetime
import json
import os
import tempfile
import unittest

from agent.tutor.cli import main
from agent.tutor.profile import load_profile
from agent.tutor.session import Refused, Session
from skip_support import NOW, M2, close_q1, make


class TestPause(unittest.TestCase):
    def test_pause_writes_docs_and_profile_and_blocks_turns(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths, s = make(tmp)
            close_q1(s)
            s.say("Right. Do you have any lingering questions, or are you ready to move on?")
            out = s.pause()
            self.assertTrue(out["paused"])
            self.assertTrue(os.path.exists(out["transcript"]))
            self.assertTrue(os.path.exists(out["summary"]))
            prof = load_profile(paths.profile_json)
            self.assertEqual(prof["concepts"]["random-consideration-set"]["history"][0]["part"], "q1")
            self.assertEqual(s.view()["state"], "PAUSED")
            with self.assertRaises(Refused) as ctx:
                s.turn("attempt", "I will keep going")
            self.assertIn("start", ctx.exception.next_commands)
            with self.assertRaises(Refused):
                s.say("anything")
            with self.assertRaises(Refused):
                s.pause()

    def test_start_resumes_a_paused_session_with_an_identical_brief(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths, s = make(tmp)
            s.turn("stuck", "I am stuck")
            s.turn("attempt", M2)
            before = s._brief()
            s.pause()
            again = Session.start(paths, now=NOW + datetime.timedelta(hours=2))
            after = again.view()
            self.assertTrue(after.pop("resumed"))
            self.assertEqual(after["session"], before["session"])
            self.assertEqual({k: v for k, v in after.items() if k not in ("rules",)},
                             {k: v for k, v in before.items() if k not in ("rules",)})
            self.assertEqual(again.turn("attempt", "so it is one minus the sum of the others")["state"], "WORKING")

    def test_pause_from_launch_and_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths, s = make(tmp)
            s.pause()
            self.assertEqual(Session.start(paths, now=NOW).view()["state"], "LAUNCH")

    def test_fresh_ends_the_paused_session_as_partial_and_starts_a_new_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths, s = make(tmp)
            s.turn("attempt", M2)
            s.pause()
            sid = s.session_id
            new = Session.start(paths, now=NOW + datetime.timedelta(days=1), fresh=True)
            self.assertNotEqual(new.session_id, sid)
            self.assertEqual(new.view()["state"], "LAUNCH")
            old_events = Session.open(paths, sid).log.load()
            self.assertEqual(old_events[-1].type, "session_end")
            self.assertTrue(old_events[-1].data["partial"])
            self.assertEqual(Session.latest_session_id(paths), new.session_id)
            self.assertEqual(Session._latest_open(paths), new.session_id)

    def test_pause_then_end_does_not_duplicate_profile_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths, s = make(tmp)
            close_q1(s)
            s.say("Right. Do you have any lingering questions, or are you ready to move on?")
            s.pause()
            first = json.dumps(load_profile(paths.profile_json), sort_keys=True)
            s2 = Session.start(paths, now=NOW)
            s2.pause()
            self.assertEqual(json.dumps(load_profile(paths.profile_json), sort_keys=True), first)


class TestPauseCli(unittest.TestCase):
    def run_cli(self, tmp, *argv, stdin=None):
        import contextlib
        import io
        import sys
        out = io.StringIO()
        old = sys.stdin
        if stdin is not None:
            sys.stdin = io.StringIO(stdin)
        try:
            with contextlib.redirect_stdout(out):
                code = main(["--hub-root", tmp, "--course", "microecon", "--problem-set", "homework_4", *argv])
        finally:
            sys.stdin = old
        return code, json.loads(out.getvalue())

    def test_pause_and_end_partial_and_start_fresh(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths, s = make(tmp)
            code, res = self.run_cli(tmp, "pause")
            self.assertEqual((code, res["paused"]), (0, True))
            code, res = self.run_cli(tmp, "start")
            self.assertEqual((code, res["resumed"]), (0, True))
            code, res = self.run_cli(tmp, "end", "--partial")
            self.assertEqual((code, res["paused"]), (0, True))
            code, res = self.run_cli(tmp, "start", "--fresh")
            self.assertEqual((code, res["state"]), (0, "LAUNCH"))
            self.assertNotEqual(res["session"], s.session_id)
            code, res = self.run_cli(tmp, "end")
            self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
