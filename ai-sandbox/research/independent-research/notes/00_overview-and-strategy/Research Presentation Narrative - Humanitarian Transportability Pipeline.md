# Research Presentation Narrative: Humanitarian Transportability Pipeline

*Synthesis and 15-Slide Presentation Blueprint for PhD Research Presentation*

- **Author:** Aaron Scherf (with Antigravity / Gemini Operator)
- **Date:** November 8, 2026 (Updated with 15-Slide Text-First Architecture)
- **Context & Location:** `ai-sandbox/research/independent-research/notes/00_overview-and-strategy/Research Presentation Narrative - Humanitarian Transportability Pipeline.md`
- **Companion Plans & Trackers:**
  - `ai-sandbox/research/independent-research/notes/00_overview-and-strategy/Ground Truth - PhD Research Plan - 3R Revision.md`
  - `ai-sandbox/research/independent-research/notes/03_rct-transportability/Follow-up - Data Availability and Transportability Critique.md`
  - `ai-sandbox/research/independent-research/notes/03_rct-transportability/Brainstorming Transcript - Transferability of Crisis Interventions.md`
  - Central Tracker: `ai-sandbox/research/independent-research/PROJECTS.md`

---

## 1. Executive Summary: The Humanitarian Planner's Dilemma

When an emergency relief agency (UN OCHA, WFP, Red Cross, or World Bank FCV) is called to respond to a sudden crisis—such as extreme drought triggering famine in an active insurgency, or severe flooding in a conflict zone—planners face an acute operational bind:

1. **No Time for Discovery:** Planners cannot conduct a six-month academic literature review, nor can agencies run prospective randomized controlled trials (RCTs) in an active conflict zone. Planners must design and deploy an effective, life-saving intervention package **immediately**.
2. **Evidence Inaccessibility & Volume:** Without automated tools, response planning falls back on institutional memory, subjective heuristics, or qualitative "tabletop exercises." Planners are confronted with an overwhelming volume of academic papers and dense evaluation PDFs of uncertain local relevance and prohibitive complexity.
3. **The Resilience Planning Parallel:** In conflict or low-security environments, resilience planners face an analogous bottleneck under severe data scarcity:
   - They cannot safely send enumerators for extensive household surveys or ground interviews.
   - Crucially, resilience planning almost always prepares for an extreme or unprecedented shock that **has not yet occurred locally**. Planners are inherently forced to look to *other contexts* for lessons and counterfactuals.
   - While resilience operates on a longer investment horizon than emergency relief, the fundamental challenge is identical: **how to make evidence-grounded decisions across context boundaries when local historical data is missing or uninformative.**

### The Overarching Research Question
> *Can we build an open-source, reproducible computational pipeline that takes a novel crisis context and shock, rapidly ingests and fuses available multi-modal data, quantitatively maps the existing global evidence base, validates replicable trials, and predicts intervention treatment effects in the new target location—turning qualitative guesswork into an evidence-grounded simulation response exercise?*

---

## 2. Situating the Problem: Literature vs. Practitioner Reality

| Dimension | Academic Literature Reality | Humanitarian / Practitioner Reality |
| :--- | :--- | :--- |
| **Evidence Search & Consumption Costs** | Research exists, but it is dispersed across paywalled journals, disparate evaluation registries (3ie, J-PAL, World Bank), and hundreds of PDF reports with non-standardized reporting. | Planners face prohibitive search and synthesis costs. Even if evidence exists, they cannot consume, filter, and extract actionable estimands in the days or weeks before a response must launch. |
| **Comparison of Intervention Alternatives** | Evaluates a single specific intervention in isolation (or layered variations of the same program) to preserve internal validity. Academics rarely model the opportunity cost of alternative intervention types for the same problem. | Planners have an open canvas and a fixed budget. Their primary mandate is finding the **optimal portfolio of interventions** (e.g., mobile cash vs. in-kind food vs. index insurance payouts vs. infrastructure repairs) to minimize mortality and loss under budget constraints. |
| **Data Scarcity & Proxies** | Econometric identification traditionally requires clean, high-dimensional household survey panels, which are dangerous or impossible to collect in active crises. | Direct survey enumeration is unfeasible. Practitioners *must* rely on noisy, continuous proxies (satellite rasters, market price feeds, conflict event logs, mobile mobility traces) to assess conditions. |
| **Context Transportability** | Causal claims are strictly bounded by internal validity within a single study site; external validity is often addressed only qualitatively in the discussion. | Planners have no choice but to borrow evidence from other geographies; they need formal, context-aware frameworks that explicitly model how local conditions alter expected impact. |
| **Packaging & Usability** | Complex econometric specifications, bespoke code scripts, and non-standardized data pipelines. | Practitioners need a modular, portable toolkit that can be deployed to any new geography or shock without re-engineering the data pipeline. |

---

## 3. The 2×2 Mutually Reinforcing Architecture

Every component is designed as an **open-source, reproducible, standalone tool** that is portable to any new geography or shock, anchored by the foundational framework [`reprokit`](../../projects/reprokit/README.md).

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│ 0. FOUNDATIONAL INFRACRUCTURE: reprokit                                                     │
│    Standardized templates (study, evidence, library) with hash-pinned provenance            │
└──────────────────────────────────────────────┬──────────────────────────────────────────────┘
                                               │
         ┌─────────────────────────────────────┴─────────────────────────────────────┐
         │                                                                           │
         ▼                                                                           ▼
┌─────────────────────────────────────────────────────────┐ ┌─────────────────────────────────────────────────────────┐
│ PHASE 1: DISCOVERY & CONTEXT FUSION                     │ │ PHASE 2: EVIDENCE QUANTIFICATION & TRIALS               │
│                                                         │ │                                                         │
│  1.1 Literature Search & Synthesis                      │ │  2.1 3ie Evidence Taxonomy & Gap Analysis               │
│      • Continuous harvesting across OpenAlex, web,      │ │      • Quantifying evidence coverage across             │
│        and grey literature via snowball sampling.       │ │        intervention × outcome × country grids.          │
│                            │   ▲                        │ │                            │   ▲                        │
│                            ▼   │ (iterative feedback)   │ │                            ▼   │ (iterative feedback)   │
│  1.2 Context Data Fusion Panel                          │ │  2.2 Reproducible Trials Repository                     │
│      • Proof-of-concept multi-modal ingestion           │ │      • Extracting studies with open analysis microdata  │
│        (CHIRPS rasters, ACLED points, WFP prices).      │ │        and causally valid treatment effect estimators.   │
└────────────────────────────┬────────────────────────────┘ └────────────────────────────┬────────────────────────────┘
                             │                                                           │
                             └─────────────────────────────┬─────────────────────────────┘
                                                           │
                                                           ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ CONVERGENCE: AN ASYMPTOTICALLY "COMPLETE" REUSABLE KNOWLEDGE CORPUS                                                 │
│ • Mutually reinforcing iterations: taxonomy gaps direct search; trials provide context data; fusion anchors trials. │
│ • Context-Aware Replication Checks: Uncovers the relative validity of independent RCTs; outliers under identical  │
│   contexts signal study flaws or unmeasured confounders; similarity weighting informs prior variance spreads.        │
└──────────────────────────────────────────────────────────┬──────────────────────────────────────────────────────────┘
                                                           │
                                                           ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ CAUSAL TRANSPORTABILITY ENGINE (Proposed Methodological Options)                                                    │
│ Testing whether remote proxies can extend treatment effects to novel localities within context-aware frameworks:     │
│ • Bayesian Hierarchical Modeling: Priors from existing trials, updated by context shift to posterior distributions. │
│ • Synthetic Controls / Multi-Trial Weighting: Weighting combinations of related trials as a synthetic donor pool.   │
│ • Double Machine Learning (DML) & DAGs: Handling high-dimensional context features and diagnosing structural breaks.│
│ • Causal Neural Networks & Neural DAGs: Modeling non-linear interactions under structural graph constraints.       │
└──────────────────────────────────────────────────────────┬──────────────────────────────────────────────────────────┘
                                                           │
                                                           ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ PRACTITIONER DECISION SUPPORT: SIMULATION RESPONSE EXERCISE                                                         │
│ Iterating the transport engine across alternative interventions (cash vs. food vs. insurance) to compare predicted │
│ treatment effects, confidence bands, and cost-effectiveness for crisis response planning.                           │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. The 15-Slide Presentation Blueprint

### Slide 1: Title & Narrative Hook
* **Title:** The Humanitarian Planner’s Dilemma: Rapid, Evidence-Grounded Crisis Response Under Data Scarcity
* **Core Takeaway:** In a fast-moving crisis, responders face a crushing mismatch between the urgent timeline to act and the overwhelming volume of complex, hard-to-access research; an automated computational pipeline bridges this gap.
* **Key Content:**
  * **Speaker:** Aaron Scherf (Columbia University / SIPA Sustainable Development)
  * **The Operational Crisis:** Extreme disaster or conflict strikes; responders have days or weeks to allocate resources, while navigating severe data scarcity where primary field surveys or pilot RCTs are impossible.
  * **Research Identity:** Applied development economics, geospatial data fusion, and causal transportability under the 3R Framework (Resilience, Response, Recovery).
* **Visual Anchor / Placeholder:** Split infographic contrasting two realities:
  * *Left:* A 2-to-3 week emergency response window with life-or-death resource constraints.
  * *Right:* A mountain of thousands of academic papers and dense evaluation PDFs, labeled: *"High volume, fragmented access, complex econometrics, uncertain local relevance."*

### Slide 2: The Problem in Practice: Search Costs & Portfolio Decisions
* **Title:** The Reality of Crisis Response: Search Costs & Opportunity Costs
* **Core Takeaway:** Practitioners don’t lack evidence; they lack the ability to quickly consume it, synthesize it, and compare alternative interventions under budget constraints.
* **Key Content:**
  * **Evidence Search & Consumption Costs:** Thousands of evaluations exist across 3ie, J-PAL, and World Bank repositories, but they are buried in disparate databases and 80-page PDFs. Practitioners cannot consume or standardize them in an emergency.
  * **The Portfolio Optimization Problem:** Academics isolate single interventions. Humanitarian planners have a fixed budget and an open canvas—they need to compare the *relative* impact of cash vs. food vouchers vs. index insurance payouts vs. infrastructure repairs to save the most lives.
  * **The Resilience Parallel:** In conflict zones, resilience planners face identical data scarcity (no field surveys) and are almost always preparing for unprecedented shocks that haven't occurred locally yet—inherently requiring lessons borrowed from other contexts.
* **Visual Anchor / Placeholder:** A side-by-side comparison table contrasting *The Academic Question* ("Does Intervention X have an internally valid effect on Outcome Y?") with *The Planner Question* ("Given \$5M and 3 weeks in District Z, what mix of Interventions A, B, or C minimizes excess mortality?").

### Slide 3: State of the Art: The Limitations of Existing Frameworks
* **Title:** State of the Art: The Limitations of Existing Frameworks
* **Core Takeaway:** Existing tools are either descriptive dashboards, static retrospective bibliographies, or complex academic econometric models that cannot be deployed operationally.
* **Key Content:**
  * **[3ie Evidence & Gap Maps](https://www.3ieimpact.org/evidence-hub):** Excellent taxonomies, but static, manually curated, and purely descriptive; they tell you *where* studies exist, but do not extract reusable treatment effect estimators or connect to live spatial context.
  * **[World Bank DIME](https://www.worldbank.org/en/research/dime) / [Microdata Library](https://microdata.worldbank.org/) & [HDX](https://data.humdata.org/):** Rich data portals, but they function as passive visualizers. They lack counterfactual modeling, causal transportability, and the ability to simulate intervention alternatives.
  * **Academic Hierarchical Modeling & Meta-Analyses:**
    * [Meager (2019, AEJ: Applied)](https://pubs.aeaweb.org/doi/10.1257/app.20170299): Seminal Bayesian hierarchical analysis of seven microcredit RCTs, showing substantial cross-study effect variance.
    * [Vivalt (2020, JEEA)](https://academic.oup.com/jeea/article/18/6/2782/5819777): Proving impact evaluations have high dispersion across 20 intervention domains.
    * [Pritchett & Sandefur (2015, AER)](https://www.aeaweb.org/articles?id=10.1257/aer.p20151069): Showing that external trial estimates frequently have higher error than non-experimental local data.
  * **The Unmet Need:** An automated, end-to-end computational pipeline that connects literature extraction, spatial context fusion, and causal transportability into an active decision-support tool.
* **Visual Anchor / Placeholder:** A 2×2 positioning matrix: X-axis: *Static / Descriptive $\rightarrow$ Causal / Predictive*; Y-axis: *Slow / Retrospective $\rightarrow$ Rapid / Operational*. Existing solutions cluster in the other three quadrants; our pipeline targets the upper-right quadrant.

### Slide 4: Foundational Architecture: Standardized, Reproducible Research (`reprokit`)
* **Title:** Foundational Architecture: Standardized, Reproducible Research (`reprokit`)
* **Core Takeaway:** Projects require clear replication standards, licensing guidelines, taxonomy labels, and agent rules so that research is independently verifiable by humans and scalable by AI agents.
* **Key Content:**
  * **Standardizing Open Science & Data Science:** All project lines are orchestrated via [`reprokit`](../../projects/reprokit/README.md) (v0.4.0 released, open-source).
  * **Core Project Archetypes:**
    * `study`: Computational empirical pipelines with automated hash verification (e.g., panel fusion, RCT replications).
    * `evidence`: Machine-readable evidence maps, search manifests, and literature extraction schemas.
    * `library`: Reusable analytics packages.
  * **Built for Human and Agent Readability:** Designed from the ground up for modern AI-assisted research workflows. Directory layouts and metadata files (`project.yaml`, `compute.yaml`, `AGENTS.md`) allow autonomous LLM agents to parse, run, and audit codebases at scale without sacrificing human transparency.
  * **Portability Across Contexts:** Hash-pinned raw inputs, lockfiles, and CI running across Linux and Windows ensure that any pipeline can be ported to a new crisis geography in minutes.
* **Visual Anchor / Placeholder:** Architectural schematic showing `reprokit`'s project structure: `Copier Template` $\rightarrow$ `Dual Human/Agent Interface (AGENTS.md + protocol.md)` $\rightarrow$ `Automated Hash Registry` $\rightarrow$ `Verified CI Artifacts`.

### Slide 5: The 2×2 Evidence Engine: System Architecture
* **Title:** The 2×2 Architecture: Context Ingestion Meets Quantitative Evidence
* **Core Takeaway:** The system pairs continuous context data fusion with structured literature quantification, converging on an asymptotically complete, reusable knowledge corpus.
* **Key Content:**
  * **The Two Dimensions:**
    * *Dimension 1 (Context vs. Literature):* Multi-modal physical datasets vs. published academic/policy research.
    * *Dimension 2 (Discovery vs. Quantification):* Continuous automated harvesting vs. structured taxonomies and microdata extraction.
  * **The Four Quadrants:**
    * **1.1 Literature Search & Synthesis:** Automated harvesting across OpenAlex and web scraping.
    * **1.2 Context Data Fusion Panel:** Subnational harmonization of rasters, points, and prices.
    * **2.1 3ie Literature Taxonomy:** Structuring coverage and diagnosing evidence gaps.
    * **2.2 Reproducible Trials Repository:** Curating open RCTs with causal treatment estimators.
* **Visual Anchor / Placeholder:** A clean 2×2 diagram with bidirectional feedback arrows linking the four quadrants, leading down into the Causal Transportability Engine.

### Slide 6: Component 1.1: Automated Literature Discovery & Synthesis
* **Title:** Component 1.1: Automated Literature Discovery & Synthesis
* **Core Takeaway:** Automated harvesting across OpenAlex and grey literature collapses search costs from months to minutes, producing standalone synthesis reviews.
* **Key Content:**
  * **Overcoming Search Costs:** Automated harvesters continuously query OpenAlex, academic APIs, and grey literature portals (ALNAP, ReliefWeb, World Bank Open Knowledge).
  * **Snowball & Semantic Filtering:** Citation graph expansion combined with keyword filtering to capture both peer-reviewed economics papers and high-value institutional evaluation reports.
  * **Standalone Usable Deliverables:** The literature review produced by this phase is not just an intermediate data step—it serves as a standalone, publishable evidence synthesis for practitioners and researchers.
  * **Current Status:** Initialized; actively transitioning from ad-hoc sampling to an automated, structured indexing pipeline.
* **Visual Anchor / Placeholder:** Workflow diagram showing automated ingest: `OpenAlex API / Web Scraper` $\rightarrow$ `Keyword / Metadata Filter` $\rightarrow$ `Snowball Citation Expansion` $\rightarrow$ `Searchable Synthesis Document & Bibliographic Manifest`.

### Slide 7: Component 1.2: Subnational Context Data Fusion & Analytics Library
* **Title:** Component 1.2: Subnational Context Data Fusion & Analytics Library
* **Core Takeaway:** The data fusion pipeline and panel data are standalone outputs, powered by a library that converts high-dimensional raster geodata into usable subnational context.
* **Key Content:**
  * **Standalone Research Assets:** The resulting harmonized panel dataset and its open-source processing pipeline are independent, reusable research deliverables.
  * **The Open-Source Data Fusion Library:** Automates:
    * Multi-modal data ingestion (satellite rasters, point events, tabular price feeds).
    * Spatiotemporal standardization and spatial matching (Admin-2 / district-month).
    * Automated cleaning, boundary alignment, and missingness audits.
    * Exploratory spatial data visualization.
  * **Core Technical Contribution:** Transforming high-dimensional Earth observation rasters (CHIRPS precipitation, VIIRS night lights, Sentinel imagery) into structured, tabular context variables situated alongside conflict logs (ACLED/UCDP) and market feeds (WFP).
  * **Testbeds:** Somalia and Sudan pipelines rebuilt with 100% hash verification on CI.
* **Visual Anchor / Placeholder:** Pipeline schematic: `Raw High-Dimensional GeoTIFF Rasters + ACLED JSON + WFP CSV` $\rightarrow$ `Automated Fusion Library` $\rightarrow$ `Analysis-Ready Subnational Panel (Admin-2 District-Month)`.

### Slide 8: Component 2.1: Quantifying Evidence Coverage via 3ie Taxonomies
* **Title:** Component 2.1: Quantifying Evidence Coverage via 3ie Taxonomies
* **Core Takeaway:** Standardized 3ie taxonomies allow us to map evidence coverage and critical gaps across country-specific matrices, integrating academic and grey literature.
* **Key Content:**
  * **Multi-Dimensional Evidence Matrices:** Classifies both peer-reviewed papers and institutional grey literature across 3ie’s standardized intervention (cash, vouchers, insurance, public works) and outcome taxonomies (consumption, nutrition, displacement).
  * **Geographic Breakdown:** Each matrix is generated for a specific country of interest (starting with Somalia and Sudan to establish proof of concept).
  * **Diagnosing Evidence Deserts:** Calculates empirical density scores to show where evidence is dense (e.g., cash in peaceful settings) versus where critical evidence deserts exist (e.g., parametric insurance or anticipatory action in conflict).
  * **Current Status:** Yellow; proof-of-concept classification completed on a small sample of papers; moving to scale.
* **Visual Anchor / Placeholder:** Country-specific heatmaps for Somalia and Sudan: Rows = Interventions; Columns = Outcomes. Dense green clusters highlight well-studied areas, while red/blank cells illustrate severe evidence deserts.

### Slide 9: Component 2.2: Curating Whole Trial Repositories & The Geolocation Gate
* **Title:** Component 2.2: Curating Whole Trial Repositories & The Geolocation Gate
* **Core Takeaway:** Curating open-access crisis RCTs from major evaluation repositories bridges literature with spatial context, bounded by the village geolocation gate.
* **Key Content:**
  * **The Candidate Corpus:** Drawing from full evaluation databases:
    * [AEA Data and Code Repository](https://www.openicpsr.org/openicpsr/) (e.g., Niger cash & conflict rollout across 4,000 villages).
    * [World Bank Microdata Library](https://microdata.worldbank.org/) / DIME (e.g., Bangladesh forecast-based flood cash).
    * [Harvard Dataverse](https://dataverse.harvard.edu/) & [J-PAL Dataverse](https://dataverse.harvard.edu/dataverse/jpal) (hundreds of open evaluation microdata packages).
  * **Extracting Estimators:** Curating studies with open microdata and causally valid treatment effect estimators (RCTs and clean quasi-experiments).
  * **The Decisive Geolocation Gate:** Published packages often mask village GPS coordinates to protect participant safety in conflict zones. Linking treatment effects to satellite rasters requires precise cluster coordinates or formal author data linkages.
* **Visual Anchor / Placeholder:** Repository extraction flow: `Major Trial Databases (AEA, World Bank, J-PAL, Dataverse)` $\rightarrow$ `Filter for Crisis/Disaster RCTs` $\rightarrow$ `Extract Treatment Estimators` $\rightarrow$ `Village Geolocation Audit / Linkage Gate`.

### Slide 10: The Evidence Cycle: Iterative Feedback & Relative Trial Validity
* **Title:** The Evidence Cycle: Iterative Feedback & Relative Trial Validity
* **Core Takeaway:** Mutual iterations lead to an asymptotically complete knowledge corpus, while context-aware checks reveal outlier trials and calibrate prior variance.
* **Key Content:**
  * **The Reinforcing Feedback Loops:**
    * *Taxonomy $\leftrightarrow$ Search:* 2.1 gaps trigger targeted 1.1 search sweeps.
    * *Trials $\leftrightarrow$ Fusion:* 2.2 trials inject new context variables into 1.2; 1.2 fusion panels provide the spatial canvas to anchor 2.2 trials.
  * **Asymptotic Convergence:** Continuously expanding the corpus until evidence coverage for a target domain is as complete and searchable as possible.
  * **Context-Aware Relative Validity Checks:** Evaluating multiple trials of the same intervention across comparable context grids reveals relative validity. If 9 trials show positive effects but 1 shows negative effects under identical climate/market context, it exposes a study-specific flaw or an unmeasured confounder.
  * **Calibrating Priors:** Similarity weighting across related trials provides an empirical, data-driven variance spread for subsequent Bayesian priors.
* **Visual Anchor / Placeholder:** An iterative circular flowchart showing the continuous feedback between the 4 quadrants, with an inset graph showing 10 trial effect sizes where 1 context-controlled outlier is detected.

### Slide 11: Causal Transportability in Practice: Satisficing Under Covariate Shift
* **Title:** Causal Transportability in Practice: Satisficing Under Covariate Shift
* **Core Takeaway:** External validity is difficult even across peaceful settings; in crisis settings, transportability is an exercise in satisficing to estimate impact ranges and non-applicability.
* **Key Content:**
  * **The External Validity Dilemma:** Transporting causal findings across contexts is challenging even in peaceful, well-resourced environments ([Pritchett & Sandefur 2015](https://www.aeaweb.org/articles?id=10.1257/aer.p20151069); [Vivalt 2020](https://academic.oup.com/jeea/article/18/6/2782/5819777)). In disasters and armed conflict, it is exponentially harder.
  * **Satisficing in the Absence of Primary Data:** When running local RCTs or field surveys is impossible, waiting for perfect evidence is fatal. We must satisfice: generating reliable, empirically bounded impact estimates with valid confidence intervals.
  * **The Standard Covariate Shift Problem:**
    * Holding the intervention functionally constant (e.g., standard unconditional cash transfers).
    * Allowing observable context distributions to shift (climate stress, market density, baseline poverty).
    * **Measuring Non-Applicability:** Quantifying the degree to which existing evidence does *not* apply in a new setting by estimating the variability and dispersion of an intervention's impact across known environments.
* **Visual Anchor / Placeholder:** A distribution plot illustrating *Satisficing Under Covariate Shift*: Source Trial Distribution vs. Target Context Shift, showing how the target effect estimate widens to reflect genuine uncertainty rather than a false point estimate.

### Slide 12: Beyond Covariate Shift: Structural Breaks in Crisis Environments
* **Title:** Beyond Covariate Shift: Structural Breaks in Crisis Environments
* **Core Takeaway:** In conflict, unstated security assumptions fail; modeling causal linkages via DAGs identifies where mechanisms break down and how to route around them.
* **Key Content:**
  * **The Failure of Unstated Assumptions:**
    * *In Peacetime:* Cash to farmers increases drought resilience, assuming open trade corridors, functional mobile networks, and non-predatory authorities.
    * *In Armed Conflict:* Armed groups extort recipients, mobile networks are jammed, or trade routes are blockaded. The intervention's causal linkages collapse.
  * **The Structural Break as a Validity Check:** A distinct line of inquiry that audits whether the causal chain itself is intact before attempting covariate adjustment.
  * **Modeling Mechanism Breakdowns with Directed Acyclic Graphs (DAGs):**
    * Mapping transmission nodes: $Transfer \rightarrow Liquidity \rightarrow Market \; Purchase \rightarrow Nutrition / Welfare$.
    * Identifying friction nodes: Checkpoints, military blockades, inflation spikes, and extortion.
    * **Operational Route-Arounds:** If the DAG reveals that the market purchase link is severed (supply inelasticity), planners know cash will fail and in-kind food distribution or direct logistics must be deployed instead.
* **Visual Anchor / Placeholder:** Causal DAG diagram contrasting a peaceful transmission chain with a conflict-disrupted chain, highlighting a red *"Structural Break"* node where market supply or telecommunications are blocked.

### Slide 13: The Methodological Toolkit: Estimating Impact in Novel Localities
* **Title:** The Methodological Toolkit: Estimating Impact in Novel Localities
* **Core Takeaway:** A flexible toolkit—combining Bayesian hierarchical updating, synthetic control donor pools, DML, and Causal Neural Networks—models non-linear context interactions.
* **Key Content:**
  * **A Modular Set of Proposed Tools (Not a Forced Single Estimator):**
    * **Bayesian Hierarchical Modeling (e.g., Meager 2019):** Treats past trial estimates as empirical priors; updates them via observed context shifts (from the fusion panel) to yield posterior distributions for the target site.
    * **Synthetic Controls / Multi-Trial Weighting:** Treats historical trials as a synthetic donor pool, weighting them by spatial and institutional similarity to construct counterfactuals.
    * **Double Machine Learning (DML; Chernozhukov et al.):** High-dimensional regularized estimation to control for complex spatiotemporal confounders.
    * **Causal Neural Networks & Neural DAGs:** Using causal deep learning (e.g., Dragonnet, TARNet, Neural Structural Equation Models) to learn latent representations under DAG constraints, modeling complex non-linear interactions across high-dimensional satellite and context feeds.
* **Visual Anchor / Placeholder:** Methodological comparison schema: Bayesian Updating Curve + Synthetic Control Weighting Matrix + Neural DAG Architecture, converging into a unified *Predicted Treatment Effect Distribution*.

### Slide 14: Decision Support in Action: The Simulation Response Exercise
* **Title:** Decision Support in Action: The Simulation Response Exercise
* **Core Takeaway:** Planners can simulate and compare alternative intervention packages before committing resources, grounded in empirical evidence.
* **Key Content:**
  * **The Simulation Response Exercise:** Running the transport engine across multiple candidate interventions for the same crisis geography:
    * *Option A (Unconditional Cash):* High expected impact, but wide variance due to volatile local market prices.
    * *Option B (In-Kind Food Distribution):* Lower logistical efficiency, but immune to local market blockades.
    * *Option C (Parametric Index Payouts):* Rapid execution, but high basis risk.
  * **Comparing & Layering Interventions:** Simulating how interventions interact—evaluating whether layering cash with crop insurance or supply subsidies yields positive complementarities under budget constraints.
  * **Active Case Engagement:** Practical collaboration in progress with a foundation in Armenia to supply a structured evidence map and decision-support synthesis for local planning.
* **Visual Anchor / Placeholder:** Practitioner dashboard UI mock-up: A map selector for target districts, with comparative probability density curves and cost-per-life-saved curves for Cash vs. Food vs. Layered Packages under a \$5M budget.

### Slide 15: Methodological Frontiers, Open Questions & Roadmap
* **Title:** Methodological Frontiers, Open Questions & Roadmap
* **Core Takeaway:** Critical open questions remain around intervention layering, displacement dynamics, spatial resolution limits, and proxy surrogacy, setting up the Year 1 roadmap.
* **Key Content:**
  * **Core Open Questions:**
    * *Intervention Combining & Layering:* If we have context-grounded causal estimates for interventions in isolation, how do we model their combination or determine which is best suited for a specific geography?
    * *Displacement & Migration Dynamics:* Interventions assume populations remain in place; crises force displacement. Is displacement an outcome (evacuation vs. entrapment) or a mediating context filter?
    * *Spatial Resolution Limits:* Can conflict (ACLED/UCDP) and displacement tracking (UNHCR/IOM) resolve finely enough below Admin-2 (district) to match village trial clusters?
    * *Surrogate Validity of Remote Proxies:* When does satellite data (NDVI, night lights) fail statistical surrogacy for human welfare in active combat?
  * **Ideal Testbeds:** Cash transfers and index insurance in drought-induced famine settings (Somalia and Sudan testbeds, where crop failure is directly measurable via satellite).
  * **Immediate Roadmap:** Finalize village coordinate joins $\rightarrow$ Scale 3ie taxonomy classification $\rightarrow$ Complete transport engine proof of concept $\rightarrow$ Working paper for spring presentation.
* **Visual Anchor / Placeholder:** Timeline graphic for Winter 2026 – Spring 2027 mapping milestones (Data Linkages $\rightarrow$ Taxonomy Scaling $\rightarrow$ Armenia Pilot $\rightarrow$ Working Paper Draft).
