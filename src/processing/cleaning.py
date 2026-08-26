"""
Cleaning & Normalization stage (spec: Cleaning -> Normalization).

Two responsibilities, kept separate for testability:
  1. Sanitize free text pulled from HTML/RSS (strip tags, collapse
     whitespace, drop control characters).
  2. Normalize URLs to a consistent canonical form so that dedup in the
     next stage can compare them reliably (same URL written two ways
     should not become two entities).
"""

from __future__ import annotations

import re
from urllib.parse import urlparse, urlunparse

from src.models.entity import Entity

_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")
_TRACKING_PARAMS = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "ref", "fbclid"}


def sanitize_text(raw: str) -> str:
    """Strip HTML tags, collapse whitespace, trim. Never raises on bad input."""
    if not raw:
        return ""
    no_tags = _TAG_RE.sub(" ", raw)
    collapsed = _WHITESPACE_RE.sub(" ", no_tags)
    return collapsed.strip()


def normalize_url(raw_url: str) -> str:
    """
    Canonicalize a URL:
      - lowercase scheme + host
      - drop trailing slash (except bare domain)
      - strip known tracking query params
      - drop fragments
    """
    if not raw_url:
        return ""
    try:
        parsed = urlparse(raw_url.strip())
    except ValueError:
        return raw_url.strip()

    scheme = (parsed.scheme or "https").lower()
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip("/") or ""

    if parsed.query:
        kept = [
            kv for kv in parsed.query.split("&")
            if kv.split("=")[0] not in _TRACKING_PARAMS
        ]
        query = "&".join(kept)
    else:
        query = ""

    return urlunparse((scheme, netloc, path, "", query, ""))


def clean_entity(entity: Entity) -> Entity:
    """Apply text sanitization + URL normalization in place (returns same object)."""
    entity.name = sanitize_text(entity.name)
    entity.description = sanitize_text(entity.description)
    entity.url = normalize_url(entity.url)
    entity.categories = sorted({c.strip().lower() for c in entity.categories if c and c.strip()})
    return entity


def clean_all(entities: list[Entity]) -> list[Entity]:
    return [clean_entity(e) for e in entities if e.name]  # drop entities with no name at all
