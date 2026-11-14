# Framed explainer: probe status (2026-11-13)

| Probe | Status | Evidence / next step |
|---|---|---|
| P1 plugin card route | resolved 2026-11-13 | Owner probe (plugin 2.29.1): `ea.addImage(0,0,TFile)` on a .md file creates an image element (500x106 for two short paragraphs, `customData` null, no `markdownImage`). Chosen route: external md embed, one file per card under `Excalidraw/Explanations/`, default adapter built into `Apply Explanations` (`defaultCardAdapter`). Cards are identified by `customData.autoExplainKey`, not `markdownImage`. Open: confirm PDF export renders md embeds in the scratch run. |
| P2 in-vault frame PNG export | untested | Owner-live. |
| P3 agent triggering the script | untested | Owner-live. |
| P4 `agy` CLI | blocked | Not available. |
| P5 slot geometry | verified | LIML2, 20 single-slide frames: explanation LEFT of slide, top-aligned, gap ~4% slide width, width 0.97-1.08x, frame ~2.5x slide width, ink right. |
| P6 framer identity | resolved by reading | Frame key = sorted ids of slide+explanations; cards (`autoExplainKey`) excluded from key but included in bounds. |

Remaining live work: scratch-copy apply run, then acceptance scenes (LIML2 noop,
microecon slides+ink without frames, ink-only, far-ink) and a PDF export check.
