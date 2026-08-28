import json
import os
import tempfile
import unittest
from unittest.mock import MagicMock

from index_card import load_courses, load_shard, save_shard, recompute_course_entry
from index_search import build_arg_parser, rebuild, search


def _fake_client():
    client = MagicMock()
    gen_response = MagicMock()
    gen_response.text = (
        '{"title": "T", "doc_type": "ta_notes", "summary": "S.", '
        '"level": "introductory", "has_solutions": false}'
    )
    client.models.generate_content.return_value = gen_response
    embed_response = MagicMock()
    embedding = MagicMock()
    embedding.values = [0.1, 0.2]
    embed_response.embeddings = [embedding]
    client.models.embed_content.return_value = embed_response
    return client


def _make_notes_pdf(academic_hub_root, course, category, basename, write_markdown=True):
    pdf_dir = os.path.join(academic_hub_root, "academic_notes", course, category)
    os.makedirs(pdf_dir, exist_ok=True)
    pdf_path = os.path.join(pdf_dir, f"{basename}.pdf")
    with open(pdf_path, "wb") as f:
        f.write(f"fake pdf bytes for {basename}".encode())
    if write_markdown:
        out_dir = os.path.join(pdf_dir, "processed_outputs")
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, f"{basename}.md"), "w", encoding="utf-8") as f:
            f.write("---\ntotal_pages: 3\n---\n\nSome content.")
    return pdf_path


def _make_textbook(academic_hub_root, course, pdf_basename, folder_name, with_source_pdf_path=True):
    """Mirrors convert_textbook.py's real output layout: the PDF sits in
    textbooks-and-papers/ directly, its processed_outputs/<folder_name>/
    subfolder is NOT named after the PDF's filename (real corpus example:
    'Book of Proof.pdf' -> 'Hammack_Book_of_Proof_2025/'), and (once
    Task 9 lands) _metadata.json carries source_pdf_path back to it."""
    tp_dir = os.path.join(academic_hub_root, "academic_resources", course, "textbooks-and-papers")
    os.makedirs(tp_dir, exist_ok=True)
    pdf_path = os.path.join(tp_dir, f"{pdf_basename}.pdf")
    with open(pdf_path, "wb") as f:
        f.write(f"fake pdf bytes for {pdf_basename}".encode())

    book_dir = os.path.join(tp_dir, "processed_outputs", folder_name)
    os.makedirs(book_dir, exist_ok=True)
    with open(os.path.join(book_dir, f"{folder_name}.md"), "w", encoding="utf-8") as f:
        f.write("# Title\n\nChapter 1: Introduction...")

    metadata = {"total_pages_processed": 42}
    if with_source_pdf_path:
        rel_pdf_path = os.path.relpath(pdf_path, academic_hub_root).replace(os.sep, "/")
        metadata["source_pdf_path"] = rel_pdf_path
    with open(os.path.join(book_dir, f"{folder_name}_metadata.json"), "w", encoding="utf-8") as f:
        json.dump(metadata, f)
    return pdf_path


class TestRebuild(unittest.TestCase):
    def test_generates_cards_for_pdfs_with_a_markdown_sibling(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_notes_pdf(tmp, "math-camp", "ta_notes", "LN_Analysis")
            stats = rebuild(tmp, client=_fake_client())
            self.assertEqual(stats["generated"], 1)
            cards = load_shard(tmp, "math-camp")
            self.assertEqual(len(cards), 1)
            self.assertEqual(cards[0]["doc_type"], "ta_notes")

    def test_skips_pdfs_with_no_markdown_output_yet(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_notes_pdf(tmp, "math-camp", "ta_notes", "not_converted_yet", write_markdown=False)
            stats = rebuild(tmp, client=_fake_client())
            self.assertEqual(stats["generated"], 0)
            self.assertEqual(load_shard(tmp, "math-camp"), [])

    def test_second_run_with_no_changes_leaves_cards_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_notes_pdf(tmp, "math-camp", "ta_notes", "LN_Analysis")
            client = _fake_client()
            rebuild(tmp, client=client)
            stats = rebuild(tmp, client=client)
            self.assertEqual(stats["generated"], 0)
            self.assertEqual(stats["unchanged"], 1)
            self.assertEqual(client.models.generate_content.call_count, 1)  # not called again

    def test_force_regenerates_even_unchanged_cards(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_notes_pdf(tmp, "math-camp", "ta_notes", "LN_Analysis")
            client = _fake_client()
            rebuild(tmp, client=client)
            rebuild(tmp, client=client, force=True)
            self.assertEqual(client.models.generate_content.call_count, 2)

    def test_scoped_to_one_course_leaves_other_courses_alone(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_notes_pdf(tmp, "math-camp", "ta_notes", "LN_Analysis")
            _make_notes_pdf(tmp, "econ-101", "ta_notes", "Econ_Notes")
            stats = rebuild(tmp, client=_fake_client(), course="math-camp")
            self.assertEqual(stats["generated"], 1)
            self.assertEqual(load_shard(tmp, "econ-101"), [])

    def test_flags_orphaned_card_whose_pdf_disappeared(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_notes_pdf(tmp, "math-camp", "ta_notes", "LN_Analysis")
            rebuild(tmp, client=_fake_client())
            os.remove(os.path.join(tmp, "academic_notes", "math-camp", "ta_notes", "LN_Analysis.pdf"))
            stats = rebuild(tmp, client=_fake_client())
            self.assertEqual(stats["orphaned"], 1)
            self.assertTrue(load_shard(tmp, "math-camp")[0]["orphaned"])

    def test_prune_removes_confirmed_orphans_and_rolls_back_rollup(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_notes_pdf(tmp, "math-camp", "ta_notes", "LN_Analysis")
            rebuild(tmp, client=_fake_client())
            os.remove(os.path.join(tmp, "academic_notes", "math-camp", "ta_notes", "LN_Analysis.pdf"))
            rebuild(tmp, client=_fake_client())  # flags orphan
            stats = rebuild(tmp, client=_fake_client(), prune=True)
            self.assertEqual(stats["pruned"], 1)
            self.assertEqual(load_shard(tmp, "math-camp"), [])
            self.assertNotIn("math-camp", load_courses(tmp))

    def test_generates_a_textbook_card_when_source_pdf_path_is_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_textbook(tmp, "math-camp", "Book of Proof", "Hammack_Book_of_Proof_2025")
            stats = rebuild(tmp, client=_fake_client())
            self.assertEqual(stats["generated"], 1)
            cards = load_shard(tmp, "math-camp")
            self.assertEqual(len(cards), 1)
            self.assertTrue(cards[0]["path"].endswith("Hammack_Book_of_Proof_2025.md"))
            self.assertTrue(cards[0]["source_pdf_path"].endswith("Book of Proof.pdf"))

    def test_skips_textbook_with_no_source_pdf_path_yet(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_textbook(tmp, "math-camp", "Book of Proof", "Hammack_Book_of_Proof_2025",
                            with_source_pdf_path=False)
            stats = rebuild(tmp, client=_fake_client())
            self.assertEqual(stats["generated"], 0)
            self.assertEqual(stats["skipped_no_source_pdf"], 1)
            self.assertEqual(load_shard(tmp, "math-camp"), [])

    def test_textbook_content_sample_is_capped(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_textbook(tmp, "math-camp", "Big Book", "BigBook_2025")
            md_path = os.path.join(tmp, "academic_resources", "math-camp", "textbooks-and-papers",
                                    "processed_outputs", "BigBook_2025", "BigBook_2025.md")
            with open(md_path, "w", encoding="utf-8") as f:
                f.write("x" * 50000)
            client = _fake_client()
            rebuild(tmp, client=client)
            from index_card import TEXTBOOK_CONTENT_SAMPLE_CHARS
            prompt = client.models.generate_content.call_args.kwargs["contents"]
            self.assertLessEqual(len(prompt), 50000)  # the 50000-char body did NOT go in whole
            self.assertIn("x" * TEXTBOOK_CONTENT_SAMPLE_CHARS, prompt)


def _fake_query_client(query_embedding):
    client = MagicMock()
    embed_response = MagicMock()
    embedding = MagicMock()
    embedding.values = query_embedding
    embed_response.embeddings = [embedding]
    client.models.embed_content.return_value = embed_response
    return client


def _card(file_id, embedding, **overrides):
    card = {
        "file_id": file_id, "path": f"{file_id}.md", "source_pdf_path": f"{file_id}.pdf",
        "course": "math-camp", "doc_type": "textbook", "title": file_id,
        "summary": f"summary for {file_id}", "tags": [], "level": "introductory",
        "has_solutions": False, "page_count": 10, "rag_md_path": None, "embedding": embedding,
        "embedding_model": "gemini-embedding-001:768", "source_updated_at": "2026-01-01T00:00:00Z",
        "needs_indexing": False,
    }
    card.update(overrides)
    return card


class TestSearch(unittest.TestCase):
    def test_ranks_by_cosine_similarity_to_query(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [
                _card("close", [1.0, 0.0]),
                _card("far", [0.0, 1.0]),
            ])
            recompute_course_entry(tmp, "math-camp")
            results = search(tmp, "linear algebra", client=_fake_query_client([1.0, 0.0]))
            self.assertEqual(results[0].path, "close.md")
            self.assertGreater(results[0].score, results[1].score)

    def test_reason_is_the_cards_own_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [_card("x", [1.0, 0.0])])
            recompute_course_entry(tmp, "math-camp")
            results = search(tmp, "q", client=_fake_query_client([1.0, 0.0]))
            self.assertEqual(results[0].reason, "summary for x")

    def test_prefers_rag_md_path_over_path_when_set(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [
                _card("x", [1.0, 0.0], rag_md_path="x.rag.md"),
            ])
            recompute_course_entry(tmp, "math-camp")
            results = search(tmp, "q", client=_fake_query_client([1.0, 0.0]))
            self.assertEqual(results[0].path, "x.rag.md")

    def test_falls_back_to_path_when_rag_md_path_is_unset(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [_card("x", [1.0, 0.0])])  # rag_md_path defaults to None
            recompute_course_entry(tmp, "math-camp")
            results = search(tmp, "q", client=_fake_query_client([1.0, 0.0]))
            self.assertEqual(results[0].path, "x.md")

    def test_course_scope_skips_other_courses_entirely(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [_card("m", [1.0, 0.0])])
            save_shard(tmp, "spanish-101", [_card("s", [1.0, 0.0])])
            recompute_course_entry(tmp, "math-camp")
            recompute_course_entry(tmp, "spanish-101")
            results = search(tmp, "q", client=_fake_query_client([1.0, 0.0]), course="math-camp")
            self.assertEqual([r.path for r in results], ["m.md"])

    def test_top_k_limits_results(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [_card(str(i), [1.0, 0.0]) for i in range(10)])
            recompute_course_entry(tmp, "math-camp")
            results = search(tmp, "q", client=_fake_query_client([1.0, 0.0]), top_k=3)
            self.assertEqual(len(results), 3)

    def test_doc_type_filter_applies_before_truncation(self):
        with tempfile.TemporaryDirectory() as tmp:
            cards = [_card(f"p{i}", [1.0, 0.0], doc_type="problem_set") for i in range(5)]
            cards.append(_card("t", [0.99, 0.01], doc_type="textbook"))
            save_shard(tmp, "math-camp", cards)
            recompute_course_entry(tmp, "math-camp")
            results = search(tmp, "q", client=_fake_query_client([1.0, 0.0]), top_k=2, doc_type="textbook")
            self.assertEqual([r.path for r in results], ["t.md"])

    def test_has_solutions_filter(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [
                _card("solved", [1.0, 0.0], has_solutions=True),
                _card("unsolved", [1.0, 0.0], has_solutions=False),
            ])
            recompute_course_entry(tmp, "math-camp")
            results = search(tmp, "q", client=_fake_query_client([1.0, 0.0]), has_solutions=False)
            self.assertEqual([r.path for r in results], ["unsolved.md"])

    def test_max_level_filter_excludes_harder_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [
                _card("easy", [1.0, 0.0], level="introductory"),
                _card("hard", [1.0, 0.0], level="advanced"),
            ])
            recompute_course_entry(tmp, "math-camp")
            results = search(tmp, "q", client=_fake_query_client([1.0, 0.0]), max_level="introductory")
            self.assertEqual([r.path for r in results], ["easy.md"])

    def test_excludes_orphaned_and_needs_indexing_cards(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [
                _card("good", [1.0, 0.0]),
                _card("orphan", [1.0, 0.0], orphaned=True),
                _card("pending", [], needs_indexing=True),
            ])
            recompute_course_entry(tmp, "math-camp")
            results = search(tmp, "q", client=_fake_query_client([1.0, 0.0]))
            self.assertEqual([r.path for r in results], ["good.md"])

    def test_no_courses_indexed_yet_returns_empty_list_not_a_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            results = search(tmp, "q", client=_fake_query_client([1.0, 0.0]))
            self.assertEqual(results, [])


class TestCLIArgParsing(unittest.TestCase):
    def test_query_subcommand_defaults(self):
        args = build_arg_parser().parse_args(["query", "teach me linear algebra"])
        self.assertEqual(args.command, "query")
        self.assertEqual(args.query, "teach me linear algebra")
        self.assertIsNone(args.course)
        self.assertEqual(args.top_k, 5)
        self.assertIsNone(args.doc_type)
        self.assertIsNone(args.has_solutions)
        self.assertIsNone(args.max_level)

    def test_query_subcommand_with_filters(self):
        args = build_arg_parser().parse_args([
            "query", "eigenvalues", "--course", "math-camp", "--top-k", "3",
            "--doc-type", "problem_set", "--has-solutions", "false", "--max-level", "intermediate",
        ])
        self.assertEqual(args.course, "math-camp")
        self.assertEqual(args.top_k, 3)
        self.assertEqual(args.doc_type, "problem_set")
        self.assertFalse(args.has_solutions)
        self.assertEqual(args.max_level, "intermediate")

    def test_rebuild_subcommand_defaults(self):
        args = build_arg_parser().parse_args(["rebuild"])
        self.assertEqual(args.command, "rebuild")
        self.assertIsNone(args.course)
        self.assertFalse(args.force)
        self.assertFalse(args.prune)

    def test_rebuild_subcommand_with_flags(self):
        args = build_arg_parser().parse_args(["rebuild", "--course", "math-camp", "--force", "--prune"])
        self.assertEqual(args.course, "math-camp")
        self.assertTrue(args.force)
        self.assertTrue(args.prune)


if __name__ == "__main__":
    unittest.main()
