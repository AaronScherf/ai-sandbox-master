# Socratic Tutor (`agent/tutor`)

A session gate for live Socratic office hours. An IDE agent (Antigravity first) does the dialogue; this package owns
the rules. The agent calls a local CLI every turn. The CLI replays an append-only event log through a pure state
machine, marks which **claims** the student has established (prep-authored recognizers run over the student's own
words), rejects tutor drafts that introduce a claim the student has not reached, releases a part's solution once for a
quoted step check, caps ratings by logged evidence, and persists sessions and a learner-gap profile into the vault. No
model call happens at runtime.

Not the same thing as `agent/rag/` (the RAG Q&A and `/draft` diagnosis REPL). For a tutoring session, use this package.

Design: `docs/superpowers/specs/2026-10-08-socratic-tutor-v1-1-design.md` (amends the v1 spec). Plan:
`docs/superpowers/plans/2026-10-08-socratic-tutor-v1-1-plan-a.md`. Skip/defer/revisit, pause and profile v2 (Plan B):
`docs/superpowers/plans/2026-10-09-socratic-tutor-v1-1-plan-b.md`.

## Flow

1. **Prep (once per problem set).** `prep-collect` parses the problem set, retrieves grounding passages (the only
   network call: a Gemini query embedding via `agent.rag.rag_agent.retrieve_passages`) and writes a packet skeleton
   plus `worklist.md`. The IDE agent fills in the glossary, rubric, solution steps, `claims.json` and, in a separate
   blind pass, `samples.json`; `prep-submit` validates everything, runs the recognizer self-test and writes
   `validated.json`. Any later edit to a hashed file invalidates the packet until `prep-submit` is run again.
2. **Session.** Paste the output of `bootstrap` into the agent. `start`, send the launch line through `say`, then each
   turn is two commands: `turn` (logs the student's message, updates the ledger, returns a **brief**: state, claims
   established, pitfalls hit, `rules`, `next`) and `say` (lints the draft; send only an `ok` result).
3. **Finish a part.** When the brief says `verify_available`, `verify` releases the solution steps once; the agent
   submits a step check with quotes (`verify --check-file`). A clean check closes the part with ratings; defects
   reopen it. A student `confirm_advance` moves on. `end` renders the transcript, summary and learner profile.

```powershell
python -m agent.tutor.cli --hub-root ../academic-hub --course microecon --problem-set homework_4 <command>
```

## Commands

| Command | Purpose |
|---|---|
| `prep-collect --problem-set-file F --question-ref N [--hints-file --solutions-file --force]` | Build the packet skeleton. |
| `prep-submit` | Validate the packet (including the self-test) and write the marker. |
| `bootstrap` | Print the agent's operating contract with paths filled in. |
| `start [--fresh]` | Create or resume a session (a paused one resumes); `--fresh` ends the open one as partial and begins a new one. Returns the brief with `launch_text`. |
| `turn --intent I (--stdin \| --text-file F \| --text T) [--admits-gap [axis]] [--define TERM] [--establish C --establish-quote Q] [--flag-slip TAG[:axis] --slip-quote Q] [--resolve TAG --resolve-quote Q] [--skip] [--part P]` | Log a student message and return the brief. Manual flags need a quote the student wrote. `--skip` marks a skip request; `--part` names the parked part for `--intent revisit`. |
| `say (--stdin \| --text-file F \| --text T) [--check]` | Lint a tutor draft; `ok` returns `send`. `--check` logs nothing. A rejection is normal. |
| `verify [--check-file F] [--downgrade axis=rating ... --why TEXT]` | Without a file: release the solution steps once. With a file: submit the step check. |
| `pause` | Stop for now: write the documents and the profile and block turns until `start`. |
| `end --big-picture-file F` / `end --partial` | Finish the session and render documents (`--partial` is `pause`). Refused while parked parts have not been offered in a closing message. |
| `audit [--session ID]` | Re-lint a session (open or finished) from its log. |

Exit code 0 when `ok`, 2 otherwise; output is JSON. Every error is `{"ok": false, "error": ..., "next": [...]}`.

## Packet (`<hub>/academic_notes/<course>/tutoring/<ps>/packet/`)

`parts.json`, `glossary.json`, `rubric.json`, `claims.json`, `samples.json`, `sealed/solution.md` (one `## <part_id>`
section per part with `### Step N` headings), `grounding.md`, `validated.json`, `prior_gaps.md`. `sealed/hints.md` is
optional reference and is not used at runtime.

A recognizer is `{"all": [[entry, ...], ...], "window": N}`: every group must have a hit within N consecutive words.
An entry matches a whole word; one ending in `*` matches a prefix. Example (a claim that the others must not be
considered): `{"all": [["consider*"], ["better", "higher"], ["not", "never", "fail*"]], "window": 14}`.

## `say` rules

Short launch line (`"Question 1.3. How would you like to approach this problem?"`; the statement is in the brief);
verbatim definitions after `define_request`; **disclosure** (no recognized unreached claim; level 3 may state the next
claim; copied 6-word runs of the problem statement are ignored); **question form** at hint levels 0-1 (one question,
60 words, one sentence restating the student's words); check-in wording once a part is closed; no next-part mention
before the student confirms; Unicode math in chat.

## Vault output

`<ps>/sessions/<YYYY-MM-DD-HHMM>/{events.jsonl,transcript.md,summary.md}` and `tutoring/learner_profile.{json,md}`
(`schema_version` 2: history entries carry `status` rated | deferred | skipped and `attempt`; written by `end` and `pause`).

## Known limits

- Soft wall: the agent can read `packet/` files and the tutor source directly; that is undetectable. The audit flags
  symptoms (replies without `say`, manual overrides, a release without coverage).
- Recognizers are lexical: an unforeseen phrasing neither establishes a claim nor trips the disclosure check. The
  blind-sample self-test and manual `--establish` (audited) are the mitigations.
- `verify` depends on the agent comparing the student's words with the released steps honestly; quote validation and
  the summary's list of confirmed steps make a rubber stamp visible, not impossible.
- Manual overrides (`--establish`, `--flag-slip`, `--resolve`) and `verify`'s confirmed steps need a quote of at least 3 words
  (or the student's whole shorter message) that appears in the part's student messages. That raises the bar but a manual
  override is still an attestation by the agent; the audit lists every one with its quote.
- Intent labels come from the agent; the audit cross-checks obvious mismatches.
- Piping text through PowerShell needs `$OutputEncoding = [Text.UTF8Encoding]::new($false)` (in the bootstrap
  contract). Verified on Windows PowerShell 5.1; fall back to `--text-file` if symbols turn into `?`.
- The 8-word real-attempt threshold, the 20-word acknowledgement and the 60-word question cap are guesses to tune from live runs.
