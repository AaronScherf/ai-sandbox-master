# Socratic Tutor Pipeline: Status Summary

Package: `agent/tutor/`. Spec: `docs/superpowers/specs/2026-10-08-socratic-tutor-pipeline-design.md`. Plan: `docs/superpowers/plans/2026-10-08-socratic-tutor-pipeline.md`. Branch: `claude/socratic-tutor`.

## What shipped

The v1 session gate from the spec, implemented task by task with a test watched failing before each module:

- `events.py`, `paths.py`: append-only JSONL log (corruption raises with file and line) and vault layout.
- `fsm.py`: pure state machine and hint-level gating (level 3 needs two failed attempts at level 2).
- `ratings.py`: evidence-capped tri-axial rating; ratings above the ceiling are rejected, evidence must be an event id or a real student quote.
- `lint.py`: tutor-message lint (named techniques, notation bridging, sealed-solution phrases, leading sub-question lists, next-part mentions, LaTeX in chat) and glossary lint.
- `packet.py`, `prep.py`, `sample_packet.py`: packet model, validation, content hash marker (CRLF-insensitive), `prep-collect` / `prep-submit`.
- `render.py`, `profile.py`: transcript and four-part summary; versioned learner-gap profile.
- `session.py`, `audit.py`, `cli.py`, `bootstrap_prompt.md`: the stateless session, the audit, the command surface, and the agent's operating contract.
- Routing: `academic-rag-model/CLAUDE.md`, `docs/AGENT_ROUTING.md`, `agent/rag/README.md` and the package map now say which tutor to use for what.

Tests: `python -m pytest tests/agent/tutor -q` -> 97 passed. `tests/agent/tutor/test_tutor_regression.py` replays the five HW4 deviations; disabling the technique rule, the rating ceiling or the sealed-overlap rule each makes the matching test fail.

## Not validated

- No live Antigravity run yet. Whether Antigravity's workflow and shell-permission settings let the agent run the CLI every turn, and whether it follows the contract, is the open validation.
- `prep-collect` (Gemini query embedding for retrieval) has no automated test; `prep.collect` is tested with an injected `retrieve`.
- Lint thresholds (technique lexicon, two shared six-word phrases for sealed overlap) are tuned on fixtures only; the first real prep and session should add false-positive and false-negative cases.

## Known limits

Soft wall only: direct reads of `packet/sealed/` are undetectable, and `audit` flags the symptom (a reply with no `say`), not the read. Lexical lint cannot catch a paraphrased strategy hint. Intent labels are the agent's.

## What's next

1. Real prep plus a first live HW session on Antigravity; fold the findings back into lint cases and the bootstrap prompt.
2. Disentangle naming between this package and `agent/rag/` (pending to-do "Socratic Tutor vs RAG Tutor Disentanglement" in `docs/trackers/academic_hub_to_do.md`).
3. Spec §10.1: topic/timeframe review and study-guide walkthrough modes (new packet sources, configurable FSM states).
4. Spec §10.2: learning-progress tracker built on `learner_profile.json` (`schema_version` 1).

## 2026-10-08 update: v1.1 Plan A (claim ledger core)

Spec: `docs/superpowers/specs/2026-10-08-socratic-tutor-v1-1-design.md`. Plan: `docs/superpowers/plans/2026-10-08-socratic-tutor-v1-1-plan-a.md`. Branch `claude/tutor-v1-1-core`. Written in response to the HW4 manual trial (see "Socratic Tutor Trial-Run Fixes" in `docs/trackers/academic_hub_to_do.md`).

### What shipped

- `claims.py`, `ledger.py`: prep-authored recognizers (group-window, whole-word or `*` prefix), the `claims.json` schema, the blind-sample self-test (90% of leak samples and 80% of student samples matched, no neutral sample matched), and a deterministic ledger of established claims and pitfalls replayed from the event log.
- `packet.py`, `sample_packet.py`, `prep.py`: packet v1.1 (`claims.json`, `samples.json` in the validated hash, per-part `launch_style`, short launch line), new prep worklist with the blind second pass.
- `fsm.py`, `lint.py`, `ratings.py`, `render.py`: a closed part is never reopened by a side question; failed attempts are attempts that establish nothing new; claim disclosure (`REVEALS_CLAIM`, ids only, copied statement runs masked) and the question form (`QUESTION_FORM`); ratings default to the evidence ceiling with CLI-attached evidence and can only be lowered; the summary lists verified steps with the student's quotes.
- `session.py`, `cli.py`, `audit.py`, `bootstrap_prompt.md`: `turn` / `say --stdin|--check` / `verify` (two phases, once-per-part solution release, quote-validated step check), actionable errors (`next`), manual overrides with quotes, audit of manual overrides and releases without coverage, `audit` on finished sessions.

Tests: `python -m pytest tests/agent/tutor -q` passes (171 at the end of Task 11). `test_tutor_regression.py` holds analogues of the HW4 trial's bad replies against the sample claims and the offline half of the seven adversarial scenarios; breaking the disclosure, coverage and unresolved-slip rules each turns the intended tests red.

PowerShell stdin check (Task 10): `$OutputEncoding = [Text.UTF8Encoding]::new($false)` plus a here-string pipe carried `x ≽ y and γ(b) in ℝ` into the log unchanged on Windows PowerShell 5.1, so the two-call turn works; `--text-file` remains the fallback.

### Not yet validated

- No live Antigravity run on the claim ledger. The HW4 packet must be re-prepped with `claims.json` and `samples.json` from the new worklist before any live run (the old packet is refused with a message saying so).
- Tool calls per turn have not been measured live (target 2).
- The live half of the adversarial suite (spec §11) and the decision on an independent judge (spec §12) are still to do.
- Recognizer quality on real course content is unknown; the self-test only measures coverage against blind samples written by the same model family.

### What's next

1. Re-prep HW4 with the new worklist (Antigravity), then a live session and the live adversarial scenarios; add false positives and misses to the fixtures.
2. Decide on the independent judge from those results.
3. Plan B: skip/defer/revisit, `pause`, profile v2, and their audit checks.
4. The one-sentence Antigravity entry point.


## v1.1 Plan B (skip / defer / revisit, pause, profile v2)

Landed on branch `claude/tutor-v1-1-plan-b` (not yet on main; waits for the live Plan A run).

- Two-request skip: request 1 needs a "try it" nudge question; request 2 parks the part as `skipped` (no real attempt) or `deferred` (at least one real attempt: 8+ words outside skip phrases on an `attempt` turn, or a newly matched claim/pitfall; an `--admits-gap` turn never counts). A skip phrase inside an `attempt` turn is not a skip unless `--skip` is passed; the audit lists those turns.
- Parked parts are offered only at the check-in after the next completed part, and once more in the closing message; `end` is refused until that offer is said. Mentioning a parked part mid-part is a lint error.
- Revisit reopens the part at its saved hint level with claims intact, as attempt 2; its rating is capped at Proficient on every axis.
- Profile `schema_version` 2 (`status`, `attempt`); v1 files load as rated attempt 1; `update_profile` is idempotent per session, so `pause` then `end` does not duplicate history.
- `pause` / `end --partial`, `start` resumes, `start --fresh` ends the open session as partial.
- Audit adds `SKIP_TOO_EARLY`, `SKIP_WITHOUT_NUDGE`, `REVISIT_OFFER_MISSING`, `REVISIT_MID_PART`, `SKIP_PHRASE_UNCOUNTED`, and exempts legitimate part moves from `ADVANCE_WITHOUT_CONFIRM`.

Rulings: `skip_request` is `data.skip` on the student event, not its own event; the ending skip message is logged under the parked part followed by `part_status`; one short acknowledgement (at most 20 words, no question, no claim content) may precede the launch line after a skip; the regression test found that `synthesis`/`session_end` are logged under the last part, so the audit now exempts them from the part-move check.

Live validation pending: the tunables (8 words, 20 words, 60 words) are guesses.

## 2026-10-10 live runs and the open design question (strict vs permissive tutoring)

Landed on `main` since the Plan B entry above: Plan B (`0ecfe1f`), and two live-run fixes (`67ea2cb`: definition relay, one warm sentence, auto-resolve of a missing step once a later `verify` confirms it; `8307b05`: a relayed definition plus one question is allowed at the launch line). The HW4 `claims.json` recognizers for `q1_1` were tightened in the vault (uncommitted there); `q1_2`..`q1_6` were not.

### What two live HW4 sessions showed
Sessions `2026-10-09-2327` (Plan A) and `2026-10-10-2145` (Plan B), Gemini in Antigravity.

- **Skip, defer, pause, definition relay, warm opener work.** The first skip request gets one "try a first step" question, the second parks the part (`deferred` after a real attempt), and `pause` is logged.
- **The tutor never explains.** In 57 events the only teaching content was glossary definitions and the formula copied from the statement. Replies are one sentence plus one question (about 15-35 words). A student who says "I don't really get why the better items matter" gets another question; a student who asks for the answer twice gets the same question three times.
- **Cause: the live leak check, not only the word cap.** `REVEALS_CLAIM` rejects any draft matching the recognizer of a claim the student has not reached, at every hint level. An explanation of why better items matter is a statement of C2, so only questions pass. The v1 prototype's long free-text window explained well and also leaked the solution. The two failures are the two ends of one dial.
- **Time to useful content is long.** The strict mode is a good assessor of material the student already has, and a weak teacher of material they do not.
- **Revisit is too rigid.** The check-in offer was made (event 48) but bundled into "lingering questions, revisit 1.1, or ready to move on?", and "Let's move on" consumed it. A later explicit "go back to 1.1" at 1.3 was refused (revisit is valid only at a check-in or in the closing message) and was then sent with `--skip`, so the student received the skip nudge. A clear student request to go back should be honored at the next natural point, and `--skip` must never apply to it.
- **Recognizers misfire outside `q1_1`.** Event 27 (C4 on "the default option is not included") and event 32 (C1 and pitfall P1 on "monotonically increasing functions") look like false positives. A side check showed `q1_2`..`q1_6` recognizers hit glossary entries and other parts' claim texts.
- **Ratings count "can I just see the answer?" as evidence**, giving Developing on all axes for a part closed cleanly in five turns.
- **Latency is model steps, not the CLI.** Each student message costs at least two model steps (`turn`, `say`), 8-35 s each; `verify` adds more.

Defects fixed in this round: bare definition at launch (my regression, `8307b05`); a defect left open after the step was later confirmed (`67ea2cb`); false positives for C1/C2/P1 on `q1_1` (vault).

### Ideas on the table (nothing decided)
1. **Two modes.** A strict tutor (questions only, claim leak check on, near-guaranteed not to reveal) for assessment and for material the student should already know, and a permissive tutor (explains, gives worked analogies, may lead the answer more) for learning something not yet mastered. How extreme each ends up being is what the testing should measure.
2. **Choose the mode from the assessment.** Suggest strict where the learner profile rates the concept at or above Proficient, permissive where it is Developing or unassessed.
3. **Offer a switch on frustration.** Signals: repeated hint requests, repeated "just tell me", several admitted gaps, repeated skip requests. The tutor offers the permissive mode; the switch is logged and caps the part's rating.
4. **A temperature that moves with performance.** One setting that changes the lint level after each turn: down after a claim is established unaided, up after an admitted gap or a failed attempt at the same level. Replaces the binary switch with a ladder.
5. **Prep-time vetted explanations (preferred design so far).** The prep pass, which already holds the sealed solution, writes for each claim a ladder of explanations: intuition, a worked analogy in a different setting, a bridging hint. They are checked once for solution leaks. At runtime the tutor relays them word for word, the way it now relays glossary definitions, and writes its own warm bridge and one question. The live check then only needs the sealed-solution phrase check, so the claim recognizers can go back to being a ledger tool. Cost: a larger prep pass and more review.
6. **Loosen the live lint only.** From hint level 2 allow free explanation and rely on the sealed-solution overlap check. Cheapest; closest to the version that leaked.
7. **Shelve the live gate.** A contract file plus a plain chat, a small post-session script for the log and learner profile, and a separate review pass that reads the transcript for leaks and inflated ratings. Natural tutoring, no live guarantee.

### Proposed comparison test
Same HW4 questions, three arms, the same student script (the 13-line table used for the Plan B run: definition request, "no idea where to start", admitted gap, "just tell me the formula", skip x2 with a real attempt between, "can I see the answer?", "should I use contradiction?", finish a part, go back to the skipped one, pause and resume):
- **Arm 1:** current strict pipeline (baseline, already run).
- **Arm 2:** plain chat with a contract file only (idea 7).
- **Arm 3:** a permissive prototype: the pipeline with the claim leak check relaxed from hint level 2 (idea 6), or with prep-time vetted explanations (idea 5).

Score every arm on: explanations the student could use; solution leaks and near-leaks (a reviewer reads each transcript against the sealed solution); whether the student's own words were required to close a part; seconds per turn; honesty of ratings; whether a stated "go back" request was honored. Two leak measures: exact (sealed-solution phrases) and by judgment (does the tutor state a claim before the student does).

### Open questions
- What does the learner profile need to hold if the live gate is shelved (history of parts, ratings with evidence quotes, admitted gaps)?
- Is a mode switch a session-level or a part-level setting?
- Does a rating earned in the permissive mode count the same as one earned in the strict mode? Current lean: capped at Proficient, like a revisit.
- Is the unique value the live guarantee, the audit trail, or the learner profile? The answer decides between ideas 5 and 7.

Known small defects to fix under any option: the revisit rule above; recognizers for `q1_2`..`q1_6`; rating evidence should exclude answer requests; the audit's `INTENT_MISMATCH` is too strict on "stuck" labels.
