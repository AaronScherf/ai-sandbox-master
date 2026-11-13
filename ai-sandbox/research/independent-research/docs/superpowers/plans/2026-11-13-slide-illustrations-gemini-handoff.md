You are a Gemini (Antigravity) session. Task: generate a small set of decorative illustrations for a PhD peer-talk slide deck on evidence and decisions in prolonged humanitarian crises. Follow docs/WORKTREE_WORKFLOW.md (your own worktree; explicit-path staging; never `git add -A`). Do not edit the deck, do not commit or push without reporting to Aaron.

## Rules (from `Visual Standards - Nexus Evidence Agenda Slides - v1.md` in `ai-sandbox/research/independent-research/notes/00_overview-and-strategy/`)
- Illustrations are **decorative only**. They must carry no claim, no data, no labels. Do **not** generate diagrams, charts, maps with borders, or anything with text: image models garble text and invent detail.
- **No text, letters, numbers, logos, flags, or organization marks** anywhere in the images.
- **No identifiable people and no faces.** No depictions of suffering, children, camps or violence. Prefer landscape, abstract shapes, paths and objects.
- Calm, restrained, editorial style. Flat or soft-gradient vector-like look, not photorealistic. Palette to match the deck: navy `#1e3a8a`, slate `#334155`, light grey-blue `#e2e8f0` and `#f1f5f9`, with one warm accent (`#d97706`) used sparingly; large areas of white or near-white so slide text stays readable on top.
- 16:9, 1920x1080 PNG, each under 1 MB (reduce or recompress if needed).

## Images to produce (two variants each, so Aaron can choose)
1. **title_banner**: a wide, low-contrast banner for the title slide. Idea: an arid plain with a distant horizon and a few faint converging paths that branch and merge, suggesting many possible routes and decisions. Visual weight in the bottom third; top two thirds nearly white.
2. **appendix_divider**: a simple abstract texture or pattern (layered contour lines or a faint topographic grid) in grey-blue, to sit behind the single word "Appendix". Very low contrast.
3. **section_motif**: a small square (1080x1080) motif for reuse as a corner accent: a minimal compass-like or fork-in-the-path shape, navy with one amber element, transparent or white background.

## Output
- Save files in `ai-sandbox/research/independent-research/notes/00_overview-and-strategy/figures/generated/` named `<image>_v1.png` and `<image>_v2.png`.
- Write `figures/generated/PROMPTS.md` recording, for each file: the exact prompt, the model and tool used, and the date.
- Report back to Aaron with a short description of each and clickable `file://` links. Say plainly if any image contains text, a face, or a logo, and discard it.
