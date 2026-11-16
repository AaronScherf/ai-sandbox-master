# Reference checker: identity tiers decision, v3 (title-less rows)

Date: 2026-11-16. Supersedes only the PLAUSIBLE rule of `... - v2.md` (tiers and linking pass otherwise unchanged). Design only.

## Decision (Aaron, 2026-11-16)

Reviewing a title-less row adds nothing a registry lookup does not already do: the reviewer opens the DOI and compares the title, which is what the checker does. So PLAUSIBLE is no longer always reviewed. A title-less row passes automatically, under a new tier **AUTHOR_YEAR**, when all of the following hold:

1. Identity is SAME_WORK and no title is available (in the citation or through the linking pass).
2. Every cited surname is in the registered author list. For an "et al." citation, the cited first surname must be the registered first author.
3. The cited year equals a registered year exactly (no one-year tolerance).
4. The DOI is registered with Crossref (the guard below is Crossref-only; DataCite rows stay PLAUSIBLE).
5. The **same-team guard** finds no other work by the same team near that year, and the query was complete.

Otherwise the row stays PLAUSIBLE and goes to review, now carrying the other works found, so the reviewer has something to compare.

AUTHOR_YEAR is reported separately from CONFIRMED, so reports still show the evidence was author and year only.

## Same-team guard

The one gap a registry cannot close from author and year alone is the same team publishing another paper that year. The guard asks Crossref for works by the registered authors within one year of the cited year and counts a work as a "sibling" only if:
- its first author's family name equals the registered first author's;
- it shares at least one co-author with the registered list (single-author works: first author only);
- it is not a dataset, peer review, component or grant record;
- its title scores below 0.5 against the registered title. A higher score is another version of the same project (working paper, preprint); the owner judged a mix-up between versions not costly.

Any lookup failure, rate limit, offline run without a cached answer, or result set that could not be read to the end keeps the row in review (fail closed).

Outbound data added: the registered authors' family names and a year range, sent to Crossref. Public bibliographic metadata only.

## Evidence (Claude's probe, fresh registry, 2026-11-16; not tool output)

Over the 16 PLAUSIBLE items in the review queue, a hand-written version of this guard gave:
- no siblings (would pass): Bongers et al. 2021; Maystadt and Ecker 2014; Zens and Thalheimer 2025; Marchiori, Maystadt and Schumacher 2012; Hjort et al. 2021; Pearl and Bareinboim 2014; Thalheimer, Schwarz and Pretis 2023; McGuirk and Burke 2020; Egger et al. 2022;
- no siblings on the first page but too many results to be sure (must be paged, else review): Butler and Broockman 2011; Harari and La Ferrara 2018;
- siblings found (stay in review): Allcott 2015 (single author, 19 other works 2014 to 2016); Vivalt and Coville 2023 (1); Groh et al. 2016 (3 same-team papers 2015 to 2016); Raleigh, Choi and Kniveton 2015 (1); Brok et al. 2008 (3, including another trial sequential analysis paper in 2008).

Surname-only matching was tried first and rejected: every common or prolific surname returned other works (Hjort 2021: 37, mostly different people), so nothing would have passed.

## Not changed

- Titled rows: CONFIRMED and REVIEW rules unchanged. The two REVIEW rows the owner looked at (Rosenzweig and Udry; Lopez et al.) have matching authors, year and journal but a different title in the note; they stay in review. Whether a titled row with a low title score should pass when authors, exact year and the guard all agree is open, not decided here.
- WRONG_WORK and NOT_FOUND still go to the defects list; a DOI pointing at someone else's paper never reaches AUTHOR_YEAR because the authors do not match.
- Checking the claim a citation supports remains the planned quote-anchored check; it is the only step where a reviewer adds information for title-less rows.
