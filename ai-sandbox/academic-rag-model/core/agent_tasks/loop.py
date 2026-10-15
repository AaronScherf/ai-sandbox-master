"""Collect / submit / api_run over a stage module, independent of any one subproject's store.

A stage module is duck-typed: `validate_result(entry, result, target) -> list[str]` (empty list = valid) and
`apply_result(target, entry, result, provenance) -> str | None` (a returned string means "skipped, with this reason").
Both are looked up on the module at call time, so a stage can be patched or swapped after import."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from .tasks import ResultError, Task, extract_result, result_from_response
from .work import Run, create_run

PRICE_IN = 0.75    # $/M input tokens: the repo's gemini-3.8-flash ceiling price
PRICE_OUT = 3.75   # $/M output tokens
OUT_TOKENS = 900   # assumed reply size per task
FREE_LIMIT = 1.0   # above this an explicit approve_cost is required
API_SUFFIX = "\n\nReply with only the YAML mapping for the Result block (inside a ```yaml fence), no commentary.\n"


class BudgetError(Exception):
    pass


@dataclass
class SubmitReport:
    applied: list[str] = field(default_factory=list)
    bounced: dict[str, list[str]] = field(default_factory=dict)
    skipped: dict[str, str] = field(default_factory=dict)
    untouched: list[str] = field(default_factory=list)


def provenance(driver: str, agent: str | None, run: str) -> dict:
    return {"driver": driver, "agent": agent, "run": run}


def collect_run(stage: str, tasks: list[Task], work_root: str | Path, output_repo: str | Path, *,
                run_id: str | None = None, repo_label: str = "output repo") -> Run | None:
    """Write the cards for already-built tasks. Returns None when there is nothing to do."""
    if not tasks:
        return None
    return create_run(work_root, output_repo, stage, tasks, run_id=run_id, repo_label=repo_label)


def _process(run: Run, target: Any, mod: Any, entry: dict, result: dict, agent_name: str | None, driver: str,
             report: SubmitReport, provenance_fn: Callable, target_label: str) -> None:
    task_id = entry["id"]
    try:
        problems = mod.validate_result(entry, result, target)
        if problems:
            run.bounce(task_id, problems)
            report.bounced[task_id] = problems
            return
        reason = mod.apply_result(target, entry, result, provenance_fn(driver, agent_name, run.run_id))
    except Exception as exc:  # one bad card must never stop the others
        reasons = [f"could not process this card: {exc}. If this was a file or disk problem, part of the card may "
                   f"already be in the {target_label}; check the data files before submitting again"]
        run.bounce(task_id, reasons)
        report.bounced[task_id] = reasons
        return
    if reason:
        run.set_status(task_id, "skipped", [reason])
        report.skipped[task_id] = reason
    else:
        run.set_status(task_id, "applied")
        report.applied.append(task_id)


def submit_run(run: Run, mod: Any, target: Any, agent_name: str | None = None, *,
               provenance_fn: Callable = provenance, target_label: str = "output") -> SubmitReport:
    """Validate and apply every pending or bounced card the agent has filled in. Applied cards are never revisited."""
    report = SubmitReport()
    for entry in run.tasks:
        if entry["status"] not in ("pending", "bounced"):
            continue
        task_id = entry["id"]
        try:
            result = extract_result(run.card_path(task_id).read_text(encoding="utf-8"))
        except ResultError as exc:
            run.bounce(task_id, [str(exc)])
            report.bounced[task_id] = [str(exc)]
            continue
        if result is None:
            report.untouched.append(task_id)
            continue
        _process(run, target, mod, entry, result, agent_name, "agent", report, provenance_fn, target_label)
    return report


def estimate_cost(texts: list[str], price_in: float = PRICE_IN, price_out: float = PRICE_OUT,
                  out_tokens: int = OUT_TOKENS) -> float:
    """Rough dollars for sending these prompts: about 4 characters per input token, a fixed reply size."""
    tokens_in = sum(len(t) for t in texts) / 4
    return (tokens_in * price_in + len(texts) * out_tokens * price_out) / 1_000_000


def api_run(run: Run, mod: Any, target: Any, complete: Callable[[str], str], approve_cost: float | None,
            agent_name: str = "gemini-api", *, price_in: float = PRICE_IN, price_out: float = PRICE_OUT,
            out_tokens: int = OUT_TOKENS, provenance_fn: Callable = provenance,
            target_label: str = "output") -> SubmitReport:
    """Send each pending card to `complete(prompt) -> reply`, behind the cost gate."""
    pending = [e for e in run.tasks if e["status"] in ("pending", "bounced")]
    prompts = [run.card_path(e["id"]).read_text(encoding="utf-8") + API_SUFFIX for e in pending]
    estimate = estimate_cost(prompts, price_in, price_out, out_tokens)
    if approve_cost is None and estimate > FREE_LIMIT:
        raise BudgetError(f"estimated cost ${estimate:.2f} is over ${FREE_LIMIT:.2f}; nothing was sent. "
                          f"Re-run with --approve-cost <usd> to confirm")
    if approve_cost is not None and estimate > approve_cost:
        raise BudgetError(f"estimated cost ${estimate:.4f} exceeds the approved ${approve_cost:.4f}; nothing was sent")
    report = SubmitReport()
    for entry, prompt in zip(pending, prompts):
        task_id = entry["id"]
        try:
            reply = complete(prompt)
        except Exception as exc:
            run.bounce(task_id, [f"api call failed: {exc}"])
            report.bounced[task_id] = [f"api call failed: {exc}"]
            continue
        if not isinstance(reply, str):
            run.bounce(task_id, ["the api reply was not text"])
            report.bounced[task_id] = ["the api reply was not text"]
            continue
        try:
            result = result_from_response(reply)
        except Exception as exc:  # a bad reply is one bounced card, never a crashed run
            run.bounce(task_id, [str(exc)])
            report.bounced[task_id] = [str(exc)]
            continue
        if result is None:
            run.bounce(task_id, ["the reply contained no result"])
            report.bounced[task_id] = ["the reply contained no result"]
            continue
        _process(run, target, mod, entry, result, agent_name, "api", report, provenance_fn, target_label)
    return report
