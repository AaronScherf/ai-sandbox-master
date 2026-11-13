You are a Gemini (Antigravity) session. Your task is a READ-ONLY-for-existing-files literature check. Write only the new output files named below. Do not edit, rename or delete any existing file, and do not commit or push without reporting to Aaron first.

Before any write, follow docs/WORKTREE_WORKFLOW.md at the monorepo root: use your own branch and worktree (for example `gemini/nexus-novelty-check`), not the Codex worktree `codex-nexus-presentation-strategy-v3`.

Goal
Aaron is planning a PhD research agenda on how external causal and other evidence can be found, assessed, adapted and used for decisions in prolonged or recurrent crises and the humanitarian-development transition. The agenda has three research questions. For EACH, find out whether it already has a well-defined answer in past research, so Aaron knows whether it is a useful contribution or already done. "Not novel" is a valuable result. Do not try to make the questions look novel.

Read first (in the main checkout; the review files may exist only in the Codex worktree until landed, so ask Aaron for the path if you cannot find them)
- Review v5: notes/00_overview-and-strategy/02_agenda-strategy-and-reviews/Review - Cohesive Nexus Evidence Agenda Recommendation - v5.md (pipeline, gates, validation definitions)
- v3 sections 2 and 3 for the RQ definitions and the value-of-information framing
- notes/00_overview-and-strategy/02_agenda-strategy-and-reviews/Humanitarian Evidence Agenda - Source Verification.md (the standard for what counts as a verified claim)
- notes/03_rct-transportability/Follow-up - Data Availability and Transportability Critique.md (transportability background)
All paths are under ai-sandbox/research/independent-research/.

The three research questions (run order)
- RQ1, knowledge audit: what does a decision-maker already know or have access to, and would new evidence (or a more accessible version of existing evidence) be marginally worth the time, effort and cost to collect, analyze and understand? Includes revealed demand for evidence support (do decision-makers hire consultants or use headquarters support, and when).
- RQ2, decision space: what are the constraints and discretion of a specific decision, and which interventions would be considered under which scenarios? Method idea: participatory DAG mapping plus scenario planning, with a log-frame per scenario, a data inventory per node, and thresholds that force decisions.
- RQ3, transfer: given a decision space, which external sources are informative, how far are they from the target setting (spatial, temporal, institutional, market, treatment version, population, interference), and what output does the evidence support (target estimate, bounds, mechanism hypothesis, or no inference)? Plus a proposed test: pre-register a transport prediction, implement with evaluation built in, and compare the realized effect with the prediction.

Sub-questions to search (these are starting points, not a ceiling)
RQ1
1. Has value-of-information analysis (expected value of perfect or sample information) been applied to decisions about commissioning evidence in humanitarian or development programme design? It is established in health economics; is the transfer to this setting done?
2. Existing frameworks for auditing a decision-maker's evidence needs and evidence use (evidence-use research, research uptake, knowledge brokering, evidence-to-decision frameworks, "evidence readiness").
3. Studies of policymakers' or practitioners' demand for or willingness to pay for evidence or research (including experiments), and of when organizations commission consultants or external analysis.
4. Response and uptake rates for researcher-practitioner partnership outreach.
RQ2
5. Scenario planning and contingency planning in humanitarian and social-protection practice (including shock-responsive social protection operational guidance).
6. Participatory causal mapping methods (participatory system mapping, causal loop diagrams, fuzzy cognitive maps, theory-of-change workshops) used with decision-makers.
7. Constraint-first approaches (growth diagnostics, problem-driven iterative adaptation) and decision-making under deep uncertainty (robust decision-making, info-gap).
8. Has anyone built scenario-specific log-frames with node-level data inventories and decision thresholds?
RQ3
9. Transportability and generalizability theory (selection diagrams, conditional-effect exchangeability, trial-to-target generalization) and applications in development or crisis settings.
10. Empirical work on predicting effects in new sites (site selection, heterogeneity across evaluations, hierarchical pooling, external validity over time and weather).
11. Prospective, pre-registered predictions of treatment effects compared with later experiments. What exists, what did it find, and was transport explicitly modeled?
12. Cash transfer evidence under conflict or displacement and the transfer from disaster to conflict settings.
Cross-cutting
13. Measures of saturation or stopping in evidence synthesis and evidence gap maps (search sufficiency, capture-recapture, cumulative meta-analysis stability).

Leads from Claude's memory. UNVERIFIED. They may be wrong, misattributed, or misdated. Use them only as search starting points, and do not cite them until you have opened the primary source:
- Value of information: Raiffa and Schlaifer; Howard; health-economics VOI literature.
- Bounded rationality and satisficing: Simon.
- Policymaker demand for research: a Brazil municipalities experiment by Hjort and coauthors; work by Vivalt and Coville on how policymakers update beliefs.
- Transportability: Pearl and Bareinboim; Dahabreh and coauthors; Stuart and coauthors; Hotz, Imbens and Mortimer; Allcott on site selection; Gechter; Bates and Glennerster; Pritchett and Sandefur; Vivalt; Meager; Rosenzweig and Udry on external validity over time.
- Constraint-first and adaptive: Hausmann, Rodrik and Velasco growth diagnostics; Andrews, Pritchett and Woolcock on problem-driven iterative adaptation.
- Shock-responsive social protection: Oxford Policy Management research.

Standard of evidence (matches the repo's source-verification note)
- Open every source you cite and read the relevant part. Give a stable link (DOI or publisher URL). No citation from memory or from another AI summary.
- Say what the source actually shows, and for empirical papers, the sample and setting. Do not stretch a result.
- Earlier Gemini output in this project included references that could not be verified. Assume that risk applies again, and flag every reference you could not confirm as UNVERIFIED rather than dropping or silently keeping it.
- "I found nothing" is valid only with a search log: databases and engines searched, exact search strings, date, and how many results you screened. Say it is absence of evidence from that search, not proof of absence.
- Distinguish: (a) the same question answered, (b) a related question answered, (c) the method exists elsewhere (such as health economics) but not in this setting, (d) nothing found.

Output (new files only; versioned; do not overwrite)
Write one file per RQ plus a summary, in ai-sandbox/research/independent-research/notes/00_overview-and-strategy/:
- Novelty Check - RQ1 Knowledge Audit - v1.md
- Novelty Check - RQ2 Decision Space - v1.md
- Novelty Check - RQ3 Transfer - v1.md
- Novelty Check - Summary - v1.md
Each RQ file: (1) a verdict in one of three forms: well answered / partly answered / open, with the reason in two or three sentences; (2) the sub-questions with findings, each tagged (a) to (d) above; (3) what a contribution could still be if the question is partly answered; (4) the search log; (5) a list of references with link, a one-line description of what each shows, and a VERIFIED or UNVERIFIED tag.
The summary: one table (RQ, verdict, strongest prior work, what remains open) and the three most important surprises. Keep each RQ file under about 2,500 words.

Constraints
- This repository is public. Do not copy copyrighted text or PDFs into it; short quotations with citation are fine.
- No human-subjects work, no outreach to anyone.
- Do not edit the review, strategy, tracker or plans. Aaron decides what to change after reading your results.
- If a question turns out much broader than you can cover, say what you covered and stop. Do not pad.
- When done, report to Aaron with the file list and links as clickable file:// paths, the verdict table, and anything you could not verify.
