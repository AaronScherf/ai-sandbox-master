import shutil
import tempfile
from pathlib import Path

import pytest

from agent.literature.profile import folders, review
from core.indexer.index_card import find_card_by_file_id, load_shard, save_shard
from core.indexer.research_profile import set_research_profile

ECON = "Economics, Econometrics and Finance"


def _paper(root: Path, folder: str, name: str, fid: str, discipline: str | None, report_type="journal_article"):
    pdf = root / "journal-articles" / folder / f"{name}.pdf"
    md = root / "journal-articles" / folder / "processed_outputs" / f"{name}.md"
    meta = root / "journal-articles" / folder / f"{name}.meta.json"
    md.parent.mkdir(parents=True, exist_ok=True)
    pdf.write_bytes(b"%PDF " + name.encode())
    md.write_text(f"transcript {name}", encoding="utf-8")
    meta.write_text("{}", encoding="utf-8")
    card = {"file_id": fid, "course": folder, "title": name, "doc_type": "journal_article",
            "path": f"journal-articles/{folder}/processed_outputs/{name}.md",
            "source_pdf_path": f"journal-articles/{folder}/{name}.pdf"}
    shard = load_shard(str(root), folder) + [card]
    save_shard(str(root), folder, shard)
    if discipline:
        set_research_profile(str(root), fid, {"discipline": discipline, "report_type": report_type})
    return fid


def _setup(extra=()):
    tmp = tempfile.TemporaryDirectory()
    root = Path(tmp.name)
    for n, fid in enumerate(("a1", "a2", "a3")):
        _paper(root, "business", f"econ{n}", fid, ECON)
    _paper(root, "business", "lonely", "m1", "Medicine")
    for args in extra:
        _paper(root, *args)
    return tmp, root


def _cards(root):
    return [c for fid in ("a1", "a2", "a3", "m1") if (c := (find_card_by_file_id(str(root), fid) or (None, None))[1])]


def _plan(root, **kw):
    cards = [c for course in ("business", "economics-econometrics-and-finance", "other")
             for c in load_shard(str(root), course)]
    return folders.plan_moves(cards, str(root), **kw)


def test_small_discipline_goes_to_other_and_large_gets_its_own_folder():
    tmp, root = _setup()
    with tmp:
        moves = {m.file_id: m for m in _plan(root)}
        assert moves["a1"].to_folder == "economics-econometrics-and-finance"
        assert moves["m1"].to_folder == "other" and "1 paper" in moves["m1"].reason


def test_min_papers_is_configurable():
    tmp, root = _setup()
    with tmp:
        moves = {m.file_id: m for m in _plan(root, min_papers=1)}
        assert moves["m1"].to_folder == "medicine"


def test_plan_has_no_move_for_unchanged_or_unclassified_papers():
    tmp, root = _setup(extra=[("business", "raw", "u1", None)])
    with tmp:
        assert "u1" not in {m.file_id for m in _plan(root)}
        folders.apply_moves(str(root), _plan(root), {m.file_id for m in _plan(root)})
        assert _plan(root) == []


def test_human_decision_overrides_the_model_discipline_in_the_plan():
    tmp, root = _setup()
    with tmp:
        review.record_decision(str(root), "m1", "discipline", ECON, "owner")
        assert {m.file_id: m.to_folder for m in _plan(root)}["m1"] == "economics-econometrics-and-finance"


def test_non_research_documents_go_to_other():
    tmp, root = _setup(extra=[("business", "essay", "e1", "Medicine", "notes")])
    with tmp:
        assert {m.file_id: m.to_folder for m in _plan(root)}["e1"] == "other"


def test_apply_moves_card_transcript_pdf_and_sidecar_together():
    tmp, root = _setup()
    with tmp:
        log = folders.apply_moves(str(root), _plan(root), {"a1"})
        base = root / "journal-articles" / "economics-econometrics-and-finance"
        assert (base / "econ0.pdf").exists() and (base / "econ0.meta.json").exists()
        assert (base / "processed_outputs" / "econ0.md").read_text(encoding="utf-8") == "transcript econ0"
        assert not (root / "journal-articles" / "business" / "econ0.pdf").exists()
        card = find_card_by_file_id(str(root), "a1")[1]
        assert card["course"] == "economics-econometrics-and-finance"
        assert card["path"] == "journal-articles/economics-econometrics-and-finance/processed_outputs/econ0.md"
        assert (root / card["source_pdf_path"]).exists()
        assert [e["file_id"] for e in log] == ["a1"]


def test_file_id_unchanged_after_move():
    tmp, root = _setup()
    with tmp:
        folders.apply_moves(str(root), _plan(root), {"a1"})
        assert find_card_by_file_id(str(root), "a1")[1]["file_id"] == "a1"


def test_apply_skips_unapproved():
    tmp, root = _setup()
    with tmp:
        folders.apply_moves(str(root), _plan(root), {"a1"})
        assert (root / "journal-articles" / "business" / "econ1.pdf").exists()
        assert find_card_by_file_id(str(root), "a2")[1]["course"] == "business"


def test_filename_collision_refused_and_nothing_moved():
    tmp, root = _setup()
    with tmp:
        blocker = root / "journal-articles" / "economics-econometrics-and-finance"
        blocker.mkdir(parents=True)
        (blocker / "econ0.pdf").write_bytes(b"someone else")
        with pytest.raises(ValueError, match="econ0.pdf"):
            folders.apply_moves(str(root), _plan(root), {"a1", "a2"})
        assert (root / "journal-articles" / "business" / "econ1.pdf").exists()
        assert find_card_by_file_id(str(root), "a2")[1]["course"] == "business"


def test_interrupted_apply_is_resumable_and_idempotent(monkeypatch):
    tmp, root = _setup()
    with tmp:
        real_move, calls = shutil.move, {"n": 0}

        def flaky(src, dst):
            calls["n"] += 1
            if calls["n"] == 2:
                raise OSError("interrupted")
            return real_move(src, dst)

        monkeypatch.setattr(folders.shutil, "move", flaky)
        approved = {m.file_id for m in _plan(root)}
        with pytest.raises(OSError):
            folders.apply_moves(str(root), _plan(root), approved)
        monkeypatch.undo()
        folders.apply_moves(str(root), _plan(root), approved)
        assert _plan(root) == []
        for fid in ("a1", "a2", "a3", "m1"):
            card = find_card_by_file_id(str(root), fid)[1]
            assert (root / card["path"]).exists() and (root / card["source_pdf_path"]).exists()
        assert folders.apply_moves(str(root), [], approved) == []


def test_undo_restores_original_layout():
    tmp, root = _setup()
    with tmp:
        log = folders.apply_moves(str(root), _plan(root), {"a1", "m1"})
        folders.undo_moves(str(root), log)
        assert (root / "journal-articles" / "business" / "econ0.pdf").exists()
        assert (root / "journal-articles" / "business" / "processed_outputs" / "lonely.md").exists()
        card = find_card_by_file_id(str(root), "a1")[1]
        assert card["course"] == "business" and card["path"].startswith("journal-articles/business/")


def test_render_plan_page_lists_every_move_with_a_checkbox():
    tmp, root = _setup()
    with tmp:
        page = folders.render_plan_page(_plan(root))
        assert page.count('type="checkbox"') == 4 and "econ0" in page and "other" in page


def _loose(root: Path, name: str, fid: str, discipline: str, subfield: str | None = None):
    """A paper sitting directly in journal-articles/, whose course is its own file name (as in the real index)."""
    pdf = root / "journal-articles" / f"{name}.pdf"
    md = root / "journal-articles" / "processed_outputs" / f"{name}.md"
    md.parent.mkdir(parents=True, exist_ok=True)
    pdf.write_bytes(b"%PDF " + name.encode())
    md.write_text(f"transcript {name}", encoding="utf-8")
    card = {"file_id": fid, "course": f"{name}.pdf", "title": name, "doc_type": "journal_article",
            "path": f"journal-articles/processed_outputs/{name}.md", "source_pdf_path": f"journal-articles/{name}.pdf",
            "source_asset_path": f"journal-articles/{name}.pdf"}
    save_shard(str(root), card["course"], [card])
    fields = {"discipline": discipline, "report_type": "journal_article"}
    if subfield:
        fields["openalex_subfields"] = [{"id": "x", "label": subfield, "source": "openalex", "score": 1.0}]
    set_research_profile(str(root), fid, fields)


def _all_cards(root: Path):
    from core.indexer.index_card import list_courses
    return [c for course in list_courses(str(root)) for c in load_shard(str(root), course)]


SOCIAL = "Social Sciences"


def test_social_sciences_get_one_subfolder_per_subfield_and_other_disciplines_stay_flat():
    tmp = tempfile.TemporaryDirectory()
    root = Path(tmp.name)
    with tmp:
        for n in range(3):
            _loose(root, f"dev{n}", f"d{n}", SOCIAL, "Development")
        _loose(root, "edu", "e1", SOCIAL, "Education")
        _loose(root, "nosub", "n1", SOCIAL)
        for n in range(3):
            _loose(root, f"eco{n}", f"c{n}", ECON, "Economics and Econometrics")
        moves = {m.file_id: m.to_folder for m in folders.plan_moves(_all_cards(root), str(root))}
        assert moves["d0"] == "social-sciences/development" and moves["e1"] == "social-sciences/education"
        assert moves["n1"] == "social-sciences/general"
        assert moves["c0"] == "economics-econometrics-and-finance"


def test_loose_paper_moves_into_a_nested_folder_and_the_card_follows_the_layout_a_reindex_would_derive():
    tmp = tempfile.TemporaryDirectory()
    root = Path(tmp.name)
    with tmp:
        for n in range(3):
            _loose(root, f"dev{n}", f"d{n}", SOCIAL, "Development")
        folders.apply_moves(str(root), folders.plan_moves(_all_cards(root), str(root)), {"d0"})
        base = root / "journal-articles" / "social-sciences" / "development"
        assert (base / "dev0.pdf").exists() and (base / "processed_outputs" / "dev0.md").exists()
        assert not (root / "journal-articles" / "dev0.pdf").exists()
        card = find_card_by_file_id(str(root), "d0")[1]
        assert card["course"] == "social-sciences"
        assert card["path"] == "journal-articles/social-sciences/development/processed_outputs/dev0.md"
        assert card["source_pdf_path"] == "journal-articles/social-sciences/development/dev0.pdf"
        assert card["source_asset_path"] == card["source_pdf_path"]
        assert folders.plan_moves(_all_cards(root), str(root))[0].file_id != "d0"


def test_undo_of_a_nested_move_puts_the_loose_paper_back():
    tmp = tempfile.TemporaryDirectory()
    root = Path(tmp.name)
    with tmp:
        for n in range(3):
            _loose(root, f"dev{n}", f"d{n}", SOCIAL, "Development")
        log = folders.apply_moves(str(root), folders.plan_moves(_all_cards(root), str(root)), {"d0"})
        folders.undo_moves(str(root), log)
        assert (root / "journal-articles" / "dev0.pdf").exists()
        assert (root / "journal-articles" / "processed_outputs" / "dev0.md").exists()
        card = find_card_by_file_id(str(root), "d0")[1]
        assert card["course"] == "dev0.pdf" and card["path"] == "journal-articles/processed_outputs/dev0.md"


def test_a_paper_with_a_project_stays_where_it_is():
    tmp, root = _setup()
    with tmp:
        set_research_profile(str(root), "a1", {"projects": ["nexus-novelty-check"]})
        assert "a1" not in {m.file_id for m in _plan(root)}


def test_transcriber_page_caches_move_with_the_transcript():
    tmp, root = _setup()
    with tmp:
        out = root / "journal-articles" / "business" / "processed_outputs"
        (out / "econ0_pages_cache.json").write_text("{}", encoding="utf-8")
        (out / "econ0_pages_driver.json").write_text("{}", encoding="utf-8")
        folders.apply_moves(str(root), _plan(root), {"a1"})
        new = root / "journal-articles" / "economics-econometrics-and-finance" / "processed_outputs"
        assert (new / "econ0_pages_cache.json").exists() and (new / "econ0_pages_driver.json").exists()
        assert not (out / "econ0_pages_cache.json").exists()


def test_cards_outside_the_articles_folder_are_never_planned():
    tmp, root = _setup(extra=[("business", "essay", "e1", "Medicine", "notes")])
    with tmp:
        cards = [c for course in ("business", "economics-econometrics-and-finance", "other")
                 for c in load_shard(str(root), course)]
        for c in cards:
            if c["file_id"] == "e1":
                c["path"] = "independent-research/notes/processed_outputs/essay.md"
        assert "e1" not in {m.file_id for m in folders.plan_moves(cards, str(root))}


def test_undo_refuses_when_the_original_location_now_holds_another_file():
    tmp, root = _setup()
    with tmp:
        log = folders.apply_moves(str(root), _plan(root), {"a1"})
        newcomer = root / "journal-articles" / "business" / "econ0.pdf"
        newcomer.write_text("a different paper", encoding="utf-8")
        with pytest.raises(ValueError, match="occupied"):
            folders.undo_moves(str(root), log)
        assert newcomer.read_text(encoding="utf-8") == "a different paper"
        assert (root / find_card_by_file_id(str(root), "a1")[1]["source_pdf_path"]).exists()


def test_undo_drops_entries_from_the_log_so_they_cannot_be_replayed():
    tmp, root = _setup()
    with tmp:
        log = folders.apply_moves(str(root), _plan(root), {"a1"})
        folders.undo_moves(str(root), log)
        assert folders._read_log(str(root)) == []
        with pytest.raises(ValueError, match="stale"):
            folders.undo_moves(str(root), log)  # a replay of an already-undone entry is refused


def test_names_that_differ_only_by_case_collide_in_one_batch():
    tmp, root = _setup(extra=[("folderb", "Econ0", "b1", ECON)])
    with tmp:
        cards = [c for course in ("business", "folderb") for c in load_shard(str(root), course)]
        moves = folders.plan_moves(cards, str(root))
        assert {"a1", "b1"} <= {m.file_id for m in moves}
        with pytest.raises(ValueError, match="nothing was moved"):
            folders.apply_moves(str(root), moves, {"a1", "b1"})
        assert (root / "journal-articles" / "business" / "econ0.pdf").exists()


def test_undo_after_an_interrupted_and_resumed_apply_restores_every_file(monkeypatch):
    tmp, root = _setup()
    with tmp:
        real_move, calls = shutil.move, {"n": 0}

        def flaky(src, dst):
            calls["n"] += 1
            if calls["n"] == 2:
                raise OSError("interrupted")
            return real_move(src, dst)

        monkeypatch.setattr(folders.shutil, "move", flaky)
        with pytest.raises(OSError):
            folders.apply_moves(str(root), _plan(root), {"a1"})
        monkeypatch.undo()
        log = folders.apply_moves(str(root), _plan(root), {"a1"})
        folders.undo_moves(str(root), log)
        card = find_card_by_file_id(str(root), "a1")[1]
        assert card["path"].startswith("journal-articles/business/")
        assert (root / "journal-articles" / "business" / "processed_outputs" / "econ0.md").exists()
        assert (root / "journal-articles" / "business" / "econ0.pdf").exists()


def test_a_moved_papers_chunks_follow_its_card():
    from core.indexer.chunk_index import load_chunks, save_chunks
    tmp, root = _setup()
    with tmp:
        save_chunks(str(root), "business", [{"file_id": "a1", "text": "x"}, {"file_id": "m1", "text": "y"}])
        folders.apply_moves(str(root), _plan(root), {"a1"})
        assert [c["file_id"] for c in load_chunks(str(root), "economics-econometrics-and-finance")] == ["a1"]
        assert [c["file_id"] for c in load_chunks(str(root), "business")] == ["m1"]


CRLF = bytes([13, 10])


def _front(root: Path, fid: str, **fields):
    """Gives a paper's transcript frontmatter with CRLF endings, as a Windows text-mode write would."""
    card = find_card_by_file_id(str(root), fid)[1]
    lines = ["---"] + [f"{k}: {v}" for k, v in fields.items()] + ["---", "", "body text", ""]
    (root / card["path"]).write_bytes(CRLF.join(x.encode() for x in lines))
    return card


def _frontmatter(root: Path, fid: str) -> dict:
    from core.env.frontmatter import parse_frontmatter
    card = find_card_by_file_id(str(root), fid)[1]
    text = (root / card["path"]).read_bytes().replace(CRLF, bytes([10])).decode()
    return parse_frontmatter(text)[0]


def test_move_rewrites_transcript_frontmatter_and_undo_restores_it():
    tmp, root = _setup()
    with tmp:
        old = find_card_by_file_id(str(root), "a1")[1]
        _front(root, "a1", title="x", source_pdf=old["source_pdf_path"])
        raw_before = (root / old["path"]).read_bytes()
        log = folders.apply_moves(str(root), _plan(root), {"a1"})
        card = find_card_by_file_id(str(root), "a1")[1]
        raw_after = (root / card["path"]).read_bytes()
        assert _frontmatter(root, "a1")["source_pdf"] == card["source_pdf_path"]
        assert raw_after.count(CRLF) == raw_before.count(CRLF) and b"body text" in raw_after
        folders.undo_moves(str(root), log)
        assert (root / old["path"]).read_bytes() == raw_before


def test_moving_the_canonical_repoints_its_clones_card_and_transcript():
    tmp, root = _setup()
    with tmp:
        canon = find_card_by_file_id(str(root), "a1")[1]
        _paper(root, "business", "clone", "c1", None)
        _front(root, "c1", duplicate_of_path=canon["path"])
        shard = [dict(c, duplicate_of_path=canon["path"]) if c["file_id"] == "c1" else c
                 for c in load_shard(str(root), "business")]
        save_shard(str(root), "business", shard)
        log = folders.apply_moves(str(root), _plan(root), {"a1"})
        new_path = find_card_by_file_id(str(root), "a1")[1]["path"]
        assert _frontmatter(root, "c1")["duplicate_of_path"] == new_path
        assert find_card_by_file_id(str(root), "c1")[1]["duplicate_of_path"] == new_path
        folders.undo_moves(str(root), log)
        assert _frontmatter(root, "c1")["duplicate_of_path"] == canon["path"]
        assert find_card_by_file_id(str(root), "c1")[1]["duplicate_of_path"] == canon["path"]
