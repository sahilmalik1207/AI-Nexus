"""
GitHub extractor.

Covers two spec categories from one API:
  - "repository" entities: general AI/ML open-source repos discovered via
    GitHub Code Search-style queries against the Search API.
  - "mcp" entities: repos that are specifically MCP (Model Context Protocol)
    servers/tools, detected via topic + name/description heuristics.

API-first, not scraping: uses GitHub's public REST Search API
(`/search/repositories`) with an optional bearer token for higher rate
limits (5000/hr vs 60/hr unauthenticated).
"""

from __future__ import annotations

import logging
from typing import Iterable

from src.config import GITHUB_TOKEN
from src.http_client import get_json
from src.models.entity import Entity, EntityType, SourceRef

logger = logging.getLogger("ai_orbit.extractors.github")

SEARCH_URL = "https://api.github.com/search/repositories"

# Queries chosen to surface real, currently-active AI repos across different
# niches, rather than one giant generic "AI" query that just returns the
# same top-10 mega-repos repeatedly.
REPO_QUERIES = [
    "topic:artificial-intelligence stars:>500",
    "topic:machine-learning stars:>1000",
    "topic:llm stars:>200",
    "topic:agent-framework",
    "topic:computer-vision stars:>500",
]

MCP_QUERIES = [
    "topic:mcp-server",
    "topic:model-context-protocol",
    '"model context protocol" server in:name,description',
]


def _headers() -> dict:
    headers = {"Accept": "application/vnd.github+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return headers


# Best-effort language -> package-manager mapping, used to populate MCP
# servers' "installation methods" / "runtime requirements" metadata (spec
# 4.2) without an extra API call per repo. This is a heuristic based on
# GitHub's reported primary language, documented as such rather than
# presented as ground truth scraped from each repo's actual install docs.
_LANGUAGE_INSTALL_HINTS = {
    "Python": {"install_method": "pip install (see repository README/pyproject.toml)", "runtime": "Python 3.10+"},
    "TypeScript": {"install_method": "npm install / npx (see repository README/package.json)", "runtime": "Node.js 18+"},
    "JavaScript": {"install_method": "npm install / npx (see repository README/package.json)", "runtime": "Node.js 18+"},
    "Go": {"install_method": "go install (see repository README/go.mod)", "runtime": "Go 1.21+"},
    "Rust": {"install_method": "cargo install (see repository README/Cargo.toml)", "runtime": "Rust (stable toolchain)"},
    "Java": {"install_method": "Maven/Gradle build (see repository README)", "runtime": "JDK 17+"},
}
_DEFAULT_INSTALL_HINT = {"install_method": "see repository README for installation instructions", "runtime": "unspecified (see repository README)"}


def _entity_from_repo(item: dict, entity_type: EntityType) -> Entity:
    full_name = item.get("full_name", "")
    canonical_key = f"github.com/{full_name}"
    language = item.get("language")

    metadata = {
        "stars": item.get("stargazers_count", 0),
        "language": language,
        "last_updated": item.get("updated_at"),
        "owner": (item.get("owner") or {}).get("login"),
        "full_name": full_name,
        "forks": item.get("forks_count", 0),
        "open_issues": item.get("open_issues_count", 0),
    }

    if entity_type == EntityType.MCP:
        # Spec 4.2 requires "Installation methods and runtime requirements"
        # for MCP servers specifically.
        hint = _LANGUAGE_INSTALL_HINTS.get(language, _DEFAULT_INSTALL_HINT)
        metadata["installation_method"] = hint["install_method"]
        metadata["runtime_requirements"] = hint["runtime"]

    return Entity(
        id=Entity.make_id(entity_type, canonical_key),
        entity_type=entity_type,
        name=item.get("name", full_name),
        description=(item.get("description") or "")[:500],
        url=item.get("html_url", ""),
        categories=(item.get("topics") or [])[:10],
        source=SourceRef(name="GitHub API", url="https://api.github.com/search/repositories"),
        metadata=metadata,
        raw_name=full_name,
    )


def _run_queries(queries: Iterable[str], entity_type: EntityType, per_query: int = 20) -> list[Entity]:
    entities: list[Entity] = []
    seen_ids: set[str] = set()
    for q in queries:
        params = {"q": q, "sort": "stars", "order": "desc", "per_page": per_query}
        data = get_json(SEARCH_URL, params=params, headers=_headers())
        if not data or "items" not in data:
            logger.warning("GitHub query returned nothing: %s", q)
            continue
        for item in data["items"]:
            entity = _entity_from_repo(item, entity_type)
            if entity.id in seen_ids:
                continue
            seen_ids.add(entity.id)
            entities.append(entity)
        logger.info("GitHub query '%s' -> %d items", q, len(data.get("items", [])))
    return entities


def discover_repositories() -> list[Entity]:
    """General AI/ML repositories -> entity_type = repository."""
    return _run_queries(REPO_QUERIES, EntityType.REPOSITORY)


def discover_mcp_servers() -> list[Entity]:
    """MCP-specific repos -> entity_type = mcp."""
    return _run_queries(MCP_QUERIES, EntityType.MCP)


def run() -> list[Entity]:
    repos = discover_repositories()
    mcps = discover_mcp_servers()
    logger.info("GitHub extractor total: %d repositories, %d MCP servers", len(repos), len(mcps))
    return repos + mcps
