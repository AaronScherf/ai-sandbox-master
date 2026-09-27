import os
import tempfile
import unittest

from rag.rag_agent import Citation
from rag.session_log import Event, append_event, load_events


def _event(**overrides):
    defaults = dict(
        type="answer", course="microecon", unit="homework_3", question="q",
        text="a", citations=[Citation(chunk_id="c-1", file_id="c", path="c.md", citation="p. 1", root="/root")],
        timestamp="2026-09-27T00:00:00+00:00", gap_tag=None, correctness=None, rigor=None, course_fit=None,
    )
    defaults.update(overrides)
    return Event(**defaults)


class TestLoadEventsMissingFile(unittest.TestCase):
    def test_returns_empty_list_when_no_log_exists_yet(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(load_events([tmp], "microecon"), [])


class TestAppendAndLoadRoundTrip(unittest.TestCase):
    def test_round_trips_a_single_event(self):
        with tempfile.TemporaryDirectory() as tmp:
            append_event([tmp], _event())
            loaded = load_events([tmp], "microecon")
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0].question, "q")
        self.assertEqual(loaded[0].citations[0].citation, "p. 1")

    def test_appends_do_not_overwrite_prior_events(self):
        with tempfile.TemporaryDirectory() as tmp:
            append_event([tmp], _event(question="q1"))
            append_event([tmp], _event(question="q2"))
            loaded = load_events([tmp], "microecon")
        self.assertEqual([e.question for e in loaded], ["q1", "q2"])

    def test_unit_filter_excludes_other_units(self):
        with tempfile.TemporaryDirectory() as tmp:
            append_event([tmp], _event(unit="homework_3", question="q1"))
            append_event([tmp], _event(unit="homework_4", question="q2"))
            loaded = load_events([tmp], "microecon", unit="homework_3")
        self.assertEqual([e.question for e in loaded], ["q1"])

    def test_no_unit_filter_loads_all_units(self):
        with tempfile.TemporaryDirectory() as tmp:
            append_event([tmp], _event(unit="homework_3"))
            append_event([tmp], _event(unit="homework_4"))
            loaded = load_events([tmp], "microecon")
        self.assertEqual(len(loaded), 2)

    def test_course_filter_excludes_other_courses(self):
        with tempfile.TemporaryDirectory() as tmp:
            append_event([tmp], _event(course="microecon"))
            append_event([tmp], _event(course="econometrics"))
            loaded = load_events([tmp], "microecon")
        self.assertEqual(len(loaded), 1)

    def test_draft_fields_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            append_event([tmp], _event(type="draft", gap_tag="vacuous-case", correctness=4, rigor=3, course_fit=5))
            loaded = load_events([tmp], "microecon")
        self.assertEqual(loaded[0].gap_tag, "vacuous-case")
        self.assertEqual((loaded[0].correctness, loaded[0].rigor, loaded[0].course_fit), (4, 3, 5))
