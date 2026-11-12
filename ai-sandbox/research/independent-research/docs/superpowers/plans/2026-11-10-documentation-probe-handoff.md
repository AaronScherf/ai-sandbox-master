You are a Gemini (Antigravity) session, separate from the session doing the novelty literature check. Your task is a bounded documentation probe: for three candidate programmes, find out how much of the design-to-closeout record is publicly documented, and score it against a fixed rubric. Write only the new output file named below. Do not edit any existing file, and do not commit or push without reporting to Aaron first.

Before any write, follow docs/WORKTREE_WORKFLOW.md at the monorepo root: use your own branch and worktree (for example `gemini/documentation-probe`), not the Codex worktree `codex-nexus-presentation-strategy-v3`.

Why this probe exists
Aaron is planning a PhD agenda on how external evidence is used in decisions during prolonged or recurrent crises. The first empirical step is a desk-based retrospective audit of one richly documented programme in the cash vs. safety-net family. That audit can only work if a programme's public record shows (1) what options the designers considered, (2) what evidence they cited and used, (3) monitoring data across the programme's life, and (4) a closeout evaluation. This probe tests cheaply whether any candidate has that record. A candidate scoring poorly is a useful result.

Read first (under ai-sandbox/research/independent-research/; the files may exist only in the Codex worktree until landed, so ask Aaron for paths if you cannot find them)
- notes/00_overview-and-strategy/Candidate Sources - Programme Documentation for the Desk Audit - v1.md (the sources, the rubric and the open caveats)
- notes/00_overview-and-strategy/Review - Cohesive Nexus Evidence Agenda Recommendation - v5.md, section 7 and the gates table (context only)
- notes/00_overview-and-strategy/Humanitarian Evidence Agenda - Source Verification.md (the standard for verified claims)

Candidates
These were found by web-search summaries. Nobody has yet confirmed which documents exist or how rich they are.

A. Somalia: World Bank shock-responsive safety net sequence leading to the national Baxnaano programme.
- P174065 Shock Responsive Safety Net for Locust Response (approved 29 June 2020): https://projects.worldbank.org/en/projects-operations/project-detail/P174065
- P176369 locust response additional financing: https://projects.worldbank.org/en/projects-operations/project-detail/P176369
- P171346 Shock Responsive Safety Net for Human Capital Project (closing date reported as 31 December 2025): https://projects.worldbank.org/P171346?lang=en
- P181469 third additional financing supporting Baxnaano: https://projects.worldbank.org/en/projects-operations/project-detail/P181469
- Reported related documents, unopened: a World Bank discussion paper "From Protracted Humanitarian Relief to State-led Social Safety Net System: Somalia Baxnaano Program" (2022); a Samuel Hall "SNHCP Targeting Evaluation Final Report" (https://www.samuelhall.org/s/SNHCP-Targeting-Evaluation-Final-Report.pdf); a CGIAR "Review of the shock responsive safety net for human capital project, Somalia" (2024).

B. Ethiopia: Productive Safety Nets Project 4 (PSNP 4), World Bank P146883.
- Reported: IDA credit of USD 600 million equivalent approved 2014; implementation completion report ICR6153 dated 30 November 2023 and disclosed 9 December 2023, reported ratings moderately satisfactory on outcome and Bank performance and "modest" on monitoring and evaluation quality; a 2026 IEG country programme evaluation (FY2013 to FY2023) with an appendix on PSNP.
- Project page: https://projects.worldbank.org/en/projects-operations/project-detail/P163350 (this is the page the search tied to the family; confirm which project ID applies to PSNP 4 versus the additional or successor financing, because search results mixed P146883 and P163350).
- Document list page found: https://documents.worldbank.org/en/publication/documents-reports/documentdetail/894041590076668825 (unconfirmed what it is)
- Note: PSNP is a long-running programme with several phases. Say in your report which phase a document belongs to.

C. Kenya: Hunger Safety Net Programme Phase 2 (HSNP2), a safety net designed with a scalable drought-response component after the 2011 drought. Reported funders and implementers include the UK's aid department and a contractor, DAI.
- Reported documents, unopened: "Drought Emergency Scale-up Payments Process Review, final report, 24 January 2016" (https://library.alnap.org/system/files/content/resource/files/main/hsnp-emergency-scale-up-payments-process-review-report.pdf); a 2019 SPaN case study (https://capacity4dev.europa.eu/library/span-2019-case-study-kenya-hunger-safety-net-programme-hsnp_en); an ODI HPN blog on scaling up (https://odihpn.org/blog/shock-responsive-social-protection-in-practice-kenyas-experience-in-scaling-up-cash-transfers/).
- Not found yet: the UK DevTracker entry with a business case, annual reviews and completion review. Search DevTracker (https://devtracker.fcdo.gov.uk) by programme name and by IATI identifier. If you cannot find it, say so; that itself is a result.

Why these three: A is in Somalia, the geography of Aaron's existing context panel, and spans an emergency-to-national-platform path. B is a long-lived safety net with a completion report on file. C is a shock-responsive design with an independent process review. Note that two of the three are World Bank projects, whose documentation is standardized, so they may look better documented than programmes from other funders. Mention that in your report.

Rubric (score each candidate 0 absent, 1 partial, 2 rich; give evidence for every score)
1. Design document with options: alternatives named and compared.
2. Evidence-use trace: external evidence cited and tied to a design choice.
3. M&E data: a results framework plus repeated indicator reports across the programme's life.
4. Closeout evaluation: a final report linking results to design.
5. Geographic specificity: sub-national targeting or locations.
6. Support-seeking record: consultants, technical assistance or advisory services identifiable.
7. Organization status: the funder or implementer still exists with similar work ongoing or planned.

What to do for each candidate
1. Build a document inventory: document type, title, date, link, and access status (opened and read / listed but not opened / blocked or broken). Start from the project or programme page and its documents tab; open the appraisal or business case, implementation status reports or annual reviews, additional-financing papers, and the completion report or completion review, whichever exist.
2. Read the design document (project appraisal document or business case). Record whether it compares options, and list each external-evidence citation it relies on, with a one-line note on whether the citation is tied to a design choice. Do not paste long text.
3. Record the date of each document you rely on. Aaron will use only information available at design time, so dates matter.
4. For criterion 6, search the World Bank consultant-services contract awards data (FinancesOne; API at search.worldbank.org/api/contractdata) and the project's own documents for consultants and technical assistance linked to the project. Note that the awards data are not exhaustive. For candidate C, look for contractor or advisory arrangements in the programme documents.
5. Score the rubric. Every score needs a link to the specific document and page or section, and a quotation of at most 25 words or a plain description. Do not score from a search snippet, an abstract, or another summary. If you could not open the document, score the item "not assessed" and say why.

Standard of evidence
- Open and read before you cite. State exactly what you could and could not access.
- Do not infer richness from titles. A document titled "evaluation" may not link results to design.
- Do not copy copyrighted text or PDFs into the repository (it is public). Short quotations with citation are fine.
- If a site blocks your access, record it and move on. Do not work around access controls.

Time-box and stop rules
- Aim for about half a day of effort per candidate. If the design document has no options analysis and no evidence citations, score it, note it, and stop on that candidate.
- If one of the three clearly dominates after two are scored, you may finish the third more lightly, but say you did.

Output (new file only; versioned; do not overwrite)
Write ai-sandbox/research/independent-research/notes/00_overview-and-strategy/Documentation Probe - Scored Candidates - v1.md, containing:
1. A summary table: candidate by rubric criterion (0, 1, 2 or not assessed) with a total, and one sentence on the most important weakness of each.
2. For each candidate: the document inventory, the evidence-citation list from step 2, the support-seeking findings, the scores with evidence, and a short note on hindsight-bias risk (what could be known at design time).
3. A recommendation: which candidate (if any) is the best base for a retrospective audit, and what is missing. Say plainly if none qualifies.
4. A tooling-friction log: pages you could not open, broken links, anything that needed a login.
5. A section "Things to check next" listing other programmes you noticed that might score higher, without researching them.

Constraints
- No human-subjects work. No outreach to any organization or person.
- Do not edit the review, candidate list, strategy, tracker or plans.
- When done, report to Aaron with the file path as a clickable file:// link, the summary table, and anything you could not verify.
