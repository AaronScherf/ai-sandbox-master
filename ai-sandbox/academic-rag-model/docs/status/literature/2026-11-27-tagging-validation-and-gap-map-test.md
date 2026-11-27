# Tagging validation and the gap map test (2026-11-27)

Follows [the 2026-11-25 handoff](2026-11-25-spec-a-transcription-handoff.md). Covers handoff item 7 (blind labels),
what it changed, and the next test. It also feeds the later evidence gap map recreation pipeline (umbrella design,
section 10).

## Decisions (owner)
- **Document types** (Spec A amendment 2026-11-26): `grey_literature` merged into `report`; conference papers are
  `working_paper` with subtype `conference_paper`; an evaluation commissioned by the implementer or funder is a
  `program_document`.
- **Tags are a broad catchment.** Intervention and outcome tags cover anything relevant, including what a review
  synthesises. Narrowing to direct evaluations is a later filter, not a tagging rule.
- **A management or planning method is not an intervention, and quoted context statistics are not outcomes.** From
  the owner's ruling notes. Not yet in the tagger's prompt.
- **A primary evaluation needs an intervention that was carried out.** A simulation of a real program counts; a
  projection of proposed ones does not. Not yet in `classify` (it still says "evaluates a program, policy or practice
  itself").

## Results

### Report type and applicability, 25 papers
Owner labelled blind; Codex was the second reader; the owner ruled on the 16 fields (14 papers) that differed, with
the other answers and quotes in view. The reference is therefore adjudicated, not blind, and the 11 papers on which
all three agreed were not re-examined.

| Matches the reference | Report type | Applicability |
|---|---|---|
| Pipeline | 23/25 | 23/25 |
| Codex | 24/25 | 17/25 |
| Owner's blind labels | 24/25 | 16/25 |

The 25 were used to define types and re-type the corpus, so they are not held out for type. Main intervention and
outcome terms were not labelled.

### Evidence role, 30 further papers
Drawn at random within the model's own groups (15 primary evaluation, 10 other, 5 synthesis), model value hidden.

| Model said | n | Owner: primary | Owner: other | Owner: synthesis |
|---|---|---|---|---|
| primary_evaluation | 15 | 10 | 3 | 2 |
| other | 10 | 0 | 9 | 1 |
| synthesis | 5 | 0 | 1 | 4 |

- The errors in `primary_evaluation` are mostly theory or methods papers that use real data to test an idea.
- One answer was changed from primary to other after the owner clarified the rule above; the page's wording had
  allowed a simulation of a proposed intervention.
- Weighting the groups back to the 141 papers sampled from gives roughly 17% direct evaluations (wide uncertainty).
  An earlier in-session figure of 20 to 25% predates the changed answer.

### State of the index
All rulings (16) and evidence-role answers (30) are saved as owner decisions in
`research/.index/research_profile/decisions.json` (backups in `research/.agent_work/`). Effective evidence role:
41 primary evaluation, 48 synthesis, 86 other, 20 blank. **31 of the 41 primary evaluations are unchecked.**

## Next test: tags against 3ie's per-study terms

Map: [food security in humanitarian settings](https://developmentevidence.3ieimpact.org/egm/food-security-in-humanitarian-settings-egm)
(192 studies in its CSV; 184 after dropping protocols and ongoing studies).

- Each study's page on the Development Evidence Portal lists intervention and outcome terms from the global taxonomy
  we already load. On the three pages pasted so far, all 25 terms match our vocabulary by label.
- The map CSV and the search export carry no per-study terms. The search export has a `Record Type` column that
  separates reviews (`SRR`). The saved map page shows which cells are filled but no paper lists were found in it.
- The owner pastes each page's text into `research/.agent_work/egm_test/portal_pages.md`: 30 studies drawn at random
  (seed 20261127), plus a separate set of reviews picked by hand, because a random 30 holds only about three.

Procedure:
1. Check each paste's title and abstract against the map CSV.
2. Fetch openly available full texts; the owner downloads what is missing.
3. Give a cost estimate before transcribing or tagging.
4. Tag from the papers only. The tagger never sees the pasted pages.
5. Report recall of 3ie's terms (leaf and branch level) and how many evaluations are marked `primary_evaluation`.
   Report the random and hand-picked groups separately.

Limits: extra tags are not scored as errors, since 3ie may record only some outcomes; agreement on terms is not
checked for precision. The portal's terms of use have not been read; do not automate page downloads without doing so.

Not built: reading the pasted pages into an answer key (`cli eval` takes a 3ie CSV or label JSON today).

## For gap map recreation (later)
- The map's rows and columns are its own categories (for example "Cash Transfers", "Food Expenditure"), not exact
  terms of the global taxonomy. Recreating it needs that framework as a vocabulary, or a crosswalk, plus per-study
  cell assignments, which we do not have.
- A map built from our tags must filter on the effective evidence role (decisions over model values), not on tags
  alone, since reviews and theory papers carry many tags.
- Filter by keeping `primary_evaluation`; dropping only `synthesis` leaves theory and context papers in.
- `summary` still counts tags that an owner's applicability decision rules out (two papers). Fix before any map
  counts from it.
- Synthesis check against 3ie's reports: on the to-do list (`docs/trackers/academic_hub_to_do.md`).

## Open
- Check the other 31 primary evaluations by hand, or tighten the `evidence_role` definition and re-run it with a
  fresh test sample.
- Add the two ruling-note rules to the tagging prompt (the 25 would then no longer test applicability).
- Six books and chapters have no applicability (owner: ignore for now).
- Handoff items 1, 2, 4, 5 and 6 are unchanged.

## Private files
All under `ai-sandbox/research/.agent_work/` (gitignored): `blind_label/`, `second_reader/`, `adjudication/`
(reference.json), `evidence_role/` (sample and answers), `egm_test/` (paste document, sample.json, map_context.md).
Review pages (private): [label disagreements](https://claude.ai/artifact/DVhUPnLAjkrgYebJETJLbJ),
[primary evaluation check](https://claude.ai/artifact/Q4nPkPB1XF4wyQGyijjrKG).
