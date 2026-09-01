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
