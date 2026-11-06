# Brief for Gemini: Literature Gap Memo (Review Gate, Part B)

Drafted by Claude, 2026-11-03, for Gemini (Antigravity) to execute and Aaron to review. Routing follows `docs/AGENT_ROUTING.md`: Gemini runs the literature pipeline and large-context reads; Claude reviews the result afterwards.

## Purpose

Produce one document, **`ai-sandbox/research/independent-research/notes/01_compound-shocks-panel/review-gate/Literature Gap Memo.md`**, that answers the three questions the gate requires (`Pilot Scope Realignment - Exploratory Review Gate.md`, section 6, step 2) plus a fourth that Aaron added on 2026-11-03:

1. **What has already been published?** Are we duplicating an existing paper?
2. **What is the specific contribution?** Does it advance Direction I of the PhD plan (climate adaptation, migration and cash transfers under conflict; `Ground Truth - PhD Research Plan.md`, section 03)?
3. **What identification strategy is credible given the data gaps found in Phase A?**
4. **What additional data would be useful or interesting to add to the panel?** Look at what the closest papers use that we lack, and at what would close the gaps the audit found.

Aaron uses the memo to choose the research question, so the memo must tell him what is known and what was only searched for and not found. It must not propose or run any model.

## What the data can and cannot support (read first)

Read `Review Gate - Data Audit Review.md` in this folder. The points that matter for the search:

- **Panels:** Somalia (74 Admin 2 units, 2021-01 to 2025-10) and Sudan (189 localities, same months). Core columns in both: `events`, `fatalities`, `precip_mm`. Prices and displacement are extensions that differ by country.
- **Somalia prices** jump from 12 to 16 priced districts to 34 to 35 at about 2023-07, which looks like WFP network expansion. Before that the price panel is thin. **Somalia displacement** (PRMN, a flow) ends 2023-08, so dense prices and displacement barely overlap.
- **Sudan prices** cover 18 of 189 localities. **Sudan displacement** (DTM, a stock, Overview series only) starts 2023-08. Price gaps there look conflict-linked after the war began.
- The Somalia flow and Sudan stock are not comparable and cannot be pooled.
- Results are descriptive. Do not treat anything in the audit as a finding about causes.

## Tasks

### A. Search the existing corpus (offline, no API cost)

Use `python -m agent.literature` from `ai-sandbox/academic-rag-model/` (see `agent/literature/README.md`). Start with:

- `gap run` and `db query` with `countries=SO` and `countries=SD`, then by intervention, outcome and data source.
- `db cooccur` for papers that combine conflict event data, rainfall and prices or displacement.
- `db dist data_sources` to see whether ACLED + CHIRPS + WFP or DTM/PRMN appear together.

Report corpus coverage honestly: how many papers, how many extracted at which confidence tier. A corpus that does not include a paper does not show the paper does not exist.

### B. Search outside the corpus

Sources: OpenAlex, Semantic Scholar, NBER, CEPR, 3ie, SSRN, and the working-paper series of the World Bank, IFPRI, FEWS NET, WFP and FAO. Record the query, the source and the date for every search, including searches that returned nothing.

Topics, each answered separately:

1. **Somalia 2021 to 2023:** empirical work on the drought, the Ukraine-driven food price shock and al-Shabaab conflict together; displacement outcomes in particular.
2. **Import-price and climate interactions in East Africa:** food price transmission, rainfall shocks and conflict, with markets or districts as the unit.
3. **Compound or interacting conflict-climate shocks and displacement:** attribution methods, and what identification strategies they use (fixed effects, IV, event study, descriptive decomposition).
4. **Selection in market-price data under conflict:** studies of WFP or FEWS NET price series with missing markets, access constraints or survival bias. This matters because the audit found that missing prices look programme-driven in Somalia and conflict-linked in Sudan.
5. **Sudan since April 2023:** published or preprint work using ACLED and DTM or price data.
6. **Datasets and methods papers** that fuse ACLED, CHIRPS, WFP and displacement data into district-month panels (the Project 02 tool angle).
7. **Candidate additional data** (question 4). Start from what the closest papers use, then check at least these families: food-security classification (IPC, FEWS NET); malnutrition and health surveys; vegetation and drought indices beyond rainfall (NDVI/VHI, soil moisture, temperature, SPEI); exchange rates and USD or import prices; market access and roads; territorial control and humanitarian access constraints; other conflict sources (UCDP GED, GDELT); remittances and cash or social-protection programme data (the Direction I link); refugee and cross-border movement data (UNHCR, IDMC); night lights or settlement data as a population proxy.

### C. Write the memo

Structure it to match the three questions, plus:

- **Closest existing papers** (up to ten): citation, country and period, data, unit, identification strategy, and one sentence on how ours would differ.
- **Evidence table:** each claim, its source, and whether you read the paper, the abstract only, or a record in the corpus.
- **Not found:** queries that returned nothing relevant, so absence is documented, not asserted.
- **Identification options the data allow**, as a list for Aaron to choose from, with each option's main threat from the audit (for example: a Somalia price design must start around 2023-07; a Sudan design cannot use prices as exposure). Do not rank them beyond saying which the gaps rule out.
- **Additional data (question 4).** A table of the five to ten most worthwhile candidates. For each: source and provider, spatial and time resolution, coverage of Somalia and Sudan for 2021-01 to 2025-10, access route, licence and cost, and **which audit gap or paper-identified need it addresses** (for example: Somalia's thin pre-2023-07 prices, Sudan's pre-2023-08 displacement gap, price series not in a comparable currency, a population denominator that is a fixed 2014 estimate, no direct measure of access or market functioning). Mark each as core-style (could apply to both countries) or extension-style (one country only), and say whether it fits Direction I. Flag licences that restrict use: the Somalia COD-PS population file is limited to humanitarian operations, which is the kind of restriction to look for. End with a recommended shortlist of at most three, and say what each would allow that the current panel cannot.
- **Open questions** for Aaron.

## Rules

- **No fabrication.** Every citation needs a DOI or URL that you opened. If you cannot verify a paper, mark it unverified and say why.
- **No raw ACLED rows** in any prompt, file or external AI tool. Counts and aggregates only.
- **No modelling, regressions or data downloads into the panel.** This is a reading task: identify and describe candidate data, do not fetch or build it.
- **Cost:** the default route is a subscription agent and no paid API. If any step would cost more than $1, stop and ask Aaron first.
- **Verification states** as in `protocol.md`: label claims proposed, source-verified or corpus-derived. Nothing is "independently reproduced".
- Work in your own `gemini/<task>` branch and worktree (`docs/WORKTREE_WORKFLOW.md`). Do not land on `main`; hand the branch to Aaron.

## Hand-off

When done, tell Aaron the branch name, the memo path, how many papers each search returned, and what you could not verify. Claude will then review the memo before the Review Gate decision (Part C).
