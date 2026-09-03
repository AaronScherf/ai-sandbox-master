# Viz Ollama Fallback: Validate-and-Retry Hardening

Brainstormed and approved with the user 2026-09-03. Extends
`docs/superpowers/specs/2026-09-02-visualization-agent-design.md` §4
(`viz/llm_fallback.py`) — the visualization sub-agent shipped and
merged 2026-09-02; this spec covers one follow-up hardening pass to its
Ollama fallback, not a new subsystem.

## 1. Problem & goals

Real usage on 2026-09-03 confirmed the reliability gap the original
spec's own real-corpus validation (Task 11) had already flagged as an
open risk: two real questions ("explain the intermediate value
theorem", then "eigenvectors and eigenvalues" phrased outside the
`spectral_decomposition` template's keywords) both fell through to the
Ollama fallback, and both times `qwen2.5-coder:7b` produced Plotly code
using an invalid property, failing at render time. The fallback
degraded safely both times (no crash, `None` returned, a warning
printed) — the *contract* worked as designed — but a fallback that
fails on 2 of its first 2 real invocations isn't actually delivering
the "any topic in the corpus" coverage the template tier can't provide
on its own.

**Scope, set with the user 2026-09-03:** math-camp breadth — the range
of topics actually taught in math-camp (calculus, linear algebra,
probability, real analysis, etc.), not the entire academic-hub corpus.
The 4 existing templates stay as-is; this pass hardens the fallback
tier itself rather than growing template coverage, since template
coverage can never scale to "any topic" the way a working generation
path can.

**Goals**
- When the Ollama fallback's generated code fails (bad Plotly property,
  any other execution error, or a timeout), give the model a bounded
  number of chances to fix its own mistake using the exact error it
  produced, before giving up.
- Reduce the odds of even needing a retry via a tighter base prompt.
- Preserve every existing contract unchanged: `generate_via_llm()`
  still never raises past its caller, still returns `None` (with a
  warning) on exhausted attempts, still caches only a genuinely
  successful result, still costs no paid API call.

**Non-goals (for this pass — noted as real future directions, not
built here)**
- Storing successful generations as reusable few-shot examples for
  future prompts, or as a "hybrid" tier that reuses a past generation
  when a new concept is similar enough to one already solved. Raised
  by the user 2026-09-03 as a real next step once the fresh-generation
  path itself is solid — deliberately out of scope here so this change
  stays focused and testable on its own.
- Expanding the template library. The user explicitly chose hardening
  the fallback over growing templates 2026-09-03: templates alone
  can't cover "any topic," so the fallback is the tier that has to
  actually work.
- Any change to the template-matching tier (§3 of the original spec)
  or to the tutor integration (§6) — this pass touches
  `viz/llm_fallback.py` only.

## 2. Architecture: the retry loop

`generate_via_llm()` currently does one shot: build a prompt, call
Ollama, extract code, run it, cache-and-return or fail. This becomes a
bounded loop, `MAX_GENERATION_ATTEMPTS = 3` (one initial attempt plus
up to 2 corrective retries — generous enough for the model to actually
converge on a fix, still bounded to a few minutes worst-case for this
personal, non-time-critical tool, per the user's 2026-09-03 latency
call: ~3 minutes worst case at ~60-70s/attempt is acceptable). A plain
module-level constant, not env-overridable — matching
`EXECUTION_TIMEOUT_SECONDS`'s own precedent in this file (only
`OLLAMA_MODEL` is env-overridable today, because swapping models is a
real per-machine need; a retry budget isn't).

```
attempt 1..MAX_GENERATION_ATTEMPTS:
    prompt = _build_prompt(concept, context, previous_code, previous_error)
    response = _call_ollama(prompt)
    if response is None:                     # Ollama unreachable
        return None                          # not worth retrying -- see §4
    code = _extract_code(response)
    if code is None:
        previous_code, previous_error = None, "no ```python code block in the response"
        continue
    if _run_generated_code(code, cached_path):
        cache and return VizResult(source="llm_fallback")
    previous_code, previous_error = code, <captured failure text>
return None   # all attempts exhausted
```

Only the final, actually-successful attempt is ever written to
`cache_dir` — a failed intermediate attempt is never cached, matching
the existing cache's own meaning ("a cached result is a known-good
result you can copy straight to the output path without re-running
anything").

## 3. Prompt construction

`_call_ollama` currently builds its own prompt internally from
`(concept, context)`. This splits into two functions:

```python
def _build_prompt(
    concept: str, context: str,
    previous_code: str | None = None, previous_error: str | None = None,
) -> str:
    """First attempt: the existing concept+context prompt template.
    Retry attempts (previous_code/previous_error both set): the same
    base prompt, plus the previous attempt's code and the exact error
    it produced, asking for a corrected script. previous_error is
    subprocess.run's captured stderr (or "no ```python code block" / a
    timeout note) -- the same text _run_generated_code already prints
    as a WARNING today, just fed back to the model instead of only to
    the console."""

def _call_ollama(prompt: str) -> str | None:
    """Unchanged contract -- sends an already-composed prompt string,
    returns the response text or None on any network/HTTP failure.
    No longer builds the prompt itself; _build_prompt does that, so
    this stays a thin, independently-testable "send this, get that"
    function regardless of which attempt it's serving."""
```

`_call_ollama`'s signature changes from `(concept, context)` to
`(prompt)` — its only caller is `generate_via_llm`'s loop, so this is
an internal refactor, not a public interface change.

**Base-prompt tightening**, applied to attempt 1 regardless of whether
a retry ever happens (cheap, reduces the expected number of attempts
needed): steer the model toward the trace types and properties actually
exercised by this project's own hand-written templates (`Scatter`,
`Bar`, `Contour`, basic `layout.title`/axis labels) and explicitly warn
against speculative annotation/styling properties — the exact class of
mistake both real failures hit ("Bad property path: bold", "Bad
property path: z"). This is additive to the existing prompt's
requirements (assign to `fig`, don't call `write_html`/`show`, only
`plotly`+`numpy` imports, one fenced code block), not a rewrite of them.

## 4. What triggers a retry vs. an immediate `None`

Not every failure is worth retrying:

- **Bad/no code block extracted, execution error (non-zero exit),
  timeout** — all retry, since each is plausibly something the model
  can fix given the specific error (or, for a timeout, a hint to avoid
  expensive computation).
- **Ollama unreachable** (`_call_ollama` returns `None` — connection
  refused, server not running) — **does not retry.** If Ollama itself
  isn't reachable on attempt 1, it won't become reachable on attempts 2
  or 3 within the same call; retrying here just triples the wait before
  the same inevitable `None`, for no benefit. This matches the existing
  contract (`_call_ollama` returning `None` short-circuits today) and
  is the one place the loop exits early rather than exhausting its
  budget.

A timeout on one attempt does not reduce the timeout budget available
to the next attempt — each attempt gets the same `EXECUTION_TIMEOUT_SECONDS`
independently.

## 5. Testing

`test_llm_fallback.py` gains:
- `_build_prompt`: unit tests confirming the first-attempt prompt has
  no retry content, and a retry-attempt prompt includes the previous
  code and the previous error text verbatim.
- `_call_ollama`: existing tests updated for the new `(prompt)` signature
  — same mocked-network-call pattern as today, no behavior change to
  verify beyond the signature.
- `generate_via_llm`: a new test simulating one failed attempt (bad
  code, mocked) followed by one successful attempt, asserting the final
  result is returned, `_call_ollama` was called twice, and the second
  call's prompt contains the first attempt's error; a persistent-failure
  test confirming exactly `MAX_GENERATION_ATTEMPTS` calls happen before
  returning `None`; a test confirming an unreachable-Ollama response
  short-circuits after exactly 1 call, not 3; a test confirming only
  the final successful attempt's output is cached (a failed
  intermediate attempt must not leave a cache-dir entry behind).

No new end-to-end/real-Ollama test is added — real validation happens
the same way the original spec called for (§7 there): a real manual
run, recorded honestly in a status-doc update, not asserted in CI.

## 6. What's next (explicitly deferred, not built here)

- **Local example/template storage.** Cache successful generations
  (beyond the existing content-hash cache, which only helps an exact
  repeat of the same concept+context) as reusable few-shot examples for
  future prompts, or as a "hybrid" tier: if a new concept is similar
  enough to a previously-solved one, reuse or adapt that generation
  instead of a fresh Ollama call. Raised by the user 2026-09-03 as the
  natural next step once fresh generation itself is reliable — needs
  its own design (similarity matching, storage format, staleness/
  invalidation) rather than being folded into this pass.
- Whether the base-prompt tightening (§3) alone, without any retry ever
  firing, turns out to already fix most real failures — worth checking
  once real usage accumulates, since it's the cheaper of the two levers
  this pass adds.
