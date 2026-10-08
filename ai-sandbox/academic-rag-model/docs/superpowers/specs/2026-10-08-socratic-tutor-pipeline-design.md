# Socratic Tutor Pipeline — Design

Date: 2026-10-08 · Status: draft for review · Package: `agent/tutor/` (new)

Source evidence: `academic-hub/academic_notes/microecon/tutoring/` (HW4 beta run; `tutoring_pipeline_meta_lessons_learned.md`) and the 2026-10-08 entry in `docs/status/agent/rag/2026-09-27-tutor-diagnosis-status.md`.

## 1. Goal and success criteria

A Socratic office-hours tutor that runs live inside a flat-rate agent app (Antigravity first) with **no metered API loop**. Local Python does all preparation and enforcement; the live agent supplies dialogue only.

Success:
1. Replaying the five HW4 deviations (see §8) as regression fixtures, each is blocked or flagged by the pipeline.
2. A second session on the same course starts with the student's prior gaps visible and updates them.
3. Every session leaves a transcript, a calibrated summary and a machine-readable event log in the vault.

Out of scope (v1): hard file-access wall; spaced review (see §10); replacing the existing `rag_agent.py` REPL (`/draft`, `/hint`, `/verify`, `/summarize` stay as they are).

## 2. Decisions taken

| Decision | Choice | Why |
|---|---|---|
| Live host | Antigravity agent session, host-agnostic file/CLI protocol where free | Subscription-priced; user's choice |
| Enforcement | FSM implemented in a local CLI the agent must call each turn; prompt alone is not trusted | Same prompt-only approach failed 5 times in the beta |
| Leak wall | **Soft**: sealed solutions live in `packet/sealed/`; reading them goes through the CLI so each reveal is logged; direct reads are forbidden by the bootstrap prompt but not technically blocked | User's choice; direct reads are not detectable in-host, so the audit can only surface what the CLI saw |
| LLM work in prep | Done by the live IDE agent in a separate prep session; Python only collects, validates and writes. No paid API key. Only the query-embedding call remains | Flat-rate agent makes the paid key unnecessary; user's direction |
| Learner profile | Per-course concept-gap tracker only | Spaced review is a separate future subproject |

## 3. Architecture

Three layers, one-way dependency (offline → live → persistence):

```
OFFLINE (python, run by user/Gemini/Codex)         LIVE (Antigravity agent)             VAULT
tutor prep  ──► packet/  ─────────────────────►  bootstrap prompt + tutor CLI  ──►  sessions/…/events.jsonl
 (retrieve, parse, glossary, rubric, lint)         (FSM gate, lint, sealed reads)       transcript.md, summary.md
                                                                                         learner_profile.{json,md}
```

### 3.1 Offline: `tutor prep <course> <problem_set>`

Builds a **packet** per problem set, reusing `problem_set_parser.extract_question`, `rag_agent.retrieve_passages`, existing `*_hints.md` and `*_guided_solutions.md`. The packet is cached, so prep runs once per problem set.

**No paid LLM calls.** Prep is split into deterministic Python steps and agent-authored steps, run in a dedicated *prep session* of the same IDE agent (flat-rate):
- Python (`tutor prep --collect`): parse the problem set, run retrieval, write `parts.json` skeletons and `grounding.md`, and emit a prep worklist.
- Agent (follows the worklist): draft `glossary.json`, `rubric.json`, and each part's `concept_tags` / `expected_evidence`. It submits them through `tutor prep --submit`, which runs the glossary lint (§3.1) and schema validation and rejects bad drafts for revision.
- The only remaining API dependency is the Gemini **query embedding** used by `retrieve_passages` / `core.indexer.index_search` (the index was built with those embeddings). It is one small call per query and runs on the free tier. Everything else is offline or agent-side.
- Prep runs in a separate session from tutoring, so the agent that drafts sealed content is not mid-dialogue with the student. Packets are human-reviewable files; the user may edit them before the first session.
- Trade-off: prep now needs an agent session rather than a headless batch run, and draft quality depends on the IDE model. The lints and the human review step are the quality gates.

Packet layout (`academic_notes/<course>/tutoring/<ps>/packet/`):

- `parts.json` — ordered parts, each with `part_id`, `statement` (verbatim, neutral, definitions only), `concept_tags`, `expected_evidence` (what a correct attempt must show).
- `glossary.json` — term → **generic domain definition**. A prep-time lint rejects any definition containing the problem's own variables or notation (the "choice overload → d" bridge failure).
- `rubric.json` — per part, the three axes with ratings (§5) and the evidence each rating needs.
- `grounding.md` — retrieved course passages (notes, slides) for the tutor's internal use, with source citations.
- `sealed/hints.md`, `sealed/solution.md` — internal verification only.
- `prior_gaps.md` — rendered from the learner profile (§6): the concept tags the student rated Developing/Needs Review previously. Informational for the tutor and for the summary's action menu; never a source of hints.

### 3.2 Live: the `tutor` CLI (`python -m agent.tutor.cli`)

The agent calls the CLI on every turn. The CLI owns the state and returns what the agent may do next.

| Command | Purpose |
|---|---|
| `start <ps> [--part]` | Create or resume a session; returns state and the verbatim launch text for the current part. |
| `student --intent <attempt\|stuck\|hint_request\|define_request\|confirm_advance\|has_questions\|other> --text …` | Logs the student's message verbatim and the agent's intent label; applies the FSM transition; returns the current state and its allowed moves. |
| `say --file <draft>` | Lints a draft tutor message against the current state. Returns `OK` (message logged) or the violations. The agent must revise and resubmit before sending. |
| `define <term>` | Returns the glossary entry only. Logged. |
| `sealed <part>` | Returns the sealed hint or solution for the current part. Refused before the student has logged an attempt on it. Every call is logged as a reveal. |
| `close-part --evidence …` | Records the tri-axial rating (§5). Rejects any rating above the computed ceiling. |
| `end --big-picture <file>` | Writes the synthesis event, renders the vault documents, and updates the learner profile. |
| `audit <session>` | Re-lints a finished session from its log (§7). |

Intent classification is done by the agent, since the CLI cannot read free text reliably. The student's verbatim text is stored with the label so the audit can catch mislabels (e.g., `confirm_advance` on a message that never asked to move on).

### 3.3 The FSM (`fsm.py`, pure functions, table-driven)

Per part:

```
LAUNCH ─student(attempt|stuck|…)─► WORKING ─(verdict: correct)─► VERIFIED
                                     │  ▲                          │
                          hint_request/stuck (level +1 max)        │ tutor asks "lingering questions or ready to move on?"
                                                                   ▼
                                                           AWAITING_ADVANCE ─student(confirm_advance)─► next part LAUNCH
                                                                   │ student(has_questions)
                                                                   └──────────► WORKING (same part)
last part, after confirm_advance ─► SYNTHESIS ─► DONE
```

Rules encoded as transitions, not prose:
- `LAUNCH` allows only the verbatim neutral launch text ending "How would you like to approach this problem?". No hints, no setup.
- Hint level starts at 0 and rises by at most one per explicit `stuck`/`hint_request` event. Level 3 requires at least two logged failed attempts at level 2. The tutor can never raise the level on its own initiative.
- `VERIFIED` can only go to `AWAITING_ADVANCE`; the only exit to the next part is a logged `confirm_advance`.
- `define_request` is answered from `define` only and returns to the same state with the hint level unchanged.
- The `say` lint is parameterized by state and hint level.

## 4. Message lint (`say`)

Lexical and structural checks, intentionally conservative (false positives cost one revision; false negatives cost a leak):

- **Technique lexicon** (contradiction, contrapositive, induction, "for the sake of", "suppose that …", construct/counterexample directives) blocked below hint level 2, and at level 2 unless the student named the technique first.
- **Notation bridge**: variables and symbols from the current part's `statement` appearing in a definition answer.
- **Sealed overlap**: n-gram overlap of the draft with `sealed/solution.md` above a threshold.
- **Pacing**: any message in `VERIFIED` that references the next part, or a draft in `WORKING` that ends with a leading sub-question list (≥2 enumerated sub-questions before the student has proposed a plan).
- **Rendering**: LaTeX-only math in chat bubbles; the agent is told to use Unicode math in chat and keep full LaTeX in vault files.

## 5. Calibrated rating (anti-inflation)

Axes: Conceptual Fluency · Mathematical Rigor & Notation · Directness & Proof Elegance. Ratings: Mastered · Proficient · Developing / Needs Review.

The agent proposes ratings, but the CLI computes a **ceiling** per axis from the event log:
- Mastered requires max hint level 0 and no logged `misconception` events on that part.
- Proficient requires max hint level ≤ 1 and every logged misconception marked resolved by the student themselves.
- Any unresolved misconception, hint level ≥ 2, or a student statement of not understanding caps the axis at Developing / Needs Review.

`close-part` rejects a rating above the ceiling and requires at least one cited event id or quoted student statement per axis. The agent logs misconceptions as they happen (`student --misconception <tag>`); this is the same signal that feeds the learner profile.

The summary uses the beta's four-part module: Diagnostic, Big Picture (agent-written, supplied at `end`), Tri-Axial Rubric (rendered from the log), Action Menu (readings and review topics derived from `concept_tags` and `prior_gaps`).

## 6. Persistence and learner profile

Per session (`…/<ps>/sessions/<YYYY-MM-DD-HHMM>/`):
- `events.jsonl` — append-only, one event per line: `{id, ts, type, part, state, hint_level, text?, intent?, tags?, ...}`. The source of truth.
- `transcript.md` — word-for-word dialogue, rendered from the log.
- `summary.md` — the student-facing four-part module.

Per course: `…/tutoring/learner_profile.json` (+ rendered `learner_profile.md` for Obsidian). Keys are concept tags from `parts.json`; each holds the rating history `[{session, part, axis, rating, date}]` and open misconception tags. Updated only by `end`. Read by `tutor prep` to produce `prior_gaps.md`.

Sync notes: `academic_notes/` is its own repo and the tablet syncs it, so session output is committed there by the user's normal sync. Sessions are append-only per directory, and the profile has a single writer (`end`), so there are no merge hot spots. The `sealed/` folder follows the repo's existing IP ignore rules; check them before staging.

## 7. Audit

`tutor audit` replays the log and reports: advances without a preceding `confirm_advance`, hint-level jumps without a stuck/hint request, `sealed` reads outside permitted states, intent labels that contradict the student's text (keyword heuristic), and missing `say` coverage (tutor turns with no lint record, which means the agent bypassed the gate). The audit is the stand-in for the hard wall: drift becomes visible even when it isn't blocked.

## 8. Testing

- Unit: FSM transition table, hint-level rules, rating ceilings, glossary lint, message lint.
- **Regression replay**: the five beta deviations (Turn 4/5 scaffolding, Turns 4/15/19 advancement, Turn 11/12 bridging, Turn 19/20 contradiction prescription, Turn 23/24 grade inflation) become fixtures; each must be rejected by `say`, the FSM, or `close-part`.
- Fixture packet built from HW4; no live corpus writes in tests (per the worktree policy).
- No test depends on a live LLM except an optional, gated `prep` smoke test.

## 9. Integration with existing code

Reuse, don't modify: `problem_set_parser`, `retrieve_passages`, `session_log` conventions. At plan time, check whether `tutor_diagnosis.Diagnosis` rubric fields can be shared with `rubric.json`; if not, keep the two independent. The Antigravity bootstrap (a short prompt file or workflow that runs `tutor start` and states the "call `student` then `say` every turn" contract) must be confirmed against Antigravity's workflow/shell-permission features during planning.

## 10. Future extensions (not in v1)

v1 assumes an existing, structured problem set (§3.1 parses it into parts). The extensions below are deferred until v1 works end to end. To keep them cheap, v1 treats `packet/` as the only contract between prep and the live session: anything that can produce a valid packet can drive a session.

### 10.1 Session modes

1. **Topic / timeframe review.** The student states a topic and scope in plain language ("what we covered in the past week in microeconomics", "everything up to now for the midterm"). A scope resolver turns that into a bounded set of course material (by date, lecture or note range, using the index and card metadata). The tutor then calls the existing **problem set generator pipeline** on that subset to produce problems, converts them into a packet (`parts.json` etc.), and the normal Socratic session runs on it. Needs: a scope resolver, an adapter from generator output to packet format, and sealed solutions generated from the same grounded material.
2. **Study-guide walkthrough.** The student supplies a study guide (possibly from the study guide pipeline) and picks one of:
   - *Practice problems:* falls back to mode 1, with the guide's topics as the scope.
   - *Walkthrough:* a Q&A mode with no problem set, where the tutor goes through the guide's topics and answers the student's questions, grounded in the guide and the retrieved course material. It reuses the FSM's pacing gate (student-controlled advancement), the define-only boundary and the calibrated gap logging, but drops the proof-solving states and the sealed solution.

Design implications to preserve now: keep `parts.json` generic (a "part" may be a problem or a topic), keep the FSM state set configurable per session mode, and keep concept tags free of any problem-set assumption.

### 10.2 Learning-progress tracker (separate subproject)

Spaced review driven by `learner_profile.json`: schedule review problems per open gap, track decay across courses, surface a dashboard. v1 only guarantees the profile schema is stable and versioned (`schema_version` field) so this can build on it. The review problems themselves would come from mode 1 above.

## 11. Open risks

- The agent skipping the CLI is the main residual risk; the audit's "missing `say` coverage" check is the detector, not a preventer.
- Lexical lint will miss paraphrased strategy hints; the sealed-overlap and student-first-named rules are the second line.
- Intent classification errors can mis-drive the FSM; mitigated by verbatim storage and audit, not eliminated.
