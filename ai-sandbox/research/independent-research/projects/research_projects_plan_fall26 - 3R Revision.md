# Research Projects Plan: Fall 2026 – Spring 2027 (3R Revision)

*Operational Project Roadmap — Revised Focus: Compounded Disasters, Conflict Economics, and the 3R Framework*

This document tracks the execution and publishing timeline for first-year doctoral research projects at Columbia SIPA (Sustainable Development). It operationalizes the strategic vision outlined in `ai-sandbox/research/independent-research/notes/Ground Truth - PhD Research Plan - 3R Revision.md`, while keeping `research_projects_plan_fall26.md` intact for comparison.

---

## Objectives & Core Deliverables

Per the calibrated month-by-month timeline (September 2026 – May 2027, integrated realistically alongside the core first-year doctoral sequence), deliver the following interconnected projects:

1. **Academic Hub & Pedagogy Infrastructure (CTL Collaboration):**
   - Collaborate with Columbia's Center for Teaching and Learning (CTL) on AI-assisted pedagogy, classroom agents, and tutoring tools.
   - Establish high-standard software engineering practices (unit testing, CI/CD, modular package architecture) that directly underpin Project 04.
2. **Project 01: Evidence Map on Anticipatory Action, Cash & Conflict:**
   - Structured public catalogue of evaluations comparing disaster vs. conflict settings (3ie, J-PAL, WFP).
   - Assembled as desk research and reading synthesis; published in November 2026.
3. **Project 02: Fused Multi-Shock Empirical Studies:**
   - *Phase A (Fall 2026):* Somalia Three-Shock Case Study (disentangling Ukraine grain price shock, multi-season drought, and al-Shabaab conflict). Informal student brownbag presentation in November (Lit Review + EDA + Pitch).
   - *Phase B (Spring 2027):* Ukraine Response & Recovery empirical study, fusing digital social safety nets (*Diia*), remote sensing damage assessments, and regional economic recovery.
   - *Applied Methodology:* Double Machine Learning (`EconML`) for heterogeneous effects and spatial network spillover models. Presented at formal SusDev seminar in April 2027.
4. **Project 03 (NEW): Disaster-to-Conflict Transferability Working Paper:**
   - *Replaces the dropped Chatbot Survey Pilot (eliminating IRB bottlenecks and surveyor displacement concerns).*
   - Rigorous methods and policy paper on transferring natural disaster risk financing (parametric triggers, forecast-based financing, mobile cash rails) to armed conflict. Drafted during Winter Break (Dec–Jan), submitted in March 2027.
5. **Project 04: Open-Source Disaster & Conflict Analytics Toolkit:**
   - Python library (`pip`-installable) built during Project 02's data harmonization to fuse continuous rasters (SAR, optical, rainfall), conflict points (ACLED), market prices, and aid distribution polygons. Published January 2027.
6. **Project 05: Internal Scoping Note on Systems Dynamics in Post-Shock Recovery:**
   - Conceptual memo connecting non-linear tipping points, network cascades, and poverty traps to compound shock recovery, prepared for advisor alignment in March 2027.
7. **Project 06: Math Thesis Rewrite as an Agentic Statistical Lab:**
   - Refactored penalized-GLS test with second-order roughness penalty and data-driven $\lambda$ selection. Used as an experimental sandbox for multi-agent autonomous research orchestration and applied validation using empirical residuals from Project 02/04 panel models.
8. **Dissemination:** Publish all working papers, toolkits, and interactive visual summaries on personal website and GitHub.

---

## Month-by-Month Milestones

### September 2026 (Completed)
- **Coursework:** Began PhD core sequence (Micro, Macro, Econometrics, Environmental Science).
- **Lit Lanes:** Opened three literature lanes (disaster risk financing & Anticipatory Action, conflict economics, social protection/cash in fragile settings); targeted 15–20 anchor papers per lane.
- **Scoping Project 02:** Scoped Project 02 and detailed the Somalia Three-Shock case study design (`Somalia Three-Shock Case Study.md`).
- **Outreach:** Attended opening SIPA Sustainable Development seminars, Saltzman Institute conflict talks, and CIESIN events.
- **Personal Website:** Launched site architecture, bio, project pages, and blog strategy.
- **Academic Hubs:** Published core codebase for Academic and Research Hubs on GitHub.
- **Math Thesis (Project 06):** Commenced R code refactoring (vectorization, deterministic covariance) and updated roughness penalty to second-order differences.

### October 2026 (Current)
- **Coursework Priority:** Midterm exam prep and problem sets (primary academic focus).
- **Strategic Re-alignment:** Drafted and adopted the 3R Framework Revision (`Ground Truth - 3R Revision` and this operational roadmap), formally shelving the chatbot pilot.
- **Project 01 (Evidence Map):** Began cataloguing existing RCTs and quasi-experiments across disaster vs. conflict settings using 3ie, J-PAL, and WFP registries.
- **Project 02 (Somalia Case Study):** Ingest raw WFP/FSNAU market price data, ACLED conflict events, and UNHCR PRMN displacement records. Conduct initial Exploratory Data Analysis (EDA) and summary plotting.
- **CTL Collaboration:** Initiate outreach to Columbia Center for Teaching and Learning (CTL) regarding AI tutoring and pedagogy fellowship.
- **Outreach:** Held initial low-stakes informational meetings with Alexander de Sherbinin (CIESIN) and Daniel Björkegren (SIPA).
- **Math Thesis (Project 06):** Run initial test scripts for second-order roughness penalty against skewed distributions.

### November 2026
- **Coursework:** Complete midterm examinations.
- **Student Presentation:** Deliver informal 30-minute student talk at the PhD student SusDev brownbag (Focus: Literature Review + Exploratory Data Analysis of Somalia shocks + 3R Research Pitch). Purely peer-facing, low-stakes feedback loop.
- **Project 01:** Finalize and publish Project 01 (Evidence Map v1 notes/catalogue) as a public interactive dashboard and literature gap memo.
- **CTL Fellowship:** Submit application for AI pedagogy / research computing fellowship with CTL leveraging Academic Hub tools.
- **Outreach:** Informal coffee chats with Jack Willis and Jeffrey Sachs / Nirupam Bajpai; attend talks by Humphreys, Fortna, or Verhoogen.

### December 2026
- **Coursework Priority:** Final examinations period.
- **Winter Break Deep Work Sprint (Dec 15 – Jan 20):**
  - **Project 03 (Transferability):** Draft comprehensive outline and literature review for the *Disaster-to-Conflict Transferability* working paper over the winter recess.
  - **Project 02 (Ukraine Scoping):** Scope public and open-source data availability for Ukraine Phase B (World Bank RDNA damages, VIIRS night lights, agricultural burn scars, *Diia* cash assistance).
  - **Math Thesis (Project 06):** Deploy agent-orchestrated simulation batch for automated $\lambda$ selection (GCV/REML).
- **Outreach:** Send low-pressure end-of-semester update emails to Tier 1 faculty featuring the Project 01 Evidence Map link.

### January 2027
- **Winter Break Deep Work Sprint (Continued):**
  - **Project 03:** Complete first full draft of *Disaster-to-Conflict Transferability* paper.
  - **Project 04 (Toolkit):** Package, document, and test Project 04 (*Disaster & Conflict Analytics Toolkit*) using modern software standards established in Academic Hub; publish to GitHub with interactive tutorial.
  - **Project 02:** Ingest and harmonize Somalia and initial Ukraine data using Project 04 toolkit.
- **Outreach:** Conduct first round of Tier 2 faculty meetings (Humphreys, Fortna, Naidu, Verhoogen) showcasing Project 01 and the Project 04 open-source toolkit.
- **Math Thesis (Project 06):** Run applied validation of the normality test using empirical residuals exported from Project 02/04 panel regressions.

### February 2027
- **Coursework:** Spring semester coursework resumes.
- **Project 02 Modeling:** Estimate Double Machine Learning (`EconML`) models and spatial network spillover regressions for Somalia and Ukraine cases.
- **Project 03:** Circulate Project 03 draft for peer/faculty feedback and polish for submission.
- **Outreach:** Discuss summer RA lines, pre-doc research, and potential field collaboration with target faculty (de Sherbinin, Humphreys, Willis).
- **Math Thesis (Project 06):** Complete final manuscript of the revised math thesis; identify statistics/econometrics conference opportunities.

### March 2027
- **Project 03 Submission:** Submit Project 03 to target academic/policy journal (*World Development* or *Disasters*); publish working paper on website.
- **Project 05:** Draft internal scoping memo on complex systems, non-linear tipping points, and poverty traps in post-shock recovery for committee discussions.
- **Project 02:** Complete unified working paper draft of Project 02 incorporating both Somalia and Ukraine comparative insights.
- **Outreach:** Conduct second-round "decision" meetings with faculty regarding Year 2 dissertation committee and advisory fit.

### April 2027
- **Formal Seminar Presentation:** Present the finalized Project 02 paper to faculty and peers at the official Columbia Sustainable Development Seminar.
- **Portfolio Publishing:** Publish Project 02 working paper and accompanying interactive replication notebooks on personal website and GitHub.
- **Summer Plans:** Formalize funded summer research plans with primary faculty mentor.
- **Portfolio Status:** Personal website now hosts four polished deliverables: Evidence Map, Transferability Working Paper, Unified Panel Study, and Open-Source Toolkit.

### May 2027
- **Coursework:** Complete first-year core doctoral sequences; prepare for qualifying examinations.
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
