"""
News/RSS extractor — "news" entities.

Uses `feedparser` against public RSS feeds of well-known AI/tech outlets.
RSS is the API-first equivalent for news: no scraping of rendered HTML,
just structured feed data the publishers themselves expose for syndication.

NOTE ON NETWORK: this module makes plain HTTP GETs via feedparser, which
needs outbound access to each feed's domain. In restrictive sandboxes this
may be blocked; that's a network-policy issue, not a code issue — see
README "Environment & Network Notes".
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import feedparser

from src.models.entity import Entity, EntityType, SourceRef

logger = logging.getLogger("ai_orbit.extractors.news")

FEEDS = {
    "TechCrunch AI": "https://techcrunch.com/category/artificial-intelligence/feed/",
    "VentureBeat AI": "https://venturebeat.com/category/ai/feed/",
    "The Verge AI": "https://www.theverge.com/ai-artificial-intelligence/rss/index.xml",
    "MIT Technology Review AI": "https://www.technologyreview.com/topic/artificial-intelligence/feed",
}


def _entity_from_feed_item(entry: dict, feed_name: str, feed_url: str) -> Entity:
    link = entry.get("link", "")
    title = entry.get("title", "Untitled")
    published = entry.get("published", "") or entry.get("updated", "")
    summary = (entry.get("summary", "") or "")[:500]

    return Entity(
        id=Entity.make_id(EntityType.NEWS, link or f"{feed_name}:{title}"),
        entity_type=EntityType.NEWS,
        name=title,
        description=summary,
        url=link,
        categories=["news", "ai-industry"],
        source=SourceRef(name=feed_name, url=feed_url),
        metadata={
            "published_at": published,
            "publisher": feed_name,
        },
        raw_name=title,
    )


def discover_news(per_feed: int = 15) -> list[Entity]:
    entities: list[Entity] = []
    seen_ids: set[str] = set()
    for feed_name, feed_url in FEEDS.items():
        try:
            parsed = feedparser.parse(feed_url)
        except Exception as exc:  # feedparser rarely raises but be defensive
            logger.warning("Failed to parse feed %s: %s", feed_name, exc)
            continue

        if parsed.bozo and not parsed.entries:
            logger.warning("Feed %s unreachable or malformed, skipping", feed_name)
            continue

        for entry in parsed.entries[:per_feed]:
            entity = _entity_from_feed_item(entry, feed_name, feed_url)
            if entity.id in seen_ids or not entity.url:
                continue
            seen_ids.add(entity.id)
            entities.append(entity)
        logger.info("Feed '%s' -> %d items", feed_name, min(len(parsed.entries), per_feed))
    return entities


def run() -> list[Entity]:
    news = discover_news()
    logger.info("News extractor total: %d articles", len(news))
    return news
