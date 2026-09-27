# Somalia Three-Shock Case Study

*Case-study design for Project 02 — converted from a project-pitch brainstorm originally prepared for a NECR5250 one-on-one; course-specific framing (assignment splits, syllabus notes, meeting agenda) dropped since that course is no longer part of the courseload. The research design itself still stands as a candidate first case study for Project 02 — see `Ground Truth - PhD Research Plan.md`, Project 02.*

## The pitch

**The Black Sea grain disruption, drought and conflict in Somalia, 2021–2023**

In 2022, three shocks hit Somalia at once. The war in Ukraine disrupted Black Sea grain exports, a multi-season drought hit the Horn of Africa, and fighting with al-Shabaab continued *(verify)*. Food insecurity and displacement rose. Public actors then competed to explain why: the Russian blockade, Western sanctions, or the climate.

The project separates what each shock did, using public data on prices, rainfall, conflict and displacement, then tests the competing narratives against that evidence. It produces a verified dataset and a candidate mechanism for Project 02: import dependence as a condition on how climate shocks become displacement *(inference)*.

> One-line framing: "How a war in Ukraine, a drought and a local insurgency combined in Somalia's 2022 crisis, and who told the true story about it."

## Project design

**Main question** — How much of Somalia's 2021–2023 food crisis and displacement tracks the war-driven import price shock, the drought, and local conflict? How well did the public explanations match the evidence?

**Sub-questions**
1. **Shocks.** Across districts and months, how do imported-food prices, local-staple prices, food-security phase, and displacement move with each shock?
2. **Attribution.** How was displacement recorded as drought- or conflict-driven? How independent are the sources behind those figures?
3. **Narratives.** Who claimed what about the cause, where did each claim originate, and which claims hold up?

**Intended reader** — A humanitarian or donor analyst deciding whether a food crisis calls for a local response (drought relief, negotiating access) or a global one (import prices, trade policy). They also have to judge which public claims to trust.

**Scope** — Somalia only, roughly 2021–2023, at district and month level. Focus on south-central regions where drought, fighting and displacement overlapped, such as Bay, Bakool and Hiraan *(verify)*. The Ukraine end comes from existing trade and shipping series, not new OSINT collection.

### Layer 1 — Data: what happened

- Prices: WFP market prices on HDX, FSNAU *(verify)*
- Climate: CHIRPS rainfall, SPEI, vegetation anomalies
- Conflict: ACLED and UCDP events by district and actor
- Displacement: UNHCR-led PRMN (records reason for displacement, *verify*), plus IOM and IDMC
- Food security: IPC analyses
- Trade: grain-deal shipment records, UN Comtrade, FAO and AMIS prices

### Layer 2 — Narratives: what was claimed

- GDELT and Media Cloud news collections
- ReliefWeb reports, UN Security Council records
- Government and embassy press pages and Telegram channels
- RT and Sputnik Africa services
- Somali outlets such as Hiiraan Online and Garowe Online, machine-translated
- Sampled around key dates: Feb 2022, Jul 2022, Jul 2023

### Layer 3 — Verification: what holds up

- Remove duplicate syndicated stories before counting anything
- An LLM codes each claim against a short codebook; hand-code a sample to measure its accuracy
- Trace each claim to its origin in a lineage map
- Label each item as observation, source claim, or hypothesis, with a stated confidence

This verification layer — claim-lineage tracing plus a hand-checked LLM coding pass — is a reusable methods component worth folding into the Project 04 toolkit, not just a one-off step for this case.

## Method and risks

**Key method** — The war mainly raises prices of imported food (wheat flour, cooking oil). The drought mainly hits local staples (sorghum, maize) and livestock. Comparing the two across markets and months separates the shocks. Conflict then shows where markets and aid were cut off *(inference)*. This case study describes and triangulates these patterns with stated confidence; causal identification is deferred to the full Project 02 panel.

**Verification risks** — ACLED probably under-reports areas under al-Shabaab control, and price series have gaps there. The widely repeated share of Somali wheat that came from Russia and Ukraine needs tracing to its source. Famine was reportedly projected in late 2022 but never formally declared — check IPC before using the word *(verify)*. Causality also runs in several directions: drought can fuel conflict, and displaced people can become targets.

**Ethical risks** — The narratives are live information warfare, so report them without amplifying them. Keep all maps at district level or coarser, and treat aid-diversion claims as source claims, not facts. Observe armed actors' channels; don't engage with them. Check ACLED's terms before republishing its data *(verify)*.

**Deliverables** — A price-chart analysis separating the shocks, coarse district maps, a claims table with confidence ratings, and a claim-lineage graph. Code goes in a public repository.

## Rough timeline

- **Late Sep** — Verify load-bearing facts: famine status (IPC), how PRMN codes displacement reasons, source of the wheat-import-share figure. Register for ACLED.
- **October** — Pull price, rainfall, conflict, and displacement series. Draft the claims codebook and hand-code a first sample without AI.
- **November** — Run narrative collection and LLM coding; this feeds Project 02's first full draft (see Ground Truth's timeline).
- **December** — Analysis and writing.

## Adjustments worth keeping in mind

- **If it reads as too broad:** drop the Ukraine link and most of the narrative layer. The project becomes Somalia's drought, conflict and displacement alone — how drought reached people inside an active conflict, and how displacement got attributed to drought or conflict. Still keeps Layer 1, the attribution question, and the Project 02 connection.
- **If it should track a live conflict instead:** extend the Somalia window to the present, or run the same three-layer design on Sudan, where the war and food crisis are ongoing *(verify data availability)*.
- **If Ukraine should be the center instead:** shift to the supply end — strikes on Odesa and Danube export ports after the 2023 grain-deal collapse, and what happened to export volumes, with Somalia as one destination among several. Public sources only, kept separate from earlier RCT-based field work.
