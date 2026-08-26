"""
YouTube extractor — "video" entities.

Uses the official YouTube Data API v3 `search` + `videos` endpoints.
Requires an API key (`YOUTUBE_API_KEY` in .env) — YouTube's public API does
not offer meaningful unauthenticated access, unlike GitHub/HF. If no key is
configured, this extractor logs a clear warning and returns an empty list
rather than failing the whole pipeline (graceful degradation, spec section 6).
"""

from __future__ import annotations

import logging

from src.config import YOUTUBE_API_KEY
from src.http_client import get_json
from src.models.entity import Entity, EntityType, SourceRef

logger = logging.getLogger("ai_orbit.extractors.youtube")

SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"

SEARCH_QUERIES = [
    "AI agent tutorial",
    "large language model explained",
    "machine learning project walkthrough",
    "AI tool review 2026",
]


def _entity_from_video(item: dict, stats: dict | None) -> Entity:
    video_id = item["id"]["videoId"] if isinstance(item.get("id"), dict) else item.get("id")
    snippet = item.get("snippet", {})
    url = f"https://www.youtube.com/watch?v={video_id}"

    metadata = {
        "channel": snippet.get("channelTitle"),
        "published_at": snippet.get("publishedAt"),
    }
    if stats:
        metadata["view_count"] = int(stats.get("statistics", {}).get("viewCount", 0))
        metadata["like_count"] = int(stats.get("statistics", {}).get("likeCount", 0))
        metadata["duration"] = stats.get("contentDetails", {}).get("duration")

    return Entity(
        id=Entity.make_id(EntityType.VIDEO, video_id),
        entity_type=EntityType.VIDEO,
        name=snippet.get("title", "Untitled video"),
        description=(snippet.get("description", "") or "")[:500],
        url=url,
        categories=["video", "ai"],
        source=SourceRef(name="YouTube Data API v3", url=SEARCH_URL),
        metadata=metadata,
        raw_name=snippet.get("title"),
    )


def discover_videos(per_query: int = 10) -> list[Entity]:
    if not YOUTUBE_API_KEY:
        logger.warning("YOUTUBE_API_KEY not set — skipping video discovery. "
                        "Set it in .env to enable this source.")
        return []

    entities: list[Entity] = []
    seen_ids: set[str] = set()

    for query in SEARCH_QUERIES:
        params = {
            "part": "snippet",
            "q": query,
            "type": "video",
            "maxResults": per_query,
            "order": "relevance",
            "key": YOUTUBE_API_KEY,
        }
        data = get_json(SEARCH_URL, params=params)
        if not data or "items" not in data:
            logger.warning("YouTube search returned nothing for query=%s", query)
            continue

        video_ids = [
            it["id"]["videoId"] for it in data["items"]
            if isinstance(it.get("id"), dict) and it["id"].get("videoId")
        ]
        stats_by_id = _fetch_video_stats(video_ids)

        for item in data["items"]:
            vid = item["id"].get("videoId") if isinstance(item.get("id"), dict) else None
            if not vid:
                continue
            entity = _entity_from_video(item, stats_by_id.get(vid))
            if entity.id in seen_ids:
                continue
            seen_ids.add(entity.id)
            entities.append(entity)
        logger.info("YouTube query '%s' -> %d videos", query, len(data.get("items", [])))

    return entities


def _fetch_video_stats(video_ids: list[str]) -> dict[str, dict]:
    if not video_ids:
        return {}
    params = {
        "part": "statistics,contentDetails",
        "id": ",".join(video_ids),
        "key": YOUTUBE_API_KEY,
    }
    data = get_json(VIDEOS_URL, params=params)
    if not data or "items" not in data:
        return {}
    return {item["id"]: item for item in data["items"]}


def run() -> list[Entity]:
    videos = discover_videos()
    logger.info("YouTube extractor total: %d videos", len(videos))
    return videos
