# Candidate sources for the desk audit (v1)

*Claude, 2026-11-10. A small sanity-check list for the retrospective desk audit described in the [review v5](Review%20-%20Cohesive%20Nexus%20Evidence%20Agenda%20Recommendation%20-%20v5.md) §7. Built from the repo's existing register plus about eight web searches and four page fetches. **Search-result summaries only: I did not open most documents, and two page fetches failed (below).** Treat every row as a lead, not a verified source. Superseding versions will be new files (`- v2`).*

**Tags.** **[V]** already verified in the repo. **[S]** reported by a web-search summary, not opened by me. **[I]** my inference or prior knowledge, unverified.

## What the audit needs from a case

From the owner's criteria (review v3 §6, v4 §7): (1) design documentation that traces evidence use and shows the alternatives considered; (2) monitoring and evaluation data across the programme's life; (3) a closeout evaluation traceable to design choices; (4) geographic specificity; (5) real scale; plus (6) an organization that still exists with similar projects ongoing or planned, and (7) preferably the cash vs. safety net family.

## Source families

| Source | What it may hold | Access (how checked) | Coverage | Fit and caveats |
|---|---|---|---|---|
| **World Bank projects and documents** (projects.worldbank.org; documents portal) | Project appraisal documents, implementation status reports, additional-financing papers, completion reports **[I: standard document types; not confirmed per project]** | Project pages found by search **[S]**; fetching a project page returned only the title (page is script-rendered), so the **documents tab is unverified** | Global | Strong lead for criteria 1–6. Appraisal documents typically carry results frameworks and sometimes options analysis **[I]**. Needs a browser or manual pass. |
| **IEG, "How the World Bank Supports Adaptive Social Protection in Crisis Response"** | A portfolio-level evaluation that may list projects reviewed and findings on design | Listed by search **[S]**; fetch returned **403** | World Bank ASP portfolio | A way to find well-documented ASP projects and to learn how evidence use is judged. Open manually. |
| **FCDO DevTracker** (devtracker.fcdo.gov.uk) | Business cases, annual reviews with results frameworks, completion reviews | A documents page for *Cash Transfers for Climate Resilience in Malawi* exists **[S]**; the snippet showed only navigation. An annual review excerpt lists an output score, risk rating, and links to the business case and results framework **[S]**. FCDO's operating framework requires an approved business case before programme start **[S]**. An ICAI review found over 90% of DFID business cases published 2017–2020 **[S: DFID, not FCDO]** | UK-funded programmes | Business cases usually contain an options appraisal **[I]**, which speaks to the owner's "ex ante alternatives" criterion. DevTracker pages may be in flux **[S]**. |
| **AidData archive of USAID evaluations** (usaid-archive.aiddata.org) | About 4,500 English-language evaluations, 2000–2023 (4,524 items) **[S]** | Reported as a preserved copy after the USAID Development Experience Clearinghouse site shut down in 2025; downloadable dataset v1.0 **[S]**. The page warns it is a curated subset **[S]** | USAID programmes | Good for **evaluations** (criterion 3). Weak for design documents and options. May fail criterion 6 if the funder no longer exists in similar form (owner's judgement). |
| **World Bank contract awards** (FinancesOne datasets; API at search.worldbank.org/api/contractdata) | Consultant-services and other contract awards under Bank-financed projects | Dataset pages found **[S]**: one lists query, API and bulk download, CC BY 4.0; coverage is prior-reviewed Bank-funded contracts under IDA/IBRD investment projects; **not exhaustive**; subcontracts excluded | Bank-financed projects | For the **support-seeking and pricing check** (review v4 §4). Project names may allow linking to the same projects as the design documents **[I]**. A 2019 mirror exists with unclear licence. Use the official source. |
| **SAM.gov contract opportunities** | US federal procurement notices (State, CDC and others) | Public CSV extract of *active* notices reported, about 70,000 notices, downloadable without login **[S, third-party listings]**. Archived notices may require the official API with a free key **[S, unconfirmed]**. Official GSA documentation not retrieved | US federal | Supports the planned procurement subproject, not the programme-documentation search. Historical depth unconfirmed. |
| **UNGM** contract awards | Awards by participating UN organizations | **[V]** in the register and source verification: most, not all, organizations publish; thresholds apply; some supplier names withheld | UN system | Procurement-side only. Coverage audit needed. |
| **IATI Datastore** | Organization-published activities, budgets, transactions, results | **[V]** in the register: as published, no harmonization; coverage varies | Global | Useful for **locating** programmes and linking funders to implementers, not for design reasoning. |
| **Not yet checked** | EU and ECHO documents and tenders, GIZ, IFAD, AfDB, ADB, UNDP, WFP's evaluation library, national government and NGO consortia | – | – | Next round. The owner's rule: organizations still active with similar projects. |

## A concrete lead worth noting

Search results list a **Somalia sequence** of World Bank projects: a *Shock Responsive Safety Net for Locust Response* project (P174065, approved 29 June 2020), an additional financing (P176369), the *Shock Responsive Safety Net for Human Capital Project* (P171346, closing date reported as 31 December 2025), and a third additional financing supporting the national platform **Baxnaano** (P181469) **[S]**. If the documents are as rich as is typical **[I]**, this looks like an emergency-cash-to-national-safety-net transition, which is the cash vs. safety net family, in the geography of the compound-shocks panel **[V: panel covers Somalia]**. It also overlaps the tracker's unrun *Option C: Baxnaano* access check **[V]**. **I have not opened any of these project documents.** Whether design papers cite external evidence, show options, or have closeout reporting is the thing to test. Because the first project's closing date was in December 2025, a completion report may be pending or just issued **[I]**.

## Scoring rubric for the documentation probe [P]

Score each candidate 0 (absent), 1 (partial), 2 (rich), with the document link as evidence.

| Criterion | What counts as rich |
|---|---|
| Design document with options | Alternatives named and compared |
| Evidence-use trace | External evidence cited and tied to a design choice |
| M&E data | Results framework plus repeated indicator reports across the programme's life |
| Closeout evaluation | Final report linking results to design |
| Geographic specificity | Sub-national targeting or locations |
| Support-seeking record | Consultants, technical assistance or advisory services identifiable |
| Organization status | Still active, with similar work ongoing or planned |

## Sanity-check result

- **The approach looks feasible at the listing stage.** At least two source families (World Bank, FCDO) plausibly hold design documents and results frameworks, and there is a cash-to-safety-net lead in the panel's own country. Procurement data for the support-seeking check exist in at least one open, licensed form, though they are incomplete.
- **Not yet established:** whether any candidate has the *evidence-use trace* and *options appraisal* the audit needs. That is the actual risk, and a documentation probe (below) answers it cheaply.
- **Tooling friction [V from this session]:** the World Bank project page and the IEG page could not be read by my fetch tool. The probe needs a browser pass, which the owner, Gemini or a browser-enabled session can do.
- **Not checked at all:** the list in the "not yet checked" row.

## Next steps

1. Run the documentation probe on three candidates (the Somalia sequence, one FCDO programme, one other) and score them. About half a day each.
2. Extend the list to the unchecked donor sites.
3. Keep the procurement scrape as its own later subproject.
