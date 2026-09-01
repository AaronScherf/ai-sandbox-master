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
        # doi=None short-circuits try_unpaywall() before it makes any
        # fetch_with_retries call, so the single mocked response below is
        # unambiguously the arXiv download attempt.
        mock_fetch.return_value = _pdf_response(b"arxiv-content")
        work = _work(doi=None, oa_url=None, arxiv_id="2401.12345")

        result = resolve_full_text(work, "me@example.com", ezproxy_cookie=None, pace_per_hour=25)

        self.assertEqual(result.tier, "arxiv")
        self.assertEqual(result.content, b"arxiv-content")

    @patch("journal_discovery.access.paced_sleep")
    @patch("journal_discovery.access.fetch_with_retries")
    def test_falls_back_to_ezproxy_with_cookie(self, mock_fetch, mock_pace):
        # A doi is required to build the EZProxy URL, so try_unpaywall()
        # *does* make a real fetch_with_retries call here -- the first
        # mocked response represents Unpaywall reporting no OA location,
        # the second represents the EZProxy PDF download.
        no_oa_response = MagicMock(status_code=200)
        no_oa_response.json.return_value = {"best_oa_location": None}
        mock_fetch.side_effect = [no_oa_response, _pdf_response(b"ezproxy-content")]
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
