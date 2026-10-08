import os
import tempfile
import unittest

from agent.tutor.events import EventLog
from agent.tutor.paths import TutorPaths


class TestTutorPaths(unittest.TestCase):
    def test_layout(self):
        p = TutorPaths("/hub", "microecon", "homework_4")
        norm = lambda s: s.replace("\\", "/")
        self.assertEqual(norm(p.tutoring_dir), "/hub/academic_notes/microecon/tutoring")
        self.assertEqual(norm(p.packet_dir), "/hub/academic_notes/microecon/tutoring/homework_4/packet")
        self.assertEqual(norm(p.sessions_dir), "/hub/academic_notes/microecon/tutoring/homework_4/sessions")
        self.assertEqual(norm(p.profile_json), "/hub/academic_notes/microecon/tutoring/learner_profile.json")
        self.assertEqual(norm(p.profile_md), "/hub/academic_notes/microecon/tutoring/learner_profile.md")


class TestEventLog(unittest.TestCase):
    def test_missing_file_loads_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(EventLog(os.path.join(tmp, "e.jsonl")).load(), [])

    def test_append_assigns_sequential_ids_and_round_trips_unicode(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = EventLog(os.path.join(tmp, "sub", "e.jsonl"))
            a = log.append("student", part="q1", state="WORKING", hint_level=1, intent="attempt", text="x ≽ y, \"quoted\" $a$")
            b = log.append("tutor_say", part="q1", state="WORKING", text="ok", data={"k": 1})
            self.assertEqual((a.id, b.id), (1, 2))
            loaded = log.load()
            self.assertEqual(loaded[0].text, "x ≽ y, \"quoted\" $a$")
            self.assertEqual(loaded[1].data, {"k": 1})
            self.assertEqual(loaded[0].hint_level, 1)

    def test_corrupt_line_raises_with_path_and_line_number(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "e.jsonl")
            log = EventLog(path)
            log.append("student", text="a")
            with open(path, "a", encoding="utf-8") as f:
                f.write('{"id": 2, "ts": "t", "ty')  # half-written crash
            with self.assertRaises(ValueError) as ctx:
                log.load()
            self.assertIn("line 2", str(ctx.exception))
            self.assertIn(path, str(ctx.exception))
