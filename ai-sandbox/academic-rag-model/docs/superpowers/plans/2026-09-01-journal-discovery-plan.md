# Journal Discovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `journal_discovery`, a new subproject that resolves a faculty name or topic query into full-text PDFs on disk under `research/journal-articles/<topic>/`, ready for the existing, unmodified `convert_journal_articles.py` to pick up.

**Architecture:** A sibling package to `journal_articles/`/`essays/`/`notes/`/`textbook/` inside `academic-rag-model/`. OpenAlex resolves candidate works; a local `sentence-transformers` model scores each against a user-supplied relevance prompt before any network access is attempted; surviving works are deduped against a JSON manifest, resolved to full text through a paced Unpaywall → arXiv → EZProxy tier chain, routed into an auto-created topic folder, and written to disk with a bibliographic `.meta.json` sidecar. Conversion, indexing, and RAG are untouched — this subproject only ever writes files.

**Tech Stack:** Python (matching the rest of `academic-rag-model`), `requests` for HTTP, `sentence-transformers` for local relevance embeddings, `pyzotero` for optional Zotero sync, `unittest`/`unittest.mock` for tests (matching the existing `tests/` convention).

**Spec:** `academic-rag-model/docs/superpowers/specs/2026-08-31-journal-discovery-design.md`

## Global Constraints

- Never import from `indexer/`; never write into `.index/` (spec §2).
- Never invoke `convert_journal_articles.py`; a PDF (+ `.meta.json` sidecar) on disk in `research/journal-articles/<topic>/` is the sole handoff to the rest of the pipeline (spec §1, §2).
- Relevance scoring uses a **local** `sentence-transformers` model only, never Gemini — this is what keeps "a discovery run costs network calls only, never Gemini API spend" true (spec §1, §3).
- Every full-text download attempt, on every tier, is paced via `paced_sleep()`; default `--pace-per-hour 25`, jittered ±30% (spec §3).
- Do not reuse `common.gemini_utils.call_with_retries` for HTTP — its retry-delay parsing is written for Gemini's own `retryDelay` error text. `journal_discovery` has its own `fetch_with_retries` (spec §6).
- Tests mirror the existing flat `tests/` convention: `unittest.TestCase` + `unittest.mock`, package-qualified imports via the root `conftest.py`, no real network calls, no real model downloads (spec §7).

---

## File Structure

**Create:**
- `academic-rag-model/journal_discovery/__init__.py` — empty, matches every other subproject package.
- `academic-rag-model/journal_discovery/http_utils.py` — generic HTTP retry loop and download pacing. No OpenAlex/Unpaywall-specific knowledge.
- `academic-rag-model/journal_discovery/discovery.py` — OpenAlex-only: author/topic resolution, `Work` dataclass, abstract reconstruction.
- `academic-rag-model/journal_discovery/relevance.py` — local embedding model, cosine similarity, and the score/ceiling selection logic.
- `academic-rag-model/journal_discovery/manifest.py` — dedup manifest read/update.
- `academic-rag-model/journal_discovery/metadata_sidecar.py` — `.meta.json` read/write.
- `academic-rag-model/journal_discovery/topic_routing.py` — concept → folder name, auto-create.
- `academic-rag-model/journal_discovery/access.py` — Unpaywall/arXiv/EZProxy full-text resolution + pacing integration.
- `academic-rag-model/journal_discovery/manual_validate_ezproxy.py` — manual-only validation aid, not part of the automated pipeline.
- `academic-rag-model/journal_discovery/zotero_sync.py` — optional Zotero push.
- `academic-rag-model/journal_discovery/discover.py` — CLI entry point, wires everything together.
- `academic-rag-model/journal_discovery_instructions.md` — usage doc, matching `journal_articles_instructions.md`'s style.
- `academic-rag-model/tests/test_http_utils.py`, `test_discovery.py`, `test_relevance.py`, `test_manifest.py`, `test_metadata_sidecar.py`, `test_topic_routing.py`, `test_access.py`, `test_zotero_sync.py`, `test_discover.py`.

**Modify:**
- `academic-rag-model/README.md` — add `journal_discovery/` to the subproject list.
- `ai-sandbox/.env.example` — document `OPENALEX_CONTACT_EMAIL`, `EZPROXY_SESSION_COOKIE`, `ZOTERO_LIBRARY_ID`, `ZOTERO_API_KEY`.

---

### Task 1: HTTP retry loop and download pacing

**Files:**
- Create: `academic-rag-model/journal_discovery/__init__.py`
- Create: `academic-rag-model/journal_discovery/http_utils.py`
- Test: `academic-rag-model/tests/test_http_utils.py`

**Interfaces:**
- Produces: `FetchError(RuntimeError)`; `fetch_with_retries(method: str, url: str, *, retries=3, backoff_seconds=2.0, max_wait_seconds=60.0, **request_kwargs) -> requests.Response`; `is_pdf_response(response) -> bool`; `paced_sleep(pace_per_hour: float, jitter: float = 0.3) -> None`.

- [ ] **Step 1: Create the empty package file**

```python
# academic-rag-model/journal_discovery/__init__.py
```

(Empty file — matches `essays/__init__.py`, `journal_articles/__init__.py`.)

- [ ] **Step 2: Write the failing tests**

```python
# academic-rag-model/tests/test_http_utils.py
import unittest
from unittest.mock import MagicMock, patch

from journal_discovery.http_utils import FetchError, fetch_with_retries, is_pdf_response, paced_sleep


class TestFetchWithRetries(unittest.TestCase):
    @patch("journal_discovery.http_utils.time.sleep")
    @patch("journal_discovery.http_utils.requests.request")
    def test_retries_on_429_honoring_retry_after(self, mock_request, mock_sleep):
        rate_limited = MagicMock(status_code=429, headers={"Retry-After": "5"})
        success = MagicMock(status_code=200, headers={})
        mock_request.side_effect = [rate_limited, success]

        response = fetch_with_retries("GET", "https://example.com")

        self.assertIs(response, success)
        mock_sleep.assert_called_once_with(5.0)

    @patch("journal_discovery.http_utils.time.sleep")
    @patch("journal_discovery.http_utils.requests.request")
    def test_returns_immediately_on_success(self, mock_request, mock_sleep):
        success = MagicMock(status_code=200, headers={})
        mock_request.return_value = success

        response = fetch_with_retries("GET", "https://example.com")

        self.assertIs(response, success)
        mock_sleep.assert_not_called()

    @patch("journal_discovery.http_utils.time.sleep")
    @patch("journal_discovery.http_utils.requests.request")
    def test_raises_after_exhausting_retries(self, mock_request, mock_sleep):
        mock_request.return_value = MagicMock(status_code=500, headers={})

        with self.assertRaises(FetchError):
            fetch_with_retries("GET", "https://example.com", retries=2, backoff_seconds=0.01)

        self.assertEqual(mock_request.call_count, 2)


class TestIsPdfResponse(unittest.TestCase):
    def test_true_for_pdf_content_type(self):
        response = MagicMock(headers={"Content-Type": "application/pdf"})
        self.assertTrue(is_pdf_response(response))

    def test_false_for_html_content_type(self):
        response = MagicMock(headers={"Content-Type": "text/html; charset=utf-8"})
        self.assertFalse(is_pdf_response(response))

    def test_false_when_header_missing(self):
        response = MagicMock(headers={})
        self.assertFalse(is_pdf_response(response))


class TestPacedSleep(unittest.TestCase):
    @patch("journal_discovery.http_utils.time.sleep")
    @patch("journal_discovery.http_utils.random.uniform")
    def test_sleeps_jittered_interval(self, mock_uniform, mock_sleep):
        mock_uniform.return_value = 100.0

        paced_sleep(pace_per_hour=25)

        # min_interval = 3600 / 25 = 144 seconds, jittered +/-30%
        args, _ = mock_uniform.call_args
        self.assertAlmostEqual(args[0], 144 * 0.7, places=3)
        self.assertAlmostEqual(args[1], 144 * 1.3, places=3)
        mock_sleep.assert_called_once_with(100.0)

    @patch("journal_discovery.http_utils.time.sleep")
    def test_disabled_when_pace_is_zero(self, mock_sleep):
        paced_sleep(pace_per_hour=0)
        mock_sleep.assert_not_called()


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd academic-rag-model && python -m pytest tests/test_http_utils.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'journal_discovery.http_utils'`

- [ ] **Step 4: Write the implementation**

```python
# academic-rag-model/journal_discovery/http_utils.py
"""
http_utils.py
Generic HTTP retry loop and download pacing shared by discovery.py and
access.py. Deliberately not common.gemini_utils.call_with_retries -- that
helper's retry-delay parsing is written specifically for Gemini's own
"retryDelay"/"retry in Ns" error text, not a standard HTTP Retry-After
header.
"""
from __future__ import annotations

import random
import time

import requests


class FetchError(RuntimeError):
    """Raised when an HTTP request fails after exhausting all retries."""


def fetch_with_retries(
    method: str,
    url: str,
    *,
    retries: int = 3,
    backoff_seconds: float = 2.0,
    max_wait_seconds: float = 60.0,
    **request_kwargs,
) -> requests.Response:
    last_response = None
    last_error = None
    for attempt in range(retries):
        try:
            response = requests.request(method, url, **request_kwargs)
        except requests.RequestException as err:
            last_error = err
            if attempt < retries - 1:
                time.sleep(min(backoff_seconds * (attempt + 1), max_wait_seconds))
            continue

        if response.status_code < 400:
            return response

        last_response = response
        retryable = response.status_code == 429 or response.status_code >= 500
        if retryable and attempt < retries - 1:
            retry_after = response.headers.get("Retry-After")
            wait = float(retry_after) if retry_after else backoff_seconds * (attempt + 1)
            time.sleep(min(wait, max_wait_seconds))
            continue
        break

    if last_response is not None:
        raise FetchError(
            f"{method} {url} failed with status {last_response.status_code} after {retries} attempts"
        )
    raise FetchError(f"{method} {url} failed after {retries} attempts: {last_error}")


def is_pdf_response(response: requests.Response) -> bool:
    """True only if Content-Type is application/pdf -- catches an EZProxy
    login wall (text/html) on an expired cookie before it's ever written
    to disk, per spec S6."""
    return "application/pdf" in response.headers.get("Content-Type", "").lower()


def paced_sleep(pace_per_hour: float, jitter: float = 0.3) -> None:
    """Sleeps min_interval = 3600/pace_per_hour seconds, jittered +/-jitter
    (default +/-30%) so the request cadence isn't perfectly periodic --
    itself a detectable pattern. Protects the user's own institutional
    EZProxy standing from automated-abuse detection (spec S3), not just
    politeness. pace_per_hour <= 0 disables pacing (local testing only)."""
    if pace_per_hour <= 0:
        return
    min_interval = 3600.0 / pace_per_hour
    time.sleep(random.uniform(min_interval * (1 - jitter), min_interval * (1 + jitter)))
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd academic-rag-model && python -m pytest tests/test_http_utils.py -v`
Expected: PASS (7 tests)

- [ ] **Step 6: Commit**

```bash
git add academic-rag-model/journal_discovery/__init__.py academic-rag-model/journal_discovery/http_utils.py academic-rag-model/tests/test_http_utils.py
git commit -m "feat(journal_discovery): add HTTP retry loop and download pacing"
```

---

### Task 2: OpenAlex discovery

**Files:**
- Create: `academic-rag-model/journal_discovery/discovery.py`
- Test: `academic-rag-model/tests/test_discovery.py`

**Interfaces:**
- Consumes: `journal_discovery.http_utils.fetch_with_retries(method, url, **kwargs) -> requests.Response`
- Produces: `Work` (dataclass: `openalex_id: str`, `doi: str | None`, `title: str`, `authors: list[str]`, `year: int | None`, `abstract: str | None`, `concepts: list[str]`, `oa_url: str | None`, `is_oa: bool`, `arxiv_id: str | None`, `page_count: int | None`); `reconstruct_abstract(inverted_index: dict | None) -> str | None`; `resolve_author_id(name: str, mailto: str, ror: str = COLUMBIA_ROR) -> str | None`; `iter_author_works(author_id: str, mailto: str, batch_size: int) -> Iterator[Work]`; `iter_topic_works(keywords: str, mailto: str, batch_size: int, ror: str | None = None) -> Iterator[Work]`; `resolve_works(faculty: list[str], topics: list[str], mailto: str, batch_size: int) -> Iterator[Work]`.

- [ ] **Step 1: Write the failing tests**

```python
# academic-rag-model/tests/test_discovery.py
import unittest
from unittest.mock import MagicMock, patch

from journal_discovery.discovery import (
    Work,
    iter_author_works,
    iter_topic_works,
    reconstruct_abstract,
    resolve_author_id,
    resolve_works,
)


def _openalex_work(title="Untitled", doi="https://doi.org/10.1/abc", arxiv_url=None):
    return {
        "id": "https://openalex.org/W1",
        "doi": doi,
        "title": title,
        "publication_year": 2024,
        "authorships": [{"author": {"display_name": "Jane Doe"}}],
        "abstract_inverted_index": {"Climate": [0], "displacement": [1]},
        "concepts": [
            {"display_name": "Climate change", "score": 0.9},
            {"display_name": "Economics", "score": 0.4},
        ],
        "open_access": {"is_oa": True, "oa_url": "https://example.com/paper.pdf"},
        "locations": [{"landing_page_url": arxiv_url}] if arxiv_url else [],
    }


def _response(json_data, status_code=200):
    response = MagicMock(status_code=status_code)
    response.json.return_value = json_data
    return response


class TestReconstructAbstract(unittest.TestCase):
    def test_reorders_by_position(self):
        result = reconstruct_abstract({"displacement": [1], "Climate": [0]})
        self.assertEqual(result, "Climate displacement")

    def test_none_when_missing(self):
        self.assertIsNone(reconstruct_abstract(None))
        self.assertIsNone(reconstruct_abstract({}))


class TestResolveAuthorId(unittest.TestCase):
    @patch("journal_discovery.discovery.fetch_with_retries")
    def test_returns_ror_filtered_match(self, mock_fetch):
        mock_fetch.return_value = _response({"results": [{"id": "https://openalex.org/A1"}]})
        result = resolve_author_id("Jane Doe", "me@example.com")
        self.assertEqual(result, "https://openalex.org/A1")
        self.assertEqual(mock_fetch.call_count, 1)

    @patch("journal_discovery.discovery.fetch_with_retries")
    def test_falls_back_when_ror_filter_finds_nothing(self, mock_fetch):
        mock_fetch.side_effect = [
            _response({"results": []}),
            _response({"results": [{"id": "https://openalex.org/A2"}]}),
        ]
        result = resolve_author_id("Jane Doe", "me@example.com")
        self.assertEqual(result, "https://openalex.org/A2")
        self.assertEqual(mock_fetch.call_count, 2)

    @patch("journal_discovery.discovery.fetch_with_retries")
    def test_none_when_nothing_matches_at_all(self, mock_fetch):
        mock_fetch.return_value = _response({"results": []})
        self.assertIsNone(resolve_author_id("Nobody", "me@example.com"))


class TestIterAuthorWorks(unittest.TestCase):
    @patch("journal_discovery.discovery.fetch_with_retries")
    def test_pages_until_empty_and_parses_fields(self, mock_fetch):
        mock_fetch.side_effect = [
            _response({"results": [_openalex_work()]}),
            _response({"results": []}),
        ]
        works = list(iter_author_works("https://openalex.org/A1", "me@example.com", batch_size=25))
        self.assertEqual(len(works), 1)
        work = works[0]
        self.assertIsInstance(work, Work)
        self.assertEqual(work.doi, "10.1/abc")
        self.assertEqual(work.title, "Untitled")
        self.assertEqual(work.authors, ["Jane Doe"])
        self.assertEqual(work.abstract, "Climate displacement")
        self.assertEqual(work.concepts, ["Climate change", "Economics"])
        self.assertTrue(work.is_oa)
        self.assertEqual(work.oa_url, "https://example.com/paper.pdf")
        self.assertIsNone(work.arxiv_id)

    @patch("journal_discovery.discovery.fetch_with_retries")
    def test_extracts_arxiv_id(self, mock_fetch):
        mock_fetch.side_effect = [
            _response({"results": [_openalex_work(arxiv_url="https://arxiv.org/abs/2401.12345")]}),
            _response({"results": []}),
        ]
        works = list(iter_author_works("https://openalex.org/A1", "me@example.com", batch_size=25))
        self.assertEqual(works[0].arxiv_id, "2401.12345")


class TestIterTopicWorks(unittest.TestCase):
    @patch("journal_discovery.discovery.fetch_with_retries")
    def test_pages_until_empty(self, mock_fetch):
        mock_fetch.side_effect = [
            _response({"results": [_openalex_work()]}),
            _response({"results": []}),
        ]
        works = list(iter_topic_works("climate displacement", "me@example.com", batch_size=25))
        self.assertEqual(len(works), 1)


class TestResolveWorks(unittest.TestCase):
    @patch("journal_discovery.discovery.iter_topic_works")
    @patch("journal_discovery.discovery.iter_author_works")
    @patch("journal_discovery.discovery.resolve_author_id")
    def test_chains_faculty_then_topic_queries(self, mock_resolve_author, mock_iter_author, mock_iter_topic):
        mock_resolve_author.return_value = "https://openalex.org/A1"
        mock_iter_author.return_value = iter([Work(
            openalex_id="W1", doi="10.1/a", title="A", authors=[], year=2024, abstract="x",
            concepts=[], oa_url=None, is_oa=False, arxiv_id=None, page_count=None,
        )])
        mock_iter_topic.return_value = iter([Work(
            openalex_id="W2", doi="10.1/b", title="B", authors=[], year=2024, abstract="y",
            concepts=[], oa_url=None, is_oa=False, arxiv_id=None, page_count=None,
        )])

        results = list(resolve_works(["Jane Doe"], ["climate"], "me@example.com", batch_size=25))

        self.assertEqual([w.openalex_id for w in results], ["W1", "W2"])

    @patch("journal_discovery.discovery.iter_author_works")
    @patch("journal_discovery.discovery.resolve_author_id")
    def test_skips_unresolvable_faculty(self, mock_resolve_author, mock_iter_author):
        mock_resolve_author.return_value = None

        results = list(resolve_works(["Nobody"], [], "me@example.com", batch_size=25))

        self.assertEqual(results, [])
        mock_iter_author.assert_not_called()


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd academic-rag-model && python -m pytest tests/test_discovery.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'journal_discovery.discovery'`

- [ ] **Step 3: Write the implementation**

```python
# academic-rag-model/journal_discovery/discovery.py
"""
discovery.py
OpenAlex-only work resolution: resolves a faculty name or topic query
into Work records. Knows nothing about relevance scoring, full-text
access, or where files land -- see relevance.py, access.py,
topic_routing.py for those.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from journal_discovery.http_utils import fetch_with_retries

_OPENALEX_BASE = "https://api.openalex.org"
COLUMBIA_ROR = "https://ror.org/00hj8s172"

_ARXIV_URL_RE = re.compile(r"arxiv\.org/abs/([\w.\-]+)", re.IGNORECASE)


@dataclass
class Work:
    openalex_id: str
    doi: str | None
    title: str
    authors: list[str]
    year: int | None
    abstract: str | None
    concepts: list[str] = field(default_factory=list)
    oa_url: str | None = None
    is_oa: bool = False
    arxiv_id: str | None = None
    page_count: int | None = None


def reconstruct_abstract(inverted_index: dict[str, list[int]] | None) -> str | None:
    """OpenAlex stores abstracts as {word: [positions]} to sidestep
    publisher copyright on the plain-text form -- reassembling it here is
    the standard, documented way to get the abstract back."""
    if not inverted_index:
        return None
    positions = []
    for word, indices in inverted_index.items():
        for index in indices:
            positions.append((index, word))
    positions.sort()
    return " ".join(word for _, word in positions)


def _bare_doi(doi_url: str | None) -> str | None:
    """OpenAlex's own `doi` field is a full https://doi.org/... URL, not
    a bare DOI -- Unpaywall's API and our own manifest/dedup keys both
    want the bare form."""
    if not doi_url:
        return None
    return doi_url.split("doi.org/")[-1]


def _extract_arxiv_id(record: dict) -> str | None:
    for location in record.get("locations") or []:
        url = (location or {}).get("landing_page_url") or ""
        match = _ARXIV_URL_RE.search(url)
        if match:
            return match.group(1)
    return None


def _work_from_openalex(record: dict) -> Work:
    concepts = sorted(record.get("concepts") or [], key=lambda c: c.get("score", 0), reverse=True)
    open_access = record.get("open_access") or {}
    return Work(
        openalex_id=record.get("id"),
        doi=_bare_doi(record.get("doi")),
        title=record.get("title") or "Untitled",
        authors=[
            (a.get("author") or {}).get("display_name", "")
            for a in record.get("authorships") or []
        ],
        year=record.get("publication_year"),
        abstract=reconstruct_abstract(record.get("abstract_inverted_index")),
        concepts=[c.get("display_name") for c in concepts if c.get("display_name")],
        oa_url=open_access.get("oa_url"),
        is_oa=bool(open_access.get("is_oa")),
        arxiv_id=_extract_arxiv_id(record),
        page_count=None,  # OpenAlex doesn't reliably provide this
    )


def resolve_author_id(name: str, mailto: str, ror: str = COLUMBIA_ROR) -> str | None:
    params = {"search": name, "mailto": mailto}
    if ror:
        params["filter"] = f"last_known_institutions.ror:{ror}"
    response = fetch_with_retries("GET", f"{_OPENALEX_BASE}/authors", params=params)
    results = response.json().get("results", [])
    if not results and ror:
        response = fetch_with_retries(
            "GET", f"{_OPENALEX_BASE}/authors", params={"search": name, "mailto": mailto}
        )
        results = response.json().get("results", [])
    return results[0]["id"] if results else None


def iter_author_works(author_id: str, mailto: str, batch_size: int):
    page = 1
    while True:
        params = {
            "filter": f"author.id:{author_id}",
            "sort": "publication_year:desc,cited_by_count:desc",
            "per-page": batch_size,
            "page": page,
            "mailto": mailto,
        }
        response = fetch_with_retries("GET", f"{_OPENALEX_BASE}/works", params=params)
        results = response.json().get("results", [])
        if not results:
            return
        for record in results:
            yield _work_from_openalex(record)
        page += 1


def iter_topic_works(keywords: str, mailto: str, batch_size: int, ror: str | None = None):
    page = 1
    while True:
        search_filter = f"default.search:{keywords}"
        if ror:
            search_filter += f",institutions.ror:{ror}"
        params = {
            "filter": search_filter,
            "per-page": batch_size,
            "page": page,
            "mailto": mailto,
        }
        response = fetch_with_retries("GET", f"{_OPENALEX_BASE}/works", params=params)
        results = response.json().get("results", [])
        if not results:
            return
        for record in results:
            yield _work_from_openalex(record)
        page += 1


def resolve_works(faculty: list[str], topics: list[str], mailto: str, batch_size: int):
    """Chains every --faculty query (fully paged) then every --topic query
    into one generator, per spec S4 step 1. Deliberately lazy (a
    generator, not a list) so an early stop in relevance.select_relevant_works
    (S3's max-results/max-examined ceilings) never pages further into
    OpenAlex than it needs to."""
    for name in faculty:
        author_id = resolve_author_id(name, mailto)
        if author_id is None:
            print(f"WARNING: could not resolve an OpenAlex author id for {name!r}; skipping.")
            continue
        yield from iter_author_works(author_id, mailto, batch_size)
    for keywords in topics:
        yield from iter_topic_works(keywords, mailto, batch_size)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd academic-rag-model && python -m pytest tests/test_discovery.py -v`
Expected: PASS (11 tests)

- [ ] **Step 5: Commit**

```bash
git add academic-rag-model/journal_discovery/discovery.py academic-rag-model/tests/test_discovery.py
git commit -m "feat(journal_discovery): add OpenAlex author/topic discovery"
```

---

### Task 3: Local relevance scoring and selection ceiling

**Files:**
- Create: `academic-rag-model/journal_discovery/relevance.py`
- Test: `academic-rag-model/tests/test_relevance.py`

**Interfaces:**
- Consumes: `journal_discovery.discovery.Work`
- Produces: `ScoredWork` (dataclass: `work: Work`, `score: float | None`); `cosine_similarity(a: list[float], b: list[float]) -> float`; `load_relevance_model(model_name: str = "all-MiniLM-L6-v2")`; `embed_text(model, text: str) -> list[float]`; `score_work(model, prompt_embedding: list[float], work: Work) -> float | None`; `select_relevant_works(works: Iterable[Work], model, relevance_prompt: str, threshold: float, max_results: int, max_examined: int) -> list[ScoredWork]`.

- [ ] **Step 1: Write the failing tests**

```python
# academic-rag-model/tests/test_relevance.py
import unittest
from unittest.mock import MagicMock

from journal_discovery.discovery import Work
from journal_discovery.relevance import (
    ScoredWork,
    cosine_similarity,
    embed_text,
    score_work,
    select_relevant_works,
)


def _work(idx, abstract="a real abstract"):
    return Work(
        openalex_id=f"W{idx}", doi=f"10.1/{idx}", title=f"Paper {idx}", authors=[],
        year=2024, abstract=abstract,
    )


class TestCosineSimilarity(unittest.TestCase):
    def test_identical_vectors_score_one(self):
        self.assertAlmostEqual(cosine_similarity([1.0, 0.0], [1.0, 0.0]), 1.0)

    def test_orthogonal_vectors_score_zero(self):
        self.assertAlmostEqual(cosine_similarity([1.0, 0.0], [0.0, 1.0]), 0.0)


class TestEmbedText(unittest.TestCase):
    def test_normalizes_and_converts_to_list(self):
        model = MagicMock()
        encoded = MagicMock()
        encoded.tolist.return_value = [0.1, 0.2, 0.3]
        model.encode.return_value = encoded

        result = embed_text(model, "some text")

        model.encode.assert_called_once_with("some text", normalize_embeddings=True)
        self.assertEqual(result, [0.1, 0.2, 0.3])


class TestScoreWork(unittest.TestCase):
    def test_none_when_no_abstract(self):
        model = MagicMock()
        work = _work(1, abstract=None)
        self.assertIsNone(score_work(model, [1.0, 0.0], work))

    def test_scores_via_cosine_similarity(self):
        model = MagicMock()
        encoded = MagicMock()
        encoded.tolist.return_value = [1.0, 0.0]
        model.encode.return_value = encoded
        work = _work(1, abstract="matches the prompt")

        score = score_work(model, [1.0, 0.0], work)

        self.assertAlmostEqual(score, 1.0)


class TestSelectRelevantWorks(unittest.TestCase):
    def _model_scoring(self, scores_by_abstract):
        model = MagicMock()

        def encode(text, normalize_embeddings=True):
            encoded = MagicMock()
            encoded.tolist.return_value = scores_by_abstract.get(text, [0.0, 0.0])
            return encoded

        model.encode.side_effect = encode
        return model

    def test_drops_below_threshold(self):
        model = self._model_scoring({
            "prompt": [1.0, 0.0],
            "on topic": [1.0, 0.0],
            "off topic": [0.0, 1.0],
        })
        works = [_work(1, "on topic"), _work(2, "off topic")]

        selected = select_relevant_works(
            works, model, "prompt", threshold=0.5, max_results=10, max_examined=10,
        )

        self.assertEqual([sw.work.openalex_id for sw in selected], ["W1"])

    def test_stops_at_max_results(self):
        model = self._model_scoring({"prompt": [1.0, 0.0], "on topic": [1.0, 0.0]})
        works = [_work(i, "on topic") for i in range(5)]

        selected = select_relevant_works(
            works, model, "prompt", threshold=0.5, max_results=2, max_examined=10,
        )

        self.assertEqual(len(selected), 2)

    def test_stops_at_max_examined_even_if_under_max_results(self):
        model = self._model_scoring({"prompt": [1.0, 0.0], "on topic": [1.0, 0.0]})
        works = [_work(i, "on topic") for i in range(5)]

        selected = select_relevant_works(
            works, model, "prompt", threshold=0.5, max_results=100, max_examined=3,
        )

        self.assertEqual(len(selected), 3)

    def test_no_abstract_candidates_only_fill_remaining_slots(self):
        model = self._model_scoring({"prompt": [1.0, 0.0], "on topic": [1.0, 0.0]})
        works = [_work(1, "on topic"), _work(2, None), _work(3, None)]

        selected = select_relevant_works(
            works, model, "prompt", threshold=0.5, max_results=2, max_examined=10,
        )

        self.assertEqual(len(selected), 2)
        self.assertEqual(selected[0].work.openalex_id, "W1")
        self.assertEqual(selected[0].score, 1.0)
        self.assertEqual(selected[1].work.openalex_id, "W2")
        self.assertIsNone(selected[1].score)

    def test_no_abstract_candidates_excluded_when_no_room(self):
        model = self._model_scoring({"prompt": [1.0, 0.0], "on topic": [1.0, 0.0]})
        works = [_work(i, "on topic") for i in range(2)] + [_work(9, None)]

        selected = select_relevant_works(
            works, model, "prompt", threshold=0.5, max_results=2, max_examined=10,
        )

        self.assertEqual(len(selected), 2)
        self.assertTrue(all(sw.score is not None for sw in selected))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd academic-rag-model && python -m pytest tests/test_relevance.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'journal_discovery.relevance'`

- [ ] **Step 3: Write the implementation**

```python
# academic-rag-model/journal_discovery/relevance.py
"""
relevance.py
Local (sentence-transformers, no Gemini API spend) relevance scoring for
discovery candidates against a user-supplied prompt, plus the two-layer
volume control from spec S1/S3: a similarity threshold as the primary
filter, a numeric ceiling as backstop.

Deliberately does not import indexer.index_card.cosine_similarity even
though an equivalent function exists there -- journal_discovery never
imports from indexer/ (spec S2), and this embedding space is private to
this one scoring step, never compared against anything indexer/ produces
(spec S3, S9).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable

from journal_discovery.discovery import Work

_DEFAULT_MODEL_NAME = "all-MiniLM-L6-v2"


@dataclass
class ScoredWork:
    work: Work
    score: float | None  # None means no abstract was available to score


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def load_relevance_model(model_name: str = _DEFAULT_MODEL_NAME):
    """Import is local to this function (not module-level) so importing
    journal_discovery.relevance never requires sentence-transformers to be
    installed unless this is actually called -- matches common/gemini_utils.py's
    own get_gemini_client() pattern of deferring the heavy import."""
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_name)


def embed_text(model, text: str) -> list[float]:
    return model.encode(text, normalize_embeddings=True).tolist()


def score_work(model, prompt_embedding: list[float], work: Work) -> float | None:
    if not work.abstract:
        return None
    return cosine_similarity(prompt_embedding, embed_text(model, work.abstract))


def select_relevant_works(
    works: Iterable[Work],
    model,
    relevance_prompt: str,
    threshold: float,
    max_results: int,
    max_examined: int,
) -> list[ScoredWork]:
    """Consumes `works` lazily (spec S4 step 2): stops examining candidates
    once max_examined have been scored, or once max_results have passed
    the threshold, whichever comes first. A work with no abstract can't
    be scored and is deprioritized -- collected separately and only used
    to fill slots max_results didn't otherwise reach (spec S6)."""
    prompt_embedding = embed_text(model, relevance_prompt)
    scored: list[ScoredWork] = []
    unscored: list[ScoredWork] = []
    examined = 0

    for work in works:
        if examined >= max_examined:
            break
        examined += 1

        score = score_work(model, prompt_embedding, work)
        if score is None:
            unscored.append(ScoredWork(work=work, score=None))
        elif score >= threshold:
            scored.append(ScoredWork(work=work, score=score))
            if len(scored) >= max_results:
                break

    remaining_slots = max_results - len(scored)
    if remaining_slots > 0:
        scored.extend(unscored[:remaining_slots])
    return scored
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd academic-rag-model && python -m pytest tests/test_relevance.py -v`
Expected: PASS (10 tests)

- [ ] **Step 5: Commit**

```bash
git add academic-rag-model/journal_discovery/relevance.py academic-rag-model/tests/test_relevance.py
git commit -m "feat(journal_discovery): add local relevance scoring and selection ceiling"
```

---

### Task 4: Dedup manifest and metadata sidecar

**Files:**
- Create: `academic-rag-model/journal_discovery/manifest.py`
- Create: `academic-rag-model/journal_discovery/metadata_sidecar.py`
- Test: `academic-rag-model/tests/test_manifest.py`
- Test: `academic-rag-model/tests/test_metadata_sidecar.py`

**Interfaces:**
- Consumes: `journal_discovery.discovery.Work`
- Produces: `manifest_path(articles_dir) -> Path`; `load_manifest(path) -> dict`; `save_manifest(path, manifest: dict) -> None`; `manifest_key(work: Work) -> str`; `is_seen(manifest: dict, key: str) -> bool`; `record_outcome(manifest: dict, key: str, status: str, folder: str | None = None) -> None`; `sidecar_path(pdf_path) -> Path`; `write_sidecar(pdf_path, work: Work, relevance_score: float | None, source_tier: str | None) -> None`.

- [ ] **Step 1: Write the failing tests**

```python
# academic-rag-model/tests/test_manifest.py
import json
import tempfile
import unittest
from pathlib import Path

from journal_discovery.discovery import Work
from journal_discovery.manifest import (
    is_seen,
    load_manifest,
    manifest_key,
    manifest_path,
    record_outcome,
    save_manifest,
)


def _work(doi="10.1/abc", openalex_id="W1"):
    return Work(openalex_id=openalex_id, doi=doi, title="T", authors=[], year=2024, abstract=None)


class TestManifestPath(unittest.TestCase):
    def test_lives_under_dot_discovery(self):
        path = manifest_path("/some/articles/dir")
        self.assertEqual(path, Path("/some/articles/dir") / ".discovery" / "seen.json")


class TestLoadSaveManifest(unittest.TestCase):
    def test_load_missing_file_returns_empty_dict(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(load_manifest(Path(tmp) / "seen.json"), {})

    def test_save_then_load_round_trips(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nested" / "seen.json"
            save_manifest(path, {"10.1/abc": {"status": "fetched"}})
            self.assertEqual(load_manifest(path), {"10.1/abc": {"status": "fetched"}})
            self.assertTrue(path.exists())


class TestManifestKey(unittest.TestCase):
    def test_prefers_doi(self):
        self.assertEqual(manifest_key(_work(doi="10.1/abc", openalex_id="W1")), "10.1/abc")

    def test_falls_back_to_openalex_id_without_doi(self):
        self.assertEqual(manifest_key(_work(doi=None, openalex_id="W1")), "W1")


class TestIsSeenAndRecordOutcome(unittest.TestCase):
    def test_is_seen(self):
        manifest = {"10.1/abc": {"status": "fetched"}}
        self.assertTrue(is_seen(manifest, "10.1/abc"))
        self.assertFalse(is_seen(manifest, "10.1/other"))

    def test_record_outcome_adds_entry_with_status_and_folder(self):
        manifest = {}
        record_outcome(manifest, "10.1/abc", "fetched", folder="climate-displacement")
        entry = manifest["10.1/abc"]
        self.assertEqual(entry["status"], "fetched")
        self.assertEqual(entry["folder"], "climate-displacement")
        self.assertIn("fetched_at", entry)

    def test_record_outcome_without_folder(self):
        manifest = {}
        record_outcome(manifest, "10.1/abc", "needs_manual")
        self.assertEqual(manifest["10.1/abc"]["status"], "needs_manual")
        self.assertNotIn("folder", manifest["10.1/abc"])


if __name__ == "__main__":
    unittest.main()
```

```python
# academic-rag-model/tests/test_metadata_sidecar.py
import json
import tempfile
import unittest
from pathlib import Path

from journal_discovery.discovery import Work
from journal_discovery.metadata_sidecar import sidecar_path, write_sidecar


def _work():
    return Work(
        openalex_id="W1", doi="10.1/abc", title="A Paper", authors=["Jane Doe"],
        year=2024, abstract="...", concepts=["Climate change"], page_count=12,
    )


class TestSidecarPath(unittest.TestCase):
    def test_replaces_pdf_extension(self):
        self.assertEqual(sidecar_path(Path("/x/paper.pdf")), Path("/x/paper.meta.json"))


class TestWriteSidecar(unittest.TestCase):
    def test_writes_expected_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdf_path = Path(tmp) / "paper.pdf"
            pdf_path.write_bytes(b"%PDF-1.4")

            write_sidecar(pdf_path, _work(), relevance_score=0.82, source_tier="open_access")

            data = json.loads((Path(tmp) / "paper.meta.json").read_text(encoding="utf-8"))
            self.assertEqual(data["title"], "A Paper")
            self.assertEqual(data["authors"], ["Jane Doe"])
            self.assertEqual(data["year"], 2024)
            self.assertEqual(data["doi"], "10.1/abc")
            self.assertEqual(data["concepts"], ["Climate change"])
            self.assertEqual(data["source_tier"], "open_access")
            self.assertEqual(data["relevance_score"], 0.82)
            self.assertEqual(data["page_count"], 12)

    def test_null_relevance_score_for_unscored_work(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdf_path = Path(tmp) / "paper.pdf"
            write_sidecar(pdf_path, _work(), relevance_score=None, source_tier="ezproxy")
            data = json.loads((Path(tmp) / "paper.meta.json").read_text(encoding="utf-8"))
            self.assertIsNone(data["relevance_score"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd academic-rag-model && python -m pytest tests/test_manifest.py tests/test_metadata_sidecar.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

```python
# academic-rag-model/journal_discovery/manifest.py
"""
manifest.py
Dedup manifest per spec S5: research/journal-articles/.discovery/seen.json,
keyed by DOI (falling back to OpenAlex work id absent a DOI), so a paper
reached by both a --faculty and a --topic query in the same or a later
run is only ever fetched once.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from journal_discovery.discovery import Work


def manifest_path(articles_dir) -> Path:
    return Path(articles_dir) / ".discovery" / "seen.json"


def load_manifest(path) -> dict:
    path = Path(path)
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_manifest(path, manifest: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)


def manifest_key(work: Work) -> str:
    return work.doi or work.openalex_id


def is_seen(manifest: dict, key: str) -> bool:
    return key in manifest


def record_outcome(manifest: dict, key: str, status: str, folder: str | None = None) -> None:
    entry = {"status": status, "fetched_at": datetime.now(timezone.utc).isoformat()}
    if folder is not None:
        entry["folder"] = folder
    manifest[key] = entry
```

```python
# academic-rag-model/journal_discovery/metadata_sidecar.py
"""
metadata_sidecar.py
Per spec S3: a <paper>.meta.json sidecar carrying OpenAlex bibliographic
data forward for Zotero sync and dedup, deliberately separate from
convert_journal_articles.py's own frontmatter schema (routing/model/tags),
which this subproject never touches.
"""
from __future__ import annotations

import json
from pathlib import Path

from journal_discovery.discovery import Work


def sidecar_path(pdf_path) -> Path:
    return Path(pdf_path).with_suffix(".meta.json")


def write_sidecar(pdf_path, work: Work, relevance_score: float | None, source_tier: str | None) -> None:
    data = {
        "title": work.title,
        "authors": work.authors,
        "year": work.year,
        "doi": work.doi,
        "openalex_id": work.openalex_id,
        "concepts": work.concepts,
        "source_tier": source_tier,
        "relevance_score": relevance_score,
        "page_count": work.page_count,
    }
    with open(sidecar_path(pdf_path), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd academic-rag-model && python -m pytest tests/test_manifest.py tests/test_metadata_sidecar.py -v`
Expected: PASS (9 tests)

- [ ] **Step 5: Commit**

```bash
git add academic-rag-model/journal_discovery/manifest.py academic-rag-model/journal_discovery/metadata_sidecar.py academic-rag-model/tests/test_manifest.py academic-rag-model/tests/test_metadata_sidecar.py
git commit -m "feat(journal_discovery): add dedup manifest and metadata sidecar"
```

---

### Task 5: Topic routing

**Files:**
- Create: `academic-rag-model/journal_discovery/topic_routing.py`
- Test: `academic-rag-model/tests/test_topic_routing.py`

**Interfaces:**
- Consumes: `journal_discovery.discovery.Work`
- Produces: `sanitize_topic_name(concept_display_name: str | None) -> str`; `route_to_folder(articles_dir, work: Work) -> Path`.

- [ ] **Step 1: Write the failing tests**

```python
# academic-rag-model/tests/test_topic_routing.py
import tempfile
import unittest
from pathlib import Path

from journal_discovery.discovery import Work
from journal_discovery.topic_routing import route_to_folder, sanitize_topic_name


class TestSanitizeTopicName(unittest.TestCase):
    def test_lowercases_and_hyphenates(self):
        self.assertEqual(sanitize_topic_name("Climate Change"), "climate-change")

    def test_strips_punctuation(self):
        self.assertEqual(sanitize_topic_name("Machine Learning & AI"), "machine-learning-ai")

    def test_falls_back_to_misc_when_empty(self):
        self.assertEqual(sanitize_topic_name(""), "misc")
        self.assertEqual(sanitize_topic_name(None), "misc")


class TestRouteToFolder(unittest.TestCase):
    def test_creates_folder_from_top_concept(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Work(
                openalex_id="W1", doi=None, title="T", authors=[], year=2024, abstract=None,
                concepts=["Climate change", "Economics"],
            )
            folder = route_to_folder(tmp, work)
            self.assertEqual(folder, Path(tmp) / "climate-change")
            self.assertTrue(folder.is_dir())

    def test_falls_back_to_misc_without_concepts(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Work(openalex_id="W1", doi=None, title="T", authors=[], year=2024, abstract=None, concepts=[])
            folder = route_to_folder(tmp, work)
            self.assertEqual(folder, Path(tmp) / "misc")
            self.assertTrue(folder.is_dir())

    def test_reuses_existing_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "climate-change").mkdir()
            work = Work(
                openalex_id="W1", doi=None, title="T", authors=[], year=2024, abstract=None,
                concepts=["Climate change"],
            )
            folder = route_to_folder(tmp, work)
            self.assertEqual(folder, Path(tmp) / "climate-change")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd academic-rag-model && python -m pytest tests/test_topic_routing.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

```python
# academic-rag-model/journal_discovery/topic_routing.py
"""
topic_routing.py
Per spec S1/S3: routes a fetched paper into a topic subfolder derived
from its top OpenAlex concept, auto-creating the folder when no existing
one fits (a deliberate design choice for this subproject -- contrast
indexer/retag.py's conservative fallback-tagging, discussed in the spec's
own follow-on section, S9).
"""
from __future__ import annotations

import re
from pathlib import Path

from journal_discovery.discovery import Work

_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


def sanitize_topic_name(concept_display_name: str | None) -> str:
    if not concept_display_name:
        return "misc"
    cleaned = _NON_ALNUM_RE.sub("-", concept_display_name.strip().lower()).strip("-")
    return cleaned or "misc"


def route_to_folder(articles_dir, work: Work) -> Path:
    top_concept = work.concepts[0] if work.concepts else None
    folder_name = sanitize_topic_name(top_concept)
    folder = Path(articles_dir) / folder_name
    folder.mkdir(parents=True, exist_ok=True)
    return folder
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd academic-rag-model && python -m pytest tests/test_topic_routing.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add academic-rag-model/journal_discovery/topic_routing.py academic-rag-model/tests/test_topic_routing.py
git commit -m "feat(journal_discovery): add topic routing with auto-created folders"
```

---

### Task 6: Full-text access resolution with pacing

**Files:**
- Create: `academic-rag-model/journal_discovery/access.py`
- Test: `academic-rag-model/tests/test_access.py`

**Interfaces:**
- Consumes: `journal_discovery.http_utils.fetch_with_retries`, `is_pdf_response`, `paced_sleep`; `journal_discovery.discovery.Work`
- Produces: `AccessResult` (dataclass: `status: str` [`"fetched"` or `"needs_manual"`], `content: bytes | None = None`, `tier: str | None = None`); `try_unpaywall(doi, mailto) -> str | None`; `try_arxiv_url(arxiv_id) -> str | None`; `build_ezproxy_url(target_url: str) -> str`; `resolve_full_text(work: Work, mailto: str, ezproxy_cookie: str | None, pace_per_hour: float) -> AccessResult`.

- [ ] **Step 1: Write the failing tests**

```python
# academic-rag-model/tests/test_access.py
import unittest
from unittest.mock import MagicMock, patch

from journal_discovery.access import (
    AccessResult,
    build_ezproxy_url,
    resolve_full_text,
    try_arxiv_url,
    try_unpaywall,
)
from journal_discovery.discovery import Work


def _work(doi="10.1/abc", oa_url=None, arxiv_id=None):
    return Work(
        openalex_id="W1", doi=doi, title="T", authors=[], year=2024, abstract=None,
        oa_url=oa_url, arxiv_id=arxiv_id,
    )


def _pdf_response(content=b"%PDF-1.4"):
    return MagicMock(status_code=200, headers={"Content-Type": "application/pdf"}, content=content)


def _html_response():
    return MagicMock(status_code=200, headers={"Content-Type": "text/html"}, content=b"<html>login</html>")


class TestTryUnpaywall(unittest.TestCase):
    @patch("journal_discovery.access.fetch_with_retries")
    def test_returns_pdf_url(self, mock_fetch):
        response = MagicMock(status_code=200)
        response.json.return_value = {"best_oa_location": {"url_for_pdf": "https://x.com/p.pdf"}}
        mock_fetch.return_value = response
        self.assertEqual(try_unpaywall("10.1/abc", "me@example.com"), "https://x.com/p.pdf")

    def test_none_without_doi(self):
        self.assertIsNone(try_unpaywall(None, "me@example.com"))


class TestTryArxivUrl(unittest.TestCase):
    def test_builds_pdf_url(self):
        self.assertEqual(try_arxiv_url("2401.12345"), "https://arxiv.org/pdf/2401.12345.pdf")

    def test_none_without_id(self):
        self.assertIsNone(try_arxiv_url(None))


class TestBuildEzproxyUrl(unittest.TestCase):
    def test_prefixes_target_url(self):
        url = build_ezproxy_url("https://doi.org/10.1/abc")
        self.assertTrue(url.startswith("https://ezproxy.cul.columbia.edu/login?url="))
        self.assertIn("https://doi.org/10.1/abc", url)


class TestResolveFullText(unittest.TestCase):
    @patch("journal_discovery.access.paced_sleep")
    @patch("journal_discovery.access.fetch_with_retries")
    def test_uses_open_access_url_first(self, mock_fetch, mock_pace):
        mock_fetch.return_value = _pdf_response(b"oa-content")
        work = _work(oa_url="https://x.com/p.pdf")

        result = resolve_full_text(work, "me@example.com", ezproxy_cookie=None, pace_per_hour=25)

        self.assertEqual(result, AccessResult(status="fetched", content=b"oa-content", tier="open_access"))
        mock_pace.assert_called_once_with(25)

    @patch("journal_discovery.access.paced_sleep")
    @patch("journal_discovery.access.fetch_with_retries")
    def test_falls_back_to_arxiv(self, mock_fetch, mock_pace):
        mock_fetch.return_value = _pdf_response(b"arxiv-content")
        work = _work(oa_url=None, arxiv_id="2401.12345")

        result = resolve_full_text(work, "me@example.com", ezproxy_cookie=None, pace_per_hour=25)

        self.assertEqual(result.tier, "arxiv")
        self.assertEqual(result.content, b"arxiv-content")

    @patch("journal_discovery.access.paced_sleep")
    @patch("journal_discovery.access.fetch_with_retries")
    def test_falls_back_to_ezproxy_with_cookie(self, mock_fetch, mock_pace):
        mock_fetch.return_value = _pdf_response(b"ezproxy-content")
        work = _work(doi="10.1/abc", oa_url=None, arxiv_id=None)

        result = resolve_full_text(work, "me@example.com", ezproxy_cookie="session123", pace_per_hour=25)

        self.assertEqual(result.tier, "ezproxy")
        self.assertEqual(result.content, b"ezproxy-content")

    @patch("journal_discovery.access.paced_sleep")
    @patch("journal_discovery.access.fetch_with_retries")
    def test_html_response_never_written_falls_through_to_needs_manual(self, mock_fetch, mock_pace):
        mock_fetch.return_value = _html_response()
        work = _work(oa_url="https://x.com/p.pdf")

        result = resolve_full_text(work, "me@example.com", ezproxy_cookie=None, pace_per_hour=25)

        self.assertEqual(result.status, "needs_manual")
        self.assertIsNone(result.content)

    @patch("journal_discovery.access.paced_sleep")
    def test_needs_manual_without_any_viable_tier(self, mock_pace):
        work = _work(doi=None, oa_url=None, arxiv_id=None)

        result = resolve_full_text(work, "me@example.com", ezproxy_cookie=None, pace_per_hour=25)

        self.assertEqual(result, AccessResult(status="needs_manual"))
        mock_pace.assert_not_called()


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd academic-rag-model && python -m pytest tests/test_access.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

```python
# academic-rag-model/journal_discovery/access.py
"""
access.py
Full-text resolution per spec S1/S3/S6: Unpaywall (open access) -> arXiv
(preprints) -> Columbia EZProxy (gated, manual session cookie). A
response that isn't actually application/pdf (an EZProxy login wall on
an expired cookie) is never written to disk. Every real download
attempt is paced (paced_sleep) to protect the user's own institutional
EZProxy standing, not just publisher politeness.
"""
from __future__ import annotations

from dataclasses import dataclass

from journal_discovery.discovery import Work
from journal_discovery.http_utils import fetch_with_retries, is_pdf_response, paced_sleep

_UNPAYWALL_BASE = "https://api.unpaywall.org/v2"
_EZPROXY_PREFIX = "https://ezproxy.cul.columbia.edu/login?url="


@dataclass
class AccessResult:
    status: str  # "fetched" or "needs_manual"
    content: bytes | None = None
    tier: str | None = None


def try_unpaywall(doi: str | None, mailto: str) -> str | None:
    if not doi:
        return None
    response = fetch_with_retries("GET", f"{_UNPAYWALL_BASE}/{doi}", params={"email": mailto})
    if response.status_code != 200:
        return None
    return (response.json().get("best_oa_location") or {}).get("url_for_pdf")


def try_arxiv_url(arxiv_id: str | None) -> str | None:
    if not arxiv_id:
        return None
    return f"https://arxiv.org/pdf/{arxiv_id}.pdf"


def build_ezproxy_url(target_url: str) -> str:
    return f"{_EZPROXY_PREFIX}{target_url}"


def _download(url: str, pace_per_hour: float, cookies: dict | None = None) -> bytes | None:
    paced_sleep(pace_per_hour)
    response = fetch_with_retries("GET", url, cookies=cookies, timeout=30)
    if response.status_code != 200 or not is_pdf_response(response):
        return None
    return response.content


def resolve_full_text(
    work: Work, mailto: str, ezproxy_cookie: str | None, pace_per_hour: float
) -> AccessResult:
    oa_url = work.oa_url or try_unpaywall(work.doi, mailto)
    if oa_url:
        content = _download(oa_url, pace_per_hour)
        if content:
            return AccessResult(status="fetched", content=content, tier="open_access")

    arxiv_url = try_arxiv_url(work.arxiv_id)
    if arxiv_url:
        content = _download(arxiv_url, pace_per_hour)
        if content:
            return AccessResult(status="fetched", content=content, tier="arxiv")

    if ezproxy_cookie and work.doi:
        ezproxy_url = build_ezproxy_url(f"https://doi.org/{work.doi}")
        content = _download(ezproxy_url, pace_per_hour, cookies={"ezproxy": ezproxy_cookie})
        if content:
            return AccessResult(status="fetched", content=content, tier="ezproxy")

    return AccessResult(status="needs_manual")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd academic-rag-model && python -m pytest tests/test_access.py -v`
Expected: PASS (9 tests)

- [ ] **Step 5: Commit**

```bash
git add academic-rag-model/journal_discovery/access.py academic-rag-model/tests/test_access.py
git commit -m "feat(journal_discovery): add paced Unpaywall/arXiv/EZProxy access resolution"
```

---

### Task 7: Manual EZProxy cookie validation (empirical, not unit-testable)

This task has no automated test — its entire purpose is checking real
institutional behavior, which mocking would defeat. Per spec S9, this
must happen before relying on `EZPROXY_SESSION_COOKIE` for any real
discovery run, and its outcome is the concrete trigger for whether
browser-automated login needs to move up the priority list.

**Files:**
- Create: `academic-rag-model/journal_discovery/manual_validate_ezproxy.py`
- Modify: `academic-rag-model/journal_discovery_instructions.md` (created in Task 10 — if Task 10 hasn't run yet, create a placeholder file here with just the validation-results paragraph; Task 10 will build the rest of the doc around it)

**Interfaces:**
- Consumes: `journal_discovery.access.build_ezproxy_url`, `journal_discovery.access._download`; `common.gemini_utils.load_dotenv_override`

- [ ] **Step 1: Write the validation script**

```python
# academic-rag-model/journal_discovery/manual_validate_ezproxy.py
"""
manual_validate_ezproxy.py
NOT part of the automated pipeline and has no unit tests -- its entire
purpose is checking real institutional behavior (does the manually
obtained EZProxy session cookie survive a real session at the actual
target pace), which mocking would defeat. Run this by hand once before
relying on EZPROXY_SESSION_COOKIE for a real discovery run (spec S9).

Usage:
    python -m journal_discovery.manual_validate_ezproxy \
        --doi 10.1016/j.example1 --doi 10.1016/j.example2 \
        --pace-per-hour 25
"""
from __future__ import annotations

import argparse
import os

from common.gemini_utils import load_dotenv_override
from journal_discovery.access import _download, build_ezproxy_url


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--doi", action="append", required=True, dest="dois",
                         help="A real, known-gated DOI to test against (repeatable).")
    parser.add_argument("--pace-per-hour", type=float, default=25.0)
    args = parser.parse_args()

    load_dotenv_override()
    cookie = os.environ.get("EZPROXY_SESSION_COOKIE")
    if not cookie:
        print("EZPROXY_SESSION_COOKIE is not set in .env -- nothing to validate.")
        return

    print(f"Validating {len(args.dois)} DOI(s) at --pace-per-hour {args.pace_per_hour}...")
    for doi in args.dois:
        url = build_ezproxy_url(f"https://doi.org/{doi}")
        content = _download(url, args.pace_per_hour, cookies={"ezproxy": cookie})
        outcome = "OK -- got a real PDF" if content else "FAILED -- login wall, expired cookie, or non-PDF response"
        print(f"  {doi}: {outcome}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Obtain a real EZProxy session cookie**

Log into `https://ezproxy.cul.columbia.edu` through a normal browser
session (triggers Columbia SSO/2FA as usual). Once authenticated, open
browser DevTools → Application (Chrome) or Storage (Firefox) → Cookies →
`ezproxy.cul.columbia.edu`, and copy the value of the session cookie
(commonly named `ezproxy` or `ezproxyn` — check what's actually present,
naming can vary by EZProxy configuration version).

- [ ] **Step 3: Configure `.env`**

Add to `ai-sandbox/.env` (not `.env.example` — this is a real secret):

```
EZPROXY_SESSION_COOKIE=<the cookie value from Step 2>
```

- [ ] **Step 4: Run the validation against a handful of real gated papers**

Pick 5–6 real DOIs you know are gated behind Columbia's subscriptions
(not open access — the point is testing the EZProxy tier specifically).

Run: `cd academic-rag-model && python -m journal_discovery.manual_validate_ezproxy --doi <doi1> --doi <doi2> --doi <doi3> --doi <doi4> --doi <doi5> --pace-per-hour 25`

This takes roughly `5 * (3600/25)` ≈ 12 minutes at default pacing.
Expected: every DOI reports `OK -- got a real PDF`, and the cookie is
still valid at the end (no challenge/login-wall partway through).

- [ ] **Step 5: Record the outcome**

Append a short paragraph to `academic-rag-model/journal_discovery_instructions.md`
(create it now with just this section if Task 10 hasn't run yet — Task 10
will build the rest of the doc around it) under a `## EZProxy validation
results` heading: the date tested, how many of the N DOIs succeeded, and
whether the cookie held for the full session. If any failed, note which
tier they fell through to (`needs_manual`) and whether that's a cookie
problem or a genuinely unavailable paper.

**If validation fails** (cookie gets challenged or expires mid-session):
this is the concrete signal spec S9 describes — flag to revisit
browser-automated login as a near-term follow-up rather than relying on
the manual hand-off for real usage. Do not attempt to build around it
silently; the spec's non-goal here was deliberate and the fix is a
scoped follow-on, not a workaround in `access.py`.

- [ ] **Step 6: Commit**

```bash
git add academic-rag-model/journal_discovery/manual_validate_ezproxy.py academic-rag-model/journal_discovery_instructions.md
git commit -m "feat(journal_discovery): add manual EZProxy validation script and record results"
```

---

### Task 8: Zotero sync

**Files:**
- Create: `academic-rag-model/journal_discovery/zotero_sync.py`
- Test: `academic-rag-model/tests/test_zotero_sync.py`

**Interfaces:**
- Consumes: `journal_discovery.discovery.Work`
- Produces: `sync_to_zotero(work: Work, pdf_path, topic_folder: str, library_id: str, api_key: str, library_type: str = "user") -> None`

- [ ] **Step 1: Write the failing tests**

```python
# academic-rag-model/tests/test_zotero_sync.py
import unittest
from unittest.mock import MagicMock, patch

from journal_discovery.discovery import Work
from journal_discovery.zotero_sync import sync_to_zotero


def _work():
    return Work(
        openalex_id="W1", doi="10.1/abc", title="A Paper", authors=["Jane Doe", "John Roe"],
        year=2024, abstract=None,
    )


class TestSyncToZotero(unittest.TestCase):
    @patch("journal_discovery.zotero_sync.zotero.Zotero")
    def test_creates_collection_when_missing(self, mock_zotero_cls):
        zot = MagicMock()
        mock_zotero_cls.return_value = zot
        zot.collections.return_value = []
        zot.create_collections.return_value = {"successful": {"0": {"key": "COLLKEY"}}}
        zot.item_template.return_value = {}
        zot.create_items.return_value = {"successful": {"0": {"key": "ITEMKEY"}}}

        sync_to_zotero(_work(), "/tmp/paper.pdf", "climate-change", "12345", "apikey")

        zot.create_collections.assert_called_once_with([{"name": "climate-change"}])
        created_item = zot.create_items.call_args[0][0][0]
        self.assertEqual(created_item["title"], "A Paper")
        self.assertEqual(created_item["DOI"], "10.1/abc")
        self.assertEqual(created_item["collections"], ["COLLKEY"])
        self.assertEqual(
            created_item["creators"],
            [{"creatorType": "author", "name": "Jane Doe"}, {"creatorType": "author", "name": "John Roe"}],
        )
        zot.attachment_simple.assert_called_once_with(["/tmp/paper.pdf"], "ITEMKEY")

    @patch("journal_discovery.zotero_sync.zotero.Zotero")
    def test_reuses_existing_collection(self, mock_zotero_cls):
        zot = MagicMock()
        mock_zotero_cls.return_value = zot
        zot.collections.return_value = [{"data": {"key": "EXISTING", "name": "climate-change"}}]
        zot.item_template.return_value = {}
        zot.create_items.return_value = {"successful": {"0": {"key": "ITEMKEY"}}}

        sync_to_zotero(_work(), "/tmp/paper.pdf", "climate-change", "12345", "apikey")

        zot.create_collections.assert_not_called()
        created_item = zot.create_items.call_args[0][0][0]
        self.assertEqual(created_item["collections"], ["EXISTING"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd academic-rag-model && python -m pytest tests/test_zotero_sync.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

```python
# academic-rag-model/journal_discovery/zotero_sync.py
"""
zotero_sync.py
Optional Zotero push per spec S1/S3: find-or-create a collection matching
the topic folder, push the item's bibliographic metadata, attach the
fetched PDF. A failure here is always caught and logged by the caller
(discover.py) -- it must never discard or block a PDF that's already
safely on disk (spec S6).
"""
from __future__ import annotations

from pyzotero import zotero

from journal_discovery.discovery import Work


def _get_or_create_collection(zot, name: str) -> str:
    for collection in zot.collections():
        if collection["data"]["name"] == name:
            return collection["data"]["key"]
    created = zot.create_collections([{"name": name}])
    return created["successful"]["0"]["key"]


def sync_to_zotero(
    work: Work, pdf_path, topic_folder: str, library_id: str, api_key: str, library_type: str = "user"
) -> None:
    zot = zotero.Zotero(library_id, library_type, api_key)
    collection_key = _get_or_create_collection(zot, topic_folder)

    item = zot.item_template("journalArticle")
    item["title"] = work.title
    item["date"] = str(work.year or "")
    item["DOI"] = work.doi or ""
    item["creators"] = [{"creatorType": "author", "name": name} for name in work.authors]
    item["collections"] = [collection_key]

    created = zot.create_items([item])
    item_key = created["successful"]["0"]["key"]
    zot.attachment_simple([str(pdf_path)], item_key)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd academic-rag-model && python -m pytest tests/test_zotero_sync.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add academic-rag-model/journal_discovery/zotero_sync.py academic-rag-model/tests/test_zotero_sync.py
git commit -m "feat(journal_discovery): add optional Zotero sync"
```

---

### Task 9: CLI orchestration

**Files:**
- Create: `academic-rag-model/journal_discovery/discover.py`
- Test: `academic-rag-model/tests/test_discover.py`

**Interfaces:**
- Consumes: `journal_discovery.discovery.resolve_works`; `journal_discovery.relevance.load_relevance_model`, `select_relevant_works`; `journal_discovery.manifest.manifest_path`, `load_manifest`, `save_manifest`, `manifest_key`, `is_seen`, `record_outcome`; `journal_discovery.access.resolve_full_text`; `journal_discovery.topic_routing.route_to_folder`, `sanitize_topic_name`; `journal_discovery.metadata_sidecar.write_sidecar`; `journal_discovery.zotero_sync.sync_to_zotero`; `common.gemini_utils.load_dotenv_override`
- Produces: `run(args: argparse.Namespace) -> dict` (the run-summary counts, per spec S4 step 9); `main() -> None`

- [ ] **Step 1: Write the failing tests**

```python
# academic-rag-model/tests/test_discover.py
import argparse
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from journal_discovery.access import AccessResult
from journal_discovery.discover import run
from journal_discovery.discovery import Work
from journal_discovery.relevance import ScoredWork


def _args(**overrides):
    defaults = dict(
        faculty=["Jane Doe"], topic=[], relevance_prompt="climate", relevance_threshold=0.5,
        batch_size=25, max_results=100, max_examined=300, pace_per_hour=25.0, zotero=False,
    )
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


def _work(idx, doi="10.1/abc"):
    return Work(
        openalex_id=f"W{idx}", doi=doi, title=f"Paper {idx}", authors=[], year=2024,
        abstract="x", concepts=["Climate change"],
    )


class TestRun(unittest.TestCase):
    @patch("journal_discovery.discover.load_relevance_model", return_value=MagicMock())
    @patch("journal_discovery.discover.resolve_works", return_value=iter([]))
    @patch("journal_discovery.discover.select_relevant_works")
    @patch("journal_discovery.discover.resolve_full_text")
    def test_fetched_work_writes_pdf_and_sidecar_and_updates_manifest(
        self, mock_resolve_full_text, mock_select, mock_resolve_works, mock_load_model
    ):
        with tempfile.TemporaryDirectory() as tmp:
            work = _work(1)
            mock_select.return_value = [ScoredWork(work=work, score=0.9)]
            mock_resolve_full_text.return_value = AccessResult(status="fetched", content=b"%PDF-1.4", tier="open_access")

            counts = run(_args(articles_dir=tmp, mailto="me@example.com", ezproxy_cookie=None))

            self.assertEqual(counts["fetched"], 1)
            self.assertEqual(counts["needs_manual"], 0)
            self.assertEqual(counts["already_seen"], 0)

            climate_dir = Path(tmp) / "climate-change"
            pdfs = list(climate_dir.glob("*.pdf"))
            self.assertEqual(len(pdfs), 1)
            self.assertTrue(pdfs[0].with_suffix(".meta.json").exists())

            manifest = (Path(tmp) / ".discovery" / "seen.json")
            self.assertTrue(manifest.exists())

    @patch("journal_discovery.discover.load_relevance_model", return_value=MagicMock())
    @patch("journal_discovery.discover.resolve_works", return_value=iter([]))
    @patch("journal_discovery.discover.select_relevant_works")
    @patch("journal_discovery.discover.resolve_full_text")
    def test_needs_manual_work_recorded_without_pdf(
        self, mock_resolve_full_text, mock_select, mock_resolve_works, mock_load_model
    ):
        with tempfile.TemporaryDirectory() as tmp:
            work = _work(2)
            mock_select.return_value = [ScoredWork(work=work, score=0.9)]
            mock_resolve_full_text.return_value = AccessResult(status="needs_manual")

            counts = run(_args(articles_dir=tmp, mailto="me@example.com", ezproxy_cookie=None))

            self.assertEqual(counts["needs_manual"], 1)
            self.assertEqual(counts["fetched"], 0)
            self.assertEqual(list(Path(tmp).rglob("*.pdf")), [])

    @patch("journal_discovery.discover.load_relevance_model", return_value=MagicMock())
    @patch("journal_discovery.discover.resolve_works", return_value=iter([]))
    @patch("journal_discovery.discover.select_relevant_works")
    @patch("journal_discovery.discover.resolve_full_text")
    def test_already_seen_work_is_skipped_without_fetch_attempt(
        self, mock_resolve_full_text, mock_select, mock_resolve_works, mock_load_model
    ):
        with tempfile.TemporaryDirectory() as tmp:
            work = _work(3)
            mock_select.return_value = [ScoredWork(work=work, score=0.9)]

            from journal_discovery.manifest import manifest_path, record_outcome, save_manifest, load_manifest
            path = manifest_path(tmp)
            manifest = load_manifest(path)
            record_outcome(manifest, "10.1/abc", "fetched", folder="climate-change")
            save_manifest(path, manifest)

            counts = run(_args(articles_dir=tmp, mailto="me@example.com", ezproxy_cookie=None))

            self.assertEqual(counts["already_seen"], 1)
            mock_resolve_full_text.assert_not_called()

    @patch("journal_discovery.discover.load_relevance_model", return_value=MagicMock())
    @patch("journal_discovery.discover.resolve_works", return_value=iter([]))
    @patch("journal_discovery.discover.select_relevant_works")
    @patch("journal_discovery.discover.resolve_full_text")
    @patch("journal_discovery.discover.sync_to_zotero")
    def test_zotero_sync_called_only_when_flag_set_and_configured(
        self, mock_sync, mock_resolve_full_text, mock_select, mock_resolve_works, mock_load_model
    ):
        with tempfile.TemporaryDirectory() as tmp:
            work = _work(4)
            mock_select.return_value = [ScoredWork(work=work, score=0.9)]
            mock_resolve_full_text.return_value = AccessResult(status="fetched", content=b"%PDF-1.4", tier="open_access")

            run(_args(
                articles_dir=tmp, mailto="me@example.com", ezproxy_cookie=None, zotero=True,
                zotero_library_id="12345", zotero_api_key="apikey",
            ))

            mock_sync.assert_called_once()

    @patch("journal_discovery.discover.load_relevance_model", return_value=MagicMock())
    @patch("journal_discovery.discover.resolve_works", return_value=iter([]))
    @patch("journal_discovery.discover.select_relevant_works")
    @patch("journal_discovery.discover.resolve_full_text")
    @patch("journal_discovery.discover.sync_to_zotero")
    def test_zotero_sync_skipped_without_flag(
        self, mock_sync, mock_resolve_full_text, mock_select, mock_resolve_works, mock_load_model
    ):
        with tempfile.TemporaryDirectory() as tmp:
            work = _work(5)
            mock_select.return_value = [ScoredWork(work=work, score=0.9)]
            mock_resolve_full_text.return_value = AccessResult(status="fetched", content=b"%PDF-1.4", tier="open_access")

            run(_args(articles_dir=tmp, mailto="me@example.com", ezproxy_cookie=None, zotero=False))

            mock_sync.assert_not_called()


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd academic-rag-model && python -m pytest tests/test_discover.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'journal_discovery.discover'`

- [ ] **Step 3: Write the implementation**

```python
# academic-rag-model/journal_discovery/discover.py
"""
discover.py
CLI entry point per spec S2/S4: python -m journal_discovery.discover.
Wires discovery -> relevance scoring -> dedup -> access -> topic routing
-> sidecar -> manifest -> optional Zotero sync, in that order. Never
imports indexer/ and never invokes convert_journal_articles.py -- a PDF
(+ sidecar) on disk is this subproject's entire contract with the rest
of the pipeline.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from common.gemini_utils import load_dotenv_override
from journal_discovery.access import resolve_full_text
from journal_discovery.discovery import resolve_works
from journal_discovery.manifest import (
    is_seen,
    load_manifest,
    manifest_key,
    manifest_path,
    record_outcome,
    save_manifest,
)
from journal_discovery.metadata_sidecar import write_sidecar
from journal_discovery.relevance import load_relevance_model, select_relevant_works
from journal_discovery.topic_routing import route_to_folder, sanitize_topic_name
from journal_discovery.zotero_sync import sync_to_zotero

_DEFAULT_BATCH_SIZE = 25
_DEFAULT_MAX_RESULTS = 100
_DEFAULT_MAX_EXAMINED = 300
_DEFAULT_RELEVANCE_THRESHOLD = 0.5
_DEFAULT_PACE_PER_HOUR = 25.0


def _pdf_filename(work) -> str:
    key = work.doi or work.openalex_id or work.title
    return f"{sanitize_topic_name(key)[:80] or 'paper'}.pdf"


def _sync_zotero_if_configured(work, pdf_path, topic_folder: str, args) -> None:
    library_id = getattr(args, "zotero_library_id", None) or os.environ.get("ZOTERO_LIBRARY_ID")
    api_key = getattr(args, "zotero_api_key", None) or os.environ.get("ZOTERO_API_KEY")
    if not library_id or not api_key:
        print("WARNING: --zotero passed but ZOTERO_LIBRARY_ID/ZOTERO_API_KEY not set; skipping sync.")
        return
    try:
        sync_to_zotero(work, pdf_path, topic_folder, library_id, api_key)
    except Exception as err:
        print(f"WARNING: Zotero sync failed for {pdf_path.name}: {err}")


def run(args: argparse.Namespace) -> dict:
    mailto = getattr(args, "mailto", None) or os.environ.get("OPENALEX_CONTACT_EMAIL")
    ezproxy_cookie = getattr(args, "ezproxy_cookie", None) or os.environ.get("EZPROXY_SESSION_COOKIE")

    model = load_relevance_model()
    works = resolve_works(args.faculty, args.topic, mailto, args.batch_size)
    scored = select_relevant_works(
        works, model, args.relevance_prompt, args.relevance_threshold,
        args.max_results, args.max_examined,
    )

    manifest_file = manifest_path(args.articles_dir)
    manifest = load_manifest(manifest_file)

    counts = {"examined": len(scored), "already_seen": 0, "fetched": 0, "needs_manual": 0}
    for scored_work in scored:
        work = scored_work.work
        key = manifest_key(work)
        if is_seen(manifest, key):
            counts["already_seen"] += 1
            continue

        result = resolve_full_text(work, mailto, ezproxy_cookie, args.pace_per_hour)
        if result.status == "fetched":
            folder = route_to_folder(args.articles_dir, work)
            pdf_path = folder / _pdf_filename(work)
            pdf_path.write_bytes(result.content)
            write_sidecar(pdf_path, work, scored_work.score, result.tier)
            record_outcome(manifest, key, "fetched", folder=folder.name)
            counts["fetched"] += 1
            if args.zotero:
                _sync_zotero_if_configured(work, pdf_path, folder.name, args)
        else:
            record_outcome(manifest, key, "needs_manual")
            counts["needs_manual"] += 1

    save_manifest(manifest_file, manifest)
    return counts


def main():
    parser = argparse.ArgumentParser(
        description="Resolve a faculty name or topic query into full-text PDFs under research/journal-articles/."
    )
    parser.add_argument("--faculty", action="append", default=[], help="Faculty name to query (repeatable).")
    parser.add_argument("--topic", action="append", default=[], help="Topic/keyword query (repeatable).")
    parser.add_argument(
        "--relevance-prompt", required=True,
        help="Free-text description of what you're actually looking for -- scored against each "
             "candidate's abstract, not just matched by author/topic name.",
    )
    parser.add_argument("--relevance-threshold", type=float, default=_DEFAULT_RELEVANCE_THRESHOLD)
    parser.add_argument("--batch-size", type=int, default=_DEFAULT_BATCH_SIZE)
    parser.add_argument("--max-results", type=int, default=_DEFAULT_MAX_RESULTS)
    parser.add_argument("--max-examined", type=int, default=_DEFAULT_MAX_EXAMINED)
    parser.add_argument("--pace-per-hour", type=float, default=_DEFAULT_PACE_PER_HOUR,
                         help="Full-text download attempts per hour, jittered +/-30%%. 0 disables pacing "
                              "(local testing against a mocked endpoint only).")
    parser.add_argument("--zotero", action="store_true", help="Also sync fetched papers into Zotero.")
    default_articles_dir = Path(__file__).resolve().parent.parent.parent / "research" / "journal-articles"
    parser.add_argument("--articles-dir", default=str(default_articles_dir))
    args = parser.parse_args()

    if not args.faculty and not args.topic:
        parser.error("at least one --faculty or --topic is required")

    load_dotenv_override()
    if not os.environ.get("OPENALEX_CONTACT_EMAIL"):
        print("ERROR: OPENALEX_CONTACT_EMAIL must be set in .env (required by OpenAlex/Unpaywall).")
        sys.exit(1)

    counts = run(args)

    print(f"\nExamined and scored: {counts['examined']}")
    print(f"Already seen (skipped): {counts['already_seen']}")
    print(f"Fetched: {counts['fetched']}")
    print(f"Needs manual download: {counts['needs_manual']}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd academic-rag-model && python -m pytest tests/test_discover.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Run the full journal_discovery test suite**

Run: `cd academic-rag-model && python -m pytest tests/test_http_utils.py tests/test_discovery.py tests/test_relevance.py tests/test_manifest.py tests/test_metadata_sidecar.py tests/test_topic_routing.py tests/test_access.py tests/test_zotero_sync.py tests/test_discover.py -v`
Expected: PASS (all tests across every task)

- [ ] **Step 6: Commit**

```bash
git add academic-rag-model/journal_discovery/discover.py academic-rag-model/tests/test_discover.py
git commit -m "feat(journal_discovery): add CLI orchestration wiring discovery through to disk"
```

---

### Task 10: Documentation and config

**Files:**
- Create/Modify: `academic-rag-model/journal_discovery_instructions.md` (extend the file started in Task 7)
- Modify: `academic-rag-model/README.md`
- Modify: `ai-sandbox/.env.example`

**Interfaces:** None (docs/config only).

- [ ] **Step 1: Write/extend `journal_discovery_instructions.md`**

```markdown
# Journal Discovery Pipeline

Companion to `journal_articles_instructions.md`, one step upstream: resolves
a faculty name or topic query into full-text PDFs on disk under
`research/journal-articles/<topic>/`, ready for `convert_journal_articles.py`
to pick up exactly as it does for manually-added papers. Design spec:
`docs/superpowers/specs/2026-08-31-journal-discovery-design.md`.

## Step 1: One-time local setup

```powershell
cd academic-rag-model
pip install requests sentence-transformers pyzotero
```

Add to `ai-sandbox/.env` (copy the placeholders from `.env.example`):
- `OPENALEX_CONTACT_EMAIL` -- required. OpenAlex and Unpaywall both use
  this for their "polite pool" of higher, faster rate limits.
- `EZPROXY_SESSION_COOKIE` -- optional. Only needed for gated (non-open-
  access, non-arXiv) papers. See "EZProxy setup" below before relying on
  this for real use.
- `ZOTERO_LIBRARY_ID` / `ZOTERO_API_KEY` -- optional, only needed with `--zotero`.

## Step 2: Run it

```powershell
python -m journal_discovery.discover --faculty "Alexander de Sherbinin" `
  --relevance-prompt "climate-forced displacement and migration vulnerability"

python -m journal_discovery.discover --topic "climate-forced displacement" `
  --relevance-prompt "empirical measurement of displacement, not policy commentary" `
  --max-results 50
```

- `--faculty` / `--topic` are both repeatable and can be combined in one run.
- `--relevance-prompt` is required: describe what you're actually looking
  for, not just the author/topic name -- it's what every candidate's
  abstract is scored against (locally, via `sentence-transformers`, no
  Gemini API cost) before any full-text access is attempted.
- `--relevance-threshold` (default `0.5`), `--max-results` (default `100`),
  `--max-examined` (default `300`) control the two-layer volume cap from
  the spec's S1 -- tune the threshold empirically against a few real runs
  before trusting the default.
- `--pace-per-hour` (default `25`) paces every full-text download attempt,
  jittered +/-30%. This protects your own institutional EZProxy access
  from automated-abuse detection, not just publisher politeness -- don't
  raise it casually.
- `--zotero` additionally pushes fetched papers into a Zotero collection
  matching the topic folder.
- Output: PDFs land in `research/journal-articles/<topic>/`, auto-created
  from each paper's top OpenAlex concept if it doesn't already exist, each
  with a `.meta.json` sidecar (title/authors/year/DOI/concepts/relevance
  score). A `research/journal-articles/.discovery/seen.json` manifest
  tracks what's already been fetched or flagged, across runs.
- This step never calls into `indexer/` or `convert_journal_articles.py`.
  Run that separately (`--dry-run` first, as its own docs already say)
  once you're happy with what landed on disk.

## EZProxy setup

`EZPROXY_SESSION_COOKIE` is a manually-obtained session cookie, not
automated login -- log into `https://ezproxy.cul.columbia.edu` in a real
browser, then copy the session cookie's value from DevTools. It will
expire; when gated-paper fetches start failing (`needs_manual_download`
climbing), re-obtain it the same way. Semi-automated browser login is a
deliberate non-goal for now (see the design spec's S9) -- revisit only if
the manual hand-off proves too brittle in practice, per the validation
below.

## EZProxy validation results

<!-- Filled in by Task 7: date tested, how many of N real gated DOIs
succeeded, and whether the cookie held for the full paced session. -->
```

- [ ] **Step 2: Update `academic-rag-model/README.md`**

Find this line in the "Repository layout" list:

```markdown
- [`journal_articles/`](journal_articles/README.md) — local, reuses `notes/`'s tiered pipeline unchanged for academic journal-article PDFs. See [`journal_articles_instructions.md`](journal_articles_instructions.md).
```

Add immediately after it:

```markdown
- [`journal_discovery/`](journal_discovery/) — resolves a faculty name or topic query (OpenAlex, locally-scored relevance, paced Unpaywall/arXiv/EZProxy access) into full-text PDFs under `research/journal-articles/<topic>/`, ready for `journal_articles/` to pick up. See [`journal_discovery_instructions.md`](journal_discovery_instructions.md).
```

- [ ] **Step 3: Update `ai-sandbox/.env.example`**

Add at the end of the file:

```
# journal_discovery -- OpenAlex/Unpaywall "polite pool" contact email
# (academic-rag-model/journal_discovery_instructions.md). Required.
OPENALEX_CONTACT_EMAIL=your_email@example.com

# journal_discovery -- optional, manually-obtained Columbia EZProxy
# session cookie for gated-paper access. Expires periodically; see
# journal_discovery_instructions.md's EZProxy setup section.
EZPROXY_SESSION_COOKIE=

# journal_discovery -- optional, only used with --zotero.
ZOTERO_LIBRARY_ID=
ZOTERO_API_KEY=
```

- [ ] **Step 4: Commit**

```bash
git add academic-rag-model/journal_discovery_instructions.md academic-rag-model/README.md ai-sandbox/.env.example
git commit -m "docs(journal_discovery): add usage instructions and config placeholders"
```

---

## Self-Review Notes

- **Spec coverage:** S1 goals (relevance threshold + numeric ceiling → Task 3; tiered access + pacing → Task 6; topic routing + sidecar → Tasks 4–5; dedup → Task 4; Zotero → Task 8; PDF-on-disk-only boundary → Task 9) all have a task. S2 architecture (sibling package, no `indexer/` import) → Task 1 scaffolding + enforced by every task's imports. S3 components map 1:1 to Tasks 2–6, 8. S4 data flow is exactly `run()` in Task 9. S5 dedup → Task 4. S6 error handling → Tasks 1 (retry), 6 (content-type, EZProxy degrade), 4 (no-abstract sidecar). S7 testing conventions followed throughout. S8/S9 are narrative/rationale sections, not implementable — Task 7 implements S9's one actionable item (EZProxy validation).
- **Placeholder scan:** none found — every step has runnable code or a concrete manual action.
- **Type consistency:** `Work` (Task 2) is consumed with the same field names by Tasks 3–6, 8–9. `AccessResult` (Task 6) fields (`status`, `content`, `tier`) match how Task 9 reads them. `ScoredWork` (Task 3) fields (`work`, `score`) match Task 9's usage. Function names (`resolve_works`, `select_relevant_works`, `resolve_full_text`, `route_to_folder`, `write_sidecar`, `manifest_key`/`is_seen`/`record_outcome`/`load_manifest`/`save_manifest`/`manifest_path`, `sync_to_zotero`) are identical between the task that defines them and every task that imports them.
