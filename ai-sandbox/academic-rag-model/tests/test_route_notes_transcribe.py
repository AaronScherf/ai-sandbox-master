import os
from unittest.mock import patch

from notes.route_notes_transcribe import (
    PipelinePlan,
    build_plan,
    discover_excalidraw_sources,
    discover_pdf_sources,
    excalidraw_output_path,
    filter_unprocessed_excalidraw,
    filter_unprocessed_pdfs,
    find_course_dirs,
    pdf_output_path,
    run_plan,
)


def _make_course(root, course, category, files: dict):
    """files: {filename: content-or-bytes}. Writes each directly under
    root/academic_notes/course/category/."""
    d = root / "academic_notes" / course / category
    d.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        path = d / name
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content)
    return d


def test_find_course_dirs_lists_only_directories(tmp_path):
    (tmp_path / "academic_notes" / "econometrics").mkdir(parents=True)
    (tmp_path / "academic_notes" / "microecon").mkdir(parents=True)
    (tmp_path / "academic_notes" / ".obsidian").mkdir(parents=True)
    (tmp_path / "academic_notes" / "stray_file.md").write_text("not a course")

    courses = find_course_dirs(str(tmp_path))

    assert courses == ["econometrics", "microecon"]


def test_find_course_dirs_missing_academic_notes_returns_empty(tmp_path):
    assert find_course_dirs(str(tmp_path)) == []


def test_discover_pdf_sources_finds_pdfs_recursively(tmp_path):
    _make_course(tmp_path, "econometrics", "ta_notes", {"01-terms.pdf": b"fake-pdf"})
    _make_course(tmp_path, "econometrics", "professor_notes", {"090926.pdf": b"fake-pdf"})

    paths = discover_pdf_sources(str(tmp_path / "academic_notes" / "econometrics"))

    names = sorted(os.path.basename(p) for p in paths)
    assert names == ["01-terms.pdf", "090926.pdf"]


def test_discover_pdf_sources_ignores_processed_outputs_directory(tmp_path):
    # A stray .pdf sitting inside processed_outputs/ (shouldn't happen in
    # practice, but the walk must not treat that directory as a source
    # location at all -- pruned, not just filtered by name).
    ta_dir = _make_course(tmp_path, "econometrics", "ta_notes", {"01-terms.pdf": b"fake-pdf"})
    out_dir = ta_dir / "processed_outputs"
    out_dir.mkdir()
    (out_dir / "decoy.pdf").write_bytes(b"should not be discovered")

    paths = discover_pdf_sources(str(tmp_path / "academic_notes" / "econometrics"))

    assert [os.path.basename(p) for p in paths] == ["01-terms.pdf"]


def test_discover_pdf_sources_also_finds_pdfs_migrated_to_academic_resources(tmp_path):
    # academic_notes/<course>/ta_notes/ exists (even if empty of PDFs) --
    # that's what makes academic_resources/<course>/ta_notes/ eligible.
    (tmp_path / "academic_notes" / "econometrics" / "ta_notes").mkdir(parents=True)
    resources_dir = tmp_path / "academic_resources" / "econometrics" / "ta_notes"
    resources_dir.mkdir(parents=True)
    (resources_dir / "01-terms.pdf").write_bytes(b"x")

    paths = discover_pdf_sources(str(tmp_path / "academic_notes" / "econometrics"))

    assert [os.path.basename(p) for p in paths] == ["01-terms.pdf"]


def test_discover_pdf_sources_ignores_academic_resources_categories_with_no_notes_counterpart(tmp_path):
    # academic_resources/<course>/textbooks/ has no academic_notes/<course>/textbooks/
    # counterpart -- must stay out of scope (that's convert_textbook.py's
    # pipeline, not transcribe_notes.py's).
    (tmp_path / "academic_notes" / "econometrics" / "ta_notes").mkdir(parents=True)
    textbooks_dir = tmp_path / "academic_resources" / "econometrics" / "textbooks"
    textbooks_dir.mkdir(parents=True)
    (textbooks_dir / "Hansen.pdf").write_bytes(b"x")

    paths = discover_pdf_sources(str(tmp_path / "academic_notes" / "econometrics"))

    assert paths == []


def test_discover_pdf_sources_combines_notes_and_resources_pdfs(tmp_path):
    ta_dir = tmp_path / "academic_notes" / "econometrics" / "ta_notes"
    ta_dir.mkdir(parents=True)
    (ta_dir / "not-yet-migrated.pdf").write_bytes(b"x")
    resources_dir = tmp_path / "academic_resources" / "econometrics" / "ta_notes"
    resources_dir.mkdir(parents=True)
    (resources_dir / "already-migrated.pdf").write_bytes(b"x")

    paths = discover_pdf_sources(str(tmp_path / "academic_notes" / "econometrics"))

    assert sorted(os.path.basename(p) for p in paths) == ["already-migrated.pdf", "not-yet-migrated.pdf"]


def test_discover_excalidraw_sources_pairs_md_and_image_recursively(tmp_path):
    _make_course(
        tmp_path, "econometrics", "lecture_notes",
        {"Drawing.excalidraw.md": "---\n---\n", "Drawing.excalidraw.svg": "<svg></svg>"},
    )

    pairs = discover_excalidraw_sources(str(tmp_path / "academic_notes" / "econometrics"))

    assert len(pairs) == 1
    assert os.path.basename(pairs[0][0]) == "Drawing.excalidraw.md"
    assert os.path.basename(pairs[0][1]) == "Drawing.excalidraw.svg"


def test_discover_excalidraw_sources_does_not_rediscover_its_own_raw_output(tmp_path):
    # The pipeline's own raw-transcription output is named
    # "<name>.excalidraw.md" -- the exact same suffix as a real source
    # file. A recursive scan that doesn't prune processed_outputs/ would
    # treat its own prior output as a brand-new unprocessed source.
    lecture_dir = _make_course(
        tmp_path, "econometrics", "lecture_notes",
        {"Drawing.excalidraw.md": "---\n---\n", "Drawing.excalidraw.svg": "<svg></svg>"},
    )
    out_dir = lecture_dir / "processed_outputs"
    out_dir.mkdir()
    (out_dir / "Drawing.excalidraw.md").write_text("raw transcription output, not a source")
    (out_dir / "Drawing.excalidraw.rag.md").write_text("expanded output, not a source")

    pairs = discover_excalidraw_sources(str(tmp_path / "academic_notes" / "econometrics"))

    assert len(pairs) == 1
    assert os.path.basename(pairs[0][0]) == "Drawing.excalidraw.md"
    assert os.path.dirname(pairs[0][0]) == str(lecture_dir)


def test_pdf_output_path_points_at_processed_outputs_md():
    pdf_path = os.path.join("academic_notes", "econometrics", "ta_notes", "01-terms.pdf")
    expected = os.path.join("academic_notes", "econometrics", "ta_notes", "processed_outputs", "01-terms.md")
    assert pdf_output_path(pdf_path) == expected


def test_pdf_output_path_mirrors_to_notes_root_for_a_migrated_pdf():
    # Real finding (2026-09-23, math-camp migration): pdf_output_path only
    # ever assumed processed_outputs/ is a sibling of the PDF -- true
    # before migration, but a migrated PDF's real .md output stays under
    # academic_notes/ while the PDF itself now lives under
    # academic_resources/. Without this, filter_unprocessed_pdfs treats
    # every already-transcribed migrated PDF as unprocessed and would
    # re-transcribe it.
    pdf_path = os.path.join("academic_resources", "math-camp", "ta_notes", "LN1.pdf")
    expected = os.path.join("academic_notes", "math-camp", "ta_notes", "processed_outputs", "LN1.md")
    assert pdf_output_path(pdf_path) == expected


def test_excalidraw_output_path_points_at_processed_outputs_rag_md():
    md_path = os.path.join("academic_notes", "econometrics", "lecture_notes", "Drawing.excalidraw.md")
    expected = os.path.join(
        "academic_notes", "econometrics", "lecture_notes", "processed_outputs", "Drawing.excalidraw.rag.md",
    )
    assert excalidraw_output_path(md_path) == expected


def test_filter_unprocessed_pdfs_skips_files_with_nonempty_output(tmp_path):
    ta_dir = _make_course(tmp_path, "econometrics", "ta_notes", {"done.pdf": b"x", "todo.pdf": b"x"})
    out_dir = ta_dir / "processed_outputs"
    out_dir.mkdir()
    (out_dir / "done.md").write_text("already transcribed")

    pdfs = [str(ta_dir / "done.pdf"), str(ta_dir / "todo.pdf")]
    todo = filter_unprocessed_pdfs(pdfs)

    assert [os.path.basename(p) for p in todo] == ["todo.pdf"]


def test_filter_unprocessed_pdfs_treats_empty_output_as_unprocessed(tmp_path):
    ta_dir = _make_course(tmp_path, "econometrics", "ta_notes", {"partial.pdf": b"x"})
    out_dir = ta_dir / "processed_outputs"
    out_dir.mkdir()
    (out_dir / "partial.md").write_text("")  # 0 bytes -- a known stale-artifact pattern in this corpus

    todo = filter_unprocessed_pdfs([str(ta_dir / "partial.pdf")])

    assert len(todo) == 1


def test_filter_unprocessed_pdfs_force_reprocesses_everything(tmp_path):
    ta_dir = _make_course(tmp_path, "econometrics", "ta_notes", {"done.pdf": b"x"})
    out_dir = ta_dir / "processed_outputs"
    out_dir.mkdir()
    (out_dir / "done.md").write_text("already transcribed")

    todo = filter_unprocessed_pdfs([str(ta_dir / "done.pdf")], force=True)

    assert len(todo) == 1


def test_filter_unprocessed_excalidraw_checks_rag_md_not_raw_md(tmp_path):
    # The raw .md is an intermediate artifact -- only the .rag.md is the
    # RAG-canonical output (matches write_outputs' own indexing choice).
    # A file with only the raw .md written (e.g. a prior run crashed
    # before expansion) must still count as unprocessed.
    lecture_dir = _make_course(
        tmp_path, "econometrics", "lecture_notes",
        {"partial.excalidraw.md": "---\n---\n", "partial.excalidraw.svg": "<svg></svg>"},
    )
    out_dir = lecture_dir / "processed_outputs"
    out_dir.mkdir()
    (out_dir / "partial.excalidraw.md").write_text("raw only, expansion never finished")

    pairs = [(str(lecture_dir / "partial.excalidraw.md"), str(lecture_dir / "partial.excalidraw.svg"))]
    todo = filter_unprocessed_excalidraw(pairs)

    assert len(todo) == 1


def test_filter_unprocessed_excalidraw_skips_when_rag_md_exists(tmp_path):
    lecture_dir = _make_course(
        tmp_path, "econometrics", "lecture_notes",
        {"done.excalidraw.md": "---\n---\n", "done.excalidraw.svg": "<svg></svg>"},
    )
    out_dir = lecture_dir / "processed_outputs"
    out_dir.mkdir()
    (out_dir / "done.excalidraw.rag.md").write_text("expanded output")

    pairs = [(str(lecture_dir / "done.excalidraw.md"), str(lecture_dir / "done.excalidraw.svg"))]
    todo = filter_unprocessed_excalidraw(pairs)

    assert todo == []


def test_build_plan_combines_pdf_and_excalidraw_across_courses(tmp_path):
    _make_course(tmp_path, "econometrics", "ta_notes", {"a.pdf": b"x"})
    _make_course(tmp_path, "microecon", "lecture_notes", {"b.excalidraw.md": "---\n---\n", "b.excalidraw.svg": "<svg></svg>"})

    plan = build_plan(str(tmp_path))

    assert [os.path.basename(p) for p in plan.pdf_todo] == ["a.pdf"]
    assert [os.path.basename(md) for md, _img in plan.excalidraw_todo] == ["b.excalidraw.md"]


def test_build_plan_respects_course_filter(tmp_path):
    _make_course(tmp_path, "econometrics", "ta_notes", {"a.pdf": b"x"})
    _make_course(tmp_path, "microecon", "ta_notes", {"b.pdf": b"x"})

    plan = build_plan(str(tmp_path), courses=["econometrics"])

    assert [os.path.basename(p) for p in plan.pdf_todo] == ["a.pdf"]


def test_build_plan_tracks_skipped_alongside_todo(tmp_path):
    ta_dir = _make_course(tmp_path, "econometrics", "ta_notes", {"done.pdf": b"x", "todo.pdf": b"x"})
    out_dir = ta_dir / "processed_outputs"
    out_dir.mkdir()
    (out_dir / "done.md").write_text("already transcribed")

    plan = build_plan(str(tmp_path), courses=["econometrics"])

    assert [os.path.basename(p) for p in plan.pdf_todo] == ["todo.pdf"]
    assert [os.path.basename(p) for p in plan.pdf_skipped] == ["done.pdf"]


def test_run_plan_dispatches_pdfs_and_excalidraw_to_the_right_function(tmp_path):
    ta_dir = _make_course(tmp_path, "econometrics", "ta_notes", {"a.pdf": b"x"})
    lecture_dir = _make_course(
        tmp_path, "microecon", "lecture_notes",
        {"b.excalidraw.md": "---\n---\n", "b.excalidraw.svg": "<svg></svg>"},
    )
    plan = PipelinePlan(
        pdf_todo=[str(ta_dir / "a.pdf")],
        excalidraw_todo=[(str(lecture_dir / "b.excalidraw.md"), str(lecture_dir / "b.excalidraw.svg"))],
    )

    def fake_process_pdf(pdf_path, client, model, academic_hub_root, dry_run=False):
        out = ta_dir / "processed_outputs"
        out.mkdir(exist_ok=True)
        (out / "a.md").write_text("transcribed")

    def fake_process_excalidraw_note(md_path, image_path, client, model, expand_backend, academic_hub_root, use_grounding=False, dry_run=False):
        out = lecture_dir / "processed_outputs"
        out.mkdir(exist_ok=True)
        (out / "b.excalidraw.rag.md").write_text("expanded")

    with patch("notes.route_notes_transcribe.process_pdf", side_effect=fake_process_pdf) as mock_pdf, \
         patch("notes.route_notes_transcribe.process_excalidraw_note", side_effect=fake_process_excalidraw_note) as mock_exc:
        report = run_plan(plan, client=object(), academic_hub_root=str(tmp_path))

    mock_pdf.assert_called_once()
    mock_exc.assert_called_once()
    assert report.pdf_results[0].status == "ok"
    assert report.excalidraw_results[0].status == "ok"


def test_run_plan_records_failure_without_stopping_the_batch(tmp_path):
    ta_dir = _make_course(tmp_path, "econometrics", "ta_notes", {"bad.pdf": b"x", "good.pdf": b"x"})
    plan = PipelinePlan(pdf_todo=[str(ta_dir / "bad.pdf"), str(ta_dir / "good.pdf")])

    def fake_process_pdf(pdf_path, client, model, academic_hub_root, dry_run=False):
        if "bad" in pdf_path:
            raise ValueError("simulated API failure")
        out = ta_dir / "processed_outputs"
        out.mkdir(exist_ok=True)
        (out / "good.md").write_text("transcribed")

    with patch("notes.route_notes_transcribe.process_pdf", side_effect=fake_process_pdf):
        report = run_plan(plan, client=object(), academic_hub_root=str(tmp_path))

    statuses = {os.path.basename(r.path): r.status for r in report.pdf_results}
    assert statuses["bad.pdf"] == "failed"
    assert statuses["good.pdf"] == "ok"


def test_run_plan_flags_output_missing_when_process_silently_writes_nothing(tmp_path):
    # Verification step: a process_* call that raises no exception but
    # never actually writes the expected output file must not be reported
    # as a silent success.
    ta_dir = _make_course(tmp_path, "econometrics", "ta_notes", {"a.pdf": b"x"})
    plan = PipelinePlan(pdf_todo=[str(ta_dir / "a.pdf")])

    with patch("notes.route_notes_transcribe.process_pdf", return_value=None):
        report = run_plan(plan, client=object(), academic_hub_root=str(tmp_path))

    assert report.pdf_results[0].status == "output_missing"


def test_discover_pdf_sources_ignores_textbooks_even_when_notes_has_a_textbooks_folder(tmp_path):
    # Each book's .rag.md is mirrored into academic_notes/<course>/textbooks/,
    # so a same-named notes category now exists -- textbook PDFs must
    # still never be routed into notes transcription.
    (tmp_path / "academic_notes" / "econometrics" / "textbooks" / "processed_outputs").mkdir(parents=True)
    textbooks_dir = tmp_path / "academic_resources" / "econometrics" / "textbooks"
    textbooks_dir.mkdir(parents=True)
    (textbooks_dir / "Hansen.pdf").write_bytes(b"x")

    paths = discover_pdf_sources(str(tmp_path / "academic_notes" / "econometrics"))

    assert paths == []
