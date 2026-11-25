# Spec A and journal-article transcription: handoff for a new session

Date: 2026-11-25. Written for a fresh Claude session with no memory of the previous one. Spec A (the research profile) is on `main` (landed 2026-11-25, tip of the landing `580cbab7`, follow-ups on `claude/spec-a-followups`). This note says what exists, what is left, and the traps.

## Read first
- Design: `docs/superpowers/specs/literature_taxonomy/2026-11-13-spec-a-indexing-classification-applicability-design.md` (claims marked **[Owner]** are decided; **[Call]** are defaults still open for the owner).
- Plan: `docs/superpowers/plans/2026-11-13-spec-a-indexing-classification-applicability.md` (Tasks 0 to 11).
- Run guide: `agent/literature/profile/README.md` (run order, discipline check, notes) and `pipelines/convert_journal_articles/README.md` (oversize rule, rounds, queue tracker).
- Run reviews: `docs/status/literature/2026-11-15-full-run-review.md`, `2026-11-14-trial20-not-applicable-review.md`, `2026-11-13-spec-a-regression-run.md`.
- Root `CLAUDE.md` and `ai-sandbox/academic-rag-model/CLAUDE.md`: the worktree rule, landing rule, and the interactive-Artifact rule apply.

## State of the corpus (research folder, outside git)
- 173 papers carry research-profile cards under `ai-sandbox/research/.index/`; chunks exist for all 173. Folder moves are applied (the planner now ignores anything outside `journal-articles/`; the application essays live in `independent-research/notes/application_essays/`).
- 25 of the 44 newest papers are tagged; 19 are notes and were skipped by design.
- Project tags (`projects`) exist for the two project folders. Re-run the `project` command for a folder after regenerating its cards, because regeneration drops them.
- Gemini runbooks and work files are in `ai-sandbox/research/.agent_work/` (gitignored): `PROFILE_NEW_RUNBOOK.md`, `TAG_NEW_RUNBOOK.md`, `new44_ids.txt`. The queue tracker is `journal-articles/TRANSCRIPTION_QUEUE.md` (regenerate with the `queue` command; do not edit by hand).

## Open work
### Transcription
1. `EvalFCV-Guide` (90 pages) and `elrha-r2hc` (64 pages): waiting for spare Gemini quota. Run through the agent driver (`--driver agent --collect`, Gemini fills, `--submit`). Pages are strictly ordered, 6 per round. A transcript with missing pages is now refused (`missing_pages`), so a submit that says "incomplete" just needs another submit.
2. Long articles cleared by the owner as articles but not collected yet: Doocy and Tappis (205 pp), the Turkey book (152 pp), the *Adaptive Social Protection* volume (155 pp, in two folders). Ask before running them: they are large, and any run estimated over $1 needs a warning first.
3. Three byte-identical `crisis_transfer_review` PDFs (`rdz021`, `jvaa019`, `qjv015`): link them as duplicates at no API cost.
4. Any further PDF over 100 pages is an open item for the owner (`article`, `leave`, `move`) on an Artifact; never decide it for them.
5. After new transcripts exist: `index`/embed them, run `chunk` (pass `--use-paid-key`), then profile and tag. Always pass `--file-id` when collecting tag cards: the `tag-v3` prompt version makes every earlier-tagged paper eligible again, and an unrestricted `tag collect` produced 139 cards.

### Spec A evaluation and decisions
6. 3ie answer-key test: `python -m agent.literature.profile.cli eval <answer_key.csv>` (matches by DOI). Needs the owner's 3ie `all_study_record` CSV. Report per-stratum numbers; do not set pass bars without the owner.
7. Blind-label page: an interactive Artifact where the owner (or a different model) labels each test paper's `report_type`, applicability, main intervention and outcome before any extractor runs, with decisions in its `db` collection. Not built yet.
8. Open owner decisions: grep the spec for `[Call]`, and `agent/literature/profile` `queue` for open review items (`python -m agent.literature.profile.cli queue`). Present them on an Artifact, not in a file.

### Code follow-ups
9. TODO-0102 (in `docs/trackers/academic_hub_to_do.md`): after a folder move the transcript's frontmatter `source_pdf` and `duplicate_of_path` keep the old folder. The fix must update the card's `content_hash` and make `undo_moves` reverse both.
10. Old empty chunk shard files for four loose PDFs remain. They are harmless.

## Traps
- Verify Gemini output mechanically: DOIs and citations were wrong before. Crossref-check every identifier and read the paper before quoting a claim.
- `GEMINI_API_KEY` may be a free-tier key (429 RESOURCE_EXHAUSTED). Pipeline runs use `PAID_GEMINI_KEY` (`--use-paid-key`). Never print a key.
- Profile write commands now take the corpus write lock (the research folder must be a git repo for the lock to resolve). A refusal prints which writer holds it.
- Worktrees have no `.env`; `load_dotenv_override()` falls back to the main checkout's.
- Run scripts as modules from `ai-sandbox/academic-rag-model/`; use the main checkout's venv (`C:\Users\theaa\ai-sandbox-master\ai-sandbox\academic-rag-model\.venv\Scripts\python.exe`).
- Work in your own `claude/<task>` worktree cut from the latest `main`. Landing needs `tools.active_work` clear of overlaps, a passing `tools.land_branch check`, one named change-ID approval from the owner, and `git push origin main`. Never merge or push `main` yourself, and never work around `land`. Keep tracker edits (`academic_hub_to_do.md`) on one branch at a time, because they overlap-block.
- Do not commit transcripts, PDFs, or anything under `ai-sandbox/research/`: the repo is public and the sources are copyrighted.
