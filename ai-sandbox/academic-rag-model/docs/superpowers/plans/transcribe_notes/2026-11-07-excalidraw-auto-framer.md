# Excalidraw Auto-Framer Script — implementation plan

**Status:** Implementation in task branches as of 2026-11-08; fixture-tested, pending in-Obsidian scratch validation. A two-slide scratch note exists in the current vault; the original LIML2 canvas is unchanged.
**Spec:** `docs/superpowers/specs/transcribe_notes/2026-11-07-excalidraw-auto-framer-design.md`.
**Goal:** Add a user-invoked `Auto-Frame Slides.md` EA script that wraps unambiguous slide/explanation/handwriting groups in printable frames ordered by verified slide numbers, without moving source content or duplicating frames on rerun.

**Owner scope decision (2026-11-08):** Deliver numbered PDF export and spatial handwriting matching first. Physical rearrangement of slides, explanations, or strokes is excluded and requires a separate future plan.

**Owner risk decision (2026-11-08):** Default framing may leave handwriting outside the print area. Report at-risk stroke counts per frame, provide a strict ink mode, and keep stroke-grouping improvements separate. Temporary canvas spacing followed by restoration would restore the same PDF overlaps, so the framer does not move content.

## Verified context and smallest release

- The vault's Excalidraw plugin manifest says 2.29.1; settings point to `Excalidraw/Scripts`. A minimal `test_script.md` already runs there. `Downloaded/Printable Layout Wizard.md` is installed and pinned. Its code reads view elements, adds frames, and orders PDF pages alphabetically by name. Its help says frames define spatial print areas and same size/orientation gives a uniform PDF. The PDF implementation creates an SVG for each selected frame using that frame's own view box, so mixed dimensions may export but must be checked for readability and page sizing.
- `Econometrics 2026-10-28 2sls recovered.excalidraw.md` is the reference with standard and overflow cases. The user reports a successful direct slide-explainer run on `Econometrics 2026-11-04 LIML2 10.09.10.excalidraw.md`; this gives a second sample after its writer and sync state are confirmed. Do not run the framer on the original note or interpret the explainer result as proof that framing works.
- A read-only decode of LIML2 found 2,570 `freedraw` strokes, 48 images, 24 rectangles, and no frames in that snapshot. Its slide x coordinates are far outside the 2SLS grid. A sampled slide PNG shows `18/56`; its asset filename contains no usable page number. Treat these as verified structural observations, not proof that every stroke belongs to one slide or every number is readable.
- The first usable release handles ordinary, unambiguous slide/explanation/ink groups, sorts PDF pages by a verified slide-number map, previews changes, adopts exact matching existing frames, and reports skips. It does not physically reorder canvas elements. Tall/stacked/exercise support is a second milestone. No server, scheduler, database, or Python slide-explainer pipeline is needed.

## Requirement-to-task map

| Requirement / global constraint | Task | Acceptance evidence |
|---|---|---|
| Correct EA scene access and supported 2.29.1 methods | 1, 3 | Scratch API probe; save/reopen shows same IDs |
| 907 × 510 / 16:9 slide filtering; Markdown-image detection | 1, 2 | Sample inventory against source scene; false-positive log |
| Number map keyed to slide IDs/assets; duplicate and missing page checks | 1, 2 | PNG sample comparison, stale-map fixture, shuffled-slide PDF order |
| Relative pairing across irregular positions; 250 px rows only as candidates | 2 | 2SLS and LIML2 sample comparison; no absolute x split |
| Freehand stroke-region clustering; zero/many regions per slide; ambiguous shared ink | 1, 2, 4 | Varied live read-only sample, ink fixture tests, disclosed at-risk strokes; strict mode blocks incomplete ink |
| 1980 minimum width, 570–620 height, balanced padding | 2, 3 | Numeric tests and canvas bounds audit |
| Adaptive 750–850, 1840 × 800 two-part, vertical continuation | 4 | Fixture tests and scratch export; indivisible overflow blocked |
| Frame naming and PDF order independent of canvas coordinates | 3, 5 | Wizard preview and shuffled-slide PDF page audit |
| Exact selector, machine-readable per-pair results, idempotency | 2, 3 | Same-scene rerun shows no new IDs/changes; JSON report |
| Writer coordination, safe commit, post-run audit | 3, 5 | Original scene unchanged; scratch test copy in current vault reopens and memberships persist |
| Separate nested repository and Obsidian sync | 0, 5 | Worktree/root and writer checks logged |

Evidence labels throughout: **implemented** means the script exists; **fixture-tested** means Node/mocked EA checks pass; **live scratch-tested** means Obsidian save/reopen and PDF export were observed; **observed over time** would require later repeated real use and is not a release claim.

## Task 0 — Isolate repositories and capture baseline

**Write destinations:** Outer `academic-rag-model` repo for this plan and any test harness; nested `academic-hub/academic_notes` repo for the future `Excalidraw/Scripts/Auto-Frame Slides.md`. Create a dedicated child-repo branch/worktree for the script before writing it. The outer `codex/excalidraw-slide-specs` worktree does not isolate the child repo. Do not stage or alter the live LIML2 note while Gemini is editing it. Read the current worktree and child-repo instructions, check both Git statuses, and identify the Obsidian sync owner. Use a **copy** of the recovered 2SLS note and required assets inside the child worktree for experiments; keep the original read-only.

- [ ] Confirm `git rev-parse --show-toplevel` for outer, child, and script worktree; record branch and writer.
- [ ] Record plugin version, script-folder setting, and Printable Layout Wizard settings (`markersOnly`, export selection, margin); do not change user settings as part of setup.
- [ ] Capture a read-only element inventory from a small varied sample: 2SLS left/right pairs, crowded row, slide 22/23 overflow, exercises 1–4; LIML2 shuffled numbered slides, isolated/adjacent/shared ink regions, and unrelated strokes. Record actual `type`, `fileId`, `customData`, `frameId`, dimensions, names, and false-positive candidates. Wait for confirmed writer/sync quiescence before copying LIML2.
- [ ] Save a baseline checksum and original element-ID set for the scratch copy. Stop if a source note or asset link is missing.

## Task 1 — Probe EA and define safe discovery

**Files (implementation stage):** Child-repo `Excalidraw/Scripts/Auto-Frame Slides.md`; outer-repo `tests/pipelines/transcribe_notes/test_auto_frame_slides.cjs` for Node's built-in test runner (Node 24 is available). Keep pure planning functions in the script accessible to a mock-EA test harness without importing Obsidian. No new runtime package dependency.

- [ ] On a scratch canvas, verify `ea.getViewElements()` yields actual scene objects while `ea.getElements()` yields workbench objects. Test `copyViewElementsToEAforEditing`, `addFrame`, `addElementsToFrame`, and `addElementsToView` in the installed 2.29.1 plugin; record any signature/version mismatch. Restore the scratch copy after the probe.
- [ ] Implement `classify(elements, embeddedFileMap)` with explicit slide, Markdown-image, and `freedraw` evidence. Use aspect tolerance and asset link; ratio alone cannot classify an arbitrary image. Ignore deleted elements and unrelated rectangles. Return `{elementId, kind, reason}` plus warnings.
- [ ] Define `<scene basename>.slide-order.json` beside the scene: `slideElementId`, `fileId`, asset SHA-1, deck, displayed page and optional total. Verify Obsidian/EA can read it from the active vault. Create a scratch map by visually checking a varied set of slide PNG page numbers, using the subscription agent or manual entry; this map is input to the framer, not an OCR feature. Reject stale asset hashes, duplicate deck/page keys, and unreadable numbers. A missing or invalid map limits the script to preview/report rather than an order-dependent write.
- [ ] Compare classifications to the varied live read-only sample; document and fix false positives before using aggregate counts. If the Markdown-image marker differs in LIML2, support the observed representation or skip it explicitly.

**Gate:** No frame mutation until discovery has been inspected against real elements.

## Task 2 — Pure row, pair, and frame planning

- [ ] Implement deterministic `planFrames(elements, existingFrames, slideOrder)` returning per-target records: stable key from slide/explanation IDs and continuation part, verified deck/page, associated ink-region and stroke IDs, ordinal, bounds, existing frame ID, action (`create`, `update`, `noop`, `skip`), and reason. Target selector is the **active view file** plus explicit matched IDs; never scan the vault.
- [ ] Generate local pairing candidates by vertical overlap/center distance and horizontal gap. Use Δy ≤ 250 px anchored rows only for regular regions; infer row bands from actual slide boxes. Do not use absolute x = 950 or demand one explanation per slide in every note. Sort frame ordinals by verified deck/page, not canvas coordinates. Report missing/duplicate page numbers, ambiguous neighbors, and unpaired elements.
- [ ] Cluster `freedraw` stroke bounds into bounded handwriting regions without transitive merging through long strokes. Associate zero or more regions to a slide using proximity/overlap and local slide band; permit a contiguous page range only when one combined frame encloses it. Report ambiguous, noncontiguous, and orphan ink. No transcription or stroke movement is needed. Keep stroke ID lists for an inclusion audit, but avoid reparenting thousands of strokes solely for PDF output.
- [ ] Use the slide/explanation union for default bounds: `W = max(Xmax − Xmin + 80, 1980)`, centered x, and normal `H = clamp(Ymax − Ymin + 60, 570, 620)` when the core fits. Otherwise classify as adaptive or overflow. Include the assigned ink union only with optional `inkPolicy: "strict"`. Report strokes outside a default frame; strict mode skips if ink does not fit. Reject overlaps with unrelated images.
- [ ] Adopt an existing unmarked frame only on a unique, exact member-set/geometry match. If membership is unavailable, use unique spatial containment plus a tight geometry test and mark it `needs_review` before mutation. Managed frames retain their original ID. A second identical plan must contain only `noop`/`skip` actions.
- [ ] Write Node fixture cases for regular and irregular pairs, Δy boundary and chain trap, shuffled numbered slides, stale/duplicate page map, non-slide 16:9 images, duplicate explanations, zero/many/shared ink regions, long connecting stroke, existing manual frames, drifted members, and no-op rerun. Fixture code must not touch live vault files.

**Gate:** For every create/update, the report contains exact target IDs and final bounds. Skips are machine-readable, not silent.

## Task 3 — In-vault preview, apply, and idempotency audit

- [ ] Add a preview-first interaction to the EA script: show counts and a compact per-pair plan in an Obsidian modal/notice, then let the user apply only safe actions. If the modal API proves awkward, a visible preview plus explicit second invocation is acceptable; a hidden immediate write is not. Ambiguous pairings are skipped with reasons; if a later workflow asks for formal owner decisions, use the project's interactive Artifact convention.
- [ ] Before apply, verify the active view and file are still the same as at planning time and its element-ID/version snapshot has not changed. Abort if Obsidian or another writer changed it. Clear EA workbench, copy affected existing elements, create frames with `ea.addFrame`, edit existing copies under the same IDs, and call `ea.addElementsToFrame` only where grouping is desired. Commit once with awaited `ea.addElementsToView(false, true)`, then clear workbench. Check the returned success value.
- [ ] Name frames with zero-padded **global** ordinals derived from verified slide numbers (`001 Slide 18`, `002 Slide 19`, etc.), with continuation suffixes, so Printable Layout Wizard's alphabetical order is correct even when slides are spatially shuffled. Preserve other user frame names unless uniquely adopted. Store a managed marker in `customData` only if save/reopen proves it survives. Otherwise derive identity from stable member IDs and exact geometry, and skip ambiguity. Do not move slide, explanation, rectangle, or stroke coordinates.
- [ ] Re-read the view after commit and audit per target: frame exists once, bounds match plan, slide/explanation member IDs remain, optional `frameId` links point to the intended frame, and unrelated element IDs/positions remain unchanged. Surface per-group at-risk stroke counts and results; strict mode requires all assigned ink inside the print area. On audit failure, report failure and use the scratch backup for recovery; do not make a second blind repair pass.
- [ ] Test mocked EA apply for failure return, changed view, duplicate existing frame, and repeat-run no-op. Then manually test save/reopen on the 2SLS scratch copy.

**Gate:** Successful fixture tests are not proof of plugin persistence; save/reopen is mandatory.

## Task 4 — Tall and exercise layouts

- [ ] Extend planner to 750–850 px adaptive frames only when the full content-and-ink box plus vertical padding fits. For a two-panel exercise, require two distinct Markdown-image elements, use approximately 1840 × 800 bounds, and assign explicit Part 1/Part 2 reading order.
- [ ] For stacked continuation, require separate elements or verified continuation regions. If a single 1479 px Markdown image is indivisible, emit `needs_split`; do not create overlapping or empty frames and call that a solution. This covers the recovered note's tall slide 22/23 examples without claiming to split existing image elements.
- [ ] Add fixtures for 520 px threshold, adaptive maximum, neighboring row collision, two-part panel, ink overflow, shared ink between adjacent slides, and indivisible overflow. Manually check the recovered-note tall examples and LIML2's handwriting-rich sample on scratch copies.

**Gate:** Every framed slide and explanation is fully visible. Ink omissions remain a disclosed risk in default mode; strict mode requires full assigned-ink inclusion. Semantic splitting remains the explainer agent's responsibility.

## Task 5 — Export verification and handoff

- [ ] Run the script on the recovered 2SLS scratch copy, capture before/after element counts and frame IDs, save/reopen, then run again. Confirm no duplicate frames or changed geometry on the second pass.
- [ ] Use installed Printable Layout Wizard to preview and export. Deliberately shuffle two numbered slide positions in a scratch copy; confirm PDF order follows slide numbers while source element coordinates do not change. Inspect clipped ink, text readability, shared handwriting, and blank pages. Export a normal-only subset and a mixed standard/tall/exercise subset. Record whether mixed page dimensions produce an acceptable PDF. If not, report that limitation and retain the safe standard-frame release; do not silently normalize or resize mathematical content.
- [ ] Validate on a **copy** of the finished LIML2 scene only after Gemini has stopped editing it and the user/Obsidian sync owner has coordinated the writer. Compare a small varied sample of its panels with actual scene objects before accepting aggregate results.
- [ ] Update spec status with implemented, fixture-tested, live scratch-tested, and unverified items separately. Review explicit staged paths in both Git repositories; do not land either branch to `main` without the workspace landing process and user approval.

## Release decision

Release the script when ordinary slide/explanation groups classify correctly; page-number input is validated; preview results disclose at-risk ink; exact targets are audited; a second run is a no-op; and a scratch PDF follows numbered slide order without clipping slide/explanation content. Tall/exercise support may ship later if its distinct evidence gates are unmet. Physical canvas reflow remains a separate future plan because it would move content and its ink together. The direct Gemini slide-explainer workflow can continue independently and requires no new pipeline for this release.

## Implementation progress (2026-11-08)

- **Implemented in child-repo branch `codex/auto-frame-slides`:** `Excalidraw/Scripts/Auto-Frame Slides.md` classifies slides, Markdown images, and freehand strokes; reads and hashes linked PNGs; emits a slide-order template; validates a filled sidecar; computes numbered frame plans from relative geometry; groups nearby strokes; previews actions; applies safe frame changes through EA; audits frame bounds and ink inclusion. Source element coordinates are never changed.
- **Fixture-tested in outer branch `codex/excalidraw-slide-specs`:** Node tests cover classification, shuffled numbered order, spatial ink matching, ambiguity, missing/stale number input, overflow, unmanaged-frame avoidance, mocked EA save, and no-op rerun. These tests do not prove behavior inside the installed Obsidian plugin.
- **Read-only live inventory:** 2SLS decoded to 108 elements, including 24 slide images, 32 Markdown images, and 30 frames. LIML2 decoded to 2,642 elements, including 24 slides, 24 Markdown images, and 2,570 strokes. Revised pairing and default best-effort ink framing produce 22 proposed frames and 2 skips for `foreign_content` image intersections; this is a diagnostic geometry plan, not a live framing run. Its slide numbers were placeholders, so no PDF-order claim follows from it.
- **Current-vault scratch prepared:** `academic-hub/academic_notes/econometrics/part_2/lecture_notes/Auto-Frame Scratch 2026-11-08.excalidraw.md` contains copied LIML2 slides 18 and 19, their explanations, and 56 nearby strokes. Its sidecar uses visually verified `18/56` and `19/56` page labels with SHA-1 asset hashes. `academic-hub/academic_notes/Excalidraw/Scripts/Auto-Frame Slides Scratch.md` is a temporary script copy. A read-only diagnostic proposes 2 frames and 0 skips. These three untracked artifacts are deliberately in the existing vault for Obsidian testing; the original note remains unchanged.
- **Still unverified:** EA 2.29.1 runtime API compatibility, plugin save/reopen persistence of managed frame metadata, actual sidecar reading inside the vault, ink legibility and page order in Printable Layout Wizard PDF output, mixed-size pages, and a second live scratch run. Task 4's two-panel exercise handling remains deferred; tall complete groups up to 850 px are planned by the script, while indivisible overflow is skipped. The two full-LIML2 `foreign_content` skips need individual canvas review; do not bypass them by temporary spacing and restoration.
