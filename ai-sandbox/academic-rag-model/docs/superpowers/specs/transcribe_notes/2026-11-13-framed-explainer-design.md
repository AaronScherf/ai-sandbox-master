# Framed Excalidraw explainer pipeline — design (2026-11-13)

**Status:** Design for owner approval. No code, scene or pipeline change is authorized by this document. Supersedes the open questions in the Codex [handoff](../../../status/transcribe_notes/2026-11-13-framed-excalidraw-explainer-claude-handoff.md) and the provisional [brainstorm](../../../brainstorms/2026-11-13-framed-excalidraw-explanation-cards.md). Builds on the landed [auto-framer](2026-11-07-excalidraw-auto-framer-design.md) and the [direct-edit explainer spec](2026-11-07-excalidraw-slide-explainer-design.md).

## Intent

The owner already gets useful explanations by telling Gemini in Antigravity to read slide PNGs and write explanations into an Excalidraw note. What is missing is **repeatability and a layout contract**: "run the explanation pipeline for my canvas" should work as one instruction, with no custom prompt, and every explanation must land where the auto-framer expects it, so that slide, handwriting and explanation ship together as **one PDF export** (the reason frames exist).

The owner's stated shape: slide conversion and framing already work and stay as they are. The explanation pass is a separate, later, chainable stage (group → explain → place → reframe). The subscription agent does the hard reading and writing. Deterministic code owns placement and audit. The handwriting must never be dropped: it is only meaningful next to its own slide.

## Goals, non-goals, anti-goals

**Goals**
1. One runbook an agent follows from a short instruction; no per-run prompt authoring.
2. One two-paragraph Markdown card per slide frame, placed consistently and inside its frame.
3. **Total ink coverage:** every `freedraw` stroke in the scene ends in exactly one disposition, and the apply step refuses to finish if the count does not reconcile.
4. Reruns are idempotent: no duplicate cards; changed inputs mark a card stale instead of stacking a second one.
5. Stages are separable and chainable (framing, then explanation, then reframing).

**Non-goals**
- Moving or rearranging existing slides or ink (a separate project).
- Fully unattended headless generation in the first release (blocked; see gates).
- A server, scheduler or database.
- Whole-vault scans; the caller names one scene.

**Anti-goals** (failure even if it technically works)
- Ink silently excluded from the PDF, or silently attached to the wrong slide.
- A card that invents equations or context not in the slide or ink.
- Any write to a scene file by something other than the single apply script.
- The framer flipping previously good frames to `skip` after cards exist.

## Evidence from the example notes (read-only, count-only decode)

Decoded element counts from the 16 lecture scenes under `econometrics/part_2/` and `microecon/part_2/` (the `processed_outputs/` copy excluded):

- The corpus is **heterogeneous**, so the pipeline must tolerate all of these inputs:
  - three econometrics scenes are **ink only** (1,031 to 2,570 strokes, no images, no frames);
  - three microeconomics scenes have slides (8 to 16 images, mostly paired with rectangles) and 2,143 to 2,562 strokes but **no frames and no explanations**; a fourth has 13 slides and no ink;
  - two econometrics scenes have slides and 1,216 to 1,483 strokes but no frames yet (the frame-then-explain chain case);
  - four econometrics scenes have 31 to 56 images (slides plus explanation panels), 17 to 30 frames and no ink;
  - the LIML2 scene has 24 slides, 24 Markdown-image explanations, 2,461 strokes and 25 frames (the only scene with all three).
- Slide size varies by about 2x (microeconomics slides about 607 x 457; econometrics 1,000 to 1,470 wide), so placement must be proportional to the slide, not absolute.
- **The existing Markdown-image contract is observable.** In LIML2, each explanation is an `image` element whose `fileId` equals a 40-hex marker `<!-- excalidraw-markdown-image:<fileId> -->` in `# Markdown Images`. Its `customData.markdownImage` holds `schemaVersion`, `version`, `source`, a `render` block (width 1000, font, border) and `renderedSize`. Its `frameId` is set. What is still unknown is **what bytes the hash covers**, which is why the design avoids reproducing it (Approach B).
- LIML2 explanation images already carry `frameId`, so "explanation inside the slide's frame" is an existing convention, not a new one. The exact slot geometry (slide, card and ink positions inside a frame) has not been measured; that is probe P5.

The decode used a throwaway script (not committed). These counts are the basis for the acceptance corpus below, not for any claim about whole-deck reliability.

## Approaches considered

| | Approach | Trade-off |
|---|---|---|
| A | Runbook only: the agent edits the scene file directly, as it does today | Least to build. Placement consistency depends on the agent obeying rules each run, it must hand-write unverified plugin bookkeeping, and it writes the file while Obsidian may have it open. |
| **B** | **Agent decides, script places.** The agent writes a result file; an in-vault Excalidraw script creates the cards, audits and reframes. | One extra component and a small framer change. Placement is identical every run and reruns cannot duplicate. **Chosen by owner.** |
| C | Fully headless via an `agy` CLI | Blocked: the CLI is not installed, and image input and account routing are unproven. It would later replace only the "agent runs the runbook" step in B. |

## Design (Approach B)

### Pipeline stages

```
 0 frame      (existing)  Auto-Frame Slides: slides + ink + slide-order sidecar -> frames
 1 collect    (Python)    stage frame rasters + scene facts into .agent_work/<run>/
 2 group      (agent)     assign ink + explanations to slides; write result file
 3 explain    (agent)     one 2-paragraph card per slide; transcribe ink regions
 4 apply      (in-vault)  validate result, place cards, audit ink coverage
 5 reframe    (existing + change)  Auto-Frame Slides again, aware of cards and sections
```

Stages 2 and 3 may run in one agent session. Stages are separable: the owner can run 0 alone, or 1-5 on an already framed scene.

### Roles and write map

| Component | Does | Writes |
|---|---|---|
| Collector (Python, `pipelines/transcribe_notes/`) | Parses the exact scene read-only; lists slides, existing explanations, strokes, frames, sidecar; rasterizes each frame; writes the task card | `.agent_work/<run>/` only |
| Agent (Antigravity, subscription) | Follows the runbook; reads rasters; writes `result.json` | `result.json` in the run directory only. **Never the scene.** |
| Apply script (in-vault, `Apply Explanations.md`, same family as Auto-Frame Slides) | Validates `result.json`, creates cards through the plugin's own EA API, audits, saves | the one scene, through `ea.addElementsToView` |
| Framer (existing, amended) | Frames slides, cards and handwriting sections | the one scene |

Repositories: collector, tests and docs live in the outer monorepo; the apply script, framer and scene live in the nested `academic_notes` repo. Keep the two repositories distinct; land each in its own worktree and branch.

### Result file (`result.json`, schema version 1)

```json
{
  "schema": 1,
  "scene": "<scene path relative to vault>",
  "scene_sha1": "<hash of the scene bytes the collector read>",
  "prompt_version": "explainer-v1",
  "provider": "antigravity-interactive",
  "slides": [{
    "slide_id": "<slide image element id>",
    "frame_id": "<frame id or null>",
    "ink": [{"region_id": "r3", "stroke_ids": ["..."], "disposition": "assigned|fallback_nearest",
             "confidence": 0.0, "rationale": "<one line>",
             "transcription": "<text or LaTeX>", "legibility": "legible|partial|unreadable"}],
    "existing_explanation_id": "<id or null>",
    "card": {"paragraphs": ["<para 1>", "<para 2>"], "status": "ok|needs_review", "reason": "<if needs_review>"}
  }],
  "sections": [{
    "section_id": "s1", "anchor_slide_id": "<slide id>", "stroke_ids": ["..."],
    "transcription": "<text>", "legibility": "...", "note": "<short transcription note>",
    "also_near": "<slide id or null>"
  }]
}
```

Validator rules (the apply script, not the agent, enforces): exactly two paragraphs when `status` is `ok`; every referenced ID exists in the scene at `scene_sha1`; no stroke ID appears twice; every `slide_id` is a current slide; LaTeX is allowed only inside transcribed or slide-visible content (the validator cannot check grounding, so the runbook requires a `rationale` and the Artifact review samples it).

### Handwriting coverage (the central rule)

**Invariant:** `strokes in scene = assigned + fallback_nearest + in sections`, no stroke counted twice, and every stroke ends inside the bounds of some frame. A mismatch blocks the write.

Disposition cascade, in order:
1. **Agent assignment** from the visual: each ink region next to its candidate slides, with confidence and rationale.
2. **Nearest-slide fallback** for regions the agent leaves unassigned, by box-to-box distance. Accepted only when the nearest slide is clearly closer than the second-nearest (default: nearest distance below 0.5 times the second) and no other group's ink lies between them. Recorded as `fallback_nearest` and listed in the report. The 0.5 value is my call and a tunable.
3. **Handwriting section** for everything else, including ink between two slides.

Two coverage guarantees are kept separate:
- **Visual:** the stroke is inside a frame, so it appears in the PDF. Deterministic, holds even for unreadable ink.
- **Interpretive:** the agent transcribes it and may use it in the card, with a legibility flag. Unreadable ink still ships visually; the card says so.

**Physical limit:** a stroke appears in a frame's PDF page only if it lies inside that frame's bounds. Assigning a stroke to slide A therefore changes the PDF only if A's frame can expand to cover it without swallowing other content (the framer's existing `foreign_content` rule). When it cannot, the stroke becomes part of a section, and the card for A may still mention it in text. No element is moved.

**Sections:** a handwriting section is a frame of its own, wrapping a cluster of strokes where they already are. A large block of ink near one slide is split along its natural gaps (the framer's existing ink clustering, `clusterInk`). Each section is **anchored to the slide it is closest to**, and PDF order is: slide page, then that slide's sections in reading order (top to bottom, then left to right), then the next slide. Anchoring is for page order only; content is not assigned. A section between two slides is anchored to the closer one and records the other in `also_near`, which the transcription note may mention. Sections get a short transcription note (what the handwriting says and which slide it relates to), **not** a two-paragraph card, because a full explanation would invent context.

### Card placement contract

Applies to every card the apply script creates.
- Card = a plugin-created Markdown image (an `image` element with `customData.markdownImage` and `frameId`).
- **Slot (default, subject to probe P5):** top-aligned with its slide, to the slide's right, a gap of 4% of slide width, card width equal to the slide width (clamped to the frame's free width), height from the rendered size. The slot rule is proportional to the slide so it survives the 2x size variation seen in the corpus.
- The card must lie wholly inside the slide's frame bounds, clear of the slide, existing ink and other cards. If the frame has no free slot, the frame may be **expanded** only under the framer's own rules (no foreign content, no overlap with a neighbouring frame, all ink still contained). Otherwise the result is `placement_conflict` for that slide with **no change to the scene** for it.
- Existing manual explanations are protected. `existing_explanation_id` set means update or adopt only when the owner selects it in the review Artifact; the default is `skipped_existing`.
- Every card carries `customData.autoExplainKey = <logical card key>` (see identity). The framer excludes elements with this key from its `explanations` and `foreign_content` classification.

### Framer amendments (nested repo, Node-tested)

1. Ignore elements bearing `autoExplainKey` when counting `multiple_explanations` and when computing `foreignContent`; treat them as frame members instead.
2. Include card IDs in the frame's member set so the exact-members adoption rule still matches after cards exist.
3. Accept section entries in the slide-order sidecar (`{"kind": "section", "anchor": "<slideElementId>", "seq": 1}`) and give them frames named e.g. `018 Slide 18 · notes 1`, ordered after their anchor.
4. Existing tests stay green; add fixtures for cards-present, sections, and a section overlapping a slide frame (expected: conflict, no write).

These are changes to `Auto-Frame Slides.md` and its Node test, which must be verified live on a scratch copy before the main script changes.

### Identity, state and idempotency

- **Logical card key** = scene namespace + frame ID + slide element ID. Sections: namespace + anchor slide ID + section sequence.
- **Input fingerprint** = slide asset hash, ordered ink stroke IDs with versions and geometry, frame association, `prompt_version`, and the accepted context-summary version. A pure frame resize does not change it.
- States: `pending -> generated -> validated -> applied -> verified`; terminal `needs_review`, `placement_conflict`, `declined`, `skipped_existing`.
- Same fingerprint at `verified` is a `noop`. A changed fingerprint marks the old result `stale` and creates **one** replacement revision of the same logical card, never a second visible card. A declined card stays suppressed on identical input.

### Writer coordination and safety

- Only the apply script writes the scene, **from inside Obsidian** through EA. This removes the external-writer races with Obsidian live saves and Git sync that the brainstorm had to engineer around.
- Use the framer's own pattern: before writing, check the canvas fingerprint and a scene SHA-1 against `scene_sha1`; abort with "scene changed since collect" if either differs. After saving, run a post-save audit (all original element IDs present, ink coverage count, every card inside its frame, card keys unique).
- The scene file is in the nested repo that syncs to the tablet. Run on a scratch copy until the acceptance corpus passes. Take a git commit of the scene before each real apply so recovery is `git checkout`, not bespoke backup logic.

### Cost and permission behavior

- First release uses the **interactive Antigravity agent** (the owner's existing subscription route); no API key, no metered call, no silent fallback. The result file records `provider`.
- An API driver or local Ollama remains an explicit opt-in with a cost estimate shown first (per the repo's over-$1 rule).
- The agent is given read access to the run directory and write access to `result.json` only; the runbook forbids editing the scene.

### Human review surface

Anything needing an owner decision uses an **interactive Artifact** with decisions in its `db` collection (per `academic-rag-model/CLAUDE.md`), not a JSON file to edit. It covers: low-confidence assignments, `fallback_nearest` results, `placement_conflict`, sections with near-tie anchors, and replace-or-adopt of existing explanations. The apply script reads the resolved decisions; `result.json` is machine state.

## Feasibility gates and probes (all must pass or be waived before the named stage)

| ID | Gate | Verdict now | Needed before | Fallback if it fails |
|---|---|---|---|---|
| P1 | Which EA call creates a rendered-Markdown image card, and does it set `fileId`, marker, `customData.markdownImage` and `frameId` as seen in LIML2? | requires probe | stage 4 | Write a minimal plugin-created card by hand on a scratch copy and diff its sections against the plugin's own; only then consider direct file writes |
| P2 | Can the apply script export one frame as PNG from inside the vault (copy frame elements into EA, then export)? | requires probe | stage 1 | Manual Printable Layout PDF plus page rasterization, with page-to-frame mapping proven by page count and name order |
| P3 | Can the agent trigger the Obsidian script (URI or command)? | requires probe | one-instruction UX | Agent finishes at `result.json`; the owner clicks the script button for stages 4-5 |
| P4 | Is `agy` installable, signed in on the account, able to read a local PNG headlessly, and on subscription quota? | **blocked** (not on PATH; the IDE launcher has no headless mode) | unattended release | Stay on the interactive agent |
| P5 | What is the actual slot geometry in LIML2 (slide, card and ink positions inside a frame)? | requires measurement | stage 4 | Use the default slot rule above |
| P6 | Does the framer's `kinds` classification need `autoExplainKey` exclusion beyond the two places listed, and do the 22 existing Node tests still pass after the amendment? | requires read plus test | stage 5 | Add the exclusion in `kinds` |

## First release and boundary

**First release:** the existing two-slide scratch scene (`Auto-Frame Scratch 2026-11-08`, 56 strokes, 4 images, 2 frames). Run stage 0 (already done), then collect, interactive agent produces `result.json`, apply on a scratch copy, reframe, export PDF. **Then** LIML2 as a large already-explained case, to prove `skipped_existing` and re-run `noop`. Microeconomics scenes (slides plus ink, no frames) cover the frame-then-explain chain. Ink-only scenes are expected to be `no slides: nothing to do` and must not error.

**Out of the first release:** headless `agy`, scheduling, whole-vault discovery, canvas rearrangement, the "adjacent section" ordering for scenes with no sidecar.

## Acceptance criteria

1. Scratch scene: one card per frame, inside its frame, with visible handwriting in the exported PDF; original element IDs preserved; save, reopen, resave and PDF export stable.
2. Second run on unchanged input: all `noop`, zero new elements.
3. Changed ink or slide PNG: the old card becomes `stale` and is replaced by one card, not two.
4. **Ink coverage audit passes** on the scratch scene, LIML2 and one microeconomics scene: strokes in equals assigned plus fallback plus section strokes, no duplicates, every stroke inside a frame; the report lists counts per disposition.
5. Existing LIML2 explanations are `skipped_existing` and untouched by default.
6. Each failure yields a specific no-write result: stale scene hash, `placement_conflict`, `needs_review`, schema violation, duplicate stroke, unknown ID, canvas changed since collect.
7. After cards exist, rerunning the framer yields `noop` for existing frames and does not classify cards as foreign content (the amended Node tests cover this; a live scratch run confirms it).
8. Ink-only and no-slide scenes exit with a clear "nothing to do", not an error.

## My calls (for the owner to check; all overridable)

- The nearest-slide fallback margin of 0.5 and the 4% gap in the slot rule are defaults, to be tuned against LIML2 geometry (P5).
- Sections get a transcription note, not a two-paragraph card.
- Interactive agent is the first-release generation route; `agy` is a later swap-in.
- Git commit before apply is the recovery mechanism, not a separate backup file.
- A single ordered context summary (5 to 10 preceding cards) is passed to the agent per batch for notation consistency; its exact format is left to the builder.
- Collector and prompt/runbook live in `pipelines/transcribe_notes/`; the apply script is added beside `Auto-Frame Slides.md` in the nested vault.

## Left to the builder

Runbook text and prompt wording; collector module layout; EA call details (P1); exact JSON schema validation library; Node test fixtures; Artifact page layout. Card-length thresholds should be set after the first rendered examples, and a longer "proof card" mode is a later decision, not part of this release.
