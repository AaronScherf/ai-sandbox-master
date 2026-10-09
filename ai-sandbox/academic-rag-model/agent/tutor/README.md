# Socratic Tutor (`agent/tutor`)

A session gate for live Socratic office hours. An IDE agent (Antigravity first) does the dialogue; this package
owns the rules. The agent calls a local CLI every turn, the CLI replays an append-only event log through a pure
state machine, lints every tutor message before it is sent, caps ratings by logged evidence, and persists sessions
and a learner-gap profile into the vault.

Not the same thing as `agent/rag/` (the RAG Q&A and `/draft` diagnosis REPL). For a tutoring session, use this package.

Design: `docs/superpowers/specs/2026-10-08-socratic-tutor-pipeline-design.md`. Plan: `docs/superpowers/plans/2026-10-08-socratic-tutor-pipeline.md`.

## Flow

1. **Prep (once per problem set).** `prep-collect` parses the problem set, retrieves grounding passages (the only
   network call: a Gemini query embedding via `agent.rag.rag_agent.retrieve_passages`) and writes a packet skeleton
   plus `worklist.md`. The IDE agent then fills in the glossary, rubric, concept tags, expected evidence and sealed
   hints/solution, and `prep-submit` validates them (schema, glossary lint) and writes `validated.json`. Any edit to
   the packet afterwards invalidates it until `prep-submit` is run again.
2. **Session.** Paste the output of `bootstrap` into the agent. Each turn: `student` (log the student's message and
   an intent label) -> follow the returned `guidance` -> `say` (lint the draft; send only an `ok` result).
3. **Persist.** `end` writes `transcript.md` and `summary.md` and updates the course's `learner_profile.json`.

```powershell
python -m agent.tutor.cli --hub-root ../academic-hub --course microecon --problem-set homework_4 <command>
```

## Commands

| Command | Purpose |
|---|---|
| `prep-collect --problem-set-file F --question-ref N [--hints-file --solutions-file --force]` | Build the packet skeleton. |
| `prep-submit` | Validate the packet and write the marker. |
| `bootstrap` | Print the agent's operating contract with paths filled in. |
| `start` | Create or resume a session; returns state, `guidance`, and the verbatim `launch_text`. |
| `student --intent I (--text T \| --text-file F) [--misconception tag[:axis]] [--admits-gap [axis]]` | Log a student message and apply the transition. Use `--text-file` for anything with math or quotes. |
| `say (--text T \| --text-file F)` | Lint a tutor draft. `ok` returns `send`; otherwise returns violations to fix. |
| `define TERM` | Glossary definition only. |
| `sealed hint\|solution` | Sealed content for the current part; refused before a student attempt; every call is logged. |
| `verdict --assessment correct\|on_track\|adjacent\|off_track` | Record the agent's judgment of an attempt. |
| `misconception TAG [--axis A] [--resolved]` | Log or resolve a student error. |
| `close-part --ratings-file F` | Record the tri-axial rating; rejected above the evidence ceiling. |
| `end --big-picture-file F` | Finish the session and render documents. |
| `audit` | Re-lint the session from its log. |

Exit code 0 when `ok`, 2 otherwise; output is JSON.

## Packet (`<hub>/academic_notes/<course>/tutoring/<ps>/packet/`)

`parts.json` (part_id, label, statement, concept_tags, expected_evidence, optional chat_statement), `glossary.json`
(`{term: generic definition}`), `rubric.json` (`{part_id: {conceptual|rigor|directness: {rating: descriptor}}}`),
`grounding.md`, `sealed/hints.md` and `sealed/solution.md` (one `## <part_id>` section per part), `validated.json`,
`prior_gaps.md` (refreshed by `start`).

## State machine

`LAUNCH -> WORKING -> VERIFIED -> AWAITING_ADVANCE -> (next part LAUNCH | SYNTHESIS) -> DONE`. Hint level (0-3) rises
only on an explicit student `stuck`/`hint_request`; level 3 needs two failed attempts at level 2. A part advances only
on a logged student `confirm_advance`, after `close-part`.

## Vault output

`<ps>/sessions/<YYYY-MM-DD-HHMM>/{events.jsonl,transcript.md,summary.md}` and `tutoring/learner_profile.{json,md}`
(`schema_version` 1; single writer: `end`).

## Known limits

- Soft wall: the agent can still read `sealed/` files directly. Reveals through `sealed` are logged; direct reads are
  not detectable. `audit` flags the symptom (replies without `say`), not the read.
- Lint is lexical. It catches named techniques, problem notation in definitions, sealed-solution phrases, leading
  sub-question lists, early mention of the next part and LaTeX in chat. It cannot catch a paraphrased strategy hint.
- Intent labels come from the agent; the student's verbatim text is stored so `audit` can spot obvious mislabels.
- Not yet validated against a live Antigravity run.
