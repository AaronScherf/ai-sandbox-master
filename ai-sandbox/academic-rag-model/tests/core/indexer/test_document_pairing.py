import os
import tempfile

from core.indexer.document_pairing import (
    LECTURE_SLIDES_NOTES_PAIR_TYPE,
    PROBLEM_SOLUTION_PAIR_TYPE,
    classify_document,
    find_document_pairs,
    is_dismissed,
    load_dismissals,
    load_review,
    record_dismissal,
    save_dismissals,
    save_review,
)

# --- classify_document(): naming-convention heuristics against real
# filenames seen in academic-hub (academic_notes/microecon/problem_sets/,
# academic_notes/econometrics/problem_sets/,
# academic_notes/microecon/2025_class/Homeworks/{,Solutions/}). ---


def _card(path, course="microecon"):
    return {"file_id": path, "path": path, "course": course}


def test_classify_document_recognizes_a_bare_homework_as_the_problem_role():
    card = _card("academic_notes/microecon/problem_sets/processed_outputs/Homework_4.md")
    result = classify_document(card)
    assert result["pair_type"] == PROBLEM_SOLUTION_PAIR_TYPE
    assert result["role"] == "problem"


def test_classify_document_recognizes_a_solutions_suffix():
    card = _card("academic_notes/microecon/problem_sets/homework_4_solutions.md")
    result = classify_document(card)
    assert result["role"] == "solution"
    assert result["group_key"] == classify_document(
        _card("academic_notes/microecon/problem_sets/processed_outputs/Homework_4.md")
    )["group_key"]


def test_classify_document_recognizes_a_guided_solutions_variant_in_the_same_group():
    base = classify_document(_card("academic_notes/microecon/problem_sets/processed_outputs/Homework_4.md"))
    guided = classify_document(_card("academic_notes/microecon/problem_sets/homework_4_guided_solutions.md"))
    assert guided["role"] == "solution"
    assert guided["group_key"] == base["group_key"]


def test_classify_document_recognizes_an_abbreviated_hw_solution():
    # Real pattern: academic_notes/microecon/2025_class/Homeworks/Solutions/HW4_Sol.md
    # pairs with .../Homeworks/Homework_4.md -- different directory, same number.
    base = classify_document(_card("academic_notes/microecon/2025_class/Homeworks/Homework_4.md"))
    sol = classify_document(
        _card("academic_notes/microecon/2025_class/Homeworks/Solutions/processed_outputs/HW4_Sol.md")
    )
    assert sol["role"] == "solution"
    assert sol["group_key"] == base["group_key"]


def test_classify_document_recognizes_a_solution_prefixed_pset():
    # Real pattern: academic_notes/econometrics/problem_sets/processed_outputs/pset3.md
    # pairs with .../solution-pset3.md -- marker is a prefix, not a suffix.
    base = classify_document(_card("academic_notes/econometrics/problem_sets/processed_outputs/pset3.md",
                                    course="econometrics"))
    sol = classify_document(_card("academic_notes/econometrics/problem_sets/processed_outputs/solution-pset3.md",
                                   course="econometrics"))
    assert sol["role"] == "solution"
    assert sol["group_key"] == base["group_key"]


def test_classify_document_recognizes_problem_set_written_as_two_words():
    base = classify_document(_card("academic_notes/econometrics/problem_sets/processed_outputs/problem_set_1.md",
                                    course="econometrics"))
    sol = classify_document(
        _card("academic_notes/econometrics/problem_sets/problem_set_1_solutions.md", course="econometrics")
    )
    assert base["role"] == "problem"
    assert sol["role"] == "solution"
    assert base["group_key"] == sol["group_key"]


def test_classify_document_treats_an_extra_unknown_token_on_a_solution_as_still_a_solution():
    # Real file: problem_set_1_gemini_solutions.md -- "gemini" is leftover
    # but the explicit "solutions" marker is decisive on its own.
    result = classify_document(
        _card("academic_notes/econometrics/problem_sets/problem_set_1_gemini_solutions.md", course="econometrics")
    )
    assert result["role"] == "solution"


def test_classify_document_excludes_an_auxiliary_hints_document():
    # Real file: homework_4_hints.md -- same number as homework_4 but
    # neither a problem statement nor a solution.
    assert classify_document(_card("academic_notes/microecon/problem_sets/homework_4_hints.md")) is None


def test_classify_document_excludes_an_auxiliary_tutoring_audit_document():
    assert classify_document(_card("academic_notes/microecon/problem_sets/homework_3_tutoring_audit.md")) is None


def test_classify_document_returns_none_without_a_number():
    assert classify_document(_card("academic_notes/microecon/problem_sets/processed_outputs/Practice Sheet.md")) \
        is None


def test_classify_document_returns_none_for_an_unrelated_file():
    assert classify_document(_card("academic_notes/microecon/textbooks/processed_outputs/Press_2011.md")) is None


def test_classify_document_does_not_treat_ta_notes_as_lecture_family():
    # "notes" alone must never trigger lecture-family membership --
    # real folders like ta_notes/ are extremely common and unrelated.
    assert classify_document(_card("academic_notes/econometrics/ta_notes/notes_3.md")) is None


def test_classify_document_recognizes_lecture_slides_and_notes_roles():
    slides = classify_document(_card("academic_notes/econometrics/lecture_notes/lecture_12_slides.md",
                                      course="econometrics"))
    notes = classify_document(_card("academic_notes/econometrics/lecture_notes/lecture_12_notes.md",
                                     course="econometrics"))
    assert slides["pair_type"] == LECTURE_SLIDES_NOTES_PAIR_TYPE
    assert slides["role"] == "slides"
    assert notes["role"] == "notes"
    assert slides["group_key"] == notes["group_key"]


def test_classify_document_returns_none_for_a_lecture_number_with_no_slides_or_notes_marker():
    assert classify_document(_card("academic_notes/econometrics/lecture_notes/lecture_12.md",
                                    course="econometrics")) is None


def test_classify_document_separates_different_offering_years_into_different_groups():
    y2024 = classify_document(_card("academic_notes/microecon/2024_class/Homeworks/Homework_4.md"))
    y2025 = classify_document(_card("academic_notes/microecon/2025_class/Homeworks/Homework_4.md"))
    assert y2024["group_key"] != y2025["group_key"]


def test_classify_document_treats_class_prefixed_year_the_same_as_suffixed():
    prefixed = classify_document(
        _card("academic_notes/econometrics/class_2024/Problem Sets with Solutions/Solutions-pset1-part1.md",
              course="econometrics")
    )
    suffixed = classify_document(_card("academic_notes/econometrics/2024_class/pset1.md", course="econometrics"))
    assert prefixed["group_key"][:2] == suffixed["group_key"][:2]


# --- find_document_pairs(): grouping + confidence rule. ---


def test_find_document_pairs_single_problem_single_solution_is_auto():
    cards = [
        _card("academic_notes/microecon/problem_sets/processed_outputs/Homework_4.md"),
        _card("academic_notes/microecon/problem_sets/homework_4_solutions.md"),
    ]
    auto, review = find_document_pairs(cards)
    assert len(auto) == 1
    assert review == []
    assert auto[0][2] == PROBLEM_SOLUTION_PAIR_TYPE


def test_find_document_pairs_one_problem_two_solution_variants_are_both_auto():
    # Real pattern: homework_4_solutions.md AND homework_4_guided_solutions.md
    # both legitimately pair with the same Homework_4.md.
    cards = [
        _card("academic_notes/microecon/problem_sets/processed_outputs/Homework_4.md"),
        _card("academic_notes/microecon/problem_sets/homework_4_solutions.md"),
        _card("academic_notes/microecon/problem_sets/homework_4_guided_solutions.md"),
    ]
    auto, review = find_document_pairs(cards)
    assert len(auto) == 2
    assert review == []
    paired_solution_ids = {b["file_id"] for _, b, _ in auto}
    assert paired_solution_ids == {
        "academic_notes/microecon/problem_sets/homework_4_solutions.md",
        "academic_notes/microecon/problem_sets/homework_4_guided_solutions.md",
    }


def test_find_document_pairs_two_candidate_base_documents_is_ambiguous():
    # Two distinct "problem"-shaped docs claiming the same number+offering
    # -- can't tell which one the lone solution belongs to.
    cards = [
        _card("academic_notes/microecon/problem_sets/processed_outputs/Homework_4.md"),
        _card("academic_notes/microecon/problem_sets/processed_outputs/HW_4.md"),
        _card("academic_notes/microecon/problem_sets/homework_4_solutions.md"),
    ]
    auto, review = find_document_pairs(cards)
    assert auto == []
    assert len(review) == 2  # both candidate problem docs paired against the one solution, for a human to pick


def test_find_document_pairs_excludes_an_auxiliary_hints_document_from_pairing():
    cards = [
        _card("academic_notes/microecon/problem_sets/processed_outputs/Homework_4.md"),
        _card("academic_notes/microecon/problem_sets/homework_4_solutions.md"),
        _card("academic_notes/microecon/problem_sets/homework_4_hints.md"),
    ]
    auto, review = find_document_pairs(cards)
    assert len(auto) == 1  # hints never enters a role at all, so it can't be a third pair


def test_find_document_pairs_skips_a_solution_with_no_base_document():
    cards = [_card("academic_notes/microecon/problem_sets/TA_solutions/processed_outputs/Part_I_HW9_Sol.md")]
    auto, review = find_document_pairs(cards)
    assert auto == [] and review == []


def test_find_document_pairs_bijective_slides_notes_is_auto():
    cards = [
        _card("academic_notes/econometrics/lecture_notes/lecture_12_slides.md", course="econometrics"),
        _card("academic_notes/econometrics/lecture_notes/lecture_12_notes.md", course="econometrics"),
    ]
    auto, review = find_document_pairs(cards)
    assert len(auto) == 1
    assert auto[0][2] == LECTURE_SLIDES_NOTES_PAIR_TYPE


def test_find_document_pairs_multiple_slides_candidates_is_ambiguous():
    cards = [
        _card("academic_notes/econometrics/lecture_notes/lecture_12_slides.md", course="econometrics"),
        _card("academic_notes/econometrics/lecture_notes/lecture_12_slides_v2.md", course="econometrics"),
        _card("academic_notes/econometrics/lecture_notes/lecture_12_notes.md", course="econometrics"),
    ]
    auto, review = find_document_pairs(cards)
    assert auto == []
    assert len(review) == 2


def test_find_document_pairs_never_crosses_offering_years():
    cards = [
        _card("academic_notes/microecon/2024_class/Homeworks/Homework_4.md"),
        _card("academic_notes/microecon/2024_class/Homeworks/Solutions/HW4_sols_final.md"),
        _card("academic_notes/microecon/2025_class/Homeworks/Homework_4.md"),
        _card("academic_notes/microecon/2025_class/Homeworks/Solutions/HW4_Sol.md"),
    ]
    auto, review = find_document_pairs(cards)
    assert len(auto) == 2
    assert review == []
    for card_a, card_b, _ in auto:
        assert ("2024_class" in card_a["path"]) == ("2024_class" in card_b["path"])


def test_find_document_pairs_returns_empty_for_cards_with_no_pairing_signal():
    cards = [_card("academic_notes/microecon/textbooks/processed_outputs/Press_2011.md")]
    auto, review = find_document_pairs(cards)
    assert auto == [] and review == []


# --- Ledger round trips (mirrors offering_links.py's own ledger tests --
# this module's ledger is deliberately a separate file under a separate
# .index/document_pairs/ directory, never offering_links'). ---


def test_load_dismissals_returns_empty_list_when_missing():
    with tempfile.TemporaryDirectory() as tmp:
        assert load_dismissals(tmp) == []


def test_record_dismissal_round_trips():
    with tempfile.TemporaryDirectory() as tmp:
        record_dismissal(tmp, "fid1", "fid2")
        dismissals = load_dismissals(tmp)
        assert is_dismissed(dismissals, "fid1", "fid2")
        assert is_dismissed(dismissals, "fid2", "fid1")


def test_record_dismissal_is_a_no_op_if_already_recorded():
    with tempfile.TemporaryDirectory() as tmp:
        record_dismissal(tmp, "fid1", "fid2")
        record_dismissal(tmp, "fid2", "fid1")
        assert len(load_dismissals(tmp)) == 1


def test_dismissals_file_lives_under_its_own_document_pairs_directory():
    with tempfile.TemporaryDirectory() as tmp:
        record_dismissal(tmp, "fid1", "fid2")
        assert os.path.isfile(os.path.join(tmp, ".index", "document_pairs", "dismissals.json"))
        assert not os.path.isfile(os.path.join(tmp, ".index", "offering_links", "dismissals.json"))


def test_review_round_trips():
    with tempfile.TemporaryDirectory() as tmp:
        save_review(tmp, [{"file_id_a": "a", "file_id_b": "b", "pair_type": PROBLEM_SOLUTION_PAIR_TYPE,
                            "course": "microecon"}])
        assert load_review(tmp) == [{"file_id_a": "a", "file_id_b": "b", "pair_type": PROBLEM_SOLUTION_PAIR_TYPE,
                                      "course": "microecon"}]


def test_load_review_returns_empty_list_when_missing():
    with tempfile.TemporaryDirectory() as tmp:
        assert load_review(tmp) == []


def test_load_dismissals_warns_and_treats_malformed_file_as_empty(capsys):
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, ".index", "document_pairs", "dismissals.json")
        os.makedirs(os.path.dirname(path))
        with open(path, "w") as f:
            f.write("{not valid json")
        assert load_dismissals(tmp) == []
        assert "WARNING" in capsys.readouterr().out


# --- write_pairs() / run_for_course() / resolve_pending() / reject_pending(): end to end. ---


def _seed_course(tmp_path, course, cards):
    from core.indexer.index_card import save_shard
    note_dir = tmp_path / "academic_notes" / course
    note_dir.mkdir(parents=True, exist_ok=True)
    save_shard(str(tmp_path), course, cards)


def test_write_pairs_updates_paired_with_on_both_cards(tmp_path):
    from core.indexer.document_pairing import write_pairs
    from core.indexer.index_card import load_shard, save_shard

    card_a = {"file_id": "fa", "path": "academic_notes/microecon/problem_sets/processed_outputs/Homework_4.md",
              "title": "Homework 4"}
    card_b = {"file_id": "fb", "path": "academic_notes/microecon/problem_sets/homework_4_solutions.md",
              "title": "Homework 4 Solutions"}
    save_shard(str(tmp_path), "microecon", [card_a, card_b])

    stats = write_pairs(str(tmp_path), "microecon", [(card_a, card_b, PROBLEM_SOLUTION_PAIR_TYPE)],
                         confidence="high")

    cards = {c["file_id"]: c for c in load_shard(str(tmp_path), "microecon")}
    assert cards["fa"]["paired_with"] == [
        {"file_id": "fb", "path": card_b["path"], "pair_type": PROBLEM_SOLUTION_PAIR_TYPE, "confidence": "high"}
    ]
    assert cards["fb"]["paired_with"] == [
        {"file_id": "fa", "path": card_a["path"], "pair_type": PROBLEM_SOLUTION_PAIR_TYPE, "confidence": "high"}
    ]
    assert stats["links_written"] == 1


def test_write_pairs_preserves_an_existing_entry_for_a_different_counterpart(tmp_path):
    from core.indexer.document_pairing import write_pairs
    from core.indexer.index_card import load_shard, save_shard

    card_a = {"file_id": "fa", "path": "academic_notes/microecon/problem_sets/processed_outputs/Homework_4.md"}
    card_b = {"file_id": "fb", "path": "academic_notes/microecon/problem_sets/homework_4_solutions.md"}
    card_c = {"file_id": "fc", "path": "academic_notes/microecon/problem_sets/homework_4_guided_solutions.md"}
    save_shard(str(tmp_path), "microecon", [card_a, card_b, card_c])

    write_pairs(str(tmp_path), "microecon", [(card_a, card_b, PROBLEM_SOLUTION_PAIR_TYPE)], confidence="high")
    write_pairs(str(tmp_path), "microecon", [(card_a, card_c, PROBLEM_SOLUTION_PAIR_TYPE)], confidence="high")

    cards = {c["file_id"]: c for c in load_shard(str(tmp_path), "microecon")}
    linked_ids = {e["file_id"] for e in cards["fa"]["paired_with"]}
    assert linked_ids == {"fb", "fc"}


def test_run_for_course_writes_an_auto_pair_end_to_end(tmp_path):
    from core.indexer.index_card import load_shard
    card_a = {"file_id": "fa", "path": "academic_notes/microecon/problem_sets/processed_outputs/Homework_4.md",
              "title": "Homework 4", "course": "microecon"}
    card_b = {"file_id": "fb", "path": "academic_notes/microecon/problem_sets/homework_4_solutions.md",
              "title": "Homework 4 Solutions", "course": "microecon"}
    _seed_course(tmp_path, "microecon", [card_a, card_b])

    from core.indexer.document_pairing import run_for_course
    stats = run_for_course(str(tmp_path), "microecon")

    cards = {c["file_id"]: c for c in load_shard(str(tmp_path), "microecon")}
    assert cards["fa"]["paired_with"][0]["file_id"] == "fb"
    assert cards["fb"]["paired_with"][0]["file_id"] == "fa"
    assert stats["auto_matches"] == 1
    assert stats["review_matches"] == 0


def test_run_for_course_dry_run_writes_nothing(tmp_path):
    from core.indexer.index_card import load_shard
    card_a = {"file_id": "fa", "path": "academic_notes/microecon/problem_sets/processed_outputs/Homework_4.md",
              "course": "microecon"}
    card_b = {"file_id": "fb", "path": "academic_notes/microecon/problem_sets/homework_4_solutions.md",
              "course": "microecon"}
    _seed_course(tmp_path, "microecon", [card_a, card_b])

    from core.indexer.document_pairing import run_for_course
    stats = run_for_course(str(tmp_path), "microecon", dry_run=True)

    cards = {c["file_id"]: c for c in load_shard(str(tmp_path), "microecon")}
    assert "paired_with" not in cards["fa"]
    assert stats["auto_matches"] == 1


def test_run_for_course_logs_a_review_pair_instead_of_writing_it(tmp_path):
    from core.indexer.document_pairing import load_review, run_for_course
    from core.indexer.index_card import load_shard
    card_a = {"file_id": "fa", "path": "academic_notes/microecon/problem_sets/processed_outputs/Homework_4.md",
              "course": "microecon"}
    card_b = {"file_id": "fb", "path": "academic_notes/microecon/problem_sets/processed_outputs/HW_4.md",
              "course": "microecon"}
    card_c = {"file_id": "fc", "path": "academic_notes/microecon/problem_sets/homework_4_solutions.md",
              "course": "microecon"}
    _seed_course(tmp_path, "microecon", [card_a, card_b, card_c])

    stats = run_for_course(str(tmp_path), "microecon")

    assert stats["auto_matches"] == 0
    assert stats["review_matches"] == 2
    assert len(load_review(str(tmp_path))) == 2
    cards = {c["file_id"]: c for c in load_shard(str(tmp_path), "microecon")}
    assert "paired_with" not in cards["fa"]


def test_run_for_course_skips_a_dismissed_pair(tmp_path):
    from core.indexer.document_pairing import record_dismissal, run_for_course
    card_a = {"file_id": "fa", "path": "academic_notes/microecon/problem_sets/processed_outputs/Homework_4.md",
              "course": "microecon"}
    card_b = {"file_id": "fb", "path": "academic_notes/microecon/problem_sets/homework_4_solutions.md",
              "course": "microecon"}
    _seed_course(tmp_path, "microecon", [card_a, card_b])
    record_dismissal(str(tmp_path), "fa", "fb")

    stats = run_for_course(str(tmp_path), "microecon")

    assert stats["auto_matches"] == 0
    from core.indexer.index_card import load_shard
    cards = {c["file_id"]: c for c in load_shard(str(tmp_path), "microecon")}
    assert "paired_with" not in cards["fa"]


def test_run_for_course_is_idempotent_on_rerun_after_auto_linking(tmp_path):
    from core.indexer.document_pairing import run_for_course
    card_a = {"file_id": "fa", "path": "academic_notes/microecon/problem_sets/processed_outputs/Homework_4.md",
              "course": "microecon"}
    card_b = {"file_id": "fb", "path": "academic_notes/microecon/problem_sets/homework_4_solutions.md",
              "course": "microecon"}
    _seed_course(tmp_path, "microecon", [card_a, card_b])

    first = run_for_course(str(tmp_path), "microecon")
    second = run_for_course(str(tmp_path), "microecon")

    assert first["auto_matches"] == 1
    assert second["auto_matches"] == 0


def test_resolve_pending_promotes_a_review_pair_to_a_written_link(tmp_path):
    from core.indexer.document_pairing import load_review, resolve_pending, run_for_course
    from core.indexer.index_card import load_shard
    card_a = {"file_id": "fa", "path": "academic_notes/microecon/problem_sets/processed_outputs/Homework_4.md",
              "course": "microecon"}
    card_b = {"file_id": "fb", "path": "academic_notes/microecon/problem_sets/processed_outputs/HW_4.md",
              "course": "microecon"}
    card_c = {"file_id": "fc", "path": "academic_notes/microecon/problem_sets/homework_4_solutions.md",
              "course": "microecon"}
    _seed_course(tmp_path, "microecon", [card_a, card_b, card_c])
    run_for_course(str(tmp_path), "microecon")  # produces two pending review entries (fa-fc, fb-fc)

    resolved = resolve_pending(str(tmp_path), "fa", "fc")

    assert resolved is True
    remaining_review = load_review(str(tmp_path))
    assert len(remaining_review) == 1  # the fb-fc candidate is still pending
    cards = {c["file_id"]: c for c in load_shard(str(tmp_path), "microecon")}
    assert cards["fa"]["paired_with"][0]["file_id"] == "fc"
    assert cards["fa"]["paired_with"][0]["confidence"] == "high"


def test_resolve_pending_returns_false_when_pair_not_in_review(tmp_path):
    from core.indexer.document_pairing import resolve_pending
    assert resolve_pending(str(tmp_path), "nope", "nothing") is False


def test_reject_pending_dismisses_and_clears_the_pending_entry(tmp_path):
    from core.indexer.document_pairing import is_dismissed, load_dismissals, load_review, reject_pending, \
        run_for_course
    card_a = {"file_id": "fa", "path": "academic_notes/microecon/problem_sets/processed_outputs/Homework_4.md",
              "course": "microecon"}
    card_b = {"file_id": "fb", "path": "academic_notes/microecon/problem_sets/processed_outputs/HW_4.md",
              "course": "microecon"}
    card_c = {"file_id": "fc", "path": "academic_notes/microecon/problem_sets/homework_4_solutions.md",
              "course": "microecon"}
    _seed_course(tmp_path, "microecon", [card_a, card_b, card_c])
    run_for_course(str(tmp_path), "microecon")

    rejected = reject_pending(str(tmp_path), "fa", "fc")

    assert rejected is True
    assert len(load_review(str(tmp_path))) == 1
    assert is_dismissed(load_dismissals(str(tmp_path)), "fa", "fc")


def test_reject_pending_removes_an_existing_auto_linked_pair(tmp_path):
    from core.indexer.document_pairing import is_dismissed, load_dismissals, reject_pending, run_for_course
    from core.indexer.index_card import load_shard
    card_a = {"file_id": "fa", "path": "academic_notes/microecon/problem_sets/processed_outputs/Homework_4.md",
              "course": "microecon"}
    card_b = {"file_id": "fb", "path": "academic_notes/microecon/problem_sets/homework_4_solutions.md",
              "course": "microecon"}
    _seed_course(tmp_path, "microecon", [card_a, card_b])
    run_for_course(str(tmp_path), "microecon")  # auto-links fa <-> fb

    rejected = reject_pending(str(tmp_path), "fa", "fb")

    cards = {c["file_id"]: c for c in load_shard(str(tmp_path), "microecon")}
    assert rejected is True
    assert cards["fa"].get("paired_with") == []
    assert cards["fb"].get("paired_with") == []
    assert is_dismissed(load_dismissals(str(tmp_path)), "fa", "fb")


def test_academic_hub_dir_resolves_to_the_real_sibling_directory():
    from core.indexer.document_pairing import _academic_hub_dir
    resolved = _academic_hub_dir()
    assert resolved.name == "academic-hub"
    assert resolved.parent.name == "ai-sandbox"
    assert os.path.isdir(resolved)
