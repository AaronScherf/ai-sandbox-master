# Framed explainer: probe status (2026-11-13)

| Probe | Status | Evidence / next step |
|---|---|---|
| P1 plugin card route | static only | Plugin 2.29.1: local Markdown cards come from internal code (`renderMarkdownToSVG` -> `ea.addImage(dataURL)` -> fileId swap -> `customData.markdownImage` {schemaVersion, version, source:"local", render, renderedSize} -> `excalidrawData.setMarkdownImage`), not exposed on `ea`. Public alternative: external md embed via `ea.addImage(TFile)`. **Owner:** run `Probe Markdown Card` on a scratch copy, paste console output here, then install `window.ExplainerCardAdapter {measureCard(ea,view,md), createCard(ea,view,spec)}`. |
| P2 in-vault frame PNG export | untested | Owner-live. |
| P3 agent triggering the script | untested | Owner-live. |
| P4 `agy` CLI | blocked | Not available. |
| P5 slot geometry | verified | LIML2, 20 single-slide frames: explanation LEFT of slide, top-aligned, gap ~4% slide width, width 0.97-1.08x, frame ~2.5x slide width, ink right. |
| P6 framer identity | resolved by reading | Frame key = sorted ids of slide+explanations; cards (`autoExplainKey`) excluded from key but included in bounds. |

Remaining live work: scratch-copy apply run, then acceptance scenes (LIML2 noop,
microecon slides+ink without frames, ink-only, far-ink) and a PDF export check.
