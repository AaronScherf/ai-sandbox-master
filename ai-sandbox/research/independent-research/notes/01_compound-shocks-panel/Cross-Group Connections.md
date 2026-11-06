# Cross-Group Connections: Compound Shocks Panel

*Group B (Project 02, with the Project 04 toolkit work). Files: Somalia Three-Shock, Data Sources, Sudan Data Sources, ACLED Terms, Pilot Scope Realignment, Data Audit Review, Gemini Brief, Pipeline Review. Written 2026-11-05. "(inference)" marks my own reading.*

This group is the most self-contained. What follows is what other groups' files say about it, and what it provides to them.

## Current state in one paragraph
Phase A is done: balanced district-month panels for Somalia (74 districts) and Sudan (189 localities), 2021-01 to 2025-10, reproduced byte for byte from fresh clones. The review gate is open: Part A (data audit) is written, Part B (the Literature Gap Memo) is written (Gemini, commit `d6915e4f` on branch `gemini/compound-shocks-lit-memo`, not yet on `main`, and awaiting your and Claude's review), and Part C is the owner's decision. The Pipeline Review that used to be listed here now lives with the reprokit group (`../05_reprokit-reproducibility-framework/`). Modeling is on hold until then.

## From the overview group (A)
- The 3R plan states Project 02's question as separating the Ukraine price shock, drought and al-Shabaab on displacement and prices, then testing whether cash transfers moderate it. Of those pieces, the audit says the panel can support only conflict and rainfall for now.
- Cash-transfer presence (WFP/OCHA Cash Working Group data) is a core variable in the original and 3R plans and the fusion equation in Data Sources (`β5 Climate × Cash`). Neither panel contains it. The Gemini Brief's question 4 (additional data) is the natural place to scope it.
- Phase B resumes Plan 2 Tasks 11, 12 and 15 (price decomposition, LaTeX report, nested F-tests), preserved in the Pilot Scope Realignment with commit SHAs.

## From the literature group (C)
- The Gemini Brief is the first real use of the literature pipeline for a project decision. Its search commands (`db cooccur`, `db dist data_sources`) are exactly the queries the Pitch's taxonomy schema was designed to answer: papers combining ACLED, CHIRPS and WFP or DTM.
- The brief asks Gemini to report corpus coverage honestly (how many papers, which confidence tier). The Pitch's accuracy-validation step (check extraction against known papers such as Warsame et al.) is the same concern at design time.

## From the RCT group (D)
- **ACLED and displacement as a forecast target.** The brainstorm's "separate note" proposes treating future displacement or conflict events as an autoregressive outcome, linked to Bai-Ng supervised factor models. This is a different use of the panel than the descriptive/identification work now gated. The core columns (`events`, `fatalities`, `precip_mm`) are the only ones dense enough in both countries, which is the minimum a forecast would need (inference).
- **Satellite proxies as substitutes for missing survey data.** Sudan Data Sources recommends MODIS NDVI and VIIRS night lights where WFP prices and DTM are thin. The brainstorm's proxy framework says why that is not free: a proxy measures the local aggregate, includes spillovers, and attenuates effect sizes. Anyone using night lights to fill Sudan's price gap inherits those caveats.
- **Selection in the price series.** The audit's finding that missing prices are programme-driven in Somalia and conflict-linked in Sudan is a measurement-error problem of the same family as the proxy issue above.

## From the exploratory methods group (E)
- `Research Ideas.docx` proposes agent-based models of climate and conflict shocks (mitigation vs adaptation, preparedness vs response, cost vs lives saved). The panel is descriptive data; an agent-based model would need calibration targets from it (inference). No document connects the two yet.

## What this group provides to others
- **To the toolkit (Project 04):** the Somalia note's verification layer (claim-lineage tracing, LLM coding checked against hand coding) is flagged there as reusable, and is not yet built. The Pipeline Review's ten `reprokit` v0.3 recommendations are the concrete backlog.
- **To the literature group (C):** the Gemini Brief's question 4 and "Closest existing papers" table will be the first filled-in example of a gap memo.
- **To the strategy group (A):** the data audit is the first empirical evidence on whether the flagship question is answerable with public data.

## Items to reconcile
- Somalia Three-Shock's timeline (Late Sep to Dec) and Data Sources' next steps ("run the preliminary regression", "3-shock price decomposition") predate the gate.
- Pilot Scope Realignment gives the Somalia window as 2021-01 to 2023-08. The audit and the briefs use 2021-01 to 2025-10.
- Sudan Data Sources' Option B (host-locality arrival model) and the audit's "no pre-war baseline" finding both depend on the DTM stock series, which starts 2023-08.
- ACLED Terms: the research tier's rolling 12-month lag matches the 2025-10 end of the panel. Any extension to newer months needs a different access tier.
