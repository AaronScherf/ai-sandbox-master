# Option C (Baxnaano cash transfers and climate displacement): planning handoff

Written 2026-11-06. **Plan only. Nothing is to be implemented.** Aaron wants to explore data and literature first to decide whether this direction is worth pursuing. Confirm scope with him at the start. Decision context: `notes/01_compound-shocks-panel/review-gate/Review Gate - Part C Decision Note.md`.

## The idea (from the Gap Memo, Gemini draft, citations unverified)

Add Somalia district-level Baxnaano cash-transfer data to the Somalia panel and test whether social assistance reduced climate displacement under conflict. This is the option closest to PhD Direction I (cash transfers) and, if geocoded transfer data exist, it also supplies the programme locations the RCT transportability line of work lacks (see `notes/03_rct-transportability/Cross-Group Connections.md`). Parallel work on Option B is in a separate handoff.

## What is known

- Baxnaano is a World Bank-supported, government-run safety net paying monthly cash to over four million Somalis (programme description from the World Bank, found 2026-11-06).
- **No microdata or district-level beneficiary data was found** in a search that day. Only descriptions, the [design paper](https://openknowledge.worldbank.org/entities/publication/4d209ccd-8ac3-5bab-b98f-a96f5c67d687/full), and an IFPRI survey questionnaire turned up. The memo's claim of district-level quarterly or monthly disbursements for 2021 to 2024 and project ID P171346 is **unverified**.
- The panel has no transfer data. Outcomes available now: PRMN displacement, ACLED conflict, CHIRPS rainfall.

## Questions to answer, in this order

1. **Access first.** What transfer data exist, at what geography and frequency, and who holds them (World Bank task team, Ministry of Labour and Social Affairs, WFP, IFPRI)? How would Aaron request them? If nothing district-level exists, say so plainly; the plan may end here.
2. **Design.** If data exist: what variation identifies an effect (staggered district rollout, targeting thresholds, shock-triggered top-ups)? Targeting is not random, so what confounds it?
3. **Measurement.** A programme location is not a completed transfer, and displacement reason is not causal attribution (as the project README says). What can the data actually support?
4. **Literature.** Check and verify the closest work on cash transfers and displacement or conflict, including the Baxnaano evaluations.
5. **Fallbacks.** If only district-year or Admin-1 data exist, is a coarser design still worth running, or should C pause?

## Deliverable

One plan note (`notes/01_compound-shocks-panel/Option C Plan - Baxnaano.md`) with: the access findings, design options, risks, and a green, yellow or red go/no-go test, plus a draft email or request text for the data holders that Aaron can send himself.

## Ground rules

- Verify every citation and every access claim at the source; mark the rest unverified.
- Do not contact data holders on Aaron's behalf, and do not edit the panel repository or instance configs. Add only the plan note.
- Later implementation will live in `compound-shocks-panel` under `analysis/option_c_baxnaano/`, extend the shared panel only through a versioned release, and keep source code in its own files. That is for after Aaron approves the plan.
- Credentials never go in git. Follow the repo's worktree and landing procedure.
