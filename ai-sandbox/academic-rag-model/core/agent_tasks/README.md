# core/agent_tasks

Task cards an agent fills in, run manifests, and the collect / submit / api loop. It exists so that LLM steps run on the **subscription route** (Gemini in Antigravity reads a card and writes a YAML answer) with **code**, not Claude, validating and applying the result. The paid API is an explicit opt-in behind a cost gate.

## Files

| File | Responsibility |
|---|---|
| `tasks.py` | `Task`, `Passage`, `ResultError`, `render_card`, `extract_result`, `parse_result_text`, `result_from_response` |
| `work.py` | `Run`, `STATUSES`, `task_entry`, `render_worklist`, `create_run`, `load_run` |
| `loop.py` | `collect_run`, `submit_run`, `api_run`, `estimate_cost`, `provenance`, `SubmitReport`, `BudgetError` and the cost constants |

## Stage-module contract

A stage is any object (usually a module) with these two functions, looked up **at call time** so they can be patched or swapped after import:

```python
def validate_result(entry: dict, result: dict, target) -> list[str]:
    """Problems with the agent's answer; an empty list means valid. Problems bounce the card."""

def apply_result(target, entry: dict, result: dict, provenance: dict) -> str | None:
    """Write the answer into `target`. Return a reason string to mark the card skipped, else None."""
```

Building tasks is up to the consumer: it creates `Task` objects and calls `collect_run(stage, tasks, work_root, output_repo)`. A toy end-to-end example lives in `tests/core/test_agent_tasks_loop.py`.

## Compatibility rules (frozen)

- Card format (`## Result`, `## Bounced`), manifest keys (including `graph_repo`), status names and error-message text must not change: runs already on disk must still load and submit.
- `create_run` refuses a work directory inside the output repo (cards hold source text) and a missing attachment, before creating anything.
- A change here needs the whole `tests/agent/concept_graph` suite green, with no edits to its tests.

## Attachments

`Task.attachments` is an optional list of existing file paths (for example page images). When present the card gets an `## Attachments` section just before `## Result`, and the manifest entry gets an `attachments` key. Cards and manifests for tasks without attachments are byte-identical to before.

## Consumers

- `agent/concept_graph` (through the shims in `tasks.py`, `work.py`, `drivers.py`).
- The literature extraction stage is the next one: see `docs/superpowers/specs/literature_taxonomy/2026-10-15-literature-taxonomy-pipeline-design.md`.

`pipelines/transcribe_notes/agent_work.py` is a separate, image-page card system and is intentionally not part of this layer.
