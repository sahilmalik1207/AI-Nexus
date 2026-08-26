"""
Collections extractor — "collection" entities.

A "collection" in the AI Orbit taxonomy is a curated group of AI resources.
GitHub's "awesome list" convention (repos like `awesome-llm`,
`awesome-mcp-servers`) is exactly this, community-curated and
API-discoverable — so we reuse the same GitHub Search API as the
repository/MCP extractor rather than inventing a new source.
"""

from __future__ import annotations

import logging

from src.extraction.github_extractor import _run_queries
from src.models.entity import Entity, EntityType

logger = logging.getLogger("ai_orbit.extractors.collections")

COLLECTION_QUERIES = [
    "awesome ai in:name",
    "awesome llm in:name",
    "awesome machine-learning in:name",
    "awesome mcp in:name",
]


def discover_collections() -> list[Entity]:
    entities = _run_queries(COLLECTION_QUERIES, EntityType.COLLECTION, per_query=15)
    logger.info("Collections extractor total: %d collections", len(entities))
    return entities


def run() -> list[Entity]:
    return discover_collections()
