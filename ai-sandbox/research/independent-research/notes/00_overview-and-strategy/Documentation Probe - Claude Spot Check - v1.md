# Spot check of Gemini's documentation probe (v1)

*Claude, 2026-11-11. Checks `Documentation Probe - Scored Candidates - v1.md` (in the worktree `gemini-documentation-probe`) against the primary documents for the leading candidate, Kenya HSNP Phase 2. I did not edit Gemini's file. This is a spot check of one candidate, not an audit of all three.*

**Tags.** **[C]** checked by me against the primary document. **[I]** my judgement.

## 1. Method

- Fetched the DevTracker documents page for programme `GB-1-204258` and compared it with Gemini's document inventory [C].
- Downloaded the Business Case (`4857207.odt`) and the Project Completion Review (`50441178.odt`) from the FCDO IATI store into an empty scratch folder and extracted the text from the files' `content.xml` with a Python script (run with `-I`). I then searched the text for Gemini's specific claims [C].
- Not checked: Candidates A (Somalia) and B (Ethiopia), the annual reviews, the logical framework, the tender documents, and any claim about FCDO or NDMA status today.

## 2. Result: this probe is much more reliable than the novelty check

| Gemini's claim | Finding |
|---|---|
| Document inventory (Business Case, addendum, logframe, five annual reviews, completion review, tenders) with IDs and dates | **Matches** the DevTracker page: 14 documents, same IDs and dates [C] |
| Business Case compares seven options and recommends Option 3 | **Supported.** The text defines Options 1 to 4 in full and lists Options 1, 2, 3, 4, 5a, 5b and 6 in the comparison table; "the recommended option is Option 3," with a 54% government share of caseload [C] |
| Hybrid community-based plus proxy-means targeting, with index values 1.21, 1.17, 1.15 and 1.47 | **Supported.** Table 3 gives exactly these values; the text describes testing a combined community-based and proxy-means approach [C] |
| Business Case cites OPM and IDS (2011) targeting evaluation | **Supported** [C] |
| Business Case cites Coady, Grosh and Hoddinott (2004) to compute those indices | **Not supported.** The text uses the label "CGH index" but its source line for Table 3 is "OPM (2010)." Searches for Coady, Grosh and Hoddinott return nothing in the Business Case [C]. This looks like a plausible inference presented as a citation. |
| Business Case cites Bold (2012) / CGAP on payments; NAO (2011); IEG review of World Bank safety nets | **Supported** (Bold 2012, NAO 2011 and the IEG evaluation all appear) [C] |
| Business Case cites a 2011 DEC Horn of Africa evaluation | **Not found.** The text discusses the 2011 drought and appeal, but I found no DEC evaluation citation [C]. Treat as unverified. |
| Completion review: final programme value £119.85m; started 23 Aug 2013; overall rating A+ | **Supported** [C] |
| Delivery-cost shares over the whole programme: DAI 6.5%, Equity Bank 9.6%, Oxford Policy Management 2.1% | **Supported.** Table 6 gives exactly these "entire period" figures [C] |

Overall: the factual spine of the Kenya assessment holds, with one wrong attribution (Coady et al.) and one unverified citation (DEC). By contrast, many identifiers in the novelty notes were wrong.

## 3. Issues that affect how to use the result

1. **The seven options differ in scale, speed and financing, not in kind [C, I].** The options are variations on caseload (69,000 to 130,000 households), timing (early or late) and government cost share, within one cash-transfer design. The RQ2 question is which interventions would be considered under which conditions. A rubric that scores "alternatives named and compared" gives full marks here, but the alternatives are scaling variants, not different intervention types such as cash versus in-kind. The 14/14 total therefore overstates fit for that part of the audit. The rubric should separate "options compared" from "options differ in kind."
2. **Setting differs from the nexus focus [I].** HSNP2 is a drought-prone, largely non-conflict setting (2013 to 2019), with a built-in scalable drought response. It is a good test of a design-to-closeout trace and of a cash safety-net decision, but it does not exercise displacement, conflict or the humanitarian-to-national-system transition that Somalia does.
3. **The Somalia "premature" verdict may be stale [I].** Gemini says project P171346 "remains active through December 31, 2025." Today is 2026-11-11, so that date is almost a year old. An extension, or a completion report that is now due or recently issued, would change the verdict. Re-check the closing date and whether a completion report exists before ruling Somalia out. I did not do this.
4. **The rubric has low discrimination at the top [I].** One candidate hit the maximum. A ceiling score hides differences that matter (for example, whether closeout findings are traced to design assumptions, or whether options differ in kind). A second probe version should use finer anchors.
5. **Single-case risk [I].** One retrospective audit of one programme is a thin base. Using Kenya for the design trace and Ethiopia for the closeout candor (as Gemini's own notes suggest) would test whether the method generalizes.

## 4. Recommendation

- Proceed with **Kenya HSNP2 as the first desk-audit case**, with the caveats above, because the document trail is verifiably complete.
- **Do not cite Coady et al. (2004) as a Business Case citation** in any downstream document. The index is named for them, but the source line says OPM (2010).
- Ask Gemini to correct the Coady attribution and the DEC item, tighten the rubric as in item 1, and re-check the Somalia closing date. Use a versioned `- v2`.
- Whether to commit the probe report to Gemini's branch is your call. If you commit it, commit the v1 file as it stands and add the corrections as v2, rather than editing it.
