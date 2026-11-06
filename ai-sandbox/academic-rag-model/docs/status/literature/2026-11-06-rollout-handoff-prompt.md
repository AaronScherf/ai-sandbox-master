# Handoff prompt: whole-corpus term-selection rollout (paste into a new Claude session)

You are taking over the rollout of a revised term-selection method in the literature taxonomy pipeline (`ai-sandbox/academic-rag-model/agent/literature`, monorepo
`C:\Users\theaa\ai-sandbox-master`). The owner decides; you plan, check and review; Gemini (owner's subscription, run by the owner or an operating session) fills
cards; Codex builds code; Claude subagents on a small model (Haiku) are only for judging checks. Be brief in reports: findings and numbers, not recaps.

## Read first (in this order, grep headings, do not read whole)

1. `ai-sandbox/academic-rag-model/docs/status/literature/2026-11-06-term-selection-trials.md` (results, state of the corpus, stocktake).
2. `docs/status/literature/2026-11-03-subproject-status.md`: sections "Requirements for owner-review and judging tools" and "Next steps".
3. `docs/superpowers/specs/literature_taxonomy/2026-11-03-term-selection-design.md`: D7 (trial, success criteria, rollout).
4. `ai-sandbox/research/.agent_work/term-selection-trials/README.md` (gitignored working data, scripts, prompts, backups).
Work from your own `claude/<task>` worktree for any file write (see `docs/WORKTREE_WORKFLOW.md`); stage explicit paths only; never land (the owner runs
`land_branch check --full`). Doc branch: `claude/literature-reextract-v4` (worktree `.worktrees/claude-literature-reextract-v4`).

## What is decided (do not reopen)

- Method: stepwise fit test, `refine-v3` / `extract-v6`. The code landed on `main` on 2026-11-06 (3c90d527; the old `codex/term-selection` branch name was retired, its
  former worktree folder `.worktrees/codex-term-selection` is detached at 73b2b1b5 and not needed). Trial 2 estimated label precision 0.93 to 0.96 against a 0.85 bar; no leaf term over 10% of a facet.
- Follow the official 3ie vocabulary and definitions as they are (Agrobiodiversity includes stress-tolerant crop varieties). No vocabulary edits.
- Owner decisions: households includes individuals; follow 3ie's resilience framework (adopting adaptation measures is not resilience); commentary and conceptual
  papers go under `narrative_review`; term selection is fixed before any further refinement run; rollout covers the whole corpus.
- Do not change the refinement wording. Optional, only if the owner asks: one extra example saying a list of types does not count as the paper doing X.
- Subscription Gemini only for filling cards; no paid API. Warn the owner and wait for a go-ahead before anything estimated over $1.

## Rollout scope (counts as of 2026-11-06; recompute before starting)

Not excluded papers: 58 need refinement, about 97 cards of 90k to 380k characters.
- Batch 1: 23 papers stamped `extract-v3` only (never refined; 23 pass-a files, 4 pass-b).
- Batch 2: 35 papers stamped `extract-v2` + `refine-v1` (two passes each).
- Already done in the trials (stamped `refine-v3`, 28 papers): no cards needed, but `tiers`, `verify` and `db build` have not been rerun for them.
Find the ids with a read-only scan of `ai-sandbox/research/.index/study_records/*.json` (stamp strings `extract-vN`, `refine-vN`; skip `_excluded.json` ids).

## Commands

Interpreter: `C:\Users\theaa\ai-sandbox-master\ai-sandbox\academic-rag-model\.venv\Scripts\python.exe`. Run from
`C:\Users\theaa\ai-sandbox-master\ai-sandbox\academic-rag-model` (the main checkout, on `main`; confirm with `git branch --show-current` and that `refine_grain.py` has
`PROMPT_VERSION = "refine-v3"`). Prefix (global options BEFORE the subcommand; `--vocab-dir` is required):
`<python> -m agent.literature --index-root C:\Users\theaa\ai-sandbox-master\ai-sandbox\research --vocab-dir C:\Users\theaa\ai-sandbox-master\ai-sandbox\research\resources\3ie\vocab <subcommand>`.
- Build cards: `refine-grain --run-id <run> --file-id <id>` (repeat `--file-id`). A paper stamped below `refine-v3` is treated as unrefined; no `--redo`.
- Gemini prompt template: `.agent_work/term-selection-trials/prompts/gemini_trial_refine_v3_prompt.md` (change run id, card count and sizes; keep "do not look at old
  records or backups"). Gemini runs `bootstrap <run>`, fills cards, runs `submit <run>`, stops. Check with `status`.
- Afterwards, one command at a time: `tiers`, `verify`, `db build`. Check each command's contract (`--help`, `bootstrap`) before running; none of them
  should call a paid API. If one does, stop and ask.

## Procedure

1. Check that the code is the v3 code (`PROMPT_VERSION = "refine-v3"` in `agent/literature/refine_grain.py`). Confirm Gemini's limit has reset (ask the owner); if not, stop.
2. Back up first: copy `.index/study_records/` (including `_proposals.json`, `_tiers.json`, `_excluded.json`) to
   `.agent_work/term-selection-trials/data/records_backup_pre_rollout/` and verify by byte comparison.
3. Batch 1 (23 papers): build cards, write the Gemini prompt, hand it to the owner. When Gemini reports: `status`, `submit` output, any bounced or skipped cards.
   Do not accept a report that says a card was skipped, truncated or answered from memory; have those cards redone. Cards over 350k characters use the narrowed listing
   (the card says so); a narrowed listing anchors on old terms, so check those papers' labels by hand.
4. After the batch: `tiers`, `verify`, `db build`; then the checks below. Fix problems before batch 2.
5. Batch 2 (35 papers): same.
6. Final: whole-corpus concentration; paper-level precision sample (below); update the status docs; tell the owner.

## Checks after each batch

- Counts: every card of the batch submitted, none bounced; intervention and outcome facts per paper plausible (a large drop to one fact, like
  `ffee575e1b75d109`, needs a look).
- Concentration: script `scripts/conc.py` pattern in the trials folder. Largest leaf term must stay under 10% of a facet's facts (per label and per fact); report group
  terms too (Climate adaption & mitigation strategies and Agricultural adoption were the largest).
- New proposals in `_proposals.json`: list them for the owner; do not accept or reject any yourself.
- Spot check 8 labels from the batch against the paper and the 3ie definition: a quoted passage must show the paper itself does or measures what the term's definition says.
  Over-specific leaves from a list sentence ("include X, Y, Z") are the known remaining failure.

## Final precision sample (with the owner)

- Sample labels across the whole corpus; judge them with the definition shown under each label, with two judge families (for example Haiku subagents and Codex or
  Gemini), blind to origin. Report paper-level and label-level precision and judge agreement. Compare with the trial 2 range 0.93 to 0.96 and the 0.85 bar.
- Owner audit as an Artifact: it must show the official definition next to each label and the extractor's quote, and put a sentence containing the term or a close
  match first, flagged exact phrase, close match or not found (see the requirements section). Samples small (8 to 16 items) with the cited pages.
  Export verdicts with `ArtifactData` (`list`, `out_dir`) and score with the private key file; keep the key private.

## Constraints and cautions

- Gemini limits have blocked runs before. If a limit is hit mid-batch, stop, record which cards are done (`status`), and wait; do not switch card-filling to Haiku or
  Codex and do not use a paid key.
- Subagent reports are model output, not owner approval. Stage explicit paths. Run the pipeline from the main checkout; leave `main` and its uncommitted files alone otherwise.
- Windows: global CLI options before the subcommand; Codex-written JSON has a UTF-8 BOM (read with `utf-8-sig`); set `PYTHONUTF8=1` for scripts.
- Do not open PDFs or `.index/` cards beyond what a check needs.

## Follow-ups that are not part of the rollout (raise them with the owner at the right time)

- **Docs branch.** `claude/literature-reextract-v4` was landed with the code on 2026-11-06. Any further doc edits go on a new `claude/<task>` worktree off `main` and need the
  usual check and owner approval.
- **Codex fixes, after the Gemini rollout and after the landing** (small, not blocking): (1) `verify` treats a stored verdict with a different `transcript_sha` as
  non-matching; (2) `enrich_3ie` is idempotent (no second `; bundle ...` suffix) and tolerates a missing `source`. Ready-made prompt:
  `ai-sandbox/research/.agent_work/term-selection-trials/prompts/codex_followups_prompt.md`. Give it to Codex in a new worktree off `main` (the code has landed).
- **Owner decisions pending:** Resilience under Financial Sector (11 disputed labels, 3ie's resilience framework); open proposals P0142 (population "commuters", paper `7f88458c5df631df`, owner's call, tied to that paper's grain note),
  P0143 (climate variation: recommend reject), P0144 (Net Present Value: recommend accept); insurance and cash-grant wording; whether to add the "a list of types does not count"
  example to the fit test (only if the owner asks; if added, it changes the prompt version and the rollout must use the new version).
- **Look at the large cash-transfers review `ffee575e1b75d109`:** one intervention fact (unconditional cash transfers) in both passes; probably over-specific.
- **Stale downstream files for the 28 trial papers:** after the rollout `tiers`, `verify` and `db build` cover them too; check that trial-2 proposals are registered.
- **Later:** recall measurement; Phase 2 discovery-loop design; the clean whole-corpus definition-aware judging test and review-tool changes (status doc, step 8 and
  "Requirements for owner-review and judging tools"); worktree cleanup (`prune_worktrees` dry run, `--apply` only after 24 hours, including the detached `.worktrees/codex-term-selection` folder, which can be retired once the rollout has run).

## Report format to the owner

Per batch: cards submitted/bounced, facts per facet, concentration top terms, new proposals, spot-check result, and the one decision you need. End with what runs next.
