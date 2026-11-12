You are the Gemini (Antigravity) session that wrote `Documentation Probe - Scored Candidates - v1.md` in your worktree `gemini-documentation-probe`. This is a short correction pass. Claude spot-checked the Kenya HSNP Phase 2 part against the primary documents and found it mostly reliable, with two citation problems and some rubric and status issues. Fix them honestly; do not defend v1.

If you are a fresh session rather than the original one, read the v1 file first. If you cannot find it, ask Aaron.

Rules
- Do NOT edit the v1 file. Write `Documentation Probe - Scored Candidates - v2.md` and `Documentation Probe - Correction Log - v1.md` in the same folder (`ai-sandbox/research/independent-research/notes/00_overview-and-strategy/` of your worktree).
- Do not edit any other existing file. Do not commit or push without reporting to Aaron first. Follow docs/WORKTREE_WORKFLOW.md.
- This repository is public. No copyrighted text or PDFs. Short quotations with citation are fine.
- Evidence standard from the first probe handoff still applies: open every document you cite, record the exact URL, tag what you actually read. Never fill a citation from memory.

What Claude checked (all against the downloaded Business Case and Project Completion Review text)
Matched: the 14-document DevTracker inventory; the seven-option comparison with Option 3 recommended (54% government share); targeting index values 1.21, 1.17, 1.15, 1.47 (Table 3); OPM/IDS 2011, Bold 2012, NAO 2011 and the IEG evaluation citations; completion review final value 119.85m GBP, start 23 Aug 2013, rating A+; Table 6 delivery-cost shares (DAI 6.5%, Equity Bank 9.6%, OPM 2.1%).

What did not match
1. You wrote that the Business Case cites Coady, Grosh and Hoddinott (2004). The text uses the label "CGH index" but its source line for Table 3 is "OPM (2010)", and Coady et al. does not appear in the Business Case. Open the Business Case, search it, and either quote where it cites them or remove the attribution. If you inferred it from the label, say so.
2. You wrote that the Business Case cites a 2011 DEC Horn of Africa evaluation. Claude found no such citation. Locate the exact passage (document, section or page) or mark it UNVERIFIED and remove it from the findings.

Rubric and interpretation problems to fix in v2
3. The seven Kenya options vary caseload, timing and government cost share inside one cash design. They are not alternatives that differ in kind (for example cash versus in-kind, or a different delivery system). Split the criterion "alternatives named and compared" into (a) options compared, and (b) options differ in kind (score 0 if they are scale, speed or financing variants of one intervention). Re-score all three candidates on the new criteria.
4. The v1 rubric hit its ceiling (14 of 14 for Kenya), which hides differences. Add finer anchors for at least these: does the closeout or completion review trace findings back to named design assumptions; does the documentation record the evidence base the design used (with citations you have opened); do the documents record why alternatives were rejected. Define each anchor in one sentence so a second reader would score it the same way.
5. Setting fit: state for each candidate whether it is conflict-affected, displacement-related, drought-only, and whether it involves a humanitarian-to-national-system transition. HSNP2 is a drought-prone, largely non-conflict setting; say what it can and cannot test for the agenda.

Status re-check for Somalia (Candidate A)
6. v1 says the World Bank project P171346 "remains active through December 31, 2025", and rates Somalia premature. Today is 2026-11-11, so that date has passed. Re-check on the World Bank project page: the current closing date (extended or closed), the current status, and whether an Implementation Completion and Results Report (ICR) or equivalent exists. Do the same for the other Somalia project IDs in v1. If a page will not load or shows only a title, say so and tag NOT OPENED; do not guess. Then restate the Somalia verdict with the date you checked.
7. Do the same status check for Ethiopia PSNP 4 (Candidate B): what closeout documents exist, with URLs you opened.

Also report
8. Recommend which candidate to use first for a retrospective desk audit and why, in at most five sentences, and whether a second case (for example Kenya for design trace and Ethiopia for closeout candor) is worth the extra work.

Output
- `Documentation Probe - Scored Candidates - v2.md`, starting with a "What changed from v1" list.
- `Documentation Probe - Correction Log - v1.md`: table of every change (claim, what was wrong, correction, page opened) and a short account of how the Coady and DEC items got into v1 (inferred from a label, recalled from memory, or something else; which tool calls produced them).
- An access report for the documents cited: full text, abstract only, landing page only, or not opened.

Report back to Aaron with: file list as clickable file:// paths (real absolute paths; do not repeat the drive prefix or leave out the backslash before `.worktrees`), counts by tag, the claims or scores that changed, the new Somalia status with the date checked, and the account of how the errors arose in your own words.
