import json
import os
from unittest.mock import patch

from pipelines.transcribe_notes.route_notes_transcribe import (
    PipelinePlan,
    _dedupe,
    _walk_marked_subset,
    build_plan,
    discover_excalidraw_sources,
    discover_marked_subset_excalidraw_sources,
    discover_marked_subset_pdf_sources,
    discover_pdf_sources,
    excalidraw_output_path,
    filter_unprocessed_excalidraw,
    filter_unprocessed_pdfs,
    find_course_dirs,
    find_subset_roots,
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


def test_excalidraw_output_path_mirrors_to_notes_root_for_a_migrated_scene():
    # Same bug class as test_pdf_output_path_mirrors_to_notes_root_for_a_migrated_pdf:
    # before marked-subset discovery, every .excalidraw.md source came from
    # the academic_notes/ side, where dirname-based and resolve_output_dir-
    # based paths agree. A scene discovered under academic_resources/ (via
    # a marked subset) needs the real mirrored output location, or it's
    # judged unprocessed and re-transcribed on every run.
    md_path = os.path.join(
        "academic_resources", "econometrics", "class_2024", "Scanned Canvases", "Drawing.excalidraw.md",
    )
    expected = os.path.join(
        "academic_notes", "econometrics", "class_2024", "Scanned Canvases",
        "processed_outputs", "Drawing.excalidraw.rag.md",
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

    with patch("pipelines.transcribe_notes.route_notes_transcribe.process_pdf", side_effect=fake_process_pdf) as mock_pdf, \
         patch("pipelines.transcribe_notes.route_notes_transcribe.process_excalidraw_note", side_effect=fake_process_excalidraw_note) as mock_exc:
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

    with patch("pipelines.transcribe_notes.route_notes_transcribe.process_pdf", side_effect=fake_process_pdf):
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

    with patch("pipelines.transcribe_notes.route_notes_transcribe.process_pdf", return_value=None):
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


def test_find_subset_roots_finds_a_marked_directory(tmp_path):
    resources_dir = tmp_path / "academic_resources" / "econometrics" / "class_2024"
    resources_dir.mkdir(parents=True)
    (resources_dir / ".notes_subset.json").write_text(json.dumps({"label": "2024"}))

    roots = find_subset_roots(str(tmp_path / "academic_resources" / "econometrics"))

    assert roots == [str(resources_dir)]


def test_find_subset_roots_ignores_unmarked_directories(tmp_path):
    resources_dir = tmp_path / "academic_resources" / "econometrics" / "class_2024"
    resources_dir.mkdir(parents=True)
    (resources_dir / "some.pdf").write_bytes(b"x")  # no marker file

    roots = find_subset_roots(str(tmp_path / "academic_resources" / "econometrics"))

    assert roots == []


def test_find_subset_roots_does_not_search_for_nested_markers_inside_a_claimed_root(tmp_path):
    outer = tmp_path / "academic_resources" / "econometrics" / "class_2024"
    inner = outer / "Class Notes"
    inner.mkdir(parents=True)
    (outer / ".notes_subset.json").write_text(json.dumps({"label": "2024"}))
    (inner / ".notes_subset.json").write_text(json.dumps({"label": "nested-should-be-ignored"}))

    roots = find_subset_roots(str(tmp_path / "academic_resources" / "econometrics"))

    assert roots == [str(outer)]


def test_find_subset_roots_skips_malformed_marker_with_a_warning(tmp_path, capsys):
    resources_dir = tmp_path / "academic_resources" / "econometrics" / "class_2024"
    resources_dir.mkdir(parents=True)
    (resources_dir / ".notes_subset.json").write_text("{not valid json")

    roots = find_subset_roots(str(tmp_path / "academic_resources" / "econometrics"))

    assert roots == []
    assert "WARNING" in capsys.readouterr().out


def test_find_subset_roots_returns_empty_for_missing_resources_dir(tmp_path):
    assert find_subset_roots(str(tmp_path / "academic_resources" / "nonexistent")) == []


def test_walk_marked_subset_yields_nested_directories(tmp_path):
    root = tmp_path / "class_2024"
    deep = root / "Class Notes" / "Hand-Written Notes"
    deep.mkdir(parents=True)

    dirs = list(_walk_marked_subset(str(root)))

    assert str(deep) in dirs
    assert str(root / "Class Notes") in dirs
    assert str(root) in dirs


def test_walk_marked_subset_prunes_processed_outputs_and_hidden_dirs(tmp_path):
    root = tmp_path / "class_2024"
    (root / "processed_outputs").mkdir(parents=True)
    (root / ".obsidian").mkdir(parents=True)
    (root / "Slides").mkdir(parents=True)

    dirs = list(_walk_marked_subset(str(root)))

    assert str(root / "processed_outputs") not in dirs
    assert str(root / ".obsidian") not in dirs
    assert str(root / "Slides") in dirs


def test_walk_marked_subset_prunes_textbook_folders_at_any_depth(tmp_path):
    root = tmp_path / "class_2024"
    textbooks_dir = root / "Readings" / "textbooks"
    textbooks_dir.mkdir(parents=True)

    dirs = list(_walk_marked_subset(str(root)))

    assert str(textbooks_dir) not in dirs
    assert str(root / "Readings") in dirs


def test_discover_marked_subset_pdf_sources_finds_pdfs_at_arbitrary_depth(tmp_path):
    resources_econ = tmp_path / "academic_resources" / "econometrics"
    subset = resources_econ / "class_2024"
    deep = subset / "Class Notes" / "Hand-Written Notes"
    deep.mkdir(parents=True)
    (subset / ".notes_subset.json").write_text(json.dumps({"label": "2024"}))
    (deep / "090424.pdf").write_bytes(b"x")
    (subset / "2023exam1.pdf").write_bytes(b"x")  # loose file directly under the marked root

    paths = discover_marked_subset_pdf_sources(str(resources_econ))

    names = sorted(os.path.basename(p) for p in paths)
    assert names == ["090424.pdf", "2023exam1.pdf"]


def test_discover_marked_subset_pdf_sources_ignores_unmarked_siblings(tmp_path):
    resources_econ = tmp_path / "academic_resources" / "econometrics"
    unmarked = resources_econ / "class_2023"
    unmarked.mkdir(parents=True)
    (unmarked / "old.pdf").write_bytes(b"x")

    paths = discover_marked_subset_pdf_sources(str(resources_econ))

    assert paths == []


def test_discover_marked_subset_excalidraw_sources_finds_pairs_at_depth(tmp_path):
    resources_econ = tmp_path / "academic_resources" / "econometrics"
    subset = resources_econ / "class_2024"
    deep = subset / "Scanned Canvases"
    deep.mkdir(parents=True)
    (subset / ".notes_subset.json").write_text(json.dumps({"label": "2024"}))
    (deep / "Drawing.excalidraw.md").write_text("---\n---\n")
    (deep / "Drawing.excalidraw.svg").write_text("<svg></svg>")

    pairs = discover_marked_subset_excalidraw_sources(str(resources_econ))

    assert len(pairs) == 1
    assert os.path.basename(pairs[0][0]) == "Drawing.excalidraw.md"


def test_discover_pdf_sources_includes_marked_subset_at_depth(tmp_path):
    # academic_notes/econometrics/ta_notes/ already exists from normal use;
    # the marked subset sits alongside it in academic_resources/, under a
    # brand-new "class_2024" name with no academic_notes/ counterpart --
    # exactly the case _discover_migrated_pdf_sources can't handle.
    (tmp_path / "academic_notes" / "econometrics" / "ta_notes").mkdir(parents=True)
    subset = tmp_path / "academic_resources" / "econometrics" / "class_2024"
    deep = subset / "Class Notes" / "Hand-Written Notes"
    deep.mkdir(parents=True)
    (subset / ".notes_subset.json").write_text(json.dumps({"label": "2024"}))
    (deep / "090424.pdf").write_bytes(b"x")

    paths = discover_pdf_sources(str(tmp_path / "academic_notes" / "econometrics"))

    assert [os.path.basename(p) for p in paths] == ["090424.pdf"]


def test_discover_pdf_sources_does_not_duplicate_pdfs_seen_by_both_paths(tmp_path):
    # Pathological but guarded-against case: a marker placed directly
    # inside a category that's also eligible for the existing flat
    # migrated-category sweep must not cause double processing.
    (tmp_path / "academic_notes" / "econometrics" / "ta_notes").mkdir(parents=True)
    resources_dir = tmp_path / "academic_resources" / "econometrics" / "ta_notes"
    resources_dir.mkdir(parents=True)
    (resources_dir / ".notes_subset.json").write_text(json.dumps({"label": "overlap"}))
    (resources_dir / "01-terms.pdf").write_bytes(b"x")

    paths = discover_pdf_sources(str(tmp_path / "academic_notes" / "econometrics"))

    assert [os.path.basename(p) for p in paths] == ["01-terms.pdf"]


def test_discover_pdf_sources_ignores_marker_placed_on_the_notes_side(tmp_path):
    # The marker is only ever read from the academic_resources/ side --
    # placing it under academic_notes/ by mistake must be a quiet no-op,
    # not an error, and must not accidentally re-trigger the normal
    # recursive academic_notes/ walk differently.
    notes_dir = tmp_path / "academic_notes" / "econometrics" / "ta_notes"
    notes_dir.mkdir(parents=True)
    (notes_dir / ".notes_subset.json").write_text(json.dumps({"label": "2024"}))
    (notes_dir / "01-terms.pdf").write_bytes(b"x")

    paths = discover_pdf_sources(str(tmp_path / "academic_notes" / "econometrics"))

    assert [os.path.basename(p) for p in paths] == ["01-terms.pdf"]


def test_discover_excalidraw_sources_includes_marked_subset(tmp_path):
    (tmp_path / "academic_notes" / "econometrics" / "lecture_notes").mkdir(parents=True)
    subset = tmp_path / "academic_resources" / "econometrics" / "class_2024"
    deep = subset / "Scanned Canvases"
    deep.mkdir(parents=True)
    (subset / ".notes_subset.json").write_text(json.dumps({"label": "2024"}))
    (deep / "Drawing.excalidraw.md").write_text("---\n---\n")
    (deep / "Drawing.excalidraw.svg").write_text("<svg></svg>")

    pairs = discover_excalidraw_sources(str(tmp_path / "academic_notes" / "econometrics"))

    assert len(pairs) == 1
    assert os.path.basename(pairs[0][0]) == "Drawing.excalidraw.md"


def test_marked_subset_pdf_is_skipped_on_second_run_once_transcribed(tmp_path):
    # End-to-end check of the spec's "nothing downstream needs to change"
    # claim: resolve_output_dir/filter_unprocessed_pdfs must correctly
    # recognize a marked-subset PDF as already done, through build_plan.
    (tmp_path / "academic_notes" / "econometrics" / "ta_notes").mkdir(parents=True)
    subset = tmp_path / "academic_resources" / "econometrics" / "class_2024"
    deep = subset / "Class Notes" / "Hand-Written Notes"
    deep.mkdir(parents=True)
    (subset / ".notes_subset.json").write_text(json.dumps({"label": "2024"}))
    (deep / "090424.pdf").write_bytes(b"x")
    mirrored_out = (
        tmp_path / "academic_notes" / "econometrics" / "class_2024"
        / "Class Notes" / "Hand-Written Notes" / "processed_outputs"
    )
    mirrored_out.mkdir(parents=True)
    (mirrored_out / "090424.md").write_text("already transcribed")

    plan = build_plan(str(tmp_path), courses=["econometrics"])

    assert plan.pdf_todo == []
    assert [os.path.basename(p) for p in plan.pdf_skipped] == ["090424.pdf"]


def test_marked_subset_excalidraw_is_skipped_on_second_run_once_transcribed(tmp_path):
    # Mirrors test_marked_subset_pdf_is_skipped_on_second_run_once_transcribed
    # for the Excalidraw path -- catches the excalidraw_output_path bug a
    # pure unit test on the function alone wouldn't: a wrong "is this done"
    # check means it's never actually exercised through build_plan.
    (tmp_path / "academic_notes" / "econometrics" / "lecture_notes").mkdir(parents=True)
    subset = tmp_path / "academic_resources" / "econometrics" / "class_2024"
    deep = subset / "Scanned Canvases"
    deep.mkdir(parents=True)
    (subset / ".notes_subset.json").write_text(json.dumps({"label": "2024"}))
    (deep / "Drawing.excalidraw.md").write_text("---\n---\n")
    (deep / "Drawing.excalidraw.svg").write_text("<svg></svg>")
    mirrored_out = (
        tmp_path / "academic_notes" / "econometrics" / "class_2024"
        / "Scanned Canvases" / "processed_outputs"
    )
    mirrored_out.mkdir(parents=True)
    (mirrored_out / "Drawing.excalidraw.rag.md").write_text("already transcribed")

    plan = build_plan(str(tmp_path), courses=["econometrics"])

    assert plan.excalidraw_todo == []
    assert [os.path.basename(md) for md, _img in plan.excalidraw_skipped] == ["Drawing.excalidraw.md"]


def test_find_subset_roots_accepts_a_marker_saved_with_a_utf8_bom(tmp_path):
    # Real finding: Windows PowerShell's Out-File/> and some editors write
    # UTF-8 with a BOM by default. The spec's own migration steps tell the
    # user to create this file from the shell, so rejecting a BOM would
    # silently break the documented happy path on this platform.
    resources_dir = tmp_path / "academic_resources" / "econometrics" / "class_2024"
    resources_dir.mkdir(parents=True)
    (resources_dir / ".notes_subset.json").write_bytes(
        b"\xef\xbb\xbf" + json.dumps({"label": "2024"}).encode("utf-8")
    )

    roots = find_subset_roots(str(tmp_path / "academic_resources" / "econometrics"))

    assert roots == [str(resources_dir)]


def test_find_subset_roots_warns_and_ignores_a_null_marker(tmp_path, capsys):
    resources_dir = tmp_path / "academic_resources" / "econometrics" / "class_2024"
    resources_dir.mkdir(parents=True)
    (resources_dir / ".notes_subset.json").write_text("null")

    roots = find_subset_roots(str(tmp_path / "academic_resources" / "econometrics"))

    assert roots == []
    assert "WARNING" in capsys.readouterr().out


def test_find_subset_roots_warns_and_ignores_a_non_dict_marker(tmp_path, capsys):
    # json.load("[]") returns [] -- not None -- so a naive "is not None"
    # check would wrongly treat this as a valid marker and mark the
    # directory, unlike the null case above where it happens to coincide
    # with "not marked" already.
    resources_dir = tmp_path / "academic_resources" / "econometrics" / "class_2024"
    resources_dir.mkdir(parents=True)
    (resources_dir / ".notes_subset.json").write_text("[]")

    roots = find_subset_roots(str(tmp_path / "academic_resources" / "econometrics"))

    assert roots == []
    assert "WARNING" in capsys.readouterr().out


def test_walk_marked_subset_prunes_textbook_folders_case_insensitively(tmp_path):
    root = tmp_path / "class_2024"
    textbooks_dir = root / "Readings" / "Textbooks"
    textbooks_dir.mkdir(parents=True)

    dirs = list(_walk_marked_subset(str(root)))

    assert str(textbooks_dir) not in dirs
    assert str(root / "Readings") in dirs


def test_find_subset_roots_does_not_descend_into_textbook_folders(tmp_path):
    # A marker mistakenly placed inside/under a textbooks/ folder must not
    # sweep book PDFs into notes transcription -- the same invariant
    # _walk_marked_subset already enforces for a subset's own interior,
    # needed here too since find_subset_roots walks ahead of any marker
    # being found.
    resources_econ = tmp_path / "academic_resources" / "econometrics"
    textbooks_dir = resources_econ / "Textbooks" / "SomeBook"
    textbooks_dir.mkdir(parents=True)
    (textbooks_dir / ".notes_subset.json").write_text(json.dumps({"label": "oops"}))

    roots = find_subset_roots(str(resources_econ))

    assert roots == []


def test_build_plan_computes_subset_roots_once_per_course(tmp_path):
    # Real finding: discover_pdf_sources and discover_excalidraw_sources
    # each independently called find_subset_roots, walking the whole
    # marked-subset tree twice (and double-printing any malformed-marker
    # warning) for one build_plan() call.
    (tmp_path / "academic_notes" / "econometrics" / "ta_notes").mkdir(parents=True)
    subset = tmp_path / "academic_resources" / "econometrics" / "class_2024"
    subset.mkdir(parents=True)
    (subset / ".notes_subset.json").write_text(json.dumps({"label": "2024"}))
    (subset / "a.pdf").write_bytes(b"x")

    with patch(
        "pipelines.transcribe_notes.route_notes_transcribe.find_subset_roots",
        wraps=find_subset_roots,
    ) as mock_find:
        build_plan(str(tmp_path), courses=["econometrics"])

    assert mock_find.call_count == 1


def test_dedupe_preserves_order_and_removes_duplicates():
    assert _dedupe(["a", "b", "a", "c", "b"]) == ["a", "b", "c"]


def test_run_plan_passes_force_vision_to_process_pdf():
    plan = PipelinePlan(pdf_todo=["some/path/doc.pdf"])
    with patch("pipelines.transcribe_notes.route_notes_transcribe.process_pdf") as mock_process:
        with patch("pipelines.transcribe_notes.route_notes_transcribe._is_nonempty_file", return_value=True):
            report = run_plan(plan, client=None, academic_hub_root="/dummy", force_vision=True)
            mock_process.assert_called_once_with("some/path/doc.pdf", None, None, "/dummy", force_vision=True)
            assert report.pdf_results[0].status == "ok"

