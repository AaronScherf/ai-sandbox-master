import os

from core.indexer.related import (
    containment,
    handwriting_text,
    lecture_date,
    raw_transcript_path,
    read_raw,
)

HW = (
    "preference relation complete transitive define strict preference asymmetric "
    "indifference symmetric choice set nonempty by completeness utility function "
    "represents preferences ordinal"
)
HW_OTHER = (
    "consumer demand slutsky equation income substitution effect compensated hicksian "
    "marshallian expenditure minimization duality"
)


def test_raw_transcript_path_drops_the_rag_infix():
    assert raw_transcript_path("a/processed_outputs/X 2026-09-15.excalidraw.rag.md") == (
        "a/processed_outputs/X 2026-09-15.excalidraw.md"
    )


def test_raw_transcript_path_is_none_for_other_cards():
    assert raw_transcript_path("a/textbook.md") is None


def test_lecture_date_reads_first_iso_date_from_basename():
    assert lecture_date("a/b/Microeconomics with slides 2026-09-15 10.15.55.excalidraw.rag.md") == "2026-09-15"
    assert lecture_date("a/2026-01-01/Microeconomics.excalidraw.rag.md") is None


def test_handwriting_text_slides_note_keeps_only_handwritten_blocks():
    body = (
        "<!-- chunk 1 -->\n\n**[Slide]**\nslide words here\n\n**[Handwritten]**\n"
        f"{HW}\n\n<!-- chunk 2 -->\n\n**[Slide]**\nmore slide words\n"
    )
    text = handwriting_text({"embedded_slides": "true"}, body)
    assert "preference relation" in text
    assert "slide words" not in text
    assert "chunk" not in text


def test_handwriting_text_plain_note_is_whole_body_without_chunk_markers():
    text = handwriting_text({}, f"<!-- chunk 1 -->\n\n{HW}\n")
    assert "preference relation" in text
    assert "chunk" not in text


def test_containment_identical_is_one_and_disjoint_is_zero():
    assert containment(HW, HW) == 1.0
    assert containment(HW, HW_OTHER) == 0.0


def test_containment_is_asymmetric_subset_in_superset():
    assert containment(HW, HW + " " + HW_OTHER) == 1.0
    assert containment(HW + " " + HW_OTHER, HW) < 0.6


def test_containment_of_text_with_no_ngrams_is_zero():
    assert containment("", HW) == 0.0
    assert containment("two words", HW) == 0.0


def test_read_raw_returns_frontmatter_and_body_or_none(tmp_path):
    out = tmp_path / "academic_notes" / "c" / "lecture_notes" / "processed_outputs"
    out.mkdir(parents=True)
    (out / "N 2026-09-15.excalidraw.md").write_text("---\nchunks: 2\nembedded_slides: true\n---\n\nBODY", encoding="utf-8")
    card = {"path": "academic_notes/c/lecture_notes/processed_outputs/N 2026-09-15.excalidraw.rag.md"}
    meta, body = read_raw(str(tmp_path), card)
    assert meta["embedded_slides"] == "true" and body == "BODY"
    assert read_raw(str(tmp_path), {"path": "academic_notes/c/lecture_notes/processed_outputs/Gone.excalidraw.rag.md"}) is None
    assert read_raw(str(tmp_path), {"path": "x.md"}) is None


import json
from unittest.mock import patch

import core.indexer.related as related
from core.indexer.index_card import load_shard, save_shard
from core.indexer.related import link_subsets, load_overrides, overrides_path

SLIDE_FILLER = "**[Slide]**\nbudget set indifference curve slide text about consumer choice\n\n"


def _note(hub, basename, *, slides, handwriting, file_id, course="microecon",
          category="lecture_notes", write_raw=True):
    out = os.path.join(hub, "academic_notes", course, category, "processed_outputs")
    os.makedirs(out, exist_ok=True)
    if write_raw:
        front = "---\nchunks: 1\n" + ("embedded_slides: true\n" if slides else "") + "---\n\n"
        body = (SLIDE_FILLER + "**[Handwritten]**\n" + handwriting + "\n\n" + SLIDE_FILLER) if slides else handwriting
        with open(os.path.join(out, f"{basename}.excalidraw.md"), "w", encoding="utf-8") as f:
            f.write(front + body)
    return {
        "file_id": file_id, "doc_type": "excalidraw_notes", "course": course,
        "path": f"academic_notes/{course}/{category}/processed_outputs/{basename}.excalidraw.rag.md",
        "embedding": [1.0, 0.0], "needs_indexing": False,
    }


def _pair(tmp_path, hw_sub=HW, hw_sup=HW):
    hub = str(tmp_path)
    sub = _note(hub, "Micro 2026-09-15 10.15.55", slides=False, handwriting=hw_sub, file_id="sub")
    sup = _note(hub, "Micro with slides 2026-09-15 10.15.55", slides=True, handwriting=hw_sup, file_id="sup")
    save_shard(hub, "microecon", [sub, sup])
    return hub


def test_links_a_true_pair_and_leaves_the_superset_untouched(tmp_path):
    hub = _pair(tmp_path)
    links = link_subsets(hub, "microecon")
    assert [(l.subset_id, l.superset_id) for l in links] == [("sub", "sup")]
    cards = {c["file_id"]: c for c in load_shard(hub, "microecon")}
    assert cards["sub"]["subset_of"] == "sup"
    assert cards["sub"]["subset_link_score"] == 1.0
    assert "subset_of" not in cards["sup"]


def test_second_run_is_idempotent_and_does_not_rewrite_the_shard(tmp_path):
    hub = _pair(tmp_path)
    link_subsets(hub, "microecon")
    with patch.object(related, "save_shard") as mock_save:
        links = link_subsets(hub, "microecon")
    assert len(links) == 1
    mock_save.assert_not_called()


def test_same_day_different_content_does_not_link(tmp_path):
    # lecture vs recitation on the same date: same-date candidates, different ink
    hub = _pair(tmp_path, hw_sub=HW_OTHER, hw_sup=HW)
    assert link_subsets(hub, "microecon") == []
    assert "subset_of" not in load_shard(hub, "microecon")[0]


def test_different_date_does_not_link(tmp_path):
    hub = str(tmp_path)
    sub = _note(hub, "Micro 2026-09-10 10.00.00", slides=False, handwriting=HW, file_id="sub")
    sup = _note(hub, "Micro with slides 2026-09-15 10.15.55", slides=True, handwriting=HW, file_id="sup")
    save_shard(hub, "microecon", [sub, sup])
    assert link_subsets(hub, "microecon") == []


def test_filename_without_a_date_does_not_link(tmp_path):
    hub = str(tmp_path)
    sub = _note(hub, "Micro notes", slides=False, handwriting=HW, file_id="sub")
    sup = _note(hub, "Micro with slides notes", slides=True, handwriting=HW, file_id="sup")
    save_shard(hub, "microecon", [sub, sup])
    assert link_subsets(hub, "microecon") == []


def test_different_folder_does_not_link(tmp_path):
    hub = str(tmp_path)
    sub = _note(hub, "Micro 2026-09-15", slides=False, handwriting=HW, file_id="sub", category="lecture_notes")
    sup = _note(hub, "Micro with slides 2026-09-15", slides=True, handwriting=HW, file_id="sup", category="recitation")
    save_shard(hub, "microecon", [sub, sup])
    assert link_subsets(hub, "microecon") == []


def test_two_plain_notes_or_two_slides_notes_never_link(tmp_path):
    hub = str(tmp_path)
    a = _note(hub, "A 2026-09-15 1", slides=False, handwriting=HW, file_id="a")
    b = _note(hub, "B 2026-09-15 2", slides=False, handwriting=HW, file_id="b")
    c = _note(hub, "C with slides 2026-09-15 3", slides=True, handwriting=HW, file_id="c")
    d = _note(hub, "D with slides 2026-09-15 4", slides=True, handwriting=HW, file_id="d")
    save_shard(hub, "microecon", [a, b])
    assert link_subsets(hub, "microecon") == []
    save_shard(hub, "microecon", [c, d])
    assert link_subsets(hub, "microecon") == []


def test_missing_raw_transcript_excludes_the_card_without_crashing(tmp_path):
    hub = str(tmp_path)
    sub = _note(hub, "Drawing 2026-09-15", slides=False, handwriting=HW, file_id="sub", write_raw=False)
    sup = _note(hub, "Micro with slides 2026-09-15", slides=True, handwriting=HW, file_id="sup")
    save_shard(hub, "microecon", [sub, sup])
    assert link_subsets(hub, "microecon") == []


def test_threshold_is_enforced(tmp_path):
    hub = _pair(tmp_path)
    with patch.object(related, "CONTAINMENT_THRESHOLD", 1.1):
        assert link_subsets(hub, "microecon") == []


def test_best_scoring_superset_wins(tmp_path):
    hub = str(tmp_path)
    sub = _note(hub, "Micro 2026-09-15", slides=False, handwriting=HW, file_id="sub")
    weak = _note(hub, "Weak with slides 2026-09-15", slides=True, handwriting=HW[: len(HW) // 2] + " " + HW_OTHER, file_id="weak")
    strong = _note(hub, "Strong with slides 2026-09-15", slides=True, handwriting=HW, file_id="strong")
    save_shard(hub, "microecon", [sub, weak, strong])
    links = link_subsets(hub, "microecon")
    assert [(l.subset_id, l.superset_id) for l in links] == [("sub", "strong")]


def test_block_override_prevents_a_link(tmp_path):
    hub = _pair(tmp_path)
    os.makedirs(os.path.dirname(overrides_path(hub)))
    with open(overrides_path(hub), "w", encoding="utf-8") as f:
        json.dump({"block": ["sub"]}, f)
    assert link_subsets(hub, "microecon") == []


def test_force_override_links_regardless_of_content(tmp_path):
    hub = _pair(tmp_path, hw_sub=HW_OTHER, hw_sup=HW)
    os.makedirs(os.path.dirname(overrides_path(hub)))
    with open(overrides_path(hub), "w", encoding="utf-8") as f:
        json.dump({"force": [{"subset": "sub", "superset": "sup"}]}, f)
    links = link_subsets(hub, "microecon")
    assert [(l.subset_id, l.superset_id, l.forced) for l in links] == [("sub", "sup", True)]
    assert load_shard(hub, "microecon")[0]["subset_of"] == "sup"


def test_force_to_a_missing_card_or_onto_itself_is_ignored(tmp_path):
    hub = _pair(tmp_path, hw_sub=HW_OTHER, hw_sup=HW)
    os.makedirs(os.path.dirname(overrides_path(hub)))
    with open(overrides_path(hub), "w", encoding="utf-8") as f:
        json.dump({"force": [{"subset": "sub", "superset": "nope"}, {"subset": "sup", "superset": "sup"}]}, f)
    assert link_subsets(hub, "microecon") == []


def test_forced_chain_is_dropped_so_links_stay_one_level(tmp_path):
    hub = _pair(tmp_path)
    cards = load_shard(hub, "microecon")
    cards.append(_note(hub, "Third 2026-09-15", slides=False, handwriting=HW, file_id="third"))
    save_shard(hub, "microecon", cards)
    os.makedirs(os.path.dirname(overrides_path(hub)))
    with open(overrides_path(hub), "w", encoding="utf-8") as f:
        json.dump({"force": [{"subset": "third", "superset": "sub"}]}, f)
    ids = {(l.subset_id, l.superset_id) for l in link_subsets(hub, "microecon")}
    assert ("third", "sub") not in ids  # sub is itself a subset


def test_stale_link_is_cleared_when_the_superset_disappears(tmp_path):
    hub = _pair(tmp_path)
    link_subsets(hub, "microecon")
    save_shard(hub, "microecon", [c for c in load_shard(hub, "microecon") if c["file_id"] != "sup"])
    assert link_subsets(hub, "microecon") == []
    sub = load_shard(hub, "microecon")[0]
    assert "subset_of" not in sub and "subset_link_score" not in sub


def test_dry_run_computes_but_writes_nothing(tmp_path):
    hub = _pair(tmp_path)
    with patch.object(related, "save_shard") as mock_save:
        links = link_subsets(hub, "microecon", dry_run=True)
    assert len(links) == 1
    mock_save.assert_not_called()
    assert "subset_of" not in load_shard(hub, "microecon")[0]


def test_load_overrides_defaults_when_file_missing(tmp_path):
    assert load_overrides(str(tmp_path)) == {"force": [], "block": []}


def test_cli_dry_run_prints_links(tmp_path, capsys):
    hub = _pair(tmp_path)
    related.main(["--root", hub, "--course", "microecon", "--dry-run"])
    out = capsys.readouterr().out
    assert "sub" in out and "sup" in out and "1.00" in out
    assert "subset_of" not in load_shard(hub, "microecon")[0]
