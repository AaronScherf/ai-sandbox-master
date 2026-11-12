Addendum for the Claude session reviewing the Codex reference checker (`2026-11-11-reference-checker-codex-handoff.md`).

Why this exists
Gemini returned a correction pass (`Novelty Check - ... - v2.md` plus `Correction Log - v1.md` in worktree `gemini-nexus-novelty-check`). It was run before the fixed checker existed. Claude resolved all 43 distinct DOIs in the four v2 notes against Crossref (and the one arXiv DOI against DataCite). The pass fixed about 30 references but left new failures, while its own report claims "zero unverified, every DOI matches". This gives the checker a second, harder regression set: errors that survived one correction round.

Ground truth below was produced by Claude with a throwaway script (Crossref REST, generic user agent). Treat it as the expected answer, but re-check any row where the checker disagrees.

Expected MISMATCH (DOI resolves to a different paper than the citation text)
| Citation in v2 note | DOI | Crossref says |
|---|---|---|
| Butler and Broockman (2011), AJPS | 10.1111/j.1540-5907.2011.00518.x | Gaines and Kuklinski, "Experimental Estimation of Heterogeneous Treatment Effects Related to Self-Selection", AJPS 55(3) |
| Vivalt and Coville (2023), JDE | 10.1016/j.jdeveco.2023.103074 | Augsburg, Malde, Olorenshaw, sanitation paper, JDE 162 |
| Bongers et al. (2021), Annals of Statistics | 10.1214/20-AOS1970 | Efromovich, minimax distribution estimation, Annals of Statistics 49(1) |
| Allcott (2015), QJE | 10.1093/qje/qjv001 | Bertrand, Kamenica, Pan, "Gender Identity and Relative Income within Households", QJE 130(2) |
| Brok et al. (2008), J Clin Epidemiol | 10.1016/j.jclinepi.2007.10.012 | Costa and Bergallo, submission of scientific papers, J Clin Epidemiol 61(4) |
| Egger et al. (2022), JDE | 10.1016/j.jdeveco.2022.102867 | Nyarko and Pellegrina, commodity exchange search model, JDE 157 |
| Groh et al. (2016), World Bank Econ Rev | 10.1093/wber/lhw023 | Iacovone, Pereira-Lopez, Schiffbauer, ICT use in Mexico, WBER 30 |

Expected UNRESOLVED or not found in Crossref
- Hjort et al. (2021), AER, 10.1257/aer.20191834 (not found; the earlier handoff gives 10.1257/aer.20190830 as the correct DOI)
- DellaVigna, Pope and Vivalt (2020), Science, 10.1126/science.abb7442 (not found)
- Pearl and Bareinboim (2014), J Causal Inference, 10.1515/jci-2012-0022 (not found)
- Lopez et al. (2020), the string 10.1016/wace.2018.03.006 appears in a "what changed" line as a quoted v1 error. Correct DOI is 10.1016/j.wace.2018.03.006 (MATCH). The checker should not double-count the malformed string as a separate reference without noting context.

Expected to resolve via DataCite, not Crossref
- Montiel Olea, Prallon, Qiu, Stoye (2024), 10.48550/arXiv.2408.09187: DataCite returns "Externally Valid Selection of Experimental Sites via the k-Median Problem", MATCH. Crossref returns 404. This is the benign-404 case the checker must handle.

Expected MATCH (corrected references that now resolve correctly; use as positives)
Brown, Salisbury and Ball 10.1257/pandp.20251021; Claxton 1999 10.1016/s0167-6296(98)00039-3 (parenthesized, lower-case); Claxton and Sculpher 10.2165/00019053-200624110-00003; Fenwick et al. 10.1177/0272989x07308751 (issued 2007 online, 2008 in citation: expect PARTIAL on year, which is the intended one-year tolerance); Crost, Felter and Johnston 10.1016/j.jdeveco.2015.08.005; Gechter 10.1080/07350015.2023.2241529 (citation says 2024, Crossref says 2023: one-year tolerance); Meager 10.1257/app.20170299; Pritchett and Sandefur 10.1257/aer.p20151016; Rosenzweig and Udry 10.1093/restud/rdz021 (Crossref year 2019, citation says 2020); Vivalt 10.1093/jeea/jvaa019; Kastner et al. 10.1016/j.jclinepi.2008.06.001; Altmejd et al. 10.1371/journal.pone.0225826; Tennant et al. 10.1093/ije/dyaa213 (2020 online, cited 2021); Hausmann et al. chapter 10.1093/acprof:oso/9780199534081.003.0015; and the others in the v2 notes.

Other notes for the checker design
- Book DOIs (Barbrook-Johnson and Penn 10.1007/978-3-031-01919-7; Bowen et al. 10.1596/978-1-4648-1575-1) resolve in Crossref with empty container and volume: the comparison must not penalize missing venue fields on books.
- Some Crossref titles contain HTML entities (&amp;) and Windows-1252 characters; normalize before comparing.
- The v2 notes contain lines that list several DOIs in one bullet. The extractor should attach each DOI to its own nearby citation text, not to the whole line, or every one of them inherits the same context.

Self-report to compare against
Gemini's v2 report claims 44 VERIFIED, 7 ABSTRACT-ONLY, 0 UNVERIFIED. Per the table above, at least 7 of these cited DOIs resolve to the wrong paper, and 3 more do not resolve. The checker's summary should disagree with that report.

Constraints unchanged: do not edit the Gemini notes, the review files or pipeline code in this pass.
