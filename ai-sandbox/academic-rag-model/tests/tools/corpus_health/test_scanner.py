from __future__ import annotations

import json
import subprocess
from dataclasses import replace
from pathlib import Path

from core.indexer.index_card import compute_content_hash, compute_file_id, save_shard
from tools.corpus_health.cli import main
from tools.corpus_health.config import MarkdownPolicy, ScanConfig, load_config
from tools.corpus_health.discovery import _frontmatter_status, scan
from tools.corpus_health.state import StateStore, default_state_dir


def _make_config(tmp_path: Path, *, notes_required: bool = False) -> ScanConfig:
    hub = tmp_path / "hub"
    (hub / "academic_resources").mkdir(parents=True)
    notes = tmp_path / "academic_notes"
    notes.mkdir()
    subprocess.run(["git", "init", "-b", "main", str(hub)], check=True, capture_output=True)
    subprocess.run(["git", "init", "-b", "main", str(notes)], check=True, capture_output=True)
    return ScanConfig(
        academic_hub_root=hub,
        academic_notes_root=notes,
        courses=(),
        markdown_policies=(),
        required_roots=("hub", "notes") if notes_required else ("hub",),
    )


def test_scan_finds_missing_note_and_excalidraw_outputs_without_writing_corpus(tmp_path):
    config = _make_config(tmp_path)
    resources = config.academic_hub_root / "academic_resources" / "econ" / "problem_sets"
    resources.mkdir(parents=True)
    (resources / "Set 1.pdf").write_bytes(b"fake pdf bytes")
    (config.academic_notes_root / "econ" / "problem_sets").mkdir(parents=True)
    notes_course = config.academic_notes_root / "econ" / "lecture_notes"
    notes_course.mkdir(parents=True)
    scene = notes_course / "Lecture.excalidraw.md"
    scene.write_text("scene", encoding="utf-8")
    (notes_course / "Lecture.excalidraw.svg").write_text("<svg/>", encoding="utf-8")
    before = {path.relative_to(tmp_path): path.read_bytes()
              for path in tmp_path.rglob("*") if path.is_file()}

    report = scan(config)

    kinds = [finding.kind for finding in report.findings]
    assert "note_transcription_missing" in kinds
    assert kinds.count("note_transcription_missing") == 2
    assert report.complete
    after = {path.relative_to(tmp_path): path.read_bytes()
             for path in tmp_path.rglob("*") if path.is_file()}
    assert after == before


def test_scan_uses_explicit_markdown_policy_and_read_only_index_audit(tmp_path):
    config = _make_config(tmp_path)
    notes_dir = config.academic_notes_root / "econ" / "summaries"
    notes_dir.mkdir(parents=True)
    summary = notes_dir / "new.md"
    summary.write_text("No frontmatter", encoding="utf-8")
    config = ScanConfig(
        academic_hub_root=config.academic_hub_root,
        academic_notes_root=config.academic_notes_root,
        courses=(),
        markdown_policies=(),
        required_roots=("hub",),
    )
    config = ScanConfig(**{**config.__dict__, "markdown_policies": (
        MarkdownPolicy("summaries", "notes", "*/summaries/*.md", True, ("title",), True),
    )})
    index = config.academic_hub_root / ".index"
    index.mkdir()
    before_index = {path.relative_to(index): path.read_bytes() for path in index.rglob("*") if path.is_file()}

    report = scan(config)

    kinds = [finding.kind for finding in report.findings]
    assert "markdown_frontmatter_missing" in kinds
    assert "index_card_missing" in kinds
    assert not report.complete  # no readable index shard can establish health
    after_index = {path.relative_to(index): path.read_bytes() for path in index.rglob("*") if path.is_file()}
    assert after_index == before_index


def test_index_policy_detects_current_index_and_missing_chunks(tmp_path):
    config = _make_config(tmp_path)
    notes_dir = config.academic_notes_root / "econ" / "summaries"
    notes_dir.mkdir(parents=True)
    summary = notes_dir / "one.md"
    summary.write_text("---\ntitle: One\n---\n\nBody", encoding="utf-8")
    index_path = "academic_notes/econ/summaries/one.md"
    save_shard(str(config.academic_hub_root), "econ", [{
        "path": index_path, "file_id": "id-one", "content_hash": compute_content_hash(str(summary)),
    }])
    config = ScanConfig(
        academic_hub_root=config.academic_hub_root,
        academic_notes_root=config.academic_notes_root,
        courses=(),
        markdown_policies=(MarkdownPolicy("summaries", "notes", "*/summaries/*.md"),),
        required_roots=("hub",),
    )

    report = scan(config)

    assert not any(finding.kind in {"markdown_frontmatter_missing", "index_card_missing", "index_card_stale"}
                   for finding in report.findings)
    assert any(finding.kind == "index_chunks_missing_or_stale" for finding in report.findings)


def test_textbook_pdf_is_not_misclassified_as_note_transcription(tmp_path):
    config = _make_config(tmp_path)
    book_dir = config.academic_hub_root / "academic_resources" / "econ" / "textbooks"
    book_dir.mkdir(parents=True)
    book = book_dir / "Textbook.pdf"
    book.write_bytes(b"fake pdf")

    report = scan(config)

    assert [finding.kind for finding in report.findings] == ["textbook_conversion_missing"]
    assert "transcription" not in report.findings[0].kind


def test_textbook_conversion_uses_source_id_across_metadata_and_index_paths(tmp_path):
    config = _make_config(tmp_path)
    books = config.academic_hub_root / "academic_resources" / "econ" / "textbooks"
    books.mkdir(parents=True)
    metadata_pdf = books / "Library filename.pdf"
    metadata_pdf.write_bytes(b"metadata-linked source")
    card_pdf = books / "Different library filename.pdf"
    card_pdf.write_bytes(b"card-linked source")
    outputs = books / "processed_outputs"
    metadata_book = outputs / "Author_Metadata_Title_2026"
    metadata_book.mkdir(parents=True)
    metadata_markdown = metadata_book / f"{metadata_book.name}.md"
    metadata_markdown.write_text("converted book", encoding="utf-8")
    (metadata_book / f"{metadata_book.name}_metadata.json").write_text(json.dumps({
        "source_pdf_file_id": compute_file_id(str(metadata_pdf)),
    }), encoding="utf-8")
    card_book = outputs / "Author_Index_Title_2026"
    card_book.mkdir(parents=True)
    card_markdown = card_book / f"{card_book.name}.md"
    card_markdown.write_text("another converted book", encoding="utf-8")
    save_shard(str(config.academic_hub_root), "econ", [{
        "file_id": compute_file_id(str(card_pdf)),
        "path": card_markdown.relative_to(config.academic_hub_root).as_posix(),
        "doc_type": "textbook",
    }])

    report = scan(config)

    assert not [f for f in report.findings if f.kind == "textbook_conversion_missing"]
    assert report.complete


def test_textbook_metadata_with_missing_markdown_reports_actual_output_path(tmp_path):
    config = _make_config(tmp_path)
    books = config.academic_hub_root / "academic_resources" / "econ" / "textbooks"
    books.mkdir(parents=True)
    source = books / "Library filename.pdf"
    source.write_bytes(b"source pdf")
    book_dir = books / "processed_outputs" / "Author_Title_2026"
    book_dir.mkdir(parents=True)
    (book_dir / "Author_Title_2026_metadata.json").write_text(json.dumps({
        "source_pdf_file_id": compute_file_id(str(source)),
    }), encoding="utf-8")

    report = scan(config)

    gaps = [f for f in report.findings if f.kind == "textbook_conversion_missing"]
    assert len(gaps) == 1
    assert gaps[0].expected_output == str(book_dir / "Author_Title_2026.md")


def test_textbook_same_name_output_without_source_identity_is_not_accepted(tmp_path):
    config = _make_config(tmp_path)
    books = config.academic_hub_root / "academic_resources" / "econ" / "textbooks"
    books.mkdir(parents=True)
    source = books / "Book.pdf"
    source.write_bytes(b"new PDF contents")
    legacy = books / "processed_outputs" / "Book" / "Book.md"
    legacy.parent.mkdir(parents=True)
    legacy.write_text("unlinked Markdown", encoding="utf-8")

    report = scan(config)

    gaps = [f for f in report.findings if f.kind == "textbook_conversion_missing"]
    assert len(gaps) == 1
    assert "content ID" in gaps[0].evidence


def test_frontmatter_parser_reads_past_64k_and_detects_missing_delimiter(tmp_path):
    good = tmp_path / "good.md"
    good.write_text("---\ntitle: Long metadata\nrefs: " + "x" * 70000 + "\n---\nBody", encoding="utf-8")
    bad = tmp_path / "bad.md"
    bad.write_text("---\ntitle: Incomplete\nrefs: " + "x" * 70000, encoding="utf-8")

    assert _frontmatter_status(good, ("title",)) == (True, "")
    assert _frontmatter_status(bad, ("title",)) == (False, "frontmatter closing delimiter is missing")


def test_example_policy_excludes_audio_derivatives_and_named_test_artifacts(tmp_path):
    config = _make_config(tmp_path)
    example = load_config(Path(__file__).parents[3] / "tools" / "corpus_health" / "corpus_health.example.json")
    config = replace(config, markdown_policies=example.markdown_policies)
    processed = config.academic_notes_root / "econ" / "ta_notes" / "processed_outputs"
    processed.mkdir(parents=True)
    for name in ("Lesson.narrated.md", "Lesson__part01.narrated.md", "Lesson__index.md"):
        (processed / name).write_text("audio artifact", encoding="utf-8")
    summaries = config.academic_notes_root / "econ" / "summaries"
    summaries.mkdir(parents=True)
    for name in ("generate_plots.md.md", "testing_html.md", "testing_html_export.md"):
        (summaries / name).write_text("test artifact", encoding="utf-8")
    substantive = summaries / "Actual summary.md"
    substantive.write_text("Needs frontmatter", encoding="utf-8")

    report = scan(config)

    affected = [f for f in report.findings if f.kind in {"markdown_frontmatter_missing", "index_card_missing"}]
    assert {Path(f.path).name for f in affected} == {substantive.name}


def test_textbook_rag_recheck_uses_exact_textbook_folder_names(tmp_path):
    config = _make_config(tmp_path)
    resources = config.academic_hub_root / "academic_resources" / "econ"
    exact_book = resources / "textbooks" / "processed_outputs" / "Book" / "Book.md"
    archive_book = resources / "textbooks_archive" / "processed_outputs" / "Archive" / "Archive.md"
    exact_book.parent.mkdir(parents=True)
    archive_book.parent.mkdir(parents=True)
    exact_book.write_text("converted book", encoding="utf-8")
    archive_book.write_text("not a textbook category", encoding="utf-8")

    report = scan(config)

    assert [(finding.kind, finding.path) for finding in report.findings] == [
        ("textbook_rag_output_missing", str(exact_book)),
    ]


def test_resource_pdf_outside_pipeline_category_or_subset_is_ignored(tmp_path):
    config = _make_config(tmp_path)
    source = config.academic_hub_root / "academic_resources" / "econ" / "unclassified" / "loose.pdf"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"input")
    subset = source.parent / "subset" / "prior.pdf"
    subset.parent.mkdir()
    subset.write_bytes(b"input")
    (subset.parent / ".notes_subset.json").write_text('{"label":"prior"}', encoding="utf-8")

    report = scan(config)

    assert [(finding.kind, finding.path) for finding in report.findings] == [
        ("unknown_input", str(source)), ("note_transcription_missing", str(subset)),
    ]


def test_notes_git_sync_exceptions_are_exact_and_dirty_files_are_reported(tmp_path):
    config = _make_config(tmp_path)
    notes_root = config.academic_notes_root
    (notes_root / ".gitignore").write_text("generated\n", encoding="utf-8")
    (notes_root / ".obsidian").mkdir()
    (notes_root / ".obsidian" / "unrelated.json").write_text("{}", encoding="utf-8")
    config = ScanConfig(**{**config.__dict__, "ignored_notes_git_paths": (".gitignore",)})

    report = scan(config)

    notes_git = report.roots["notes"]["git"]
    assert notes_git["suppressed_known_sync_paths"] == [".gitignore"]
    assert notes_git["dirty_paths"] == [".obsidian/unrelated.json"]


def test_config_load_resolves_paths_relative_to_config(tmp_path):
    config_path = tmp_path / "settings" / "corpus.json"
    config_path.parent.mkdir()
    config_path.write_text(json.dumps({
        "version": 1, "academic_hub_root": "../hub", "academic_notes_root": None,
        "markdown_policies": [],
    }), encoding="utf-8")
    loaded = load_config(config_path)
    assert loaded.academic_hub_root == (tmp_path / "hub").resolve()
    assert loaded.academic_notes_root is None


def test_cli_emits_json_and_returns_incomplete_status_for_missing_required_root(tmp_path, capsys):
    config = tmp_path / "config.json"
    config.write_text(json.dumps({
        "version": 1, "academic_hub_root": "./missing", "academic_notes_root": None,
        "required_roots": ["hub"], "markdown_policies": [],
    }), encoding="utf-8")
    code = main(["scan", "--config", str(config), "--format", "json"])
    captured = capsys.readouterr()
    assert code == 2
    assert json.loads(captured.out)["complete"] is False


def test_cli_scan_persists_findings_and_suppresses_unchanged_declines(tmp_path, capsys):
    config = _make_config(tmp_path)
    resources = config.academic_hub_root / "academic_resources" / "econ" / "problem_sets"
    resources.mkdir(parents=True)
    (config.academic_notes_root / "econ" / "problem_sets").mkdir(parents=True)
    (resources / "Set.pdf").write_bytes(b"pdf")
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({
        "version": 1, "academic_hub_root": str(config.academic_hub_root),
        "academic_notes_root": str(config.academic_notes_root),
        "required_roots": ["hub", "notes"], "markdown_policies": [],
    }), encoding="utf-8")

    assert main(["scan", "--config", str(config_path)]) == 0
    capsys.readouterr()
    store = StateStore(default_state_dir(config.academic_hub_root))
    pending = store.pending()
    assert len(pending) == 1
    store.decide(pending[0]["finding_id"], "declined", pending[0]["finding"]["fingerprint"])

    assert main(["scan", "--config", str(config_path), "--format", "json"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["findings"][0]["finding_id"] == pending[0]["finding_id"]
    assert store.pending() == []


def test_review_validator_reuses_one_corpus_scan_snapshot(tmp_path, monkeypatch):
    from types import SimpleNamespace

    from tools.corpus_health import cli
    from tools.corpus_health.finding import Finding

    config = _make_config(tmp_path)
    finding = Finding("index_card_missing", "notes", "C:/notes/a.md", "a.md", "missing card",
                      suggested_action="index", fingerprint="sha256:one", scope="notes/econ")
    calls = 0

    def fake_scan(_config):
        nonlocal calls
        calls += 1
        return SimpleNamespace(findings=[finding])

    monkeypatch.setattr(cli, "scan", fake_scan)
    validator = cli._review_snapshot_validator(config)
    entry = {
        "finding_id": StateStore.finding_id(finding),
        "finding": {"fingerprint": finding.fingerprint},
        "action_signature": StateStore.action_signature(finding),
    }

    assert validator([entry])
    assert validator([entry])
    assert calls == 1
