# Reference checker v17: review, live sweep and owner findings (2026-11-23)

This covers the v17 work from handoff to live use: Claude's review of Codex's branch, the acceptance sweep, the sync of the review page, the owner's decisions, and what the owner's review showed about title-less citations. That last finding is the reason for handoff v18.

Paths:

```text
P = ai-sandbox/research/independent-research/docs/superpowers/plans/
N = ai-sandbox/research/independent-research/notes/
```

## 1. Why v17

The v16 sweep of 24 notes left 60 open review items and 3 defects. Of the 60:
- 36 were author-and-year only;
- 14 also gave a venue that matched;
- 8 were links whose text was not an author;
- 2 had a title the checker missed.

At that point the owner had made 8 decisions on title-less rows, and all 8 were accepts. Both real catches (Lopez et al., Rosenzweig & Udry) were rows with titles, and those are automated since v12. The owner's view was that a reviewer adds nothing to a name-and-year row except clicking the DOI. v17 (`P/2026-11-11-reference-checker-claude-review-handoff - v17.md`, landed `6b12d3a1`) set the rule that a row reaches the page only when a person can add information. It had five rules:
1. title-less author-year rows pass regardless of same-team siblings;
2. a matching venue, volume and pages pass, while any conflict stays in review;
3. better title detection;
4. descriptive links pass as DESCRIBED;
5. a review-load summary reported after each `raise`.

## 2. Review of Codex's branch

`codex/reference-checker-v17` took three review rounds before landing.

| Round | Finding | Fix |
| --- | --- | --- |
| 1 | `_venue_matches("", x)` returns True, so a title-less row with **no** venue matched every same-year sibling and went to REVIEW. This broke rule 1, for example Barbrook-Johnson & Penn (2022) and Bowen et al. (2020) in the Fetch List. | The better-sibling check requires a cited venue. |
| 1 | The new table extraction kept the whole cell, and the venue check compared the full tail, including a backticked DOI, for exact equality. So "Brown, Salisbury & Ball (2025), AEA P&P (`…`)" in the Spot Check became a false TITLE_WRONG. | Strip a trailing parenthetical or code span, and compare with an acronym-aware match. |
| 1 | The review-load accept rate read only `review.json`. But accepts are stored in `dismissals.json` and declines in `defects.json` or `false_positives.json`, with no tier, so the rate could never be computed. | `apply` saves `review_tier` on each of those entries, and the summary counts them. Older decisions have no tier and stay uncounted. |
| 2 | The round-1 venue fix matched in both directions. A title that contains the journal name was therefore read as a venue: Lin et al. (2022), "The impact of Russia-Ukraine conflict on global food security", in Global Food Security, lost its title and fell to PLAUSIBLE. An invented title that contains the journal name would also have skipped the title search. | `_venue_label_matches`: the cited text must be contained in the registered venue or be its acronym, never the reverse. Tests cover Lin, "AEA P&P", and an invented title containing the venue. |
| 3 | No further findings. | Landed by Codex at `6ced8bb4` (change `29ec8c08…`). |

## 3. Acceptance (copied ledger, 24 notes)

Of the 57 items still open in the main ledger, 38 cleared:
- 32 as AUTHOR_YEAR;
- 2 as DESCRIBED;
- 2 as CONFIRMED;
- 2 whose DOI is no longer in the note.

That left 20 open items and 8 defects:
- **4 known errors** already fixed on `claude/citation-error-fixes`: the Pritchett & Sandefur DOI in the Narrative and slides, and the Crost and Bold rows in Context Distance Cases v1.
- **3 deliberate quotes** in the Literature Gap Memo Verification Review.
- **1 real mislabel:** the Kenya Documentation Probe gives "Multidimensional Poverty Reanalysis" as the title of Song & Imai (2019), which is not the registered title.

Codex's report is `.worktrees/codex-reference-checker-v17/.worktrees/v17-acceptance.json`. It is local only.

## 4. Live sweep and page sync

The main checkout had staged renames that nobody had committed. They moved `N/00_overview-and-strategy/05_slides-and-talk/*` into `previous/`, and `projects/compound-shocks/literature_review.md` to `N/01_compound-shocks-panel/`. So the sweep ran from a temporary detached worktree of `main`, and the staged changes were left alone. 22 notes were raised from `main`. Four more were raised from `claude/citation-error-fixes` after rebasing it onto the new `main`, so that they used the v17 checker:
- the Narrative;
- the slides;
- Context Distance Cases v2;
- Adversarial Scan v2.

Superseded versions, such as Context Distance v1 and RQ1 v4, were left off the page.

The review page (`https://claude.ai/artifact/EQM9L22JbowiAGMfx8jUQe`) went from **60 items and 3 defects to 20 items and 4 defects**. The added defect is Song & Imai.

**Hazard:** the staged move of `presentation_slides.marp.md` collides with `claude/citation-error-fixes`, which edits that file at its old path. Land the fix branch before that move is committed.

## 5. Owner decisions (applied 2026-11-23)

24 decisions: 8 accept, 12 defer, 4 quoted. Ledger backups before apply are in the session scratchpad only.

| Decision | Note | Citation text | DOI |
| --- | --- | --- | --- |
| accept | Research Presentation Narrative | Meager (2019, AEJ: Applied) | `10.1257/app.20170299` |
| accept | Novelty Check - Claude Spot Check - v1 | Crost et al. (2016) (Spot Check correction text) | `10.1016/j.jdeveco.2015.08.005` |
| accept | Novelty Check - Context Distance Cases - v2 | Egger et al. (2022) vs Kenya HSNP Phase 2 LEWIE (2019), *Econometrica* 90(4) | `10.3982/ecta17945` |
| accept | Novelty Check - Fetch List and Priorities - v1 | Montiel Olea et al. (2024) | `10.48550/arxiv.2408.09187` |
| accept | Literature Gap Memo - Verification Review | Zens & Thalheimer (2025), memo DOI … | `10.1214/24-aoas1959` |
| accept | Literature Gap Memo - Verification Review | McGuirk & Burke (2020), memo DOI … | `10.1086/709993` |
| accept | Proposal Draft - v5 | Meager R (2019). *AEJ: Applied* | `10.1257/app.20170299` |
| accept | Proposal Draft - v5 | Lobell DB (2017). *PNAS* | `10.1073/pnas.1616919114` |
| defer | Novelty Check - Claude Spot Check - v1 | JBES 41(3), 839–851, 2023 … | `10.1080/07350015.2023.2241529` |
| defer | Novelty Check - Fetch List and Priorities - v1 | White, Saran, & Welch (2020) | `10.1002/cl2.1075` |
| defer | Novelty Check - Fetch List and Priorities - v1 | Dahabreh et al. (2020) | `10.1111/biom.13009` |
| defer | Documentation Probe - Kenya Data and Replication Sweep - v1 | 2012 Impact Evaluation Microdata (World Bank Microdata Library) | `10.48529/3jkx-m214` |
| defer | Literature Gap Memo - Verification Review | (search-query text, not a citation) | `10.1016/j.isci.2024.110628` |
| defer | Machine-Readable Literature Sources | published trial | `10.1257/aeri.20230069` |
| defer | Follow-up - Data Availability and Transportability Critique | AEA/openICPSR replication package | `10.3886/e192721v1` |
| defer | Feasibility Addendum - v2 | Springer chapter 14 | `10.1007/978-3-030-25120-8_14` |
| defer | Project Summary and References - v1 | Wortmann CS, et al. (2017). Nutrient Cycling in Agroecosystems 107:175-186 | `10.1007/s10705-017-9827-0` |
| defer | Proposal Draft - v5 | Wortmann CS (2017). *Nutrient Cycling in Agroecosystems* 109:269-289 | `10.1007/s10705-017-9887-1` |
| defer | Proposal Draft - v5 | Bruin S (2021). *Ecological Modelling* | `10.1016/j.ecolmodel.2021.109692` |
| defer | Proposal Draft - v5 | Wortmann CS et al. (2017). *Nutrient Cycling in Agroecosystems* 107:175-186 | `10.1007/s10705-017-9827-0` |
| quoted | Documentation Probe - Kenya Data and Replication Sweep - v1 | Song & Imai (2019) Multidimensional Poverty Reanalysis | `10.1080/21665095.2019.1582347` |
| quoted | Literature Gap Memo - Verification Review | McGuirk & Burke (2020), memo DOI | `10.1086/709977` |
| quoted | Literature Gap Memo - Verification Review | Abushama, Resnick, Siddig & Kirui (2023), memo DOI | `10.2499/p15738coll2.137021` |
| quoted | Literature Gap Memo - Verification Review | Zens & Thalheimer (2025), memo DOI | `10.1214/24-aoas1921` |

The Song & Imai "quoted" decision suppresses the defect for that exact citation text. The probe still gives a title that is not the registered one. If the intent was to correct it, the note needs the registered title.

After apply, `claude/citation-error-fixes` passed its landing check with 0 defects and 0 open items in all four notes (change `bf09f152…`). It is waiting for owner approval.

## 6. Owner finding: name, year and DOI do not show what was meant

The owner's account of the review, in their words:

> if all we have from the gemini generated report is a name and year, then I don't know what it was trying to cite most of the time. If there is a paper that matches the authors and year with a related topic, then it is probably right but I can't go read every single paper and every report to see if they line up. Some were very clearly unrelated DOIs but there were real papers with the author and year mentioned […] It seems like it was making up DOIs when it couldn't find one, and occasionally was using entirely unrelated work, so DOIs can't be taken as ground truth on what it meant to cite.

The owner gave an example: the Abushama, Resnick, Siddig & Kirui (2023) paper the memo meant exists on CGSpace (`https://cgspace.cgiar.org/items/b38475a5-f646-4985-8911-be6fe500ae89`), but the memo attached a different DOI.

**What this changes:**
- v17's AUTHOR_YEAR pass treats "this DOI is by these authors in this year" as evidence of what was meant. It is evidence that the DOI is real and by those people. It is not evidence that it is the work the writer intended.
- When Gemini picks a real paper by the same author and year, or invents a DOI that happens to resolve to such a paper, AUTHOR_YEAR passes it. No reviewer can tell otherwise from the citation alone. Only the writer knows what it meant.
- A writer who fills in the title **by reading the DOI's own record** launders the error. The title then matches by construction. The lookup has to go from the work to the DOI (search by title and author, then take the DOI from that record), never from the DOI to a title.
- None of this tests whether the paper supports the claim. That is a separate design, recorded as a pending to-do under `## Claim Support Check` in `docs/trackers/academic_hub_to_do.md`. It covers a download-and-transcribe queue ordered by how much the claim matters and how uncertain the reviewer is.

Handoff v18 (`P/2026-11-11-reference-checker-claude-review-handoff - v18.md`) moves the burden to the writer: in a note a branch adds or edits, a citation without a title is a defect for the writer to fix, not a review item.
