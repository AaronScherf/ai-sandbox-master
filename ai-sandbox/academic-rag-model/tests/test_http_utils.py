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
