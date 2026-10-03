import hashlib

import pytest

from agent.summary_enhance.source_loader import (
    MissingSourcesError, SourceError, load_guide, locate_vault,
)
from conftest import write_guide


def test_loads_chunks_in_ref_order_with_labels(vault):
    guide = load_guide(vault.guide)
    assert [s.label for s in guide.sources] == ["S1", "S2", "S3"]
    assert [s.chunk_id for s in guide.sources] == ["cam-1", "cam-2", "han-1"]
    assert guide.sources[0].text.startswith("Cameron: the Wald")
    assert guide.sources[0].citation == "§7.2.3 Wald Test Statistic, p. 249"
    assert guide.sources[2].path.endswith("han.rag.md")


def test_unreferenced_chunks_are_not_loaded(vault):
    guide = load_guide(vault.guide)
    assert "unused-1" not in {s.chunk_id for s in guide.sources}


def test_root_course_title_body_rel_path(vault):
    guide = load_guide(vault.guide)
    assert guide.root == vault.root.resolve()
    assert guide.course == "econ"
    assert guide.title == "Wald and LM tests"
    assert "Body text." in guide.body and "indexer_source_refs" not in guide.body
    assert guide.rel_path == "academic_notes/econ/summaries/guide.md"


def test_stale_ref_root_is_ignored(vault):
    # refs carry root "STALE-ROOT"; loading must still work off the guide's own path
    assert load_guide(vault.guide).sources


def test_duplicate_refs_deduped(vault):
    write_guide(vault.guide, vault.refs + [vault.refs[0]])
    assert len(load_guide(vault.guide).sources) == 3


def test_missing_chunks_all_listed(vault):
    refs = vault.refs + [{**vault.refs[0], "chunk_id": "gone-1"}, {**vault.refs[0], "chunk_id": "gone-2"}]
    write_guide(vault.guide, refs)
    with pytest.raises(MissingSourcesError) as err:
        load_guide(vault.guide)
    assert err.value.missing == ["gone-1", "gone-2"]


def test_file_id_mismatch_counts_as_missing(vault):
    refs = [{**vault.refs[0], "file_id": "WRONG"}]
    write_guide(vault.guide, refs)
    with pytest.raises(MissingSourcesError):
        load_guide(vault.guide)


@pytest.mark.parametrize("refs", [None, "[]", "not json", '{"a": 1}', '[{"chunk_id": "x"}]'])
def test_bad_refs_raise_source_error(vault, refs):
    write_guide(vault.guide, refs)
    with pytest.raises(SourceError):
        load_guide(vault.guide)


def test_no_frontmatter_raises(vault):
    vault.guide.write_text("# just a heading\n", encoding="utf-8")
    with pytest.raises(SourceError):
        load_guide(vault.guide)


def test_guide_outside_academic_notes_raises(tmp_path):
    stray = tmp_path / "scratch" / "guide.md"
    write_guide(stray, [])
    with pytest.raises(SourceError):
        load_guide(stray)


def test_locate_vault_requires_course_dir(tmp_path):
    with pytest.raises(SourceError):
        locate_vault(tmp_path / "academic_notes" / "guide.md")


def test_crlf_guide_parses_and_hash_is_raw_bytes(vault):
    write_guide(vault.guide, vault.refs, newline="\r\n")
    guide = load_guide(vault.guide)
    assert len(guide.sources) == 3
    assert guide.sha256 == hashlib.sha256(vault.guide.read_bytes()).hexdigest()
