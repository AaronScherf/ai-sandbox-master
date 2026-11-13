# Novelty check: reference fetch list and priorities (v1)

*Claude, 2026-11-11. Lists all 51 references in Gemini's `Novelty Check - RQ1/RQ2/RQ3 - v3.md` (worktree `gemini-nexus-novelty-check`) for full-text retrieval and reading. Gemini's v4 fix (Montiel Olea title; tag vocabulary) is in progress and does not change any identifier below.*

**Tags.** **[C]** checked by me against Crossref or DataCite (identifiers resolve to the cited paper, see `Novelty Check - Status and Pipeline Idea - v1.md`). **[I]** my judgement (priorities).

## How priorities were set [I]

- **P1 (check first, 16 items):** a headline claim in the novelty summary rests on the reference: the value-of-information prior art for RQ1 (IDinsight, Brown et al., Lopez et al.), humanitarian evidence use (Smith et al., Campbell and Knox Clarke, Hjort et al., Vivalt and Coville), cyclic causal models and participatory DAGs for RQ2 (Bongers et al., Tennant et al.), the pre-registered prediction and transport claims for RQ3 (Altmejd et al., DellaVigna, Pope and Vivalt, Montiel Olea et al., Crost et al., Gechter), and the evidence-gap-map and capture-recapture claim (Kastner et al., White et al.).
- **P2:** supporting or background. Still fetched, read later.
- Priorities are my reading of the notes, not a finding. Revisit after Gemini's v4 lists which claims rest on registry-matched references only.

## How they will be fetched

- 42 references have DOIs: they go into `docs/superpowers/plans/2026-11-11-novelty-check-fetch-dois.txt`, which the new DOI-list mode of the discovery pipeline will take (Codex handoff `2026-11-11-discovery-doi-list-mode-codex-handoff.md`). Open-access copies are fetched automatically; the rest land on the `needs_manual_downloads.md` checklist.
- 9 references have no DOI (reports, books, grey literature). They need a manual download or a page capture. One entry is not a document: Hummelbrunner (2010) points to the FASID home page (`https://www.fasid.or.jp/`), so its location must be found first. Two (Ben-Haim 2006 on ScienceDirect, Lempert et al. 2003 on RAND) are books or monographs and may be paywalled or only partly open.
- PDFs and converted Markdown stay under `ai-sandbox/research/journal-articles/`, which is git-ignored (PDF, Markdown and images). Nothing from the papers goes into this repo except short quotations with citation.

## The 51 references

| # | RQ | Reference | Identifier | Priority | Fetch route |
|---|---|---|---|---|---|
| 1 | RQ1 | Alonso-Coello et al. (2016) | `10.1136/bmj.i2016` | P2 | DOI list |
| 2 | RQ1 | Brown, Salisbury, & Ball (2025) | `10.1257/pandp.20251021` | P1 | DOI list |
| 3 | RQ1 | Butler & Broockman (2011) | `10.1111/j.1540-5907.2011.00515.x` | P2 | DOI list |
| 4 | RQ1 | Campbell & Knox Clarke (2019) | <https://www.alnap.org/help-library/beyond-assumptions-humanitarian-decision-making-in-practice> | P1 | manual (no DOI) |
| 5 | RQ1 | Claxton (1999) | `10.1016/s0167-6296(98)00039-3` | P2 | DOI list |
| 6 | RQ1 | Claxton & Sculpher (2006) | `10.2165/00019053-200624110-00003` | P2 | DOI list |
| 7 | RQ1 | Coburn & Penuel (2016) | `10.3102/0013189X16631750` | P2 | DOI list |
| 8 | RQ1 | Coughlan de Perez et al. (2015) | `10.5194/nhess-15-895-2015` | P2 | DOI list |
| 9 | RQ1 | Fenwick, Claxton, & Sculpher (2008) | `10.1177/0272989x07308751` | P2 | DOI list |
| 10 | RQ1 | Henrick et al. (2017) | <https://wtgrantfoundation.org/library/uploads/2017/10/RPP-Five-Dimensions-of-Effectiveness.pdf> | P2 | manual (no DOI) |
| 11 | RQ1 | Hjort et al. (2021) | `10.1257/aer.20190830` | P1 | DOI list |
| 12 | RQ1 | IDinsight / Allier-Gagneur et al. (2022) | <https://www.idinsight.org/blog/idinsights-new-value-of-information-work/> | P1 | manual (no DOI) |
| 13 | RQ1 | Lopez et al. (2020) | `10.1016/j.wace.2018.03.006` | P1 | DOI list |
| 14 | RQ1 | Smith, Swithern, & Harrison (2022) | <https://www.elrha.org/researchdatabase/from-knowing-to-doing-evidence-use-in-the-humanitarian-sector/> | P1 | manual (no DOI) |
| 15 | RQ1 | Vivalt & Coville (2023) | `10.1016/j.jdeveco.2023.103121` | P1 | DOI list |
| 16 | RQ2 | Andrews, Pritchett, & Woolcock (2013) | `10.1016/j.worlddev.2013.05.011` | P2 | DOI list |
| 17 | RQ2 | Bakewell & Garbutt (2005) | <https://www.intrac.org/wpcms/wp-content/uploads/2016/09/The-use-and-abuse-of-the-logical-framework-approach.pdf> | P2 | manual (no DOI) |
| 18 | RQ2 | Barbrook-Johnson & Penn (2022) | `10.1007/978-3-031-01919-7` | P2 | DOI list |
| 19 | RQ2 | Ben-Haim (2006) | <https://www.sciencedirect.com/book/9780123735522/info-gap-decision-theory> | P2 | manual (no DOI) |
| 20 | RQ2 | Bongers et al. (2021) | `10.1214/21-aos2064` | P1 | DOI list |
| 21 | RQ2 | Bowen et al. (2020) | `10.1596/978-1-4648-1575-1` | P2 | DOI list |
| 22 | RQ2 | Haasnoot et al. (2013) | `10.1016/j.gloenvcha.2012.12.006` | P2 | DOI list |
| 23 | RQ2 | Hausmann, Rodrik, & Velasco (2008) | `10.1093/acprof:oso/9780199534081.003.0015` | P2 | DOI list |
| 24 | RQ2 | Hummelbrunner (2010) | <https://www.fasid.or.jp/> | P2 | manual (no DOI) |
| 25 | RQ2 | Kok (2009) | `10.1016/j.gloenvcha.2008.08.003` | P2 | DOI list |
| 26 | RQ2 | Lempert, Popper, & Bankes (2003) | <https://www.rand.org/pubs/monograph_reports/MR1626.html> | P2 | manual (no DOI) |
| 27 | RQ2 | O’Brien et al. (2018) | <https://www.opml.co.uk/files/Publications/a0408-shock-responsive-social-protection-systems/srsp-synthesis-report.pdf> | P2 | manual (no DOI) |
| 28 | RQ2 | Tennant et al. (2021) | `10.1093/ije/dyaa213` | P1 | DOI list |
| 29 | RQ3 | Allcott (2015) | `10.1093/qje/qjv015` | P2 | DOI list |
| 30 | RQ3 | Altmejd et al. (2019) | `10.1371/journal.pone.0225826` | P1 | DOI list |
| 31 | RQ3 | Bareinboim & Pearl (2016) | `10.1073/pnas.1510507113` | P2 | DOI list |
| 32 | RQ3 | Brok et al. (2008) | `10.1093/ije/dyn188` | P2 | DOI list |
| 33 | RQ3 | Crost, Felter, & Johnston (2016) | `10.1016/j.jdeveco.2015.08.005` | P1 | DOI list |
| 34 | RQ3 | Dahabreh et al. (2020) | `10.1111/biom.13009` | P2 | DOI list |
| 35 | RQ3 | DellaVigna & Pope (2018) | `10.1086/699976` | P2 | DOI list |
| 36 | RQ3 | DellaVigna, Pope, & Vivalt (2019) | `10.1126/science.aaz1704` | P1 | DOI list |
| 37 | RQ3 | Doocy & Tappis (2017) | `10.4073/csr.2017.17` | P2 | DOI list |
| 38 | RQ3 | Egger et al. (2022) | `10.3982/ecta17945` | P2 | DOI list |
| 39 | RQ3 | Gechter (2024) | `10.1080/07350015.2023.2241529` | P1 | DOI list |
| 40 | RQ3 | Groh et al. (2016) | `10.1162/rest_a_00584` | P2 | DOI list |
| 41 | RQ3 | Hotz, Imbens, & Mortimer (2005) | `10.1016/j.jeconom.2004.04.009` | P2 | DOI list |
| 42 | RQ3 | Kastner et al. (2009) | `10.1016/j.jclinepi.2008.06.001` | P1 | DOI list |
| 43 | RQ3 | Meager (2019) | `10.1257/app.20170299` | P2 | DOI list |
| 44 | RQ3 | Montiel Olea et al. (2024) | `10.48550/arXiv.2408.09187` | P1 | DOI list |
| 45 | RQ3 | Pearl & Bareinboim (2014) | `10.1214/14-sts486` | P2 | DOI list |
| 46 | RQ3 | Pritchett & Sandefur (2015) | `10.1257/aer.p20151016` | P2 | DOI list |
| 47 | RQ3 | Rosenzweig & Udry (2020) | `10.1093/restud/rdz021` | P2 | DOI list |
| 48 | RQ3 | Saunders et al. (2018) | `10.1007/s11135-017-0574-8` | P2 | DOI list |
| 49 | RQ3 | Vivalt (2020) | `10.1093/jeea/jvaa019` | P2 | DOI list |
| 50 | RQ3 | Wetterslev et al. (2008) | `10.1016/j.jclinepi.2007.03.013` | P2 | DOI list |
| 51 | RQ3 | White, Saran, & Welch (2020) | `10.1002/cl2.1075` | P1 | DOI list |
