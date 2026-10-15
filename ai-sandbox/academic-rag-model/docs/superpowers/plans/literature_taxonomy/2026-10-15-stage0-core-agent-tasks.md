# Stage 0: shared task-card layer (`core/agent_tasks/`) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Lift concept_graph's generic task-card, run-manifest and collect/submit/api_run code into `core/agent_tasks/`, make `agent/concept_graph` a consumer through compatibility shims, and add optional task attachments, with no behavior change for concept_graph.

**Architecture:** Three new core modules (`tasks.py`, `work.py`, `loop.py`) hold the generic code. `agent/concept_graph/{tasks,work,drivers}.py` become thin shims or graph-bound adapters that import from core and keep every existing name, signature, message and on-disk byte. A characterization test written *before* the move pins card text, manifest keys and bounce text; the existing 331 concept_graph tests are the regression net and are not edited.

**Tech Stack:** Python 3.13, PyYAML (already used by `tasks.py`), pytest.

**Spec:** `docs/superpowers/specs/literature_taxonomy/2026-10-15-literature-taxonomy-pipeline-design.md` (section 5, "Shared task-card layer"). Executors read both.

## Global Constraints

- Run from `ai-sandbox/academic-rag-model/` **inside the worktree**. Interpreter: `PY="C:/Users/theaa/ai-sandbox-master/ai-sandbox/academic-rag-model/.venv/Scripts/python.exe"` (worktrees have no `.venv`). Run tests as `"$PY" -m pytest <path> -q`.
- Baseline before any change: `tests/agent/concept_graph` = **331 passed** (~55 s).
- **No existing test file is edited.** New tests go in new files. Test directories have no `__init__.py`, so new test basenames must be unique across `tests/`.
- Card format (`## Result`, `## Bounced`), manifest keys (including `graph_repo`), status names (`pending`, `filled`, `applied`, `bounced`, `skipped`) and error-message text (e.g. `inside the graph repo`) stay byte-compatible.
- `core/` changes need tests for the callers too (academic-rag-model CLAUDE.md); the caller suite is `tests/agent/concept_graph`.
- Stage explicit paths only; never `git add -A` / `git add .`. Local commits on the task branch are pre-authorized; landing on `main` is the owner's. Commit trailer: `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.
- Do not touch `pipelines/transcribe_notes/agent_work.py` (out of scope per spec).
- No paid API calls anywhere in this plan; `gemini_complete` stays in concept_graph and is not exercised.

## Review Focus

Failure modes the spec implies that the obvious tests would miss, most likely first. Each is pinned in the task named in brackets.

1. **An in-flight run created by the old code must load and submit with the new code**: a hand-written old-format manifest (no `attachments` key) plus an old-format card. [Task 3, Task 4]
2. **Stage functions patched or swapped after import must still be honoured**: the loop must call `mod.validate_result` / `mod.apply_result` at call time, never bind them early (existing tests monkeypatch them). [Task 4]
3. **Non-ASCII text and Windows line endings**: cards are written with `newline="\n"`; accented and Greek characters in passages must round-trip byte-for-byte. [Task 2]
4. **Attachments that do not exist**: card creation must fail early, naming the file, and must not leave a half-created run directory. [Task 3]
5. **Cards without attachments must be byte-identical to today's**, so the new section may only appear when attachments are present. [Task 1, Task 2]

## File Structure

| File | Responsibility |
| --- | --- |
| `core/agent_tasks/__init__.py` | Package marker; re-exports the public names |
| `core/agent_tasks/tasks.py` | `Task`, `Passage`, `ResultError`, `render_card`, `extract_result`, `parse_result_text`, `result_from_response` |
| `core/agent_tasks/work.py` | `Run`, `STATUSES`, `task_entry`, `render_worklist`, `create_run`, `load_run` |
| `core/agent_tasks/loop.py` | `SubmitReport`, `BudgetError`, `estimate_cost`, `provenance`, `collect_run`, `submit_run`, `api_run` and cost constants |
| `core/agent_tasks/README.md` | What the layer is, the stage-module contract, how to add a consumer |
| `agent/concept_graph/tasks.py` | Shim: re-exports from core |
| `agent/concept_graph/work.py` | Shim: re-exports from core; `create_run` wrapper that passes `repo_label="graph repo"` |
| `agent/concept_graph/drivers.py` | Graph-bound adapter: resolves stage modules, passes `store`, keeps constants and `gemini_complete` |
| `agent/concept_graph/sources.py` | `Passage` import from core instead of local definition |
| `agent/concept_graph/stages/common.py` | `provenance` imported from core |
| `tests/agent/concept_graph/test_cg_compat_golden.py` | Characterization (new, written first) |
| `tests/agent/concept_graph/test_cg_shims.py` | Identity and wrapper checks (new) |
| `tests/core/test_agent_tasks_tasks.py`, `..._work.py`, `..._loop.py` | Core unit tests (new) |

---

### Task 1: Baseline and characterization tests (before any move)

**Files:**
- Create: `tests/agent/concept_graph/test_cg_compat_golden.py`

**Interfaces:**
- Consumes: `agent.concept_graph.tasks.{Task, render_card}`, `agent.concept_graph.sources.Passage`, `agent.concept_graph.work.{create_run, load_run}`.
- Produces: a golden contract that must pass **unchanged** after Tasks 2-5.

- [ ] **Step 1: Confirm the baseline**

Run: `"$PY" -m pytest tests/agent/concept_graph -q`
Expected: `331 passed`. If not, stop and report; do not continue on a red baseline.

- [ ] **Step 2: Write the characterization test**

```python
"""Pins the on-disk contract of concept_graph's task cards and run manifests.

Written before the code moved to core/agent_tasks; it must keep passing, unedited, afterwards."""
import json

from agent.concept_graph.sources import Passage
from agent.concept_graph.tasks import Task, render_card
from agent.concept_graph.work import create_run, load_run


def _task():
    return Task(
        id="fill-001", stage="fill", subject={"concept": "Elasticity"},
        instructions="Draft the entry.\n", context="Concept: Elasticity\n",
        passages=[Passage(id="P1", source="notes", ref="Lecture 3", text="Elasticity measures...\n", path="a/b.md")],
    )


def test_card_text_is_byte_stable():
    expected = "\n".join([
        "# Task fill-001   (stage: fill)",
        "",
        "## Instructions",
        "Draft the entry.",
        "",
        "## Subject",
        "Concept: Elasticity",
        "",
        "## Offered passages",
        "### P1  [source: notes | ref: Lecture 3]",
        "Elasticity measures...",
        "",
        "## Result",
        "Write only the YAML mapping, inside the fence below.",
        "```yaml",
        "```",
        "",
    ])
    assert render_card(_task()) == expected


def test_manifest_keys_and_worklist_are_stable(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    run = create_run(tmp_path / "work", repo, "fill", [_task()], run_id="r1")
    data = json.loads((run.root / "manifest.json").read_text(encoding="utf-8"))
    assert list(data) == ["run_id", "stage", "created", "graph_repo", "tasks"]
    assert data["graph_repo"] == str(repo)
    entry = data["tasks"][0]
    assert list(entry) == ["id", "subject", "status", "attempts", "reasons", "offered", "passages"]
    assert list(entry["passages"][0]) == ["id", "source", "ref", "text", "path"]
    assert (run.root / "worklist.md").read_text(encoding="utf-8").startswith("# Worklist: run r1 (stage: fill)\n")
    assert (run.root / "cards" / "fill-001.md").read_text(encoding="utf-8") == render_card(_task())


def test_bounce_text_and_counters_are_stable(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    run = create_run(tmp_path / "work", repo, "fill", [_task()], run_id="r1")
    run.bounce("fill-001", ["reason one"])
    card = run.card_path("fill-001").read_text(encoding="utf-8")
    assert card.endswith(
        "\n## Bounced\nFix only what is listed, in the same ```yaml block above, then ask for a re-submit.\n- reason one\n"
    )
    reloaded = load_run(tmp_path / "work", "r1")
    assert reloaded.task("fill-001")["status"] == "bounced"
    assert reloaded.task("fill-001")["attempts"] == 1


def test_privacy_guard_message_names_the_graph_repo(tmp_path):
    import pytest
    repo = tmp_path / "repo"
    repo.mkdir()
    with pytest.raises(ValueError, match="inside the graph repo"):
        create_run(repo / "work", repo, "fill", [_task()])
```

- [ ] **Step 3: Run it against the unmoved code**

Run: `"$PY" -m pytest tests/agent/concept_graph/test_cg_compat_golden.py -q`
Expected: `4 passed`. If a golden assertion fails, the test mis-describes today's behavior: fix the *test* to match the existing code, never the code.

- [ ] **Step 4: Commit**

```bash
git add tests/agent/concept_graph/test_cg_compat_golden.py
git commit -m "test(concept_graph): characterization of card, manifest and bounce contract before core extraction

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 2: `core/agent_tasks/tasks.py` with attachments, and the `tasks.py` / `sources.py` shims

**Files:**
- Create: `core/agent_tasks/__init__.py`, `core/agent_tasks/tasks.py`, `tests/core/test_agent_tasks_tasks.py`
- Modify: `agent/concept_graph/tasks.py` (replace body with shim), `agent/concept_graph/sources.py:17-27` (replace local `Passage` with import)

**Interfaces:**
- Produces (core): `Passage(id, source, ref, text, path="")` frozen dataclass with `.offered -> (source, ref)`; `Task(id, stage, subject, instructions, context, passages=[], attachments=[])`; `ResultError`; `render_card(task) -> str`; `extract_result(card_text) -> dict | None`; `parse_result_text(text)`; `result_from_response(response)`.
- Card rule: an `## Attachments` section is emitted **only** when `task.attachments` is non-empty, placed immediately before `## Result`.

- [ ] **Step 1: Write the failing core tests** (`tests/core/test_agent_tasks_tasks.py`)

```python
import pytest

from core.agent_tasks.tasks import (
    Passage, ResultError, Task, extract_result, parse_result_text, render_card, result_from_response,
)


def _task(**kw):
    base = dict(id="t-1", stage="demo", subject={"k": "v"}, instructions="Do it.", context="Ctx.",
                passages=[Passage(id="P1", source="paper", ref="p. 3", text="Body.")])
    base.update(kw)
    return Task(**base)


def test_card_without_attachments_has_no_attachments_section():
    assert "## Attachments" not in render_card(_task())


def test_attachments_section_sits_just_before_result():
    card = render_card(_task(attachments=["pages/p4.png", "pages/p5.png"]))
    assert card.index("## Offered passages") < card.index("## Attachments") < card.index("## Result")
    assert "- `pages/p4.png`" in card and "- `pages/p5.png`" in card


def test_non_ascii_text_round_trips_in_the_card():
    card = render_card(_task(context="Élasticité β = 0.5 — “quoted”"))
    assert "Élasticité β = 0.5 — “quoted”" in card


def test_extract_result_reads_the_fenced_mapping():
    card = render_card(_task()).replace("```yaml\n```", "```yaml\nvalue: 1\nnote: \"a: b\"\n```")
    assert extract_result(card) == {"value": 1, "note": "a: b"}


def test_empty_block_is_none_and_missing_heading_raises():
    assert extract_result(render_card(_task())) is None
    with pytest.raises(ResultError, match="no '## Result' heading"):
        extract_result("nothing here")


def test_dates_come_back_as_text():
    assert parse_result_text("when: 2026-09-10\n") == {"when": "2026-09-10"}


def test_result_from_response_prefers_the_fence():
    assert result_from_response("sure\n```yaml\na: 1\n```\nthanks") == {"a": 1}
    assert result_from_response("a: 2") == {"a": 2}
```

- [ ] **Step 2: Run to confirm failure**

Run: `"$PY" -m pytest tests/core/test_agent_tasks_tasks.py -q`
Expected: collection error `ModuleNotFoundError: No module named 'core.agent_tasks'`.

- [ ] **Step 3: Create the core module**

`core/agent_tasks/__init__.py`:

```python
"""Shared task-card layer: cards an agent fills in, run manifests, and the collect/submit/api loop."""
```

`core/agent_tasks/tasks.py`: copy `agent/concept_graph/tasks.py` verbatim, then make exactly these changes. Remove `from .sources import Passage` and define `Passage` here:

```python
@dataclass(frozen=True)
class Passage:
    id: str
    source: str
    ref: str
    text: str
    path: str = ""

    @property
    def offered(self) -> tuple[str, str]:
        return (self.source, self.ref)
```

Add the field to `Task` (last, defaulted):

```python
@dataclass
class Task:
    id: str
    stage: str
    subject: dict
    instructions: str
    context: str
    passages: list[Passage] = field(default_factory=list)
    attachments: list[str] = field(default_factory=list)
```

In `render_card`, replace the final `parts += [...]` line with:

```python
    if task.attachments:
        parts += ["## Attachments",
                  "Open these files (page images of the source) if a passage or table is unclear:"]
        parts += [f"- `{a}`" for a in task.attachments]
        parts.append("")
    parts += ["## Result", "Write only the YAML mapping, inside the fence below.", "```yaml", "```", ""]
```

Everything else (`ResultError`, `_FENCE`, `extract_result`, `_plain`, `parse_result_text`, `result_from_response`) is unchanged.

- [ ] **Step 4: Run core tests**

Run: `"$PY" -m pytest tests/core/test_agent_tasks_tasks.py -q`
Expected: `7 passed`.

- [ ] **Step 5: Turn concept_graph's `tasks.py` and `sources.py` into consumers**

Replace the whole of `agent/concept_graph/tasks.py` with:

```python
"""Compatibility shim: task cards now live in core.agent_tasks.tasks. Import paths here keep working."""
from __future__ import annotations

from core.agent_tasks.tasks import (  # noqa: F401
    Passage,
    ResultError,
    Task,
    _FENCE,
    _plain,
    extract_result,
    parse_result_text,
    render_card,
    result_from_response,
)
```

In `agent/concept_graph/sources.py`, delete the local `Passage` class (lines 17-27) and add to the imports at the top: `from core.agent_tasks.tasks import Passage  # noqa: F401  (re-exported; same object as core's)`. Remove `from dataclasses import dataclass` only if nothing else in the file uses it (check with `grep -n dataclass agent/concept_graph/sources.py`).

- [ ] **Step 6: Run the concept_graph suite and the golden file, unedited**

Run: `"$PY" -m pytest tests/agent/concept_graph -q`
Expected: `335 passed` (331 + 4 golden).

- [ ] **Step 7: Commit**

```bash
git add core/agent_tasks/__init__.py core/agent_tasks/tasks.py tests/core/test_agent_tasks_tasks.py agent/concept_graph/tasks.py agent/concept_graph/sources.py
git commit -m "refactor(core): extract task cards to core.agent_tasks.tasks, add optional attachments

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 3: `core/agent_tasks/work.py` and the `work.py` shim

**Files:**
- Create: `core/agent_tasks/work.py`, `tests/core/test_agent_tasks_work.py`
- Modify: `agent/concept_graph/work.py` (replace body with shim)

**Interfaces:**
- Consumes: Task 2's `Task`, `render_card`.
- Produces: `STATUSES`; `Run(root: Path, data: dict)` with `.run_id`, `.stage`, `.tasks`, `.task(id)`, `.card_path(id)`, `.set_status(id, status, reasons=None)`, `.bounce(id, reasons)`; `task_entry(task) -> dict` (adds an `"attachments"` key **only** when non-empty); `render_worklist(run) -> str`; `create_run(work_root, output_repo, stage, tasks, run_id=None, *, repo_label="output repo") -> Run`; `load_run(work_root, run_id) -> Run`. The manifest key stays `"graph_repo"` (compatibility).

- [ ] **Step 1: Write the failing core tests** (`tests/core/test_agent_tasks_work.py`)

```python
import json

import pytest

from core.agent_tasks.tasks import Task, render_card
from core.agent_tasks.work import create_run, load_run


def _task(task_id="t-1", **kw):
    return Task(id=task_id, stage="demo", subject={}, instructions="Do.", context="Ctx.", **kw)


def test_guard_message_uses_the_label(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    with pytest.raises(ValueError, match="inside the output repo"):
        create_run(repo / "work", repo, "demo", [_task()])
    with pytest.raises(ValueError, match="inside the graph repo"):
        create_run(repo / "work", repo, "demo", [_task()], repo_label="graph repo")


def test_manifest_keeps_the_graph_repo_key_and_omits_empty_attachments(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    run = create_run(tmp_path / "work", repo, "demo", [_task()], run_id="r1")
    data = json.loads((run.root / "manifest.json").read_text(encoding="utf-8"))
    assert data["graph_repo"] == str(repo)
    assert "attachments" not in data["tasks"][0]


def test_attachments_are_recorded_when_present(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    img = tmp_path / "p4.png"
    img.write_bytes(b"png")
    run = create_run(tmp_path / "work", repo, "demo", [_task(attachments=[str(img)])], run_id="r1")
    assert run.task("t-1")["attachments"] == [str(img)]
    assert str(img) in run.card_path("t-1").read_text(encoding="utf-8")


def test_a_missing_attachment_fails_early_and_leaves_no_run_directory(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    work = tmp_path / "work"
    with pytest.raises(ValueError, match="attachment .*missing.png"):
        create_run(work, repo, "demo", [_task(attachments=[str(tmp_path / "missing.png")])], run_id="r1")
    assert not (work / "r1").exists()


def test_an_old_format_in_flight_run_still_loads_and_bounces(tmp_path):
    root = tmp_path / "work" / "old-1"
    (root / "cards").mkdir(parents=True)
    (root / "cards" / "t-1.md").write_text(render_card(_task()), encoding="utf-8", newline="\n")
    manifest = {"run_id": "old-1", "stage": "demo", "created": "2026-10-01T09:00:00", "graph_repo": "X:/repo",
                "tasks": [{"id": "t-1", "subject": {}, "status": "pending", "attempts": 0, "reasons": [],
                           "offered": [], "passages": []}]}
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    run = load_run(tmp_path / "work", "old-1")
    run.bounce("t-1", ["needs a fix"])
    assert load_run(tmp_path / "work", "old-1").task("t-1")["status"] == "bounced"


def test_run_ids_may_not_carry_a_path(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    with pytest.raises(ValueError, match="invalid run id"):
        create_run(tmp_path / "work", repo, "demo", [_task()], run_id="../evil")
```

- [ ] **Step 2: Run to confirm failure**

Run: `"$PY" -m pytest tests/core/test_agent_tasks_work.py -q`
Expected: `ModuleNotFoundError: No module named 'core.agent_tasks.work'`.

- [ ] **Step 3: Create `core/agent_tasks/work.py`**

Copy `agent/concept_graph/work.py` (git: `git show HEAD:ai-sandbox/academic-rag-model/agent/concept_graph/work.py`) and change only:

1. Import: `from .tasks import Task, render_card` (unchanged text, now resolves to core).
2. `task_entry` becomes:
```python
def task_entry(task: Task) -> dict:
    """The manifest record for one task: everything validation needs, so the card itself is never trusted."""
    entry = {
        "id": task.id, "subject": task.subject, "status": "pending", "attempts": 0, "reasons": [],
        "offered": [list(p.offered) for p in task.passages],
        "passages": [{"id": p.id, "source": p.source, "ref": p.ref, "text": p.text, "path": p.path} for p in task.passages],
    }
    if task.attachments:  # absent when empty, so manifests for attachment-free tasks stay byte-identical
        entry["attachments"] = list(task.attachments)
    return entry
```
3. `create_run` becomes (the `_inside` helper and `_check_run_id` stay as copied):
```python
def create_run(work_root: str | Path, output_repo: str | Path, stage: str, tasks: list[Task],
               run_id: str | None = None, *, repo_label: str = "output repo") -> Run:
    work_root, output_repo = Path(work_root), Path(output_repo)
    if _inside(work_root, output_repo):
        raise ValueError(f"the work directory {work_root} is inside the {repo_label} {output_repo}; "
                         f"cards hold source text and must stay private")
    if run_id is not None:
        _check_run_id(run_id)
    for t in tasks:
        for a in t.attachments:
            if not Path(a).is_file():
                raise ValueError(f"task {t.id}: attachment {a!r} does not exist")
    if run_id is None:
        base = f"{stage}-{dt.datetime.now():%Y%m%d-%H%M%S}"
        run_id, n = base, 1
        while (work_root / run_id).exists():
            n += 1
            run_id = f"{base}-{n}"
    root = work_root / run_id
    if _inside(root, output_repo):
        raise ValueError(f"the run folder {root} is inside the {repo_label} {output_repo}; "
                         f"cards hold source text and must stay private")
    (root / "cards").mkdir(parents=True, exist_ok=False)
    data = {
        "run_id": run_id, "stage": stage, "created": dt.datetime.now().isoformat(timespec="seconds"),
        "graph_repo": str(output_repo),  # key name kept for compatibility with runs already on disk
        "tasks": [task_entry(t) for t in tasks],
    }
    run = Run(root, data)
    for t in tasks:
        run.card_path(t.id).write_text(render_card(t), encoding="utf-8", newline="\n")
    run._save()
    return run
```

- [ ] **Step 4: Run core work tests**

Run: `"$PY" -m pytest tests/core/test_agent_tasks_work.py -q`
Expected: `6 passed`.

- [ ] **Step 5: Replace `agent/concept_graph/work.py` with the shim**

```python
"""Compatibility shim: run manifests now live in core.agent_tasks.work. Import paths here keep working.

create_run keeps its graph-flavored signature and error text by passing repo_label."""
from __future__ import annotations

from pathlib import Path

from core.agent_tasks import work as _core_work
from core.agent_tasks.work import (  # noqa: F401
    STATUSES,
    Run,
    _check_run_id,
    _inside,
    load_run,
    render_worklist,
    task_entry,
)

from .tasks import Task


def create_run(work_root: str | Path, graph_repo: str | Path, stage: str, tasks: list[Task],
               run_id: str | None = None) -> Run:
    return _core_work.create_run(work_root, graph_repo, stage, tasks, run_id=run_id, repo_label="graph repo")
```

- [ ] **Step 6: Run the concept_graph suite**

Run: `"$PY" -m pytest tests/agent/concept_graph -q`
Expected: `335 passed`.

- [ ] **Step 7: Commit**

```bash
git add core/agent_tasks/work.py tests/core/test_agent_tasks_work.py agent/concept_graph/work.py
git commit -m "refactor(core): extract run manifests to core.agent_tasks.work with attachment checks

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 4: `core/agent_tasks/loop.py` and the `drivers.py` adapter

**Files:**
- Create: `core/agent_tasks/loop.py`, `tests/core/test_agent_tasks_loop.py`
- Modify: `agent/concept_graph/drivers.py` (delegate), `agent/concept_graph/stages/common.py:59-60` (import `provenance` from core)

**Interfaces:**
- Consumes: Task 2 `ResultError, Task, extract_result, result_from_response`; Task 3 `Run, create_run`.
- Produces (core.loop):
  - `PRICE_IN=0.75`, `PRICE_OUT=3.75`, `OUT_TOKENS=900`, `FREE_LIMIT=1.0`, `API_SUFFIX` (exact original string).
  - `class BudgetError(Exception)`; `@dataclass SubmitReport(applied: list[str], bounced: dict[str, list[str]], skipped: dict[str, str], untouched: list[str])`.
  - `provenance(driver, agent, run) -> {"driver", "agent", "run"}`.
  - `estimate_cost(texts, price_in=PRICE_IN, price_out=PRICE_OUT, out_tokens=OUT_TOKENS) -> float`.
  - `collect_run(stage, tasks, work_root, output_repo, *, run_id=None, repo_label="output repo") -> Run | None` (None when `tasks` is empty).
  - `submit_run(run, mod, target, agent_name=None, *, provenance_fn=provenance, target_label="output") -> SubmitReport`.
  - `api_run(run, mod, target, complete, approve_cost, agent_name="gemini-api", *, price_in=PRICE_IN, price_out=PRICE_OUT, out_tokens=OUT_TOKENS, provenance_fn=provenance, target_label="output") -> SubmitReport`.
- Stage-module contract (duck-typed): `validate_result(entry, result, target) -> list[str]` (empty list = valid) and `apply_result(target, entry, result, provenance_dict) -> str | None` (a returned string means "skipped, with this reason").

- [ ] **Step 1: Write the failing core tests** (`tests/core/test_agent_tasks_loop.py`)

```python
"""The loop with a toy stage and a plain-dict target: proves it has no concept_graph dependency."""
import types

import pytest

from core.agent_tasks import loop
from core.agent_tasks.tasks import Task
from core.agent_tasks.work import load_run


def _stage(applied):
    def validate_result(entry, result, target):
        return [] if "answer" in result else ["answer is required"]

    def apply_result(target, entry, result, prov):
        target[entry["id"]] = {"answer": result["answer"], "prov": prov}
        applied.append(entry["id"])
        return None

    return types.SimpleNamespace(validate_result=validate_result, apply_result=apply_result)


def _run(tmp_path, n=1):
    repo = tmp_path / "repo"
    repo.mkdir()
    tasks = [Task(id=f"t-{i}", stage="toy", subject={}, instructions="Answer.", context="Q") for i in range(n)]
    return loop.collect_run("toy", tasks, tmp_path / "work", repo, run_id="r1")


def _fill(run, task_id, body):
    path = run.card_path(task_id)
    path.write_text(path.read_text(encoding="utf-8").replace("```yaml\n```", f"```yaml\n{body}\n```"),
                    encoding="utf-8", newline="\n")


def test_collect_returns_none_without_tasks(tmp_path):
    assert loop.collect_run("toy", [], tmp_path / "work", tmp_path / "repo") is None


def test_submit_applies_a_valid_card_with_provenance(tmp_path):
    run, target, applied = _run(tmp_path), {}, []
    _fill(run, "t-0", "answer: 42")
    report = loop.submit_run(run, _stage(applied), target, "test-agent")
    assert report.applied == ["t-0"]
    assert target["t-0"]["prov"] == {"driver": "agent", "agent": "test-agent", "run": "r1"}
    assert load_run(tmp_path / "work", "r1").task("t-0")["status"] == "applied"


def test_invalid_card_bounces_and_untouched_card_is_left_alone(tmp_path):
    run, target = _run(tmp_path, n=2), {}
    _fill(run, "t-0", "other: 1")
    report = loop.submit_run(run, _stage([]), target)
    assert report.bounced == {"t-0": ["answer is required"]}
    assert report.untouched == ["t-1"]


def test_stage_functions_are_looked_up_at_call_time(tmp_path):
    run, target = _run(tmp_path), {}
    _fill(run, "t-0", "answer: 1")
    mod = _stage([])
    mod.validate_result = lambda entry, result, tgt: ["patched after import"]
    assert loop.submit_run(run, mod, target).bounced == {"t-0": ["patched after import"]}


def test_a_card_that_raises_is_bounced_with_the_target_label(tmp_path):
    run, target = _run(tmp_path), {}
    _fill(run, "t-0", "answer: 1")
    mod = _stage([])
    mod.apply_result = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("disk"))
    report = loop.submit_run(run, mod, target, target_label="graph")
    assert "part of the card may already be in the graph" in report.bounced["t-0"][0]


def test_api_run_stops_at_the_cost_gate_before_sending(tmp_path):
    run, target, sent = _run(tmp_path), {}, []
    with pytest.raises(loop.BudgetError, match="--approve-cost"):
        loop.api_run(run, _stage([]), target, lambda p: sent.append(p) or "answer: 1", None, price_out=100000.0)
    assert sent == []


def test_api_run_applies_replies_through_the_same_path(tmp_path):
    run, target = _run(tmp_path), {}
    report = loop.api_run(run, _stage([]), target, lambda p: "```yaml\nanswer: 7\n```", 1.0, agent_name="g-test")
    assert report.applied == ["t-0"]
    assert target["t-0"]["prov"]["driver"] == "api"
```

- [ ] **Step 2: Run to confirm failure**

Run: `"$PY" -m pytest tests/core/test_agent_tasks_loop.py -q`
Expected: `ImportError` for `core.agent_tasks.loop`.

- [ ] **Step 3: Create `core/agent_tasks/loop.py`**

Port `agent/concept_graph/drivers.py` lines 15-131 with these exact substitutions: no `stages`, `GraphStore` or `.stages.common` imports; `store` becomes `target`; the module is passed in as `mod` rather than resolved by name; "graph" in the `_process` failure text comes from `target_label`; `collect` is split so task-building stays with the caller.

```python
"""Collect / submit / api_run over a stage module, independent of any one subproject's store."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from .tasks import Task, extract_result, result_from_response, ResultError
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
```

Continue the same file with the three remaining functions (message strings are copied verbatim from the original `drivers.py`):

```python
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
```

- [ ] **Step 4: Run core loop tests**

Run: `"$PY" -m pytest tests/core/test_agent_tasks_loop.py -q`
Expected: `7 passed`.

- [ ] **Step 5: Rewrite `agent/concept_graph/drivers.py` as the adapter**

```python
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
```

In `agent/concept_graph/stages/common.py` replace the local `provenance` definition (lines 59-60) with `from core.agent_tasks.loop import provenance  # noqa: F401` placed with the other imports.

- [ ] **Step 6: Run the full concept_graph suite**

Run: `"$PY" -m pytest tests/agent/concept_graph -q`
Expected: `335 passed`. In particular `test_cg_drivers.py` (monkeypatched `fill.validate_result` / `fill.apply_result`, `BudgetError`, `estimate_cost`) must pass unedited. If a patched-function test fails, the loop bound a stage function too early: fix `loop.py`, not the test.

- [ ] **Step 7: Commit**

```bash
git add core/agent_tasks/loop.py tests/core/test_agent_tasks_loop.py agent/concept_graph/drivers.py agent/concept_graph/stages/common.py
git commit -m "refactor(core): extract collect/submit/api_run to core.agent_tasks.loop; drivers becomes the graph adapter

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Shim identity checks and documentation

**Files:**
- Create: `tests/agent/concept_graph/test_cg_shims.py`, `core/agent_tasks/README.md`
- Modify: `agent/concept_graph/README.md` (one paragraph under the existing structure/commands section)

- [ ] **Step 1: Write the identity test**

```python
"""Old import paths keep resolving, to the very same objects as core's."""
import core.agent_tasks.loop as core_loop
import core.agent_tasks.tasks as core_tasks
import core.agent_tasks.work as core_work
from agent.concept_graph import drivers, sources, tasks, work
from agent.concept_graph.stages import common


def test_task_card_names_are_core_objects():
    for name in ("Task", "Passage", "ResultError", "render_card", "extract_result",
                 "parse_result_text", "result_from_response"):
        assert getattr(tasks, name) is getattr(core_tasks, name), name
    assert sources.Passage is core_tasks.Passage


def test_run_names_are_core_objects_and_create_run_is_a_wrapper():
    for name in ("Run", "STATUSES", "task_entry", "render_worklist", "load_run"):
        assert getattr(work, name) is getattr(core_work, name), name
    assert work.create_run is not core_work.create_run


def test_driver_names_are_core_objects():
    for name in ("SubmitReport", "BudgetError", "estimate_cost", "PRICE_IN", "PRICE_OUT", "OUT_TOKENS",
                 "FREE_LIMIT", "API_SUFFIX"):
        assert getattr(drivers, name) is getattr(core_loop, name), name
    assert common.provenance is core_loop.provenance
    for name in ("collect", "submit", "api_run", "gemini_complete"):
        assert callable(getattr(drivers, name))
```

- [ ] **Step 2: Run it**

Run: `"$PY" -m pytest tests/agent/concept_graph/test_cg_shims.py -q`
Expected: `3 passed`.

- [ ] **Step 3: Write `core/agent_tasks/README.md`**

Sections (each 3-8 lines, no placeholders): **What it is** (cards an agent fills in on the subscription route; code validates and applies; Claude is not in the loop); **Files** (the table above); **Stage-module contract** (the `make_tasks` / `validate_result` / `apply_result` signatures from Task 4 with one worked toy example copied from `tests/core/test_agent_tasks_loop.py`); **Compatibility rules** (card format, manifest keys incl. `graph_repo`, statuses, message text are frozen; changes need the concept_graph suite green and no edits to its tests); **Consumers** (`agent/concept_graph`; the literature extraction stage is next, see the spec); **Attachments** (optional list of existing file paths, rendered before `## Result`, missing files rejected at `create_run`).

- [ ] **Step 4: Add the concept_graph README note**

Add one paragraph to `agent/concept_graph/README.md`: task cards, run manifests and the collect/submit/api loop now live in `core/agent_tasks/`; `tasks.py`, `work.py` and `drivers.py` here are compatibility shims and the graph-bound adapter; link to `core/agent_tasks/README.md`.

- [ ] **Step 5: Commit**

```bash
git add tests/agent/concept_graph/test_cg_shims.py core/agent_tasks/README.md agent/concept_graph/README.md
git commit -m "test+docs(core): shim identity checks and core.agent_tasks README

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Verification and landing readiness

**Files:** none changed unless a check fails.

- [ ] **Step 1: Confirm no test file was edited**

Run: `git diff --name-status main...HEAD -- tests/`
Expected: only `A` (added) lines: `test_cg_compat_golden.py`, `test_cg_shims.py`, and the three `tests/core/test_agent_tasks_*.py`. Any `M` line is a violation: revert it and fix the code instead.

- [ ] **Step 2: Leftover references**

Run: `grep -rn "concept_graph\.\(tasks\|work\|drivers\)" --include=*.md --include=*.py . | grep -v "\.venv\|tests/\|docs/superpowers"`
Expected: no unexpected callers. Any new hit is a caller the shims must also satisfy: read it and add a name to the shim if needed.

- [ ] **Step 3: Run the two suites that matter**

Run: `"$PY" -m pytest tests/agent/concept_graph tests/core -q`
Expected: all pass (`335` concept_graph + the new core tests + existing core tests).

- [ ] **Step 4: Run the landing gate**

Run from the worktree: `"$PY" -m tools.land_branch check --full`
Expected: clean branch, rebase onto `main` succeeds, full suite passes, overlaps reported. Read the overlap list (the spec names `claude/notes-pipeline-consolidation` and others) and run `"$PY" -m tools.active_work`.

- [ ] **Step 5: Hand off**

Do not merge or push. Report: branch, SHA, changed paths, check result, overlaps, the main checkout's `git status --short` snapshot, known risks. Ask the owner whether to land commit `<SHA>` on `main`. Landing needs fresh approval if the SHA changes after a rebase.

---

## Self-review notes

- **Spec coverage (section 5):** generic contents lifted (Tasks 2-4); `Task`/`Passage` attachments (Task 2, 3); `graph_repo` to `output_repo` with alias and preserved privacy guard (Task 3); shims with same-object assertion (Task 5); byte-compat for card, manifest and statuses (Task 1 + Task 3 old-manifest test); suite-before/after gate with no test edits (Tasks 1, 6); caller tests for `core/` changes (Tasks 4, 6). Spec item "hidden graph-only fields on `provenance()` / `Passage`": checked while planning, both are plain (`provenance` is a 3-key dict; `Passage` is a 5-field dataclass) so no extra work.
- **Deviation from spec wording:** `create_run` in the concept_graph shim is a wrapper, not the same object as core's (it must keep the `graph_repo` name and the "graph repo" message text); the identity test asserts this explicitly.
- **Out of scope here (spec stages 1-6):** the literature extraction stage, journal transcription wiring and everything after. Stage 0 only proves generality with the toy stage in `tests/core/test_agent_tasks_loop.py`.
