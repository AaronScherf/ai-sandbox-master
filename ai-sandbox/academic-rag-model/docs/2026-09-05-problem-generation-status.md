# Problem Generation: Real End-to-End Validation

Real-corpus validation of `problem_gen/` (spec:
`docs/superpowers/specs/2026-09-03-problem-generation-design.md`, plan:
`docs/superpowers/plans/2026-09-03-problem-generation-plan.md`, Task 7),
run against the real math-camp corpus with a real, locally-running
Ollama model — not the mocked unit tests. Two real bugs were found and
fixed here; two real capability limitations were found and are recorded
below as known, not fixed (they're model-capability limits, not code
defects).

## Setup

- Corpus: real `academic-hub/academic_notes/math-camp/` (problem sets,
  past exams, TA notes) — already indexed with `doc_type` populated.
  Passage-level chunks had to be built for this worktree specifically
  (`.index/chunks/` is gitignored, so a fresh worktree checkout starts
  without them, unlike the file-level `.index/*.json` cards which are
  tracked). Chunking the 5 real textbooks failed as expected — their
  `.md` files are also gitignored (real copyrighted content, correctly
  excluded from a fresh checkout) — so the content pool (`doc_type=
  "textbook"`) was empty for every real run below; only the style pool
  (`doc_type="problem_set"`) had real data in this environment.
- Ollama: confirmed running locally, **CPU-only inference** (`ollama ps`
  showed `100% CPU`, no GPU).

## Bug #1: the default model doesn't exist

The design's chosen default, `qwen2.5-math:7b`, is **not a real
pullable Ollama library model**. `ollama pull qwen2.5-math:7b` and
`qwen2.5-math:7b-instruct` both fail with `Error: pull model manifest:
file does not exist`. A web search confirmed only two real options:
a community upload under a different namespace
(`mightykatun/qwen2.5-math:7b`), or the official older-generation
`qwen2-math:7b`. Chose the official one — pulled and confirmed working.
Fixed in `problem_gen/llm_gen.py`'s `PROBLEMGEN_OLLAMA_MODEL` default,
with both READMEs updated to match (commit `386f7e7`).

## Bug #2: the per-call timeout was far too short

`OLLAMA_REQUEST_TIMEOUT_SECONDS = 180` was copied from `viz/`'s own
constant without re-measuring for this module's actual workload. Every
real call at 180s hit the timeout — none succeeded. Root cause: this
module's expected output (a full problem statement plus a full worked
solution) is much longer than `viz/`'s short Plotly code snippets, and
this machine's Ollama has no GPU. Bumped the per-request timeout to
900s purely to measure real behavior, then set a permanent value from
that evidence. Fixed to `300` seconds (commit follows this doc).

## Real generation runs

**Topic 1: "a problem on eigenvalues and diagonalization"** (genuine
math-camp topic, real style-pool coverage)
- Wall-clock: **22m43s** for the whole `generate_problem()` call.
  Attempt 1's generation call itself hit the (then-900s-budgeted) call
  without completing in a reasonable window before attempt 2 succeeded
  — the two "Generating a practice problem..." console lines confirm
  two full generation attempts were needed.
- Generated problem: a genuine, well-posed request to prove that a
  linear operator's eigenspaces for distinct eigenvalues span the whole
  space as a direct sum — a real theorem, not a copy of any retrieved
  example (the style examples were about *computing* eigenvalues/
  diagonalizing a specific matrix; this is the more abstract structural
  theorem behind that computation).
- **Solution correctness, checked by hand: flawed.** Step 1 asserts
  eigenspaces for distinct eigenvalues are "pairwise orthogonal" — this
  is false in general (only true for special operator classes like
  self-adjoint/normal operators on an inner product space, not for a
  generic linear operator on a generic vector space, which is exactly
  what the problem itself states). Step 2's spanning argument invokes
  "since T is diagonalizable" to justify the very decomposition the
  problem asks to prove — circular reasoning. The final boxed answer is
  the correct statement, but the proof supporting it has real gaps.
  **Verification (a second call to the same model) returned `VALID`
  anyway.**

**Topic 2: "a problem on supply and demand curves"** (deliberately
mismatched — an economics phrase against a pure-math corpus, with
`course="math-camp"` given explicitly)
- Wall-clock: **9m16s**. Attempt 1's generation call timed out at the
  (by-then-permanent) 300s; attempt 2 succeeded.
- This surfaced a real, undocumented behavior: **style-pool retrieval
  has no relevance threshold.** With an explicit `course` given,
  `search_passages` still returns math-camp's most-cosine-similar
  `problem_set` chunks regardless of how weak that similarity actually
  is — here, contraction-mapping/fixed-point problems from an old exam
  and problem set. The generated problem drifted toward *that* topic
  (a Banach fixed-point equilibrium argument) rather than anything
  resembling "supply and demand curves." Nothing in `generate_problem`'s
  return value signals that this happened — a caller has no way to
  distinguish "grounded, on-topic style examples" from "closest
  available, weakly-relevant style examples" from the result alone.
- **Solution correctness, checked by hand: shallow.** It restates the
  Banach fixed-point theorem's conclusion nearly verbatim as its own
  proof, without deriving the actual crux of the problem as posed (that
  `T` remains a contraction, with a uniform constant, for `θ` near
  `θ_0` — the real content of a parameter-continuity argument). Again,
  **verification returned `VALID`.**

**Empty-style-pool short-circuit** (a nonexistent course, so
`doc_type="problem_set"` retrieval returns zero cards by construction):
confirmed instant (~2s, no Ollama call attempted) — this path works
exactly as designed, no finding here.

## Known limitations (not fixed — real model-capability limits)

1. **Self-verification does not reliably catch subtle math errors.**
   Both real runs above produced a solution with a genuine flaw
   (a false claim in one case, circular/shallow reasoning in the
   other), and both were rated `VALID` by a second call to the *same*
   local model. This is a real limit of asking a small (~7B) local
   model to grade its own math, not a bug in `generate_and_verify`'s
   control flow — the retry-on-`INVALID` mechanism works exactly as
   built; the model's own judgment is what's unreliable. A stronger
   verification approach (an independent, larger, or differently-
   prompted checker) is a real candidate follow-up, not built here.
2. **No relevance threshold on style-pool retrieval.** A topic with
   weak or no real coverage in the resolved course still returns
   "closest available" real problems and the generation drifts toward
   their topic/style, with no signal surfaced to the caller. Worth a
   future design pass (e.g. a minimum-cosine-similarity cutoff that
   falls back to the same "no style examples" `None` path already
   built) if real usage shows this misleads more than it helps —
   real-evidence-driven, not spent here.

## Operational takeaway

On CPU-only Ollama, a single `generate_problem()` call took **9–23
minutes** across the two real trials here, each needing 2 of the
allowed 3 generate+verify attempts. Both READMEs (`README.md`,
`problem_gen/README.md`) now set this expectation explicitly rather
than reusing `viz/`'s much shorter "~1 minute" framing, which does not
transfer to this module's longer expected output.

## Follow-up candidates from final review

Real-evidence-driven ideas for a future pass — not fixed here, not
required for this branch to merge.

1. **The verification-timeout retry path regenerates instead of
   re-verifying.** In `problem_gen/llm_gen.py`'s `generate_and_verify`,
   the branch handling a verification call's `OLLAMA_TIMEOUT` composes
   feedback text saying "the verification request itself timed out" and
   feeds that into the *next generation attempt's* prompt. That framing
   is nonsensical — a network timeout isn't something to "fix" in a
   math solution — and the retry discards a possibly-good
   problem/solution pair and regenerates the whole thing from scratch.
   A cheaper, more correct fix would just re-verify the existing pair
   instead of regenerating it.
2. **`_parse_verdict`'s loose prefix check can fail both open and
   closed.** `problem_gen/llm_gen.py`'s `_parse_verdict` checks
   `stripped.upper().startswith("VALID")`, which would incorrectly
   accept a response like "VALIDATION FAILED: ..." as valid (fail-open),
   while a formatted response like "**VALID**" would incorrectly fall
   through to the "unexpected format" branch (fail-closed, wasting a
   full retry on a verdict that was actually fine). A word-boundary
   regex match would handle both cases correctly.
3. **`_extract_problem_and_solution` takes the leftmost `## Problem`/
   `## Solution` match, which the prompt's own template skeleton could
   trigger.** The generation prompt in `problem_gen/llm_gen.py` itself
   contains a literal `## Problem` / `## Solution` template skeleton
   (the instructions to the model). A small model that echoes part of
   its instructions before answering could have that literal
   placeholder text extracted by `_SECTION_PATTERN` instead of its real
   answer, since the regex takes the first match in the response text.
   Taking the last match instead of the first, or rejecting a body
   that's just a `<placeholder>`-shaped marker, would be more robust.
4. **The generated solution text never enters conversation history.**
   By deliberate design choice, only `problem_text` is appended to
   history in `rag/rag_agent.py`'s `answer_question()` — `solution_text`
   is returned to the caller but never stored. This means a natural
   follow-up like "walk me through step 2" has no solution text in
   context to work from. This is a known, disclaimed non-goal (no
   conversation-state work was in scope for this feature), not a
   defect — but it's a real seam worth a future design pass if
   follow-up-on-a-generated-problem becomes a real use case.

## 2026-09-06: user dogfooding — constraint enforcement, visualize toggle, and a real meta-commentary bug

Two follow-ups were built after the user tried the shipped feature
themselves and found the model ignoring an explicit request ("must use
an epsilon-delta proof") in favor of the open-cover technique used by
the retrieved style examples:

1. **Constraint enforcement**: `_build_generation_prompt` now restates
   the student's literal request a second time as a separately labeled,
   imperative "Required constraint" block (verbatim, not parsed/split
   from the topic string), and `_build_verification_prompt` now also
   checks whether the generated problem actually satisfies that
   constraint, not just whether the math is correct.
2. **Visualize toggle on the problem-generation path**: `rag_agent.py`
   can now trigger a visualization for a generated problem via an
   explicit in-text request ("visualize this", "make a graph") or the
   existing `visualize=True` flag — previously this was silently
   unreachable on that code path (see Follow-up candidate above about
   this same integration gap, now closed).

**Real re-trial after the constraint-enforcement fix.** Re-ran the same
compactness/epsilon-delta request that originally motivated the fix.
Result: **the constraint was still not honored.** The style pool this
time genuinely retrieved a "Sequential Definition of Compactness" chunk
from the student's own notes — the right material was available — but
the model still produced an open-cover proof anyway (for a different
example problem: non-compactness of ℚ∩[0,1]). This upgrades the earlier
hypothesis to a confirmed finding: **prompt-level emphasis alone is not
enough to override this 7B model's tendency to imitate the dominant
technique in its retrieved style examples.** Restating a constraint more
forcefully in the prompt is necessary but evidently not sufficient here;
further prompt iteration on this specific point looks like it has
diminishing returns without changing the model or the retrieval
strategy (e.g. filtering style examples toward the requested technique
before generation, or using a larger/instruction-tuned model for
constraint-sensitive requests). Options for addressing this are being
discussed with the user next, not decided here.

The same re-trial also surfaced a genuine, previously-unseen bug: the
accepted solution's text ended with *"The verification response was not
in the expected VALID/invalid format. The solution has been corrected
to provide a clear, valid proof."* — a near-verbatim echo of
`_parse_verdict`'s own internal fallback message. **Root cause:** the
retry prompt tells the model `"That attempt failed with: {previous_error}
... Write a corrected problem and solution"` but never told it not to
*narrate* that correction in its actual answer — so the model included
a sign-off sentence referencing the internal feedback text, which then
got extracted as part of the "real" solution. **Fixed** by adding an
explicit instruction to the retry prompt: not to mention the correction,
the previous attempt, or the verification process anywhere in the
answer, and to write as if it were the first and only attempt. Covering
test: `TestBuildGenerationPrompt.test_retry_instructs_not_to_reference_the_correction_process`.
Full suite re-run: 849/849 pass. This fix reduces the *likelihood* of
this specific leak; it does not structurally prevent a small model from
narrating in some other, differently-worded way — a residual risk worth
watching for in future real trials, not something a regex-based
extraction filter was added to chase here (per this project's general
preference for prompt-level fixes over guessing at every possible
hallucinated phrasing).
