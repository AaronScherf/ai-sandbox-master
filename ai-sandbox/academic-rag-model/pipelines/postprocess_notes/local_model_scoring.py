"""
Local small-model scoring for postprocess_notes.py's detection layer --
see docs/superpowers/specs/2026-08-26-notes-postprocessing-design.md.
Loaded via HuggingFace `transformers` (PyTorch CPU backend) -- Ollama
was the original candidate but was dropped: verified against its own
official docs that neither its native nor OpenAI-compatible API
supports scoring caller-provided text (no echo/prompt-logprobs mode),
only probabilities for tokens the model generates itself.

Touches transformers/torch -- not unit-tested locally, matching this
project's established split for anything model- or network-dependent
(transcribe_page_via_gemini, render_page_to_image_bytes, etc. are the
same way). Validated instead against real documents; see Task 8's
validation script in the implementation plan for the concrete real-bug
check this was built against. The one exception is `_local_zscores`,
the pure-math core of score_causal_zscore's z-score calculation -- it
has no model dependency and is unit-tested directly (see
tests/pipelines/postprocess_notes/test_local_model_scoring.py and
TODO-0060's calibration fix in its own docstring).
"""
from __future__ import annotations

import functools
import statistics


@functools.lru_cache(maxsize=4)
def _load_masked_model(model_name: str):
    """
    Cached model+tokenizer load, keyed by model_name. Confirmed necessary
    against a real corpus run: without caching, score_masked_candidates
    reloaded the model from scratch on every single call (once per page),
    which dominated real end-to-end runtime far more than the actual
    scoring work itself. lru_cache is safe here since a single
    postprocess_notes.py run only ever uses a small, fixed set of model
    names (maxsize=4 comfortably covers masked + causal, plus headroom).
    """
    from transformers import AutoModelForMaskedLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForMaskedLM.from_pretrained(model_name)
    model.eval()
    return tokenizer, model


@functools.lru_cache(maxsize=4)
def _load_causal_model(model_name: str):
    """Cached counterpart to _load_masked_model for score_causal_zscore's causal LM."""
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(model_name)
    model.eval()
    return tokenizer, model


def score_masked_candidates(
    model_name: str, text: str, candidate_spans: list[tuple[int, int]], window_chars: int = 200,
) -> list[dict]:
    """
    For each (start, end) character span in `text`, masks exactly that
    span and reads the model's own probability for the actual text that
    was there -- the signal confirmed strongest in the design spike
    (DistilBERT correctly scored a real bug at probability 0.0018, ~40x
    below its top candidate, using both left and right context). Skips
    any span whose text isn't exactly one model token (multi-token
    masked scoring needs a different approach than single-token
    probability lookup; out of scope here). Returns one dict per scored
    span: {"start", "end", "text", "probability", "rank"}.

    Scores against a local window (window_chars on each side of the
    span), not the full `text` -- confirmed necessary against a real
    page from Analysis_Exercises.pdf that tokenized to 554 tokens,
    past DistilBERT's fixed 512-token position-embedding limit. A short
    page (window comfortably covers the whole thing) behaves exactly as
    before; this only changes behavior for pages long enough to have
    hit the crash. Windowing also keeps every call fast regardless of
    page length, consistent with the design spike's own finding that
    nearby context carries the signal, not the whole page.
    """
    import torch

    tokenizer, model = _load_masked_model(model_name)

    results = []
    for start, end in candidate_spans:
        target_text = text[start:end]
        target_ids = tokenizer(target_text, add_special_tokens=False)["input_ids"]
        if len(target_ids) != 1:
            continue
        window_start = max(0, start - window_chars)
        window_end = min(len(text), end + window_chars)
        local_start = start - window_start
        local_end = end - window_start
        windowed_text = text[window_start:window_end]
        masked_text = windowed_text[:local_start] + tokenizer.mask_token + windowed_text[local_end:]
        inputs = tokenizer(masked_text, return_tensors="pt", truncation=True, max_length=512)
        mask_positions = (inputs["input_ids"][0] == tokenizer.mask_token_id).nonzero()
        if len(mask_positions) == 0:
            continue
        mask_idx = mask_positions[0].item()
        with torch.no_grad():
            logits = model(**inputs).logits[0, mask_idx]
        probs = torch.softmax(logits, dim=-1)
        target_id = target_ids[0]
        probability = probs[target_id].item()
        rank = (probs > probs[target_id]).sum().item() + 1
        results.append({
            "start": start, "end": end, "text": target_text,
            "probability": probability, "rank": rank,
        })
    return results


def _local_zscores(
    surprisal: list[float], window: int = 10, min_stdev_fraction: float = 0.5,
) -> list[float]:
    """
    Pure-math core of the per-token local z-score -- split out from
    score_causal_zscore so it's unit-testable without transformers/torch
    (the rest of this module is deliberately not unit-tested locally; see
    the module docstring. This helper has no model dependency at all, so
    it's the one exception).

    Calibration fix for TODO-0060 / the precision problem documented in
    docs/status/postprocess_notes/2026-08-27-notes-postprocessing-status.md
    ("Remaining open items"): raising `_CAUSAL_ZSCORE_THRESHOLD` alone
    (3.0 -> 5.0, and as far as 6.0 in further analysis) never found a
    clean cutoff against real terse, LaTeX-heavy problem-set prose
    (Practice Sheet.md) -- correct words like "Let" (z=11.60) and
    "subject" (z=5.91-6.27) still cleared even the highest bar tried.

    Root cause: a token's local window (+/- `window` tokens) in short or
    symbolic-math-heavy text is often itself very low-variance -- it's
    surrounded by highly predictable digits, operators, and single-letter
    variables GPT-2 scores confidently. An ordinary English word only
    *moderately* more surprising than those neighbors still produces a
    huge z-score, not because the word is anomalous in absolute terms,
    but because the neighborhood's own stdev is artificially tiny. No
    fixed z-score threshold can separate that from a genuine anomaly,
    which also produces a high z-score, but for the right reason (an
    actually large gap between its surprisal and its neighbors', not a
    deflated denominator).

    Fix: floor each token's local stdev at `min_stdev_fraction` of the
    *whole page's* own stdev, so a deflated local-window variance can no
    longer manufacture an oversized z-score by itself -- a token now also
    has to be surprising relative to the page's overall register, not
    merely relative to an unusually uniform immediate neighborhood. A
    real anomaly (surprisal far outside the page's own range) clears that
    bar easily either way; a rare-but-correct word sitting in a locally
    uniform pocket of otherwise-ordinary text typically no longer does.
    This is a mitigation tuned against the documented examples above, not
    re-validated against a live model run this session -- see this
    change's commit message for the honest caveat.
    """
    n = len(surprisal)
    if n == 0:
        return []
    page_stdev = statistics.pstdev(surprisal) if n >= 2 else 0.0
    stdev_floor = min_stdev_fraction * page_stdev
    z_scores = []
    for i in range(n):
        lo, hi = max(0, i - window), min(n, i + window + 1)
        neighborhood = surprisal[lo:i] + surprisal[i + 1:hi]
        if len(neighborhood) < 4:
            z_scores.append(0.0)
            continue
        mean = statistics.mean(neighborhood)
        local_stdev = statistics.pstdev(neighborhood)
        stdev = max(local_stdev, stdev_floor) or 1e-6
        z_scores.append((surprisal[i] - mean) / stdev)
    return z_scores


def score_causal_zscore(model_name: str, text: str, window: int = 10) -> list[dict]:
    """
    Per-token causal surprisal, converted to a local z-score against
    each token's own neighborhood rather than ranked globally across the
    whole page -- confirmed in the design spike to modestly outperform
    raw global ranking (moved the real bug from rank 6 to rank 3 of 523
    tokens on the same real test page). Kept as a secondary signal
    alongside score_masked_candidates: this needs only one forward pass
    for an entire page, versus one pass per candidate span for masked
    scoring, so it's a cheaper first coarse pass. Returns one dict per
    token: {"text", "start", "end", "surprisal", "z_score"}.

    The z-score itself is computed by `_local_zscores` (see its
    docstring for the TODO-0060 calibration fix: a page-stdev floor on
    the local neighborhood's stdev, to curb false positives on short or
    symbolic-math-heavy notes).

    Truncated to GPT-2's own 1024-token position-embedding limit --
    confirmed necessary against a real corpus run (a dense LaTeX-typeset
    page in ta_notes/LN_Linear Algebra.pdf crashed with "IndexError:
    index out of range in self" without this). Unlike
    score_masked_candidates's local-window fix, this scores the whole
    page to find *where* anomalies are in the first place, so there's no
    single candidate span to window around yet -- truncation means a
    page longer than 1024 tokens only gets scored on its first ~1024,
    a known, accepted gap rather than a crash.
    """
    import torch

    tokenizer, model = _load_causal_model(model_name)

    enc = tokenizer(text, return_tensors="pt", return_offsets_mapping=True, truncation=True, max_length=1024)
    input_ids = enc["input_ids"]
    offsets = enc["offset_mapping"][0].tolist()[1:]
    with torch.no_grad():
        logits = model(input_ids).logits[:, :-1, :]
    targets = input_ids[:, 1:]
    log_probs = torch.log_softmax(logits, dim=-1)
    token_logprob = log_probs.gather(2, targets.unsqueeze(-1)).squeeze(-1)[0]
    surprisal = (-token_logprob).tolist()
    token_strs = tokenizer.convert_ids_to_tokens(input_ids[0])[1:]

    z_scores = _local_zscores(surprisal, window=window)

    results = []
    for i in range(len(surprisal)):
        start, end = offsets[i]
        results.append({
            "text": token_strs[i], "start": start, "end": end,
            "surprisal": surprisal[i], "z_score": z_scores[i],
        })
    return results
