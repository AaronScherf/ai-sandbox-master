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
12. **Editable and reproducible.** Prefer inline SVG or HTML/CSS inside the Marp file (version-controlled, diffable, renders to PDF). Raster images only for illustration, kept in `figures/` with the prompt or source recorded.
13. **Accessible.** Each visual gets alt text or a one-line description for the speaker notes.
14. **Check in the PDF.** Every visual is viewed in the rendered PDF at full size, not only in the editor.

## 2. Who builds what

- **Claude (structural diagrams, in SVG or HTML/CSS in the deck):** decision landscape, decision flow, literature field map and gap-map inset, two-panel case comparison, 2×2 pipeline with loop, selection diagram pair, timeline. These depend on the exact content and wording, which changes with review, and must stay editable. Handing them off would add a round trip for little gain.
- **Codex (mechanics):** a small script that renders the deck to PDF, flags text overflow and fails if a visual placeholder remains. Optional.
- **Gemini (only if wanted):** *image generation* for non-informational illustration, for example a restrained background or icon set for the title and decision-landscape slides. Diffusion output is a poor fit for labelled diagrams (garbled text, invented detail) and for anything that carries a claim, so it should not make the diagrams above. It can also do a legibility and consistency review of the finished PDF.

## 3. Placeholders in the deck

| Slide | Visual | What it must show that the text does not |
|---|---|---|
| 2 | Decision landscape | Immediate response versus nexus design, which actors shape each, the discretion window narrowing |
| 3 | Decision flow | The three tests and the three outcomes; where the research measures shares |
| 4 | Literature field map plus 3ie gap-map inset | Five fields around the unfilled decision; the intervention-by-outcome matrix with empty cells |
| 5 | Two-panel cases | Same country, two answers, with what each tested; the stable-to-conflict path |
| 10 | 2×2 pipeline with loop | Maturity by colour; the loop between the four parts |
| 12 | Selection diagram pair | Same graph in two settings, marked arrows |
| 15 | Timeline | Dates, three gates, parallel workstreams |

Candidates not yet in the deck: slide 6 (overview map of problem, questions and goal), slide 9 (comparability profile as a radar or paired-bar chart; the appendix has the table), slide 11 (the transport cycle with the planner in each step).
