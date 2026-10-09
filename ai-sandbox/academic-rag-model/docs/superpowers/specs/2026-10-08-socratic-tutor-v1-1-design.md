# Socratic Tutor v1.1 — Design (claim ledger, verify, skip/defer)

Date: 2026-10-08 · Status: draft for review · Package: `agent/tutor/` · Amends: `2026-10-08-socratic-tutor-pipeline-design.md` (v1, landed in `c9019c1`)

Evidence: the HW4 manual trial in Antigravity, log at `academic-hub/academic_notes/microecon/tutoring/homework_4/trial_runs/2026-10-08-2112/events.jsonl` (44 events), and the findings recorded in `docs/trackers/academic_hub_to_do.md` under "Socratic Tutor Trial-Run Fixes". Event numbers below refer to that log.

## 1. Goals and success criteria

v1 enforced process (order of commands, hint levels, rating caps) but not content. The trial showed the tutor leaking steps and methods, missing a student slip, marking a part "correct" with an error uncaught, forcing completion on a student who wanted to move on, and taking 8-10 tool calls per turn. v1.1 makes those failures structurally harder, without any paid or local model call at runtime.

Success:
1. The trial's bad tutor replies are handled as regression fixtures (§11): events 10, 13, 36 and 39 are rejected by `say`; events 17 and 44 produce the missing pitfall or slip flag that the tutor failed to log.
2. The seven adversarial scenarios (§11) are run and recorded; their results decide whether an independent judge is needed (§12).
3. A tutoring turn takes 2 tool calls (`turn`, `say`), measured in a live Antigravity run.
4. A student can skip or defer a part under the rules in §8 and revisit it, with the rating and profile rules in §8-§9.
5. A session can be paused part-way without losing its record.

Out of scope: the Antigravity one-sentence entry point (tracker: "Socratic Tutor Antigravity Entry Point", built after this); the independent judge (conditional, §12); v1 §10 modes (topic review, study-guide walkthrough, spaced review).

## 2. Decisions taken

| Decision | Choice | Why |
|---|---|---|
| Hint control | Claim ledger + question form. Prep writes the claims and recognizers; the CLI marks claims established from the student's own messages and rejects tutor drafts that introduce unreached claims | The agent can solve the problem itself (the event-10 leak preceded any `sealed` call), so hiding the solution is not enough; disclosure must be checked against what the student has reached |
| Judge model | None at runtime (no paid or local call). Conditional escalation, §12 | User constraint; flat-rate agent only |
| Hints | Written by the tutor from the student's words; no pre-scripted hint text | Scripted hints force one solution path and go stale |
| Verification | Once-per-part `verify` releases that part's sealed solution; step-by-step check with quotes | Holding the solution back at the moment of "solved" only makes a wrong "correct" more likely |
| Ratings | Default to the evidence ceiling; the CLI attaches the evidence; the agent can only lower | The agent's evidence picks were irrelevant in the trial; unlogged slips are caught by recognizers |
| Self-attestation | Never a control | The agent reported "100% compliant" while its tool log showed direct sealed reads |
| Skip | Two explicit requests, with a "try it" nudge in between | User decision |
| Revisit | Offered only at the check-in after the next completed part, and once more at the session end | User decision |
| Plans | One spec, two plans: A (core) then B (skip/defer/pause/profile) | Independent, testable deliverables |

## 3. Packet v1.1

New files `claims.json` and `samples.json` at the packet root; `sealed/solution.md` stays, one `## <part_id>` section per part, used only by `verify` and for human reference. `sealed/hints.md` is optional reference only and is not read at runtime. `glossary.json`, `rubric.json` and `parts.json` keep their v1 shape; `parts.json` may add an optional `final_answer` recognizer (§4) for derivation parts. The validated hash covers `parts.json`, `glossary.json`, `rubric.json`, `claims.json`, `samples.json` and `sealed/solution.md`. `parts.json` entries may carry a per-part `launch_style` (`"label"`, the default, or `"statement"`).

```json
{ "q1_1": {
    "claims": [
      { "id": "C1", "text": "a must be considered, with probability gamma(a)",
        "object_terms": ["the chosen item", "being considered"],
        "recognizer": { "all": [["consider*","attend*","notice*"], ["chosen","select*","pick*","best"]], "window": 14 } },
      { "id": "C2", "text": "every item ranked above a must fail to be considered",
        "object_terms": ["the items ranked above a"],
        "recognizer": { "all": [["consider*","attend*","notice*"], ["better","higher","superior","dominat*"], ["not","never","fail*","absent"]], "window": 16 } },
      { "id": "C3", "text": "independence makes the joint probability the product of (1 - gamma(b))",
        "object_terms": ["combining the probabilities"],
        "recognizer": { "all": [["independen*"], ["multipl*","product"]], "window": 14 } } ],
    "routes": { "A": ["C1","C2","C3"] },
    "pitfalls": [
      { "id": "P1", "tag": "adds-independent-probabilities", "axis": "rigor", "resolved_by": "C3",
        "recognizer": { "all": [["independen*"], ["add","sum","plus"]], "window": 12 },
        "repair_question": "If both events must happen together, does combining their probabilities add or multiply?" } ] } }
```

- **Recognizer.** `{"all": [group, ...], "window": N}`. Text is lowercased and tokenized into words (punctuation and math symbols dropped). An entry matches a whole token unless it ends in `*`, which makes it a prefix (`consider*`); `n't` is read as `not`. A group matches a token if one of its entries does. The recognizer matches when some window of N consecutive tokens contains a match for every group. No regex; deterministic and safe to author.
- **Routes** are ordered claim sets; a part is covered when every claim of at least one route is established. Alternative proofs are extra routes, which may share claims.
- **Pitfalls** run only on student messages. Each carries a tag, the axis it affects, a Socratic `repair_question`, and optionally `resolved_by` (a claim id): when that claim is established at or after the message that triggered the pitfall, the misconception is resolved automatically (`misconception_resolved`, `auto: true`); otherwise the agent resolves it with a quote.
- **Optional `final_answer`** on a part: a recognizer over the student's final expression, for derivation parts; an additional condition for coverage.
- **`samples.json`** (written in a *second, blind* prep pass by an agent that has not seen the recognizers): per claim, ≥10 `leak_samples` (tutor-style sentences that reveal the claim) and ≥5 `student_samples` (ways a student might state it); per part ≥5 `neutral_samples` (Socratic questions that reveal nothing); per pitfall ≥3 `student_samples`.
- **`prep-submit` self-test.** For each claim the recognizer must match ≥90% of its `leak_samples` and ≥80% of its `student_samples`; no recognizer may match any `neutral_sample`; each pitfall recognizer must match ≥80% of its samples. Failures are reported with the offending sample so the prep agent can fix the recognizer. Because samples are authored blind, this measures coverage, not just self-consistency; it is still written by the same model family, which §13 records as a risk.
- **Prep contract changes.** The worklist gains: author `claims.json`; then, in a separate pass, author `samples.json` without reading the recognizers; keep `solution.md` verbatim from the guided solutions.

## 4. State and ledger

State is still replayed from `events.jsonl`; there is no state file. Event types added in Plan A: `establish` (manual, with quote), `verify_release`, `verify`, `defect`. A `turn` logs an ordinary `student` event (its data carries `made_progress` and `established`); a manual slip is a `misconception` event with `manual: true`; automatic resolution is a `misconception_resolved` event with `auto: true`. Messages with intent `define_request` or `confirm_advance` never establish claims or hit pitfalls. Plan B adds `skip_request`, `part_status`, `revisit`, `paused`, `resumed`. A claim is *established* when the recognizer matches any student message of that part, or by a manual `establish` event whose quote is found in the part's student messages (audit-flagged). A pitfall is *hit* when its recognizer matches a student message; the CLI logs the misconception automatically (axis from the pitfall).

Per part: `status ∈ {open, closed, skipped, deferred, revisiting}`, `skip_requests`, `solution_released`, `attempts` (list of attempt records for revisits). Session: `cursor` (next fresh part), `current` (part being worked), `deferred_queue`.

Hint levels keep the v1 meaning (0-3, raised only by an explicit student `stuck`/`hint_request`). Level 3 now requires two *failed attempts* at level 2, where a failed attempt is an `attempt` turn that establishes no new claim.

States per part: `LAUNCH → WORKING → VERIFIED (closed, check-in owed) → AWAITING_ADVANCE`, plus session-level `SYNTHESIS → DONE` and `PAUSED`. Changes from v1: a side question or `define_request` in `VERIFIED`/`AWAITING_ADVANCE` keeps the state (the closed part is not reopened); `verify` replaces `verdict` + `close-part`; the `revisit` intent is valid only in `AWAITING_ADVANCE` and `SYNTHESIS`.

## 5. Commands

Every error is `{"ok": false, "error": "...", "next": ["legal command", ...]}` so the agent never reads source to recover. Flat names as in v1.

| Command | Purpose |
|---|---|
| `turn --intent I (--stdin \| --text-file F \| --text T) [--admits-gap [axis]] [--define TERM] [--establish Cn --establish-quote Q] [--flag-slip TAG[:axis] --slip-quote Q] [--resolve TAG --resolve-quote Q]` | Logs the student message and returns one **brief**; replaces `student`, `verdict`, `misconception`, `define`, `sealed hint` |
| `say (--stdin \| --text-file F \| --text T) [--check]` | Lints and logs the tutor draft; `--check` is a dry run that logs nothing. A rejection is normal and unpenalized |
| `verify [--check-file F] [--downgrade axis=rating ... --why TEXT]` | Two phases: without a file it releases the part's solution steps once; with a file it submits the step check and closes the part on success |
| `end`, `start`, `audit`, `bootstrap`, `prep-collect`, `prep-submit` | As in v1 (`audit` also works on a finished session); `pause`, `start --fresh` and the `--skip` flag arrive with Plan B (§8-§9) |

Intents: `attempt`, `stuck`, `hint_request`, `define_request`, `confirm_advance`, `has_questions`, `revisit`, `other`. The intent label is the agent's; a deterministic phrase check cross-checks `confirm_advance`, `stuck`/`hint_request` and skip phrases, and the audit compares them.

**The brief** (JSON): `state`, `part_id`, `label`, `statement` (agent-only, not to be printed), `hint_level`, `claims_established` (ids), `route_coverage`, `pitfalls_hit` (tag + repair question), `definition` (verbatim glossary entry if the intent was `define_request`), `verify_available`, `solution_released`, `rules` (the exact constraints on the next reply, §6), and `next` (legal commands). At level 2 it adds the next claim's `object_terms`; at level 3 it adds that claim's `text`. Claim texts otherwise never appear. `skip_requests` and `revisit_offer` are added by Plan B.

## 6. The `say` rules

Kept from v1: verbatim launch, definition-only after `define_request`, sealed-phrase overlap (6-word run), technique words, check-in wording, next-part mention, Unicode math in chat.

New:
- **Launch** is the short line `"{label}. How would you like to approach this problem?"` (no statement; the agent has it in the brief). A per-part `launch_style: "statement"` field restores the v1 text.
- **Disclosure.** A draft may not match the recognizer of any claim (on any route) that the student has not established, except the next claim at level 3 (object terms at level 2 are guidance only and need no exemption). Runs of six words copied from the part statement are masked before the recognizers run, so the tutor can quote the problem. A rejection reports the claim id (`REVEALS_CLAIM:C3`), never its text.
- **Question form** at hint levels 0-1, and below level 3 for any part with `solution_released`: at most one question mark; at most 60 words; at most one non-question sentence, which must share ≥2 content words with the student's last message.
- **Skip request #1:** the reply must be a question that invites an attempt and must not advance.
- **Check-in** (state `VERIFIED`): the v1 wording, plus the revisit offer when the deferred queue is non-empty ("go back to 1.2, or on to 1.4?").
- **Synthesis:** if the deferred queue is non-empty the closing message must offer the revisit.

## 7. `verify`

Available only when a route is covered (recognized or manually established, plus `final_answer` if the part has one). `verify` without a file returns that part's `solution.md` steps (markdown headings of level 3 or deeper, else paragraphs), **once**; a second release is refused. The agent then submits a check file with `verify --check-file` (resubmittable): a list with one entry per solution step, `{"step": n, "status": "confirmed"|"missing"|"wrong", "quote": "<student words>", "note": "<about the student's step, not the solution>"}`; every `confirmed` entry needs a quote that appears in the part's student messages (validated).

- **Clean** (all steps confirmed, no unresolved pitfall): the part closes; ratings are computed (§10); state `VERIFIED`.
- **Defects** (any `missing`/`wrong`, or unresolved pitfall): each becomes a `defect` event and a logged misconception (axis supplied with the entry, default `rigor`); the part returns to `WORKING`; the solution is not released again; `solution_released` tightens the question form (§6).
- The check file is archived in the log, and the end-of-session summary lists the confirmed steps with their quotes so the student can spot a rubber stamp.

## 8. Skip, defer, revisit

- **Counting.** A skip request is a `turn` with `--skip` or a deterministic phrase hit ("skip", "move on", "next question", "come back"); the count is the larger of the two per part.
- **Request #1** keeps the part open and requires the "try it" nudge (§6). **Request #2** (same part, any later turn) ends the part: it moves to the next fresh part, or to `SYNTHESIS` if none.
- **Statuses.** `skipped`: no real attempt, no rating, not a gap. `deferred`: a real attempt was made first; gap evidence. A *real attempt* is an `attempt` turn with ≥8 words outside the skip phrases (configurable) or any turn where a recognizer matched.
- **Revisit offer** appears only in the check-in after the next *completed* part (skip 1.2, finish 1.3, offer at the end of 1.3: back to 1.2, or on to 1.4), never mid-part. Declining leaves the part queued for one last offer at the session end. A skipped single-part question (Question 2) is offered after the next completed part (Question 3).
- **Choosing "back"** (`revisit` intent) reopens that part in `WORKING` with its claims and hint level restored. A new attempt record starts; the earlier attempt stays in the log.
- **Scoring on revisit.** When a revisited part is verified, its ratings are the ceiling **capped at Proficient on every axis**. The profile keeps both attempts.

## 9. Ratings, profile, pause

- **Ceiling** (v1 rules, extended): unresolved pitfall or defect → Developing; hint level ≥2 → Developing; hint level 1 or a resolved misconception → at most Proficient; stated gap (`--admits-gap`) → Developing on that axis; revisit → at most Proficient.
- **CLI-attached evidence.** For each axis the evidence is the set of events that caused its cap (hint-raising turns, misconception/defect events for that axis, admitted-gap turns); if the axis is uncapped, the turns that established the route's claims. The agent may lower a rating with `--downgrade axis=rating --why TEXT` (stored with the rating); it can never raise one.
- **Profile v2** (`schema_version: 2`; v1 files load with every entry marked `status: "rated"`). History entries carry `status` ∈ `rated`/`deferred`/`skipped`, an `attempt` number and the part id. A concept is an open gap when its latest session has a Developing rating, an open misconception, or a `deferred` entry with no later successful revisit. `skipped` entries never create a gap and appear in the summary as "not covered".
- **`pause`** (alias `end --partial`): renders `transcript.md` and `summary.md` for closed, deferred and skipped parts, updates the profile from them, and logs `paused`. `start` on a paused session offers resume (default) or `--fresh`, which ends the paused session as partial. A session directory is open only if its log has neither `session_end` nor a partial end; trial or copied logs belong in `trial_runs/`, not `sessions/`.

## 10. Audit additions

Flag: a skip with fewer than two requests; a deferral with no "try it" nudge before it; a check-in missing the revisit offer; a revisit prompt while a part is `WORKING`; every manual `establish`/`flag_slip`; a `verify` whose check file confirms steps with quotes from the wrong part; a `turn` intent that contradicts the phrase check; and v1's checks. The audit remains blind to direct file reads and to anything not logged; it never decides correctness.

## 11. Testing

- **Unit:** recognizer matching and self-test, ledger replay, FSM transitions (skip, revisit, pause, closed-part questions), `say` rules (disclosure, question form, launch, check-in), `verify` (once-only, quote validation, defect path), ratings and evidence attachment, profile v2 and v1 loading, audit checks, actionable errors.
- **Trial fixtures:** the tutor replies at events 10, 13, 36 and 39 of the trial log, each paired with the student state at that point, must be rejected by `say`. At events 17 and 44 the student's messages (the "add independent probabilities" slip; "adding any new item to the consideration set") must produce the corresponding pitfall hit or flagged slip, so the tutor cannot silently correct or approve them.
- **Adversarial suite** (offline from recorded drafts in CI; live in Antigravity by hand, several trials each; failure threshold fixed beforehand): (1) a nearly-right proof with one subtle flaw (consideration set vs menu) must not be marked correct or silently fixed; (2) right words, wrong logic; (3) a correct proof via an unusual route or phrasing the recognizers miss must be recognized or manually established, not stall; (4) student pressure to reveal the proof or insistence it is done; (5) a nudge to call `verify` early or to establish claims just to unlock the solution; (6) a rubber-stamp `verify` on a defective proof; (7) paraphrased leaks of an unreached claim at levels 0-2.
- **Speed:** count tool calls per turn in a live run; target 2.

## 12. Escalation: the independent judge

If any adversarial scenario fails its threshold (e.g. a false "correct" on a seeded flaw, or a paraphrased leak passing the ledger), add an independent judge. Candidates: a small metered Gemini Flash call inside `turn`/`say` (holds the solution; assesses the student's work; vets drafts; roughly 2k tokens per call, cost to be measured), or a second Antigravity chat as reviewer through a shared file. Local Ollama was judged too slow and unreliable on math. The design leaves a seam for this: `turn` and `say` each call one internal `assess()`/`vet()` function that is a no-op in v1.1.

## 13. Risks

- Recognizers are lexical; unforeseen phrasings of a claim slip past disclosure checks and fail to establish. Mitigations: blind sample pass, manual `establish` with quotes, adversarial suite.
- The prep agent writes both recognizers and (in a second pass) samples; they share a model family, so the self-test measures coverage but not independence.
- The agent can still read `packet/` files and tutor source (soft wall); this is undetectable and the design assumes it will sometimes happen.
- `verify` correctness depends on the agent comparing the student's argument with the released solution honestly; the quote validation and the summary list make a stamp visible, not impossible.
- Hard proofs (Question 1.5, Question 2) lean more on the agent's judgment than simple parts.
- The 8-word attempt threshold and the 60-word cap are guesses; both are configurable and should be tuned from live runs.

## 14. Build order (two plans)

- **Plan A (core):** `claims.py` (schema, recognizer, self-test), ledger replay, `turn`/`say --stdin|--check`/`verify`, disclosure and question-form lint, short launch, CLI-attached evidence ratings, actionable errors, closed-part question handling, prep worklist for claims and blind samples, bootstrap prompt update, trial fixtures. Deliverable: tutoring turns in 2 calls with content-level gating.
- **Plan B (agency):** skip/defer/revisit state, `pause`/resume, profile v2, audit additions, revisit-offer lint. Starts from Plan A's committed result.
- The adversarial suite is written alongside Plan A (offline portion) and run live after both plans land.
