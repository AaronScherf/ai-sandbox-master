# Ground Truth (3R Framework Revision)

*Research Planning Memo — Revised Focus: Compounded Disasters, Conflict Economics, and the 3R Framework*

A strategic revision of the PhD research plan at Columbia SIPA (Sustainable Development). This memo supersedes the August 2026 admissions synthesis by incorporating a refined research identity centered on **Resilience, Response, and Recovery (3R) in Compounded Disasters and Armed Conflict under Data Scarcity**, while preserving the original `Ground Truth - PhD Research Plan.md` for historical comparison.

- **Author:** Aaron Scherf (with Antigravity / Gemini Operator)
- **Date:** October 2026 (Revised from 2026-08-31 baseline)
- **Source Context:** `research/independent-research/notes/Ground Truth - PhD Research Plan.md`
- **Companion Operational Plan:** `research/independent-research/projects/research_projects_plan_fall26 - 3R Revision.md`

---

## 01. Summary of Strategic Revisions

Following in-depth reflection on earlier statements, brainstorms (`Research Ideas.md`, `Somalia Three-Shock Case Study.md`, `Data Sources - Climate Displacement Cash Conflict.md`), and the reality of the first-year core courseload, this revision makes explicit structural adjustments:

1. **Re-centering on the "3R" Framework (Resilience, Response, Recovery):**
   Rather than treating climate adaptation and conflict as two separate silos, this agenda studies how civilian populations navigate **compounded crises** (natural hazards, armed conflict, and macroeconomic price shocks). The substantive focus is not on why wars start or how to broker peace (military/political issues), but on how normal people survive, how emergency relief reaches them, and how reconstruction can be sustained:
   - **Resilience / Preparedness (Ex-Ante):** Anticipatory action, pre-positioned mobile money rails, early-warning risk communication, and parametric risk protection.
   - **Response (Ex-Post Immediate):** Rapid damage assessment via satellite and drone sensing, mobile network tracing, market price monitoring, and emergency mobile cash delivery.
   - **Recovery / Rebuilding (Medium to Long-Term):** Capital replacement, preventing distress asset sales, returning IDPs, and public/private investment in physical and economic reconstruction.

2. **Differentiating from Pure Agricultural Economics:**
   Agriculture and climate are the primary *mechanisms of exposure*—because vulnerable populations in fragile states depend heavily on agriculture for sustenance and income, disruptions to food production drive poverty and displacement. However, the intellectual identity is not agronomic or crop-science (agnostic to specific seed genetics or irrigation engineering), but institutional, financial, and empirical.

3. **Pioneering the Disaster-to-Conflict Transferability Agenda:**
   Disaster risk reduction (DRR) boasts mature empirical research, robust parametric insurance schemes, and institutional Anticipatory Action frameworks (OCHA, Red Cross, World Bank). Armed conflict environments have historically lacked this financial architecture because researchers avoid them due to data scarcity and political risk. Demonstrating how disaster-response mechanisms transfer to conflict shocks is the core intellectual contribution.

4. **Dropping the Chatbot Survey Pilot (Project 03):**
   The proposed AI-chatbot survey pilot is formally dropped from the flagship research plan. While conversational LLM interfaces are technically interesting, software already exists, IRB lead times are heavy, surveyor-displacement and respondent-trust raise substantial ethical complications, and the project risks miscasting the researcher as "the chatbot guy" rather than a serious empirical development economist.

5. **Elevating Ukraine and Somalia as Symmetrical Testbeds:**
   - **Somalia (2021–2023):** Serves as the primary proof-of-concept for the *Response and Attribution* layer—disentangling an external food-price shock (Ukraine war), a multi-season drought, and local al-Shabaab insurgency.
   - **Ukraine (2022–Present):** Serves as the marquee testbed for *Preparedness and Recovery*—evaluating how digital state infrastructure (e.g., the *Diia* platform, mobile banking) facilitated rapid cash response, tracking agricultural disruption via remote sensing, and architecting post-conflict recovery and capital replacement.

6. **Advanced Technical Identity — Bleeding-Edge Applied Modeling:**
   Rather than defaulting to standard linear panel regressions, this agenda leverages cutting-edge data science that respects the complexity of compounded crises without alienating applied microeconomists:
   - **Double Machine Learning (DML):** Using debiased machine learning (Chernozhukov et al. / `EconML`) for high-dimensional nuisance parameter control and estimating heterogeneous treatment effects across vulnerable subpopulations.
   - **Spatiotemporal Network & Graph Models:** Modeling how physical shocks propagate through trade corridors, river basins, road disruptions, and displacement networks.
   - **Multi-Modal Data Fusion:** Ingesting continuous satellite rasters (Sentinel-1 SAR damage, CHIRPS rainfall, VIIRS night lights), discrete conflict point processes (ACLED), call detail records (CDR), and high-frequency market price feeds.

7. **Cross-Project Synergy: Academic Hub & Pedagogy with CTL:**
   The Academic Hub repository is formally integrated into the portfolio in partnership with Columbia's **Center for Teaching and Learning (CTL)**, focusing on AI-assisted pedagogy and classroom tutoring agents. Beyond pedagogy, this engineering work establishes a rigorous foundation in modern software architecture, automated testing, and CI/CD—directly feeding into the development of the open-source **Disaster & Conflict Analytics Toolkit (Project 04)** to professional software standards rather than fragile academic scripts.

8. **Math Thesis as an Agentic Research Lab Sandbox (Project 06):**
   The penalized-GLS omnibus normality test is maintained not as a career publishing priority, but as an experimental testbed for **agent-orchestrated research pipelines** in theoretical statistics and simulation. Interpreting these simulations deepens econometric and statistical fundamentals in a fun, low-stakes environment.

---

## 02. Core Intellectual Pillars

```
                     ┌─────────────────────────────────────────────────────────┐
                     │                   COMPOUNDED SHOCKS                     │
                     │  Natural Disasters (Drought, Flood) × Conflict (Invasion, │
                     │  Insurgency, Blockades) × Macro Disruptions (Prices)    │
                     └───────────────────────────┬─────────────────────────────┘
                                                 │
                        ┌────────────────────────┴────────────────────────┐
                        ▼                                                 ▼
        ┌───────────────────────────────┐                 ┌───────────────────────────────┐
        │ 1. RESILIENCE / PREPAREDNESS  │                 │   2. RAPID HUMANITARIAN       │
        │    (Ex-Ante)                  │                 │      RESPONSE (Ex-Post)       │
        │ - Risk communication          │                 │ - Satellite / drone damage    │
        │ - Pre-positioned cash safety  │                 │   assessments (SAR, Optical)  │
        │   nets & mobile money rails   │                 │ - CDR / mobile network traces │
        │ - Parametric / index insurance│                 │ - Targeted mobile cash payout │
        └───────────────┬───────────────┘                 └───────────────┬───────────────┘
                        │                                                 │
                        └────────────────────────┬────────────────────────┘
                                                 │
                                                 ▼
                               ┌───────────────────────────────────┐
                               │     3. RECOVERY & REBUILDING      │
                               │        (Medium to Long-Term)      │
                               │ - Capital replacement & liquidity │
                               │ - Return vs. permanent migration  │
                               │ - Reconstruction investment flows │
                               │ - Ukraine Recovery Architecture   │
                               └───────────────────────────────────┘
```

### Pillar I: Severe Data Scarcity as a Comparative Advantage
Mainstream empirical economics frequently bypasses active conflict zones because traditional administrative data and randomized household survey fieldwork are infeasible or dangerous. Leveraging alternative, multi-modal data streams—high-resolution satellite imagery (optical, SAR, thermal), drone mapping, nighttime lights (VIIRS), mobile phone network activity (CDR), crowd-sourced conflict logs (ACLED), and high-frequency market price feeds (WFP/FSNAU)—allows rigorous empirical evaluation where standard tools fail.

### Pillar II: Disaster-to-Conflict Mechanism Transfer
Natural disaster response has developed sophisticated ex-ante financing: forecast-based financing, parametric index insurance, and pre-arranged disaster liquidity. In conflict settings, aid remains overwhelmingly ex-post, slow, and reactive. We investigate:
- Can parametric triggers (e.g., rainfall deficits, sudden price spikes, displacement threshold alerts) automatically trigger emergency mobile cash disbursements in contested areas before acute famine or displacement takes hold?
- How do communication protocols and digital money systems need to be hardened when the hazard is human-induced (telecom blackouts, jamming, forced displacement) rather than natural?

### Pillar III: Rebuilding and Capital Replacement
Disasters and wars both destroy physical capital, decapitalize small businesses and farms, and induce distress sales. This pillar investigates how rapid post-shock liquidity injections, credit guarantees, and property restitution support permanent economic recovery versus perpetuating chronic poverty traps.

---

## 03. Dissertation Directions

### I. The 3R Economics of Compounded Disasters and Conflict
*The Flagship Spine*
Investigating how compounding shocks—where severe climate stress intersects active armed conflict—alter household survival strategies, displacement rates, and economic vulnerability. Uses Double Machine Learning and spatial network models to test whether social protection and emergency cash moderate the impact of environmental shocks when conflict is actively present.
- **Columbia Fit:** Alexander de Sherbinin (CIESIN / Climate-forced displacement), Macartan Humphreys (Political Science / Conflict economics), Jack Willis (Economics / Risk and social protection).

### II. Anticipatory Action & Financial Preparedness: Disaster-to-Conflict Transferability
*The Applied Policy & Mechanism Contribution*
Examining how mechanisms perfected in natural disaster management (forecast-based financing, index insurance, automated cash transfers) can be responsibly adapted to armed conflict settings. Focuses on the trade-offs between ex-ante preparedness investments versus ex-post humanitarian relief.
- **Columbia Fit:** Jack Willis (crop/weather insurance), Daniel Björkegren (digital finance & manipulation-robust targeting), Jeffrey Sachs & Nirupam Bajpai (digital infrastructure and e-governance).

### III. Data-Fusion & Measurement under Active Conflict
*The Open-Source Methods and Toolmaker Contribution*
Developing reproducible, open-source computational pipelines to harmonize spatiotemporal rasters (climate, satellite damage), discrete conflict events, mobile phone mobility proxies, and subnational displacement flows. Explicitly addresses reporting bias, missingness in insurgent-held territories, and spatial aggregation bias (MAUP).
- **Columbia Fit:** Daniel Björkegren, Data Science Institute (AI & Development), CIESIN data science teams.

### IV. Post-Shock Reconstruction & Capital Recovery: Evidence from Ukraine and Fragile Settings
*The Applied Recovery Horizon*
Studying the dynamics of economic rebuilding, capital replacement, and return migration following violent conflict. Uses Ukraine's rich public and remote-sensing data to analyze how digital social safety nets (*Diia*), emergency agricultural credit, and reconstruction investments prevent long-term distress and accelerate regional recovery.
- **Columbia Fit:** Eric Verhoogen (firm disruption, industrial recovery), Suresh Naidu (political economy and labor reconstruction).

---

## 04. Faculty Outreach & Institutional Alignment

Sequenced outreach strategy: Attend seminars first, hold exploratory informational meetings second, and present working papers/tools third.

### Tier 1 — Core Alignment & Advisory Committee Candidates
- **Alexander de Sherbinin** *(CIESIN, Columbia Climate School)*: Climate-forced displacement, spatial vulnerability data, disaster risk integration. Primary anchor for Directions I and III.
- **Daniel Björkegren** *(SIPA / AI and Development Initiative)*: Machine learning under distribution shift, manipulation-robust prediction, digital infrastructure in developing contexts. Primary anchor for Directions II and III.
- **Jack Willis** *(Economics, Barnard/SIPA)*: Micro-insurance, value-chain finance, social safety nets, risk management in agriculture. Anchor for Directions I and II.
- **Jeffrey Sachs & Nirupam Bajpai** *(Center for Sustainable Development)*: Digital infrastructure, ICT for development, policy scaling to multilateral institutions.

### Tier 2 — Conflict, Political Economy, and Recovery Adjacent
- **Macartan Humphreys** *(Political Science)*: Experimental methods in conflict and fragile states, institutional economics, natural resources.
- **Page Fortna** *(Political Science)*: Civil conflict, ceasefire dynamics, peace duration, humanitarian intervention political economy.
- **Eric Verhoogen** *(Economics / SIPA)*: Industrial development, firm recovery, market disruption, technology adoption.
- **Suresh Naidu** *(Economics / SIPA)*: Political economy, labor economics, institutional recovery.

### Tier 3 — Institutional Centers & Seminar Series
- **CIESIN (Center for International Earth Science Information Network):** Core geospatial and population displacement data community.
- **Saltzman Institute of War and Peace Studies:** Seminars on conflict dynamics, state fragility, and security.
- **Columbia Center for Teaching and Learning (CTL):** Partnership on AI pedagogy, tutoring agents, and research tool evaluation.
- **International Research Institute for Climate and Society (IRI):** Index insurance and climate risk forecasting.
- **Program on Forced Migration and Health (Mailman School):** Interdisciplinary public health and humanitarian displacement perspectives.
- **World Bank FCV & OCHA Centre for Humanitarian Data (HDX):** External practitioner bridges for tool deployment.

---

## 05. Revised Project Portfolio for Year One

Every project is self-contained, relies exclusively on public or standard academic data (no classified USAID data), requires no primary IRB fieldwork in Year 1, and directly builds toward the 3R framework.

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│ YEAR 1 PORTFOLIO ARCHITECTURE                                                                   │
│                                                                                                 │
│  [Project 01]                               [Project 03] (NEW)                                  │
│  Evidence Map: Anticipatory Action,         Disaster-to-Conflict Transferability:               │
│  Cash & Social Protection in Disasters      Working Paper on Applying DRR Mechanisms            │
│  and Conflict                               to Armed Conflict & Insecurity                      │
│        │                                          │                                             │
│        ▼                                          ▼                                             │
│  [Project 02]                               [Project 04]                                        │
│  Fused Empirical Multi-Shock Studies        Open-Source Disaster & Conflict                     │
│  • Somalia Three-Shock Case (Fall 26)       Analytics Toolkit (Python)                          │
│  • Ukraine Response & Recovery (Spring 27)  (Harmonizes Rasters, Points, Prices, Cash)          │
│        │                                          │                                             │
│        └────────────────────┬─────────────────────┘                                             │
│                             ▼                                                                   │
│                       [Project 06]                                                              │
│                       Math Thesis Rewrite: Agent-Orchestrated Statistics Lab                    │
│                       (Asymmetric Normality Test Validated on Panel Residuals)                  │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Project 01 — Evidence Map: Anticipatory Action, Cash Transfers & Conflict
- **Focus:** Systematic catalogue of RCTs and quasi-experiments evaluating cash transfers, social protection, and anticipatory action across two distinct bins: *natural disaster settings* vs. *armed conflict / fragile settings*.
- **Data:** 3ie, J-PAL, CEGA, Campbell Collaboration, WFP evaluation registries.
- **Deliverable:** Public interactive dashboard/catalogue + a published gap memo highlighting where disaster evidence has not been tested in conflict.
- **Timeline:** October – November 2026.

### Project 02 — Fused Subnational Multi-Shock Studies
- **Focus:** Empirical econometric study testing how compounding shocks translate into displacement and economic damage, and how social protection/cash transfers moderate those impacts.
  - *Phase A (Somalia Three-Shock Case Study):* Fall 2026. Separating the 2021–2023 Ukraine grain-import price shock, Horn of Africa drought, and al-Shabaab conflict on district displacement and food prices.
  - *Phase B (Ukraine Response & Recovery Scoping):* Spring 2027. Analyzing public data on infrastructure/agricultural damage, digital cash disbursements, and regional economic recovery.
- **Methodology:** Advanced spatiotemporal data fusion, Double Machine Learning (`EconML`) for heterogeneous treatment effects, and spatial network spillover models.
- **Deliverable:** November student seminar presentation (Lit + EDA + Pitch), working paper, reproducible notebook, and SusDev seminar presentation (April 2027).
- **Timeline:** September 2026 – April 2027.

### Project 03 (NEW) — Working Paper: Disaster-to-Conflict Transferability
*Replaces the dropped Chatbot Survey Pilot*
- **Focus:** A rigorous methods and policy paper analyzing the transferability of natural disaster response mechanisms (parametric index triggers, forecast-based financing, pre-positioned mobile money) to armed conflict and civil unrest. Identifies failure modes (telecom sabotage, reporting bias, targeting manipulation) and outlines resilient protocol designs.
- **Data:** Desk review, case comparative synthesis (e.g., Kenya/Somalia drought vs. Ukraine invasion cash rollouts).
- **Deliverable:** Working paper / methods note prepared for submission to a humanitarian or development policy journal (e.g., *World Development*, *Disasters*).
- **Timeline:** December 2026 – March 2027.

### Project 04 — Open-Source Disaster & Conflict Analytics Toolkit
- **Focus:** Reusable Python library for spatiotemporal aggregation and harmonization. Ingests gridded climate/damage rasters, point-level conflict events, boundary polygons, market prices, and aid distribution records into analysis-ready panel data.
- **Engineering Standard:** Backed by software architecture standards developed in Academic Hub (automated pytest suite, modular pipelines, clean package design).
- **Deliverable:** Public, documented Python package on GitHub (`pip`-installable) with tutorials and CLI.
- **Timeline:** December 2026 – January 2027 (built alongside Project 02, published once stable).

### Project 05 — Internal Scoping Note: Systems Dynamics & Non-Linear Recovery
- **Focus:** Internal theoretical memo exploring how complex systems concepts (tipping points, hysteresis, multi-dimensional poverty traps) provide theoretical foundations for why post-conflict recovery fails when multiple shocks compound. Written for advisor alignment.
- **Deliverable:** Internal 8–10 page conceptual paper.
- **Timeline:** March 2027.

### Project 06 — Math Thesis Rewrite: Agent-Orchestrated Statistical Lab
- **Focus:** Reworking the penalized-GLS omnibus normality test (roughness penalty with second-order differences and data-driven $\lambda$ selection) around its asymmetric-alternative power advantage. Serves as an experimental sandbox for multi-agent autonomous research workflows and a vehicle for deepening mathematical statistics fundamentals.
- **Data:** Simulated skewed distributions + empirical residuals exported from Project 02/04 panel models.
- **Deliverable:** Revised thesis manuscript and empirical validation note.
- **Timeline:** September 2026 – February 2027.

---

## 06. Coursework-Realistic Month-by-Month Roadmap

### September 2026 (Completed / Established)
- **[coursework]** Commenced PhD core sequence (Micro, Macro, Econometrics, Environmental Science).
- **[research]** Established reference manager and reading logs across disaster risk financing, conflict economics, and social safety nets.
- **[research]** Scoped Project 02 and formulated the Somalia three-shock case study design.
- **[outreach]** Attended opening SIPA SusDev and Saltzman conflict seminars.
- **[academic hub]** Deployed Academic and Research Hub infrastructure.
- **[math thesis]** Initiated R code refactoring for penalized-GLS test (second-order difference penalty).

### October 2026 (Current)
- **[coursework]** Problem sets and midterm preparation (primary time commitment).
- **[strategy]** Formulate and finalize this 3R Framework Revision (`Ground Truth - 3R Revision` and operational companion).
- **[research]** Pull raw Somalia datasets: WFP/FSNAU market prices, ACLED conflict points, UNHCR PRMN displacement records. Conduct initial exploratory data analysis (EDA).
- **[research]** Launch Project 01 (Evidence Map): begin cataloguing first wave of RCTs/evaluations across disaster vs. conflict settings.
- **[outreach]** First low-stakes informational meetings with de Sherbinin (CIESIN) and Björkegren (SIPA).
- **[ctl]** Initiate outreach to Columbia Center for Teaching and Learning (CTL) regarding AI tutoring and pedagogy fellowship.

### November 2026
- **[coursework]** Complete midterm examinations.
- **[presentation]** Deliver informal 30-minute student talk at the PhD student SusDev brownbag (Focus: Lit Review + Exploratory Data Analysis of Somalia shocks + Project Pitch). Low-stakes peer feedback loop.
- **[portfolio]** Assemble Project 01 (Evidence Map v1 notes/catalogue) as part of literature synthesis.
- **[ctl]** Submit application for AI pedagogy / research computing fellowship with CTL.
- **[outreach]** Informal coffee chats with Jack Willis and Jeffrey Sachs / Nirupam Bajpai; attend talks by Humphreys or Fortna.

### December 2026
- **[coursework]** Final examinations period (academic priority).
- **[winter break sprint]** With classes out of session, draft comprehensive outline and literature review for Project 03 (*Disaster-to-Conflict Transferability*).
- **[research]** Scope public data sources for Ukraine Phase B of Project 02 (World Bank damage assessments, Diia platform metrics, remote sensing crop/burn scars).
- **[outreach]** Send short end-of-semester update notes with links to Project 01 to Tier 1 faculty.
- **[math thesis]** Run agent-orchestrated simulation batch for automated $\lambda$ selection (GCV/REML).

### January 2027
- **[winter break sprint]** Write first full draft of Project 03 (*Disaster-to-Conflict Transferability* working paper).
- **[toolkit]** Package, document, and test Project 04 (*Disaster & Conflict Analytics Toolkit*) using modern software standards established in Academic Hub; publish to GitHub.
- **[research]** Ingest and harmonize Somalia and initial Ukraine data using Project 04 toolkit.
- **[outreach]** First meetings with Tier 2 faculty (Humphreys, Fortna, Naidu, Verhoogen) showcasing Project 01 and the Project 04 open-source toolkit.
- **[math thesis]** Run applied validation of normality test using empirical residuals from Project 02/04 panel regressions.

### February 2027
- **[coursework]** Spring semester coursework resumes.
- **[research]** Estimate Double Machine Learning (`EconML`) models and spatial network spillover regressions for Project 02.
- **[research]** Circulate Project 03 draft for peer/faculty comments.
- **[outreach]** Inquire with de Sherbinin / CIESIN and Tier 2 faculty regarding summer RA / pre-doc collaborations.
- **[math thesis]** Finalize revised math thesis manuscript; prepare seminar / conference submission.

### March 2027
- **[research]** Finalize Project 03 paper for journal submission (*World Development* or *Disasters*).
- **[research]** Complete unified draft of Project 02 incorporating both Somalia and Ukraine comparative insights.
- **[research]** Draft Project 05 internal scoping note on complex systems and non-linear recovery dynamics.
- **[outreach]** Second-round advisory fit discussions for Year 2 committee formation.

### April 2027
- **[presentation]** Present finalized Project 02 research paper at the formal Columbia Sustainable Development Seminar.
- **[portfolio]** Publish Project 02 working paper, Project 03 paper, and toolkit tutorials to personal website and GitHub.
- **[outreach]** Formalize funded summer research plans with faculty mentor.

### May 2027
- **[coursework]** Conclude Year 1 coursework; prepare for qualifying exams.
- **[retrospective]** Write an end-of-year retrospective documenting empirical progress, lessons learned, and refined dissertation questions.
- **[outreach]** Lock in primary dissertation advisor and second-year research trajectory.
