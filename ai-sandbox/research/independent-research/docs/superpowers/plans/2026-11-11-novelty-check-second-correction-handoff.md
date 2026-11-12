You are the Gemini (Antigravity) session that wrote `Novelty Check - RQ1 / RQ2 / RQ3 / Summary - v2.md` and `Novelty Check - Correction Log - v1.md` in your worktree `gemini-nexus-novelty-check`. Thank you for the v2 pass: about 30 references are now correct and the substantive fixes (Crost et al., the cyclic-models point, Altmejd et al.) look right. Claude then resolved every DOI in the v2 notes against Crossref. Ten references are still wrong, and your report said none were. This is a second, short correction pass on those ten only.

If you are a fresh session, read the v2 notes and the correction log first. If you cannot find them, ask Aaron.

Rules
- Do NOT edit v1 or v2 files. Write new files with the suffix `- v3` for any note that changes, and `Novelty Check - Correction Log - v2.md`.
- Do not edit any other existing file. Do not commit or push without reporting to Aaron first. Follow docs/WORKTREE_WORKFLOW.md.
- Public repository: no copyrighted text or PDFs; short quotations with citation are fine.

The ten references (Crossref's answer in brackets)
A. DOI resolves to a different paper
1. Butler and Broockman (2011), AJPS, cited as 10.1111/j.1540-5907.2011.00518.x [Gaines and Kuklinski, "Experimental Estimation of Heterogeneous Treatment Effects Related to Self-Selection"]
2. Vivalt and Coville (2023), JDE, 10.1016/j.jdeveco.2023.103074 [Augsburg, Malde and Olorenshaw, a sanitation paper]
3. Bongers et al. (2021), Annals of Statistics, 10.1214/20-AOS1970 [Efromovich, minimax distribution estimation]. This one supports your cyclic-models correction in RQ2, so it matters.
4. Allcott (2015), QJE, 10.1093/qje/qjv001 [Bertrand, Kamenica and Pan, "Gender Identity and Relative Income within Households"]
5. Brok et al. (2008), J Clin Epidemiol, 10.1016/j.jclinepi.2007.10.012 [Costa and Bergallo]
6. Egger et al. (2022), JDE, 10.1016/j.jdeveco.2022.102867 [Nyarko and Pellegrina, a commodity-exchange paper]. Check the venue too: the general equilibrium cash-transfer study from Kenya may not be in JDE.
7. Groh et al. (2016), World Bank Economic Review, 10.1093/wber/lhw023 [Iacovone, Pereira-Lopez and Schiffbauer, ICT use in Mexico]. Check the title and what the paper actually says about forecast accuracy.
B. DOI not found in Crossref
8. Hjort et al. (2021), AER, 10.1257/aer.20191834 [not found; a different DOI, 10.1257/aer.20190830, has been suggested elsewhere, confirm yourself]
9. DellaVigna, Pope and Vivalt (2020), "Predict science to improve science", Science, 10.1126/science.abb7442 [not found]
10. Pearl and Bareinboim (2014), "External validity: From do-calculus to transportability across populations", J Causal Inference, 10.1515/jci-2012-0022 [not found]

Also fix: in the RQ1 v2 note a "what changed" line quotes `10.1016/wace.2018.03.006`, which is a malformed string. The correct DOI is `10.1016/j.wace.2018.03.006`; quote the v1 error as an error, not as the correction.

What to do
1. For each of the ten, find the paper through the publisher page, the journal's own site or a registry search by title and author (not by the DOI you remember). Record the exact URL you opened. Copy title, authors, venue, volume, issue, pages and year as displayed.
2. Confirm the DOI by resolving it: `https://api.crossref.org/works/<url-encoded DOI>` (or DataCite for non-Crossref DOIs). The title and first author it returns must match your citation. If you have a shell, do this for every DOI you write, not only these ten. Use a generic client name in any user agent; send no personal information.
3. If you cannot find a reference at a publisher or registry, say so and mark it UNVERIFIED. An unverified reference left in the note is acceptable; an invented one is not. Do not fill any field from memory.
4. For each of the ten, re-read what your note says the paper found, against the abstract or text you opened, and correct the description if it differs. Say what changed.
5. If a correction changes a claim or verdict in the notes (for example the cyclic-models point if Bongers cannot be confirmed), say so plainly.
6. Correct the counts: report how many references are now VERIFIED (page opened and metadata matches), ABSTRACT-ONLY, and UNVERIFIED. Last time the reported 44 verified / 0 unverified did not hold up; be conservative.

Error report (short, in your own words)
- For these ten, what you did in v2: did you open a landing page, run a Crossref query, or copy the DOI from your earlier note? Which tool calls did you make for items 1 to 7?
- If you resolved DOIs against Crossref in v2 but these still slipped through, say why (for example the comparison was not done, or it was done on the wrong field).

Output
- `Novelty Check - Correction Log - v2.md`: a table of the ten (reference, what was wrong, correction, URL opened) and the error report.
- `- v3` copies of only those notes in which a reference or description changed, each starting with a "What changed from v2" list.

Report back to Aaron with: file list as clickable file:// paths (real absolute paths; do not repeat the drive prefix or leave out the backslash before `.worktrees`), counts by tag, and any claim whose verdict changed.
