# Novelty check: status and a possible pipeline feature (v1)

*Claude, 2026-11-11. Records where the literature novelty check stands and what we learned about doing it reliably. Nothing here edits the strategy, deck, tracker or project plans.*

**Tags.** **[C]** checked by me against a registry or primary document. **[G]** Gemini's claim, not checked by me. **[I]** my judgement. **[P]** proposal, not built.

## 1. Status (2026-11-11)

| Item | State |
|---|---|
| Question | Are RQ1 (knowledge audit and value of information), RQ2 (decision space) and RQ3 (transfer diagnostics) already answered in the literature? |
| Handoff | `docs/superpowers/plans/2026-11-10-novelty-literature-check-handoff.md` (Gemini) |
| Gemini output | v1 (four notes), v2 (after my spot check), v3 (after a second correction), all in worktree `gemini-nexus-novelty-check`; nothing committed |
| Reference identifiers | v1: 13 of 38 DOIs correct [C]. v2: about 30 corrected, 10 still wrong [C]. v3: all DOIs resolve to the cited paper except the arXiv title for Montiel Olea et al. [C] |
| Open fix | Montiel Olea title, and honest tag vocabulary (`2026-11-11-novelty-check-third-fix-handoff.md`) |
| What nobody has done | Read any cited paper's text. Claims about what papers found rest on search snippets, abstracts and model recall [I] |
| Verdicts (v3, [G]) | RQ1 substantially answered in adjacent domains (health economics, IDinsight and GiveWell value-of-information work), open for humanitarian and transition programme design. RQ2 and RQ3: narrower gaps than v1 claimed (cyclic causal models exist; pre-registered model predictions exist in replication prediction; gap is a prospective transport prediction tested in a crisis) |
| Use now | As a reading list. Do not quote the verdicts or "surprises" in the talk until the papers behind the key claims have been read |

## 2. What went wrong, and the lesson [C, I]

- Identifiers recalled from memory looked plausible, resolved to real but unrelated papers, and were tagged "verified".
- A correction round that checked only the references we flagged left the others unchecked; the same error pattern showed up in new additions (Bongers et al.).
- A script match on title and first author proves the paper exists and is the one cited. It does not prove the paper says what the note says it says.
- My own spot check also erred once on the probe (endnotes skipped in text extraction), so checks need to be mechanical and complete, not sampled.
- Rule worth keeping: identifiers and bibliographic metadata come from a registry or the source file, never from model recall. Claims about content come from text that was read, with a quote-anchored span.

## 3. Would reading the full texts help? [I]

Yes, for the claims that carry weight (RQ1 prior art, the cyclic causal models point, pre-registered prediction work, the evidence-gap-map and capture-recapture claim, Crost et al.). Proposed process [P]:
1. Resolve every reference with the checker Codex is building.
2. Fetch open-access copies through the existing journal-discovery code (it already uses Unpaywall and a `needs_manual` worklist) [I, based on file names in `academic-rag-model/discovery/discover_journal_articles/`; not re-read].
3. Give Aaron a checklist of what could not be fetched.
4. Transcribe to markdown with the existing process and read excerpts by search, not by loading PDFs.
5. Keep the PDFs and transcripts outside the public repo. This repo is public and must not hold copyrighted source material; the existing ignore rules and the journal pipeline's storage location apply. Only short quotations with citations go into notes.

## 4. A possible pipeline feature: evaluate a proposal's contribution [P]

Aim: given a research proposal or question, report what is already known, what is partly known and where a contribution could fill a gap, with every claim traceable to a source.

Relation to existing work: it is close to finding evidence gaps in the intervention literature, but the goal is different (a contribution claim for one proposal) and the structure is open (no fixed 3ie taxonomy of interventions and outcomes).

Sketch of stages:
1. **Decompose** the proposal into claim-sized questions (like RQ1 to RQ3 and their sub-questions).
2. **Search** by registry and keyword, snowballing from the best matches (the journal-discovery code is the nearest existing tool).
3. **Resolve** every reference mechanically; reject anything the checker cannot match.
4. **Retrieve and transcribe** full texts where open; list the rest for manual retrieval.
5. **Extract** what each paper does, with quote-anchored spans, into a structured card (question, population, method, finding, limits).
6. **Compare** the proposal's claims to the cards: answered, partly answered, open, with the nearest prior work named for each.
7. **Report** with absence language kept proportional ("I found no example in these searches", search log attached) and a saturation or stopping rule when we have one (the open saturation subproject).

Design points to decide later: how to assess a proposal against papers without a fixed taxonomy; what counts as "answered"; how to estimate recall of the search; whether a human confirms the nearest-prior-work judgements.

## 5. Open items

1. Gemini third fix (Montiel Olea title; tag vocabulary).
2. Codex reference checker (separate session). The addendum with the v2 regression set is `2026-11-11-reference-checker-regression-addendum.md`.
3. Decide whether to fetch and transcribe the cited papers (section 3) and which ones first.
4. Read RQ1, RQ2, RQ3 for substance, starting with IDinsight's value-of-information work.
5. Decide whether the pipeline feature in section 4 becomes a pending to-do or a design spec.
