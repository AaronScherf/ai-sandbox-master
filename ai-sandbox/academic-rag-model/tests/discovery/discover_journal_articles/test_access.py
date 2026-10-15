import unittest
from unittest.mock import MagicMock, patch

from discovery.discover_journal_articles.access import (
    AccessResult,
    build_ezproxy_url,
    resolve_full_text,
    try_arxiv_url,
    try_core,
    try_semantic_scholar,
    try_unpaywall,
)
from discovery.discover_journal_articles.discovery import Work


def _work(doi="10.1/abc", oa_url=None, arxiv_id=None):
    return Work(
        openalex_id="W1", doi=doi, title="T", authors=[], year=2024, abstract=None,
        oa_url=oa_url, arxiv_id=arxiv_id,
    )


def _real_pdf_bytes() -> bytes:
    # A real, pypdf-parseable PDF -- Task 1 (is_valid_pdf_bytes) now
    # requires the downloaded body to actually open, not just start with
    # "%PDF-", so fixture content for a successful download must be real.
    import io
    from pypdf import PdfWriter
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


_REAL_PDF_BYTES = _real_pdf_bytes()


def _pdf_response(content=None):
    return MagicMock(status_code=200, headers={"Content-Type": "application/pdf"}, content=content or _REAL_PDF_BYTES)


def _html_response():
    return MagicMock(status_code=200, headers={"Content-Type": "text/html"}, content=b"<html>login</html>")


class TestTryUnpaywall(unittest.TestCase):
    @patch("discovery.discover_journal_articles.access.fetch_with_retries")
    def test_returns_pdf_url(self, mock_fetch):
        response = MagicMock(status_code=200)
        response.json.return_value = {"best_oa_location": {"url_for_pdf": "https://x.com/p.pdf"}}
        mock_fetch.return_value = response
        self.assertEqual(try_unpaywall("10.1/abc", "me@example.com"), "https://x.com/p.pdf")

    def test_none_without_doi(self):
        self.assertIsNone(try_unpaywall(None, "me@example.com"))


class TestTrySemanticScholar(unittest.TestCase):
    @patch("discovery.discover_journal_articles.access.fetch_with_retries")
    def test_returns_open_access_pdf_url(self, mock_fetch):
        response = MagicMock(status_code=200)
        response.json.return_value = {"openAccessPdf": {"url": "https://x.com/s2.pdf"}}
        mock_fetch.return_value = response
        self.assertEqual(try_semantic_scholar("10.1/abc"), "https://x.com/s2.pdf")

    @patch("discovery.discover_journal_articles.access.fetch_with_retries")
    def test_none_when_no_open_access_pdf(self, mock_fetch):
        response = MagicMock(status_code=200)
        response.json.return_value = {"openAccessPdf": None}
        mock_fetch.return_value = response
        self.assertIsNone(try_semantic_scholar("10.1/abc"))

    def test_none_without_doi(self):
        self.assertIsNone(try_semantic_scholar(None))

    @patch("discovery.discover_journal_articles.access.fetch_with_retries")
    def test_none_on_terminal_error(self, mock_fetch):
        from discovery.discover_journal_articles.http_utils import FetchError
        mock_fetch.side_effect = FetchError("not found")
        self.assertIsNone(try_semantic_scholar("10.1/unknown"))


class TestTryCore(unittest.TestCase):
    @patch("discovery.discover_journal_articles.access.fetch_with_retries")
    def test_returns_download_url(self, mock_fetch):
        response = MagicMock(status_code=200)
        response.json.return_value = {"results": [{"downloadUrl": "https://core.ac.uk/download/123.pdf"}]}
        mock_fetch.return_value = response
        self.assertEqual(try_core("10.1/abc", "my-api-key"), "https://core.ac.uk/download/123.pdf")

    @patch("discovery.discover_journal_articles.access.fetch_with_retries")
    def test_falls_back_to_source_fulltext_urls(self, mock_fetch):
        response = MagicMock(status_code=200)
        response.json.return_value = {
            "results": [{"downloadUrl": None, "sourceFulltextUrls": ["https://example.com/repo/123.pdf"]}],
        }
        mock_fetch.return_value = response
        self.assertEqual(try_core("10.1/abc", "my-api-key"), "https://example.com/repo/123.pdf")

    @patch("discovery.discover_journal_articles.access.fetch_with_retries")
    def test_none_when_no_results(self, mock_fetch):
        response = MagicMock(status_code=200)
        response.json.return_value = {"results": []}
        mock_fetch.return_value = response
        self.assertIsNone(try_core("10.1/abc", "my-api-key"))

    def test_none_without_doi(self):
        self.assertIsNone(try_core(None, "my-api-key"))

    def test_none_without_api_key(self):
        self.assertIsNone(try_core("10.1/abc", None))

    @patch("discovery.discover_journal_articles.access.fetch_with_retries")
    def test_none_on_terminal_error(self, mock_fetch):
        from discovery.discover_journal_articles.http_utils import FetchError
        mock_fetch.side_effect = FetchError("not found")
        self.assertIsNone(try_core("10.1/unknown", "my-api-key"))

    @patch("discovery.discover_journal_articles.access.fetch_with_retries")
    def test_sends_bearer_auth_and_doi_query(self, mock_fetch):
        response = MagicMock(status_code=200)
        response.json.return_value = {"results": []}
        mock_fetch.return_value = response
        try_core("10.1/abc", "my-api-key")
        _, kwargs = mock_fetch.call_args
        self.assertEqual(kwargs["headers"], {"Authorization": "Bearer my-api-key"})
        self.assertEqual(kwargs["params"], {"q": 'doi:"10.1/abc"'})


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
    @patch("discovery.discover_journal_articles.access.paced_sleep")
    @patch("discovery.discover_journal_articles.access.fetch_with_retries")
    def test_uses_open_access_url_first(self, mock_fetch, mock_pace):
        mock_fetch.return_value = _pdf_response(_REAL_PDF_BYTES)
        work = _work(oa_url="https://x.com/p.pdf")

        result = resolve_full_text(work, "me@example.com", ezproxy_cookie=None, pace_per_hour=25)

        self.assertEqual(result, AccessResult(status="fetched", content=_REAL_PDF_BYTES, tier="open_access"))
        # OA hosts carry none of the EZProxy account-safety risk pacing
        # exists for -- confirmed 2026-09-02, only the EZProxy tier paces.
        mock_pace.assert_called_once_with(0)

    @patch("discovery.discover_journal_articles.access.paced_sleep")
    @patch("discovery.discover_journal_articles.access.fetch_with_retries")
    def test_download_sends_a_realistic_user_agent(self, mock_fetch, mock_pace):
        # Confirmed live 2026-09-03: a real CORE.ac.uk downloadUrl 403'd
        # with default requests' own User-Agent (a Cloudflare "Just a
        # moment..." bot challenge, the same failure class already
        # documented for EZProxy) but succeeded with a real browser
        # User-Agent string -- _download() must always send one.
        mock_fetch.return_value = _pdf_response(_REAL_PDF_BYTES)
        work = _work(oa_url="https://x.com/p.pdf")

        resolve_full_text(work, "me@example.com", ezproxy_cookie=None, pace_per_hour=25)

        _, kwargs = mock_fetch.call_args
        self.assertIn("User-Agent", kwargs["headers"])
        self.assertNotIn("python-requests", kwargs["headers"]["User-Agent"])

    @patch("discovery.discover_journal_articles.access.paced_sleep")
    @patch("discovery.discover_journal_articles.access.fetch_with_retries")
    def test_falls_back_to_semantic_scholar_when_unpaywall_has_no_oa(self, mock_fetch, mock_pace):
        no_oa_response = MagicMock(status_code=200)
        no_oa_response.json.return_value = {"best_oa_location": None}
        s2_response = MagicMock(status_code=200)
        s2_response.json.return_value = {"openAccessPdf": {"url": "https://x.com/s2.pdf"}}
        mock_fetch.side_effect = [no_oa_response, s2_response, _pdf_response(_REAL_PDF_BYTES)]
        work = _work(doi="10.1/abc", oa_url=None, arxiv_id=None)

        result = resolve_full_text(work, "me@example.com", ezproxy_cookie=None, pace_per_hour=25)

        self.assertEqual(result.tier, "semantic_scholar")
        self.assertEqual(result.content, _REAL_PDF_BYTES)
        mock_pace.assert_called_once_with(0)

    @patch("discovery.discover_journal_articles.access.paced_sleep")
    @patch("discovery.discover_journal_articles.access.fetch_with_retries")
    def test_falls_back_to_core_when_semantic_scholar_has_no_oa(self, mock_fetch, mock_pace):
        no_oa_response = MagicMock(status_code=200)
        no_oa_response.json.return_value = {"best_oa_location": None}
        no_s2_response = MagicMock(status_code=200)
        no_s2_response.json.return_value = {"openAccessPdf": None}
        core_response = MagicMock(status_code=200)
        core_response.json.return_value = {"results": [{"downloadUrl": "https://core.ac.uk/download/123.pdf"}]}
        mock_fetch.side_effect = [no_oa_response, no_s2_response, core_response, _pdf_response(_REAL_PDF_BYTES)]
        work = _work(doi="10.1/abc", oa_url=None, arxiv_id=None)

        result = resolve_full_text(
            work, "me@example.com", ezproxy_cookie=None, pace_per_hour=25, core_api_key="my-api-key",
        )

        self.assertEqual(result.tier, "core")
        self.assertEqual(result.content, _REAL_PDF_BYTES)
        mock_pace.assert_called_once_with(0)

    @patch("discovery.discover_journal_articles.access.paced_sleep")
    @patch("discovery.discover_journal_articles.access.fetch_with_retries")
    def test_core_skipped_without_api_key_falls_through_to_arxiv(self, mock_fetch, mock_pace):
        no_oa_response = MagicMock(status_code=200)
        no_oa_response.json.return_value = {"best_oa_location": None}
        no_s2_response = MagicMock(status_code=200)
        no_s2_response.json.return_value = {"openAccessPdf": None}
        mock_fetch.side_effect = [no_oa_response, no_s2_response, _pdf_response(_REAL_PDF_BYTES)]
        work = _work(doi="10.1/abc", oa_url=None, arxiv_id="2401.12345")

        result = resolve_full_text(
            work, "me@example.com", ezproxy_cookie=None, pace_per_hour=25, core_api_key=None,
        )

        self.assertEqual(result.tier, "arxiv")
        self.assertEqual(result.content, _REAL_PDF_BYTES)

    @patch("discovery.discover_journal_articles.access.paced_sleep")
    @patch("discovery.discover_journal_articles.access.fetch_with_retries")
    def test_falls_back_to_arxiv(self, mock_fetch, mock_pace):
        # doi=None short-circuits try_unpaywall() before it makes any
        # fetch_with_retries call, so the single mocked response below is
        # unambiguously the arXiv download attempt.
        mock_fetch.return_value = _pdf_response(_REAL_PDF_BYTES)
        work = _work(doi=None, oa_url=None, arxiv_id="2401.12345")

        result = resolve_full_text(work, "me@example.com", ezproxy_cookie=None, pace_per_hour=25)

        self.assertEqual(result.tier, "arxiv")
        self.assertEqual(result.content, _REAL_PDF_BYTES)
        mock_pace.assert_called_once_with(0)

    @patch("discovery.discover_journal_articles.access.paced_sleep")
    @patch("discovery.discover_journal_articles.access.fetch_with_retries")
    def test_falls_back_to_ezproxy_with_cookie(self, mock_fetch, mock_pace):
        # A doi is required to build the EZProxy URL, so try_unpaywall()
        # and try_semantic_scholar() *do* make real fetch_with_retries
        # calls here -- the first two mocked responses represent both
        # reporting no OA location, the third is the EZProxy PDF download.
        no_oa_response = MagicMock(status_code=200)
        no_oa_response.json.return_value = {"best_oa_location": None}
        no_s2_response = MagicMock(status_code=200)
        no_s2_response.json.return_value = {"openAccessPdf": None}
        mock_fetch.side_effect = [no_oa_response, no_s2_response, _pdf_response(_REAL_PDF_BYTES)]
        work = _work(doi="10.1/abc", oa_url=None, arxiv_id=None)

        result = resolve_full_text(work, "me@example.com", ezproxy_cookie="session123", pace_per_hour=25)

        self.assertEqual(result.tier, "ezproxy")
        self.assertEqual(result.content, _REAL_PDF_BYTES)
        # The EZProxy tier is the only one where account-safety pacing
        # actually matters -- the real --pace-per-hour value is used here.
        mock_pace.assert_called_once_with(25)

    @patch("discovery.discover_journal_articles.access.paced_sleep")
    @patch("discovery.discover_journal_articles.access.fetch_with_retries")
    def test_falls_through_to_next_oa_provider_when_first_oa_url_fails_download(self, mock_fetch, mock_pace):
        # The audit's core finding: a present-but-broken oa_url must not
        # block trying Unpaywall/Semantic Scholar/CORE -- only an
        # exhausted provider list reaches needs_manual.
        broken_oa_download = _html_response()
        unpaywall_lookup = MagicMock(status_code=200)
        unpaywall_lookup.json.return_value = {"best_oa_location": {"url_for_pdf": "https://x.com/unpaywall.pdf"}}
        mock_fetch.side_effect = [broken_oa_download, unpaywall_lookup, _pdf_response(_REAL_PDF_BYTES)]
        work = _work(doi="10.1/abc", oa_url="https://x.com/broken.pdf")

        result = resolve_full_text(work, "me@example.com", ezproxy_cookie=None, pace_per_hour=25)

        self.assertEqual(result.tier, "unpaywall")
        self.assertEqual(result.content, _REAL_PDF_BYTES)

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

    @patch("discovery.discover_journal_articles.access.paced_sleep")
    @patch("discovery.discover_journal_articles.access.fetch_with_retries")
    def test_html_response_never_written_falls_through_to_needs_manual(self, mock_fetch, mock_pace):
        mock_fetch.return_value = _html_response()
        work = _work(oa_url="https://x.com/p.pdf")

        result = resolve_full_text(work, "me@example.com", ezproxy_cookie=None, pace_per_hour=25)

        self.assertEqual(result.status, "needs_manual")
        self.assertIsNone(result.content)

    @patch("discovery.discover_journal_articles.access.paced_sleep")
    def test_needs_manual_without_any_viable_tier(self, mock_pace):
        work = _work(doi=None, oa_url=None, arxiv_id=None)

        result = resolve_full_text(work, "me@example.com", ezproxy_cookie=None, pace_per_hour=25)

        self.assertEqual(result, AccessResult(status="needs_manual"))
        mock_pace.assert_not_called()

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

    @patch("discovery.discover_journal_articles.access.paced_sleep")
    @patch("discovery.discover_journal_articles.access.fetch_with_retries")
    def test_terminal_http_error_falls_through_instead_of_crashing(self, mock_fetch, mock_pace):
        # Confirmed live 2026-09-02: a real OA link (aeaweb.org) returned a
        # permanent 403. fetch_with_retries() raises FetchError for a
        # non-retryable status like this rather than returning a response
        # -- _download() must catch that and treat it as "this tier
        # failed," not let it crash the whole run.
        from discovery.discover_journal_articles.http_utils import FetchError
        mock_fetch.side_effect = FetchError("GET https://x.com/p.pdf failed with status 403 after 3 attempts")
        work = _work(oa_url="https://x.com/p.pdf")

        result = resolve_full_text(work, "me@example.com", ezproxy_cookie=None, pace_per_hour=25)

        self.assertEqual(result.status, "needs_manual")
        self.assertIsNone(result.content)

    @patch("discovery.discover_journal_articles.access.time.monotonic")
    @patch("discovery.discover_journal_articles.access.paced_sleep")
    @patch("discovery.discover_journal_articles.access.fetch_with_retries")
    def test_deadline_exhausted_mid_chain_stops_before_the_next_download(
        self, mock_fetch, mock_pace, mock_monotonic
    ):
        # Confirmed real (code review finding, 2026-10-15): the per-run
        # time budget (A.5) was only checked between papers in
        # discover.py's loop -- one paper's own OA -> arXiv -> EZProxy
        # chain under sustained 429s could run arbitrarily long before
        # the next check. resolve_full_text() must honor a deadline
        # between its own tiers too, not just let the caller stop
        # between papers.
        mock_fetch.return_value = _pdf_response(_REAL_PDF_BYTES)
        mock_monotonic.return_value = 1000.0  # already past the deadline
        work = _work(doi="10.1/abc", oa_url="https://x.com/p.pdf", arxiv_id="1234.5678")

        result = resolve_full_text(
            work, "me@example.com", ezproxy_cookie=None, pace_per_hour=25, deadline=999.0,
        )

        self.assertEqual(result.status, "needs_manual")
        mock_fetch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
