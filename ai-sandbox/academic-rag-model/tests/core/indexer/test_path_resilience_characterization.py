from core.indexer.index_card import compute_content_hash
from hub_fixture import make_hub, write_note


def _pair(tmp_path, body_a="body", body_b="body"):
    hub = make_hub(tmp_path)
    a = write_note(hub, "academic_notes/econ/lecture_notes/n.md",
                   {"source_pdf": "academic_resources/econ/lecture_notes/n.pdf"}, body_a)
    b = write_note(hub, "academic_notes/econ/part_1/lecture_notes/n.md",
                   {"source_pdf": "academic_resources/econ/part_1/lecture_notes/n.pdf"}, body_b)
    return a, b


def test_pure_move_keeps_content_hash(tmp_path):
    a, b = _pair(tmp_path)
    assert compute_content_hash(str(a)) == compute_content_hash(str(b))


def test_body_edit_changes_content_hash(tmp_path):
    a, b = _pair(tmp_path, body_b="edited body")
    assert compute_content_hash(str(a)) != compute_content_hash(str(b))
