# Handoff to Codex: false positives from the first full sweep (v16)

From: Claude, 2026-11-18. To: Codex.
State: on 2026-11-18 Claude raised the latest version of every tracked research note that contains a DOI: 24 files, against the main ledger. The result was 22 defects and 48 open items. Claude checked each checker defect by hand (Crossref, read from the note). About half are checker errors, listed in section 1. Fix them before the ledger is shown to Aaron, otherwise he reviews noise and the gate blocks edits to correct notes.

v14 (lookup failures) and v15 (discovery) are separate work orders. v16 touches `tools/reference_checker.py` and `tools/reference_review.py`, so do it after v14 lands, on its own branch, or fold it into the v14 branch if that has not landed yet. Report before landing.

DOIs are left out of this file on purpose: the landing gate checks Markdown under `ai-sandbox/research/`. Find the rows with `python -m tools.reference_review list --status all` and in `.reference_checker_review/defects.json` (read only) in the main checkout.

## 1. Checker errors (fix)

1. **Venue parsed as title.** `Proposal Draft - v5.md` cites "Nziguheba G et al. (2021). *Nutrient Cycling in Agroecosystems*. doi…" and "Kihara J et al. (2016). *Agriculture, Ecosystems and Environment*. doi…". These citations have no title. The checker took the journal name as the title, the title search found no such paper, and the rows became TITLE_WRONG. Rule: a parsed title that matches the registered container-title (score ≥0.9), or that is the italic segment directly before the volume or DOI, is the venue. Treat that row as having no title, which sends it to AUTHOR_YEAR or PLAUSIBLE.
2. **Short title that is a prefix of the registered title.** "Lee et al. (2025). HarvestStat Africa. *Scientific Data*" is registered as "HarvestStat Africa – Harmonized Subnational Crop Statistics for Sub-Saharan Africa". It appears in `Project Summary and References - v1.md` and in `Proposal Draft - v5.md`. Rule: if the normalized cited title is a whole-word prefix of the registered title (or of title plus subtitle) and is at least two words long, treat it as a strong match (CONFIRMED when the year agrees). Never run the title search on such a row.
3. **Comparison prose parsed as title.** `Novelty Check - Context Distance Cases - v1.md` has a heading-like line, "Egger et al. (2022) vs Kenya HSNP Phase 2 LEWIE (2019)", which the checker read as a citation with the title "vs Kenya HSNP…", giving TITLE_WRONG. Rule: only run the title-not-found path when the citation has a recognisable bibliographic shape (a year followed by a title-like segment, then a venue, volume or DOI). Prose mentions with an author-year and a DOI link stay identity-only and are never sent to the title search.
4. **Trailing Markdown captured inside a DOI.** Three NOT_FOUND rows are DOIs that end in a backtick followed by `**`, or in `)):**`. They come from `Literature Gap Memo - Verification Review.md` and `presentation_slides.marp.md`. Strip trailing backticks, asterisks, underscores and unbalanced closing parentheses or brackets, the same way trailing `.` and `,` are already stripped. Keep balanced parentheses inside DOIs (for example `S0000(00)00000-0`).
5. **DOI attached to the wrong mention on a line.** In `presentation_slides.marp.md`, one line has two Markdown links: Meager 2019, and Pritchett & Sandefur 2015. Meager's DOI was paired with the Pritchett text and came out WRONG_WORK. Rule: a DOI inside a link's URL belongs to that link's text, plus the text up to the next link. It does not belong to the whole line.

## 2. A decision for review documents (build)

Some notes are reviews that quote wrong citations on purpose: `Literature Gap Memo - Verification Review.md` (five defects) and `Novelty Check - Claude Spot Check - v1.md` (one). Their defects are the evidence, not errors. Today the gate would stop any edit to those files.

Add a sixth decision to the ledger and the page: **"Quoted on purpose"** (`quoted`). It dismisses that item, or clears that checker defect, for **this note only** and this citation text. It is never carried to other notes. It is only available through the review page and `apply`; there is no file marker, so an agent cannot exempt its own note. The page shows it on defect rows as well as review rows. That means the page needs a way to list defects. Add a `defects` section seeded the same way as `items`, and say in the report how Claude seeds it. Claude updates the published page after this lands.

## 3. Tests (recorded answers only)

One test per item in section 1, using the citation shapes quoted there. For section 2: `quoted` clears a checker defect for its note; the same citation in another note still raises; a changed citation text raises again; `apply` rejects `quoted` on an item from a different note.

## 4. Acceptance (report; do not tune)

Re-raise the same 24 files: rebuild the list from the latest version of each tracked `.md` under `ai-sandbox/research/` that contains a DOI, excluding `docs/superpowers/plans/` and the unversioned `Literature Gap Memo.md`. Do this against a copy of the main ledger, and report defects and open items per file. Expected: the nine checker defects from section 1 are gone. These real defects remain:
- Pritchett & Sandefur (2015) linked to the wrong DOI in two places (the Narrative note and the slides);
- Bold et al. (2018) and Crost, Felter & Johnston (2014) in Context Distance Cases;
- Bailey et al. (2020) in the Adversarial Scan;
- the Verification Review and Spot Check quotes, until a person marks them `quoted`.

Rows marked "title search unavailable" in that run were rate-limited. Retry them once and report what remains.

## 5. Out of scope

Editing any note (Claude and Aaron handle content); the gate's scope; v14 and v15 behaviour.
