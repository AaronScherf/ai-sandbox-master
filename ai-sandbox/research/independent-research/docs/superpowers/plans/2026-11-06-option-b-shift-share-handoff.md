# Option B (shift-share import price shock): planning handoff

Written 2026-11-06. **Plan only. Nothing is to be implemented.** Aaron wants to explore data and literature first to decide whether this direction is worth pursuing. Confirm scope with him at the start. Decision context: `notes/01_compound-shocks-panel/review-gate/Review Gate - Part C Decision Note.md`.

## The idea (from the Gap Memo, Gemini draft, citations unverified)

Interact World Bank Pink Sheet global food prices (the memo names wheat) with each Somalia district's baseline dependence on that commodity to study the 2022 global food price shock and its effect on displacement and conflict, without relying on the sparse local WFP price series. Parallel work on Option C is in a separate handoff; both read the same Somalia panel.

## What is known about the data

- The Somalia panel is 74 districts by 58 months (2021-01 to 2025-10), frozen at `compound-shocks-panel` v0.1.2. Outcomes available now: PRMN displacement, ACLED conflict. Add UCDP GED once a token exists.
- Local prices are sparse: 37 of 74 districts have a sorghum or wheat price at all. Imported wheat flour starts in 2017. Red sorghum and imported rice go back to 1995. Only about the last decade is needed.
- The panel has **no baseline dependence measure** per district. Finding or constructing one is the central open question.

## Questions to answer

1. **Exposure.** Which pre-period measure of district dependence on a global commodity exists for Somalia (livelihood zones, import routes, market food baskets, household survey consumption shares)? Is it exogenous enough? Is wheat the right commodity, or is imported rice or cooking oil a better fit given the WFP series?
2. **Identification.** What does the shift-share literature require here (exogenous shares or exogenous shocks, number of effective shocks, inference with few shocks)? Cite and verify the standard references and the McGuirk and Burke (2020) application the memo names.
3. **Data.** Which Pink Sheet series, units and months; which outcomes; any gaps. See `2026-11-06-new-data-sources-handoff.md`.
4. **Novelty.** Re-check the memo's no-duplicate claim with a fresh search; the memo's search log is the starting point.
5. **Feasibility.** With 74 districts and one global shock episode, is there enough variation, or does it reduce to a time series with few effective observations?

## Deliverable

One plan note (`notes/01_compound-shocks-panel/Option B Plan - Shift-Share Import Shock.md`) with: the question, exposure options ranked, identification argument, data needs, risks, and a green, yellow or red go/no-go test that can be run cheaply before any estimator is built.

## Ground rules

- Verify every citation against the source; mark unchecked ones unverified.
- Do not edit the panel repository, `project.yaml` or instance configs. Add only the plan note.
- Later implementation will live in `compound-shocks-panel` under `analysis/option_b_shift_share/`, extend the shared panel only through a versioned release, and keep new source code in its own files. That is for after Aaron approves the plan.
- Credentials never go in git. Follow the repo's worktree and landing procedure (`docs/WORKTREE_WORKFLOW.md`, `docs/WORKTREE_LANDING.md`).
