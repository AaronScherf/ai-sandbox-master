# Journal Discovery Snowball Sampling Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add citation-based snowball sampling as a third `journal_discovery` route: `python -m journal_discovery.snowball propose` seeds from the corpus's own papers, follows OpenAlex's forward-citation graph, scores candidates through the existing relevance gate, and writes a checkbox worklist for human review; `confirm` fetches only what's checked.

**Architecture:** A new `journal_discovery/snowball.py` module reusing `discovery.py` (two new functions, two promoted utilities), `manifest.py` (one promoted function), `worklist.py` (generalized into a shared checkbox-writer), `relevance.py`, and `access.py` completely unchanged. A new manifest status, `"proposed"`, sits between "never seen" and `"fetched"`/`"needs_manual"`.

**Tech Stack:** Python, `requests` (via existing `http_utils`), `unittest`/`unittest.mock`, matching every convention already established in `journal_discovery/`.

**Spec:** `academic-rag-model/docs/superpowers/specs/2026-09-02-journal-discovery-snowball-design.md`

## Global Constraints

- Never auto-fetch a snowball candidate. `propose` only ever writes to the manifest as `status="proposed"` and to `snowball_candidates.md`; only `confirm`, acting on checked boxes, calls `resolve_full_text()`.
- `skip_already_seen()` (the promoted filter) must treat `"proposed"` as seen, same as any other status — a proposed-but-unconfirmed paper is invisible to every discovery route, including a later `propose` run, until `confirm` acts on it or changes its status.
- `confirm()` never calls `skip_already_seen()` — it looks up `status == "proposed"` entries directly, by design.
- No changes to `access.py`, `relevance.py`'s public behavior, `topic_routing.py`, or `metadata_sidecar.py` — snowball reuses all of them exactly as they are today.
- Tests mirror the existing flat `tests/` convention: `unittest.TestCase` + `unittest.mock`, no real network calls, no real model downloads.

---

## File Structure

**Modify:**
- `academic-rag-model/journal_discovery/discovery.py` — add `resolve_work_by_doi()`, `iter_citing_works()`, and promote `doi_url()`/`pdf_filename()` (moved here from `discover.py`'s private `_doi_url`/`_pdf_filename`, since both are pure `Work -> str` utilities that belong alongside `Work` itself).
- `academic-rag-model/journal_discovery/manifest.py` — promote `skip_already_seen()` (moved here from `discover.py`'s private `_skip_already_seen`).
- `academic-rag-model/journal_discovery/discover.py` — remove the three now-promoted private functions; import and use the shared versions instead. No behavior change.
- `academic-rag-model/journal_discovery/worklist.py` — generalize into a shared `_write_checkbox_worklist()`; `write_needs_manual_worklist()` becomes a thin wrapper around it; add `write_snowball_candidates_worklist()`.
- `academic-rag-model/journal_discovery_instructions.md` — add a "Route 3: Citation snowball sampling" section.
- `academic-rag-model/tests/test_discovery.py`, `test_manifest.py`, `test_discover.py`, `test_worklist.py` — updated/extended per the tasks below.

**Create:**
- `academic-rag-model/journal_discovery/snowball.py`
- `academic-rag-model/tests/test_snowball.py`

---

### Task 1: Promote `doi_url()`/`pdf_filename()` to `discovery.py`; add `resolve_work_by_doi()` and `iter_citing_works()`

**Files:**
- Modify: `academic-rag-model/journal_discovery/discovery.py`
- Modify: `academic-rag-model/journal_discovery/discover.py`
- Modify: `academic-rag-model/tests/test_discovery.py`
- Test: `academic-rag-model/tests/test_discover.py` (existing tests must still pass unchanged)

**Interfaces:**
- Consumes: `journal_discovery.http_utils.fetch_with_retries`, `FetchError`
- Produces: `doi_url(work: Work) -> str`; `pdf_filename(work: Work) -> str`; `resolve_work_by_doi(doi: str, mailto: str) -> Work | None`; `iter_citing_works(openalex_id: str, mailto: str, batch_size: int) -> Iterator[Work]`

- [ ] **Step 1: Write the failing tests**

```python
# Add to academic-rag-model/tests/test_discovery.py, alongside existing imports:
from journal_discovery.discovery import (
    Work,
    doi_url,
    iter_author_works,
    iter_citing_works,
    iter_topic_works,
    pdf_filename,
    reconstruct_abstract,
    resolve_author_id,
    resolve_work_by_doi,
    resolve_works,
)
```

```python
# New test classes, appended to test_discovery.py:

class TestDoiUrl(unittest.TestCase):
    def test_builds_doi_dot_org_url(self):
        work = Work(openalex_id="W1", doi="10.1/abc", title="T", authors=[], year=2024, abstract=None)
        self.assertEqual(doi_url(work), "https://doi.org/10.1/abc")

    def test_falls_back_to_openalex_id_without_doi(self):
        work = Work(openalex_id="https://openalex.org/W1", doi=None, title="T", authors=[], year=2024, abstract=None)
        self.assertEqual(doi_url(work), "https://openalex.org/W1")


class TestPdfFilename(unittest.TestCase):
    def test_uses_sanitized_doi(self):
        work = Work(openalex_id="W1", doi="10.1/abc", title="T", authors=[], year=2024, abstract=None)
        self.assertEqual(pdf_filename(work), "10-1-abc.pdf")

    def test_falls_back_to_openalex_id_without_doi(self):
        work = Work(openalex_id="W1", doi=None, title="T", authors=[], year=2024, abstract=None)
        self.assertEqual(pdf_filename(work), "w1.pdf")


class TestResolveWorkByDoi(unittest.TestCase):
    @patch("journal_discovery.discovery.fetch_with_retries")
    def test_returns_parsed_work(self, mock_fetch):
        mock_fetch.return_value = _response(_openalex_work(doi="https://doi.org/10.1/abc"))
        work = resolve_work_by_doi("10.1/abc", "me@example.com")
        self.assertIsInstance(work, Work)
        self.assertEqual(work.doi, "10.1/abc")

    @patch("journal_discovery.discovery.fetch_with_retries")
    def test_none_on_non_200(self, mock_fetch):
        mock_fetch.return_value = _response({}, status_code=404)
        self.assertIsNone(resolve_work_by_doi("10.1/unknown", "me@example.com"))

    @patch("journal_discovery.discovery.fetch_with_retries")
    def test_none_on_fetch_error(self, mock_fetch):
        from journal_discovery.http_utils import FetchError
        mock_fetch.side_effect = FetchError("not found")
        self.assertIsNone(resolve_work_by_doi("10.1/unknown", "me@example.com"))


class TestIterCitingWorks(unittest.TestCase):
    @patch("journal_discovery.discovery.fetch_with_retries")
    def test_pages_until_empty(self, mock_fetch):
        mock_fetch.side_effect = [
            _response({"results": [_openalex_work()]}),
            _response({"results": []}),
        ]
        works = list(iter_citing_works("https://openalex.org/W1", "me@example.com", batch_size=25))
        self.assertEqual(len(works), 1)

    @patch("journal_discovery.discovery.fetch_with_retries")
    def test_excludes_dataset_type_works(self, mock_fetch):
        mock_fetch.side_effect = [
            _response({"results": [_openalex_work(work_type="dataset")]}),
            _response({"results": []}),
        ]
        works = list(iter_citing_works("https://openalex.org/W1", "me@example.com", batch_size=25))
        self.assertEqual(works, [])
```

Note: `_response()` and `_openalex_work()` already exist as test helpers in `test_discovery.py` (per the `2026-08-31` plan) — reused here as-is, no changes needed to them. `_openalex_work()`'s `doi` parameter already defaults to a full `https://doi.org/...` URL, matching what `resolve_work_by_doi`'s single-work response shape needs.

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd academic-rag-model && python -m pytest tests/test_discovery.py -v`
Expected: FAIL with `ImportError` (`doi_url`, `pdf_filename`, `resolve_work_by_doi`, `iter_citing_works` don't exist yet)

- [ ] **Step 3: Write the implementation**

```python
# In academic-rag-model/journal_discovery/discovery.py:
# Change the import line near the top from:
#     from journal_discovery.http_utils import fetch_with_retries
# to:
from journal_discovery.http_utils import FetchError, fetch_with_retries
```

```python
# Add to journal_discovery/discovery.py, after the Work dataclass definition:

def doi_url(work: Work) -> str:
    if work.doi:
        return f"https://doi.org/{work.doi}"
    return work.openalex_id


def pdf_filename(work: Work) -> str:
    key = work.doi or work.openalex_id or work.title
    return f"{sanitize_topic_name(key)[:80] or 'paper'}.pdf"
```

Wait -- `pdf_filename()` needs `sanitize_topic_name()`, which lives in
`topic_routing.py`. Add the import at the top of `discovery.py`:

```python
from journal_discovery.topic_routing import sanitize_topic_name
```

Check this doesn't create a circular import: `topic_routing.py` imports
`Work` from `discovery.py` for type hints only (per the `2026-08-31`
design). Moving `pdf_filename()` into `discovery.py` and having
`discovery.py` import `sanitize_topic_name` from `topic_routing.py`
*would* create a cycle (`discovery` -> `topic_routing` -> `discovery`).
**Resolve this by keeping `pdf_filename()` in `topic_routing.py`
instead of `discovery.py`** -- it already imports `Work` for type hints,
and `sanitize_topic_name` lives there natively, so no new import is
needed at all. Only `doi_url()` moves into `discovery.py` (no
`topic_routing` dependency). Add to `journal_discovery/topic_routing.py`:

```python
def pdf_filename(work: Work) -> str:
    key = work.doi or work.openalex_id or work.title
    return f"{sanitize_topic_name(key)[:80] or 'paper'}.pdf"
```

Move the two `TestPdfFilename` cases from `test_discovery.py` (Step 1
above) into `tests/test_topic_routing.py` instead, importing
`pdf_filename` from `journal_discovery.topic_routing`, and remove
`pdf_filename` from the `test_discovery.py` import list in Step 1.

Now add the two new discovery functions to `journal_discovery/discovery.py`:

```python
def resolve_work_by_doi(doi: str, mailto: str) -> Work | None:
    try:
        response = fetch_with_retries(
            "GET", f"{_OPENALEX_BASE}/works/https://doi.org/{doi}", params={"mailto": mailto},
        )
    except FetchError:
        return None
    if response.status_code != 200:
        return None
    return _work_from_openalex(response.json())


def iter_citing_works(openalex_id: str, mailto: str, batch_size: int):
    page = 1
    while True:
        params = {
            "filter": f"cites:{openalex_id}",
            "per-page": batch_size,
            "page": page,
            "mailto": mailto,
        }
        response = fetch_with_retries("GET", f"{_OPENALEX_BASE}/works", params=params)
        results = response.json().get("results", [])
        if not results:
            return
        for record in results:
            if record.get("type") in _EXCLUDED_WORK_TYPES:
                continue
            yield _work_from_openalex(record)
        page += 1
```

Now update `journal_discovery/discover.py`: remove the local
`_pdf_filename()` and `_doi_url()` function definitions entirely, and
change its imports/call sites:

```python
# Remove these two functions from discover.py:
#   def _pdf_filename(work) -> str: ...
#   def _doi_url(work) -> str: ...

# Change the import line:
#     from journal_discovery.topic_routing import route_to_folder, sanitize_topic_name
# to:
from journal_discovery.topic_routing import pdf_filename, route_to_folder

# Add a new import:
from journal_discovery.discovery import doi_url, resolve_works
```

Replace every call site: `_pdf_filename(work)` -> `pdf_filename(work)`,
`_doi_url(work)` -> `doi_url(work)` (two call sites each, in `run()`'s
fetched and needs_manual branches).

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd academic-rag-model && python -m pytest tests/test_discovery.py tests/test_topic_routing.py tests/test_discover.py -v`
Expected: PASS, all tests including the pre-existing `test_discover.py` suite (unchanged behavior, just relocated helpers)

- [ ] **Step 5: Commit**

```bash
git add academic-rag-model/journal_discovery/discovery.py academic-rag-model/journal_discovery/topic_routing.py academic-rag-model/journal_discovery/discover.py academic-rag-model/tests/test_discovery.py academic-rag-model/tests/test_topic_routing.py
git commit -m "refactor(journal_discovery): promote doi_url/pdf_filename, add citation lookup"
```

---

### Task 2: Promote `skip_already_seen()` to `manifest.py`

**Files:**
- Modify: `academic-rag-model/journal_discovery/manifest.py`
- Modify: `academic-rag-model/journal_discovery/discover.py`
- Modify: `academic-rag-model/tests/test_manifest.py`

**Interfaces:**
- Consumes: `journal_discovery.discovery.Work`
- Produces: `skip_already_seen(works: Iterable[Work], manifest: dict, counts: dict) -> Iterator[Work]`

- [ ] **Step 1: Write the failing test**

```python
# Add to academic-rag-model/tests/test_manifest.py imports:
from journal_discovery.manifest import (
    is_seen,
    load_manifest,
    manifest_key,
    manifest_path,
    record_outcome,
    save_manifest,
    skip_already_seen,
)
```

```python
# New test class, appended to test_manifest.py:

class TestSkipAlreadySeen(unittest.TestCase):
    def test_filters_seen_and_counts_them(self):
        manifest = {"10.1/abc": {"status": "fetched"}}
        works = [_work(doi="10.1/abc"), _work(doi="10.1/new")]
        counts = {"already_seen": 0}

        result = list(skip_already_seen(works, manifest, counts))

        self.assertEqual([w.doi for w in result], ["10.1/new"])
        self.assertEqual(counts["already_seen"], 1)

    def test_proposed_status_also_treated_as_seen(self):
        # Deliberate per spec 2026-09-02: a snowball-proposed-but-not-
        # yet-confirmed paper must be invisible to every discovery route
        # until confirmed, not just to a future propose run.
        manifest = {"10.1/abc": {"status": "proposed"}}
        works = [_work(doi="10.1/abc")]
        counts = {"already_seen": 0}

        result = list(skip_already_seen(works, manifest, counts))

        self.assertEqual(result, [])
        self.assertEqual(counts["already_seen"], 1)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd academic-rag-model && python -m pytest tests/test_manifest.py -v`
Expected: FAIL with `ImportError: cannot import name 'skip_already_seen'`

- [ ] **Step 3: Write the implementation**

```python
# Add to journal_discovery/manifest.py, after is_seen():

def skip_already_seen(works, manifest: dict, counts: dict):
    """Filters out already-seen candidates (fetched/needs_manual/
    downloaded/proposed) BEFORE they reach relevance scoring. Shared by
    discover.py's author/topic routes and snowball.py's citation route
    -- confirmed real 2026-09-02 that filtering after scoring wastes
    --max-results slots re-selecting already-seen candidates on a
    rerun."""
    for work in works:
        if is_seen(manifest, manifest_key(work)):
            counts["already_seen"] += 1
            continue
        yield work
```

Now update `journal_discovery/discover.py`: remove the local
`_skip_already_seen()` function definition entirely, add
`skip_already_seen` to the existing `from journal_discovery.manifest
import (...)` block, and replace the one call site
`_skip_already_seen(works, manifest, counts)` with
`skip_already_seen(works, manifest, counts)`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd academic-rag-model && python -m pytest tests/test_manifest.py tests/test_discover.py -v`
Expected: PASS, all tests including the pre-existing `test_discover.py` suite unchanged

- [ ] **Step 5: Commit**

```bash
git add academic-rag-model/journal_discovery/manifest.py academic-rag-model/journal_discovery/discover.py academic-rag-model/tests/test_manifest.py
git commit -m "refactor(journal_discovery): promote skip_already_seen to manifest.py"
```

---

### Task 3: Generalize `worklist.py` into a shared checkbox-writer; add the snowball worklist

**Files:**
- Modify: `academic-rag-model/journal_discovery/worklist.py`
- Modify: `academic-rag-model/tests/test_worklist.py`

**Interfaces:**
- Produces: `write_snowball_candidates_worklist(manifest: dict, articles_dir) -> Path` (new); `write_needs_manual_worklist(manifest: dict, articles_dir) -> Path` (unchanged signature and behavior, reimplemented on top of the new shared helper)

- [ ] **Step 1: Write the failing tests**

```python
# Add to academic-rag-model/tests/test_worklist.py imports:
from journal_discovery.worklist import write_needs_manual_worklist, write_snowball_candidates_worklist
```

```python
# New test class, appended to test_worklist.py:

class TestWriteSnowballCandidatesWorklist(unittest.TestCase):
    def test_writes_titled_links_with_target_folder(self):
        manifest = {
            "10.1/abc": {
                "status": "proposed", "title": "A Candidate", "folder": "business",
                "doi_url": "https://doi.org/10.1/abc",
            },
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = write_snowball_candidates_worklist(manifest, tmp)

            self.assertEqual(path, Path(tmp) / "snowball_candidates.md")
            content = path.read_text(encoding="utf-8")
            self.assertIn("- [ ] [A Candidate](https://doi.org/10.1/abc)", content)
            self.assertIn("research/journal-articles/business/", content)

    def test_shows_relevance_score_and_cited_seed_when_present(self):
        manifest = {
            "10.1/abc": {
                "status": "proposed", "title": "A Candidate", "folder": "business",
                "doi_url": "https://doi.org/10.1/abc", "relevance_score": 0.62,
                "cites_seed": "10.1/seed-paper",
            },
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = write_snowball_candidates_worklist(manifest, tmp)
            content = path.read_text(encoding="utf-8")
            self.assertIn("0.62", content)
            self.assertIn("10.1/seed-paper", content)

    def test_excludes_needs_manual_entries(self):
        manifest = {
            "10.1/manual": {"status": "needs_manual", "title": "Not This One"},
            "10.1/proposed": {"status": "proposed", "title": "This One"},
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = write_snowball_candidates_worklist(manifest, tmp)
            content = path.read_text(encoding="utf-8")
            self.assertNotIn("Not This One", content)
            self.assertIn("This One", content)

    def test_preserves_checked_state_across_regeneration(self):
        manifest = {
            "10.1/abc": {"status": "proposed", "title": "A Candidate", "doi_url": "https://doi.org/10.1/abc"},
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = write_snowball_candidates_worklist(manifest, tmp)
            path.write_text(
                path.read_text(encoding="utf-8").replace("- [ ] [A Candidate]", "- [x] [A Candidate]"),
                encoding="utf-8",
            )

            write_snowball_candidates_worklist(manifest, tmp)

            self.assertIn("- [x] [A Candidate](https://doi.org/10.1/abc)", path.read_text(encoding="utf-8"))

    def test_needs_manual_and_snowball_worklists_track_checks_independently(self):
        manifest = {
            "10.1/manual": {"status": "needs_manual", "title": "Manual One", "doi_url": "https://doi.org/10.1/manual"},
            "10.1/proposed": {"status": "proposed", "title": "Proposed One", "doi_url": "https://doi.org/10.1/proposed"},
        }
        with tempfile.TemporaryDirectory() as tmp:
            manual_path = write_needs_manual_worklist(manifest, tmp)
            snowball_path = write_snowball_candidates_worklist(manifest, tmp)

            manual_path.write_text(
                manual_path.read_text(encoding="utf-8").replace("- [ ] [Manual One]", "- [x] [Manual One]"),
                encoding="utf-8",
            )

            write_needs_manual_worklist(manifest, tmp)
            write_snowball_candidates_worklist(manifest, tmp)

            self.assertIn("- [x] [Manual One]", manual_path.read_text(encoding="utf-8"))
            self.assertIn("- [ ] [Proposed One]", snowball_path.read_text(encoding="utf-8"))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd academic-rag-model && python -m pytest tests/test_worklist.py -v`
Expected: FAIL with `ImportError: cannot import name 'write_snowball_candidates_worklist'`

- [ ] **Step 3: Write the implementation**

Replace the body of `journal_discovery/worklist.py` from
`write_needs_manual_worklist` onward (keep `_CHECKBOX_LINE_RE`,
`_link_for`, `_read_checked_links` exactly as they are) with:

```python
def _write_checkbox_worklist(
    manifest: dict, articles_dir, filename: str, heading_lines: list[str], status_filter: str,
) -> Path:
    entries = [
        (key, entry) for key, entry in manifest.items()
        if entry.get("status") == status_filter and entry.get("work_type") != "dataset"
    ]
    entries.sort(key=lambda kv: kv[1].get("title") or kv[0])

    path = Path(articles_dir) / filename
    previously_checked = _read_checked_links(path)

    lines = list(heading_lines) + [""]
    for key, entry in entries:
        title = entry.get("title") or key
        link = _link_for(key, entry)
        folder = entry.get("folder")
        checkbox = "x" if link in previously_checked else " "
        lines.append(f"- [{checkbox}] [{title}]({link})")
        if folder:
            lines.append(f"  - Save to: `research/journal-articles/{folder}/`")
        else:
            lines.append("  - Save to: `research/journal-articles/misc/` (no folder recorded yet)")
        if "relevance_score" in entry:
            lines.append(f"  - Relevance score: {entry['relevance_score']:.2f}")
        if "cites_seed" in entry:
            lines.append(f"  - Cites: {entry['cites_seed']}")
    lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def write_needs_manual_worklist(manifest: dict, articles_dir) -> Path:
    heading = [
        "# Papers needing manual download",
        "",
        "Auto-fetch couldn't reach these (gated, bot-blocked, or otherwise",
        "unavailable to a scripted request). Open each link in your own",
        "authenticated browser, download the PDF, and save it into the",
        "folder listed underneath -- `convert_journal_articles.py` picks up",
        "anything sitting there automatically. Check a box to track your own",
        "progress; once conversion confirms a download landed, the reconciler",
        "removes that entry from this list entirely.",
    ]
    return _write_checkbox_worklist(manifest, articles_dir, "needs_manual_downloads.md", heading, "needs_manual")


def write_snowball_candidates_worklist(manifest: dict, articles_dir) -> Path:
    heading = [
        "# Snowball-sampled candidates awaiting review",
        "",
        "Found by following citations from papers already in your corpus,",
        "via OpenAlex's own citation graph, then narrowed by your",
        "--relevance-prompt. Nothing here has been downloaded yet. Check the",
        "papers you actually want, then run:",
        "",
        "    python -m journal_discovery.snowball confirm",
        "",
        "to fetch just those.",
    ]
    return _write_checkbox_worklist(manifest, articles_dir, "snowball_candidates.md", heading, "proposed")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd academic-rag-model && python -m pytest tests/test_worklist.py -v`
Expected: PASS, all tests including the pre-existing `write_needs_manual_worklist` suite unchanged

- [ ] **Step 5: Commit**

```bash
git add academic-rag-model/journal_discovery/worklist.py academic-rag-model/tests/test_worklist.py
git commit -m "refactor(journal_discovery): generalize checkbox worklist writer, add snowball candidates worklist"
```

---

### Task 4: `snowball.py` — seed resolution and candidate streaming

**Files:**
- Create: `academic-rag-model/journal_discovery/snowball.py`
- Test: `academic-rag-model/tests/test_snowball.py`

**Interfaces:**
- Consumes: `journal_discovery.discovery.resolve_work_by_doi`, `iter_citing_works`; `journal_discovery.manifest.skip_already_seen`
- Produces: `iter_seed_openalex_ids(manifest: dict, mailto: str, seed_dois: list[str] | None = None) -> Iterator[tuple[str, str]]` (yields `(seed_key, openalex_id)` pairs); `iter_snowball_candidates(manifest: dict, mailto: str, batch_size: int, counts: dict, seed_map: dict, seed_dois: list[str] | None = None) -> Iterator[Work]`

- [ ] **Step 1: Write the failing tests**

```python
# academic-rag-model/tests/test_snowball.py
import unittest
from unittest.mock import MagicMock, patch

from journal_discovery.discovery import Work
from journal_discovery.snowball import iter_seed_openalex_ids, iter_snowball_candidates


def _work(idx, doi=None, openalex_id=None):
    return Work(
        openalex_id=openalex_id or f"https://openalex.org/W{idx}", doi=doi, title=f"Paper {idx}",
        authors=[], year=2024, abstract="x",
    )


class TestIterSeedOpenalexIds(unittest.TestCase):
    @patch("journal_discovery.snowball.resolve_work_by_doi")
    def test_yields_pairs_for_fetched_and_downloaded_entries(self, mock_resolve):
        manifest = {
            "10.1/fetched": {"status": "fetched"},
            "10.1/downloaded": {"status": "downloaded"},
            "10.1/manual": {"status": "needs_manual"},
        }
        mock_resolve.side_effect = lambda doi, mailto: _work(1, doi=doi, openalex_id=f"https://openalex.org/{doi}")

        pairs = list(iter_seed_openalex_ids(manifest, "me@example.com"))

        self.assertEqual(
            sorted(pairs),
            sorted([
                ("10.1/fetched", "https://openalex.org/10.1/fetched"),
                ("10.1/downloaded", "https://openalex.org/10.1/downloaded"),
            ]),
        )

    @patch("journal_discovery.snowball.resolve_work_by_doi")
    def test_skips_seed_that_fails_to_resolve(self, mock_resolve):
        manifest = {"10.1/broken": {"status": "fetched"}}
        mock_resolve.return_value = None

        pairs = list(iter_seed_openalex_ids(manifest, "me@example.com"))

        self.assertEqual(pairs, [])

    @patch("journal_discovery.snowball.resolve_work_by_doi")
    def test_seed_doi_override_bypasses_manifest_scan(self, mock_resolve):
        manifest = {"10.1/ignored": {"status": "fetched"}}
        mock_resolve.return_value = _work(1, doi="10.1/explicit", openalex_id="https://openalex.org/W1")

        pairs = list(iter_seed_openalex_ids(manifest, "me@example.com", seed_dois=["10.1/explicit"]))

        self.assertEqual(pairs, [("10.1/explicit", "https://openalex.org/W1")])

    def test_non_doi_manifest_key_used_directly_as_openalex_id(self):
        manifest = {"https://openalex.org/W9": {"status": "fetched"}}
        pairs = list(iter_seed_openalex_ids(manifest, "me@example.com"))
        self.assertEqual(pairs, [("https://openalex.org/W9", "https://openalex.org/W9")])


class TestIterSnowballCandidates(unittest.TestCase):
    @patch("journal_discovery.snowball.iter_citing_works")
    @patch("journal_discovery.snowball.iter_seed_openalex_ids")
    def test_chains_seeds_and_populates_seed_map(self, mock_seeds, mock_citing):
        mock_seeds.return_value = iter([("10.1/seed-a", "OA-A"), ("10.1/seed-b", "OA-B")])
        mock_citing.side_effect = lambda openalex_id, mailto, batch_size: iter(
            [_work(1, doi="10.1/citer-a")] if openalex_id == "OA-A" else [_work(2, doi="10.1/citer-b")]
        )
        manifest = {}
        counts = {"already_seen": 0}
        seed_map = {}

        candidates = list(iter_snowball_candidates(manifest, "me@example.com", 25, counts, seed_map))

        self.assertEqual(sorted(w.doi for w in candidates), ["10.1/citer-a", "10.1/citer-b"])
        self.assertEqual(seed_map["10.1/citer-a"], "10.1/seed-a")
        self.assertEqual(seed_map["10.1/citer-b"], "10.1/seed-b")

    @patch("journal_discovery.snowball.iter_citing_works")
    @patch("journal_discovery.snowball.iter_seed_openalex_ids")
    def test_already_seen_candidates_filtered_and_counted(self, mock_seeds, mock_citing):
        mock_seeds.return_value = iter([("10.1/seed-a", "OA-A")])
        mock_citing.return_value = iter([_work(1, doi="10.1/already-seen")])
        manifest = {"10.1/already-seen": {"status": "fetched"}}
        counts = {"already_seen": 0}
        seed_map = {}

        candidates = list(iter_snowball_candidates(manifest, "me@example.com", 25, counts, seed_map))

        self.assertEqual(candidates, [])
        self.assertEqual(counts["already_seen"], 1)
        self.assertNotIn("10.1/already-seen", seed_map)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd academic-rag-model && python -m pytest tests/test_snowball.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'journal_discovery.snowball'`

- [ ] **Step 3: Write the implementation**

```python
# academic-rag-model/journal_discovery/snowball.py
"""
snowball.py
Citation-based snowball sampling per spec 2026-09-02: a third discovery
route seeded from papers already in the corpus, using OpenAlex's own
forward-citation graph ("papers that cite this one") -- no bibliography
text-parsing needed. Deliberately never auto-fetched: propose() records
candidates as a checkbox worklist for human review; confirm() fetches
only what's checked. Reuses the existing relevance/access/manifest/
worklist machinery unchanged.
"""
from __future__ import annotations

from journal_discovery.discovery import Work, iter_citing_works, resolve_work_by_doi
from journal_discovery.manifest import skip_already_seen


def iter_seed_openalex_ids(manifest: dict, mailto: str, seed_dois: list[str] | None = None):
    """Yields (seed_key, openalex_id) pairs. seed_key is what a
    downstream proposed candidate records as its cites_seed metadata
    (the seed's own DOI when known, else its OpenAlex id); openalex_id
    is what iter_citing_works() actually queries against."""
    if seed_dois:
        for doi in seed_dois:
            work = resolve_work_by_doi(doi, mailto)
            if work is None:
                print(f"WARNING: could not resolve seed DOI {doi!r}; skipping.")
                continue
            yield doi, work.openalex_id
        return

    for key, entry in manifest.items():
        if entry.get("status") not in ("fetched", "downloaded"):
            continue
        if key.startswith("http"):
            yield key, key
            continue
        work = resolve_work_by_doi(key, mailto)
        if work is None:
            print(f"WARNING: could not resolve seed {key!r} to an OpenAlex id; skipping.")
            continue
        yield key, work.openalex_id


def iter_snowball_candidates(
    manifest: dict, mailto: str, batch_size: int, counts: dict, seed_map: dict,
    seed_dois: list[str] | None = None,
):
    from journal_discovery.manifest import manifest_key

    for seed_key, openalex_id in iter_seed_openalex_ids(manifest, mailto, seed_dois):
        citing = iter_citing_works(openalex_id, mailto, batch_size)
        for work in skip_already_seen(citing, manifest, counts):
            seed_map.setdefault(manifest_key(work), seed_key)
            yield work
```

Note: `manifest_key` is imported locally inside `iter_snowball_candidates`
rather than at module level to avoid a needless module-level dependency
surface -- this matches no particular existing convention strongly
either way; a top-level `from journal_discovery.manifest import
manifest_key, skip_already_seen` is equally acceptable if you prefer it
during implementation. Either passes the tests above unchanged.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd academic-rag-model && python -m pytest tests/test_snowball.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add academic-rag-model/journal_discovery/snowball.py academic-rag-model/tests/test_snowball.py
git commit -m "feat(journal_discovery): add snowball seed resolution and candidate streaming"
```

---

### Task 5: `snowball.py propose` — score and record candidates

**Files:**
- Modify: `academic-rag-model/journal_discovery/snowball.py`
- Modify: `academic-rag-model/tests/test_snowball.py`

**Interfaces:**
- Consumes: `journal_discovery.relevance.load_relevance_model`, `select_relevant_works`; `journal_discovery.manifest.load_manifest`, `save_manifest`, `manifest_path`, `manifest_key`, `record_outcome`; `journal_discovery.topic_routing.route_to_folder`; `journal_discovery.discovery.doi_url`; `journal_discovery.worklist.write_snowball_candidates_worklist`
- Produces: `propose(args: argparse.Namespace) -> dict`

- [ ] **Step 1: Write the failing tests**

```python
# Append to academic-rag-model/tests/test_snowball.py

import argparse
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from journal_discovery.relevance import ScoredWork
from journal_discovery.snowball import propose


def _propose_args(**overrides):
    defaults = dict(
        relevance_prompt="climate", relevance_threshold=0.5, batch_size=25,
        max_results=50, max_examined=200, seed_doi=[],
    )
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


class TestPropose(unittest.TestCase):
    @patch("journal_discovery.snowball.load_relevance_model", return_value=MagicMock())
    @patch("journal_discovery.snowball.iter_snowball_candidates")
    @patch("journal_discovery.snowball.select_relevant_works")
    def test_records_scored_candidates_as_proposed(self, mock_select, mock_candidates, mock_load_model):
        with tempfile.TemporaryDirectory() as tmp:
            work = _work(1, doi="10.1/citer")
            mock_candidates.return_value = iter([work])
            mock_select.return_value = [ScoredWork(work=work, score=0.75)]

            counts = propose(_propose_args(articles_dir=tmp, mailto="me@example.com"))

            self.assertEqual(counts["proposed"], 1)

            from journal_discovery.manifest import load_manifest, manifest_path
            manifest = load_manifest(manifest_path(tmp))
            entry = manifest["10.1/citer"]
            self.assertEqual(entry["status"], "proposed")
            self.assertEqual(entry["relevance_score"], 0.75)
            self.assertEqual(entry["title"], "Paper 1")
            self.assertIn("folder", entry)

    @patch("journal_discovery.snowball.load_relevance_model", return_value=MagicMock())
    @patch("journal_discovery.snowball.iter_snowball_candidates")
    @patch("journal_discovery.snowball.select_relevant_works")
    def test_writes_worklist(self, mock_select, mock_candidates, mock_load_model):
        with tempfile.TemporaryDirectory() as tmp:
            work = _work(1, doi="10.1/citer")
            mock_candidates.return_value = iter([work])
            mock_select.return_value = [ScoredWork(work=work, score=0.75)]

            propose(_propose_args(articles_dir=tmp, mailto="me@example.com"))

            worklist = Path(tmp) / "snowball_candidates.md"
            self.assertTrue(worklist.exists())
            self.assertIn("Paper 1", worklist.read_text(encoding="utf-8"))

    @patch("journal_discovery.snowball.load_relevance_model", return_value=MagicMock())
    @patch("journal_discovery.snowball.iter_snowball_candidates")
    @patch("journal_discovery.snowball.select_relevant_works")
    def test_records_cites_seed_from_seed_map(self, mock_select, mock_candidates, mock_load_model):
        with tempfile.TemporaryDirectory() as tmp:
            work = _work(1, doi="10.1/citer")

            def fake_candidates(manifest, mailto, batch_size, counts, seed_map, seed_dois=None):
                seed_map["10.1/citer"] = "10.1/seed-paper"
                yield work

            mock_candidates.side_effect = fake_candidates
            mock_select.return_value = [ScoredWork(work=work, score=0.75)]

            propose(_propose_args(articles_dir=tmp, mailto="me@example.com"))

            from journal_discovery.manifest import load_manifest, manifest_path
            manifest = load_manifest(manifest_path(tmp))
            self.assertEqual(manifest["10.1/citer"]["cites_seed"], "10.1/seed-paper")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd academic-rag-model && python -m pytest tests/test_snowball.py -k Propose -v`
Expected: FAIL with `ImportError: cannot import name 'propose'`

- [ ] **Step 3: Write the implementation**

```python
# Add to the top of journal_discovery/snowball.py, alongside the existing imports:
from journal_discovery.discovery import doi_url
from journal_discovery.manifest import (
    load_manifest,
    manifest_key,
    manifest_path,
    record_outcome,
    save_manifest,
)
from journal_discovery.relevance import load_relevance_model, select_relevant_works
from journal_discovery.topic_routing import route_to_folder
from journal_discovery.worklist import write_snowball_candidates_worklist

_DEFAULT_BATCH_SIZE = 25
_DEFAULT_MAX_RESULTS = 50
_DEFAULT_MAX_EXAMINED = 200
_DEFAULT_RELEVANCE_THRESHOLD = 0.5
_DEFAULT_PACE_PER_HOUR = 25.0
```

```python
# Add to journal_discovery/snowball.py, after iter_snowball_candidates():

def propose(args) -> dict:
    manifest_file = manifest_path(args.articles_dir)
    manifest = load_manifest(manifest_file)
    counts = {"examined": 0, "already_seen": 0, "proposed": 0}
    seed_map: dict[str, str] = {}

    model = load_relevance_model()
    candidates = iter_snowball_candidates(
        manifest, args.mailto, args.batch_size, counts, seed_map, args.seed_doi or None,
    )
    scored = select_relevant_works(
        candidates, model, args.relevance_prompt, args.relevance_threshold,
        args.max_results, args.max_examined,
    )
    counts["examined"] = len(scored)

    for scored_work in scored:
        work = scored_work.work
        key = manifest_key(work)
        folder = route_to_folder(args.articles_dir, work)
        record_outcome(manifest, key, "proposed", folder=folder.name, metadata={
            "title": work.title,
            "authors": work.authors,
            "year": work.year,
            "doi_url": doi_url(work),
            "relevance_score": scored_work.score,
            "cites_seed": seed_map.get(key),
        })
        counts["proposed"] += 1

    save_manifest(manifest_file, manifest)
    write_snowball_candidates_worklist(manifest, args.articles_dir)
    return counts
```

Note: `args.mailto` is read directly here (not via `os.environ` fallback)
because Task 6 wires `main()` to resolve it once via
`os.environ.get("OPENALEX_CONTACT_EMAIL")` before calling `propose()` --
tests pass it explicitly on the `Namespace`, matching how
`test_discover.py`'s `_args()` helper already does this for `discover.run()`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd academic-rag-model && python -m pytest tests/test_snowball.py -v`
Expected: PASS (9 tests total: 6 from Task 4 + 3 new)

- [ ] **Step 5: Commit**

```bash
git add academic-rag-model/journal_discovery/snowball.py academic-rag-model/tests/test_snowball.py
git commit -m "feat(journal_discovery): add snowball propose phase"
```

---

### Task 6: `snowball.py confirm` and CLI wiring

**Files:**
- Modify: `academic-rag-model/journal_discovery/snowball.py`
- Modify: `academic-rag-model/tests/test_snowball.py`

**Interfaces:**
- Consumes: `journal_discovery.access.resolve_full_text`; `journal_discovery.metadata_sidecar.write_sidecar`; `journal_discovery.topic_routing.pdf_filename`; `journal_discovery.worklist.write_needs_manual_worklist`, `_read_checked_links`
- Produces: `confirm(args: argparse.Namespace) -> dict`; `main() -> None`

- [ ] **Step 1: Write the failing tests**

```python
# Append to academic-rag-model/tests/test_snowball.py

from journal_discovery.access import AccessResult
from journal_discovery.snowball import confirm


def _confirm_args(**overrides):
    defaults = dict(pace_per_hour=25.0)
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


class TestConfirm(unittest.TestCase):
    @patch("journal_discovery.snowball.resolve_work_by_doi")
    @patch("journal_discovery.snowball.resolve_full_text")
    def test_fetches_checked_proposed_entry(self, mock_resolve_full_text, mock_resolve_by_doi):
        with tempfile.TemporaryDirectory() as tmp:
            from journal_discovery.manifest import manifest_path, load_manifest, save_manifest, record_outcome
            from journal_discovery.worklist import write_snowball_candidates_worklist

            path = manifest_path(tmp)
            manifest = load_manifest(path)
            record_outcome(manifest, "10.1/citer", "proposed", folder="business", metadata={
                "title": "A Candidate", "doi_url": "https://doi.org/10.1/citer", "relevance_score": 0.7,
            })
            save_manifest(path, manifest)
            worklist_path = write_snowball_candidates_worklist(manifest, tmp)
            worklist_path.write_text(
                worklist_path.read_text(encoding="utf-8").replace("- [ ] [A Candidate]", "- [x] [A Candidate]"),
                encoding="utf-8",
            )

            mock_resolve_by_doi.return_value = _work(1, doi="10.1/citer")
            mock_resolve_full_text.return_value = AccessResult(status="fetched", content=b"%PDF-1.4", tier="open_access")

            counts = confirm(_confirm_args(articles_dir=tmp, mailto="me@example.com", ezproxy_cookie=None))

            self.assertEqual(counts["confirmed"], 1)
            self.assertEqual(counts["fetched"], 1)

            manifest = load_manifest(path)
            self.assertEqual(manifest["10.1/citer"]["status"], "fetched")
            pdfs = list((Path(tmp) / "business").glob("*.pdf"))
            self.assertEqual(len(pdfs), 1)

    @patch("journal_discovery.snowball.resolve_work_by_doi")
    @patch("journal_discovery.snowball.resolve_full_text")
    def test_unchecked_proposed_entry_left_untouched(self, mock_resolve_full_text, mock_resolve_by_doi):
        with tempfile.TemporaryDirectory() as tmp:
            from journal_discovery.manifest import manifest_path, load_manifest, save_manifest, record_outcome
            from journal_discovery.worklist import write_snowball_candidates_worklist

            path = manifest_path(tmp)
            manifest = load_manifest(path)
            record_outcome(manifest, "10.1/citer", "proposed", folder="business", metadata={
                "title": "A Candidate", "doi_url": "https://doi.org/10.1/citer",
            })
            save_manifest(path, manifest)
            write_snowball_candidates_worklist(manifest, tmp)  # left unchecked

            counts = confirm(_confirm_args(articles_dir=tmp, mailto="me@example.com", ezproxy_cookie=None))

            self.assertEqual(counts["confirmed"], 0)
            mock_resolve_full_text.assert_not_called()
            manifest = load_manifest(path)
            self.assertEqual(manifest["10.1/citer"]["status"], "proposed")

    @patch("journal_discovery.snowball.resolve_work_by_doi")
    @patch("journal_discovery.snowball.resolve_full_text")
    def test_confirmed_but_unfetchable_lands_in_needs_manual_worklist(self, mock_resolve_full_text, mock_resolve_by_doi):
        with tempfile.TemporaryDirectory() as tmp:
            from journal_discovery.manifest import manifest_path, load_manifest, save_manifest, record_outcome
            from journal_discovery.worklist import write_snowball_candidates_worklist

            path = manifest_path(tmp)
            manifest = load_manifest(path)
            record_outcome(manifest, "10.1/citer", "proposed", folder="business", metadata={
                "title": "A Candidate", "doi_url": "https://doi.org/10.1/citer",
            })
            save_manifest(path, manifest)
            worklist_path = write_snowball_candidates_worklist(manifest, tmp)
            worklist_path.write_text(
                worklist_path.read_text(encoding="utf-8").replace("- [ ] [A Candidate]", "- [x] [A Candidate]"),
                encoding="utf-8",
            )

            mock_resolve_by_doi.return_value = _work(1, doi="10.1/citer")
            mock_resolve_full_text.return_value = AccessResult(status="needs_manual")

            counts = confirm(_confirm_args(articles_dir=tmp, mailto="me@example.com", ezproxy_cookie=None))

            self.assertEqual(counts["needs_manual"], 1)
            needs_manual_content = (Path(tmp) / "needs_manual_downloads.md").read_text(encoding="utf-8")
            self.assertIn("A Candidate", needs_manual_content)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd academic-rag-model && python -m pytest tests/test_snowball.py -k Confirm -v`
Expected: FAIL with `ImportError: cannot import name 'confirm'`

- [ ] **Step 3: Write the implementation**

```python
# Add to the top of journal_discovery/snowball.py, alongside the existing imports:
import argparse
import os
import sys
from pathlib import Path

from common.gemini_utils import load_dotenv_override
from journal_discovery.access import resolve_full_text
from journal_discovery.metadata_sidecar import write_sidecar
from journal_discovery.topic_routing import pdf_filename, route_to_folder
from journal_discovery.worklist import (
    _read_checked_links,
    write_needs_manual_worklist,
    write_snowball_candidates_worklist,
)
```

```python
# Add to journal_discovery/snowball.py, after propose():

def confirm(args) -> dict:
    manifest_file = manifest_path(args.articles_dir)
    manifest = load_manifest(manifest_file)
    checked_links = _read_checked_links(Path(args.articles_dir) / "snowball_candidates.md")

    counts = {"confirmed": 0, "fetched": 0, "needs_manual": 0}
    for key, entry in list(manifest.items()):
        if entry.get("status") != "proposed":
            continue
        link = entry.get("doi_url") or (key if key.startswith("http") else f"https://doi.org/{key}")
        if link not in checked_links:
            continue
        counts["confirmed"] += 1

        work = resolve_work_by_doi(key, args.mailto) if not key.startswith("http") else None
        if work is None:
            print(f"WARNING: could not re-resolve {key!r}; leaving as proposed.")
            counts["confirmed"] -= 1
            continue

        result = resolve_full_text(work, args.mailto, args.ezproxy_cookie, args.pace_per_hour)
        folder = route_to_folder(args.articles_dir, work)
        if result.status == "fetched":
            pdf_path = folder / pdf_filename(work)
            pdf_path.write_bytes(result.content)
            write_sidecar(pdf_path, work, entry.get("relevance_score"), result.tier)
            record_outcome(manifest, key, "fetched", folder=folder.name)
            counts["fetched"] += 1
        else:
            record_outcome(manifest, key, "needs_manual", folder=folder.name, metadata={
                "title": work.title,
                "authors": work.authors,
                "year": work.year,
                "doi_url": doi_url(work),
            })
            counts["needs_manual"] += 1

    save_manifest(manifest_file, manifest)
    write_snowball_candidates_worklist(manifest, args.articles_dir)
    write_needs_manual_worklist(manifest, args.articles_dir)
    return counts


def main():
    parser = argparse.ArgumentParser(
        description="Citation-based snowball sampling: propose candidates from the corpus's own "
                     "citation network, then confirm which to fetch.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    default_articles_dir = Path(__file__).resolve().parent.parent.parent / "research" / "journal-articles"

    propose_parser = subparsers.add_parser(
        "propose", help="Find and score citing-paper candidates, write a checkbox worklist.",
    )
    propose_parser.add_argument(
        "--relevance-prompt", required=True,
        help="Free-text description of what you're actually looking for -- scored against each "
             "candidate's abstract, same as discover.py's own flag.",
    )
    propose_parser.add_argument("--relevance-threshold", type=float, default=_DEFAULT_RELEVANCE_THRESHOLD)
    propose_parser.add_argument("--batch-size", type=int, default=_DEFAULT_BATCH_SIZE)
    propose_parser.add_argument("--max-results", type=int, default=_DEFAULT_MAX_RESULTS)
    propose_parser.add_argument("--max-examined", type=int, default=_DEFAULT_MAX_EXAMINED)
    propose_parser.add_argument(
        "--seed-doi", action="append", default=[],
        help="Scope seeding to these DOIs instead of every fetched/downloaded paper in the corpus (repeatable).",
    )
    propose_parser.add_argument("--articles-dir", default=str(default_articles_dir))

    confirm_parser = subparsers.add_parser(
        "confirm", help="Fetch full text for whatever's checked in snowball_candidates.md.",
    )
    confirm_parser.add_argument(
        "--pace-per-hour", type=float, default=_DEFAULT_PACE_PER_HOUR,
        help="EZProxy-tier pacing, same meaning as discover.py's own flag.",
    )
    confirm_parser.add_argument("--articles-dir", default=str(default_articles_dir))

    args = parser.parse_args()

    load_dotenv_override()
    args.mailto = os.environ.get("OPENALEX_CONTACT_EMAIL")
    if not args.mailto:
        print("ERROR: OPENALEX_CONTACT_EMAIL must be set in .env (required by OpenAlex).")
        sys.exit(1)
    args.ezproxy_cookie = os.environ.get("EZPROXY_SESSION_COOKIE")

    if args.command == "propose":
        counts = propose(args)
        print(f"\nExamined: {counts['examined']}")
        print(f"Already seen (skipped): {counts['already_seen']}")
        print(f"Proposed: {counts['proposed']}")
        if counts["proposed"]:
            print(f"Review: {Path(args.articles_dir) / 'snowball_candidates.md'}")
    else:
        counts = confirm(args)
        print(f"\nConfirmed: {counts['confirmed']}")
        print(f"Fetched: {counts['fetched']}")
        print(f"Needs manual download: {counts['needs_manual']}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd academic-rag-model && python -m pytest tests/test_snowball.py -v`
Expected: PASS (12 tests total)

- [ ] **Step 5: Run the entire journal_discovery test suite**

Run: `cd academic-rag-model && python -m pytest tests/ -q`
Expected: PASS, all tests across the whole project (baseline count from before this plan, plus every new test added across Tasks 1-6)

- [ ] **Step 6: Commit**

```bash
git add academic-rag-model/journal_discovery/snowball.py academic-rag-model/tests/test_snowball.py
git commit -m "feat(journal_discovery): add snowball confirm phase and CLI"
```

---

### Task 7: Documentation

**Files:**
- Modify: `academic-rag-model/journal_discovery_instructions.md`

**Interfaces:** None (docs only).

- [ ] **Step 1: Add a "Route 3" section**

Insert after the existing "Step 3: Reconcile manual downloads" section
(before "## EZProxy setup"):

```markdown
## Route 3: Citation snowball sampling

A third way to find papers, alongside `--faculty`/`--topic`: follow
citations from what's already in your corpus, via OpenAlex's own
"cited by" graph. Two steps, deliberately never auto-fetching anything:

```powershell
python -m journal_discovery.snowball propose --relevance-prompt "climate-forced displacement and adaptation policy"
```

Seeds from every paper already `fetched`/`downloaded` in your corpus
(or `--seed-doi`, repeatable, to scope it to specific papers), finds
what cites them, scores each candidate through the same relevance gate
`discover.py` uses, and writes `snowball_candidates.md` -- a checkbox
list, nothing downloaded yet. Each entry shows its relevance score and
which corpus paper it cites, so you have context for *why* it was
proposed. Check the ones you actually want, then:

```powershell
python -m journal_discovery.snowball confirm
```

Fetches full text only for checked candidates, through the same
Unpaywall -> Semantic Scholar -> arXiv -> EZProxy chain as any other
route. A confirmed candidate that can't be auto-fetched lands in
`needs_manual_downloads.md` exactly like any other route's outcome --
nothing downstream treats a snowball-sourced paper any differently once
you've confirmed it.

An unchecked candidate is never re-proposed on a later `propose` run --
leaving it unchecked *is* the reject; there's no separate action
needed. Change your mind later by checking it before your next
`confirm`.
```

- [ ] **Step 2: Commit**

```bash
git add academic-rag-model/journal_discovery_instructions.md
git commit -m "docs(journal_discovery): document citation snowball sampling"
```

---

## Self-Review Notes

- **Spec coverage:** S1 goals (seed from corpus + `--seed-doi` override -> Task 4; relevance-scoring gate reused unmodified -> Task 5; checkbox worklist, never auto-fetched -> Tasks 3, 5; confirm reuses the existing access chain -> Task 6; never re-propose already-seen -> Tasks 2, 4) all map to a task. S2 architecture (module lives inside `journal_discovery`) -> Task 4-6's import structure. S3 components map 1:1 to Tasks 1 (`discovery.py`), 2 (`manifest.py`), 3 (`worklist.py`), 4-6 (`snowball.py`). S4 data flow is exactly `propose()`/`confirm()`. S5 state model (the `"proposed"` status, `skip_already_seen` treating it as seen, `confirm` bypassing that filter) is enforced by Task 2's test (`test_proposed_status_also_treated_as_seen`) and Task 6's design (`confirm` reads `status == "proposed"` directly, never calls `skip_already_seen`). S6 error handling (unresolvable seed, `FetchError` on DOI lookup) -> Tasks 1, 4. S7 testing conventions followed throughout. S8 follow-ons are explicitly not implemented by this plan, matching the spec's own "not decided" framing.
- **Placeholder scan:** none found -- every step has runnable code or an explicit, justified deviation (the `pdf_filename()` relocation from `discovery.py` to `topic_routing.py` in Task 1, decided and explained inline to avoid a circular import, not left as a TODO).
- **Type consistency:** `Work` (unchanged, from `discovery.py`) flows through every new function identically to how `discover.py` already uses it. `ScoredWork` (unchanged, from `relevance.py`) is consumed the same way in `propose()` as in `discover.run()`. `AccessResult` (unchanged, from `access.py`) is consumed the same way in `confirm()` as in `discover.run()`. Function names introduced in one task (`doi_url`, `pdf_filename`, `skip_already_seen`, `resolve_work_by_doi`, `iter_citing_works`, `iter_seed_openalex_ids`, `iter_snowball_candidates`) are used identically by every later task that imports them.
