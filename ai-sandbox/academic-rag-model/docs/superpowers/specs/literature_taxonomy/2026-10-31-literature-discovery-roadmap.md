# Literature taxonomy: roadmap to a discovery loop

Date: 2026-10-31. Status: proposal for the owner's approval. Nothing here is built. Scope: `agent/literature`.

## Where we are

On `main`: extraction (two passes, checker, confidence tiers), synthesis, the query database, and gap analysis with an opt-in
OpenAlex recall probe (`gap run --probe`). The same-label-branches question is decided (opt-in label groups). The tracker's
literature section is closed except TODO-0091.

Known open items, none of them blocking the above:
- TODO-0091 (reference data separated from the vocabulary directory); the 8 deferred minors from gap slice 1.
- Quality: the committed gold set is a silver set (about 12 papers); recall of facts both passes missed is unmeasured; 11 vocabulary
  proposals await a decision; the review page for proposed terms (stage 2b) is not built; there is no adjudication for real
  disagreements; on the real database, 83 tier C facts are open and 8 eligible papers have no record.
- TODO-0092: clean up stale worktrees, after this subproject.

## Goal

A deliberate, opt-in loop: when a gap run finds the corpus thin, find relevant external works, review them in a queue,
and (separately, by choice) add accepted ones to the corpus. The probe stays the measurement; expansion is a second phase.

## Phases

### Phase 0: housekeeping
TODO-0091 and the 8 minors. Small, independent, test-first.

### Phase 1: quality gate on the taxonomy as it is
Expansion runs new papers through the same extraction, so weaknesses in extraction or vocabulary would be multiplied. Before
building, the owner decides pass criteria (not set here) for:
1. Gold set: a hand-checked set larger than the current 12, then `eval` for precision and recall.
2. Open vocabulary proposals (11) accepted, merged or rejected, ideally through the stage 2b review Artifact.
3. The tier C backlog and the 8 papers without a record worked down or explicitly accepted as a known gap.
4. A decision on adjudication or a third pass for real disagreements.

Outcome: a short status doc saying "meets the bar" or listing what must change first.

### Phase 2: discovery loop design (Claude, brainstorm then spec)
Decisions to make with the owner:
- Live search wording and the **held-out split**: probe wordings used to decide what to expand versus wordings used only to
  re-measure coverage afterwards, so a better recall number cannot come from tuning the corpus to its own test.
- Classification card (direct / adjacent / neither from title and abstract) and what counts as "relevant enough to queue".
- Discovery queue Artifact (check, link, dismiss; decisions in its `db`), and how accepted items enter the existing discovery
  accept/reject functions.
- `found_externally_not_in_corpus` as an additive verdict: queue the relevant hit, and its precedence over corpus-adjacent evidence.
- The expansion phase: snowball rules (citations in and out), stopping rule, a cost and API warning before any paid step.

### Phase 3: build (plan, then tasks as in the routing table)

### Phase 4: cleanup
TODO-0092, from a fresh shell in the main checkout, after Phase 3 lands.

## Who does what

Follows `docs/AGENT_ROUTING.md`: Codex takes routine, well-specified work and stops to flag any design question; Claude takes
design, the Artifact, and review; Gemini operates existing pipelines and reads at scale; the owner makes the judgments.

| Step | Owner of the work | Why |
|---|---|---|
| Phase 0: stale `candidates.json` deleted after a successful `gap run` | Codex | Behaviour is fully specified: delete it on success; test it |
| Phase 0: clear error instead of a traceback on a db with no tables | Codex | Message and exit code 2, as other `gap` errors |
| Phase 0: `--pick` that is ignored (unused facet, wrong facet, already resolved) | Codex | Specified: exit 2 naming the unused pick |
| Phase 0: Windows reserved run ids (`con`, `nul`, `com1`...) | Codex | Reject in `gap_dir`'s run-id check |
| Phase 0: `report.json` and `report.md` written as a pair | Codex | Write both temp files, then replace both |
| Phase 0: fuzzy country-name candidates; a fact satisfying both a constraint and its widening; report text outside the ignored tree | Claude first | Each needs a rule decided before it can be handed off; Claude writes the rule, then Codex implements |
| Phase 0: TODO-0091 | Codex, with Claude review | Approach is in the tracker; it touches the shared vocabulary loader, so every caller's tests must pass, and any design question goes back to Claude |
| Phase 1: gold set hand-checking and pass criteria | Owner | Only the owner can judge correctness; Gemini may prepare the reading |
| Phase 1: run `eval`, `silver`, `tiers`; operate extraction and verify cards for the 8 papers and tier C backlog | Gemini | Existing pipeline, documented commands, relayed through Antigravity |
| Phase 1: accept or reject the 11 proposals | Owner | Vocabulary judgment |
| Phase 1: stage 2b review Artifact design | Claude | New Artifact; repo rule requires an interactive page for human decisions |
| Phase 1: stage 2b Artifact build and its apply functions | Codex, from a Claude spec | Mechanical once the page contract and `Proposals.accept/merge` calls are specified |
| Phase 1: adjudication decision | Claude with the owner | Design tradeoff |
| Phase 2: all design and the spec | Claude | Architecture and cross-session decisions |
| Phase 3: OpenAlex fetch, parsing and recorded-fixture tests | Codex | Well specified once the spec exists; reuse `discovery` helpers |
| Phase 3: classification card (prompt, validation) | Claude | Prompt and validation design, matching the other cards |
| Phase 3: classification card runs | Gemini | Subscription route via Antigravity, relayed by the owner |
| Phase 3: discovery queue Artifact | Claude | Design and capability choices |
| Phase 3: verdict and held-out-split logic in `gap/` | Claude | Changes what the report claims |
| Phase 3: final branch review | Claude | Review is Claude's remit |
| Landing | Owner | Only the owner lands on `main` after `land_branch check --full` |
| Phase 4: worktree cleanup (TODO-0092) | Codex | Git mechanics; never remove a worktree with unlanded or dirty work without asking |

## Constraints that carry over

Worktree per task; explicit-path staging; no paid API calls without a warning and go-ahead; quotes and 3ie term text stay local
and uncommitted; the repo is public. The recall probe and any live search send only query wording and the owner's
contact address to OpenAlex, never paper text.
