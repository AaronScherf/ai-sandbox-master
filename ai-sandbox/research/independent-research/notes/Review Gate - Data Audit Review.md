# Review Gate, Part A: data audit review (2026-11-03)

Reviewer: Claude. Inputs: both audit memos from `compound-shocks-panel` v0.1.1 (Somalia 74 districts x 58 months, Sudan 189 localities x 58 months, 2021-01 to 2025-10), the verification notes, and a count of districts with a price by month from the Somalia panel (no ACLED rows used). This is descriptive. No tests were run and nothing here is a causal claim. Part B (the literature gap memo) and Part C (your decision) are not covered.

## Bottom line

Neither panel is ready for a conflict-by-price design as it stands. Three things decide what is usable:

1. **Somalia's price coverage jumps at one date, which looks like WFP network expansion, not conflict.** 12 to 16 districts have a price in the months I sampled (every fourth month) from 2021-01 to 2023-05, then 34 to 35 from 2023-09 to 2025-09. The 21 districts with exactly 28 priced months are all priced 2023-07 to 2025-10, with no earlier price.
2. **The two displacement measures barely overlap the period when each country's prices are good.** Somalia's flow ends 2023-08, before price coverage improves. Sudan's stock starts 2023-08.
3. **Sudan's price panel is too thin and too selected to use.** 18 of 189 localities have a price (7% of locality-months, 17% of population).

## 1. Do price gaps track conflict intensity?

**Somalia: not in the way the survival-bias worry predicts.** Pooled, market districts have more events in months with a price (6.08) than without (3.91). By year the sign flips: 2021 and 2022 price months have more events (6.43 vs 3.24; 8.60 vs 3.00), 2024 and 2025 price months have fewer (4.30 vs 7.52; 7.46 vs 9.00). The pooled gap is a mix of year effects and which districts entered the price panel when. The 2023-07 step change explains much of it. Between districts, markets sit in busier places (5.33 vs 3.37 mean events) but per 100,000 residents the difference reverses (2.57 vs 3.07). **Reading:** the selection problem is where and when WFP monitors, which is not random with respect to conflict but is mostly a programme decision. A design that treats a missing price as informative about conflict would be misspecified before 2023-07.

**Sudan: consistent with conflict-driven gaps after the war began.** Within market localities, months without a price have more events (8.49 vs 5.63) and more fatalities (29.8 vs 17.0). By year, 2023 (12.19 vs 5.57) and 2024 (10.72 vs 6.24) show the largest gaps. 2021 and 2025 do not. This is the pattern you would expect if markets stop reporting under intense fighting, but it is a pattern in means, not evidence of cause. Between localities, the 18 with prices have 3.8 times the mean events of the rest (6.39 vs 1.69), so the sample is selected toward violent, populous places.

**Both countries:** ACLED counts reflect reporting and access as well as events. The zero-event shares (41% Somalia, 65% Sudan) mean "none recorded". Price gaps and event gaps can share a cause (access constraints), which this audit cannot separate.

## 2. Does Admin 2 aggregation hide or create patterns?

Not testable from the memos alone, so treat as open. What the memos do show:

- **Banadir is a merged unit** (17 Mogadishu districts plus "Unspecified"): 1.65 million people and 2,856 of 18,663 events (15%). Any pooled estimate is sensitive to it. Check results with and without it.
- **Unit sizes differ widely**, and no area column is in the panel. Mean monthly rainfall over a large arid district may mask local rainfall variation, and `coverage_frac` is 100% everywhere so it carries no information. Rainfall is the variable most exposed to this.
- **Sudan's localities have 296 to 344 unassigned events** (maritime or outside polygons) and Somalia 278; all are excluded, not allocated.
- **Population is a fixed figure.** Somalia's is a 2014 modelled estimate (not a census, includes IDPs as then counted); Sudan's is the 2024 file. Per-100,000 rates mix vintages and will drift from current populations after displacement.

## 3. What is too sparse to use

| Item | Coverage | Use |
| --- | --- | --- |
| Somalia sorghum or wheat price | 33% of district-months, 37 of 74 districts (68% of population); 12 to 16 districts before 2023-07 | Only 2023-07 to 2025-10 is reasonably dense, and only in market districts |
| Somalia displacement (PRMN flow) | 2021-01 to 2023-08 only | Overlaps the thin-price period; none for 2023-09 on |
| Sudan sorghum or wheat price | 7% of locality-months, 18 of 189 localities | Descriptive only |
| Sudan displacement (DTM stock) | 32% of locality-months, none before 2023-08, 39 months with no report anywhere | War period only; no pre-war baseline |
| ACLED, CHIRPS, boundaries | Complete in both | Fine as the core of a panel |
| Prices generally | Nominal local currency | Not comparable across districts or time without a deflator or USD series; Sudan also mixes retail and wholesale and 3.5 kg and 90 kg millet units |

The only consistent, dense, cross-country variables are the core ones: `events`, `fatalities`, `precip_mm`. That limits any early work to conflict-rainfall relationships unless the price and displacement gaps are handled by design.

## 4. Defects found in the audit memos themselves

These do not change the panels or hashes, but they affect how the memos read.

1. **Stale text in the working-copy memos.** The Somalia memo on disk says the pipeline keeps 2021-01 to 2023-08 and that 111 events fall outside districts (correct: 2025-10 and 278). The Sudan memo says it keeps 2021-01 to 2024-12 and 296 events (correct: 2025-10 and 344). The fresh-clone memos are correct. The audit step evidently does not rerun when only a descriptor changes, so a memo can describe an older descriptor. Rerun the memos before sharing them.
2. **Boilerplate wrong for Sudan.** The "Points to carry" list says "A missing displacement row is a missing value: PRMN lists reported flows only." For Sudan the source is a DTM stock. The same list also describes sorghum price coverage while the warnings are about millet.
3. **Sudan unit label.** The memo says "189 districts" where the unit is localities.

None is a data error. Item 1 is a small reproducibility bug in the audit step. Items 2 and 3 are template wording. I made no code changes, per the gate rules. A `v0.1.2` could fix them if you want the memos publishable as is.

## 5. What this implies for the research question

Not a recommendation yet, since Part B (what is already published) is missing. But the data constrain the options:

- A Somalia design that uses prices needs to start in 2023-07 or model the coverage change explicitly. That is after PRMN ends, so price effects and displacement outcomes cannot share a window.
- A Sudan design can use displacement (stock) and conflict from 2023-08, but prices are too thin to be an exposure.
- A cross-country comparison is limited to the core columns by design. Displacement cannot be pooled.
- Missing prices should be handled as missing, not zero, and not read as informative before the coverage change is understood.

## Open items for you

1. Whether to fix the memo defects (item 4) in a `v0.1.2` or leave them documented.
2. Which window and country the research question should centre on, once Part B is done.
3. Part B needs the literature pipeline and Gemini. I have not run it.
