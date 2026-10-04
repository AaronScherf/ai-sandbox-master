import json
import os
import tempfile

from core.indexer.offering_links import (
    derive_offering_for_card,
    is_dismissed,
    load_dismissals,
    load_review,
    record_dismissal,
    save_dismissals,
    save_review,
)


def test_load_dismissals_returns_empty_list_when_missing():
    with tempfile.TemporaryDirectory() as tmp:
        assert load_dismissals(tmp) == []


def test_record_dismissal_round_trips():
    with tempfile.TemporaryDirectory() as tmp:
        record_dismissal(tmp, "fid1", "fid2")
        dismissals = load_dismissals(tmp)
        assert is_dismissed(dismissals, "fid1", "fid2")
        assert is_dismissed(dismissals, "fid2", "fid1")  # order-independent


def test_record_dismissal_is_a_no_op_if_already_recorded():
    with tempfile.TemporaryDirectory() as tmp:
        record_dismissal(tmp, "fid1", "fid2")
        record_dismissal(tmp, "fid2", "fid1")  # same pair, swapped order
        assert len(load_dismissals(tmp)) == 1


def test_is_dismissed_false_for_an_unrecorded_pair():
    assert is_dismissed([], "fid1", "fid2") is False


def test_dismissals_file_lives_one_level_inside_index_not_as_a_direct_child():
    with tempfile.TemporaryDirectory() as tmp:
        record_dismissal(tmp, "fid1", "fid2")
        assert os.path.isfile(os.path.join(tmp, ".index", "offering_links", "dismissals.json"))
        assert not os.path.isfile(os.path.join(tmp, ".index", "offering_links.json"))


def test_review_round_trips():
    with tempfile.TemporaryDirectory() as tmp:
        save_review(tmp, [{"file_id_a": "a", "file_id_b": "b", "similarity": 0.85, "course": "econometrics"}])
        assert load_review(tmp) == [{"file_id_a": "a", "file_id_b": "b", "similarity": 0.85, "course": "econometrics"}]


def test_load_review_returns_empty_list_when_missing():
    with tempfile.TemporaryDirectory() as tmp:
        assert load_review(tmp) == []


def test_load_dismissals_warns_and_treats_malformed_file_as_empty(capsys):
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, ".index", "offering_links", "dismissals.json")
        os.makedirs(os.path.dirname(path))
        with open(path, "w") as f:
            f.write("{not valid json")
        assert load_dismissals(tmp) == []
        assert "WARNING" in capsys.readouterr().out


def test_derive_offering_for_card_returns_none_for_a_primary_card():
    with tempfile.TemporaryDirectory() as tmp:
        notes_dir = os.path.join(tmp, "academic_notes", "econometrics", "ta_notes")
        os.makedirs(notes_dir)
        card = {"path": "academic_notes/econometrics/ta_notes/foo.md"}
        assert derive_offering_for_card(card, tmp) is None


def test_derive_offering_for_card_finds_the_label_from_a_marked_subset():
    with tempfile.TemporaryDirectory() as tmp:
        subset = os.path.join(tmp, "academic_resources", "econometrics", "class_2024")
        deep = os.path.join(subset, "Class Notes", "Hand-Written Notes")
        os.makedirs(deep)
        with open(os.path.join(subset, ".notes_subset.json"), "w") as f:
            json.dump({"label": "2024"}, f)
        card = {
            "path": "academic_notes/econometrics/class_2024/Class Notes/Hand-Written Notes/"
                    "processed_outputs/090424.md",
        }
        assert derive_offering_for_card(card, tmp) == "2024"


def test_derive_offering_for_card_works_without_a_stored_offering_label_field():
    # The real class_2024 cards from Phase 1's first run predate the
    # offering_label field entirely -- this must still work from path alone.
    with tempfile.TemporaryDirectory() as tmp:
        subset = os.path.join(tmp, "academic_resources", "econometrics", "class_2024")
        os.makedirs(subset)
        with open(os.path.join(subset, ".notes_subset.json"), "w") as f:
            json.dump({"label": "2024"}, f)
        card = {"path": "academic_notes/econometrics/class_2024/processed_outputs/2023exam1.md"}
        assert "offering_label" not in card
        assert derive_offering_for_card(card, tmp) == "2024"


from core.indexer.offering_links import find_cross_offering_matches

# Unit vectors at chosen angles so cosine_similarity's dot product gives an
# exact, easy-to-reason-about similarity: a=[1,0] vs [cos(t), sin(t)] -> cos(t).
_A = [1.0, 0.0]
_HIGH = [0.95, 0.3122498999199199]   # cosine 0.95 vs _A -- above auto (0.90)
_MID = [0.85, 0.5266403851195171]    # cosine 0.85 vs _A -- in review band (0.80-0.90)
_LOW = [0.5, 0.8660254037844387]     # cosine 0.5 vs _A -- below review band


def _card(file_id, embedding, path="academic_notes/econometrics/x.md"):
    return {"file_id": file_id, "path": path, "embedding": embedding, "title": file_id}


def test_same_offering_pairs_are_never_compared():
    cards = [(_card("a", _A), "2024"), (_card("b", _HIGH), "2024")]
    auto, review = find_cross_offering_matches(cards)
    assert auto == []
    assert review == []


def test_cross_offering_high_similarity_is_an_auto_match():
    cards = [(_card("a", _A), None), (_card("b", _HIGH), "2024")]
    auto, review = find_cross_offering_matches(cards)
    assert len(auto) == 1
    assert review == []
    card_a, card_b, similarity = auto[0]
    assert {card_a["file_id"], card_b["file_id"]} == {"a", "b"}
    assert similarity > 0.90

def test_cross_offering_mid_similarity_is_a_review_match():
    cards = [(_card("a", _A), None), (_card("b", _MID), "2024")]
    auto, review = find_cross_offering_matches(cards)
    assert auto == []
    assert len(review) == 1


def test_cross_offering_low_similarity_is_ignored():
    cards = [(_card("a", _A), None), (_card("b", _LOW), "2024")]
    auto, review = find_cross_offering_matches(cards)
    assert auto == []
    assert review == []


def test_three_offerings_compares_every_cross_pair():
    # 2023 vs 2024 counts too, not just subset-vs-primary (brainstorming
    # decision: "every pair in the course").
    cards = [(_card("a", _A), "2023"), (_card("b", _HIGH), "2024"), (_card("c", _LOW), None)]
    auto, review = find_cross_offering_matches(cards)
    assert len(auto) == 1  # a-b only; a-c and b-c are both low similarity
    matched_ids = {auto[0][0]["file_id"], auto[0][1]["file_id"]}
    assert matched_ids == {"a", "b"}


def test_custom_thresholds_are_respected():
    cards = [(_card("a", _A), None), (_card("b", _MID), "2024")]
    auto, review = find_cross_offering_matches(cards, auto_threshold=0.80, review_threshold=0.70)
    assert len(auto) == 1  # 0.85 now clears the lowered auto bar
    assert review == []


from core.indexer.offering_links import append_related_section, link_target_display, write_matches


def test_link_target_display_strips_notes_prefix_and_md_suffix():
    card = {"path": "academic_notes/econometrics/class_2024/Class Notes/Slides/processed_outputs/slides1.md",
            "title": "Slides 1"}
    link_path, alias = link_target_display(card, "2024")
    assert link_path == "econometrics/class_2024/Class Notes/Slides/processed_outputs/slides1"
    assert alias == "2024: Slides 1"


def test_link_target_display_labels_a_primary_card_as_current():
    card = {"path": "academic_notes/econometrics/professor_notes/processed_outputs/slides1.md", "title": "Slides 1"}
    _, alias = link_target_display(card, None)
    assert alias == "current: Slides 1"


def test_append_related_section_writes_a_new_block(tmp_path):
    academic_hub_root = str(tmp_path)
    note_dir = tmp_path / "academic_notes" / "econometrics"
    note_dir.mkdir(parents=True)
    note_path = note_dir / "y.md"
    note_path.write_text("---\ntitle: foo\n---\n\nBody text.\n")
    card = {"path": "academic_notes/econometrics/y.md"}
    target = {"path": "academic_notes/econometrics/class_2024/processed_outputs/x.md", "title": "X"}

    written = append_related_section(academic_hub_root, card, [(target, "2024", 0.92)])

    content = note_path.read_text()
    assert written is True
    assert content.startswith("---\ntitle: foo\n---\n\nBody text.\n")
    assert "## Related notes" in content
    assert "[[econometrics/class_2024/processed_outputs/x|2024: X]]" in content


def test_append_related_section_is_idempotent(tmp_path):
    academic_hub_root = str(tmp_path)
    note_dir = tmp_path / "academic_notes" / "econometrics"
    note_dir.mkdir(parents=True)
    note_path = note_dir / "y.md"
    note_path.write_text("---\ntitle: foo\n---\n\nBody text.\n")
    card = {"path": "academic_notes/econometrics/y.md"}
    target = {"path": "academic_notes/econometrics/class_2024/processed_outputs/x.md", "title": "X"}

    written_1 = append_related_section(academic_hub_root, card, [(target, "2024", 0.92)])
    content_1 = note_path.read_text()
    written_2 = append_related_section(academic_hub_root, card, [(target, "2024", 0.92)])
    content_2 = note_path.read_text()

    assert written_1 is True
    assert written_2 is True
    assert content_1 == content_2  # rerun replaces in place, doesn't duplicate
    assert content_1.count("## Related notes") == 1
    assert "[[econometrics/class_2024/processed_outputs/x|2024: X]]" in content_1


def test_append_related_section_reflects_a_changed_match_list(tmp_path):
    academic_hub_root = str(tmp_path)
    note_dir = tmp_path / "academic_notes" / "econometrics"
    note_dir.mkdir(parents=True)
    note_path = note_dir / "y.md"
    note_path.write_text("Body text.\n")
    card = {"path": "academic_notes/econometrics/y.md"}
    target_a = {"path": "academic_notes/econometrics/class_2024/processed_outputs/a.md", "title": "A"}
    target_b = {"path": "academic_notes/econometrics/class_2023/processed_outputs/b.md", "title": "B"}

    append_related_section(academic_hub_root, card, [(target_a, "2024", 0.92)])
    append_related_section(academic_hub_root, card, [(target_a, "2024", 0.92), (target_b, "2023", 0.88)])
    content = note_path.read_text()

    assert content.count("## Related notes") == 1
    assert "2024: A" in content
    assert "2023: B" in content


def test_append_related_section_skips_a_missing_file_without_raising(tmp_path):
    academic_hub_root = str(tmp_path)
    card = {"path": "academic_notes/econometrics/does-not-exist.md"}
    target = {"path": "academic_notes/econometrics/class_2024/processed_outputs/x.md", "title": "X"}

    written = append_related_section(academic_hub_root, card, [(target, "2024", 0.92)])
    assert written is False


def test_write_matches_updates_related_offerings_on_both_cards(tmp_path):
    from core.indexer.index_card import load_shard, save_shard

    academic_hub_root = str(tmp_path)
    note_dir_a = tmp_path / "academic_notes" / "econometrics"
    note_dir_a.mkdir(parents=True)
    (note_dir_a / "a.md").write_text("Body A.\n")
    (note_dir_a / "b.md").write_text("Body B.\n")

    card_a = {"file_id": "fa", "path": "academic_notes/econometrics/a.md", "title": "A", "embedding": [1.0, 0.0]}
    card_b = {"file_id": "fb", "path": "academic_notes/econometrics/b.md", "title": "B", "embedding": [0.95, 0.31]}
    save_shard(academic_hub_root, "econometrics", [card_a, card_b])

    stats = write_matches(academic_hub_root, [(card_a, card_b, 0.92)], confidence="high")

    cards = {c["file_id"]: c for c in load_shard(academic_hub_root, "econometrics")}
    assert cards["fa"]["related_offerings"] == [{"file_id": "fb", "path": card_b["path"], "similarity": 0.92, "confidence": "high"}]
    assert cards["fb"]["related_offerings"] == [{"file_id": "fa", "path": card_a["path"], "similarity": 0.92, "confidence": "high"}]
    assert stats["links_written"] == 1


def test_write_matches_replaces_a_stale_entry_for_the_same_pair_on_rerun(tmp_path):
    from core.indexer.index_card import load_shard, save_shard

    academic_hub_root = str(tmp_path)
    note_dir = tmp_path / "academic_notes" / "econometrics"
    note_dir.mkdir(parents=True)
    (note_dir / "a.md").write_text("Body A.\n")
    (note_dir / "b.md").write_text("Body B.\n")
    card_a = {"file_id": "fa", "path": "academic_notes/econometrics/a.md", "title": "A", "embedding": [1.0, 0.0]}
    card_b = {"file_id": "fb", "path": "academic_notes/econometrics/b.md", "title": "B", "embedding": [0.95, 0.31]}
    save_shard(academic_hub_root, "econometrics", [card_a, card_b])

    write_matches(academic_hub_root, [(card_a, card_b, 0.80)], confidence="review")
    write_matches(academic_hub_root, [(card_a, card_b, 0.95)], confidence="high")

    cards = {c["file_id"]: c for c in load_shard(academic_hub_root, "econometrics")}
    assert cards["fa"]["related_offerings"] == [{"file_id": "fb", "path": card_b["path"], "similarity": 0.95, "confidence": "high"}]


from core.indexer.offering_links import reject_pending, resolve_pending, run_for_course


def _seed_course(tmp_path, course, cards):
    from core.indexer.index_card import save_shard
    note_dir = tmp_path / "academic_notes" / course
    note_dir.mkdir(parents=True, exist_ok=True)
    for card in cards:
        rel = card["path"][len("academic_notes/"):]
        full = tmp_path / "academic_notes" / rel
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(f"Body for {card['file_id']}.\n")
    save_shard(str(tmp_path), course, cards)


def test_run_for_course_writes_an_auto_match_end_to_end(tmp_path):
    subset = tmp_path / "academic_resources" / "econometrics" / "class_2024"
    subset.mkdir(parents=True)
    (subset / ".notes_subset.json").write_text(json.dumps({"label": "2024"}))

    card_a = {"file_id": "fa", "path": "academic_notes/econometrics/professor_notes/a.md",
              "title": "A", "embedding": [1.0, 0.0]}
    card_b = {"file_id": "fb", "path": "academic_notes/econometrics/class_2024/b.md",
              "title": "B", "embedding": [0.95, 0.3122498999199199]}
    _seed_course(tmp_path, "econometrics", [card_a, card_b])

    stats = run_for_course(str(tmp_path), "econometrics")

    from core.indexer.index_card import load_shard
    cards = {c["file_id"]: c for c in load_shard(str(tmp_path), "econometrics")}
    assert cards["fa"]["related_offerings"][0]["file_id"] == "fb"
    assert cards["fb"]["related_offerings"][0]["file_id"] == "fa"
    assert stats["auto_matches"] == 1


def test_run_for_course_excludes_a_card_with_no_embedding(tmp_path):
    # A needs_indexing failure card has embedding=[] -- must be cleanly
    # excluded from comparison, not crash cosine_similarity() or get
    # spuriously matched against everything via an empty-vector score.
    subset = tmp_path / "academic_resources" / "econometrics" / "class_2024"
    subset.mkdir(parents=True)
    (subset / ".notes_subset.json").write_text(json.dumps({"label": "2024"}))
    card_a = {"file_id": "fa", "path": "academic_notes/econometrics/professor_notes/a.md",
              "title": "A", "embedding": [1.0, 0.0]}
    card_b = {"file_id": "fb", "path": "academic_notes/econometrics/class_2024/b.md",
              "title": "B", "embedding": [], "needs_indexing": True}
    _seed_course(tmp_path, "econometrics", [card_a, card_b])

    stats = run_for_course(str(tmp_path), "econometrics")

    assert stats["auto_matches"] == 0
    assert stats["review_matches"] == 0


def test_run_for_course_dry_run_writes_nothing(tmp_path):
    subset = tmp_path / "academic_resources" / "econometrics" / "class_2024"
    subset.mkdir(parents=True)
    (subset / ".notes_subset.json").write_text(json.dumps({"label": "2024"}))
    card_a = {"file_id": "fa", "path": "academic_notes/econometrics/professor_notes/a.md",
              "title": "A", "embedding": [1.0, 0.0]}
    card_b = {"file_id": "fb", "path": "academic_notes/econometrics/class_2024/b.md",
              "title": "B", "embedding": [0.95, 0.3122498999199199]}
    _seed_course(tmp_path, "econometrics", [card_a, card_b])

    stats = run_for_course(str(tmp_path), "econometrics", dry_run=True)

    from core.indexer.index_card import load_shard
    cards = {c["file_id"]: c for c in load_shard(str(tmp_path), "econometrics")}
    assert "related_offerings" not in cards["fa"]
    assert stats["auto_matches"] == 1


def test_run_for_course_logs_a_review_match_instead_of_writing_it(tmp_path):
    subset = tmp_path / "academic_resources" / "econometrics" / "class_2024"
    subset.mkdir(parents=True)
    (subset / ".notes_subset.json").write_text(json.dumps({"label": "2024"}))
    card_a = {"file_id": "fa", "path": "academic_notes/econometrics/professor_notes/a.md",
              "title": "A", "embedding": [1.0, 0.0]}
    card_b = {"file_id": "fb", "path": "academic_notes/econometrics/class_2024/b.md",
              "title": "B", "embedding": [0.85, 0.5266403851195171]}
    _seed_course(tmp_path, "econometrics", [card_a, card_b])

    stats = run_for_course(str(tmp_path), "econometrics")

    from core.indexer.offering_links import load_review
    from core.indexer.index_card import load_shard
    assert stats["review_matches"] == 1
    assert len(load_review(str(tmp_path))) == 1
    cards = {c["file_id"]: c for c in load_shard(str(tmp_path), "econometrics")}
    assert "related_offerings" not in cards["fa"]


def test_run_for_course_skips_a_dismissed_pair(tmp_path):
    from core.indexer.offering_links import record_dismissal
    subset = tmp_path / "academic_resources" / "econometrics" / "class_2024"
    subset.mkdir(parents=True)
    (subset / ".notes_subset.json").write_text(json.dumps({"label": "2024"}))
    card_a = {"file_id": "fa", "path": "academic_notes/econometrics/professor_notes/a.md",
              "title": "A", "embedding": [1.0, 0.0]}
    card_b = {"file_id": "fb", "path": "academic_notes/econometrics/class_2024/b.md",
              "title": "B", "embedding": [0.95, 0.3122498999199199]}
    _seed_course(tmp_path, "econometrics", [card_a, card_b])
    record_dismissal(str(tmp_path), "fa", "fb")

    stats = run_for_course(str(tmp_path), "econometrics")

    assert stats["auto_matches"] == 0
    from core.indexer.index_card import load_shard
    cards = {c["file_id"]: c for c in load_shard(str(tmp_path), "econometrics")}
    assert "related_offerings" not in cards["fa"]


def test_resolve_pending_promotes_a_review_match_to_a_written_link(tmp_path):
    subset = tmp_path / "academic_resources" / "econometrics" / "class_2024"
    subset.mkdir(parents=True)
    (subset / ".notes_subset.json").write_text(json.dumps({"label": "2024"}))
    card_a = {"file_id": "fa", "path": "academic_notes/econometrics/professor_notes/a.md",
              "title": "A", "embedding": [1.0, 0.0]}
    card_b = {"file_id": "fb", "path": "academic_notes/econometrics/class_2024/b.md",
              "title": "B", "embedding": [0.85, 0.5266403851195171]}
    _seed_course(tmp_path, "econometrics", [card_a, card_b])
    run_for_course(str(tmp_path), "econometrics")  # produces one pending review entry

    resolved = resolve_pending(str(tmp_path), "fa", "fb")

    from core.indexer.offering_links import load_review
    from core.indexer.index_card import load_shard
    assert resolved is True
    assert load_review(str(tmp_path)) == []
    cards = {c["file_id"]: c for c in load_shard(str(tmp_path), "econometrics")}
    assert cards["fa"]["related_offerings"][0]["confidence"] == "high"


def test_resolve_pending_returns_false_when_pair_not_in_review(tmp_path):
    assert resolve_pending(str(tmp_path), "nope", "nothing") is False


def test_reject_pending_dismisses_and_clears_the_pending_entry(tmp_path):
    subset = tmp_path / "academic_resources" / "econometrics" / "class_2024"
    subset.mkdir(parents=True)
    (subset / ".notes_subset.json").write_text(json.dumps({"label": "2024"}))
    card_a = {"file_id": "fa", "path": "academic_notes/econometrics/professor_notes/a.md",
              "title": "A", "embedding": [1.0, 0.0]}
    card_b = {"file_id": "fb", "path": "academic_notes/econometrics/class_2024/b.md",
              "title": "B", "embedding": [0.85, 0.5266403851195171]}
    _seed_course(tmp_path, "econometrics", [card_a, card_b])
    run_for_course(str(tmp_path), "econometrics")

    rejected = reject_pending(str(tmp_path), "fa", "fb")

    from core.indexer.offering_links import is_dismissed, load_dismissals, load_review
    assert rejected is True
    assert load_review(str(tmp_path)) == []
    assert is_dismissed(load_dismissals(str(tmp_path)), "fa", "fb")


# --- Final-review fix pass: merge-not-replace, resolved matches staying
# resolved, dismissing an already-linked pair, content_hash freshness,
# unreadable-file safety, wikilink sanitization, and --dry-run detail. ---

def test_link_target_display_sanitizes_unsafe_wikilink_characters():
    card = {"path": "academic_notes/econometrics/Problem Set #1/processed_outputs/a.md",
            "title": "A]] | evil\ntitle"}
    link_path, alias = link_target_display(card, "2024")
    assert "]]" not in alias
    assert "|" not in alias
    assert "#" not in link_path
    assert "\n" not in alias


def test_append_related_section_skips_an_unreadable_file_without_raising(tmp_path):
    academic_hub_root = str(tmp_path)
    note_dir = tmp_path / "academic_notes" / "econometrics"
    note_dir.mkdir(parents=True)
    note_path = note_dir / "y.md"
    note_path.write_bytes(b"\xff\xfe not valid utf-8 \x80\x81")  # guaranteed UnicodeDecodeError on utf-8 read
    card = {"path": "academic_notes/econometrics/y.md"}
    target = {"path": "academic_notes/econometrics/class_2024/processed_outputs/x.md", "title": "X"}

    written = append_related_section(academic_hub_root, card, [(target, "2024", 0.92)])
    assert written is False


def test_write_matches_preserves_existing_links_to_other_cards(tmp_path):
    from core.indexer.index_card import load_shard, save_shard
    academic_hub_root = str(tmp_path)
    note_dir = tmp_path / "academic_notes" / "econometrics"
    note_dir.mkdir(parents=True)
    (note_dir / "a.md").write_text("Body A.\n")
    (note_dir / "b.md").write_text("Body B.\n")
    (note_dir / "c.md").write_text("Body C.\n")
    card_a = {"file_id": "fa", "path": "academic_notes/econometrics/a.md", "title": "A", "embedding": [1.0, 0.0]}
    card_b = {"file_id": "fb", "path": "academic_notes/econometrics/b.md", "title": "B", "embedding": [0.95, 0.31]}
    card_c = {"file_id": "fc", "path": "academic_notes/econometrics/c.md", "title": "C", "embedding": [0.95, 0.31]}
    save_shard(academic_hub_root, "econometrics", [card_a, card_b, card_c])

    write_matches(academic_hub_root, [(card_a, card_b, 0.92)], confidence="high")
    write_matches(academic_hub_root, [(card_a, card_c, 0.93)], confidence="high")

    cards = {c["file_id"]: c for c in load_shard(academic_hub_root, "econometrics")}
    linked_ids = {e["file_id"] for e in cards["fa"]["related_offerings"]}
    assert linked_ids == {"fb", "fc"}


def test_write_matches_updates_content_hash_to_match_the_written_markdown(tmp_path):
    from core.indexer.index_card import compute_content_hash, load_shard, save_shard
    academic_hub_root = str(tmp_path)
    note_dir = tmp_path / "academic_notes" / "econometrics"
    note_dir.mkdir(parents=True)
    (note_dir / "a.md").write_text("Body A.\n")
    (note_dir / "b.md").write_text("Body B.\n")
    card_a = {"file_id": "fa", "path": "academic_notes/econometrics/a.md", "title": "A",
              "embedding": [1.0, 0.0], "content_hash": "stale"}
    card_b = {"file_id": "fb", "path": "academic_notes/econometrics/b.md", "title": "B", "embedding": [0.95, 0.31]}
    save_shard(academic_hub_root, "econometrics", [card_a, card_b])

    write_matches(academic_hub_root, [(card_a, card_b, 0.92)], confidence="high")

    cards = {c["file_id"]: c for c in load_shard(academic_hub_root, "econometrics")}
    real_hash = compute_content_hash(str(tmp_path / "academic_notes" / "econometrics" / "a.md"))
    assert cards["fa"]["content_hash"] == real_hash
    assert cards["fa"]["content_hash"] != "stale"


def test_run_for_course_is_idempotent_on_rerun_after_auto_linking(tmp_path):
    subset = tmp_path / "academic_resources" / "econometrics" / "class_2024"
    subset.mkdir(parents=True)
    (subset / ".notes_subset.json").write_text(json.dumps({"label": "2024"}))
    card_a = {"file_id": "fa", "path": "academic_notes/econometrics/professor_notes/a.md",
              "title": "A", "embedding": [1.0, 0.0]}
    card_b = {"file_id": "fb", "path": "academic_notes/econometrics/class_2024/b.md",
              "title": "B", "embedding": [0.95, 0.3122498999199199]}
    _seed_course(tmp_path, "econometrics", [card_a, card_b])

    first = run_for_course(str(tmp_path), "econometrics")
    second = run_for_course(str(tmp_path), "econometrics")

    assert first["auto_matches"] == 1
    assert second["auto_matches"] == 0  # already linked, not re-processed


def test_resolve_pending_then_rerun_does_not_put_the_pair_back_in_review(tmp_path):
    subset = tmp_path / "academic_resources" / "econometrics" / "class_2024"
    subset.mkdir(parents=True)
    (subset / ".notes_subset.json").write_text(json.dumps({"label": "2024"}))
    card_a = {"file_id": "fa", "path": "academic_notes/econometrics/professor_notes/a.md",
              "title": "A", "embedding": [1.0, 0.0]}
    card_b = {"file_id": "fb", "path": "academic_notes/econometrics/class_2024/b.md",
              "title": "B", "embedding": [0.85, 0.5266403851195171]}
    _seed_course(tmp_path, "econometrics", [card_a, card_b])
    run_for_course(str(tmp_path), "econometrics")  # produces one pending review entry
    resolve_pending(str(tmp_path), "fa", "fb")

    stats = run_for_course(str(tmp_path), "econometrics")

    assert load_review(str(tmp_path)) == []
    assert stats["review_matches"] == 0


def test_reject_pending_removes_an_existing_auto_linked_pair(tmp_path):
    subset = tmp_path / "academic_resources" / "econometrics" / "class_2024"
    subset.mkdir(parents=True)
    (subset / ".notes_subset.json").write_text(json.dumps({"label": "2024"}))
    card_a = {"file_id": "fa", "path": "academic_notes/econometrics/professor_notes/a.md",
              "title": "A", "embedding": [1.0, 0.0]}
    card_b = {"file_id": "fb", "path": "academic_notes/econometrics/class_2024/b.md",
              "title": "B", "embedding": [0.95, 0.3122498999199199]}
    _seed_course(tmp_path, "econometrics", [card_a, card_b])
    run_for_course(str(tmp_path), "econometrics")  # auto-links fa <-> fb

    rejected = reject_pending(str(tmp_path), "fa", "fb")

    from core.indexer.index_card import load_shard
    from core.indexer.offering_links import is_dismissed, load_dismissals
    assert rejected is True
    cards = {c["file_id"]: c for c in load_shard(str(tmp_path), "econometrics")}
    assert cards["fa"].get("related_offerings") == []
    assert cards["fb"].get("related_offerings") == []
    assert is_dismissed(load_dismissals(str(tmp_path)), "fa", "fb")
    a_content = (tmp_path / "academic_notes" / "econometrics" / "professor_notes" / "a.md").read_text()
    assert "## Related notes" not in a_content


def test_run_for_course_dry_run_reports_pair_details(tmp_path):
    subset = tmp_path / "academic_resources" / "econometrics" / "class_2024"
    subset.mkdir(parents=True)
    (subset / ".notes_subset.json").write_text(json.dumps({"label": "2024"}))
    card_a = {"file_id": "fa", "path": "academic_notes/econometrics/professor_notes/a.md",
              "title": "A", "embedding": [1.0, 0.0]}
    card_b = {"file_id": "fb", "path": "academic_notes/econometrics/class_2024/b.md",
              "title": "B", "embedding": [0.95, 0.3122498999199199]}
    _seed_course(tmp_path, "econometrics", [card_a, card_b])

    stats = run_for_course(str(tmp_path), "econometrics", dry_run=True)

    assert len(stats["auto_pairs"]) == 1
    pair = stats["auto_pairs"][0]
    assert {pair["file_id_a"], pair["file_id_b"]} == {"fa", "fb"}
    assert pair["similarity"] > 0.9


def test_academic_hub_dir_resolves_to_the_real_sibling_directory():
    # Real finding: this previously pointed one level too shallow
    # (academic-rag-model/academic-hub, which doesn't exist) instead of
    # the real ai-sandbox/academic-hub sibling -- load_shard() silently
    # returns [] for a missing path, so main() ran with zero cards and
    # reported "0 linked, 0 pending review" with no error at all.
    from core.indexer.offering_links import _academic_hub_dir
    resolved = _academic_hub_dir()
    assert resolved.name == "academic-hub"
    assert resolved.parent.name == "ai-sandbox"
    assert os.path.isdir(resolved)
