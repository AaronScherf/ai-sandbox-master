# Viz Ollama Fallback: Local Example Store (Few-Shot Accuracy)

Brainstormed and approved with the user 2026-09-03. Extends
`docs/superpowers/specs/2026-09-02-visualization-agent-design.md` §4 and
`docs/superpowers/specs/2026-09-03-viz-ollama-retry-hardening-design.md`
(`viz/llm_fallback.py`) — this is the "local example/template storage"
item both of those specs named and explicitly deferred. It covers only
the accuracy-improving half of that idea (few-shot prompting from past
successes); the speed-improving half (skip Ollama entirely on a close
match) is deferred again here — see §6.

## 1. Problem & goals

The Ollama fallback (`qwen2.5-coder:7b`, a small local coder model) has
already been observed producing invalid-Plotly-property code on first
real use, twice, before the retry-hardening pass fixed the immediate
cases. Every fallback call today starts from the same fixed base prompt
with zero examples of what this specific model has actually gotten
right before — it re-derives valid Plotly usage from scratch on every
single concept, with no memory across calls except the exact-hash
result cache (which only helps a byte-identical repeat of the same
`concept`+`context`, not a paraphrase or a related topic).

**Goal:** before every Ollama call, look up 0-2 of this model's own past
*successful* generations for a similar concept, and inject them into the
prompt as worked examples — "here is valid Plotly code you already got
right for something like this." This is a pure prompt-quality lever: it
does not skip the Ollama call, does not change the retry loop's
structure, and costs nothing beyond one small local embedding call per
generation.

**Explicit sequencing choice (user, 2026-09-03):** accuracy before
speed. Build the corpus of validated successes first; only once it's
large enough that a genuinely close match is likely does "skip Ollama
and reuse/adapt directly" become worth the added complexity (deferred
to a future pass — see §6).

**Non-goals for this pass**
- Skipping the Ollama call on a close match ("hybrid" direct reuse).
  Needs its own design once the corpus has real size; folding it in now
  would test two mechanisms (selection quality, reuse safety) in one
  change.
- Any promotion of an example into the curated `viz/templates/*.py`
  registry. See §3 for why the two stores stay structurally separate.
- Pruning, deduplication, or a size cap on the example store. It grows
  unbounded for now; a cleanup pass is a later problem once real usage
  shows whether it's actually needed.
- Sharing the example store across machines. It's local, git-ignored
  state under `.viz/`, same as the existing HTML cache.
- Using the RAG tutor's *generated answer text* as additional grounding
  context. Viz already receives the same retrieved-passage `context`
  the tutor's citations are grounded in (`rag_agent.py`'s `viz_context`,
  built from `passages`, not from the synthesized `answer`) — that stays
  unchanged. Widening it to include the generated answer is a separate,
  unscoped idea not raised as part of this pass.

## 2. Architecture

One new module, `viz/example_store.py`, sitting alongside
`viz/llm_fallback.py`. Its only job: persist validated generations and
retrieve the most relevant ones for a new concept.

```python
@dataclass
class ExampleRecord:
    concept: str
    context: str
    keywords: list[str]
    embedding: list[float]
    script: str
    created_at: str  # ISO 8601, UTC

def find_examples(concept: str, context: str) -> list[ExampleRecord]:
    """Returns up to MAX_EXAMPLES past successful generations relevant
    to (concept, context), or [] if the store is empty or nothing is
    close enough. Never raises -- any failure (Ollama embeddings
    unreachable, corrupt store file) is caught, logged as a WARNING,
    and treated as "no examples available", degrading to today's
    from-scratch prompt."""

def save(concept: str, context: str, script: str) -> None:
    """Appends a new validated record. Never raises -- a failure to
    save is logged as a WARNING and otherwise ignored; it must never
    turn a successful generation into a failed generate_via_llm() call."""
```

**Storage:** a single flat JSON file, `.viz/.examples/examples.json`
(sibling to the existing `.viz/.cache/`, under the same already
git-ignored `.viz/` root). A flat file matches the project's existing
precedent for small, per-machine JSON stores (the indexer's
`.index/chunks/*.json`) and is more than sufficient for the corpus size
this realistically reaches (tens to low hundreds of records, not
thousands) — no database needed.

**Two-tier naming, kept deliberately distinct:**

| | `viz/templates/*.py` | `viz/example_store.py` records |
|---|---|---|
| Trust level | **Verified** — hand-written, reviewed, committed to git | **Unverified** — auto-generated, the only bar is "it executed successfully" |
| Selected by | keyword substring match (`match_template`) | embedding similarity, keyword fallback (§4) |
| Used for | directly rendering the visualization | few-shot prompt context only — never rendered or returned directly |
| Lifecycle | manually authored, one file per concept | appended automatically on every Ollama fallback success |

This distinction is documented explicitly (module docstrings on both
`viz/templates/__init__.py` and `viz/example_store.py`) because a future
pass may want a promotion path — an example that's proven itself
(matched and reused repeatedly, or passed a manual review) getting
hand-adapted into a real `Template`. That promotion mechanism is not
built here; keeping the two stores structurally separate now is what
keeps that door open without conflating "ran once without crashing"
with "a maintainer vouched for this."

## 3. Embedding

Reusing the project's existing embedding infrastructure
(`indexer/index_card.py`'s `EMBEDDING_MODEL`, via Gemini) was
considered and rejected: it's a paid API call, conflicting with the viz
fallback tier's own existing principle of staying free of paid calls.
Embedding spaces are also not cross-compatible between models — a
Gemini-space vector and an Ollama-space vector can't be compared to
each other — so there is no advantage to matching Gemini's space here
even if cost weren't a concern. The example store is a brand-new,
self-contained index that this module both writes and queries, so it
only needs internal consistency, not compatibility with anything else.

**Decision:** embed locally via Ollama's `/api/embeddings` endpoint
using `nomic-embed-text` (~275MB, one-time `ollama pull
nomic-embed-text`), mirroring `_call_ollama`'s existing local-HTTP
pattern in `llm_fallback.py`:

```python
EMBEDDING_MODEL = "nomic-embed-text"
EMBEDDING_URL = "http://localhost:11434/api/embeddings"

def _embed(text: str) -> list[float] | None:
    """POSTs to Ollama's embeddings endpoint, same failure handling as
    _call_ollama: returns None on any network/HTTP failure (logged as
    a WARNING), never raises."""
```

**Embedding input:** `concept` and `context` are concatenated
(`f"{concept}\n{context}"`) before embedding, for both `save()` and
`find_examples()`. Concept text alone is ambiguous — two questions with
identical wording ("eigenvalues") can come from genuinely different
domains depending on which corpus passages were retrieved (linear
algebra vs. a stats/PCA aside) — and `context` is exactly the signal
that disambiguates that, already flowing into this call today as the
same `viz_context` the fallback prompt itself uses for grounding.

## 4. Matching: the selection cascade

```
find_examples(concept, context):
    if store is empty: return []
    query_embedding = _embed(f"{concept}\n{context}")
    if query_embedding is None:          # Ollama embeddings unreachable
        return []                        # degrade to from-scratch, no crash
    scored = [(cosine_similarity(query_embedding, r.embedding), r) for r in records]
    above_threshold = [r for score, r in scored if score >= EXAMPLE_SIMILARITY_THRESHOLD]
    if above_threshold:
        return top MAX_EXAMPLES of above_threshold, highest score first
    # nothing close enough semantically -- try keyword overlap
    query_words = _derive_keywords(f"{concept}\n{context}")
    overlapping = [r for r in records if query_words & set(r.keywords)]
    if overlapping:
        return top MAX_EXAMPLES of overlapping (most overlapping words first;
            ties broken by insertion order, oldest first)
    return []
```

```python
EXAMPLE_SIMILARITY_THRESHOLD = 0.85  # deliberately high -- a related-but-
    # distinct topic (e.g. "eigenvalues" vs. "singular values") getting
    # shown as a worked example is worse than showing none, per the
    # user's explicit call: avoid pulling in a similar-but-distinct
    # subject
MAX_EXAMPLES = 2
```

**Keyword fallback, kept auto-derived (no LLM call, no hand-curated
list):** `_derive_keywords(text)` lowercases, splits on non-alphanumeric
characters, and drops short tokens (length < 3) and a small built-in
stopword list (`the`, `and`, `for`, `with`, etc. — same low-tech spirit
as the hand-written templates' keyword lists, just generated instead of
authored). `save()` computes and stores this alongside the embedding, so
matching at lookup time is a plain set-intersection — cheap, and
independently testable without any network call.

## 5. Prompt integration

`_build_prompt` in `llm_fallback.py` gains one new parameter:

```python
def _build_prompt(
    concept: str, context: str,
    previous_code: str | None = None, previous_error: str | None = None,
    examples: list[ExampleRecord] | None = None,
) -> str:
```

When `examples` is non-empty, a new block is inserted ahead of the
existing requirements list (present on every attempt of a given
`generate_via_llm()` call — first attempt and retries alike, since
examples are concept-level context, not attempt-level):

```
Here are examples of visualizations you generated successfully for
related concepts -- follow similar patterns (trace types, layout
options) where they fit this new concept:

Example 1 (concept: "spectral decomposition"):
```python
<script>
```
```

`generate_via_llm()`'s orchestration changes:

```python
def generate_via_llm(concept, context, output_path, cache_dir) -> VizResult | None:
    ...
    examples = example_store.find_examples(concept, context)  # once, before the attempt loop
    for _ in range(MAX_GENERATION_ATTEMPTS):
        prompt = _build_prompt(concept, context, previous_code, previous_error, examples)
        ...
        if success:
            example_store.save(concept, context, code)  # the final, working code
            succeeded = True
            break
        ...
```

`example_store` failures (either call) never propagate — both functions
are internally exception-safe per §2's contracts, so a broken example
store degrades `generate_via_llm()` to exactly today's behavior, never
blocks or fails a generation because of it.

An intermediate failed attempt within a multi-attempt call is never
saved as an example, matching the existing cache's own rule (only a
genuinely successful result is ever persisted).

## 6. Testing

New `tests/test_example_store.py`:
- `_embed`: mocked-network tests (same convention as `_call_ollama`'s
  existing tests) confirming a successful response returns the vector
  and any failure returns `None`.
- `cosine_similarity` / ranking: deterministic, no network — given a
  fixed set of records with known embeddings, confirm threshold
  filtering, `MAX_EXAMPLES` capping, and highest-score-first ordering.
- Keyword fallback: deterministic tests for `_derive_keywords` (short
  words and stopwords dropped) and for the overlap-based fallback firing
  only when nothing clears the similarity threshold.
- `save()` / `find_examples()` round-trip against a temp file, including
  first-write-creates-file and appending to an existing file.
- Corrupt/missing store file: `find_examples` returns `[]`, `save`
  still succeeds (rewrites a fresh valid file) — both logged as
  WARNINGs, neither raises.

`test_llm_fallback.py` gains:
- `_build_prompt`: a test confirming the examples block appears when
  `examples` is non-empty and is absent when `None`/`[]`.
- `generate_via_llm`: a test (with `example_store.find_examples` and
  `.save` mocked) confirming `find_examples` is called once per
  `generate_via_llm()` call (not once per attempt) and `save` is called
  exactly once, with the final successful code, after a multi-attempt
  run that failed once then succeeded.

No new end-to-end/real-Ollama or real-embedding test — same as the
retry-hardening pass, real validation happens as a manual run recorded
honestly in a status-doc update, not asserted in CI.

## 7. What's next (explicitly deferred, not built here)

- **Direct reuse / "hybrid" tier.** Once the example store has enough
  real accumulated volume that close matches are actually common, skip
  the Ollama call entirely on a high-confidence match — copy or lightly
  adapt the stored script instead. This is the speed-improving half of
  the original idea, deliberately sequenced after this accuracy-only
  pass.
- **Example → template promotion.** A path for a repeatedly-successful
  or manually-reviewed example to graduate into `viz/templates/*.py`
  as a verified, directly-matched template. Needs its own design for
  what "proven itself" means and who/what does the reviewing.
  Table in §2 is the record kept for making that decision easier later.
- **Store maintenance.** No pruning, deduplication, or staleness
  handling yet. If real usage shows the store growing large enough to
  slow down `find_examples`'s linear scan, or accumulating enough
  near-duplicate concepts to matter, that's a follow-up.
