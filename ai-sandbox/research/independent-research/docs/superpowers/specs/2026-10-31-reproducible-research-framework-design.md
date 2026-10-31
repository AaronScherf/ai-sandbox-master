# Reproducible research project framework: design

Status: draft for owner review, 2026-10-31. Nothing here is built. Choices marked
**[Claude's call]** were not decided by the owner and can be overridden.

## 1. Intent

Independent research (`ai-sandbox/research/independent-research/projects/`) will
produce empirical studies, reusable Python libraries, and evidence/desk reviews. The
owner wants each to be reproducible by a non-technical outsider, adaptable to other
countries/datasets/questions, safe to publish, and shaped from day one to plug into
a larger structure (the literature-review pipeline and the 3ie development-data
taxonomy, which is still being finalized).

The first pilot is Project 02 (Somalia compounded shocks), with Sudan as the test of
portability. Codex has already landed an intake scaffold there (`8fa6f6c`): source
register, hash inventory, protocol with verification states, release gate. This
design builds on it and does not replace it.

## 2. Goals

1. **Reproduce.** With the same data access, one command reproduces every table and
   figure of a study repo.
2. **Adapt.** A user can change parameters (geography, dates, event filters, climate
   baseline, robustness settings) in a config file, or swap in a different dataset of
   the same kind, and re-run processing, fusion, analysis, and visualization.
3. **Compare.** Methodology is fixed per study design, so runs for different
   countries are directly comparable, including nested/pooled tests on common data.
4. **Standalone.** Every project is its own GitHub repo, cloneable and testable alone,
   with a fast test suite independent of the monorepo.
5. **Plug-and-play libraries.** Library repos install with pip and depend on no study repo.
6. **Restricted data stays restricted but reachable.** Non-shareable data is obtained
   by pinned, scripted queries with expected hashes/schemas; tests use synthetic fixtures.
7. **Agent-accessible.** A human or an AI agent can read, validate, and modify a project
   safely. Human readability stays primary.
8. **Cost-transparent.** Paid AI and heavy compute are declared, estimated, and have
   free or cheaper alternatives named.
9. **Rights-safe.** No sensitive, confidential, or copyrighted material is committed;
   licensing is explicit.
10. **Fits a meta-structure.** Each repo carries machine-readable metadata (3ie taxonomy
    tags, sources, literature links, sibling repos) that a registry assembles.
11. **Knows what it is for.** Every project declares its purpose, audiences, publication
    strategy, and confidentiality class from inception, and those declarations drive the
    deliverables, the communication plan, and what an agent may share.
12. **Plans its end products.** Each project declares its final deliverables (paper, slides,
    interactive app, report, dashboard); the one-command reproduce builds them.
13. **Communicates as it goes.** Project-to-website-page and progress-post material is
    produced from the project's own metadata, so science communication is not an afterthought.
14. **Adaptable to future kinds.** New project kinds (web apps, consulting corpus analysis,
    others not yet imagined) are added as templates on the common core without changing it.
15. **Derivable.** An agent following explicit rules can build a version for another
    audience (e.g. public from academic) without leaking restricted material.

## 3. Non-goals and anti-goals

- Not a general workflow engine, and not a replacement for the econometric design of any study.
- Not hosting data. No OSF project hub (see 5.1).
- No automatic publishing. The communication pipeline drafts and stages website pages and
  posts; publishing, deploying, or submitting needs the owner's explicit go-ahead each time.
- Future project kinds (section 4) are designed for, not built, in this scope.
- Anti-goals (would make it a failure even if it runs): sprawling overlapping systems
  written by agents; hidden coupling to the monorepo; hard-coded file paths; silent
  cross-source substitutions; a replication that needs a paid subscription without saying so.

## 4. Project kinds

| Kind | Examples | Contract |
| --- | --- | --- |
| Study repo | 02 Somalia, later Ukraine | cookiecutter-data-science-style layout; fixed study design; per-run instances |
| Library repo | 04 data-fusion toolkit | pip-installable, standalone, SemVer, own docs/tests; study repos pin it as a dependency |
| Evidence/desk repo | 01 evidence map, 03 transferability | no PDFs; citation manifest (DOI/OpenAlex ID) plus a shared Zotero group library so others fetch the same sources |

Anticipated future kinds, not built now (**[Claude's call]** examples to test the design):

| Kind | Sketch |
| --- | --- |
| Interactive app repo | Ingests data or a study repo's published results and presents a non-technical explorer; deliverable is a built app; data connection declared as a role like any other input |
| Consulting/corpus repo | Takes a project corpus (design and implementation documents, evaluation reports, monitoring data) and analyzes it; usually confidential class, so private repo, no public push, redaction rules for derivatives |

**Extensibility rule.** The common core (section 5) must stay kind-agnostic: charter,
descriptors, role-based inputs, manifests, profiles, deliverables, derivative rules,
`AGENTS.md`, locked environment, CI. A kind is only a template plus its own schema
additions and deliverable types. If a new kind forces a change to the core, that is a
design decision for Claude and a schema version bump, not an inline patch.

All kinds share a **common core** (section 5) and add a small kind-specific layer.
A template tool (copier or cookiecutter, **[Claude's call]**: copier, because it can
update existing repos when the template changes) generates the repo.

## 5. The shared standard

### 5.1 Alignment with existing standards (verify before adopting; most are from memory)

TIER Protocol 4.0 and the Social Science Data Editors' README template (study layout and
replication README); Frictionless Data Package for data descriptors; `CITATION.cff` plus
GitHub-to-Zenodo releases for DOIs; PyPA `pyproject.toml`, SemVer, changelog for
libraries; OSF Registries or the AEA registry for preregistration; W3C PROV / RO-Crate
as vocabulary for run manifests if cheap; the Social Science Reproduction Platform as an
external audit. OSF Projects stops accepting new projects on 2026-11-16 and goes
read-only 2027-02-19, so OSF is not used as the hub (Registries/Preprints are unaffected).

### 5.2 Components (each has a published, validated schema)

- **Data descriptor** (sidecar per source/file, Frictionless-based): what the data is,
  provider, query that produced it, variable meanings and units, geography and period,
  reuse terms, and "what to look for in another geography". Extends the existing
  `data/source_register.csv`.
- **Role-based data references.** The pipeline asks for roles ("conflict_events",
  "rainfall", "prices"), not filenames. A thin adapter per role locates files and maps
  columns to a canonical schema. Renames (e.g. `lat_long` vs separate `lat`/`lon`) are
  cosmetic mappings and are logged only.
- **Step graph.** Steps declare inputs/outputs so dependent fetches work (conflict
  coordinates feed a satellite query) and changed inputs trigger reruns. The tool
  (Make, Snakemake, DVC, or a small runner) is chosen in the pilot **[open: builder]**.
- **Study instance config.** Geography, dates, parameter overrides. Defaults carry over
  unchanged when only the data changes; every default is adjustable and recorded.
- **Run manifest.** Code version, resolved parameters, input hashes, schema version,
  resolved package versions. Two runs are comparable only if manifests show the same method.
- **Harmonization record** (two tiers). Cosmetic changes (rename a column/file) are
  logged. Structural changes (different provider, changed category definitions, e.g.
  PRMN to IOM DTM) block the run until a written record exists: how the sources differ,
  decision, rationale, affected outputs. Manifests link to these so source swaps can be
  analyzed later as a bias source.
- **Verification states** on results: proposed, source-verified, fixture-tested, run on
  acquired data, independently reproduced (already in Project 02's protocol).
- **Compute profile** (`compute.yaml`): local limits (no GPU assumed), backend
  preference order, and per-backend access and cost notes. Backends are an open list:
  local, Google Earth Engine, institutional clusters (e.g. Columbia HPC), cloud VMs
  (e.g. GCP), others. Shared schema and defaults live in one place; repos override
  only differences. A step that exceeds the profile says so before running and prints
  a cost estimate when billable.
- **Agent profile** (`agents.yaml`), modeled on the owner's agent rules: which AI
  subscriptions the user has (if any); local vs subscription processing preference;
  when, if ever, to offload to token-priced APIs (e.g. Gemini), with a spend ceiling
  and warn-before threshold (owner's standing rule: warn and get go-ahead above $1).
- **Agent instruction files.** A generic `AGENTS.md` in every repo (commands, module
  boundaries, what not to touch: raw data, credentials, locked specs; how to adapt to a
  new country). Optional `CLAUDE.md` / `GEMINI.md` per repo link to `AGENTS.md` and
  add only agent-specific notes. Plus: schemas for validation, a dry-run mode that
  prints planned steps and needed inputs, errors that name file/column/expected value,
  and a short "adapt this study to a new country" runbook readable by humans or agents.
- **Reproducible environments.** Locked dependencies (`uv.lock` or equivalent
  **[Claude's call]**: uv), pinned Python version, optional devcontainer/Docker image,
  Python version and platform last verified recorded, CI that builds from the lockfile.
  Libraries keep loose compatible ranges in `pyproject.toml` and test across a version matrix.
- **Rights and safety.** Code license explicit; data and derived-output licenses
  stated per descriptor; raw data, credentials, and ACLED records never committed
  (ACLED redistribution terms need review); secret scanning in CI; the AI-cost section
  of the README (what needs a subscription, price, free/cheaper alternative).
- **Project charter** (`project.yaml`, also carries the meta-structure metadata: 3ie
  taxonomy tags, data sources, literature review link, sibling repos; taxonomy fields
  are placeholders until it is final). Declared at inception:
  - *Purpose and type:* academic publication, dissertation chapter, independent
    consulting, open-source tool, or side project.
  - *Confidentiality class:* public, private-until-release, or confidential. This
    governs repo visibility, what may be committed, and what a derivative may contain.
  - *Stakeholder/audience analysis:* who will use or read this (academics, practitioners,
    funders, general public), what each needs, their technical level, and the channel.
  - *Publication strategy:* target venues or none, preregistration plan, timing.
  - *Communication plan:* what is shared at each stage (inception, data, preliminary
    results, release) and for which audience.
- **Deliverables spec** (in `project.yaml`): each final product with its audience,
  format, and build step. Examples: LaTeX paper to PDF, slide deck, regenerated figures,
  interactive app wired to its data source, dashboard, policy brief. The one-command
  `reproduce` builds everything listed. A deliverable aimed at a non-technical audience
  carries an interpretability requirement (plain-language summary, uncertainty shown
  without jargon) that analysis and figure steps must meet, so this end goal shapes the
  earlier steps and is not added at the end.
- **Derivative rules** (a section of `AGENTS.md` backed by fields in `project.yaml`):
  how an agent adapts a project for another audience (e.g. academic to public).
  - *May reuse:* public-class material and aggregated results.
  - *Must exclude or redact:* restricted data, confidential-class content, unreleased
    results, copyrighted text.
  - *Must do:* link back to the source project and its version, keep claims within the
    verification state of the underlying result, and stop for owner review before any
    publication.
- **Communication log and website hook.** The charter's audience and communication
  fields generate drafts for a project page (title, summary, status, links, resources)
  and progress posts, kept in the repo (`comms/`) in the format the personal-website
  repo expects. The website is a separate repo with its own agent guidance; per the
  routing convention, Gemini drafts website text and Claude decides structural
  questions. Drafts are staged for the owner and never published automatically.
- **Literature/AI cost.** The literature pipeline is the only paid-AI-heavy part. Its
  outputs ship as a citation manifest so replicators never need to re-run it; the
  pipeline stays available with cost and alternatives documented.

### 5.3 Monorepo relationship

Each project is a separate GitHub repo. The monorepo keeps a **registry file** (URL,
pinned tag, metadata path per repo) and an optional script that clones all repos into a
gitignored workspace folder. No submodules (owner's security preference). Dependencies
between repos are declared in each repo's `pyproject.toml` as a PyPI version or a
git-URL pinned to a tag, with install steps in its README and `AGENTS.md`.

Known defect to fix first: `berkeley_thesis/wheat_yield_prediction_gee` and
`math_thesis/Novel-Omnibus-...` are committed as gitlinks (mode 160000) with no
`.gitmodules` (added by auto-commit `c17c1264`, 2026-09-15). A fresh clone gets empty
folders. A separate handoff investigates; expected fix is `git rm --cached`, gitignore,
and registry entries.

## 6. Scope and phases

Two deliverables: **A**, the shared standard and templates; **B**, the Project 02
pilot extracted to its own repo, with a Sudan portability test.

Agent routing follows `docs/AGENT_ROUTING.md`. All writes follow the worktree procedure
(one branch/worktree/writer per task). Claude holds design and review; Codex builds
well-specified pieces; Gemini operates pipelines, reads at scale, and drafts docs.

| # | Phase | Output | Owner | Notes |
| --- | --- | --- | --- | --- |
| 0 | Gitlink investigation and fix | cleaned index, registry stub | Codex (after Claude approves the investigation report) | Already has a handoff prompt |
| 1 | Verify standards (TIER, Frictionless, Data Editors README, RO-Crate, copier) and the 3ie taxonomy state | short findings note | Gemini (large-context reading), Claude reviews | Resolves the "from memory" claims in 5.1 |
| 2 | Schema design: descriptor, config, manifest, harmonization record, compute and agent profiles, project charter (purpose, confidentiality, audiences, publication strategy), deliverables spec, derivative rules | schema files + rationale | **Claude** | Schema changes are Claude's per routing doc |
| 3 | Template repo (copier): layout, lockfile, CI, license, AGENTS.md, issue templates | template repo | Codex, from Claude's spec | Claude reviews |
| 4 | Validators and CLI skeleton (schema checks, dry-run, manifest writer) | small package | Codex, from Claude's spec | Concise modules; Claude code review |
| 5 | Pilot architecture: step graph tool choice, adapter interface, harmonization gate | design note | **Claude** | Architecture |
| 6 | Pilot implementation: extract 02, adapters for ACLED, PRMN, prices, CHIRPS, synthetic fixtures, tests | 02 repo | Codex, in slices from Claude's spec | Owner supplies accounts/credentials |
| 7 | Acquire restricted data; run on real data | verified outputs | Owner acquires; Gemini operates documented runs | Warn above $1 |
| 8 | Docs: replication README, runbook, AI-cost section, "new country" guide | docs | Gemini drafts, Claude reviews | No invented results |
| 9 | Sudan portability test; harmonization record for the PRMN-to-alternate-source swap | comparison + record | Gemini runs; **Claude** judges the harmonization | Judgment, owner sign-off |
| 10 | Library template and Project 04 split | library repo | Codex scaffold, Claude architecture review | After pilot shows what 02 needs |
| 11 | Security/code review; external reproduction attempt (SSRP-style, clean machine) | review report | **Claude** review; owner or a volunteer reproduces | Includes secret and licensing check |
| 12 | 3ie taxonomy and literature-pipeline hooks | filled meta fields, citation manifest export | Claude design; Codex implement | **Blocked** until taxonomy is final |
| 13 | `reproduce` builds the declared deliverables for the pilot (figures and LaTeX paper PDF only) | working build target | Codex, from Claude's spec | App and slide builds are designed for, not built |
| 14 | Communication hook: generate project-page and progress-post drafts from `project.yaml` | draft generator + one sample | Claude designs format with the website repo's guidance; Gemini drafts text; Codex implements generator | Needs the website agent guidance (website PR #3) present; never auto-publishes |
| 15 | Derivative test: an agent builds a public version of the pilot from the academic version using the derivative rules | test report | Gemini runs; **Claude** reviews for leaks | Verifies the rules actually work |
| 16 | Future-kind check: sketch templates for an interactive app and a consulting-corpus repo against the core | gap list; core changes only if needed | **Claude** | Design exercise, no build |

Phases 2 to 5 are sequential. 3 and 4 can run in parallel worktrees once 2 is approved.
Anything a delegated agent finds that needs a design decision goes back to Claude.

## 7. Constraints

- Public monorepo: no secrets (`ai-sandbox/.env`), no copyrighted source material.
- No GPU or large machine assumed; heavy steps declared and routed via the compute profile.
- Stage explicit paths only; one writer per worktree.
- Raw data is immutable; cleaning reads `data/raw/` and writes `data/derived/`.

## 8. Left to the builder

Step-graph tool; exact descriptor field list; copier vs cookiecutter details; CI provider
settings; how adapters declare column mappings; registry file format; which schema
validator library.

## 9. Open items for the owner

- Whether `docs/` placement (this file) is right for research-specific designs.
- 3ie taxonomy final shape and the literature pipeline's export interface (phase 12).
- ACLED redistribution terms for any shared derived output.
- Which institutional compute (Columbia HPC) the owner can actually access and at what cost.
- Confidentiality classes: the three proposed (public, private-until-release, confidential)
  may need refining for consulting clients under NDA.
- How far the charter's stakeholder analysis should go (a short structured list per
  audience is the proposal; a full stakeholder-mapping method is not).
- The pilot's deliverables: paper and figures are assumed; confirm whether slides belong in v1.
