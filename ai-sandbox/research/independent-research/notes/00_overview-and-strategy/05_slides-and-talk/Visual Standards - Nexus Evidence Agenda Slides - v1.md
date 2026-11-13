# Visual standards for the Nexus evidence agenda slides (v1)

*Claude, 2026-11-13. Standards for the dashed "VISUAL" placeholders in `nexus_evidence_agenda_slides.marp.md`. Proposals for the owner to accept or change.*

## 1. Rules

1. **No repetition.** A fact appears once, in the text or in the visual. The slide text carries the claim, the definition and the "so what"; the visual carries structure, relationships and comparison. Never caption a visual with a sentence that restates its labels.
2. **A visual must add understanding.** Use one only where the form shows something prose cannot: sequence, loop, branching, containment, position on a scale, a matrix with gaps, a before-and-after. If the picture is a table in boxes, keep the table or cut it.
3. **One idea per visual.** Test: can the audience say what it shows in one sentence after five seconds?
4. **Label sparingly.** Short labels inside the shapes, at most about 6 words each; no paragraphs. Detail goes to the speaker notes or the appendix.
5. **Legible at the back of the room.** Minimum 16 px text at slide scale (the deck's body text is 19 px); high contrast; do not rely on colour alone (add shape, line style or a label).
6. **Meaning-carrying colour, used consistently.** One palette for the whole deck: for example one colour for "built", one for "in design", one for "planned", the same on every slide. Colour distinguishes status or role, never decorates. Keep it readable in greyscale (printing, projectors).
7. **Direction and grouping are explicit.** Arrows only where something flows or causes; proximity and enclosure for groups; a single reading order (left to right, top to bottom).
8. **Illustrative is labelled.** Placeholder values, hypothetical examples and the 1-to-6 scale are marked "illustrative" on the visual itself.
9. **No unverified numbers inside visuals.** Figures from the evidence-use scans stay out; the scale figures stay out until verified; Egger and HSNP quantities appear beside each other only with the definition note.
10. **Honest status.** Components are shown as built, in design or planned exactly as in the maturity table; the visual must not suggest an integrated system.
11. **Source and checked.** Every visual that depicts a source's content says which source, and the speaker note says what was read.
12. **Editable and reproducible.** Diagrams are SVG files in `figures/` (named `nexus_*.svg`) referenced from the deck as images, or HTML/CSS in the deck (Marp strips inline `<svg>`); version-controlled and diffable. Raster images only if needed, with the source recorded.
13. **Accessible.** Each visual gets alt text or a one-line description for the speaker notes.
14. **Check in the PDF.** Every visual is viewed in the rendered PDF at full size, not only in the editor.

## 2. Who builds what

Decision (2026-11-13): Claude builds all figures as SVG in `figures/`. Generated decorative images (Gemini) are not needed for a peer talk; they would suit a public-facing version. A Codex or Gemini pass is used for review, not for drawing.

## 3. Visuals in the deck (all built 2026-11-13)

| Slide | File in `figures/` | What it shows that the text does not |
|---|---|---|
| 2 | `nexus_decision_landscape.svg` | Immediate response versus nexus design, who shapes each, the discretion window between constraints |
| 3 | `nexus_decision_flow.svg` | The three tests, the exits and the three outcomes; what the research target is |
| 4 | `nexus_literature_map.svg` | Five fields around the open gap; a schematic 3ie gap map with empty cells |
| 5 | `nexus_three_studies.svg` | Payment schedules of the two Kenyan studies, who and what they measure, the Bedoya package and path |
| 7 | `nexus_discretion_instruments.svg` | The four questions, then desk audit followed by partner funnel |
| 8 | `nexus_evidence_barriers.svg` | What informs a plan versus the three barriers evidence passes through |
| 9 | `nexus_comparability_profile.svg` | Objective and planner similarity per dimension against thresholds |
| 10 | `nexus_pipeline_2x2.svg` | The four components, their maturity, and the loop between them |
| 11 | `nexus_transport_cycle.svg` | Six steps, with who acts at each |
| 12 | `nexus_selection_diagram.svg` | The same causal graph in source and target, with marked arrows |
| 14 | `nexus_timeline.svg` | Dates, three gates, parallel workstreams, what needs IRB approval |

Slide 6 (problem, questions, goal) is an HTML/CSS diagram in the deck. Slides 1, 13 (approaches table) and the appendix are text or tables by design.
