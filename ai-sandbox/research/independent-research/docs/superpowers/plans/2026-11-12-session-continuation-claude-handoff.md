# Handoff to a fresh Claude session: nexus evidence agenda review, novelty check and discovery pipeline

Written 2026-11-12 by the previous Claude session (context was long). Read this, then `CLAUDE.md` (root and `ai-sandbox/academic-rag-model/`), `docs/WORKTREE_WORKFLOW.md` and `docs/AGENT_ROUTING.md`. Deep history, if needed: the previous session's transcript at `C:\Users\theaa\.claude\projects\C--Users-theaa-ai-sandbox-master\f613e85d-7cc4-46eb-9056-0c3018f52006.jsonl` (large; grep, do not read whole).

## 1. What the work is

Academic PhD research planning by Aaron Scherf, in the public GitHub monorepo `ai-sandbox-master`. Subject: a research agenda on how external causal evidence is found, assessed, adapted and used for decisions in prolonged crises and the humanitarian-development transition. Deliverables are review documents, handoff prompts for other AI agents (Gemini, Codex) and literature and source checks. The repo is public: never commit secrets (`ai-sandbox/.env`) or copyrighted source material. No human-subjects work yet (practitioner interviews are a later phase after IRB). The original handoff said: review and brainstorm only; do not edit the strategy, deck, tracker or project plans (the tracker exception: Aaron's explicit "add as a pending to-do" requests go to `ai-sandbox/academic-rag-model/docs/trackers/academic_hub_to_do.md` directly on `main`, one file, commit message starts `todo:`).

Working rules Aaron has set or confirmed:
- Every revision round of a review or strategy document is a new `- vN` file; never edit in place (memory file `feedback_versioned_reports_not_overwrites.md`).
- Handoffs and deliverables go in the repo (`docs/superpowers/plans/`, `notes/00_overview-and-strategy/`), never only in the scratchpad. Give clickable `file://` links to anything for review.
- Warn before any run or API call estimated over $1. Never pass identifying information to outside services beyond what the existing pipeline already does.
- One writer per worktree; stage explicit paths; use a `claude/<task>` branch and worktree for code. Do not write into another agent's worktree.
- Tag claims: [V] verified, [I] interpretive, [P] proposed, [O] owner choice, [C] checked by me, [S] search-summary only.
- References: identifiers come from a registry (Crossref/DataCite) or the source file, never from model recall. This was the central lesson of the novelty check.

Paths below are under `C:\Users\theaa\ai-sandbox-master\.worktrees\codex-nexus-presentation-strategy-v3\ai-sandbox\research\independent-research\` unless stated (uncommitted unless noted). Call it `IR/`.

## 2. State of the review documents

`IR/notes/00_overview-and-strategy/Review - Cohesive Nexus Evidence Agenda Recommendation - v1.md` through `- v5.md`. v3 added the RQ label key, timeline and value-of-information framing; v4 added validation definitions, the 2x2 buildout and saturation milestone, a 12-slide compressed deck sketch with appendix list A1-A12; v5 added the partner funnel, gate inventory, revised timeline (faculty talk about April 2027; IRB submit autumn year 2, approval spring, partner work summer), saturation as a subproject, pre-registration, triage funnel and procurement/case-source planning. Owner-chosen framing is C (a staged pipeline): RQ1 knowledge audit and value of information; RQ2 decision space (participatory DAG mapping, scenario planning, per-scenario log-frames); RQ3 transfer diagnostics; then a data-insufficient gap register, terminal-state prospective evaluation, portfolio and iteration. Next review version would be v6, folding in the source list, probe and novelty findings.

Open owner choices (v5 section 8): funnel time-box, IRB scope for outreach, gate presentation for the talk, who runs the saturation literature check, pre-registration registry, peer talk date, whether to start the case-source listing. The audience for the first talk is fellow PhD students, 30 minutes including questions.

## 3. Documentation probe (which case to audit first)

- Candidate source families note: `IR/notes/00_overview-and-strategy/Candidate Sources - Programme Documentation for the Desk Audit - v1.md`.
- Gemini probe (worktree `gemini-documentation-probe`): `Documentation Probe - Scored Candidates - v1.md` and `- v2.md`, `Documentation Probe - Correction Log - v1.md`.
- My checks: `Documentation Probe - Claude Spot Check - v1.md` and `- v2.md` (v2 corrects my own v1 error: Coady, Grosh and Hoddinott IS cited in endnote 63 of the Kenya HSNP2 Business Case; my text extraction skipped endnote bodies. Lesson: search raw `content.xml`, not extracted paragraphs, for ODT files).
- Findings: Kenya HSNP Phase 2 document trail verified (inventory, seven options, Option 3, completion review figures). The seven options vary scale/speed/financing, not intervention type; Kenya is a drought, non-conflict setting. Gemini v2 re-scored out of 16: Somalia 11, Ethiopia PSNP 4 14, Kenya 13; its recommendation still starts with Kenya. Not checked by me: Ethiopia's ICR (ICR00006153) and IEG review (ICRR23858), and Somalia's "no ICR disclosed" API result. DEC 2011 citation in v1 was hallucinated (confirmed absent).
- Pending: owner choice of first case (Kenya vs Ethiopia); a second reader should spot-check the Ethiopia closeout documents; Somalia status needs a browser look (World Bank pages are JavaScript shells to a static fetch).

## 4. Novelty literature check (RQ1-RQ3)

- Handoffs in `IR/docs/superpowers/plans/`: `2026-11-10-novelty-literature-check-handoff.md` (Gemini), then correction handoffs `2026-11-11-novelty-check-correction-handoff.md`, `-second-correction-handoff.md`, `-third-fix-handoff.md`, `-fourth-fix-handoff.md`.
- Gemini outputs are in worktree `.worktrees\gemini-nexus-novelty-check\...\notes\00_overview-and-strategy\`: `Novelty Check - RQ1/RQ2/RQ3/Summary` v1 to v4, `Correction Log` v1 to v3. My checks: `IR/notes/00_overview-and-strategy/Novelty Check - Claude Spot Check - v1.md` (covers v1 only; I did not write a note for v2-v4; the Crossref results are summarized here).
- Reference accuracy by round (my Crossref resolution of every DOI): v1 13 of 38 correct; v2 about 30 fixed, 7 wrong, 3 not found; v3 all 42 DOIs resolve to the cited paper except the arXiv one (Crossref 404, DataCite fine); v4 identifiers clean and Montiel Olea title fixed ("Externally Valid Selection of Experimental Sites via the k-Median Problem"). Check script is in the previous session's scratchpad only (not in the repo): resolve each `10.` DOI at `https://api.crossref.org/works/<doi>` and compare title, authors, venue, volume, pages, year (use `-I` for Python; generic user agent).
- OPEN SUBSTANTIVE ERROR: v2 and v3 correctly said Crost, Felter and Johnston (2016, J Dev Econ 118:171-182) found conditional cash transfers DECREASED insurgent influence/incidents; v4 reverted to "increased insurgent violence" (RQ3 v4 line 58; Summary v4 line 71). The fourth-fix handoff (`2026-11-11-novelty-check-fourth-fix-handoff.md`) was written for Gemini; check whether Gemini has returned `- v5` notes and `Correction Log - v4`. Also check the others in the Gemini claims list that came from memory: Hjort "10 percentage points", Altmejd "65-70%", Egger "2.5 multiplier", Groh details.
- Gemini's tag vocabulary now: REGISTRY-MATCHED (DOI resolves, nothing read), ABSTRACT-READ, FULL-TEXT-READ, INSTITUTIONAL-URL, UNVERIFIED. Do not quote the novelty verdicts or "surprises" in the talk until the claim-bearing papers (P1 list below) have been read. Summary verdicts (Gemini v3/v4, unverified): RQ1 substantially answered in adjacent domains (health economics VOI, IDinsight and GiveWell work), open for humanitarian/transition programme design; RQ2 and RQ3 narrower gaps than v1 claimed.
- Status and pipeline note: `IR/notes/00_overview-and-strategy/Novelty Check - Status and Pipeline Idea - v1.md`. Fetch list with priorities (P1 = 16 claim-bearing items): `Novelty Check - Fetch List and Priorities - v1.md`.
- Reading the papers: the PDFs are being fetched and transcribed (section 5). When the transcripts exist, do the claim check: read abstracts and the specific passages behind each P1 claim (Crost finding; IDinsight VOI work against RQ1's contribution; Bongers cyclic models; Tennant participatory DAGs; Altmejd pre-registered models; DellaVigna-Pope-Vivalt platform; Montiel Olea k-median; Gechter bounds; Kastner capture-recapture; White et al. gap maps). Write the result as a new versioned note (for example `Novelty Check - Claude Claim Check - v1.md`) with quote-anchored spans (short quotes, page numbers), then a Gemini or Claude revision of the novelty summary.
- Then: start with RQ1 against IDinsight's value-of-information work (nearest prior art), read RQ2 and RQ3 notes for substance.

## 5. Discovery pipeline work (code)

- Branch `claude/discovery-doi-list`, worktree `.worktrees\claude-discovery-doi-list` (unpushed, unmerged), commits `a5fe8523` (new `discovery/discover_journal_articles/fetch_dois.py` DOI-list route + tests + README Route 4), `dcf30667` (landing-page `citation_pdf_url` fallback in `access.py`), `25aabd99` and `e5f60e0f` (security hardening after automated reviews: landing-page hop never follows when cookies are in play, no credentials, hostname resolved and non-public addresses refused, redirects followed by hand and re-validated, max 3). All 232 discovery tests pass (venv at main checkout `ai-sandbox\academic-rag-model\.venv`). Known residual: DNS rebinding between check and connect is not closed; the older EZProxy path passes a cookie dict to `requests` with default redirects (pre-existing, not changed). Aaron's EZProxy no longer works, so skipped.
- Real run result: 13 of 42 DOIs fetched automatically (the rest bot-blocked or paywalled); Aaron then downloaded many by hand into `ai-sandbox\research\journal-articles\novelty-check\`. The 9 references without DOIs (IDinsight, Elrha/Smith, ALNAP/Campbell and Knox Clarke, Henrick et al., Bakewell and Garbutt, Ben-Haim, Hummelbrunner [URL is a home page, not a document], Lempert et al., O'Brien et al.) are a separate manual job.
- The Codex handoff `2026-11-11-discovery-doi-list-mode-codex-handoff.md` is MOOT (I built it). Tell Codex not to start it if it resurfaces.
- Merge: the branch needs Aaron's go-ahead; a reviewer should look at `access.py` and `fetch_dois.py`. Not pushed.
- Side effects in the main checkout (integrator checkout): `research/journal-articles/.discovery/seen.json` and `needs_manual_downloads.md` are modified and uncommitted; many other untracked journal-article files predate this work. Aaron edited `needs_manual_downloads.md` by hand; it is regenerated from `seen.json` on every run, so deleted lines return unless the manifest entry is dismissed (see TODO-0098).
- Transcription handoff for Gemini (just written): `2026-11-12-novelty-papers-transcription-gemini-handoff.md`. Check its report; then use `python -m core.indexer.index_search query "..."` (from `ai-sandbox/academic-rag-model`) or read the Markdown under `research/journal-articles/novelty-check/processed_outputs/`.

## 6. Reference checker (Codex)

`2026-11-11-reference-checker-codex-handoff.md` and its regression addendum `2026-11-11-reference-checker-regression-addendum.md` (expected answers for the v2 set: 7 wrong DOIs, 3 not found, 1 DataCite-only, about 20 correct). A separate Claude session reviews Codex's work. Codex hit a session limit; status unknown. Do not wire the checker into pipelines without Aaron's approval. Design rule to propose: identifiers and bibliographic metadata come from a registry or the source file, never model recall; an LLM only extracts claims with quote-anchored spans.

## 7. Tracker items added (on `main`)

- TODO-0097 (new section "Proposal Novelty Check (subproject of Literature Taxonomy, `agent/literature`)"): research-proposal novelty-check pipeline; first step is a WEB survey of existing tools, papers and services, plus this repo (`agent/literature/gap`, `discovery/discover_journal_articles`). Commit `2144a285`.
- TODO-0098: discovery relevance false positives (example "Disaster Recovery and Business Continuity for Database Services in Multi-Cloud"); also the dismissed-status idea for the worklist. TODO-0099: survey more complete literature databases than OpenAlex alone. Commit `eb1a3173`.
- Only those tracker commits are on `main`; nothing else of this work is committed except the discovery branch above.

## 8. Suggested order for the next session

1. Check for returned Gemini results: novelty `- v5` and `Correction Log - v4`; transcription report; documentation probe follow-ups. Check Codex's reference checker status.
2. Verify the Crost fix directly from the transcript once it exists.
3. Run the claim check on the P1 papers and write the versioned note.
4. Do the Kenya checks Aaron agreed: log-frame and evidence trace on HSNP2, a prediction-power check for the pre-registered terminal evaluation, and a triage-funnel sanity check on the Kenya Business Case. (Aaron: "we will come back to the 1 to 3 items after".)
5. Fold everything into review v6 (new file), ask Aaron for the open owner choices, and only then revise slides.
6. Offer to get the discovery branch reviewed and merged, and to start the TODO-0097 web survey when Aaron wants it.
