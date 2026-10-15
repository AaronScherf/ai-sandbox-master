import unittest
from unittest.mock import MagicMock, patch

from discovery.discover_journal_articles.http_utils import FetchError, fetch_with_retries, is_pdf_response, paced_sleep


class TestFetchWithRetries(unittest.TestCase):
    @patch("discovery.discover_journal_articles.http_utils.time.sleep")
    @patch("discovery.discover_journal_articles.http_utils.requests.request")
    def test_retries_on_429_honoring_retry_after(self, mock_request, mock_sleep):
        rate_limited = MagicMock(status_code=429, headers={"Retry-After": "5"})
        success = MagicMock(status_code=200, headers={})
        mock_request.side_effect = [rate_limited, success]

        response = fetch_with_retries("GET", "https://example.com")

        self.assertIs(response, success)
        mock_sleep.assert_called_once_with(5.0)

    @patch("discovery.discover_journal_articles.http_utils.time.sleep")
    @patch("discovery.discover_journal_articles.http_utils.requests.request")
    def test_returns_immediately_on_success(self, mock_request, mock_sleep):
        success = MagicMock(status_code=200, headers={})
        mock_request.return_value = success

        response = fetch_with_retries("GET", "https://example.com")

        self.assertIs(response, success)
        mock_sleep.assert_not_called()

    @patch("discovery.discover_journal_articles.http_utils.time.sleep")
    @patch("discovery.discover_journal_articles.http_utils.requests.request")
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
    def test_negative_numeric_retry_after_clamps_to_zero(self, mock_request, mock_sleep):
        rate_limited = MagicMock(status_code=429, headers={"Retry-After": "-5"})
        success = MagicMock(status_code=200, headers={})
        mock_request.side_effect = [rate_limited, success]

        fetch_with_retries("GET", "https://example.com")

        mock_sleep.assert_called_once_with(0.0)

    @patch("discovery.discover_journal_articles.http_utils.time.sleep")
    @patch("discovery.discover_journal_articles.http_utils.requests.request")
    def test_nan_retry_after_falls_back_to_default_backoff(self, mock_request, mock_sleep):
        rate_limited = MagicMock(status_code=429, headers={"Retry-After": "nan"})
        success = MagicMock(status_code=200, headers={})
        mock_request.side_effect = [rate_limited, success]

        fetch_with_retries("GET", "https://example.com", backoff_seconds=2.0)

        mock_sleep.assert_called_once_with(2.0)

    @patch("discovery.discover_journal_articles.http_utils.time.sleep")
    @patch("discovery.discover_journal_articles.http_utils.requests.request")
    def test_malformed_retry_after_falls_back_to_default_backoff(self, mock_request, mock_sleep):
        rate_limited = MagicMock(status_code=429, headers={"Retry-After": "not-a-value"})
        success = MagicMock(status_code=200, headers={})
        mock_request.side_effect = [rate_limited, success]

        fetch_with_retries("GET", "https://example.com", backoff_seconds=2.0)

        mock_sleep.assert_called_once_with(2.0)


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


class TestPacedSleep(unittest.TestCase):
    @patch("discovery.discover_journal_articles.http_utils.time.sleep")
    @patch("discovery.discover_journal_articles.http_utils.random.uniform")
    def test_sleeps_jittered_interval(self, mock_uniform, mock_sleep):
        mock_uniform.return_value = 100.0

        paced_sleep(pace_per_hour=25)

        # min_interval = 3600 / 25 = 144 seconds, jittered +/-30%
        args, _ = mock_uniform.call_args
        self.assertAlmostEqual(args[0], 144 * 0.7, places=3)
        self.assertAlmostEqual(args[1], 144 * 1.3, places=3)
        mock_sleep.assert_called_once_with(100.0)

    @patch("discovery.discover_journal_articles.http_utils.time.sleep")
    def test_disabled_when_pace_is_zero(self, mock_sleep):
        paced_sleep(pace_per_hour=0)
        mock_sleep.assert_not_called()


if __name__ == "__main__":
    unittest.main()
