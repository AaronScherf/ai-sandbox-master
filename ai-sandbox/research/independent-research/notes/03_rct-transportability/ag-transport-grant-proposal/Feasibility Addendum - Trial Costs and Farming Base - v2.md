# Trial costs, farmer survey and the farming base (Addendum v2)

*2026-11-17. Extends [Addendum v1](Feasibility%20Addendum%20-%20Fertilizer%20Access%20and%20Trial%20Size%20-%20v1.md) (model and results there still stand). Code: [`16_farming_base_by_risk.py`](../../projects/ag-transport-pilot/scripts/16_farming_base_by_risk.py); tables `outputs/farming_base_*.csv`. One analyst; not independently reproduced.*

## 1. Per-site trial cost: no real figure found

Four searches (on-farm trial budgets, mother-baby trials, N2Africa, conflict-setting data-collection premiums) found **no published per-site cost of a researcher-managed fertilizer-response trial in sub-Saharan Africa**, and none for a conflict setting. What exists:

- Maize **breeding** trials in Eastern and Southern Africa cost about **$5.73 per row**, rising $1 per 130 km from the coordinating centre ([CGSpace costing study](https://cgspace.cgiar.org/server/api/core/bitstreams/2978519a-f177-4710-b4fa-159ca8b63766/content)). Not comparable: no fertilizer treatments, no crop cuts, no security.
- A World Bank volume on data collection in fragile settings is split: one chapter says costs are much higher in violent settings, another that innovations compare favourably with traditional methods ([Springer chapter 14](https://link.springer.com/chapter/10.1007/978-3-030-25120-8_14)). No percentage premium is given. Qualitative only.
- A $24,000 N2Africa Ethiopia pilot budget exists but is not broken down per trial.

**Verdict: my $20,000-60,000 per site is unvalidated; I cannot say it is close.** The fertilizer itself is a trivial share (a five-rate, four-replicate plot set is about 500 m2). Cost is driven by staff, vehicles, security, supervision and three seasons of visits, which is where conflict bites. Better anchors, in order: (1) the budget of the CIMMYT/Sustain Sudan 2024/25 crop-cut assessment and its seed and fertilizer delivery (ask the authors); (2) Africa RISING or N2Africa final-report budgets; (3) a bottom-up count of visits, vehicle-days and security days, which I can build once you have partner quotes. Until then the proposal should show cost as a parameter, not a number.

## 2. The IFPRI survey

Full report: [Farming in Crisis: Livelihood Challenges and Resilience in Conflict-Affected Sudan, Sudan Strategy Support Program Working Paper 27, May 2026](https://cgspace.cgiar.org/server/api/core/bitstreams/c1849f3b-34ed-4d9f-92c9-2548f7e642e9/content) (60 pages, read); [summary page](https://sudan.ifpri.info/2026/05/14/farming-in-crisis-livelihood-challenges-and-resilience-in-conflict-affected-sudan-insights-from-the-sudan-2024-smallholder-farmers-survey/). **It has no fertilizer or seed prices** (searched the text for price, urea). What it does give:

- **Design:** phone (CATI) survey, 2,101 farming households in 13 of 18 states (**no Darfur**), planned for 4,500; sampling frame built from existing contact databases, so it over-represents connected farmers.
- **Fertilizer use** in the 2023/24 winter season: over three-quarters of households (almost three-quarters chemical), mostly bought on the market; in the 2023 summer over 40% used none. The by-crop figure lists wheat, maize, beans, other pulses, vegetables and fodder, **not sorghum**; I found no rainfed-sorghum use rate.
- **Planting:** for the 2024 summer season **just over half of households planned to grow no crops**; 21% planned more area, under 14% less, 14% the same.
- **Displacement and constraints:** 28% of farming households displaced in 2023 (earlier survey); 61% in 2023 could not buy seed and fertilizer; over three-quarters had no external assistance in 2024.

## 3. Is there a farming base worth a program?

**"No documented cropland" is a mapping artifact in South Sudan, not an absence of farmers.** The FAO/WFP assessment ([CFSAM 2025](https://climis-southsudan.org/uploads/publications/CFSAM_2025.pdf), 19 March 2026, read) puts **1.34 million farming households** (sum of Table 2 state rows) on **1.26 million hectares of cereals**, about 0.9 ha each, yield 1.2 t/ha, area **up 7%** in 2025 as returnees and urban households took up farming. That is about 2% of the country in small scattered plots; WorldCover's 1 km mean cropland share averages 0.4%. For Sudan, the two sources agree: WorldCover cropland 16.3 million ha in my cells against FAO's 15.3 million ha planted to sorghum, millet and wheat in 2024/25 (up 10% on the previous season). Sudan's 2025 cereal output was 5.2 million tonnes, 22% down (sorghum down 25%), so farming continues at scale but hurt. FAO reached about 827,000 farming households with seed in 2025 (the 15.3 million ha, +10%, and 827,000 figures come from search summaries of FAO Sudan reports that I could not open).

**The relevant question is how much of it is both fertilizer-relevant and reachable.**

| | Farming households or cropland | In cells with risk at or below 2 | At or below 10 | At or below 40 |
|---|---|---|---|---|
| South Sudan households (CFSAM, spread evenly within each state, rough) | 1.34 million | 0.25 million (19%) | **0.53 million (40%)** | 0.90 million (68%) |
| Sudan cropland (WorldCover), all cells | 16.3 million ha | 3.4 (21%) | **5.7 (35%)** | 10.2 (62%) |
| Sudan cropland, climate-suitable cells (AI at least 0.2) | 8.3 million ha (51%) | 1.8 (11%) | **3.7 (23%)** | 6.2 (38%) |

Risk is weighted violent events a year within 50 km, October 2023 to October 2025.

By state in Sudan: **Gedaref (3.8 million ha cropland, median risk 1.5) and Kassala (1.0, 0.5) are low-risk**; Al Jazirah (1.7 million ha, median 380) and Sennar (2.7, 25) are not; Kordofan and Darfur are mid (median 8-19). In South Sudan the low-risk states are Western Bahr el Ghazal (median 0), Northern Bahr el Ghazal (3) and Western Equatoria (9); Warrap (82), Lakes (39) and Central Equatoria (37) are not.

**Reading.**
1. There are enough farmers to matter: millions of households. But the **addressable base is much smaller**, and for different reasons by country.
2. **South Sudan:** about 0.5 million households sit in cells below a cap of 10, but none uses fertilizer and the stated limit on their area is labour, not nutrients (CFSAM). A fertilizer program needs supply and a reason to expand; trials alone would not create either.
3. **Sudan:** the low-risk belt (Gedaref, Kassala) is largely mechanized rainfed sorghum, whose operators can already import inputs; the smallholder rainfed zones (Kordofan, Darfur) are riskier, have no measured fertilizer use rate, and half the surveyed households did not plan to plant in 2024. Irrigated Gezira, where fertilizer is used and prices were reported, is the highest-risk area on the map.
4. My AI cut (at least 0.2) removes irrigated land in arid states (Nile, Northern); the table shows that cost, about half of Sudan's cropland.

**Implication for the proposal.** The case for funding is strongest as *conditional* and *staged*: (a) Aim 1 first (cheap); (b) a small trial network where fertilizer is, or soon can be, available and risk is low (Sudan's Gedaref-Kassala-Kordofan belt; South Sudan's Western Equatoria and Bahr el Ghazal states) rather than a country-wide coverage design; (c) a use-case check, before any trial is funded, with two or three named decision-makers (for example the Sustain Sudan input program and FAO's seed and fertilizer distribution) on what response size would change what they buy or distribute.

## 4. Limits
Households are spread evenly over each state's cells; GAUL 2015 states with Ruweng, Pibor and Abyei folded into Unity, Jonglei and Warrap; WorldCover cropland is a share of 1 km cells; ACLED reflects reporting, not true risk; the farmers who answered a phone survey are not representative. IFPRI text was read via PDF extraction, which garbles some characters.
