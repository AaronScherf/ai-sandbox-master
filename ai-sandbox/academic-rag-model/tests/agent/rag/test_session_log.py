import os
import tempfile
import unittest

from agent.rag.rag_agent import Citation
from agent.rag.session_log import Event, append_event, load_events


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

    def test_grounded_defaults_true(self):
        with tempfile.TemporaryDirectory() as tmp:
            append_event([tmp], _event())
            loaded = load_events([tmp], "microecon")
        self.assertTrue(loaded[0].grounded)

    def test_grounded_false_round_trips(self):
        with tempfile.TemporaryDirectory() as tmp:
            append_event([tmp], _event(grounded=False, citations=[]))
            loaded = load_events([tmp], "microecon")
        self.assertFalse(loaded[0].grounded)
        self.assertEqual(loaded[0].citations, [])

    def test_a_pre_grounded_field_log_line_loads_as_grounded_true(self):
        # A line written before this field existed has no "grounded" key at
        # all -- Event(**data) must fall back to the default, not crash.
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, ".session_log", "microecon.jsonl")
            os.makedirs(os.path.dirname(path))
            with open(path, "w", encoding="utf-8") as f:
                f.write(
                    '{"type": "hint", "course": "microecon", "unit": null, "question": "q", '
                    '"text": "a", "citations": [], "timestamp": "2026-09-01T00:00:00+00:00", '
                    '"gap_tag": null, "correctness": null, "rigor": null, "course_fit": null}\n'
                )
            loaded = load_events([tmp], "microecon")
        self.assertTrue(loaded[0].grounded)


class TestLoadEventsMalformedLines(unittest.TestCase):
    """Regression for the final-review Important finding: because
    answer_question() now calls _recent_gap_tags() -> load_events() on
    every course-scoped question, a single corrupt log line (a truncated
    write, a future schema change) must not permanently break ordinary
    Q&A for that course -- it should be skipped, not raised."""

    def test_skips_a_truncated_json_line_and_loads_the_rest(self):
        with tempfile.TemporaryDirectory() as tmp:
            append_event([tmp], _event(question="q1"))
            path = os.path.join(tmp, ".session_log", "microecon.jsonl")
            with open(path, "a", encoding="utf-8") as f:
                f.write('{"type": "answer", "course": "microecon", incomplete\n')
            append_event([tmp], _event(question="q3"))
            loaded = load_events([tmp], "microecon")
        self.assertEqual([e.question for e in loaded], ["q1", "q3"])

    def test_skips_a_line_missing_a_required_field(self):
        with tempfile.TemporaryDirectory() as tmp:
            append_event([tmp], _event(question="q1"))
            path = os.path.join(tmp, ".session_log", "microecon.jsonl")
            with open(path, "a", encoding="utf-8") as f:
                f.write('{"type": "answer", "course": "microecon"}\n')  # missing required fields
            append_event([tmp], _event(question="q3"))
            loaded = load_events([tmp], "microecon")
        self.assertEqual([e.question for e in loaded], ["q1", "q3"])
