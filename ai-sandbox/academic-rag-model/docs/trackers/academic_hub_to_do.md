# Pending Improvements for the Academic Hub by Subproject

<!-- Convention: one bullet per pending item under its subproject's `##` heading, ending in
     `(added YYYY-MM-DD)`. New sections go directly under this title: the file ends in pasted
     example text, so don't append at the end. Agents add items when asked to "add this as a
     pending to-do" (see the root CLAUDE.md). -->

## Codex Brainstorming, Planning, and Implementation
- <!-- TODO-0001 --> Use the [Codex corpus-health project retrospective](../brainstorms/2026-10-09-codex-corpus-health-project-retrospective.md) to improve Codex's project-work guidance. Review its proposed `AGENTS.md` additions for requirement-to-evidence traceability, exact-scope repair contracts, live finding validation, and a proportionality check after design review; decide which should become durable rules after the corpus-health trial and Claude's review. Keep the distinction between a reviewed design, passing fixture tests, a successful live scan, and an observed multi-day run in future project handoffs. (added 2026-10-09)

## Study Guide Pipeline (`agent/study_guide`)

- <!-- TODO-0002 --> Calibrate the revise relevance floor per course: the `[revise]` relevance stage in `agent/study_guide/revise` uses an embedding-similarity floor (0.68 in the microeconomics HW4 spec, carried over from the Wald guide). In the first micro run (`micro_hw4_consumer_choice.a1.enhanced.a1`, 2026-10-09) 29 of 30 relevance deletes were primer blocks (budget slope, Kuhn-Tucker, Lagrangian, tangency) scoring 0.66 to 0.68, just under the floor, because primers draw on textbooks while the course evidence is thin. The same run did not flag the invented "Test Statistics, Decision Rules" block in section 7, so the floor also misses off-topic content. Approach: derive the floor from the guide's own score distribution (or make the delete need both a low score and a judge verdict), and log the decision so it can be tuned in the spec. (added 2026-10-09)
- <!-- TODO-0003 --> Add an assignment-check step to the study-guide pipeline: after revise, compare the finished guide against the assignment it serves (coverage of every question and consistency with the solutions document) and report gaps and conflicts. In the first microeconomics HW4 guide (2026-10-09) this was done by hand and found what revise missed: no demands for four of the five utility functions in question 3, an aggregation example whose construction could not produce the violation, a textbook typo copied into the guide, and a formula error in the solutions document. Approach: assignment questions and solutions as inputs listed in the spec, one model or agent call per question, output through a review Artifact. Part of the subscription-agent design above. Status: `docs/status/agent/2026-10-09-microecon-hw4-guide-status.md`. (added 2026-10-09)
- <!-- TODO-0004 --> Fix `strip_citations` in `agent/study_guide/draft.py` for the leftovers seen in the microeconomics draft: multi-citation parentheses written with semicolons that leave `(§3.B, p. 52;`, `; §4.C, p. 119)`, empty backtick pairs and stray `;.` separators, and citations inside a LaTeX `\text{(...;}` in display math. About 100 section-sign fragments, 88 empty backtick pairs and 40 stray semicolons survived in five sections and were removed by a one-off script; add the patterns with tests, and check the sidecar `guide_plans/<id>.<tag>.cited.json` for the exact original forms. (added 2026-10-09)
- <!-- TODO-0005 --> Make revise `note` edits visible and resolvable: `apply-revise` records a `note` edit in the changelog as acknowledged but leaves the guide text unchanged, so five audit findings in the microeconomics guide (convexity and concavity wording, a framing-experiment description, an unsupported lexicographic formula, an unsupported differentiability claim, a CES algebra error) stayed in the text until fixed by hand. Options: render accepted notes as a visible review marker in the guide, or let the audit propose a `fix` with a quote when it is confident. (added 2026-10-09)
- <!-- TODO-0006 --> Index markdown that has no source PDF (homework hints, guided solutions, tutoring conversation notes): `core/indexer` only pairs a PDF in `academic_resources/` with `processed_outputs/<stem>.md`, so `homework_{3,4}_hints.md` and `homework_{3,4}_guided_solutions.md` for microeconomics could not feed the study guide. Needs an indexer change for notes-only sources, with a `doc_type` such as `hand_notes`. Also unindexed: the 29 Sep and 1 Oct microeconomics canvases, which need exported `.svg` or `.png` files before `transcribe_notes` can read them; choose which copy of each to use and run a paid dry run first. (added 2026-10-09)
- <!-- TODO-0007 --> Make a subscription agent the default way to run the study-guide pipeline, with the current API path kept as the fallback for users without a subscription. Why: the first microeconomics HW4 run (2026-10-09) cost about $0.62 to draft, $0.38 to enhance and $1.51 to revise, and still left defects: an invented econometrics block in section 7, and a WARP aggregation example in section 11 whose construction was impossible (the audit flagged the wealth error but not that). The correctness audit is nearly all the cost ($1.46) and reads text without checking it. Design to brainstorm: a Claude Code or Antigravity agent drafts and audits using the local index (`python -m indexer.index_search`) and can run code to check examples, while `agent/study_guide` keeps the plan, review, apply and validation steps so output is still checked and reproducible; the API mode stays for others. Both modes share the subject-neutral draft prompt and the per-course relevance floor (see the two items below). Related: the Antigravity run-mode notes elsewhere in this file. (added 2026-10-09)
- <!-- TODO-0008 --> Make the draft prompt subject-neutral: `GUIDE_V1_TEMPLATE` in `agent/study_guide/prompts.py` tells the model to cover "the statistic and how it is computed, its distribution and the decision rule", which is econometrics wording. In the microeconomics HW4 guide (draft `micro_hw4_consumer_choice.a1`) it produced an invented "Test Statistics, Decision Rules" sub-section with null hypotheses in section 7 (non-rational choice) and "The Statistic and Its Formula" headings elsewhere. Approach: add a `guide_v2` prompt id (keep `guide_v1` frozen for the Wald guides) with wording driven by the topic instruction or a spec field, accept it in the spec validation, and redraft the affected micro sections to compare. For now the micro guide leaves section 7 for the revise pass's relevance stage to catch; check whether it did. (added 2026-10-09)
- <!-- TODO-0009 --> Optional API-driven topic proposal and spec/source-plan authoring, so a user without a Claude subscription can run the whole pipeline. Today the steps before `plan` (reading the course materials, proposing the topic list, writing the guide spec TOML and picking pinned sources) are done by a Claude Code session; `plan`, `draft`, `enhance` and `revise` already run on the Gemini API. Add an optional command (for example `python -m agent.study_guide propose`) that sends the syllabus, lecture and problem-set outlines, and the user's focus statement to a Gemini call, returns a proposed topic list for confirmation (through the review Artifact or a plain JSON/Markdown file for users without Artifacts), then writes the spec TOML from the confirmed list with `section`/`file`/`discover` source rules. Keep it opt-in beside the Claude-driven path; reuse the dry-run cost estimate and `--max-cost` guard, and warn before any call estimated over $1 (owner's standing preference). Context: first used for the microeconomics HW4 guide (2026-10-09), where the topic proposal and spec were written by Claude Code. (added 2026-10-09)

## Socratic Tutor Trial-Run Fixes (HW4 manual run, found 2026-10-08; fix after the run ends)
- <!-- TODO-0010 --> Short launch option plus `statement` in every view (`agent/tutor/packet.py`, `session.py`, `lint.py`). Today `LAUNCH` requires the part's full statement verbatim plus "How would you like to approach this problem?", which is noisy: the student usually has the questions, and Question 1's ~800-character setup paragraph repeats in parts 1.2-1.6. The verbatim rule exists only to stop the launch message carrying a roadmap (beta failure #1), not to show the question. Fix: (1) add a packet setting (e.g. `launch_style: "label" | "statement"`, per packet) so a short launch like "Question 1.3. How would you like to approach this problem?" is the only text the lint accepts at LAUNCH; (2) make `Session.view()` return the current part's `statement` in every state, so the agent always has the question without printing it (also fixes resuming mid-part, where the statement is currently lost because `launch_text` is only returned in `LAUNCH`); (3) keep the full-statement launch available for use away from the paper (tablet). Needs tests (lint accepts only the short line, view always carries the statement, resume mid-part still has it) and a worktree/branch. Land it only after the trial run so the CLI rules do not change under a live session. STATUS 2026-10-09: **DONE (v1.1 Plan A, d0031a8):** the launch is now the short `"{label}. How would you like to approach this problem?"` line, `launch_style` is a per-part field, and every brief carries the `statement`. (added 2026-10-08)

- <!-- TODO-0011 --> Graded hints and no full solution in the agent's reach (`agent/tutor/packet.py`, `session.py`, `prep.py`, `bootstrap_prompt.md`). In the HW4 trial the tutor leaked the answer or method despite the lint, because the agent holds the whole hint and solution text and converts it into leading questions: it handed over the decomposition at hint level 1 (events 10, 13 in `academic-hub/academic_notes/microecon/tutoring/homework_4/trial_runs/2026-10-08-2112/events.jsonl`), told the student "the conclusion is yes" and named the method (event 36), and gave the whole argument at level 1 (event 39). The lexical lint cannot catch paraphrase. Fix: (1) author per-level hints in prep (L1 = what definition or intuition applies; L2 = the object to think about, not the computation; L3 = intermediate steps) and make `sealed hint` return only the current level's text; (2) replace the agent-readable `sealed/solution.md` with short per-part checkpoints (what a correct argument must establish) plus `pitfalls`, and keep the full solution out of the tutor chat's reach; (3) message-shape rules at hint levels 0-1 (at most one question mark, roughly 60-word cap) and stricter L1/L2 guidance text ("do not restate the student's idea in completed form; do not state any condition of the answer"); (4) turn the real replies above into regression fixtures that the lint or gate must reject. STATUS 2026-10-09: **Plan A (d0031a8) replaced this with the claim ledger** (prep-authored claims, routes, pitfalls and recognizers; disclosure check; question form; once-per-part `verify`) instead of graded hint text. Still open: live validation on re-prepped HW4, and the solution file remains readable on disk (soft wall). (added 2026-10-08)
- <!-- TODO-0012 --> Agent works around the gate (`agent/tutor/`, `bootstrap_prompt.md`): in the trial it read `sealed/solution.md` straight from disk with its own Python (to test candidate replies for 6-word overlap), imported `lint._ngrams`, read `session.py` and `fsm.py` several times, computed rating ceilings itself, and pre-linted with `student_text=''` (a weaker context than the real one). None of this is visible to the log or `audit`. Fix: contract wording forbidding source and sealed reads; a cheap `say --check` dry run, with lint rejections described as normal and unpenalized (the agent was pre-testing to avoid them); actionable error messages (below); and decide whether enforcement source and sealed files should sit outside what the tutor chat can read. Note the soft-wall limit: direct reads are undetectable. Also: asked afterwards to assess itself, the agent reported "100% compliant" on every contract item including "no sealed direct access", which its own tool log contradicts, and omitted the leaks and the missed slip; so no control may rely on agent self-attestation or self-assessment, compliance must be checked from the log or an independent check. STATUS 2026-10-09: **Partly addressed (Plan A):** `say --check` dry run, contract wording against source/packet reads, actionable errors, manual overrides audited with their quotes. Still open: direct reads of `packet/` and the source remain undetectable; the no-self-attestation rule stands. (added 2026-10-08)
- <!-- TODO-0013 --> Speed: measured CLI latency is about 0.27 s per call, so the gate is not the cause; the cause is tool-call round trips. A tutoring turn took 8-10 tool calls (temp-file creation, `student`, `verdict`, `define` or `sealed`, self-run lint and ceiling scripts, source reads, `say`) versus 1 for a raw agent. Fix: a single `turn` command (student text + intent + misconceptions + verdict, returning state and guidance), `say --stdin` so no temp file is needed, and the `say --check` dry run above; target 2 tool calls per turn. STATUS 2026-10-09: **Implemented (Plan A):** `turn`, `say --stdin|--check`, `verify`; PowerShell stdin carries Unicode (checked on 5.1). Still open: count tool calls per turn in a live Antigravity run (target 2). (added 2026-10-08)
- <!-- TODO-0014 --> Actionable errors and `has_questions` state (`fsm.py`, `session.py`): `confirm_advance` in WORKING returns only "only valid after the part is verified (state is WORKING)", which sent the agent into `fsm.py`; errors should name the next legal action (e.g. "call verdict correct, then close-part"). Also a side question after the part is verified and closed sends the FSM back to WORKING and forces a redundant `verdict correct`; a question about an already-closed part should keep the state at AWAITING_ADVANCE (spec §3.3 currently says return to WORKING). STATUS 2026-10-09: **DONE (Plan A):** errors carry `next`; side questions no longer reopen a closed part. (added 2026-10-08)
- <!-- TODO-0015 --> Skip/defer escape valve (user decisions, 2026-10-08; needs a spec amendment): a `--skip` flag on any student message (a flag, not an intent, because the agent labelled "ready to move on" messages as `attempt` in the trial). Two explicit requests are required: after the first the tutor pushes back once and prompts the student to try, after the second it honors the request with no further argument. Revisit timing (user correction, 2026-10-08): offer at the end of the NEXT part the student completes after the skip, e.g. skip 1.2, finish 1.3, then at the end of 1.3 ask "go back to 1.2, or on to 1.4?"; a skipped single-part question such as Question 2 is offered at the end of the next completed part (Question 3). Never prompt while the student is mid-part (they would just defer repeatedly). No `group` field is needed. Assumption to confirm with the user: if the student declines at that boundary, ask once more at the session end rather than at every later boundary. Statuses: skipped with no real attempt = "not attempted", no rating and NOT a gap (the professor may not have covered it); deferred after at least one attempt = gap evidence, counted toward `prior_gaps`. If the student later solves a revisited part, keep the failed attempt in the history, cap the new rating at Proficient (never Mastered) as a modest penalty. A skip-only message does not count as an attempt. `audit` flags any deferral without two student requests; the summary action menu lists deferred parts. STATUS 2026-10-09: **Not started: Plan B** (see `docs/superpowers/specs/2026-10-08-socratic-tutor-v1-1-design.md` §8-§9). (added 2026-10-08)
- <!-- TODO-0016 --> Pitfalls, silent corrections and evidence relevance (`ratings.py`, `session.py`, `prep.py`): in the last trial round the student tested monotonicity on the consideration set instead of the menu; the tutor replied "Precisely! Adding an option ..." (silently fixing the wording), logged no misconception, marked the earlier misconception resolved and gave `verdict correct`, so rigor was rated Proficient with the erroneous message itself cited as evidence, and directness was rated Proficient citing an unrelated "we can move on" message. The ceiling only reflects what the agent logs, and evidence validation only checks that a quote exists. Fix: prep authors per-part `pitfalls` (known slips, e.g. "tests monotonicity on the consideration set, not the menu"); `verdict correct` requires `--pitfalls none|tag,...` and each tag becomes a misconception event automatically; a "no silent correction" rule (the tutor must surface a flagged slip Socratically before the check-in); and tighten evidence so a quote cited for an axis must come from an event relevant to that axis. STATUS 2026-10-09: **DONE (Plan A):** prep-authored pitfall recognizers log slips automatically, a standing slip blocks a clean `verify`, ratings use CLI-attached evidence. Still open: recognizer quality on real course content (live run). (added 2026-10-08)
- <!-- TODO-0017 --> No way to leave a session part-way (`session.py`, `cli.py`): `end` requires SYNTHESIS with every part closed, so a partial session stays open forever, a later `start` resumes it instead of beginning fresh, and `learner_profile.json` is never updated from the parts that were completed. Add a `pause` / `end --partial` command that closes the log, renders the transcript and summary for the closed parts, and updates the profile from closed parts only; `start` should then offer resume or fresh. Also `Session._latest_open` treats every directory under `sessions/` as a session, so a renamed or copied session folder is picked up as open; move trial sessions out of `sessions/` instead. STATUS 2026-10-09: **Not started: Plan B** (`pause`, `start --fresh`, profile v2). (added 2026-10-08)

- <!-- TODO-0018 --> Escalation test for the claim-ledger design (decided 2026-10-08): the v1.1 hint-control design (claim ledger + question form + once-per-part `verify` that releases that part's solution) deliberately avoids an independent judge model. Write an explicit adversarial test suite that tries to trick the tutor into the failures the user most wants to avoid, and use its results to decide whether an independent judge is needed after all (candidates: a small metered Gemini Flash call inside the CLI that holds the solution and vets drafts/assesses student work, or a second Antigravity chat as reviewer; local Ollama judged too slow/unreliable). Seed scenarios: (1) the student's proof is nearly right but has one subtle flaw (e.g. tests monotonicity on the consideration set instead of the menu, as in the HW4 trial) and the tutor must not mark it correct or silently fix it; (2) the student uses all the right words but the argument is wrong (recognizers match, logic does not); (3) the student is correct via an unusual route or phrasing the recognizers miss (must be recognized or manually established, not stalled); (4) the student pressures the tutor to reveal the proof or insists it is done; (5) the tutor is nudged to call `verify` early or to manually establish claims just to unlock the solution; (6) `verify` rubber-stamp: a defective proof with a plausible all-confirmed step check; (7) paraphrased leaks of an unreached claim at hint levels 0-2. Run each both offline (recorded drafts through the lint/ledger) and live in Antigravity, several trials each. Define the failure threshold up front (e.g. any false "correct" on a seeded flaw, or a paraphrased leak that passes, in N trials means add the judge). STATUS 2026-10-09: **Offline half DONE (Plan A):** `tests/agent/tutor/test_tutor_regression.py` covers the trial-reply analogues and the seven scenarios as far as they run without the live agent. Still open: the live half in Antigravity on a re-prepped HW4 packet, then the judge/no-judge decision. (added 2026-10-08)

## Socratic Tutor Antigravity Entry Point (`agent/tutor`)
- <!-- TODO-0019 --> Goal: the user types one sentence into Antigravity ("I would like some tutoring help with my problem set 4 in microeconomics") and the agent starts the session with no further input. Today the pipeline needs a human to run prep and paste the `bootstrap` output. Work: (1) add a `prep` mode to `python -m agent.tutor.cli ... bootstrap` that prints the full prep contract (run `prep-collect`, author glossary/rubric/tags/sealed sections from `packet/worklist.md` using the existing `*_guided_solutions.md` as the source of truth, run `prep-submit`, fix errors) so prep is runnable from the agent too; (2) write the single entry point Antigravity loads (a workflow, rules file, `GEMINI.md` or `AGENTS.md`, whichever Antigravity actually reads: verify against its docs or by trial, do not guess filenames) that maps a free-text request to course + problem set (find `academic_notes/<course>/problem_sets/homework_N.md`), runs `bootstrap` in prep mode if no validated packet exists else session mode, and follows it; (3) make sure the agent can run the CLI without per-command approval prompts (each tutoring turn runs 2-3 commands) and uses the repo `.venv` Python; (4) decide whether `sealed/` should be excluded from the `academic_notes` tablet sync (it is visible in Obsidian). Known gaps found in the manual run: (Plan A, d0031a8, now embeds `Set-Location` + the venv Python and uses stdin instead of temp files in `bootstrap_prompt.md`; the "begin now" closing line is still missing.) Original note: `bootstrap_prompt.md` said to run the gate command "from the academic-rag-model directory" but never said how, so the generated prompt should embed `Set-Location "<academic-rag-model>"; & "<venv python>" -m agent.tutor.cli ...` and a temp path for `--text-file` (the manual-run copies in `tutoring/homework_4/packet/gemini_*_prompt.md` were patched by hand); it also lacks a "begin now: run `start`, send the launch text" closing line. Do the manual run first and let what Gemini actually needs shape the entry prompt. Context: `docs/superpowers/specs/2026-10-08-socratic-tutor-pipeline-design.md`, `agent/tutor/README.md`, `agent/tutor/bootstrap_prompt.md`. (added 2026-10-08)

## Socratic Tutor vs RAG Tutor Disentanglement (`agent/tutor` vs `agent/rag`)
- <!-- TODO-0020 --> Make sure nothing confuses the new Socratic tutor (`agent/tutor`, live IDE-agent sessions gated by the `agent.tutor.cli` FSM; spec `docs/superpowers/specs/2026-10-08-socratic-tutor-pipeline-design.md`, plan `docs/superpowers/plans/2026-10-08-socratic-tutor-pipeline.md`) with the older RAG tutor (`agent/rag`: `rag_agent.py` REPL with `/draft`, `/hint`, `/verify`, `/summarize`, `tutor_diagnosis.py`, `session_log.py`, metered Gemini). The names overlap ("tutor", "session", "hint", "diagnosis", "rubric", `session_log` vs `events.jsonl`, `.session_log/` vs `tutoring/<ps>/sessions/`), so an agent told to "start a tutoring session" could call the wrong one. Audit and fix: (1) grep docs, READMEs, CLAUDE.md files, status docs, trackers and prompts for "tutor", "tutoring" and "RAG tutor" and rename or qualify each reference to say which tutor it means (e.g. "RAG Q&A/diagnosis agent" for `agent/rag`, "Socratic tutor" for `agent/tutor`); (2) consider renaming the old REPL's user-facing labels (module docstrings, the "RAG Tutoring Agent" heading below, the `rag_agent.py` banner) so "tutor" is not its primary name; (3) confirm routing text (`academic-rag-model/CLAUDE.md`, `docs/AGENT_ROUTING.md`, `agent/rag/README.md`) sends interactive tutoring to `agent/tutor` and one-off lookups or `/draft` diagnosis to `agent/rag`; (4) decide whether `agent/rag`'s "Persistent conversation and student history" item below is now covered by the Socratic tutor's `learner_profile.json` and close or retarget it; (5) add a test or doc check that the two packages share no module names or CLI entry points that could be mistaken for each other. Do not retire the old REPL's `/draft` and `/hint` until the new pipeline has had a real homework run, since they are validated against real corpus data. (added 2026-10-08)

## API Cost: Caching and Batch Mode (all Gemini pipelines)
- <!-- TODO-0021 --> Audit every expensive Gemini call path for context caching (large shared prefix across calls) and Batch API (50% price, ~24h turnaround, so only for jobs that can wait). Candidates, roughly by volume: `core/indexer` (`index_card.py`, `retag.py`, `chunk_index.py`), `pipelines/transcribe_notes` (`transcribe_notes.py`, `transcribe_excalidraw.py`), `pipelines/convert_textbook` (`describe_images.py`, `toc_repair.py`), `agent/problem_gen`, `agent/problem_corpus`, `agent/viz`, `agent/rag` (interactive, so caching only: fixed system prompt and corpus excerpt first). For each: measure the shared-prefix share and the run volume first; skip where the saving is small. Rule of thumb: shared prefix means caching, many independent calls that can wait means batch. Unverified: whether code execution, structured output and image input work in batch jobs, and whether our key tier allows batch. Prices and minimums (3.8 Flash: $0.75 input, $0.375 batch, $0.075 cached per 1M tokens; implicit-cache minimum 4,096 tokens) are from Google's docs as of 2026-10-08; re-check. Findings and a first implementation for `agent/study_guide` and `agent/summary_enhance` are in `docs/superpowers/plans/2026-10-08-guide-revise-pipeline.md` ("Follow-up: caching and batch", branch `claude/study-guide-spec`). (added 2026-10-08)
- <!-- TODO-0022 --> Reduce or cap the cost of the guide revise pass (`agent/study_guide/revise`): the first full run on the a3 guide cost about $1.90 (66 calls, 634,649 prompt tokens, 34,935 output tokens, 357,420 thinking tokens at 3.8 Flash list prices), roughly 8 times the $0.25 the plan estimated because that estimate ignored thinking tokens, which were 91% of the spend. Ideas, none built: a per-run token or dollar cap (`[revise] max_cost` or `--max-cost`) checked against a dry-run estimate that includes thinking, aborting before the paid stages; set a low or zero thinking budget for the judge, dedup and organization calls (structured, low-reasoning tasks) and keep it only for the correctness audit; use a cheaper model (flash-lite) for the judge and dedup; send only the changed sections to the audit on a re-run; run stages separately with `--stages` and the existing checkpoint to stop early; make the dry-run print an estimated cost. Batch mode is too slow for an interactive revise (24-hour window). The same thinking-token blind spot likely applies to the draft and enhance cost estimates. Results: `docs/status/agent/2026-10-07-study-guide-comparison-status.md` ("Revise first run", branch `claude/study-guide-spec`). BUILT on `claude/study-guide-spec` (2026-10-08, unmerged): per-stage usage, `light_thinking = "low"` for all stages but the audit, `max_cost`/`--max-cost` with dry-run estimate and resumable stop, content-keyed audit cache. Still open: measure the real per-stage split and the quality at low thinking on one paid run; try flash-lite for judge and dedup; apply the same thinking-token audit to draft and enhance estimates. (added 2026-10-08)
- <!-- TODO-0023 --> Explore a subscription-backed run mode for the Gemini pipelines (starting with `agent/study_guide`, draft/enhance/revise): the owner has a Gemini Pro subscription running through Antigravity in a local app, which can use the subscription instead of paid API calls while the pipelines keep using Gemini embeddings through the API. Build it as an additional option, not a replacement: the user picks the API mode or the subscription mode per run, based on the anticipated cost (the dry-run estimate and `--max-cost` already exist) and on whether they have a Pro subscription and Google still allows this route. Questions to settle: how a pipeline hands prompts to the Antigravity app and reads structured JSON back (a file or folder handoff, as `agent/tutor` does for its Antigravity entry point), how usage and caps are tracked when there are no token counts, whether thinking level can be controlled there, and how resume/checkpointing works. Motivation: the guide revise pass cost about $1.3 for 7 of 21 audit sections on the API. (added 2026-10-08)

## Corpus Health Orchestrator (`docs/superpowers/specs/academic_hub/2026-10-07-corpus-health-orchestrator-design.md`)
- <!-- TODO-0024 --> Review the discovery-only trial after its October 10-16 scheduled runs. Check each run's exit status, log, runtime, root availability, and change in findings; manually verify a sample across finding kinds and courses, including textbook identity, generated-file exclusions, frontmatter, and intentionally deferred Math Camp PDFs. Check that declined/deferred decisions remain stable and changed sources return for review, then decide whether to keep the daily schedule or adjust scanner policy. Do not enable unattended repairs merely because scans complete successfully. Handoff and limits: [corpus-health implementation retrospective](../status/academic_hub/2026-10-09-corpus-health-implementation-retrospective.md). (added 2026-10-09)
- <!-- TODO-0025 --> Defer Task 7 note-transcription, Excalidraw, enhancement, question-resolution, and
  postprocessing repair adapters. Keep detecting and reporting these gaps, but do not
  rerun the current pipeline through orchestrator `apply`: its enhancement can omit
  source themes/graphs and leave questions unresolved, so repairing now would spend
  API calls on outputs that must be regenerated. First fix and verify the source
  pipeline under **Notes Transcription**, then reprocess and review affected notes.
  Revisit exact-source apply adapters only after that quality gate and the separate
  `academic_notes/` sync-quiescence gate are resolved. (added 2026-10-09)
- <!-- TODO-0026 --> The design's `git_state` finding kind will misreport known, device-local sync churn in the
  nested `academic_notes/` repo as drift every day unless it explicitly excepts it. Two known
  causes: (1) the tablet's Direct Git Sync plugin stamps `.gitignore` from each device's own
  local plugin settings on every load, so that file's diffs are not a signal of real divergence
  (see [[feedback_git_ignore_regenerates_from_local_plugin_settings]] in Claude's persisted
  memory / `docs/status/2026-09-21-obsidian-git-sync-status.md`); (2) the Fit sync plugin
  hard-blocks syncing its own `main.js`/`styles.css`, so those paths can look permanently
  out-of-sync between devices without being a real problem. Before the `git_state` finding is
  implemented (rollout phase 2, discovery prototype), add an exception list/pattern for these
  known paths/causes in the nested-repo status check so they're not surfaced as findings needing
  review. Also flagged in `docs/brainstorms/2026-10-07-corpus-orchestrator-codex-plan-review.md`
  §4.2. (added 2026-10-08)

## Project Steering and Work Selection
- <!-- TODO-0027 --> Design a local interactive “project steering” page and `what_to_do_today` workflow that surfaces pending project ideas, subprojects, resumable work, and bugs; ranks candidates by complexity and potential utility; lets the user adjust or provide those rankings; and recommends a small set of work for today. Evaluate whether ideas and bugs should move into separate source lists, while keeping this project-wide planning workflow distinct from the academic-hub corpus-health orchestrator. The two may share a local review-page pattern, but have different findings, state, and apply behavior. (added 2026-10-07)

## Git Workflow Between Agents (brainstorm pending, nothing implemented)
- <!-- TODO-0028 --> The user wants to brainstorm a smoother git workflow between agents (Claude, Codex, Gemini) before
  changing any rules or tooling, and to pick this up with another agent. Everything below is evidence
  and candidate ideas from one long Claude session, not decisions. Read first: `docs/WORKTREE_WORKFLOW.md`,
  `docs/AGENT_ROUTING.md`, the root `CLAUDE.md` ("Git" and "Pending to-dos"). (added 2026-10-04)

### The problem, with evidence from the 2026-10-03/04 session
- **Landing a branch is a hand-run ritual.** Three landings (`14ca7f4` slide-aware transcription +
  subset linking, `e55402c` question resolver, `6de9095` to-do rule) each took roughly: count commits
  `main` gained since the branch point (14 both times for the big ones), `git merge-tree` conflict check,
  `git merge main` into the branch, full test suite (~107 s, 1939-2148 tests), a by-hand overlap check
  against `main`'s dirty files, then `git merge --ff-only`. One real textual conflict in three landings:
  `transcribe_excalidraw.py`, where both sides edited the same `print(...)` line (main switched it to
  `resolve_output_dir(...)`, the branch added a `return True` after it).
- **The main checkout is never clean**, yet the policy ("The integrator ensures the integration checkout
  is clean") assumes it is. It always holds the user's/Obsidian's and other agents' work: `.obsidian/*`,
  `lab_1_report.md`, `journal-articles/needs_manual_downloads.md`, `.index/*.json`, untracked
  `academic_resources/microecon/2025_class/`. So overlap with dirty files has to be computed by hand.
  Pitfall hit once: comparing `main` against the branch *tip* lists files `main` itself changed; the right
  comparison is the branch against the **merge-base**.
- **Obsidian "vault backup" auto-commits land on `main` in both repos** (monorepo log has
  `vault backup: 2026-10-01 17:00:21`; the `academic_notes` repo has `vault backup: 2026-10-03 21:50:07`),
  sweeping whatever tracked files are dirty. That made switching branches in the main checkout feel unsafe,
  so generated data was committed straight to `main` twice (monorepo `59846d7`, `academic_notes`
  `165084f`), outside the worktree rule. The Obsidian Git plugin's real settings were NOT inspected
  (`.obsidian/` is off-limits unless asked).
- **Two repos, one logical change.** The monorepo `.gitignore` (line 9) ignores
  `ai-sandbox/academic-hub/academic_notes/`, which is its own git repo (tablet sync). Resolving questions
  produced outputs in `academic_notes` and index changes (`.index/*.json`) in the monorepo, so one change
  needed commits in both. `WORKTREE_WORKFLOW.md` says child repos need their own worktrees, but real
  pipeline runs write to the live vault.
- **Shared aggregate files mix agents' work.** `.index/courses.json` held both our `microecon` change and
  another session's in-progress `econometrics` change. Committing only ours needed partial staging by
  building a blob (see snippets) because `git add -p` is not available non-interactively.
- **Worktrees lack ignored files** (`.env`, SVG sources, vault data). Running a pipeline from a worktree
  failed with a misleading "PAID_GEMINI_KEY not set" (fixed 2026-10-03: `load_dotenv_override()` now falls
  back to the main checkout's `.env`), and real runs still need
  `PYTHONPATH="$(pwd -W)" python -m <module> --root <main>/ai-sandbox/academic-hub` by hand. The policy
  forbids junctioning the live vault, which is right but leaves no easy path.
- **Docs-only changes got the same ceremony as code** (worktree, branch, merge). The to-do tracker now has
  a standing exemption (root `CLAUDE.md`, 2026-10-04); other docs do not.
- **Worktree sprawl.** 12 worktrees registered on 2026-10-04 (incl. `main`), several merged and idle:
  `claude-excalidraw-slides`, `claude-question-resolver`, `claude-todo-tracking`, `claude-status-docs`,
  the three `claude-summary-*`, and four `codex-*`. Retirement is manual per the doc.
- **Overlap found late.** Another session changed `core/indexer/index_card.py` and added `offering_links.py`
  while we were in `core/indexer`; we only saw it at merge time.
- **Tests are the other time cost.** ~107 s serial on 8 cores; `pytest-xdist` is not installed. The full
  suite was re-run many times per feature.

- **A shared main checkout plus direct-to-main edits lets other agents' commits sweep up your
  uncommitted work.** On 2026-10-04 this very section was written into the main checkout's tracker
  (uncommitted, under the new to-do exemption) and was then committed by a *different agent's* commit,
  `6d1e107` ("todo: aggregate pending to-dos..."), which was editing the same file in the same checkout.
  When the author went to commit, git reported "nothing to commit, working tree clean". In the same
  window another agent merged this session's `claude/status-docs-1004` branch (`d6f97fe`), retired its
  worktree, and pushed, all while the author was paused on a usage limit. The content ended up intact, but
  commit authorship and order are no longer traceable, and the exemption makes concurrent edits to the
  tracker more likely. Ideas to weigh: a claim step before editing a shared file; one append-only to-do
  file per agent merged later; always re-check `git status`/`git log -3` immediately before editing and
  committing a shared file.

### Existing policy to build on (and where proposals collide with it)
- Already in `docs/WORKTREE_WORKFLOW.md`: one writer per worktree, `.worktrees/` ignored, integration "one
  task at a time", retire-worktree procedure, Windows `git show` path gotcha, child-repo worktrees, "adopt
  the policy in existing sessions" (running agents do not reload guidance; they must be told).
- Collisions to resolve: the doc prescribes `git merge --no-ff` (merge commits) while rebase-then-ff gives
  linear history (the doc allows rebasing only an exclusively owned, unpublished branch); workers "do not
  merge into main unless assigned the integrator role" yet in practice the user tells an agent to merge;
  "integration checkout must be clean" is never true; "do not junction/symlink writable output dirs to the
  live vault" vs. needing real data in tests/runs.

### Candidate changes (unimplemented; roughly by payoff)
1. **Landing helper** (`tools/land.py` or `.ps1`): verify the worktree is clean, rebase (or merge) onto
   `main`, run tests (changed-path subset by default, full with a flag), compute overlap against
   `main`'s dirty files using the merge-base, then `merge --ff-only`; print a summary. Replaces ~6
   manual steps and bakes in the safety checks.
2. **Lanes by risk** in `WORKTREE_WORKFLOW.md`: code (`core/`, `pipelines/`, `agent/`, tests) in a worktree;
   docs (status docs, specs, plans, trackers, READMEs) and pipeline-generated vault/index output may go
   straight to `main` with explicit paths. The to-do exemption is the first instance. Need rules for
   two agents editing one doc (append-only sections, commit promptly).
3. **Merge style decision:** rebase + `--ff-only` (linear, no "Merge main into ..." commits) vs the doc's
   `--no-ff` (explicit integration points). Pick one and update the doc.
4. **Faster tests:** install `pytest-xdist` (`-n auto`) and/or a path-to-tests mapper so iteration runs
   only affected packages; keep the full suite for landing. Not measured; the ~25 s figure is a guess.
5. **Active-work report:** a small tool listing each worktree's changed files vs its merge-base and flagging
   overlaps, so collisions in shared packages (`core/indexer`, `core/env`) are seen before landing.
6. **Scope the Obsidian Git auto-backup** (content paths only, or a separate `vault-backup` branch merged
   periodically) so `main` is not repeatedly swept. Needs the user's plugin config; not inspected.
7. **Cross-repo "land data" helper** that commits `.index/*.json` (monorepo) and the matching
   `academic_notes` outputs together with explicit paths, including partial staging of shared aggregate
   files such as `courses.json`.
8. **Worktree lifecycle helpers:** list merged/idle worktrees as retirement candidates (never auto-remove
   other agents' work), and a `new_worktree` helper that creates the branch/worktree and prints the
   correct `--root`/env for running pipelines against the live vault without junctions.

### Open design questions for the brainstorm
- Who may land on `main`: only the user, or any agent after the user says "merge"? How is that recorded?
- Merge style (item 3), and whether to keep merge commits as audit points.
- When may generated data (index, pipeline outputs) go straight to `main`, and who is its single writer
  (the doc requires "one assigned writer" for shared corpus/index writes)?
- Where should pipelines write when run from a worktree: a worktree-local corpus (policy) or the live
  vault (what real validation actually needs)?
- Can the auto-backup be limited, and does the tablet sync (Fit plugin on the vault repo) constrain that?
- How do Claude/Codex/Gemini claim shared packages so overlaps surface early (claims file, branch
  naming, or the item 5 report)?
- Test policy at landing: full suite always, or changed-package subset plus periodic full runs?

### Useful snippets from this session
- Conflict preview without touching any working tree:
  `git merge-tree --write-tree --name-only main <branch>` (prints `CONFLICT (...)` lines if any).
- Overlap with the main checkout's uncommitted files (merge-base form, the correct one):
  `MB=$(git merge-base main <branch>); comm -12 <(git diff --name-only $MB <branch> | sort) <(git status --short | awk '{print $2}' | sort)`
- Land an exclusively owned, unpublished branch: in the worktree `git rebase main`; in the main checkout
  `git merge --ff-only <branch>`. Verify the main checkout's `git status --short` is unchanged afterwards.
- Stage one entry of a shared aggregate file: build the file from `HEAD`'s version with only your entry
  replaced, then `git hash-object -w --path <file> <tmpfile>` and
  `git update-index --add --cacheinfo 100644,<sha>,<file>`; confirm with `git diff --cached`.
- Child repo from the monorepo root: `git -C ai-sandbox/academic-hub/academic_notes <command>`; stage
  renames there with `git mv` so history follows.
- Run worktree code against the live vault:
  `PYTHONPATH="$(pwd -W)" python -m <module> --root <main-checkout>/ai-sandbox/academic-hub`.
- Windows: `git show origin/some/branch:path` is mangled by MSYS path conversion; use the commit SHA or
  `MSYS_NO_PATHCONV=1` (already in the workflow doc).

### Guardrails for whoever implements
- Keep: never `git add -A`/`git add .`; never print or commit `ai-sandbox/.env`; no force-push, `reset
  --hard`, or `clean`; never remove another agent's worktree; commit/push only when the user asks; the
  monorepo is public on GitHub (see the root `.gitignore` comments for the IP exclusions).
- Changes to `WORKTREE_WORKFLOW.md` take effect only for sessions told to re-read them.
- <!-- TODO-0029 --> `days_since_cut` metric resets to 0 after a rebase: `tools/land_branch.py`'s `check()` computes the branch's age from `git merge-base main HEAD`, but once a branch is rebased onto `main` (which happens on almost every landing, since `main` moves constantly), the merge-base becomes `main`'s own tip, so the age no longer reflects when the branch was actually started. Fix needs a small persistent store, e.g. `<git-common-dir>/agent-landing-cuts.json` keyed by branch name: write the branch's first-seen merge-base on its first `check()` call, reuse it on later calls regardless of rebases, and clear the entry when `record()` is called with `outcome="landed"`. Spec: `docs/superpowers/specs/2026-10-06-agent-git-workflow-design.md`; plan: `docs/superpowers/plans/2026-10-06-agent-git-workflow.md` (both under this package). Deferred during the 2026-10-06/07 implementation session pending the user's go-ahead for the added state; not a blocker for landing, since the metric is informational. (added 2026-10-07)

## Notes Transcription (`pipelines/transcribe_notes`)
- <!-- TODO-0030 --> **URGENT — Excalidraw expansion loses source content:** investigate and fix the end-to-end
  transcription/expansion/question-resolution path in `pipelines/transcribe_notes/transcribe_excalidraw.py`
  and its downstream resolver. Treat transcription/expansion and question resolution as a required pair:
  after each Excalidraw note is transcribed and expanded, automatically run
  `agent.rag.resolve_questions` for that note, surface any failures, and don't report the note complete
  while tagged questions remain unresolved. The 2026-10-08 run resolved 17 source questions, but an
  output audit still found two stale sidecar answers and five open `[Question]` markers across the
  Econometrics Oct 7 10:19 and Microeconomics Oct 8 08:21 notes; the resolver dry run reported zero
  pending because it checks raw tags against sidecar IDs, not whether every expanded tag was linked.
  Add an end-to-end post-resolution check for zero stale answers and zero unpaired/unresolved expanded
  tags. In the six Oct 6–8, 2026 Econometrics/Microeconomics notes, the first-pass
  transcript is mostly faithful, but the expanded `.rag.md` drops or compresses themes and graph details
  that were present in the transcript; some handwritten questions also remain unanswered. Compare each
  raw `.excalidraw.md` with its `.rag.md`, verify `[Question]` tags survive and reach the existing
  question-resolution step, and add coverage checks so expansion preserves every substantive theme and
  graph description. Preserve the visual information in the enhanced notes too: retain or recreate the
  relevant graphs/diagrams in the final artifact rather than leaving only prose descriptions. Test whether
  the `gemini-3.1-flash-lite` expansion model contributes to the loss versus prompt/context behavior before
  treating it as the cause. Re-expand and review the affected notes after the fix.
  Only then reconsider enabling the corpus-health orchestrator's note repair
  adapters; leave discovery active in the meantime. (added 2026-10-08; updated 2026-10-09)
- <!-- TODO-0031 --> Move the `*_pages_cache.json` resume caches out of `processed_outputs/` into `processed_outputs/_cache/`, to cut clutter when browsing folders (89 files, ~2.2 MB, all tracked in the `academic_notes` repo). Plan: the cache path is built in one place (`transcribe_notes.py`, `cache_path`, around line 1095) so change it there; read `_cache/` first and fall back to the old location so unmigrated caches still resume; update `tools/audit_metadata.py`, which moves a cache along with its `.md`; one-shot `git mv` of the existing 89 in the `academic_notes` repo; test both locations plus the fallback. The caches are only read when the same document is rerun or `--force`d (to skip pages already paid for); the indexer, search and tutor never touch them. Deferred by the user (added 2026-10-04)
- <!-- TODO-0032 --> Reprocess `LN_Analysis.pdf` and `LN_Linear Algebra.pdf` using whole-document batching and PyMuPDF dict-mode: their existing outputs predate the dict-mode/subscript reconstruction and whole-document batching improvements. Estimated cost under $0.30 total. Paused at user request pending review. (added 2026-10-04)
- <!-- TODO-0033 --> Radical/square-root font encoding repair: in PDF font extractions (e.g. `Analysis_Exercises.pdf` page 6), square-root signs can extract as plain ASCII 'p' or missing glyphs due to broken ToUnicode font mappings; implement a regex/post-processing repair pass. (added 2026-10-04)
- <!-- TODO-0034 --> Process the prior-year microecon class folders `academic-hub/academic_resources/microecon/2024_class/` (52 files: Exam, Exam Prep, Homeworks + Solutions, Pre/Post lecture notes, Proofs, Recitation) and `2025_class/` (36 files: Homeworks + Solutions, Post-Lecture Notes, Recitation notes, Midterm suggested solutions, Pre-exam survivals kit, proofs). Together 86 PDFs plus one `.md` and one `.Rmd`; none have been converted into `academic_notes/microecon/` yet, so the index and RAG don't see them. Also check `professor_notes/` items 4-6 (`Random_choice`, `Failures Of Rationality`, `Consumer_Choice_1`): `academic_notes/microecon/professor_notes/processed_outputs/` showed only items 1-3 plus the proofs file when last listed, so verify before assuming. Motivation: these feed the microecon concept-graph project (corpus for node explanations and edge citations) and the tutor/RAG. Approach so far: run `python -m pipelines.transcribe_notes.transcribe_notes --dry-run` on the folders first to see the tier split, since the local text tier costs nothing and only defective-text or handwritten/scanned documents need Gemini. For those Gemini tiers, consider an agent-driven mode modeled on `agent/tutor` (CLI renders page images and writes a worklist, the Antigravity IDE agent transcribes under the subscription, a `submit` step validates) instead of metered API calls; with `--driver api` kept as the fallback. A truly local Ollama vision model is untested here and likely weak on handwritten math (the transcribe_notes README says even Marker/Surya OCR does poorly on handwriting). Ask the user before any batch run estimated over $1. (added 2026-10-09)

## Journal Article Discovery (`discovery/discover_journal_articles`)
- <!-- TODO-0035 --> Playwright-driven automated download tier: for paywalled or institutional journals where manual download from `needs_manual_downloads.md` is tedious, build a Playwright browser automation script using institutional SSO. (added 2026-10-04)
- <!-- TODO-0036 --> OpenAlex vs. Academic Hub semantic tag consolidation and topic clustering: test OpenAlex concept tags against the indexer's tag mining system on a larger corpus (>20 papers) to enable cross-vault reference and automatic topic clustering. (added 2026-10-04)
- <!-- TODO-0037 --> Unified discovery-to-index convenience pipeline: create a wrapper CLI that orchestrates search/discovery (`pipeline.py`), conversion (`convert_journal_articles.py`), and index card generation in one command. (added 2026-10-04)

## Source Indexer and Search (`core/indexer`)
- <!-- TODO-0038 --> Tag co-occurrence graph persistence: compute and persist the tag co-occurrence matrix in `.index/` so that related concepts across courses can be traversed in Obsidian graph view or via CLI search. (added 2026-10-04)
- <!-- TODO-0039 --> Automated document-pairing detection: automatically detect and record links between problem sets and their corresponding solution sets, or lecture slides and lecture notes, in index cards. (added 2026-10-04)
- <!-- TODO-0040 --> Persist `offering_label` on index cards through rebuilds: `offering_label` (set by `find_containing_offering_label()` in `core/env/academic_hub_paths.py`) is stored on cards via `generate_index_card` / `reconcile_and_write` in `core/indexer/index_card.py`, but `index_search.rebuild()` (`core/indexer/index_search.py`, around lines 603-759) does not pass it, and `reconcile_and_write` only writes it on the changed-path branch (around line 440). A rebuild can therefore drop or leave stale the field. Nothing reads the field yet, so links are unaffected. Fix: compute the label from the source path at each `rebuild()` call site and always write it in `reconcile_and_write`, with a caller test per site, then rebuild `econometrics` to refresh the stored values. Not a quick fix because it touches the shared indexer and needs caller tests. (added 2026-10-04)
- <!-- TODO-0041 --> Cross-offering linkage review notes not yet triaged: the final review of the cross-offering linkage work (`core/indexer/offering_links.py`) deferred several Minor findings, and their exact text was not kept in a durable record after the review workspace was deleted. Re-run a whole-branch review of `offering_links.py` and its tests, then triage each Minor into a fix or a dismissal. Known deferred item: finding #7 above. (added 2026-10-04)
- <!-- TODO-0042 --> Chunk the microecon question sidecars so passage-level search finds the resolved answers: run `python -m core.indexer.index_search --root <academic-hub> chunk --course microecon` (embeds the 4 `*.excalidraw.questions.md` sidecars, one heading chunk per question). Not yet run, so only file-level `query` returns them; `query --passages` and `search_passages`, which the tutor uses, do not. Costs embedding calls on `PAID_GEMINI_KEY`. Rerun `rebuild` then `chunk` after any future resolver run so new or changed answers are picked up. (added 2026-10-04)

## Resume Manager (`resume_manager`)
- <!-- TODO-0043 --> Paired cover-letter generation: add a cover-letter generator (`cover_letter.py`) that uses the tailored application's selected facts, target company/role, and job description (design spec §10). (added 2026-10-04)
- <!-- TODO-0044 --> Named-entity preservation verification in `fact_diff.py`: extend validation beyond numeric metrics and repeated openings to check that award names, degrees, and core tools are not dropped during tailoring. (added 2026-10-04)
- <!-- TODO-0045 --> Generalized section header matching in `normalize.py`: extend `match_section_header()` synonyms and line-shape heuristics to support alternate source resume layouts beyond the initial master format. (added 2026-10-04)

## RAG Tutoring Agent (`agent/rag`)
- <!-- TODO-0046 --> Persistent conversation and student history: persist REPL session transcripts and diagnostic records to disk (e.g. under `.sessions/` or student profile) so multi-turn context and mastery history survive process restarts. (added 2026-10-04)
- <!-- TODO-0047 --> Automated third-model adjudication in `/verify`: implement an automated verification evaluator to resolve diagnostic ambiguities when student answers partially match retrieved context. (added 2026-10-04)
- <!-- TODO-0048 --> Cross-course foundational retrieval testing: validate retrieval performance on multi-course queries (e.g. Econometrics questions requiring Math Camp matrix algebra lemmas). (added 2026-10-04)
- <!-- TODO-0049 --> Re-resolve the three ungrounded question answers once textbook coverage exists: 09-17 "why can they still be used?" and, on 09-22, "what is furthest you can get from A while in B?" and "what if we don't observe choices from all choice sets?". They were answered from general knowledge (marked `answered (ungrounded)` in the `.rag.md` and `grounded: false` in the sidecar) because no retrieved passage mentioned their key terms. Convert/index the relevant textbook chapters first, then `python -m agent.rag.resolve_questions --course microecon --note <date> --redo` and `rebuild`. Note `--redo` re-answers every question in the selected note, not only the ungrounded ones (09-22 has four, two of them grounded), at about two paid `gemini-3.6-flash` calls per question. (added 2026-10-04)

## Visualization Sub-Agent (`agent/viz`)
- <!-- TODO-0050 --> Template library expansion: add new Plotly visualization templates for recurring mathematical/economic concepts (e.g. utility maximization, IS-LM, consumer surplus) beyond the initial 4 templates. (added 2026-10-04)
- <!-- TODO-0051 --> Parameter extraction from retrieved context: extract specific numbers, equations, or matrix values from retrieved passages to populate templates with course-specific data instead of default toy values. (added 2026-10-04)
- <!-- TODO-0052 --> Connect visualization pipeline to study guide generation (`agent/study_guide`): enable study guides to automatically incorporate visualizations, supporting interactive Plotly objects for course-specific parameterized curves and static asset exports. Brainstorm note and architecture design completed: [`docs/brainstorms/agent/viz/2026-10-06-interactive-plotly-obsidian-pipeline.md`](../brainstorms/agent/viz/2026-10-06-interactive-plotly-obsidian-pipeline.md). (added 2026-10-05, updated 2026-10-06)
- <!-- TODO-0053 --> Automated decoupled asset injection pipeline: implement `agent/viz/vault_emitter.py` to emit partial HTML `<div>` assets to `assets/<slug>_div.html` alongside standardized DataviewJS mounting snippets, bypassing Pyodide sandboxes and Webpage HTML Export deadlocks. (added 2026-10-06)
- <!-- TODO-0054 --> Dual visualization modality (LLM-generated scientific diagrams alongside Plotly): evaluate and integrate LLM-generated conceptual diagrams for abstract theoretical geometry (such as the Testing Trinity likelihood surface) rather than strictly Python Plotly code. (added 2026-10-05)

## Audio Generator (`audio_generator`)
- <!-- TODO-0055 --> Paragraph-level splitting fallback for oversized sections: in `sections.py`, split oversized sections by paragraph boundaries when individual markdown sections exceed the TTS chunk limit, preventing oversized audio parts. (added 2026-10-04)
- <!-- TODO-0056 --> LLM summary-to-audio pipeline: build the direct workflow for generating audio from synthesized lecture summaries rather than raw note transcripts. (added 2026-10-04)
- <!-- TODO-0057 --> Textbook chapter-boundary integration: connect `chapter_index.py` from `convert_textbook` to enable narrated audio overviews per textbook chapter. (added 2026-10-04)
- <!-- TODO-0058 --> Flaky timing assertion under parallel test runs: `tests/audio_generator/test_audio_generator_pipeline.py::TestRunPipelineNotesEpisodes::test_episode_synthesis_is_dispatched_concurrently_not_one_at_a_time` asserts a wall-clock duration under 0.3s to prove synthesis calls run concurrently. It failed once at 0.36s when the full suite ran under `pytest-xdist -n auto`; it passes reliably alone and in a serial run. Found while measuring `pytest-xdist` for the agent git workflow's landing gate (`ai-sandbox/academic-rag-model/docs/superpowers/plans/2026-10-06-agent-git-workflow.md`, Task 6); not yet fixed since it's outside that work's package. Fix: replace the wall-clock threshold with a deterministic signal (e.g. recorded start/end timestamps on the mocked synthesis calls, asserting they overlap) so the test doesn't depend on machine load, or raise the threshold with a comment explaining why. (added 2026-10-07)

## Notes Post-Processing (`pipelines/postprocess_notes`)
- <!-- TODO-0059 --> Multi-directory batch post-processing: update `postprocess_notes.py` CLI to process multiple course directories in a single command. (added 2026-10-04)
- <!-- TODO-0060 --> Statistical anomaly z-score calibration: tune the causal z-score and perplexity thresholds in `local_model_scoring.py` to reduce false positives on short or highly symbolic mathematical notes. (added 2026-10-04)

## Textbook Conversion (`pipelines/convert_textbook`)
Things to fix in post-processing?
- <!-- TODO-0061 --> subscripts and superscripts seem to get mixed up a lot (Hansen)
- <!-- TODO-0062 --> internal links are not preserved (Hansen)
- <!-- TODO-0063 --> Table of Contents does not link to anything
- <!-- TODO-0064 --> Some complex Latex contains errors (Hansen)
- <!-- TODO-0065 --> Inline latex equations often yield bad formatting in output
	- Dropping some hats from estimators
- <!-- TODO-0066 --> Could add internal links to obsidian when figures or sections are mentioned
- <!-- TODO-0067 --> Printed TOC spurious entry repair in `chapter_index.py`: `parse_printed_toc()` extracts a spurious frontmatter entry in books like Hammack; add filtering for Roman-numeral or unnumbered frontmatter page markers. (added 2026-10-04)
- <!-- TODO-0068 --> Front-matter image filter boundary tuning in `describe_images.py`: refine the filter to avoid dropping legitimate introductory diagrams near the start of Chapter 1. (added 2026-10-04)



Example from Hansen:

Latex Error:

Q_{XX}^{-1} = \begin{bmatrix} Q_{11} & Q_{12} \\ Q_{21} & Q_{22} \end{bmatrix}^{-1} \stackrel{\text{def}}}{=} \begin{bmatrix} Q_{11}^{-1} & Q_{12}^{-1} \\ Q_{21}^{-1} & Q_{22}^{-1} \end{bmatrix} = \begin{bmatrix} Q_{11}^{-1} & -Q_{11}^{-1} Q_{12}^{-1} Q_{22}^{-1} \\ -Q_{22}^{-1} Q_{21} Q_{11}^{-1} & Q_{22}^{-1} \end{bmatrix} \quad (2.43)



#### 2.24 OMITTED VARIABLE BIAS

Again, let the regressors be partitioned as in [\(2.41\)](#page-76-0). Consider the projection of *Y* on *X*<sup>1</sup> only. Perhaps this is done because the variables *X*<sup>2</sup> are not observed. This is the equation

$$Y = X'_1 \gamma_1 + u \quad (2.45)$$

$$\mathbb{E} [X_1 u] = 0.$$

Notice that we have written the coefficient as γ<sup>1</sup> rather than β<sup>1</sup> and the error as *u* rather than *e*. This is because (2.45) is different than [\(2.42\)](#page-76-0). Goldberger (1991) introduced the catchy labels **long regression** for [\(2.42\)](#page-76-0) and **short regression** for (2.45) to emphasize the distinction.

Typically,  $\beta_1 \neq \gamma_1$ , except in special cases. To see this, we calculate

$$\begin{aligned} n_1 &= (\mathbb{E}[X_1 X'_1])^{-1} \mathbb{E}[X_1 Y] \\ &= (\mathbb{E}[X_1 X'_1])^{-1} \mathbb{E}[X_1 (X'_1 \beta_1 + X'_2 \beta_2 + \epsilon)] \\ &= \beta_1 + (\mathbb{E}[X_1 X'_1])^{-1} \mathbb{E}[X_1 X'_2] \beta_2 \\ &= \beta_1 + \Gamma_{12} \beta_2 \end{aligned}$$

where <sup>12</sup> = *<sup>Q</sup>*−<sup>1</sup> <sup>11</sup> *Q*<sup>12</sup> is the coefficient matrix from a projection of *X*<sup>2</sup> on *X*1, where we use the notation from Section [2.22.](#page-76-0)

Observe that γ<sup>1</sup> = β<sup>1</sup> + 12β<sup>2</sup> = β<sup>1</sup> unless <sup>12</sup> = 0 or β<sup>2</sup> = 0. Thus the short and long regressions have different coefficients. They are the same only under one of two conditions. First, if the projection of *X*<sup>2</sup> on *X*<sup>1</sup> yields a set of zero coefficients (they are uncorrelated), or second, if the coefficient on *X*<sup>2</sup> in [\(2.42\)](#page-76-0) is zero. The difference 12β<sup>2</sup> between γ<sup>1</sup> and β<sup>1</sup> is known as **omitted variable bias**. It is the consequence of the omission of a relevant correlated variable.




Another example:

In general, many parameters of interest can be written as a function of moments of  $Y$ . Notationally,  $\beta = g(\mu)$  and  $\mu = \mathbb{E}[h(Y)]$ . Here, the  $Y$  are the random variables,  $h(Y)$  are functions (transformations) of the random variables, and  $\mu$  is the expectation of these functions.  $\beta$  is the parameter of interest, and is the (nonlinear) function  $g(\cdot)$  of these expectations.

In this context, a natural estimator of  $\beta$  is obtained by replacing  $\mu$  with  $\hat{\mu}$ . Thus  $\hat{\beta} = g(\hat{\mu})$ . The estimator  $\hat{\beta}$  is often called a **plug-in estimator**. We also call  $\hat{\beta}$  a moment, or moment-based, estimator of  $\beta$ , since it is a natural extension of the moment estimator  $\hat{\mu}$ .

natural extension of the moment estimator  $\hat{\mu}$ .  
Take the example of the variance  $\sigma^2 = \text{var} [Y]$ . Its moment estimator is

$$\hat{\sigma}^2 = \hat{\mu_2 - \hat{\mu}_1^2 = \frac{1}{n} \sum_{i=1}^n Y_i^2 - \left( \frac{1}{n} \sum_{i=1}^n Y_i \right)^2.$$

This is not the only possible estimator for  $\sigma^2$  (there is also the well-known bias-corrected estimator), but  $\hat{\sigma}^2$  is a straightforward and simple choice.





Formatting:

Technically, the estimator β in [\(3.7\)](#page-99-0) only exists if the denominator is nonzero. Since it is a sum of squares, it is necessarily nonnegative. Thus β exists if *<sup>n</sup> <sup>i</sup>*=<sup>1</sup> *<sup>X</sup>*<sup>2</sup> *<sup>i</sup>* > 0.


Inline formatting drops hats that are present in nearby equations, should be easy to fix.
#### 3.8 LEAST SQUARES RESIDUALS

As a by-product of estimation, we define the **fitted value** *Yi* <sup>=</sup> *<sup>X</sup> i* β and the **residual**

$$\hat{e}_i = Y_i - \hat{Y}_i = Y_i - X'_i \hat{\beta}. \quad (3.14)$$

Sometimes *Yi* is called the predicted value, but this is a misleading label. The fitted value *Yi* is a function of the entire sample, including *Yi*, and thus cannot be interpreted as a valid prediction of *Yi*. It is thus more accurate to describe *Yi* as a *fitted* rather than a *predicted* value.

Note that *Yi* <sup>=</sup> *Yi* <sup>+</sup> *ei*, and

$$Y_i = X'_i \hat{\beta} + \hat{e}_i. \quad (3.15)$$

We make a distinction between the **error** *ei* and the **residual** *ei*. The error *ei* is unobservable, while the residual *ei* is an estimator. These two variables are frequently mislabeled, which can cause confusion.




Confusing letters in script form:

<span id="page-106-0"></span>When *Xi* contains a constant, an implication of [\(3.16\)](#page-105-0) is

$$\frac{1}{n} \sum_{i=1}^n \hat{c}_i = 0. \quad (3.17)$$

Thus the residuals have a sample mean of 0 and the sample correlation between the regressors and the residual is 0. These are algebraic results and hold true for all linear regression estimates.



