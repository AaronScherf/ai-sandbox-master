# Batch Slide Explainer & Layout Placer — engineering specification

**Status:** Proposed for review, 2026-11-07. This specification task made no implementation or live canvas write; a separate Gemini agent has been editing the LIML2 scene.
**Target:** A reusable prompt and direct-edit workflow for a subscription agent. Python tooling under `pipelines/transcribe_notes/` is a later option, not a prerequisite.
**Source:** `docs/brainstorms/2026-11-07-excalidraw-slide-explainer-and-auto-framer.md` (untracked in the main checkout at spec time).

## Goal and requirements

Given an exact `.excalidraw.md` target and its slide PNGs under `academic_notes/<course>/lecture_notes/assets/` (including a `part_N` segment where present), have a subscription agent such as Gemini in Antigravity generate explanatory LaTeX/Markdown and edit that scene directly. Work in 5–10 sequential slides per pass so notation and narrative remain consistent. Preserve existing elements, manual explanations, frames, frontmatter, and line endings. The owner supplies the exact scene and prompt; the agent edits it in the same interactive session. No agent task-card staging, standalone Python pipeline, or API driver is required for the default workflow.

This is **slide explanation generation**, separate from `transcribe_excalidraw.py`'s canvas OCR, expansion, and `.rag.md` output. Relevant verified references: `pipelines/transcribe_notes/README.md`, `docs/superpowers/specs/transcribe_notes/2026-10-15-excalidraw-agent-driver-design.md`, and tracker `TODO-0030` (a separate transcription fidelity issue). The live `Econometrics 2026-11-04 LIML2 10.09.10.excalidraw.md` had 21 Markdown-image marker blocks at the read-only inspection snapshot and was modified in the nested notes repository. The user reports a successful, fast direct-edit run; final output quality, successful save/reopen, and rendered PDF have **not** been independently verified here. This is evidence that a direct agent workflow is viable enough to make it the default, not evidence that a new pipeline has been implemented.

## Capability and cost map

| Step / option | Discovery and scope | Side effects / cost | Output | Idempotency | Verification |
|---|---|---|---|---|---|
| Direct subscription-agent pass (default) | User-named scene and its linked local slide PNGs; 5–10 sequential pending slides | Agent subscription usage; direct nested-repo scene edit, no separate metered API call | Explanations and positioned Markdown images | Check existing slide/panel mapping before edit; update only explicitly requested panels | Diff, section/scene integrity checks, Obsidian reopen and visual review |
| Separate slide transcription (optional later) | Same PNGs, only if reusable transcripts are needed elsewhere in academic-hub | Additional processing and transcript writes; can reuse existing `transcribe_notes` conventions | Reusable slide text | Key by slide asset content | Compare transcript to PNGs |
| API driver (optional later) | Same bounded batches | Metered personal API and local scene writes | Same panels | Cache by asset/prompt/model version | Cost report and fixture/live checks |
| Local Ollama (optional later) | Same bounded batches | Local compute and scene writes | Same panels | Same keys | Vision capability and quality check |
| Auto-framer (separate tool) | Completed slide/panel positions only | Frame mutation in Obsidian | Printable frames | Stable frame IDs | Scratch export and repeat-run audit |

This is an interactive, user-triggered workflow. There is no scheduled execution, server, cache database, or unattended retry requirement. If no human/agent is available, the scene remains untouched. Existing `.agent_work` collect/submit infrastructure is for transcription and is **not** required here. If a human must decide between ambiguous slide pairings, use an interactive Artifact or ask in the live agent session; do not encode a silent decision in task cards.

## Exact input scope and prompt contract

The user supplies the exact scene path and the range of slides or asks for the next unpaired group. The agent resolves only that scene's linked PNGs in its lecture `assets/`, inspects existing slide and explanation objects, and reports missing/ambiguous links before editing. It must not scan or alter other course scenes. It groups 5–10 slides in visual reading order, with a shorter final group permitted. Include the previous accepted notation summary and adjacent slide context. Map each generated response to the source slide's element ID and asset filename, then confirm that mapping before insertion.

The reusable prompt shall instruct the agent to: (1) read only the named scene and selected PNGs; (2) preserve unrelated Markdown sections, scene elements, IDs, and line endings; (3) produce the pedagogical sections below, grounded in each image; (4) fit rendered panels or split them semantically; (5) place each panel beside its source slide using the local layout rather than assuming absolute x coordinates; (6) record any visibly printed slide number with source element ID and asset hash for the auto-framer's `<scene basename>.slide-order.json` input, marking unreadable/duplicate numbers rather than guessing; (7) save safely and report per-slide `created`, `updated`, `skipped`, or `needs_review` with reason; and (8) audit the saved note against its pre-edit inventory. A direct edit should operate on a stable saved snapshot, avoid racing Obsidian/sync, and create a recoverable local copy before modifying compressed scene data.

Panel identity is `(scene path, source slide element ID, panel part)`. A repeat pass skips an existing matching panel unless the user requests regeneration. A changed PNG or a changed explanation request calls for review of the existing panel, not a duplicate. Skipped/declined ambiguous slides retain their status in the agent's completion report and are not presented as fresh discoveries during the same run. Persisted machine state is optional because the scene itself contains the panel mapping.

## Pedagogical template and height control

Each explanation must be faithful to the slide and use these headings as applicable: **Conceptual Intuition**, **Formal Derivation**, **Estimator Formulae**, **Regularity / Asymptotics**, **Practical Software Notes**. The prompt requires definitions of all symbols, complete steps for nontrivial equalities, and explicit distinction between slide claims and added explanation. Omit inapplicable headings rather than invent material. Use `$...$` and `$$...$$` consistently; request no raw HTML or unsupported Markdown constructs.

The 520 px rendered-height limit is a **measured-layout acceptance target**, not something a character count can guarantee. Initial preflight heuristic: flag more than roughly 1,800 characters or four display equations, and estimate height from wrapped line count at the intended 950–1070 px panel width, heading spacing, and equation blocks. Tune only against a small varied set of real rendered examples. Render each generated block through the installed Excalidraw Markdown-image mechanism and read its actual `height`; if above 520 px, ask the agent for a tighter rewrite or split semantically. Never truncate mathematics to meet a budget. A character estimate alone is not a pass.

## Semantic overflow and placement

A proof/exercise is a two-part candidate when its rendered height exceeds 520 px, when it contains more than four display equations and a natural setup-to-conclusion boundary, or when the slide is explicitly an exercise. Split at a mathematical transition: **Part 1** states assumptions, definitions, and setup; **Part 2** carries derivation, interpretation, or consequences. Both parts must be independently intelligible, preserve equation dependencies, and be reasonably balanced after rendering. For a two-panel exercise target an approximately 1840 × 800 px frame, with each panel fitting the inner height; otherwise report `needs_manual_layout`. The auto-framer owns the eventual frame, so the agent creates panels and records intended membership in its completion report.

For the regular 2SLS reference, the left lane spans approximately x ∈ [−1050, 950] and places `[Explanation] → [Slide]`; the right lane spans x ∈ [950, 3000] and places `[Slide] → [Explanation]`. LIML2 uses a much wider and less regular layout, so these are example coordinates, not hard constraints. Preserve each slide's position and choose an explanation slot from its actual neighboring boxes, with a roughly 40 px gap when feasible. Align vertical centers, avoid existing elements and handwriting, and reject collisions; do not move a manual slide or overwrite an explanation. A 950–1070 px explanation width and actual rendered height feed the slot calculation. Report source slide ID, printed page number if legible, and local pair order for the framer. If no safe slot exists, report `placement_conflict` without modifying the scene.

## Scene serialization, writes, and audit

The agent must parse the note's `# Markdown Images`, `## Embedded Files`, and fenced `compressed-json` drawing sections without rewriting unrelated text. For each new explanation, create a unique Markdown-image marker block, register the plugin-compatible 40-hex SHA-1 key under `## Embedded Files`, and create one scene image element referencing that key. **Prerequisite:** determine from a plugin-created panel exactly which bytes are hashed and how marker ID, embedded-file ID, `fileId`, and `customData.markdownImage` relate; the reference note shows distinct values, so they must not be conflated. The agent may use a validated local LZ-String helper for scene round-tripping; it must demonstrate decode/encode/decode equality on a scratch copy before direct scene writes. Unsupported compression or schema versions fail closed.

Apply against a saved-scene revision/hash and refuse if Obsidian or sync changed it since planning. Use a temporary sibling file, flush it, then atomic replace within the same volume where supported, preserving original line endings and all untouched sections. Keep a recoverable backup until audit succeeds. Reparse the written scene; assert every original element ID remains, every new `fileId` resolves exactly once, marker/registry/scene counts agree, and decompression still works. Reopen in Obsidian to ensure the plugin renders and preserves the new panels on resave. The auto-framer runs only after this verification. Any direct repair or regeneration needs exact target selection, per-target machine-readable results, writer coordination, atomic output, and a post-run audit.

## Repository and write destinations

| Path | Repository | Write and coordination rule |
|---|---|---|
| `academic-rag-model/pipelines/transcribe_notes/` and mirrored tests | Outer monorepo | Optional future reusable helper/transcription code; no code in this spec task |
| `academic-rag-model/docs/superpowers/specs/transcribe_notes/` | Outer monorepo | This design in `codex/excalidraw-slide-specs` |
| Agent completion report in the interactive session | Subscription-agent workspace | Per-slide results for human review; no required `.agent_work` task cards |
| `academic-hub/academic_notes/<course>/.../assets/*.png` | Nested `academic_notes` repo | Read-only source; no asset publishing or rewriting |
| `academic-hub/academic_notes/<course>/.../*.excalidraw.md` | Nested `academic_notes` repo | Future exact-scene write in a child-repo worktree or coordinated single-writer checkout; pause Obsidian Git sync during apply |
| `academic-hub/academic_notes/<course>/.../<scene basename>.slide-order.json` | Nested `academic_notes` repo | Optional number map produced while the subscription agent already reads slide PNGs; coordinate with scene writer |

The outer monorepo worktree does not isolate the nested notes repository. `academic_resources/` mirrors course paths for heavy sources but is outside this tool's write scope. A live note write must coordinate with Obsidian, tablet sync, existing transcription writers, and any framer invocation on the same scene.

## Acceptance and verification

- On a scratch copy, verify LZ-String decode/encode/decode equality, preservation of unknown scene fields and note sections, malformed payload refusal, and line endings. Check SHA-1 against a plugin-generated panel, including marker/registry/`fileId` linkage, not merely a self-consistent hash.
- Review a varied sample of source PNGs and generated explanations for grounding, notation continuity, rendered height, both grid lanes, tall content, and exercises. Repeat the same prompt over an already completed slide; it must skip or update by identity, with no duplicate marker, registry entry, or image element.
- The interactive agent's report lists each slide ID, asset, outcome, rendered size, and any blocked reason. Diff and reopen the saved scene; verify old elements persist and newly inserted panels render. The user-reported LIML2 run is useful live workflow evidence, while final quality/export behavior awaits independent inspection.

**Smallest usable release:** the prompt-driven direct-edit workflow that Gemini is already exercising, with an integrity and visual checklist. Separate transcription is a possible later improvement when reusable slide text is needed in academic-hub; it is not justified by speed or cost in the current run. Python staging, API/Ollama drivers, a server, scheduler, and database are deferred. Remaining validation gates are the exact plugin SHA-1/file identity contract, save/reopen stability, and the finished LIML2 note's visual quality.
