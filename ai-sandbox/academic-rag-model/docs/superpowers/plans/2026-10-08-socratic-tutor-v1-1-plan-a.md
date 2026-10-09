# Socratic Tutor v1.1 — Plan A (Core) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the v1 tutor's lexical-lint-only gate with a claim ledger: prep authors claims, routes, pitfalls and recognizers; the CLI marks claims established from the student's own words, rejects tutor drafts that introduce unreached claims, releases a part's solution once for a quoted step check (`verify`), and takes 2 tool calls per turn (`turn`, `say`).

**Architecture:** Same stateless design as v1: every command replays `events.jsonl` through the pure FSM, now plus a deterministic ledger built by running prep-authored recognizers over the student's messages. New modules `claims.py` (vocabulary, schema, self-test) and `ledger.py`; `session.py` and `cli.py` are rewritten around `turn` / `say` / `verify`; ratings default to the evidence ceiling with CLI-attached evidence. No model call at runtime.

**Tech Stack:** Python 3.13 stdlib only; `unittest.TestCase` tests run by pytest, like the rest of `agent/tutor`.

**Spec:** `docs/superpowers/specs/2026-10-08-socratic-tutor-v1-1-design.md` (commit `24b99b1`); it amends `2026-10-08-socratic-tutor-pipeline-design.md`. Plan A implements spec §3-§7, §9 (ratings only), §11 and the Plan A half of §14. Skip/defer/revisit/pause/profile v2 and their audit checks are **Plan B** (not here).

## Spec elaborations decided while planning (applied to the spec in Task 12)

1. **Recognizer entries match whole tokens unless they end with `*`, which makes them a prefix.** Spec §3 said "stems", but `not` would then match `notice`, `add` would match `address`, `sum` would match `summary`. Text is lowercased; `n't` becomes ` not`; punctuation and math symbols are dropped.
2. **A pitfall may carry `resolved_by` (a claim id).** When that claim is established, the pitfall's misconception is resolved automatically (event `misconception_resolved`, `auto: true`). Otherwise the agent resolves it with `turn --resolve TAG --resolve-quote Q`.
3. **`verify` is two-phase:** `verify` (no file) releases the part's solution steps once; `verify --check-file F` submits the step check. Steps are markdown headings of level 3 or deeper inside the part's solution section, or paragraphs if there are none.
4. **`launch_style` is a per-part field** (`"label"` default, or `"statement"`).
5. **`sealed/hints.md` is optional reference only.** The packet hash covers `parts.json`, `glossary.json`, `rubric.json`, `claims.json`, `samples.json` and `sealed/solution.md`.
6. **Disclosure ignores copied problem text:** 6-word runs of the draft that also occur in the part statement are masked before claim recognizers run, so the tutor can quote the problem.
7. **Manual actions each have their own quote flag:** `--establish C --establish-quote Q`, `--flag-slip TAG[:axis] --slip-quote Q`, `--resolve TAG --resolve-quote Q`. Every quote must appear in the part's student messages.
8. **At hint level 3 the next unestablished claim is exempt from the disclosure check;** every other unestablished claim stays blocked.
9. `turn`'s brief omits the spec's skip/revisit fields until Plan B.

## Global Constraints

- No paid or local model call anywhere in `agent/tutor/` at runtime; Python stdlib only; no new dependencies.
- Chat-facing text uses Unicode math; LaTeX only in vault markdown files (v1 spec §4).
- Hint levels 0-3, raised only by an explicit student `stuck`/`hint_request`; level 3 requires two failed attempts at level 2, where a failed attempt is an `attempt` turn that establishes no new claim.
- Ratings are exactly `Mastered`, `Proficient`, `Developing / Needs Review`; axes `conceptual`, `rigor`, `directness`. Ratings default to the evidence ceiling; the agent can only lower them.
- The event log is append-only JSONL and the single source of truth; no state file.
- Claim texts reach the agent only at hint level 3 (next claim) and in `verify`'s released steps; `say` rejections name a claim id, never its text.
- No control may rely on agent self-attestation (spec §2).
- Tests live in `tests/agent/tutor/test_tutor_<module>.py` (unique basenames; `tests/` has no `__init__.py`), use `unittest.TestCase` + `tempfile`, and never touch the live vault.
- Work happens in a dedicated worktree on branch `claude/tutor-v1-1-core`; stage explicit paths only (never `git add -A` / `git add .`); append the session's attribution trailer to every commit.
- Run Python with the main checkout's venv. In every command block: `$PY = "C:\Users\theaa\ai-sandbox-master\ai-sandbox\academic-rag-model\.venv\Scripts\python.exe"` and the working directory is `C:\Users\theaa\ai-sandbox-master\.worktrees\claude-tutor-v1-1-core\ai-sandbox\academic-rag-model`.
- Edits to existing files: if the Edit tool fails on a line-ending mismatch (CRLF on disk), use a small Python replace script that normalizes `\r\n` to `\n`, replaces, and writes back with the original line ending.

## Review Focus

Input classes the spec implies but happy-path tests do not exercise; each has a pinning test in the task named in brackets.

1. **Contractions, Unicode and LaTeX in student text** (`wouldn't`, `γ(b)`, `≽`, `$x$`): tokenization must not crash or mangle, and `n't` must count as negation. [Task 1]
2. **The tutor quoting the problem statement**: a draft that copies a 6-word run of the statement must not be rejected as revealing a claim just because the statement itself contains the claim's words. [Task 6]
3. **`verify` misuse**: called before coverage, called twice, check file with a quote from the wrong part or a fabricated quote, wrong step count: each must be refused with nothing re-released and nothing closed. [Task 8]
4. **Resuming mid-part** after the CLI exits with some claims established (recognized and manual): the ledger and brief must be identical after reload. [Task 8]
5. **A v1 packet** (no `claims.json`, stale hash) and **edits to `claims.json`/`samples.json` after validation**: `start` must refuse with a message that says what to do. [Task 4]

---

## File Structure

```
agent/tutor/
  claims.py          NEW  tokenizer, Recognizer, claims schema, samples self-test
  ledger.py          NEW  build_ledger / next_claim from recognizers + events
  packet.py          MOD  claims.json/samples.json in the hash and validation; launch_style; read_solution
  sample_packet.py   MOD  sample claims + samples
  prep.py            MOD  skeleton claims/samples, new worklist
  fsm.py             MOD  closed parts stay closed; failed attempts; verify event
  lint.py            MOD  disclosure (REVEALS_CLAIM) and question form (QUESTION_FORM)
  ratings.py         MOD  build_ratings with CLI-attached evidence (replaces validate_close_part)
  render.py          MOD  verified steps in the summary
  session.py         REWRITE  turn / say / verify
  audit.py           MOD  manual overrides, verify coverage
  cli.py             REWRITE  turn, say --stdin/--check, verify; actionable errors
  bootstrap_prompt.md REWRITE
tests/agent/tutor/
  test_tutor_claims.py (new)  test_tutor_ledger.py (new)  test_tutor_packet.py (mod)  test_tutor_prep.py (mod)
  test_tutor_fsm.py (rewrite)  test_tutor_lint.py (mod)  test_tutor_ratings.py (rewrite)  test_tutor_render_profile.py (mod)
  test_tutor_session.py (rewrite)  test_tutor_audit.py (rewrite)  test_tutor_cli.py (rewrite)  test_tutor_regression.py (rewrite)
```

New event types: `establish`, `verify_release`, `verify`, `defect`. `student` events gain `data.made_progress` and `data.established`; `misconception` events gain `data.pitfall` / `data.manual` / `data.defect`; `misconception_resolved` gains `data.auto` / `data.manual`. `close_part` is unchanged (written by a clean `verify`), so render and profile need no change except the verified-steps list.

---

### Task 0: Worktree and baseline

**Files:** none

- [ ] **Step 1: Create the worktree from the repo root**

```powershell
Set-Location C:\Users\theaa\ai-sandbox-master
git status --short
git worktree list
git check-ignore .worktrees/probe
$taskBase = git rev-parse main
git worktree add -b claude/tutor-v1-1-core .worktrees/claude-tutor-v1-1-core $taskBase
```

Expected: `.worktrees/probe` printed by `check-ignore`; the worktree is added. Open the agent session in that worktree.

- [ ] **Step 2: Baseline**

```powershell
Set-Location C:\Users\theaa\ai-sandbox-master\.worktrees\claude-tutor-v1-1-core\ai-sandbox\academic-rag-model
git branch --show-current
$PY = "C:\Users\theaa\ai-sandbox-master\ai-sandbox\academic-rag-model\.venv\Scripts\python.exe"
& $PY -m pytest tests/agent/tutor -q
```

Expected: branch `claude/tutor-v1-1-core`; 100 tests pass.

---

### Task 1: Tokenizer and Recognizer

**Files:**
- Create: `agent/tutor/claims.py`
- Test: `tests/agent/tutor/test_tutor_claims.py`

**Interfaces:**
- Produces: `ClaimsError(ValueError)`; `tokenize(text) -> list[str]`; frozen dataclass `Recognizer(groups: tuple[tuple[str, ...], ...], window: int)` with `.matches(text) -> bool` and `.matches_tokens(tokens) -> bool`; `parse_recognizer(raw, where="recognizer") -> Recognizer`.
- Recognizer JSON: `{"all": [[entry, ...], ...], "window": N}`; an entry ending in `*` is a prefix, any other entry matches a whole token.

- [ ] **Step 1: Write the failing test**

```python
# tests/agent/tutor/test_tutor_claims.py
import unittest

from agent.tutor.claims import ClaimsError, parse_recognizer, tokenize


class TestTokenize(unittest.TestCase):
    def test_lowercases_and_drops_punctuation_and_math_symbols(self):
        self.assertEqual(tokenize("Let γ(b) ≻ a, then p(a, A)!"),
                         ["let", "γ", "b", "a", "then", "p", "a", "a"])

    def test_contractions_become_negation(self):
        self.assertEqual(tokenize("It wouldn't work, can't stop"), ["it", "would", "not", "work", "ca", "not", "stop"])
        self.assertEqual(tokenize("isn’t"), ["is", "not"])  # curly apostrophe

    def test_latex_and_empty_input_do_not_crash(self):
        self.assertEqual(tokenize("$x \\succeq y$"), ["x", "succeq", "y"])
        self.assertEqual(tokenize(""), [])
        self.assertEqual(tokenize("   ...  "), [])


def rec(groups, window=8):
    return parse_recognizer({"all": groups, "window": window})


class TestRecognizerMatching(unittest.TestCase):
    def test_every_group_must_be_present(self):
        r = rec([["consider*"], ["chosen", "best"]])
        self.assertTrue(r.matches("a must be considered to be chosen"))
        self.assertFalse(r.matches("a must be chosen"))
        self.assertFalse(r.matches("a must be considered"))

    def test_prefix_entries_and_case(self):
        r = rec([["consider*"], ["chosen", "best"]])
        self.assertTrue(r.matches("Consideration comes first and then the BEST item"))

    def test_plain_entries_match_whole_tokens_only(self):
        r = rec([["not"], ["consider*"]])
        self.assertFalse(r.matches("notice the considered item"))   # 'notice' is not 'not'
        self.assertTrue(r.matches("it is not considered"))
        self.assertTrue(r.matches("it isn't considered"))           # n't -> not

    def test_window_limits_the_distance(self):
        r = rec([["alpha"], ["omega"]], window=3)
        self.assertTrue(r.matches("alpha x omega"))
        self.assertFalse(r.matches("alpha x y omega"))

    def test_one_token_can_satisfy_two_groups(self):
        r = rec([["unconsidered"], ["unconsidered", "ignored"]])
        self.assertTrue(r.matches("the item stays unconsidered"))

    def test_empty_text_never_matches(self):
        self.assertFalse(rec([["a"]]).matches(""))


class TestParseRecognizer(unittest.TestCase):
    def test_rejects_bad_shapes(self):
        bad = [
            None, [], {"all": [["a"]]}, {"window": 5}, {"all": [], "window": 5},
            {"all": [[]], "window": 5}, {"all": [["a"]], "window": 1}, {"all": [["a"]], "window": True},
            {"all": [["a", 3]], "window": 5}, {"all": [["a"]], "window": 5, "extra": 1}, {"all": ["a"], "window": 5},
        ]
        for raw in bad:
            with self.subTest(raw=raw):
                with self.assertRaises(ClaimsError):
                    parse_recognizer(raw)

    def test_error_names_where(self):
        with self.assertRaises(ClaimsError) as ctx:
            parse_recognizer({"all": [], "window": 5}, "q1.claims[0].recognizer")
        self.assertIn("q1.claims[0].recognizer", str(ctx.exception))

    def test_entries_are_lowercased_and_stripped(self):
        r = parse_recognizer({"all": [[" Consider* "]], "window": 4})
        self.assertEqual(r.groups, (("consider*",),))
```

- [ ] **Step 2: Run to verify it fails**

Run: `& $PY -m pytest tests/agent/tutor/test_tutor_claims.py -q`
Expected: FAIL `ModuleNotFoundError: No module named 'agent.tutor.claims'`.

- [ ] **Step 3: Implement**

```python
# agent/tutor/claims.py
"""claims.py -- vocabulary of the v1.1 claim ledger (spec §3): the tokenizer,
the group-window Recognizer, the claims.json schema and the samples self-test.
Recognizers are prep-authored and deterministic: no regex, no model call."""
from __future__ import annotations

import bisect
import re
from dataclasses import dataclass

AXES_ALL = ("conceptual", "rigor", "directness", "all")
_TOKEN = re.compile(r"[^\W_]+", re.UNICODE)


class ClaimsError(ValueError):
    pass


def tokenize(text: str) -> list[str]:
    t = text.lower().replace("’", "'")
    t = re.sub(r"n't\b", " not", t)
    return _TOKEN.findall(t)


def _group_hits(tokens: list[str], group: tuple[str, ...]) -> list[int]:
    exact = {g for g in group if not g.endswith("*")}
    prefixes = tuple(g[:-1] for g in group if g.endswith("*") and len(g) > 1)
    return [i for i, tok in enumerate(tokens)
            if tok in exact or (prefixes and tok.startswith(prefixes))]


@dataclass(frozen=True)
class Recognizer:
    groups: tuple
    window: int

    def matches_tokens(self, tokens: list[str]) -> bool:
        positions = [_group_hits(tokens, g) for g in self.groups]
        if any(not p for p in positions):
            return False
        for start in range(max(1, len(tokens) - self.window + 1)):
            end = start + self.window
            ok = True
            for p in positions:
                i = bisect.bisect_left(p, start)
                if i >= len(p) or p[i] >= end:
                    ok = False
                    break
            if ok:
                return True
        return False

    def matches(self, text: str) -> bool:
        return self.matches_tokens(tokenize(text))


def parse_recognizer(raw, where: str = "recognizer") -> Recognizer:
    if not isinstance(raw, dict) or set(raw) - {"all", "window"}:
        raise ClaimsError(f"{where}: must be an object with only 'all' and 'window'")
    groups, window = raw.get("all"), raw.get("window")
    if not isinstance(groups, list) or not groups:
        raise ClaimsError(f"{where}: 'all' must be a non-empty list of groups")
    parsed = []
    for g in groups:
        if not isinstance(g, list) or not g or not all(isinstance(x, str) and x.strip() for x in g):
            raise ClaimsError(f"{where}: each group must be a non-empty list of non-empty strings")
        parsed.append(tuple(x.strip().lower() for x in g))
    if not isinstance(window, int) or isinstance(window, bool) or window < 2:
        raise ClaimsError(f"{where}: 'window' must be an integer of at least 2")
    return Recognizer(tuple(parsed), window)
```

- [ ] **Step 4: Run to verify it passes**

Run: `& $PY -m pytest tests/agent/tutor/test_tutor_claims.py -q`
Expected: all passed.

- [ ] **Step 5: Commit**

```powershell
git add agent/tutor/claims.py tests/agent/tutor/test_tutor_claims.py
git commit -m "feat(tutor): claim recognizer with whole-token and prefix matching"
```

---

### Task 2: Claims schema and samples self-test

**Files:**
- Modify: `agent/tutor/claims.py` (append)
- Test: `tests/agent/tutor/test_tutor_claims.py` (append)

**Interfaces:**
- Consumes: `Recognizer`, `parse_recognizer`.
- Produces: frozen dataclasses `Claim(id, text, object_terms: tuple[str, ...], recognizer)`, `Pitfall(id, tag, axis, recognizer, repair_question, resolved_by: str | None)`, `PartClaims(claims: tuple[Claim, ...], routes: dict[str, list[str]], pitfalls: tuple[Pitfall, ...], final_answer: Recognizer | None)`; `parse_claims(raw, part_ids) -> (dict[str, PartClaims], list[str])` (errors, never raises); `self_test(claims, samples) -> list[str]`; constants `MIN_LEAK=10, MIN_STUDENT=5, MIN_NEUTRAL=5, MIN_PITFALL=3, LEAK_RECALL=0.9, STUDENT_RECALL=0.8`.
- `claims.json` per part: `{"claims": [{id, text, object_terms, recognizer}], "routes": {name: [claim ids]}, "pitfalls": [{id, tag, axis, recognizer, repair_question, resolved_by?}], "final_answer": recognizer?}`.
- `samples.json` per part: `{"claims": {claim_id: {"leak_samples": [...], "student_samples": [...]}}, "pitfalls": {pitfall_id: {"student_samples": [...]}}, "neutral_samples": [...]}`.

- [ ] **Step 1: Write the failing test (append to `test_tutor_claims.py`)**

```python
from agent.tutor.claims import (
    LEAK_RECALL, MIN_LEAK, PartClaims, parse_claims, self_test,
)

RAW = {"p1": {
    "claims": [
        {"id": "C1", "text": "a must be considered", "object_terms": ["the chosen item"],
         "recognizer": {"all": [["consider*"], ["chosen", "select*", "best"]], "window": 12}},
        {"id": "C2", "text": "independence gives a product", "object_terms": ["combining probabilities"],
         "recognizer": {"all": [["independen*"], ["multipl*", "product", "together"]], "window": 12}}],
    "routes": {"A": ["C1", "C2"]},
    "pitfalls": [{"id": "P1", "tag": "adds-independent-probabilities", "axis": "rigor", "resolved_by": "C2",
                  "recognizer": {"all": [["independen*"], ["add", "sum", "plus"]], "window": 12},
                  "repair_question": "Does combining add or multiply?"}]}}


def deepcopy_raw():
    import copy
    return copy.deepcopy(RAW)


class TestParseClaims(unittest.TestCase):
    def test_valid_claims_parse(self):
        claims, errors = parse_claims(RAW, ["p1"])
        self.assertEqual(errors, [])
        pc = claims["p1"]
        self.assertIsInstance(pc, PartClaims)
        self.assertEqual([c.id for c in pc.claims], ["C1", "C2"])
        self.assertEqual(pc.routes, {"A": ["C1", "C2"]})
        self.assertEqual(pc.pitfalls[0].resolved_by, "C2")
        self.assertIsNone(pc.final_answer)

    def test_each_defect_is_reported(self):
        def errors_for(mutate):
            raw = deepcopy_raw()
            mutate(raw["p1"])
            return "\n".join(parse_claims(raw, ["p1"])[1])
        self.assertIn("duplicate claim id", errors_for(lambda p: p["claims"][1].update(id="C1")))
        self.assertIn("routes", errors_for(lambda p: p["routes"].update(A=["C1", "C9"])))
        self.assertIn("'text'", errors_for(lambda p: p["claims"][0].update(text="")))
        self.assertIn("axis", errors_for(lambda p: p["pitfalls"][0].update(axis="style")))
        self.assertIn("resolved_by", errors_for(lambda p: p["pitfalls"][0].update(resolved_by="C9")))
        self.assertIn("repair_question", errors_for(lambda p: p["pitfalls"][0].update(repair_question="")))
        self.assertIn("recognizer", errors_for(lambda p: p["claims"][0].update(recognizer={"all": [], "window": 5})))
        self.assertIn("non-empty list", errors_for(lambda p: p.update(claims=[])))

    def test_missing_and_unknown_parts(self):
        _, errors = parse_claims(RAW, ["p1", "p2"])
        self.assertTrue(any("no entry for part p2" in e for e in errors))
        _, errors = parse_claims({**RAW, "zz": RAW["p1"]}, ["p1"])
        self.assertTrue(any("unknown part zz" in e for e in errors))
        _, errors = parse_claims([], ["p1"])
        self.assertTrue(errors)

    def test_final_answer_is_optional_and_parsed(self):
        raw = deepcopy_raw()
        raw["p1"]["final_answer"] = {"all": [["answer"]], "window": 4}
        claims, errors = parse_claims(raw, ["p1"])
        self.assertEqual(errors, [])
        self.assertTrue(claims["p1"].final_answer.matches("the answer is 3"))


PREFIXES = ["Remember that", "Keep in mind that", "It turns out that", "You should see that", "Here is the thing:"]


def good_samples():
    c1 = [f"{p} the item must be considered to be chosen" for p in PREFIXES] + \
         [f"{p} being selected requires the item enters the consideration set" for p in PREFIXES]
    c2 = [f"{p} independent events combine by multiplication" for p in PREFIXES] + \
         [f"{p} independence means the joint probability is a product" for p in PREFIXES]
    return {"p1": {
        "claims": {
            "C1": {"leak_samples": c1, "student_samples": [
                "it has to be considered and chosen", "the item must be considered then selected",
                "a needs to be considered to be the best", "it is chosen only if considered",
                "consideration comes first, then the best is selected"]},
            "C2": {"leak_samples": c2, "student_samples": [
                "since they are independent I multiply", "independence lets us take the product",
                "multiplying the independent probabilities", "the product follows from independence",
                "independent so we multiply them together"]}},
        "pitfalls": {"P1": {"student_samples": [
            "for independent events we add them", "independent so I sum the probabilities",
            "we add the independent probabilities"]}},
        "neutral_samples": ["What have you tried so far?", "Which part of the model feels least clear?",
                            "How would you say the setup in your own words?", "What does the problem ask you to show?",
                            "Which assumption have you not used yet?", "What would a simple example look like?"]}}


class TestSelfTest(unittest.TestCase):
    def setUp(self):
        self.claims, _ = parse_claims(RAW, ["p1"])

    def test_good_samples_pass(self):
        self.assertEqual(self_test(self.claims, good_samples()), [])

    def test_missing_part_and_too_few_samples_are_reported(self):
        self.assertTrue(any("no entry for p1" in e for e in self_test(self.claims, {})))
        s = good_samples()
        s["p1"]["claims"]["C1"]["leak_samples"] = s["p1"]["claims"]["C1"]["leak_samples"][:3]
        self.assertTrue(any("C1" in e and str(MIN_LEAK) in e for e in self_test(self.claims, s)))

    def test_low_leak_recall_names_the_unmatched_sample(self):
        s = good_samples()
        s["p1"]["claims"]["C1"]["leak_samples"] = [
            f"{p} the item has to enter the aware set" for p in PREFIXES] * 2   # no recognizer words
        errors = "\n".join(self_test(self.claims, s))
        self.assertIn("C1", errors)
        self.assertIn("leak", errors)
        self.assertIn("aware set", errors)
        self.assertGreater(LEAK_RECALL, 0.5)

    def test_neutral_sample_that_matches_a_recognizer_is_reported(self):
        s = good_samples()
        s["p1"]["neutral_samples"][0] = "Is the item considered and then chosen?"
        errors = "\n".join(self_test(self.claims, s))
        self.assertIn("neutral sample matches claim C1", errors)

    def test_pitfall_recall_is_checked(self):
        s = good_samples()
        s["p1"]["pitfalls"]["P1"]["student_samples"] = ["we do something else", "no idea", "unrelated words"]
        self.assertTrue(any("pitfall P1" in e for e in self_test(self.claims, s)))
```

- [ ] **Step 2: Run to verify it fails**

Run: `& $PY -m pytest tests/agent/tutor/test_tutor_claims.py -q`
Expected: FAIL `ImportError: cannot import name 'LEAK_RECALL'`.

- [ ] **Step 3: Implement (append to `agent/tutor/claims.py`)**

```python
MIN_LEAK, MIN_STUDENT, MIN_NEUTRAL, MIN_PITFALL = 10, 5, 5, 3
LEAK_RECALL, STUDENT_RECALL = 0.9, 0.8


@dataclass(frozen=True)
class Claim:
    id: str
    text: str
    object_terms: tuple
    recognizer: Recognizer


@dataclass(frozen=True)
class Pitfall:
    id: str
    tag: str
    axis: str
    recognizer: Recognizer
    repair_question: str
    resolved_by: str | None


@dataclass(frozen=True)
class PartClaims:
    claims: tuple
    routes: dict
    pitfalls: tuple
    final_answer: Recognizer | None


def _req_str(d: dict, key: str, where: str) -> str:
    v = d.get(key)
    if not isinstance(v, str) or not v.strip():
        raise ClaimsError(f"{where}: '{key}' must be a non-empty string")
    return v.strip()


def _parse_part(pid: str, raw) -> PartClaims:
    if not isinstance(raw, dict):
        raise ClaimsError(f"{pid}: must be an object")
    claims_raw = raw.get("claims")
    if not isinstance(claims_raw, list) or not claims_raw:
        raise ClaimsError(f"{pid}: 'claims' must be a non-empty list")
    claims, ids = [], []
    for i, c in enumerate(claims_raw):
        w = f"{pid}.claims[{i}]"
        if not isinstance(c, dict):
            raise ClaimsError(f"{w}: must be an object")
        cid = _req_str(c, "id", w)
        if cid in ids:
            raise ClaimsError(f"{w}: duplicate claim id {cid!r}")
        terms = c.get("object_terms", [])
        if not isinstance(terms, list) or not all(isinstance(t, str) for t in terms):
            raise ClaimsError(f"{w}: 'object_terms' must be a list of strings")
        claims.append(Claim(cid, _req_str(c, "text", w), tuple(terms),
                            parse_recognizer(c.get("recognizer"), f"{w}.recognizer")))
        ids.append(cid)
    routes_raw = raw.get("routes")
    if not isinstance(routes_raw, dict) or not routes_raw:
        raise ClaimsError(f"{pid}: 'routes' must be a non-empty object")
    routes = {}
    for name, seq in routes_raw.items():
        if not isinstance(seq, list) or not seq or any(x not in ids for x in seq):
            raise ClaimsError(f"{pid}: routes[{name!r}] must list known claim ids")
        routes[name] = list(seq)
    pitfalls, tags = [], []
    for i, p in enumerate(raw.get("pitfalls", [])):
        w = f"{pid}.pitfalls[{i}]"
        if not isinstance(p, dict):
            raise ClaimsError(f"{w}: must be an object")
        tag = _req_str(p, "tag", w)
        if tag in tags:
            raise ClaimsError(f"{w}: duplicate tag {tag!r}")
        axis = p.get("axis")
        if axis not in AXES_ALL:
            raise ClaimsError(f"{w}: axis must be one of {list(AXES_ALL)}")
        resolved_by = p.get("resolved_by")
        if resolved_by is not None and resolved_by not in ids:
            raise ClaimsError(f"{w}: resolved_by must be a known claim id")
        pitfalls.append(Pitfall(_req_str(p, "id", w), tag, axis,
                                parse_recognizer(p.get("recognizer"), f"{w}.recognizer"),
                                _req_str(p, "repair_question", w), resolved_by))
        tags.append(tag)
    final = raw.get("final_answer")
    final_rec = parse_recognizer(final, f"{pid}.final_answer") if final is not None else None
    return PartClaims(tuple(claims), routes, tuple(pitfalls), final_rec)


def parse_claims(raw, part_ids: list[str]) -> tuple[dict, list[str]]:
    if not isinstance(raw, dict):
        return {}, ["claims.json must be an object keyed by part id"]
    errors, out = [], {}
    for pid in part_ids:
        if pid not in raw:
            errors.append(f"claims.json has no entry for part {pid}")
            continue
        try:
            out[pid] = _parse_part(pid, raw[pid])
        except ClaimsError as err:
            errors.append(str(err))
    for pid in raw:
        if pid not in part_ids:
            errors.append(f"claims.json has an entry for unknown part {pid}")
    return out, errors


def _unmatched(rec: Recognizer, samples: list) -> list[str]:
    return [s for s in samples if not rec.matches(s)]


def self_test(claims: dict, samples) -> list[str]:
    errors: list[str] = []
    samples = samples if isinstance(samples, dict) else {}
    for pid, pc in claims.items():
        ps = samples.get(pid)
        if not isinstance(ps, dict):
            errors.append(f"samples.json has no entry for {pid}")
            continue
        neutral = ps.get("neutral_samples", [])
        if len(neutral) < MIN_NEUTRAL:
            errors.append(f"{pid}: needs at least {MIN_NEUTRAL} neutral_samples")
        recs = [(f"claim {c.id}", c.recognizer) for c in pc.claims] + \
               [(f"pitfall {p.id}", p.recognizer) for p in pc.pitfalls]
        for sample in neutral:
            for label, rec in recs:
                if rec.matches(sample):
                    errors.append(f"{pid}: neutral sample matches {label}: {sample[:70]!r}")
        for c in pc.claims:
            cs = ps.get("claims", {}).get(c.id, {})
            for key, minimum, ratio in (("leak_samples", MIN_LEAK, LEAK_RECALL), ("student_samples", MIN_STUDENT, STUDENT_RECALL)):
                got = cs.get(key, [])
                if len(got) < minimum:
                    errors.append(f"{pid}.{c.id}: needs at least {minimum} {key} (has {len(got)})")
                    continue
                missed = _unmatched(c.recognizer, got)
                if (len(got) - len(missed)) / len(got) < ratio:
                    kind = "leak" if key == "leak_samples" else "student"
                    errors.append(f"{pid}.{c.id}: recognizer matches only {len(got) - len(missed)}/{len(got)} {kind} samples "
                                  f"(needs {int(ratio * 100)}%); unmatched e.g. {missed[0][:70]!r}")
        for p in pc.pitfalls:
            got = ps.get("pitfalls", {}).get(p.id, {}).get("student_samples", [])
            if len(got) < MIN_PITFALL:
                errors.append(f"{pid}.{p.id}: pitfall needs at least {MIN_PITFALL} student_samples")
                continue
            missed = _unmatched(p.recognizer, got)
            if (len(got) - len(missed)) / len(got) < STUDENT_RECALL:
                errors.append(f"{pid}: pitfall {p.id} recognizer matches only {len(got) - len(missed)}/{len(got)} "
                              f"student samples; unmatched e.g. {missed[0][:70]!r}")
    return errors
```

- [ ] **Step 4: Run to verify it passes**

Run: `& $PY -m pytest tests/agent/tutor/test_tutor_claims.py -q`
Expected: all passed.

- [ ] **Step 5: Commit**

```powershell
git add agent/tutor/claims.py tests/agent/tutor/test_tutor_claims.py
git commit -m "feat(tutor): claims.json schema and blind-samples self-test"
```

---

### Task 3: Ledger

**Files:**
- Create: `agent/tutor/ledger.py`
- Test: `tests/agent/tutor/test_tutor_ledger.py`

**Interfaces:**
- Consumes: `PartClaims`, `Event`.
- Produces: dataclass `PartLedger(established: list[str], manual: list[str], pitfalls_hit: list[str], route_progress: dict[str, tuple[int, int]], covered_route: str | None, final_answer_ok: bool)` with property `covered` (route complete and final answer ok); `build_ledger(pc, part_events, extra_student_text=None) -> PartLedger`; `next_claim(pc, ledger) -> Claim | None`.
- Rules: events are processed in order; `student` events whose intent is `confirm_advance` or `define_request` (a question about a term is not a claim) are ignored, via the exported `IGNORED_INTENTS`; `establish` events add their `data["claim"]` as manual; `extra_student_text` is appended as a virtual last student message (used to ask "what would this message establish?").

- [ ] **Step 1: Write the failing test**

```python
# tests/agent/tutor/test_tutor_ledger.py
import unittest

from agent.tutor.claims import parse_claims
from agent.tutor.events import Event
from agent.tutor.ledger import build_ledger, next_claim

RAW = {"p1": {
    "claims": [
        {"id": "C1", "text": "considered", "object_terms": [],
         "recognizer": {"all": [["consider*"], ["chosen", "best"]], "window": 12}},
        {"id": "C2", "text": "others excluded", "object_terms": [],
         "recognizer": {"all": [["consider*"], ["better", "higher"], ["not", "never", "fail*"]], "window": 14}},
        {"id": "C3", "text": "product", "object_terms": [],
         "recognizer": {"all": [["independen*"], ["multipl*", "product", "together"]], "window": 12}},
        {"id": "D1", "text": "alt route claim", "object_terms": [],
         "recognizer": {"all": [["complement*"]], "window": 4}}],
    "routes": {"A": ["C1", "C2", "C3"], "B": ["C1", "D1"]},
    "pitfalls": [{"id": "P1", "tag": "adds", "axis": "rigor", "resolved_by": "C3",
                  "recognizer": {"all": [["independen*"], ["add", "sum"]], "window": 12},
                  "repair_question": "add or multiply?"}]}}
PC = parse_claims(RAW, ["p1"])[0]["p1"]


def student(i, text, intent="attempt"):
    return Event(id=i, ts="t", type="student", part="p1", intent=intent, text=text)


class TestBuildLedger(unittest.TestCase):
    def test_claims_are_established_in_event_order(self):
        events = [student(1, "a must be considered to be chosen"),
                  student(2, "higher items must not be considered")]
        led = build_ledger(PC, events)
        self.assertEqual(led.established, ["C1", "C2"])
        self.assertEqual(led.manual, [])
        self.assertEqual(led.route_progress, {"A": (2, 3), "B": (1, 2)})
        self.assertIsNone(led.covered_route)
        self.assertFalse(led.covered)

    def test_a_route_covers_the_part(self):
        events = [student(1, "considered and chosen"), student(2, "independent so multiply")]
        led = build_ledger(PC, events + [Event(id=3, ts="t", type="establish", part="p1",
                                               data={"claim": "C2", "quote": "x"})])
        self.assertEqual(led.established, ["C1", "C3", "C2"])
        self.assertEqual(led.manual, ["C2"])
        self.assertEqual(led.covered_route, "A")
        self.assertTrue(led.covered)

    def test_alternative_route_also_covers(self):
        led = build_ledger(PC, [student(1, "it is considered and chosen"), student(2, "take the complement")])
        self.assertEqual(led.covered_route, "B")

    def test_pitfalls_are_detected_once(self):
        led = build_ledger(PC, [student(1, "independent events so we add them"), student(2, "independent so I sum")])
        self.assertEqual(led.pitfalls_hit, ["P1"])

    def test_confirm_advance_define_request_and_tutor_events_are_ignored(self):
        events = [student(1, "considered and chosen", intent="confirm_advance"),
                  student(3, "what does considered mean for the chosen item", intent="define_request"),
                  Event(id=2, ts="t", type="tutor_say", part="p1", text="independent so multiply")]
        self.assertEqual(build_ledger(PC, events).established, [])

    def test_extra_student_text_is_a_virtual_last_message(self):
        led = build_ledger(PC, [], extra_student_text="considered and chosen")
        self.assertEqual(led.established, ["C1"])

    def test_final_answer_is_required_for_coverage_when_defined(self):
        raw = {"p1": {**RAW["p1"], "final_answer": {"all": [["answer"]], "window": 4}}}
        pc = parse_claims(raw, ["p1"])[0]["p1"]
        events = [student(1, "considered and chosen"), student(2, "complement")]
        self.assertFalse(build_ledger(pc, events).covered)
        self.assertTrue(build_ledger(pc, events + [student(3, "the answer is 3")]).covered)


class TestNextClaim(unittest.TestCase):
    def test_follows_the_route_with_most_progress(self):
        led = build_ledger(PC, [student(1, "considered and chosen"), student(2, "independent so multiply")])
        self.assertEqual(next_claim(PC, led).id, "C2")          # route A has 2/3, B has 1/2

    def test_ties_go_to_the_first_listed_route_and_covered_returns_none(self):
        self.assertEqual(next_claim(PC, build_ledger(PC, [])).id, "C1")
        led = build_ledger(PC, [student(1, "considered and chosen"), student(2, "complement")])
        self.assertIsNone(next_claim(PC, led))
```

- [ ] **Step 2: Run to verify it fails**

Run: `& $PY -m pytest tests/agent/tutor/test_tutor_ledger.py -q`
Expected: FAIL `ModuleNotFoundError: No module named 'agent.tutor.ledger'`.

- [ ] **Step 3: Implement**

```python
# agent/tutor/ledger.py
"""ledger.py -- which claims the student has established, which pitfalls they
hit, and whether a route is complete (spec §4). Pure functions over the event
log: the same events always give the same ledger, so a CLI restart cannot
change it."""
from __future__ import annotations

from dataclasses import dataclass

from agent.tutor.claims import Claim, PartClaims
from agent.tutor.events import Event

IGNORED_INTENTS = frozenset({"confirm_advance", "define_request"})


@dataclass
class PartLedger:
    established: list
    manual: list
    pitfalls_hit: list
    route_progress: dict
    covered_route: str | None
    final_answer_ok: bool

    @property
    def covered(self) -> bool:
        return self.covered_route is not None and self.final_answer_ok


def build_ledger(pc: PartClaims, part_events: list[Event], extra_student_text: str | None = None) -> PartLedger:
    sequence = []
    for e in part_events:
        if e.type == "student" and e.intent not in IGNORED_INTENTS:
            sequence.append(("text", e.text or ""))
        elif e.type == "establish":
            sequence.append(("claim", e.data["claim"]))
    if extra_student_text is not None:
        sequence.append(("text", extra_student_text))
    established, manual, hit = [], [], []
    final_ok = pc.final_answer is None
    for kind, value in sequence:
        if kind == "claim":
            if value not in established:
                established.append(value)
                manual.append(value)
            continue
        for c in pc.claims:
            if c.id not in established and c.recognizer.matches(value):
                established.append(c.id)
        for p in pc.pitfalls:
            if p.id not in hit and p.recognizer.matches(value):
                hit.append(p.id)
        if pc.final_answer is not None and pc.final_answer.matches(value):
            final_ok = True
    progress = {r: (sum(1 for c in ids if c in established), len(ids)) for r, ids in pc.routes.items()}
    covered = next((r for r, (n, total) in progress.items() if n == total), None)
    return PartLedger(established, manual, hit, progress, covered, final_ok)


def next_claim(pc: PartClaims, ledger: PartLedger) -> Claim | None:
    if ledger.covered_route is not None:
        return None
    best = max(pc.routes, key=lambda r: ledger.route_progress[r][0])   # max() keeps the first on ties
    by_id = {c.id: c for c in pc.claims}
    for cid in pc.routes[best]:
        if cid not in ledger.established:
            return by_id[cid]
    return None
```

- [ ] **Step 4: Run to verify it passes**

Run: `& $PY -m pytest tests/agent/tutor/test_tutor_claims.py tests/agent/tutor/test_tutor_ledger.py -q`
Expected: all passed.

- [ ] **Step 5: Commit**

```powershell
git add agent/tutor/ledger.py tests/agent/tutor/test_tutor_ledger.py
git commit -m "feat(tutor): claim ledger replay and next-claim selection"
```


---

> **Expected red between Task 4 and Task 8.** Tasks 4-7 change `packet`, `fsm`, `lint` and `ratings` under the v1 `session.py`, `cli.py` and `audit.py`, whose tests (`test_tutor_session.py`, `test_tutor_cli.py`, `test_tutor_audit.py`, `test_tutor_regression.py`) target the v1 API and are rewritten in Tasks 8-11. Until then those four files may fail; each task below names the files that must pass. The whole `tests/agent/tutor` directory must be green at the end of Task 11.

### Task 4: Packet v1.1 (claims, samples, short launch), sample fixture, prep

**Files:**
- Modify: `agent/tutor/packet.py` (replace whole file), `agent/tutor/sample_packet.py` (replace whole file), `agent/tutor/prep.py` (replace whole file)
- Test: `tests/agent/tutor/test_tutor_packet.py` (replace), `tests/agent/tutor/test_tutor_prep.py` (replace)

**Interfaces:**
- Consumes: `claims.parse_claims`, `claims.self_test`, `lint.lint_glossary`.
- Produces: `Part(part_id, statement, concept_tags, expected_evidence, label=None, chat_statement=None, launch_style="label")` with `launch_text()` = `"{label or part_id}. How would you like to approach this problem?"` for `"label"`, the v1 text for `"statement"`; `Packet(course, problem_set, parts, glossary, rubric, claims={})` where `claims: dict[str, PartClaims]`; `read_solution(packet_dir) -> str`; `validate_packet`, `compute_hash`, `write_validated`, `is_validated`, `load_packet(paths)`, `sealed_section` as in v1; `prep.collect(...)` additionally writes `claims.json` and `samples.json` as `{}`; `sample_packet.write_sample_packet(paths)` writes a fully valid v1.1 packet (parts `q1`, `q2`).
- The hash now covers `parts.json`, `glossary.json`, `rubric.json`, `claims.json`, `samples.json`, `sealed/solution.md`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/agent/tutor/test_tutor_packet.py  (replace the whole file)
import json
import os
import tempfile
import unittest

from agent.tutor.packet import (
    LAUNCH_SUFFIX, PacketError, Part, is_validated, load_packet, read_solution, sealed_section,
    validate_packet, write_validated,
)
from agent.tutor.paths import TutorPaths
from agent.tutor.sample_packet import write_sample_packet


def _paths(tmp):
    return TutorPaths(tmp, "microecon", "homework_4")


def _edit_json(paths, name, fn):
    path = os.path.join(paths.packet_dir, name)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    fn(data)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)


class TestSealedSection(unittest.TestCase):
    def test_extracts_section_by_part_id(self):
        md = "## q1\nfirst\nmore\n## q2\nsecond\n"
        self.assertEqual(sealed_section(md, "q1"), "first\nmore")
        self.assertEqual(sealed_section(md, "q2"), "second")
        self.assertIsNone(sealed_section(md, "q3"))

    def test_part_id_with_regex_characters_and_step_headings(self):
        self.assertEqual(sealed_section("## q1.2\nbody", "q1.2"), "body")
        self.assertIsNone(sealed_section("## q1x2\nbody", "q1.2"))
        self.assertEqual(sealed_section("## q1\n### Step 1\na\n### Step 2\nb\n## q2\nc", "q1"), "### Step 1\na\n### Step 2\nb")


class TestLaunchText(unittest.TestCase):
    def test_label_launch_is_short_and_statement_launch_is_v1(self):
        p = Part("q1_3", "Long statement with $x$.", ["t"], ["e"], label="Question 1.3", chat_statement="Long statement with x.")
        self.assertEqual(p.launch_text(), f"Question 1.3. {LAUNCH_SUFFIX}")
        self.assertEqual(Part("q9", "S", ["t"], ["e"]).launch_text(), f"q9. {LAUNCH_SUFFIX}")
        p.launch_style = "statement"
        self.assertEqual(p.launch_text(), f"Long statement with x.\n\n{LAUNCH_SUFFIX}")


class TestSamplePacket(unittest.TestCase):
    def test_sample_is_valid_and_loadable(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = _paths(tmp)
            write_sample_packet(paths)
            self.assertEqual(validate_packet(paths.packet_dir), [])
            packet = load_packet(paths)
            self.assertEqual([p.part_id for p in packet.parts], ["q1", "q2"])
            self.assertEqual(set(packet.claims), {"q1", "q2"})
            self.assertEqual(packet.parts[0].launch_text(), f"Question 1. {LAUNCH_SUFFIX}")
            self.assertIn("### Step 1", read_solution(paths.packet_dir))


class TestValidation(unittest.TestCase):
    def test_reports_each_kind_of_defect(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = _paths(tmp)
            write_sample_packet(paths)
            _edit_json(paths, "parts.json", lambda d: d[0].update(concept_tags=[], expected_evidence=[], launch_style="loud"))
            _edit_json(paths, "rubric.json", lambda d: d["q2"]["rigor"].pop("Mastered"))
            _edit_json(paths, "glossary.json", lambda d: d.update({"choice overload": "Means d is chosen more."}))
            _edit_json(paths, "claims.json", lambda d: d["q2"]["routes"].update(A=["C1", "C9"]))
            with open(os.path.join(paths.packet_dir, "sealed", "solution.md"), "w", encoding="utf-8") as f:
                f.write("## q1\nonly q1\n")
            errors = "\n".join(validate_packet(paths.packet_dir))
            self.assertIn("q1: concept_tags", errors)
            self.assertIn("q1: expected_evidence", errors)
            self.assertIn("q1: launch_style", errors)
            self.assertIn("rubric q2.rigor missing 'Mastered'", errors)
            self.assertIn("GLOSSARY_NOTATION", errors)
            self.assertIn("routes", errors)
            self.assertIn("sealed/solution.md has no '## q2' section", errors)

    def test_failing_self_test_blocks_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = _paths(tmp)
            write_sample_packet(paths)
            _edit_json(paths, "samples.json", lambda d: d["q1"]["neutral_samples"].append(
                "Is the sum of the probabilities one?"))
            errors = "\n".join(validate_packet(paths.packet_dir))
            self.assertIn("neutral sample matches", errors)

    def test_missing_files_reported_including_claims(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(_paths(tmp).packet_dir)
            errors = validate_packet(_paths(tmp).packet_dir)
            self.assertIn("parts.json missing", errors)
            self.assertIn("claims.json missing", errors)


class TestValidatedMarker(unittest.TestCase):
    def test_edit_after_validation_invalidates_until_resubmitted(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = _paths(tmp)
            write_sample_packet(paths)
            self.assertTrue(is_validated(paths.packet_dir))
            for name in ("claims.json", "samples.json"):
                _edit_json(paths, name, lambda d: d.update(extra={}))
                self.assertFalse(is_validated(paths.packet_dir), name)
                _edit_json(paths, name, lambda d: d.pop("extra"))
                self.assertTrue(is_validated(paths.packet_dir), name)
            sol = os.path.join(paths.packet_dir, "sealed", "solution.md")
            with open(sol, "a", encoding="utf-8") as f:
                f.write("\nhuman tweak\n")
            self.assertFalse(is_validated(paths.packet_dir))
            with self.assertRaises(PacketError) as ctx:
                load_packet(paths)
            self.assertIn("prep-submit", str(ctx.exception))
            write_validated(paths.packet_dir)
            load_packet(paths)

    def test_v1_packet_without_claims_is_refused_with_a_clear_message(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = _paths(tmp)
            write_sample_packet(paths)
            os.remove(os.path.join(paths.packet_dir, "claims.json"))
            self.assertFalse(is_validated(paths.packet_dir))
            with self.assertRaises(PacketError) as ctx:
                load_packet(paths)
            self.assertIn("claims.json", str(ctx.exception))

    def test_crlf_conversion_does_not_invalidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = _paths(tmp)
            write_sample_packet(paths)
            sol = os.path.join(paths.packet_dir, "sealed", "solution.md")
            with open(sol, "rb") as f:
                raw = f.read()
            with open(sol, "wb") as f:
                f.write(raw.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
            self.assertTrue(is_validated(paths.packet_dir))
```

```python
# tests/agent/tutor/test_tutor_prep.py  (replace the whole file)
import json
import os
import tempfile
import unittest
from types import SimpleNamespace

from agent.tutor import prep
from agent.tutor.packet import is_validated
from agent.tutor.paths import TutorPaths
from agent.tutor.sample_packet import write_sample_packet

PS = "## Question 1\nFirst question text with $d$.\n\n## Question 2\nSecond question text.\n"


def _retrieve(query):
    return [SimpleNamespace(citation="p. 3", path="notes/a.md", score=0.81, text="line one\nline two")]


def _write_ps(tmp):
    psf = os.path.join(tmp, "homework_4.md")
    with open(psf, "w", encoding="utf-8") as f:
        f.write(PS)
    return psf


class TestCollect(unittest.TestCase):
    def test_writes_skeleton_grounding_claims_and_worklist(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = TutorPaths(tmp, "microecon", "homework_4")
            psf = _write_ps(tmp)
            sol = os.path.join(tmp, "solutions.md")
            with open(sol, "w", encoding="utf-8") as f:
                f.write("solution text")
            out = prep.collect(paths, psf, ["1", "2"], _retrieve, solutions_file=sol)
            with open(os.path.join(paths.packet_dir, "parts.json"), encoding="utf-8") as f:
                parts = json.load(f)
            self.assertEqual([p["part_id"] for p in parts], ["q1", "q2"])
            self.assertIn("First question text", parts[0]["statement"])
            self.assertEqual(parts[0]["concept_tags"], [])
            for name in ("claims.json", "samples.json", "glossary.json", "rubric.json"):
                with open(os.path.join(paths.packet_dir, name), encoding="utf-8") as f:
                    self.assertEqual(f.read(), "{}", name)
            with open(os.path.join(paths.packet_dir, "grounding.md"), encoding="utf-8") as f:
                grounding = f.read()
            self.assertIn("## q1", grounding)
            self.assertIn("p. 3", grounding)
            with open(os.path.join(paths.packet_dir, "sealed", "solution.md"), encoding="utf-8") as f:
                self.assertEqual(f.read(), "solution text")
            with open(os.path.join(paths.packet_dir, "worklist.md"), encoding="utf-8") as f:
                worklist = f.read()
            self.assertIn("claims.json", worklist)
            self.assertIn("samples.json", worklist)
            self.assertIn("without reading", worklist)       # the blind second pass
            self.assertFalse(out["validated"])

    def test_refuses_to_overwrite_existing_parts_without_force(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = TutorPaths(tmp, "microecon", "homework_4")
            write_sample_packet(paths)
            psf = _write_ps(tmp)
            with self.assertRaises(FileExistsError):
                prep.collect(paths, psf, ["1"], _retrieve)
            prep.collect(paths, psf, ["1"], _retrieve, force=True)


class TestSubmit(unittest.TestCase):
    def test_skeleton_fails_validation_with_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = TutorPaths(tmp, "microecon", "homework_4")
            prep.collect(paths, _write_ps(tmp), ["1"], _retrieve)
            result = prep.submit(paths)
            self.assertFalse(result["ok"])
            self.assertTrue(result["errors"])
            self.assertFalse(is_validated(paths.packet_dir))

    def test_valid_packet_gets_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = TutorPaths(tmp, "microecon", "homework_4")
            write_sample_packet(paths)
            os.remove(os.path.join(paths.packet_dir, "validated.json"))
            self.assertEqual(prep.submit(paths), {"ok": True})
            self.assertTrue(is_validated(paths.packet_dir))
```

- [ ] **Step 2: Run to verify it fails**

Run: `& $PY -m pytest tests/agent/tutor/test_tutor_packet.py tests/agent/tutor/test_tutor_prep.py -q`
Expected: FAIL (`ImportError: cannot import name 'read_solution'` and similar).

- [ ] **Step 3: Implement `packet.py`**

```python
# agent/tutor/packet.py  (replace the whole file)
"""packet.py -- the contract between offline prep and the live session
(spec v1 §3.1, v1.1 §3). Anything that produces a valid packet can drive a session."""
from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass, field

from agent.tutor.claims import parse_claims, self_test
from agent.tutor.lint import lint_glossary
from agent.tutor.paths import TutorPaths
from agent.tutor.ratings import AXES, RATINGS

LAUNCH_SUFFIX = "How would you like to approach this problem?"
LAUNCH_STYLES = ("label", "statement")
_HASHED = ("parts.json", "glossary.json", "rubric.json", "claims.json", "samples.json",
           os.path.join("sealed", "solution.md"))


class PacketError(ValueError):
    pass


@dataclass
class Part:
    part_id: str
    statement: str
    concept_tags: list
    expected_evidence: list
    label: str | None = None
    chat_statement: str | None = None
    launch_style: str = "label"

    def launch_text(self) -> str:
        if self.launch_style == "statement":
            return f"{(self.chat_statement or self.statement).strip()}\n\n{LAUNCH_SUFFIX}"
        return f"{self.label or self.part_id}. {LAUNCH_SUFFIX}"


@dataclass
class Packet:
    course: str
    problem_set: str
    parts: list
    glossary: dict
    rubric: dict
    claims: dict = field(default_factory=dict)


def sealed_section(markdown: str, part_id: str) -> str | None:
    m = re.search(rf"^##\s+{re.escape(part_id)}\s*$", markdown, re.M)
    if not m:
        return None
    rest = markdown[m.end():]
    nxt = re.search(r"^##\s+", rest, re.M)
    body = rest[:nxt.start()] if nxt else rest
    return body.strip() or None


def _read(packet_dir: str, rel: str) -> str:
    with open(os.path.join(packet_dir, rel), "r", encoding="utf-8") as f:
        return f.read()


def _load_json(packet_dir: str, rel: str):
    return json.loads(_read(packet_dir, rel))


def validate_packet(packet_dir: str) -> list[str]:
    errors: list[str] = []
    for rel in _HASHED:
        if not os.path.exists(os.path.join(packet_dir, rel)):
            errors.append(f"{rel.replace(os.sep, '/')} missing")
    if errors:
        return errors
    try:
        parts = _load_json(packet_dir, "parts.json")
        glossary = _load_json(packet_dir, "glossary.json")
        rubric = _load_json(packet_dir, "rubric.json")
        claims_raw = _load_json(packet_dir, "claims.json")
        samples = _load_json(packet_dir, "samples.json")
    except json.JSONDecodeError as err:
        return [f"invalid JSON: {err}"]
    if not isinstance(parts, list) or not parts:
        return ["parts.json must be a non-empty list"]
    ids = [p.get("part_id") for p in parts]
    if len(set(ids)) != len(ids) or not all(ids):
        errors.append("parts.json: part_id values must be present and unique")
    solution = _read(packet_dir, os.path.join("sealed", "solution.md"))
    for p in parts:
        pid = p.get("part_id", "?")
        if not str(p.get("statement", "")).strip():
            errors.append(f"{pid}: statement is empty")
        if not p.get("concept_tags"):
            errors.append(f"{pid}: concept_tags must be non-empty")
        if not p.get("expected_evidence"):
            errors.append(f"{pid}: expected_evidence must be non-empty")
        if p.get("launch_style", "label") not in LAUNCH_STYLES:
            errors.append(f"{pid}: launch_style must be one of {list(LAUNCH_STYLES)}")
        for axis in AXES:
            for rating in RATINGS:
                if not str(rubric.get(pid, {}).get(axis, {}).get(rating, "")).strip():
                    errors.append(f"rubric {pid}.{axis} missing '{rating}'")
        if sealed_section(solution, pid) is None:
            errors.append(f"sealed/solution.md has no '## {pid}' section")
    if not isinstance(glossary, dict) or not glossary:
        errors.append("glossary.json must be a non-empty object")
    else:
        for v in lint_glossary(glossary, [p.get("statement", "") for p in parts]):
            errors.append(f"{v.code}: {v.detail}")
    claims, claim_errors = parse_claims(claims_raw, [i for i in ids if i])
    errors.extend(claim_errors)
    if not claim_errors:
        errors.extend(self_test(claims, samples))
    return errors


def compute_hash(packet_dir: str) -> str:
    h = hashlib.sha256()
    for rel in _HASHED:
        with open(os.path.join(packet_dir, rel), "rb") as f:
            h.update(rel.encode())
            h.update(f.read().replace(b"\r\n", b"\n"))
    return h.hexdigest()


def write_validated(packet_dir: str) -> None:
    with open(os.path.join(packet_dir, "validated.json"), "w", encoding="utf-8") as f:
        json.dump({"sha256": compute_hash(packet_dir)}, f)


def is_validated(packet_dir: str) -> bool:
    marker = os.path.join(packet_dir, "validated.json")
    try:
        with open(marker, "r", encoding="utf-8") as f:
            return json.load(f)["sha256"] == compute_hash(packet_dir)
    except (OSError, KeyError, json.JSONDecodeError):
        return False


def load_packet(paths: TutorPaths) -> Packet:
    if not is_validated(paths.packet_dir):
        raise PacketError(
            f"packet at {paths.packet_dir} is missing, changed since validation, or a v1 packet without "
            "claims.json and samples.json; author them from worklist.md and run prep-submit first"
        )
    parts = [Part(**p) for p in _load_json(paths.packet_dir, "parts.json")]
    claims, errors = parse_claims(_load_json(paths.packet_dir, "claims.json"), [p.part_id for p in parts])
    if errors:
        raise PacketError("claims.json is invalid: " + "; ".join(errors))
    return Packet(
        course=paths.course, problem_set=paths.problem_set, parts=parts,
        glossary=_load_json(paths.packet_dir, "glossary.json"), rubric=_load_json(paths.packet_dir, "rubric.json"),
        claims=claims,
    )


def read_solution(packet_dir: str) -> str:
    return _read(packet_dir, os.path.join("sealed", "solution.md"))
```

- [ ] **Step 4: Implement `sample_packet.py`**

```python
# agent/tutor/sample_packet.py  (replace the whole file)
"""sample_packet.py -- a small valid v1.1 packet used by tests and docs. Not real course content."""
from __future__ import annotations

import json
import os

from agent.tutor.packet import write_validated
from agent.tutor.paths import TutorPaths
from agent.tutor.ratings import AXES, RATINGS

Q1 = (
    "Question 1. Choice overload suggests a consumer may walk away without choosing. Let $d$ be the default "
    "alternative and let $p(d, A)$ denote the probability that she walks away from the set $A$. Express "
    "$p(d, A)$ in terms of the probabilities of choosing each element of $A$."
)
Q2 = (
    "Question 2. Let $\\succeq$ be a preference relation on $\\mathbb{R}$ that ranks every non-positive number "
    "below every positive number but reverses the usual order on each side. Show that no concave function "
    "represents $\\succeq$."
)
PARTS = [
    {"part_id": "q1", "label": "Question 1", "statement": Q1,
     "concept_tags": ["random-consideration-set", "default-alternative"],
     "expected_evidence": ["identifies p(d, A) as the complement of the choice probabilities"]},
    {"part_id": "q2", "label": "Question 2", "statement": Q2,
     "concept_tags": ["preference-topology", "concavity"],
     "expected_evidence": ["finds a violation of concave representability"]},
]
GLOSSARY = {
    "choice overload": "The empirical finding that facing many options can make a person less likely to choose anything at all.",
    "concave function": "A function whose value at any weighted average of two points is at least the weighted average of its values at those points.",
}
SOLUTION = """\
## q1
### Step 1
The probabilities of choosing the alternatives in a menu sum to one.

### Step 2
Walking away is the case where none of the other alternatives is chosen, so its probability equals one minus the sum of the other choice probabilities.

## q2
### Step 1
Every non-positive number is indifferent to every other, so the preference is flat there.

### Step 2
Any representing function is therefore constant on the non-positives and strictly increasing on the positives.

### Step 3
A function that is constant and then strictly increasing cannot be concave, so no concave function represents the preference.
"""


def _rec(groups, window):
    return {"all": groups, "window": window}


CLAIMS = {
    "q1": {
        "claims": [
            {"id": "C1", "text": "the choice probabilities in a menu sum to one", "object_terms": ["the probabilities in the menu"],
             "recognizer": _rec([["sum*", "total*"], ["one", "1"]], 10)},
            {"id": "C2", "text": "walking away is the case where nothing else is chosen", "object_terms": ["walking away"],
             "recognizer": _rec([["default", "walk*", "away"], ["remains", "rest", "left", "nothing", "none", "complement*"]], 12)},
            {"id": "C3", "text": "so the walk-away probability is one minus the sum of the others", "object_terms": ["the other probabilities"],
             "recognizer": _rec([["one", "1"], ["minus", "subtract*", "except", "excluding"], ["sum*", "total", "others", "rest"]], 14)}],
        "routes": {"A": ["C1", "C2", "C3"]},
        "pitfalls": [{"id": "P1", "tag": "multiplies-instead-of-subtracting", "axis": "rigor", "resolved_by": "C3",
                      "recognizer": _rec([["multipl*", "product"], ["probabilit*"]], 10),
                      "repair_question": "What must all the choice probabilities in a menu add up to?"}]},
    "q2": {
        "claims": [
            {"id": "C1", "text": "all non-positive numbers are indifferent to each other", "object_terms": ["the non-positive numbers"],
             "recognizer": _rec([["indifferent", "indifference", "flat", "constant", "equally"], ["negative*", "zero", "non", "nonpositive"]], 14)},
            {"id": "C2", "text": "a representing function is flat on the non-positives and strictly increasing above zero", "object_terms": ["a representing function"],
             "recognizer": _rec([["flat", "constant"], ["increasing", "rises", "rising"], ["positive*", "above", "zero"]], 20)},
            {"id": "C3", "text": "a flat-then-increasing function cannot be concave", "object_terms": ["concavity"],
             "recognizer": _rec([["concave", "concavity"], ["flat", "constant", "kink"], ["increasing", "rises", "rising", "strictly"]], 20)}],
        "routes": {"A": ["C1", "C2", "C3"]},
        "pitfalls": [{"id": "P1", "tag": "confuses-concave-with-quasiconcave", "axis": "conceptual", "resolved_by": "C3",
                      "recognizer": _rec([["quasi*"], ["same", "equivalent", "like"]], 10),
                      "repair_question": "What does concavity require that quasiconcavity does not?"}]},
}

_PREFIXES = ["Remember that", "Keep in mind that", "It turns out that", "You should see that", "Here is the thing:"]


def _leaks(*cores):
    return [f"{p} {c}" for p in _PREFIXES for c in cores]


_NEUTRAL = ["What have you tried so far?", "Which part of the model feels least clear?",
            "How would you say the setup in your own words?", "What does the problem ask you to show?",
            "Which assumption have you not used yet?", "What would a simple example look like?"]

SAMPLES = {
    "q1": {
        "claims": {
            "C1": {"leak_samples": _leaks("the probabilities of all the alternatives must sum to one",
                                          "the total probability across the menu is one"),
                   "student_samples": ["probabilities of everything in the set sum to 1", "the total probability is one",
                                       "the sum of everything is one", "choice probabilities total one", "they must sum to one"]},
            "C2": {"leak_samples": _leaks("the default is what remains when nothing else is picked",
                                          "walking away is the complement of choosing something else"),
                   "student_samples": ["the default is whatever is left", "walking away is when nothing else gets chosen",
                                       "the default is the rest", "if none of the others is chosen she walks away",
                                       "default means nothing else was picked"]},
            "C3": {"leak_samples": _leaks("so the default probability equals one minus the sum of the others",
                                          "subtract the total of the other choice probabilities from one"),
                   "student_samples": ["one minus the sum of the others", "1 minus the total of the other probabilities",
                                       "I subtract the sum of the other options from one", "it is one except the sum of the rest",
                                       "p of d is 1 minus everything else summed"]}},
        "pitfalls": {"P1": {"student_samples": ["multiplying the probabilities of the others", "take the product of the choice probabilities",
                                                "I multiply the probabilities"]}},
        "neutral_samples": _NEUTRAL},
    "q2": {
        "claims": {
            "C1": {"leak_samples": _leaks("every non-positive number is indifferent to every other",
                                          "the preference is flat on the negatives and zero"),
                   "student_samples": ["all the non-positive numbers are indifferent", "it is flat on the negatives",
                                       "zero and below are equally good", "the preference is constant for negative numbers",
                                       "nonpositive numbers are all indifferent"]},
            "C2": {"leak_samples": _leaks("any representing function is flat up to zero and then strictly increasing",
                                          "utility is constant on the non-positives and rises on the positives"),
                   "student_samples": ["the utility must be flat then strictly increasing for positive numbers",
                                       "constant up to zero and rising after", "it rises above zero and is flat below",
                                       "flat on the left and increasing on the positive side", "increasing above zero but constant before"]},
            "C3": {"leak_samples": _leaks("a function that is flat and then increasing cannot be concave",
                                          "concavity fails because the graph is constant and then rises"),
                   "student_samples": ["flat then increasing cannot be concave", "a concave function cannot be constant then strictly increasing",
                                       "concavity rules out a flat part followed by rising values", "the kink makes it non concave and it rises after",
                                       "constant and then increasing means not concave"]}},
        "pitfalls": {"P1": {"student_samples": ["quasiconcave is the same as concave here", "a quasiconcave function is equivalent to a concave one",
                                                "quasi concave is like concave"]}},
        "neutral_samples": _NEUTRAL},
}


def write_sample_packet(paths: TutorPaths) -> None:
    d = paths.packet_dir
    os.makedirs(os.path.join(d, "sealed"), exist_ok=True)
    rubric = {
        p["part_id"]: {a: {r: f"{p['part_id']} {a} {r} descriptor" for r in RATINGS} for a in AXES} for p in PARTS
    }
    for name, payload in (("parts.json", PARTS), ("glossary.json", GLOSSARY), ("rubric.json", rubric),
                          ("claims.json", CLAIMS), ("samples.json", SAMPLES)):
        with open(os.path.join(d, name), "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
    with open(os.path.join(d, "grounding.md"), "w", encoding="utf-8") as f:
        f.write("# Grounding (sample)\n")
    with open(os.path.join(d, "sealed", "solution.md"), "w", encoding="utf-8") as f:
        f.write(SOLUTION)
    write_validated(d)
```

- [ ] **Step 5: Implement `prep.py`**

```python
# agent/tutor/prep.py  (replace the whole file)
"""prep.py -- deterministic half of offline prep (v1 spec §3.1, v1.1 §3). collect()
parses the problem set, retrieves grounding passages and writes a packet skeleton
plus a worklist; the live IDE agent then authors the glossary, rubric, claims and
(in a blind second pass) the samples, and submit() validates them, including the
recognizer self-test. No LLM call happens here; the caller supplies `retrieve`."""
from __future__ import annotations

import json
import os
import re
from typing import Callable

from agent.rag.problem_set_parser import extract_question
from agent.tutor.packet import validate_packet, write_validated
from agent.tutor.paths import TutorPaths

WORKLIST = """# Prep worklist (for the IDE agent)

Complete these in `packet/`, then run `prep-submit` and fix every reported error. Do steps 1-5 first, then step 6
in a SEPARATE step as described.

1. `parts.json`: split each question into the parts the student will work through (one entry per sub-part is
   fine). Per part set `part_id` (unique, e.g. `q1_2`), `label`, `statement` (verbatim, neutral, no hints),
   `concept_tags` (kebab-case, reusable across problem sets), `expected_evidence` (what a correct attempt must show).
   Optional: `chat_statement` (Unicode math instead of LaTeX), `launch_style` (`"label"` default, or `"statement"`).
2. `glossary.json`: `{term: generic domain definition}` for every term a student might ask about. A definition
   must NOT use the problem's variables or notation and must NOT refer to a part or question number.
3. `rubric.json`: `{part_id: {axis: {rating: descriptor}}}` with axes `conceptual`, `rigor`, `directness` and
   ratings `Developing / Needs Review`, `Proficient`, `Mastered`.
4. `sealed/solution.md`: one `## <part_id>` section per part, copied verbatim from the guided solutions. Inside each
   section use `### Step N` headings, one per logical step; `verify` shows these steps to the tutor once, after the
   student has covered the part. `sealed/hints.md` is optional reference only and is not used at runtime.
5. `claims.json` (the claim ledger). Per part: `claims` (each: `id`, `text`, `object_terms`, `recognizer`), `routes`
   (name -> ordered claim ids; add a route for each genuinely different valid proof), `pitfalls` (each: `id`, `tag`,
   `axis`, `recognizer`, `repair_question`, optional `resolved_by` claim id), optional `final_answer` recognizer.
   A recognizer is `{"all": [[w, ...], ...], "window": N}`: every group must have a hit within N consecutive words.
   An entry matches a whole word; end it with `*` to match a prefix (`consider*`). Do not use plain `not`, `add` or
   `sum` expecting prefixes. Recognizers run on the STUDENT's words to detect claims and on the TUTOR's drafts to
   detect leaks, so make them specific to the idea, not to words already in the problem statement.
6. `samples.json`, written in a separate step, without reading the recognizers in `claims.json` (only the claim texts):
   per part `neutral_samples` (>=5 Socratic questions that reveal nothing); per claim `leak_samples` (>=10 sentences a
   tutor might say that reveal the claim) and `student_samples` (>=5 ways a student might state it); per pitfall
   `student_samples` (>=3). `prep-submit` runs every recognizer on these: it needs 90% of the leak samples and 80% of
   the student samples matched and no neutral sample matched.
7. Read `grounding.md` for the course's own notation and sources.
"""


def _write(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def _slug(ref: str) -> str:
    return "q" + re.sub(r"[^A-Za-z0-9]+", "_", ref).strip("_")


def collect(
    paths: TutorPaths, problem_set_file: str, question_refs: list[str], retrieve: Callable[[str], list],
    hints_file: str | None = None, solutions_file: str | None = None, force: bool = False,
) -> dict:
    d = paths.packet_dir
    if os.path.exists(os.path.join(d, "parts.json")) and not force:
        raise FileExistsError(f"{d}/parts.json already exists; pass force=True to overwrite")
    parts, grounding = [], ["# Grounding passages (internal; never quote to the student)\n"]
    for ref in question_refs:
        statement = extract_question(problem_set_file, ref)
        pid = _slug(ref)
        parts.append({"part_id": pid, "label": f"Question {ref}", "statement": statement,
                      "concept_tags": [], "expected_evidence": []})
        grounding.append(f"\n## {pid}\n")
        for p in retrieve(statement):
            snippet = p.text[:600].replace("\n", " ")
            grounding.append(f"- {p.citation} ({p.path}, score {p.score:.2f})\n  > {snippet}\n")
    _write(os.path.join(d, "parts.json"), json.dumps(parts, ensure_ascii=False, indent=2))
    for name in ("glossary.json", "rubric.json", "claims.json", "samples.json"):
        _write(os.path.join(d, name), "{}")
    _write(os.path.join(d, "grounding.md"), "\n".join(grounding))
    for rel, src in ((os.path.join("sealed", "hints.md"), hints_file), (os.path.join("sealed", "solution.md"), solutions_file)):
        text = ""
        if src:
            with open(src, "r", encoding="utf-8") as f:
                text = f.read()
        _write(os.path.join(d, rel), text)
    _write(os.path.join(d, "worklist.md"), WORKLIST)
    return {"ok": True, "packet_dir": d, "parts": [p["part_id"] for p in parts], "validated": False}


def submit(paths: TutorPaths) -> dict:
    errors = validate_packet(paths.packet_dir)
    if errors:
        return {"ok": False, "errors": errors}
    write_validated(paths.packet_dir)
    return {"ok": True}
```

- [ ] **Step 6: Run to verify it passes**

Run: `& $PY -m pytest tests/agent/tutor/test_tutor_packet.py tests/agent/tutor/test_tutor_prep.py tests/agent/tutor/test_tutor_claims.py tests/agent/tutor/test_tutor_ledger.py -q`
Expected: all passed. If `test_sample_is_valid_and_loadable` reports self-test errors, the message names the sample and claim; fix the sample text (not the thresholds) so the recognizer matches it.

- [ ] **Step 7: Commit**

```powershell
git add agent/tutor/packet.py agent/tutor/sample_packet.py agent/tutor/prep.py tests/agent/tutor/test_tutor_packet.py tests/agent/tutor/test_tutor_prep.py
git commit -m "feat(tutor): packet v1.1 with claims, samples, short launch and new prep worklist"
```

---

### Task 5: FSM changes

**Files:**
- Modify: `agent/tutor/fsm.py` (replace whole file)
- Test: `tests/agent/tutor/test_tutor_fsm.py` (replace whole file)

**Interfaces:**
- Produces (changed): `student_event(s, intent, n_parts, made_progress=True) -> (FsmState, dict)`. In `VERIFIED`/`AWAITING_ADVANCE`/`SYNTHESIS` every intent except `confirm_advance` leaves the state unchanged and never raises the hint level; an `attempt` with `made_progress=False` increments `failed_at_level`; `define_request` never changes state. New `verify_clean_event(s) -> FsmState` (WORKING -> VERIFIED, else `IllegalTransition`). `replay` passes `e.data.get("made_progress", True)` and handles `verify` events with `data["clean"]`.
- Kept: `verdict_event`, `checkin_event`, `finish_event`, constants, `IllegalTransition`, `FsmState`.

- [ ] **Step 1: Write the failing test (replace `test_tutor_fsm.py`)**

```python
# tests/agent/tutor/test_tutor_fsm.py
import unittest

from agent.tutor.events import Event
from agent.tutor.fsm import (
    AWAITING_ADVANCE, DONE, LAUNCH, SYNTHESIS, VERIFIED, WORKING,
    FsmState, IllegalTransition, checkin_event, finish_event, replay, student_event,
    verdict_event, verify_clean_event,
)


def S(**kw):
    return FsmState(**kw)


class TestStudentEvents(unittest.TestCase):
    def test_first_attempt_moves_launch_to_working(self):
        s, _ = student_event(S(), "attempt", 2)
        self.assertEqual((s.state, s.hint_level), (WORKING, 0))

    def test_define_request_never_changes_state_or_hint_level(self):
        s, _ = student_event(S(state=WORKING, hint_level=2), "define_request", 2)
        self.assertEqual((s.state, s.hint_level), (WORKING, 2))
        s, _ = student_event(S(), "define_request", 2)
        self.assertEqual(s.state, LAUNCH)

    def test_stuck_raises_hint_one_level_at_a_time(self):
        s, _ = student_event(S(state=WORKING), "stuck", 2)
        self.assertEqual(s.hint_level, 1)
        s, _ = student_event(s, "hint_request", 2)
        self.assertEqual(s.hint_level, 2)

    def test_level_three_requires_two_failed_attempts_at_level_two(self):
        s, info = student_event(S(state=WORKING, hint_level=2, failed_at_level=1), "stuck", 2)
        self.assertEqual(s.hint_level, 2)
        self.assertTrue(info["hint_capped"])
        s, info = student_event(S(state=WORKING, hint_level=2, failed_at_level=2), "stuck", 2)
        self.assertEqual(s.hint_level, 3)
        self.assertFalse(info["hint_capped"])

    def test_attempt_that_makes_progress_never_raises_or_fails(self):
        s, _ = student_event(S(state=WORKING, hint_level=1), "attempt", 2, made_progress=True)
        self.assertEqual((s.hint_level, s.failed_at_level), (1, 0))

    def test_attempts_without_progress_count_as_failures_until_level_three_opens(self):
        s = S(state=WORKING, hint_level=2)
        for _ in range(2):
            s, _ = student_event(s, "attempt", 2, made_progress=False)
        self.assertEqual(s.failed_at_level, 2)
        s, info = student_event(s, "stuck", 2)
        self.assertEqual((s.hint_level, s.failed_at_level, info["hint_capped"]), (3, 0, False))

    def test_first_attempt_without_progress_is_a_failure_at_level_zero(self):
        s, _ = student_event(S(), "attempt", 2, made_progress=False)
        self.assertEqual((s.state, s.failed_at_level), (WORKING, 1))

    def test_confirm_advance_illegal_while_working_or_launch(self):
        for st in (LAUNCH, WORKING):
            with self.assertRaises(IllegalTransition):
                student_event(S(state=st), "confirm_advance", 2)

    def test_confirm_advance_from_awaiting_goes_to_next_part_launch_and_resets_hints(self):
        s, _ = student_event(S(part_index=0, state=AWAITING_ADVANCE, hint_level=2, failed_at_level=1), "confirm_advance", 2)
        self.assertEqual(s, FsmState(part_index=1, state=LAUNCH, hint_level=0, failed_at_level=0))

    def test_confirm_advance_from_verified_is_allowed(self):
        s, _ = student_event(S(state=VERIFIED), "confirm_advance", 2)
        self.assertEqual(s.part_index, 1)

    def test_confirm_on_last_part_goes_to_synthesis(self):
        s, _ = student_event(S(part_index=1, state=AWAITING_ADVANCE), "confirm_advance", 2)
        self.assertEqual((s.part_index, s.state), (1, SYNTHESIS))

    def test_closed_part_stays_closed_for_questions_and_hint_requests(self):
        for st in (VERIFIED, AWAITING_ADVANCE):
            for intent in ("has_questions", "other", "attempt", "stuck", "hint_request", "define_request"):
                s, _ = student_event(S(state=st, hint_level=1), intent, 2, made_progress=False)
                self.assertEqual((s.state, s.hint_level, s.failed_at_level), (st, 1, 0), (st, intent))

    def test_unknown_intent_and_done_state_rejected(self):
        with self.assertRaises(IllegalTransition):
            student_event(S(), "dance", 2)
        with self.assertRaises(IllegalTransition):
            student_event(S(state=DONE), "attempt", 2)


class TestTutorSideEvents(unittest.TestCase):
    def test_verdict_event_is_kept_for_v1_logs(self):
        s = verdict_event(S(state=WORKING), "off_track")
        self.assertEqual((s.state, s.failed_at_level), (WORKING, 1))
        self.assertEqual(verdict_event(s, "correct").state, VERIFIED)
        with self.assertRaises(IllegalTransition):
            verdict_event(S(state=LAUNCH), "correct")

    def test_verify_clean_event_only_while_working(self):
        self.assertEqual(verify_clean_event(S(state=WORKING)).state, VERIFIED)
        for st in (LAUNCH, VERIFIED, AWAITING_ADVANCE):
            with self.assertRaises(IllegalTransition):
                verify_clean_event(S(state=st))

    def test_checkin_only_moves_verified(self):
        self.assertEqual(checkin_event(S(state=VERIFIED)).state, AWAITING_ADVANCE)
        self.assertEqual(checkin_event(S(state=WORKING)).state, WORKING)

    def test_finish_requires_synthesis(self):
        self.assertEqual(finish_event(S(state=SYNTHESIS)).state, DONE)
        with self.assertRaises(IllegalTransition):
            finish_event(S(state=WORKING))


class TestReplay(unittest.TestCase):
    def test_replay_reproduces_state_with_verify_events(self):
        ev = lambda i, t, **kw: Event(id=i, ts="t", type=t, **kw)
        events = [
            ev(1, "session_start"),
            ev(2, "student", intent="attempt", data={"made_progress": True}),
            ev(3, "verify", data={"clean": False}),
            ev(4, "student", intent="attempt", data={"made_progress": False}),
            ev(5, "verify", data={"clean": True}),
            ev(6, "close_part", data={"ratings": {}}),
            ev(7, "tutor_say", data={"checkin": True}),
            ev(8, "student", intent="has_questions"),
            ev(9, "student", intent="confirm_advance"),
        ]
        s = replay(events[:5], 2)
        self.assertEqual((s.state, s.failed_at_level), (VERIFIED, 1))
        s = replay(events[:8], 2)
        self.assertEqual((s.part_index, s.state), (0, AWAITING_ADVANCE))
        s = replay(events, 2)
        self.assertEqual((s.part_index, s.state), (1, LAUNCH))

    def test_replay_still_understands_v1_verdict_logs(self):
        ev = lambda i, t, **kw: Event(id=i, ts="t", type=t, **kw)
        events = [ev(1, "student", intent="attempt"), ev(2, "verdict", data={"assessment": "correct"})]
        self.assertEqual(replay(events, 2).state, VERIFIED)
```

- [ ] **Step 2: Run to verify it fails**

Run: `& $PY -m pytest tests/agent/tutor/test_tutor_fsm.py -q`
Expected: FAIL `ImportError: cannot import name 'verify_clean_event'`.

- [ ] **Step 3: Implement**

```python
# agent/tutor/fsm.py  (replace the whole file)
"""fsm.py -- the Socratic tutoring state machine as pure functions (v1 spec §3.3,
v1.1 §4). Nothing here touches disk: session.py replays the event log through
replay() on every CLI call, so state can never drift from the log."""
from __future__ import annotations

from dataclasses import dataclass, replace

from agent.tutor.events import Event

LAUNCH = "LAUNCH"
WORKING = "WORKING"
VERIFIED = "VERIFIED"
AWAITING_ADVANCE = "AWAITING_ADVANCE"
SYNTHESIS = "SYNTHESIS"
DONE = "DONE"

INTENTS = {"attempt", "stuck", "hint_request", "define_request", "confirm_advance", "has_questions", "other"}
ASSESSMENTS = {"correct", "on_track", "adjacent", "off_track"}
MAX_HINT_LEVEL = 3


class IllegalTransition(ValueError):
    pass


@dataclass(frozen=True)
class FsmState:
    part_index: int = 0
    state: str = LAUNCH
    hint_level: int = 0
    failed_at_level: int = 0


def student_event(s: FsmState, intent: str, n_parts: int, made_progress: bool = True) -> tuple[FsmState, dict]:
    if intent not in INTENTS:
        raise IllegalTransition(f"unknown intent {intent!r}; expected one of {sorted(INTENTS)}")
    if s.state == DONE:
        raise IllegalTransition("session is already DONE")
    if intent == "confirm_advance":
        if s.state not in (VERIFIED, AWAITING_ADVANCE):
            raise IllegalTransition(
                f"confirm_advance is only valid after the part is verified (state is {s.state})"
            )
        if s.part_index + 1 >= n_parts:
            return replace(s, state=SYNTHESIS), {"hint_capped": False}
        return FsmState(part_index=s.part_index + 1), {"hint_capped": False}
    info = {"hint_capped": False}
    if s.state in (SYNTHESIS, VERIFIED, AWAITING_ADVANCE) or intent == "define_request":
        return s, info          # a closed part is never reopened by a side question
    new = s
    if intent in ("stuck", "hint_request"):
        if s.hint_level >= MAX_HINT_LEVEL:
            info["hint_capped"] = True
        elif s.hint_level == 2 and s.failed_at_level < 2:
            info["hint_capped"] = True
        else:
            new = replace(s, hint_level=s.hint_level + 1, failed_at_level=0)
    elif intent == "attempt" and not made_progress:
        new = replace(s, failed_at_level=s.failed_at_level + 1)
    if new.state == LAUNCH:
        new = replace(new, state=WORKING)
    return new, info


def verdict_event(s: FsmState, assessment: str) -> FsmState:
    """v1 only; kept so v1 logs still replay."""
    if assessment not in ASSESSMENTS:
        raise IllegalTransition(f"unknown assessment {assessment!r}; expected one of {sorted(ASSESSMENTS)}")
    if s.state != WORKING:
        raise IllegalTransition(f"verdict is only valid while WORKING (state is {s.state})")
    if assessment == "correct":
        return replace(s, state=VERIFIED)
    return replace(s, failed_at_level=s.failed_at_level + 1)


def verify_clean_event(s: FsmState) -> FsmState:
    if s.state != WORKING:
        raise IllegalTransition(f"verify is only valid while WORKING (state is {s.state})")
    return replace(s, state=VERIFIED)


def checkin_event(s: FsmState) -> FsmState:
    return replace(s, state=AWAITING_ADVANCE) if s.state == VERIFIED else s


def finish_event(s: FsmState) -> FsmState:
    if s.state != SYNTHESIS:
        raise IllegalTransition(f"cannot end the session from state {s.state}; finish all parts first")
    return replace(s, state=DONE)


def replay(events: list[Event], n_parts: int) -> FsmState:
    s = FsmState()
    for e in events:
        if e.type == "student":
            s, _ = student_event(s, e.intent, n_parts, e.data.get("made_progress", True))
        elif e.type == "verdict":
            s = verdict_event(s, e.data["assessment"])
        elif e.type == "verify" and e.data.get("clean"):
            s = verify_clean_event(s)
        elif e.type == "tutor_say" and e.data.get("checkin"):
            s = checkin_event(s)
        elif e.type == "session_end":
            s = finish_event(s)
    return s
```

- [ ] **Step 4: Run to verify it passes**

Run: `& $PY -m pytest tests/agent/tutor/test_tutor_fsm.py tests/agent/tutor/test_tutor_claims.py tests/agent/tutor/test_tutor_ledger.py tests/agent/tutor/test_tutor_events.py -q`
Expected: all passed.

- [ ] **Step 5: Commit**

```powershell
git add agent/tutor/fsm.py tests/agent/tutor/test_tutor_fsm.py
git commit -m "feat(tutor): closed parts stay closed, failed attempts, verify event in the FSM"
```

---

### Task 6: Lint — disclosure and question form

**Files:**
- Modify: `agent/tutor/lint.py` (replace whole file)
- Test: `tests/agent/tutor/test_tutor_lint.py` (append two classes; existing tests stay and must still pass)

**Interfaces:**
- Consumes: `claims.Recognizer`, `claims.tokenize`.
- Produces: `lint_message(text, *, state, hint_level, student_text="", statement="", sealed_solution="", allowed_exact=(), after_define=False, forbidden_patterns=(), blocked_claims=None, form=False, last_student_text="") -> list[Violation]` where `blocked_claims: dict[str, Recognizer] | None`. New codes `REVEALS_CLAIM` (detail names the claim id only) and `QUESTION_FORM`. New helper `check_form(text, last_student_text, max_words=60) -> str | None`.
- Disclosure runs on the draft's tokens with every 6-word run that also appears in `statement` masked out.

- [ ] **Step 1: Write the failing tests (append to `test_tutor_lint.py`)**

```python
from agent.tutor.claims import parse_recognizer
from agent.tutor.lint import check_form

BLOCKED = {"C3": parse_recognizer({"all": [["independen*"], ["multipl*", "product", "joint", "together"]], "window": 14})}
STATEMENT2 = ("The probability of an alternative a being considered is gamma which is independent of the "
              "probability of any other alternative being considered together here.")


class TestDisclosure(unittest.TestCase):
    def test_unreached_claim_is_rejected_by_id_only(self):
        draft = "Since each item is considered independently, how would you express the probability of all those events together?"
        v = lint(draft, blocked_claims=BLOCKED)
        self.assertEqual(codes(v), {"REVEALS_CLAIM"})
        self.assertIn("C3", v[0].detail)
        self.assertNotIn("independen", v[0].detail)        # the recognizer words must not leak through the message

    def test_neutral_question_passes_with_blocked_claims(self):
        self.assertEqual(lint("What have you tried so far?", blocked_claims=BLOCKED), [])

    def test_no_blocked_claims_means_no_disclosure_check(self):
        self.assertEqual(lint("The events are independent so multiply them together."), [])

    def test_quoting_the_problem_statement_is_not_a_reveal(self):
        quote = "As written, independent of the probability of any other alternative being considered together, correct?"
        self.assertEqual(lint(quote, statement=STATEMENT2, blocked_claims=BLOCKED), [])
        paraphrase = "These are independent, so how do they combine together?"
        self.assertIn("REVEALS_CLAIM", codes(lint(paraphrase, statement=STATEMENT2, blocked_claims=BLOCKED)))


class TestQuestionForm(unittest.TestCase):
    LAST = "I think the alternative needs to be considered and have the highest utility"

    def form(self, text):
        return lint(text, form=True, last_student_text=self.LAST)

    def test_good_forms_pass(self):
        self.assertEqual(self.form("What else has to happen for that alternative to be chosen?"), [])
        self.assertEqual(self.form("You said the alternative needs the highest utility. What else has to happen?"), [])

    def test_two_questions_rejected(self):
        self.assertIn("QUESTION_FORM", codes(self.form("What do you mean? And why does it matter?")))

    def test_word_cap_rejected(self):
        self.assertIn("QUESTION_FORM", codes(self.form(" ".join(["word"] * 70) + "?")))

    def test_second_statement_rejected(self):
        self.assertIn("QUESTION_FORM", codes(self.form("You are right. That is the idea. What next?")))

    def test_statement_must_echo_the_student(self):
        reason = check_form("Items have prices. What do you think?", self.LAST)
        self.assertIn("own words", reason)

    def test_form_is_off_by_default(self):
        self.assertEqual(lint("Two questions? Really? Yes, " + "word " * 80), [])
```

- [ ] **Step 2: Run to verify it fails**

Run: `& $PY -m pytest tests/agent/tutor/test_tutor_lint.py -q`
Expected: FAIL (`ImportError: cannot import name 'check_form'` or unexpected keyword `blocked_claims`).

- [ ] **Step 3: Implement (replace `agent/tutor/lint.py`)**

```python
# agent/tutor/lint.py  (replace the whole file)
"""lint.py -- checks on a tutor draft before it is sent (v1 spec §4, v1.1 §6) and
on glossary definitions at prep time. v1.1 adds claim disclosure (a draft may not
match the recognizer of a claim the student has not reached) and the question
form. A false positive costs one revision; a false negative costs a leak."""
from __future__ import annotations

import re
from dataclasses import dataclass

from agent.tutor.claims import tokenize
from agent.tutor.fsm import LAUNCH, VERIFIED, WORKING


@dataclass(frozen=True)
class Violation:
    code: str
    detail: str

    def to_dict(self) -> dict:
        return {"code": self.code, "detail": self.detail}


TECHNIQUES = {
    "contradiction": re.compile(r"contradiction|reductio|for the sake of", re.I),
    "contrapositive": re.compile(r"contraposit", re.I),
    "induction": re.compile(r"\binduct(?:ion|ive)\b", re.I),
    "construction": re.compile(r"\bconstruct(?:ion|ive)?\b|counterexample", re.I),
}
_MATH = re.compile(r"\$([^$]+)\$")
_LATEX_CMD = re.compile(r"\\[A-Za-z]+")
_GREEK = re.compile(r"[α-ωΑ-Ω]")
_LETTER = re.compile(r"(?<![A-Za-z\\])[A-Za-z](?![A-Za-z])")
_COMMON_LETTERS = {"a", "A", "I"}
_UNICODE_FOR_LATEX = {
    "\\succeq": "≽", "\\succ": "≻", "\\preceq": "≼", "\\prec": "≺", "\\in": "∈", "\\cup": "∪", "\\cap": "∩",
    "\\gamma": "γ", "\\Gamma": "Γ", "\\lambda": "λ", "\\Lambda": "Λ", "\\mu": "μ", "\\sigma": "σ",
    "\\epsilon": "ε", "\\delta": "δ", "\\Delta": "Δ", "\\alpha": "α", "\\beta": "β", "\\theta": "θ",
}
_SUBQ_LINE = re.compile(r"^\s*(?:\d+[.)]|[A-Za-z][.)]|[-*•])\s+.*\?\s*$", re.M)
_LATEX_IN_CHAT = re.compile(r"\$|\\\(|\\\[|\\[A-Za-z]{2,}")
_CHECKIN = re.compile(r"lingering|any questions|ready to move on|move on", re.I)
_BACKREF = re.compile(r"\b(?:part|question|problem)\s+\d", re.I)
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
_STOP = {"that", "this", "with", "from", "have", "been", "were", "will", "would", "could", "should", "what",
         "when", "where", "which", "there", "their", "them", "then", "than", "into", "your", "about", "also",
         "just", "like", "does", "think", "said", "because", "these", "those", "every", "being"}
MAX_FORM_WORDS = 60
STATEMENT_RUN = 6


def _normalize(text: str) -> str:
    return " ".join(text.split())


def extract_symbols(statement: str) -> set[str]:
    symbols: set[str] = set()
    for math in _MATH.findall(statement):
        symbols.update(_LATEX_CMD.findall(math))
        symbols.update(_GREEK.findall(math))
        symbols.update(l for l in _LETTER.findall(math) if l not in _COMMON_LETTERS)
    symbols.update(_GREEK.findall(statement))
    return symbols


def symbol_hits(text: str, symbols: set[str]) -> list[str]:
    hits = []
    for sym in sorted(symbols):
        if sym.startswith("\\"):
            if sym in text or _UNICODE_FOR_LATEX.get(sym, "\0") in text:
                hits.append(sym)
        elif len(sym) > 1 or not sym.isascii():
            if sym in text:
                hits.append(sym)
        elif re.search(rf"(?<![A-Za-z]){re.escape(sym)}(?![A-Za-z])", text):
            hits.append(sym)
    return hits


def _ngrams(text: str, n: int = 6) -> set[tuple]:
    words = re.findall(r"[A-Za-z0-9']+", text.lower())
    return {tuple(words[i:i + n]) for i in range(len(words) - n + 1)}


def _mask_statement_runs(tokens: list[str], statement_tokens: list[str], n: int = STATEMENT_RUN) -> list[str]:
    runs = {tuple(statement_tokens[i:i + n]) for i in range(len(statement_tokens) - n + 1)}
    masked = list(tokens)
    for i in range(len(tokens) - n + 1):
        if tuple(tokens[i:i + n]) in runs:
            for j in range(i, i + n):
                masked[j] = ""
    return masked


def _content_words(text: str) -> set[str]:
    return {t for t in tokenize(text) if len(t) >= 4 and t not in _STOP}


def check_form(text: str, last_student_text: str, max_words: int = MAX_FORM_WORDS) -> str | None:
    """The question form (v1.1 §6): at most one question, a word cap, and at most one other
    sentence which must restate the student's own words. Returns the reason or None."""
    if text.count("?") > 1:
        return "ask at most one question"
    if len(text.split()) > max_words:
        return f"use at most {max_words} words"
    sentences = [s.strip() for s in _SENTENCE_SPLIT.split(text.strip()) if s.strip()]
    statements = [s for s in sentences if not s.endswith("?")]
    if len(statements) > 1:
        return "use at most one non-question sentence"
    if statements and len(_content_words(statements[0]) & _content_words(last_student_text)) < 2:
        return ("the one non-question sentence must restate or acknowledge the student's own words "
                "(share at least two content words with their last message)")
    return None


def lint_message(
    text: str, *, state: str, hint_level: int, student_text: str = "", statement: str = "",
    sealed_solution: str = "", allowed_exact=(), after_define: bool = False, forbidden_patterns=(),
    blocked_claims: dict | None = None, form: bool = False, last_student_text: str = "",
) -> list[Violation]:
    if _normalize(text) in {_normalize(a) for a in allowed_exact}:
        return []
    found: list[Violation] = []
    if state == LAUNCH:
        found.append(Violation("LAUNCH_NOT_VERBATIM", "In LAUNCH send exactly the launch text, nothing added or changed."))
    if hint_level < 3:
        for name, rx in TECHNIQUES.items():
            if rx.search(text) and not rx.search(student_text):
                found.append(Violation("TECHNIQUE", f"names the proof technique '{name}' before the student did"))
    if after_define:
        hits = symbol_hits(text, extract_symbols(statement))
        if hits:
            found.append(Violation("NOTATION_BRIDGE", f"a definition answer must not use the problem's notation: {hits}"))
    if sealed_solution and _ngrams(text) & _ngrams(sealed_solution):
        found.append(Violation("SEALED_OVERLAP", "draft repeats a phrase from the sealed solution"))
    if blocked_claims:
        masked = _mask_statement_runs(tokenize(text), tokenize(statement))
        for cid, rec in blocked_claims.items():
            if rec.matches_tokens(masked):
                found.append(Violation("REVEALS_CLAIM", f"introduces an idea the student has not reached (claim {cid})"))
    if state == WORKING and hint_level < 3 and len(_SUBQ_LINE.findall(text)) >= 2:
        found.append(Violation("SUBQUESTION_LIST", "leading sub-question list before the student proposed a plan"))
    if form:
        reason = check_form(text, last_student_text)
        if reason:
            found.append(Violation("QUESTION_FORM", reason))
    if state == VERIFIED and not (_CHECKIN.search(text) and "?" in text):
        found.append(Violation("CHECKIN_MISSING", "ask whether they have lingering questions or are ready to move on"))
    for pattern in forbidden_patterns:
        if re.search(pattern, text, re.I):
            found.append(Violation("NEXT_PART_REFERENCE", "do not mention the next part before the student confirms advancing"))
            break
    if _LATEX_IN_CHAT.search(text):
        found.append(Violation("LATEX_IN_CHAT", "use Unicode math (≽, ≤, λ, ℝ) in chat; keep LaTeX for vault files"))
    return found


def lint_glossary(glossary: dict[str, str], statements: list[str]) -> list[Violation]:
    found: list[Violation] = []
    for term, definition in glossary.items():
        if _BACKREF.search(definition):
            found.append(Violation("GLOSSARY_BACKREF", f"{term!r}: definition refers to a part/question number"))
        for statement in statements:
            if term.lower() in statement.lower():
                hits = symbol_hits(definition, extract_symbols(statement))
                if hits:
                    found.append(Violation("GLOSSARY_NOTATION", f"{term!r}: definition uses the problem's notation {hits}"))
                    break
    return found
```

- [ ] **Step 4: Run to verify it passes**

Run: `& $PY -m pytest tests/agent/tutor/test_tutor_lint.py tests/agent/tutor/test_tutor_packet.py -q`
Expected: all passed (the v1 lint tests still pass because the new parameters default to off).

- [ ] **Step 5: Commit**

```powershell
git add agent/tutor/lint.py tests/agent/tutor/test_tutor_lint.py
git commit -m "feat(tutor): claim disclosure and question-form lint"
```

---

### Task 7: Ratings with CLI-attached evidence; verified steps in the summary

**Files:**
- Modify: `agent/tutor/ratings.py` (replace whole file), `agent/tutor/render.py` (one edit)
- Test: `tests/agent/tutor/test_tutor_ratings.py` (replace), `tests/agent/tutor/test_tutor_render_profile.py` (append one test)

**Interfaces:**
- Produces: `ceiling(part_events, axis) -> (rating, reasons)` (unchanged); `cap_evidence(part_events, axis) -> list[int]`; `build_ratings(part_events, downgrades=None) -> {axis: {"rating", "evidence": [event ids], "why"?}}` where `downgrades = {axis: (rating, why)}`; raises `RatingRejected` for an unknown axis, an unknown rating, or a rating above the ceiling. `validate_close_part` is removed.
- Evidence = ids of: student events with intent `stuck`/`hint_request` and `hint_level >= 1`; `misconception` events applying to the axis; student events with `admits_gap` applying to the axis. If none, the student events whose `data["established"]` is non-empty; if still none, the last student event.
- Render: after a part's axis lines, a clean `verify` event adds `- **Verified steps** (student words):` with one `step N: "quote"` line per entry.

- [ ] **Step 1: Write the failing tests**

```python
# tests/agent/tutor/test_tutor_ratings.py  (replace the whole file)
import unittest

from agent.tutor.events import Event
from agent.tutor.ratings import AXES, RatingRejected, build_ratings, cap_evidence, ceiling

DEV, PROF, MAST = "Developing / Needs Review", "Proficient", "Mastered"


def ev(i, type, hint=0, text=None, **data):
    return Event(id=i, ts="t", type=type, part="q1", hint_level=hint, text=text, intent=data.pop("intent", None), data=data)


class TestCeiling(unittest.TestCase):
    def test_clean_part_can_be_mastered(self):
        self.assertEqual(ceiling([ev(1, "student", text="my answer", intent="attempt")], "rigor")[0], MAST)

    def test_hint_level_one_caps_at_proficient(self):
        self.assertEqual(ceiling([ev(1, "student", hint=1, text="a", intent="stuck")], "rigor")[0], PROF)

    def test_hint_level_two_caps_at_developing(self):
        rating, reasons = ceiling([ev(1, "student", hint=2, text="a", intent="stuck")], "rigor")
        self.assertEqual(rating, DEV)
        self.assertTrue(any("hint level" in r for r in reasons))

    def test_unresolved_misconception_caps_at_developing(self):
        events = [ev(1, "student", text="a", intent="attempt"), ev(2, "misconception", tag="closed-implies-bounded")]
        self.assertEqual(ceiling(events, "conceptual")[0], DEV)

    def test_resolved_misconception_caps_at_proficient_not_mastered(self):
        events = [ev(1, "misconception", tag="t"), ev(2, "misconception_resolved", tag="t")]
        self.assertEqual(ceiling(events, "conceptual")[0], PROF)

    def test_axis_scoped_misconception_only_caps_that_axis(self):
        events = [ev(1, "misconception", tag="t", axis="rigor")]
        self.assertEqual(ceiling(events, "rigor")[0], DEV)
        self.assertEqual(ceiling(events, "conceptual")[0], MAST)

    def test_student_admitted_gap_caps_axis(self):
        events = [ev(1, "student", text="I don't understand concavity", intent="other", admits_gap=True, gap_axis="conceptual")]
        self.assertEqual(ceiling(events, "conceptual")[0], DEV)
        self.assertEqual(ceiling(events, "rigor")[0], MAST)


class TestCapEvidence(unittest.TestCase):
    def test_hint_misconception_and_gap_events_are_the_evidence(self):
        events = [
            ev(1, "student", hint=0, text="try", intent="attempt", established=["C1"]),
            ev(2, "student", hint=1, text="stuck", intent="stuck"),
            ev(3, "misconception", tag="t", axis="rigor"),
            ev(4, "student", hint=1, text="idk", intent="other", admits_gap=True, gap_axis="conceptual"),
        ]
        self.assertEqual(cap_evidence(events, "rigor"), [2, 3])
        self.assertEqual(cap_evidence(events, "conceptual"), [2, 4])
        self.assertEqual(cap_evidence(events, "directness"), [2])

    def test_uncapped_axis_cites_the_turns_that_established_claims(self):
        events = [ev(1, "student", text="a", intent="attempt"),
                  ev(2, "student", text="b", intent="attempt", established=["C1"]),
                  ev(3, "student", text="c", intent="attempt", established=["C2"])]
        self.assertEqual(cap_evidence(events, "rigor"), [2, 3])

    def test_falls_back_to_the_last_student_event(self):
        events = [ev(1, "student", text="a", intent="attempt"), ev(2, "student", text="b", intent="attempt")]
        self.assertEqual(cap_evidence(events, "rigor"), [2])


class TestBuildRatings(unittest.TestCase):
    def _events(self):
        return [
            ev(1, "student", text="a closed set must be bounded", intent="attempt", established=[]),
            ev(2, "misconception", hint=0, tag="closed-implies-bounded", axis="conceptual"),
            ev(3, "student", hint=1, text="a hint please", intent="hint_request"),
            ev(4, "student", hint=1, text="so it is compact", intent="attempt", established=["C1"]),
        ]

    def test_defaults_to_the_ceiling_with_cli_attached_evidence(self):
        r = build_ratings(self._events())
        self.assertEqual(set(r), set(AXES))
        self.assertEqual(r["conceptual"]["rating"], DEV)          # unresolved misconception on the conceptual axis
        self.assertEqual(r["rigor"]["rating"], PROF)              # hint level 1 only
        self.assertEqual(r["conceptual"]["evidence"], [2, 3])
        self.assertEqual(r["rigor"]["evidence"], [3])

    def test_agent_can_lower_but_not_raise(self):
        events = self._events()
        r = build_ratings(events, {"rigor": (DEV, "sloppy notation throughout")})
        self.assertEqual(r["rigor"]["rating"], DEV)
        self.assertEqual(r["rigor"]["why"], "sloppy notation throughout")
        with self.assertRaises(RatingRejected) as ctx:
            build_ratings(events, {"conceptual": (PROF, "they got there in the end")})
        self.assertIn("cannot raise", str(ctx.exception))

    def test_unknown_axis_and_rating_rejected(self):
        with self.assertRaises(RatingRejected):
            build_ratings(self._events(), {"style": (DEV, "x")})
        with self.assertRaises(RatingRejected):
            build_ratings(self._events(), {"rigor": ("Excellent", "x")})
```

```python
# append to tests/agent/tutor/test_tutor_render_profile.py
class TestRenderVerifiedSteps(unittest.TestCase):
    def test_summary_lists_confirmed_steps_with_student_quotes(self):
        events = EVENTS + [Event(id=7, ts="t", type="verify", part="q1", data={"clean": True, "check": [
            {"step": 1, "status": "confirmed", "quote": "I think the set is bounded"},
            {"step": 2, "status": "confirmed", "quote": "it is one minus the sum"}]})]
        s = render_summary(events, PACKET, "bp", [], "2026-10-08")
        self.assertIn("Verified steps", s)
        self.assertIn('step 1: "I think the set is bounded"', s)
        self.assertIn('step 2: "it is one minus the sum"', s)

    def test_no_verified_steps_block_without_a_clean_verify(self):
        self.assertNotIn("Verified steps", render_summary(EVENTS, PACKET, "bp", [], "2026-10-08"))
```

- [ ] **Step 2: Run to verify it fails**

Run: `& $PY -m pytest tests/agent/tutor/test_tutor_ratings.py tests/agent/tutor/test_tutor_render_profile.py -q`
Expected: FAIL (`ImportError: cannot import name 'build_ratings'`; render test fails on missing "Verified steps").

- [ ] **Step 3: Implement `ratings.py`**

```python
# agent/tutor/ratings.py  (replace the whole file)
"""ratings.py -- evidence-capped tri-axial rating (v1 spec §5, v1.1 §9). Ratings
default to the highest rating the event log supports; the agent may only lower
one. The CLI attaches the evidence itself, so an unrelated quote can no longer
be cited for an axis."""
from __future__ import annotations

from agent.tutor.events import Event

AXES = ("conceptual", "rigor", "directness")
RATINGS = ("Developing / Needs Review", "Proficient", "Mastered")  # ascending


class RatingRejected(ValueError):
    pass


def ceiling(part_events: list[Event], axis: str) -> tuple[str, list[str]]:
    applies = lambda e, key: e.data.get(key, "all") in (axis, "all")
    max_hint = max((e.hint_level for e in part_events), default=0)
    miscs = [e for e in part_events if e.type == "misconception" and applies(e, "axis")]
    resolved_tags = {e.data["tag"] for e in part_events if e.type == "misconception_resolved"}
    unresolved = [e for e in miscs if e.data["tag"] not in resolved_tags]
    gaps = [e for e in part_events if e.type == "student" and e.data.get("admits_gap") and applies(e, "gap_axis")]

    reasons = []
    if max_hint >= 2:
        reasons.append(f"hint level reached {max_hint}")
    if unresolved:
        reasons.append("unresolved misconception(s): " + ", ".join(sorted({e.data['tag'] for e in unresolved})))
    if gaps:
        reasons.append("student stated they did not understand")
    if reasons:
        return RATINGS[0], reasons
    if max_hint == 0 and not miscs:
        return RATINGS[2], []
    why = []
    if max_hint == 1:
        why.append("hint level reached 1")
    if miscs:
        why.append("a misconception occurred (resolved)")
    return RATINGS[1], why


def cap_evidence(part_events: list[Event], axis: str) -> list[int]:
    applies = lambda e, key: e.data.get(key, "all") in (axis, "all")
    ids = [e.id for e in part_events
           if e.type == "student" and e.intent in ("stuck", "hint_request") and e.hint_level >= 1]
    ids += [e.id for e in part_events if e.type == "misconception" and applies(e, "axis")]
    ids += [e.id for e in part_events if e.type == "student" and e.data.get("admits_gap") and applies(e, "gap_axis")]
    if not ids:
        ids = [e.id for e in part_events if e.type == "student" and e.data.get("established")]
    if not ids:
        ids = [e.id for e in part_events if e.type == "student"][-1:]
    return sorted(set(ids))


def build_ratings(part_events: list[Event], downgrades: dict | None = None) -> dict:
    downgrades = downgrades or {}
    unknown = set(downgrades) - set(AXES)
    if unknown:
        raise RatingRejected(f"unknown axis in downgrade: {sorted(unknown)}; expected {list(AXES)}")
    out = {}
    for axis in AXES:
        cap, _ = ceiling(part_events, axis)
        rating, why = cap, None
        if axis in downgrades:
            want, why = downgrades[axis]
            if want not in RATINGS:
                raise RatingRejected(f"axis {axis!r}: rating {want!r} is not one of {list(RATINGS)}")
            if RATINGS.index(want) > RATINGS.index(cap):
                raise RatingRejected(f"axis {axis!r}: cannot raise {want!r} above the evidence ceiling {cap!r}")
            rating = want
        out[axis] = {"rating": rating, "evidence": cap_evidence(part_events, axis)}
        if why:
            out[axis]["why"] = why
    return out
```

- [ ] **Step 4: Implement the render edit**

In `agent/tutor/render.py`, replace

```python
            lines.append(f"- **{AXIS_NAMES[a]} — {r[a]['rating']}**: {ev_text}")
        lines.append("")
```

with

```python
            lines.append(f"- **{AXIS_NAMES[a]} — {r[a]['rating']}**: {ev_text}")
        verify = next((e for e in events if e.type == "verify" and e.part == part.part_id and e.data.get("clean")), None)
        if verify:
            lines.append("- **Verified steps** (student words):")
            for entry in verify.data["check"]:
                lines.append(f'  - step {entry["step"]}: "{entry.get("quote", "")}"')
        lines.append("")
```

- [ ] **Step 5: Run to verify it passes**

Run: `& $PY -m pytest tests/agent/tutor/test_tutor_ratings.py tests/agent/tutor/test_tutor_render_profile.py tests/agent/tutor/test_tutor_fsm.py tests/agent/tutor/test_tutor_lint.py tests/agent/tutor/test_tutor_packet.py tests/agent/tutor/test_tutor_prep.py tests/agent/tutor/test_tutor_claims.py tests/agent/tutor/test_tutor_ledger.py tests/agent/tutor/test_tutor_events.py -q`
Expected: all passed. (`test_tutor_session.py`, `test_tutor_cli.py`, `test_tutor_audit.py`, `test_tutor_regression.py` are expected red until Tasks 8-11.)

- [ ] **Step 6: Commit**

```powershell
git add agent/tutor/ratings.py agent/tutor/render.py tests/agent/tutor/test_tutor_ratings.py tests/agent/tutor/test_tutor_render_profile.py
git commit -m "feat(tutor): ratings default to the ceiling with CLI-attached evidence"
```

---

### Task 8: Session — `turn`, `say`, `verify`

**Files:**
- Modify: `agent/tutor/session.py` (replace whole file)
- Test: `tests/agent/tutor/test_tutor_session.py` (replace whole file)

**Interfaces:**
- Consumes: everything from Tasks 1-7.
- Produces:
  - `class Refused(ValueError)` with `.next_commands: list[str]`; `split_steps(section) -> list[str]`.
  - `Session.start(paths, now=None)`, `Session.open(paths, session_id=None)` (as v1), `Session.view() -> dict` (= the brief).
  - `Session.turn(intent, text, *, admits_gap=None, establish=None, establish_quote=None, flag_slip=None, slip_quote=None, resolve=None, resolve_quote=None, define_term=None) -> dict` (the brief; plus `definition`, or `definition_error` and `terms`).
  - `Session.say(text, check=False) -> dict`: `{"ok": True, "send": text, **brief}` after logging, `{"ok": True, "checked": True}` for a clean dry run, or `{"ok": False, "violations": [...], "message": ...}`.
  - `Session.verify(check=None, downgrades=None) -> dict`: without `check`, releases the part's solution steps once (`{"ok": True, "released": True, "steps": [{"n", "text"}], "instructions"}`); with `check` (a list of `{step, status, quote?, note?, tag?, axis?}`), either closes the part (`{**brief, "closed": True}`) or returns `{**brief, "closed": False, "defects": [...], "unresolved": [tags]}`.
  - `Session.end(big_picture) -> dict` (as v1).
  - Removed: `student`, `verdict`, `misconception`, `close_part`, `define`, `sealed`.
- Brief keys: `ok, session, state, part_id, label, part_index, n_parts, hint_level, statement, chat_statement, claims_established, route_coverage, pitfalls_hit, verify_available, solution_released, rules, next, prior_gaps`; plus `launch_text` in `LAUNCH`, `object_terms` at hint level 2, `next_claim_text` at level 3.
- Event semantics: `turn` logs a `student` event (`data`: `hint_capped`, `made_progress`, `established`, optional `admits_gap`/`gap_axis`), then `misconception` events for newly hit pitfalls (`data`: `tag`, `axis`, `pitfall`, `msg` = the student event id), then any manual `establish` / `misconception` (`manual`) / `misconception_resolved` (`manual`) events, then automatic `misconception_resolved` (`auto`) events when a pitfall's `resolved_by` claim has been established at or after the message that triggered it. A clean `verify` logs `verify` (`clean: true`, `check`) then `close_part` (`ratings`).

- [ ] **Step 1: Write the failing test**

```python
# tests/agent/tutor/test_tutor_session.py  (replace the whole file)
import datetime
import json
import os
import tempfile
import unittest

from agent.tutor.events import EventLog
from agent.tutor.paths import TutorPaths
from agent.tutor.sample_packet import write_sample_packet
from agent.tutor.session import Refused, Session, split_steps

NOW = datetime.datetime(2026, 10, 8, 10, 0)
DEV, PROF, MAST = "Developing / Needs Review", "Proficient", "Mastered"

M1 = "the probabilities of everything in the set sum to 1"                    # q1 C1
M2 = "walking away is whatever is left over when nothing else is chosen"       # q1 C2
M3 = "so it is one minus the sum of the others"                                # q1 C3 (and C1)
PM = "I would multiply the probabilities of the other options"                 # q1 pitfall P1
N1 = "all the non-positive numbers are indifferent to each other"              # q2 C1
N2 = "so any representing function is flat up to zero and then strictly increasing"   # q2 C2
N3 = "a flat then increasing function cannot be concave"                       # q2 C3
CHECK_Q1 = [{"step": 1, "status": "confirmed", "quote": M3}, {"step": 2, "status": "confirmed", "quote": M2}]
CHECK_Q2 = [{"step": 1, "status": "confirmed", "quote": N1}, {"step": 2, "status": "confirmed", "quote": N2},
            {"step": 3, "status": "confirmed", "quote": N3}]
CHECKIN = "Right. Do you have any lingering questions, or are you ready to move on?"


def make(tmp):
    paths = TutorPaths(tmp, "microecon", "homework_4")
    write_sample_packet(paths)
    return paths, Session.start(paths, now=NOW)


def codes(result):
    return {v["code"] for v in result.get("violations", [])}


def cover_q1(s):
    s.turn("attempt", M2)
    return s.turn("attempt", M3)


def to_level_three(s):
    s.turn("stuck", "I am stuck")              # level 1
    s.turn("hint_request", "a hint please")    # level 2
    s.turn("attempt", "I do not know")         # failed attempt 1
    s.turn("attempt", "still not sure")        # failed attempt 2
    return s.turn("stuck", "please help")      # level 3


class TestSplitSteps(unittest.TestCase):
    def test_headings_paragraphs_and_preamble(self):
        self.assertEqual(split_steps("### Step 1\na\n\n### Step 2\nb"), ["### Step 1\na", "### Step 2\nb"])
        self.assertEqual(split_steps("first para\n\nsecond para"), ["first para", "second para"])
        self.assertEqual(split_steps("intro\n### Step 1\na"), ["intro", "### Step 1\na"])


class TestStartAndResume(unittest.TestCase):
    def test_start_shows_the_short_launch_the_statement_and_no_claim_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths, s = make(tmp)
            v = s.view()
            self.assertEqual((v["state"], v["part_id"], v["session"]), ("LAUNCH", "q1", "2026-10-08-1000"))
            self.assertEqual(v["launch_text"], "Question 1. How would you like to approach this problem?")
            self.assertIn("Choice overload", v["statement"])
            blob = json.dumps(v)
            for claim in s.packet.claims["q1"].claims:
                self.assertNotIn(claim.text, blob)          # claim texts never appear in the brief at level 0
            self.assertTrue(os.path.exists(os.path.join(paths.sessions_dir, "2026-10-08-1000", "events.jsonl")))

    def test_restart_mid_part_gives_an_identical_brief(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths, s = make(tmp)
            s.turn("stuck", "no idea")
            s.turn("attempt", "nobody else picks it so it is the default", establish="C2", establish_quote="nobody else picks it")
            s.turn("attempt", M1)
            again = Session.start(paths, now=NOW + datetime.timedelta(hours=1))
            self.assertEqual(again._brief(), s._brief())
            self.assertEqual(again.view()["claims_established"], ["C2", "C1"])
            self.assertEqual(again.view()["hint_level"], 1)

    def test_new_session_after_finished_one_gets_new_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths, s = make(tmp)
            sid = s.view()["session"]
            EventLog(os.path.join(paths.sessions_dir, sid, "events.jsonl")).append("session_end", state="DONE")
            self.assertEqual(Session.start(paths, now=NOW).view()["session"], sid + "-2")

    def test_unvalidated_packet_refused_and_open_without_session_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = TutorPaths(tmp, "microecon", "homework_4")
            write_sample_packet(paths)
            with self.assertRaises(ValueError):
                Session.open(paths)
            with open(os.path.join(paths.packet_dir, "sealed", "solution.md"), "a", encoding="utf-8") as f:
                f.write("\nedit")
            with self.assertRaises(Exception) as ctx:
                Session.start(paths, now=NOW)
            self.assertIn("prep-submit", str(ctx.exception))


class TestTurn(unittest.TestCase):
    def test_turn_updates_state_ledger_and_progress_flags(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            b = s.turn("attempt", "I really am not sure where to begin")
            self.assertEqual((b["state"], b["claims_established"]), ("WORKING", []))
            self.assertFalse(s.log.load()[-1].data["made_progress"])
            b = s.turn("attempt", M2)
            self.assertEqual(b["claims_established"], ["C2"])
            self.assertEqual(b["route_coverage"], {"A": "1/3"})
            self.assertEqual(s.log.load()[-1].data["established"], ["C2"])
            self.assertFalse(b["verify_available"])

    def test_hint_level_rises_only_on_student_request_and_is_capped(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            self.assertEqual(s.turn("attempt", "first try")["hint_level"], 0)
            self.assertEqual(s.turn("stuck", "I'm stuck")["hint_level"], 1)
            self.assertEqual(s.turn("attempt", "another try")["hint_level"], 1)
            self.assertEqual(s.turn("hint_request", "a hint?")["hint_level"], 2)
            self.assertEqual(s.turn("stuck", "more please")["hint_level"], 2)      # level 3 not yet open
            self.assertTrue(s.log.load()[-1].data["hint_capped"])

    def test_level_two_and_three_briefs_release_only_what_the_level_allows(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            s.turn("stuck", "I am stuck")
            b = s.turn("hint_request", "a hint please")
            self.assertEqual(b["object_terms"], ["the probabilities in the menu"])
            self.assertNotIn("next_claim_text", b)
            s.turn("attempt", "I do not know")
            s.turn("attempt", "still not sure")
            b = s.turn("stuck", "please help")
            self.assertEqual(b["hint_level"], 3)
            self.assertEqual(b["next_claim_text"], "the choice probabilities in a menu sum to one")

    def test_pitfall_is_logged_surfaced_and_auto_resolved_by_the_resolving_claim(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            b = s.turn("attempt", PM)
            self.assertEqual([p["tag"] for p in b["pitfalls_hit"]], ["multiplies-instead-of-subtracting"])
            self.assertIn("add up to", b["pitfalls_hit"][0]["repair_question"])
            self.assertIn("Socratically", b["rules"])
            miscs = [e for e in s.log.load() if e.type == "misconception"]
            self.assertEqual((miscs[0].data["pitfall"], miscs[0].data["axis"]), ("P1", "rigor"))
            b = s.turn("attempt", M3)
            self.assertEqual(b["pitfalls_hit"], [])
            resolved = [e for e in s.log.load() if e.type == "misconception_resolved"]
            self.assertTrue(resolved[0].data["auto"])

    def test_a_slip_after_the_resolving_claim_is_not_auto_resolved(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            s.turn("attempt", M3)
            b = s.turn("attempt", PM)
            self.assertEqual(len(b["pitfalls_hit"]), 1)

    def test_define_request_returns_the_glossary_entry_and_is_not_a_claim(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            b = s.turn("define_request", "what is the sum of choice overload, one total?", define_term="Choice Overload")
            self.assertIn("less likely to choose anything", b["definition"])
            self.assertEqual(b["claims_established"], [])
            self.assertTrue(s.say(b["definition"])["ok"])
            self.assertFalse(s.say("It means d gets chosen more.")["ok"])
            b = s.turn("define_request", "what is a flurb?", define_term="flurb")
            self.assertIn("flurb", b["definition_error"])
            self.assertIn("choice overload", b["terms"])

    def test_empty_text_and_bad_manual_actions_log_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            s.turn("attempt", "some words about nobody picking it")
            n = len(s.log.load())
            for kwargs in (
                dict(text="   "),
                dict(text="x y z", establish="C9", establish_quote="x y"),
                dict(text="x y z", establish="C2", establish_quote="words nobody wrote"),
                dict(text="x y z", flag_slip="oops", slip_quote="words nobody wrote"),
                dict(text="x y z", resolve="never-flagged", resolve_quote="x y"),
                dict(text="ready", intent="confirm_advance", establish="C2", establish_quote="ready"),
            ):
                kwargs.setdefault("intent", "attempt")
                with self.subTest(kwargs=kwargs):
                    with self.assertRaises(ValueError):
                        s.turn(**kwargs)
                    self.assertEqual(len(s.log.load()), n)

    def test_manual_establish_slip_and_resolve_are_logged_with_quotes(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            s.turn("attempt", "nobody else picks it so it is the default")
            b = s.turn("other", "I mean exactly that", establish="C2", establish_quote="nobody else picks it")
            self.assertEqual(b["claims_established"], ["C2"])
            b = s.turn("attempt", "walking away is just sort of unknown", flag_slip="invented-tag:conceptual", slip_quote="sort of unknown")
            self.assertEqual([p["tag"] for p in b["pitfalls_hit"]], ["invented-tag"])
            self.assertIsNone(b["pitfalls_hit"][0]["repair_question"])
            b = s.turn("attempt", "oh I see now", resolve="invented-tag", resolve_quote="I see now")
            self.assertEqual(b["pitfalls_hit"], [])
            kinds = [(e.type, bool(e.data.get("manual"))) for e in s.log.load() if e.type in ("establish", "misconception", "misconception_resolved")]
            self.assertEqual(kinds, [("establish", False), ("misconception", True), ("misconception_resolved", True)])

    def test_confirm_advance_before_the_part_is_closed_is_refused_with_next_steps(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            s.turn("attempt", "working on it")
            n = len(s.log.load())
            with self.assertRaises(Refused) as ctx:
                s.turn("confirm_advance", "ready to move on")
            self.assertTrue(ctx.exception.next_commands)
            self.assertNotIn("verify first", str(ctx.exception))
            self.assertEqual(len(s.log.load()), n)
            cover_q1(s)
            with self.assertRaises(Refused) as ctx:
                s.turn("confirm_advance", "ready to move on")
            self.assertIn("Run verify", str(ctx.exception))


class TestSay(unittest.TestCase):
    def test_launch_line_ok_and_extras_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            launch = s.view()["launch_text"]
            self.assertTrue(s.say(launch)["ok"])
            r = s.say(launch + " Assume the first option is better.")
            self.assertFalse(r["ok"])
            self.assertEqual(r["violations"][0]["code"], "LAUNCH_NOT_VERBATIM")

    def test_unreached_claim_is_blocked_until_the_student_reaches_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            s.turn("attempt", M1)
            leak = "Walking away is whatever remains when nothing else is chosen."
            r = s.say(leak, check=True)
            self.assertIn("REVEALS_CLAIM", codes(r))
            self.assertTrue(any("C2" in v["detail"] for v in r["violations"]))
            self.assertFalse(any("probabilities in a menu" in v["detail"] for v in r["violations"]))   # ids only, never claim text
            good = "You said the probabilities of everything in the set sum to 1. What happens when she walks away?"
            self.assertTrue(s.say(good, check=True)["ok"])

    def test_question_form_at_level_zero_and_one_but_not_at_level_three(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            s.turn("attempt", "I think we start from the menu")
            self.assertIn("QUESTION_FORM", codes(s.say("What do you mean? And why?", check=True)))
            to_level_three(s)
            self.assertNotIn("QUESTION_FORM", codes(s.say("What do you mean? And why?", check=True)))

    def test_level_three_exempts_only_the_next_claim(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            to_level_three(s)
            ok = s.say("The probabilities of everything in the set sum to 1, so what comes next?", check=True)
            self.assertTrue(ok["ok"])
            bad = s.say("So it is one minus the sum of the others.", check=True)
            self.assertIn("REVEALS_CLAIM", codes(bad))
            self.assertTrue(any("C3" in v["detail"] for v in bad["violations"]))
            self.assertFalse(any("C1" in v["detail"] for v in bad["violations"]))

    def test_check_logs_nothing_and_a_rejection_is_logged_but_not_a_tutor_turn(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            s.turn("attempt", "hm")
            n = len(s.log.load())
            self.assertEqual(s.say("What did you try?", check=True), {"ok": True, "checked": True})
            self.assertEqual(len(s.log.load()), n)
            s.say("Use contradiction here.")
            types = [e.type for e in s.log.load()]
            self.assertIn("lint_reject", types)
            self.assertNotIn("tutor_say", types)


class TestVerify(unittest.TestCase):
    def test_refused_before_coverage_and_nothing_is_released(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            s.turn("attempt", M2)
            with self.assertRaises(Refused) as ctx:
                s.verify()
            self.assertIn("every claim on one route", str(ctx.exception))
            self.assertNotIn("verify_release", [e.type for e in s.log.load()])

    def test_release_once_then_check_file_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            b = cover_q1(s)
            self.assertTrue(b["verify_available"])
            r = s.verify()
            self.assertEqual([st["n"] for st in r["steps"]], [1, 2])
            self.assertIn("none of the other alternatives", r["steps"][1]["text"])
            self.assertTrue(s.view()["solution_released"])
            with self.assertRaises(Refused) as ctx:
                s.verify()
            self.assertIn("already released", str(ctx.exception))

    def test_check_before_release_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            cover_q1(s)
            with self.assertRaises(Refused):
                s.verify(CHECK_Q1)

    def test_bad_check_files_are_refused_and_close_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            cover_q1(s)
            s.verify()
            n = len(s.log.load())
            bad_files = [
                [{"step": 1, "status": "confirmed", "quote": M3}],                                         # step 2 missing
                [{"step": 1, "status": "confirmed", "quote": "words the student never wrote"}, CHECK_Q1[1]],  # fabricated quote
                [{"step": 1, "status": "confirmed"}, CHECK_Q1[1]],                                          # no quote
                [{"step": 1, "status": "wrong"}, CHECK_Q1[1]],                                              # defect without a note
                [{"step": 1, "status": "fine", "quote": M3}, CHECK_Q1[1]],                                  # unknown status
                [CHECK_Q1[0], CHECK_Q1[0], CHECK_Q1[1]],                                                    # duplicate step
                [{"step": 3, "status": "confirmed", "quote": M3}, CHECK_Q1[1]],                             # out-of-range step
                "not a list",
            ]
            for check in bad_files:
                with self.subTest(check=check):
                    with self.assertRaises(ValueError):
                        s.verify(check)
                    self.assertEqual(len(s.log.load()), n)
            self.assertEqual(s.view()["state"], "WORKING")

    def test_clean_check_closes_the_part_with_ceiling_ratings_and_cli_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            cover_q1(s)
            s.verify()
            r = s.verify(CHECK_Q1)
            self.assertTrue(r["closed"])
            self.assertEqual(r["state"], "VERIFIED")
            close = [e for e in s.log.load() if e.type == "close_part"][0]
            ratings = close.data["ratings"]
            self.assertEqual({a: v["rating"] for a, v in ratings.items()}, {"conceptual": MAST, "rigor": MAST, "directness": MAST})
            self.assertTrue(all(v["evidence"] for v in ratings.values()))
            self.assertEqual([e.type for e in s.log.load()][-2:], ["verify", "close_part"])

    def test_agent_can_lower_a_rating_but_not_raise_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            s.turn("stuck", "I am stuck")                                  # hint level 1: ceiling is Proficient
            cover_q1(s)
            s.verify()
            with self.assertRaises(ValueError):
                s.verify(CHECK_Q1, {"rigor": (MAST, "they were great")})
            self.assertEqual(s.view()["state"], "WORKING")
            r = s.verify(CHECK_Q1, {"rigor": (DEV, "uneven notation")})
            self.assertTrue(r["closed"])
            close = [e for e in s.log.load() if e.type == "close_part"][0]
            self.assertEqual(close.data["ratings"]["rigor"]["rating"], DEV)
            self.assertEqual(close.data["ratings"]["rigor"]["why"], "uneven notation")
            self.assertEqual(close.data["ratings"]["conceptual"]["rating"], PROF)

    def test_a_defect_reopens_work_and_a_resolved_defect_caps_at_proficient(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            cover_q1(s)
            s.verify()
            bad = [CHECK_Q1[0], {"step": 2, "status": "wrong", "note": "treats the others as multiplied",
                                 "tag": "multiplied-others", "axis": "rigor"}]
            r = s.verify(bad)
            self.assertFalse(r["closed"])
            self.assertEqual((r["state"], [d["step"] for d in r["defects"]]), ("WORKING", [2]))
            types = [e.type for e in s.log.load()]
            self.assertIn("defect", types)
            miscs = [e for e in s.log.load() if e.type == "misconception"]
            self.assertTrue(miscs[-1].data["defect"])
            with self.assertRaises(Refused):
                s.verify()                                              # the solution is released only once
            r2 = s.verify(CHECK_Q1)                                     # all steps confirmed but the defect is unresolved
            self.assertFalse(r2["closed"])
            self.assertEqual(r2["unresolved"], ["multiplied-others"])
            s.turn("attempt", "ah the others are subtracted not multiplied", resolve="multiplied-others",
                   resolve_quote="subtracted not multiplied")
            r3 = s.verify(CHECK_Q1)
            self.assertTrue(r3["closed"])
            close = [e for e in s.log.load() if e.type == "close_part"][0]
            self.assertEqual(close.data["ratings"]["rigor"]["rating"], PROF)

    def test_manual_establish_can_cover_a_route_but_needs_a_real_quote(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            s.turn("attempt", M3)                                       # C1, C3
            s.turn("attempt", "nobody else picks it so it is the default")
            self.assertFalse(s.view()["verify_available"])
            s.turn("other", "as I said", establish="C2", establish_quote="nobody else picks it")
            self.assertTrue(s.view()["verify_available"])
            self.assertEqual(len(s.verify()["steps"]), 2)


class TestFullFlow(unittest.TestCase):
    def test_two_parts_to_end_with_check_in_and_cross_part_quote_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths, s = make(tmp)
            self.assertTrue(s.say(s.view()["launch_text"])["ok"])
            cover_q1(s)
            s.verify()
            self.assertTrue(s.verify(CHECK_Q1)["closed"])
            self.assertFalse(s.say("Correct.")["ok"])                   # no check-in question
            r = s.say(CHECKIN)
            self.assertEqual((r["ok"], r["state"], r["part_id"]), (True, "AWAITING_ADVANCE", "q1"))
            b = s.turn("has_questions", "why does this matter for microeconomics?")
            self.assertEqual(b["state"], "AWAITING_ADVANCE")            # a side question does not reopen the closed part
            b = s.turn("confirm_advance", "ready, next one")
            self.assertEqual((b["state"], b["part_id"], b["hint_level"]), ("LAUNCH", "q2", 0))
            self.assertEqual(b["claims_established"], [])               # the confirm message is not a claim
            self.assertTrue(s.say(b["launch_text"])["ok"])
            for msg in (N1, N2, N3):
                s.turn("attempt", msg)
            s.verify()
            with self.assertRaises(ValueError):                         # a quote from part 1 does not count in part 2
                s.verify([dict(CHECK_Q2[0], quote=M3), CHECK_Q2[1], CHECK_Q2[2]])
            self.assertTrue(s.verify(CHECK_Q2)["closed"])
            self.assertTrue(s.say(CHECKIN)["ok"])
            self.assertEqual(s.turn("confirm_advance", "done, thanks")["state"], "SYNTHESIS")
            out = s.end("Big picture text.")
            for key in ("transcript", "summary", "profile"):
                self.assertTrue(os.path.exists(out[key]), key)
            with open(out["summary"], encoding="utf-8") as f:
                summary = f.read()
            self.assertIn("Verified steps", summary)
            self.assertEqual(s.log.load()[-1].type, "session_end")
            with self.assertRaises(Refused):
                s.turn("attempt", "more")
            with self.assertRaises(Refused):
                s.say("hello")

    def test_end_requires_synthesis(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            with self.assertRaises(Refused):
                s.end("too early")
```

- [ ] **Step 2: Run to verify it fails**

Run: `& $PY -m pytest tests/agent/tutor/test_tutor_session.py -q`
Expected: FAIL `ImportError: cannot import name 'Refused'`.

- [ ] **Step 3: Implement**

```python
# agent/tutor/session.py  (replace the whole file)
"""session.py -- ties the FSM, ledger, lint, ratings, packet and persistence together
(v1.1 §4-§7). Stateless: every method replays events.jsonl, so a CLI process can exit
between calls and state is identical on reload."""
from __future__ import annotations

import os
import re
from datetime import datetime

from agent.tutor import fsm
from agent.tutor.claims import AXES_ALL
from agent.tutor.events import Event, EventLog
from agent.tutor.fsm import (
    AWAITING_ADVANCE, LAUNCH, SYNTHESIS, VERIFIED, WORKING, FsmState, IllegalTransition, replay, student_event,
)
from agent.tutor.ledger import IGNORED_INTENTS, build_ledger, next_claim
from agent.tutor.lint import lint_message
from agent.tutor.packet import Packet, load_packet, read_solution, sealed_section
from agent.tutor.paths import TutorPaths
from agent.tutor.profile import load_profile, open_gaps, save_profile, update_profile
from agent.tutor.ratings import build_ratings
from agent.tutor.render import write_session_docs

CHECK_STATUSES = ("confirmed", "missing", "wrong")

_NEXT = {
    LAUNCH: ["say (send the launch line)", "turn (once the student replies)"],
    WORKING: ["turn (the student's next message)", "say (your reply)", "verify (only when verify_available is true)"],
    VERIFIED: ["say (the check-in question)"],
    AWAITING_ADVANCE: ["turn (the student's reply)", "say (answer a question)"],
    SYNTHESIS: ["say (closing message)", "end --big-picture-file F"],
}
_LEVEL_RULES = {
    0: "Level 0: no hints. Ask what the student is thinking.",
    1: "Level 1: a Socratic check only (what definition or intuition applies?). No direction yet.",
    2: "Level 2: you may point at the object to think about (see object_terms) but not the relation or computation.",
    3: "Level 3 (last resort): you may state the next claim (next_claim_text) and nothing beyond it.",
}


class Refused(ValueError):
    """A command the gate will not run now; carries the legal next commands."""

    def __init__(self, message: str, next_commands):
        super().__init__(message)
        self.next_commands = list(next_commands)


def _norm(text: str | None) -> str:
    return " ".join((text or "").split())


def split_steps(section: str) -> list[str]:
    lines = section.splitlines()
    heading = re.compile(r"^#{3,}\s")
    if any(heading.match(l) for l in lines):
        steps, cur = [], []
        for line in lines:
            if heading.match(line) and cur:
                steps.append("\n".join(cur).strip())
                cur = [line]
            else:
                cur.append(line)
        steps.append("\n".join(cur).strip())
        return [s for s in steps if s]
    return [p.strip() for p in re.split(r"\n\s*\n", section) if p.strip()]


class Session:
    def __init__(self, paths: TutorPaths, session_id: str, packet: Packet):
        self.paths, self.session_id, self.packet = paths, session_id, packet
        self.dir = os.path.join(paths.sessions_dir, session_id)
        self.log = EventLog(os.path.join(self.dir, "events.jsonl"))
        self._solution = read_solution(paths.packet_dir)

    # ---- construction -------------------------------------------------
    @staticmethod
    def _is_open(paths: TutorPaths, sid: str) -> bool:
        events = EventLog(os.path.join(paths.sessions_dir, sid, "events.jsonl")).load()
        return bool(events) and not any(e.type == "session_end" for e in events)

    @classmethod
    def _latest_open(cls, paths: TutorPaths) -> str | None:
        if not os.path.isdir(paths.sessions_dir):
            return None
        for sid in sorted(os.listdir(paths.sessions_dir), reverse=True):
            if cls._is_open(paths, sid):
                return sid
        return None

    @classmethod
    def start(cls, paths: TutorPaths, now: datetime | None = None) -> "Session":
        packet = load_packet(paths)
        sid = cls._latest_open(paths)
        if sid is None:
            base = (now or datetime.now()).strftime("%Y-%m-%d-%H%M")
            sid, n = base, 1
            while os.path.exists(os.path.join(paths.sessions_dir, sid)):
                n += 1
                sid = f"{base}-{n}"
            session = cls(paths, sid, packet)
            session.log.append("session_start", part=packet.parts[0].part_id, state=LAUNCH,
                               data={"problem_set": paths.problem_set})
        else:
            session = cls(paths, sid, packet)
        session._write_prior_gaps()
        return session

    @classmethod
    def open(cls, paths: TutorPaths, session_id: str | None = None) -> "Session":
        packet = load_packet(paths)
        sid = session_id or cls._latest_open(paths)
        if sid is None:
            raise ValueError("no open session; run start first")
        return cls(paths, sid, packet)

    # ---- helpers ------------------------------------------------------
    def _prior_gaps(self) -> list[str]:
        tags = {t for p in self.packet.parts for t in p.concept_tags}
        return [g for g in open_gaps(load_profile(self.paths.profile_json)) if g in tags]

    def _write_prior_gaps(self) -> None:
        gaps = self._prior_gaps()
        text = "# Prior gaps (informational; never a source of hints)\n\n" + (
            "\n".join(f"- `{g}`" for g in gaps) if gaps else "- None") + "\n"
        with open(os.path.join(self.paths.packet_dir, "prior_gaps.md"), "w", encoding="utf-8") as f:
            f.write(text)

    def _fsm(self, events: list[Event] | None = None) -> FsmState:
        return replay(self.log.load() if events is None else events, len(self.packet.parts))

    @staticmethod
    def _require_live(s: FsmState) -> None:
        if s.state == fsm.DONE:
            raise Refused("session has ended; start a new session", ["start"])

    @staticmethod
    def _part_events(events: list[Event], part_id: str) -> list[Event]:
        return [e for e in events if e.part == part_id]

    @staticmethod
    def _closed(events: list[Event], part_id: str) -> bool:
        return any(e.type == "close_part" and e.part == part_id for e in events)

    @staticmethod
    def _released(pe: list[Event]) -> bool:
        return any(e.type == "verify_release" for e in pe)

    @staticmethod
    def _unresolved(pe: list[Event]) -> list[Event]:
        resolved = {e.data["tag"] for e in pe if e.type == "misconception_resolved"}
        seen, out = set(), []
        for e in pe:
            tag = e.data.get("tag") if e.type == "misconception" else None
            if tag and tag not in resolved and tag not in seen:
                out.append(e)
                seen.add(tag)
        return out

    def _form_active(self, s: FsmState, pe: list[Event]) -> bool:
        return s.state == WORKING and (s.hint_level <= 1 or (self._released(pe) and s.hint_level < 3))

    def _rules(self, s: FsmState, ledger, unresolved: list[Event], form: bool) -> str:
        if s.state == LAUNCH:
            return "Send ONLY launch_text through say, then wait for the student."
        if s.state == SYNTHESIS:
            return "All parts are closed. Write the big-picture synthesis and run end."
        if s.state == VERIFIED:
            return ("The part is closed. Say the check-in: ask whether they have lingering questions or are ready to "
                    "move on. Do not mention the next part.")
        if s.state == AWAITING_ADVANCE:
            return ("Answer any question briefly under the usual rules. Do not mention the next part until the "
                    "student asks to move on.")
        bits = []
        if unresolved:
            bits.append("First surface the slip Socratically with the repair_question in pitfalls_hit; do not state the correction.")
        bits.append(_LEVEL_RULES[s.hint_level])
        if form:
            bits.append("Reply with at most ONE question (60 words max) plus at most one sentence restating the "
                        "student's own words; introduce no idea the student has not said.")
        if ledger.covered:
            bits.append("Every claim on a route is established: call verify.")
        return " ".join(bits)

    def _brief(self, events: list[Event] | None = None, definition: str | None = None) -> dict:
        events = self.log.load() if events is None else events
        s = self._fsm(events)
        part = self.packet.parts[s.part_index]
        pc = self.packet.claims[part.part_id]
        pe = self._part_events(events, part.part_id)
        ledger = build_ledger(pc, pe)
        unresolved = self._unresolved(pe)
        by_tag = {p.tag: p for p in pc.pitfalls}
        out = {
            "ok": True, "session": self.session_id, "state": s.state, "part_id": part.part_id,
            "label": part.label or part.part_id, "part_index": s.part_index, "n_parts": len(self.packet.parts),
            "hint_level": s.hint_level, "statement": part.statement, "chat_statement": part.chat_statement,
            "claims_established": ledger.established,
            "route_coverage": {r: f"{n}/{total}" for r, (n, total) in ledger.route_progress.items()},
            "pitfalls_hit": [{"tag": e.data["tag"],
                              "repair_question": by_tag[e.data["tag"]].repair_question if e.data["tag"] in by_tag else None}
                             for e in unresolved],
            "verify_available": s.state == WORKING and ledger.covered,
            "solution_released": self._released(pe),
            "rules": self._rules(s, ledger, unresolved, self._form_active(s, pe)),
            "next": _NEXT.get(s.state, []), "prior_gaps": self._prior_gaps(),
        }
        if s.state == LAUNCH:
            out["launch_text"] = part.launch_text()
        nxt = next_claim(pc, ledger)
        if s.state == WORKING and nxt is not None:
            if s.hint_level == 2:
                out["object_terms"] = list(nxt.object_terms)
            if s.hint_level >= 3:
                out["next_claim_text"] = nxt.text
        if definition:
            out["definition"] = definition
        return out

    def view(self) -> dict:
        return self._brief()

    # ---- turn ---------------------------------------------------------
    def turn(self, intent: str, text: str, *, admits_gap: str | None = None, establish: str | None = None,
             establish_quote: str | None = None, flag_slip: str | None = None, slip_quote: str | None = None,
             resolve: str | None = None, resolve_quote: str | None = None, define_term: str | None = None) -> dict:
        if not (text or "").strip():
            raise ValueError("student text is empty; pass the student's verbatim message")
        events = self.log.load()
        s = self._fsm(events)
        self._require_live(s)
        part = self.packet.parts[s.part_index]
        pc = self.packet.claims[part.part_id]
        pe = self._part_events(events, part.part_id)
        virtual = None if intent in IGNORED_INTENTS else text
        prev = build_ledger(pc, pe)
        now = build_ledger(pc, pe, extra_student_text=virtual)
        newly = [c for c in now.established if c not in prev.established]

        manual = any(x is not None for x in (establish, flag_slip, resolve))
        if manual and intent == "confirm_advance":
            raise ValueError("manual establish / flag-slip / resolve cannot be combined with confirm_advance")
        texts = [_norm(e.text) for e in pe if e.type == "student"] + [_norm(text)]
        quote_ok = lambda q: bool(_norm(q)) and any(_norm(q) in t for t in texts)
        if establish is not None:
            if establish not in {c.id for c in pc.claims}:
                raise ValueError(f"unknown claim id {establish!r}; known ids: {sorted(c.id for c in pc.claims)}")
            if not quote_ok(establish_quote):
                raise ValueError("--establish needs --establish-quote: words the student actually wrote in this part")
        if flag_slip is not None and not quote_ok(slip_quote):
            raise ValueError("--flag-slip needs --slip-quote: words the student actually wrote in this part")
        if resolve is not None:
            if resolve not in {e.data["tag"] for e in self._unresolved(pe)}:
                raise ValueError(f"no unresolved misconception tagged {resolve!r}")
            if not quote_ok(resolve_quote):
                raise ValueError("--resolve needs --resolve-quote: words the student actually wrote in this part")

        try:
            new, info = student_event(s, intent, len(self.packet.parts), bool(newly))
        except IllegalTransition as err:
            extra = " Run verify first; a clean verify closes the part." if s.state == WORKING and prev.covered else ""
            raise Refused(str(err) + extra, _NEXT.get(s.state, [])) from err

        part_id = self.packet.parts[new.part_index].part_id
        data = dict(info)
        data["made_progress"] = bool(newly)
        data["established"] = newly
        if admits_gap:
            data.update(admits_gap=True, gap_axis=admits_gap)
        student_ev = self.log.append("student", part=part_id, state=new.state, hint_level=new.hint_level,
                                     intent=intent, text=text, data=data)
        if part_id == part.part_id:
            common = dict(part=part_id, state=new.state, hint_level=new.hint_level)
            for p in pc.pitfalls:
                if p.id in now.pitfalls_hit and p.id not in prev.pitfalls_hit and virtual is not None:
                    self.log.append("misconception", data={"tag": p.tag, "axis": p.axis, "pitfall": p.id,
                                                           "msg": student_ev.id}, **common)
            if establish is not None:
                self.log.append("establish", data={"claim": establish, "quote": establish_quote}, **common)
            if flag_slip is not None:
                tag, _, axis = flag_slip.partition(":")
                self.log.append("misconception", data={"tag": tag, "axis": axis or "all", "manual": True,
                                                       "quote": slip_quote, "msg": student_ev.id}, **common)
            if resolve is not None:
                self.log.append("misconception_resolved", data={"tag": resolve, "axis": "all", "manual": True,
                                                                "quote": resolve_quote}, **common)
            self._auto_resolve(part, pc, new)

        definition, definition_error = None, None
        if define_term:
            for key, d in self.packet.glossary.items():
                if key.lower() == define_term.strip().lower():
                    definition = d
                    self.log.append("define", part=part_id, state=new.state, hint_level=new.hint_level,
                                    data={"term": key, "definition": d})
                    break
            else:
                definition_error = f"no glossary entry for {define_term!r}"
        brief = self._brief(definition=definition)
        if definition_error:
            brief["definition_error"] = definition_error
            brief["terms"] = sorted(self.packet.glossary)
        return brief

    def _auto_resolve(self, part, pc, st: FsmState) -> None:
        pe = self._part_events(self.log.load(), part.part_id)
        by_tag = {p.tag: p for p in pc.pitfalls}
        for e in self._unresolved(pe):
            p = by_tag.get(e.data["tag"])
            msg = e.data.get("msg")
            if p is None or not p.resolved_by or msg is None:
                continue
            after = build_ledger(pc, [x for x in pe if x.id >= msg])
            if p.resolved_by in after.established:
                self.log.append("misconception_resolved", part=part.part_id, state=st.state, hint_level=st.hint_level,
                                data={"tag": p.tag, "axis": p.axis, "auto": True})

    # ---- say ----------------------------------------------------------
    def say(self, text: str, check: bool = False) -> dict:
        events = self.log.load()
        s = self._fsm(events)
        self._require_live(s)
        part = self.packet.parts[s.part_index]
        pc = self.packet.claims[part.part_id]
        pe = self._part_events(events, part.part_id)
        ledger = build_ledger(pc, pe)
        student_text = " ".join(e.text or "" for e in pe if e.type == "student")
        last_student = next((e for e in reversed(events) if e.type == "student"), None)
        last_text = (last_student.text or "") if last_student else ""
        allowed = [part.launch_text()] if s.state == LAUNCH else []
        after_define = bool(last_student and last_student.intent == "define_request")
        if after_define:
            for e in reversed(events):
                if e.type == "define":
                    allowed.append(e.data["definition"])
                    break
                if e.type == "student":
                    break
        forbidden = []
        nxt_index = s.part_index + 1
        if s.state in (VERIFIED, AWAITING_ADVANCE) and nxt_index < len(self.packet.parts):
            n = self.packet.parts[nxt_index]
            forbidden = [rf"\b{re.escape(n.part_id)}\b"] + ([rf"\b{re.escape(n.label)}\b"] if n.label else [])
        blocked = {}
        if s.state == WORKING:
            nc = next_claim(pc, ledger)
            for c in pc.claims:
                if c.id in ledger.established or (s.hint_level >= 3 and nc is not None and c.id == nc.id):
                    continue
                blocked[c.id] = c.recognizer
        violations = lint_message(
            text, state=s.state, hint_level=s.hint_level, student_text=student_text, statement=part.statement,
            sealed_solution=sealed_section(self._solution, part.part_id) or "", allowed_exact=allowed,
            after_define=after_define, forbidden_patterns=forbidden, blocked_claims=blocked,
            form=self._form_active(s, pe), last_student_text=last_text,
        )
        if violations:
            payload = [v.to_dict() for v in violations]
            if not check:
                self.log.append("lint_reject", part=part.part_id, state=s.state, hint_level=s.hint_level, text=text,
                                data={"violations": payload})
            return {"ok": False, "violations": payload,
                    "message": "Revise the draft and call say again. Send nothing to the student until it returns ok."}
        if check:
            return {"ok": True, "checked": True}
        checkin = s.state == VERIFIED
        new = fsm.checkin_event(s) if checkin else s
        self.log.append("tutor_say", part=part.part_id, state=new.state, hint_level=new.hint_level, text=text,
                        data={"checkin": checkin})
        return {**self._brief(), "send": text}

    # ---- verify -------------------------------------------------------
    def _validate_check(self, check, n_steps: int, pe: list[Event]) -> list[dict]:
        if not isinstance(check, list) or not check:
            raise ValueError("the check file must be a non-empty JSON list of {step, status, quote, note}")
        texts = [_norm(e.text) for e in pe if e.type == "student"]
        seen, entries = [], []
        for item in check:
            if not isinstance(item, dict):
                raise ValueError("each check entry must be an object")
            step, status = item.get("step"), item.get("status")
            if not isinstance(step, int) or isinstance(step, bool) or not 1 <= step <= n_steps:
                raise ValueError(f"step must be an integer from 1 to {n_steps}")
            if step in seen:
                raise ValueError(f"step {step} appears more than once")
            if status not in CHECK_STATUSES:
                raise ValueError(f"step {step}: status must be one of {list(CHECK_STATUSES)}")
            quote, note = _norm(item.get("quote")), _norm(item.get("note"))
            if status == "confirmed":
                if not quote or not any(quote in t for t in texts):
                    raise ValueError(f"step {step}: a confirmed step needs a quote that appears in this part's student messages")
            elif not note:
                raise ValueError(f"step {step}: a {status} step needs a note about the student's step")
            axis = item.get("axis", "rigor")
            if axis not in AXES_ALL:
                raise ValueError(f"step {step}: axis must be one of {list(AXES_ALL)}")
            entry = {"step": step, "status": status, "quote": quote, "note": note, "axis": axis}
            if item.get("tag"):
                entry["tag"] = str(item["tag"])
            seen.append(step)
            entries.append(entry)
        missing = sorted(set(range(1, n_steps + 1)) - set(seen))
        if missing:
            raise ValueError(f"missing check entries for steps {missing}")
        return sorted(entries, key=lambda e: e["step"])

    def verify(self, check=None, downgrades: dict | None = None) -> dict:
        events = self.log.load()
        s = self._fsm(events)
        self._require_live(s)
        part = self.packet.parts[s.part_index]
        pc = self.packet.claims[part.part_id]
        pe = self._part_events(events, part.part_id)
        if s.state != WORKING:
            raise Refused(f"verify is only valid while the part is being worked (state is {s.state})", _NEXT.get(s.state, []))
        ledger = build_ledger(pc, pe)
        if not ledger.covered:
            raise Refused("verify is available only when every claim on one route has been established by the student "
                          "(recognized in their messages, or established with a quote)", ["turn", "say"])
        released = self._released(pe)
        steps = split_steps(sealed_section(self._solution, part.part_id) or "")
        if check is None:
            if released:
                raise Refused("the solution was already released for this part; submit your step check with "
                              "verify --check-file", ["verify --check-file F"])
            self.log.append("verify_release", part=part.part_id, state=s.state, hint_level=s.hint_level)
            return {"ok": True, "released": True,
                    "steps": [{"n": i + 1, "text": t} for i, t in enumerate(steps)],
                    "instructions": ("For EVERY step write one entry {step, status: confirmed|missing|wrong, quote, note}. "
                                     "A confirmed step needs a quote of the student's own words from this part; a "
                                     "missing or wrong step needs a note about the student's step (not the solution). "
                                     "Do not quote or outline these steps to the student.")}
        if not released:
            raise Refused("run verify without --check-file first to receive the solution steps", ["verify"])
        entries = self._validate_check(check, len(steps), pe)
        defects = [e for e in entries if e["status"] != "confirmed"]
        unresolved = [e.data["tag"] for e in self._unresolved(pe)]
        common = dict(part=part.part_id, hint_level=s.hint_level)
        if not defects and not unresolved:
            ratings = build_ratings(pe, downgrades)            # may raise before anything is logged
            self.log.append("verify", state=VERIFIED, data={"clean": True, "check": entries}, **common)
            self.log.append("close_part", state=VERIFIED, data={"ratings": ratings}, **common)
            return {**self._brief(), "closed": True}
        self.log.append("verify", state=WORKING, data={"clean": False, "check": entries}, **common)
        for d in defects:
            tag = d.get("tag") or f"defect-step-{d['step']}"
            self.log.append("defect", state=WORKING, data={"step": d["step"], "status": d["status"], "note": d["note"],
                                                           "quote": d["quote"]}, **common)
            self.log.append("misconception", state=WORKING, data={"tag": tag, "axis": d["axis"], "defect": True}, **common)
        unresolved_now = [e.data["tag"] for e in self._unresolved(self._part_events(self.log.load(), part.part_id))]
        return {**self._brief(), "closed": False, "defects": defects, "unresolved": unresolved_now}

    # ---- end ----------------------------------------------------------
    def end(self, big_picture: str) -> dict:
        events = self.log.load()
        s = self._fsm(events)
        self._require_live(s)
        if s.state != SYNTHESIS:
            raise Refused(f"cannot end from state {s.state}; finish and close every part first", _NEXT.get(s.state, []))
        missing = [p.part_id for p in self.packet.parts if not self._closed(events, p.part_id)]
        if missing:
            raise Refused(f"parts not closed: {missing}", ["verify"])
        last = self.packet.parts[-1].part_id
        self.log.append("synthesis", part=last, state=SYNTHESIS, text=big_picture)
        self.log.append("session_end", part=last, state=fsm.DONE)
        events = self.log.load()
        date = self.session_id[:10]
        transcript, summary = write_session_docs(self.dir, events, self.packet, big_picture, self._prior_gaps(), date)
        profile = update_profile(load_profile(self.paths.profile_json), session_id=self.session_id, date=date,
                                 events=events, packet=self.packet)
        save_profile(self.paths.profile_json, self.paths.profile_md, profile)
        return {"ok": True, "transcript": transcript, "summary": summary, "profile": self.paths.profile_json}
```

- [ ] **Step 4: Run to verify it passes**

Run: `& $PY -m pytest tests/agent/tutor/test_tutor_session.py -q`
Expected: all passed. Likely trouble spots, in order: (1) a `say` draft in the tests unexpectedly tripping the 6-word sealed-overlap rule (the failure names the code; adjust the test draft, not the rule); (2) `test_level_three_exempts_only_the_next_claim`: confirm `next_claim` returns C1 when nothing is established (all routes at 0, tie goes to route A); (3) if `kinds` in `test_manual_establish_slip_and_resolve_are_logged_with_quotes` has an extra `misconception` entry, a pitfall recognizer matched one of the test messages: change the message wording.

- [ ] **Step 5: Run the files that must be green so far**

Run: `& $PY -m pytest tests/agent/tutor --ignore=tests/agent/tutor/test_tutor_cli.py --ignore=tests/agent/tutor/test_tutor_audit.py --ignore=tests/agent/tutor/test_tutor_regression.py -q`
Expected: all passed.

- [ ] **Step 6: Commit**

```powershell
git add agent/tutor/session.py tests/agent/tutor/test_tutor_session.py
git commit -m "feat(tutor): session turn/say/verify over the claim ledger"
```

---

### Task 9: Audit for v1.1 events

**Files:**
- Modify: `agent/tutor/audit.py` (replace whole file)
- Test: `tests/agent/tutor/test_tutor_audit.py` (replace whole file)

**Interfaces:**
- Produces: `audit(events, packet) -> list[Finding]` with v1's codes (`ADVANCE_WITHOUT_CONFIRM`, `HINT_JUMP`, `SEALED_EARLY` for old logs, `INTENT_MISMATCH`, `UNANSWERED_STUDENT_TURN`, `RATING_OVER_CEILING`) plus `MANUAL_OVERRIDE` (every manual `establish`, manual `misconception`, manual `misconception_resolved`) and `VERIFY_WITHOUT_COVERAGE` (a `verify_release` when the ledger was not covered at that point; skipped when the packet has no claims for the part).

- [ ] **Step 1: Write the failing test**

```python
# tests/agent/tutor/test_tutor_audit.py  (replace the whole file)
import datetime
import tempfile
import unittest

from agent.tutor.audit import audit
from agent.tutor.events import Event
from agent.tutor.packet import Packet, Part
from agent.tutor.paths import TutorPaths
from agent.tutor.sample_packet import write_sample_packet
from agent.tutor.session import Session

NOW = datetime.datetime(2026, 10, 8, 10, 0)
M2 = "walking away is whatever is left over when nothing else is chosen"
M3 = "so it is one minus the sum of the others"


def codes(findings):
    return [f.code for f in findings]


def ev(i, type, part="q1", **kw):
    data = kw.pop("data", {})
    return Event(id=i, ts="t", type=type, part=part, data=data, **kw)


def make(tmp):
    paths = TutorPaths(tmp, "microecon", "homework_4")
    write_sample_packet(paths)
    return Session.start(paths, now=NOW)


class TestAudit(unittest.TestCase):
    def test_clean_session_has_no_findings(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = make(tmp)
            s.say(s.view()["launch_text"])
            s.turn("attempt", M2)
            s.say("You said walking away is whatever is left over. What else is true?")
            self.assertEqual(audit(s.log.load(), s.packet), [])

    def test_unanswered_student_turn_flags_possible_bypass(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = make(tmp)
            s.turn("attempt", "first")
            s.turn("attempt", "second")            # no tutor say in between
            self.assertEqual(codes(audit(s.log.load(), s.packet)), ["UNANSWERED_STUDENT_TURN"])

    def test_manual_overrides_are_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = make(tmp)
            s.turn("attempt", "nobody else picks it so it is the default", establish="C2", establish_quote="nobody else picks it")
            s.say("You said nobody else picks it, so it is the default. What follows?")
            s.turn("attempt", "walking away is sort of unknown", flag_slip="invented", slip_quote="sort of unknown")
            s.say("You said walking away is sort of unknown. What do you mean?")
            s.turn("attempt", "oh I see now", resolve="invented", resolve_quote="I see now")
            found = audit(s.log.load(), s.packet)
            self.assertEqual(codes(found).count("MANUAL_OVERRIDE"), 3)

    def test_verify_release_without_coverage_is_flagged_and_with_coverage_is_not(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = make(tmp)
            s.turn("attempt", M2)
            s.say("You said walking away is whatever is left over. What else is true?")
            s.log.append("verify_release", part="q1", state="WORKING")          # forced past the gate
            self.assertIn("VERIFY_WITHOUT_COVERAGE", codes(audit(s.log.load(), s.packet)))
        with tempfile.TemporaryDirectory() as tmp:
            s = make(tmp)
            s.turn("attempt", M2)
            s.say("You said walking away is whatever is left over. What else is true?")
            s.turn("attempt", M3)
            s.say("You said it is one minus the sum of the others. Why does that hold?")
            s.verify()
            self.assertNotIn("VERIFY_WITHOUT_COVERAGE", codes(audit(s.log.load(), s.packet)))

    def test_tampered_log_findings(self):
        events = [
            ev(1, "session_start"),
            ev(2, "sealed", data={"kind": "solution"}),                                  # v1 log: before any attempt
            ev(3, "student", text="I like pizza", intent="confirm_advance"),            # label contradicts text
            ev(4, "tutor_say", text="ok"),
            ev(5, "student", part="q2", text="hmm", intent="attempt"),                   # part change without confirm_advance
            ev(6, "tutor_say", part="q2", text="ok"),
            ev(7, "student", part="q2", text="a", intent="attempt", hint_level=2),       # hint 0 -> 2 on an attempt
            ev(8, "tutor_say", part="q2", text="ok"),
            ev(9, "close_part", part="q2", hint_level=2, data={"ratings": {
                a: {"rating": "Mastered", "evidence": [7]} for a in ("conceptual", "rigor", "directness")}}),
        ]
        packet = Packet("c", "p", [Part("q1", "s", ["t"], ["e"]), Part("q2", "s", ["t"], ["e"])], {}, {})
        found = codes(audit(events, packet))
        for expected in ("SEALED_EARLY", "INTENT_MISMATCH", "ADVANCE_WITHOUT_CONFIRM", "HINT_JUMP", "RATING_OVER_CEILING"):
            self.assertIn(expected, found)
```

- [ ] **Step 2: Run to verify it fails**

Run: `& $PY -m pytest tests/agent/tutor/test_tutor_audit.py -q`
Expected: FAIL (the manual-override and coverage tests; the old `Session.student` calls are gone).

- [ ] **Step 3: Implement**

```python
# agent/tutor/audit.py  (replace the whole file)
"""audit.py -- re-lints a finished (or in-progress) session from its log (v1 spec §7,
v1.1 §10). The stand-in for the hard file-access wall the user declined: drift
becomes visible even when it was not blocked. UNANSWERED_STUDENT_TURN is a proxy for
'the agent replied without calling say' because the CLI cannot observe the chat.
It never decides whether an answer is correct."""
from __future__ import annotations

import re
from dataclasses import dataclass

from agent.tutor.events import Event
from agent.tutor.ledger import build_ledger
from agent.tutor.packet import Packet
from agent.tutor.ratings import RATINGS, ceiling

_CONFIRM_WORDS = re.compile(r"move on|next|ready|continue|go ahead|yes|\bok\b|okay|sure|proceed|done|good", re.I)
_STUCK_WORDS = re.compile(r"stuck|help|hint|don't know|do not know|not sure|no idea|lost|confus", re.I)


@dataclass(frozen=True)
class Finding:
    code: str
    event_id: int
    detail: str

    def to_dict(self) -> dict:
        return {"code": self.code, "event_id": self.event_id, "detail": self.detail}


def audit(events: list[Event], packet: Packet) -> list[Finding]:
    found: list[Finding] = []
    prev_part, prev_level = None, 0
    pending: Event | None = None
    for e in events:
        if e.part and prev_part and e.part != prev_part and not (e.type == "student" and e.intent == "confirm_advance"):
            found.append(Finding("ADVANCE_WITHOUT_CONFIRM", e.id, f"moved from {prev_part} to {e.part} without a student confirm_advance"))
        if e.part and e.part == prev_part and e.hint_level > prev_level:
            ok = e.type == "student" and e.intent in ("stuck", "hint_request") and e.hint_level - prev_level == 1
            if not ok:
                found.append(Finding("HINT_JUMP", e.id, f"hint level rose {prev_level}->{e.hint_level} without a single-step student request"))
        if e.part:
            prev_part, prev_level = e.part, e.hint_level
        if e.type == "sealed":          # v1 logs only
            attempted = any(x.type == "student" and x.part == e.part and x.intent == "attempt" and x.id < e.id for x in events)
            if not attempted:
                found.append(Finding("SEALED_EARLY", e.id, "sealed content released before any student attempt on this part"))
        if e.type == "verify_release":
            pc = packet.claims.get(e.part) if packet.claims else None
            if pc is not None:
                before = [x for x in events if x.part == e.part and x.id < e.id]
                if not build_ledger(pc, before).covered:
                    found.append(Finding("VERIFY_WITHOUT_COVERAGE", e.id, "the solution was released before a route was covered"))
        if e.type == "establish":
            found.append(Finding("MANUAL_OVERRIDE", e.id, f"claim {e.data.get('claim')} was established manually"))
        if e.type in ("misconception", "misconception_resolved") and e.data.get("manual"):
            found.append(Finding("MANUAL_OVERRIDE", e.id, f"{e.type.replace('_', ' ')} '{e.data.get('tag')}' was entered manually"))
        if e.type == "student":
            if e.intent == "confirm_advance" and not _CONFIRM_WORDS.search(e.text or ""):
                found.append(Finding("INTENT_MISMATCH", e.id, "labelled confirm_advance but the text does not ask to move on"))
            if e.intent in ("stuck", "hint_request") and not _STUCK_WORDS.search(e.text or ""):
                found.append(Finding("INTENT_MISMATCH", e.id, f"labelled {e.intent} but the text does not ask for help"))
            if pending is not None:
                found.append(Finding("UNANSWERED_STUDENT_TURN", pending.id, "no tutor say before the next student turn"))
            pending = None if e.state == "SYNTHESIS" else e
        elif e.type == "tutor_say":
            pending = None
        elif e.type == "close_part":
            part_events = [x for x in events if x.part == e.part and x.id < e.id]
            for axis, r in e.data["ratings"].items():
                cap, _ = ceiling(part_events, axis)
                if RATINGS.index(r["rating"]) > RATINGS.index(cap):
                    found.append(Finding("RATING_OVER_CEILING", e.id, f"{axis}: {r['rating']} exceeds ceiling {cap}"))
    if pending is not None and any(x.type == "session_end" for x in events):
        found.append(Finding("UNANSWERED_STUDENT_TURN", pending.id, "session ended with an unanswered student turn"))
    return found
```

- [ ] **Step 4: Run to verify it passes**

Run: `& $PY -m pytest tests/agent/tutor/test_tutor_audit.py tests/agent/tutor/test_tutor_session.py -q`
Expected: all passed. If `test_clean_session_has_no_findings` reports `UNANSWERED_STUDENT_TURN`, the `say` was rejected (a rejected draft is not a tutor turn): print the violations and reword the test draft.

- [ ] **Step 5: Commit**

```powershell
git add agent/tutor/audit.py tests/agent/tutor/test_tutor_audit.py
git commit -m "feat(tutor): audit flags manual overrides and verify without coverage"
```

---

### Task 10: CLI (`turn`, `say --stdin|--check`, `verify`) and bootstrap prompt

**Files:**
- Modify: `agent/tutor/cli.py` (replace whole file), `agent/tutor/bootstrap_prompt.md` (replace whole file)
- Test: `tests/agent/tutor/test_tutor_cli.py` (replace whole file)

**Interfaces:**
- Consumes: `Session`, `Refused`, `prep`, `audit`, `TutorPaths`, `RATINGS`.
- Produces: `main(argv=None) -> int`. Global options `--hub-root` (default `<repo>/ai-sandbox/academic-hub`), `--course`, `--problem-set`, `--session`. Commands: `prep-collect`, `prep-submit`, `start`, `turn`, `say`, `verify`, `end`, `audit`, `bootstrap`. Removed: `student`, `verdict`, `misconception`, `define`, `sealed`, `close-part`.
  - `turn --intent I (--stdin | --text-file F | --text T) [--admits-gap [axis]] [--define TERM] [--establish C --establish-quote Q] [--flag-slip TAG[:axis] --slip-quote Q] [--resolve TAG --resolve-quote Q]`
  - `say (--stdin | --text-file F | --text T) [--check]`
  - `verify [--check-file F] [--downgrade axis=rating ...] [--why TEXT]` (rating may be `developing`, `proficient` or `mastered`)
  - `end --big-picture-file F`
- Output is JSON on stdout (UTF-8); exit 0 when `ok`, else 2. Every error is `{"ok": false, "error": "...", "next": [...]}`; a `Refused` carries its own `next`, any other `ValueError`/`PacketError`/`OSError` gets a generic retry hint. Stdin and `--text-file` text has trailing newlines removed; `--text-file` is read as `utf-8-sig`.
- `bootstrap` prints `bootstrap_prompt.md` with `{PYTHON}`, `{RAG_DIR}`, `{HUB_ROOT}`, `{COURSE}`, `{PROBLEM_SET}` filled in.

- [ ] **Step 1: Write the failing test**

```python
# tests/agent/tutor/test_tutor_cli.py  (replace the whole file)
import contextlib
import io
import json
import os
import tempfile
import unittest
from unittest import mock

from agent.tutor import cli
from agent.tutor.paths import TutorPaths
from agent.tutor.sample_packet import write_sample_packet

M2 = "walking away is whatever is left over when nothing else is chosen"
M3 = "so it is one minus the sum of the others"
N1 = "all the non-positive numbers are indifferent to each other"
N2 = "so any representing function is flat up to zero and then strictly increasing"
N3 = "a flat then increasing function cannot be concave"
GOOD_Q = "You said walking away is whatever is left over. What else is true?"
CHECKIN = "Right. Do you have any lingering questions, or are you ready to move on?"


def run(tmp, *args, stdin=None):
    out = io.StringIO()
    argv = ["--hub-root", tmp, "--course", "microecon", "--problem-set", "homework_4", *args]
    with contextlib.redirect_stdout(out):
        if stdin is None:
            code = cli.main(argv)
        else:
            with mock.patch("sys.stdin", io.StringIO(stdin)):
                code = cli.main(argv)
    return code, json.loads(out.getvalue())


def events(tmp, session):
    path = os.path.join(TutorPaths(tmp, "microecon", "homework_4").sessions_dir, session, "events.jsonl")
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


class TestCli(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.t = self.tmp.name
        write_sample_packet(TutorPaths(self.t, "microecon", "homework_4"))

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, name, content):
        path = os.path.join(self.t, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    def test_start_shows_the_short_launch(self):
        code, v = run(self.t, "start")
        self.assertEqual((code, v["state"]), (0, "LAUNCH"))
        self.assertEqual(v["launch_text"], "Question 1. How would you like to approach this problem?")

    def test_turn_via_stdin_round_trips_unicode_quotes_and_latex_and_strips_the_newline(self):
        run(self.t, "start")
        msg = 'Is $x \\succeq y$ transitive? She said "maybe" — ≽ γ(b)'
        code, v = run(self.t, "turn", "--intent", "attempt", "--stdin", stdin=msg + "\r\n")
        self.assertEqual((code, v["state"]), (0, "WORKING"))
        logged = [e for e in events(self.t, v["session"]) if e["type"] == "student"][0]
        self.assertEqual(logged["text"], msg)

    def test_turn_via_text_file_accepts_a_bom(self):
        run(self.t, "start")
        path = os.path.join(self.t, "m.txt")
        with open(path, "w", encoding="utf-8-sig") as f:
            f.write("≽ with a byte order mark\n")
        code, v = run(self.t, "turn", "--intent", "attempt", "--text-file", path)
        self.assertEqual(code, 0)
        logged = [e for e in events(self.t, v["session"]) if e["type"] == "student"][0]
        self.assertEqual(logged["text"], "≽ with a byte order mark")

    def test_say_violation_exits_2_and_check_logs_nothing(self):
        _, v = run(self.t, "start")
        run(self.t, "turn", "--intent", "attempt", "--stdin", stdin="hm")
        n = len(events(self.t, v["session"]))
        code, r = run(self.t, "say", "--stdin", "--check", stdin="Try proof by contradiction.")
        self.assertEqual(code, 2)
        self.assertFalse(r["ok"])
        self.assertIn("TECHNIQUE", {x["code"] for x in r["violations"]})
        self.assertEqual(len(events(self.t, v["session"])), n)              # --check logs nothing
        code, r = run(self.t, "say", "--stdin", stdin="Try proof by contradiction.")
        self.assertEqual(code, 2)
        self.assertIn("lint_reject", [e["type"] for e in events(self.t, v["session"])])

    def test_errors_carry_a_next_list(self):
        run(self.t, "start")
        code, v = run(self.t, "turn", "--intent", "confirm_advance", "--stdin", stdin="next")
        self.assertEqual(code, 2)
        self.assertFalse(v["ok"])
        self.assertIn("confirm_advance", v["error"])
        self.assertTrue(v["next"])
        code, v = run(self.t, "turn", "--intent", "attempt", "--stdin", "--establish", "C9", "--establish-quote", "x", stdin="x y")
        self.assertEqual(code, 2)
        self.assertIn("unknown claim id", v["error"])
        self.assertTrue(v["next"])

    def test_define_flow(self):
        run(self.t, "start")
        code, v = run(self.t, "turn", "--intent", "define_request", "--stdin", "--define", "choice overload",
                      stdin="what is choice overload?")
        self.assertEqual(code, 0)
        self.assertIn("less likely to choose anything", v["definition"])

    def test_removed_v1_commands_are_gone(self):
        for old in ("student", "verdict", "misconception", "define", "sealed", "close-part"):
            with self.subTest(command=old):
                with contextlib.redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit):
                        run(self.t, old)

    def test_two_part_session_through_verify_and_end(self):
        _, v = run(self.t, "start")
        sid = v["session"]
        self.assertEqual(run(self.t, "say", "--stdin", stdin=v["launch_text"])[0], 0)
        run(self.t, "turn", "--intent", "attempt", "--stdin", stdin=M2)
        self.assertEqual(run(self.t, "say", "--stdin", stdin=GOOD_Q)[0], 0)
        _, b = run(self.t, "turn", "--intent", "attempt", "--stdin", stdin=M3)
        self.assertTrue(b["verify_available"])
        code, rel = run(self.t, "verify")
        self.assertEqual((code, len(rel["steps"])), (0, 2))
        check = self.write("check1.json", json.dumps([{"step": 1, "status": "confirmed", "quote": M3},
                                                      {"step": 2, "status": "confirmed", "quote": M2}]))
        code, done = run(self.t, "verify", "--check-file", check, "--downgrade", "rigor=proficient", "--why", "notation was loose")
        self.assertEqual((code, done["closed"]), (0, True))
        close = [e for e in events(self.t, sid) if e["type"] == "close_part"][0]
        self.assertEqual(close["data"]["ratings"]["rigor"]["rating"], "Proficient")
        self.assertEqual(close["data"]["ratings"]["rigor"]["why"], "notation was loose")
        self.assertEqual(run(self.t, "say", "--stdin", stdin=CHECKIN)[1]["state"], "AWAITING_ADVANCE")
        _, b = run(self.t, "turn", "--intent", "confirm_advance", "--stdin", stdin="ready, next one")
        self.assertEqual((b["state"], b["part_id"]), ("LAUNCH", "q2"))
        self.assertEqual(run(self.t, "say", "--stdin", stdin=b["launch_text"])[0], 0)
        for msg in (N1, N2, N3):
            run(self.t, "turn", "--intent", "attempt", "--stdin", stdin=msg)
        run(self.t, "verify")
        check2 = self.write("check2.json", json.dumps([{"step": 1, "status": "confirmed", "quote": N1},
                                                       {"step": 2, "status": "confirmed", "quote": N2},
                                                       {"step": 3, "status": "confirmed", "quote": N3}]))
        self.assertTrue(run(self.t, "verify", "--check-file", check2)[1]["closed"])
        run(self.t, "say", "--stdin", stdin=CHECKIN)
        self.assertEqual(run(self.t, "turn", "--intent", "confirm_advance", "--stdin", stdin="done")[1]["state"], "SYNTHESIS")
        bp = self.write("bp.md", "The big picture.")
        code, out = run(self.t, "end", "--big-picture-file", bp)
        self.assertEqual(code, 0)
        self.assertTrue(os.path.exists(out["summary"]))
        self.assertEqual(run(self.t, "audit")[0], 0)

    def test_downgrade_errors_are_reported(self):
        run(self.t, "start")
        run(self.t, "turn", "--intent", "attempt", "--stdin", stdin=M2)
        run(self.t, "turn", "--intent", "attempt", "--stdin", stdin=M3)
        run(self.t, "verify")
        check = self.write("c.json", json.dumps([{"step": 1, "status": "confirmed", "quote": M3},
                                                 {"step": 2, "status": "confirmed", "quote": M2}]))
        code, v = run(self.t, "verify", "--check-file", check, "--downgrade", "rigor=proficient")
        self.assertEqual(code, 2)
        self.assertIn("--why", v["error"])
        code, v = run(self.t, "verify", "--check-file", check, "--downgrade", "rigor")
        self.assertEqual(code, 2)

    def test_prep_submit_validates_the_packet(self):
        code, v = run(self.t, "prep-submit")
        self.assertEqual((code, v), (0, {"ok": True}))

    def test_bootstrap_fills_placeholders(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cli.main(["--hub-root", "/H", "--course", "microecon", "--problem-set", "homework_4", "bootstrap"])
        text = out.getvalue()
        self.assertEqual(code, 0)
        self.assertIn("/H", text)
        self.assertIn("homework_4", text)
        for placeholder in ("{HUB_ROOT}", "{PYTHON}", "{RAG_DIR}", "{COURSE}", "{PROBLEM_SET}"):
            self.assertNotIn(placeholder, text)
        for must in ("turn", "say", "verify", "--stdin", "Set-Location"):
            self.assertIn(must, text)
```

- [ ] **Step 2: Run to verify it fails**

Run: `& $PY -m pytest tests/agent/tutor/test_tutor_cli.py -q`
Expected: FAIL (the v1 CLI has no `turn`; argparse exits).

- [ ] **Step 3: Implement `cli.py`**

```python
# agent/tutor/cli.py  (replace the whole file)
"""cli.py -- the command surface the live IDE agent calls every turn (v1.1 §5).
JSON on stdout, exit 0 when ok else 2. Run as
`python -m agent.tutor.cli --hub-root H --course C --problem-set PS <command> ...`."""
from __future__ import annotations

import argparse
import json
import os
import sys

from agent.tutor import audit as audit_mod
from agent.tutor import prep
from agent.tutor.fsm import INTENTS
from agent.tutor.packet import PacketError
from agent.tutor.paths import TutorPaths
from agent.tutor.ratings import RATINGS
from agent.tutor.session import Refused, Session

_RAG_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
_DEFAULT_HUB = os.path.normpath(os.path.join(_RAG_DIR, "..", "academic-hub"))
_RATING_ALIASES = {"developing": RATINGS[0], "proficient": RATINGS[1], "mastered": RATINGS[2]}
_RETRY = ["fix the arguments named in the error and retry the same command"]


def _read(path: str) -> str:
    with open(path, "r", encoding="utf-8-sig") as f:
        return f.read()


def _text(args) -> str:
    if getattr(args, "stdin", False):
        return sys.stdin.read().rstrip("\r\n")
    if getattr(args, "text_file", None):
        return _read(args.text_file).rstrip("\r\n")
    if getattr(args, "text", None) is not None:
        return args.text
    raise ValueError("provide --stdin, --text-file or --text")


def _downgrades(items, why):
    out = {}
    for item in items or []:
        axis, sep, rating = item.partition("=")
        if not sep:
            raise ValueError(f"--downgrade expects axis=rating, got {item!r}")
        if not why:
            raise ValueError("--downgrade needs --why: the reason for lowering the rating")
        out[axis.strip()] = (_RATING_ALIASES.get(rating.strip().lower(), rating.strip()), why)
    return out


def _add_text_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--stdin", action="store_true")
    p.add_argument("--text-file")
    p.add_argument("--text")


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Socratic tutor session gate.")
    p.add_argument("--hub-root", default=_DEFAULT_HUB)
    p.add_argument("--course", required=True)
    p.add_argument("--problem-set", required=True)
    p.add_argument("--session", default=None)
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("prep-collect")
    c.add_argument("--problem-set-file", required=True)
    c.add_argument("--question-ref", action="append", required=True)
    c.add_argument("--hints-file")
    c.add_argument("--solutions-file")
    c.add_argument("--force", action="store_true")
    sub.add_parser("prep-submit")
    sub.add_parser("start")

    t = sub.add_parser("turn")
    t.add_argument("--intent", required=True, choices=sorted(INTENTS))
    _add_text_args(t)
    t.add_argument("--admits-gap", nargs="?", const="all", default=None)
    t.add_argument("--define")
    t.add_argument("--establish")
    t.add_argument("--establish-quote")
    t.add_argument("--flag-slip")
    t.add_argument("--slip-quote")
    t.add_argument("--resolve")
    t.add_argument("--resolve-quote")

    sy = sub.add_parser("say")
    _add_text_args(sy)
    sy.add_argument("--check", action="store_true")

    v = sub.add_parser("verify")
    v.add_argument("--check-file")
    v.add_argument("--downgrade", action="append", default=[])
    v.add_argument("--why")

    e = sub.add_parser("end")
    e.add_argument("--big-picture-file", required=True)
    sub.add_parser("audit")
    sub.add_parser("bootstrap")
    return p


def _dispatch(args, paths: TutorPaths) -> dict:
    if args.cmd == "prep-collect":
        from core.env.gemini_utils import get_gemini_client, load_dotenv_override
        from agent.rag.rag_agent import retrieve_passages
        load_dotenv_override()
        client = get_gemini_client()
        if client is None:
            raise SystemExit(1)
        retrieve = lambda q: retrieve_passages([paths.hub_root], q, client, course=paths.course)
        return prep.collect(paths, args.problem_set_file, args.question_ref, retrieve,
                            hints_file=args.hints_file, solutions_file=args.solutions_file, force=args.force)
    if args.cmd == "prep-submit":
        return prep.submit(paths)
    if args.cmd == "bootstrap":
        template = _read(os.path.join(os.path.dirname(__file__), "bootstrap_prompt.md"))
        for key, value in (("{PYTHON}", sys.executable), ("{RAG_DIR}", _RAG_DIR), ("{HUB_ROOT}", paths.hub_root),
                           ("{COURSE}", paths.course), ("{PROBLEM_SET}", paths.problem_set)):
            template = template.replace(key, value)
        return {"ok": True, "_raw": template}
    if args.cmd == "start":
        return Session.start(paths).view()
    session = Session.open(paths, args.session)
    if args.cmd == "turn":
        return session.turn(
            args.intent, _text(args), admits_gap=args.admits_gap, establish=args.establish,
            establish_quote=args.establish_quote, flag_slip=args.flag_slip, slip_quote=args.slip_quote,
            resolve=args.resolve, resolve_quote=args.resolve_quote, define_term=args.define,
        )
    if args.cmd == "say":
        return session.say(_text(args), check=args.check)
    if args.cmd == "verify":
        check = json.loads(_read(args.check_file)) if args.check_file else None
        return session.verify(check, _downgrades(args.downgrade, args.why))
    if args.cmd == "end":
        return session.end(_read(args.big_picture_file))
    if args.cmd == "audit":
        return {"ok": True, "findings": [f.to_dict() for f in audit_mod.audit(session.log.load(), session.packet)]}
    raise ValueError(f"unknown command {args.cmd}")


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stdin):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    args = _build_parser().parse_args(argv)
    paths = TutorPaths(args.hub_root, args.course, args.problem_set)
    try:
        result = _dispatch(args, paths)
    except Refused as err:
        result = {"ok": False, "error": str(err), "next": err.next_commands}
    except (PacketError, ValueError, FileExistsError, OSError) as err:
        result = {"ok": False, "error": str(err), "next": list(_RETRY)}
    if "_raw" in result:
        print(result["_raw"])
        return 0
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Implement `bootstrap_prompt.md`**

````markdown
# Socratic tutor session — operating contract

You are the live tutor for ONE office-hours session. A local gate owns the session state and you must use it
every turn. Do not read the tutor's source code or anything under the packet folder: every error message tells
you what to do next, and trying to work around a rejection defeats the purpose of the session.

## The gate command (PowerShell)
Always run it in exactly this form (the `Set-Location` matters). Text goes in on stdin as a here-string; the
closing `'@` must start at column 0:

    $OutputEncoding = [Text.UTF8Encoding]::new($false); Set-Location "{RAG_DIR}"
    @'
    <the text>
    '@ | & "{PYTHON}" -m agent.tutor.cli --hub-root "{HUB_ROOT}" --course {COURSE} --problem-set {PROBLEM_SET} <command>

If math symbols (≽, γ, ℝ) come back as `?` in the brief or the log, write the text to a UTF-8 file and use
`--text-file <path>` instead of `--stdin`.

## Start, and the launch line
Run `start` once. In state LAUNCH send `launch_text` through `say`, exactly as given, then wait for the student.

## Every turn: two commands
1. `turn --intent <attempt|stuck|hint_request|define_request|confirm_advance|has_questions|other> --stdin` with the
   student's verbatim message. Add `--define "<term>"` when they ask what a term means, and `--admits-gap [axis]`
   when they say they do not understand something. Read the JSON brief: follow `rules`, use `next`, and use
   `statement` only to understand the problem (print it only if the student asks to see the question).
2. Write your reply and send it with `say --stdin`. Send the student ONLY the `send` text of an ok result. A
   rejection is normal: revise and call `say` again. `say --check` tests a draft without logging it. Never send
   text that did not come back ok.

## Finishing a part
When the brief says `verify_available`, run `verify` (no file). It returns the solution steps ONCE. Compare the
student's own words with each step, write a check file (JSON list, one entry per step) and run
`verify --check-file <file>`:

    [{"step": 1, "status": "confirmed", "quote": "<the student's own words>"},
     {"step": 2, "status": "wrong", "note": "<what is wrong in the student's step>"}]

A confirmed step needs a quote the student actually wrote in this part. Never quote, summarize or outline the
steps to the student. If the result is `closed: false`, keep tutoring from the defects under the usual rules (the
solution is not shown again). When it is `closed: true`, `say` the check-in: ask whether they have lingering
questions or are ready to move on. After the last part is closed and the student confirms, run
`end --big-picture-file <file>`.

## Moving on
Only a student message labelled `confirm_advance` moves to the next part. Do not mention the next part before
that.

## Manual overrides (rare, and audited)
- `--establish C --establish-quote "<student words>"`: the student clearly stated a claim in words the system
  could not match.
- `--flag-slip TAG[:axis] --slip-quote "<student words>"`: a slip the system did not catch.
- `--resolve TAG --resolve-quote "<student words>"`: the student has corrected a flagged slip.

## Hard rules
- Never name a proof technique before the student does. Never connect a definition to the problem's variables.
- At hint levels 0-1 ask ONE question and restate the student's own words; add no idea they have not said.
- Never open the packet folder or the tutor source. If `say` rejects a draft, change what you are saying; do not
  hunt for a wording that slips past the check.
- Use Unicode math in chat (≽, ≤, λ, ℝ). Be frank: struggle is information, not an insult.
````

- [ ] **Step 5: Run to verify it passes**

Run: `& $PY -m pytest tests/agent/tutor/test_tutor_cli.py tests/agent/tutor/test_tutor_session.py -q`
Expected: all passed.

- [ ] **Step 6: Smoke-test the PowerShell pipe on this machine (Unicode over stdin)**

The speed target depends on piping text through a PowerShell here-string without a temp file, and Windows PowerShell 5.1 can mangle non-ASCII on a pipe to a native program. Run this in the PowerShell tool and record the result:

```powershell
$PY = "C:\Users\theaa\ai-sandbox-master\ai-sandbox\academic-rag-model\.venv\Scripts\python.exe"
Set-Location "C:\Users\theaa\ai-sandbox-master\.worktrees\claude-tutor-v1-1-core\ai-sandbox\academic-rag-model"
$tmp = Join-Path $env:TEMP "tutor_smoke"
Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue
& $PY -c "from agent.tutor.paths import TutorPaths; from agent.tutor.sample_packet import write_sample_packet; write_sample_packet(TutorPaths(r'$tmp','microecon','homework_4'))"
$OutputEncoding = [Text.UTF8Encoding]::new($false)
$base = @('-m','agent.tutor.cli','--hub-root',$tmp,'--course','microecon','--problem-set','homework_4')
& $PY @base start | Out-Null
@'
x ≽ y and γ(b) in ℝ
'@ | & $PY @base turn --intent attempt --stdin | Out-Null
Get-Content (Join-Path $tmp 'academic_notes\microecon\tutoring\homework_4\sessions\*\events.jsonl') -Encoding UTF8 | Select-String 'x ≽ y and γ\(b\) in ℝ'
```

Expected: one matching line. If it does not match (the log holds `?`), change the contract text in `bootstrap_prompt.md` to make `--text-file` the default for any message containing non-ASCII, update `test_bootstrap_fills_placeholders` accordingly, and note the 2-vs-4 tool-call consequence in the status doc (Task 12).

- [ ] **Step 7: Commit**

```powershell
git add agent/tutor/cli.py agent/tutor/bootstrap_prompt.md tests/agent/tutor/test_tutor_cli.py
git commit -m "feat(tutor): turn/say/verify CLI with stdin, check mode and actionable errors"
```

---

### Task 11: Trial fixtures and the offline adversarial suite

**Files:**
- Test: `tests/agent/tutor/test_tutor_regression.py` (replace whole file)

**Interfaces:** consumes `Session`, `sample_packet` (parts `q1`, `q2`). No production code. This task is the offline half of spec §11: analogues of the HW4 trial's bad replies run against the sample packet's claims (the real HW4 replay needs the HW4 packet re-prepped with claims, which is a post-plan step), and the seven adversarial scenarios as far as they can run without the live agent. Tests marked "documented limit" assert behavior the design cannot prevent, so a future judge (spec §12) has a baseline.

- [ ] **Step 1: Write the tests**

```python
# tests/agent/tutor/test_tutor_regression.py  (replace the whole file)
"""Offline half of spec §11: trial-reply analogues and the seven adversarial scenarios.
Real HW4 replay needs the HW4 packet re-prepped with claims (post-plan step)."""
import datetime
import tempfile
import unittest

from agent.tutor.audit import audit
from agent.tutor.paths import TutorPaths
from agent.tutor.sample_packet import SAMPLES, write_sample_packet
from agent.tutor.session import Refused, Session

NOW = datetime.datetime(2026, 10, 8, 10, 0)
M1 = "the probabilities of everything in the set sum to 1"
M2 = "walking away is whatever is left over when nothing else is chosen"
M3 = "so it is one minus the sum of the others"
PM = "I would multiply the probabilities of the other options"
N1 = "all the non-positive numbers are indifferent to each other"
N2 = "so any representing function is flat up to zero and then strictly increasing"
N3 = "a flat then increasing function cannot be concave"
QUASI = "quasiconcave is the same as concave here so that works"
CHECKIN = "Right. Do you have any lingering questions, or are you ready to move on?"


def make(tmp):
    paths = TutorPaths(tmp, "microecon", "homework_4")
    write_sample_packet(paths)
    return Session.start(paths, now=NOW)


def codes(result):
    return {v["code"] for v in result.get("violations", [])}


def to_q2(s):
    s.turn("attempt", M2)
    s.turn("attempt", M3)
    s.verify()
    s.verify([{"step": 1, "status": "confirmed", "quote": M3}, {"step": 2, "status": "confirmed", "quote": M2}])
    s.say(CHECKIN)
    s.turn("confirm_advance", "ready, next one")


class TestTrialReplyAnalogues(unittest.TestCase):
    """Each analogue is the shape of a bad reply from the HW4 trial, against the sample claims."""

    def test_event_10_next_step_introduced_before_the_student_reached_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = make(tmp)
            s.turn("attempt", M1)
            s.turn("attempt", M2)
            r = s.say("Now, the walk-away probability is one minus the sum of the others, so how would you write it down?", check=True)
            self.assertIn("REVEALS_CLAIM", codes(r))

    def test_event_13_stepwise_scaffold_with_two_questions_at_level_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = make(tmp)
            s.turn("stuck", "I am stuck")
            r = s.say("First, the probabilities sum to 1. Next, what is left when nothing else is chosen? "
                      "And what operation turns that into the walk-away probability?", check=True)
            self.assertTrue({"REVEALS_CLAIM", "QUESTION_FORM"} <= codes(r))

    def test_event_36_telling_the_answer_and_the_method(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = make(tmp)
            s.turn("attempt", "I think walking away matters here")
            r = s.say("Yes, the walk-away probability is one minus the others; now work out how the sum changes.", check=True)
            self.assertTrue({"REVEALS_CLAIM", "QUESTION_FORM"} <= codes(r))

    def test_event_17_tutor_states_the_correction_instead_of_asking(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = make(tmp)
            b = s.turn("attempt", PM)
            self.assertEqual([p["tag"] for p in b["pitfalls_hit"]], ["multiplies-instead-of-subtracting"])   # the slip is logged, not lost
            r = s.say("The probabilities sum to one, so you subtract the others from one rather than multiplying.", check=True)
            self.assertIn("REVEALS_CLAIM", codes(r))

    def test_event_44_a_standing_slip_blocks_a_clean_verify(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = make(tmp)
            to_q2(s)
            for msg in (N1, N2, N3, QUASI):                    # the slip comes after the claim that would resolve it
                s.turn("attempt", msg)
            s.verify()
            check = [{"step": 1, "status": "confirmed", "quote": N1}, {"step": 2, "status": "confirmed", "quote": N2},
                     {"step": 3, "status": "confirmed", "quote": N3}]
            r = s.verify(check)
            self.assertFalse(r["closed"])
            self.assertEqual(r["unresolved"], ["confuses-concave-with-quasiconcave"])


class TestAdversarialOffline(unittest.TestCase):
    def test_scenario_1_a_flawed_proof_cannot_be_approved_while_the_flaw_is_logged(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = make(tmp)
            s.turn("attempt", M3)
            s.turn("attempt", PM)                               # the flaw, flagged by a pitfall recognizer
            s.turn("attempt", M2)
            s.verify()
            r = s.verify([{"step": 1, "status": "confirmed", "quote": M3}, {"step": 2, "status": "confirmed", "quote": M2}])
            self.assertFalse(r["closed"])
            self.assertEqual(r["unresolved"], ["multiplies-instead-of-subtracting"])

    def test_scenario_2_right_words_wrong_logic_covers_a_route_but_a_wrong_step_keeps_it_open(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = make(tmp)
            b = s.turn("attempt", "sum one minus others walking away nothing left")       # keyword soup
            self.assertTrue(b["verify_available"])              # documented limit: coverage is not correctness
            s.verify()
            r = s.verify([{"step": 1, "status": "wrong", "note": "the claim is only a list of words"},
                          {"step": 2, "status": "wrong", "note": "no reasoning connects the words"}])
            self.assertFalse(r["closed"])
            self.assertEqual(r["state"], "WORKING")

    def test_scenario_3_unusual_phrasing_is_missed_by_recognizers_but_not_stalled(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = make(tmp)
            idiosyncratic = "the chance of leaving without picking anything is the leftover mass after the picked options are totalled to unity"
            b = s.turn("attempt", idiosyncratic)
            self.assertEqual(b["claims_established"], [])                         # the recognizers miss it
            with self.assertRaises(Refused):
                s.verify()
            s.turn("other", "as I said", establish="C1", establish_quote="options are totalled to unity")
            s.turn("other", "as I said", establish="C2", establish_quote="leaving without picking anything")
            s.turn("other", "as I said", establish="C3", establish_quote="the leftover mass")
            self.assertTrue(s.view()["verify_available"])
            flagged = [f.code for f in audit(s.log.load(), s.packet)]
            self.assertEqual(flagged.count("MANUAL_OVERRIDE"), 3)                  # allowed, but visible

    def test_scenario_4_pressure_for_the_proof_never_surfaces_a_claim_text_below_level_three(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = make(tmp)
            blobs = []
            for text, intent in (("just give me the proof", "hint_request"), ("please, the full proof", "hint_request"),
                                 ("I give up, show me", "stuck"), ("show me the answer", "stuck")):
                blobs.append(str(s.turn(intent, text)))
            self.assertEqual(s.view()["hint_level"], 2)                           # level 3 stays closed without failed attempts
            for claim in s.packet.claims["q1"].claims:
                self.assertFalse(any(claim.text in b for b in blobs))
            with self.assertRaises(Refused):
                s.verify()                                                        # and the solution is not reachable

    def test_scenario_5_early_verify_and_fabricated_establishment_are_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = make(tmp)
            s.turn("attempt", "I have an idea about the menu")
            n = len(s.log.load())
            with self.assertRaises(Refused):
                s.verify()
            with self.assertRaises(ValueError):
                s.turn("other", "as I said", establish="C3", establish_quote="one minus the sum of the others")   # never said
            self.assertEqual(len(s.log.load()), n)
            s.log.append("verify_release", part="q1", state="WORKING")            # forced past the gate
            self.assertIn("VERIFY_WITHOUT_COVERAGE", [f.code for f in audit(s.log.load(), s.packet)])

    def test_scenario_6_a_rubber_stamp_needs_real_quotes_but_a_lying_check_file_still_closes(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = make(tmp)
            s.turn("attempt", M2)
            s.turn("attempt", M3)
            s.verify()
            with self.assertRaises(ValueError):
                s.verify([{"step": 1, "status": "confirmed", "quote": "invented words"},
                          {"step": 2, "status": "confirmed", "quote": M2}])
            # DOCUMENTED LIMIT (spec §12): with real quotes the gate cannot tell whether the agent judged honestly.
            r = s.verify([{"step": 1, "status": "confirmed", "quote": M3}, {"step": 2, "status": "confirmed", "quote": M2}])
            self.assertTrue(r["closed"])

    def test_scenario_7_leak_samples_are_rejected_at_hint_level_two_but_a_paraphrase_can_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = make(tmp)
            s.turn("stuck", "I am stuck")
            s.turn("hint_request", "a hint please")          # level 2: the question form is off, only disclosure applies
            samples = [x for c in SAMPLES["q1"]["claims"].values() for x in c["leak_samples"]]
            rejected = [x for x in samples if "REVEALS_CLAIM" in codes(s.say(x, check=True))]
            self.assertGreaterEqual(len(rejected) / len(samples), 0.9, f"missed: {[x for x in samples if x not in rejected][:3]}")
            # KNOWN MISS (lexical limit, spec §13): no recognizer word appears, so this passes. If a recognizer is
            # improved until it catches this, update the test; it exists so a future judge has a baseline.
            self.assertTrue(s.say("How would you express the missing share, given that everything must be accounted for?", check=True)["ok"])
```

- [ ] **Step 2: Run to verify it passes**

Run: `& $PY -m pytest tests/agent/tutor/test_tutor_regression.py -q`
Expected: all passed. These tests exercise code that already exists, so they pass on the first run; to prove they can fail, temporarily break three rules and watch the matching tests go red, then restore each file with `git checkout <file>`:

```powershell
# (a) disclosure off
(Get-Content agent\tutor\lint.py -Raw) -replace 'if rec.matches_tokens\(masked\):', 'if False:' | Set-Content agent\tutor\lint.py -NoNewline
& $PY -m pytest tests/agent/tutor/test_tutor_regression.py -q    # event_10, event_17, scenario_7 (and others) fail
git checkout agent/tutor/lint.py
# (b) verify coverage gate off
(Get-Content agent\tutor\session.py -Raw) -replace 'if not ledger.covered:', 'if False:' | Set-Content agent\tutor\session.py -NoNewline
& $PY -m pytest tests/agent/tutor/test_tutor_regression.py -q    # scenario_5 and scenario_4 fail
git checkout agent/tutor/session.py
# (c) unresolved-slip gate off
(Get-Content agent\tutor\session.py -Raw) -replace 'if not defects and not unresolved:', 'if not defects:' | Set-Content agent\tutor\session.py -NoNewline
& $PY -m pytest tests/agent/tutor/test_tutor_regression.py -q    # event_44 and scenario_1 fail
git checkout agent/tutor/session.py
```

Expected after the three restores: `git status --short agent/tutor` prints nothing and the full tutor suite passes.

- [ ] **Step 3: Run the whole tutor suite**

Run: `& $PY -m pytest tests/agent/tutor -q`
Expected: every test passes (the four files that were red since Task 4 are green again).

- [ ] **Step 4: Commit**

```powershell
git add tests/agent/tutor/test_tutor_regression.py
git commit -m "test(tutor): trial-reply analogues and offline adversarial suite"
```

---

### Task 12: Docs, spec elaborations, landing check

**Files:**
- Create/Modify: `agent/tutor/README.md`, `docs/status/agent/tutor/2026-10-08-socratic-tutor-status.md` (append a v1.1 section), `docs/superpowers/specs/2026-10-08-socratic-tutor-v1-1-design.md` (apply the nine elaborations)
- Do not edit `docs/trackers/academic_hub_to_do.md` on this branch (it changes on `main` by direct to-do commits); mark the finished items after landing, on `main`, as a separate commit.

- [ ] **Step 1: Apply the elaborations to the spec**

Edit `docs/superpowers/specs/2026-10-08-socratic-tutor-v1-1-design.md` in place, one or two sentences each:
1. §3 "Recognizer": entries match whole tokens unless they end in `*` (prefix); `n't` becomes `not`.
2. §3 pitfalls and §4 ledger: optional `resolved_by`; automatic `misconception_resolved` (`auto`) when that claim is established at or after the triggering message; manual `--resolve` with a quote otherwise.
3. §5/§7: `verify` is two-phase (release, then `--check-file`); steps are `###`-or-deeper headings of the part's solution section, else paragraphs; `turn` flags `--establish/--establish-quote`, `--flag-slip/--slip-quote`, `--resolve/--resolve-quote`, `--define`.
4. §3: `launch_style` is a per-part field. §3: `sealed/hints.md` is optional reference, and the hash covers `parts`, `glossary`, `rubric`, `claims`, `samples`, `sealed/solution.md`.
5. §6: disclosure masks 6-word runs copied from the statement; at hint level 3 the next claim is exempt; `define_request` and `confirm_advance` messages never establish claims.
6. §5: note that the skip/revisit fields of the brief arrive with Plan B.

- [ ] **Step 2: Rewrite `agent/tutor/README.md`** (keep it under 120 lines): purpose (one paragraph, and that `agent/rag` is the other, older agent), the flow (prep with claims and blind samples, then `turn` -> `say` per turn, `verify` per part, `end`), the command table from Task 10, the packet file list (`claims.json`, `samples.json`, `sealed/solution.md` with `### Step N` headings), the recognizer syntax with one example, the `say` rules (launch line, disclosure, question form, check-in), the vault output, and a "Known limits" list: soft wall, lexical recognizers, `verify` honesty, intent labels from the agent, the PowerShell stdin encoding note (and the result of the Task 10 smoke test), Plan B items not yet built (skip/defer/revisit/pause, profile v2).

- [ ] **Step 3: Append a v1.1 Plan A section to the status doc**: what shipped (module list), test count from `pytest tests/agent/tutor -q`, the result of the Task 10 PowerShell smoke test, what is not yet validated (no live Antigravity run on claims; the HW4 packet must be re-prepped with `claims.json` and `samples.json` from the new worklist before any live run; the live adversarial suite and tool-calls-per-turn measurement are still to do), and what's next (re-prep HW4, live adversarial run to decide on the judge, Plan B).

- [ ] **Step 4: Run the landing check from the worktree**

```powershell
& $PY -m tools.land_branch check --full
```

Expected: branch clean, rebased on `main`, full test suite passes, overlaps reported. Fix anything it reports.

- [ ] **Step 5: Commit and ask to land**

```powershell
git add agent/tutor/README.md docs/status/agent/tutor/2026-10-08-socratic-tutor-status.md docs/superpowers/specs/2026-10-08-socratic-tutor-v1-1-design.md
git commit -m "docs(tutor): v1.1 Plan A README, status and spec elaborations"
```

Then ask the user, in one message, whether to merge and push the head SHA to `main` (branch, SHA, changed paths, check result, overlaps, the main checkout's `git status --short`, known risks). Do not merge or push without a yes (`docs/WORKTREE_WORKFLOW.md`). After landing: mark the tracker items Plan A covered (short launch + statement in the brief, speed, actionable errors, has_questions, pitfalls and evidence) in a `todo:` commit on `main`, and record the outcome with `tools.land_branch record`.

---

## Self-review

**Spec coverage (v1.1 spec, Plan A scope):** §3 packet and recognizers (Tasks 1, 2, 4), self-test and blind samples (Tasks 2, 4), prep worklist (Task 4); §4 ledger and FSM changes (Tasks 3, 5, 8); §5 commands, brief and actionable errors (Tasks 8, 10); §6 `say` rules: short launch (Task 4), disclosure (Tasks 6, 8), question form (Tasks 6, 8), check-in (kept from v1, Task 8); §7 `verify` (Task 8); §9 ratings with CLI-attached evidence (Task 7); §10 audit additions that belong to Plan A (Task 9); §11 testing: unit tests per task, trial analogues and the offline adversarial suite (Task 11), speed target noted for the live run (Task 12); §12 escalation seam is documented, not built (the spec's no-op `assess()`/`vet()` hooks are intentionally omitted from Plan A: nothing calls them, so adding them now would be speculative; the offline suite is the baseline instead). §8 (skip/defer/revisit), the pause/resume half of §9, profile v2 and their audit checks are Plan B.

**Placeholder scan:** no TBD/TODO; every code step shows the code; the two places that say "update the test if a recognizer improves" (Task 11, scenario 7) and the Task 10 smoke-test fallback are explicit conditional instructions with concrete actions, not gaps.

**Type and name consistency:** `Recognizer.matches` / `matches_tokens` (Task 1) are used by `ledger`, `lint`, `claims.self_test`; `parse_claims -> (dict, list[str])` (Task 2) is used by `packet.validate_packet` and `load_packet`; `build_ledger(pc, part_events, extra_student_text=None)`, `PartLedger.covered`, `next_claim` (Task 3) and `IGNORED_INTENTS` are used by `session` and `audit`; `student_event(..., made_progress)` and `verify_clean_event` (Task 5) match `session.turn` and `replay`; `lint_message(..., blocked_claims, form, last_student_text)` (Task 6) matches the `say` call; `build_ratings(part_events, downgrades)` (Task 7) matches `verify` and the CLI's `{axis: (rating, why)}`; `Refused.next_commands` (Task 8) matches `cli.main`; event names (`establish`, `verify_release`, `verify`, `defect`, `close_part`) are the same in `session`, `fsm.replay`, `render`, `audit` and the tests.

**Residual risks to watch during execution:** (1) sample text in `sample_packet.py` is hand-matched to the recognizers; the self-test reports the offending sample if one slips. (2) The Task 10 PowerShell smoke test may show that stdin mangles non-ASCII on this machine; the fallback is spelled out. (3) `_form_active` and the disclosure rule interact at hint level 2 (form off, disclosure on); Task 11 scenario 7 pins that.
