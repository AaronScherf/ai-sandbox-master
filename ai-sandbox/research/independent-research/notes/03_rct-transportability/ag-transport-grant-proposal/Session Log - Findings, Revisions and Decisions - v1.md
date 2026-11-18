# Session log: findings, revisions and decisions - v1

*2026-11-18. Covers the whole grant-proposal working session, from the fertilizer-market check through the two-paragraph summary. Companion to [Project Summary and References v1](Project%20Summary%20and%20References%20-%20v1.md) and the [Final Review](Final%20Review%20-%20What%20the%20Pilot%20Showed%20and%20What%20to%20Propose%20-%20v1.md). Course project: nobody outside the course was contacted.*

## 1. What the project is
A hypothetical NSF-style proposal for an environmental science course ("research proposal in one natural science or at the intersection of several; context, question, hypotheses, methods"), which also tests the environmental foundations of the owner's RQ3 (context transfer). Design B: hold-out prediction on OFRA and HarvestStat Africa (Somalia as country holdout, plus a temporal holdout), then a funded trial network in Sudan and South Sudan with sites chosen by covariate-space coverage under a conflict-risk cap. Written as natural science, with economics only as constraints.

## 2. Major findings (preliminary; open data and proxy covariates; not independently reproduced)
- **Covariates barely transfer.** Skill of the OFRA similarity method over a pooled curve: +0.04 leave-site-out, -0.02 leave-country-out (maize, 271 sites). The Inference Tool's pseudo-R2 was only partly reproduced with proxy layers.
- **Why.** A fitted Gaussian-process lengthscale of about 0.16 (standardized units) is far shorter than the distance from Sudan's candidate cells to the nearest OFRA site (median 1.4 against 0.36 between OFRA sites, roughly four times).
- **Weather signal.** Rain and NDVI explain some yield anomaly within an administrative unit (R2 about 0.07-0.24) and almost none across countries (about 0.02-0.07).
- **Data coverage.** No OFRA records in Somalia, Sudan or South Sudan; South Sudan has no usable sorghum or maize yield series after 2012. Somalia is the only country with enough conflict-exposed and unexposed yield unit-years to serve as a holdout.
- **Price decides whether fertilizer pays.** Break-even gain at 50 kg N/ha is about 120 kg grain/ha at urea $11 a bag and about 540 at $50, against a mean OFRA sorghum gain of 476 kg/ha. The grain price of $0.40/kg is an unsourced assumption.
- **Farming base and access.** South Sudan: about 1.34 million farming households, no chemical fertilizer use by smallholders. Sudan: Sudan's fertilizer imports reportedly fell from about 450,000 t to about 50,000 t in 2024. The conflict cap works through site eligibility rather than information gain (cells eligible at weighted risk at most 2, 10, 40: Sudan 19%, 45%, 80%; South Sudan 23%, 44%, 74%).
- **Trial-size model.** At data-fitted covariance, 80 trials per country make 16-28% of cells "decidable" at 2025 prices and 6-9% at 2026 prices; under an imposed optimistic covariance, about 30 trials reach 42-47% at 2026 prices.
- **Targeting.** The gain from allocating scarce fertilizer by prediction depends on between-site response variation (in OFRA sorghum about as large as the mean response) and on how well predictions rank sites. This is an illustration, not run on data.
- **Funding landscape.** NASA Harvest is a commissioned consortium, not a competed call; A.36 (2022) was the last agriculture-specific ROSES element and is domestic-framed; A.13 (closed 15 Oct 2026) is US-framed; a ROSES-26 element is unconfirmed. J-PAL/CEGA's ATAI is not offering an RFP and is limited to affiliated researchers; IFPRI and CIMMYT look like partners and users rather than funders. IFPRI's June 2026 Malawi trial found soil-test recommendations alone did not change fertilizer use.

## 3. Decisions
- Predictability-first Design B; conservation angle dropped; RQ1-2 and the planner-in-the-loop kept out of this paper.
- No outreach to any ministry or organization; this is a course project.
- Staged funding gates (Aim 1, price, access, use) are kept in the full proposal but left out of the short summary as too complex for this stage.
- NASA is the target framing (Earth-observation covariates, decision-maker pathway); the realistic real-world route would be a partnership with Harvest Africa, with trials funded elsewhere.
- Targeting efficiency is the lead motivating idea, framed as the need of subsidy and distribution programs for evidence on where scarce fertilizer pays.
- Summary guidance from the owner: pitch voice rather than a record of work; name the data sources by what they are ("a review of the main open sources"); do not assume why coverage is thin; frame phase one as a preliminary review that validates the approach and phase two as the main grant-dependent proposal; drop the rho formula and the 85/450 kg/ha figures as too speculative; say "undersampled" rather than "not yet sampled"; foreground environmental covariates and proximity; state that trials cover sorghum, with maize where grown.

## 4. Revisions and files (branch claude/ag-transport-pilot)
- Proposal Draft v1-v5 (v4 withdrew the DISES funder mention; v5 restructured to the course format with NASA framing).
- Feasibility Addenda v1 (fertilizer access, trial size), v2 (costs, farming base), v3 (decision-makers), v4 (NASA Harvest, partner interest).
- Final Review v1; Reference Logs v1-v4; Proposal Idea Summaries v1-v2.
- Project Summary and References v1 (two candidates were drafted; the problem-first one, B, was chosen and revised four times).
- Pilot scripts 01-16 under projects/ag-transport-pilot; commits 6d66f8f9, c64adce5, 0830c163, 4bcbc082, 60d93102, fc81ad27, 7c92228f.

## 5. Corrections made along the way
- DISES was named as a funder in drafts v1-v3 but is archived; withdrawn in v4 and the Final Review.
- Earlier text overstated several figures (tractor-hire and fuel rises, table ranges, household and hectare totals); corrected after fact-checking against the sources.
- OFRA's CoefA is the plateau yield, not the control yield; earlier 1.9x and 1.7x ratios were plateau ratios (control ratios 1.43 and 1.26).
- CHIRPS numbers in early reports were wrong because of a single-season window bug; v3 onward is correct.
- Several PDFs (FAO CFSAM, Clingendael, FAO DIEM) could not be read and are marked "summary only" or "not read".

## 6. Open items
- Real per-site trial cost (the $20-60k placeholder is unsourced) and a sourced sorghum grain price.
- Reproduce the Inference Tool's validation with the authors' own rasters; crop-masked NDVI; a hierarchical model.
- Reference list gaps: CHIRPS and MODIS citations, news sources for the price claim, a verified reference for Sustain Sudan; a fresh Crossref pass.
- Whether to mention the Malawi finding as a limitation in the summary, and whether to name Sustain Sudan or FAO.
- Check headings against the full course assignment (only the quoted prompt was available) and the length limit.
- Landing the branch on main (needs `tools.active_work` and approval of a change ID); nothing is landed yet.
