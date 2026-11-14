# Framed Excalidraw explanation cards — Claude design handoff (2026-11-13)

**Stage:** Architecture review requested; no new pipeline or live scene edit is authorized by this document. Claude should review the companion [brainstorm](../../brainstorms/2026-11-13-framed-excalidraw-explanation-cards.md), challenge the feasibility gates below, and produce a dated design specification only after resolving material choices with the owner. Codex's role here was to land the approved auto-framer and assemble evidence, not to decide the new architecture.

## Owner request and fixed requirements

The owner has manually asked Gemini in Antigravity to read slide PNGs and write explanations into an Excalidraw note; this has been useful and fairly fast. The new goal is a replicable pipeline that takes slide images and associated handwritten ink, preferably grouped by the now-landed frames, sends **one frame at a time with neighboring context** to a subscription Gemini agent, generates **one two-paragraph Markdown explanation card per frame**, and adds each card to that frame. Prefer the subscription account path. The owner wants eventual full automation, including placement, rather than a collection of manual prompts. Physical canvas rearrangement remains a separate project.

The canonical Obsidian script is now `academic-hub/academic_notes/Excalidraw/Scripts/Auto-Frame Slides.md` on the nested vault's `main` at `0c9decb`. The supporting auto-framer spec, plan, and Node test are on outer `main` at `acaff210`. Keep those two repositories distinct.

## Verified behavior and limits

| Evidence | What it establishes | What it does not establish |
|---|---|---|
| Owner ran the revised auto-framer twice on a two-slide scratch note, reopened it, and confirmed the revised two-page PDF shows handwriting and is legible. A read-only repeat plan gave two no-ops and all 56 matched strokes inside slide 18's expanded frame. | Framing, ink capture, persistence, idempotent planning, and PDF export work on that scratch sample. | Whole-deck matching, complete ink capture, or automatic frame raster export. |
| Focused Node tests passed 22/22, including safe adoption of existing frames only with exact members and close geometry. | Planner behavior under fixtures. | A live Obsidian run of the final adoption safety rule. |
| Current read-only LIML2 snapshot has 24 slides, 24 explanations, 2,461 strokes, and 25 existing frames; diagnostic yields 5 possible updates and 19 skips with placeholder page numbers. | The real canvas is irregular and a frame is not automatically a trustworthy semantic pair. | A ready-to-run, ordered 24-frame input or high whole-deck coverage. |
| `pipelines/transcribe_notes` has `.agent_work` collect/submit drivers for Excalidraw transcription. | A task-card and validation pattern exists. | An installed headless transport or a frame-card pipeline. |
| The prior [slide-explainer spec](../../superpowers/specs/transcribe_notes/2026-11-07-excalidraw-slide-explainer-design.md) documents the owner's direct Gemini editing workflow and scene-writing safeguards. | Existing design constraints and known scene sections. | The plugin's Markdown-image hash/link contract; that spec marks it unresolved. |

The earlier subscription investigation reported no callable unattended agent transport **at that time**. Google's current [headless CLI documentation](https://antigravity.google/docs/cli/headless/) describes `agy -p`, JSON/streaming JSON, schema-constrained output, cached sign-in, and noninteractive permission behavior. Google's [authentication documentation](https://antigravity.google/docs/install/) distinguishes account sign-in from Gemini API-key routing. A `Get-Command agy,antigravity` check on this machine found neither command on `PATH`. Thus headless automation is a **candidate**, not locally demonstrated; do not claim zero metered cost or assume IDE login supplies a usable CLI session. The CLI's interactive media attachment documentation does not by itself prove that `agy -p` can ingest local PNGs as visual input. Test that separately.

## Existing work Claude should inspect

- `academic-rag-model/CLAUDE.md`, package `README.md`, `pipelines/transcribe_notes/README.md`, and `docs/AGENT_ROUTING.md` for routing, cost, and human review conventions.
- `docs/superpowers/specs/transcribe_notes/2026-11-07-excalidraw-auto-framer-design.md`, `docs/superpowers/plans/transcribe_notes/2026-11-07-excalidraw-auto-framer.md`, and the landed `Auto-Frame Slides.md` for frame selection, skipped/at-risk ink, and ordering sidecar semantics.
- `docs/superpowers/specs/transcribe_notes/2026-11-07-excalidraw-slide-explainer-design.md` and the 2026-11-07 brainstorm for panel identity, Markdown-image storage, layout constraints, and the successful direct-edit workflow.
- `pipelines/transcribe_notes/excalidraw_agent_work.py`, `excalidraw_agent_submit.py`, and `agent_work.py` for reusable collect/submit mechanisms; `transcribe_excalidraw.py` for the existing whole-canvas PNG/SVG workflow. `tools/` yielded no existing framed-card pipeline.
- `docs/status/transcribe_notes/2026-10-14-subscription-pipeline-investigation.md` for historical transport limits; `docs/trackers/academic_hub_to_do.md` (TODO-0072 and TODO-0075) for adjacent agent handoffs. Reconcile dates rather than assuming the old transport note is current.

## Feasibility questions for Claude

1. **Visual input:** Can a signed-in, account-based headless `agy -p` run actually inspect a named local PNG (and preferably a cropped frame showing handwritten strokes)? Show a small no-write test and record the model's visual evidence. If not, keep the already working interactive Antigravity collect/submit route as the first release and treat unattended generation as blocked.
2. **Frame render:** Is there a supported, scriptable way to export exactly one Excalidraw frame as PNG/SVG with the slide and assigned ink? The Printable Layout Wizard's PDF was observed on scratch, so manual PDF export plus local page rasterization is a plausible first bridge. Verify page-to-frame identity before relying on it.
3. **Scene insertion:** From a plugin-created Markdown card, determine precisely how `# Markdown Images`, `## Embedded Files`, SHA-1, `fileId`, `customData.markdownImage`, and `frameId` relate. Test add, reopen, resave, and export on a scratch copy. A self-consistent synthetic hash test is insufficient.
4. **Membership:** Should the card be a member of the existing slide frame, or should the frame be safely resized/rebuilt to include the new card? A frame's current geometry may be full, and the auto-framer can skip ambiguous or foreign-image collisions. Define a deterministic no-overwrite path and a blocked result.
5. **Account and cost:** Verify CLI installation, cached personal-account auth, subscription limits, Windows execution mode, and whether the run is using account quota or an API key/credits. No silent fallback to a metered API.
6. **Writer coordination:** Choose one writer to each exact nested-repo scene; account for Obsidian live saves and Git sync. Specify atomic replace or an in-vault apply route, precondition hashes, backup, and post-save audit.
7. **First release:** Re-read the owner's goal after review. Which smallest release delivers a card for one unambiguous scratch frame, with repeat-run safety and visible handwriting, before whole-deck scheduling or reflow? Avoid a server or database unless evidence requires one.

## Requested review output

Give a feasibility verdict per gate (`verified`, `requires probe`, `blocked`), compare at least the interactive agent and headless CLI paths, then write a formal standalone design only for the path that has sufficient evidence. Include capability table, repository/write map, exact output schema, identity and state transitions, cost/permission behavior, writer coordination, idempotency, acceptance criteria, and an explicit boundary between first release and later unattended whole-deck automation. Where ambiguity requires an owner decision, use the interactive Artifact convention in `academic-rag-model/CLAUDE.md`; a technical run manifest is not a decision surface.
