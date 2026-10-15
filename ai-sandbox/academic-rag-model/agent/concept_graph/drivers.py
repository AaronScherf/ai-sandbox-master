"""The two transports for the drafting stages.

agent: `collect` writes task cards, an IDE agent fills them in, `submit` validates and applies.
api:   the same cards are sent to Gemini behind a cost gate; replies go through the same validate/apply path.

The generic loop lives in core.agent_tasks.loop; this module binds it to the graph store and stage registry."""
from __future__ import annotations

from core.agent_tasks import loop as _loop
from core.agent_tasks.loop import (  # noqa: F401  (re-exported: callers and tests import these from here)
    API_SUFFIX, FREE_LIMIT, OUT_TOKENS, PRICE_IN, PRICE_OUT, BudgetError, SubmitReport, estimate_cost,
)

from . import stages
from .stages.common import provenance
from .store import GraphStore
from .work import Run

_LABEL = "graph"


def collect(stage: str, store: GraphStore, retriever, work_root, *, run_id: str | None = None, **opts) -> Run | None:
    """Build the stage's tasks and write their cards. Returns None when there is nothing to do."""
    tasks = stages.get(stage).make_tasks(store, retriever, **opts)
    return _loop.collect_run(stage, tasks, work_root, store.root, run_id=run_id, repo_label="graph repo")


def submit(run: Run, store: GraphStore, agent_name: str | None = None) -> SubmitReport:
    """Validate and apply every pending or bounced card the agent has filled in. Applied cards are never revisited."""
    return _loop.submit_run(run, stages.get(run.stage), store, agent_name, provenance_fn=provenance, target_label=_LABEL)


def api_run(stage: str, run: Run, store: GraphStore, complete, approve_cost: float | None,
            agent_name: str = "gemini-api", *, price_in: float = PRICE_IN, price_out: float = PRICE_OUT,
            out_tokens: int = OUT_TOKENS) -> SubmitReport:
    """Send each pending card to `complete(prompt) -> reply`, behind the cost gate."""
    return _loop.api_run(run, stages.get(stage), store, complete, approve_cost, agent_name,
                         price_in=price_in, price_out=price_out, out_tokens=out_tokens,
                         provenance_fn=provenance, target_label=_LABEL)


def gemini_complete(model: str = "gemini-3.8-flash"):
    """A `complete(prompt)` that calls Gemini with the paid key. Not unit-tested (network, paid)."""
    from core.env.gemini_utils import call_with_retries

    from .retrieval import make_gemini_client

    client = make_gemini_client()

    def complete(prompt: str) -> str:
        return call_with_retries(
            lambda: client.models.generate_content(model=model, contents=prompt, config={"temperature": 0}).text or "")

    return complete
