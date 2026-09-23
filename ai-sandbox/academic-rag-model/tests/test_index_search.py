import json
import os
import tempfile
import time
import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from indexer.chunk_index import save_chunks
from indexer.index_card import (
    compute_file_id, find_card_by_file_id, load_courses, load_shard, load_tags, save_shard, save_tags,
    recompute_course_entry,
)
from indexer.index_search import (
    _DEFAULT_ROOT, _is_stale, _single_root, build_arg_parser, rebuild, search, search_passages,
    _render_citation,
)


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


def _make_textbook(academic_hub_root, course, pdf_basename, folder_name, with_source_pdf_path=True,
                    category_folder_name="textbooks-and-papers", subfolder=None):
    """Mirrors convert_textbook.py's real output layout: the PDF sits in
    textbooks-and-papers/ directly, its processed_outputs/<folder_name>/
    subfolder is NOT named after the PDF's filename (real corpus example:
    'Book of Proof.pdf' -> 'Hammack_Book_of_Proof_2025/'), and (once
    Task 9 lands) _metadata.json carries source_pdf_path back to it.

    category_folder_name defaults to the long-standing name but accepts
    "textbooks" too, to exercise the folder-name alias math-camp uses on
    disk (see docs/status/2026-09-06-problem-corpus-extraction-status.md).

    subfolder, if given, nests the PDF and its processed_outputs/ one
    level deeper (e.g. "Bonus") -- mirrors a course's textbook folder
    having its own subfolder for supplementary readings converted in a
    separate batch (see convert_textbook_agent_instructions.md)."""
    tp_dir = os.path.join(academic_hub_root, "academic_resources", course, category_folder_name)
    if subfolder:
        tp_dir = os.path.join(tp_dir, subfolder)
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


def _make_video_lecture_note(academic_hub_root, course, slug, member_video_ids,
                              markdown="# Real Analysis\n\nSome content."):
    lecture_notes_dir = os.path.join(academic_hub_root, "academic_notes", course, "lecture_notes")
    os.makedirs(lecture_notes_dir, exist_ok=True)
    md_path = os.path.join(lecture_notes_dir, f"{slug}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(markdown)
    with open(os.path.join(lecture_notes_dir, f"{slug}.meta.json"), "w", encoding="utf-8") as f:
        json.dump({"member_video_ids": member_video_ids}, f)
    return md_path


def _make_excalidraw_note(academic_hub_root, course, category, basename, write_rag_md=True):
    note_dir = os.path.join(academic_hub_root, "academic_notes", course, category)
    os.makedirs(note_dir, exist_ok=True)
    md_path = os.path.join(note_dir, f"{basename}.excalidraw.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("---\n---\n\nfake compressed-json scene data")
    svg_path = os.path.join(note_dir, f"{basename}.excalidraw.svg")
    with open(svg_path, "w", encoding="utf-8") as f:
        f.write("<svg></svg>")
    if write_rag_md:
        out_dir = os.path.join(note_dir, "processed_outputs")
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, f"{basename}.excalidraw.rag.md"), "w", encoding="utf-8") as f:
            f.write("---\nchunks: 2\n---\n\nExpanded prose content.")
    return md_path, svg_path


class TestIsStale(unittest.TestCase):
    def test_matching_content_hash_is_not_stale_regardless_of_mtime(self):
        # content_hash is decisive whenever the card has one -- mtime
        # doesn't even get consulted. Real motivation: a container/session
        # remount can reset every .md's mtime to the same future instant
        # without touching a single byte of content.
        card = {"source_updated_at": "2026-01-01T00:00:00+00:00", "content_hash": "abc123"}
        far_future_mtime = time.mktime(time.strptime("2099-01-01", "%Y-%m-%d"))
        self.assertFalse(_is_stale(card, far_future_mtime, "abc123"))

    def test_differing_content_hash_is_stale_regardless_of_mtime(self):
        card = {"source_updated_at": "2099-01-01T00:00:00+00:00", "content_hash": "abc123"}
        very_old_mtime = time.mktime(time.strptime("2000-01-01", "%Y-%m-%d"))
        self.assertTrue(_is_stale(card, very_old_mtime, "different-hash"))

    def test_no_stored_hash_falls_back_to_mtime_comparison_stale(self):
        card = {"source_updated_at": "2026-01-01T00:00:00+00:00"}  # legacy card, no content_hash key
        newer_mtime = time.mktime(time.strptime("2026-01-02", "%Y-%m-%d"))
        self.assertTrue(_is_stale(card, newer_mtime, "irrelevant-hash"))

    def test_no_stored_hash_falls_back_to_mtime_comparison_not_stale(self):
        card = {"source_updated_at": "2026-01-05T00:00:00+00:00"}
        older_mtime = time.mktime(time.strptime("2026-01-01", "%Y-%m-%d"))
        self.assertFalse(_is_stale(card, older_mtime, "irrelevant-hash"))

    def test_missing_source_updated_at_is_treated_as_stale(self):
        self.assertTrue(_is_stale({}, time.time(), "irrelevant-hash"))

    def test_unparseable_source_updated_at_is_treated_as_stale(self):
        self.assertTrue(_is_stale({"source_updated_at": "not-a-date"}, time.time(), "irrelevant-hash"))


class TestRebuild(unittest.TestCase):
    def test_generates_cards_for_pdfs_with_a_markdown_sibling(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_notes_pdf(tmp, "math-camp", "ta_notes", "LN_Analysis")
            stats = rebuild(tmp, client=_fake_client())
            self.assertEqual(stats["generated"], 1)
            cards = load_shard(tmp, "math-camp")
            self.assertEqual(len(cards), 1)
            self.assertEqual(cards[0]["doc_type"], "ta_notes")

    def test_a_needs_indexing_card_is_retried_on_the_next_plain_rebuild(self):
        # Real finding: a card left as needs_indexing=True after a failed
        # generation attempt correctly bypasses "already current" on the
        # next rebuild, but was never actually retried -- reconcile_and_write()
        # finds the old card by file_id and just patches its metadata
        # unless the caller explicitly removes it first to force a true
        # regeneration, which rebuild only did for force/stale, not for
        # needs_indexing.
        with tempfile.TemporaryDirectory() as tmp:
            _make_notes_pdf(tmp, "math-camp", "ta_notes", "flaky")
            bad_client = MagicMock()
            bad_client.models.generate_content.side_effect = RuntimeError("quota exceeded")
            rebuild(tmp, client=bad_client)
            self.assertTrue(load_shard(tmp, "math-camp")[0]["needs_indexing"])

            good_client = _fake_client()
            stats = rebuild(tmp, client=good_client)
            self.assertEqual(stats["updated"], 1)
            cards = load_shard(tmp, "math-camp")
            self.assertEqual(len(cards), 1)
            self.assertFalse(cards[0]["needs_indexing"])
            self.assertEqual(cards[0]["doc_type"], "ta_notes")

    def test_skips_pdfs_with_no_markdown_output_yet(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_notes_pdf(tmp, "math-camp", "ta_notes", "not_converted_yet", write_markdown=False)
            stats = rebuild(tmp, client=_fake_client())
            self.assertEqual(stats["generated"], 0)
            self.assertEqual(load_shard(tmp, "math-camp"), [])

    def test_discovers_a_pdf_nested_below_the_category_directory(self):
        # Real finding (2026-09-22): a user reorganizing ta_notes/ into
        # year subfolders (ta_notes/2026/foo.pdf) found rebuild() silently
        # stopped seeing those PDFs at all -- _notes_pdf_paths only ever
        # walked exactly course/category/*.pdf, two levels, no deeper.
        # Every other subproject's own discovery (route_notes_transcribe.py,
        # migrate_sources_to_resources.py) already recurses via os.walk;
        # this brings rebuild()'s PDF-notes discovery in line with them.
        with tempfile.TemporaryDirectory() as tmp:
            nested_dir = os.path.join(tmp, "academic_notes", "math-camp", "ta_notes", "2026")
            os.makedirs(nested_dir)
            pdf_path = os.path.join(nested_dir, "LN_Analysis.pdf")
            with open(pdf_path, "wb") as f:
                f.write(b"fake pdf bytes")
            out_dir = os.path.join(nested_dir, "processed_outputs")
            os.makedirs(out_dir)
            with open(os.path.join(out_dir, "LN_Analysis.md"), "w", encoding="utf-8") as f:
                f.write("---\ntotal_pages: 3\n---\n\nSome content.")

            stats = rebuild(tmp, client=_fake_client())

            self.assertEqual(stats["generated"], 1)
            cards = load_shard(tmp, "math-camp")
            self.assertEqual(len(cards), 1)
            self.assertEqual(
                cards[0]["source_pdf_path"], "academic_notes/math-camp/ta_notes/2026/LN_Analysis.pdf",
            )

    def test_rebuild_does_not_orphan_or_collide_a_linked_duplicate_note(self):
        # Real finding (2026-09-23): two byte-identical econometrics PDFs
        # (problem_sets/ and ta_notes/ copies of the same handout) were
        # independently transcribed before notes.transcribe_notes.
        # link_duplicate_note existed to catch this -- the second one
        # processed silently overwrote the first one's card `path` in
        # place, since reconcile_and_write matches by file_id and a
        # byte-identical PDF always hashes to the same file_id. A repaired
        # (linked) clone must not fall back into the same collision on the
        # very next rebuild(), which is what this test guards.
        from notes.transcribe_notes import link_duplicate_note
        with tempfile.TemporaryDirectory() as tmp:
            canonical_pdf_path = _make_notes_pdf(tmp, "econometrics", "problem_sets", "00-review-questions")
            client = _fake_client()
            rebuild(tmp, client)  # generates the canonical card
            canonical_course, canonical_card = find_card_by_file_id(
                tmp, compute_file_id(canonical_pdf_path),
            )

            clone_dir = os.path.join(tmp, "academic_notes", "econometrics", "ta_notes")
            os.makedirs(clone_dir, exist_ok=True)
            clone_pdf_path = os.path.join(clone_dir, "00-review-questions.pdf")
            with open(canonical_pdf_path, "rb") as f:
                pdf_bytes = f.read()
            with open(clone_pdf_path, "wb") as f:
                f.write(pdf_bytes)
            link_duplicate_note(tmp, canonical_course, canonical_card, clone_pdf_path, "ta_notes")

            stats = rebuild(tmp, client)

            self.assertEqual(stats["orphaned"], 0)
            self.assertGreaterEqual(stats["skipped_duplicate_clone"], 1)
            cards = load_shard(tmp, "econometrics")
            self.assertEqual(len(cards), 2)
            canonical_after = next(c for c in cards if c["file_id"] == canonical_card["file_id"])
            self.assertEqual(canonical_after["path"], canonical_card["path"])  # not overwritten by the clone

    def test_rebuild_discovers_and_refreshes_a_pdf_that_migrated_to_resources(self):
        # Real finding (2026-09-23, first real migration run against
        # econometrics): _notes_pdf_paths only ever walked academic_notes/,
        # so a PDF that migrates to academic_resources/ became invisible to
        # rebuild() entirely -- its file_id was never re-added to
        # seen_file_ids, which would silently orphan any already-
        # transcribed card the moment its source moved.
        with tempfile.TemporaryDirectory() as tmp:
            pdf_path = _make_notes_pdf(tmp, "math-camp", "ta_notes", "LN_Analysis")
            client = _fake_client()
            rebuild(tmp, client)  # first run: generates the card, PDF still under academic_notes/

            migrated_pdf_path = os.path.join(
                tmp, "academic_resources", "math-camp", "ta_notes", "LN_Analysis.pdf",
            )
            os.makedirs(os.path.dirname(migrated_pdf_path), exist_ok=True)
            os.rename(pdf_path, migrated_pdf_path)

            stats = rebuild(tmp, client)  # second run: PDF has moved

            self.assertEqual(stats["orphaned"], 0)
            self.assertEqual(client.models.generate_content.call_count, 1)  # still no regen
            cards = load_shard(tmp, "math-camp")
            self.assertEqual(len(cards), 1)
            expected = os.path.relpath(migrated_pdf_path, tmp).replace(os.sep, "/")
            self.assertEqual(cards[0]["source_pdf_path"], expected)
            self.assertEqual(cards[0]["source_asset_path"], expected)

    def test_still_ignores_processed_outputs_when_recursing(self):
        # A stray .pdf sitting inside processed_outputs/ (shouldn't happen
        # in practice) must not be treated as its own source -- same
        # pruning discipline route_notes_transcribe.py's own walker uses.
        with tempfile.TemporaryDirectory() as tmp:
            _make_notes_pdf(tmp, "math-camp", "ta_notes", "LN_Analysis")
            out_dir = os.path.join(tmp, "academic_notes", "math-camp", "ta_notes", "processed_outputs")
            with open(os.path.join(out_dir, "decoy.pdf"), "wb") as f:
                f.write(b"should not be discovered as its own source")

            stats = rebuild(tmp, client=_fake_client())

            self.assertEqual(stats["generated"], 1)
            self.assertEqual(len(load_shard(tmp, "math-camp")), 1)

    def test_skips_zero_byte_markdown_and_orphans_any_existing_card(self):
        # Real-corpus finding (docs/trackers/2026-08-30-academic-hub-status.md): a
        # 0-byte .md next to a real, un-transcribed source PDF must not
        # get a vacuous "this is empty" card generated for it, and any
        # such card from before this fix existed should get cleaned up
        # by the normal orphan-flagging pass, not left behind silently.
        with tempfile.TemporaryDirectory() as tmp:
            pdf_path = _make_notes_pdf(tmp, "math-camp", "ta_notes", "untranscribed")
            client = _fake_client()
            stats = rebuild(tmp, client=client)
            self.assertEqual(stats["generated"], 1)  # the normal-content fixture .md indexes fine

            # Now simulate the real-corpus case: truncate the .md to 0 bytes.
            md_path = os.path.join(os.path.dirname(pdf_path), "processed_outputs", "untranscribed.md")
            open(md_path, "w").close()

            stats = rebuild(tmp, client=client)
            self.assertEqual(stats["skipped_empty_md"], 1)
            self.assertEqual(client.models.generate_content.call_count, 1)  # not called again
            self.assertTrue(load_shard(tmp, "math-camp")[0]["orphaned"])

    def test_second_run_with_no_changes_leaves_cards_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_notes_pdf(tmp, "math-camp", "ta_notes", "LN_Analysis")
            client = _fake_client()
            rebuild(tmp, client=client)
            stats = rebuild(tmp, client=client)
            self.assertEqual(stats["generated"], 0)
            self.assertEqual(stats["unchanged"], 1)
            self.assertEqual(client.models.generate_content.call_count, 1)  # not called again

    def test_regenerates_when_md_content_changes_even_if_pdf_and_path_are_unchanged(self):
        # Real-corpus finding: fixing a transcription bug and re-running
        # produces a .md with genuinely different content, but the same
        # PDF (same file_id) and the same path -- rebuild must notice the
        # content changed via the .md's mtime and regenerate, not silently
        # keep serving a stale card forever just because file_id/path
        # never moved.
        with tempfile.TemporaryDirectory() as tmp:
            pdf_path = _make_notes_pdf(tmp, "math-camp", "ta_notes", "was_stale")
            md_path = os.path.join(os.path.dirname(pdf_path), "processed_outputs", "was_stale.md")

            client = _fake_client()
            rebuild(tmp, client=client)
            self.assertEqual(client.models.generate_content.call_count, 1)

            with open(md_path, "w", encoding="utf-8") as f:
                f.write("---\ntotal_pages: 3\n---\n\nGenuinely different content now.")
            future = time.time() + 10  # force strictly-newer mtime, not relying on clock resolution
            os.utime(md_path, (future, future))

            stats = rebuild(tmp, client=client)
            self.assertEqual(stats["unchanged"], 0)
            self.assertEqual(stats["updated"], 1)
            self.assertEqual(client.models.generate_content.call_count, 2)  # regenerated

    def test_touching_mtime_without_changing_content_does_not_regenerate(self):
        # Real bug, caught live: something (a container/session remount)
        # once reset every .md's mtime to the same instant in the real
        # corpus, and a plain mtime-based staleness check spuriously
        # regenerated cards whose content hadn't actually changed --
        # wasting real LLM/embedding calls. content_hash must be the
        # decisive signal once a card has one, regardless of mtime.
        with tempfile.TemporaryDirectory() as tmp:
            pdf_path = _make_notes_pdf(tmp, "math-camp", "ta_notes", "untouched")
            md_path = os.path.join(os.path.dirname(pdf_path), "processed_outputs", "untouched.md")

            client = _fake_client()
            rebuild(tmp, client=client)
            self.assertEqual(client.models.generate_content.call_count, 1)

            future = time.time() + 10
            os.utime(md_path, (future, future))  # mtime bumped, content byte-for-byte unchanged

            stats = rebuild(tmp, client=client)
            self.assertEqual(stats["unchanged"], 1)
            self.assertEqual(stats["updated"], 0)
            self.assertEqual(client.models.generate_content.call_count, 1)  # not called again

    def test_legacy_card_without_content_hash_migrates_on_next_rebuild(self):
        # A card indexed before content_hash existed has no such field.
        # As long as the old mtime bridge agrees it's not actually stale,
        # rebuild must backfill content_hash onto it (cheap, no LLM call)
        # so it never needs the mtime bridge again.
        with tempfile.TemporaryDirectory() as tmp:
            pdf_path = _make_notes_pdf(tmp, "math-camp", "ta_notes", "legacy")
            md_path = os.path.join(os.path.dirname(pdf_path), "processed_outputs", "legacy.md")
            file_id = compute_file_id(pdf_path)
            rel_md_path = os.path.relpath(md_path, tmp).replace(os.sep, "/")
            rel_pdf_path = os.path.relpath(pdf_path, tmp).replace(os.sep, "/")
            future = time.time() + 3600
            save_shard(tmp, "math-camp", [{
                "file_id": file_id, "path": rel_md_path, "source_pdf_path": rel_pdf_path,
                "course": "math-camp", "embedding": [0.1, 0.2], "tags": [],
                "source_updated_at": datetime.fromtimestamp(future, tz=timezone.utc).isoformat(),
                # no content_hash key -- simulates a pre-migration card
            }])

            client = _fake_client()
            stats = rebuild(tmp, client=client)
            self.assertEqual(stats["unchanged"], 1)  # mtime bridge: card time is in the future, not stale
            self.assertIsNotNone(load_shard(tmp, "math-camp")[0]["content_hash"])
            client.models.generate_content.assert_not_called()  # backfill is local-only, no LLM call

            # Now that it's migrated, an mtime bump alone must not regenerate it.
            os.utime(md_path, (future + 10, future + 10))
            stats = rebuild(tmp, client=client)
            self.assertEqual(stats["unchanged"], 1)
            client.models.generate_content.assert_not_called()

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

    def test_rebuild_never_touches_tags_json(self):
        # Real bug, caught live: _flag_or_prune_orphans excluded the old
        # pre-rename filename "topics.json" instead of "tags.json"
        # (spec's topics -> tags rename), so every rebuild treated the
        # tag vocabulary as a course shard of file-cards -- stamping a
        # meaningless orphaned: True onto every tag entry (harmless by
        # itself, since nothing reads it), and would silently delete the
        # entire tag vocabulary the first time anyone ran
        # `rebuild --prune`, since a tag entry never has a file_id and so
        # can never be "seen".
        with tempfile.TemporaryDirectory() as tmp:
            _make_notes_pdf(tmp, "math-camp", "ta_notes", "LN_Analysis")
            save_tags(tmp, [{"tag": "real-analysis", "embedding": [1.0, 0.0]}])
            rebuild(tmp, client=_fake_client())
            tags = load_tags(tmp)
            self.assertEqual(len(tags), 1)
            self.assertNotIn("orphaned", tags[0])

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

    def test_generates_a_textbook_card_under_the_textbooks_folder_alias(self):
        # Real-corpus finding: math-camp's textbook folder was renamed on
        # disk from "textbooks-and-papers" to "textbooks", but the walk
        # in _textbook_book_dirs() only recognized the old name --
        # rebuild() silently saw zero book dirs for the whole course,
        # with no warning or failure to signal it.
        with tempfile.TemporaryDirectory() as tmp:
            _make_textbook(tmp, "math-camp", "Book of Proof", "Hammack_Book_of_Proof_2025",
                            category_folder_name="textbooks")
            stats = rebuild(tmp, client=_fake_client())
            self.assertEqual(stats["generated"], 1)
            cards = load_shard(tmp, "math-camp")
            self.assertEqual(len(cards), 1)
            self.assertTrue(cards[0]["path"].endswith("Hammack_Book_of_Proof_2025.md"))
            self.assertIn("/textbooks/", cards[0]["path"])

    def test_generates_a_textbook_card_for_a_book_under_a_subfolder(self):
        # Real-corpus finding: a course's textbook folder can have its own
        # subfolder (e.g. "Bonus", for supplementary readings converted in
        # a separate batch per convert_textbook_agent_instructions.md) --
        # rebuild() silently saw zero book dirs for books converted there,
        # with no warning or failure to signal it, because
        # _textbook_book_dirs() only looked directly under
        # category_folder_name, never one level deeper.
        with tempfile.TemporaryDirectory() as tmp:
            _make_textbook(tmp, "microecon", "Economics and Language", "Rubenstein_Economics_and_Language_2000",
                            category_folder_name="textbooks", subfolder="Bonus")
            stats = rebuild(tmp, client=_fake_client())
            self.assertEqual(stats["generated"], 1)
            cards = load_shard(tmp, "microecon")
            self.assertEqual(len(cards), 1)
            self.assertTrue(cards[0]["path"].endswith("Rubenstein_Economics_and_Language_2000.md"))
            self.assertIn("/textbooks/Bonus/", cards[0]["path"])

    def test_both_textbook_folder_aliases_are_picked_up_in_the_same_course(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_textbook(tmp, "econometrics", "Old Style", "OldStyle_2020",
                            category_folder_name="textbooks-and-papers")
            _make_textbook(tmp, "econometrics", "New Style", "NewStyle_2026",
                            category_folder_name="textbooks")
            stats = rebuild(tmp, client=_fake_client())
            self.assertEqual(stats["generated"], 2)
            self.assertEqual(len(load_shard(tmp, "econometrics")), 2)

    def test_backfills_rag_md_path_from_metadata_when_card_is_missing_it(self):
        # Real-corpus finding: describe_images.py's link_rag_md() writes
        # rag_md_path into _metadata.json unconditionally, but only sets
        # it on the index card if one already existed at that moment --
        # if describe_images.py ran before (or without) a later rebuild,
        # the card's own rag_md_path is silently left None forever with
        # no automatic way to catch up. rebuild must reconcile this from
        # _metadata.json itself, since that's the durable record.
        with tempfile.TemporaryDirectory() as tmp:
            pdf_path = _make_textbook(tmp, "math-camp", "Axler", "Axler_Linear_Algebra_2026")
            rebuild(tmp, client=_fake_client())
            cards = load_shard(tmp, "math-camp")
            self.assertIsNone(cards[0]["rag_md_path"])

            metadata_path = os.path.join(
                os.path.dirname(pdf_path), "processed_outputs",
                "Axler_Linear_Algebra_2026", "Axler_Linear_Algebra_2026_metadata.json",
            )
            with open(metadata_path, encoding="utf-8") as f:
                metadata = json.load(f)
            metadata["rag_md_path"] = (
                "academic_resources/math-camp/textbooks-and-papers/processed_outputs/"
                "Axler_Linear_Algebra_2026/Axler_Linear_Algebra_2026.rag.md"
            )
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f)

            rebuild(tmp, client=_fake_client())
            cards = load_shard(tmp, "math-camp")
            self.assertEqual(cards[0]["rag_md_path"], metadata["rag_md_path"])

    def test_rebuild_recognizes_a_clone_directory_and_never_rehashes_it(self):
        # Regression for the original corruption bug (pipeline-autonomy-
        # policies spec, Component 3): a Tier 1 (byte-identical) clone's
        # PDF hashes to the SAME file_id as the canonical book -- before
        # this fix, rebuild()'s textbook loop would recompute that hash,
        # find no card under it in the clone's OWN course shard, and fall
        # through to reconcile_and_write's cross-course "file moved"
        # handling, which relocated the canonical card out of its own
        # shard entirely. A book directory whose _metadata.json carries
        # duplicate_of_file_id must never be re-hashed or reconciled.
        with tempfile.TemporaryDirectory() as tmp:
            # Same pdf_basename ("Ok") in both calls -- _make_textbook's
            # fake PDF bytes are derived only from pdf_basename, so they
            # come out byte-identical, exactly reproducing the real Tier 1
            # collision.
            canonical_pdf = _make_textbook(tmp, "econometrics", "Ok", "Ok_RealAnalysis_2007")
            clone_pdf = _make_textbook(tmp, "microecon", "Ok", "Ok_RealAnalysis_2007")

            canonical_file_id = compute_file_id(canonical_pdf)
            rel_canonical_pdf = os.path.relpath(canonical_pdf, tmp).replace(os.sep, "/")
            canonical_md_path = os.path.join(os.path.dirname(canonical_pdf), "processed_outputs", "Ok_RealAnalysis_2007", "Ok_RealAnalysis_2007.md")

            from indexer.index_card import compute_id_from_parts, compute_content_hash
            save_shard(tmp, "econometrics", [{
                "file_id": canonical_file_id,
                "path": "academic_resources/econometrics/textbooks-and-papers/processed_outputs/Ok_RealAnalysis_2007/Ok_RealAnalysis_2007.md",
                "source_pdf_path": rel_canonical_pdf, "course": "econometrics",
                "doc_type": "textbook", "title": "Real Analysis with Economic Applications",
                "embedding": [0.1, 0.2], "tags": [], "needs_indexing": False,
                "source_updated_at": "2026-01-01T00:00:00+00:00", "content_hash": compute_content_hash(canonical_md_path),
            }])

            clone_file_id = compute_id_from_parts([canonical_file_id, "microecon"])
            rel_clone_pdf = os.path.relpath(clone_pdf, tmp).replace(os.sep, "/")
            save_shard(tmp, "microecon", [{
                "file_id": clone_file_id,
                "path": "academic_resources/microecon/textbooks-and-papers/processed_outputs/Ok_RealAnalysis_2007/Ok_RealAnalysis_2007.md",
                "source_pdf_path": rel_clone_pdf, "course": "microecon",
                "doc_type": "textbook", "title": "Real Analysis with Economic Applications",
                "embedding": [0.1, 0.2], "tags": [], "needs_indexing": False,
                "source_updated_at": "2026-01-01T00:00:00+00:00", "content_hash": "clone-hash",
                "duplicate_of_file_id": canonical_file_id,
            }])

            clone_metadata_path = os.path.join(
                os.path.dirname(clone_pdf), "processed_outputs", "Ok_RealAnalysis_2007",
                "Ok_RealAnalysis_2007_metadata.json",
            )
            with open(clone_metadata_path, encoding="utf-8") as f:
                clone_metadata = json.load(f)
            clone_metadata["duplicate_of_file_id"] = canonical_file_id
            with open(clone_metadata_path, "w", encoding="utf-8") as f:
                json.dump(clone_metadata, f)

            client = _fake_client()
            stats = rebuild(tmp, client=client)

            # The canonical card must still be in ITS OWN shard, under its
            # own file_id -- not relocated into microecon.
            canonical_cards = load_shard(tmp, "econometrics")
            self.assertEqual(len(canonical_cards), 1)
            self.assertEqual(canonical_cards[0]["file_id"], canonical_file_id)

            # The clone's card is untouched -- still present, still its own
            # derived file_id and content_hash, never overwritten.
            clone_cards = load_shard(tmp, "microecon")
            self.assertEqual(len(clone_cards), 1)
            self.assertEqual(clone_cards[0]["file_id"], clone_file_id)
            self.assertEqual(clone_cards[0]["content_hash"], "clone-hash")

            self.assertEqual(stats["skipped_duplicate_clone"], 1)
            # Only the canonical book's own (pre-existing, unchanged) card
            # means no LLM call was made at all in this run.
            self.assertEqual(client.models.generate_content.call_count, 0)

    def test_rebuild_prune_does_not_evict_a_clone_marked_seen(self):
        # A clone card is never "backed by a re-hashed PDF" the normal
        # way -- without adding its own derived id to seen_file_ids,
        # --prune would treat it as an orphan and delete it.
        with tempfile.TemporaryDirectory() as tmp:
            canonical_pdf = _make_textbook(tmp, "econometrics", "Ok", "Ok_RealAnalysis_2007")
            clone_pdf = _make_textbook(tmp, "microecon", "Ok", "Ok_RealAnalysis_2007")
            canonical_file_id = compute_file_id(canonical_pdf)
            from indexer.index_card import compute_id_from_parts
            clone_file_id = compute_id_from_parts([canonical_file_id, "microecon"])

            save_shard(tmp, "econometrics", [{
                "file_id": canonical_file_id,
                "path": "academic_resources/econometrics/textbooks-and-papers/processed_outputs/Ok_RealAnalysis_2007/Ok_RealAnalysis_2007.md",
                "source_pdf_path": os.path.relpath(canonical_pdf, tmp).replace(os.sep, "/"),
                "course": "econometrics", "doc_type": "textbook", "title": "T",
                "embedding": [0.1, 0.2], "tags": [], "needs_indexing": False,
                "source_updated_at": "2026-01-01T00:00:00+00:00", "content_hash": "canonical-hash",
            }])
            save_shard(tmp, "microecon", [{
                "file_id": clone_file_id,
                "path": "academic_resources/microecon/textbooks-and-papers/processed_outputs/Ok_RealAnalysis_2007/Ok_RealAnalysis_2007.md",
                "source_pdf_path": os.path.relpath(clone_pdf, tmp).replace(os.sep, "/"),
                "course": "microecon", "doc_type": "textbook", "title": "T",
                "embedding": [0.1, 0.2], "tags": [], "needs_indexing": False,
                "source_updated_at": "2026-01-01T00:00:00+00:00", "content_hash": "clone-hash",
                "duplicate_of_file_id": canonical_file_id,
            }])
            clone_metadata_path = os.path.join(
                os.path.dirname(clone_pdf), "processed_outputs", "Ok_RealAnalysis_2007",
                "Ok_RealAnalysis_2007_metadata.json",
            )
            with open(clone_metadata_path, encoding="utf-8") as f:
                clone_metadata = json.load(f)
            clone_metadata["duplicate_of_file_id"] = canonical_file_id
            with open(clone_metadata_path, "w", encoding="utf-8") as f:
                json.dump(clone_metadata, f)

            stats = rebuild(tmp, client=_fake_client(), prune=True)

            self.assertEqual(stats["pruned"], 0)
            self.assertEqual(len(load_shard(tmp, "microecon")), 1)
            self.assertEqual(load_shard(tmp, "microecon")[0]["file_id"], clone_file_id)

    def test_skips_textbook_with_no_source_pdf_path_yet(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_textbook(tmp, "math-camp", "Book of Proof", "Hammack_Book_of_Proof_2025",
                            with_source_pdf_path=False)
            stats = rebuild(tmp, client=_fake_client())
            self.assertEqual(stats["generated"], 0)
            self.assertEqual(stats["skipped_no_source_pdf"], 1)
            self.assertEqual(load_shard(tmp, "math-camp"), [])

    def test_falls_back_to_source_pdf_filename_when_source_pdf_path_is_stale(self):
        # Real, confirmed incident: for a book converted from a gs://
        # input on the GCP VM, convert_textbook.py records the VM's own
        # local temp-download path as source_pdf_path -- meaningless (and
        # nonexistent) once back on this machine. The real source PDF is
        # still sitting locally though (Step 3.2 uploads it without moving
        # it), so rebuild() should find it via source_pdf_filename instead
        # of just giving up.
        with tempfile.TemporaryDirectory() as tmp:
            pdf_path = _make_textbook(tmp, "econometrics", "Hansen Econometrics", "Hansen_ECONOMETRICS_2022")
            metadata_path = os.path.join(
                os.path.dirname(pdf_path), "processed_outputs",
                "Hansen_ECONOMETRICS_2022", "Hansen_ECONOMETRICS_2022_metadata.json",
            )
            with open(metadata_path, encoding="utf-8") as f:
                metadata = json.load(f)
            metadata["source_pdf_path"] = "../academic-rag-model/temp_gcs_input_Hansen_Econometrics.pdf"
            metadata["source_pdf_filename"] = "Hansen Econometrics.pdf"
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f)

            stats = rebuild(tmp, client=_fake_client())

            self.assertEqual(stats["generated"], 1)
            self.assertEqual(stats["skipped_no_source_pdf"], 0)
            cards = load_shard(tmp, "econometrics")
            self.assertTrue(cards[0]["source_pdf_path"].endswith("Hansen Econometrics.pdf"))

    def test_still_skips_when_source_pdf_filename_fallback_also_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdf_path = _make_textbook(tmp, "math-camp", "Book of Proof", "Hammack_Book_of_Proof_2025")
            metadata_path = os.path.join(
                os.path.dirname(pdf_path), "processed_outputs",
                "Hammack_Book_of_Proof_2025", "Hammack_Book_of_Proof_2025_metadata.json",
            )
            with open(metadata_path, encoding="utf-8") as f:
                metadata = json.load(f)
            metadata["source_pdf_path"] = "../academic-rag-model/temp_gcs_input_stale.pdf"
            metadata["source_pdf_filename"] = "Nonexistent Book.pdf"
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f)

            stats = rebuild(tmp, client=_fake_client())

            self.assertEqual(stats["generated"], 0)
            self.assertEqual(stats["skipped_no_source_pdf"], 1)

    def test_textbook_content_sample_is_capped(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_textbook(tmp, "math-camp", "Big Book", "BigBook_2025")
            md_path = os.path.join(tmp, "academic_resources", "math-camp", "textbooks-and-papers",
                                    "processed_outputs", "BigBook_2025", "BigBook_2025.md")
            with open(md_path, "w", encoding="utf-8") as f:
                f.write("x" * 50000)
            client = _fake_client()
            rebuild(tmp, client=client)
            from indexer.index_card import TEXTBOOK_CONTENT_SAMPLE_CHARS
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


def _fake_client_returning_doc_type(doc_type):
    client = MagicMock()
    gen_response = MagicMock()
    gen_response.text = (
        '{"title": "T", "doc_type": "%s", "summary": "S.", '
        '"level": "introductory", "has_solutions": false}' % doc_type
    )
    client.models.generate_content.return_value = gen_response
    embed_response = MagicMock()
    embedding = MagicMock()
    embedding.values = [0.1, 0.2]
    embed_response.embeddings = [embedding]
    client.models.embed_content.return_value = embed_response
    return client


class TestRebuildVideoLectureNotes(unittest.TestCase):
    def test_generates_a_card_for_a_lecture_note_with_a_sidecar(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_video_lecture_note(tmp, "math-camp", "real-analysis", ["A", "B"])
            stats = rebuild(tmp, client=_fake_client())
            self.assertEqual(stats["generated"], 1)
            cards = load_shard(tmp, "math-camp")
            self.assertEqual(len(cards), 1)
            self.assertEqual(cards[0]["source_pdf_path"], "academic_notes/math-camp/lecture_notes/real-analysis.meta.json")

    def test_never_classified_into_the_shared_corpus_doc_types(self):
        # Regression guard: generate_index_card()'s prompt only ever lets
        # the LLM pick from the known_doc_types it's given, so a lecture
        # note must be reconciled with its own known_doc_types (not the
        # shared KNOWN_DOC_TYPES) or it gets miscategorized as whichever
        # of textbook/problem_set/ta_notes/handwritten_notes looks closest
        # -- confirmed live against a real playlist before this fix.
        with tempfile.TemporaryDirectory() as tmp:
            _make_video_lecture_note(tmp, "math-camp", "real-analysis", ["A", "B"])
            rebuild(tmp, client=_fake_client_returning_doc_type("ta_notes"))
            cards = load_shard(tmp, "math-camp")
            self.assertNotIn(cards[0]["doc_type"], {"textbook", "problem_set", "ta_notes", "handwritten_notes"})

    def test_classified_as_lecture_notes_when_the_model_complies(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_video_lecture_note(tmp, "math-camp", "real-analysis", ["A", "B"])
            rebuild(tmp, client=_fake_client_returning_doc_type("lecture_notes"))
            cards = load_shard(tmp, "math-camp")
            self.assertEqual(cards[0]["doc_type"], "lecture_notes")

    def test_missing_sidecar_is_skipped_not_crashed(self):
        with tempfile.TemporaryDirectory() as tmp:
            lecture_notes_dir = os.path.join(tmp, "academic_notes", "math-camp", "lecture_notes")
            os.makedirs(lecture_notes_dir)
            with open(os.path.join(lecture_notes_dir, "orphaned.md"), "w", encoding="utf-8") as f:
                f.write("# No sidecar")
            stats = rebuild(tmp, client=_fake_client())
            self.assertEqual(stats["generated"], 0)

    def test_unchanged_note_is_not_regenerated_on_second_rebuild(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_video_lecture_note(tmp, "math-camp", "real-analysis", ["A", "B"])
            rebuild(tmp, client=_fake_client())
            stats = rebuild(tmp, client=_fake_client())
            self.assertEqual(stats["unchanged"], 1)
            self.assertEqual(stats["generated"], 0)

    def test_a_lecture_note_survives_prune_when_still_on_disk(self):
        # Regression guard for the bug this task exists to prevent: before
        # _video_lecture_note_paths() existed, a lecture note's card was
        # invisible to rebuild()'s file-discovery walk and would have been
        # flagged/pruned as an orphan even though the note was still there.
        with tempfile.TemporaryDirectory() as tmp:
            _make_video_lecture_note(tmp, "math-camp", "real-analysis", ["A", "B"])
            rebuild(tmp, client=_fake_client())
            stats = rebuild(tmp, client=_fake_client(), prune=True)
            self.assertEqual(stats["pruned"], 0)
            self.assertEqual(len(load_shard(tmp, "math-camp")), 1)

    def test_ignores_excalidraw_md_files_in_the_same_lecture_notes_folder(self):
        # Real finding (2026-09-22): after math-camp/lecture-notes/ was
        # renamed to lecture_notes/ (folder vocabulary unification), this
        # walker started scanning every course's lecture_notes/ folder --
        # including the ones that hold Excalidraw scene files, which also
        # end in ".md". No card was ever generated from one (missing
        # .meta.json correctly skips it), but a noisy "no sidecar" warning
        # printed for every single Excalidraw file in every course on every
        # rebuild. This must be silent: an .excalidraw.md is never a
        # video-lecture-note candidate at all, not a video-lecture-note
        # candidate missing its sidecar.
        with tempfile.TemporaryDirectory() as tmp:
            lecture_notes_dir = os.path.join(tmp, "academic_notes", "econometrics", "lecture_notes")
            os.makedirs(lecture_notes_dir)
            with open(os.path.join(lecture_notes_dir, "Drawing.excalidraw.md"), "w", encoding="utf-8") as f:
                f.write("---\n---\n\nfake compressed-json scene data")

            with patch("builtins.print") as mock_print:
                stats = rebuild(tmp, client=_fake_client())

            self.assertEqual(stats["generated"], 0)
            for call in mock_print.call_args_list:
                self.assertNotIn("no sidecar", str(call))


class TestRebuildExcalidrawNotes(unittest.TestCase):
    def test_rebuild_generates_a_card_for_a_real_excalidraw_note(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_excalidraw_note(tmp, "econometrics", "lecture_notes", "Drawing")
            client = _fake_client()
            stats = rebuild(tmp, client)
            self.assertEqual(stats["generated"], 1)
            cards = load_shard(tmp, "econometrics")
            self.assertEqual(len(cards), 1)
            # _fake_client's canned doc_type ("ta_notes") isn't in
            # EXCALIDRAW_DOC_TYPES, so generate_index_card() correctly
            # falls back to folder_category ("lecture_notes").
            self.assertEqual(cards[0]["doc_type"], "lecture_notes")

    def test_rebuild_skips_a_note_with_no_rag_md_yet(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_excalidraw_note(tmp, "econometrics", "lecture_notes", "Drawing", write_rag_md=False)
            client = _fake_client()
            stats = rebuild(tmp, client)
            self.assertEqual(stats["generated"], 0)
            self.assertEqual(load_shard(tmp, "econometrics"), [])

    def test_rebuild_does_not_orphan_an_existing_excalidraw_card(self):
        # This is the real, live bug this task fixes: before this task,
        # rebuild() has no walker for Excalidraw notes at all, so its
        # orphan pass flags every Excalidraw card as orphaned on every
        # run. Verified against a real isolated copy of the production
        # index before this task existed -- see the design spec.
        with tempfile.TemporaryDirectory() as tmp:
            _make_excalidraw_note(tmp, "econometrics", "lecture_notes", "Drawing")
            client = _fake_client()
            rebuild(tmp, client)  # first run: generates the card
            stats = rebuild(tmp, client)  # second run: must not orphan it
            self.assertEqual(stats["orphaned"], 0)
            cards = load_shard(tmp, "econometrics")
            self.assertNotIn("orphaned", cards[0])

    def test_rebuild_sets_source_asset_path_to_the_image_sibling(self):
        with tempfile.TemporaryDirectory() as tmp:
            md_path, svg_path = _make_excalidraw_note(tmp, "econometrics", "lecture_notes", "Drawing")
            client = _fake_client()
            rebuild(tmp, client)
            card = load_shard(tmp, "econometrics")[0]
            expected = os.path.relpath(svg_path, tmp).replace(os.sep, "/")
            self.assertEqual(card["source_asset_path"], expected)

    def test_rebuild_refreshes_source_asset_path_after_the_image_migrates(self):
        # Real finding (2026-09-23, first real migration run): once the
        # image sibling moves to academic_resources/, _find_excalidraw_image
        # correctly locates it there on the next rebuild(), but
        # _reconcile_one's "already_current" short-circuit only ever
        # compared `path` (the .rag.md output, which never moves) -- so the
        # freshly-resolved source_asset_path was silently discarded and the
        # card was left pointing at the old, now-nonexistent local path.
        with tempfile.TemporaryDirectory() as tmp:
            md_path, svg_path = _make_excalidraw_note(tmp, "econometrics", "lecture_notes", "Drawing")
            client = _fake_client()
            rebuild(tmp, client)  # first run: generates the card, image still local

            migrated_svg_path = os.path.join(
                tmp, "academic_resources", "econometrics", "lecture_notes", "Drawing.excalidraw.svg",
            )
            os.makedirs(os.path.dirname(migrated_svg_path), exist_ok=True)
            os.rename(svg_path, migrated_svg_path)

            stats = rebuild(tmp, client)  # second run: image has moved

            self.assertEqual(stats["orphaned"], 0)
            self.assertEqual(client.models.generate_content.call_count, 1)  # still no regen
            card = load_shard(tmp, "econometrics")[0]
            expected = os.path.relpath(migrated_svg_path, tmp).replace(os.sep, "/")
            self.assertEqual(card["source_asset_path"], expected)


class TestSearch(unittest.TestCase):
    def test_ranks_by_cosine_similarity_to_query(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [
                _card("close", [1.0, 0.0]),
                _card("far", [0.0, 1.0]),
            ])
            recompute_course_entry(tmp, "math-camp")
            results = search([tmp], "linear algebra", client=_fake_query_client([1.0, 0.0]))
            self.assertEqual(results[0].path, "close.md")
            self.assertGreater(results[0].score, results[1].score)

    def test_reason_is_the_cards_own_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [_card("x", [1.0, 0.0])])
            recompute_course_entry(tmp, "math-camp")
            results = search([tmp], "q", client=_fake_query_client([1.0, 0.0]))
            self.assertEqual(results[0].reason, "summary for x")

    def test_prefers_rag_md_path_over_path_when_set(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [
                _card("x", [1.0, 0.0], rag_md_path="x.rag.md"),
            ])
            recompute_course_entry(tmp, "math-camp")
            results = search([tmp], "q", client=_fake_query_client([1.0, 0.0]))
            self.assertEqual(results[0].path, "x.rag.md")

    def test_falls_back_to_path_when_rag_md_path_is_unset(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [_card("x", [1.0, 0.0])])  # rag_md_path defaults to None
            recompute_course_entry(tmp, "math-camp")
            results = search([tmp], "q", client=_fake_query_client([1.0, 0.0]))
            self.assertEqual(results[0].path, "x.md")

    def test_course_scope_skips_other_courses_entirely(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [_card("m", [1.0, 0.0])])
            save_shard(tmp, "spanish-101", [_card("s", [1.0, 0.0])])
            recompute_course_entry(tmp, "math-camp")
            recompute_course_entry(tmp, "spanish-101")
            results = search([tmp], "q", client=_fake_query_client([1.0, 0.0]), course="math-camp")
            self.assertEqual([r.path for r in results], ["m.md"])

    def test_top_k_limits_results(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [_card(str(i), [1.0, 0.0]) for i in range(10)])
            recompute_course_entry(tmp, "math-camp")
            results = search([tmp], "q", client=_fake_query_client([1.0, 0.0]), top_k=3)
            self.assertEqual(len(results), 3)

    def test_result_carries_file_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [_card("xyz789", [1.0, 0.0])])
            recompute_course_entry(tmp, "math-camp")
            results = search([tmp], "query", client=_fake_query_client([1.0, 0.0]))
            self.assertEqual(results[0].file_id, "xyz789")

    def test_doc_type_filter_applies_before_truncation(self):
        with tempfile.TemporaryDirectory() as tmp:
            cards = [_card(f"p{i}", [1.0, 0.0], doc_type="problem_set") for i in range(5)]
            cards.append(_card("t", [0.99, 0.01], doc_type="textbook"))
            save_shard(tmp, "math-camp", cards)
            recompute_course_entry(tmp, "math-camp")
            results = search([tmp], "q", client=_fake_query_client([1.0, 0.0]), top_k=2, doc_type="textbook")
            self.assertEqual([r.path for r in results], ["t.md"])

    def test_has_solutions_filter(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [
                _card("solved", [1.0, 0.0], has_solutions=True),
                _card("unsolved", [1.0, 0.0], has_solutions=False),
            ])
            recompute_course_entry(tmp, "math-camp")
            results = search([tmp], "q", client=_fake_query_client([1.0, 0.0]), has_solutions=False)
            self.assertEqual([r.path for r in results], ["unsolved.md"])

    def test_max_level_filter_excludes_harder_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [
                _card("easy", [1.0, 0.0], level="introductory"),
                _card("hard", [1.0, 0.0], level="advanced"),
            ])
            recompute_course_entry(tmp, "math-camp")
            results = search([tmp], "q", client=_fake_query_client([1.0, 0.0]), max_level="introductory")
            self.assertEqual([r.path for r in results], ["easy.md"])

    def test_excludes_needs_indexing_cards_but_not_orphaned_ones(self):
        # Real finding (2026-09-23): orphaned=true means "this card's
        # source PDF couldn't be found on the last rebuild" -- a
        # provenance note, not a verdict on the card's own content. A
        # user deleting/renaming a source PDF (confirmed real cases: some
        # were simple renames the pipeline's basename-matching missed,
        # others genuinely gone) must not silently blackhole the already-
        # transcribed, still-real .md content from search. needs_indexing
        # (generation failed, no real card yet) and a missing embedding
        # are the only cases search() should still refuse to surface.
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [
                _card("good", [1.0, 0.0]),
                _card("orphan", [1.0, 0.0], orphaned=True),
                _card("pending", [], needs_indexing=True),
            ])
            recompute_course_entry(tmp, "math-camp")
            results = search([tmp], "q", client=_fake_query_client([1.0, 0.0]))
            self.assertEqual(sorted(r.path for r in results), ["good.md", "orphan.md"])

    def test_no_courses_indexed_yet_returns_empty_list_not_a_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            results = search([tmp], "q", client=_fake_query_client([1.0, 0.0]))
            self.assertEqual(results, [])

    def test_multiple_roots_both_contribute_results(self):
        with tempfile.TemporaryDirectory() as tmp:
            root_a, root_b = os.path.join(tmp, "a"), os.path.join(tmp, "b")
            save_shard(root_a, "notes", [_card("from-a", [1.0, 0.0])])
            save_shard(root_b, "notes", [_card("from-b", [1.0, 0.0])])
            recompute_course_entry(root_a, "notes")
            recompute_course_entry(root_b, "notes")
            results = search([root_a, root_b], "q", client=_fake_query_client([1.0, 0.0]))
            self.assertEqual({r.path for r in results}, {"from-a.md", "from-b.md"})
            self.assertEqual({r.root for r in results}, {root_a, root_b})

    def test_same_course_name_in_two_roots_does_not_collide(self):
        # The actual point of qualifying candidates by (root, course):
        # two unrelated corpora can each have a course literally called
        # "notes" without one shadowing or merging into the other.
        with tempfile.TemporaryDirectory() as tmp:
            root_a, root_b = os.path.join(tmp, "a"), os.path.join(tmp, "b")
            save_shard(root_a, "notes", [_card("x", [1.0, 0.0], title="from root a")])
            save_shard(root_b, "notes", [_card("x", [1.0, 0.0], title="from root b")])
            recompute_course_entry(root_a, "notes")
            recompute_course_entry(root_b, "notes")
            results = search([root_a, root_b], "q", client=_fake_query_client([1.0, 0.0]))
            self.assertEqual(len(results), 2)
            by_root = {r.root: r for r in results}
            self.assertEqual(load_shard(root_a, "notes")[0]["title"], "from root a")
            self.assertEqual(load_shard(root_b, "notes")[0]["title"], "from root b")
            self.assertEqual(set(by_root.keys()), {root_a, root_b})

    def test_course_filter_checks_every_given_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root_a, root_b = os.path.join(tmp, "a"), os.path.join(tmp, "b")
            save_shard(root_a, "notes", [_card("from-a", [1.0, 0.0])])
            save_shard(root_b, "notes", [_card("from-b", [1.0, 0.0])])
            results = search([root_a, root_b], "q", client=_fake_query_client([1.0, 0.0]), course="notes")
            self.assertEqual({r.root for r in results}, {root_a, root_b})

    def test_single_root_behaves_exactly_as_before(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [_card("x", [1.0, 0.0])])
            recompute_course_entry(tmp, "math-camp")
            results = search([tmp], "q", client=_fake_query_client([1.0, 0.0]))
            self.assertEqual(results[0].root, tmp)


class TestSingleRoot(unittest.TestCase):
    def test_defaults_when_no_root_given(self):
        args = build_arg_parser().parse_args(["rebuild"])
        self.assertEqual(_single_root(args), _DEFAULT_ROOT)

    def test_returns_the_one_given_root(self):
        args = build_arg_parser().parse_args(["--root", "/x", "rebuild"])
        self.assertEqual(_single_root(args), "/x")

    def test_raises_on_more_than_one_root(self):
        # rebuild/retag/chunk write into exactly one root's own .index/ --
        # more than one --root is a usage error, not something to
        # silently resolve by picking the first.
        args = build_arg_parser().parse_args(["--root", "/x", "--root", "/y", "rebuild"])
        with self.assertRaises(SystemExit):
            _single_root(args)


class TestCLIArgParsing(unittest.TestCase):
    def test_root_defaults_to_none_when_omitted(self):
        args = build_arg_parser().parse_args(["query", "q"])
        self.assertIsNone(args.root)

    def test_root_is_repeatable(self):
        args = build_arg_parser().parse_args(["--root", "a", "--root", "b", "query", "q"])
        self.assertEqual(args.root, ["a", "b"])

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

    def test_retag_subcommand_defaults(self):
        args = build_arg_parser().parse_args(["retag"])
        self.assertEqual(args.command, "retag")
        self.assertFalse(args.dry_run)

    def test_retag_subcommand_with_dry_run(self):
        args = build_arg_parser().parse_args(["retag", "--dry-run"])
        self.assertTrue(args.dry_run)

    def test_chunk_subcommand_defaults(self):
        args = build_arg_parser().parse_args(["chunk"])
        self.assertEqual(args.command, "chunk")
        self.assertIsNone(args.course)
        self.assertIsNone(args.file)
        self.assertFalse(args.dry_run)

    def test_chunk_subcommand_with_flags(self):
        args = build_arg_parser().parse_args(["chunk", "--course", "math-camp", "--file", "a.md", "--dry-run"])
        self.assertEqual(args.course, "math-camp")
        self.assertEqual(args.file, "a.md")
        self.assertTrue(args.dry_run)

    def test_query_passages_flag(self):
        args = build_arg_parser().parse_args(["query", "something", "--passages"])
        self.assertTrue(args.passages)

    def test_query_passages_flag_defaults_false(self):
        args = build_arg_parser().parse_args(["query", "something"])
        self.assertFalse(args.passages)

    def test_ask_subcommand_defaults(self):
        args = build_arg_parser().parse_args(["ask", "what is the spectral theorem"])
        self.assertEqual(args.command, "ask")
        self.assertEqual(args.question, "what is the spectral theorem")
        self.assertIsNone(args.course)

    def test_ask_subcommand_with_course(self):
        args = build_arg_parser().parse_args(["ask", "q", "--course", "math-camp"])
        self.assertEqual(args.course, "math-camp")


class TestRenderCitation(unittest.TestCase):
    def test_heading_tier_citation(self):
        chunk = {"tier": "heading", "heading_path": ["3", "3.7 Optimization"], "page_range": [44, 44], "problem_label": None}
        self.assertEqual(_render_citation(chunk), "§3.7 Optimization, p. 44")

    def test_problem_number_tier_citation(self):
        chunk = {"tier": "problem_number", "heading_path": None, "page_range": [12, 12], "problem_label": "Problem 4"}
        self.assertEqual(_render_citation(chunk), "Problem 4, p. 12")

    def test_page_tier_citation(self):
        chunk = {"tier": "page", "heading_path": None, "page_range": [8, 8], "problem_label": None}
        self.assertEqual(_render_citation(chunk), "p. 8")

    def test_multi_page_range_renders_as_a_span(self):
        chunk = {"tier": "page", "heading_path": None, "page_range": [8, 9], "problem_label": None}
        self.assertEqual(_render_citation(chunk), "p. 8-9")

    def test_no_page_range_falls_back_to_heading_or_label_only(self):
        chunk = {"tier": "heading", "heading_path": ["Intro"], "page_range": None, "problem_label": None}
        self.assertEqual(_render_citation(chunk), "§Intro")

    def test_paragraph_tier_citation(self):
        chunk = {"tier": "paragraph", "heading_path": None, "problem_label": None,
                 "page_range": None, "paragraph_range": [3, 3]}
        self.assertEqual(_render_citation(chunk), "¶3")

    def test_multi_paragraph_range_renders_as_a_span(self):
        chunk = {"tier": "paragraph", "heading_path": None, "problem_label": None,
                 "page_range": None, "paragraph_range": [2, 4]}
        self.assertEqual(_render_citation(chunk), "¶2-4")

    def test_missing_paragraph_range_key_does_not_crash(self):
        # A chunk from before this field existed (or any non-paragraph
        # tier) simply has no paragraph_range key at all.
        chunk = {"tier": "page", "heading_path": None, "problem_label": None, "page_range": [8, 8]}
        self.assertEqual(_render_citation(chunk), "p. 8")


class TestSearchPassages(unittest.TestCase):
    def test_ranks_passages_within_the_top_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [_card("aaa", [1.0, 0.0])])
            recompute_course_entry(tmp, "math-camp")
            save_chunks(tmp, "math-camp", [
                {"chunk_id": "aaa-000", "file_id": "aaa", "chunk_index": 0, "tier": "page",
                 "heading_path": None, "problem_label": None, "page_range": [1, 1],
                 "text": "close match", "embedding": [0.9, 0.1], "embedding_model": "m", "content_hash": "h"},
                {"chunk_id": "aaa-001", "file_id": "aaa", "chunk_index": 1, "tier": "page",
                 "heading_path": None, "problem_label": None, "page_range": [2, 2],
                 "text": "far match", "embedding": [0.0, 1.0], "embedding_model": "m", "content_hash": "h"},
            ])
            results = search_passages([tmp], "query", client=_fake_query_client([1.0, 0.0]))
            self.assertEqual(results[0].text, "close match")
            self.assertGreater(results[0].score, results[1].score)
            self.assertEqual(results[0].file_id, "aaa")
            self.assertEqual(results[0].chunk_id, "aaa-000")

    def test_file_with_no_chunks_yet_is_skipped_not_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [_card("aaa", [1.0, 0.0])])
            recompute_course_entry(tmp, "math-camp")
            # No save_chunks() call at all -- chunk hasn't been run yet.
            results = search_passages([tmp], "query", client=_fake_query_client([1.0, 0.0]))
            self.assertEqual(results, [])

    def test_top_k_limits_results(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [_card("aaa", [1.0, 0.0])])
            recompute_course_entry(tmp, "math-camp")
            save_chunks(tmp, "math-camp", [
                {"chunk_id": f"aaa-{i:03d}", "file_id": "aaa", "chunk_index": i, "tier": "page",
                 "heading_path": None, "problem_label": None, "page_range": [i, i],
                 "text": f"chunk {i}", "embedding": [1.0, 0.0], "embedding_model": "m", "content_hash": "h"}
                for i in range(5)
            ])
            results = search_passages([tmp], "query", client=_fake_query_client([1.0, 0.0]), top_k=2)
            self.assertEqual(len(results), 2)

    def test_multiple_roots_with_colliding_file_id_stay_separate(self):
        # Same course name AND same file_id in both roots -- the strongest
        # version of the collision risk (root, course) keying exists to
        # prevent: without it, chunks_by_root_course would key purely by
        # course name, and file_id "x"'s chunks from whichever root loaded
        # second would silently shadow or merge with the first.
        with tempfile.TemporaryDirectory() as tmp:
            root_a, root_b = os.path.join(tmp, "a"), os.path.join(tmp, "b")
            save_shard(root_a, "notes", [_card("x", [1.0, 0.0], course="notes")])
            save_shard(root_b, "notes", [_card("x", [1.0, 0.0], course="notes")])
            recompute_course_entry(root_a, "notes")
            recompute_course_entry(root_b, "notes")
            save_chunks(root_a, "notes", [
                {"chunk_id": "x-000", "file_id": "x", "chunk_index": 0, "tier": "page",
                 "heading_path": None, "problem_label": None, "page_range": [1, 1],
                 "text": "root a content", "embedding": [1.0, 0.0], "embedding_model": "m", "content_hash": "h"},
            ])
            save_chunks(root_b, "notes", [
                {"chunk_id": "x-000", "file_id": "x", "chunk_index": 0, "tier": "page",
                 "heading_path": None, "problem_label": None, "page_range": [1, 1],
                 "text": "root b content", "embedding": [1.0, 0.0], "embedding_model": "m", "content_hash": "h"},
            ])
            results = search_passages([root_a, root_b], "query", client=_fake_query_client([1.0, 0.0]))
            self.assertEqual(len(results), 2)
            self.assertEqual({r.text for r in results}, {"root a content", "root b content"})
            self.assertEqual({r.root for r in results}, {root_a, root_b})

    def test_doc_type_filter_restricts_which_files_contribute_chunks(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [
                _card("p", [1.0, 0.0], doc_type="problem_set"),
                _card("t", [1.0, 0.0], doc_type="textbook"),
            ])
            recompute_course_entry(tmp, "math-camp")
            save_chunks(tmp, "math-camp", [
                {"chunk_id": "p-000", "file_id": "p", "chunk_index": 0, "tier": "page",
                 "heading_path": None, "problem_label": None, "page_range": [1, 1],
                 "text": "problem set chunk", "embedding": [1.0, 0.0], "embedding_model": "m", "content_hash": "h"},
                {"chunk_id": "t-000", "file_id": "t", "chunk_index": 0, "tier": "page",
                 "heading_path": None, "problem_label": None, "page_range": [1, 1],
                 "text": "textbook chunk", "embedding": [1.0, 0.0], "embedding_model": "m", "content_hash": "h"},
            ])
            results = search_passages([tmp], "query", client=_fake_query_client([1.0, 0.0]), doc_type="textbook")
            self.assertEqual([r.text for r in results], ["textbook chunk"])


class TestRebuildWithRealDuplicateClone(unittest.TestCase):
    """Integration coverage: Task 1 (duplicate_check.py writes the marker)
    and Task 2 (index_search.py reads it) tested together via the real
    production functions, not hand-fabricated metadata -- confirms the
    fix actually closes the loop end to end, the way a real conversion
    run's duplicate-check step and a later `rebuild` would encounter it."""

    def test_a_real_copy_duplicate_artifacts_clone_survives_rebuild(self):
        from indexer.duplicate_check import copy_duplicate_artifacts
        from indexer.index_card import compute_id_from_parts

        with tempfile.TemporaryDirectory() as tmp:
            canonical_pdf = _make_textbook(tmp, "econometrics", "Ok", "Ok_RealAnalysis_2007")
            canonical_file_id = compute_file_id(canonical_pdf)
            rel_canonical_pdf = os.path.relpath(canonical_pdf, tmp).replace(os.sep, "/")

            canonical_card = {
                "file_id": canonical_file_id,
                "path": "academic_resources/econometrics/textbooks-and-papers/processed_outputs/Ok_RealAnalysis_2007/Ok_RealAnalysis_2007.md",
                "source_pdf_path": rel_canonical_pdf, "course": "econometrics",
                "doc_type": "textbook", "title": "Real Analysis with Economic Applications",
                "embedding": [0.1, 0.2], "tags": [], "needs_indexing": False,
                "source_updated_at": "2026-01-01T00:00:00+00:00", "content_hash": "canonical-hash",
            }
            save_shard(tmp, "econometrics", [canonical_card])

            # The real production call, exactly as duplicate_check.py's
            # run_duplicate_check makes it on a confirmed Tier 1 match --
            # the new course's PDF path is fabricated here (not written to
            # disk) since copy_duplicate_artifacts never reads the new
            # PDF's own bytes, only the canonical book directory's.
            copy_duplicate_artifacts(
                tmp, "econometrics", canonical_card, "microecon", "textbooks-and-papers",
                "academic_resources/microecon/textbooks-and-papers/Ok.pdf",
            )

            client = _fake_client()
            stats = rebuild(tmp, client=client)

            # The canonical card is untouched, in its own shard.
            self.assertEqual(len(load_shard(tmp, "econometrics")), 1)
            self.assertEqual(load_shard(tmp, "econometrics")[0]["file_id"], canonical_file_id)

            # The clone survives, under its real derived id.
            clone_file_id = compute_id_from_parts([canonical_file_id, "microecon"])
            clone_cards = load_shard(tmp, "microecon")
            self.assertEqual(len(clone_cards), 1)
            self.assertEqual(clone_cards[0]["file_id"], clone_file_id)
            self.assertEqual(stats["skipped_duplicate_clone"], 1)

            # A subsequent --prune still doesn't touch either course.
            prune_stats = rebuild(tmp, client=_fake_client(), prune=True)
            self.assertEqual(prune_stats["pruned"], 0)
            self.assertEqual(len(load_shard(tmp, "econometrics")), 1)
            self.assertEqual(len(load_shard(tmp, "microecon")), 1)


if __name__ == "__main__":
    unittest.main()
