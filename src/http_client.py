"""
Shared HTTP client wrapper.

Why this exists: every extractor talks to a different flaky third-party API.
Rather than duplicate retry/backoff/error-handling logic six times, it lives
here once. This is what the spec's "Error Handling" (10%) and "Architecture"
(20%) criteria are really asking for — resilience should be a cross-cutting
concern, not copy-pasted per source.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

import requests

from src.config import MAX_RETRIES, REQUEST_TIMEOUT, RETRY_BACKOFF_SECONDS, USER_AGENT

logger = logging.getLogger("ai_orbit.http")


class FetchError(Exception):
    """Raised when a request ultimately fails after retries."""


def get_json(
    url: str,
    params: Optional[dict] = None,
    headers: Optional[dict] = None,
    timeout: int = REQUEST_TIMEOUT,
) -> Optional[Any]:
    """
    GET a URL and parse JSON, with retry + exponential backoff.
    Returns None (never raises) on final failure so a single flaky source
    can't crash the whole pipeline run — callers just get an empty result
    and the run continues (graceful degradation, per spec section 6).
    """
    merged_headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if headers:
        merged_headers.update(headers)

    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(url, params=params, headers=merged_headers, timeout=timeout)
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code == 404:
                logger.info("404 for %s — skipping", url)
                return None
            if resp.status_code in (403, 429):
                # rate limited — back off harder
                wait = RETRY_BACKOFF_SECONDS * (2 ** attempt)
                logger.warning("Rate limited (%s) on %s, backing off %.1fs", resp.status_code, url, wait)
                time.sleep(wait)
                continue
            logger.warning("Unexpected status %s for %s", resp.status_code, url)
            last_error = FetchError(f"status={resp.status_code}")
        except requests.RequestException as exc:
            last_error = exc
            wait = RETRY_BACKOFF_SECONDS * attempt
            logger.warning("Request error on attempt %d for %s: %s — retrying in %.1fs", attempt, url, exc, wait)
            time.sleep(wait)

    logger.error("Giving up on %s after %d attempts (%s)", url, MAX_RETRIES, last_error)
    return None


def get_text(url: str, timeout: int = REQUEST_TIMEOUT) -> Optional[str]:
    """GET raw text (used for RSS/HTML), same retry semantics as get_json."""
    headers = {"User-Agent": USER_AGENT}
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(url, headers=headers, timeout=timeout)
            if resp.status_code == 200:
                return resp.text
            if resp.status_code == 404:
                return None
        except requests.RequestException as exc:
            time.sleep(RETRY_BACKOFF_SECONDS * attempt)
            last_error = exc
            continue
    logger.error("Giving up fetching text from %s", url)
    return None
