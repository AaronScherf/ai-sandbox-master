"""
access.py
Full-text resolution per spec S1/S3/S6: Unpaywall -> Semantic Scholar ->
CORE.ac.uk (all three open-access discovery; Semantic Scholar and
CORE.ac.uk added 2026-09-02/03 since Unpaywall's own OA-repository
coverage is incomplete) -> arXiv (preprints) -> Columbia EZProxy
(gated, manual session cookie). CORE.ac.uk requires a free API key
(CORE_API_KEY) registered at core.ac.uk/services/api -- skipped
silently, same as EZProxy without a cookie, when unset. Columbia's own
Academic Commons repository was considered as a fourth tier alongside
CORE.ac.uk but deliberately not built: it has no single-DOI lookup API
(OAI-PMH is harvest-only; its REST API's search shape is undocumented),
and its content is already harvested into CORE.ac.uk's own index, so a
dedicated integration would add real engineering cost for likely
redundant coverage. A response that isn't actually application/pdf (an
EZProxy login wall on an expired cookie) is never written to disk.

Pacing (paced_sleep) applies to the EZProxy tier only, per real usage
2026-09-02: its purpose is protecting the user's own Columbia account
from automated-abuse detection, which simply doesn't apply to OA/arXiv
downloads -- those hit diverse, unrelated hosts, not Columbia's proxy.
Pacing every tier uniformly (the original design) made OA-heavy batches
needlessly slow with no actual safety benefit.
"""
from __future__ import annotations

import html
import ipaddress
import re
import socket
import time
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

from discovery.discover_journal_articles.discovery import Work
from discovery.discover_journal_articles.http_utils import (
    FetchError,
    fetch_with_retries,
    is_pdf_response,
    is_valid_pdf_bytes,
    paced_sleep,
)

_UNPAYWALL_BASE = "https://api.unpaywall.org/v2"
_SEMANTIC_SCHOLAR_BASE = "https://api.semanticscholar.org/graph/v1/paper"
_CORE_BASE = "https://api.core.ac.uk/v3/search/works"
_EZPROXY_PREFIX = "https://ezproxy.cul.columbia.edu/login?url="

# Confirmed live 2026-09-03: a real CORE.ac.uk downloadUrl 403'd with
# requests' own default User-Agent -- a Cloudflare "Just a moment..."
# bot challenge, the same failure class already documented for EZProxy
# -- but succeeded with a real browser User-Agent string. Every download
# (not just CORE's) sends one now, since a default python-requests/x.x
# UA is exactly the kind of fingerprint this class of block targets.
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)


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


def try_semantic_scholar(doi: str | None) -> str | None:
    """A second, independent free OA-discovery source alongside
    Unpaywall -- real API, not scraping, no bot-detection risk. Added
    2026-09-02 since Unpaywall's own OA-repository coverage is
    incomplete; Semantic Scholar's crawl sometimes catches a green-OA
    copy Unpaywall hasn't indexed."""
    if not doi:
        return None
    try:
        response = fetch_with_retries(
            "GET", f"{_SEMANTIC_SCHOLAR_BASE}/DOI:{doi}", params={"fields": "openAccessPdf"},
        )
    except FetchError:
        return None
    if response.status_code != 200:
        return None
    return (response.json().get("openAccessPdf") or {}).get("url")


def try_core(doi: str | None, api_key: str | None) -> str | None:
    """A third, independent free OA-discovery source alongside Unpaywall
    and Semantic Scholar. Requires a free API key (CORE_API_KEY,
    registered at core.ac.uk/services/api) -- skipped entirely, same as
    EZProxy without a session cookie, when unset. Returns the first
    result's direct downloadUrl, falling back to the first entry in
    sourceFulltextUrls when downloadUrl is absent."""
    if not doi or not api_key:
        return None
    try:
        response = fetch_with_retries(
            "GET", _CORE_BASE, params={"q": f'doi:"{doi}"'}, headers={"Authorization": f"Bearer {api_key}"},
        )
    except FetchError:
        return None
    if response.status_code != 200:
        return None
    results = response.json().get("results") or []
    if not results:
        return None
    result = results[0]
    return result.get("downloadUrl") or next(iter(result.get("sourceFulltextUrls") or []), None)


def try_arxiv_url(arxiv_id: str | None) -> str | None:
    if not arxiv_id:
        return None
    return f"https://arxiv.org/pdf/{arxiv_id}.pdf"


def build_ezproxy_url(target_url: str) -> str:
    return f"{_EZPROXY_PREFIX}{target_url}"


# Both attribute orders occur in the wild (name before content, and the reverse).
_CITATION_PDF_META = (
    re.compile(r'''<meta[^>]+name=["']citation_pdf_url["'][^>]+content=["']([^"']+)["']''', re.IGNORECASE),
    re.compile(r'''<meta[^>]+content=["']([^"']+)["'][^>]+name=["']citation_pdf_url["']''', re.IGNORECASE),
)


def _citation_pdf_url(response) -> str | None:
    """The direct-PDF link a publisher landing page advertises in its <meta name="citation_pdf_url"> tag (the
    Highwire/Google Scholar convention, used by PLOS, BMJ, Springer and others), resolved against the page URL.
    OpenAlex often lists the landing page, not the PDF, as a paper's open-access location (confirmed live
    2026-11-11: PLOS ONE returned a normal 200 HTML page whose tag pointed at the PDF)."""
    try:
        text = response.text
    except Exception:
        return None
    if not isinstance(text, str):
        return None
    for pattern in _CITATION_PDF_META:
        match = pattern.search(text)
        if match:
            return urljoin(getattr(response, "url", "") or "", html.unescape(match.group(1)).strip())
    return None


_MAX_FOLLOW_REDIRECTS = 3


def _address_is_public(address) -> bool:
    return not (
        address.is_private or address.is_loopback or address.is_link_local or address.is_reserved
        or address.is_multicast or address.is_unspecified
    )


def _is_public_http_url(url: str) -> bool:
    """True only for an http(s) URL whose host is not localhost and whose every resolved address is public. The
    link comes from page content, so it is untrusted. A DNS answer can change between this check and the connect
    (rebinding); closing that needs pinning the connection to the validated address, which this does not do."""
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    if parsed.scheme not in ("http", "https") or not host or host == "localhost" or host.endswith(".localhost"):
        return False
    try:
        return _address_is_public(ipaddress.ip_address(host))
    except ValueError:
        pass  # a hostname: resolve it
    try:
        infos = socket.getaddrinfo(host, None)
    except OSError:
        return False
    try:
        return bool(infos) and all(_address_is_public(ipaddress.ip_address(info[4][0])) for info in infos)
    except ValueError:
        return False


def _fetch_followup_pdf(url: str) -> bytes | None:
    """Fetches a page-advertised PDF link without credentials, following at most _MAX_FOLLOW_REDIRECTS redirects
    by hand so every Location is re-validated (requests would otherwise follow them unchecked)."""
    for _ in range(_MAX_FOLLOW_REDIRECTS + 1):
        if not _is_public_http_url(url):
            return None
        try:
            response = fetch_with_retries(
                "GET", url, headers={"User-Agent": _USER_AGENT}, timeout=30, allow_redirects=False,
            )
        except FetchError:
            return None
        location = response.headers.get("Location")
        if response.status_code in (301, 302, 303, 307, 308) and location:
            url = urljoin(url, location)
            continue
        if response.status_code == 200 and is_pdf_response(response) and is_valid_pdf_bytes(response.content):
            return response.content
        return None
    return None


def _download(url: str, pace_per_hour: float, cookies: dict | None = None, _follow_landing: bool = True) -> bytes | None:
    paced_sleep(pace_per_hour)
    try:
        response = fetch_with_retries(
            "GET", url, cookies=cookies, headers={"User-Agent": _USER_AGENT}, timeout=30,
        )
    except FetchError:
        # Confirmed live 2026-09-02: a real "open access" URL (aeaweb.org)
        # returned a permanent 403 -- fetch_with_retries() raises rather
        # than returning a response for a non-retryable status. This tier
        # simply didn't work for this paper; the caller falls through to
        # the next tier / needs_manual, exactly like a non-PDF response.
        return None
    if response.status_code == 200 and not is_pdf_response(response) and _follow_landing and not cookies:
        # A landing page, not a PDF: follow its advertised PDF link once, without credentials. Never done when
        # cookies are in play (the EZProxy tier): the link is page-controlled and the session cookie must not
        # travel on a hop or its redirects. Bot-blocking publishers still fail here and fall through to the
        # next tier / needs_manual exactly as before.
        pdf_url = _citation_pdf_url(response)
        if pdf_url and pdf_url != url:
            return _fetch_followup_pdf(pdf_url)
        return None
    if response.status_code != 200 or not is_pdf_response(response) or not is_valid_pdf_bytes(response.content):
        return None
    return response.content


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
    deadline: float | None = None,
) -> AccessResult:
    """deadline, when given, is a time.monotonic() timestamp checked
    before each individual download attempt -- A.5's per-run budget was
    previously only checked between papers in discover.py's own loop, so
    one paper's full OA+arXiv+EZProxy chain under sustained 429s could
    still run well past the budget before the next check."""
    def _deadline_exhausted() -> bool:
        return deadline is not None and time.monotonic() >= deadline

    seen_urls: set[str] = set()
    for tier, url in _oa_candidates(work, mailto, core_api_key):
        if url in seen_urls:
            continue
        seen_urls.add(url)
        if _deadline_exhausted():
            return AccessResult(status="needs_manual")
        content = _download(url, 0)  # OA hosts carry none of the EZProxy account-safety risk
        if content:
            return AccessResult(status="fetched", content=content, tier=tier)

    arxiv_url = try_arxiv_url(work.arxiv_id)
    if arxiv_url and not _deadline_exhausted():
        content = _download(arxiv_url, 0)  # arXiv is a real API, not a scraping target
        if content:
            return AccessResult(status="fetched", content=content, tier="arxiv")

    if ezproxy_cookie and work.doi and not _deadline_exhausted():
        ezproxy_url = build_ezproxy_url(f"https://doi.org/{work.doi}")
        content = _download(ezproxy_url, pace_per_hour, cookies={"ezproxy": ezproxy_cookie})
        if content:
            return AccessResult(status="fetched", content=content, tier="ezproxy")

    return AccessResult(status="needs_manual")
