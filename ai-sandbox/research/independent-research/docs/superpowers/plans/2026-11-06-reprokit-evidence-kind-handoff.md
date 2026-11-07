# Handoff: design and build the `evidence` project kind in reprokit (target v0.4.0)

Start with the `superpowers:brainstorming` skill. This is a DESIGN task first. Do not write code until Aaron has approved a short design. Work in a `claude/<task>` worktree of the monorepo for any monorepo doc, and in a branch of the `reprokit` repo for code. Do not tag, push, or release without Aaron's explicit approval. Warn before any step estimated over $1.

## Why this exists
Aaron wants every research project to use one standard reprokit repo layout. Study kind works (`compound-shocks-panel`). The `evidence` kind (desk-research repos: literature reviews, evidence maps, transferability papers) is designed on paper but NOT built. Projects waiting on it: `evidence-map` (old Project 01), `transferability` (old 03), later `systems-dynamics` (rough idea, currently only a literature review). A third kind, `library` (for `data-fusion-toolkit`), is deferred until after this; do not build it here.

## What exists today (verified 2026-11-06, reprokit v0.3.2, tag at 1df3791)
- `template/copier.yml` asks for `kind` (help text: "study, library, evidence, or a future kind"). `kind` is only written into `project.yaml` (`template/project.yaml.jinja`). Nothing in `template/` or `src/reprokit/` changes behaviour by kind. Every generated repo gets the study scaffolding: data roles, descriptors, `quick_check.py`, `compute.yaml`, `agents.yaml`, `protocol.md`, CI.
- Validators in `src/reprokit/`: `charter_rules.py`, `descriptor_rules.py`, `config_rules.py`, `validate.py`, plus JSON schemas in `src/reprokit/schemas/` (charter 0.1/0.2, descriptor 0.1/0.2, config, compute, agents, harmonization, manifest, run_metrics). Commands: `reprokit validate`, `quick-check`, run summaries.
- Generate with `uv run copier copy template <dir>` run from a LOCAL clone. Using the git URL copies reprokit's whole repo root.

## The design intent on record (do not edit the original spec text; changes go in its addendum)
- Spec: `ai-sandbox/research/independent-research/docs/superpowers/specs/2026-10-31-reproducible-research-framework-design.md`. Line ~71: "Evidence/desk repo | 01 evidence map, 03 transferability | no PDFs; citation manifest (DOI/OpenAlex ID) plus a shared Zotero group library so others fetch the same sources". Line ~184: outputs ship as a citation manifest so replicators never need to re-run the literature step. Line ~224: phase 12 (3ie taxonomy and literature-pipeline hooks, citation manifest export) is blocked until the taxonomy is final. Phase 16 is the future-kind check. Goals include rights-safe (no copyrighted PDFs in the repo) and fits a meta-structure (3ie taxonomy tags).
- Notes: `notes/05_reprokit-reproducibility-framework/Reprokit Project Summary.md` and `Cross-Group Connections.md` (Aaron's group-F notes; the latter links evidence kind to Projects 01 and 03 and to the literature pipeline).
- Related context, read as needed: `notes/02_literature-and-evidence-map/` (a separate project about HOW reviews are done, e.g. `Pitch - Structured Literature Taxonomy and Research Hub Extension.md`; it is NOT the per-project literature reviews), and the monorepo literature pipeline under `academic-rag-model/` (OpenAlex retrieval; produced the existing `literature_review.md` files, 15 papers each, Oct 2026).

## Questions the design must settle (recommend an answer for each, do not just list)
1. **What is an evidence repo's unit of work and "reproduction"?** Candidate: a search/screen/extract pipeline whose outputs are a citation manifest, extraction table, and synthesis, with "reproduce" meaning re-fetch the same sources by ID and regenerate the tables, never ship PDFs.
2. **Citation manifest schema.** Fields (DOI, OpenAlex ID, title, year, retrieval date, access class, screening status, extraction fields, rights note), versioning, and a JSON schema in `src/reprokit/schemas/`. How it relates to the existing `literature_review.md` format so those 4 existing reviews can migrate.
3. **Zotero.** Shared group library as optional source of truth vs. manifest as the only source of truth. Reproducibility without an account, credentials via `.env` (use `reprokit.env`; never log values), and the rule that no PDFs or full-text conversions are committed.
4. **Claims vs. sources.** Evidence repos make claims about papers. Does `validate` check that each claim cites a manifest entry and that each entry has a verified-resolves DOI/ID state? Reuse the verification-states vocabulary (proposed, source-verified, ...) from the study kind.
5. **Which study-kind pieces apply?** Data descriptors (probably replaced by source/search records), `quick_check.py` (what is a made-up-data check for a desk review? maybe a tiny fixture manifest through the real pipeline), `compute.yaml` (matters: paid AI use in screening/extraction is a cost-transparency goal and the $1 warning rule), `agents.yaml`, CI (Linux and Windows), secret scan, run summary.
6. **Charter.** Does `project.yaml` need kind-specific fields (taxonomy tags, search protocol, inclusion criteria)? Charter schema is at 0.2.0; decide whether this is 0.3.0 and keep 0.1/0.2 files validating.
7. **Template mechanics.** Copier conditionals on `kind` vs. separate template dirs; keep the study output byte-identical so `compound-shocks-panel` is unaffected; how `validate` dispatches by kind.
8. **Scope guard.** `systems-dynamics` may be only a memo. Decide whether a minimal evidence repo (manifest + synthesis doc) is acceptable so small projects are not over-scaffolded (an anti-goal in the spec: no empty scaffolding).

## Proposed shape of the work (adjust after the design is approved)
1. Short design doc (monorepo, `docs/superpowers/specs/` as an addendum-style new file, not an edit of the original) for Aaron to review; give him a clickable link.
2. Implementation plan, then build on a reprokit branch, TDD: schema + validator rules + template variant + tests + CHANGELOG, under the repo's rules (tests under 30 s, modules near 150 lines or fewer, no secrets, role directories, uv lockfile). Codex can implement after Claude designs (routing convention).
3. Test case: generate `evidence-map` (old Project 01) as the first evidence repo from a local clone, migrate its `literature_review.md` into it, run `validate` and `quick-check`, confirm CI on Linux and Windows in a scratch repo. Confirm a study repo generated before and after is unchanged.
4. Release v0.4.0 only on Aaron's approval (tag and push are his call), then update the pin in `compound-shocks-panel` only if he asks.

## Constraints and traps
- Standing: no raw ACLED rows anywhere; no copyrighted PDFs or full text committed; stage explicit paths only; one writer per worktree; the original design-doc text is not edited.
- Codex is concurrently doing a monorepo-only reorganization of `research/independent-research/projects/` (renaming `01_evidence_map` to `evidence-map`, etc., deleting the stale `02_compound_shocks` scaffold). It does NOT touch reprokit. Do not generate evidence repos into those folders until Aaron says the reorganization has landed.
- Windows CRLF: `.gitattributes` handles new checkouts; older checkouts keep CRLF after a fast-forward unless files are re-checked-out.
- Known reprokit follow-ups that could ride along only if Aaron asks: RUN_SUMMARY memory figure counts only the main process; README notes on `copier copy` from a local clone and on renormalizing line endings in old checkouts.
- `uv` is at `C:\Users\theaa\AppData\Roaming\Python\Python313\Scripts\uv.exe` (not on PATH in the shell).
