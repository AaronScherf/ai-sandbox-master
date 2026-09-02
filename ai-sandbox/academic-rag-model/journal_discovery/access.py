"""
access.py
Full-text resolution per spec S1/S3/S6: Unpaywall (open access) -> arXiv
(preprints) -> Columbia EZProxy (gated, manual session cookie). A
response that isn't actually application/pdf (an EZProxy login wall on
an expired cookie) is never written to disk.

Pacing (paced_sleep) applies to the EZProxy tier only, per real usage
2026-09-02: its purpose is protecting the user's own Columbia account
from automated-abuse detection, which simply doesn't apply to OA/arXiv
downloads -- those hit diverse, unrelated hosts, not Columbia's proxy.
Pacing every tier uniformly (the original design) made OA-heavy batches
needlessly slow with no actual safety benefit.
"""
from __future__ import annotations

from dataclasses import dataclass

from journal_discovery.discovery import Work
from journal_discovery.http_utils import FetchError, fetch_with_retries, is_pdf_response, paced_sleep

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
    try:
        response = fetch_with_retries("GET", f"{_UNPAYWALL_BASE}/{doi}", params={"email": mailto})
    except FetchError:
        # A DOI Unpaywall doesn't recognize returns 404 -- a permanent,
        # non-retryable failure, not a bug -- just no OA record for it.
        return None
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
    try:
        response = fetch_with_retries("GET", url, cookies=cookies, timeout=30)
    except FetchError:
        # Confirmed live 2026-09-02: a real "open access" URL (aeaweb.org)
        # returned a permanent 403 -- fetch_with_retries() raises rather
        # than returning a response for a non-retryable status. This tier
        # simply didn't work for this paper; the caller falls through to
        # the next tier / needs_manual, exactly like a non-PDF response.
        return None
    if response.status_code != 200 or not is_pdf_response(response):
        return None
    return response.content


def resolve_full_text(
    work: Work, mailto: str, ezproxy_cookie: str | None, pace_per_hour: float
) -> AccessResult:
    oa_url = work.oa_url or try_unpaywall(work.doi, mailto)
    if oa_url:
        content = _download(oa_url, 0)  # OA hosts carry none of the EZProxy account-safety risk
        if content:
            return AccessResult(status="fetched", content=content, tier="open_access")

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
