# Question-Resolver Agent Driver Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the collect/submit/manifest agent-driven pattern to `agent/rag/resolve_questions.py`'s two generative call sites (key-term extraction, answer generation), as its own standalone CLI, mirroring the PDF and Excalidraw agent drivers.

**Architecture:** A qid-keyed key-terms cache and a qid-keyed answers cache make the two generative stages independently resumable (unlike Excalidraw, no source-hash invalidation is needed — `qid` already embeds a content hash of the question text, so a changed question simply gets a new qid and never collides with stale cache entries). A new `QuestionResolverDriver` protocol (Api/Agent/Null) lives in its own module to avoid a circular import. Submit's final step is a dedicated, driver-free `finalize_note_answers` function — not a re-invocation of the main entry point through a `NullDriver`, which is a deliberate departure from the Excalidraw stage's pattern, explained in Task 6, to avoid that stage's own AgentPending-swallowing review finding recurring here.

**Tech Stack:** Python 3.13, pytest, existing `core.env.gemini_utils` cache helpers, `pipelines.transcribe_notes.agent_work`'s generic manifest/worklist primitives (reused across packages, already precedent from the Excalidraw stage), existing Gemini client (mocked in tests).

**Spec:** `docs/superpowers/specs/agent/rag/2026-10-16-question-resolver-agent-driver-design.md`. Three corrections this plan makes to that spec, found while grounding exact signatures (recorded here, not silently): (1) answers DO need a small intermediate cache after all — the spec's "sidecar already serves that role" reasoning missed that a filled answer card gives only raw text, not a complete `Entry` (which needs `grounded`/`sources`/`context`, recomputable only by re-running retrieval); (2) `ManifestEntry.pages: list[int]` is reused to hold `list[str]` of qids — a type-hint mismatch, not a runtime one (dataclasses don't enforce annotations), accepted rather than forking the manifest module for one field; (3) cache-path helpers return a single path, not a `(cache_path, driver_path)` pair — Excalidraw's `driver_path` was flagged in that stage's final review as "computed but never written," so this plan doesn't repeat it.

## Global Constraints

- No hidden generative fallback: a note with a pending key-term or answer card reports "pending agent work," never silently retried against the metered API. `--allow-api-fallback` at `--submit` time is the one sanctioned, explicit exception.
- `AgentPending`/`NullDriverFired` must never be caught by a bare `except Exception` ahead of their own specific clause — Stage 2's final review found exactly this bug in `run_plan`; every new `except Exception` added by this plan must be checked against this.
- Retrieval (`retrieve_passages`) never routes through any driver, in either mode — it's embedding calls, not generation.
- `--driver` defaults to `"agent"`; `--driver api` is the explicit opt-out for a fully metered run (same default-flip decision already shipped for the other two drivers).
- No live API calls in any test — every Gemini call site is mocked or routed through a fake driver.
- The answer-stage collect call needs a **real** Gemini client even under `--driver agent` (retrieval is embedding calls) — unlike the Excalidraw and PDF collect branches, which pass `client=None`. Do not copy that convention here.

## Review Focus

- A note where `--redo` is combined with collect/submit — redo reuses a cached key-terms entry for an already-answered question rather than forcing fresh extraction (a deliberate, documented scope decision, not a bug) — confirm the implementation actually behaves this way and a test pins it, so a future reader doesn't "fix" it into silently diverging from the API path's behavior.
- A note whose question text changes between a collect and its submit (e.g. a retranscription ran in between) — the qid changes, so the old qid's staged card becomes orphaned (never matched at submit). Must not crash; should print a clear "no matching pending question" warning, same shape as Excalidraw's `doc_slug`-mismatch warning.
- `--submit --allow-api-fallback` on a document with zero manifest entries, or with only one of the two stages' entries present (e.g. key-terms card was staged and submitted, but the note was never re-collected for the answer stage) — must not crash.
- A bounced (validation-rejected) key-term or answer — its text must never land in the respective cache, so a later resumed collect or `--allow-api-fallback` run re-requests it rather than treating the bounce as done.
- The `finalize_note_answers` function's own exception handling — since it deliberately does NOT reuse the `NullDriver`-via-reinvocation pattern, confirm there is no equivalent bare-`except Exception` trap around whatever it does raise when a qid is unexpectedly still missing from the answers cache.

---

## Task 1: Cache path helpers + `QuestionResolverDriver` protocol, `ApiDriver`/`NullDriver`

**Files:**
- Modify: `agent/rag/resolve_questions.py` (add cache-path helpers)
- Create: `agent/rag/resolve_questions_driver.py`
- Create: `tests/agent/rag/test_resolve_questions_driver.py`
- Test: `tests/agent/rag/test_resolve_questions.py` (new cache-path tests)

**Interfaces:**
- Produces: `keyterms_cache_path_for(raw_path: str) -> str`, `answers_cache_path_for(raw_path: str) -> str` (both in `resolve_questions.py`). `QuestionResolverDriver` Protocol, `QuestionResolverApiDriver(client)`, `QuestionResolverNullDriver()` (in the new module).

- [ ] **Step 1: Write the failing test for the cache-path helpers**

Add to `tests/agent/rag/test_resolve_questions.py`:

```python
from agent.rag.resolve_questions import answers_cache_path_for, keyterms_cache_path_for


def test_keyterms_cache_path_sits_next_to_the_sidecar():
    path = keyterms_cache_path_for("/hub/academic_notes/c/lecture_notes/processed_outputs/N.excalidraw.md")
    assert path == "/hub/academic_notes/c/lecture_notes/processed_outputs/N.excalidraw.keyterms_cache.json"


def test_answers_cache_path_sits_next_to_the_sidecar():
    path = answers_cache_path_for("/hub/academic_notes/c/lecture_notes/processed_outputs/N.excalidraw.md")
    assert path == "/hub/academic_notes/c/lecture_notes/processed_outputs/N.excalidraw.answers_cache.json"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/agent/rag/test_resolve_questions.py -k cache_path -v`
Expected: FAIL with `ImportError: cannot import name 'keyterms_cache_path_for'`

- [ ] **Step 3: Add the two helpers to `resolve_questions.py`**

Add near `sidecar_path_for`'s import block (after the existing imports, before `RESOLVER_MODEL`):

```python
def keyterms_cache_path_for(raw_path: str) -> str:
    return raw_path[: -len(".excalidraw.md")] + ".excalidraw.keyterms_cache.json"


def answers_cache_path_for(raw_path: str) -> str:
    return raw_path[: -len(".excalidraw.md")] + ".excalidraw.answers_cache.json"
```

No `os.makedirs` is needed before saving either cache (unlike the Excalidraw stage): question resolution only ever runs on an already-transcribed note, so `processed_outputs/` already exists by the time either cache is written.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/agent/rag/test_resolve_questions.py -k cache_path -v`
Expected: PASS

- [ ] **Step 5: Write the failing test for `QuestionResolverApiDriver`**

Create `tests/agent/rag/test_resolve_questions_driver.py`:

```python
import unittest.mock

import pytest

from pipelines.transcribe_notes.agent_driver import NullDriverFired
from agent.rag.resolve_questions_driver import QuestionResolverApiDriver, QuestionResolverNullDriver


def test_api_driver_extract_key_terms_calls_gemini():
    client = unittest.mock.MagicMock()
    client.models.generate_content.return_value = unittest.mock.MagicMock(text="Hausdorff, Luce")
    driver = QuestionResolverApiDriver(client)
    result = driver.extract_key_terms("note.excalidraw.md", "q1-abc", "prompt text")
    assert result == "Hausdorff, Luce"
    call = client.models.generate_content.call_args.kwargs
    assert call["contents"] == "prompt text"


def test_api_driver_generate_answer_calls_gemini():
    client = unittest.mock.MagicMock()
    client.models.generate_content.return_value = unittest.mock.MagicMock(text="An explanation.")
    driver = QuestionResolverApiDriver(client)
    result = driver.generate_answer("note.excalidraw.md", "q1-abc", "answer prompt")
    assert result == "An explanation."


def test_null_driver_raises_on_every_method():
    driver = QuestionResolverNullDriver()
    with pytest.raises(NullDriverFired):
        driver.extract_key_terms("note.excalidraw.md", "q1-abc", "p")
    with pytest.raises(NullDriverFired):
        driver.generate_answer("note.excalidraw.md", "q1-abc", "p")
    with pytest.raises(NullDriverFired):
        driver.stage_key_terms("note.excalidraw.md", [("q1-abc", "p")])
    with pytest.raises(NullDriverFired):
        driver.stage_answers("note.excalidraw.md", [("q1-abc", "p")])
```

- [ ] **Step 6: Run test to verify it fails**

Run: `python -m pytest tests/agent/rag/test_resolve_questions_driver.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agent.rag.resolve_questions_driver'`

- [ ] **Step 7: Create `resolve_questions_driver.py`**

```python
# agent/rag/resolve_questions_driver.py
"""
Driver seam for resolve_questions.py's two Gemini call sites: key-term
extraction and answer generation. Mirrors excalidraw_agent_driver.py's
ApiDriver/AgentDriver/NullDriver split, in its own module for the same
reason: it needs prompt-building helpers that live in resolve_questions.py,
and resolve_questions.py needs this module's driver classes, so one of the
two imports must be lazy/local to avoid a cycle (resolve_questions.py's is).
See docs/superpowers/specs/agent/rag/
2026-10-16-question-resolver-agent-driver-design.md.
"""
from __future__ import annotations

from typing import Protocol

from core.env.gemini_utils import call_with_retries
from core.indexer.index_card import GENERATION_MODEL
from pipelines.transcribe_notes.agent_driver import NullDriverFired

_ANSWER_MODEL = "gemini-3.6-flash"  # matches resolve_questions.RESOLVER_MODEL


class QuestionResolverDriver(Protocol):
    def extract_key_terms(self, note_key: str, qid: str, prompt: str) -> str: ...

    def generate_answer(self, note_key: str, qid: str, prompt: str) -> str: ...

    def stage_key_terms(
        self, note_key: str, missing: list[tuple[str, str]],
    ) -> dict[str, str]: ...

    def stage_answers(
        self, note_key: str, missing: list[tuple[str, str]],
    ) -> dict[str, str]: ...


class QuestionResolverApiDriver:
    """Default driver: reproduces resolve_questions.py's existing direct
    Gemini calls unchanged."""

    def __init__(self, client):
        self.client = client

    def extract_key_terms(self, note_key: str, qid: str, prompt: str) -> str:
        response = call_with_retries(lambda: self.client.models.generate_content(
            model=GENERATION_MODEL, contents=prompt,
            config={"temperature": 0, "thinking_config": {"thinking_level": "minimal"}},
        ))
        return (response.text or "").strip()

    def generate_answer(self, note_key: str, qid: str, prompt: str) -> str:
        response = call_with_retries(lambda: self.client.models.generate_content(
            model=_ANSWER_MODEL, contents=prompt, config={"temperature": 0.2},
        ))
        return (response.text or "").strip()

    def stage_key_terms(self, note_key: str, missing: list[tuple[str, str]]) -> dict[str, str]:
        return {qid: self.extract_key_terms(note_key, qid, prompt) for qid, prompt in missing}

    def stage_answers(self, note_key: str, missing: list[tuple[str, str]]) -> dict[str, str]:
        return {qid: self.generate_answer(note_key, qid, prompt) for qid, prompt in missing}


class QuestionResolverNullDriver:
    """Used once every question's key terms/answer are already cached: a
    live call here is a cache-completeness bug, not a real gap."""

    def extract_key_terms(self, note_key: str, qid: str, prompt: str) -> str:
        raise NullDriverFired(
            f"QuestionResolverNullDriver: unexpected live call for {qid} in "
            f"{note_key} -- the cache should already be complete at this point."
        )

    def generate_answer(self, note_key: str, qid: str, prompt: str) -> str:
        raise NullDriverFired(
            f"QuestionResolverNullDriver: unexpected live call for {qid} in "
            f"{note_key} -- the cache should already be complete at this point."
        )

    def stage_key_terms(self, note_key: str, missing: list[tuple[str, str]]) -> dict[str, str]:
        raise NullDriverFired(
            f"QuestionResolverNullDriver: unexpected stage_key_terms call for {note_key} -- "
            "the cache should already be complete at this point."
        )

    def stage_answers(self, note_key: str, missing: list[tuple[str, str]]) -> dict[str, str]:
        raise NullDriverFired(
            f"QuestionResolverNullDriver: unexpected stage_answers call for {note_key} -- "
            "the cache should already be complete at this point."
        )
```

- [ ] **Step 8: Run test to verify it passes**

Run: `python -m pytest tests/agent/rag/test_resolve_questions_driver.py -v`
Expected: PASS

- [ ] **Step 9: Run both test files and commit**

Run: `python -m pytest tests/agent/rag/test_resolve_questions.py tests/agent/rag/test_resolve_questions_driver.py -v`
Expected: all PASS

```bash
git add agent/rag/resolve_questions.py agent/rag/resolve_questions_driver.py tests/agent/rag/test_resolve_questions.py tests/agent/rag/test_resolve_questions_driver.py
git commit -m "feat(agent/rag): QuestionResolverDriver protocol + cache-path helpers"
```

---

## Task 2: Route `resolve_question`'s sequential path through an optional driver

**Files:**
- Modify: `agent/rag/resolve_questions.py` (`resolve_question`)
- Test: `tests/agent/rag/test_resolve_questions.py`

**Interfaces:**
- Consumes: `QuestionResolverApiDriver`/`QuestionResolverDriver` (Task 1).
- Produces: `resolve_question(tag, context, neighbors, *, client, roots, course, model, exclude_paths, retrieve=retrieve_passages, extract=_extract_key_terms, driver=None, note_key=None) -> Entry`. **Backward compatible**: with `driver=None` (the default, used by every existing test), behavior is byte-for-byte identical to today — this task only adds a new, optional branch.

- [ ] **Step 1: Write the failing test for driver-routed key-term extraction and answer generation**

Add to `tests/agent/rag/test_resolve_questions.py`:

```python
def test_resolve_question_routes_key_terms_and_answer_through_a_driver():
    class FakeDriver:
        def __init__(self):
            self.calls = []

        def extract_key_terms(self, note_key, qid, prompt):
            self.calls.append(("extract", note_key, qid))
            return "Hausdorff"

        def generate_answer(self, note_key, qid, prompt):
            self.calls.append(("answer", note_key, qid))
            assert "Hausdorff metric" in prompt  # the retrieved passage reached the prompt
            return "An explanation via the driver."

    driver = FakeDriver()
    tag = find_tags("[Question] what is the Hausdorff distance?")[0]
    entry = resolve_question(
        tag, "ctx text", ["Slide text"], client=object(), roots=["/r"], course="c", model="m",
        exclude_paths=set(), retrieve=lambda *a, **k: [_passage("The Hausdorff metric is defined as ...")],
        driver=driver, note_key="note.excalidraw.md",
    )
    assert entry.answer == "An explanation via the driver."
    assert entry.grounded is True
    assert [c[0] for c in driver.calls] == ["extract", "answer"]
    assert all(c[1] == "note.excalidraw.md" for c in driver.calls)
    assert all(c[2] == tag.qid for c in driver.calls)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/agent/rag/test_resolve_questions.py -k routes_key_terms_and_answer -v`
Expected: FAIL with `TypeError: resolve_question() got an unexpected keyword argument 'driver'`

- [ ] **Step 3: Add the driver branch to `resolve_question`**

Replace `resolve_question` (`agent/rag/resolve_questions.py:98-124`):

```python
def resolve_question(
    tag: Tag, context: str, neighbors: list[str], *, client, roots: list[str], course: str | None,
    model: str, exclude_paths: set[str], retrieve=retrieve_passages, extract=_extract_key_terms,
    driver: "QuestionResolverDriver | None" = None, note_key: str | None = None,
) -> Entry:
    """One question -> one Entry. Raises on any failure (including an empty
    answer) so the caller records nothing for it. Grounded means a passage
    survived own-note exclusion and (no key terms, or one mentions a key
    term) -- /hint's check, plus a guard so an empty retrieval can never count
    as grounded.

    driver=None (the default) reproduces today's behavior exactly via
    `extract`/`retrieve` and a direct generate_content call. A given driver
    routes key-term extraction and answer generation through it instead;
    retrieval (`retrieve`) always stays local regardless."""
    if driver is not None:
        from agent.rag.resolve_questions_driver import QuestionResolverApiDriver

        key_term_prompt = _KEY_TERM_PROMPT_TEMPLATE.format(question=f"{tag.text}\n{context}")
        key_terms = _parse_key_terms(driver.extract_key_terms(note_key, tag.qid, key_term_prompt))
    else:
        key_terms = extract(f"{tag.text}\n{context}", client)
    found = retrieve(roots, f"{tag.text}\n{context[:300]}", client, course=course, key_terms=key_terms)
    # Hub-relative paths, not basenames: a same-named note in another folder is a legitimate source.
    passages = [p for p in found if p.path.replace("\\", "/") not in exclude_paths]
    grounded = bool(passages) and (not key_terms or any(_term_match_count(p.text, key_terms) for p in passages))
    prompt = build_answer_prompt(tag.text, context, neighbors, passages if grounded else None)
    if driver is not None:
        answer = driver.generate_answer(note_key, tag.qid, prompt).strip()
    else:
        response = call_with_retries(lambda: client.models.generate_content(
            model=model, contents=prompt, config={"temperature": 0.2},
        ))
        answer = (response.text or "").strip()
    if not answer:
        raise ValueError(f"model returned an empty answer for {tag.qid}")
    return Entry(
        qid=tag.qid, question=tag.text, grounded=grounded, model=model,
        resolved_at=datetime.now(timezone.utc).isoformat(),
        context=" ".join(context.split())[:_STORED_CONTEXT_CHARS], answer=answer,
        sources=[f"{p.path} ({p.citation})" if p.citation else p.path for p in passages] if grounded else [],
    )
```

Add the shared parsing helper and the imported prompt template just above `resolve_question`:

```python
from agent.rag.rag_agent import _KEY_TERM_PROMPT_TEMPLATE


def _parse_key_terms(text: str) -> list[str]:
    """Same comma-split logic as rag_agent._extract_key_terms's own parsing
    -- duplicated deliberately rather than calling that function, which must
    stay untouched (shared with /hint and the tutor)."""
    text = (text or "").strip()
    if not text:
        return []
    return [t.strip() for t in text.split(",") if t.strip()]
```

Add `"QuestionResolverDriver"` to a `TYPE_CHECKING` import block at the top of the file:

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agent.rag.resolve_questions_driver import QuestionResolverDriver
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/agent/rag/test_resolve_questions.py -k routes_key_terms_and_answer -v`
Expected: PASS

- [ ] **Step 5: Run the full test file and commit**

Run: `python -m pytest tests/agent/rag/test_resolve_questions.py -v`
Expected: all PASS (every existing test calls `resolve_question`/`resolve_note` without `driver=`, so the `driver is None` branch — behaviorally identical to today — is what they all still exercise)

```bash
git add agent/rag/resolve_questions.py tests/agent/rag/test_resolve_questions.py
git commit -m "feat(agent/rag): route resolve_question's sequential path through an optional driver"
```

---

## Task 3: Collect-mode key-term staging

**Files:**
- Modify: `agent/rag/resolve_questions_driver.py` (already has `stage_key_terms` from Task 1 — this task adds its test coverage and wires the caller)
- Modify: `agent/rag/resolve_questions.py` (`resolve_note` gains the key-term collect phase)
- Test: `tests/agent/rag/test_resolve_questions.py`, `test_resolve_questions_driver.py`

**Interfaces:**
- Produces: `resolve_note(..., driver=None, collect_mode=False)` — new trailing params. In `collect_mode=True`, `resolve_note` returns early after staging (or finding nothing to stage).

- [ ] **Step 1: Write the failing test for `QuestionResolverApiDriver.stage_key_terms`'s batching**

Add to `tests/agent/rag/test_resolve_questions_driver.py`:

```python
def test_api_driver_stage_key_terms_extracts_each_missing_one():
    client = unittest.mock.MagicMock()
    client.models.generate_content.side_effect = [
        unittest.mock.MagicMock(text="Hausdorff"), unittest.mock.MagicMock(text="Luce, Marschak"),
    ]
    driver = QuestionResolverApiDriver(client)
    result = driver.stage_key_terms("note.excalidraw.md", [("q1-a", "prompt 1"), ("q2-b", "prompt 2")])
    assert result == {"q1-a": "Hausdorff", "q2-b": "Luce, Marschak"}
```

- [ ] **Step 2: Run test to verify it passes already**

Run: `python -m pytest tests/agent/rag/test_resolve_questions_driver.py -k stage_key_terms -v`
Expected: PASS (Task 1 already implemented `stage_key_terms`; this step just adds the missing test coverage the Review Focus/acceptance-evidence section calls for — no `RED` step since there is no new production code in this step)

- [ ] **Step 3: Write the failing test for `resolve_note`'s collect-mode key-term phase**

Add to `tests/agent/rag/test_resolve_questions.py`:

```python
def test_resolve_note_collect_mode_stages_key_terms_for_every_pending_question(tmp_path):
    hub, raw = _hub(tmp_path)

    class FakeDriver:
        def __init__(self):
            self.staged = None

        def stage_key_terms(self, note_key, missing):
            self.staged = missing
            return {}  # nothing returned yet -- simulates an AgentDriver-style "card written" collect

    driver = FakeDriver()
    resolve_note(raw, hub, client=None, roots=[hub], driver=driver, collect_mode=True)
    assert driver.staged is not None
    assert {qid for qid, _prompt in driver.staged} == {
        t.qid for t in find_tags(_read_body_for_test(raw))
    }


def _read_body_for_test(raw_path):
    from core.env.frontmatter import parse_frontmatter
    with open(raw_path, encoding="utf-8") as f:
        return parse_frontmatter(f.read())[1]
```

- [ ] **Step 4: Run test to verify it fails**

Run: `python -m pytest tests/agent/rag/test_resolve_questions.py -k collect_mode_stages_key_terms -v`
Expected: FAIL with `TypeError: resolve_note() got an unexpected keyword argument 'driver'`

- [ ] **Step 5: Add the `collect_mode`/`driver` params and key-term phase to `resolve_note`**

Replace the signature and the top of the body of `resolve_note` (`agent/rag/resolve_questions.py:173-183`):

```python
def resolve_note(
    raw_path: str, hub: str, client, roots: list[str], model: str = RESOLVER_MODEL, redo: bool = False,
    budget: int | None = None, retrieve=retrieve_passages, extract=_extract_key_terms,
    driver: "QuestionResolverDriver | None" = None, collect_mode: bool = False,
) -> NoteResult:
    """Resolves a note's unanswered questions into its sidecar, then applies
    markers. A question that fails records nothing and is retried next run.

    collect_mode=True stages task cards instead of resolving anything, and
    returns before reaching the sidecar-writing loop below -- callers in
    agent mode never see a NoteResult that means anything beyond "ran"."""
    body = _read_body(raw_path)
    tags = find_tags(body)
    sidecar = sidecar_path_for(raw_path)
    rag_path = rag_path_for(raw_path)
    fields, entries = read_sidecar(sidecar)
    rekeyed = rekey_entries(tags, entries)  # answers survive a re-transcription that shifted ordinals
    by_id = {e.qid: e for e in entries}
    card = _note_card(hub, raw_path)
    course = derive_course(_rel(hub, raw_path))
    exclude = {_rel(hub, rag_path), _rel(hub, sidecar)}

    if collect_mode:
        _collect_note_questions(
            raw_path, body, tags, by_id, client, roots, course, exclude, model, driver, redo,
        )
        return NoteResult()
```

Leave everything from `result = NoteResult()` onward (the existing sequential loop) exactly as it is today, just below this new branch.

Add `_collect_note_questions` just above `resolve_note`:

```python
def _collect_note_questions(
    raw_path: str, body: str, tags: list[Tag], by_id: dict, client, roots: list[str],
    course: str | None, exclude: set[str], model: str, driver, redo: bool,
) -> None:
    from core.env.gemini_utils import load_json_cache, save_json_cache
    from pipelines.transcribe_notes.agent_driver import AgentPending

    pending_tags = [t for t in tags if redo or t.qid not in by_id]
    if not pending_tags:
        return

    keyterms_path = keyterms_cache_path_for(raw_path)
    keyterms_cache = load_json_cache(keyterms_path)
    missing_key_terms = [
        (t.qid, _KEY_TERM_PROMPT_TEMPLATE.format(question=f"{t.text}"))
        for t in pending_tags if t.qid not in keyterms_cache
    ]
    if missing_key_terms:
        try:
            staged = driver.stage_key_terms(raw_path, missing_key_terms)
        except AgentPending:
            raise
        for qid, text in staged.items():
            keyterms_cache[qid] = _parse_key_terms(text)
        save_json_cache(keyterms_path, keyterms_cache)
        # Re-check: an ApiDriver-style call returns synchronously and may have
        # filled everything in this same call; an AgentDriver always raises
        # AgentPending above and never reaches here.
        missing_key_terms = [
            (t.qid, "") for t in pending_tags if t.qid not in keyterms_cache
        ]
        if missing_key_terms:
            return  # still incomplete; nothing more to do this call

    _collect_note_answers(raw_path, body, pending_tags, client, roots, course, exclude, driver, keyterms_cache)
```

- [ ] **Step 6: Run test to verify it passes**

Run: `python -m pytest tests/agent/rag/test_resolve_questions.py -k collect_mode_stages_key_terms -v`
Expected: FAIL at this step with `NameError: name '_collect_note_answers' is not defined` — expected, since Task 4 defines it. Add a temporary stub to make this task's own test pass in isolation:

```python
def _collect_note_answers(*args, **kwargs) -> None:
    pass  # implemented in Task 4
```

Place this stub directly above `_collect_note_questions`. Then run: `python -m pytest tests/agent/rag/test_resolve_questions.py -k collect_mode_stages_key_terms -v`
Expected: PASS

- [ ] **Step 7: Write and pass the Review Focus test for `--redo` reusing cached key terms**

Add to `tests/agent/rag/test_resolve_questions.py`:

```python
def test_redo_in_collect_mode_does_not_re_extract_already_cached_key_terms(tmp_path):
    # Review Focus: redo must force re-answering, not force re-extracting
    # key terms that are already cached under the same qid (the question
    # text, and therefore its qid, hasn't changed just because --redo was
    # passed) -- a deliberate scope decision, pinned here so it isn't later
    # "fixed" into silently diverging from the plain API path.
    hub, raw = _hub(tmp_path)
    tags = find_tags(BODY)
    import json
    with open(keyterms_cache_path_for(raw), "w", encoding="utf-8") as f:
        json.dump({t.qid: ["already cached"] for t in tags}, f)
    # Also mark both questions already answered, so only --redo makes them pending.
    from core.indexer.questions import Entry, write_sidecar
    write_sidecar(sidecar_path_for(raw), {}, [
        Entry(qid=t.qid, question=t.text, grounded=True, model="m", resolved_at="t", answer="old answer")
        for t in tags
    ])

    class FakeDriver:
        def stage_key_terms(self, note_key, missing):
            pytest.fail("key-term stage must not run -- every qid is already cached")

        def stage_answers(self, note_key, missing):
            return {}

    resolve_note(raw, hub, client=object(), roots=[hub], driver=FakeDriver(), collect_mode=True, redo=True)
```

Add `from agent.rag.resolve_questions import keyterms_cache_path_for` to this test file's imports if Task 1 didn't already add it under that exact name (it did — reuse, don't duplicate the import line).

Run: `python -m pytest tests/agent/rag/test_resolve_questions.py -k redo_in_collect_mode -v`
Expected: PASS

- [ ] **Step 8: Run both test files and commit**

Run: `python -m pytest tests/agent/rag/test_resolve_questions.py tests/agent/rag/test_resolve_questions_driver.py -v`
Expected: all PASS

```bash
git add agent/rag/resolve_questions.py tests/agent/rag/test_resolve_questions.py tests/agent/rag/test_resolve_questions_driver.py
git commit -m "feat(agent/rag): collect-mode key-term staging for resolve_note"
```

---

## Task 4: Collect-mode answer staging

**Files:**
- Modify: `agent/rag/resolve_questions.py` (replace Task 3's `_collect_note_answers` stub)
- Test: `tests/agent/rag/test_resolve_questions.py`

**Interfaces:**
- Produces: a real `_collect_note_answers(raw_path, body, pending_tags, client, roots, course, exclude, driver, keyterms_cache) -> None`.

- [ ] **Step 1: Write the failing test for the answer-staging phase**

Add to `tests/agent/rag/test_resolve_questions.py`:

```python
def test_resolve_note_collect_mode_stages_answers_once_key_terms_are_cached(tmp_path):
    hub, raw = _hub(tmp_path)

    class FakeDriver:
        def __init__(self):
            self.answer_calls = None

        def stage_key_terms(self, note_key, missing):
            pytest.fail("key-term stage must not run again -- cache already has both questions")

        def stage_answers(self, note_key, missing):
            self.answer_calls = missing
            return {}

    # Pre-seed the key-terms cache as if a prior collect already filled it.
    tags = find_tags(BODY)
    import json
    with open(keyterms_cache_path_for(raw), "w", encoding="utf-8") as f:
        json.dump({t.qid: ["term"] for t in tags}, f)

    driver = FakeDriver()
    resolve_note(raw, hub, client=object(), roots=[hub], driver=driver, collect_mode=True)
    assert driver.answer_calls is not None
    assert {qid for qid, _prompt in driver.answer_calls} == {t.qid for t in tags}
```

Add `import json` and `from agent.rag.resolve_questions import keyterms_cache_path_for` to the test file's existing imports if not already present (Task 1 already added the import for the path-helper tests — confirm before adding a duplicate).

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/agent/rag/test_resolve_questions.py -k collect_mode_stages_answers -v`
Expected: FAIL — `driver.answer_calls` stays `None` because the Task 3 stub for `_collect_note_answers` does nothing.

- [ ] **Step 3: Replace the stub with the real answer-staging phase**

Replace the Task 3 stub:

```python
def _collect_note_answers(
    raw_path: str, body: str, pending_tags: list[Tag], client, roots: list[str],
    course: str | None, exclude: set[str], driver, keyterms_cache: dict,
) -> None:
    from core.env.gemini_utils import load_json_cache, save_json_cache
    from pipelines.transcribe_notes.agent_driver import AgentPending

    answers_path = answers_cache_path_for(raw_path)
    answers_cache = load_json_cache(answers_path)
    missing_answers = []
    for tag in pending_tags:
        if tag.qid in answers_cache:
            continue
        key_terms = keyterms_cache.get(tag.qid, [])
        context, neighbors = question_context(body, tag.ordinal)
        found = retrieve_passages(roots, f"{tag.text}\n{context[:300]}", client, course=course, key_terms=key_terms)
        passages = [p for p in found if p.path.replace("\\", "/") not in exclude]
        grounded = bool(passages) and (not key_terms or any(_term_match_count(p.text, key_terms) for p in passages))
        prompt = build_answer_prompt(tag.text, context, neighbors, passages if grounded else None)
        missing_answers.append((tag.qid, prompt))
    if not missing_answers:
        return
    try:
        staged = driver.stage_answers(raw_path, missing_answers)
    except AgentPending:
        raise
    for qid, text in staged.items():
        answers_cache[qid] = text
    save_json_cache(answers_path, answers_cache)
```

Note: this duplicates the grounding/prompt-building logic already in `resolve_question` (lines ~107-112). This is deliberate, not an oversight — `resolve_question` is the single-question synchronous path and stays untouched per Task 2's backward-compatibility requirement; a shared extraction would require changing its signature/control flow for no behavioral gain, so the small duplication is the lower-risk choice, same tradeoff Stage 2 accepted for its `_EXPANSION_MODEL_*` constants.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/agent/rag/test_resolve_questions.py -k collect_mode_stages_answers -v`
Expected: PASS

- [ ] **Step 5: Run the full test file and commit**

Run: `python -m pytest tests/agent/rag/test_resolve_questions.py -v`
Expected: all PASS

```bash
git add agent/rag/resolve_questions.py tests/agent/rag/test_resolve_questions.py
git commit -m "feat(agent/rag): collect-mode answer staging for resolve_note"
```

---

## Task 5: `QuestionResolverAgentDriver` (task-card writing)

**Files:**
- Create: `agent/rag/resolve_questions_agent_work.py`
- Test: `tests/agent/rag/test_resolve_questions_agent_work.py`

**Interfaces:**
- Consumes: `ManifestEntry`, `doc_slug_for`, `doc_work_dir`, `load_manifest`, `save_manifest`, `render_worklist` from `pipelines.transcribe_notes.agent_work` (reused unmodified, same as the Excalidraw stage — the `pages: list[int]` field holds `list[str]` of qids here; dataclasses don't enforce field types at runtime, so this works, at the cost of a type-hint mismatch accepted in this plan's header). `AgentPending` from `pipelines.transcribe_notes.agent_driver`. `compute_file_id` from `core.indexer.index_card`.
- Produces: `QuestionResolverAgentDriver(hub_root, run_id, agent_name="antigravity")` implementing the full `QuestionResolverDriver` surface (`extract_key_terms`/`generate_answer` raise `AgentPending` unconditionally — defensive only, collect_mode always calls `stage_key_terms`/`stage_answers` instead). `render_keyterms_card`, `render_answers_card`, `parse_card_output`.

- [ ] **Step 1: Write the failing test for `stage_key_terms` writing one card and raising**

Create `tests/agent/rag/test_resolve_questions_agent_work.py`:

```python
import os
import tempfile

import pytest

from pipelines.transcribe_notes.agent_driver import AgentPending
from pipelines.transcribe_notes.agent_work import load_manifest
from agent.rag.resolve_questions_agent_work import QuestionResolverAgentDriver


def test_stage_key_terms_writes_one_card_covering_every_missing_question():
    with tempfile.TemporaryDirectory() as hub:
        raw_path = os.path.join(hub, "N.excalidraw.md")
        with open(raw_path, "w", encoding="utf-8") as f:
            f.write("scene content for file_id hashing")

        driver = QuestionResolverAgentDriver(hub, "run-1")
        with pytest.raises(AgentPending):
            driver.stage_key_terms(
                raw_path, missing=[("q1-abc", "key-term prompt for q1"), ("q2-def", "key-term prompt for q2")],
            )
        doc_dir = os.path.join(hub, ".agent_work", "run-1", driver.last_doc_slug)
        entries = load_manifest(doc_dir)
        assert len(entries) == 1
        assert entries[0].pages == ["q1-abc", "q2-def"]
        assert entries[0].status == "pending"
        assert entries[0].tier == "keyterms"


def test_recollecting_a_still_pending_keyterms_card_does_not_duplicate_it():
    with tempfile.TemporaryDirectory() as hub:
        raw_path = os.path.join(hub, "N.excalidraw.md")
        with open(raw_path, "w", encoding="utf-8") as f:
            f.write("scene content")

        driver = QuestionResolverAgentDriver(hub, "run-1")
        with pytest.raises(AgentPending):
            driver.stage_key_terms(raw_path, missing=[("q1-abc", "prompt")])

        second_driver = QuestionResolverAgentDriver(hub, "run-1")
        with pytest.raises(AgentPending):
            second_driver.stage_key_terms(raw_path, missing=[("q1-abc", "prompt")])

        doc_dir = os.path.join(hub, ".agent_work", "run-1", driver.last_doc_slug)
        assert len(load_manifest(doc_dir)) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/agent/rag/test_resolve_questions_agent_work.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agent.rag.resolve_questions_agent_work'`

- [ ] **Step 3: Create `resolve_questions_agent_work.py`**

```python
# agent/rag/resolve_questions_agent_work.py
"""
QuestionResolverAgentDriver: writes task cards for resolve_questions.py's two
generative stages (key-term extraction, answer generation) instead of
calling Gemini. Reuses pipelines.transcribe_notes.agent_work's generic
run-directory layout, manifest, and worklist primitives (none of them are
PDF-specific). The shared ManifestEntry.pages: list[int] field holds this
driver's qid strings instead -- a type-hint mismatch, not a runtime one
(dataclasses don't enforce field types); see the plan header for why this
was accepted over forking the manifest module. See docs/superpowers/specs/
agent/rag/2026-10-16-question-resolver-agent-driver-design.md.
"""
from __future__ import annotations

import os

from pipelines.transcribe_notes.agent_driver import AgentPending
from pipelines.transcribe_notes.agent_work import (
    ManifestEntry,
    doc_slug_for,
    doc_work_dir,
    load_manifest,
    render_worklist,
    save_manifest,
)
from core.indexer.index_card import compute_file_id

_OUTPUT_HEADER = "## Agent output"


def render_keyterms_card(doc_dir: str, task_id: str, missing: list[tuple[str, str]]) -> None:
    os.makedirs(doc_dir, exist_ok=True)
    qids = [m[0] for m in missing]
    lines = [f"# {task_id} (key terms, {len(qids)} question(s))", ""]
    for qid, prompt in missing:
        lines += [f"## {qid}", "", prompt, ""]
    lines += [
        "## Expected output", "",
        "One section per question above, in order, using this exact format:", "",
        "```", "--- KEYTERMS <qid> ---", "<comma-separated key terms, or nothing if none apply>", "```", "",
        _OUTPUT_HEADER, "",
    ]
    with open(os.path.join(doc_dir, f"{task_id}.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def render_answers_card(doc_dir: str, task_id: str, missing: list[tuple[str, str]]) -> None:
    os.makedirs(doc_dir, exist_ok=True)
    qids = [m[0] for m in missing]
    lines = [f"# {task_id} (answers, {len(qids)} question(s))", ""]
    for qid, prompt in missing:
        lines += [f"## {qid}", "", prompt, ""]
    lines += [
        "## Expected output", "",
        "One section per question above, in order, using this exact format:", "",
        "```", "--- ANSWER <qid> ---", "<the explanation markdown for that question>", "```", "",
        _OUTPUT_HEADER, "",
    ]
    with open(os.path.join(doc_dir, f"{task_id}.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def parse_card_output(doc_dir: str, task_id: str) -> str | None:
    card_path = os.path.join(doc_dir, f"{task_id}.md")
    with open(card_path, "r", encoding="utf-8") as f:
        content = f.read()
    idx = content.find(_OUTPUT_HEADER)
    if idx == -1:
        return None
    output = content[idx + len(_OUTPUT_HEADER):].strip()
    return output or None


class QuestionResolverAgentDriver:
    """QuestionResolverDriver that writes task cards instead of calling
    Gemini. One instance is reused across every note in a collect run;
    `last_doc_slug` records the slug used for the most recent call, same
    convention as the PDF and Excalidraw agent drivers."""

    def __init__(self, hub_root: str, run_id: str, agent_name: str = "antigravity"):
        self.hub_root = hub_root
        self.run_id = run_id
        self.agent_name = agent_name
        self._task_counters: dict[str, int] = {}
        self.last_doc_slug: str | None = None

    def _next_task_id(self, doc_slug: str) -> str:
        n = self._task_counters.get(doc_slug, 0) + 1
        self._task_counters[doc_slug] = n
        return f"task-{n:04d}"

    def _doc_dir(self, raw_path: str) -> str:
        file_id = compute_file_id(raw_path)
        doc_slug = doc_slug_for(raw_path, file_id)
        self.last_doc_slug = doc_slug
        doc_dir = doc_work_dir(self.hub_root, self.run_id, doc_slug)
        if doc_slug not in self._task_counters:
            max_n = 0
            for entry in load_manifest(doc_dir):
                try:
                    max_n = max(max_n, int(entry.task_id.rsplit("-", 1)[1]))
                except (IndexError, ValueError):
                    continue
            self._task_counters[doc_slug] = max_n
        return doc_dir

    def extract_key_terms(self, note_key: str, qid: str, prompt: str) -> str:
        raise AgentPending()  # collect_mode always calls stage_key_terms instead; defensive only

    def generate_answer(self, note_key: str, qid: str, prompt: str) -> str:
        raise AgentPending()  # collect_mode always calls stage_answers instead; defensive only

    def stage_key_terms(self, note_key: str, missing: list[tuple[str, str]]) -> dict[str, str]:
        doc_dir = self._doc_dir(note_key)
        qids = [m[0] for m in missing]
        for entry in load_manifest(doc_dir):
            if entry.status != "submitted" and entry.tier == "keyterms" and entry.pages == qids:
                raise AgentPending()  # already staged, not yet submitted -- don't overwrite
        task_id = self._next_task_id(self.last_doc_slug)
        render_keyterms_card(doc_dir, task_id, missing)
        entries = load_manifest(doc_dir)
        entries.append(ManifestEntry(task_id=task_id, tier="keyterms", pages=qids, status="pending"))
        save_manifest(doc_dir, entries)
        render_worklist(doc_dir, entries)
        raise AgentPending()

    def stage_answers(self, note_key: str, missing: list[tuple[str, str]]) -> dict[str, str]:
        doc_dir = self._doc_dir(note_key)
        qids = [m[0] for m in missing]
        for entry in load_manifest(doc_dir):
            if entry.status != "submitted" and entry.tier == "answers" and entry.pages == qids:
                raise AgentPending()
        task_id = self._next_task_id(self.last_doc_slug)
        render_answers_card(doc_dir, task_id, missing)
        entries = load_manifest(doc_dir)
        entries.append(ManifestEntry(task_id=task_id, tier="answers", pages=qids, status="pending"))
        save_manifest(doc_dir, entries)
        render_worklist(doc_dir, entries)
        raise AgentPending()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/agent/rag/test_resolve_questions_agent_work.py -v`
Expected: PASS

- [ ] **Step 5: Run the full new test file and commit**

```bash
git add agent/rag/resolve_questions_agent_work.py tests/agent/rag/test_resolve_questions_agent_work.py
git commit -m "feat(agent/rag): QuestionResolverAgentDriver task-card writing"
```

---

## Task 6: `resolve_questions_submit.py` — validation, submit, finalize

**Files:**
- Create: `agent/rag/resolve_questions_submit.py`
- Create: `tests/agent/rag/test_resolve_questions_submit.py`

**Interfaces:**
- Consumes: `parse_card_output` (Task 5), `QuestionResolverAgentDriver` (Task 5), `keyterms_cache_path_for`/`answers_cache_path_for` (Task 1).
- Produces: `submit_doc(hub_root, academic_hub_root, run_id, doc_slug, raw_path, hub, client, model_override, agent_name="antigravity", allow_api_fallback=False) -> str`.

**Design note — why this submit does NOT reuse Excalidraw's "restage via re-invoking the main function with NullDriver" pattern:** Excalidraw's `submit_doc` calls `process_excalidraw_note(..., driver=ExcalidrawNullDriver(), collect_mode=False)` to finish the write — safe there because every piece `write_outputs` needs (raw markdown, expanded markdown) is fully reconstructable from already-complete caches with no further decisions. Here, a filled answer card gives only raw text; a complete `Entry` also needs `grounded`/`sources`/`context`, which requires re-running retrieval — `resolve_note`'s existing sequential loop has no cache-aware short-circuit for "I already have the raw answer text, skip the driver" (adding one would mean changing `resolve_question`'s control flow, which Task 2 deliberately kept untouched for `driver=None`). So this stage's submit does NOT reuse `resolve_note`/`resolve_question` to finish the job; it has its own small, direct `finalize_note_answers` that re-runs retrieval and builds `Entry`s straight from the answers cache, writing the sidecar once at the end — never calling any driver at all for this step, which also sidesteps the entire class of "AgentPending/NullDriverFired swallowed by a bare except" bug Stage 2's final review found, since there's no exception-prone re-invocation here to get wrong.

- [ ] **Step 1: Write the failing test for key-term card validation**

Create `tests/agent/rag/test_resolve_questions_submit.py`:

```python
from agent.rag.resolve_questions_submit import validate_answer_card_output, validate_keyterms_card_output


def test_validate_keyterms_card_output_parses_all_sections():
    raw = "--- KEYTERMS q1-abc ---\nHausdorff, Luce\n--- KEYTERMS q2-def ---\n\n"
    result = validate_keyterms_card_output(raw, expected_qids=["q1-abc", "q2-def"])
    assert result.pages == {"q1-abc": "Hausdorff, Luce", "q2-def": ""}
    assert result.bounce_reason is None  # an empty key-terms section is valid -- "no specific terms" is a real answer


def test_validate_keyterms_card_output_bounces_on_a_missing_section():
    raw = "--- KEYTERMS q1-abc ---\nHausdorff\n"
    result = validate_keyterms_card_output(raw, expected_qids=["q1-abc", "q2-def"])
    assert result.bounce_reason is not None
    assert "q2-def" in result.bounce_reason


def test_validate_answer_card_output_bounces_on_an_empty_answer():
    raw = "--- ANSWER q1-abc ---\n\n"
    result = validate_answer_card_output(raw, expected_qids=["q1-abc"])
    assert result.bounce_reason is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/agent/rag/test_resolve_questions_submit.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Create `resolve_questions_submit.py` — validation**

```python
# agent/rag/resolve_questions_submit.py
"""
submit: validates a filled question-resolver task card's output and writes
it into the note's key-terms or answers cache, then (once a whole stage is
submitted) re-invokes the agent driver to advance to the next stage, or
finalizes answers directly into the sidecar. See docs/superpowers/specs/
agent/rag/2026-10-16-question-resolver-agent-driver-design.md.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone

from core.env.gemini_utils import load_json_cache, save_json_cache
from agent.rag.rag_agent import _term_match_count, retrieve_passages
from agent.rag.resolve_questions import (
    _rel,
    answers_cache_path_for,
    build_answer_prompt,
    keyterms_cache_path_for,
    question_context,
    _parse_key_terms,
)
from core.indexer.questions import Entry, Tag, find_tags, read_sidecar, sidecar_path_for, write_sidecar
from core.indexer.index_card import derive_course
from pipelines.transcribe_notes.agent_driver import AgentPending
from pipelines.transcribe_notes.agent_work import doc_work_dir, load_manifest, render_worklist, save_manifest

_SECTION_RE_TEMPLATE = r"--- {label} ([\w-]+) ---\n(.*?)(?=--- {label} [\w-]+ ---|\Z)"


@dataclass
class ValidationResult:
    pages: dict[str, str] = field(default_factory=dict)
    bounce_reason: str | None = None


def _parse_sections(raw_output: str, label: str, expected_qids: list[str]) -> dict[str, str]:
    pattern = re.compile(_SECTION_RE_TEMPLATE.format(label=label), re.DOTALL)
    parsed = {qid: text.strip() for qid, text in pattern.findall(raw_output)}
    return {q: parsed[q] for q in expected_qids if q in parsed}


def validate_keyterms_card_output(raw_output: str, expected_qids: list[str]) -> ValidationResult:
    parsed = _parse_sections(raw_output, "KEYTERMS", expected_qids)
    missing = [q for q in expected_qids if q not in parsed]
    if missing:
        return ValidationResult(pages=parsed, bounce_reason=f"missing section(s): {missing}")
    return ValidationResult(pages=parsed)  # an empty section is valid here -- "no specific terms"


def validate_answer_card_output(raw_output: str, expected_qids: list[str]) -> ValidationResult:
    parsed = _parse_sections(raw_output, "ANSWER", expected_qids)
    missing = [q for q in expected_qids if q not in parsed or not parsed[q].strip()]
    if missing:
        return ValidationResult(pages=parsed, bounce_reason=f"missing or empty section(s): {missing}")
    for qid, text in parsed.items():
        if text.count("```") % 2 != 0:
            return ValidationResult(pages=parsed, bounce_reason=f"{qid} has an unclosed code fence")
        if text.count("$$") % 2 != 0:
            return ValidationResult(pages=parsed, bounce_reason=f"{qid} has unbalanced $$ display-math delimiters")
    return ValidationResult(pages=parsed)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/agent/rag/test_resolve_questions_submit.py -v`
Expected: PASS

- [ ] **Step 5: Write the failing test for `submit_doc`'s cross-stage restage**

```python
import os
import tempfile
import unittest.mock

from core.indexer.index_card import compute_file_id
from pipelines.transcribe_notes.agent_driver import AgentPending
from pipelines.transcribe_notes.agent_work import ManifestEntry, doc_slug_for, save_manifest
from agent.rag.resolve_questions_submit import submit_doc


def test_submit_doc_writes_keyterms_cache_and_stages_the_answer_card():
    with tempfile.TemporaryDirectory() as hub:
        notes_dir = os.path.join(hub, "academic_notes", "c", "lecture_notes", "processed_outputs")
        os.makedirs(notes_dir)
        raw_path = os.path.join(notes_dir, "N.excalidraw.md")
        with open(raw_path, "w", encoding="utf-8") as f:
            f.write("---\n---\n\n[Question] what is the Hausdorff distance?\n")

        doc_slug = doc_slug_for(raw_path, compute_file_id(raw_path))
        doc_dir = os.path.join(hub, ".agent_work", "run-1", doc_slug)
        os.makedirs(doc_dir)
        task_id = "task-0001"
        from core.indexer.questions import find_tags
        qid = find_tags("[Question] what is the Hausdorff distance?")[0].qid
        with open(os.path.join(doc_dir, f"{task_id}.md"), "w", encoding="utf-8") as f:
            f.write(f"## Agent output\n\n--- KEYTERMS {qid} ---\nHausdorff\n")
        save_manifest(doc_dir, [ManifestEntry(task_id=task_id, tier="keyterms", pages=[qid], status="pending")])

        with unittest.mock.patch(
            "agent.rag.resolve_questions_submit.QuestionResolverAgentDriver",
        ) as MockAgentDriver:
            mock_instance = MockAgentDriver.return_value
            mock_instance.stage_answers.side_effect = AgentPending()
            status = submit_doc(hub, hub, "run-1", doc_slug, raw_path, hub, client=object(), model_override="m")

        assert "incomplete" in status
        mock_instance.stage_answers.assert_called_once()
```

- [ ] **Step 6: Run test to verify it fails**

Run: `python -m pytest tests/agent/rag/test_resolve_questions_submit.py -k writes_keyterms_cache -v`
Expected: FAIL with `ImportError: cannot import name 'submit_doc'`

- [ ] **Step 7: Implement `submit_doc` and `finalize_note_answers`**

Append to `resolve_questions_submit.py`:

```python
def submit_doc(
    hub_root: str, academic_hub_root: str, run_id: str, doc_slug: str,
    raw_path: str, hub: str, client, model_override: str | None,
    agent_name: str = "antigravity", allow_api_fallback: bool = False,
) -> str:
    from agent.rag.resolve_questions_agent_work import QuestionResolverAgentDriver
    from agent.rag.resolve_questions_driver import QuestionResolverApiDriver

    doc_dir = doc_work_dir(hub_root, run_id, doc_slug)
    entries = load_manifest(doc_dir)
    if not entries:
        return "incomplete: no manifest found for this document"

    from agent.rag.resolve_questions_agent_work import parse_card_output

    keyterm_entries = [e for e in entries if e.tier == "keyterms"]
    answer_entries = [e for e in entries if e.tier == "answers"]

    def _apply(card_entries: list, cache_path: str, validator, parser) -> None:
        if not card_entries:
            return
        cache = load_json_cache(cache_path)
        for entry in card_entries:
            if entry.status not in ("pending", "filled", "bounced"):
                continue
            raw_output = parse_card_output(doc_dir, entry.task_id)
            if raw_output is None:
                continue
            result = validator(raw_output, entry.pages)
            if result.bounce_reason:
                entry.status = "bounced"
                entry.bounce_reason = result.bounce_reason
                continue
            for qid, text in result.pages.items():
                cache[qid] = parser(text) if parser else text
            entry.status = "submitted"
            entry.bounce_reason = None
        save_json_cache(cache_path, cache)

    keyterms_path = keyterms_cache_path_for(raw_path)
    answers_path = answers_cache_path_for(raw_path)
    _apply(keyterm_entries, keyterms_path, validate_keyterms_card_output, _parse_key_terms)
    _apply(answer_entries, answers_path, validate_answer_card_output, None)
    save_manifest(doc_dir, entries)
    render_worklist(doc_dir, entries)

    any_unsubmitted = any(e.status != "submitted" for e in entries)
    if any_unsubmitted and not allow_api_fallback:
        remaining = sum(1 for e in entries if e.status != "submitted")
        return f"incomplete: {remaining} card(s) still pending/bounced"

    tags = find_tags(_read_raw_body(raw_path))
    _, sidecar_entries = read_sidecar(sidecar_path_for(raw_path))
    answered = {e.qid for e in sidecar_entries}
    pending_tags = [t for t in tags if t.qid not in answered]

    if allow_api_fallback:
        driver = QuestionResolverApiDriver(client)
    else:
        driver = QuestionResolverAgentDriver(hub_root, run_id, agent_name=agent_name)

    keyterms_cache = load_json_cache(keyterms_path)
    answers_cache = load_json_cache(answers_path)
    still_missing_keyterms = [t for t in pending_tags if t.qid not in keyterms_cache]
    if still_missing_keyterms:
        if allow_api_fallback:
            from agent.rag.resolve_questions import _KEY_TERM_PROMPT_TEMPLATE

            missing = [
                (t.qid, _KEY_TERM_PROMPT_TEMPLATE.format(question=t.text)) for t in still_missing_keyterms
            ]
            staged = driver.stage_key_terms(raw_path, missing)
            for qid, text in staged.items():
                keyterms_cache[qid] = _parse_key_terms(text)
            save_json_cache(keyterms_path, keyterms_cache)
        else:
            return "incomplete: key-term card not yet staged for this run"

    still_missing_answers = [t for t in pending_tags if t.qid not in answers_cache]
    if still_missing_answers:
        body = _read_raw_body(raw_path)
        course = derive_course(_rel(hub, raw_path))
        exclude = {_rel(hub, raw_path.replace(".excalidraw.md", ".excalidraw.rag.md")),
                   _rel(hub, sidecar_path_for(raw_path))}
        missing = []
        for tag in still_missing_answers:
            key_terms = keyterms_cache.get(tag.qid, [])
            context, neighbors = question_context(body, tag.ordinal)
            found = retrieve_passages([hub], f"{tag.text}\n{context[:300]}", client, course=course, key_terms=key_terms)
            passages = [p for p in found if p.path.replace("\\", "/") not in exclude]
            grounded = bool(passages) and (not key_terms or any(_term_match_count(p.text, key_terms) for p in passages))
            prompt = build_answer_prompt(tag.text, context, neighbors, passages if grounded else None)
            missing.append((tag.qid, prompt))
        try:
            staged = driver.stage_answers(raw_path, missing)
        except AgentPending:
            return "incomplete: answer card staged, awaiting agent fill"
        for qid, text in staged.items():
            answers_cache[qid] = text
        save_json_cache(answers_path, answers_cache)

    finalize_note_answers(raw_path, hub, client, [hub], model_label="api-fallback" if allow_api_fallback else "antigravity")
    return "complete" if not allow_api_fallback else "complete (api fallback used for remaining questions)"


def _read_raw_body(raw_path: str) -> str:
    from core.env.frontmatter import parse_frontmatter
    with open(raw_path, encoding="utf-8") as f:
        return parse_frontmatter(f.read())[1]


def finalize_note_answers(raw_path: str, hub: str, client, roots: list[str], model_label: str = "antigravity") -> None:
    """Builds complete Entry objects from the answers cache and writes the
    sidecar -- never calls any driver. A qid in `tags` but absent from both
    the sidecar and the answers cache is simply not part of this run (e.g.
    a question added by a retranscription after this run's collect already
    happened) and is left untouched, same as the existing sequential path's
    own by-qid skip logic."""
    from core.indexer.questions import apply_markers, rag_path_for

    body = _read_raw_body(raw_path)
    tags = find_tags(body)
    sidecar = sidecar_path_for(raw_path)
    rag_path = rag_path_for(raw_path)
    fields, entries = read_sidecar(sidecar)
    by_id = {e.qid: e for e in entries}
    course = derive_course(_rel(hub, raw_path))
    exclude = {_rel(hub, rag_path), _rel(hub, sidecar)}

    keyterms_cache = load_json_cache(keyterms_cache_path_for(raw_path))
    answers_cache = load_json_cache(answers_cache_path_for(raw_path))

    for tag in tags:
        if tag.qid in by_id or tag.qid not in answers_cache:
            continue
        try:
            key_terms = keyterms_cache.get(tag.qid, [])
            context, neighbors = question_context(body, tag.ordinal)
            found = retrieve_passages(roots, f"{tag.text}\n{context[:300]}", client, course=course, key_terms=key_terms)
            passages = [p for p in found if p.path.replace("\\", "/") not in exclude]
            grounded = bool(passages) and (not key_terms or any(_term_match_count(p.text, key_terms) for p in passages))
            by_id[tag.qid] = Entry(
                qid=tag.qid, question=tag.text, grounded=grounded, model=model_label,
                resolved_at=datetime.now(timezone.utc).isoformat(),
                context=" ".join(context.split())[:600], answer=answers_cache[tag.qid],
                sources=[f"{p.path} ({p.citation})" if p.citation else p.path for p in passages] if grounded else [],
            )
        except Exception as err:
            # One question's retrieval failing must not lose every other
            # already-cached answer in this note -- same per-question
            # resilience resolve_note's own sequential loop already has.
            # No AgentPending/NullDriverFired risk here: finalize never
            # calls any driver, so a bare except is safe, not a guardrail
            # violation.
            print(f"WARNING: {tag.qid} finalize failed: {err}")

    in_order = [by_id[t.qid] for t in tags if t.qid in by_id]
    leftover = [e for qid, e in by_id.items() if qid not in {t.qid for t in tags}]
    ordered = in_order + leftover
    fields = {
        **fields,
        "source_excalidraw": _rel(hub, raw_path),
        "resolver_model": model_label,
        "resolved_at": datetime.now(timezone.utc).isoformat(),
        "questions": str(len(ordered)),
    }
    write_sidecar(sidecar, fields, ordered)
    apply_markers(raw_path, rag_path)
```

- [ ] **Step 8: Run test to verify it passes**

Run: `python -m pytest tests/agent/rag/test_resolve_questions_submit.py -k writes_keyterms_cache -v`
Expected: PASS

- [ ] **Step 9: Write and pass a happy-path test covering `finalize_note_answers`**

```python
def test_submit_doc_finalizes_into_the_sidecar_once_both_stages_are_cached(tmp_path):
    hub = str(tmp_path / "hub")
    notes_dir = os.path.join(hub, "academic_notes", "c", "lecture_notes", "processed_outputs")
    os.makedirs(notes_dir)
    raw_path = os.path.join(notes_dir, "N.excalidraw.md")
    question = "[Question] what is the Hausdorff distance?"
    with open(raw_path, "w", encoding="utf-8") as f:
        f.write(f"---\n---\n\n{question}\n")
    rag_path = raw_path.replace(".excalidraw.md", ".excalidraw.rag.md")
    with open(rag_path, "w", encoding="utf-8") as f:
        f.write(f"---\n---\n\n{question}\n")

    from core.indexer.questions import find_tags
    qid = find_tags(question)[0].qid
    doc_slug = doc_slug_for(raw_path, compute_file_id(raw_path))
    doc_dir = os.path.join(hub, ".agent_work", "run-1", doc_slug)
    os.makedirs(doc_dir)
    save_manifest(doc_dir, [
        ManifestEntry(task_id="task-0001", tier="keyterms", pages=[qid], status="submitted"),
        ManifestEntry(task_id="task-0002", tier="answers", pages=[qid], status="submitted"),
    ])
    import json
    with open(keyterms_cache_path_for(raw_path), "w", encoding="utf-8") as f:
        json.dump({qid: ["Hausdorff"]}, f)
    with open(answers_cache_path_for(raw_path), "w", encoding="utf-8") as f:
        json.dump({qid: "An explanation."}, f)

    with unittest.mock.patch(
        "agent.rag.resolve_questions_submit.retrieve_passages", return_value=[],
    ):
        status = submit_doc(hub, hub, "run-1", doc_slug, raw_path, hub, client=object(), model_override="m")

    assert status == "complete"
    _, entries = read_sidecar(sidecar_path_for(raw_path))
    assert entries[0].answer == "An explanation."
    assert entries[0].qid == qid
```

Add `from agent.rag.resolve_questions import answers_cache_path_for, keyterms_cache_path_for` and
`from core.indexer.questions import read_sidecar, sidecar_path_for` to this test file's imports if not already present from Step 1/5.

Run: `python -m pytest tests/agent/rag/test_resolve_questions_submit.py -k finalizes_into_the_sidecar -v`
Expected: PASS

- [ ] **Step 10: Write and pass the remaining Review Focus tests**

Add to `tests/agent/rag/test_resolve_questions_submit.py`:

```python
def test_submit_doc_with_no_manifest_does_not_crash():
    # Review Focus: a mistyped doc-slug, or a note already fully submitted
    # and swept out of .agent_work/, must report "incomplete", not raise.
    with tempfile.TemporaryDirectory() as hub:
        raw_path = os.path.join(hub, "N.excalidraw.md")
        with open(raw_path, "w", encoding="utf-8") as f:
            f.write("---\n---\n\n[Question] x?\n")
        status = submit_doc(
            hub, hub, "run-1", "nonexistent-slug", raw_path, hub, client=object(), model_override="m",
            allow_api_fallback=True,
        )
    assert "incomplete" in status


def test_bounced_keyterms_card_is_marked_and_not_written_to_cache():
    # Review Focus: a bounced key-term card must not land in the cache --
    # a later resumed collect/submit must re-request it, not treat the
    # bounce as done.
    with tempfile.TemporaryDirectory() as hub:
        notes_dir = os.path.join(hub, "academic_notes", "c", "lecture_notes", "processed_outputs")
        os.makedirs(notes_dir)
        raw_path = os.path.join(notes_dir, "N.excalidraw.md")
        with open(raw_path, "w", encoding="utf-8") as f:
            f.write("---\n---\n\n[Question] what is the Hausdorff distance?\n")
        from core.indexer.questions import find_tags
        qid = find_tags("[Question] what is the Hausdorff distance?")[0].qid

        doc_slug = doc_slug_for(raw_path, compute_file_id(raw_path))
        doc_dir = os.path.join(hub, ".agent_work", "run-1", doc_slug)
        os.makedirs(doc_dir)
        task_id = "task-0001"
        with open(os.path.join(doc_dir, f"{task_id}.md"), "w", encoding="utf-8") as f:
            f.write("## Agent output\n\n")  # no "--- KEYTERMS ---" section at all -- bounces as missing
        save_manifest(doc_dir, [ManifestEntry(task_id=task_id, tier="keyterms", pages=[qid], status="pending")])

        status = submit_doc(hub, hub, "run-1", doc_slug, raw_path, hub, client=object(), model_override="m")

        assert "incomplete" in status
        cache = load_json_cache(keyterms_cache_path_for(raw_path))
        assert qid not in cache
        entries = load_manifest(doc_dir)
        assert entries[0].status == "bounced"
```

Add `from core.env.gemini_utils import load_json_cache` to this test file's imports if not already present.

Run: `python -m pytest tests/agent/rag/test_resolve_questions_submit.py -k "no_manifest_does_not_crash or bounced_keyterms_card" -v`
Expected: PASS

- [ ] **Step 11: Write and pass a test for `finalize_note_answers`'s per-question resilience**

Add to `tests/agent/rag/test_resolve_questions_submit.py`:

```python
def test_finalize_note_answers_one_failing_retrieval_does_not_lose_the_other_answers():
    # Review Focus: finalize_note_answers must isolate one question's
    # retrieval failure from the rest of the note, same resilience
    # resolve_note's own sequential loop already has.
    with tempfile.TemporaryDirectory() as hub:
        notes_dir = os.path.join(hub, "academic_notes", "c", "lecture_notes", "processed_outputs")
        os.makedirs(notes_dir)
        raw_path = os.path.join(notes_dir, "N.excalidraw.md")
        body = "[Question] first one?\n\n[Question] second one?\n"
        with open(raw_path, "w", encoding="utf-8") as f:
            f.write(f"---\n---\n\n{body}")
        rag_path = raw_path.replace(".excalidraw.md", ".excalidraw.rag.md")
        with open(rag_path, "w", encoding="utf-8") as f:
            f.write(f"---\n---\n\n{body}")

        from core.indexer.questions import find_tags
        tags = find_tags(body)
        with open(answers_cache_path_for(raw_path), "w", encoding="utf-8") as f:
            import json
            json.dump({t.qid: f"answer for {t.text}" for t in tags}, f)

        call_count = {"n": 0}

        def flaky_retrieve(*a, **k):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise RuntimeError("simulated retrieval failure")
            return []

        with unittest.mock.patch(
            "agent.rag.resolve_questions_submit.retrieve_passages", side_effect=flaky_retrieve,
        ):
            from agent.rag.resolve_questions_submit import finalize_note_answers
            finalize_note_answers(raw_path, hub, client=object(), roots=[hub])

        _, entries = read_sidecar(sidecar_path_for(raw_path))
        assert len(entries) == 1  # the first question's failure was isolated; the second still resolved
        assert entries[0].question == "second one?"
```

Run: `python -m pytest tests/agent/rag/test_resolve_questions_submit.py -k one_failing_retrieval -v`
Expected: PASS

- [ ] **Step 12: Run the full new test file and commit**

Run: `python -m pytest tests/agent/rag/test_resolve_questions_submit.py -v`
Expected: all PASS

```bash
git add agent/rag/resolve_questions_submit.py tests/agent/rag/test_resolve_questions_submit.py
git commit -m "feat(agent/rag): resolve_questions_submit with cross-stage restage and finalize"
```

---

## Task 7: CLI integration (`resolve_questions.py`'s own `main()`)

**Files:**
- Modify: `agent/rag/resolve_questions.py` (`main`)
- Test: `tests/agent/rag/test_resolve_questions.py`

**Interfaces:**
- Produces: `--driver {api,agent}` (default `agent`), `--collect`, `--run-id`, `--submit RUN_ID`, `--allow-api-fallback`, `--bootstrap RUN_ID` on `resolve_questions.py`'s CLI, mirroring `transcribe_notes.py`'s flag surface.

- [ ] **Step 1: Write the failing test for the flipped default and new flags existing**

Add to `tests/agent/rag/test_resolve_questions.py`:

```python
def test_cli_default_driver_is_agent_not_api():
    parser = rq._build_arg_parser()
    parsed = parser.parse_args([])
    assert parsed.driver == "agent"
    assert parsed.allow_api_fallback is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/agent/rag/test_resolve_questions.py -k cli_default_driver_is_agent -v`
Expected: FAIL with `AttributeError: module 'agent.rag.resolve_questions' has no attribute '_build_arg_parser'`

- [ ] **Step 3: Extract `_build_arg_parser`, flip the default, add the new flags**

Replace `main`'s argparse setup (`agent/rag/resolve_questions.py:225-234`):

```python
def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Answer the [Question] tags in Excalidraw notes.")
    parser.add_argument("--root", default=_DEFAULT_ROOT, help="Corpus root (academic-hub).")
    parser.add_argument("--course", default=None)
    parser.add_argument("--note", default=None, help="Only raw transcripts whose filename contains this text.")
    parser.add_argument("--dry-run", action="store_true", help="List questions; no API calls, no writes.")
    parser.add_argument("--redo", action="store_true", help="Re-answer questions that already have an entry.")
    parser.add_argument("--model", default=RESOLVER_MODEL)
    parser.add_argument("--max-questions", type=int, default=None)
    parser.add_argument(
        "--driver", choices=["api", "agent"], default="agent",
        help="Generation transport. Default: agent (the Antigravity subscription). "
             "Use 'api' for a fully metered run.",
    )
    parser.add_argument("--collect", action="store_true",
                         help="With --driver agent: write task cards instead of resolving.")
    parser.add_argument("--run-id", default=None,
                         help="Run id for --collect/--submit's .agent_work/ directory (default: a timestamp).")
    parser.add_argument("--submit", default=None, metavar="RUN_ID",
                         help="Validate this run's filled task cards and write them through.")
    parser.add_argument(
        "--allow-api-fallback", action="store_true",
        help="With --submit: finish any still-pending/bounced cards via the metered API instead of "
             "leaving them pending. Explicit opt-in only -- never automatic.",
    )
    parser.add_argument("--bootstrap", default=None, metavar="RUN_ID",
                         help="Print the agent's operating contract for this run.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/agent/rag/test_resolve_questions.py -k cli_default_driver_is_agent -v`
Expected: PASS

- [ ] **Step 5: Add the `--bootstrap`/`--collect`/`--submit` branches to `main()`**

Replace the body of `main()` from the `args = parser.parse_args(argv)` line onward (`agent/rag/resolve_questions.py:234-276`):

```python
    if args.bootstrap:
        print(f"""Agent-driven question-resolution contract for run '{args.bootstrap}':

1. Open each note's directory under .agent_work/{args.bootstrap}/<doc-slug>/.
2. Read worklist.md to see which task cards are pending.
3. For a key-terms card: fill ONLY the "Agent output" section with one
   "--- KEYTERMS <qid> ---" section per question listed, in order, using
   exactly the qids the card lists. A comma-separated list of specific named
   terms, or nothing if none apply -- never answer the question itself here.
4. For an answers card: fill ONLY the "Agent output" section with one
   "--- ANSWER <qid> ---" section per question listed, in order. Write the
   full explanation markdown for that question.
5. Once you've filled one or more cards, run:
   python -m agent.rag.resolve_questions --submit {args.bootstrap}
6. If a card comes back marked "bounced: <reason>" in worklist.md, redo only
   that card in place and re-run step 5.
7. Stop once worklist.md shows nothing "pending"/"filled" left for this run.
   A note's key-terms card must be fully submitted before its answers card
   is staged -- submit stages the answers card automatically once that
   happens, on your next --submit call.
""")
        return 0

    if args.collect and args.driver != "agent":
        print("--collect requires --driver agent.")
        return 1
    if args.driver == "agent" and not args.collect and not args.submit:
        print("--driver agent requires --collect or --submit.")
        return 1

    hub = os.path.abspath(args.root)

    if args.collect:
        import datetime

        from agent.rag.resolve_questions_agent_work import QuestionResolverAgentDriver

        load_dotenv_override()
        client = get_gemini_client("PAID_GEMINI_KEY")
        if client is None:
            return 1
        run_id = args.run_id or datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        driver = QuestionResolverAgentDriver(hub, run_id)
        for raw_path in discover_notes(hub, args.course, args.note):
            card = _note_card(hub, raw_path)
            if card and card.get("subset_of"):
                continue
            try:
                resolve_note(raw_path, hub, client, [hub], model=args.model, redo=args.redo,
                             driver=driver, collect_mode=True)
            except Exception as err:
                from pipelines.transcribe_notes.agent_driver import AgentPending

                if isinstance(err, AgentPending):
                    print(f"[{os.path.basename(raw_path)}] collected")
                else:
                    print(f"ERROR: {raw_path} failed: {err}")
        print(f"Collect run '{run_id}' complete under {os.path.join(hub, '.agent_work', run_id)}.")
        return 0

    if args.submit:
        from core.indexer.index_card import compute_file_id
        from pipelines.transcribe_notes.agent_work import agent_work_dir, doc_slug_for
        from agent.rag.resolve_questions_submit import submit_doc

        load_dotenv_override()
        client = get_gemini_client("PAID_GEMINI_KEY")
        if client is None:
            return 1
        run_dir = agent_work_dir(hub, args.submit)
        if not os.path.isdir(run_dir):
            print(f"No .agent_work run directory found for run '{args.submit}' at {run_dir}.")
            return 1

        notes_by_slug = {
            doc_slug_for(raw_path, compute_file_id(raw_path)): raw_path
            for raw_path in discover_notes(hub, args.course, args.note)
        }
        failed = []
        for doc_slug in sorted(os.listdir(run_dir)):
            raw_path = notes_by_slug.get(doc_slug)
            if raw_path is None:
                print(f"WARNING: no matching pending note for collected doc '{doc_slug}' "
                      f"(already submitted, or outside this --course/--note filter?) -- skipping.")
                continue
            try:
                status = submit_doc(
                    hub, hub, args.submit, doc_slug, raw_path, hub, client, args.model,
                    allow_api_fallback=args.allow_api_fallback,
                )
            except Exception as err:
                print(f"[{doc_slug}] error: {err}")
                failed.append(doc_slug)
                continue
            print(f"[{doc_slug}] {status}")
        return 1 if failed else 0

    jobs = []
    for raw_path in discover_notes(hub, args.course, args.note):
        card = _note_card(hub, raw_path)
        if card and card.get("subset_of"):
            print(f"skip (subset of another note): {os.path.basename(raw_path)}")
            continue
        answered = {e.qid for e in read_sidecar(sidecar_path_for(raw_path))[1]}
        pending = [t for t in find_tags(_read_body(raw_path)) if args.redo or t.qid not in answered]
        jobs.append((raw_path, pending))

    total = sum(len(p) for _, p in jobs)
    print(f"{len(jobs)} note(s) with [Question] tags, {total} question(s) to resolve")
    if args.dry_run:
        for raw_path, pending in jobs:
            print(f"  {os.path.basename(raw_path)}")
            for tag in pending:
                print(f"    {tag.qid}: {tag.text}")
        return 0
    if total == 0:
        return 0

    load_dotenv_override()
    client = get_gemini_client("PAID_GEMINI_KEY")
    if client is None:
        return 1
    remaining = args.max_questions
    failed = []
    for raw_path, _pending in jobs:
        if remaining is not None and remaining <= 0:
            print("stopping: --max-questions budget used")
            break
        print(f"Resolving {os.path.basename(raw_path)}...")
        result = resolve_note(
            raw_path, hub, client, [hub], model=args.model, redo=args.redo, budget=remaining,
        )
        failed.extend(result.failed)
        if remaining is not None:
            remaining -= result.resolved
    print(f"done; failed: {failed or 'none'}")
    return 1 if failed else 0
```

- [ ] **Step 6: Run the full existing CLI test suite and fix fallout**

Run: `python -m pytest tests/agent/rag/test_resolve_questions.py -v`
Expected: the four existing `test_cli_*` tests (`test_cli_dry_run_lists_questions_without_any_api_call`, `test_cli_skips_notes_that_are_a_subset_of_another`, `test_cli_full_run_returns_zero_and_nonzero_on_failure`, `test_cli_max_questions_stops_after_the_budget`) now FAIL, because none of them pass `--driver` and the default is now `"agent"`, which Step 5's new guard rejects without `--collect`/`--submit`. Fix each by adding `"--driver", "api"` to its `rq.main([...])` argument list (e.g. `rq.main(["--root", hub, "--dry-run", "--driver", "api"])`), same fix pattern Stage 2 used for the PDF and Excalidraw CLIs' own default-flip fallout.

- [ ] **Step 7: Write and pass the Review Focus test for an orphaned collected doc at submit time**

Add to `tests/agent/rag/test_resolve_questions.py`:

```python
def test_cli_submit_warns_and_skips_an_orphaned_collected_doc(tmp_path, capsys):
    # Review Focus: if a note's raw transcript changes between --collect and
    # --submit (e.g. a retranscription ran in between), compute_file_id
    # changes, so the doc_slug under .agent_work/<run>/ no longer matches
    # any currently-discoverable note. Must warn and skip, never crash.
    hub, raw = _hub(tmp_path)
    run_dir = os.path.join(hub, ".agent_work", "run-1", "orphaned-doc--deadbeef")
    os.makedirs(run_dir)
    with patch.object(rq, "load_dotenv_override"), patch.object(rq, "get_gemini_client", return_value=object()):
        assert rq.main(["--root", hub, "--submit", "run-1"]) == 0
    assert "no matching pending note" in capsys.readouterr().out
```

Run: `python -m pytest tests/agent/rag/test_resolve_questions.py -k submit_warns_and_skips_an_orphaned -v`
Expected: PASS

- [ ] **Step 8: Run the full test file one more time and commit**

Run: `python -m pytest tests/agent/rag/test_resolve_questions.py -v`
Expected: all PASS

```bash
git add agent/rag/resolve_questions.py tests/agent/rag/test_resolve_questions.py
git commit -m "feat(agent/rag): resolve_questions.py CLI wires the question-resolver agent driver, flips default to agent"
```

---

## Final verification

- [ ] Run the entire package's agent/rag test suite: `python -m pytest tests/agent/rag/ -v` — expect all PASS.
- [ ] Run the whole `academic-rag-model` suite once: `python -m pytest tests/ -q` — confirm nothing outside `agent/rag/` regressed (the only shared code touched is `pipelines.transcribe_notes.agent_work`'s primitives, read-only reused, never modified).
- [ ] Run a real-corpus dry run before any non-dry-run use: `python -m agent.rag.resolve_questions --dry-run` — confirm it lists pending questions without any API call.
- [ ] Update the spec's "Status" line from "draft, not yet implemented" to reflect this plan's landing, as a final doc-only commit, same convention the Excalidraw stage used.

