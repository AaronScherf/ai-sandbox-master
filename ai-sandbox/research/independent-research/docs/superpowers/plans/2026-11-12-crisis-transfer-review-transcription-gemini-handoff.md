You are a Gemini (Antigravity) session. Task: transcribe a priority batch of PDFs from the `crisis_transfer_review` folder to Markdown with the existing journal-article pipeline, check the output, and report. Purpose: Claude and Aaron need to read these papers directly (Egger et al., Bedoya et al., the HSNP documents, and the nexus and evidence-use reports) without ingesting large PDFs. Follow docs/WORKTREE_WORKFLOW.md (your own worktree for any note you write; explicit-path staging; never `git add -A`). Do not commit or push without reporting to Aaron.

Where things are
- Folder: `C:\Users\theaa\ai-sandbox-master\ai-sandbox\research\journal-articles\crisis_transfer_review\` (main checkout, 30 top-level items). It also holds third-party replication data (`17945_Data_and_Programs\` with .dta/.do files, `KEN_2016_HSN-P2_v01_M_CSV\` and `..._ASCII_SPSS_SAS\` microdata), zip files, and two `.odt` files (`4857207.odt`, `50441178.odt`). **Do not transcribe, open in bulk, copy, move or commit any of those.** The folder is git-ignored (a `.gitignore` entry is being landed alongside this handoff; if `git status` in your worktree shows the folder as untracked, do not stage it).
- PDFs, converted Markdown and images under `research/journal-articles/` are git-ignored because they are third-party copyrighted papers. Do not copy paper text anywhere else in the repo, and never paste long passages into notes (short quotations with citation only).
- Pipeline: `ai-sandbox/academic-rag-model/pipelines/convert_journal_articles/` (read its README first, "Step 2: Run it"). Default driver is `agent`: it stages task cards, you fill them in Antigravity following the printed contract, then `--submit`. It does not use the paid API.

Important: path arguments
Run commands from `ai-sandbox/academic-rag-model`. Pass explicit absolute paths because the defaults resolve relative to the code, which is wrong in a worktree:
`--articles-dir C:\Users\theaa\ai-sandbox-master\ai-sandbox\research\journal-articles\crisis_transfer_review` and `--index-root C:\Users\theaa\ai-sandbox-master\ai-sandbox\research`.
Index cards written under `research/.index/` are tracked in git (derived summaries): report which files changed and do not commit them.
Check first that the pipeline does not recurse into the data folders (`17945_Data_and_Programs`, `KEN_2016_*`). If it would, use `--file` for each PDF instead.

Priority batch (convert in this order; stop after each tier and report if anything fails)
- **Tier 1 (convert first; the test case and the two cases Aaron is reading):**
  1. `ecta200500.pdf` (Egger et al., general-equilibrium effects of cash transfers in Kenya; the replication package is `17945_Data_and_Programs`). Confirm whether the PDF includes the online appendix; if not, say so.
  2. `w25981.pdf` (NBER 25981; Bedoya et al., Targeting the Ultra Poor in Afghanistan).
  3. `HSNP_business_case.pdf` and `HSNP_project_review.pdf` (FCDO Kenya Hunger Safety Net Programme Phase 2 Business Case and Completion Review). Aaron already holds ODT copies; the PDFs are wanted so page numbers can be cited.
- **Tier 2 (evidence use and the nexus):** `alnap-study-evidence.pdf`, `jpal_evidence_effect_conflict_crisis.pdf`, `jpal_humanitarian_impact_Evaluations.pdf`, `Understanding Factors to Evaluation Uptake.pdf`, `HER-Learning-Agenda-4.7.22.pdf`, `Evaluation-of-Humanitarian-Innovation-and-Evidence-Programme-Summative-Phase-Two-1.pdf`, `Comparing-Robust-Decision-Making-and-Dynamic-Adaptive-Po_2016_Environmental-.pdf`.
- **Tier 3 (nexus background; convert only after Tier 1 and 2 are checked):** `ALNAP-HDP-Nexus-final_XhU3D7a.pdf`, `Explain_HDPNexus_Briefing_052025.pdf`, `The_Triple_Nexus_-_Ferrero_Baselga_and_Mena_1.pdf`, `Breaking_boundaries_Local_national_actors_engagement_in_the_HDP_nexus.pdf`, `IASC Discussion Paper_AAP Localisation Nexus links and opportunities_28_June_2024.pdf`, `undp-operationalizing-hdp-nexus-ukraine_wb0ZeCR.pdf`.
- **Hold (ask Aaron):** `Nexus-Guidelines-Final-ENG.pdf` (about 10 MB, likely long), `Faraway--So-Close--...`, `Multi-level-participation-...`, `Responding-to-climate-services-...`, `Risk-without-place-...`. Report page counts and tier routing from the dry run, but do not convert them.

Steps
1. Identification (no conversion yet): for each PDF in the three tiers, open the first page's text and record title, authors, year and, if printed, DOI. Write the result as a table: filename, identified work, how matched, confidence. List any file you cannot identify for Aaron; do not convert it.
2. Dry run: `python -m pipelines.convert_journal_articles.convert_journal_articles --dry-run --articles-dir <as above> --index-root <as above>`. Report the tier each PDF would route to, page counts, and any flagged oversized (default `--max-pages` 150). Do not raise `--max-pages` without asking Aaron. If more than a few pages need paid transcription, stop and ask Aaron (project rule: ask before any run estimated over one dollar). Do not use `--driver api` or `--allow-api-fallback`.
3. Convert Tier 1, then check, then Tier 2, then Tier 3.
4. After `--submit`, check each output Markdown (beside each PDF in `processed_outputs/`, with page tags). For Tier 1 specifically: confirm title and authors on page 1, that the abstract is present, that the equations and tables in Egger et al. Section 3 (empirics) and the multiplier table are readable, that the Bedoya et al. results tables and the registration statement are readable, and that the HSNP documents keep their page numbers, option tables and the local-economy multiplier text. Record failures (garbled math, missing tables, wrong paper, dropped pages).
5. Run `python -m tools.reconcile_needs_manual` only if the README says it applies to this folder; otherwise skip it. Report what changed in the manifest and needs-manual list.

Do not
- Convert, rename, move or delete anything outside the lists above, or touch the replication data, zips or ODT files.
- Edit Claude's review files, the strategy, the deck, the data-source register, earlier Gemini notes, or pipeline code.
- Make claims about what a paper found. Your job is a faithful transcription and an inventory. Claude and Aaron do the reading.

Report back to Aaron with: the identification table; counts (identified, unidentified, converted, flagged oversized, failed or poor quality) per tier; the specific Tier 1 quality checks from step 4; which `.index/` files changed; and the absolute paths of the Markdown files for Tier 1 and Tier 2 as clickable file:// links (keep the backslash before `.worktrees` where it applies).
