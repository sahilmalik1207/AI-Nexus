"""
Classification stage.

Two jobs:
  1. Enrich `categories` with topic keywords extracted from name/description
     via a rule-based keyword matcher (fast, deterministic, explainable —
     preferred over an LLM call for a bulk 250-300 record batch where
     precision/latency/cost all favor rules).
  2. Tag entities as "New/Recently added" (spec category) based on
     recency signals already present in metadata (first_seen, published_at,
     last_updated) — anything within the trailing RECENT_WINDOW_DAYS.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.models.entity import Entity

RECENT_WINDOW_DAYS = 30

KEYWORD_CATEGORY_MAP = {
    "agent": "agents",
    "rag": "retrieval-augmented-generation",
    "vector": "vector-search",
    "speech": "speech",
    "voice": "speech",
    "image": "computer-vision",
    "vision": "computer-vision",
    "video": "video",
    "robot": "robotics",
    "chat": "conversational-ai",
    "assistant": "conversational-ai",
    "fine-tun": "fine-tuning",
    "reasoning": "reasoning",
    "multimodal": "multimodal",
    "code": "code-generation",
}

_RECENCY_FIELDS = ("published_at", "last_updated", "first_seen")


def _extract_keyword_categories(entity: Entity) -> set[str]:
    haystack = f"{entity.name} {entity.description}".lower()
    return {tag for kw, tag in KEYWORD_CATEGORY_MAP.items() if kw in haystack}


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        # handle both 'Z' suffix and offset-aware ISO strings
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _is_recent(entity: Entity) -> bool:
    cutoff = datetime.now(timezone.utc) - timedelta(days=RECENT_WINDOW_DAYS)
    for field in _RECENCY_FIELDS:
        dt = _parse_dt(entity.metadata.get(field)) or _parse_dt(getattr(entity, field, None))
        if dt and dt >= cutoff:
            return True
    return False


def classify_entity(entity: Entity) -> Entity:
    entity.categories = sorted(set(entity.categories) | _extract_keyword_categories(entity))
    if _is_recent(entity):
        entity.categories = sorted(set(entity.categories) | {"new"})
    return entity


def classify_all(entities: list[Entity]) -> list[Entity]:
    return [classify_entity(e) for e in entities]
