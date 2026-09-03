import os
import tempfile
import unittest
from unittest.mock import MagicMock

from indexer.index_card import (
    compute_file_id,
    derive_course,
    load_courses,
    load_shard,
    save_courses,
    save_shard,
    cosine_similarity,
    generate_index_card,
    make_failure_card,
    move_card,
    recompute_course_entry,
    find_card_by_file_id,
    reconcile_and_write,
    set_rag_md_path,
    list_courses,
    load_tags,
    save_tags,
)


def _fake_client(doc_type="textbook", has_solutions=False, level="introductory"):
    client = MagicMock()
    gen_response = MagicMock()
    gen_response.text = (
        '{"title": "Linear Algebra Done Right", "doc_type": "%s", '
        '"summary": "Covers vector spaces and eigenvalues.", '
        '"level": "%s", "has_solutions": %s}'
        % (doc_type, level, str(has_solutions).lower())
    )
    client.models.generate_content.return_value = gen_response

    embed_response = MagicMock()
    embedding = MagicMock()
    embedding.values = [0.1, 0.2, 0.3]
    embed_response.embeddings = [embedding]
    client.models.embed_content.return_value = embed_response
    return client


def _fake_list_wrapped_client():
    # Real finding: gemini-3.1-flash-lite sometimes wraps an otherwise
    # perfectly-formed response object in a one-element JSON array,
    # despite response_mime_type="application/json" and prompt
    # instructions asking for a bare object. Reproduced live against
    # LN_Linear Algebra.md.
    client = MagicMock()
    gen_response = MagicMock()
    gen_response.text = (
        '[{"title": "Linear Algebra Notes", "doc_type": "ta_notes", '
        '"summary": "Covers vector spaces.", "level": "intermediate", "has_solutions": false}]'
    )
    client.models.generate_content.return_value = gen_response
    embed_response = MagicMock()
    embedding = MagicMock()
    embedding.values = [0.1, 0.2, 0.3]
    embed_response.embeddings = [embedding]
    client.models.embed_content.return_value = embed_response
    return client


class TestComputeFileId(unittest.TestCase):
    def test_same_bytes_produce_same_id_regardless_of_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = os.path.join(tmp, "a.pdf")
            b = os.path.join(tmp, "nested", "b.pdf")
            os.makedirs(os.path.dirname(b))
            for p in (a, b):
                with open(p, "wb") as f:
                    f.write(b"%PDF-1.4 fake content for hashing")
            self.assertEqual(compute_file_id(a), compute_file_id(b))

    def test_different_bytes_produce_different_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = os.path.join(tmp, "a.pdf")
            b = os.path.join(tmp, "b.pdf")
            with open(a, "wb") as f:
                f.write(b"content one")
            with open(b, "wb") as f:
                f.write(b"content two")
            self.assertNotEqual(compute_file_id(a), compute_file_id(b))

    def test_id_is_a_short_hex_string(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, "a.pdf")
            with open(p, "wb") as f:
                f.write(b"x")
            file_id = compute_file_id(p)
            self.assertEqual(len(file_id), 16)
            int(file_id, 16)  # raises ValueError if not valid hex


class TestDeriveCourse(unittest.TestCase):
    def test_notes_path(self):
        self.assertEqual(
            derive_course("academic_notes/math-camp/ta_notes/foo.pdf"), "math-camp"
        )

    def test_resources_path(self):
        self.assertEqual(
            derive_course("academic_resources/econ-101/textbooks-and-papers/bar.pdf"),
            "econ-101",
        )

    def test_handles_backslashes(self):
        self.assertEqual(
            derive_course(r"academic_notes\math-camp\handwritten_notes\x.pdf"), "math-camp"
        )

    def test_raises_on_too_short_path(self):
        with self.assertRaises(ValueError):
            derive_course("just_a_file.pdf")


class TestShardIO(unittest.TestCase):
    def test_load_missing_shard_returns_empty_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(load_shard(tmp, "math-camp"), [])

    def test_save_then_load_round_trips(self):
        with tempfile.TemporaryDirectory() as tmp:
            cards = [{"file_id": "abc", "path": "x.md"}]
            save_shard(tmp, "math-camp", cards)
            self.assertEqual(load_shard(tmp, "math-camp"), cards)

    def test_load_missing_courses_returns_empty_dict(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(load_courses(tmp), {})

    def test_save_then_load_courses_round_trips(self):
        with tempfile.TemporaryDirectory() as tmp:
            courses = {"math-camp": {"course": "math-camp", "file_count": 1}}
            save_courses(tmp, courses)
            self.assertEqual(load_courses(tmp), courses)


class TestCosineSimilarity(unittest.TestCase):
    def test_identical_vectors_score_one(self):
        self.assertAlmostEqual(cosine_similarity([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]), 1.0, places=6)

    def test_orthogonal_vectors_score_zero(self):
        self.assertAlmostEqual(cosine_similarity([1.0, 0.0], [0.0, 1.0]), 0.0, places=6)

    def test_not_sensitive_to_magnitude(self):
        # Confirmed live against the real API that gemini-embedding-001
        # does NOT return unit-normalized vectors -- this is the case that
        # would silently break if cosine_similarity assumed unit length.
        a = [1.0, 1.0]
        b = [50.0, 50.0]
        self.assertAlmostEqual(cosine_similarity(a, b), 1.0, places=6)

    def test_empty_vector_scores_zero_not_a_crash(self):
        self.assertEqual(cosine_similarity([], [1.0, 2.0]), 0.0)


class TestRecomputeCourseEntry(unittest.TestCase):
    def test_computes_centroid_and_file_count_from_shard_cards(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [
                {"file_id": "a", "embedding": [1.0, 0.0], "tags": ["linear-algebra"]},
                {"file_id": "b", "embedding": [0.0, 1.0], "tags": ["linear-algebra", "real-analysis"]},
            ])
            recompute_course_entry(tmp, "math-camp")
            courses = load_courses(tmp)
            self.assertEqual(courses["math-camp"]["file_count"], 2)
            self.assertEqual(courses["math-camp"]["embedding"], [0.5, 0.5])
            self.assertIn("linear-algebra", courses["math-camp"]["predominant_tags"])

    def test_title_is_a_readable_form_of_the_course_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [{"file_id": "a", "embedding": [1.0], "tags": []}])
            recompute_course_entry(tmp, "math-camp")
            self.assertEqual(load_courses(tmp)["math-camp"]["title"], "Math Camp")

    def test_excludes_orphaned_cards_from_rollup(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [
                {"file_id": "a", "embedding": [1.0, 0.0], "tags": [], "orphaned": True},
                {"file_id": "b", "embedding": [0.0, 1.0], "tags": []},
            ])
            recompute_course_entry(tmp, "math-camp")
            courses = load_courses(tmp)
            self.assertEqual(courses["math-camp"]["file_count"], 1)
            self.assertEqual(courses["math-camp"]["embedding"], [0.0, 1.0])

    def test_removes_course_entry_when_shard_becomes_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [{"file_id": "a", "embedding": [1.0], "tags": []}])
            recompute_course_entry(tmp, "math-camp")
            save_shard(tmp, "math-camp", [])
            recompute_course_entry(tmp, "math-camp")
            self.assertNotIn("math-camp", load_courses(tmp))

    def test_cards_missing_tags_are_missing_from_the_embedding_but_not_a_crash(self):
        # needs_indexing cards (Task 2) have embedding: [] -- must not
        # poison the centroid computation.
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [
                {"file_id": "a", "embedding": [], "tags": [], "needs_indexing": True},
                {"file_id": "b", "embedding": [1.0, 0.0], "tags": []},
            ])
            recompute_course_entry(tmp, "math-camp")
            courses = load_courses(tmp)
            self.assertEqual(courses["math-camp"]["embedding"], [1.0, 0.0])
            self.assertEqual(courses["math-camp"]["file_count"], 2)


class TestGenerateIndexCard(unittest.TestCase):
    def test_builds_a_complete_card_from_llm_and_embedding_responses(self):
        client = _fake_client()
        card = generate_index_card(
            file_id="abc123",
            path="academic_resources/math-camp/textbooks-and-papers/processed_outputs/Axler/Axler.md",
            source_pdf_path="academic_resources/math-camp/textbooks-and-papers/Axler.pdf",
            course="math-camp",
            folder_category="textbooks-and-papers",
            content_sample="Chapter 1: Vector Spaces...",
            page_count=404,
            client=client,
        )
        self.assertEqual(card["file_id"], "abc123")
        self.assertEqual(card["title"], "Linear Algebra Done Right")
        self.assertEqual(card["doc_type"], "textbook")
        self.assertEqual(card["summary"], "Covers vector spaces and eigenvalues.")
        self.assertEqual(card["level"], "introductory")
        self.assertFalse(card["has_solutions"])
        self.assertEqual(card["page_count"], 404)
        self.assertEqual(card["embedding"], [0.1, 0.2, 0.3])
        self.assertEqual(card["embedding_model"], "gemini-embedding-001:768")
        self.assertEqual(card["tags"], [])
        self.assertFalse(card["needs_indexing"])
        self.assertIsNone(card["rag_md_path"])
        self.assertNotIn("orphaned", card)

    def test_falls_back_to_folder_category_when_llm_doc_type_is_unrecognized(self):
        client = _fake_client(doc_type="something_weird")
        card = generate_index_card(
            file_id="x", path="p.md", source_pdf_path="p.pdf", course="math-camp",
            folder_category="ta_notes", content_sample="text", page_count=10, client=client,
        )
        self.assertEqual(card["doc_type"], "ta_notes")

    def test_falls_back_to_introductory_when_llm_level_is_unrecognized(self):
        client = _fake_client(level="expert-plus")
        card = generate_index_card(
            file_id="x", path="p.md", source_pdf_path="p.pdf", course="math-camp",
            folder_category="ta_notes", content_sample="text", page_count=10, client=client,
        )
        self.assertEqual(card["level"], "introductory")

    def test_custom_known_doc_types_accepts_a_value_outside_the_default_vocabulary(self):
        # Confirmed live (2026-08-30): with the default academic-hub
        # vocabulary, a personal essay corpus got every single card
        # force-fit into "textbook"/"handwritten_notes" -- a corpus
        # passing its own known_doc_types must be able to accept a value
        # the default vocabulary doesn't recognize at all.
        client = _fake_client(doc_type="personal_essay")
        card = generate_index_card(
            file_id="x", path="p.md", source_pdf_path="p.pdf", course="notes",
            folder_category="application_essays", content_sample="text", page_count=None,
            client=client, known_doc_types=frozenset({"personal_essay", "research_notes"}),
        )
        self.assertEqual(card["doc_type"], "personal_essay")

    def test_custom_known_doc_types_still_falls_back_when_llm_answer_is_outside_it(self):
        # "textbook" is valid under the *default* vocabulary but not
        # under this custom one -- proves the fallback check uses the
        # passed-in set, not the module-level KNOWN_DOC_TYPES constant.
        client = _fake_client(doc_type="textbook")
        card = generate_index_card(
            file_id="x", path="p.md", source_pdf_path="p.pdf", course="notes",
            folder_category="application_essays", content_sample="text", page_count=None,
            client=client, known_doc_types=frozenset({"personal_essay", "research_notes"}),
        )
        self.assertEqual(card["doc_type"], "application_essays")

    def test_prompt_sent_to_llm_reflects_the_custom_doc_type_vocabulary(self):
        client = _fake_client(doc_type="personal_essay")
        generate_index_card(
            file_id="x", path="p.md", source_pdf_path="p.pdf", course="notes",
            folder_category="application_essays", content_sample="text", page_count=None,
            client=client, known_doc_types=frozenset({"personal_essay", "research_notes"}),
        )
        sent_prompt = client.models.generate_content.call_args.kwargs["contents"]
        self.assertIn('"personal_essay"', sent_prompt)
        self.assertIn('"research_notes"', sent_prompt)
        self.assertNotIn('"textbook"', sent_prompt)

    def test_embeds_title_and_summary_not_raw_content(self):
        client = _fake_client()
        generate_index_card(
            file_id="x", path="p.md", source_pdf_path="p.pdf", course="math-camp",
            folder_category="ta_notes", content_sample="a" * 50000, page_count=10, client=client,
        )
        embed_call = client.models.embed_content.call_args
        self.assertIn("Linear Algebra Done Right", embed_call.kwargs["contents"])
        self.assertIn("Covers vector spaces", embed_call.kwargs["contents"])
        self.assertNotIn("a" * 50000, embed_call.kwargs["contents"])

    def test_prompt_mentions_folder_category_as_a_hint_not_a_verdict(self):
        client = _fake_client()
        generate_index_card(
            file_id="x", path="p.md", source_pdf_path="p.pdf", course="math-camp",
            folder_category="problem_sets", content_sample="text", page_count=10, client=client,
        )
        prompt = client.models.generate_content.call_args.kwargs["contents"]
        self.assertIn("problem_sets", prompt)

    def test_unwraps_a_list_wrapped_response(self):
        client = _fake_list_wrapped_client()
        card = generate_index_card(
            file_id="x", path="p.md", source_pdf_path="p.pdf", course="math-camp",
            folder_category="ta_notes", content_sample="text", page_count=10, client=client,
        )
        self.assertEqual(card["title"], "Linear Algebra Notes")
        self.assertEqual(card["doc_type"], "ta_notes")
        self.assertEqual(card["summary"], "Covers vector spaces.")
        self.assertEqual(card["level"], "intermediate")
        self.assertFalse(card["needs_indexing"])


class TestMakeFailureCard(unittest.TestCase):
    def test_minimal_card_carries_enough_to_be_reconciled_later(self):
        card = make_failure_card(
            file_id="abc123", path="p.md", source_pdf_path="p.pdf",
            course="math-camp", folder_category="ta_notes",
        )
        self.assertEqual(card["file_id"], "abc123")
        self.assertEqual(card["path"], "p.md")
        self.assertEqual(card["source_pdf_path"], "p.pdf")
        self.assertEqual(card["course"], "math-camp")
        self.assertEqual(card["doc_type"], "ta_notes")
        self.assertTrue(card["needs_indexing"])
        self.assertEqual(card["embedding"], [])


class TestFindCardByFileId(unittest.TestCase):
    def test_finds_across_shards_not_just_one_course(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [{"file_id": "x", "path": "a.md"}])
            save_shard(tmp, "econ-101", [{"file_id": "y", "path": "b.md"}])
            found = find_card_by_file_id(tmp, "y")
            self.assertEqual(found[0], "econ-101")
            self.assertEqual(found[1]["path"], "b.md")

    def test_returns_none_when_not_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [{"file_id": "x", "path": "a.md"}])
            self.assertIsNone(find_card_by_file_id(tmp, "nope"))

    def test_returns_none_when_index_dir_does_not_exist_yet(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(find_card_by_file_id(tmp, "x"))

    def test_ignores_courses_json_and_tags_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_courses(tmp, {"math-camp": {"course": "math-camp", "file_count": 0}})
            self.assertIsNone(find_card_by_file_id(tmp, "math-camp"))


class TestMoveCard(unittest.TestCase):
    def test_moves_card_between_shards_and_updates_course_field(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "misc", [
                {"file_id": "x", "path": "misc/processed_outputs/a.md",
                 "source_pdf_path": "misc/a.pdf", "course": "misc",
                 "embedding": [1.0, 0.0], "tags": ["some-tag"]},
            ])
            result = move_card(tmp, "x", "business")

            self.assertTrue(result)
            self.assertEqual(load_shard(tmp, "misc"), [])
            moved = load_shard(tmp, "business")
            self.assertEqual(len(moved), 1)
            self.assertEqual(moved[0]["course"], "business")
            self.assertEqual(moved[0]["path"], "business/processed_outputs/a.md")
            self.assertEqual(moved[0]["source_pdf_path"], "business/a.pdf")

    def test_recomputes_course_entry_for_both_old_and_new_course(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "misc", [
                {"file_id": "x", "path": "misc/processed_outputs/a.md",
                 "source_pdf_path": "misc/a.pdf", "course": "misc",
                 "embedding": [1.0, 0.0], "tags": []},
                {"file_id": "y", "path": "misc/processed_outputs/b.md",
                 "source_pdf_path": "misc/b.pdf", "course": "misc",
                 "embedding": [0.0, 1.0], "tags": []},
            ])
            move_card(tmp, "x", "business")

            self.assertEqual(load_courses(tmp)["misc"]["file_count"], 1)
            self.assertEqual(load_courses(tmp)["business"]["file_count"], 1)

    def test_returns_false_when_card_not_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "misc", [{"file_id": "x", "path": "a.md", "course": "misc",
                                       "embedding": [1.0], "tags": []}])
            self.assertFalse(move_card(tmp, "nonexistent", "business"))

    def test_no_op_when_already_in_target_course(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "misc", [{"file_id": "x", "path": "misc/a.md", "source_pdf_path": "misc/a.pdf",
                                       "course": "misc", "embedding": [1.0], "tags": []}])
            result = move_card(tmp, "x", "misc")
            self.assertTrue(result)
            self.assertEqual(len(load_shard(tmp, "misc")), 1)


class TestReconcileAndWrite(unittest.TestCase):
    def _card_kwargs(self, **overrides):
        kwargs = dict(
            file_id="fid1", path="a.md", source_pdf_path="a.pdf", course="math-camp",
            folder_category="ta_notes", content_sample="text", page_count=5, client=_fake_client(),
        )
        kwargs.update(overrides)
        return kwargs

    def test_no_match_generates_a_fresh_card(self):
        with tempfile.TemporaryDirectory() as tmp:
            card = reconcile_and_write(tmp, **self._card_kwargs())
            self.assertEqual(card["file_id"], "fid1")
            self.assertFalse(card["needs_indexing"])
            self.assertEqual(load_shard(tmp, "math-camp")[0]["file_id"], "fid1")
            self.assertEqual(load_courses(tmp)["math-camp"]["file_count"], 1)

    def test_known_doc_types_is_forwarded_on_the_genuinely_new_content_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            client = _fake_client(doc_type="personal_essay")
            card = reconcile_and_write(tmp, **self._card_kwargs(
                client=client, known_doc_types=frozenset({"personal_essay", "research_notes"}),
            ))
            self.assertEqual(card["doc_type"], "personal_essay")

    def test_generation_failure_writes_a_minimal_card_not_a_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad_client = MagicMock()
            bad_client.models.generate_content.side_effect = RuntimeError("quota exceeded")
            card = reconcile_and_write(tmp, **self._card_kwargs(client=bad_client))
            self.assertTrue(card["needs_indexing"])
            self.assertEqual(load_shard(tmp, "math-camp")[0]["file_id"], "fid1")

    def test_match_same_course_unchanged_path_is_a_no_op(self):
        with tempfile.TemporaryDirectory() as tmp:
            reconcile_and_write(tmp, **self._card_kwargs())
            before = load_shard(tmp, "math-camp")[0]
            reconcile_and_write(tmp, **self._card_kwargs())  # identical path/course
            after = load_shard(tmp, "math-camp")[0]
            self.assertEqual(before, after)  # no regeneration, no field churn

    def test_match_same_course_changed_path_updates_in_place_without_regenerating(self):
        with tempfile.TemporaryDirectory() as tmp:
            client = _fake_client()
            reconcile_and_write(tmp, **self._card_kwargs(client=client))
            self.assertEqual(client.models.generate_content.call_count, 1)
            reconcile_and_write(tmp, **self._card_kwargs(
                path="moved/a.md", source_pdf_path="moved/a.pdf", client=client,
            ))
            self.assertEqual(client.models.generate_content.call_count, 1)  # still 1 -- no regen
            cards = load_shard(tmp, "math-camp")
            self.assertEqual(len(cards), 1)
            self.assertEqual(cards[0]["path"], "moved/a.md")

    def test_match_different_course_moves_card_and_recomputes_both_rollups(self):
        with tempfile.TemporaryDirectory() as tmp:
            client = _fake_client()
            reconcile_and_write(tmp, **self._card_kwargs(client=client, course="math-camp"))
            reconcile_and_write(tmp, **self._card_kwargs(
                client=client, course="econ-101", path="moved/a.md", source_pdf_path="moved/a.pdf",
            ))
            self.assertEqual(client.models.generate_content.call_count, 1)  # still no regen
            self.assertEqual(load_shard(tmp, "math-camp"), [])
            self.assertNotIn("math-camp", load_courses(tmp))
            moved_cards = load_shard(tmp, "econ-101")
            self.assertEqual(len(moved_cards), 1)
            self.assertEqual(moved_cards[0]["course"], "econ-101")
            self.assertEqual(load_courses(tmp)["econ-101"]["file_count"], 1)

    def test_reconciliation_clears_a_prior_orphaned_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            client = _fake_client()
            reconcile_and_write(tmp, **self._card_kwargs(client=client))
            cards = load_shard(tmp, "math-camp")
            cards[0]["orphaned"] = True
            save_shard(tmp, "math-camp", cards)
            reconcile_and_write(tmp, **self._card_kwargs(client=client))
            self.assertNotIn("orphaned", load_shard(tmp, "math-camp")[0])


class TestSetRagMdPath(unittest.TestCase):
    def test_sets_rag_md_path_on_the_matching_card(self):
        with tempfile.TemporaryDirectory() as tmp:
            reconcile_and_write(tmp, file_id="fid1", path="a.md", source_pdf_path="a.pdf",
                                 course="math-camp", folder_category="textbooks-and-papers",
                                 content_sample="text", page_count=10, client=_fake_client())
            found = set_rag_md_path(tmp, "fid1", "a.rag.md")
            self.assertTrue(found)
            self.assertEqual(load_shard(tmp, "math-camp")[0]["rag_md_path"], "a.rag.md")

    def test_returns_false_and_writes_nothing_when_no_card_matches(self):
        with tempfile.TemporaryDirectory() as tmp:
            found = set_rag_md_path(tmp, "no-such-file-id", "a.rag.md")
            self.assertFalse(found)

    def test_works_on_a_needs_indexing_card_which_still_has_a_file_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad_client = MagicMock()
            bad_client.models.generate_content.side_effect = RuntimeError("quota exceeded")
            reconcile_and_write(tmp, file_id="fid1", path="a.md", source_pdf_path="a.pdf",
                                 course="math-camp", folder_category="textbooks-and-papers",
                                 content_sample="text", page_count=10, client=bad_client)
            found = set_rag_md_path(tmp, "fid1", "a.rag.md")
            self.assertTrue(found)
            self.assertEqual(load_shard(tmp, "math-camp")[0]["rag_md_path"], "a.rag.md")


class TestListCourses(unittest.TestCase):
    def test_lists_course_shards_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [{"file_id": "a"}])
            save_shard(tmp, "econ-101", [{"file_id": "b"}])
            save_courses(tmp, {"math-camp": {"course": "math-camp", "file_count": 1}})
            save_tags(tmp, [{"tag": "linear-algebra", "embedding": [1.0]}])
            self.assertEqual(sorted(list_courses(tmp)), ["econ-101", "math-camp"])

    def test_empty_when_no_index_dir_exists_yet(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(list_courses(tmp), [])


class TestTagVocabularyIO(unittest.TestCase):
    def test_load_missing_tags_returns_empty_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(load_tags(tmp), [])

    def test_save_then_load_round_trips(self):
        with tempfile.TemporaryDirectory() as tmp:
            tags = [{"tag": "linear-algebra", "embedding": [0.1, 0.2]}]
            save_tags(tmp, tags)
            self.assertEqual(load_tags(tmp), tags)


if __name__ == "__main__":
    unittest.main()
