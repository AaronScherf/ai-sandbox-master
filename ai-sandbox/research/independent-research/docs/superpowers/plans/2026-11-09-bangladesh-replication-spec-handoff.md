You are drafting the replication spec for Aaron's `bangladesh-insurance-replication` project. This is a DESIGN task: write a spec, do not write replication code, run estimates, or push anything without approval.

Read first: the monorepo root AGENTS.md and docs/WORKTREE_WORKFLOW.md (use a `claude/<task>` branch and worktree for any monorepo write), and the project's own README.md, AGENTS.md, project.yaml and protocol.md.

Where things are (verify with `git` before relying on this; last checked 2026-11-08)
- Project repo: C:\Users\theaa\ai-sandbox-master\ai-sandbox\research\independent-research\projects\bangladesh-insurance-replication. It is a SEPARATE Git repository (private, https://github.com/AaronScherf/bangladesh-insurance-replication), git-ignored by the monorepo. Generated from reprokit v0.4.0, kind `study`, confidentiality `confidential`. Branch `main`, last pushed commit 844ce98 (charter and protocol filled in).
- The spec is a project doc, so write it in that repo (for example docs/replication-spec.md or notes/), as a normal commit there. Do not write it into the monorepo unless Aaron says so.
- Data: data/raw/JDE-17-406 - Replication data.csv (491,368 bytes; SHA-256 b47c3a9cfcfdfdf79cee4143c54e538e3ed82431b5f70cf5ba7c1b8877cb4515). Git-ignored. Reuse terms are unverified. NEVER commit, publish, paste rows, or send it to an AI service. Column names are fine to cite; protocol.md already lists them.
- Article PDF is private and stays out of the repo, logs and prompts. Use the open-access PMC version instead: https://pmc.ncbi.nlm.nih.gov/articles/PMC6472668/ (Hill et al., J. Development Economics 136, 2019, DOI 10.1016/j.jdeveco.2018.09.003). Check whether the PMC page includes the supplement, appendix or authors' code/data deposit; an earlier note says the supplement and source deposit were unverified.
- Prior notes (read for context, do not edit): independent-research/notes/02_literature-and-evidence-map/Machine-Readable Literature Sources - Evidence Mapping and Trial Eligibility.md (grep "Bangladesh"). It records the design (120 randomized Bogra villages, 60 offered insurance in 2013, aman monsoon and following boro dry season) and a read-only CSV check (1,974 rows, 59 columns, 120 village IDs, treatment constant within village, 998 treated and 976 comparison household rows).
- Framework: reprokit v0.4.0 at projects/reprokit (local clone, tag v0.4.0). Its docs and template define the study layout (descriptors, quick_check, validate, run summary).

Goal of the spec
Replicate the ENTIRE article first (every table and figure reproducible from this CSV), then report each number as matching, within rounding, or materially different. No extensions in this spec; list candidate extensions (for example the NDVI idea in the notes) only as a clearly separated non-goal.

The spec must contain
1. Result inventory: every table and figure, with estimator, sample, outcome, treatment, controls, clustering and fixed effects, and the CSV columns each needs. Mark which are reproducible from this CSV alone and which need data we do not have.
2. Variable dictionary for the 59 columns (meaning, units, currency), each marked proposed or source-verified against the article.
3. Method: the language and libraries, how to match Stata defaults (clustered SEs, small-sample corrections, any randomization inference), and what cannot be matched.
4. Comparison protocol: tolerance rules, how differences are logged, where results land (outputs/, RUN_SUMMARY via reprokit).
5. Verification plan using the protocol's states (proposed, source-verified, fixture-tested, run on acquired data, independently reproduced). A quick_check on made-up data must stay separate from real-data runs.
6. Data descriptor plan for data/descriptors/ (checksum, columns, unverified terms, how a reader obtains the file).
7. Disclosure rules: what may leave the private repo given unverified data terms.
8. Milestones, the smallest first release (for example one table end to end), and open questions only Aaron can answer.

Constraints
- AGENTS.md planning rules apply: separate verified behavior from assumptions, map every repository and write destination, and avoid editing historical design text except for marked status notes.
- Do not run paid AI calls over $1 without a warning and go-ahead.
- Update protocol.md's decision log and open questions only for decisions Aaron makes; do not close an open question by assumption.
- Present the finished spec to Aaron with a clickable local link, and ask for review before any implementation plan or code.
