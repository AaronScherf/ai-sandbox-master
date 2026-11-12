You are the Gemini (Antigravity) session that wrote the four files `Novelty Check - Summary / RQ1 Knowledge Audit / RQ2 Decision Space / RQ3 Transfer - v1.md` in your worktree `gemini-nexus-novelty-check`. This is a correction pass. Claude spot-checked your work and found it unreliable in specific, checkable ways. Your job is to fix it honestly, not to defend it.

If you are a fresh session rather than the original one, read the four v1 files in the `gemini-nexus-novelty-check` worktree first. If you cannot find them, ask Aaron.

Rules
- Do NOT overwrite or edit the v1 files. Write new files with the suffix `- v2` (listed under Output).
- Do not edit any other existing file. Do not commit or push without reporting to Aaron first. Follow docs/WORKTREE_WORKFLOW.md and keep working in your own worktree.
- This repository is public. No copyrighted text or PDFs. Short quotations with citation are fine.

What Claude found (all checkable; details below)
1. Your v1 tagged every reference [VERIFIED]. Claude resolved all 38 `doi.org` links in the four notes against Crossref. Only 13 resolved to the paper you cited. 13 resolved to a **different paper**, and 12 did not resolve (a few for benign reasons: arXiv and some non-Crossref registries, and one DOI cut short by parentheses).
2. Two citations also had wrong substance.
3. The summary's lead claims ("total absence", "never", "none") are stronger than the evidence, and one contradicts your own RQ1 note.
4. Your notes never state which sources you actually opened, which the first handoff required.

The 13 DOIs that resolve to a different paper (Crossref's answer in brackets)
- Brown, Salisbury & Ball 2025 `10.1257/pandp.20251068` [a gender asset gap paper; a search result suggests the correct DOI is `10.1257/pandp.20251021`, confirm it yourself]
- Claxton & Sculpher 2006 [a Weinstein paper on decision-analytic modelling]
- Fenwick, Claxton & Sculpher 2008 [a prostate-cancer screening paper]
- Lopez et al. 2020 [a labor-market paper]
- Kok 2009 [an air-quality paper]
- Dahabreh et al. 2020 [an editorial list]
- DellaVigna & Pope 2018 [a Philosophy of Science paper]
- Hotz, Imbens & Mortimer 2005 [a trends paper by Vogelsang and Franses]
- Kastner et al. 2009 [a journal-selection paper]
- Meager 2019 [correct DOI for the microcredit paper, but your title "Six Randomised Trials of Social Programs" is wrong; the paper is "Understanding the Average Impact of Microcredit Expansions: A Bayesian Hierarchical Analysis of Seven Randomized Experiments"]
- Pritchett & Sandefur 2015 [a paper on high pay and coercion]
- Rosenzweig & Udry 2020 [a commitment-in-organizations paper]
- Vivalt 2020 [a Danish job-displacement paper]

The 12 DOIs Crossref could not find
Claxton 1999 (truncation artifact: this DOI contains parentheses), Coughlan de Perez et al. 2015, Andrews, Pritchett & Woolcock 2013, Barbrook-Johnson & Penn 2021, Ben-Haim 2006, Bowen et al. 2020, Hausmann, Rodrik & Velasco 2008, Hummelbrunner 2010, Montiel Olea et al. 2023 (arXiv), Saran & White 2018, Crost et al. 2016, Gechter 2023.

Two substantive errors
- Crost et al.: you cited "Crost, Felter & Mansour (2016), American Economic Review 106(1), 171-210" and said the program **increased** insurgent violence. Claude's check found the paper is by Crost, Felter and **Johnston**, in the **Journal of Development Economics** 118 (2016) pp. 171-182, DOI 10.1016/j.jdeveco.2015.08.005, and that it reports a **decrease** in insurgent influence and conflict incidents in treated villages. Open the paper's abstract and confirm. You may have mixed it up with the same authors' 2014 "Aid under Fire" paper on development projects.
- Gechter: you cited JBES 41(3), 839-851, 2023. A search shows JBES 42(2), 801-811, 2024, DOI 10.1080/07350015.2023.2241529. Confirm.

Also: one of your search queries used the title "Understanding the Average and Heterogeneity of Treatment Effects" for the Meager paper. That is not its title. Say whether you searched for papers by remembered title.

What to do
1. For EVERY reference in all four notes, including those without a DOI:
   a. Open the publisher or DOI landing page, or the working-paper page. Record the exact URL you opened.
   b. Copy the title, first author and venue exactly as the page displays them.
   c. Fill in volume, issue, pages and year from that page, not from memory.
   d. If you have a shell, you may also resolve the DOI at `https://api.crossref.org/works/<url-encoded DOI>` (or DataCite for arXiv and some institutional DOIs) and compare. Use a generic client name in any user agent; do not send any personal information.
   e. Tag as VERIFIED only if you opened the page and the displayed metadata matches the citation. Tag ABSTRACT-ONLY if you read only the abstract. Tag UNVERIFIED if you could not open it. Never fill a citation from memory and tag it verified. Never silently drop a reference you cannot verify; list it as UNVERIFIED.
2. For every claim you attribute to a source, check it against the abstract or text you opened. Correct any mismatch, and say what you changed. Start with Crost and with the Brown, Salisbury and Ball description (GiveWell's value-of-information model).
3. Rewrite the summary's "surprises" so each claim matches the evidence:
   - Surprise 1 ("total absence" of value of information in aid): your own RQ1 note cites GiveWell's value-of-information model and IDinsight's decision-focused evaluations. Claude's check also found IDinsight published simulation-based value-of-information work on whether to commission an evaluation before a scale-up decision (search: "IDinsight improving decisions about evidence value of information"). Read that work and state exactly what it does and does not cover. State the narrower claim that is actually supported, for example about humanitarian or transition programme design.
   - Surprise 2 (participatory mapping versus acyclic graphs): "mathematically impossible" is too strong. Check whether cyclic structural causal models and time-indexed graphs are standard, and whether any participatory-DAG elicitation work exists. Search more before claiming "virtually no literature".
   - Surprise 3 (no pre-registered transport prediction): Claude's search found related work (a registered model prediction of replication results in the Social Science Replication Project, CEGA's pre-registered forecasts of RCT effects, an external-validity function used to choose experiment sites). Check these, then state what you found and found not, with your search log. Use "I found no example", never "never" or "no one".
   - The claim that no evidence gap map has stopping rules or capture-recapture metrics: your RQ3 note also says capture-recapture has been applied to literature searches. Reconcile them and show the search that supports the narrower claim.
4. Add an "Access report" to each note: for each reference, one word for what you could open (full text, abstract only, landing page only, not opened). Be plain about it.
5. Write a short "Error report" explaining how the wrong DOIs got there: did you copy identifiers from search results, reconstruct them from memory, or something else? Which tool calls did you make for a given reference? This matters because Aaron is deciding whether to trust Gemini for literature work in the taxonomy pipeline.

Standard of evidence
- Every cited source must have been opened. A search snippet, a Scholar listing or another AI summary does not count as opening it.
- State what you could not open. "Not opened" is an acceptable answer.
- Keep verdict language proportional: absence in an indexed search is not absence in the world.
- If correcting a claim changes a verdict, say so plainly. "Partly answered" may become "better answered than I said" for RQ1.

Output (new files, versioned; do not overwrite v1)
In ai-sandbox/research/independent-research/notes/00_overview-and-strategy/ of your worktree:
- Novelty Check - RQ1 Knowledge Audit - v2.md
- Novelty Check - RQ2 Decision Space - v2.md
- Novelty Check - RQ3 Transfer - v2.md
- Novelty Check - Summary - v2.md
- Novelty Check - Correction Log - v1.md: a table of every change (reference, what was wrong, correction, evidence page opened) plus the error report from step 5.
Each v2 note starts with a "What changed from v1" list.

Report back to Aaron with: file list as clickable file:// paths (use the real absolute paths; do not repeat the drive prefix or leave out the backslash before `.worktrees`), counts of references by tag (VERIFIED, ABSTRACT-ONLY, UNVERIFIED), the claims whose verdict changed, and the error report in your own words.
