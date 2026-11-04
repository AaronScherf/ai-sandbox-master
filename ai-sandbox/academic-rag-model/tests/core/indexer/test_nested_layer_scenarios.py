"""P2 scenarios: an extra folder layer above a known category needs no code change.

Each test nests the layout one more level (academic_notes/econ/2025_fall/part_1/<category>/...) and checks
one caller of the hub vocabulary. tmp_path hubs only; the shipped hub_config.json supplies the vocabulary.
"""
from pathlib import Path

from audio_generator.discovery import discover_source_files
from core.course_materials.model import Catalog, Material
from core.env.academic_hub_paths import eligible_resource_note_pdf
from core.indexer.markdown_sources import classify_markdown

LAYERS = "2025_fall/part_1"


def _note(hub: Path, rel: str, body: str = "# note\n") -> Path:
    path = hub / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8", newline="\n")
    return path


def test_markdown_row_reports_the_category_under_extra_layers(tmp_path):
    hub = tmp_path / "hub"
    _note(hub, f"academic_notes/econ/{LAYERS}/lecture_notes/a.md")
    rows = classify_markdown(str(hub))
    assert [r["folder_category"] for r in rows if r["path"].endswith("a.md")] == ["lecture_notes"]


def test_audio_discovery_finds_notes_under_extra_layers(tmp_path):
    hub = tmp_path / "hub"
    _note(hub, f"academic_notes/econ/{LAYERS}/lecture_notes/a.md")
    sources = discover_source_files(str(hub), "econ", ["notes"])
    assert [s.rel_md_path for s in sources] == [f"academic_notes/econ/{LAYERS}/lecture_notes/a.md"]


def test_audio_discovery_still_skips_a_sub_folder_of_a_category(tmp_path):
    hub = tmp_path / "hub"
    _note(hub, "academic_notes/econ/lecture_notes/sub/deep.md")
    assert discover_source_files(str(hub), "econ", ["notes"]) == []


def test_resource_pdf_is_eligible_only_with_the_full_mirror(tmp_path):
    hub = tmp_path / "hub"
    pdf = hub / f"academic_resources/econ/{LAYERS}/lecture_notes/x.pdf"
    notes_course = hub / "academic_notes" / "econ"
    (notes_course / "2025_fall").mkdir(parents=True)  # only the outer layer exists
    assert not eligible_resource_note_pdf(str(pdf), str(notes_course))
    (notes_course / LAYERS / "lecture_notes").mkdir(parents=True)
    assert eligible_resource_note_pdf(str(pdf), str(notes_course))


def test_catalog_lookup_does_not_climb_above_the_category_under_extra_layers():
    base = f"academic_notes/econ/{LAYERS}"
    catalog = Catalog("econ", [Material(path=f"{base}/lecture_notes/a.md", role="instructor"),
                               Material(path=f"{base}/ta_notes/c.md", role="instructor")])
    assert catalog.lookup(f"{base}/problem_sets/x.md") is None
    assert catalog.lookup(f"{base}/lecture_notes/sub/b.md").path == f"{base}/lecture_notes/a.md"


def test_transcription_routing_finds_the_resource_pdf_and_mirrors_its_output(tmp_path):
    from core.env.academic_hub_paths import resolve_output_dir
    from pipelines.transcribe_notes.route_notes_transcribe import discover_pdf_sources
    hub = tmp_path / "hub"
    pdf = hub / f"academic_resources/econ/{LAYERS}/lecture_notes/x.pdf"
    pdf.parent.mkdir(parents=True)
    pdf.write_bytes(b"%PDF-1.4\n")
    (hub / f"academic_notes/econ/{LAYERS}/lecture_notes").mkdir(parents=True)
    found = discover_pdf_sources(str(hub / "academic_notes" / "econ"))
    assert [Path(p) for p in found] == [pdf]
    out = Path(resolve_output_dir(str(pdf)))
    assert out == hub / f"academic_notes/econ/{LAYERS}/lecture_notes/processed_outputs"


def test_textbooks_are_found_under_extra_layers(tmp_path):
    hub = tmp_path / "hub"
    book = hub / f"academic_resources/econ/{LAYERS}/textbooks/processed_outputs/Book"
    book.mkdir(parents=True)
    (book / "Book.md").write_text("# b", encoding="utf-8")
    sources = discover_source_files(str(hub), "econ", ["textbook"])
    assert [s.rel_md_path for s in sources] == [f"academic_resources/econ/{LAYERS}/textbooks/processed_outputs/Book/Book.md"]


def test_an_unconfirmed_subfolder_does_not_newly_enable_transcription(tmp_path, seed_hub_config):
    """Live-tree regression: math-camp/problem_sets/past_exams held 14 PDFs that discovery skipped. Seeding
    `past_exams` as a category made them eligible (a paid run), so an unconfirmed folder must not be. Uses the
    frozen seed config; the owner has since confirmed `past_exams` in the shipped config."""
    from pipelines.transcribe_notes.route_notes_transcribe import discover_pdf_sources
    hub = tmp_path / "hub"
    pdf = hub / "academic_resources/math-camp/problem_sets/past_exams/exam.pdf"
    pdf.parent.mkdir(parents=True)
    pdf.write_bytes(b"%PDF-1.4\n")
    (hub / "academic_notes/math-camp/problem_sets/past_exams").mkdir(parents=True)
    assert discover_pdf_sources(str(hub / "academic_notes" / "math-camp")) == []
