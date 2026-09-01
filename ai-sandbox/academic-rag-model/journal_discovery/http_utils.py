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
