# agent/study_guide/revise/cost.py
"""Price a revise run from token usage, estimate it before it starts, and stop it at a cap."""
from __future__ import annotations

# USD per million tokens: (input, cached input, output). Thinking tokens bill as output.
PRICES = {"gemini-3.8-flash": (0.75, 0.075, 3.75)}
DEFAULT_MODEL = "gemini-3.8-flash"

# Per-call token guesses used when no earlier run of this guide recorded real usage:
# (prompt, output + thinking). The audit reads a whole section and plan passages and thinks hardest.
DEFAULT_CALL_TOKENS = {"relevance": (8_000, 3_000), "dedup": (6_000, 3_000), "correctness": (20_000, 14_000),
                       "organization": (12_000, 3_000), "inline": (10_000, 3_000)}


class CostCapReached(RuntimeError):
    """Raised between units of work once spend has passed the cap; finished units stay in the checkpoint."""


def cost_usd(usage: dict, model: str) -> float:
    inp, cached_rate, out = PRICES.get(model, PRICES[DEFAULT_MODEL])
    cached = usage.get("cached_tokens", 0)
    fresh = usage.get("prompt_tokens", 0) - cached
    return (fresh * inp + cached * cached_rate + (usage.get("output_tokens", 0) + usage.get("thinking_tokens", 0)) * out) / 1e6


def estimate_cost(calls: dict[str, int], model: str, prior: dict[str, dict] | None) -> float:
    """Estimated spend for `calls` model calls per stage. A stage that an earlier run recorded is priced at that run's
    average cost per call; the rest use rough defaults, so treat the figure as an order of magnitude."""
    total = 0.0
    for stage, n in calls.items():
        seen = (prior or {}).get(stage)
        if seen and seen.get("calls"):
            total += n * cost_usd(seen, model) / seen["calls"]
        else:
            prompt, out = DEFAULT_CALL_TOKENS.get(stage, DEFAULT_CALL_TOKENS["relevance"])
            total += n * cost_usd({"prompt_tokens": prompt, "output_tokens": out}, model)
    return total
