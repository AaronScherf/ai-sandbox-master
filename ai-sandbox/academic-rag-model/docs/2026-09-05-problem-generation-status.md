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

## 2026-09-06 (continued): split TECHNIQUE/CORRECTNESS verification — does it actually help?

Per the option chosen with the user (cheapest experiment first: a
narrower, separately-judged verification check, before considering a
model swap or paid-API batching): `_build_verification_prompt` now asks
for two independently-judged, separately-labeled lines instead of one
combined verdict — `TECHNIQUE: YES/NO` and `CORRECTNESS: VALID/INVALID:
<reason>` — in the same single call (not two network round-trips, to
avoid doubling an already multi-minute-per-call workload).
`_parse_verdict` combines both into one retry-feedback reason, fails
closed on either line being unparseable, and tolerates markdown bold
formatting.

**Real trial #1 (MAX_ATTEMPTS still 3).** Re-ran the same epsilon-delta
compactness request. Result: `None` after exhausting all 3 attempts —
but the instrumented trace showed the fix *is* doing its job: on the
one attempt that reached a clean verification response, the model
explicitly said `TECHNIQUE: NO — the solution does not use an
epsilon-delta style argument or the sequential/metric definition of
compactness, as required` while `CORRECTNESS: valid` — exactly the
case the old combined verdict got wrong (a mathematically valid proof
using the wrong technique, previously rubber-stamped `VALID`). The
technique failure alone now correctly forces rejection, independent of
correctness passing. The run failed to produce a final result only
because one of the 3 attempts was entirely consumed by an
`OLLAMA_TIMEOUT` retry, not a bad proof — real evidence, not a guess,
motivating the `MAX_ATTEMPTS` bump below.

**`MAX_ATTEMPTS` bumped 3 → 5** on this evidence (real headroom for the
technique-check to actually get enough real attempts, without doubling
the worst case).

**Real trial #2 (MAX_ATTEMPTS=5, instrumented with full prompt/response
logging).** All 5 attempts got a real shot this time (no timeouts
wasted). Result: still `None` — every attempt was correctly rejected by
the technique check, and the model never settled into reliably
satisfying the constraint:

- Attempts 1–3 used open-cover/closure arguments dressed up with
  claims like "we will use the sequential definition of compactness"
  in their opening sentence, without the actual proof mechanics
  matching that claim. The verifier correctly said `TECHNIQUE: NO` each
  time (though its own stated reasoning was sometimes confused — e.g.
  once describing the constraint backwards, "uses sequential... instead
  of open cover" when open-cover was the *unwanted* technique — a
  reminder that the verifier's judgment, while directionally right here,
  is itself an unreliable small-model judgment, consistent with the
  known self-verification limitation logged above).
- **Attempt 4 was the closest real progress observed**: the solution
  introduced an actual sequence `{x_n}` and invoked sequential
  compactness ("every sequence in a compact set has a convergent
  subsequence whose limit is in the set") as its key step — genuinely
  using the requested characterization, just without literal
  epsilon-delta notation. It was still rejected, via a terse,
  unexplained `TECHNIQUE: NO` / `CORRECTNESS: VALID` with zero
  justification — plausibly a defensible call (no literal ε/δ
  formalism), plausibly just verifier noise. Real ambiguity, not a bug.
- Attempt 5 regenerated a near-identical proof to attempts 2–3
  (open-cover dressed as "sequential"), rejected the same way.

**A genuine parsing bug found and fixed from this trial's raw log**:
when a verification response had a *bare* `TECHNIQUE: NO` with nothing
else on that line, immediately followed by a `CORRECTNESS: ...` line,
the old regex's `\s*` (which also matches newlines) swallowed the line
break and captured the **entire next line** as the technique's own
"detail" — producing corrupted retry feedback fed into the next
generation attempt: *"does not use the required technique (used
instead: CORRECTNESS: VALID)"*. Fixed by restricting the connective
whitespace around each label's value to `[ \t]*` (never crossing a
newline). Covering tests:
`test_bare_technique_no_does_not_swallow_the_next_line`,
`test_bare_correctness_invalid_does_not_swallow_a_preceding_technique_line`.
Full suite re-run: 856/856 pass. A related, lower-priority parsing gap
was also observed but not fixed: a response phrased `CORRECTNESS:
isValid` (rather than a clean `VALID`) failed to parse — safely
fail-closed in that instance (technique had already said `NO`), but a
residual robustness gap worth revisiting if it recurs and actually
changes an outcome.

**Conclusion — local feasibility for this class of request.** Two
independent real trials (3 attempts, then 5 clean attempts with no
wasted timeouts) never produced an accepted result for this specific
highly technique-constrained request, despite the verification fix
correctly catching every clear technique violation. This is now solid
evidence — not a single anecdote — that **the bottleneck is this local
7B model's capability, not the retry budget, not Ollama flakiness, and
not (any longer) the verification logic.** Attempt 4's partial success
suggests the model *can* occasionally get close, but not reliably.
Continuing to tune the local retry/verification loop further looks like
it has genuinely diminishing returns for this kind of request; the
next real levers are the ones already on the table with the user — a
larger/different local model, or Gemini API batching (with its real
cost tradeoff) for constraint-sensitive requests specifically, rather
than further prompt or parsing iteration on the current model.

## 2026-09-06 (continued): Gemini Flash-Lite feasibility spike

**Setup.** A throwaway spike script (not committed, not wired into
`problem_gen`) reused the *exact same* prompt-building and
verification-parsing functions from `llm_gen.py`
(`_build_generation_prompt`, `_extract_problem_and_solution`,
`_build_verification_prompt`, `_parse_verdict`) for a fair,
apples-to-apples comparison — only the backend model changed, from
local Ollama to `gemini-3.1-flash-lite` via the existing
`common/gemini_utils.py` client. Three independent, single-shot trials
(no retry loop — a raw first-attempt reliability read) were run per
topic, each with an explicit technique constraint chosen to fight the
retrieved style examples' "obvious default" approach, the same shape of
test that broke the local model:

- **Real analysis / compactness** (from the earlier local trials):
  epsilon-delta/sequential proof, not open-cover.
- **Linear algebra**: diagonalizability of an operator with $T^2 = I$
  (or $T^2 = T$), proof by contradiction, not direct eigenvalue
  computation or the spectral theorem.
- **Probability theory**: convergence in probability proven directly
  from the $\epsilon$-$N$ definition, not by citing the Weak Law of
  Large Numbers, CLT, or Chebyshev's inequality as a black box.

(A fourth topic, econometrics, was dropped before running — that
course has zero indexed content of any kind in this corpus, not just
missing problem sets, so it couldn't test anything about the model.)

**Results: 9/9 passed verification across all three topics**, and every
proof was checked by hand — all mathematically correct. This is a
dramatic contrast with the local model, which never once produced an
accepted result across two independent real trials (8+ real attempts
total) on the comparably-constrained compactness request.

**Two real nuances found (not correctness failures):**
1. All three linear algebra proofs technically satisfied "prove by
   contradiction" — assume ¬P, then derive P directly, note the
   contradiction — but never actually *used* the negated assumption's
   structure to derive an absurdity. That's logically valid but a
   mechanical, fairly vacuous form of "by contradiction" (most
   mathematicians would just call it a direct proof). Verification
   only checks whether the labeled technique nominally appears, not
   whether it's doing genuine logical work — the same class of gap as
   the compactness trial's "problem doesn't actually need compactness"
   finding from earlier in this doc.
2. Probability trials 1 and 3 generated **nearly word-for-word
   identical problems** (same distribution, same setup) despite being
   independent calls; trial 2 varied it. Repeated calls aren't
   guaranteed to be diverse — relevant to the "give me another one" use
   case, since low diversity across calls would undercut the point of
   deliberately not caching (§1/§7 of the design spec).

**Speed and cost, measured against the same real-evidence standard as
the local trials.** The entire spike — retrieval for 3 topics plus 3
trials × 2 calls (generation + verification) per topic, 18 Gemini calls
total — completed in **under two minutes**, versus 10–50 minutes for a
*single* local attempt sequence. Real cost was negligible: every trial
passed on the first attempt (no retries), so actual spend was a small
fraction of a cent per problem at Flash-Lite's real pricing ($0.25/1M
input, $1.50/1M output tokens, confirmed against Google's own pricing
page 2026-09-06). The earlier worst-case estimate (assuming up to 5
attempts, the local `MAX_ATTEMPTS`) was ~$0.01/problem for Flash-Lite,
~$0.03 for Flash, ~$0.08 for Pro — all now corroborated by a real run
rather than a guess.

**Tradeoff summary:**

| | Local (`qwen2-math:7b` via Ollama) | Gemini Flash-Lite |
|---|---|---|
| Cost | Free (electricity only) | ~$0.001–0.01 per problem |
| Speed | 9–50 min per problem (real measurements) | Seconds per call, whole spike <2 min |
| Reliability on constraint-heavy requests | 0/2 real trials succeeded, even with a working technique-check and 5 attempts | 9/9 across 3 different topics |
| Network/privacy | Fully local, no data leaves the machine | Requires network + the existing `GEMINI_API_KEY` (already a project dependency for retrieval embeddings) |
| Verification reliability | Verifier itself is a small, sometimes-confused model | Same self-verification limitation in principle, but not observed misfiring in this testing |

**Conclusion:** for this class of technique-constrained request, Gemini
Flash-Lite is both cheaper in practice (given how much local compute
time a single local attempt burns) and dramatically more reliable.
Local generation remains free and fully private, which still matters
for some use cases, but is not the better default for requests that
carry an explicit technique constraint.

## 2026-09-06 (continued): Gemini becomes the default backend

Direct follow-through on the feasibility spike above: `PROBLEMGEN_BACKEND`
now defaults to `"gemini"` (was previously Ollama-only, no toggle).
`generate_and_verify()` and `generate_problem()` thread a `client`
parameter through so the dispatcher (`_call_model()`) can call either
backend without callers branching on which one is active. Local Ollama
generation remains available as an explicit opt-in
(`PROBLEMGEN_BACKEND=ollama`) for fully free/private generation, with the
reliability caveat from the spike above carried into the README.
`root/README.md`, `problem_gen/README.md`, and `rag/README.md` updated to
describe the new default, the opt-in, and real measured timing/cost for
each.

## 2026-09-06 (continued): report_builder integration gap + real end-to-end validation

**Bug found (not from this session's own testing — user dogfooding):**
the problem-generation branch in `rag/rag_agent.py` never called
`rag/report_builder.py`'s `build_report()` at all, regardless of
`report=True` — the same category of integration gap `--visualize` had
on this same branch until its own earlier fix (see
`docs/2026-09-02-visualization-agent-status.md`'s "Combined report"
section). A generated problem's `report=True` call silently produced no
report file.

**Fix:** wired `build_report()`/`report_path()` into the
problem-generation branch, and extended `build_report()` with a new
optional `solution` parameter — rendered as its own `<h2>Solution</h2>`
section — so a generated problem's worked solution shows up in the
combined report alongside the problem statement, citations, and (if
present) a visualization. New tests in `test_report_builder.py` (the
`solution` parameter) and `test_rag_agent.py`
(`TestAnswerQuestionProblemGenerationReport`, 4 tests).

**Real end-to-end validation**, run from `ai-sandbox/academic-rag-model`
against `../academic-hub` (`math-camp`), the same compactness/epsilon-delta
request used throughout this doc, now with `report=True` and an explicit
"Visualize this." request:

1. **Trial 1** (Ollama viz, then-default): problem generation succeeded
   via Gemini in 2 attempts, correctly using an epsilon-delta proof via
   the distance-function-to-a-compact-set technique (not the open-cover
   technique this doc's earlier local-model trials struggled to avoid) —
   consistent with the spike's 9/9 constraint-following result. The
   report was built correctly: problem, solution as its own section, and
   all 7 real citations present, with the Visualization section cleanly
   and entirely absent after the local Ollama viz fallback failed (two
   180s timeouts, then a script using an invalid Plotly property).
2. **Trial 2** (Ollama viz, then-default): same outcome shape — correct
   problem generation and report again, viz again failed on Ollama (two
   more timeouts, then a script with a numpy broadcasting error).
3. **Trial 3** (after adding `VIZ_BACKEND=gemini`, see the viz sub-agent's
   own status doc for the full detail): same correct problem generation
   and report, and this time the visualization succeeded on the first
   attempt — a real Plotly line chart embedded correctly in the combined
   report (4.3MB self-contained HTML file, one `<h2>Visualization</h2>`
   section, a real `Plotly.newPlot` call with binary-encoded trace data).

This confirms, for the first time with a real trial rather than mocked
tests, that the full pipeline — problem generation, self-verification,
report building with a solution section, and an embedded visualization —
works end to end. It also surfaced that `viz`'s own LLM fallback had the
same Ollama-reliability problem this doc already found for problem
generation, on the very first real attempt to exercise it against a
freshly-generated (never-templated) problem/solution pair — see
`docs/2026-09-02-visualization-agent-status.md`'s "Gemini fallback
backend, made the default" section for that fix.

## 2026-09-06 (continued): fixed the verification-timeout retry; triaged the rest into a to-do list

Picked up from this doc's own "Follow-up candidates from final review"
section above, after the `problem_corpus` folder-alias bug fix (see
`docs/2026-09-06-problem-corpus-extraction-status.md`) prompted a fresh
look at what else was still open.

**Fixed:** follow-up candidate #1, the verification-timeout retry path.
`problem_gen/llm_gen.py`'s `generate_and_verify()` previously treated an
`OLLAMA_TIMEOUT` on the *verification* call the same as any other
retry-with-feedback case — it discarded the already-generated
`problem_text`/`solution_text` and regenerated a brand new problem from
scratch, with feedback text ("the verification request itself timed
out") that made no sense fed into the next generation prompt. Fixed to
retry the same verification call for the same problem/solution pair
(bounded to `MAX_ATTEMPTS` tries) instead, only giving up entirely if
verification itself never gets a real response. Two new tests
(`test_reverifies_the_same_pair_after_a_verification_timeout_instead_of_regenerating`,
`test_gives_up_when_verification_keeps_timing_out`); full suite green.

**Already resolved, no longer a to-do:** follow-up candidate #2 (the
loose `stripped.upper().startswith("VALID")` prefix check that could
fail both open and closed) turned out to be stale — the "split
TECHNIQUE/CORRECTNESS verification" rework earlier in this doc already
replaced it with anchored `(YES|NO)`/`(VALID|INVALID)` regexes
(`_TECHNIQUE_LINE_PATTERN`, `_CORRECTNESS_LINE_PATTERN`) that don't have
the substring-match problem. No action needed.

### To-do (not fixed, real-evidence-driven — revisit if usage shows they matter)

**`problem_gen`:**
1. **`_extract_problem_and_solution` takes the first `## Problem`/`##
   Solution` match** (follow-up candidate #3). `_SECTION_PATTERN`'s
   trailing group is greedy-to-end-of-string, so a chatty small model
   that echoes part of its own instructional template before the real
   answer could pollute or entirely misdirect the extracted solution
   text. Needs actual design thought (e.g. stripping known template
   lines before searching, or rejecting a body that's just the
   placeholder shape) — not a one-line first/last-match swap.
2. **Self-verification does not reliably catch subtle math errors** —
   a small (~7B) local model grading its own math is a real capability
   limit, not a control-flow bug. Candidate fix: an independent, larger,
   or differently-prompted checker.
3. **No relevance threshold on style-pool retrieval** — a topic with
   weak/no real corpus coverage still returns "closest available"
   examples with no signal to the caller.
4. **Generated solution text never enters conversation history** — a
   disclaimed non-goal, not a defect, but a real seam if
   follow-up-on-a-generated-problem becomes a real use case.

**`problem_corpus`** (see
`docs/2026-09-06-problem-corpus-extraction-status.md` for full detail):
5. **Boundary detection over-splits on numbered content embedded inside
   a problem's own body** (numbered sub-statements, guided-walkthrough
   steps) — produces duplicate-labeled records on 6/8 real problem-set
   files.
6. **Boundary detection also under-performs on textbook-style terse
   exercise lists** — found during the folder-alias fix's real
   validation; some Book of Proof records extracted to a single bare
   symbol (e.g. `$$\phi$$`) instead of the actual exercise text. Same
   family as #5 but a distinct failure mode (over-triggering on
   textbook content shape, not fragmenting problem-set prose) — both
   share the regex duplicated from `indexer/chunk_index.py`, so a fix
   needs regression coverage across both consumers.

## Future development ideas (idea #1 shipped as `problem_corpus`; #2-6 not implemented — revisit once a Gemini path exists)

Raised by the user while reviewing these results. Recorded here as a
real-evidence-informed roadmap, not decided or built:

1. **DONE (`problem_corpus/`, 2026-09-06).** ~~Extract a structured
   example-problem corpus from the textbooks and problem sets already
   in the corpus.~~ Textbooks and past exams already contain plenty of
   problems the student's own materials treat as valid, and some (e.g.
   textbook odd-numbered exercises with answers in the back) have
   solutions that are already verified by the textbook itself, not just
   self-reported by an LLM. Extracting these into a structured format
   (topic tag, problem formulation, solution(s), course(s)) gives this
   subsystem a real, growing bank of known-good examples to draw on,
   rather than only the same passage-level chunks retrieval happens to
   surface. Shipped without a "verified" tier, though — see the spec's
   own real-corpus finding that no such tier exists yet
   (`docs/superpowers/specs/2026-09-06-problem-corpus-extraction-design.md`).
   Ideas #2-6 below all depend on this corpus and remain unstarted.
2. **Two uses for that structured corpus**: (a) richer, curated few-shot
   examples in the generation prompt (more reliable "style anchors" than
   whatever raw chunk retrieval turns up), or (b) served directly to the
   student when a good match already exists in the corpus — no
   generation call needed at all.
3. **Backfilling missing solutions.** For textbook problems that don't
   have a solution in the corpus yet, generate just the solution (not a
   whole new problem) via a Gemini call — a narrower, likely easier and
   more reliable task than generating a full problem+solution pair from
   scratch, since the problem itself is already fixed and doesn't need
   inventing.
4. **Grow the corpus with usage.** Save Gemini-generated problems (and
   backfilled solutions) into this same structured store, explicitly
   tagged as LLM-generated rather than original course content — so the
   available example pool grows over time instead of staying fixed at
   whatever's already in the student's own materials.
5. **A tiered pipeline**, once a Gemini path exists: **Tier 1** —
   check the existing (and growing) structured problem corpus for
   something that already matches the student's request; local, free,
   no LLM call at all if a good match exists. **Tier 2** — Gemini
   generation for anything genuinely new; likely the default tier for a
   request with no good existing match.
6. **A middle ground between the two tiers**: retrieve a few *similar*
   existing problems for the specific request (not just topically
   similar, but close to what was actually asked), and pass those to
   Gemini as concrete prompt-examples to adapt with the specific changes
   the student's request calls for — closer to templated modification
   of a known-good problem than free-form generation from a style-pool
   of loosely-related examples.

None of this is built yet. It's recorded here so the reasoning behind
it (why a structured, growing, provenance-tagged corpus matters, and
why it pairs naturally with a Gemini-backed generation tier) survives
until it's actually picked up.
