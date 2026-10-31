# ACLED Data Redistribution & Open-Source Research Terms: Findings & Compliance Analysis

**Document Status:** Complete Read-Only Legal & Compliance Assessment  
**Retrieval & Review Date:** 2026-10-31  
**Target Repository Context:** Open-source, reproducible academic research repository (Somalia compound shocks pilot, expanding to Sudan). Pipeline fetches ACLED conflict data via an academic-registered account (`myACLED` Research Tier), calculates aggregated panel counts (district-month / region-month), generates maps and econometric figures, and runs unit tests against synthetic schema fixtures.  
**Branch / Worktree:** `gemini/acled-terms` (`.worktrees/gemini-acled-terms`)  
**Relative Path:** `ai-sandbox/research/independent-research/notes/ACLED Terms - Redistribution Findings.md`  

---

> [!IMPORTANT]
> **Legal Disclaimer:** This report is a read-only research review and structural interpretation of ACLED's publicly published terms, agreements, and documentation as of 31 October 2026. It is compiled strictly for internal project governance and does not constitute formal legal advice. ACLED was not contacted during the preparation of this report.

---

## 1. Quoted Terms (Verbatim)

This section documents exact verbatim provisions from ACLED's current governing legal agreements, usage policies, attribution documentation, and API guides.

### 1.1 Core Agreements, Versioning, and Grant of Rights

* **Source URL:** `https://acleddata.com/eula/`
* **Governing Document:** End User License Agreement (EULA)
* **Effective Date / Version:** Last Updated: 8 July 2025
* **Retrieval Date:** 2026-10-31

> **Section 3.1. By Licensor.**  
> "Licensor hereby grants to Licensee, subject to the terms and conditions of this Agreement, a royalty-free, non-exclusive, non-transferable, non-sublicensable license to use the Licensed Content, and Platforms, and to develop, publish, and distribute materials incorporating the Licensed Content for non-commercial purposes, including internal analysis, planning, and training, or external use under specified conditions."

> **Section 3.1 (Derivative Materials Standard).**  
> "Licensee is not permitted to reproduce, republish, redistribute, or create derivative works from any of ACLED's Analysis, photographs, or videos. Licensee may only publish or distribute materials incorporating ACLED's data where such materials are transformative in nature and do not allow reverse engineering of the underlying dataset."

> **Section 3.1 (Insufficient Modifications).**  
> "It is not sufficient for Licensed Content to simply be supplemented, appended, excerpted, reorganized, or made available through Licensee's own dashboard."

> **Section 3.2. By Licensee.**  
> "Licensee hereby grants to Licensor, subject to the terms and conditions of the Agreement, a royalty-free, nonexclusive license to use, display, broadcast, and link to Licensee's use of the Licensed Content."

> **Section 5. Ownership of Intellectual Property.**  
> "Licensor retains sole and exclusive ownership of all right, title, and interest in and to the Site, Content, and Platforms. Licensee acknowledges that Licensee acquires no ownership or intellectual property rights whatsoever in the Licensed Content or Platforms (including any modifications or variations) and will not attempt to register them with any government office."

---

### 1.2 Access Gating, Credentials Sharing, and Direct Access Prohibitions

* **Source URL:** `https://acleddata.com/eula/`
* **Governing Document:** End User License Agreement (EULA)
* **Effective Date / Version:** Last Updated: 8 July 2025
* **Retrieval Date:** 2026-10-31

> **Section 3.3. Use Requirements and Restrictions.**  
> "All licenses granted are subject to Licensee's strict adherence to ACLED's Attribution Policy and Content Usage Terms. Licensee shall not (i) provide, permit, or allow direct access to any of the Licensed Content, except as permitted with respect to Derivative Materials, or (ii) share, permit, or allow sharing of access credentials to any Platforms. Notwithstanding the foregoing, Licensee may not, under any circumstances, provide, permit, or allow access to any of the Licensed Content and/or Platforms to Licensor’s competitors."

---

### 1.3 Confidentiality, Personnel Custody, and Data Return/Destruction

* **Source URL:** `https://acleddata.com/eula/`
* **Governing Document:** End User License Agreement (EULA)
* **Effective Date / Version:** Last Updated: 8 July 2025
* **Retrieval Date:** 2026-10-31

> **Section 13.1. Definition [of Confidential Information].**  
> "All information disclosed or made available by ACLED to the Licensee that the Licensee knows or should reasonably know to be confidential, which explicitly includes the Licensed Content, as well as information regarding ACLED's business and operations (such as platforms, sources, subscription packages, and pricing) unless it is or becomes publicly available through no breach by the Licensee."

> **Section 13.2. Use & Disclosure.**  
> "Licensee shall not disclose or make available any of the Confidential Information to any person or organization, except (1) with Licensee's Personnel who have a strict need to know and who are bound by written confidentiality obligations at least as protective as ACLED's terms... Licensee shall protect and maintain the strict confidentiality of Confidential Information, restricting its use to internal purposes only (unless expressly permitted otherwise regarding external use of Derivative Materials)."

> **Section 13.3. Return & Destruction.**  
> "Within thirty (30) days of the expiration or termination of the agreement (or upon earlier request by ACLED), the Licensee must—at ACLED's option—deliver or destroy all of ACLED's Confidential Information and documents embodying it, and ensure that all personnel do the same."

> **Section 12.3. Effect of Termination.**  
> "Upon termination: (i) Licensee shall immediately cease all use of Licensed Content and Platforms; (ii) promptly delete all Licensed Content in its possession or control; (iii) cease distributing and promptly delete all materials created using Licensed Content; and (iv) provide written attestation of compliance if requested."

---

### 1.4 Content Usage Responsibilities, Prohibitions, and Non-Compete Clauses

* **Source URL:** `https://acleddata.com/content-usage/` (and `https://acleddata.com/terms-of-use/content-usage/`)
* **Governing Document:** ACLED Content Usage Terms
* **Effective Date / Version:** Last Updated: 8 July 2025
* **Retrieval Date:** 2026-10-31

> **User Responsibilities (All users MUST):**  
> - "Use ACLED data, analysis, and platforms responsibly and in good faith."  
> - "Ensure accurate and faithful representation of ACLED's data, analysis, and methodology based on the Codebook and other public resources."  
> - "Clearly articulate and present any ways in which the data has been manipulated for specific research, analysis, or applications."  
> - "Contact ACLED directly (admin@acleddata.com) if there is any ambiguity regarding data or methodology, or if claims of misrepresentation arise, and promptly correct any identified inaccuracies."

> **Prohibited Uses (Users are PROHIBITED from using ACLED content to):**  
> - "Use the data or analysis in any manner that may harm, target, oppress, disparage, or defame any person, group, or data subject (or cause them to be harmed, targeted, oppressed, disparaged, or defamed)."  
> - "Damage ACLED's reputation, goodwill, or legitimate interests."  
> - "Create, develop, support, or benchmark any dataset, product, or platform that competes with or creates a functional substitute for ACLED's content, products, or platforms."  
> - "Provide unauthorized services to or for any other person, entity, or organization using ACLED content."  
> - "Data scraping is entirely prohibited; crawling the website or API is permitted strictly under the provisions of ACLED's robots.txt file."

> **EULA Section 10. Competitive Use Restrictions.**  
> "Licensee shall not use the Licensed Content, nor any information, ideas, structures, or insights derived from it, to develop, train, support, or assist in the development of any product or service that is competitive with Licensor’s products or services, including but not limited to datasets, APIs, or software tools that are similar in content, structure, or function."

---

### 1.5 Artificial Intelligence (AI) and Machine Learning (ML) Restrictions

* **Source URL:** `https://acleddata.com/eula/`
* **Governing Document:** End User License Agreement (EULA)
* **Effective Date / Version:** Last Updated: 8 July 2025
* **Retrieval Date:** 2026-10-31

> **Section 7.1. Restrictions on AI/ML/LLM Use.**  
> "Users are prohibited from using ACLED Content (in whole or in part) to train, test, develop, or improve any machine learning model, large language model, AI system, or similar technology in any manner that:  
> (i) Creates, enables, or contributes to a product, service, or output that functions as a substitute for ACLED Content, products, or services; or  
> (ii) Allows third parties to access, extract, or retrieve ACLED Content through such systems, directly or indirectly."

---

### 1.6 Attribution Policy, Naming Conventions, Citation Forms, and Visualizations

* **Source URL:** `https://acleddata.com/attribution-policy/`
* **Governing Document:** ACLED Attribution Policy
* **Effective Date / Version:** Last Updated: 20 September 2026
* **Retrieval Date:** 2026-10-31

> **Naming Conventions:**  
> - "Short Name: ACLED"  
> - "Full Name: Armed Conflict Location & Event Data (always use the ampersand '&' in the long version)."  
> - "Head Nouns: When nominalizing ACLED or adding a head noun, do not use 'project'; use 'organisation' or 'conflict monitor' instead."

> **Citation Requirements & Essential Elements:**  
> "ACLED must be clearly and prominently acknowledged as the source for both original data and any manipulated or added-to data. Proper acknowledgment requires:  
> - A footnote with the full citation, including a link to ACLED's website, or  
> - An in-line citation/acknowledgment stating that ACLED is the source (placed immediately preceding or following the figure or statistic).  
> All attributions (footnotes or in-text) must answer three essential questions:  
> 1. When did you access the data? (Because ACLED is a 'living dataset' updated weekly, specify the exact date the data was accessed or downloaded).  
> 2. What data did you use? (Indicate the specific filters applied, such as countries, time periods, event types, or actors).  
> 3. Have you manipulated the data? (Explicitly state if and how you made changes to the unit of analysis, categorization, or groupings)."

> **Data Visualizations, Maps, & Infographics:**  
> "Any data visualizations, maps, charts, or static images created using ACLED data must include a clear and prominent citation and a link to ACLED's website directly on the visualization itself (or within the key/legend). If a static file prevents an active link, note 'acleddata.com' as the source URL. If sharing images on social media, ensure the citation is not cropped out and tag ACLED's official accounts."

> **Academic Dataset Citation Forms:**  
> Primary Dataset Citation:  
> *"Raleigh, Clionadh, Andrew Linke, Håvard Hegre, and Joakim Karlsen. (2010). 'Introducing ACLED: An Armed Conflict Location and Event Dataset.' Journal of Peace Research, 47(5), 651–660."*  
> Updated Methodology / Scope Conditions Citation:  
> *"Clionadh Raleigh, Roudabeh Kishi, and Andrew Linke. (2023). 'Political instability patterns are obscured by conflict dataset scope conditions, sources, and coding choices.' Humanities and Social Sciences Communications, 25 February 2023."*

---

### 1.7 API Authentication and Credentials Management

* **Source URL:** `https://acleddata.com/api-documentation/`
* **Governing Document:** ACLED API Documentation & OAuth Integration Guide
* **Effective Date / Version:** Active API specification (myACLED OAuth 2.0 architecture)
* **Retrieval Date:** 2026-10-31

> **Authentication Mechanism:**  
> "ACLED supports two primary ways to authenticate API requests:  
> 1. Cookie-based authentication: Designed for browser-based access...  
> 2. OAuth token-based authentication: Designed for programmatic access (such as scripts, tools, or integrations in Python, R, or Power BI). This requires sending credentials via a POST request to generate an access token passed via an 'Authorization: Bearer <token>' header."

> **OAuth Token Endpoint Specification:**  
> Endpoint: `POST https://acleddata.com/oauth/token`  
> Header: `Content-Type: application/x-www-form-urlencoded`  
> Request Parameters:  
> - `username`: Registered myACLED account email  
> - `password`: myACLED account password  
> - `grant_type`: `password`  
> - `client_id`: `acled`  
> Bearer Token Validity: Typically 24 hours.

---

### 1.8 Access Tiers and the `myACLED` Transition

* **Source URL:** `https://acleddata.com/access/` (and `https://acleddata.com/myacled/`)
* **Governing Document:** myACLED User Tier Architecture
* **Effective Date / Version:** System transitioned from legacy static API keys to myACLED domain-verified tiers (2024–2025; active throughout 2025–2026)
* **Retrieval Date:** 2026-10-31

> **Tier Structure Summary:**  
> - **Open Tier (Public Access):** Registered with generic public email addresses (e.g., `@gmail.com`). Access limited to aggregated views, public reports, and interactive web tools (Explorer, CAST, Conflict Index); programmatic API access to event-level records is restricted.  
> - **Research Tier:** Users registering with verified institutional academic email addresses (e.g., university `.edu` domains). Provides access to research-level datasets and API querying; subject to a rolling **12-month lag/delay** on granular disaggregated event-level data.  
> - **Partner Tier:** Formal NGO and non-profit humanitarian partners. Removes the 12-month delay for operational response; grants access to timely weekly event updates.  
> - **Enterprise Tier (Commercial / Paid):** Private corporations, risk consultancies, or commercial users requiring expedited real-time event feeds and commercial exploitation rights.

---

## 2. Plain-Language Reading

> [!NOTE]
> **Interpretation Boundary:** This section represents our analytical reading and practical synthesis of ACLED's legal terms as applied to our specific open-source research pipeline. This is our project team's interpretation, **not** ACLED's official guidance or a binding legal warranty.

### 2.1 The 2025–2026 Access Model and Academic Researcher Standing

* **What Changed:** Historically, ACLED operated on a semi-open model where users requested a static `key` and appended `?key=...&email=...` to `api.acleddata.com`. Over 2024–2025, ACLED overhauled this into the **`myACLED` platform**, introducing domain-verified access tiers and migrating API authentication to OAuth 2.0 Bearer tokens.
* **Which Version Applies Today:** The active regime is governed by the **EULA dated 8 July 2025**, the **Content Usage Terms dated 8 July 2025**, and the **Attribution Policy dated 20 September 2026**.
* **Academic Standing:** An academic researcher registered with an institutional university email holds an account in the **Research Tier**. This permits non-commercial academic analysis and API access, but imposes a fundamental temporal constraint: **a rolling 12-month lag on disaggregated event-level data**. (This matches our observed Somalia raw export: downloaded on 2026-10-31 with a hard upper cutoff of 2025-10-31).

---

### 2.2 Public Repository Publication Assessment: The Five Artifacts

| Artifact | May Publish Publicly? | Governing Clause | Required Conditions & Limitations |
| :--- | :---: | :--- | :--- |
| **(a) Event-level records (or any subset)** | **STRICTLY NO** | EULA §§ 3.1, 3.3, 13.1, 13.2; Content Usage Terms | Raw event rows, whether the full 101,144 rows or a filtered subset (e.g., Somalia 2021–2023, Al-Shabaab events only, or selected columns), constitute *Licensed Content* and *Confidential Information*. The EULA explicitly clarifies that merely *excerpting*, *appending*, or *reorganizing* rows is **not sufficient** to make it an allowable derivative. Raw CSV/JSON files must remain private and untracked. |
| **(b) Aggregated counts (district-month, region-month)** | **YES** | EULA § 3.1 ("Derivative Materials"); Content Usage Terms | Panel matrices collapsing events into summary counts (e.g., total battles or fatalities per `admin2`-month) meet the threshold of **transformative materials** that **prevent reverse engineering**. A reader cannot reconstruct individual timestamps, precise GPS coordinates, actor interaction strings, or qualitative event notes from a monthly cell count. Permitted non-commercially, provided the manipulation is clearly documented and cited. |
| **(c) Maps and figures built from the data** | **YES** | EULA § 3.1; Attribution Policy | Analytical charts, choropleth maps, event-density figures, and regression coefficient plots are transformative non-commercial derivatives. **Mandatory condition:** The graphic itself (or its immediate legend/caption) must include a visible, prominent citation and the URL `acleddata.com`. (Note: You may *not* republish ACLED's own authored maps or infographics, per § 3.1). |
| **(d) Synthetic fixtures (schema & column names only)** | **YES** *(with care)* | EULA §§ 5, 10; Content Usage Terms | Fully synthetic mock files (e.g., 3 mock rows in a unit test fixture) that use ACLED's standard column headers (`event_id_cnty`, `event_date`, `admin1`, etc.) and categorical values (`Battles`, `Violence against civilians`) contain **zero real-world observations**. They are not a competing dataset or functional substitute for ACLED's data. They test code functionality. Permissible in open source, provided they contain no actual ACLED notes or proprietary content. |
| **(e) Code calling the ACLED API** | **YES** | EULA § 3.1; Content Usage Terms; Developer Docs | Ingestion scripts that query `https://acleddata.com/api/acled/read` or handle OAuth token retrieval are fully permissible open-source tools (similar to CRAN's `acled.api` and `acledR`). **Mandatory condition:** The code must read credentials dynamically from environment variables (e.g., `os.environ["ACLED_PASSWORD"]`); **no credentials may ever be committed**. |

---

### 2.3 Rules on Collaborators, Replicators, and Access Gating

1. **Internal Research Team vs. Third Parties:** Under EULA Section 13.2, raw Licensed Content may only be disclosed to "Personnel" (co-investigators, graduate research assistants) within the licensee's own institutional perimeter who have a strict need to know and are bound by confidentiality obligations.
2. **Replicators Must Hold Their Own Accounts:** Academic replicators outside your immediate research team are legally third parties. You **cannot** bundle the raw data snapshot into a replication archive (such as Zenodo, Harvard Dataverse, or OSF) without an explicit written license agreement from ACLED.
3. **The Clean Replication Protocol:**
   - The public repository provides complete transformation code, econometric scripts, and synthetic test fixtures.
   - The repository documentation (`README.md` / `data/README.md`) provides explicit instructions directing replicators to register for a free academic account on `myACLED`.
   - The repository's automated download script (`fetch_data.py`) prompts the replicator for their own myACLED credentials, pulls the data directly from the ACLED API, verifies the data schema/checksum, and executes the pipeline locally.

---

### 2.4 Citation Format, Required Notices, and Metadata Transparency

Whenever publishing papers, preprints, project documentation, or public repository readmes using ACLED data, the following three components must be satisfied:

#### 1. Organizational Nomenclature
* Use **ACLED** or **Armed Conflict Location & Event Data** (never substitute "and" for the ampersand `&`).
* If adding a descriptive noun, use **"organisation"** or **"conflict monitor"** (never refer to ACLED as a "project").

#### 2. The Three Mandatory Metadata Answers
Every in-text citation, table note, or data provenance block must explicitly state:
1. **Access Date:** The exact date the snapshot was retrieved (e.g., `Accessed 31 October 2026`).
2. **Applied Filters:** Geographic boundaries, date ranges, and event/actor filters (e.g., `Filtered for Somalia, event dates 1997-01-01 through 2025-10-31`).
3. **Data Manipulation:** The exact mathematical and geographic transformations applied (e.g., `Aggregated from raw point-level events into monthly counts at the district (Admin-2) level by the author`).

#### 3. Formal Academic Citations
* **Primary Citation (Standard in econometric references):**  
  > Raleigh, Clionadh, Andrew Linke, Håvard Hegre, and Joakim Karlsen. (2010). “Introducing ACLED: An Armed Conflict Location and Event Dataset.” *Journal of Peace Research*, 47(5), 651–660.
* **Secondary / Methodological Scope Citation (Recommended alongside primary):**  
  > Raleigh, Clionadh, Roudabeh Kishi, and Andrew Linke. (2023). “Political instability patterns are obscured by conflict dataset scope conditions, sources, and coding choices.” *Humanities and Social Sciences Communications*, 10, Article 74.

---

### 2.5 API Credentials in Public Repositories: Critical Threat Warning

* **The High Risk of the myACLED OAuth Flow:** Unlike older API architectures that used arbitrary alpha-numeric keys, the `POST https://acleddata.com/oauth/token` endpoint requires the user's **actual myACLED account password** and **account email**.
* **Contractual Consequence:** Committing credentials to a public Git repository is an immediate breach of EULA Section 3.3(ii) (*"share, permit, or allow sharing of access credentials to any Platforms"*) and Section 13 (*Confidentiality*). It exposes the researcher's institutional identity and invites immediate revocation of API privileges, account termination, and potential liability under Section 14 (Audit Rights).
* **Technical Enforcement:**
  - Add `.env` and `*.credentials` to `.gitignore`.
  - Provide a safe `.env.example` file containing:
    ```bash
    ACLED_EMAIL=your_institutional_email@columbia.edu
    ACLED_PASSWORD=your_myacled_password
    ```
  - Implement pre-commit hooks (such as `detect-secrets`) to prevent accidental commits of token strings or passwords.

---

## 3. Open Questions & Consultation Draft

### 3.1 Ambiguities Identified in Current Terms

While ACLED's documents are clear on raw event data (forbidden) and published research figures (permitted), three specific operational ambiguities affect an open-source econometric repository:

1. **Low-Count Aggregation Cells:** In a district-month panel, many cells will contain 0, 1, or 2 events. If an aggregated table disaggregates by event type (e.g., `Air/drone strike` count = 1 in district $D$ on month $M$) or includes aggregate casualty figures, could ACLED argue that a cell with $N=1$ allows a reader to infer the underlying event's existence and fatal impact, infringing the "reverse-engineering" clause?
2. **Scope of Competitive Restrictions on Test Fixtures:** EULA Section 10 prohibits using structures or insights derived from Licensed Content to develop any dataset or software tool that is "similar in content, structure, or function." While unit test fixtures are a universal software development norm, does ACLED view synthetic CSV fixtures replicating their column schema and categorical values as technically touching this clause?
3. **Replication Feasibility under the Rolling 12-Month Lag:** Because the Research Tier enforces a 12-month rolling window, a replicator executing the code 6 or 12 months after a paper is published might receive a revised or shifted historical snapshot if ACLED applies back-dated corrections or retrospective cleaning. How does ACLED recommend academic researchers publish stable replication packages for peer review without violating the raw data redistribution ban?

---

### 3.2 Specific Questions for ACLED Access & Licensing

When and if the project owner chooses to seek formal clarification, these exact questions should be posed:

1. *Regarding Panel Aggregation:* Does ACLED consider monthly district-level aggregate count tables (aggregating point events into monthly sums per district without lat/lon coordinates, notes, or event IDs) to be fully compliant "Derivative Materials" that may be published openly in an academic replication repository?
2. *Regarding Unit Test Fixtures:* Is it permissible to include a minimal, fully synthetic mock CSV fixture (e.g., 3 artificial rows using ACLED column headers and standard event-type names, but entirely fictitious coordinates, dates, and numbers) in an open-source test suite to ensure automated pipeline stability?
3. *Regarding Journal Replication Packages:* Given ACLED's strict prohibition on distributing raw Licensed Content to third parties, what is ACLED's approved best practice for authors submitting replication packages to academic journals (e.g., *Journal of Development Economics*, *American Economic Review*) that require publicly accessible data packages to verify empirical results?

---

### 3.3 Draft Consultation Email for Owner Review

> [!CAUTION]
> **DO NOT SEND:** The following draft is prepared exclusively for the project owner's review and records. Per the project instructions, Antigravity has not contacted ACLED and will not send this communication.

```text
Subject: Academic Replication & Derived Panel Guidance for University Research Project (Somalia/Sudan)
To: access@acleddata.com
Cc: licensing@acleddata.com

Dear ACLED Access and Data Compliance Team,

I am an academic researcher at [Institution / Columbia University] using ACLED data under an institutional myACLED Research Tier account for an academic research project studying compound climate and conflict shocks in the Horn of Africa (focusing on Somalia, and expanding to Sudan).

Our research methodology is committed to open science and computational reproducibility. We are preparing our codebase for eventual publication on a public GitHub repository and subsequent journal submission. We have thoroughly reviewed ACLED's End User License Agreement (EULA, updated July 2025), Content Usage Terms, and Attribution Policy (updated September 2026). To ensure our workflow strictly adheres to your redistribution and intellectual property standards, we write to request confirmation on three specific implementation points:

1. Publication of Derived District-Month Panel Aggregations:
Our automated pipeline aggregates point-level conflict events into monthly count matrices at the district level (Admin-2). The published output tables contain only district identifiers, calendar months, and total event counts / casualty sums. All raw geographic coordinates, exact event dates, qualitative source notes, actor interaction codes, and ACLED event IDs are stripped. We understand these aggregated tables to constitute permissible "Derivative Materials" that cannot be reverse-engineered into raw event data. Does ACLED confirm that publishing these district-month aggregate panel tables in a public academic GitHub repository is permitted?

2. Inclusion of Minimal Synthetic Test Fixtures:
To allow continuous integration and unit testing of our econometric pipeline without distributing any ACLED data, our test suite uses a tiny mock CSV fixture (3 rows) consisting entirely of fabricated, fictitious numbers and coordinates, shaped with ACLED's public column names and standard event-type strings. No real event records or source texts are included. Does ACLED confirm that such synthetic unit-test fixtures are acceptable and do not infringe on ACLED's structure or competitive use terms?

3. Approved Protocols for Academic Journal Replication Packages:
Many peer-reviewed economic and political science journals mandate data and code replication packages. Because ACLED terms prohibit redistributing raw Licensed Content to third-party replicators, our current protocol instructs replicators to register for their own free myACLED academic account and run an automated API retrieval script that ingests the data locally. Does ACLED endorse this "bring-your-own-account" API script approach as the standard compliance mechanism for journal replicators, or does ACLED offer an established academic archive exemption/deposit protocol for peer-reviewed replication packages?

All publications, visualizations, and documentation arising from this work will prominently credit ACLED, include direct links to acleddata.com, detail all snapshot dates and subset filters, and cite the foundational Raleigh et al. (2010) dataset paper.

Thank you very much for your time, guidance, and ongoing dedication to supporting academic research.

Sincerely,

[Project Owner Name]
[Academic Affiliation / Department]
[University Email Address]
```

---

## 4. Summary Matrix of Required Actions for Project 02

To maintain 100% compliance with ACLED's current terms:

1. **Keep Raw Data Private:** Retain `data/raw/ACLED Data_*.csv` strictly in local, git-ignored workspace storage. Ensure it is never staged, pushed, or bundled into a release.
2. **Commit Aggregations Only:** Verify that intermediate and final files saved to `data/derived/` are collapsed to district-month or region-month summary statistics prior to Git staging.
3. **Exclude Credentials:** Ensure pipeline scripts load `ACLED_EMAIL` and `ACLED_PASSWORD` via environment variables. Never hardcode credentials in code or Jupyter notebooks.
4. **Annotate Maps & Figures:** Apply the required watermark/caption (`Source: ACLED (acleddata.com), accessed 31 Oct 2026`) directly onto all generated cartographic and graphical artifacts.
5. **Document Replication Requirements:** Update repository documentation instructing external replicators to register at `acleddata.com` for their own API access credentials.
