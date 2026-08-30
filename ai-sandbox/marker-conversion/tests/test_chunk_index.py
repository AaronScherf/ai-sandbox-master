import os
import tempfile
import unittest
from unittest.mock import MagicMock

from indexer.index_card import save_shard

from indexer.chunk_index import (
    chunks_path, load_chunks, save_chunks,
    _page_markers, _strip_front_matter_by_page, _strip_yaml_frontmatter,
    _Span, _split_by_headings, _detect_problem_boundaries, _split_by_pages,
    _CHUNK_MAX_CHARS, _subdivide_oversized, _page_range_for_span, _finalize_chunks,
    chunk_file, _folder_category_from_path, generate_chunks_for_file, chunk,
)


class TestChunkStorage(unittest.TestCase):
    def test_load_missing_shard_returns_empty_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(load_chunks(tmp, "math-camp"), [])

    def test_save_then_load_round_trips(self):
        with tempfile.TemporaryDirectory() as tmp:
            chunks = [{"chunk_id": "abc-000", "file_id": "abc", "text": "hello"}]
            save_chunks(tmp, "math-camp", chunks)
            self.assertEqual(load_chunks(tmp, "math-camp"), chunks)

    def test_chunks_path_lives_under_index_chunks(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = chunks_path(tmp, "math-camp")
            self.assertTrue(path.replace("\\", "/").endswith(".index/chunks/math-camp.json"))

    def test_save_creates_parent_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_chunks(tmp, "math-camp", [])
            self.assertTrue(os.path.isdir(os.path.join(tmp, ".index", "chunks")))


class TestStripYamlFrontmatter(unittest.TestCase):
    def test_strips_frontmatter_block(self):
        text = "---\nsource_pdf: a.pdf\ntags: []\n---\n\nBody content."
        self.assertEqual(_strip_yaml_frontmatter(text), "Body content.")

    def test_no_frontmatter_returns_text_unchanged(self):
        text = "<!-- page 1 -->\n\nBody content."
        self.assertEqual(_strip_yaml_frontmatter(text), text)


class TestStripFrontMatterByPage(unittest.TestCase):
    def test_drops_pages_at_or_before_the_boundary(self):
        body = (
            "<!-- page 1 -->\n\nTitle page.\n\n"
            "<!-- page 14 -->\n\nTable of contents.\n\n"
            "<!-- page 15 -->\n\nReal chapter 1 content."
        )
        result = _strip_front_matter_by_page(body, front_matter_end=14)
        self.assertNotIn("Title page", result)
        self.assertNotIn("Table of contents", result)
        self.assertIn("Real chapter 1 content", result)
        self.assertTrue(result.startswith("<!-- page 15 -->"))

    def test_every_page_is_front_matter_keeps_everything(self):
        body = "<!-- page 1 -->\n\nOnly page."
        self.assertEqual(_strip_front_matter_by_page(body, front_matter_end=99), body)


class TestPageMarkers(unittest.TestCase):
    def test_finds_every_marker_with_offsets(self):
        body = "before<!-- page 1 -->mid<!-- page 2 -->after"
        markers = _page_markers(body)
        self.assertEqual([p for p, _ in markers], [1, 2])
        self.assertEqual(body[markers[0][1]:markers[0][1] + 6], "<!-- p")

    def test_no_markers_returns_empty_list(self):
        self.assertEqual(_page_markers("no markers here"), [])


class TestSplitByHeadings(unittest.TestCase):
    def test_splits_at_each_heading_with_correct_spans(self):
        body = "# One\n\nFirst section.\n\n# Two\n\nSecond section."
        spans = _split_by_headings(body)
        self.assertEqual(len(spans), 2)
        self.assertEqual(body[spans[0].start:spans[0].end], "# One\n\nFirst section.\n\n")
        self.assertEqual(body[spans[1].start:spans[1].end], "# Two\n\nSecond section.")

    def test_nested_headings_build_a_heading_path(self):
        body = (
            "# 3 Optimization in Euclidean Space\n\nIntro.\n\n"
            "## 3.7 Optimization over a Convex Set\n\nContent."
        )
        spans = _split_by_headings(body)
        self.assertEqual(spans[0].heading_path, ["3 Optimization in Euclidean Space"])
        self.assertEqual(
            spans[1].heading_path,
            ["3 Optimization in Euclidean Space", "3.7 Optimization over a Convex Set"],
        )

    def test_sibling_after_deeper_heading_pops_the_stack(self):
        body = (
            "# One\n\nA.\n\n## One point one\n\nB.\n\n# Two\n\nC."
        )
        spans = _split_by_headings(body)
        # "Two" is a sibling of "One", not nested under "One point one"
        self.assertEqual(spans[2].heading_path, ["Two"])

    def test_every_span_tagged_with_heading_tier(self):
        body = "# One\n\nA.\n\n# Two\n\nB."
        spans = _split_by_headings(body)
        self.assertTrue(all(s.tier == "heading" for s in spans))
        self.assertTrue(all(s.problem_label is None for s in spans))

    def test_too_few_headings_returns_none(self):
        # Confirmed live: old_exam_2021.md has exactly 1 heading in a
        # 22-page document -- not real structure, must fall through to
        # the next tier rather than produce one giant "chunk".
        body = "Some text.\n\n### Standard Counterexamples\n\nMore text."
        self.assertIsNone(_split_by_headings(body))

    def test_no_headings_returns_none(self):
        self.assertIsNone(_split_by_headings("Just plain text, no headings at all."))


class TestDetectProblemBoundaries(unittest.TestCase):
    def test_plain_numbered_problems(self):
        # Real convention confirmed live in old_problem_set.md.
        body = (
            "1. For each of the following functions, state...\n\n"
            "2. Consider a production function...\n\n"
            "3. In an economy with n goods...\n\n"
        )
        spans = _detect_problem_boundaries(body)
        self.assertEqual(len(spans), 3)
        self.assertEqual(spans[0].problem_label, "Problem 1")
        self.assertEqual(spans[2].problem_label, "Problem 3")
        self.assertTrue(all(s.tier == "problem_number" for s in spans))

    def test_bold_practice_problem_convention(self):
        # Real convention confirmed live in Practice Sheet.md -- doesn't
        # match a bare "N." pattern since it's wrapped in ** and has a title.
        body = (
            "**Practice Problem 1. Involutions**\n\nLet V be...\n\n"
            "**Practice Problem 2. Norms**\n\nShow that...\n\n"
            "**Practice Problem 3. Rank**\n\nDetermine...\n\n"
        )
        spans = _detect_problem_boundaries(body)
        self.assertEqual(len(spans), 3)
        self.assertEqual(spans[0].problem_label, "Problem 1")

    def test_points_annotated_problems(self):
        # Real convention confirmed live in old_exam_2021.md.
        body = (
            "1. **(40 points)** Are the following statements true or false?\n\n"
            "2. **(15 points)** Consider the following matrix\n\n"
            "3. **(15 points)**. Consider the following function\n\n"
        )
        spans = _detect_problem_boundaries(body)
        self.assertEqual(len(spans), 3)

    def test_too_few_matches_returns_none(self):
        # A single accidental match (e.g. one stray "1." in prose) must
        # not be trusted as real document structure -- same "empirically
        # validate before trusting" bar retag.py's discovery phase uses.
        body = "Some prose that happens to mention item 1. and nothing else numbered."
        self.assertIsNone(_detect_problem_boundaries(body))

    def test_no_matches_returns_none(self):
        self.assertIsNone(_detect_problem_boundaries("No numbered problems in here."))


class TestSplitByPages(unittest.TestCase):
    def test_one_span_per_page_marker(self):
        body = "<!-- page 1 -->\n\nFirst.\n\n<!-- page 2 -->\n\nSecond."
        spans = _split_by_pages(body)
        self.assertEqual(len(spans), 2)
        self.assertTrue(all(s.tier == "page" for s in spans))
        self.assertEqual(body[spans[0].start:spans[0].end], "<!-- page 1 -->\n\nFirst.\n\n")

    def test_no_page_markers_returns_one_span_covering_everything(self):
        body = "Just some text with nothing structural in it at all."
        spans = _split_by_pages(body)
        self.assertEqual(len(spans), 1)
        self.assertEqual(spans[0].start, 0)
        self.assertEqual(spans[0].end, len(body))


class TestSubdivideOversized(unittest.TestCase):
    def test_span_under_the_cap_is_untouched(self):
        body = "# One\n\n" + ("x" * 100)
        spans = [_Span(0, len(body), "heading", heading_path=["One"])]
        result = _subdivide_oversized(spans, body)
        self.assertEqual(result, spans)

    def test_oversized_span_splits_at_paragraph_breaks(self):
        # Confirmed live: LN_Optimization.md has a real 34,054-char
        # section with no sub-headings -- must not become one giant chunk.
        paragraph = "x" * 1500
        body = f"{paragraph}\n\n{paragraph}\n\n{paragraph}"  # ~4500 chars, 3 paragraphs
        spans = [_Span(0, len(body), "heading", heading_path=["Big Section"])]
        result = _subdivide_oversized(spans, body)
        self.assertGreater(len(result), 1)
        for s in result:
            self.assertLessEqual(s.end - s.start, _CHUNK_MAX_CHARS)
            self.assertEqual(s.heading_path, ["Big Section"])  # metadata carried through

    def test_oversized_span_with_no_paragraph_breaks_stays_one_span(self):
        # No structural boundary to split at -- can't manufacture one,
        # so the size cap is a best-effort, not an absolute guarantee.
        body = "x" * (_CHUNK_MAX_CHARS + 500)
        spans = [_Span(0, len(body), "page")]
        result = _subdivide_oversized(spans, body)
        self.assertEqual(len(result), 1)


class TestPageRangeForSpan(unittest.TestCase):
    def test_span_spanning_multiple_pages(self):
        body = "<!-- page 44 -->\n\nA.\n\n<!-- page 45 -->\n\nB."
        markers = _page_markers(body)
        self.assertEqual(_page_range_for_span(0, len(body), markers), [44, 45])

    def test_span_starting_mid_page_uses_preceding_marker(self):
        body = "<!-- page 44 -->\n\nA.\n\nB."
        markers = _page_markers(body)
        mid_start = body.index("B.")
        self.assertEqual(_page_range_for_span(mid_start, len(body), markers), [44, 44])

    def test_no_markers_at_all_returns_none(self):
        self.assertEqual(_page_range_for_span(0, 10, []), None)


class TestFinalizeChunks(unittest.TestCase):
    def test_extracts_text_and_attaches_page_range(self):
        body = "<!-- page 1 -->\n\n# One\n\nReal content here, long enough to clear the minimum length filter and be kept."
        spans = [_Span(body.index("# One"), len(body), "heading", heading_path=["One"])]
        chunks = _finalize_chunks(spans, body)
        self.assertEqual(len(chunks), 1)
        self.assertIn("Real content here", chunks[0]["text"])
        self.assertEqual(chunks[0]["page_range"], [1, 1])
        self.assertEqual(chunks[0]["heading_path"], ["One"])
        self.assertIsNone(chunks[0]["problem_label"])

    def test_drops_chunks_under_the_minimum_length(self):
        body = "# One\n\n# Two\n\nReal content, long enough to clear the minimum length filter of 80 characters easily."
        spans = _split_by_headings(body)  # "# One" section is empty -- just the heading itself
        chunks = _finalize_chunks(spans, body)
        self.assertEqual(len(chunks), 1)
        self.assertIn("Two", chunks[0]["heading_path"])


class TestChunkFile(unittest.TestCase):
    def test_strips_yaml_frontmatter_before_chunking(self):
        text = (
            "---\nsource_pdf: a.pdf\ntags: []\n---\n\n"
            "# One\n\nFirst, long enough.\n\n# Two\n\nSecond, long enough to clear the minimum length filter."
        )
        chunks = chunk_file(text, doc_type="ta_notes", folder_category="ta_notes")
        self.assertTrue(all("source_pdf" not in c["text"] for c in chunks))

    def test_uses_heading_tier_when_available(self):
        text = "# One\n\nFirst, long enough to clear the minimum length filter easily here.\n\n# Two\n\nSecond, long enough to clear the minimum length filter easily here."
        chunks = chunk_file(text, doc_type="ta_notes", folder_category="ta_notes")
        self.assertTrue(all(c["tier"] == "heading" for c in chunks))

    def test_falls_back_to_problem_number_tier_for_problem_sets(self):
        text = (
            "1. First problem, long enough to clear the minimum length filter easily here.\n\n"
            "2. Second problem, long enough to clear the minimum length filter easily here.\n\n"
            "3. Third problem, long enough to clear the minimum length filter easily here.\n\n"
        )
        chunks = chunk_file(text, doc_type="problem_set", folder_category="problem_sets")
        self.assertTrue(all(c["tier"] == "problem_number" for c in chunks))

    def test_does_not_attempt_problem_number_tier_outside_problem_sets(self):
        # Same numbered-looking content, but not a problem_sets file --
        # tier 2 is scoped to problem_sets/recitation_slides only (spec §4).
        text = (
            "1. First point, long enough to clear the minimum length filter easily here.\n\n"
            "2. Second point, long enough to clear the minimum length filter easily here.\n\n"
            "3. Third point, long enough to clear the minimum length filter easily here.\n\n"
        )
        chunks = chunk_file(text, doc_type="ta_notes", folder_category="ta_notes")
        self.assertTrue(all(c["tier"] == "page" for c in chunks))

    def test_falls_back_to_page_tier_when_nothing_else_matches(self):
        text = "<!-- page 1 -->\n\nJust some unstructured prose, long enough to keep as a chunk here for sure."
        chunks = chunk_file(text, doc_type="problem_set", folder_category="problem_sets")
        self.assertTrue(all(c["tier"] == "page" for c in chunks))

    def test_textbook_front_matter_is_skipped(self):
        text = (
            "<!-- page 1 -->\n\n# Sheldon Axler\n\nAuthor bio front matter here, long enough to matter.\n\n"
            "<!-- page 14 -->\n\n# Contents\n\nTOC front matter here, long enough to matter for real.\n\n"
            "<!-- page 15 -->\n\n# 1 Vector Spaces\n\nReal chapter content, long enough to clear the filter."
        )
        chunks = chunk_file(text, doc_type="textbook", folder_category="textbooks-and-papers", front_matter_end=14)
        all_text = " ".join(c["text"] for c in chunks)
        self.assertNotIn("Author bio", all_text)
        self.assertNotIn("TOC front matter", all_text)
        self.assertIn("Real chapter content", all_text)

    def test_notes_files_are_unaffected_by_front_matter_end(self):
        # front_matter_end is only ever passed for doc_type == "textbook" --
        # confirms notes content is never accidentally truncated by it.
        text = "# Sheldon Axler\n\nThis is real notes content, not front matter here, long enough to keep.\n\n# Two\n\nMore content here, long enough to keep as well for sure."
        chunks = chunk_file(text, doc_type="ta_notes", folder_category="ta_notes", front_matter_end=14)
        all_text = " ".join(c["text"] for c in chunks)
        self.assertIn("real notes content", all_text)


class TestFolderCategoryFromPath(unittest.TestCase):
    def test_notes_path(self):
        path = "academic_notes/math-camp/recitation_slides/processed_outputs/a.md"
        self.assertEqual(_folder_category_from_path(path), "recitation_slides")

    def test_textbook_path(self):
        path = "academic_resources/math-camp/textbooks-and-papers/processed_outputs/Axler/Axler.rag.md"
        self.assertEqual(_folder_category_from_path(path), "textbooks-and-papers")

    def test_path_with_no_processed_outputs_segment_returns_empty_string(self):
        self.assertEqual(_folder_category_from_path("weird/path.md"), "")


def _fake_embed_client(dim=3):
    client = MagicMock()
    def embed_content(model, contents, config):
        response = MagicMock()
        embedding = MagicMock()
        embedding.values = [0.1] * dim
        response.embeddings = [embedding]
        return response
    client.models.embed_content.side_effect = embed_content
    return client


def _write_notes_md(tmp, rel_path, content):
    full_path = os.path.join(tmp, rel_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)
    return full_path


_A_MD = "academic_notes/math-camp/ta_notes/processed_outputs/a.md"
_B_MD = "academic_notes/math-camp/ta_notes/processed_outputs/b.md"

# Deliberately >> _CHUNK_MIN_CHARS (80) on its own, so a heading + this
# sentence always clears the minimum-length filter regardless of heading
# text length -- avoids the exact fixture-too-short mistake this task's
# tests hit on the first pass (fixed here, not worked around).
_LONG = "This section has plenty of real content in it, well over the eighty character minimum length threshold for sure."


def _two_section_doc(word_a="First", word_b="Second"):
    return f"# One\n\n{word_a}. {_LONG}\n\n# Two\n\n{word_b}. {_LONG}"


class TestGenerateChunksForFile(unittest.TestCase):
    def test_writes_chunks_for_a_new_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_notes_md(tmp, _A_MD, _two_section_doc())
            card = {"file_id": "abc123", "path": _A_MD, "doc_type": "ta_notes", "content_hash": "hash1"}
            client = _fake_embed_client()
            stats = generate_chunks_for_file(tmp, "math-camp", card, client)
            self.assertEqual(stats["chunks_written"], 2)
            chunks = load_chunks(tmp, "math-camp")
            self.assertEqual(len(chunks), 2)
            self.assertEqual(chunks[0]["file_id"], "abc123")
            self.assertEqual(chunks[0]["chunk_id"], "abc123-000")
            self.assertEqual(chunks[0]["content_hash"], "hash1")
            self.assertEqual(chunks[0]["embedding"], [0.1, 0.1, 0.1])

    def test_up_to_date_chunks_are_skipped_without_calling_the_api(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_notes_md(tmp, _A_MD, _two_section_doc())
            card = {"file_id": "abc123", "path": _A_MD, "doc_type": "ta_notes", "content_hash": "hash1"}
            client = _fake_embed_client()
            generate_chunks_for_file(tmp, "math-camp", card, client)
            client.models.embed_content.reset_mock()

            stats = generate_chunks_for_file(tmp, "math-camp", card, client)
            self.assertEqual(stats["chunks_written"], 0)
            client.models.embed_content.assert_not_called()

    def test_stale_content_hash_regenerates_all_chunks_for_that_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            md_path = _write_notes_md(tmp, _A_MD, _two_section_doc())
            card = {"file_id": "abc123", "path": _A_MD, "doc_type": "ta_notes", "content_hash": "hash1"}
            client = _fake_embed_client()
            generate_chunks_for_file(tmp, "math-camp", card, client)

            with open(md_path, "w", encoding="utf-8") as f:
                f.write(f"# One\n\nDifferent first. {_LONG}\n\n# Two\n\nDifferent second. {_LONG}\n\n# Three\n\nA new third section. {_LONG}")
            card["content_hash"] = "hash2"
            stats = generate_chunks_for_file(tmp, "math-camp", card, client)
            self.assertEqual(stats["chunks_written"], 3)
            chunks = load_chunks(tmp, "math-camp")
            self.assertEqual(len(chunks), 3)  # old 2 replaced, not appended to
            self.assertTrue(all(c["content_hash"] == "hash2" for c in chunks))

    def test_other_files_chunks_are_left_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_notes_md(tmp, _A_MD, _two_section_doc())
            _write_notes_md(tmp, _B_MD, _two_section_doc("Third", "Fourth"))
            client = _fake_embed_client()
            generate_chunks_for_file(tmp, "math-camp",
                {"file_id": "aaa", "path": _A_MD, "doc_type": "ta_notes", "content_hash": "h1"}, client)
            generate_chunks_for_file(tmp, "math-camp",
                {"file_id": "bbb", "path": _B_MD, "doc_type": "ta_notes", "content_hash": "h2"}, client)
            file_ids = {c["file_id"] for c in load_chunks(tmp, "math-camp")}
            self.assertEqual(file_ids, {"aaa", "bbb"})

    def test_embedding_failure_leaves_existing_chunks_untouched(self):
        # Atomicity (spec §5): a partial failure must not leave a
        # half-updated, inconsistent chunk set for this file.
        with tempfile.TemporaryDirectory() as tmp:
            md_path = _write_notes_md(tmp, _A_MD, _two_section_doc())
            card = {"file_id": "abc123", "path": _A_MD, "doc_type": "ta_notes", "content_hash": "hash1"}
            good_client = _fake_embed_client()
            generate_chunks_for_file(tmp, "math-camp", card, good_client)
            original = load_chunks(tmp, "math-camp")

            with open(md_path, "w", encoding="utf-8") as f:
                f.write(_two_section_doc("Rewritten", "Also rewritten"))
            card["content_hash"] = "hash2"
            bad_client = MagicMock()
            bad_client.models.embed_content.side_effect = RuntimeError("quota exceeded")
            with self.assertRaises(RuntimeError):
                generate_chunks_for_file(tmp, "math-camp", card, bad_client)
            self.assertEqual(load_chunks(tmp, "math-camp"), original)


_MISSING_MD = "academic_notes/math-camp/ta_notes/processed_outputs/missing.md"


def _make_card(file_id, path, doc_type="ta_notes", content_hash="h1", embedding=None):
    # No folder_category key -- real cards don't have one (see Task 8's
    # "Real interface note"); generate_chunks_for_file() derives it from
    # `path` via _folder_category_from_path().
    return {
        "file_id": file_id, "path": path, "course": "math-camp",
        "doc_type": doc_type, "content_hash": content_hash, "embedding": embedding or [0.1, 0.2],
        "orphaned": False, "needs_indexing": False,
    }


class TestChunkOrchestration(unittest.TestCase):
    def test_chunks_every_indexed_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_notes_md(tmp, _A_MD, _two_section_doc())
            save_shard(tmp, "math-camp", [_make_card("aaa", _A_MD)])
            stats = chunk(tmp, client=_fake_embed_client())
            self.assertEqual(stats["chunked"], 1)
            self.assertEqual(len(load_chunks(tmp, "math-camp")), 2)

    def test_second_run_with_no_changes_is_a_no_op(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_notes_md(tmp, _A_MD, _two_section_doc())
            save_shard(tmp, "math-camp", [_make_card("aaa", _A_MD)])
            client = _fake_embed_client()
            chunk(tmp, client=client)
            client.models.embed_content.reset_mock()

            stats = chunk(tmp, client=client)
            self.assertEqual(stats["chunked"], 0)
            self.assertEqual(stats["unchanged"], 1)
            client.models.embed_content.assert_not_called()

    def test_skips_cards_with_no_embedding_yet(self):
        # A needs_indexing card has no embedding -- nothing to chunk yet.
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [{
                "file_id": "aaa", "path": _A_MD, "course": "math-camp",
                "doc_type": "ta_notes", "content_hash": None, "embedding": [], "needs_indexing": True,
            }])
            stats = chunk(tmp, client=_fake_embed_client())
            self.assertEqual(stats["skipped_no_embedding"], 1)
            self.assertEqual(stats["chunked"], 0)

    def test_one_file_failure_does_not_abort_the_rest(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_notes_md(tmp, _A_MD, _two_section_doc())
            # _MISSING_MD deliberately not written -- generate_chunks_for_file
            # will fail to open it.
            save_shard(tmp, "math-camp", [
                _make_card("aaa", _A_MD), _make_card("bbb", _MISSING_MD),
            ])
            stats = chunk(tmp, client=_fake_embed_client())
            self.assertEqual(stats["chunked"], 1)
            self.assertEqual(stats["failed"], 1)
            file_ids = {c["file_id"] for c in load_chunks(tmp, "math-camp")}
            self.assertEqual(file_ids, {"aaa"})  # a.md's chunks still written

    def test_dry_run_calls_no_api_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_notes_md(tmp, _A_MD, _two_section_doc())
            save_shard(tmp, "math-camp", [_make_card("aaa", _A_MD)])
            client = _fake_embed_client()
            stats = chunk(tmp, client=client, dry_run=True)
            client.models.embed_content.assert_not_called()
            self.assertEqual(load_chunks(tmp, "math-camp"), [])
            self.assertEqual(stats["chunked"], 1)  # reports what WOULD be chunked

    def test_scoped_to_one_course(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_notes_md(tmp, _A_MD, _two_section_doc())
            _write_notes_md(tmp, _B_MD, _two_section_doc("Third", "Fourth"))
            save_shard(tmp, "math-camp", [_make_card("aaa", _A_MD)])
            save_shard(tmp, "econ-101", [_make_card("bbb", _B_MD)])
            stats = chunk(tmp, client=_fake_embed_client(), course="math-camp")
            self.assertEqual(stats["chunked"], 1)
            self.assertEqual(load_chunks(tmp, "econ-101"), [])


if __name__ == "__main__":
    unittest.main()
