# Journal Discovery: Reliability Fixes and Classification Proposal Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix verified reliability bugs in the journal-discovery OA-download/retry path and replace the single-Concept folder router with a reviewed, Topics-based classification proposal mode that never moves files automatically.

**Architecture:** Section A (Tasks 1-7) makes narrow, independently-testable fixes inside the existing `access.py`/`http_utils.py`/`relevance.py`/`discover.py`/`manifest.py` call chain, plus one new tiny shared helper (`atomic_io.py`). Section B (Tasks 8-13) adds a `topics` field to `Work` and the sidecar schema, a pure ranking function (`propose_folder`), a read-only review ledger, and an explicit apply function (`resolve_folder_proposal`) — mirroring the existing `core/indexer/offering_links.py` review-ledger + `--resolve`/`--reject` CLI convention. No step in either section moves a file or changes a folder except Task 12's explicit, human-triggered apply step.

**Tech Stack:** Python 3.13, `requests`, `pypdf` (already a dependency), stdlib `unittest`, `argparse`.

**Spec:** [2026-10-14-reliability-and-classification-design.md](2026-10-14-reliability-and-classification-design.md)

## Global Constraints

- Run tests with `python -m pytest tests/discovery/discover_journal_articles/<file>.py -v` (or `tests/tools/test_backfill_topics.py`), from `academic-rag-model/`, using the worktree-local interpreter if present or the main checkout's `.venv` per the subproject's own CLAUDE.md.
- Never import from `core/indexer/` into anything under `discovery/discover_journal_articles/` (existing project rule, unrelated to this plan but touched files must preserve it).
- No network calls in any unit test — every OpenAlex/Unpaywall/Semantic Scholar/CORE call is mocked via `unittest.mock.patch` on `fetch_with_retries`, matching the existing test style in `tests/discovery/discover_journal_articles/`.
- No paid model calls anywhere in this plan (all OpenAlex/Unpaywall/Semantic Scholar/CORE/arXiv endpoints used are free, public GETs).
- Every manifest/sidecar write goes through the new `write_json_atomic` helper (Task 6) once it exists — no direct `json.dump` to the final path from that point on.
- Stage only the exact files each task lists when committing; never `git add -A`.

## Review Focus

- **A DOI-less work (OpenAlex id only) hitting the new retry/backfill/ledger code paths.** `try_unpaywall`/`try_semantic_scholar`/`try_core` already return `None` without a DOI, but the new `--retry` flag (Task 7) and `tools/backfill_topics.py` (Task 13) both need their own explicit "no DOI, can't look this up, skip" path rather than crashing on `resolve_work_by_doi(None, ...)`. Tested in Tasks 7 and 13.
- **Two distinct OpenAlex Topics whose sanitized display names collide** (e.g. "Climate Change" and "Climate-Change!"). `propose_folder` (Task 10) must keep only the higher-scored one as a candidate, not list a duplicate folder name twice or silently prefer whichever happened to sort last. Tested in Task 10.
- **A Retry-After value that parses to a past HTTP-date** (server clock skew, or a date already in the past). `_parse_retry_after` (Task 3) must clamp to `0.0`, not return a negative sleep duration. Tested in Task 3.
- **A paper with an empty `topics` list** (OpenAlex returned none, or the paper predates this fix and hasn't been backfilled). The ledger builder (Task 11) must skip it entirely rather than writing a zero-candidate proposal entry that would render as an empty, confusing review row. Tested in Task 11.
- **A manifest entry whose folder or sidecar no longer exists on disk** (manually deleted, moved, or renamed outside the pipeline). Both the ledger builder (Task 11) and the backfill script (Task 13) must skip that entry and count it, not raise `FileNotFoundError` and abort the whole run. Tested in Tasks 11 and 13.

---

## Section A: Reliability fixes

### Task 1: PDF byte validation

**Files:**
- Modify: `discovery/discover_journal_articles/http_utils.py`
- Modify: `discovery/discover_journal_articles/access.py:136`
- Test: `tests/discovery/discover_journal_articles/test_http_utils.py`

**Interfaces:**
- Produces: `is_valid_pdf_bytes(content: bytes) -> bool` in `http_utils.py`, used by `access.py`'s `_download`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/discovery/discover_journal_articles/test_http_utils.py`:

```python
class TestIsValidPdfBytes(unittest.TestCase):
    def _minimal_valid_pdf_bytes(self) -> bytes:
        import io
        from pypdf import PdfWriter
        writer = PdfWriter()
        writer.add_blank_page(width=72, height=72)
        buf = io.BytesIO()
        writer.write(buf)
        return buf.getvalue()

    def test_true_for_a_real_parseable_pdf(self):
        from discovery.discover_journal_articles.http_utils import is_valid_pdf_bytes
        self.assertTrue(is_valid_pdf_bytes(self._minimal_valid_pdf_bytes()))

    def test_false_without_pdf_magic_bytes(self):
        from discovery.discover_journal_articles.http_utils import is_valid_pdf_bytes
        self.assertFalse(is_valid_pdf_bytes(b"<html>not a pdf</html>"))

    def test_false_for_magic_bytes_with_garbage_body(self):
        from discovery.discover_journal_articles.http_utils import is_valid_pdf_bytes
        self.assertFalse(is_valid_pdf_bytes(b"%PDF-1.4\nthis is not actually a valid pdf body at all"))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/discovery/discover_journal_articles/test_http_utils.py -v -k IsValidPdfBytes`
Expected: FAIL with `ImportError` / `AttributeError: ... is_valid_pdf_bytes`.

- [ ] **Step 3: Implement**

Add to `http_utils.py` (after `is_pdf_response`):

```python
def is_valid_pdf_bytes(content: bytes) -> bool:
    """Checks the %PDF- magic bytes and that pypdf can actually open the
    content -- is_pdf_response() alone trusts the Content-Type header,
    which a misconfigured host or error page can mislabel."""
    if not content.startswith(b"%PDF-"):
        return False
    import io

    from pypdf import PdfReader

    try:
        PdfReader(io.BytesIO(content))
    except Exception:
        return False
    return True
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/discovery/discover_journal_articles/test_http_utils.py -v -k IsValidPdfBytes`
Expected: PASS (3 tests)

- [ ] **Step 5: Wire into access.py's `_download`**

In `access.py`, change the import line:

```python
from discovery.discover_journal_articles.http_utils import FetchError, fetch_with_retries, is_pdf_response, is_valid_pdf_bytes, paced_sleep
```

And change `_download` (line 136):

```python
    if response.status_code != 200 or not is_pdf_response(response) or not is_valid_pdf_bytes(response.content):
        return None
```

- [ ] **Step 6: Add a regression test in test_access.py**

Append to `TestResolveFullText` in `tests/discovery/discover_journal_articles/test_access.py`:

```python
    @patch("discovery.discover_journal_articles.access.paced_sleep")
    @patch("discovery.discover_journal_articles.access.fetch_with_retries")
    def test_pdf_content_type_with_non_pdf_bytes_is_rejected(self, mock_fetch, mock_pace):
        # A host that mislabels an error page as application/pdf must not
        # produce a "fetched" result just because the header looked right.
        fake_pdf = MagicMock(status_code=200, headers={"Content-Type": "application/pdf"}, content=b"not a pdf")
        mock_fetch.return_value = fake_pdf
        work = _work(doi=None, oa_url="https://x.com/p.pdf")

        result = resolve_full_text(work, "me@example.com", ezproxy_cookie=None, pace_per_hour=25)

        self.assertEqual(result.status, "needs_manual")
```

- [ ] **Step 7: Run the full access + http_utils test files**

Run: `python -m pytest tests/discovery/discover_journal_articles/test_http_utils.py tests/discovery/discover_journal_articles/test_access.py -v`
Expected: PASS (all tests)

- [ ] **Step 8: Commit**

```bash
git add discovery/discover_journal_articles/http_utils.py discovery/discover_journal_articles/access.py tests/discovery/discover_journal_articles/test_http_utils.py tests/discovery/discover_journal_articles/test_access.py
git commit -m "fix(discover_journal_articles): validate PDF bytes, not just Content-Type"
```

---

### Task 2: Lazy multi-provider OA fallback chain

**Files:**
- Modify: `discovery/discover_journal_articles/access.py:141-165`
- Test: `tests/discovery/discover_journal_articles/test_access.py`

**Interfaces:**
- Consumes: `is_valid_pdf_bytes` from Task 1 (already wired into `_download`).
- Produces: `resolve_full_text` keeps its existing signature and `AccessResult` shape, but `AccessResult.tier` can now be `"unpaywall"` or `"core"` (previously both collapsed into `"open_access"`) in addition to the existing `"open_access"`, `"arxiv"`, `"ezproxy"`.

- [ ] **Step 1: Write the failing tests**

Append to `TestResolveFullText` in `tests/discovery/discover_journal_articles/test_access.py`:

```python
    @patch("discovery.discover_journal_articles.access.paced_sleep")
    @patch("discovery.discover_journal_articles.access.fetch_with_retries")
    def test_falls_through_to_next_oa_provider_when_first_oa_url_fails_download(self, mock_fetch, mock_pace):
        # The audit's core finding: a present-but-broken oa_url must not
        # block trying Unpaywall/Semantic Scholar/CORE -- only an
        # exhausted provider list reaches needs_manual.
        broken_oa_download = _html_response()
        unpaywall_lookup = MagicMock(status_code=200)
        unpaywall_lookup.json.return_value = {"best_oa_location": {"url_for_pdf": "https://x.com/unpaywall.pdf"}}
        mock_fetch.side_effect = [broken_oa_download, unpaywall_lookup, _pdf_response(b"unpaywall-content")]
        work = _work(doi="10.1/abc", oa_url="https://x.com/broken.pdf")

        result = resolve_full_text(work, "me@example.com", ezproxy_cookie=None, pace_per_hour=25)

        self.assertEqual(result.tier, "unpaywall")
        self.assertEqual(result.content, b"unpaywall-content")

    @patch("discovery.discover_journal_articles.access.paced_sleep")
    @patch("discovery.discover_journal_articles.access.fetch_with_retries")
    def test_does_not_redownload_a_url_already_tried_by_an_earlier_provider(self, mock_fetch, mock_pace):
        same_url = "https://x.com/shared.pdf"
        broken_download = _html_response()
        unpaywall_lookup = MagicMock(status_code=200)
        unpaywall_lookup.json.return_value = {"best_oa_location": {"url_for_pdf": same_url}}
        no_s2 = MagicMock(status_code=200)
        no_s2.json.return_value = {"openAccessPdf": None}
        mock_fetch.side_effect = [broken_download, unpaywall_lookup, no_s2]
        work = _work(doi="10.1/abc", oa_url=same_url)

        result = resolve_full_text(work, "me@example.com", ezproxy_cookie=None, pace_per_hour=25)

        self.assertEqual(result.status, "needs_manual")
        # oa_url download + unpaywall lookup + semantic_scholar lookup = 3 --
        # same_url must never be re-downloaded a second time via unpaywall.
        self.assertEqual(mock_fetch.call_count, 3)
```

Change these two existing assertions (the new logic now distinguishes which provider's URL actually succeeded, instead of collapsing every OA source into `"open_access"`):

In `test_falls_back_to_semantic_scholar_when_unpaywall_has_no_oa`, change:
```python
        self.assertEqual(result.tier, "open_access")
```
to:
```python
        self.assertEqual(result.tier, "semantic_scholar")
```

In `test_falls_back_to_core_when_semantic_scholar_has_no_oa`, change:
```python
        self.assertEqual(result.tier, "open_access")
```
to:
```python
        self.assertEqual(result.tier, "core")
```

- [ ] **Step 2: Run tests to verify the new ones fail and note current tier mismatches**

Run: `python -m pytest tests/discovery/discover_journal_articles/test_access.py -v -k ResolveFullText`
Expected: `test_falls_through_to_next_oa_provider_when_first_oa_url_fails_download` and `test_does_not_redownload_a_url_already_tried_by_an_earlier_provider` FAIL (today's code never reaches Unpaywall once `work.oa_url` is present); `test_falls_back_to_semantic_scholar_when_unpaywall_has_no_oa` and `test_falls_back_to_core_when_semantic_scholar_has_no_oa` now FAIL on the updated tier assertion.

- [ ] **Step 3: Implement the lazy candidate generator**

Replace `resolve_full_text` in `access.py` (lines 141-165) with:

```python
def _oa_candidates(work: Work, mailto: str, core_api_key: str | None):
    """Lazily yields (tier_name, url) pairs in provider-preference order.
    Each try_*() call only runs once the generator is advanced past the
    previous yield -- a successful early tier never queries a later one,
    but a *failed download* of an early tier's URL (handled by the
    caller) resumes this generator to fetch the next candidate, instead
    of giving up after the first present-but-broken URL (the audit's
    core finding)."""
    if work.oa_url:
        yield "open_access", work.oa_url
    url = try_unpaywall(work.doi, mailto)
    if url:
        yield "unpaywall", url
    url = try_semantic_scholar(work.doi)
    if url:
        yield "semantic_scholar", url
    url = try_core(work.doi, core_api_key)
    if url:
        yield "core", url


def resolve_full_text(
    work: Work, mailto: str, ezproxy_cookie: str | None, pace_per_hour: float, core_api_key: str | None = None,
) -> AccessResult:
    seen_urls: set[str] = set()
    for tier, url in _oa_candidates(work, mailto, core_api_key):
        if url in seen_urls:
            continue
        seen_urls.add(url)
        content = _download(url, 0)  # OA hosts carry none of the EZProxy account-safety risk
        if content:
            return AccessResult(status="fetched", content=content, tier=tier)

    arxiv_url = try_arxiv_url(work.arxiv_id)
    if arxiv_url:
        content = _download(arxiv_url, 0)  # arXiv is a real API, not a scraping target
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

Run: `python -m pytest tests/discovery/discover_journal_articles/test_access.py -v`
Expected: PASS (all tests, including the 11 pre-existing ones -- walk through `test_html_response_never_written_falls_through_to_needs_manual`, `test_core_skipped_without_api_key_falls_through_to_arxiv`, `test_falls_back_to_arxiv`, `test_falls_back_to_ezproxy_with_cookie`, `test_needs_manual_without_any_viable_tier`, and `test_terminal_http_error_falls_through_instead_of_crashing` by hand if any fail -- they were verified compatible with the new generator during planning, but confirm against the actual run).

- [ ] **Step 5: Commit**

```bash
git add discovery/discover_journal_articles/access.py tests/discovery/discover_journal_articles/test_access.py
git commit -m "fix(discover_journal_articles): keep trying OA providers after a broken URL"
```

---

### Task 3: HTTP timeouts and Retry-After date parsing

**Files:**
- Modify: `discovery/discover_journal_articles/http_utils.py`
- Test: `tests/discovery/discover_journal_articles/test_http_utils.py`

**Interfaces:**
- Produces: `fetch_with_retries(..., timeout: float = 30.0, ...)` now defaults every request to a 30s timeout unless the caller already passed one; `Retry-After` now accepts either numeric seconds or an HTTP-date string.

- [ ] **Step 1: Write the failing tests**

Append to `tests/discovery/discover_journal_articles/test_http_utils.py`:

```python
class TestFetchWithRetriesTimeoutAndRetryAfter(unittest.TestCase):
    @patch("discovery.discover_journal_articles.http_utils.time.sleep")
    @patch("discovery.discover_journal_articles.http_utils.requests.request")
    def test_defaults_to_a_30_second_timeout(self, mock_request, mock_sleep):
        mock_request.return_value = MagicMock(status_code=200, headers={})

        fetch_with_retries("GET", "https://example.com")

        _, kwargs = mock_request.call_args
        self.assertEqual(kwargs["timeout"], 30.0)

    @patch("discovery.discover_journal_articles.http_utils.time.sleep")
    @patch("discovery.discover_journal_articles.http_utils.requests.request")
    def test_caller_supplied_timeout_is_not_overridden(self, mock_request, mock_sleep):
        mock_request.return_value = MagicMock(status_code=200, headers={})

        fetch_with_retries("GET", "https://example.com", timeout=5)

        _, kwargs = mock_request.call_args
        self.assertEqual(kwargs["timeout"], 5)

    @patch("discovery.discover_journal_articles.http_utils.time.sleep")
    @patch("discovery.discover_journal_articles.http_utils.requests.request")
    def test_retry_after_accepts_an_http_date(self, mock_request, mock_sleep):
        from email.utils import format_datetime
        from datetime import datetime, timedelta, timezone

        retry_at = datetime.now(timezone.utc) + timedelta(seconds=10)
        rate_limited = MagicMock(status_code=429, headers={"Retry-After": format_datetime(retry_at, usegmt=True)})
        success = MagicMock(status_code=200, headers={})
        mock_request.side_effect = [rate_limited, success]

        response = fetch_with_retries("GET", "https://example.com")

        self.assertIs(response, success)
        mock_sleep.assert_called_once()
        waited = mock_sleep.call_args[0][0]
        self.assertAlmostEqual(waited, 10.0, delta=1.0)

    @patch("discovery.discover_journal_articles.http_utils.time.sleep")
    @patch("discovery.discover_journal_articles.http_utils.requests.request")
    def test_retry_after_in_the_past_clamps_to_zero(self, mock_request, mock_sleep):
        from email.utils import format_datetime
        from datetime import datetime, timedelta, timezone

        retry_at = datetime.now(timezone.utc) - timedelta(seconds=30)
        rate_limited = MagicMock(status_code=429, headers={"Retry-After": format_datetime(retry_at, usegmt=True)})
        success = MagicMock(status_code=200, headers={})
        mock_request.side_effect = [rate_limited, success]

        fetch_with_retries("GET", "https://example.com")

        mock_sleep.assert_called_once_with(0.0)

    @patch("discovery.discover_journal_articles.http_utils.time.sleep")
    @patch("discovery.discover_journal_articles.http_utils.requests.request")
    def test_malformed_retry_after_falls_back_to_default_backoff(self, mock_request, mock_sleep):
        rate_limited = MagicMock(status_code=429, headers={"Retry-After": "not-a-value"})
        success = MagicMock(status_code=200, headers={})
        mock_request.side_effect = [rate_limited, success]

        fetch_with_retries("GET", "https://example.com", backoff_seconds=2.0)

        mock_sleep.assert_called_once_with(2.0)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/discovery/discover_journal_articles/test_http_utils.py -v -k TimeoutAndRetryAfter`
Expected: FAIL (`timeout` not in call kwargs; HTTP-date/malformed `Retry-After` raise `ValueError` from today's bare `float(retry_after)`).

- [ ] **Step 3: Implement**

In `http_utils.py`, add the import and helper, then update `fetch_with_retries`:

```python
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone
```

```python
def _parse_retry_after(value: str | None) -> float | None:
    """Accepts either a numeric seconds value or an HTTP-date (RFC 7231
    allows both). Returns None if the header is absent or unparseable
    either way, so the caller falls back to its own default backoff."""
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        pass
    try:
        retry_at = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if retry_at.tzinfo is None:
        retry_at = retry_at.replace(tzinfo=timezone.utc)
    return max((retry_at - datetime.now(timezone.utc)).total_seconds(), 0.0)
```

```python
def fetch_with_retries(
    method: str,
    url: str,
    *,
    retries: int = 3,
    backoff_seconds: float = 2.0,
    max_wait_seconds: float = 60.0,
    timeout: float = 30.0,
    **request_kwargs,
) -> requests.Response:
    request_kwargs.setdefault("timeout", timeout)
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
            wait = _parse_retry_after(response.headers.get("Retry-After"))
            if wait is None:
                wait = backoff_seconds * (attempt + 1)
            time.sleep(min(wait, max_wait_seconds))
            continue
        break

    if last_response is not None:
        raise FetchError(
            f"{method} {url} failed with status {last_response.status_code} after {retries} attempts"
        )
    raise FetchError(f"{method} {url} failed after {retries} attempts: {last_error}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/discovery/discover_journal_articles/test_http_utils.py -v`
Expected: PASS (all tests, including the pre-existing numeric-`Retry-After` test, which still expects `5.0`).

- [ ] **Step 5: Commit**

```bash
git add discovery/discover_journal_articles/http_utils.py tests/discovery/discover_journal_articles/test_http_utils.py
git commit -m "fix(discover_journal_articles): add request timeouts, parse HTTP-date Retry-After"
```

---

### Task 4: Honest examined vs. accepted counters

**Files:**
- Modify: `discovery/discover_journal_articles/relevance.py:80-117`
- Modify: `discovery/discover_journal_articles/discover.py:60-69,134-137`
- Test: `tests/discovery/discover_journal_articles/test_relevance.py`
- Test: `tests/discovery/discover_journal_articles/test_discover.py`

**Interfaces:**
- Produces: `select_relevant_works(...) -> tuple[list[ScoredWork], int]` (was `-> list[ScoredWork]`); second element is the true count of candidates that reached `score_work`, independent of the threshold/`max_results` outcome.

- [ ] **Step 1: Update `test_relevance.py` for the new return shape**

In `tests/discovery/discover_journal_articles/test_relevance.py`, every call site of `select_relevant_works` currently does `selected = select_relevant_works(...)`. Change each to unpack both values. There are 8 call sites; apply this exact pattern to each:

```python
        selected, examined = select_relevant_works(
            works, model, "prompt", threshold=0.5, max_results=10, max_examined=10,
        )
```

(keeping each call's own `threshold=`/`max_results=`/`max_examined=` values as they already are) and add one new test:

```python
    def test_examined_counts_every_scored_candidate_not_just_accepted(self):
        # Confirmed real: today's caller mislabels len(accepted) as
        # "examined" -- a candidate that was scored and rejected (below
        # threshold) must still count toward examined.
        model = self._model_scoring({
            "prompt": [1.0, 0.0], "on topic": [1.0, 0.0], "off topic": [0.0, 1.0],
        })
        works = [_work(1, "on topic"), _work(2, "off topic"), _work(3, "off topic")]

        selected, examined = select_relevant_works(
            works, model, "prompt", threshold=0.5, max_results=10, max_examined=10,
        )

        self.assertEqual(len(selected), 1)
        self.assertEqual(examined, 3)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/discovery/discover_journal_articles/test_relevance.py -v -k SelectRelevantWorks`
Expected: FAIL (`ValueError: not enough values to unpack`, since today's function returns a bare list).

- [ ] **Step 3: Implement**

In `relevance.py`, change the end of `select_relevant_works`:

```python
def select_relevant_works(
    works: Iterable[Work],
    model,
    relevance_prompt: str,
    threshold: float,
    max_results: int,
    max_examined: int,
) -> tuple[list[ScoredWork], int]:
    """... (docstring unchanged) ..."""
    prompt_embedding = embed_text(model, relevance_prompt)
    scored: list[ScoredWork] = []
    seen_titles: set[str] = set()
    examined = 0

    for work in works:
        if examined >= max_examined:
            break
        examined += 1

        normalized_title = _normalize_title(work.title)
        if normalized_title in seen_titles:
            continue

        score, scored_from = score_work(model, prompt_embedding, work)
        if score is not None and score >= threshold:
            scored.append(ScoredWork(work=work, score=score, scored_from=scored_from))
            seen_titles.add(normalized_title)
            if len(scored) >= max_results:
                break

    return scored, examined
```

(Only the signature's return type and final `return` line change; the loop body is untouched.)

- [ ] **Step 4: Run relevance tests to verify they pass**

Run: `python -m pytest tests/discovery/discover_journal_articles/test_relevance.py -v`
Expected: PASS (all tests)

- [ ] **Step 5: Update `discover.py`'s caller**

In `discover.py`, change `run()` (lines 60-69):

```python
    counts = {"examined": 0, "accepted": 0, "already_seen": 0, "fetched": 0, "needs_manual": 0}

    model = load_relevance_model()
    works = resolve_works(args.faculty, args.topic, mailto, args.batch_size)
    unseen_works = skip_already_seen(works, manifest, counts)
    scored, examined = select_relevant_works(
        unseen_works, model, args.relevance_prompt, args.relevance_threshold,
        args.max_results, args.max_examined,
    )
    counts["examined"] = examined
    counts["accepted"] = len(scored)
```

And change the summary print in `main()` (lines 134-137):

```python
    print(f"\nExamined and scored: {counts['examined']}")
    print(f"Already seen (skipped): {counts['already_seen']}")
    print(f"Accepted (passed relevance threshold): {counts['accepted']}")
    print(f"Fetched: {counts['fetched']}")
    print(f"Needs manual download: {counts['needs_manual']}")
```

- [ ] **Step 6: Update `test_discover.py`'s mocks**

`select_relevant_works` is mocked (not called for real) in every `test_discover.py` test, so each mock's return value must become a tuple. Update every site:

In `test_fetched_work_writes_pdf_and_sidecar_and_updates_manifest`, `test_needs_manual_work_recorded_without_pdf`, `test_needs_manual_work_still_gets_a_folder_and_link`, `test_run_writes_needs_manual_worklist`, `test_zotero_sync_called_only_when_flag_set_and_configured`, and `test_zotero_sync_skipped_without_flag`, change:

```python
            mock_select.return_value = [ScoredWork(work=work, score=0.9)]
```

to:

```python
            mock_select.return_value = ([ScoredWork(work=work, score=0.9)], 1)
```

In `test_already_seen_work_is_filtered_before_relevance_scoring`, change:

```python
            mock_select.side_effect = lambda works, *a, **kw: [ScoredWork(work=w, score=1.0) for w in works]
```

to:

```python
            def _select_side_effect(works, *a, **kw):
                # works may be a one-shot generator -- materialize once,
                # not twice, or the second pass sees an exhausted iterator.
                materialized = list(works)
                return [ScoredWork(work=w, score=1.0) for w in materialized], len(materialized)

            mock_select.side_effect = _select_side_effect
```

and add one new test confirming the distinction actually shows up through `run()`:

```python
    @patch("discovery.discover_journal_articles.discover.load_relevance_model", return_value=MagicMock())
    @patch("discovery.discover_journal_articles.discover.resolve_works", return_value=iter([]))
    @patch("discovery.discover_journal_articles.discover.select_relevant_works")
    @patch("discovery.discover_journal_articles.discover.resolve_full_text")
    def test_examined_and_accepted_are_reported_separately(
        self, mock_resolve_full_text, mock_select, mock_resolve_works, mock_load_model
    ):
        with tempfile.TemporaryDirectory() as tmp:
            work = _work(6)
            mock_select.return_value = ([ScoredWork(work=work, score=0.9)], 5)
            mock_resolve_full_text.return_value = AccessResult(status="fetched", content=b"%PDF-1.4", tier="open_access")

            counts = run(_args(articles_dir=tmp, mailto="me@example.com", ezproxy_cookie=None))

            self.assertEqual(counts["examined"], 5)
            self.assertEqual(counts["accepted"], 1)
```

- [ ] **Step 7: Run discover tests to verify they pass**

Run: `python -m pytest tests/discovery/discover_journal_articles/test_discover.py -v`
Expected: PASS (all tests)

- [ ] **Step 8: Commit**

```bash
git add discovery/discover_journal_articles/relevance.py discovery/discover_journal_articles/discover.py tests/discovery/discover_journal_articles/test_relevance.py tests/discovery/discover_journal_articles/test_discover.py
git commit -m "fix(discover_journal_articles): report examined candidates separately from accepted"
```

---

### Task 5: Per-run wall-clock budget with honest partial reporting

**Files:**
- Modify: `discovery/discover_journal_articles/discover.py`
- Test: `tests/discovery/discover_journal_articles/test_discover.py`

**Interfaces:**
- Consumes: `counts` dict from Task 4 (`examined`, `accepted`, `already_seen`, `fetched`, `needs_manual`).
- Produces: `run()` now also sets `counts["stopped_reason"]` (`None` or `"time_budget_exhausted"`); new `--time-budget-seconds` CLI flag (default `None` = unlimited).

**Design note:** scoped to a wall-clock budget only (not a separate request-count budget) -- the audit's actual concern is a run that keeps retrying through sustained 429/504s far longer than expected, and wall-clock time already bounds that; a request counter would need threading a shared counter through every HTTP call site across `access.py`/`discovery.py`/`http_utils.py`, which is unrelated surgery for the same practical benefit.

- [ ] **Step 1: Write the failing test**

Append to `tests/discovery/discover_journal_articles/test_discover.py`:

```python
    @patch("discovery.discover_journal_articles.discover.time.monotonic")
    @patch("discovery.discover_journal_articles.discover.load_relevance_model", return_value=MagicMock())
    @patch("discovery.discover_journal_articles.discover.resolve_works", return_value=iter([]))
    @patch("discovery.discover_journal_articles.discover.select_relevant_works")
    @patch("discovery.discover_journal_articles.discover.resolve_full_text")
    def test_stops_cleanly_when_time_budget_is_exhausted(
        self, mock_resolve_full_text, mock_select, mock_resolve_works, mock_load_model, mock_monotonic
    ):
        with tempfile.TemporaryDirectory() as tmp:
            work_a, work_b = _work(7), _work(8, doi="10.1/def")
            mock_select.return_value = ([ScoredWork(work=work_a, score=0.9), ScoredWork(work=work_b, score=0.9)], 2)
            mock_resolve_full_text.return_value = AccessResult(status="fetched", content=b"%PDF-1.4", tier="open_access")
            # Deadline check happens once before the loop (sets the
            # deadline) and once per iteration: 0.0 establishes the
            # deadline, 100.0 is already past a 1-second budget on the
            # first per-item check.
            mock_monotonic.side_effect = [0.0, 100.0, 100.0]

            counts = run(_args(articles_dir=tmp, mailto="me@example.com", ezproxy_cookie=None, time_budget_seconds=1.0))

            self.assertEqual(counts["stopped_reason"], "time_budget_exhausted")
            mock_resolve_full_text.assert_not_called()

    @patch("discovery.discover_journal_articles.discover.load_relevance_model", return_value=MagicMock())
    @patch("discovery.discover_journal_articles.discover.resolve_works", return_value=iter([]))
    @patch("discovery.discover_journal_articles.discover.select_relevant_works")
    @patch("discovery.discover_journal_articles.discover.resolve_full_text")
    def test_no_time_budget_means_stopped_reason_is_none(
        self, mock_resolve_full_text, mock_select, mock_resolve_works, mock_load_model
    ):
        with tempfile.TemporaryDirectory() as tmp:
            work = _work(9)
            mock_select.return_value = ([ScoredWork(work=work, score=0.9)], 1)
            mock_resolve_full_text.return_value = AccessResult(status="fetched", content=b"%PDF-1.4", tier="open_access")

            counts = run(_args(articles_dir=tmp, mailto="me@example.com", ezproxy_cookie=None))

            self.assertIsNone(counts["stopped_reason"])
            mock_resolve_full_text.assert_called_once()
```

Add `time_budget_seconds=None` to the `defaults` dict in `_args()` at the top of the file.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/discovery/discover_journal_articles/test_discover.py -v -k time_budget`
Expected: FAIL (`KeyError: 'stopped_reason'`).

- [ ] **Step 3: Implement**

In `discover.py`, add `import time` near the top (alongside the existing `os`/`sys` imports), then change `run()`:

```python
def run(args: argparse.Namespace) -> dict:
    mailto = getattr(args, "mailto", None) or os.environ.get("OPENALEX_CONTACT_EMAIL")
    ezproxy_cookie = getattr(args, "ezproxy_cookie", None) or os.environ.get("EZPROXY_SESSION_COOKIE")
    core_api_key = getattr(args, "core_api_key", None) or os.environ.get("CORE_API_KEY")

    manifest_file = manifest_path(args.articles_dir)
    manifest = load_manifest(manifest_file)
    counts = {"examined": 0, "accepted": 0, "already_seen": 0, "fetched": 0, "needs_manual": 0, "stopped_reason": None}

    time_budget_seconds = getattr(args, "time_budget_seconds", None)
    deadline = time.monotonic() + time_budget_seconds if time_budget_seconds else None

    model = load_relevance_model()
    works = resolve_works(args.faculty, args.topic, mailto, args.batch_size)
    unseen_works = skip_already_seen(works, manifest, counts)
    scored, examined = select_relevant_works(
        unseen_works, model, args.relevance_prompt, args.relevance_threshold,
        args.max_results, args.max_examined,
    )
    counts["examined"] = examined
    counts["accepted"] = len(scored)

    for scored_work in scored:
        if deadline is not None and time.monotonic() >= deadline:
            counts["stopped_reason"] = "time_budget_exhausted"
            break

        work = scored_work.work
        key = manifest_key(work)

        result = resolve_full_text(work, mailto, ezproxy_cookie, args.pace_per_hour, core_api_key)
        if result.status == "fetched":
            folder = route_to_folder(args.articles_dir, work)
            pdf_path = folder / pdf_filename(work)
            pdf_path.write_bytes(result.content)
            write_sidecar(pdf_path, work, scored_work.score, result.tier)
            record_outcome(manifest, key, "fetched", folder=folder.name)
            counts["fetched"] += 1
            if args.zotero:
                _sync_zotero_if_configured(work, pdf_path, folder.name, args)
        else:
            folder = route_to_folder(args.articles_dir, work)
            record_outcome(manifest, key, "needs_manual", folder=folder.name, metadata={
                "title": work.title,
                "authors": work.authors,
                "year": work.year,
                "doi_url": doi_url(work),
            })
            counts["needs_manual"] += 1

    save_manifest(manifest_file, manifest)
    write_needs_manual_worklist(manifest, args.articles_dir)
    return counts
```

Add the CLI flag in `main()`, right after `--pace-per-hour`:

```python
    parser.add_argument(
        "--time-budget-seconds", type=float, default=None,
        help="Stop the fetch loop cleanly after this many seconds of wall-clock time, reporting partial "
             "counts instead of implying the run completed. Omit for no limit.",
    )
```

And after the existing summary prints in `main()`, add:

```python
    if counts["stopped_reason"]:
        print(f"\nWARNING: run stopped early ({counts['stopped_reason']}); the counts above are partial.")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/discovery/discover_journal_articles/test_discover.py -v`
Expected: PASS (all tests)

- [ ] **Step 5: Commit**

```bash
git add discovery/discover_journal_articles/discover.py tests/discovery/discover_journal_articles/test_discover.py
git commit -m "feat(discover_journal_articles): add a per-run wall-clock budget with honest partial reporting"
```

---

### Task 6: Atomic writes for manifest and sidecar JSON

**Files:**
- Create: `discovery/discover_journal_articles/atomic_io.py`
- Modify: `discovery/discover_journal_articles/manifest.py:29-33`
- Modify: `discovery/discover_journal_articles/metadata_sidecar.py:20-33`
- Test: `tests/discovery/discover_journal_articles/test_atomic_io.py`
- Test: `tests/discovery/discover_journal_articles/test_manifest.py`
- Test: `tests/discovery/discover_journal_articles/test_metadata_sidecar.py`

**Interfaces:**
- Produces: `write_json_atomic(path, data) -> None` in `atomic_io.py` — writes to a temp file in the same directory, then `os.replace()`s over the target. Used by `manifest.py`'s `save_manifest` and `metadata_sidecar.py`'s `write_sidecar`, and by every later task that writes manifest/sidecar JSON (Tasks 9, 11, 12, 13).

- [ ] **Step 1: Write the failing test for the new helper**

Create `tests/discovery/discover_journal_articles/test_atomic_io.py`:

```python
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from discovery.discover_journal_articles.atomic_io import write_json_atomic


class TestWriteJsonAtomic(unittest.TestCase):
    def test_writes_and_round_trips(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nested" / "data.json"
            write_json_atomic(path, {"a": 1})
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"a": 1})

    def test_overwrites_existing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "data.json"
            write_json_atomic(path, {"a": 1})
            write_json_atomic(path, {"a": 2})
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"a": 2})

    def test_leaves_original_file_intact_if_dump_fails_midway(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "data.json"
            write_json_atomic(path, {"a": 1})

            with patch("discovery.discover_journal_articles.atomic_io.json.dump", side_effect=RuntimeError("boom")):
                with self.assertRaises(RuntimeError):
                    write_json_atomic(path, {"a": 2})

            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"a": 1})
            # No leftover .tmp file in the directory.
            self.assertEqual(list(Path(tmp).glob("*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/discovery/discover_journal_articles/test_atomic_io.py -v`
Expected: FAIL (`ModuleNotFoundError: discovery.discover_journal_articles.atomic_io`).

- [ ] **Step 3: Implement**

Create `discovery/discover_journal_articles/atomic_io.py`:

```python
"""
atomic_io.py
Shared atomic-write helper: writes JSON to a temp file in the same
directory as the target, then os.replace()s over it, so a crash
mid-write never leaves a half-written manifest or sidecar.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path


def write_json_atomic(path, data) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=True)
        os.replace(tmp_name, path)
    except Exception:
        if os.path.exists(tmp_name):
            os.remove(tmp_name)
        raise
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/discovery/discover_journal_articles/test_atomic_io.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Wire into `manifest.py`**

Change `manifest.py`:

```python
from discovery.discover_journal_articles.atomic_io import write_json_atomic
from discovery.discover_journal_articles.discovery import Work
```

```python
def save_manifest(path, manifest: dict) -> None:
    write_json_atomic(path, manifest)
```

(Remove the now-unused `import json` if nothing else in the file needs it -- `load_manifest` still needs `json.load`, so keep the import.)

- [ ] **Step 6: Wire into `metadata_sidecar.py`**

Change `metadata_sidecar.py`:

```python
from discovery.discover_journal_articles.atomic_io import write_json_atomic
from discovery.discover_journal_articles.discovery import Work
```

```python
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
    write_json_atomic(sidecar_path(pdf_path), data)
```

(Remove the now-unused `import json` from `metadata_sidecar.py` entirely -- nothing else in that file uses it.)

- [ ] **Step 7: Run manifest and sidecar tests to verify they still pass**

Run: `python -m pytest tests/discovery/discover_journal_articles/test_manifest.py tests/discovery/discover_journal_articles/test_metadata_sidecar.py -v`
Expected: PASS (all existing tests, unchanged -- `write_json_atomic` preserves the same `parent.mkdir` + round-trip behavior).

- [ ] **Step 8: Commit**

```bash
git add discovery/discover_journal_articles/atomic_io.py discovery/discover_journal_articles/manifest.py discovery/discover_journal_articles/metadata_sidecar.py tests/discovery/discover_journal_articles/test_atomic_io.py
git commit -m "fix(discover_journal_articles): write manifest and sidecar JSON atomically"
```

---

### Task 7: Scoped `--retry` for existing `needs_manual` entries

**Files:**
- Modify: `discovery/discover_journal_articles/discover.py`
- Test: `tests/discovery/discover_journal_articles/test_discover.py`

**Interfaces:**
- Consumes: the fixed `resolve_full_text` from Task 2; `resolve_work_by_doi` from `discovery.py` (not currently imported into `discover.py`).
- Produces: `retry_needs_manual(args: argparse.Namespace) -> dict` with `{"fetched": int, "needs_manual": int, "not_found": int}`; new `--retry ID` CLI flag (repeatable).

- [ ] **Step 1: Write the failing tests**

Append to `tests/discovery/discover_journal_articles/test_discover.py`:

```python
class TestRetryNeedsManual(unittest.TestCase):
    @patch("discovery.discover_journal_articles.discover.resolve_work_by_doi")
    @patch("discovery.discover_journal_articles.discover.resolve_full_text")
    def test_retries_a_named_needs_manual_entry_and_records_success(self, mock_resolve_full_text, mock_resolve_by_doi):
        with tempfile.TemporaryDirectory() as tmp:
            from discovery.discover_journal_articles.manifest import manifest_path, record_outcome, save_manifest, load_manifest
            path = manifest_path(tmp)
            manifest = load_manifest(path)
            record_outcome(manifest, "10.1/abc", "needs_manual", folder="climate-change",
                            metadata={"title": "Paper 1", "authors": [], "year": 2024, "doi_url": "https://doi.org/10.1/abc"})
            save_manifest(path, manifest)

            mock_resolve_by_doi.return_value = _work(1, doi="10.1/abc")
            mock_resolve_full_text.return_value = AccessResult(status="fetched", content=b"%PDF-1.4", tier="unpaywall")

            from discovery.discover_journal_articles.discover import retry_needs_manual
            args = _args(articles_dir=tmp, mailto="me@example.com", ezproxy_cookie=None, retry=["10.1/abc"])
            counts = retry_needs_manual(args)

            self.assertEqual(counts["fetched"], 1)
            manifest = load_manifest(path)
            self.assertEqual(manifest["10.1/abc"]["status"], "fetched")

    @patch("discovery.discover_journal_articles.discover.resolve_work_by_doi")
    @patch("discovery.discover_journal_articles.discover.resolve_full_text")
    def test_retry_failure_leaves_entry_needs_manual(self, mock_resolve_full_text, mock_resolve_by_doi):
        with tempfile.TemporaryDirectory() as tmp:
            from discovery.discover_journal_articles.manifest import manifest_path, record_outcome, save_manifest, load_manifest
            path = manifest_path(tmp)
            manifest = load_manifest(path)
            record_outcome(manifest, "10.1/abc", "needs_manual", folder="climate-change")
            save_manifest(path, manifest)

            mock_resolve_by_doi.return_value = _work(1, doi="10.1/abc")
            mock_resolve_full_text.return_value = AccessResult(status="needs_manual")

            from discovery.discover_journal_articles.discover import retry_needs_manual
            args = _args(articles_dir=tmp, mailto="me@example.com", ezproxy_cookie=None, retry=["10.1/abc"])
            counts = retry_needs_manual(args)

            self.assertEqual(counts["needs_manual"], 1)

    def test_retry_only_touches_named_ids_not_the_rest_of_the_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            from discovery.discover_journal_articles.manifest import manifest_path, record_outcome, save_manifest, load_manifest
            path = manifest_path(tmp)
            manifest = load_manifest(path)
            record_outcome(manifest, "10.1/other", "fetched", folder="misc")
            save_manifest(path, manifest)

            from discovery.discover_journal_articles.discover import retry_needs_manual
            args = _args(articles_dir=tmp, mailto="me@example.com", ezproxy_cookie=None, retry=["10.1/not-in-manifest"])
            counts = retry_needs_manual(args)

            self.assertEqual(counts["not_found"], 1)
            manifest = load_manifest(path)
            self.assertEqual(manifest["10.1/other"]["status"], "fetched")

    def test_retry_skips_an_openalex_id_only_entry_without_crashing(self):
        # No bare DOI to look up by -- resolve_work_by_doi has nothing to
        # query. Must be reported as not_found, not raise.
        with tempfile.TemporaryDirectory() as tmp:
            from discovery.discover_journal_articles.manifest import manifest_path, record_outcome, save_manifest, load_manifest
            path = manifest_path(tmp)
            manifest = load_manifest(path)
            record_outcome(manifest, "https://openalex.org/W123", "needs_manual", folder="misc")
            save_manifest(path, manifest)

            from discovery.discover_journal_articles.discover import retry_needs_manual
            args = _args(articles_dir=tmp, mailto="me@example.com", ezproxy_cookie=None, retry=["https://openalex.org/W123"])
            counts = retry_needs_manual(args)

            self.assertEqual(counts["not_found"], 1)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/discovery/discover_journal_articles/test_discover.py -v -k RetryNeedsManual`
Expected: FAIL (`ImportError: cannot import name 'retry_needs_manual'`).

- [ ] **Step 3: Implement**

In `discover.py`, change the `discovery` import line to also bring in `resolve_work_by_doi`:

```python
from discovery.discover_journal_articles.discovery import doi_url, resolve_work_by_doi, resolve_works
```

Add a new function (near `run()`):

```python
def retry_needs_manual(args: argparse.Namespace) -> dict:
    """Re-attempts full-text access for exactly the manifest keys named
    in args.retry, under the current (fixed) fallback chain -- never
    touches discovery/scoring or any other manifest entry. A manifest
    key built from an OpenAlex id rather than a DOI (no bare DOI to
    query by) is reported as not_found rather than attempted."""
    mailto = getattr(args, "mailto", None) or os.environ.get("OPENALEX_CONTACT_EMAIL")
    ezproxy_cookie = getattr(args, "ezproxy_cookie", None) or os.environ.get("EZPROXY_SESSION_COOKIE")
    core_api_key = getattr(args, "core_api_key", None) or os.environ.get("CORE_API_KEY")

    manifest_file = manifest_path(args.articles_dir)
    manifest = load_manifest(manifest_file)
    counts = {"fetched": 0, "needs_manual": 0, "not_found": 0}

    for key in args.retry:
        entry = manifest.get(key)
        if entry is None or entry.get("status") != "needs_manual" or key.startswith("http"):
            counts["not_found"] += 1
            continue

        work = resolve_work_by_doi(key, mailto)
        if work is None:
            counts["not_found"] += 1
            continue

        result = resolve_full_text(work, mailto, ezproxy_cookie, args.pace_per_hour, core_api_key)
        if result.status == "fetched":
            folder = route_to_folder(args.articles_dir, work)
            pdf_path = folder / pdf_filename(work)
            pdf_path.write_bytes(result.content)
            write_sidecar(pdf_path, work, entry.get("relevance_score"), result.tier)
            record_outcome(manifest, key, "fetched", folder=folder.name)
            counts["fetched"] += 1
        else:
            counts["needs_manual"] += 1

    save_manifest(manifest_file, manifest)
    return counts
```

Add the CLI flag in `main()`, after `--zotero`:

```python
    parser.add_argument(
        "--retry", action="append", default=[], metavar="ID",
        help="Re-attempt access for this existing needs_manual manifest key (bare DOI only; repeatable). "
             "Skips discovery/scoring entirely and touches no other manifest entry.",
    )
```

And change the entry-mode dispatch in `main()` (the existing `if not args.faculty and not args.topic:` check) to:

```python
    load_dotenv_override()
    if not os.environ.get("OPENALEX_CONTACT_EMAIL"):
        print("ERROR: OPENALEX_CONTACT_EMAIL must be set in .env (required by OpenAlex/Unpaywall).")
        sys.exit(1)

    if args.retry:
        counts = retry_needs_manual(args)
        print(f"\nRetried: {len(args.retry)}")
        print(f"Fetched: {counts['fetched']}")
        print(f"Still needs manual: {counts['needs_manual']}")
        print(f"Not found / not retryable: {counts['not_found']}")
        return

    if not args.faculty and not args.topic:
        parser.error("at least one --faculty or --topic is required (unless using --retry)")

    counts = run(args)
```

(Move the `load_dotenv_override()`/`OPENALEX_CONTACT_EMAIL` check above the `faculty`/`topic` validation, since `--retry` mode needs it too but skips the `faculty`/`topic` requirement entirely.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/discovery/discover_journal_articles/test_discover.py -v`
Expected: PASS (all tests)

- [ ] **Step 5: Commit**

```bash
git add discovery/discover_journal_articles/discover.py tests/discovery/discover_journal_articles/test_discover.py
git commit -m "feat(discover_journal_articles): add scoped --retry for existing needs_manual entries"
```

---

## Section B: Classification proposal mode

### Task 8: `Work.topics` field populated from OpenAlex

**Files:**
- Modify: `discovery/discover_journal_articles/discovery.py`
- Test: `tests/discovery/discover_journal_articles/test_discovery.py`

**Interfaces:**
- Produces: `Topic` dataclass (`id: str`, `display_name: str`, `score: float`) and `Work.topics: list[Topic]`, sorted highest-score-first, parsed from OpenAlex's `topics` field (the modern replacement for deprecated `concepts`, which stays as-is for existing callers).

- [ ] **Step 1: Write the failing tests**

The file already has an `_openalex_work(...)` fixture helper (used by `TestIterAuthorWorks`) and a `_response(json_data)` helper. Extend the fixture with a `topics` parameter, and add tests that go through the public `iter_author_works` API, matching the file's existing style for `concepts` (e.g. `test_prefers_level_zero_concept_for_ordering`).

Change the `_openalex_work` signature and body:

```python
def _openalex_work(title="Untitled", doi="https://doi.org/10.1/abc", arxiv_url=None, work_type="article",
                    concepts=None, topics=None):
    return {
        "id": "https://openalex.org/W1",
        "doi": doi,
        "title": title,
        "type": work_type,
        "publication_year": 2024,
        "authorships": [{"author": {"display_name": "Jane Doe"}}],
        "abstract_inverted_index": {"Climate": [0], "displacement": [1]},
        "concepts": concepts if concepts is not None else [
            {"display_name": "Climate change", "score": 0.9, "level": 2},
            {"display_name": "Economics", "score": 0.4, "level": 0},
        ],
        "topics": topics if topics is not None else [],
        "open_access": {"is_oa": True, "oa_url": "https://example.com/paper.pdf"},
        "locations": [{"landing_page_url": arxiv_url}] if arxiv_url else [],
    }
```

Append a new test class:

```python
class TestWorkFromOpenalexTopics(unittest.TestCase):
    @patch("discovery.discover_journal_articles.discovery.fetch_with_retries")
    def test_parses_topics_sorted_by_score_descending(self, mock_fetch):
        mock_fetch.side_effect = [
            _response({"results": [_openalex_work(topics=[
                {"id": "https://openalex.org/T1", "display_name": "Business", "score": 0.4},
                {"id": "https://openalex.org/T2", "display_name": "Soil Carbon and Nitrogen Dynamics", "score": 0.9},
            ])]}),
            _response({"results": []}),
        ]
        works = list(iter_author_works("https://openalex.org/A1", "me@example.com", batch_size=25))

        self.assertEqual([t.display_name for t in works[0].topics], ["Soil Carbon and Nitrogen Dynamics", "Business"])
        self.assertAlmostEqual(works[0].topics[0].score, 0.9)
        self.assertEqual(works[0].topics[0].id, "https://openalex.org/T2")

    @patch("discovery.discover_journal_articles.discovery.fetch_with_retries")
    def test_no_topics_yields_empty_list(self, mock_fetch):
        mock_fetch.side_effect = [
            _response({"results": [_openalex_work()]}),
            _response({"results": []}),
        ]
        works = list(iter_author_works("https://openalex.org/A1", "me@example.com", batch_size=25))

        self.assertEqual(works[0].topics, [])

    @patch("discovery.discover_journal_articles.discovery.fetch_with_retries")
    def test_a_topic_entry_without_a_display_name_is_skipped(self, mock_fetch):
        mock_fetch.side_effect = [
            _response({"results": [_openalex_work(topics=[
                {"id": "https://openalex.org/T1", "display_name": None, "score": 0.9},
            ])]}),
            _response({"results": []}),
        ]
        works = list(iter_author_works("https://openalex.org/A1", "me@example.com", batch_size=25))

        self.assertEqual(works[0].topics, [])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/discovery/discover_journal_articles/test_discovery.py -v -k Topics`
Expected: FAIL (`Work.topics` doesn't exist yet / `AttributeError`).

- [ ] **Step 3: Implement**

In `discovery.py`, add the `Topic` dataclass right after the `_EXCLUDED_WORK_TYPES` constant:

```python
@dataclass
class Topic:
    id: str
    display_name: str
    score: float
```

Add `topics: list[Topic] = field(default_factory=list)` to the `Work` dataclass (after the existing `concepts` field):

```python
@dataclass
class Work:
    openalex_id: str
    doi: str | None
    title: str
    authors: list[str]
    year: int | None
    abstract: str | None
    concepts: list[str] = field(default_factory=list)
    topics: list[Topic] = field(default_factory=list)
    oa_url: str | None = None
    is_oa: bool = False
    arxiv_id: str | None = None
    page_count: int | None = None
```

Add a parsing helper above `_work_from_openalex`:

```python
def _parse_topics(record: dict) -> list[Topic]:
    """Unlike deprecated Concepts (see the comment in _work_from_openalex
    below), Topics have no numeric "level" to sort by -- ranking by
    score alone is the correct behavior here, and is itself the fix for
    the single-broadest-Concept folder-routing bug (topic_routing.py's
    propose_folder, added separately)."""
    topics = []
    for entry in record.get("topics") or []:
        display_name = entry.get("display_name")
        if not display_name:
            continue
        topics.append(Topic(id=entry.get("id") or "", display_name=display_name, score=entry.get("score") or 0.0))
    return sorted(topics, key=lambda t: -t.score)
```

And add `topics=_parse_topics(record),` to the `Work(...)` construction inside `_work_from_openalex` (right after the existing `concepts=...` line).

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/discovery/discover_journal_articles/test_discovery.py -v`
Expected: PASS (all tests)

- [ ] **Step 5: Commit**

```bash
git add discovery/discover_journal_articles/discovery.py tests/discovery/discover_journal_articles/test_discovery.py
git commit -m "feat(discover_journal_articles): parse OpenAlex Topics onto Work"
```

---

### Task 9: `topics` field in the sidecar schema

**Files:**
- Modify: `discovery/discover_journal_articles/metadata_sidecar.py`
- Test: `tests/discovery/discover_journal_articles/test_metadata_sidecar.py`

**Interfaces:**
- Consumes: `Work.topics` from Task 8.
- Produces: `write_sidecar(...)` now also writes a `"topics"` list of `{"id", "display_name", "score"}` dicts.

- [ ] **Step 1: Write the failing test**

Append to `tests/discovery/discover_journal_articles/test_metadata_sidecar.py`, and update the `_work()` fixture at the top of the file to include topics:

```python
def _work():
    return Work(
        openalex_id="W1", doi="10.1/abc", title="A Paper", authors=["Jane Doe"],
        year=2024, abstract="...", concepts=["Climate change"], page_count=12,
        topics=[Topic(id="https://openalex.org/T1", display_name="Climate Adaptation", score=0.87)],
    )
```

(add `Topic` to the existing `from discovery.discover_journal_articles.discovery import Work` import line: `from discovery.discover_journal_articles.discovery import Topic, Work`)

```python
    def test_writes_topics(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdf_path = Path(tmp) / "paper.pdf"
            write_sidecar(pdf_path, _work(), relevance_score=0.82, source_tier="open_access")

            data = json.loads((Path(tmp) / "paper.meta.json").read_text(encoding="utf-8"))
            self.assertEqual(data["topics"], [{"id": "https://openalex.org/T1", "display_name": "Climate Adaptation", "score": 0.87}])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/discovery/discover_journal_articles/test_metadata_sidecar.py -v -k topics`
Expected: FAIL (`KeyError: 'topics'`).

- [ ] **Step 3: Implement**

In `metadata_sidecar.py`, add `"topics"` to the `data` dict in `write_sidecar`:

```python
    data = {
        "title": work.title,
        "authors": work.authors,
        "year": work.year,
        "doi": work.doi,
        "openalex_id": work.openalex_id,
        "concepts": work.concepts,
        "topics": [{"id": t.id, "display_name": t.display_name, "score": t.score} for t in work.topics],
        "source_tier": source_tier,
        "relevance_score": relevance_score,
        "page_count": work.page_count,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/discovery/discover_journal_articles/test_metadata_sidecar.py -v`
Expected: PASS (all tests, including the two pre-existing ones -- `_work()` now includes a `topics` entry but they don't assert on it, so they're unaffected).

- [ ] **Step 5: Commit**

```bash
git add discovery/discover_journal_articles/metadata_sidecar.py tests/discovery/discover_journal_articles/test_metadata_sidecar.py
git commit -m "feat(discover_journal_articles): store OpenAlex Topics in the sidecar"
```

---

### Task 10: `propose_folder` ranking function

**Files:**
- Modify: `discovery/discover_journal_articles/topic_routing.py`
- Test: `tests/discovery/discover_journal_articles/test_topic_routing.py`

**Interfaces:**
- Consumes: `Topic` from Task 8.
- Produces: `FolderProposal` dataclass (`current_folder: str`, `candidates: list[tuple[str, float]]`) and `propose_folder(topics: list[Topic], current_folder: str) -> FolderProposal`. Pure function — no filesystem access, no mutation of `route_to_folder`'s existing behavior.

- [ ] **Step 1: Write the failing tests**

Append to `tests/discovery/discover_journal_articles/test_topic_routing.py`:

```python
from discovery.discover_journal_articles.discovery import Topic
from discovery.discover_journal_articles.topic_routing import FolderProposal, propose_folder


class TestProposeFolder(unittest.TestCase):
    def test_ranks_candidates_by_score_not_breadth(self):
        # The exact bug this replaces: Concepts-based routing picked the
        # broadest label regardless of score. Topics-based proposing
        # ranks purely by relevance score.
        topics = [
            Topic(id="T1", display_name="Business", score=0.391096),
            Topic(id="T2", display_name="Soil Carbon and Nitrogen Dynamics", score=0.9),
        ]

        proposal = propose_folder(topics, current_folder="business")

        self.assertEqual(proposal.current_folder, "business")
        self.assertEqual(proposal.candidates[0], ("soil-carbon-and-nitrogen-dynamics", 0.9))
        self.assertEqual(proposal.candidates[1], ("business", 0.391096))

    def test_two_topics_sanitizing_to_the_same_folder_name_keep_only_the_higher_scored_one(self):
        topics = [
            Topic(id="T1", display_name="Climate Change", score=0.6),
            Topic(id="T2", display_name="Climate-Change!", score=0.9),
        ]

        proposal = propose_folder(topics, current_folder="misc")

        self.assertEqual(proposal.candidates, [("climate-change", 0.9)])

    def test_empty_topics_yields_no_candidates(self):
        proposal = propose_folder([], current_folder="misc")
        self.assertEqual(proposal.candidates, [])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/discovery/discover_journal_articles/test_topic_routing.py -v -k ProposeFolder`
Expected: FAIL (`ImportError: cannot import name 'propose_folder'`).

- [ ] **Step 3: Implement**

Add to `topic_routing.py` (needs `from dataclasses import dataclass` and `from discovery.discover_journal_articles.discovery import Topic, Work` -- update the existing `from discovery.discover_journal_articles.discovery import Work` import line):

```python
from dataclasses import dataclass

from discovery.discover_journal_articles.discovery import Topic, Work
```

```python
@dataclass
class FolderProposal:
    current_folder: str
    candidates: list[tuple[str, float]]  # (sanitized folder name, score), highest first


def propose_folder(topics: list[Topic], current_folder: str) -> FolderProposal:
    """Ranks candidate folders by each topic's own relevance score --
    deliberately NOT breadth-first like route_to_folder()'s Concepts-
    based rule, since that rule is exactly what files an agriculture
    paper under 'Business' whenever Business happens to be the broadest
    Concept present. Pure function: never touches the filesystem or
    moves anything -- see resolve_folder_proposal() for the only thing
    that actually applies a decision."""
    seen: set[str] = set()
    candidates: list[tuple[str, float]] = []
    for topic in sorted(topics, key=lambda t: -t.score):
        folder_name = sanitize_topic_name(topic.display_name)
        if folder_name in seen:
            continue
        seen.add(folder_name)
        candidates.append((folder_name, topic.score))
    return FolderProposal(current_folder=current_folder, candidates=candidates)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/discovery/discover_journal_articles/test_topic_routing.py -v`
Expected: PASS (all tests, including the pre-existing `route_to_folder`/`sanitize_topic_name`/`pdf_filename` ones, unaffected)

- [ ] **Step 5: Commit**

```bash
git add discovery/discover_journal_articles/topic_routing.py tests/discovery/discover_journal_articles/test_topic_routing.py
git commit -m "feat(discover_journal_articles): add score-ranked propose_folder"
```

---

### Task 11: Read-only classification proposal ledger

**Files:**
- Create: `discovery/discover_journal_articles/topic_proposals.py`
- Test: `tests/discovery/discover_journal_articles/test_topic_proposals.py`

**Interfaces:**
- Consumes: `write_json_atomic` (Task 6), `Topic` (Task 8), `propose_folder`/`sanitize_topic_name` (Task 10).
- Produces: `proposals_ledger_path(articles_dir) -> Path`; `topics_fingerprint(topics: list[Topic]) -> str`; `build_proposals_ledger(manifest: dict, articles_dir) -> list[dict]`; `write_proposals_ledger(manifest: dict, articles_dir) -> Path`. Each ledger entry: `{"key", "title", "current_folder", "candidates": [{"folder", "score"}], "fingerprint", "stale": bool}`.

- [ ] **Step 1: Write the failing tests**

Create `tests/discovery/discover_journal_articles/test_topic_proposals.py`:

```python
import json
import tempfile
import unittest
from pathlib import Path

from discovery.discover_journal_articles.topic_proposals import (
    build_proposals_ledger,
    proposals_ledger_path,
    topics_fingerprint,
    write_proposals_ledger,
)
from discovery.discover_journal_articles.discovery import Topic


def _write_sidecar(folder_dir: Path, stem: str, title: str, topics: list[dict]) -> None:
    folder_dir.mkdir(parents=True, exist_ok=True)
    (folder_dir / f"{stem}.meta.json").write_text(json.dumps({"title": title, "topics": topics}), encoding="utf-8")


class TestTopicsFingerprint(unittest.TestCase):
    def test_same_topics_same_fingerprint_regardless_of_order(self):
        a = [Topic(id="T1", display_name="X", score=0.5), Topic(id="T2", display_name="Y", score=0.9)]
        b = [Topic(id="T2", display_name="Y", score=0.9), Topic(id="T1", display_name="X", score=0.5)]
        self.assertEqual(topics_fingerprint(a), topics_fingerprint(b))

    def test_different_scores_different_fingerprint(self):
        a = [Topic(id="T1", display_name="X", score=0.5)]
        b = [Topic(id="T1", display_name="X", score=0.6)]
        self.assertNotEqual(topics_fingerprint(a), topics_fingerprint(b))


class TestBuildProposalsLedger(unittest.TestCase):
    def test_builds_one_entry_per_paper_with_topics(self):
        with tempfile.TemporaryDirectory() as tmp:
            articles_dir = Path(tmp)
            _write_sidecar(
                articles_dir / "business", "10-1-abc", "Carbon Farming",
                [{"id": "T1", "display_name": "Business", "score": 0.39},
                 {"id": "T2", "display_name": "Soil Carbon and Nitrogen Dynamics", "score": 0.9}],
            )
            manifest = {"10.1/abc": {"status": "fetched", "folder": "business"}}

            entries = build_proposals_ledger(manifest, articles_dir)

            self.assertEqual(len(entries), 1)
            entry = entries[0]
            self.assertEqual(entry["key"], "10.1/abc")
            self.assertEqual(entry["title"], "Carbon Farming")
            self.assertEqual(entry["current_folder"], "business")
            self.assertEqual(entry["candidates"][0]["folder"], "soil-carbon-and-nitrogen-dynamics")
            self.assertFalse(entry["stale"])

    def test_skips_a_paper_with_no_stored_topics(self):
        with tempfile.TemporaryDirectory() as tmp:
            articles_dir = Path(tmp)
            _write_sidecar(articles_dir / "misc", "10-1-def", "Not Backfilled Yet", [])
            manifest = {"10.1/def": {"status": "fetched", "folder": "misc"}}

            entries = build_proposals_ledger(manifest, articles_dir)

            self.assertEqual(entries, [])

    def test_skips_an_entry_whose_sidecar_no_longer_exists_on_disk(self):
        with tempfile.TemporaryDirectory() as tmp:
            articles_dir = Path(tmp)
            manifest = {"10.1/ghost": {"status": "fetched", "folder": "misc"}}

            entries = build_proposals_ledger(manifest, articles_dir)

            self.assertEqual(entries, [])

    def test_skips_a_needs_manual_entry_with_no_pdf_yet(self):
        with tempfile.TemporaryDirectory() as tmp:
            articles_dir = Path(tmp)
            manifest = {"10.1/pending": {"status": "needs_manual", "folder": "misc"}}

            entries = build_proposals_ledger(manifest, articles_dir)

            self.assertEqual(entries, [])

    def test_marks_stale_when_manifest_fingerprint_differs_from_current_topics(self):
        with tempfile.TemporaryDirectory() as tmp:
            articles_dir = Path(tmp)
            topics_data = [{"id": "T1", "display_name": "Business", "score": 0.39}]
            _write_sidecar(articles_dir / "business", "10-1-abc", "Carbon Farming", topics_data)
            manifest = {"10.1/abc": {"status": "fetched", "folder": "business", "topic_decision_fingerprint": "stale-value"}}

            entries = build_proposals_ledger(manifest, articles_dir)

            self.assertTrue(entries[0]["stale"])


class TestWriteProposalsLedger(unittest.TestCase):
    def test_writes_ledger_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            articles_dir = Path(tmp)
            _write_sidecar(
                articles_dir / "misc", "10-1-abc", "A Paper",
                [{"id": "T1", "display_name": "Economics", "score": 0.8}],
            )
            manifest = {"10.1/abc": {"status": "fetched", "folder": "misc"}}

            path = write_proposals_ledger(manifest, articles_dir)

            self.assertEqual(path, proposals_ledger_path(articles_dir))
            entries = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(len(entries), 1)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/discovery/discover_journal_articles/test_topic_proposals.py -v`
Expected: FAIL (`ModuleNotFoundError: discovery.discover_journal_articles.topic_proposals`).

- [ ] **Step 3: Implement**

Create `discovery/discover_journal_articles/topic_proposals.py`:

```python
"""
topic_proposals.py
Read-only classification-proposal ledger per spec Section B: never moves
a file on its own. build_proposals_ledger()/write_proposals_ledger()
only ever produce review data, surfaced through an interactive Artifact
per the project's standing convention (core/indexer/offering_links.py).
resolve_folder_proposal() (added in Task 12) is the only thing that
actually moves a file, driven by an explicit accepted decision.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from discovery.discover_journal_articles.atomic_io import write_json_atomic
from discovery.discover_journal_articles.discovery import Topic
from discovery.discover_journal_articles.topic_routing import propose_folder, sanitize_topic_name

_ACTIVE_STATUSES = frozenset({"fetched", "downloaded"})


def proposals_ledger_path(articles_dir) -> Path:
    return Path(articles_dir) / ".discovery" / "topic_proposals.json"


def topics_fingerprint(topics: list[Topic]) -> str:
    """A stable fingerprint over (id, score) pairs -- changes only when
    OpenAlex actually re-ranks or adds/removes topics for this paper,
    not on sidecar key ordering."""
    pairs = sorted((t.id, round(t.score, 6)) for t in topics)
    return hashlib.sha256(json.dumps(pairs, sort_keys=True).encode("utf-8")).hexdigest()


def _sidecar_path_for(folder_dir: Path, key: str) -> Path:
    # Same filename formula as topic_routing.pdf_filename()/discover.py's
    # write_sidecar() call site, applied to the bare manifest key.
    stem = sanitize_topic_name(key)[:80] or "paper"
    return folder_dir / f"{stem}.meta.json"


def build_proposals_ledger(manifest: dict, articles_dir) -> list[dict]:
    articles_dir = Path(articles_dir)
    entries = []
    for key, manifest_entry in manifest.items():
        if manifest_entry.get("status") not in _ACTIVE_STATUSES:
            continue
        folder = manifest_entry.get("folder")
        if not folder:
            continue
        sidecar = _sidecar_path_for(articles_dir / folder, key)
        if not sidecar.exists():
            continue

        sidecar_data = json.loads(sidecar.read_text(encoding="utf-8"))
        topics_data = sidecar_data.get("topics") or []
        if not topics_data:
            continue

        topics = [Topic(id=t["id"], display_name=t["display_name"], score=t["score"]) for t in topics_data]
        proposal = propose_folder(topics, folder)
        fingerprint = topics_fingerprint(topics)
        recorded_fingerprint = manifest_entry.get("topic_decision_fingerprint")

        entries.append({
            "key": key,
            "title": sidecar_data.get("title"),
            "current_folder": proposal.current_folder,
            "candidates": [{"folder": name, "score": score} for name, score in proposal.candidates],
            "fingerprint": fingerprint,
            "stale": recorded_fingerprint is not None and recorded_fingerprint != fingerprint,
        })
    return entries


def write_proposals_ledger(manifest: dict, articles_dir) -> Path:
    entries = build_proposals_ledger(manifest, articles_dir)
    path = proposals_ledger_path(articles_dir)
    write_json_atomic(path, entries)
    return path
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/discovery/discover_journal_articles/test_topic_proposals.py -v`
Expected: PASS (all tests)

- [ ] **Step 5: Commit**

```bash
git add discovery/discover_journal_articles/topic_proposals.py tests/discovery/discover_journal_articles/test_topic_proposals.py
git commit -m "feat(discover_journal_articles): build a read-only classification proposal ledger"
```

---

### Task 12: `resolve_folder_proposal` apply step, tags, and staleness, plus CLI

**Files:**
- Modify: `discovery/discover_journal_articles/topic_proposals.py`
- Modify: `discovery/discover_journal_articles/manifest.py` (no code change needed beyond what Task 6 already did; this task only reads/writes existing manifest entries through functions already present)
- Test: `tests/discovery/discover_journal_articles/test_topic_proposals.py`

**Interfaces:**
- Consumes: `write_json_atomic`, `topics_fingerprint`, `_sidecar_path_for` (this file, Tasks 6 and 11); `sanitize_topic_name` (Task 10); `load_manifest`/`save_manifest`/`manifest_path` (`manifest.py`).
- Produces: `resolve_folder_proposal(manifest: dict, articles_dir, key: str, chosen_folder: str) -> None`; a `main()` CLI with `--build`, `--resolve KEY:FOLDER`, and `--reject KEY` flags on `python -m discovery.discover_journal_articles.topic_proposals`, mirroring `core/indexer/offering_links.py`'s existing `--resolve`/`--reject` pattern.

- [ ] **Step 1: Write the failing tests**

Append to `tests/discovery/discover_journal_articles/test_topic_proposals.py`:

```python
from discovery.discover_journal_articles.manifest import load_manifest, manifest_path, record_outcome, save_manifest
from discovery.discover_journal_articles.topic_proposals import resolve_folder_proposal


class TestResolveFolderProposal(unittest.TestCase):
    def _setup(self, tmp, topics_data):
        articles_dir = Path(tmp)
        _write_sidecar(articles_dir / "business", "10-1-abc", "Carbon Farming", topics_data)
        (articles_dir / "business" / "10-1-abc.pdf").write_bytes(b"%PDF-1.4")
        manifest = {"10.1/abc": {"status": "fetched", "folder": "business"}}
        return articles_dir, manifest

    def test_moves_pdf_and_sidecar_when_chosen_folder_differs(self):
        with tempfile.TemporaryDirectory() as tmp:
            topics_data = [
                {"id": "T1", "display_name": "Business", "score": 0.39},
                {"id": "T2", "display_name": "Soil Carbon and Nitrogen Dynamics", "score": 0.9},
            ]
            articles_dir, manifest = self._setup(tmp, topics_data)

            resolve_folder_proposal(manifest, articles_dir, "10.1/abc", "soil-carbon-and-nitrogen-dynamics")

            new_dir = articles_dir / "soil-carbon-and-nitrogen-dynamics"
            self.assertTrue((new_dir / "10-1-abc.pdf").exists())
            self.assertTrue((new_dir / "10-1-abc.meta.json").exists())
            self.assertFalse((articles_dir / "business" / "10-1-abc.pdf").exists())
            self.assertEqual(manifest["10.1/abc"]["folder"], "soil-carbon-and-nitrogen-dynamics")

    def test_keeping_current_folder_still_writes_tags_and_fingerprint(self):
        with tempfile.TemporaryDirectory() as tmp:
            topics_data = [
                {"id": "T1", "display_name": "Business", "score": 0.39},
                {"id": "T2", "display_name": "Soil Carbon and Nitrogen Dynamics", "score": 0.9},
            ]
            articles_dir, manifest = self._setup(tmp, topics_data)

            resolve_folder_proposal(manifest, articles_dir, "10.1/abc", "business")

            sidecar = json.loads((articles_dir / "business" / "10-1-abc.meta.json").read_text(encoding="utf-8"))
            self.assertIn("soil-carbon-and-nitrogen-dynamics", sidecar["tags"])
            self.assertIn("topic_decision_fingerprint", manifest["10.1/abc"])

    def test_tags_exclude_topics_below_the_relevance_floor(self):
        with tempfile.TemporaryDirectory() as tmp:
            topics_data = [
                {"id": "T1", "display_name": "Business", "score": 0.39},
                {"id": "T2", "display_name": "Negligible Side Topic", "score": 0.05},
            ]
            articles_dir, manifest = self._setup(tmp, topics_data)

            resolve_folder_proposal(manifest, articles_dir, "10.1/abc", "business")

            sidecar = json.loads((articles_dir / "business" / "10-1-abc.meta.json").read_text(encoding="utf-8"))
            self.assertNotIn("negligible-side-topic", sidecar["tags"])

    def test_raises_key_error_for_an_unknown_manifest_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(KeyError):
                resolve_folder_proposal({}, tmp, "10.1/missing", "misc")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/discovery/discover_journal_articles/test_topic_proposals.py -v -k ResolveFolderProposal`
Expected: FAIL (`ImportError: cannot import name 'resolve_folder_proposal'`).

- [ ] **Step 3: Implement**

Append to `discovery/discover_journal_articles/topic_proposals.py`:

```python
_TAG_RELEVANCE_FLOOR = 0.2


def resolve_folder_proposal(manifest: dict, articles_dir, key: str, chosen_folder: str) -> None:
    """Applies exactly one accepted decision from the review ledger:
    moves the paper's PDF+sidecar into chosen_folder only if it differs
    from the current folder, writes every above-floor topic into the
    sidecar as a tag regardless of which folder was chosen, and updates
    manifest[key]. Never called automatically -- only from an explicit
    --resolve KEY:FOLDER CLI call driven by a human decision recorded in
    the review Artifact."""
    entry = manifest.get(key)
    if entry is None:
        raise KeyError(f"{key!r} not found in manifest")

    articles_dir = Path(articles_dir)
    current_folder = entry.get("folder") or "misc"
    stem = sanitize_topic_name(key)[:80] or "paper"
    old_dir = articles_dir / current_folder
    pdf_path = old_dir / f"{stem}.pdf"
    sidecar_path = old_dir / f"{stem}.meta.json"

    sidecar_data = json.loads(sidecar_path.read_text(encoding="utf-8"))
    topics_data = sidecar_data.get("topics") or []
    sidecar_data["tags"] = sorted({
        sanitize_topic_name(t["display_name"]) for t in topics_data if t.get("score", 0) > _TAG_RELEVANCE_FLOOR
    })

    if chosen_folder != current_folder:
        new_dir = articles_dir / chosen_folder
        new_dir.mkdir(parents=True, exist_ok=True)
        pdf_path.replace(new_dir / pdf_path.name)
        sidecar_path = sidecar_path.replace(new_dir / sidecar_path.name)
        entry["folder"] = chosen_folder

    write_json_atomic(sidecar_path, sidecar_data)

    topics = [Topic(id=t["id"], display_name=t["display_name"], score=t["score"]) for t in topics_data]
    entry["topic_decision_fingerprint"] = topics_fingerprint(topics)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Build or apply the classification proposal review ledger.")
    default_articles_dir = Path(__file__).resolve().parent.parent.parent.parent / "research" / "journal-articles"
    parser.add_argument("--articles-dir", default=str(default_articles_dir))
    parser.add_argument("--build", action="store_true", help="(Re)write the review ledger from the current manifest/sidecars.")
    parser.add_argument("--resolve", metavar="KEY:FOLDER", help="Apply an accepted decision: move KEY into FOLDER (or keep it, tagging only, if FOLDER matches the current folder).")
    parser.add_argument("--reject", metavar="KEY", help="Record that KEY's current folder was explicitly kept as-is, without changing anything else.")
    args = parser.parse_args()

    manifest_file = manifest_path(args.articles_dir)
    manifest = load_manifest(manifest_file)

    if args.build:
        path = write_proposals_ledger(manifest, args.articles_dir)
        print(f"Wrote {path}")
        return

    if args.resolve:
        key, _, folder = args.resolve.partition(":")
        resolve_folder_proposal(manifest, args.articles_dir, key, folder)
        save_manifest(manifest_file, manifest)
        print(f"Applied: {key} -> {folder}")
        return

    if args.reject:
        resolve_folder_proposal(manifest, args.articles_dir, args.reject, manifest[args.reject].get("folder") or "misc")
        save_manifest(manifest_file, manifest)
        print(f"Kept {args.reject} in its current folder; recorded as reviewed.")
        return

    parser.error("one of --build, --resolve, or --reject is required")


if __name__ == "__main__":
    main()
```

Add the needed imports at the top of `topic_proposals.py`:

```python
from discovery.discover_journal_articles.manifest import load_manifest, manifest_path, save_manifest
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/discovery/discover_journal_articles/test_topic_proposals.py -v`
Expected: PASS (all tests)

- [ ] **Step 5: Commit**

```bash
git add discovery/discover_journal_articles/topic_proposals.py tests/discovery/discover_journal_articles/test_topic_proposals.py
git commit -m "feat(discover_journal_articles): apply classification decisions with tags and staleness tracking"
```

---

### Task 13: `tools/backfill_topics.py` for existing manifest entries

**Files:**
- Create: `tools/backfill_topics.py`
- Test: `tests/tools/test_backfill_topics.py`

**Interfaces:**
- Consumes: `write_json_atomic` (Task 6), `resolve_work_by_doi` (`discovery.py`), `sanitize_topic_name` (Task 10), `load_manifest`/`manifest_path` (`manifest.py`).
- Produces: `backfill_topics(manifest: dict, articles_dir, mailto: str) -> dict` with `{"updated", "skipped_no_folder", "skipped_no_doi", "skipped_not_found"}`; a CLI `main()` runnable as `python -m tools.backfill_topics`.

- [ ] **Step 1: Write the failing tests**

Create `tests/tools/test_backfill_topics.py`:

```python
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from discovery.discover_journal_articles.discovery import Topic, Work
from tools.backfill_topics import backfill_topics


def _sidecar(folder_dir: Path, stem: str, extra: dict | None = None) -> None:
    folder_dir.mkdir(parents=True, exist_ok=True)
    data = {"title": "A Paper", "doi": None, "topics": []}
    data.update(extra or {})
    (folder_dir / f"{stem}.meta.json").write_text(json.dumps(data), encoding="utf-8")


def _work_with_topics():
    return Work(
        openalex_id="W1", doi="10.1/abc", title="A Paper", authors=[], year=2024, abstract=None,
        topics=[Topic(id="https://openalex.org/T1", display_name="Climate Adaptation", score=0.9)],
    )


class TestBackfillTopics(unittest.TestCase):
    @patch("tools.backfill_topics.resolve_work_by_doi")
    def test_updates_sidecar_with_fetched_topics(self, mock_resolve):
        with tempfile.TemporaryDirectory() as tmp:
            articles_dir = Path(tmp)
            _sidecar(articles_dir / "misc", "10-1-abc")
            manifest = {"10.1/abc": {"status": "fetched", "folder": "misc"}}
            mock_resolve.return_value = _work_with_topics()

            counts = backfill_topics(manifest, articles_dir, "me@example.com")

            self.assertEqual(counts["updated"], 1)
            sidecar = json.loads((articles_dir / "misc" / "10-1-abc.meta.json").read_text(encoding="utf-8"))
            self.assertEqual(sidecar["topics"], [{"id": "https://openalex.org/T1", "display_name": "Climate Adaptation", "score": 0.9}])

    def test_skips_entry_without_a_folder(self):
        manifest = {"10.1/abc": {"status": "needs_manual"}}
        counts = backfill_topics(manifest, tempfile.mkdtemp(), "me@example.com")
        self.assertEqual(counts["skipped_no_folder"], 1)

    def test_skips_entry_whose_sidecar_is_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = {"10.1/abc": {"status": "fetched", "folder": "misc"}}
            counts = backfill_topics(manifest, tmp, "me@example.com")
            self.assertEqual(counts["skipped_no_folder"], 1)

    def test_skips_an_openalex_id_only_key_without_crashing(self):
        with tempfile.TemporaryDirectory() as tmp:
            articles_dir = Path(tmp)
            _sidecar(articles_dir / "misc", "https-openalex-org-w1"[:80])
            manifest = {"https://openalex.org/W1": {"status": "fetched", "folder": "misc"}}

            counts = backfill_topics(manifest, articles_dir, "me@example.com")

            self.assertEqual(counts["skipped_no_doi"], 1)

    @patch("tools.backfill_topics.resolve_work_by_doi", return_value=None)
    def test_skips_a_doi_not_found_in_openalex(self, mock_resolve):
        with tempfile.TemporaryDirectory() as tmp:
            articles_dir = Path(tmp)
            _sidecar(articles_dir / "misc", "10-1-abc")
            manifest = {"10.1/abc": {"status": "fetched", "folder": "misc"}}

            counts = backfill_topics(manifest, articles_dir, "me@example.com")

            self.assertEqual(counts["skipped_not_found"], 1)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/tools/test_backfill_topics.py -v`
Expected: FAIL (`ModuleNotFoundError: tools.backfill_topics`).

- [ ] **Step 3: Implement**

Create `tools/backfill_topics.py`:

```python
"""
backfill_topics.py
One-time pass per spec Section B.3: existing sidecars only ever stored
flat Concept display-names (Topics weren't fetched historically). Looks
up each manifest entry by DOI against the live OpenAlex API and writes
the resulting `topics` list into that paper's existing sidecar, touching
nothing else -- not its folder, not its PDF.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from core.env.gemini_utils import load_dotenv_override
from discovery.discover_journal_articles.atomic_io import write_json_atomic
from discovery.discover_journal_articles.discovery import resolve_work_by_doi
from discovery.discover_journal_articles.manifest import load_manifest, manifest_path
from discovery.discover_journal_articles.topic_routing import sanitize_topic_name


def _sidecar_path_for(articles_dir: Path, folder: str, key: str) -> Path:
    stem = sanitize_topic_name(key)[:80] or "paper"
    return articles_dir / folder / f"{stem}.meta.json"


def backfill_topics(manifest: dict, articles_dir, mailto: str) -> dict:
    articles_dir = Path(articles_dir)
    counts = {"updated": 0, "skipped_no_folder": 0, "skipped_no_doi": 0, "skipped_not_found": 0}

    for key, entry in manifest.items():
        folder = entry.get("folder")
        if not folder:
            counts["skipped_no_folder"] += 1
            continue
        sidecar = _sidecar_path_for(articles_dir, folder, key)
        if not sidecar.exists():
            counts["skipped_no_folder"] += 1
            continue
        if key.startswith("http"):
            counts["skipped_no_doi"] += 1
            continue

        work = resolve_work_by_doi(key, mailto)
        if work is None:
            counts["skipped_not_found"] += 1
            continue

        sidecar_data = json.loads(sidecar.read_text(encoding="utf-8"))
        sidecar_data["topics"] = [
            {"id": t.id, "display_name": t.display_name, "score": t.score} for t in work.topics
        ]
        write_json_atomic(sidecar, sidecar_data)
        counts["updated"] += 1

    return counts


def main():
    parser = argparse.ArgumentParser(description="Backfill OpenAlex Topics data into existing journal-article sidecars.")
    default_articles_dir = Path(__file__).resolve().parent.parent / "research" / "journal-articles"
    parser.add_argument("--articles-dir", default=str(default_articles_dir))
    args = parser.parse_args()

    load_dotenv_override()
    mailto = os.environ.get("OPENALEX_CONTACT_EMAIL")
    if not mailto:
        print("ERROR: OPENALEX_CONTACT_EMAIL must be set in .env.")
        raise SystemExit(1)

    manifest = load_manifest(manifest_path(args.articles_dir))
    counts = backfill_topics(manifest, args.articles_dir, mailto)
    print(f"Updated: {counts['updated']}")
    print(f"Skipped (no folder/sidecar): {counts['skipped_no_folder']}")
    print(f"Skipped (no DOI): {counts['skipped_no_doi']}")
    print(f"Skipped (not found in OpenAlex): {counts['skipped_not_found']}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/tools/test_backfill_topics.py -v`
Expected: PASS (all tests)

- [ ] **Step 5: Commit**

```bash
git add tools/backfill_topics.py tests/tools/test_backfill_topics.py
git commit -m "feat(discover_journal_articles): add tools/backfill_topics.py for existing manifest entries"
```

---

## After all tasks: full-suite check

- [ ] Run the complete discovery test package plus the new tools test, from `academic-rag-model/`:

```bash
python -m pytest tests/discovery/discover_journal_articles/ tests/tools/test_backfill_topics.py -v
```

Expected: PASS (every file in the package, including `test_snowball.py`, `test_worklist.py`, `test_zotero_sync.py`, `test_text_match.py`, none of which this plan touches, to confirm no cross-file regression).

- [ ] Run the landing check per the worktree procedure before asking to merge:

```bash
<main-checkout>/ai-sandbox/academic-rag-model/.venv/Scripts/python.exe -m tools.land_branch check --full
```
