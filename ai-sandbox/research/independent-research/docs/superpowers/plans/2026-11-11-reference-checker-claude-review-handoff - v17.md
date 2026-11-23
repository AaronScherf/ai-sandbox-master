# Handoff to Codex: stop queueing rows a person cannot decide (v17)

From: Claude, 2026-11-22. To: Codex. Aaron approved this direction on 2026-11-22.
v16 is on main. Start from current `origin/main` in a new worktree, run `tools.active_work` before you start and before you ask to land, and report back before landing. This touches `tools/reference_checker.py`, `tools/reference_review.py`, their tests and the checker README.

DOIs are left out of this file on purpose, because the landing gate checks Markdown under `ai-sandbox/research/`. Find the rows with `python -m tools.reference_review list --status open` in the main checkout.

## 1. Why

After v16, a sweep of the 24 latest research notes queued 60 items for Aaron: 45 PLAUSIBLE, 8 UNCHECKED and 7 REVIEW. Most of them ask a person to match a surname and year against the DOI's registry record, which the checker already did. Here is what review has caught so far. Aaron's 10 decisions on the page were 8 "Same work", all on title-less rows, and 2 "Wrong paper". The two catches (Lopez, Rosenzweig & Udry) were titled rows, and v12 now flags that case automatically as TITLE_WRONG. Review of title-less rows has never changed an outcome.

What the 60 items contain:
- **36 give only author and year.** 26 of them are bare Fetch List rows. The same team's other papers are listed on the card, but the note offers nothing to choose between them, so a person cannot do better than the checker.
- **14 give a venue that matches the registry, often with volume and pages.** For example, Blattman et al. (2017) in the American Economic Review, volume 107 issue 4, pages 1165–1206. The checker compares these only to report a disagreement; it never counts agreement.
- **8 are links whose text describes the work** rather than naming authors, such as "Yemen, cash versus food in a crisis". Some point to datasets, replication packages or book chapters.
- **2 have a title the checker missed.** Kurdi (2021) and Bailey et al. (2020) put the title after a `<br>` in the same table cell. Shortland (2011) is assembled correctly from its field list, but its title starts with a quotation mark, and v16's prose rule (first word must start with a capital letter) drops it.

**Decision (Aaron, 2026-11-22).** A row should reach the page only when a person can add information that the checker lacks. This reverses part of the v11 ruling: same-team siblings no longer block a title-less row on their own.

## 2. Rules

1. **Title-less author-year rows.** When cited surnames and year agree with the registry and the citation gives no title, venue, volume or pages, the tier is AUTHOR_YEAR whether or not siblings exist. Keep listing siblings in the row's output for information; do not queue the row. An incomplete same-team lookup must not block this outcome, because siblings no longer change it.
2. **Venue, volume and pages count as agreement.**
   - When a title-less row's venue matches the registry (`_venue_matches`), and every volume and pages given also match, the tier is AUTHOR_YEAR. The reason says what agreed, for example "venue, volume, pages agree".
   - When the venue, volume or pages disagree (VENUE_DIFFERS, VOLUME_DIFFERS, PAGES_DIFFERS), the row stays in review as today.
   - When the cited venue or year matches a sibling's record better than the DOI's record, the row goes to REVIEW with the reason "cited venue/year match a different work by the same team" and that sibling named. This is the one remaining case where a person can choose. The guard's sibling records need venue and year for this; add the venue if it is missing, using the same OpenAlex listing.
3. **Missed titles.**
   - Inside one table cell, treat `<br>` as a separator. The segment after the author-year is then in title position, so `**Kurdi (2021)**<br>*Title*, *Venue*` has a title.
   - A title that starts with a quotation mark (`'`, `"`, `‘` or `“`) or an opening parenthesis is still a title. Only a lowercase first word marks the text as prose.
   - Do not read titles from other table cells; v4 showed that claim cells contain years.
4. **Descriptive links.**
   - A Markdown link whose text names no author and year is judged by its words. Compare the link text's content words (drop stop words and words under three letters) with the registered title plus venue.
   - Two or more shared content words gives a new pass tier, `DESCRIBED`, with the reason listing the shared words.
   - Fewer stays UNCHECKED and in review. A link text with no content words, for example "link", "here" or "Springer chapter 14", is never DESCRIBED.
   - The gate, the review page and the README treat `DESCRIBED` as a pass, like AUTHOR_YEAR.
5. **Review load in the report.** `raise` adds a short summary to its output and its JSON:
   - items queued per tier;
   - for each tier, the accept rate from human decisions recorded in the ledger;
   - any tier with at least 10 decisions that were all "accept", marked as a candidate for automation.

   Say in the README that the person reviewing should look at this after each sweep. This stops a tier that never needs a human from filling the queue again.

What still reaches the page:
- titled rows whose title disagrees and was not found elsewhere;
- a cited title found on a different DOI;
- rows where the venue, volume or pages disagree;
- rows that match a sibling better than the DOI (rule 2);
- descriptive links with too few shared words;
- defects, and anything a person must mark "quoted".

## 3. Tests (recorded answers only)

1. A title-less author-year row with five siblings is AUTHOR_YEAR, not queued, with the siblings still in its output.
2. A title-less row whose venue, volume and pages match is AUTHOR_YEAR, with "venue, volume, pages agree" in its reason. The same row with a wrong volume stays in review.
3. A title-less row whose cited venue matches a same-year sibling and not the DOI's record is REVIEW, naming the sibling.
4. The Kurdi `<br>` shape reads a title and is CONFIRMED against a matching record. The same shape with an invented title follows the TITLE_WRONG path.
5. The Shortland field-list shape, with its title starting with `'`, reads a title and is CONFIRMED.
6. Descriptive link: "Yemen, cash versus food in a crisis" against the registered title "In the Form of Bread? A Randomized Comparison of Cash and Food Transfers in Yemen" is DESCRIBED. "Springer chapter 14" is not.
7. The review-load summary counts tiers and accept rates correctly from a fixture ledger, and flags a tier with 10 accepts and no other decisions.
8. **Regression:** all v16 invented-title shapes (the four Brown shapes) still give TITLE_WRONG. The Egger, Nziguheba, Kihara and HarvestStat tests still pass.

## 4. Acceptance (report; do not tune)

On a copy of the main ledger, re-raise the same 24 notes:
- Build the list from the latest version of each tracked `.md` under `ai-sandbox/research/` that contains a DOI.
- "Latest" means the highest `- vN` overall, not the highest that still contains a DOI. That is why the Summary and the Correction Log drop out, which v16's count of 27 included.
- Exclude `docs/superpowers/plans/`, the unversioned `Literature Gap Memo.md`, and `journal-articles/needs_manual_downloads.md`, which is a generated download list.

Report:
- defects and open items per file;
- for every item still open, one line saying what a person must decide, which should be one of the cases in section 2;
- the review-load summary;
- how many of the 60 v16 open items cleared, by rule.

Expected: most of the 60 clear, and the three Literature Gap Memo Verification Review defects remain until Aaron marks them quoted.

## 5. Out of scope

Editing notes; the gate's scope; the review page's layout (it already shows siblings and reasons). Checking whether a paper supports a claim: no tier does that, and this handoff does not change it.
