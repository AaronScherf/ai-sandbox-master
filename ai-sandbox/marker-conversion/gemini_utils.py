#!/usr/bin/env python3
"""
gemini_utils.py
Small, dependency-free helpers shared by every local (no-GCP-VM) script
that calls the Gemini Developer API -- describe_images.py,
transcribe_notes.py, and any future ones. No torch/marker/pypdf/
google-genai import at module load time, matching chapter_index.py/
page_markers.py: only get_gemini_client() touches google-genai, and only
when actually called.
"""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

_RETRY_DELAY_PATTERNS = (
    re.compile(r"retryDelay[^0-9]*(\d+(?:\.\d+)?)s", re.IGNORECASE),
    re.compile(r"retry in (\d+(?:\.\d+)?)s", re.IGNORECASE),
)


def extract_retry_delay_seconds(error) -> float | None:
    """
    Pulls the API's own suggested wait time out of a 429 RESOURCE_EXHAUSTED
    error, e.g. "'retryDelay': '52s'" or "Please retry in 52.6s." -- a real
    quota-window reset (per-minute limits) is typically 40-60s, far longer
    than any fixed backoff schedule would guess, so honoring it avoids
    burning through all retries before the quota actually clears.
    """
    text = str(error)
    for pattern in _RETRY_DELAY_PATTERNS:
        match = pattern.search(text)
        if match:
            return float(match.group(1))
    return None


def call_with_retries(fn, retries: int = 3, backoff_seconds: float = 5.0, max_wait_seconds: float = 90.0):
    last_err: Exception = RuntimeError("no attempts were made")
    for attempt in range(retries):
        try:
            return fn()
        except Exception as err:
            last_err = err
            if attempt < retries - 1:
                suggested = extract_retry_delay_seconds(err)
                wait = min(suggested + 1, max_wait_seconds) if suggested is not None else backoff_seconds * (attempt + 1)
                print(f"WARNING: Gemini call failed (attempt {attempt + 1}/{retries}): {err}. Retrying in {wait:.0f}s.")
                time.sleep(wait)
    raise last_err


def load_json_cache(path: str) -> dict:
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save_json_cache(path: str, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def load_dotenv_override() -> None:
    """
    Loads ai-sandbox/.env (the parent of this script's own directory),
    with override=True so .env stays authoritative over a stale ambient
    environment variable (a leftover Windows User/Machine-level
    GEMINI_API_KEY, or one set earlier in the same shell session) --
    without override=True, load_dotenv() silently leaves such a variable
    in place, which looks identical to .env just not being read at all.
    """
    try:
        from dotenv import load_dotenv
        load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env", override=True)
    except ImportError:
        print("WARNING: python-dotenv not installed (pip install python-dotenv); "
              "relying on GEMINI_API_KEY already being set in the environment.")


def get_gemini_client():
    """
    Builds a Gemini Developer API client from GEMINI_API_KEY in the
    environment (call load_dotenv_override() first so .env is picked
    up). Prints a clear error and returns None if the key or the SDK is
    missing -- callers should treat None as "cannot proceed."
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY not set (checked the environment and ../.env). "
              "Get a key at aistudio.google.com/apikey and add it to ai-sandbox/.env.")
        return None
    try:
        from google import genai
    except ImportError:
        print("ERROR: google-genai is not installed. Run: pip install google-genai")
        return None
    return genai.Client(api_key=api_key)
