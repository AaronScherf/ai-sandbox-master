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
