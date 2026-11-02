from tools.corpus_health.discovery import _eligible_resource_note_pdf


def test_part_resource_pdf_gate_matches_route(tmp_path):
    resources = tmp_path / "academic_resources"
    notes = tmp_path / "academic_notes"
    (notes / "econometrics/part_1/problem_sets").mkdir(parents=True)
    def candidate(rel):
        path = resources / "econometrics" / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"pdf")
        return path
    matched = candidate("part_1/problem_sets/deep/yes.pdf")
    source_only = candidate("part_2/problem_sets/no.pdf")
    textbook = candidate("part_1/Textbooks/book.pdf")
    output = candidate("part_1/problem_sets/processed_outputs/output.pdf")
    stray = candidate("part_1/stray.pdf")
    assert _eligible_resource_note_pdf(matched, resources, notes)
    for path in (source_only, textbook, output, stray):
        assert not _eligible_resource_note_pdf(path, resources, notes)
    (resources / "econometrics/part_2/.notes_subset.json").write_text("{}")
    assert _eligible_resource_note_pdf(source_only, resources, notes)
