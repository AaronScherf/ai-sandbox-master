You are a Codex session. Task: a fresh, independent audit of a 14-slide Marp deck (plus appendix) for a 30-minute PhD peer talk, to check that (a) its logic holds and (b) its slide text makes sense to a reader with no prior context. This is a read-and-review task. Do not edit the deck. Follow docs/WORKTREE_WORKFLOW.md (your own worktree for the review note; explicit-path staging; never `git add -A`; do not push or land; report to Aaron).

## Audience to simulate
PhD students in economics and environmental science. They know causal inference and development economics basics. They do **not** know humanitarian-sector vocabulary, this research agenda, or its working shorthand. Each slide must be understandable on its own and in sequence.

## Review in two passes, in this order (the order matters)

**Pass 1: cold read (no context files).** Read only the deck:
`ai-sandbox/research/independent-research/notes/00_overview-and-strategy/nexus_evidence_agenda_slides.marp.md`
(on branch `claude/nexus-marp-deck`; the rendered `nexus_evidence_agenda_slides.pdf` beside it shows the visuals, which are SVG files in `figures/` named `nexus_*.svg`; open the PDF as well, since the visuals carry much of the content).
Read the slides in order, ignoring the `<!-- Note: -->` speaker notes and appendix. For every slide record, as a newcomer: what the slide claims; any term, abbreviation or shorthand not defined on or before that slide; any sentence whose meaning you cannot pin down; any step in the argument that does not follow from the previous slide; anything that reads as if it assumes knowledge you do not have. Write these down **before** opening any other file.

**Pass 2: logic check with context.** Then read, in this order, only these files (all under the same notes folder unless stated):
1. The deck's speaker notes and appendix (same file).
2. `Visual Standards - Nexus Evidence Agenda Slides - v1.md`
3. `Slide Document - Nexus Evidence Agenda - v6.md` (older text version; the deck supersedes it where they differ; the deck's appendix A9 lists open items)
4. `Slide Evidence Check - Egger and HSNP Definitions - v1.md`
5. `Review - Process Audit and Slide Document Gap - v1.md`
Do not read other notes unless a specific claim needs a source; if so, say which and why. Do not open PDFs of papers, images, or data. Full-text transcripts of source papers are git-ignored, in `ai-sandbox/research/journal-articles/crisis_transfer_review/processed_outputs/` (main checkout); use them only to spot-check a quoted fact, with short quotes (under 25 words).

## What to check
1. **Comprehension (from pass 1):** undefined terms; shorthand; slides that only make sense with the speaker notes; unclear antecedents ("the planner", "the transport model"); acronyms (HSNP, 3ie, J-PAL, DAG, IRB, RQ).
2. **Argument flow:** does each slide set up the next? Does slide 6 (the overview) actually match what slides 7 to 15 deliver? Are the three research questions, which the deck names Discretion and value of evidence, Decision mapping and Evidence transport, used consistently everywhere (no leftover "RQ1/RQ2/RQ3" labels in main slides, no renamed variants)?
3. **Logic and overreach:** claims stronger than the evidence shown; circularity; the decision-flow logic on slide 3 (room to choose, uncertainty, relevant evidence); the transport cycle on slide 11 (do the steps follow from each other? is "planner in the loop" consistent with what the prediction types and timeline say?); whether the gates on slide 14 (the timeline) are justified by what precedes them.
4. **Consistency:** between slides and between slide text and visuals (the SVGs in `figures/`); dates; component names (the deck deliberately dropped numbered labels like 1.1/2.2); the Bangladesh replication status ("nearly complete in full" is the owner's statement, unverified by files).
5. **Duplication and visual use:** against rule 1 of the visual standards (no repeated information between text and visual), list any repetition.
6. **Factual spot-checks:** only the Egger, HSNP and Bedoya descriptions on slide 5 against the transcripts (one-time transfers; bimonthly unconditional cash in four arid counties; graduation package of livestock asset, stipend, training, coaching). Do not verify the scale figures on slide 1 (a separate task covers them).

## Rules
- Tag every finding: **[C]** checked against a file or transcript (give file and line or page); **[I]** your interpretation; **[P]** a proposal.
- Rate each finding: BLOCKER (a newcomer would be lost or misled), SHOULD FIX, or POLISH.
- Do not fix anything; propose wording only as a suggestion.
- Do not rely on memory for any citation or fact.

## Output
One note, `Review - Slide Audit by Codex - v1.md`, in `ai-sandbox/research/independent-research/notes/00_overview-and-strategy/` in your own worktree, containing: (1) a short verdict (does a newcomer follow the talk, yes, mostly, or no); (2) a per-slide table: slide number, what a newcomer takes away, comprehension problems from pass 1, logic or consistency findings from pass 2; (3) a ranked list of the ten most important fixes; (4) a list of terms that need a definition on first use. Report back to Aaron with the verdict and a clickable `file://` link to the note.
