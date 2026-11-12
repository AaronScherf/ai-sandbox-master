# Spot check of Gemini's documentation probe (v2): correction to my own v1 check

*Claude, 2026-11-11. Supersedes parts of `Documentation Probe - Claude Spot Check - v1.md`, which is left unchanged. Checks Gemini's `Documentation Probe - Correction Log - v1.md` and `Scored Candidates - v2.md` (worktree `gemini-documentation-probe`) where they dispute my v1 findings.*

**Tags.** **[C]** checked by me against the primary document. **[I]** my judgement. **[G]** Gemini's claim, not checked by me.

## 1. My v1 error: Coady, Grosh and Hoddinott IS cited

- In v1 I wrote that the Business Case does not cite Coady, Grosh and Hoddinott (2004). **That was wrong.** My extraction script read body paragraphs and skipped the endnote bodies in `content.xml`, so the search missed the endnotes.
- Searching the raw XML of the Business Case, the text reads "...using the Coady-Grosh-Hoddinott index" followed by endnote 63: "Coady D., Grosh M., and Hodditnott J. (2004)..." (the endnote misspells the surname) [C].
- So Gemini's v1 attribution was correct. Its v1 failure was documentation: it gave no endnote number, and Table 3's own source line is "OPM (2010)" [C, from v1].
- Lesson for future checks: search the raw `content.xml`, not extracted paragraphs, when a document uses endnotes. I have not re-run my other v1 searches against the raw XML except as below.

## 2. DEC claim: confirmed unsupported

- Raw-XML search of the Business Case for "Disasters Emergency" returns no match; the Completion Review has none either [C].
- "Horn of Africa" appears only in a passage about the 2011 drought [C]. "Kenya Multi-Hazard Disaster Risk Assessment" appears in an endnote ("DFID (2012)...") as Gemini says [C]. I did not check which paragraph number it attaches to [G].
- Gemini's account: it recalled the DEC evaluation from background knowledge and did not string-search. That matches the pattern in the novelty check.

## 3. Remaining points on `Scored Candidates - v2`

1. **Scores now rank Ethiopia above Kenya [G, I].** Re-scored out of 16: Somalia 11, Ethiopia 14, Kenya 13. The recommendation still says start with Kenya. The reasoning (bounded documents, single standard) is fine, but the table and the recommendation point in different directions, and Aaron should see that.
2. **The table's "score shift" column is garbled** (it shows percentages of the old maximum). Do not quote it.
3. **The Ethiopia ICR and IEG review are claimed as read in full (62 and 22 pages) [G].** I did not open them. Treat Ethiopia's 14/16 as unchecked until I or a second reader do a spot check.
4. **Somalia: 0 disclosed ICRs and "Active" past the closing date [G].** Plausible and consistent with the ISR record, but it rests on an API call I did not repeat. The World Bank project page remains unreadable to a static fetch (JavaScript shell), so a person should look at it once.
5. **Counts [G].** 18 full text, 1 abstract, 8 landing page, 6 not opened (33 total); 18 + 1 + 8 + 6 = 33 is arithmetically fine.
6. **Setting fit [G, I].** The statement that HSNP2 cannot test conflict or displacement matches my own view.

## 4. Net effect

- The Kenya inventory and my other v1 confirmations stand. The Coady item moves from "not supported" to "supported, documentation incomplete". The DEC item stays unsupported.
- Kenya remains a reasonable first case. A reasonable alternative reading of Gemini's own scores is to start the desk audit with Ethiopia PSNP 4, which has a real closeout evaluation. That is an owner choice (see the chat summary).
- Before the choice is final: have a second reader open the Ethiopia ICR (ICR00006153) and IEG review (ICRR23858) and check whether the closeout traces to named design assumptions.
