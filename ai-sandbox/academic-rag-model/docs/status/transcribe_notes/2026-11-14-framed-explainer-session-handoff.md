# Framed explainer: session handoff (2026-11-14)

For a new session continuing the Excalidraw framed-explainer pipeline. Read this first, then
the design docs it links. Everything below was verified in the session that wrote it unless
marked **unverified**.

## What the pipeline is
Turns Excalidraw canvases (PDF-slide images plus handwritten ink) in the nested
`academic_notes` vault into framed pages with two-paragraph Markdown explanation cards, for
one exported PDF. Agent (Gemini via Antigravity, subscription, no metered API) does grouping,
transcription and explanations; deterministic code owns placement.
Stages: **frame** (Auto-Frame Slides) -> **collect** (Python) -> **agent** (Gemini follows
`task.md`) -> **submit** -> **apply** (Apply Explanations, in Obsidian) -> **reframe**.

Design history: `docs/superpowers/specs/transcribe_notes/2026-11-13-framed-explainer-design.md`,
plan `docs/superpowers/plans/transcribe_notes/2026-11-13-framed-explainer.md`, runbook
`pipelines/transcribe_notes/framed_explainer/runbook.md`, probes
`docs/status/transcribe_notes/2026-11-13-framed-explainer-probes.md`.

## Where the code lives (two repos)
| Repo | Branch / worktree | State |
| --- | --- | --- |
| Outer monorepo | **Landed on `main` 2026-11-14 (a9e722d0, pushed; spec docs first as 89b7778d).** Start new work on a fresh `claude/<task>` worktree from `main`. | Python package `pipelines/transcribe_notes/framed_explainer/`, tests, docs. |
| Vault (`academic_notes`, separate repo) | `claude/framed-explainer-notes`, `.worktrees/claude-framed-explainer-vault`; fast-forwarded into the vault `main` after every change | Obsidian scripts in `Excalidraw/Scripts/`. Vault `main` is live for the owner. **Unpushed.** |

Vault scripts now on vault `main`: `Auto-Frame Slides.md`, `Apply Explanations.md`,
`Probe Markdown Card.md`, `Select Below.md`, plus `.svg` icons (same basename as the script;
the plugin reads them) for those four and for `convert_pdf_to_png.md`.
The vault `main` checkout has unrelated uncommitted changes: leave them. If `main` has moved,
`git rebase main` in the vault worktree, then `git merge --ff-only` in the main checkout.

## Rules the owner set (do not relitigate)
- `CLAUDE.md`: use a `claude/<task>` worktree, stage explicit paths only, never commit
  secrets or copyrighted slides, warn before API calls over $1, human decisions go through an
  interactive Artifact, link reviewable docs with clickable `file://` paths.
- Prefer the Gemini subscription agent; no metered calls without asking.
- Slide images are anchors: the framer never moves them. The owner nudges slides by hand;
  the script warns and says how far.

## What was built this session (ink-to-slide assignment)
Implemented in the framer (`matchInk`, `assignBands`) and ported to Python
(`framed_explainer/bands.py`, `assign_strokes`). A parity test runs the same scenes through
both (`tests/.../test_framed_explainer_bands_parity.py`, runner `framer_band_runner.cjs`).
1. Slides that do not overlap in y (x may jitter) form a **column**; each owns the ink from
   its top edge to the next slide's top. Non-overlapping in x -> **row** (axes swapped).
   Anything else -> **proximity classifier**: `p = exp(-d/(0.35 W)) / (sum + e^-3)`, accept at
   `p >= 0.6`, else "cannot tell" (left loose / a section). The old 1.5-slide-width rule is gone.
2. Ink within 0.25 slide heights of a band edge is settled by drawing time (Excalidraw
   `created`, from the Obsidian Excalidraw plugin): a 1-D time cut between the confident ink
   of the two bands; strokes outside both bands' time window, or sharing an identical
   `created` (edited in post), ignore time.
3. Ink **above** the next slide's top edge never moves down; zone strokes drawn in one burst
   (gaps under 10 s) stay with the slide above if any of the burst is above the edge; with no
   usable time, ink chained to the ink above defers to the slide above.
4. Frames: left-anchored on the slide, grow right and down over their ink, **no height cap**
   (a later splitter script makes print-ready frames), never cover a neighbouring slide, never
   overlap the previous frame. Ink that does not fit is reported (`atRisk`), with a suggestion
   to move the next slide down about N px; a notice follows the apply run.
5. Collector (`collect.py`) stages `ink_stroke_ids` per slide and `band_slide` per region in
   `facts.json`, plus `created` per stroke; `results.py` falls back by band (majority >= 60%,
   only if the frame holds the ink). The runbook tells the agent to treat these as defaults.
6. Auto-Frame's confirm run no longer compares the autosaved file text (it needed three runs).

## Evidence from live tests (owner's scratch copies, microecon lecture, 9 slides, 2143 strokes)
- Frames came out nearly right; the only misclassification was the slide 6 table's lower
  rows, fixed by the owner moving slide 7 down on a copy.
- Ink drawing time separates the slides' ink almost perfectly on this scene (each band's
  strokes form a near-disjoint window, ~20-80 min total).
- **Gemini cannot reliably read handwriting from raw stroke coordinates**: structure right
  (5 lines, groupings, underline), transcription wrong on 3 of 5 lines with 0.95 stated
  confidence. Claude could not read it either. Use **images** for transcription; keep stroke
  ids and bounds only for grouping. Test inputs: `docs/status/transcribe_notes/2026-11-14-stroke-text-test/`.

## Open items, in suggested order
1. ~~Merge the outer branch~~ Done: landed on `main` 2026-11-14.
2. **Image path for the agent** (decision for the owner): today rasters come from a
   hand-exported Printable Layout PDF (110 dpi, one page per frame, page count must equal
   frame count). Proposed: send each slide's original PNG plus a frame raster at 150-200 dpi,
   and replace the manual PDF step with an in-vault frame PNG export (probe **P2**, still
   open). Stroke lists are for grouping only.
3. **Frame splitter script** (new): split a tall frame into print-ready frames by the
   570-850 px height rule, cutting at the largest vertical gaps in the ink, slide stays with
   its first piece. Not started.
4. **Run the whole chain once on a fresh copy**: Auto-Frame -> `collect --frame-pdf` ->
   Gemini on `task.md` -> `submit` -> Apply Explanations (preview, repeat to apply) ->
   Auto-Frame again. Never run on an original file. P3 (agent trigger script) is open.
5. **Test the proximity fallback** on a real scene with no clean bands plus ink (a 2x2 grid is
   only covered by synthetic tests). Requested by the owner.
6. **Strokes outside the frame**: `results.py` turns assigned ink the frame cannot hold into a
   section. The owner noted stroke lists need not be bound to frame rectangles; decide whether
   the slide's card should cover the full band's strokes even when the frame cannot.
7. PDF export of Markdown-embed cards is unverified; the review Artifact was never built.
8. Possible hardening: the time cut moves if one stray stroke sits early (I tried a
   widest-gap cut, it changed other slides' assignments unverifiably, and reverted it).

## Deferred minors (from the final review)
JS validator weaker than Python (frame_id/disposition/legibility/confidence/duplicate ids);
manual-explanation definition differs between Python and JS; Python raw-bytes SHA vs vault
BOM risk; `collect --frames` does not filter strokes; `section_id`/`region_id` collision;
unused `identity.section_key`; `apply_decisions` KeyError and unused replace/expand;
`writeSections` always writes. Details in the ledger `.superpowers/sdd/2026-11-13-framed-explainer/progress.md`
(git-ignored; keep until the owner has verified the live steps).

## Commands
```
# Python (from ai-sandbox/academic-rag-model, venv .venv)
python -m pytest tests/pipelines/transcribe_notes -q          # 483 passed at handoff
python -m pipelines.transcribe_notes.framed_explainer collect <scene> --hub-root <hub> ...
# Node tests need the vault worktree scripts:
export AUTO_FRAME_SCRIPT=".../claude-framed-explainer-vault/Excalidraw/Scripts/Auto-Frame Slides.md"
export APPLY_EXPLANATIONS_SCRIPT=".../claude-framed-explainer-vault/Excalidraw/Scripts/Apply Explanations.md"
export SELECT_BELOW_SCRIPT=".../claude-framed-explainer-vault/Excalidraw/Scripts/Select Below.md"
cd tests/pipelines/transcribe_notes && node --test test_auto_frame_slides.cjs test_apply_explanations.cjs test_select_below.cjs   # 91 + 5 pass
```

## Gotchas
- Windows working tree is CRLF, repo is LF: scripted edits must read/write with `newline=''`
  and preserve endings. Bash heredocs with backslashes or odd quotes break in this harness:
  write such files with the Write tool.
- Node tests run scripts in a `vm` realm: arrays from the script are not `===`-comparable
  to test arrays (spread or JSON-compare).
- The owner's scratch scenes (`microecon/part_2/lecture_notes/Microeconomics scratch*.md`)
  are gitignored vault content; they contain slide images, so never copy them into this repo.
  A leftover probe card image sits at the origin of the first scratch copy (it blocks slide 2).
- Strokes carry `created` (plugin template); not guaranteed after copy/paste or conversion,
  so time is a tiebreaker only.
