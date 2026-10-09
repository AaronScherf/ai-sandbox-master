# Research Projects Plan: Fall 2026 – Spring 2027 (3R Revision)

*Operational Project Roadmap — Revised Focus: Compounded Disasters, Conflict Economics, and the 3R Framework*

This document tracks the execution and publishing timeline for first-year doctoral research projects at Columbia SIPA (Sustainable Development). It operationalizes the strategic vision outlined in `ai-sandbox/research/independent-research/notes/Ground Truth - PhD Research Plan - 3R Revision.md`, while keeping `research_projects_plan_fall26.md` intact for comparison.

---

## Objective

Per the revised month-by-month timeline (September 2026 – May 2027, integrated alongside core doctoral coursework), deliver the following six interconnected deliverables:

1. **Academic Hub / Research Hub:** Knowledge management and automated literature harvesting infrastructure.
2. **Project 01: Evidence Map on Anticipatory Action, Cash & Conflict:**
   - Structured public catalogue of evaluations comparing disaster vs. conflict settings.
   - Published in November 2026 as the first public research artifact.
3. **Project 02: Fused Multi-Shock Empirical Studies:**
   - *Phase A (Fall 2026):* Somalia Three-Shock Case Study (Ukraine grain price shock vs. drought vs. al-Shabaab insurgency, 2021–2023). First draft in November.
   - *Phase B (Spring 2027):* Ukraine Response & Recovery empirical study, fusing digital social safety nets (*Diia*), remote sensing damage assessments, and regional economic recovery. Presented at SusDev seminar in April 2027.
4. **Project 03 (NEW): Disaster-to-Conflict Transferability Working Paper:**
   - *Replaces the dropped Chatbot Survey Pilot (avoiding IRB bottlenecks and ethical concerns).*
   - Rigorous methods and policy paper on transferring natural disaster risk financing (parametric triggers, forecast-based financing, mobile cash rails) to armed conflict. Drafted Dec–Jan, finalized March 2027.
5. **Project 04: Open-Source Disaster & Conflict Analytics Toolkit:**
   - Python library (`pip`-installable) built during Project 02's data harmonization to fuse rasters, conflict points, market prices, and aid distribution polygons. Published January 2027.
6. **Project 05: Internal Scoping Note on Systems Dynamics in Post-Shock Recovery:**
   - Conceptual memo connecting non-linear tipping points and poverty traps to compound shock recovery, prepared for advisor alignment in March 2027.
7. **Project 06: Math Thesis Rewrite (Asymmetric-Aware Omnibus Normality Test):**
   - Refactored penalized-GLS test with second-order roughness penalty and data-driven $\lambda$ selection. Applied validation using empirical residuals from Project 02/04 panel models in January–February 2027.
8. **Dissemination:** Publish all updates, working papers, and interactive tools on personal website and GitHub.

---

## Month-by-Month Milestones

### September 2026 (Completed)
- **Lit Lanes:** Opened three literature lanes (disaster risk financing & Anticipatory Action, conflict economics, social protection/cash in fragile settings); targeted 15–20 anchor papers per lane.
- **Scoping Project 02:** Scoped Project 02 and detailed the Somalia Three-Shock case study design (`Somalia Three-Shock Case Study.md`).
- **Outreach:** Attended opening SIPA Sustainable Development seminars, Saltzman Institute conflict talks, and CIESIN events.
- **Personal Website:** Launched site architecture, bio, project pages, and blog strategy.
- **Academic Hubs:** Published core codebase for Academic and Research Hubs on GitHub.
- **Math Thesis (Project 06):** Commenced R code refactoring (vectorization, deterministic covariance) and updated roughness penalty to second-order differences.

### October 2026 (Current)
- **Strategic Re-alignment:** Drafted and adopted the 3R Framework Revision (`Ground Truth - 3R Revision` and this operational roadmap), formally shelving the chatbot pilot.
- **Project 01 (Evidence Map):** Began cataloguing existing RCTs and quasi-experiments across disaster vs. conflict settings using 3ie, J-PAL, and WFP registries.
- **Project 02 (Somalia Case Study):** Ingested WFP/FSNAU market price data, ACLED conflict events, and UNHCR PRMN displacement records. Conducted midpoint data harmonization check.
- **Outreach:** Held initial informational meetings with Alexander de Sherbinin (CIESIN) and Daniel Björkegren (SIPA).
- **Website:** Published progress post on Academic and Research Hub architecture.
- **Math Thesis (Project 06):** Continued simulation testing of second-order difference penalty against heavy-tailed and skewed distributions.

### November 2026
- **Project 01:** Finalize and publish Project 01 (Evidence Map v1) as a public interactive dashboard and literature gap memo.
- **Project 02:** Complete first full draft of the Somalia Three-Shock empirical analysis.
- **Project 04 (Toolkit):** Begin extracting data cleaning and spatial buffering routines into the reusable Python package structure (`conflict-disaster-fusion`).
- **Research Statement:** Draft research-statement v0.1 reflecting the 3R framework.
- **Seminar Presentation:** Deliver informal 30-minute student talk at the SusDev seminar on multi-shock attribution in Somalia.
- **Outreach:** Informational meetings with Jack Willis and Jeffrey Sachs / Nirupam Bajpai; attend talks by Humphreys, Fortna, or Verhoogen.
- **Fellowships:** Submit application for AI pedagogy / research computing fellowship leveraging Research Hub tooling.

### December 2026
- **Project 03 (Transferability):** Draft comprehensive outline and literature review for the *Disaster-to-Conflict Transferability* working paper over the winter recess.
- **Project 02 (Ukraine Scoping):** Scope public and open-source data availability for Ukraine Phase B (World Bank RDNA damages, VIIRS night lights, agricultural burn scars, *Diia* cash assistance).
- **Outreach:** Send low-pressure end-of-semester update emails to Tier 1 faculty featuring the Project 01 Evidence Map link.
- **Math Thesis (Project 06):** Implement automated data-driven $\lambda$ selection (GCV/REML) and sharpen the manuscript around the asymmetric-alternative power gap.

### January 2027
- **Project 03:** Draft first complete manuscript of the *Disaster-to-Conflict Transferability* paper.
- **Project 04:** Finalize documentation, write automated test suites, and publish Project 04 (Disaster & Conflict Analytics Toolkit) on GitHub with accompanying tutorial.
- **Project 02:** Expand Project 02 into a dual-case comparative panel draft (Somalia + Ukraine) and circulate to faculty for feedback.
- **Outreach:** Conduct first round of Tier 2 faculty meetings (Humphreys, Fortna, Naidu, Verhoogen) showcasing Project 01 and the Project 04 open-source toolkit.
- **Math Thesis (Project 06):** Run applied validation of the normality test using empirical residuals exported from Project 02/04 regressions; perform finite-sample simulation study across $n \in \{50, 100, 500, 1000\}$.

### February 2027
- **Project 03:** Incorporate peer feedback and polish Project 03 for target journal submission (*World Development* or *Disasters*).
- **Project 02:** Finalize Ukraine econometric analysis and synthesize findings across both cases.
- **Outreach:** Discuss summer RA lines, pre-doc research, and potential field collaboration with target faculty (de Sherbinin, Humphreys, Willis).
- **Math Thesis (Project 06):** Complete final manuscript of the revised math thesis; identify statistics/econometrics conference opportunities.

### March 2027
- **Project 03:** Submit Project 03 to academic/policy outlet; publish preprint on website.
- **Project 05:** Draft internal scoping memo on complex systems, non-linear tipping points, and poverty traps in post-shock recovery for committee discussions.
- **Project 02:** Complete final revisions on the unified Project 02 paper.
- **Outreach:** Conduct second-round "decision" meetings with faculty regarding Year 2 dissertation committee and advisory fit.

### April 2027
- **Presentation:** Present the finalized Project 02 paper to faculty and peers at the SIPA Sustainable Development Seminar.
- **Publishing:** Publish Project 02 working paper and accompanying interactive replication notebooks on the personal website.
- **Summer Plans:** Formalize funded summer research plans with primary faculty mentor.
- **Portfolio:** Personal website now hosts four polished deliverables: Evidence Map, Transferability Working Paper, Unified Panel Study, and Open-Source Toolkit.

### May 2027
- **Coursework:** Complete first-year core doctoral sequences (Micro, Macro, Econometrics, Environmental Science).
- **Retrospective:** Write an end-of-year retrospective documenting empirical progress, lessons learned, and refined dissertation questions.
- **Advisor Fit:** Finalize primary dissertation committee chair and secondary members heading into Year 2.

---

## Linked Documents & References

- **Strategic Planning Memo:** `ai-sandbox/research/independent-research/notes/Ground Truth - PhD Research Plan - 3R Revision.md` (Primary strategic narrative).
- **Historical Baseline Memo:** `ai-sandbox/research/independent-research/notes/Ground Truth - PhD Research Plan.md` (Original admissions synthesis).
- **Somalia Case Study Specification:** `ai-sandbox/research/independent-research/notes/Somalia Three-Shock Case Study.md`.
- **Data Source Catalog:** `ai-sandbox/research/independent-research/notes/Data Sources - Climate Displacement Cash Conflict.md`.
- **Math Thesis Revision Strategy:** `ai-sandbox/research/independent-research/projects/math_thesis/rewrite/Gemini Plan for Thesis Revision.md`.
- **Website & Blog Strategy:** `ai-sandbox/research/independent-research/projects/blogging_strategy/website_blog_plan.md`.
