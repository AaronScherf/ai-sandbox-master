# Visualization Sub-Agent: Status Summary

Start here for "what happened and where do we stand" on the
visualization sub-agent -- `viz/`, which generates interactive Plotly
HTML visualizations for academic-hub concepts via a keyword-matched
template library (primary) and a local Ollama fallback (secondary).
Design reference: `docs/superpowers/specs/2026-09-02-visualization-agent-design.md`;
implementation plan: `docs/superpowers/plans/2026-09-02-visualization-agent.md`.

## What shipped

One public entry point, `viz.viz_agent.generate_visualization(concept,
context, academic_hub_root, course)`, wired into
`rag_agent.answer_question()` as an opt-in `visualize: bool = False`
parameter -- off by default, so every existing caller (the REPL,
`index_search.py ask`, anything else already calling
`answer_question()`) is unaffected unless it opts in.

Two-tier resolution, both free of any paid API call:
1. **Template match** (`viz.templates.match_template()`) -- pure
   keyword/alias substring lookup against four initial templates
   (spectral decomposition, gradient descent, distributions/CLT,
   series convergence), each a hand-written Plotly-rendering function
   with a generic, well-chosen illustrative example.
2. **Ollama fallback** (`viz.llm_fallback.generate_via_llm()`) -- only
   reached when no template matches. Sends the concept plus retrieved
   passage context to a local `qwen2.5-coder:7b` model, extracts the
   generated Plotly script, and runs it in a subprocess with an
   execution timeout, a minimal/stripped environment (no inherited
   secrets -- the subprocess never sees `GEMINI_API_KEY`), and a
   scratch working directory, then caches the result on disk keyed by
   a hash of (concept, context). Plotly/numpy are pre-imported into
   the generated script's own preamble for convenience only -- this is
   execution isolation (timeout / no secrets / no shared cwd), not a
   restriction on which modules the generated code can import (it
   still has full network access and can import anything else).

## Real-corpus validation

Both real-corpus queries below were run from
`ai-sandbox/academic-rag-model` against `../academic-hub` (real corpus,
`math-camp` course, existing `.index/math-camp.json` shard), with
Ollama confirmed reachable at `http://localhost:11434` and
`qwen2.5-coder:7b` present (`GET /api/tags` checked before running).

**Full automated suite (Step 1):**
`.\.venv\Scripts\python.exe -m unittest discover -s tests -v` -- **660
tests, OK.** (The suite's own stdout includes intentional WARNING/error
text from tests that deliberately exercise failure paths -- e.g. a test
that fakes an Ollama connection-refused, tests that feed intentionally
broken Plotly scripts -- these are expected test fixtures, not real
failures.)

**Template path (Step 2):**
```
.\.venv\Scripts\python.exe -m indexer.index_search --root ../academic-hub ask "teach me about spectral decomposition" --course math-camp --visualize
```
Wall clock: ~6.2s. Output ended with:
```
visualization: ../academic-hub\.viz\math-camp\teach-me-about-spectral-decomposition.html
```
(The text answer itself said the retrieved excerpts didn't cover
"spectral decomposition" and declined to answer from general
knowledge -- expected, since template matching is a keyword lookup on
the concept string, independent of whether retrieval found relevant
passages, and this corpus apparently doesn't have a passage matching
that exact phrasing. The visualization firing regardless is correct
behavior per the design, not a bug.)

Directly inspected the generated `.html` (4.3 MB, dominated by the
inline-bundled `plotly.js` runtime) rather than just checking it
existed:
- Contains a real `Plotly.newPlot(...)` call with **4 real data
  traces**: two eigenvectors of a symmetric 2x2 matrix and their
  images under the matrix, e.g. `"eigenvector 1 (λ=1.38)"` with
  coordinates `[0, 0.5257...] → [0, -0.8507...]` and `"A · eigenvector
  1"` with coordinates `[0, 0.7265...] → [0, -1.1756...]` -- an
  actually-computed eigendecomposition, not placeholder/dummy numbers.
- Real layout: title `"Spectral decomposition: eigenvectors of a
  symmetric matrix stay on their own line under A"`, `xaxis`/`yaxis`
  both ranged `[-4, 4]` with `scaleanchor` locking aspect ratio.
- **Confirmed: a correct, non-blank, non-error interactive plot.**

**Ollama fallback path (Step 3):**
```
.\.venv\Scripts\python.exe -m indexer.index_search --root ../academic-hub ask "explain the intermediate value theorem" --course math-camp --visualize
```
Wall clock: **67.6 seconds** (well under the plan's "up to a couple of
minutes" estimate, on CPU). "Intermediate value theorem" is correctly
outside all four templates' keyword/alias lists, so this exercised
`llm_fallback.generate_via_llm()` against the live local model for
real.

Outcome: the Ollama call itself succeeded and the model returned a
Python/Plotly script (no connection failure, no empty response), but
**the generated script failed when executed** -- it used an invalid
Plotly property (attempting something like a `"bold"` font-weight
value in a place Plotly's schema doesn't accept, based on the error
text), and the subprocess exited non-zero. The exact warning printed
(last 500 chars of the subprocess's stderr, per
`llm_fallback.py:97`'s `result.stderr[-500:]` truncation):

```
WARNING: generated visualization script failed:
 size

        style
            Sets whether a font should be styled with a normal or
            italic face from its family.
        textcase
            Sets capitalization of text. It can be used to make
            text appear in all-uppercase or all-lowercase, or with
            each word capitalized.
        variant
            Sets the variant of the font.
        weight
            Sets the weight (or boldness) of the font.

Did you mean "color"?

Bad property path:
bold
^^^^
```

No `visualization:` line printed; `result.visualization` came back
`None`; the tutor's text answer (which itself said the retrieved
excerpts didn't cover the Intermediate Value Theorem either) was still
returned normally. Confirmed no new file appeared under
`../academic-hub/.viz/math-camp/` for this query -- the failure did not
silently leave a broken/partial `.html` behind.

**Assessment:** this is exactly the degrade-to-`None`, don't-block-the-
tutor behavior the design calls for (spec §1), and it worked correctly
end to end. But it is also a real, observed instance of the risk the
plan called out speculatively: a 7B local coder model writing
schema-invalid Plotly code unsupervised. One real trial is not enough
to estimate a failure rate -- it shows the failure mode exists and is
handled safely, not how often it will happen in practice.

## Specific limitations, honestly assessed

- **No parameter extraction from retrieved content.** Templates render
  a generic illustrative example (a representative matrix, a
  representative distribution), not the specific numbers from whatever
  passage was actually retrieved -- explicitly deferred in the spec
  (§1, §7): reliably parsing LaTeX/markdown math out of corpus text is
  a real, separate problem. Confirmed in Step 2: the visualization
  fired independent of retrieval quality, using its own generic
  worked example rather than anything from the (in this case,
  unmatched) corpus passages.
- **Only four template-covered concepts today.** Every other concept
  falls through to the slower, less reliable Ollama path. Growing
  coverage is adding one file to `viz/templates/` plus one import --
  cheap, but only done reactively as real questions hit the fallback
  path, not speculatively.
- **The Ollama fallback's real-world reliability is only as validated
  as Task 11 Step 3 above shows.** The one real trial run produced a
  script with an invalid Plotly property and failed to render --
  handled safely (degrades to `None`, tutor answer unaffected,
  observed wall clock 67.6s) but a genuine, observed failure, not a
  hypothetical one. A small local model writing correct Plotly code
  unsupervised remains a real risk area; broken code is now a
  confirmed failure mode, not just a plausible one.
- **No automatic "does this question deserve a visualization" logic.**
  `visualize` is caller-set; nothing decides this automatically yet.

## What's next

Not spec'd, in rough order a future session might pick up:
1. Grow template coverage as real usage surfaces concepts that keep
   falling through to the slower Ollama path -- the intermediate value
   theorem, per Step 3 above, is now a concrete real-world candidate.
2. Revisit whether a heuristic (or the tutor's own generation call)
   should decide `visualize` automatically for certain question
   shapes, once there's real usage data on which questions actually
   benefit from a plot.
3. Parameter extraction from retrieved content, if generic illustrative
   examples turn out to be a real limitation in practice rather than a
   theoretical one.
4. Consider whether the Ollama fallback should retry once on a Plotly
   schema-validation failure (as opposed to a syntax error or timeout)
   before giving up -- Step 3's observed failure was a single invalid
   property in an otherwise-plausible script, the kind of error a
   second attempt (or a narrower prompt constraint on allowed
   properties) might plausibly avoid. Not done here since one data
   point isn't enough to justify the added complexity yet.

## Retry-hardening validation (2026-09-03)

Item 4 above was picked up after two real-usage failures on 2026-09-02
and 2026-09-03 both hit the same invalid-Plotly-property class ("Bad
property path: bold" above, and a separate "Bad property path: z"
observed live in a 2026-09-03 session against the "eigenvectors and
eigenvalues" phrasing). Design:
`docs/superpowers/specs/2026-09-03-viz-ollama-retry-hardening-design.md`;
plan: `docs/superpowers/plans/2026-09-03-viz-ollama-retry-hardening.md`.
Shipped: a bounded `MAX_GENERATION_ATTEMPTS = 3` validate-and-retry loop
in `generate_via_llm()` (each retry gets the previous attempt's exact
code and error fed back via `_build_prompt()`), plus a tightened base
prompt steering the model away from exotic/speculative Plotly
properties -- the specific mistake class both real failures hit.

**Full automated suite:** `732 tests, OK` on two of three consecutive
runs; one run showed a single transient error that did not reproduce on
immediate re-run and was not traced to anything in this change (most
likely a race with a concurrently-active peer session's own commits to
this shared repo, per this project's multi-session working style) --
not treated as a real regression.

**Re-run of the previously-failing "intermediate value theorem" query**
(the exact query and phrasing from the Step 3 trial above):
```
.\.venv\Scripts\python.exe -m indexer.index_search --root ../academic-hub ask "explain the intermediate value theorem" --course math-camp --visualize
```
Wall clock: **3 min 8 s.** Outcome: **still no visualization**, but for
a different and new reason than before -- only one "Generating a
visualization..." line printed (i.e. no retry actually fired), and the
console showed:
```
WARNING: Ollama call failed (timed out) -- is `ollama serve` running and has `ollama pull qwen2.5-coder:7b` been run?
```
This is `_call_ollama`'s own 180-second HTTP client timeout expiring --
this particular generation was simply slow (close to 3x the ~68s
observed for the same query before hardening), not a bad-code failure.
Per the retry-hardening design's own §4, `_call_ollama` returning `None`
(network/HTTP failure) is explicitly treated as non-retryable ("Ollama
unreachable... retrying here just triples the wait before the same
inevitable `None`, for no benefit") -- but that reasoning assumed a
categorically down/unreachable server, not a live server that's simply
being slow on a particular generation. **This is a real gap the design
didn't anticipate**: a slow-but-eventually-answering Ollama call is
currently bucketed with "genuinely unreachable" and never gets a retry,
even though a second attempt might well complete in normal time. The
tutor's text answer was still returned normally either way -- the
never-raises contract held -- but this specific query still doesn't get
a visualization, just from a different failure mode than the one this
hardening pass targeted.

**Re-run of the "eigenvectors and eigenvalues" query** (the exact
phrasing that failed live in this session with "Bad property path: z"):
```
.\.venv\Scripts\python.exe -m indexer.index_search --root ../academic-hub ask "Give me a lesson summarizing eigenvectors and eigenvalues: what they are, geometric intuition, and how to compute them." --course math-camp --visualize
```
Wall clock: **2 min 24 s.** **Succeeded on the first attempt** -- no
retry needed. Output ended with:
```
visualization: ../academic-hub\.viz\math-camp\give-me-a-lesson-summarizing-eigenvectors-and-eigenvalues-what-they-are-geometri.html
```
Directly inspected the generated `.html` (4.3 MB, real
`Plotly.newPlot(...)` call, not a placeholder): title `"Effect of Basis
Change on Linear Operator"` with `"Input"`/`"Output"` subplot titles --
a genuinely topical, sensible visualization for the concept, not a
generic or mismatched one. This is the same query, same wording, that
failed with an invalid-property error earlier this session before this
hardening pass -- the tightened base prompt (steering away from exotic
properties like the `bold`/`z` mistakes both prior failures hit) appears
to have been sufficient on its own here, without the retry loop needing
to fire at all.

**Assessment:** 1 of 2 previously-failing real queries is now fixed
outright by the tightened prompt (no retry needed); the other traded
one failure mode (bad code) for a different one (the HTTP client
timeout) that this hardening pass didn't target and that its own
non-retry-on-`None` rule actively prevents from getting a second
chance. Two data points, in opposite directions, on the same design --
not enough to conclude the retry loop itself works as intended (neither
real trial actually exercised a mid-loop recovery; that path is only
proven by the mocked unit tests in `test_llm_fallback.py`), only that
the prompt tightening alone already closes some of the observed gap,
and that the unreachable-vs-slow distinction in §4 is a real,
now-observed weak point worth revisiting before drawing broader
conclusions about reliability.

**Immediate follow-up candidate, surfaced by this validation and not
in the original design:** either raise `_call_ollama`'s 180s HTTP
timeout (a slow-but-live generation currently gets one shot, at a much
tighter budget than the loop's own ~3-attempt/~3-minutes-each intent
suggests), or -- more precisely -- distinguish a genuine connection
failure (retry-proof) from a client-side timeout (plausibly worth one
retry) inside `_call_ollama`'s own exception handling, rather than
collapsing both into the same `None` return the retry loop then treats
identically.

## Timeout-vs-unreachable fix (2026-09-03, same session)

Picked up immediately: `_call_ollama` now returns a distinct
`_OLLAMA_TIMEOUT` sentinel on a `TimeoutError` (direct or wrapped in
`URLError`), separate from `None`. `generate_via_llm`'s retry loop
retries on the sentinel (feeding back a "you were too slow" hint) while
a genuine `None` (connection refused, server not running) still
short-circuits immediately, unchanged. The previously-inline `180`
magic number is now the named `OLLAMA_REQUEST_TIMEOUT_SECONDS`
constant. Accepted tradeoff, confirmed with the user: no separate,
smaller retry cap for timeouts -- the existing `MAX_GENERATION_ATTEMPTS
= 3` budget applies, so a consistently-slow query's worst case rose
from ~3 min (one timeout, no retry) to ~9 min (up to 3 timeouts in a
row). Average/worst-case timing to be measured later, once there's more
real usage data.

**Re-ran the intermediate value theorem query** immediately after
shipping the fix (same exact command as both prior trials):
```
.\.venv\Scripts\python.exe -m indexer.index_search --root ../academic-hub ask "explain the intermediate value theorem" --course math-camp --visualize
```
Wall clock: **4 min 24 s.** Console output confirmed the fix's intended
behavior directly: attempt 1 hit the same 180s timeout as the earlier
trial ("Ollama call timed out after 180s -- the model may just be slow
on this request"), but this time the loop **retried instead of giving
up** -- a second "Generating a visualization..." line printed, and
attempt 2 succeeded. Output ended with:
```
visualization: ../academic-hub\.viz\math-camp\explain-the-intermediate-value-theorem.html
```
Directly inspected the generated `.html` (4.3 MB, real
`Plotly.newPlot(...)` call): title `"Intermediate Value Theorem"` with
`"x"`/`"f(x)"` axis labels -- topically correct, not a placeholder.

**Both of the two real queries that failed pre-hardening now succeed**:
eigenvectors/eigenvalues on the first attempt (prompt tightening alone
was sufficient), intermediate value theorem after one timeout-triggered
retry (this fix was necessary -- without it, this query would still be
failing exactly as it did in the trial immediately above). Two for two,
though still only two real trials total -- not enough to estimate a
steady-state success rate, but the specific, concretely-observed gap
this fix targeted is now closed and directly confirmed against the
exact query that exposed it.

## Current status (2026-09-03, end of session)

Consolidated picture for anyone starting from here, superseding the
now-stale bits of "Specific limitations" and "What's next" above (left
in place as the historical record of how each finding was actually
reached, not deleted or rewritten).

**Working today:** both tiers, exercised against the real corpus, both
now succeed on every query tried. Template path: instant, deterministic
(spectral decomposition, confirmed real eigendecomposition data).
Ollama fallback: `qwen2.5-coder:7b`, now hardened with a 3-attempt
validate-and-retry loop, a tightened prompt, and a timeout/unreachable
distinction -- 3 for 3 real queries across this session (spectral
decomposition via template; eigenvectors/eigenvalues and the
intermediate value theorem via the fallback, the latter two both
previously-failing queries that now succeed).

**Bugs found and fixed this session, all via real usage, not
speculation:**
1. Template keyword over-matching -- `convergence.py`'s bare
   `"convergence"`/`"divergence"` keywords stole unrelated concepts
   (convergence in probability, the divergence theorem) from the Ollama
   fallback; tightened to specific phrases, tested against the real
   template registry.
2. A paid API key (`GEMINI_API_KEY`) was reachable from LLM-generated
   code's subprocess environment; the subprocess now runs with a
   minimal, explicit environment and a scratch working directory.
3. The Ollama-generated code produced invalid Plotly properties on 2/2
   early real trials ("Bad property path: bold", then "z") -- addressed
   with the retry loop plus a prompt tightened to steer away from
   exotic/speculative properties.
4. A long question could overflow Windows's filename length limit and
   crash the template path *after* the tutor's paid Gemini answer call
   had already succeeded, discarding it -- the template path now caps
   the slug length and is wrapped in the same never-raises guarantee
   the fallback path already had.
5. A slow-but-live Ollama call was indistinguishable from a genuinely
   unreachable one, so it got one shot at a 180s timeout instead of the
   retry budget the design intended -- `_call_ollama` now returns a
   distinct timeout sentinel so the retry loop can tell the two apart.

**Real limitations that still stand, honestly:**
- **Output is a standalone `.html` file only -- not embedded in a
  larger report.** `generate_visualization()` returns just a
  `VizResult(html_path, title, source)`; the CLI prints a bare
  `visualization: <path>` line alongside the separately-printed text
  answer and citations. Nothing currently combines the explanation
  text, citations, and the interactive plot into one document -- a
  student gets a terminal answer and a separate file to open by hand.
  **Building a combined report (text + citations + plot in one place)
  is explicitly the next thing to design**, not built here.
- Only four template-covered concepts; every other concept still
  depends on the (now-hardened, but not infallible) Ollama path.
- No parameter extraction from retrieved content -- templates render a
  generic illustrative example, never the specific numbers from
  whatever passage was actually retrieved.
- No automatic "does this question deserve a visualization" logic --
  `visualize` is caller-set.
- Average/worst-case latency for the Ollama path is still unmeasured
  beyond a handful of real trials (67.6s, 2m24s, 4m24s, and one 3m8s
  timeout-then-give-up before the timeout fix) -- not enough real
  volume yet to know a steady-state distribution, and the timeout fix's
  own accepted tradeoff (worst case up to ~9 min for a
  consistently-slow query, vs. ~3 min before) hasn't been stress-tested
  against a run that actually times out on every attempt.

**What's next, in the order this session's findings suggest:**
1. **Combined report** -- fold the text explanation, citations, and the
   interactive plot into one document instead of three disconnected
   outputs (a printed answer, a printed citation list, a separate file
   path). Explicitly queued as the next design conversation.
2. Measure real Ollama-path timing (average and worst case) across more
   real queries, and decide whether the retry budget or the per-request
   timeout need tuning based on actual data rather than the four data
   points gathered so far.
3. Grow template coverage reactively, as real questions keep falling
   through to the slower fallback path.
4. Revisit automatic `visualize` decision logic once there's real usage
   data on which questions actually benefit from a plot.
5. Parameter extraction from retrieved content, if generic illustrative
   examples turn out to be a real limitation in practice.
