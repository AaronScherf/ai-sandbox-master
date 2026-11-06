# Pitch: Structured Literature Taxonomy & Research Hub Extension

*Automating Multi-Dimensional Evidence Mapping for Compounded Disasters and Conflict Economics*

- **Author:** Aaron Scherf (with Antigravity / Gemini Operator)
- **Date:** October 2026
- **Target Folder:** `ai-sandbox/research/independent-research/notes/`
- **Related Projects:** Project 01 (Evidence Map), Project 04 (Data-Fusion Toolkit), Academic Hub / Research Hub (CTL Pedagogy)

---

## 01. Executive Summary & Problem Statement

### The Failure of Flat Keyword Search in Applied Development Research
Traditional academic literature search (Google Scholar, standard Semantic Scholar, PubMed) relies on unstructured full-text keyword indexing and citation counts. Even modern open metadata aggregators like **OpenAlex** default to flat text searches or broad, single-dimensional topic classifications (e.g., CWTS Leiden topics).

For an applied researcher working at the intersection of **compounded disasters, armed conflict, and social protection (the 3R Framework)**, flat keyword search breaks down immediately:
1. **False Positives in Geography:** Searching for `"Somalia"` retrieves papers authored by scholars at Somali institutions, or papers that casually mention Somalia in a single sentence of the introduction, rather than empirical studies utilizing subnational Somali panel data.
2. **Conflation of Shocks vs. Interventions:** Searching for `"drought"` and `"cash transfers"` mixes studies on unconditional safety nets, studies on agricultural input vouchers, and purely diagnostic meteorological papers that offer no policy evaluation.
3. **Invisible Datasets:** Academic search engines do not treat datasets as first-class entities. A researcher cannot query: *"Show me all papers that fuse ACLED conflict events with CHIRPS rainfall rasters at the district level."*
4. **Methodological Ambiguity:** A query cannot easily isolate *Double Machine Learning*, *Synthetic Aperture Radar (SAR) change detection*, or *Staggered Difference-in-Differences* from purely descriptive qualitative commentaries.

### The Objective
To design and integrate an **open-source, reproducible taxonomic extraction pipeline** into the **Academic Hub / Research Hub**. This pipeline automatically parses academic abstracts and open-access PDFs into an orthogonal, multi-dimensional metadata schema—classifying each paper by its **empirical methods, datasets used, geographic scope, hazard types, intervention modalities, and primary outcomes**.

---

## 02. Landscape Analysis: Existing Solutions & Prior Art

| Platform / Framework | Core Architecture | Key Strengths | Critical Limitations |
|---|---|---|---|
| **Open Research Knowledge Graph (ORKG)**<br>*(TIB Leibniz / EU)* | Semantic Web RDF triples (`Paper` $\to$ `Research Problem` $\to$ `Method` $\to$ `Dataset` $\to$ `Result`). Open-source Python API & SPARQL endpoint. | • True property-based ontology.<br>• Native comparison tables.<br>• Open-source data dumps. | • Relies heavily on manual crowdsourcing.<br>• Biased toward computer science, physics, and engineering.<br>• Sparse coverage of development economics. |
| **3ie Development Evidence Portal**<br>*(International Initiative for Impact Evaluation)* | PICO-based Evidence Gap Maps (EGMs): *Intervention Modalities* $\times$ *Outcome Domains* $\times$ *Methodological Design* $\times$ *Fragility Status*. | • Gold standard in development policy (World Bank, USAID, J-PAL).<br>• Strict methodological appraisal (RCTs vs. quasi-experiments). | • Proprietary curation; slow update cycles.<br>• Excludes observational remote sensing, geospatial fusion, and macro price shocks.<br>• No programmatic API for custom literature scraping. |
| **Papers with Code**<br>*(Meta AI / Community)* | Standardized tracking of `Task` $\to$ `Method` $\to$ `Dataset` $\to$ `Metric`. | • Proven benchmark model for dataset-to-method linking.<br>• Open GitHub & HuggingFace datasets. | • Exclusively focused on machine learning and benchmark datasets; zero coverage of social protection or conflict economics. |
| **OpenAlex**<br>*(Our Research)* | Massive open graph (250M+ works) with REST API, citation graphs, and Leiden Topics. | • Fully open, fast, polite pool API.<br>• Reconstructible abstracts.<br>• Cross-disciplinary coverage. | • Country tags reflect *author affiliations*, not *study geographies*.<br>• Lacks distinct facets for datasets, empirical methods, or intervention types. |

---

## 03. Proposed Architecture: The Research Hub Taxonomy Extension

We can bridge the scale of OpenAlex with the structural rigor of 3ie and ORKG by embedding a **Pydantic-based LLM extraction layer** directly into the existing `academic-rag-model/` and Academic Hub pipeline.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ 1. HARVEST & INGESTION                                                                 │
│    • Query OpenAlex API / Semantic Scholar via lit_harvester.py                        │
│    • Ingest DOIs, Open Access PDFs (Unpaywall / EZProxy), and reconstructed abstracts  │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ 2. TAXONOMIC INFORMATION EXTRACTION (Pydantic / Instructor)                            │
│    Extract structured facets from Abstract + Methodology sections:                     │
│    ├── study_countries: list[str] (e.g., ["Somalia", "Kenya"])                         │
│    ├── spatial_resolution: str (e.g., "Admin 2 / District", "Gridded Raster 0.05°")     │
│    ├── empirical_methods: list[str] (e.g., ["Double Machine Learning", "Spatial DiD"]) │
│    ├── datasets_used: list[str] (e.g., ["ACLED", "CHIRPS", "UNHCR PRMN", "WFP HDX"])   │
│    ├── hazard_types: list[str] (e.g., ["Drought", "Armed Conflict", "Price Shock"])    │
│    ├── intervention_type: str (e.g., ["Unconditional Cash", "Anticipatory Action"])    │
│    └── primary_outcomes: list[str] (e.g., ["IDP Outflows", "Food Insecurity (IPC)"])    │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ 3. STORAGE & INDEX INTEGRATION                                                         │
│    • Write structured YAML frontmatter to local Markdown notes (`vault/papers/`)       │
│    • Sync metadata into DuckDB / SQLite catalog alongside existing vector embeddings   │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ 4. DISCOVERY & VISUALIZATION (Project 01 & Public Deliverables)                        │
│    • Interactive Evidence Gap Matrix: Method × Dataset × Country                       │
│    • Filterable CLI queries: e.g., `hub search --dataset ACLED --method DML`           │
│    • Public web dashboard export for personal website and Project 01 Evidence Map      │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### The Core Schema Definition
```python
from pydantic import BaseModel, Field

class EmpiricalStudyTaxonomy(BaseModel):
    doi: str
    title: str
    publication_year: int
    study_countries: list[str] = Field(description="Countries empirically evaluated in the study")
    geographic_scale: str = Field(description="National, Admin 1 (Region), Admin 2 (District), Village, Household")
    empirical_methods: list[str] = Field(description="Econometric or ML techniques (e.g., RCT, DiD, DML, SAR Change Detection)")
    datasets_used: list[str] = Field(description="Names of primary datasets analyzed (e.g., ACLED, CHIRPS, PRMN, VIIRS)")
    hazard_types: list[str] = Field(description="Shocks analyzed: Drought, Flood, Conflict, Food Price Inflation, etc.")
    intervention_type: str = Field(description="e.g., Anticipatory Action, Cash Transfers, Index Insurance, None/Observational")
    primary_outcomes: list[str] = Field(description="e.g., Displacement, Malnutrition, Yield, Market Prices")
    study_type: str = Field(description="Impact Evaluation, Observational Panel, Methodological, Systematic Review")
```

---

## 04. Strategic Synergies Across Your Doctoral Goals

```
                        ┌────────────────────────────────────────────────┐
                        │      ACADEMIC HUB TAXONOMY PIPELINE            │
                        │ (Automated Pydantic Extraction from OpenAlex)  │
                        └───────┬─────────────────┬──────────────────────┘
                                │                 │
            ┌───────────────────┘                 └───────────────────┐
            ▼                                                         ▼
┌────────────────────────────────────────┐       ┌────────────────────────────────────────┐
│   PROJECT 01: EVIDENCE MAP             │       │   PROJECT 04: DATA FUSION TOOLKIT      │
│ • Powers the public interactive matrix │       │ • Maps which datasets (ACLED, CHIRPS,  │
│   (Interventions × Hazards × Methods)  │       │   PRMN) are most frequently combined   │
│ • Generates the "literature gap memo"  │       │ • Defines input schemas based on real  │
│   automatically from missing cells.    │       │   empirical research practices.        │
└───────────────────┬────────────────────┘       └────────────────────┬───────────────────┘
                    │                                                 │
                    └───────────────────┬─────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│   DOCTORAL REPUTATION & PEDAGOGY (Columbia CTL Fellowship)                              │
│ • Delivers a concrete, reusable AI tool for the Center for Teaching and Learning (CTL)  │
│   showing how graduate students can map complex interdisciplinary literatures.          │
│ • Establishes software engineering rigor (pytest, modular architecture, open source)    │
│   over one-off academic script habits.                                                  │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

1. **Directly Produces Project 01 (Evidence Map):**
   Instead of spending hundreds of hours manually populating an Excel spreadsheet with 3ie-style tags, this pipeline automatically populates the matrix. The "literature gap memo" becomes a direct query over the empty intersections in your dataset (e.g., *"Zero papers combine Anticipatory Action with Double Machine Learning in Somalia"*).
2. **Defines the Schema for Project 04 (Data Fusion Toolkit):**
   By programmatically auditing 100+ empirical papers in fragile settings, the pipeline tells you exactly what spatial units and temporal frequencies are standard in the literature. You build your Python toolkit to solve the real bottlenecks identified across the literature.
3. **High-Signal Fellowship Deliverable for Columbia CTL:**
   Presenting a working, open-source tool that helps undergraduate and graduate students navigate complex, multi-method academic literatures provides an immediate, compelling project for the AI pedagogy fellowship application in November.
4. **Professional Software Architecture:**
   Treating this as an extension of the existing Research Hub enforces software engineering discipline—clean APIs, schema validation via Pydantic, test coverage, and documentation—reinforcing your identity as a builder of durable research infrastructure.

---

## 05. Implementation Steps & Milestones

1. **Step 1: Prototype Extraction Script (October 2026)**
   - Test the Pydantic schema on the 75 papers already harvested across Projects 01–05.
   - Validate extraction accuracy against known papers (e.g., checking that *Warsame et al.* correctly yields `study_countries: ["Somalia"]`, `datasets: ["ACLED", "FSNAU"]`, and `methods: ["Statistical Panel"]`).
2. **Step 2: Database Catalog Integration (November 2026)**
   - Store extracted facets in a lightweight local DuckDB/SQLite database inside `academic-rag-model/`.
   - Add automated YAML frontmatter injection for Obsidian / Markdown knowledge hubs.
3. **Step 3: Evidence Matrix Export (December 2026 / Winter Break)**
   - Generate a static HTML / Markdown matrix table for the Project 01 Evidence Map deliverable.
   - Package the extraction pipeline as a reproducible CLI command in the Research Hub.
