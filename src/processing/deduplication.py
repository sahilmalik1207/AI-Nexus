"""
Deduplication / Entity Resolution stage.

Three-tier strategy, cheapest checks first (spec section 6: "Entity
Resolution: Canonicalizing name variations e.g. 'OpenAI' vs 'Open AI'"):

  1. Exact ID match — two extractors produced the *same* deterministic
     UUID (same entity_type + canonical key). Guaranteed duplicate, merge.
  2. Exact normalized-URL match within the same entity_type — different
     canonical key inputs but same underlying resource.
  3. Fuzzy name match within the same entity_type — catches spelling/
     spacing/casing variants ("OpenAI" vs "Open AI" vs "open-ai") using
     a lightweight, dependency-free similarity ratio (difflib), with a
     conservative threshold to avoid false-positive merges.

When two records are judged duplicates, we keep the one with richer
metadata (more populated fields) and merge categories from both, rather
than arbitrarily keeping "whichever came first".
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from difflib import SequenceMatcher

from src.models.entity import Entity

logger = logging.getLogger("ai_orbit.processing.dedup")

FUZZY_MATCH_THRESHOLD = 0.92


def _normalize_name_for_matching(name: str) -> str:
    """Lowercase, strip punctuation/whitespace so 'Open AI' == 'OpenAI' == 'open-ai'."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


def _richness_score(entity: Entity) -> int:
    """More populated fields = richer record, preferred when merging duplicates."""
    score = len(entity.description) + len(entity.metadata) * 10 + len(entity.categories) * 2
    return score


def _merge(keep: Entity, drop: Entity) -> Entity:
    keep.categories = sorted(set(keep.categories) | set(drop.categories))
    # fill any metadata keys missing on the kept record from the dropped one
    for k, v in drop.metadata.items():
        keep.metadata.setdefault(k, v)
    if not keep.description and drop.description:
        keep.description = drop.description
    return keep


def deduplicate(entities: list[Entity]) -> list[Entity]:
    # --- Tier 1: exact ID collision ---
    by_id: dict[str, Entity] = {}
    for e in entities:
        if e.id in by_id:
            by_id[e.id] = _merge(
                *sorted([by_id[e.id], e], key=_richness_score, reverse=True)
            )
        else:
            by_id[e.id] = e
    stage1 = list(by_id.values())
    logger.info("Dedup tier 1 (exact id): %d -> %d", len(entities), len(stage1))

    # --- Tier 2: exact normalized-URL match within same entity_type ---
    by_url_key: dict[tuple, Entity] = {}
    for e in stage1:
        key = (e.entity_type, e.url) if e.url else None
        if key and key in by_url_key:
            by_url_key[key] = _merge(
                *sorted([by_url_key[key], e], key=_richness_score, reverse=True)
            )
        elif key:
            by_url_key[key] = e
        else:
            # no url to key on; keep as its own unique bucket via its id
            by_url_key[("__no_url__", e.id)] = e
    stage2 = list(by_url_key.values())
    logger.info("Dedup tier 2 (url match): %d -> %d", len(stage1), len(stage2))

    # --- Tier 3: fuzzy name match within same entity_type ---
    buckets: dict[str, list[Entity]] = defaultdict(list)
    for e in stage2:
        buckets[e.entity_type].append(e)

    final: list[Entity] = []
    for etype, group in buckets.items():
        merged_flags = [False] * len(group)
        for i in range(len(group)):
            if merged_flags[i]:
                continue
            current = group[i]
            norm_i = _normalize_name_for_matching(current.name)
            for j in range(i + 1, len(group)):
                if merged_flags[j]:
                    continue
                norm_j = _normalize_name_for_matching(group[j].name)
                ratio = SequenceMatcher(None, norm_i, norm_j).ratio()
                if ratio >= FUZZY_MATCH_THRESHOLD:
                    winner, loser = sorted([current, group[j]], key=_richness_score, reverse=True)
                    current = _merge(winner, loser)
                    merged_flags[j] = True
            final.append(current)

    logger.info("Dedup tier 3 (fuzzy name): %d -> %d", len(stage2), len(final))
    return final
