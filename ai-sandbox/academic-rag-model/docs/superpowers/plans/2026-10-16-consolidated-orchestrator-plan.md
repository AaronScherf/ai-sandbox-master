# Consolidated notes orchestrator (Stage 3, part 2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend `route_notes_transcribe.py` so one command ("update my notes for econometrics") drives a course from raw PDFs/Excalidraw canvases through transcribe → expand → SVG backup → resolve `[Question]` tags → chunk/embed, re-entrant across agent collect/submit sessions.

**Architecture:** `route_notes_transcribe.py`'s existing `build_plan()`/`run_plan()` gain a resolve-questions stage (computed once at plan time, from disk state before any transcription this invocation) and a per-course chunk/embed call. A prerequisite correctness fix refreshes each note's index-card `content_hash` after question resolution, since `chunk_index`'s own staleness check compares stored hashes, never the live file.

**Tech Stack:** Python 3.13, pytest, existing `agent/rag/resolve_questions*.py` and `core/indexer/{index_card,chunk_index}.py` modules.

**Spec:** `docs/superpowers/specs/transcribe_notes/2026-10-16-consolidated-orchestrator-design.md` (and its parent, `2026-10-15-consolidated-pipeline-design.md`).

## Global Constraints

- No hidden generative fallback: `--driver agent` work that isn't submitted yet reports as pending, never silently retried against the metered API.
- `--allow-api-fallback` is submit-time-only, explicit opt-in, never automatic.
- Resumability: each stage's own freshness check decides what's stale; the orchestrator only sequences calls, never duplicates that logic.
- A note transcribed via the agent driver in the same invocation that submitted it is never eligible for resolve-questions collection in that same invocation (snapshot eligibility before transcription runs, never re-query disk mid-call).
- Stage explicit task paths only when committing (`git add <path>`, never `-A`).

## Review Focus

- A note with zero `[Question]` tags must never appear in `resolve_questions_todo` and must never block the chunk step (Task 4's test covers this).
- A note whose index card doesn't exist yet (shouldn't happen in practice, but the hub could be mid-migration) must not crash resolve_note/finalize_note_answers — warn and continue (Task 2).
- `--submit` on a run directory containing a resolve-questions doc-slug that no longer matches any current note (question text changed, re-transcription shifted it) must warn and skip, not crash the whole submit loop (Task 6, mirrors the existing PDF/Excalidraw "no matching pending document" warning already in `main()`).
- `chunk()` failing for one course must not abort the batch for other courses (Task 5 — `chunk()` already isolates failures per-file; the orchestrator must not wrap it in a way that defeats that).
- Running the orchestrator a second time with nothing new to do must not re-call the Gemini API for anything (Task 5's test: a fully resolved, fully chunked course produces zero `resolve_questions_resolved` and `chunk_stats["chunked"] == 0` on a second `run_plan()` call).

---

## Task 1: `update_card_content_hash` index-card helper

**Files:**
- Modify: `core/indexer/index_card.py` (add function after `update_card_paths`, currently ending line 565)
- Test: `tests/core/indexer/test_index_card.py`

**Interfaces:**
- Produces: `update_card_content_hash(academic_hub_root: str, file_id: str, content_hash: str) -> bool`, used by Task 2.

- [ ] **Step 1: Write the failing tests**

Add to `tests/core/indexer/test_index_card.py`, right after the existing `TestUpdateCardPaths` class:

```python
class TestUpdateCardContentHash(unittest.TestCase):
    # resolve_questions.py calls this after apply_markers() rewrites a
    # note's .rag.md with resolved-answer markers -- the card's stored hash
    # must reflect that rewrite, or chunk_index's own staleness check
    # (comparing stored chunk hashes against the card's hash, never the
    # live file) would never notice the change.

    def test_updates_content_hash_without_touching_other_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            reconcile_and_write(tmp, file_id="fid1", path="a.md", source_pdf_path="a.pdf",
                                 course="econ-101", folder_category="textbooks-and-papers",
                                 content_sample="text", page_count=10, client=_fake_client(),
                                 content_hash="hash1")
            found = update_card_content_hash(tmp, "fid1", "hash2")
            self.assertTrue(found)
            card = load_shard(tmp, "econ-101")[0]
            self.assertEqual(card["content_hash"], "hash2")
            self.assertEqual(card["title"], "Linear Algebra Done Right")  # untouched, no regeneration
            self.assertEqual(card["course"], "econ-101")  # untouched, no course move

    def test_returns_false_and_writes_nothing_when_no_card_matches(self):
        with tempfile.TemporaryDirectory() as tmp:
            found = update_card_content_hash(tmp, "no-such-file-id", "hash2")
            self.assertFalse(found)
```

Add `update_card_content_hash` to the existing `from core.indexer.index_card import (...)` import block near the top of the test file (alongside `update_card_paths`).

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/core/indexer/test_index_card.py -k TestUpdateCardContentHash -v`
Expected: FAIL with `ImportError: cannot import name 'update_card_content_hash'`.

- [ ] **Step 3: Implement**

In `core/indexer/index_card.py`, add immediately after `update_card_paths` (after its closing `return True` at line 564):

```python


def update_card_content_hash(academic_hub_root: str, file_id: str, content_hash: str) -> bool:
    """Refreshes only `content_hash` on an existing card by file_id -- no
    regeneration, no path/course change, same no-op-if-missing contract as
    update_card_paths(). Called by resolve_questions.py after
    apply_markers() rewrites a note's .rag.md with resolved-answer markers:
    the card's stored hash must reflect that rewrite, or
    chunk_index.chunk()'s own staleness check (which compares its stored
    chunks' hash against the card's hash, never the live file) would never
    notice the change. Returns False (never raises) if no card exists yet
    for this file_id."""
    found = find_card_by_file_id(academic_hub_root, file_id)
    if found is None:
        return False
    course, card = found
    updated = dict(card)
    updated["content_hash"] = content_hash
    save_shard(academic_hub_root, course, _replace_card(
        load_shard(academic_hub_root, course), file_id, updated,
    ))
    return True
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/core/indexer/test_index_card.py -k TestUpdateCardContentHash -v`
Expected: PASS, 2/2.

- [ ] **Step 5: Commit**

```bash
git add core/indexer/index_card.py tests/core/indexer/test_index_card.py
git commit -m "feat(core/indexer): add update_card_content_hash, a narrow single-field card update"
```

---

## Task 2: Refresh content_hash at both `apply_markers()` call sites

**Files:**
- Modify: `agent/rag/resolve_questions.py` (`resolve_note`, ends at line 375)
- Modify: `agent/rag/resolve_questions_submit.py` (`finalize_note_answers`, ends at line 261)
- Test: `tests/agent/rag/test_resolve_questions.py`
- Test: `tests/agent/rag/test_resolve_questions_submit.py`

**Interfaces:**
- Consumes: `update_card_content_hash` from Task 1.
- Produces: both functions now keep the note's index-card `content_hash` in sync with its `.rag.md` content whenever a card exists.

- [ ] **Step 1: Write the failing tests**

Add to `tests/agent/rag/test_resolve_questions.py` (uses the existing `_hub` fixture, the `rq` alias, and `_fake_resolve` already defined above line 192):

```python
def test_resolve_note_refreshes_the_index_cards_content_hash(tmp_path):
    from core.indexer.index_card import compute_content_hash, load_shard, save_shard

    hub, raw = _hub(tmp_path)
    rel_rag = os.path.relpath(rag_path_for(raw), hub).replace(os.sep, "/")
    save_shard(hub, "microecon", [{"file_id": "fid1", "path": rel_rag, "content_hash": "stale-hash"}])
    with patch.object(rq, "resolve_question", side_effect=_fake_resolve()):
        resolve_note(raw, hub, client=object(), roots=[hub])
    card = load_shard(hub, "microecon")[0]
    assert card["content_hash"] == compute_content_hash(rag_path_for(raw))
    assert card["content_hash"] != "stale-hash"


def test_resolve_note_warns_instead_of_crashing_when_no_card_exists(capsys):
    import tempfile as _tempfile
    with _tempfile.TemporaryDirectory() as tmp_dir:
        import pathlib
        hub, raw = _hub(pathlib.Path(tmp_dir))
        with patch.object(rq, "resolve_question", side_effect=_fake_resolve()):
            resolve_note(raw, hub, client=object(), roots=[hub])  # no card ever created for this hub
        assert "content_hash not refreshed" in capsys.readouterr().out
```

Add to `tests/agent/rag/test_resolve_questions_submit.py` (mirrors the pattern above, for the agent/finalize path). First check its existing fixture helper for building a collected-and-filled run before `finalize_note_answers` -- reuse whatever fixture the existing `test_submit_doc_finalizes_into_the_sidecar_once_both_stages_are_cached` test uses to get a note through to `finalize_note_answers`, and add a card via `save_shard` before calling `submit_doc`, then assert its `content_hash` updated:

```python
def test_submit_doc_refreshes_the_index_cards_content_hash_once_finalized(tmp_path):
    # Reuses the same fixture setup as test_submit_doc_finalizes_into_the_sidecar_once_both_stages_are_cached
    # (see that test for the full collected-run setup this one starts from).
    ...  # build on that test's existing fixture helper; add:
    from core.indexer.index_card import compute_content_hash, load_shard, save_shard
    from core.indexer.questions import rag_path_for
    rel_rag = os.path.relpath(rag_path_for(raw_path), hub).replace(os.sep, "/")
    save_shard(hub, "microecon", [{"file_id": "fid1", "path": rel_rag, "content_hash": "stale-hash"}])
    status = submit_doc(hub, hub, run_id, doc_slug, raw_path, hub, client, model)
    assert status == "complete"
    card = load_shard(hub, "microecon")[0]
    assert card["content_hash"] == compute_content_hash(rag_path_for(raw_path))
```

Read `test_submit_doc_finalizes_into_the_sidecar_once_both_stages_are_cached` in full before writing this test -- copy its exact fixture variable names (`hub`, `raw_path`, `run_id`, `doc_slug`, `client`, `model`, course name) so the new test's `save_shard` call uses the same course and hub-relative path that test's own note actually lives at.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/agent/rag/test_resolve_questions.py tests/agent/rag/test_resolve_questions_submit.py -k "content_hash" -v`
Expected: FAIL — the new tests assert a `content_hash` that never changes from `"stale-hash"` (current code never refreshes it), and the "no card" test finds no `"content_hash not refreshed"` warning in captured output.

- [ ] **Step 3: Implement**

In `agent/rag/resolve_questions.py`, change the import line near the top:

```python
from core.indexer.index_card import derive_course, load_shard
```
to:
```python
from core.indexer.index_card import compute_content_hash, derive_course, load_shard, update_card_content_hash
```

Then change `resolve_note`'s ending (currently):
```python
    apply_markers(raw_path, rag_path)
    return result
```
to:
```python
    apply_markers(raw_path, rag_path)
    if card:
        update_card_content_hash(hub, card["file_id"], compute_content_hash(rag_path))
    else:
        print(f"WARNING: no index card found for {raw_path} -- content_hash not refreshed; "
              f"chunk_index will not notice resolved answers until the card exists.")
    return result
```

In `agent/rag/resolve_questions_submit.py`, add `_note_card` to the existing `from agent.rag.resolve_questions import (...)` block, and add `compute_content_hash`/`update_card_content_hash` to the existing `from core.indexer.index_card import derive_course` line (becomes `from core.indexer.index_card import compute_content_hash, derive_course, update_card_content_hash`).

Then change `finalize_note_answers`'s ending (currently):
```python
    write_sidecar(sidecar, fields, ordered)
    apply_markers(raw_path, rag_path)
```
to:
```python
    write_sidecar(sidecar, fields, ordered)
    apply_markers(raw_path, rag_path)
    card = _note_card(hub, raw_path)
    if card:
        update_card_content_hash(hub, card["file_id"], compute_content_hash(rag_path))
    else:
        print(f"WARNING: no index card found for {raw_path} -- content_hash not refreshed; "
              f"chunk_index will not notice resolved answers until the card exists.")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/agent/rag/test_resolve_questions.py tests/agent/rag/test_resolve_questions_submit.py -v`
Expected: PASS, full file for both (no regressions in the existing suites -- the "no card" case already matches every existing fixture, which never creates a card, so this is also an implicit regression check).

- [ ] **Step 5: Commit**

```bash
git add agent/rag/resolve_questions.py agent/rag/resolve_questions_submit.py tests/agent/rag/test_resolve_questions.py tests/agent/rag/test_resolve_questions_submit.py
git commit -m "fix(agent/rag): refresh the index card's content_hash after resolving questions"
```

---

## Task 3: `discover_pending_notes` eligibility helper

**Files:**
- Modify: `agent/rag/resolve_questions.py` (add after `discover_notes`, currently ending line 214)
- Test: `tests/agent/rag/test_resolve_questions.py`

**Interfaces:**
- Consumes: `discover_notes`, `_note_card`, `_read_body` (all already in this module).
- Produces: `discover_pending_notes(hub: str, course: str | None = None, note: str | None = None) -> list[str]`, used by Task 4.

- [ ] **Step 1: Write the failing tests**

Add to `tests/agent/rag/test_resolve_questions.py`:

```python
def test_discover_pending_notes_includes_a_note_with_unanswered_tags(tmp_path):
    hub, raw = _hub(tmp_path)
    assert discover_pending_notes(hub) == [raw]


def test_discover_pending_notes_excludes_a_fully_answered_note(tmp_path):
    hub, raw = _hub(tmp_path)
    with patch.object(rq, "resolve_question", side_effect=_fake_resolve()):
        resolve_note(raw, hub, client=object(), roots=[hub])
    assert discover_pending_notes(hub) == []


def test_discover_pending_notes_excludes_a_subset_of_note(tmp_path):
    from core.indexer.index_card import save_shard

    hub, raw = _hub(tmp_path)
    rel_rag = os.path.relpath(rag_path_for(raw), hub).replace(os.sep, "/")
    save_shard(hub, "microecon", [{"file_id": "fid1", "path": rel_rag, "subset_of": "other-fid"}])
    assert discover_pending_notes(hub) == []
```

Add `discover_pending_notes` to the `from agent.rag.resolve_questions import discover_notes, resolve_note` import line.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/agent/rag/test_resolve_questions.py -k discover_pending_notes -v`
Expected: FAIL with `ImportError: cannot import name 'discover_pending_notes'`.

- [ ] **Step 3: Implement**

In `agent/rag/resolve_questions.py`, add immediately after `discover_notes` (after its closing `return sorted(found)` at line 214):

```python


def discover_pending_notes(hub: str, course: str | None = None, note: str | None = None) -> list[str]:
    """Notes from discover_notes() that still have at least one unanswered
    question and are not a subset-of duplicate of another note -- the same
    filter resolve_questions.py's own CLI already applies before resolving
    or staging anything (see main()'s collect/plain-run loops), factored
    out so a caller like the consolidated orchestrator can compute
    eligibility without duplicating it."""
    pending = []
    for raw_path in discover_notes(hub, course, note):
        card = _note_card(hub, raw_path)
        if card and card.get("subset_of"):
            continue
        answered = {e.qid for e in read_sidecar(sidecar_path_for(raw_path))[1]}
        if any(t.qid not in answered for t in find_tags(_read_body(raw_path))):
            pending.append(raw_path)
    return pending
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/agent/rag/test_resolve_questions.py -v`
Expected: PASS, full file (no regressions).

- [ ] **Step 5: Commit**

```bash
git add agent/rag/resolve_questions.py tests/agent/rag/test_resolve_questions.py
git commit -m "feat(agent/rag): add discover_pending_notes, the resolve-questions eligibility filter"
```

---

## Task 4: `PipelinePlan` gains `courses` and `resolve_questions_todo`

**Files:**
- Modify: `pipelines/transcribe_notes/route_notes_transcribe.py` (`PipelinePlan` dataclass at line 301, `build_plan()` at line 309)
- Test: `tests/pipelines/transcribe_notes/test_route_notes_transcribe.py`

**Interfaces:**
- Consumes: `discover_pending_notes` from Task 3.
- Produces: `PipelinePlan.courses: list[str]`, `PipelinePlan.resolve_questions_todo: list[str]`, used by Tasks 5 and 6.

- [ ] **Step 1: Write the failing tests**

Add to `tests/pipelines/transcribe_notes/test_route_notes_transcribe.py`:

```python
def test_build_plan_records_the_target_courses(tmp_path):
    _make_course(tmp_path, "econometrics", "lecture_notes", {})
    _make_course(tmp_path, "microecon", "lecture_notes", {})
    plan = build_plan(str(tmp_path))
    assert plan.courses == ["econometrics", "microecon"]


def test_build_plan_respects_course_filter_for_courses_list(tmp_path):
    _make_course(tmp_path, "econometrics", "lecture_notes", {})
    _make_course(tmp_path, "microecon", "lecture_notes", {})
    plan = build_plan(str(tmp_path), courses=["microecon"])
    assert plan.courses == ["microecon"]


def _make_note_with_an_unanswered_question(tmp_path, course, name="N 2026-09-15"):
    out = tmp_path / "academic_notes" / course / "lecture_notes" / "processed_outputs"
    out.mkdir(parents=True, exist_ok=True)
    raw = out / f"{name}.excalidraw.md"
    raw.write_text("---\nchunks: 1\n---\n\n**[Handwritten]**\n[Question] why?\n", encoding="utf-8")
    (out / f"{name}.excalidraw.rag.md").write_text(
        "---\nx: y\n---\n\n[Question] why?\n", encoding="utf-8",
    )
    return str(raw)


def test_build_plan_includes_notes_with_unanswered_questions(tmp_path):
    raw = _make_note_with_an_unanswered_question(tmp_path, "microecon")
    plan = build_plan(str(tmp_path), courses=["microecon"])
    assert plan.resolve_questions_todo == [raw]


def test_build_plan_excludes_notes_with_no_question_tags(tmp_path):
    _make_course(tmp_path, "microecon", "lecture_notes", {})
    out = tmp_path / "academic_notes" / "microecon" / "lecture_notes" / "processed_outputs"
    out.mkdir(parents=True, exist_ok=True)
    (out / "N.excalidraw.md").write_text("---\nchunks: 1\n---\n\nno questions here\n", encoding="utf-8")
    (out / "N.excalidraw.rag.md").write_text("---\nx: y\n---\n\nno questions here\n", encoding="utf-8")
    plan = build_plan(str(tmp_path), courses=["microecon"])
    assert plan.resolve_questions_todo == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/pipelines/transcribe_notes/test_route_notes_transcribe.py -k "courses or unanswered_question or no_question_tags" -v`
Expected: FAIL — `PipelinePlan` has no `courses`/`resolve_questions_todo` attribute yet.

- [ ] **Step 3: Implement**

In `pipelines/transcribe_notes/route_notes_transcribe.py`, add the import near the other top-level imports (after the `transcribe_notes` import):

```python
from agent.rag.resolve_questions import discover_pending_notes
```

Change the `PipelinePlan` dataclass (currently):
```python
@dataclass
class PipelinePlan:
    pdf_todo: list[str] = field(default_factory=list)
    pdf_skipped: list[str] = field(default_factory=list)
    excalidraw_todo: list[tuple[str, str]] = field(default_factory=list)
    excalidraw_skipped: list[tuple[str, str]] = field(default_factory=list)
```
to:
```python
@dataclass
class PipelinePlan:
    pdf_todo: list[str] = field(default_factory=list)
    pdf_skipped: list[str] = field(default_factory=list)
    excalidraw_todo: list[tuple[str, str]] = field(default_factory=list)
    excalidraw_skipped: list[tuple[str, str]] = field(default_factory=list)
    courses: list[str] = field(default_factory=list)
    resolve_questions_todo: list[str] = field(default_factory=list)
```

Change `build_plan()`'s body: replace
```python
    target_courses = courses if courses is not None else find_course_dirs(academic_hub_root)
    plan = PipelinePlan()
    for course in target_courses:
```
with
```python
    target_courses = courses if courses is not None else find_course_dirs(academic_hub_root)
    plan = PipelinePlan(courses=list(target_courses))
    for course in target_courses:
```

And add, at the end of the `for course in target_courses:` loop body (after the existing `plan.excalidraw_skipped.extend(...)` line, still inside the loop):
```python
        plan.resolve_questions_todo.extend(discover_pending_notes(academic_hub_root, course=course))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/pipelines/transcribe_notes/test_route_notes_transcribe.py -v`
Expected: PASS, full file (no regressions in the many existing `build_plan` tests — they never created courses with questions, so `resolve_questions_todo` stays `[]` for them, and they don't assert on `courses` either).

- [ ] **Step 5: Commit**

```bash
git add pipelines/transcribe_notes/route_notes_transcribe.py tests/pipelines/transcribe_notes/test_route_notes_transcribe.py
git commit -m "feat(transcribe_notes): PipelinePlan tracks target courses and resolve-questions eligibility"
```

---

## Task 5: `run_plan()` resolves questions and chunks (API-driver path)

**Files:**
- Modify: `pipelines/transcribe_notes/route_notes_transcribe.py` (`RunReport` at line 350, `run_plan()` at line 356, `print_summary()` at line 420)
- Test: `tests/pipelines/transcribe_notes/test_route_notes_transcribe.py`

**Interfaces:**
- Consumes: `plan.resolve_questions_todo`, `plan.courses` from Task 4; `resolve_note` from `agent/rag/resolve_questions.py`; `chunk` from `core/indexer/chunk_index.py`.
- Produces: `RunReport.resolve_questions_resolved: int`, `RunReport.resolve_questions_failed: list[str]`, `RunReport.chunk_stats: dict`, read by `print_summary()` and by Final Verification's dry-run.

- [ ] **Step 1: Write the failing tests**

Add to `tests/pipelines/transcribe_notes/test_route_notes_transcribe.py`:

```python
def test_run_plan_resolves_pending_questions_via_the_api_driver(tmp_path):
    raw = _make_note_with_an_unanswered_question(tmp_path, "microecon")
    plan = PipelinePlan(courses=["microecon"], resolve_questions_todo=[raw])
    with patch("pipelines.transcribe_notes.route_notes_transcribe.resolve_note") as mock_resolve:
        from agent.rag.resolve_questions import NoteResult
        mock_resolve.return_value = NoteResult(resolved=1, skipped=0, failed=[])
        report = run_plan(plan, object(), str(tmp_path))
    mock_resolve.assert_called_once_with(raw, str(tmp_path), unittest.mock.ANY, [str(tmp_path)])
    assert report.resolve_questions_resolved == 1
    assert report.resolve_questions_failed == []


def test_run_plan_records_resolve_questions_failures_without_stopping(tmp_path):
    raw1 = _make_note_with_an_unanswered_question(tmp_path, "microecon", name="N1")
    raw2 = _make_note_with_an_unanswered_question(tmp_path, "microecon", name="N2")
    plan = PipelinePlan(courses=["microecon"], resolve_questions_todo=[raw1, raw2])
    from agent.rag.resolve_questions import NoteResult
    with patch(
        "pipelines.transcribe_notes.route_notes_transcribe.resolve_note",
        side_effect=[RuntimeError("boom"), NoteResult(resolved=1, skipped=0, failed=[])],
    ):
        report = run_plan(plan, object(), str(tmp_path))
    assert report.resolve_questions_resolved == 1
    assert report.resolve_questions_failed == [raw1]


def test_run_plan_does_not_resolve_questions_in_collect_mode(tmp_path):
    raw = _make_note_with_an_unanswered_question(tmp_path, "microecon")
    plan = PipelinePlan(courses=["microecon"], resolve_questions_todo=[raw])
    with patch("pipelines.transcribe_notes.route_notes_transcribe.resolve_note") as mock_resolve:
        run_plan(plan, None, str(tmp_path), collect_mode=True)
    mock_resolve.assert_not_called()


def test_run_plan_chunks_every_targeted_course(tmp_path):
    plan = PipelinePlan(courses=["microecon", "econometrics"])
    with patch("pipelines.transcribe_notes.route_notes_transcribe.chunk_notes") as mock_chunk:
        mock_chunk.return_value = {"chunked": 1, "unchanged": 2, "failed": 0, "skipped_no_embedding": 0}
        report = run_plan(plan, object(), str(tmp_path))
    assert mock_chunk.call_count == 2
    assert report.chunk_stats == {"chunked": 2, "unchanged": 4, "failed": 0, "skipped_no_embedding": 0}


def test_run_plan_does_not_chunk_in_collect_mode(tmp_path):
    plan = PipelinePlan(courses=["microecon"])
    with patch("pipelines.transcribe_notes.route_notes_transcribe.chunk_notes") as mock_chunk:
        run_plan(plan, None, str(tmp_path), collect_mode=True)
    mock_chunk.assert_not_called()
```

Add `unittest.mock` (for `ANY`) and `PipelinePlan` (if not already imported — it is) to the test file's imports; `_make_note_with_an_unanswered_question` is the Task 4 helper already in this file.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/pipelines/transcribe_notes/test_route_notes_transcribe.py -k "resolve_questions_via or resolve_questions_failures or collect_mode or chunks_every" -v`
Expected: FAIL — `resolve_note`/`chunk_notes` aren't imported into `route_notes_transcribe`'s namespace yet (patch target doesn't exist), and `RunReport` has no `resolve_questions_resolved`/`chunk_stats` fields.

- [ ] **Step 3: Implement**

In `pipelines/transcribe_notes/route_notes_transcribe.py`, change the `discover_pending_notes` import line from Task 4 to also pull `resolve_note`:
```python
from agent.rag.resolve_questions import discover_pending_notes, resolve_note
```
and add, alongside the other top-level imports:
```python
from core.indexer.chunk_index import chunk as chunk_notes
```

Change `RunReport` (currently):
```python
@dataclass
class RunReport:
    pdf_results: list[RunResult] = field(default_factory=list)
    excalidraw_results: list[RunResult] = field(default_factory=list)
```
to:
```python
@dataclass
class RunReport:
    pdf_results: list[RunResult] = field(default_factory=list)
    excalidraw_results: list[RunResult] = field(default_factory=list)
    resolve_questions_resolved: int = 0
    resolve_questions_failed: list[str] = field(default_factory=list)
    chunk_stats: dict = field(default_factory=lambda: {
        "chunked": 0, "unchanged": 0, "failed": 0, "skipped_no_embedding": 0,
    })
```

In `run_plan()`, add a new parameter and extend the body. Change the signature (currently):
```python
def run_plan(
    plan: PipelinePlan, client, academic_hub_root: str,
    pdf_model: str | None = None, excalidraw_model: str | None = None,
    expand_backend: str = "gemini", use_grounding: bool = False,
    force_vision: bool = False,
    driver: "TranscriptionDriver | None" = None, collect_mode: bool = False,
    excalidraw_driver=None,
) -> RunReport:
```
to:
```python
def run_plan(
    plan: PipelinePlan, client, academic_hub_root: str,
    pdf_model: str | None = None, excalidraw_model: str | None = None,
    expand_backend: str = "gemini", use_grounding: bool = False,
    force_vision: bool = False,
    driver: "TranscriptionDriver | None" = None, collect_mode: bool = False,
    excalidraw_driver=None, resolve_questions_model: str | None = None,
) -> RunReport:
```

Add, right before the function's existing `return report` (at the end of `run_plan`, after the Excalidraw loop):
```python
    if not collect_mode:
        for raw_path in plan.resolve_questions_todo:
            try:
                note_result = resolve_note(
                    raw_path, academic_hub_root, client, [academic_hub_root],
                    **({"model": resolve_questions_model} if resolve_questions_model else {}),
                )
            except Exception as err:
                print(f"ERROR: resolve-questions failed for {raw_path}: {err}")
                report.resolve_questions_failed.append(raw_path)
                continue
            report.resolve_questions_resolved += note_result.resolved
            report.resolve_questions_failed.extend(note_result.failed)

        for course_name in plan.courses:
            stats = chunk_notes(academic_hub_root, client, course=course_name)
            for key in report.chunk_stats:
                report.chunk_stats[key] += stats.get(key, 0)

    return report
```

Note the test `test_run_plan_resolves_pending_questions_via_the_api_driver` asserts the call with exactly 4 positional args (no `model=` kwarg) since `resolve_questions_model` defaults to `None` in that test — the `**({"model": ...} if ... else {})` pattern keeps the call signature matching `resolve_note`'s own default (`model: str = RESOLVER_MODEL`) rather than ever passing `model=None`.

Update `print_summary()` (currently ending with the `for r in problems:` loop) by adding, right after that loop:
```python
    if report.resolve_questions_resolved or report.resolve_questions_failed:
        print(f"Resolve-questions: {report.resolve_questions_resolved} resolved, "
              f"{len(report.resolve_questions_failed)} failed")
    cs = report.chunk_stats
    if any(cs.values()):
        print(f"Chunk/embed: {cs['chunked']} chunked, {cs['unchanged']} unchanged, "
              f"{cs['failed']} failed, {cs['skipped_no_embedding']} skipped (no embedding)")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/pipelines/transcribe_notes/test_route_notes_transcribe.py -v`
Expected: PASS, full file (no regressions — every pre-existing `run_plan()` call in older tests either passes `collect_mode=True` explicitly or a `plan` whose `courses`/`resolve_questions_todo` default to `[]`, so the new loops are no-ops for them).

- [ ] **Step 5: Commit**

```bash
git add pipelines/transcribe_notes/route_notes_transcribe.py tests/pipelines/transcribe_notes/test_route_notes_transcribe.py
git commit -m "feat(transcribe_notes): run_plan resolves pending questions and chunks every targeted course"
```

---

## Task 6: Agent-driven collect/submit wiring + dry-run preview + CLI pass-through

**Files:**
- Modify: `pipelines/transcribe_notes/route_notes_transcribe.py` (`main()`, currently lines 491-677)
- Test: `tests/pipelines/transcribe_notes/test_route_notes_transcribe.py`

**Interfaces:**
- Consumes: `plan.resolve_questions_todo` (Task 4), `resolve_note`'s `driver`/`collect_mode` kwargs and `agent.rag.resolve_questions_submit.submit_doc` (pre-existing), `chunk_notes` (Task 5).
- Produces: `resolve_questions_slug_map(plan: PipelinePlan) -> dict[str, str]`, the only new testable unit this task adds — everything else is `main()` wiring, consistent with `main()`'s existing untested-directly style (verified instead by Final Verification's real-corpus `--dry-run`).

- [ ] **Step 1: Write the failing test**

Add to `tests/pipelines/transcribe_notes/test_route_notes_transcribe.py`:

```python
def test_resolve_questions_slug_map_matches_resolve_questions_own_slug_scheme(tmp_path):
    from core.indexer.index_card import compute_file_id
    from pipelines.transcribe_notes.agent_work import doc_slug_for

    raw = tmp_path / "N.excalidraw.md"
    raw.write_text("content", encoding="utf-8")
    plan = PipelinePlan(resolve_questions_todo=[str(raw)])
    slug_map = resolve_questions_slug_map(plan)
    assert slug_map == {doc_slug_for(str(raw), compute_file_id(str(raw))): str(raw)}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/pipelines/transcribe_notes/test_route_notes_transcribe.py -k resolve_questions_slug_map -v`
Expected: FAIL with `ImportError: cannot import name 'resolve_questions_slug_map'`.

- [ ] **Step 3: Implement**

In `pipelines/transcribe_notes/route_notes_transcribe.py`, add this function right after `print_backup_summary` (before `_build_arg_parser`):

```python
def resolve_questions_slug_map(plan: PipelinePlan) -> dict[str, str]:
    """doc_slug -> raw_path for every note in plan.resolve_questions_todo,
    using the same file_id-derived slug scheme resolve_questions.py's own
    --collect/--submit use -- lets this module's submit loop match
    resolve-questions task-card directories alongside its own PDF/
    Excalidraw ones under the same .agent_work/<run-id>/ tree."""
    from core.indexer.index_card import compute_file_id
    from pipelines.transcribe_notes.agent_work import doc_slug_for

    return {doc_slug_for(p, compute_file_id(p)): p for p in plan.resolve_questions_todo}
```

Now wire `main()`. First, the `--dry-run` branch (currently):
```python
    if args.dry_run:
        for p in plan.pdf_todo:
            print(f"  [pdf] would process: {p}")
        for md, img in plan.excalidraw_todo:
            print(f"  [excalidraw] would process: {md} (+ {os.path.basename(img)})")
        for r in sync_resource_backups(all_excalidraw_pairs, dry_run=True):
            if r.status == "copied":
                print(f"  [backup] would copy: {r.source} -> {r.dest}")
        return
```
becomes:
```python
    if args.dry_run:
        for p in plan.pdf_todo:
            print(f"  [pdf] would process: {p}")
        for md, img in plan.excalidraw_todo:
            print(f"  [excalidraw] would process: {md} (+ {os.path.basename(img)})")
        for r in sync_resource_backups(all_excalidraw_pairs, dry_run=True):
            if r.status == "copied":
                print(f"  [backup] would copy: {r.source} -> {r.dest}")
        for raw_path in plan.resolve_questions_todo:
            print(f"  [resolve-questions] would process: {raw_path}")
        return
```

Next, the `--collect` branch. Change (currently):
```python
        pdf_driver = AgentDriver(str(academic_hub_dir), run_id)
        excalidraw_driver = ExcalidrawAgentDriver(str(academic_hub_dir), run_id)
        try:
            with corpus_write_lock(
                [academic_hub_dir, academic_hub_dir / "academic_notes"],
                "route notes transcription (agent collect)",
            ):
                backup_results = sync_resource_backups(all_excalidraw_pairs)
                report = run_plan(
                    plan, None, str(academic_hub_dir), pdf_model=args.pdf_model,
                    force_vision=args.force_vision, driver=pdf_driver, collect_mode=True,
                    excalidraw_driver=excalidraw_driver, use_grounding=args.grounding,
                )
        except CorpusWriteLockError as exc:
            raise SystemExit(str(exc)) from exc
        print_backup_summary(backup_results)
        print_summary(plan, report)
        print(f"Collect run '{run_id}' complete under {academic_hub_dir / '.agent_work' / run_id}.")
        return
```
to:
```python
        from agent.rag.resolve_questions_agent_work import QuestionResolverAgentDriver

        pdf_driver = AgentDriver(str(academic_hub_dir), run_id)
        excalidraw_driver = ExcalidrawAgentDriver(str(academic_hub_dir), run_id)
        rq_client = None
        if plan.resolve_questions_todo:
            rq_client = get_gemini_client("PAID_GEMINI_KEY" if args.use_paid_key else "GEMINI_API_KEY")
            if rq_client is None:
                sys.exit(1)
        try:
            with corpus_write_lock(
                [academic_hub_dir, academic_hub_dir / "academic_notes"],
                "route notes transcription (agent collect)",
            ):
                backup_results = sync_resource_backups(all_excalidraw_pairs)
                report = run_plan(
                    plan, None, str(academic_hub_dir), pdf_model=args.pdf_model,
                    force_vision=args.force_vision, driver=pdf_driver, collect_mode=True,
                    excalidraw_driver=excalidraw_driver, use_grounding=args.grounding,
                )
                rq_driver = QuestionResolverAgentDriver(str(academic_hub_dir), run_id)
                for raw_path in plan.resolve_questions_todo:
                    try:
                        resolve_note(
                            raw_path, str(academic_hub_dir), rq_client, [str(academic_hub_dir)],
                            driver=rq_driver, collect_mode=True,
                        )
                    except AgentPending:
                        pass
                    except Exception as err:
                        print(f"ERROR: resolve-questions collect failed for {raw_path}: {err}")
        except CorpusWriteLockError as exc:
            raise SystemExit(str(exc)) from exc
        print_backup_summary(backup_results)
        print_summary(plan, report)
        print(f"Collect run '{run_id}' complete under {academic_hub_dir / '.agent_work' / run_id}.")
        return
```

Next, the `--submit` branch. Change (currently):
```python
        pdf_by_slug = {doc_slug_for(p, compute_file_id(p)): p for p in plan.pdf_todo}
        excalidraw_by_slug = {
            doc_slug_for(md, compute_file_id(md)): (md, img) for md, img in plan.excalidraw_todo
        }
        try:
            with corpus_write_lock(
                [academic_hub_dir, academic_hub_dir / "academic_notes"],
                "route notes transcription (agent submit)",
            ):
                backup_results = sync_resource_backups(all_excalidraw_pairs)
                for doc_slug in sorted(os.listdir(run_dir)):
                    pdf_path = pdf_by_slug.get(doc_slug)
                    excalidraw_pair = excalidraw_by_slug.get(doc_slug)
                    if pdf_path is None and excalidraw_pair is None:
                        print(f"WARNING: no matching pending document for collected doc '{doc_slug}' "
                              f"(already submitted, or outside this --course filter?) -- skipping.")
                        continue
                    try:
                        if pdf_path is not None:
                            status = submit_pdf_doc(
                                str(academic_hub_dir), str(academic_hub_dir), args.submit, doc_slug,
                                pdf_path, client, args.pdf_model, force_vision=args.force_vision,
                                allow_api_fallback=args.allow_api_fallback,
                            )
                        else:
                            md_path, image_path = excalidraw_pair
                            status = submit_excalidraw_doc(
                                str(academic_hub_dir), str(academic_hub_dir), args.submit, doc_slug,
                                md_path, image_path, client, args.excalidraw_model or _EXCALIDRAW_MODEL,
                                expand_backend=args.expand_backend, allow_api_fallback=args.allow_api_fallback,
                                use_grounding=args.grounding,
                            )
                    except Exception as err:
                        print(f"[{doc_slug}] error: {err}")
                        continue
                    print(f"[{doc_slug}] {status}")
        except CorpusWriteLockError as exc:
            raise SystemExit(str(exc)) from exc
        print_backup_summary(backup_results)
        return
```
to:
```python
        from agent.rag.resolve_questions_submit import submit_doc as submit_resolve_questions_doc

        pdf_by_slug = {doc_slug_for(p, compute_file_id(p)): p for p in plan.pdf_todo}
        excalidraw_by_slug = {
            doc_slug_for(md, compute_file_id(md)): (md, img) for md, img in plan.excalidraw_todo
        }
        resolve_questions_by_slug = resolve_questions_slug_map(plan)
        try:
            with corpus_write_lock(
                [academic_hub_dir, academic_hub_dir / "academic_notes"],
                "route notes transcription (agent submit)",
            ):
                backup_results = sync_resource_backups(all_excalidraw_pairs)
                for doc_slug in sorted(os.listdir(run_dir)):
                    pdf_path = pdf_by_slug.get(doc_slug)
                    excalidraw_pair = excalidraw_by_slug.get(doc_slug)
                    raw_path = resolve_questions_by_slug.get(doc_slug)
                    if pdf_path is None and excalidraw_pair is None and raw_path is None:
                        print(f"WARNING: no matching pending document for collected doc '{doc_slug}' "
                              f"(already submitted, or outside this --course filter?) -- skipping.")
                        continue
                    try:
                        if pdf_path is not None:
                            status = submit_pdf_doc(
                                str(academic_hub_dir), str(academic_hub_dir), args.submit, doc_slug,
                                pdf_path, client, args.pdf_model, force_vision=args.force_vision,
                                allow_api_fallback=args.allow_api_fallback,
                            )
                        elif excalidraw_pair is not None:
                            md_path, image_path = excalidraw_pair
                            status = submit_excalidraw_doc(
                                str(academic_hub_dir), str(academic_hub_dir), args.submit, doc_slug,
                                md_path, image_path, client, args.excalidraw_model or _EXCALIDRAW_MODEL,
                                expand_backend=args.expand_backend, allow_api_fallback=args.allow_api_fallback,
                                use_grounding=args.grounding,
                            )
                        else:
                            status = submit_resolve_questions_doc(
                                str(academic_hub_dir), str(academic_hub_dir), args.submit, doc_slug,
                                raw_path, str(academic_hub_dir), client, args.resolve_questions_model,
                                allow_api_fallback=args.allow_api_fallback,
                            )
                    except Exception as err:
                        print(f"[{doc_slug}] error: {err}")
                        continue
                    print(f"[{doc_slug}] {status}")
                for course_name in plan.courses:
                    chunk_notes(str(academic_hub_dir), client, course=course_name)
        except CorpusWriteLockError as exc:
            raise SystemExit(str(exc)) from exc
        print_backup_summary(backup_results)
        return
```

`args.model` does not exist on `route_notes_transcribe.py`'s parser today (it has `--pdf-model`/`--excalidraw-model`, not a shared `--model`). Add one new argument in `_build_arg_parser()`, right after the `--excalidraw-model` line:
```python
    parser.add_argument("--resolve-questions-model", default=None,
                         help="Model override for agent/rag/resolve_questions.py (default: its own RESOLVER_MODEL).")
```
and use `args.resolve_questions_model` (not `args.model`) in the `submit_resolve_questions_doc` call above, and also pass it through to the plain/API branch's `run_plan()` call (Step 3 below).

Finally, the plain (`--driver api`, fully metered) branch at the bottom of `main()`. Change (currently):
```python
    total_todo = len(plan.pdf_todo) + len(plan.excalidraw_todo)
    if total_todo == 0 and not all_excalidraw_pairs:
        print("Nothing to do.")
        return

    client = None
    if total_todo > 0:
        client = get_gemini_client("PAID_GEMINI_KEY" if args.use_paid_key else "GEMINI_API_KEY")
        if client is None:
            sys.exit(1)

    try:
        # The router writes Markdown in the nested notes repository and
        # cards in the outer hub index. Keep both leases for the whole batch.
        with corpus_write_lock(
            [academic_hub_dir, academic_hub_dir / "academic_notes"],
            "route notes transcription",
        ):
            backup_results = sync_resource_backups(all_excalidraw_pairs)
            report = (
                run_plan(
                    plan, client, str(academic_hub_dir),
                    pdf_model=args.pdf_model, excalidraw_model=args.excalidraw_model,
                    expand_backend=args.expand_backend, use_grounding=args.grounding,
                    force_vision=args.force_vision,
                )
                if total_todo > 0 else RunReport()
            )
    except CorpusWriteLockError as exc:
        raise SystemExit(str(exc)) from exc
    print_backup_summary(backup_results)
    print_summary(plan, report)
```
to:
```python
    total_todo = len(plan.pdf_todo) + len(plan.excalidraw_todo) + len(plan.resolve_questions_todo)
    if total_todo == 0 and not all_excalidraw_pairs and not plan.courses:
        print("Nothing to do.")
        return

    client = get_gemini_client("PAID_GEMINI_KEY" if args.use_paid_key else "GEMINI_API_KEY")
    if client is None:
        sys.exit(1)

    try:
        # The router writes Markdown in the nested notes repository and
        # cards in the outer hub index. Keep both leases for the whole batch.
        with corpus_write_lock(
            [academic_hub_dir, academic_hub_dir / "academic_notes"],
            "route notes transcription",
        ):
            backup_results = sync_resource_backups(all_excalidraw_pairs)
            report = run_plan(
                plan, client, str(academic_hub_dir),
                pdf_model=args.pdf_model, excalidraw_model=args.excalidraw_model,
                expand_backend=args.expand_backend, use_grounding=args.grounding,
                force_vision=args.force_vision, resolve_questions_model=args.resolve_questions_model,
            )
    except CorpusWriteLockError as exc:
        raise SystemExit(str(exc)) from exc
    print_backup_summary(backup_results)
    print_summary(plan, report)
```

This drops the old "only construct a client / only call run_plan when there's transcription todo" shortcut — `run_plan()` now always does useful work when `plan.courses` is non-empty (resolve-questions and chunk/embed), so a client is needed whenever there's at least one course, matching this branch's new scope. The `at least one course exists` guard (`not plan.courses`) replaces the old `total_todo == 0` short-circuit for the "truly nothing in this hub" case.

Also add `AgentPending` is already imported at the top of the file (`from pipelines.transcribe_notes.agent_driver import AgentPending`) — no new import needed for the collect branch's `except AgentPending:`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/pipelines/transcribe_notes/test_route_notes_transcribe.py -v`
Expected: PASS, full file.

- [ ] **Step 5: Commit**

```bash
git add pipelines/transcribe_notes/route_notes_transcribe.py tests/pipelines/transcribe_notes/test_route_notes_transcribe.py
git commit -m "feat(transcribe_notes): wire resolve-questions and chunk/embed into collect/submit/plain CLI paths"
```

---

## Final Verification

- [ ] Run the full package suite: `python -m pytest tests/ -q`. Expected: all green, no regressions anywhere (not just the files touched above — `core/indexer/index_card.py` and `agent/rag/resolve_questions*.py` have callers elsewhere in the package).
- [ ] Real-corpus smoke test (per this spec's and the parent spec's acceptance evidence convention): `python -m pipelines.transcribe_notes.route_notes_transcribe --course microecon --dry-run` against the real `academic-hub` — confirm the new `[resolve-questions] would process: ...` lines appear for any course with unresolved questions, and that nothing is written (it's `--dry-run`).
- [ ] Confirm `print_summary()`'s new "Resolve-questions:" and "Chunk/embed:" lines appear in a real (non-dry-run) `--driver api` invocation against a small `--course` slice, or in a `--collect`/`--submit` pair against `.agent_work/`, whichever the owner prefers to run first.

## Acceptance evidence

Every task's test command above, plus Final Verification's full-suite run and real-corpus dry-run. No live Gemini API calls occur in any automated test — every test that reaches a code path which would otherwise call the API either mocks `resolve_note`/`chunk_notes`/`resolve_question`, or (Task 2's card-refresh tests) only exercises the local sidecar/marker-writing path with a `client=object()` placeholder the mocked `resolve_question` never touches.
