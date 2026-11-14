# Framed Excalidraw Explainer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One instruction ("run the explanation pipeline for this canvas") collects framed slide/ink facts, lets the subscription agent write a `result.json`, and an in-vault script places two-paragraph cards and handwriting sections consistently with the auto-framer, with total ink coverage.

**Architecture:** Python (`pipelines/transcribe_notes/framed_explainer/`) reads a scene read-only, builds course context and frame rasters, stages a task card under `.agent_work/`, and validates/resolves the agent's `result.json`. Two Obsidian scripts in the nested vault do all scene writes: the amended `Auto-Frame Slides.md` (cards, sections, no-slide mode) and a new `Apply Explanations.md` (validate, audit, place, save). JS logic is tested through the `__..._EXPORTS__` hook pattern the framer already uses.

**Tech Stack:** Python 3.13 + pytest, `lzstring` (add to `requirements.txt`), PyMuPDF (already present), Node `node:test` with `vm`, Obsidian Excalidraw Automation (EA).

**Spec:** [`docs/superpowers/specs/transcribe_notes/2026-11-13-framed-explainer-design.md`](../../specs/transcribe_notes/2026-11-13-framed-explainer-design.md) (spec commit `3262824c`). Executors read it alongside this plan.

## Global Constraints

- **Two repos, two worktrees.** Outer monorepo work goes on `claude/framed-explainer-impl` in `.worktrees/claude-framed-explainer-impl` (branch from `claude/framed-explainer-spec`). Nested `academic-hub/academic_notes` work (framer, apply script) goes on `claude/framed-explainer-notes` in a worktree of that repo. Never mix commits; stage explicit paths; no `git add -A`.
- Node tests live in the outer repo (`tests/pipelines/transcribe_notes/*.cjs`) and load nested scripts via env var (`AUTO_FRAME_SCRIPT`, `APPLY_EXPLANATIONS_SCRIPT`) pointing at the nested worktree file. Run: `node --test tests/pipelines/transcribe_notes/<file>.cjs`. The 22 existing framer tests must stay green.
- Only the in-vault scripts write a scene or sidecar. Python and the agent never write `.excalidraw.md`. The agent writes only `result.json`.
- Result schema `1`; `prompt_version` `explainer-v1`; card = **exactly two** paragraphs when `status` is `ok`.
- Card key = `<scene namespace>|<frame id>|<slide element id>`; section key = `<scene namespace>|<anchor slide id or "standalone">|<section seq>`. Cards carry `customData.autoExplainKey`.
- Nearest-slide fallback accepted only when nearest distance `< 0.5 x` second-nearest and no other group's ink lies between. Section is anchored only if within `1.5 x` slide width of a slide; otherwise standalone.
- Card slot: top-aligned with the slide, right of it, gap `4%` of slide width, width = slide width clamped to free frame width. Frame names: `018 Slide 18 · notes 1`; no-slide mode: `Notes 001`.
- Ink regions use the framer's rules: `inkGapX 75, inkGapY 55, inkMaxW 1200, inkMaxH 850`.
- Course context cap about 2,000 tokens; neighbour window default +/-7 days; context is hint-only, `context_assisted` flag.
- States: `pending -> generated -> validated -> applied -> verified`; terminal `needs_review`, `placement_conflict`, `declined`, `skipped_existing`; same fingerprint at `verified` is `noop`; changed fingerprint is `stale`, one replacement.
- No metered API, no silent provider fallback; `provider` is recorded. Warn before any call over $1.
- Windows/CRLF: read and write with `newline=''`; JSON and ID files `newline='\n'`. Run Python as modules from `ai-sandbox/academic-rag-model/`; full suite via `python tools/run_tests_chunked.py`.
- **Spec deviation (owner to confirm):** sections are written to a separate `<scene>.sections.json` by the apply script, not into the owner-verified `<scene>.slide-order.json`. Task 9 amends the spec accordingly.

## Review Focus

1. **Scene with no slides and no strokes, or only deleted elements** -> clean "nothing to do", exit 0, no files written (Task 6).
2. **A stroke ID listed twice** (slide ink and a section, or two slides) -> rejected before any write (Tasks 7, 12).
3. **LaTeX with `$`, backslashes, unicode and CRLF in transcriptions/paragraphs** survive `result.json` and card creation unchanged (Task 7).
4. **Paragraph text containing `## Agent output`, `# Markdown Images`, or `<!-- excalidraw-markdown-image:` ** must not corrupt the task card or scene sections: reject or neutralize (Task 7).
5. **Scene edited in Obsidian between collect and apply** -> abort with "scene changed since collect", no write (Task 14).
6. **Existing manual explanation present** -> `skipped_existing`, untouched (Task 13).

---

### Task 0: Probe gates (P1, P2, P3, P5, P6) and decision record

Gate for Tasks 4 and 14. Needs the owner in Obsidian; the agent drives, owner clicks.

**Files:**
- Create: `docs/status/transcribe_notes/2026-11-XX-framed-explainer-probes.md` (use the run date)
- Create (scratch, do not commit): copy of `Auto-Frame Scratch 2026-11-08.excalidraw.md` under a scratch name outside the synced vault path agreed with the owner.

**Interfaces:**
- Produces: a verdict per probe (`verified | failed`) with evidence, read by Tasks 4, 12, 13, 14.

- [ ] **Step 1: P5 slot geometry.** Using the throwaway decode approach (lzstring), measure LIML2 per frame: slide box, explanation-image box, ink bbox, frame box; report median card-x offset relative to slide width and median gap. Record whether the spec's default slot (4% gap, right of slide, top-aligned) agrees; if not, record the measured rule and change the Global Constraints slot line before Task 13.
- [ ] **Step 2: P1 card creation.** In Obsidian on the scratch copy, run a minimal EA script that creates a Markdown image card (inspect `ea` API for the markdown/embed route; record the exact call). Save, reopen. Diff the new `# Markdown Images` marker, `## Embedded Files` entry, `fileId`, `customData.markdownImage`, `frameId` against the LIML2 pattern (`fileId` == marker hash). Verdict `verified` only if reopen and resave are stable.
- [ ] **Step 3: P2 frame export.** Attempt in-vault single-frame PNG export (copy frame elements into EA, export). Verdict `verified` if ink is visible in the PNG; otherwise the PDF bridge (Task 4) is the first-release route.
- [ ] **Step 4: P3 script trigger.** Test whether an external agent can run an Obsidian script (URI or command). Record result; failure means the owner clicks the script button.
- [ ] **Step 5: P6 framer classification.** Read `classify`/`matchExplanations` in `Auto-Frame Slides.md`; record every place a card image would be counted (explanations, foreign content, members). This list defines Task 9's edits.
- [ ] **Step 6: Commit the status doc** (outer repo, explicit path). If P1 fails, stop and bring the finding back to Claude before Task 14.

### Task 1: Scene reader and classifier (Python)

**Files:**
- Create: `pipelines/transcribe_notes/framed_explainer/__init__.py`, `.../scene.py`
- Modify: `requirements.txt` (add `lzstring`)
- Test: `tests/pipelines/transcribe_notes/test_framed_explainer_scene.py`; fixture `tests/pipelines/transcribe_notes/fixtures/framed_explainer/mini_scene.excalidraw.md` (hand-built: 2 slides, 1 explanation, 3 strokes, 1 frame, `## Embedded Files` registry, one deleted element)

**Interfaces:**
- Produces: `@dataclass Scene(path: str, sha1: str, elements: list[dict], registry: dict[str, str])`; `load_scene(path: str) -> Scene` (sha1 over raw bytes with CRLF normalized to LF, read-only); `@dataclass Classified(slides, explanations, ink, frames, other: list[dict])`; `classify(scene: Scene) -> Classified` mirroring the framer's JS `classify` (deleted skipped; explanation if registry link is `markdown-image` or `customData.markdownImage`; slide if sized 907x510 +/-(25,20) or width >= 700 at 16:9 +/-0.035, and link ends `.png`).

- [ ] **Step 1: Write failing tests.** `test_load_scene_decodes_compressed_json` (element count excludes nothing: raw count 9); `test_load_scene_sha1_is_line_ending_insensitive` (CRLF copy gives equal sha1); `test_classify_buckets` (2 slides, 1 explanation, 3 ink, 1 frame; deleted ignored); `test_load_scene_never_writes` (mtime and bytes unchanged); `test_scene_without_compressed_json_raises_SceneFormatError`.
- [ ] **Step 2: Run** `python -m pytest tests/pipelines/transcribe_notes/test_framed_explainer_scene.py -v`; expect FAIL (module missing).
- [ ] **Step 3: Implement** `scene.py` per the signatures; registry parsed from `## Embedded Files` lines `<40hex>: [[name.png]]` and markdown entries; blank lines inside the section do not truncate the parse (the framer had this bug; see its `embedded file parser retains entries after blank lines` test).
- [ ] **Step 4: Run tests; expect PASS.**
- [ ] **Step 5: Commit** `requirements.txt`, `scene.py`, `__init__.py`, test and fixture.

### Task 2: Ink regions, fallback and anchoring (Python) with JS parity

**Files:**
- Create: `pipelines/transcribe_notes/framed_explainer/ink.py`
- Test: `tests/pipelines/transcribe_notes/test_framed_explainer_ink.py`; `tests/pipelines/transcribe_notes/test_framed_explainer_ink_parity.py` (calls a Node one-liner against `AUTO_FRAME_SCRIPT`)

**Interfaces:**
- Consumes: `Classified` from Task 1.
- Produces: `@dataclass Bounds(x,y,w,h)`; `@dataclass Region(region_id: str, bounds: Bounds, stroke_ids: list[str])`; `cluster_ink(strokes: list[dict]) -> list[Region]` (port of JS `clusterInk`, same RULES, same ordering `y, x, id`); `box_gap(a: Bounds, b: Bounds) -> float` (box-to-box distance); `fallback_slide(region: Region, slides: list[dict], all_regions: list[Region], margin: float = 0.5) -> str | None` (slide id if clearly nearest and nothing intervening, else None); `anchor_for(region: Region, slides: list[dict], max_slide_widths: float = 1.5) -> tuple[str | None, str | None]` returning `(anchor_slide_id or None, also_near_slide_id or None)`; `reading_order(regions: list[Region]) -> list[Region]` (top to bottom, then left to right, using region top then left).

- [ ] **Step 1: Failing tests.** `test_cluster_ink_splits_on_gap` (two strokes 200px apart in x -> 2 regions; 50px -> 1); `test_cluster_ink_respects_max_size` (strokes chain beyond 1200 width -> split); `test_fallback_requires_clear_margin` (nearest 100, second 120 -> None; nearest 40, second 120 -> nearest id); `test_fallback_blocked_by_intervening_ink` ; `test_anchor_threshold` (distance 1.4 widths -> anchored; 1.6 -> `(None, ...)`); `test_anchor_records_also_near_for_between_two` ; `test_reading_order`. Parity: `test_cluster_ink_matches_js` feeds one 40-stroke fixture to Node `__AUTO_FRAME_EXPORTS__.clusterInk` and compares sorted stroke-id sets per region.
- [ ] **Step 2: Run; expect FAIL.**
- [ ] **Step 3: Implement** `ink.py` per signatures; constants copied from the framer's `RULES`.
- [ ] **Step 4: Run; expect PASS** (parity test skips with a clear message if `AUTO_FRAME_SCRIPT`/Node missing; it must run in the executor's verification).
- [ ] **Step 5: Commit.**

### Task 3: Identity, fingerprints and state

**Files:**
- Create: `pipelines/transcribe_notes/framed_explainer/identity.py`
- Test: `tests/pipelines/transcribe_notes/test_framed_explainer_identity.py`

**Interfaces:**
- Produces: `card_key(namespace: str, frame_id: str, slide_id: str) -> str`; `section_key(namespace: str, anchor_slide_id: str | None, seq: int) -> str`; `input_fingerprint(slide_sha1: str | None, ink: list[dict], frame_id: str | None, prompt_version: str, context_version: str) -> str` (sha1 hex; ink entries contribute `id, version, x, y, width, height` sorted by id; frame size is NOT an input); `class State(str, Enum)` with the nine states in the Global Constraints; `next_state(current: State | None, stored_fp: str | None, new_fp: str) -> State` returning `noop` semantics as `State.verified` only when `current is verified and stored_fp == new_fp`, `stale` when verified and fingerprints differ, `pending` when none.

- [ ] **Step 1: Failing tests.** `test_fingerprint_ignores_frame_resize`; `test_fingerprint_changes_with_ink_geometry`; `test_fingerprint_changes_with_prompt_version`; `test_fingerprint_order_independent`; `test_next_state_noop_when_verified_same`; `test_next_state_stale_when_changed`; `test_declined_stays_suppressed_on_same_fp`; `test_keys_are_stable_strings`.
- [ ] **Step 2: Run; FAIL.** **Step 3: Implement.** **Step 4: Run; PASS.** **Step 5: Commit.**

### Task 4: Frame rasters

Implements the PDF bridge now (always available). If Task 0 verified P2, add the in-vault export as a follow-up task; do not build it here.

**Files:**
- Create: `pipelines/transcribe_notes/framed_explainer/rasters.py`
- Test: `tests/pipelines/transcribe_notes/test_framed_explainer_rasters.py` with a 3-page generated PDF fixture (PyMuPDF writes it in the test)

**Interfaces:**
- Produces: `rasterize_frame_pdf(pdf_path: str, frames: list[dict], out_dir: str, dpi: int = 110) -> dict[str, str]` mapping frame id to PNG path. Page-to-frame mapping is by order of the verified frame list sorted by frame name; raises `PageMappingError` when page count != frame count (never guesses).

- [ ] **Step 1: Failing tests:** `test_maps_pages_to_frames_in_name_order`; `test_page_count_mismatch_raises`; `test_png_written_nonblank` (pixel variance > 0).
- [ ] **Steps 2-4: fail, implement, pass.** **Step 5: Commit.**

### Task 5: Course context

**Files:**
- Create: `pipelines/transcribe_notes/framed_explainer/course_context.py`
- Test: `tests/pipelines/transcribe_notes/test_framed_explainer_course_context.py` with a tmp-dir vault fixture

**Interfaces:**
- Produces: `@dataclass CourseContext(text: str, version: str, sources: list[str], truncated: bool)`; `scene_date(scene_path: str) -> date | None` (parses `YYYY-MM-DD` from the scene filename); `build_course_context(scene_path: str, hub_root: str, window_days: int = 7, max_tokens: int = 2000) -> CourseContext` (profile from `<course>/part_N` path; syllabus text from `part_N/syllabus/`; neighbour titles from `professor_notes/`, `ta_notes/` and sibling scenes within the window; `version` = sha1 of source file contents; every line carries its source path; token estimate `len(text)/4`).

- [ ] **Step 1: Inspect** one real `part_2/syllabus/` folder (read-only) and record in the test fixture docstring the file types and how a lecture date maps to a week; if no date-bearing structure exists, `topic window` degrades to the whole-part topic list.
- [ ] **Step 2: Failing tests:** `test_missing_syllabus_degrades_to_profile`; `test_window_selects_neighbour_notes_only`; `test_cap_truncates_and_flags`; `test_version_changes_when_syllabus_changes`; `test_every_line_has_source_path`; `test_no_date_in_filename_still_builds`.
- [ ] **Steps 3-5: fail, implement, pass, commit.**

### Task 6: Collector and task card

**Files:**
- Create: `pipelines/transcribe_notes/framed_explainer/collect.py`, `.../runbook.md`
- Test: `tests/pipelines/transcribe_notes/test_framed_explainer_collect.py`

**Interfaces:**
- Consumes: Tasks 1-5 and `agent_work.{doc_work_dir, load_manifest, save_manifest, render_worklist, ManifestEntry}`.
- Produces: `collect(scene_path: str, hub_root: str, run_id: str, frame_pdf: str | None = None, frames: list[str] | None = None) -> CollectResult` where `CollectResult(run_dir: str, facts_path: str, task_path: str, status: Literal["staged","nothing_to_do","already_staged"], targets: list[Target])`; `Target(frame_id | None, slide_id | None, eligibility: Literal["eligible","ambiguous_match","missing_asset","clipped_ink","existing_card","needs_review"], fingerprint: str)`. Writes `facts.json` (scene sha1, slides, regions with stroke ids, frames, existing explanations, context version, `schema: 1`), `task.md` (runbook text + instructions + `## Agent output` pointer to `result.json`), `course_context.md`, `images/<frame>.png`. Manifest tier `cards`.

- [ ] **Step 1: Failing tests:** `test_empty_scene_is_nothing_to_do_and_writes_nothing` (Review Focus 1); `test_ink_only_scene_stages_sections_mode` (facts has regions, no slides, `mode == "ink_only"`); `test_existing_explanation_marks_existing_card`; `test_restage_same_fingerprint_is_already_staged`; `test_facts_json_uses_lf_and_is_deterministic`; `test_scene_never_modified`.
- [ ] **Step 2: Run; FAIL.** **Step 3: Implement**, with `runbook.md` containing, as the standing instruction: the stages, the `result.json` schema block, the "visible vs inferred", "no ungrounded claims", "context is a hint", "agent may not edit the scene", the 0.5/1.5 rules stated for the agent, and `needs_review` triggers. **Step 4: Run; PASS.** **Step 5: Commit.**

### Task 7: Result validation, resolution and submit

**Files:**
- Create: `pipelines/transcribe_notes/framed_explainer/results.py`, `.../submit.py`
- Test: `tests/pipelines/transcribe_notes/test_framed_explainer_results.py`, `.../test_framed_explainer_submit.py`; fixtures `fixtures/framed_explainer/result_ok.json`, `result_dup_stroke.json`

**Interfaces:**
- Produces: `class ResultError(ValueError)` with `.code`; `validate_result(result: dict, facts: dict) -> None` (schema `1`; every slide/frame/stroke/anchor id exists in facts; no stroke twice; `ok` cards have exactly two non-empty paragraphs; paragraphs and transcriptions must not contain `## Agent output`, `# Markdown Images`, `<!-- excalidraw-markdown-image:`; `scene_sha1` equals facts); `resolve_result(result: dict, facts: dict) -> dict` (applies Task 2 `fallback_slide`, `anchor_for`, `reading_order` to unassigned/ section regions, sets dispositions `assigned | fallback_nearest | section`, adds `order`, `kind`, `context_assisted`; asserts coverage `all strokes == union of dispositions`); `submit(run_dir: str) -> SubmitReport(counts: dict[str,int], needs_review: list[str], placement_risks: list[str])` (reads `result.json`, writes `result.resolved.json` and state file, updates manifest to `submitted`).

- [ ] **Step 1: Failing tests:** `test_valid_result_passes`; `test_duplicate_stroke_rejected` (Review Focus 2); `test_unknown_slide_id_rejected`; `test_three_paragraphs_rejected_for_ok_card`; `test_needs_review_may_have_no_paragraphs`; `test_marker_text_in_paragraph_rejected` (Review Focus 4, parametrized over the three strings); `test_latex_and_unicode_roundtrip_unchanged` (Review Focus 3, includes `$\hat\beta_{IV}$`, `\r\n`, `é`); `test_resolve_assigns_fallback_only_with_margin`; `test_resolve_marks_far_ink_standalone`; `test_resolve_coverage_equation_holds`; `test_submit_writes_resolved_and_counts`; `test_stale_scene_hash_rejected`.
- [ ] **Steps 2-5: fail, implement, pass, commit.**

### Task 8: CLI

**Files:**
- Create: `pipelines/transcribe_notes/framed_explainer/cli.py`, `__main__.py`
- Test: `tests/pipelines/transcribe_notes/test_framed_explainer_cli.py`

**Interfaces:**
- Produces: `python -m pipelines.transcribe_notes.framed_explainer collect --scene <path> --hub-root <dir> [--frame-pdf <pdf>] [--frames ID,...]`, `submit --run-dir <dir>`, `status --run-dir <dir>`; `main(argv: list[str]) -> int` (0 ok/nothing-to-do, 2 validation failure). Exit text names the next action for the owner or agent.

- [ ] **Step 1: Failing tests:** `test_collect_then_submit_roundtrip_exit_zero`; `test_submit_invalid_result_exits_2_with_code`; `test_collect_missing_scene_exits_nonzero`.
- [ ] **Steps 2-5: fail, implement, pass, commit.**

### Task 9: Framer is card-aware; spec amendment

Nested repo, `Auto-Frame Slides.md`. Edits are the list recorded in Task 0 Step 5.

**Files:**
- Modify: `academic_notes/Excalidraw/Scripts/Auto-Frame Slides.md` (`classify`, `matchExplanations`, `planFrames` foreignContent and members)
- Modify (outer): `tests/pipelines/transcribe_notes/test_auto_frame_slides.cjs`
- Modify (outer): the spec's framer-amendments item 3 to name `<scene>.sections.json`.

**Interfaces:**
- Produces: elements with `customData.autoExplainKey` are returned in a new `cards` bucket by `classify`; excluded from `explanations` and from `foreignContent`; included in a frame's `memberIds`.

- [ ] **Step 1: Failing tests:** `card with autoExplainKey does not trigger multiple_explanations`; `card inside frame is not foreign_content`; `frame with card is noop on rerun` (marker-matched frame, `action === "noop"`); `card ids are in memberIds`; run the existing 22 tests.
- [ ] **Step 2: Run** `node --test tests/pipelines/transcribe_notes/test_auto_frame_slides.cjs` with `AUTO_FRAME_SCRIPT` set; new tests FAIL.
- [ ] **Steps 3-4:** implement; all 22 + new PASS. **Step 5: Commit in each repo separately** (script in nested, tests and spec edit in outer).

### Task 10: Framer sections

**Files:** same two as Task 9.

**Interfaces:**
- Consumes: `<scene>.sections.json`: `{"schema":1,"sections":[{"sectionId","kind":"anchored|standalone","anchorSlideId"|null,"order":int,"strokeIds":[...]}]}`.
- Produces: `planSections(sectionsFile, elements, slidePlans) -> plans[]` with frame names `018 Slide 18 · notes 1` (anchored; page from the slide plan) or `Notes 001` (standalone); action `create|update|noop|skip`; skip reason `section_overlaps_frame` when bounds intersect another frame or foreign content; `planFrames` output order puts anchored sections after their slide.

- [ ] **Step 1: Failing tests:** `anchored section named and ordered after its slide`; `two sections sequence 1 and 2`; `section overlapping slide frame is skipped with reason and writes nothing`; `standalone section named Notes 001`; `missing sections file leaves existing behavior`.
- [ ] **Steps 2-5: fail, implement, pass, commit.**

### Task 11: Framer no-slide mode

**Files:** same two.

**Interfaces:**
- Produces: when `kinds.slides.length === 0` and strokes exist, `planFrames` builds `Notes N` frames from `clusterInk` in reading order **without requiring the slide-order sidecar** (no `invalid_order` error in this mode); when strokes also zero, returns no plans.

- [ ] **Step 1: Failing tests:** `ink-only scene yields Notes 001..N in reading order`; `no sidecar needed in ink-only mode`; `empty scene yields no plans`; `scene with slides still requires sidecar`.
- [ ] **Steps 2-5: fail, implement, pass, commit.**

### Task 12: Apply script — validation and coverage audit (pure)

**Files:**
- Create (nested): `Excalidraw/Scripts/Apply Explanations.md` (IIFE with test export hook like the framer)
- Create (outer): `tests/pipelines/transcribe_notes/test_apply_explanations.cjs`

**Interfaces:**
- Produces (exported as `__APPLY_EXPLANATIONS_EXPORTS__`): `validateResult(result, elements) -> {ok: boolean, errors: string[]}` (same invariants as Python `validate_result`: ids exist, no duplicate stroke, two paragraphs for `ok`); `auditCoverage(resolved, elements, frames) -> {ok, missing: string[], duplicated: string[], outsideFrame: string[], counts: {assigned, fallback_nearest, section}}` (strokes in scene minus deleted must equal union of dispositions; each stroke's box contained in some frame in `frames`).
- Shared fixtures: reuse Task 7's `result_ok.json` and `result_dup_stroke.json` (read by both test suites) so the two validators cannot drift.

- [ ] **Step 1: Failing tests:** `ok fixture validates`; `duplicate stroke fails with the id`; `stroke missing from every disposition fails coverage`; `stroke outside every frame fails outsideFrame`; `deleted strokes are ignored by the audit`; `counts match fixture`.
- [ ] **Steps 2-5: fail, implement, pass, commit.**

### Task 13: Apply script — placement slot and idempotency (pure)

**Files:** same two as Task 12.

**Interfaces:**
- Produces: `planCardSlot(frame, slide, cardSize, obstacles) -> {ok: true, x, y, w, h, expandFrame?: bounds} | {ok: false, reason: "placement_conflict"}` per the Global Constraints slot rule (top-aligned, gap `0.04 * slide.width`, width = slide width clamped to free frame width, card kept wholly inside frame, clear of slide, ink and other cards; frame expansion allowed only when no foreign content or other-frame overlap and all ink stays contained); `decideCardAction(existingCardsByKey: Map, key: string, fingerprint: string, hasManualExplanation: boolean) -> "create" | "noop" | "update_stale" | "skipped_existing"`.

- [ ] **Step 1: Failing tests (use the P5-measured values if they differ from spec defaults):** `slot is right of slide with 4 percent gap`; `width clamped when frame narrow`; `blocked by ink in slot yields placement_conflict`; `expansion refused when it would overlap neighbour frame`; `scales with slide size` (607 wide and 1473 wide slides); `manual explanation yields skipped_existing`; `same fingerprint yields noop`; `changed fingerprint yields update_stale (one replacement, not create)`.
- [ ] **Steps 2-5: fail, implement, pass, commit.**

### Task 14: Apply script — EA effects, safety checks, live scratch run

Depends on P1 verdict. If P1 failed, stop here.

**Files:**
- Modify (nested): `Excalidraw/Scripts/Apply Explanations.md` (`run()`, `applyResolved(view, file, resolved, snapshot, sceneHash)`)
- Test: live checklist in the probes status doc (Obsidian cannot run in Node); Node test `abort when scene hash differs` using a stubbed `ea`/`app`.

**Interfaces:**
- Consumes: `result.resolved.json` read from the run directory path the owner selects (file picker or a path constant noted in the Notice), `planCardSlot`, `decideCardAction`, `auditCoverage`, `validateResult`.
- Produces: `applyResolved(...) -> results[]` where each result is `{key, action, frameId, cardId?, reason?}`; writes `<scene>.sections.json`; follows the framer's pattern: canvas fingerprint and scene SHA-1 preconditions ("Canvas changed since preview" / "Drawing file changed since collect"), two-run preview-then-apply, `ea.addElementsToView`, post-save audit (all original element ids present, every card inside its frame, card keys unique, ink coverage holds), and a Notice telling the owner to run Auto-Frame Slides next.

- [ ] **Step 1: Failing Node test** `apply aborts with no write when scene sha1 differs from result.scene_sha1` (Review Focus 5) and `apply refuses when coverage audit fails`.
- [ ] **Step 2: Run; FAIL.** **Step 3: Implement** with the EA card-creation call recorded in P1.
- [ ] **Step 4: Node tests PASS.**
- [ ] **Step 5: Live scratch run** (owner in Obsidian) on the 2-slide scratch copy: collect, agent writes `result.json`, `submit`, apply, run the framer, export PDF; check acceptance 1 and 2 (visible ink, rerun `noop`), record in the status doc.
- [ ] **Step 6: Commit** (nested script; outer tests and status doc).

### Task 15: Review artifact and resolution

**Files:**
- Create: `pipelines/transcribe_notes/framed_explainer/review.py`
- Test: `tests/pipelines/transcribe_notes/test_framed_explainer_review.py`

**Interfaces:**
- Produces: `build_review_items(resolved: dict, apply_results: list[dict]) -> list[ReviewItem]` (`ReviewItem(item_id, kind: Literal["low_confidence","fallback_nearest","placement_conflict","needs_review","anchor_tie","replace_existing"], slide_id | section_id, summary: str, options: list[str])`); `apply_decisions(decisions: dict[str, str], run_dir: str) -> DecisionReport` (writes `decisions.json` consumed by the next collect: declined cards suppressed, adopt/replace flags set).
- The Artifact page itself (checkbox/Link/Dismiss, decisions in `db`) is built at execution time with the Artifact tool following `core/indexer/offering_links.py`'s reference page; not committed code.

- [ ] **Step 1: Failing tests:** `fallback_nearest regions become items`; `placement_conflict becomes item with options skip/expand`; `declined decision suppresses card on next collect with same fingerprint`; `changed fingerprint reopens a declined card`.
- [ ] **Steps 2-5: fail, implement, pass, commit.** Then build the review Artifact, publish it, and link it in the status doc.

### Task 16: Corpus acceptance run and docs

**Files:**
- Modify: `pipelines/transcribe_notes/README.md` (new section), `docs/status/transcribe_notes/2026-11-XX-framed-explainer-probes.md` (results table)

- [ ] **Step 1:** Run the full flow (collect, agent, submit, apply, framer, PDF) on scratch copies of: LIML2 (expect `skipped_existing` for all 24, rerun `noop`); one microeconomics slides+ink scene with no frames (frame, then explain); one ink-only econometrics scene (`Notes N`, card per section); a scene with ink far from every slide (standalone sections).
- [ ] **Step 2:** Record per scene the ink coverage counts (assigned / fallback_nearest / section), every `needs_review`, and every blocked result against acceptance criteria 1-9 in the spec.
- [ ] **Step 3:** Run `python tools/run_tests_chunked.py` and the Node suites; record output.
- [ ] **Step 4:** Update the README with the three commands, the runbook location, and the owner's one-instruction wording; commit.

## Self-review

- **Spec coverage:** pipeline stages -> Tasks 6-8, 14; result file -> Task 7; ink coverage invariant -> Tasks 2, 7, 12; sections and ink-only -> Tasks 10-11; placement contract -> Task 13; framer amendments -> Tasks 9-11; identity/state -> Task 3; writer safety -> Task 14; review surface -> Task 15; course context -> Task 5; probes P1-P6 -> Task 0 (P4 stays blocked, out of scope); acceptance criteria -> Tasks 14, 16.
- **Not in this plan by design:** headless `agy`, in-vault frame export (follow-up if P2 verifies), scheduling, rearrangement.
- **Type consistency:** `Region.stroke_ids`, `facts.json`, `result.resolved.json` dispositions (`assigned | fallback_nearest | section`), `autoExplainKey` and the card/section key formats are used identically in Tasks 3, 7, 9, 10, 12-14.
