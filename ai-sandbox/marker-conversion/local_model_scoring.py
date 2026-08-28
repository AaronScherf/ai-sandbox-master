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
check this was built against.
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
    """
    import torch

    tokenizer, model = _load_causal_model(model_name)

    enc = tokenizer(text, return_tensors="pt", return_offsets_mapping=True)
    input_ids = enc["input_ids"]
    offsets = enc["offset_mapping"][0].tolist()[1:]
    with torch.no_grad():
        logits = model(input_ids).logits[:, :-1, :]
    targets = input_ids[:, 1:]
    log_probs = torch.log_softmax(logits, dim=-1)
    token_logprob = log_probs.gather(2, targets.unsqueeze(-1)).squeeze(-1)[0]
    surprisal = (-token_logprob).tolist()
    token_strs = tokenizer.convert_ids_to_tokens(input_ids[0])[1:]

    results = []
    n = len(surprisal)
    for i in range(n):
        lo, hi = max(0, i - window), min(n, i + window + 1)
        neighborhood = surprisal[lo:i] + surprisal[i + 1:hi]
        if len(neighborhood) < 4:
            z = 0.0
        else:
            mean = statistics.mean(neighborhood)
            stdev = statistics.pstdev(neighborhood) or 1e-6
            z = (surprisal[i] - mean) / stdev
        start, end = offsets[i]
        results.append({
            "text": token_strs[i], "start": start, "end": end,
            "surprisal": surprisal[i], "z_score": z,
        })
    return results
