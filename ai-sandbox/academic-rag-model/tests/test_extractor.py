import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from indexer.index_card import save_shard

from problem_corpus.extractor import (
    _extract_file, _folder_category_from_path, _record_id, build_arg_parser,
    extract_problems, _single_root, _DEFAULT_ROOT,
)
from problem_corpus.llm_extract import ExtractedRecord
from problem_corpus.store import load_records


def _write_md(tmp, rel_path, content):
    full_path = os.path.join(tmp, rel_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)
    return full_path


_PROBLEM_SET_MD = "academic_notes/math-camp/problem_sets/processed_outputs/set.md"
_MISSING_MD = "academic_notes/math-camp/problem_sets/processed_outputs/missing.md"
_TEXTBOOK_MD = "academic_resources/math-camp/textbooks/processed_outputs/book.md"
_NOTES_MD = "academic_notes/math-camp/ta_notes/processed_outputs/notes.md"

_THREE_PROBLEMS = (
    "1. Find the eigenvalues of A.\n\n"
    "2. Prove the set is compact.\n\n"
    "3. Show the sequence converges.\n\n"
)

_TWO_PROBLEMS_ONLY = "1. Find X.\n\n2. Find Y.\n\n"  # below _MIN_PROBLEM_MATCHES -- no spans detected


def _make_card(file_id, path, content_hash="h1"):
    # No folder_category key -- real cards don't have one; extractor.py
    # derives it from `path` via _folder_category_from_path().
    return {
        "file_id": file_id, "path": path, "course": "math-camp",
        "doc_type": "problem_set", "content_hash": content_hash, "embedding": [0.1],
        "orphaned": False, "needs_indexing": False,
    }


def _fake_client():
    """A Gemini client stand-in isn't used directly by these tests --
    extract_record() itself is mocked (per this project's established
    network-call-mocked-only convention) -- but _extract_file/
    extract_problems still take a `client` positional argument, so a
    plain placeholder is enough."""
    return MagicMock()


class TestFolderCategoryFromPath(unittest.TestCase):
    def test_problem_sets_path(self):
        self.assertEqual(_folder_category_from_path(_PROBLEM_SET_MD), "problem_sets")

    def test_textbook_path(self):
        self.assertEqual(_folder_category_from_path(_TEXTBOOK_MD), "textbooks")

    def test_path_with_no_processed_outputs_segment_returns_empty_string(self):
        self.assertEqual(_folder_category_from_path("some/other/path.md"), "")


class TestRecordId(unittest.TestCase):
    def test_same_inputs_produce_same_id(self):
        self.assertEqual(_record_id("aaa", 0, "Problem 1"), _record_id("aaa", 0, "Problem 1"))

    def test_different_span_index_produces_different_id(self):
        # Collision-safety for two spans that both fall back to the bare
        # label "Problem" (no number) -- span index disambiguates them.
        self.assertNotEqual(_record_id("aaa", 0, "Problem"), _record_id("aaa", 1, "Problem"))

    def test_different_file_id_produces_different_id(self):
        self.assertNotEqual(_record_id("aaa", 0, "Problem 1"), _record_id("bbb", 0, "Problem 1"))


class TestExtractFile(unittest.TestCase):
    def test_extracts_every_span_in_a_new_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_md(tmp, _PROBLEM_SET_MD, _THREE_PROBLEMS)
            card = _make_card("aaa", _PROBLEM_SET_MD)
            responses = [
                ExtractedRecord(problem_text="Find the eigenvalues of A.", solution_text=None, topic_tag="eigenvalues"),
                ExtractedRecord(problem_text="Prove the set is compact.", solution_text="Proof.", topic_tag="compactness"),
                ExtractedRecord(problem_text="Show the sequence converges.", solution_text=None, topic_tag="convergence"),
            ]
            with patch("problem_corpus.extractor.extract_record", side_effect=responses):
                result = _extract_file(tmp, "math-camp", card, _fake_client())
            self.assertEqual(result, {"status": "extracted", "problems_extracted": 3})
            records = load_records(tmp, "math-camp")
            self.assertEqual(len(records), 3)
            self.assertEqual(records[1]["solution_text"], "Proof.")
            self.assertEqual(records[1]["solution_provenance"], "student_attempt")
            self.assertIsNone(records[0]["solution_provenance"])

    def test_solution_and_provenance_are_both_null_together(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_md(tmp, _PROBLEM_SET_MD, _THREE_PROBLEMS)
            card = _make_card("aaa", _PROBLEM_SET_MD)
            extracted = ExtractedRecord(problem_text="p", solution_text=None, topic_tag="t")
            with patch("problem_corpus.extractor.extract_record", return_value=extracted):
                _extract_file(tmp, "math-camp", card, _fake_client())
            records = load_records(tmp, "math-camp")
            for r in records:
                self.assertIsNone(r["solution_text"])
                self.assertIsNone(r["solution_provenance"])

    def test_record_source_fields_are_populated(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_md(tmp, _PROBLEM_SET_MD, _THREE_PROBLEMS)
            card = _make_card("aaa", _PROBLEM_SET_MD)
            extracted = ExtractedRecord(problem_text="p", solution_text=None, topic_tag="t")
            with patch("problem_corpus.extractor.extract_record", return_value=extracted):
                _extract_file(tmp, "math-camp", card, _fake_client())
            record = load_records(tmp, "math-camp")[0]
            self.assertEqual(record["source"]["file_id"], "aaa")
            self.assertEqual(record["source"]["path"], _PROBLEM_SET_MD)
            self.assertEqual(record["source"]["root"], tmp)
            self.assertEqual(record["source"]["folder_category"], "problem_sets")
            self.assertIn("set.md", record["source"]["citation"])
            self.assertIn("Problem 1", record["source"]["citation"])
            self.assertEqual(record["content_hash"], "h1")
            self.assertEqual(record["course"], "math-camp")

    def test_unchanged_content_hash_is_skipped_without_calling_gemini(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_md(tmp, _PROBLEM_SET_MD, _THREE_PROBLEMS)
            card = _make_card("aaa", _PROBLEM_SET_MD)
            extracted = ExtractedRecord(problem_text="p", solution_text=None, topic_tag="t")
            with patch("problem_corpus.extractor.extract_record", return_value=extracted) as mock_extract:
                _extract_file(tmp, "math-camp", card, _fake_client())
                mock_extract.reset_mock()
                result = _extract_file(tmp, "math-camp", card, _fake_client())
            self.assertEqual(result, {"status": "unchanged"})
            mock_extract.assert_not_called()

    def test_stale_content_hash_re_extracts_and_replaces(self):
        with tempfile.TemporaryDirectory() as tmp:
            md_path = _write_md(tmp, _PROBLEM_SET_MD, _THREE_PROBLEMS)
            card = _make_card("aaa", _PROBLEM_SET_MD)
            extracted = ExtractedRecord(problem_text="p", solution_text=None, topic_tag="t")
            with patch("problem_corpus.extractor.extract_record", return_value=extracted):
                _extract_file(tmp, "math-camp", card, _fake_client())
                with open(md_path, "w", encoding="utf-8") as f:
                    f.write(_THREE_PROBLEMS + "\n4. A fourth problem.\n\n")
                card["content_hash"] = "h2"
                result = _extract_file(tmp, "math-camp", card, _fake_client())
            self.assertEqual(result["status"], "extracted")
            records = load_records(tmp, "math-camp")
            self.assertTrue(all(r["content_hash"] == "h2" for r in records))

    def test_zero_spans_detected_is_skipped_not_failed(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_md(tmp, _PROBLEM_SET_MD, _TWO_PROBLEMS_ONLY)
            card = _make_card("aaa", _PROBLEM_SET_MD)
            result = _extract_file(tmp, "math-camp", card, _fake_client())
            self.assertEqual(result, {"status": "skipped_no_problems"})
            self.assertEqual(load_records(tmp, "math-camp"), [])

    def test_one_failed_span_does_not_drop_the_rest(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_md(tmp, _PROBLEM_SET_MD, _THREE_PROBLEMS)
            card = _make_card("aaa", _PROBLEM_SET_MD)
            responses = [
                ExtractedRecord(problem_text="Find the eigenvalues of A.", solution_text=None, topic_tag="eigenvalues"),
                None,  # this span's extraction failed
                ExtractedRecord(problem_text="Show the sequence converges.", solution_text=None, topic_tag="convergence"),
            ]
            with patch("problem_corpus.extractor.extract_record", side_effect=responses):
                result = _extract_file(tmp, "math-camp", card, _fake_client())
            self.assertEqual(result, {"status": "extracted", "problems_extracted": 2})
            self.assertEqual(len(load_records(tmp, "math-camp")), 2)

    def test_frontmatter_is_stripped_before_boundary_detection(self):
        with tempfile.TemporaryDirectory() as tmp:
            content = "---\nsource_pdf: set.pdf\ntags: [algebra]\n---\n\n" + _THREE_PROBLEMS
            _write_md(tmp, _PROBLEM_SET_MD, content)
            card = _make_card("aaa", _PROBLEM_SET_MD)
            extracted = ExtractedRecord(problem_text="p", solution_text=None, topic_tag="t")
            with patch("problem_corpus.extractor.extract_record", return_value=extracted) as mock_extract:
                _extract_file(tmp, "math-camp", card, _fake_client())
            first_span_arg = mock_extract.call_args_list[0].args[0]
            self.assertNotIn("source_pdf", first_span_arg)


class TestExtractProblems(unittest.TestCase):
    def test_extracts_every_problem_bearing_card(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_md(tmp, _PROBLEM_SET_MD, _THREE_PROBLEMS)
            save_shard(tmp, "math-camp", [_make_card("aaa", _PROBLEM_SET_MD)])
            extracted = ExtractedRecord(problem_text="p", solution_text=None, topic_tag="t")
            with patch("problem_corpus.extractor.extract_record", return_value=extracted):
                stats = extract_problems(tmp, _fake_client())
            self.assertEqual(stats["extracted"], 1)
            self.assertEqual(stats["problems_extracted"], 3)

    def test_non_problem_bearing_folder_category_is_skipped_entirely(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_md(tmp, _NOTES_MD, _THREE_PROBLEMS)
            save_shard(tmp, "math-camp", [_make_card("aaa", _NOTES_MD)])
            with patch("problem_corpus.extractor.extract_record") as mock_extract:
                stats = extract_problems(tmp, _fake_client())
            mock_extract.assert_not_called()
            self.assertEqual(stats["extracted"], 0)

    def test_orphaned_cards_are_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_md(tmp, _PROBLEM_SET_MD, _THREE_PROBLEMS)
            card = _make_card("aaa", _PROBLEM_SET_MD)
            card["orphaned"] = True
            save_shard(tmp, "math-camp", [card])
            stats = extract_problems(tmp, _fake_client())
            self.assertEqual(stats["extracted"], 0)
            self.assertEqual(stats["unchanged"], 0)
            self.assertEqual(stats["skipped_no_problems"], 0)

    def test_needs_indexing_cards_are_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_md(tmp, _PROBLEM_SET_MD, _THREE_PROBLEMS)
            card = _make_card("aaa", _PROBLEM_SET_MD)
            card["needs_indexing"] = True
            save_shard(tmp, "math-camp", [card])
            stats = extract_problems(tmp, _fake_client())
            self.assertEqual(stats["extracted"], 0)

    def test_second_run_with_no_changes_reports_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_md(tmp, _PROBLEM_SET_MD, _THREE_PROBLEMS)
            save_shard(tmp, "math-camp", [_make_card("aaa", _PROBLEM_SET_MD)])
            extracted = ExtractedRecord(problem_text="p", solution_text=None, topic_tag="t")
            with patch("problem_corpus.extractor.extract_record", return_value=extracted) as mock_extract:
                extract_problems(tmp, _fake_client())
                mock_extract.reset_mock()
                stats = extract_problems(tmp, _fake_client())
            self.assertEqual(stats["unchanged"], 1)
            self.assertEqual(stats["extracted"], 0)
            mock_extract.assert_not_called()

    def test_one_file_failure_does_not_abort_the_rest(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_md(tmp, _PROBLEM_SET_MD, _THREE_PROBLEMS)
            # _MISSING_MD deliberately not written -- _extract_file will
            # fail to open it.
            save_shard(tmp, "math-camp", [
                _make_card("aaa", _PROBLEM_SET_MD), _make_card("bbb", _MISSING_MD),
            ])
            extracted = ExtractedRecord(problem_text="p", solution_text=None, topic_tag="t")
            with patch("problem_corpus.extractor.extract_record", return_value=extracted):
                stats = extract_problems(tmp, _fake_client())
            self.assertEqual(stats["extracted"], 1)
            self.assertEqual(stats["failed"], 1)
            file_ids = {r["source"]["file_id"] for r in load_records(tmp, "math-camp")}
            self.assertEqual(file_ids, {"aaa"})

    def test_dry_run_calls_no_gemini_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_md(tmp, _PROBLEM_SET_MD, _THREE_PROBLEMS)
            save_shard(tmp, "math-camp", [_make_card("aaa", _PROBLEM_SET_MD)])
            with patch("problem_corpus.extractor.extract_record") as mock_extract:
                stats = extract_problems(tmp, _fake_client(), dry_run=True)
            mock_extract.assert_not_called()
            self.assertEqual(load_records(tmp, "math-camp"), [])
            self.assertEqual(stats["extracted"], 1)  # reports what WOULD be extracted

    def test_scoped_to_one_course(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_md(tmp, _PROBLEM_SET_MD, _THREE_PROBLEMS)
            other_md = "academic_notes/econ-101/problem_sets/processed_outputs/set.md"
            _write_md(tmp, other_md, _THREE_PROBLEMS)
            save_shard(tmp, "math-camp", [_make_card("aaa", _PROBLEM_SET_MD)])
            save_shard(tmp, "econ-101", [_make_card("bbb", other_md)])
            extracted = ExtractedRecord(problem_text="p", solution_text=None, topic_tag="t")
            with patch("problem_corpus.extractor.extract_record", return_value=extracted):
                stats = extract_problems(tmp, _fake_client(), course="math-camp")
            self.assertEqual(stats["extracted"], 1)
            self.assertEqual(load_records(tmp, "econ-101"), [])

    def test_scoped_to_one_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_md(tmp, _PROBLEM_SET_MD, _THREE_PROBLEMS)
            other_md = "academic_notes/math-camp/problem_sets/processed_outputs/other.md"
            _write_md(tmp, other_md, _THREE_PROBLEMS)
            save_shard(tmp, "math-camp", [
                _make_card("aaa", _PROBLEM_SET_MD), _make_card("bbb", other_md),
            ])
            extracted = ExtractedRecord(problem_text="p", solution_text=None, topic_tag="t")
            with patch("problem_corpus.extractor.extract_record", return_value=extracted):
                stats = extract_problems(tmp, _fake_client(), file="set.md")
            self.assertEqual(stats["extracted"], 1)
            file_ids = {r["source"]["file_id"] for r in load_records(tmp, "math-camp")}
            self.assertEqual(file_ids, {"aaa"})


class TestBuildArgParser(unittest.TestCase):
    def test_extract_subcommand_defaults(self):
        args = build_arg_parser().parse_args(["extract"])
        self.assertEqual(args.command, "extract")
        self.assertIsNone(args.course)
        self.assertIsNone(args.file)
        self.assertFalse(args.dry_run)

    def test_extract_subcommand_with_flags(self):
        args = build_arg_parser().parse_args(["extract", "--course", "math-camp", "--file", "a.md", "--dry-run"])
        self.assertEqual(args.course, "math-camp")
        self.assertEqual(args.file, "a.md")
        self.assertTrue(args.dry_run)

    def test_root_defaults_to_none_when_omitted(self):
        args = build_arg_parser().parse_args(["extract"])
        self.assertIsNone(args.root)

    def test_root_is_repeatable_at_parse_time(self):
        args = build_arg_parser().parse_args(["--root", "a", "--root", "b", "extract"])
        self.assertEqual(args.root, ["a", "b"])


class TestSingleRoot(unittest.TestCase):
    def test_defaults_when_no_root_given(self):
        args = build_arg_parser().parse_args(["extract"])
        self.assertEqual(_single_root(args), _DEFAULT_ROOT)

    def test_returns_the_one_given_root(self):
        args = build_arg_parser().parse_args(["--root", "/x", "extract"])
        self.assertEqual(_single_root(args), "/x")

    def test_raises_on_more_than_one_root(self):
        args = build_arg_parser().parse_args(["--root", "/x", "--root", "/y", "extract"])
        with self.assertRaises(SystemExit):
            _single_root(args)


if __name__ == "__main__":
    unittest.main()
