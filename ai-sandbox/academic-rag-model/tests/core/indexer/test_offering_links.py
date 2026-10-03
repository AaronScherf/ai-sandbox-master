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
