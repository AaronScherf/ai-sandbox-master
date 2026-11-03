# Literature taxonomy, Phase 1 quality gate: status

Date: 2026-11-02. Branch `claude/literature-phase1-status`. Roadmap:
`docs/superpowers/specs/literature_taxonomy/2026-10-31-literature-discovery-roadmap.md` (Phase 1).

Question: is the taxonomy as it stands good enough to expand into a discovery pipeline? Expansion runs new papers through the
same extraction, so weaknesses here would be multiplied there.

**Verdict: meets the bar on the measured criteria, with three known gaps and one unmeasured quantity (recall).** The bar was
set by the owner on 2026-11-02 (see each criterion). Nothing below should be read as a pass on recall.

All figures are on the real database of 2026-11-02. Aggregates only: no quotes or paper text appear in this document.

## Criterion 1: precision of the facts analyses use (tier A and B)

Bar: at least 0.80 facet precision on tier A and B facts.

Method (replaces hand-checking 18 papers, which would have taken hours and mostly measured recall): a stratified sample of
90 facts (30 each from tiers A, B and C, spread across facets, fixed seed, papers already in the gold set excluded). Each
fact was judged blind to its tier on one question: does its supporting quote support the label as a fact about the paper?
Claude screened all 90; the owner audited 31 of them (every A/B fact screened as unsure or unsupported, 15 random supported
ones, 5 supported tier C ones), with a short rationale on each disagreement. Owner verdicts replace the screen where they differ.

| Tier | Sample | Supported | Precision | 95% interval (Wilson) |
|---|---|---|---|---|
| A | 30 | 27 | 0.90 | 0.74 to 0.97 |
| B | 30 | 25 | 0.83 | 0.66 to 0.93 |
| **A+B** | **60** | **52** | **0.87** | **0.76 to 0.93** |
| C | 30 | 12 | 0.40 | 0.25 to 0.58 |

Reading it:
- The point estimate clears 0.80, but with 60 facts the 95% interval reaches 0.76. This is "meets the bar", not "clears it
  comfortably". A larger sample would narrow it; 150 A/B facts would give about ±5 points.
- Tier C is clearly worse, which supports the rule that analyses start from A and B and treat C as excluded.
- The owner's three disagreements on A/B facts all went the same way (screen too strict on short quotes), so the screen
  under-credits, not over-credits. Of the 15 random supported facts the owner audited, none was overturned.
- Failures in A/B were of one kind: the label names something the paper discusses, not something the paper did. Examples:
  a data-source label from a game description, a country from a nine-country list that omits it. See "Recommendations".
- The older gold-set `eval` (12 papers: facet precision 0.66, recall 0.60) is not comparable: it scores matches against a short
  expected list, not whether a quote supports a fact. Keep it as a regression check only; I have not investigated why its
  precision is lower than the audit's.

## Criterion 2: open vocabulary proposals

The roadmap's "11 open proposals" is stale. `_proposals.json` holds 141 proposals; 71 are open, and **all 71 belong to the 15
excluded (off-topic) papers**. On eligible papers there are 0 open proposals (`status` agrees). No decision is pending, and the
stage 2b review Artifact is not needed for the current corpus. If excluded papers are re-admitted, build it then.
**Met.**

## Criterion 3: tier C backlog and papers without a record

Tier C (83 facts: outcome 43, intervention 21, data sources 7, population 7, study design 5): `verify` found nothing to verify
because every eligible paper already has a verification pass; the checker marked these facts not supported or unclear. They stay
at C by design and out of analyses. The audit (40% supported) shows the rule is right. **Accepted as designed.**

Papers without a record (8 on `status`) are two different things:
- **5 duplicate-title copies** of recorded papers (same title, year and DOI where present). `collect` already drops them, so they
  are never extracted. The owner decided not to `exclude` them (exclusion means off-topic). `status` overstates the gap by
  counting them; fix in progress on `codex/literature-status-honest` (a new `duplicate titles (not extracted)` line).
- **3 papers over the 240,000-character card limit** (`3268b7062f1745f2`, `ffee575e1b75d109`, `7f88458c5df631df`; 268k, 279k
  and 267k characters, 12 to 16% over). Chunked extraction is not built. **Known gap.** Priority: `ffee575e1b75d109`, a systematic
  review of large-scale cash transfers in low- and lower-middle-income countries (poverty and climate resilience outcomes),
  which is directly on topic for the cash-transfer gap questions. **Resolved:** the limit was raised to 300,000 and all three
  now have records; see "Resolved: card limit" below.

## Criterion 4: adjudication for real disagreements

Deferred. The whole-paper double-pass agreement of 0.078 (5 of 64 papers) is a strict measure: a paper counts only if the two
passes differ on nothing. At the fact level, 367 of 602 eligible-paper facts (61%) are tier A, found by both passes. The weak
spot is outcome and intervention (64 of the 83 tier C facts). Revisit once recall is measured and a decision on grain is needed.

## Unmeasured: recall

Recall of facts that both passes missed is unmeasured. Measuring it needs a person to read whole papers. The owner chose to
skip it for now. Consequence: a gap verdict of `no_evidence_in_corpus` can mean a missed fact as well as an absent study. Reports
already say corpus-only; this is one more reason not to read a zero as proof. Revisit before the discovery loop scales
up, on 4 or 5 papers chosen for outcome and intervention richness.

## Recommendations (not done)

1. **Review papers and data sources.** For a review or a competition, extraction lists data sources for what the paper
   discusses, not what it used (the owner's tier C rationales; two tier A/B cases too). Options: no data-source facts on
   reviews, or a separate label for secondary sources. A contract or vocabulary change, so it needs a design pass.
2. **Mention-only countries.** A country named in a list of examples is extracted as a country of the study. Worth a check in
   the extraction contract before expansion.
3. **Card limit.** Done (300,000); see below.
4. **Larger precision sample** before declaring the 0.80 bar firmly met (about 150 A/B facts).

## Resolved: card limit raised from 240,000 to 300,000 characters

`stage.py` had `MAX_CARD_CHARS = 240_000` ("about 60k tokens"), with no recorded reason beyond that comment. The three papers
exceeded it by 12 to 16%. Trial (2026-11-02, Gemini, `--double`, subscription): raised to 300,000 and extracted all three.
**Adopted.** The constant is also used by `verify`, `contribute` and `refine_grain`.

| | Trial (3 papers) | Baseline (64 papers) |
|---|---|---|
| Facts per paper | 13, 21, 16 (mean 16.7) | mean 9.4, median 8.5 |
| Tier A / B / C | 88% / 8% / 4% | 61% / 25% / 14% |
| Quote-location failures | 0 | not tracked |
| First-attempt bounces | 2 (one paper, bad vocabulary ids; fixed on retry) | n/a |

- No loss at the end of long documents: each paper has facts cited from its conclusion pages; later pages are references and appendices.
- Independence: the share of pass b's quotes also used by pass a was 0.0 for all three (baseline median 0.33), so the passes did not copy each other.
- Caveats: only three papers; the higher tier A share probably reflects long reports stating facts plainly and repeatedly, not a general quality gain. Both passes were filled by one agent.
- Paper `ffee575e1b75d109` (the priority gap) has two tier C facts of the known review-paper kind (a study design and a data source the review discusses, not used). This strengthens recommendation 1.
- To look at when next reading `7f88458c5df631df`: its record lists a randomized controlled trial while tier B includes a natural experiment.
- Records now: 82 with a record; tiers A 411, B 156, C 85.

## Resolved: review-paper rule (`extract-v4`, 2026-11-03)

Recommendations 1 and 2 are addressed by one rule, landed as `6db5f9e3`: a country must be the paper's own sample or setting,
a review or overview paper lists only data it analysed, and the checker applies the same country test. The prompt version is
now `extract-v4`.

Existing records were **not** re-extracted; they keep `extract-v2/v3` provenance (tiers A 411, B 156, C 85). Eight papers still
hold wrong facts (`2f30f1372f72c7db`, `32d269e4d88f17cb` with 10 wrong countries, `6dc85fe4875ce8ef`, `98049fc423ba0aab`,
`c51f7e59bb550dee`, `d688c2e9cec6e735`, `ffee575e1b75d109`, `2c52c3e38095bd14`).

Trial 2 (valid re-extraction of 10 papers, results restored afterwards; 20 passes):

| Measure | Result |
|---|---|
| Wrong countries removed | 14 of 14 |
| Correct countries lost | 0 |
| Wrong data sources removed | 4 of 5 |
| Correct data sources lost | 1 (`ffee575e1b75d109`, programme documents) |
| Wrong fact surviving | 1 (`c51f7e59bb550dee`, a portal for one country, now tier A) |
| Outcome facts | 37 down to 27 (probably variance; unconfirmed) |

This was the second trial; the first was not a valid re-extraction. Re-extraction runs must be checked for byte-identity against
the backed-up records. Next: re-extract the eight papers, watch the outcome-fact counts, and fix the portal fact by hand.

## Next

- Re-extract the eight papers with `extract-v4` (above), then run the larger precision sample on the corrected data.
- Gap coverage `without_record` (`gap/coverage.py`) still counts excluded papers and duplicate-title copies; make it agree with `status`.
- Phase 2: design the discovery loop (brainstorm, then spec). Chunked extraction goes on that list if the limit trial fails.
