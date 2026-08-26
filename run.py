#!/usr/bin/env python3
"""
AI Orbit Data Ingestion Pipeline — orchestrator.

Runs the full pipeline exactly as specified:
  Discovery -> Extraction -> Cleaning -> Normalization -> Deduplication ->
  Classification -> Relationship Mapping -> Validation

Usage:
    python run.py                  # full run, writes data/entities.json etc.
    python run.py --skip youtube    # skip one or more sources (comma-separated)
    python run.py --verbose         # debug-level logging

Each extractor is isolated with a try/except: if one source is down or
misconfigured (e.g. missing API key), the pipeline logs it and continues
with everything else, rather than crashing the whole run. This is a direct
requirement of spec section 6 ("Resilience: Graceful degradation and
logging for missing fields").
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from datetime import datetime, timezone

from src.config import ENTITIES_JSON, PIPELINE_LOG, RELATIONSHIPS_JSON, RUN_REPORT_JSON
from src.models.entity import Entity, Relationship
from src.processing.classification import classify_all
from src.processing.cleaning import clean_all
from src.processing.deduplication import deduplicate
from src.processing.relationships import extract_relationships
from src.processing.validation import validate_entities, validate_relationships

logger = logging.getLogger("ai_orbit.run")

EXTRACTORS = {
    "github": ("src.extraction.github_extractor", "run"),
    "huggingface": ("src.extraction.huggingface_extractor", "run"),
    "news": ("src.extraction.news_extractor", "run"),
    "youtube": ("src.extraction.youtube_extractor", "run"),
    "tasks": ("src.extraction.tasks_extractor", "run"),
    "collections": ("src.extraction.collections_extractor", "run"),
    "curated": ("src.extraction.curated_extractor", "run"),
}


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(PIPELINE_LOG, mode="a"),
        ],
    )


def run_discovery_and_extraction(skip: set[str]) -> list[Entity]:
    """Discovery + Extraction stages. Each source isolated so one failure
    never takes down the others."""
    all_entities: list[Entity] = []
    source_counts: dict[str, int] = {}

    for source_name, (module_path, func_name) in EXTRACTORS.items():
        if source_name in skip:
            logger.info("Skipping source: %s (--skip)", source_name)
            continue
        try:
            import importlib
            module = importlib.import_module(module_path)
            extractor_fn = getattr(module, func_name)
            t0 = time.time()
            entities = extractor_fn()
            elapsed = time.time() - t0
            all_entities.extend(entities)
            source_counts[source_name] = len(entities)
            logger.info("[%s] extracted %d entities in %.1fs", source_name, len(entities), elapsed)
        except Exception:
            logger.exception("Extractor '%s' failed — continuing without it", source_name)
            source_counts[source_name] = 0

    return all_entities, source_counts


def run_pipeline(skip: set[str]) -> dict:
    started_at = datetime.now(timezone.utc).isoformat()
    logger.info("=== AI Orbit pipeline run starting ===")

    # 1-2: Discovery + Extraction
    raw_entities, source_counts = run_discovery_and_extraction(skip)
    logger.info("Total raw entities from all sources: %d", len(raw_entities))

    # 3-4: Cleaning + Normalization
    cleaned = clean_all(raw_entities)
    logger.info("After cleaning: %d entities", len(cleaned))

    # 5: Deduplication / Entity Resolution
    deduped = deduplicate(cleaned)
    logger.info("After deduplication: %d entities", len(deduped))

    # 6: Classification
    classified = classify_all(deduped)

    # 7: Relationship Mapping (run before final validation so relationships
    #    can be checked against the same entity id set)
    relationships = extract_relationships(classified)

    # 8: Validation (entities, then relationships against valid entity ids)
    valid_entities, quarantined_entities = validate_entities(classified)
    valid_ids = {e.id for e in valid_entities}
    valid_relationships, quarantined_relationships = validate_relationships(relationships, valid_ids)

    # --- Persist outputs ---
    ENTITIES_JSON.write_text(
        json.dumps([e.model_dump() for e in valid_entities], indent=2, default=str), encoding="utf-8"
    )
    RELATIONSHIPS_JSON.write_text(
        json.dumps([r.model_dump() for r in valid_relationships], indent=2, default=str), encoding="utf-8"
    )

    by_type: dict[str, int] = {}
    for e in valid_entities:
        by_type[e.entity_type.value] = by_type.get(e.entity_type.value, 0) + 1

    report = {
        "started_at": started_at,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "source_counts_raw": source_counts,
        "raw_entity_count": len(raw_entities),
        "final_entity_count": len(valid_entities),
        "final_relationship_count": len(valid_relationships),
        "entities_by_type": by_type,
        "quarantined_entities": len(quarantined_entities),
        "quarantined_relationships": len(quarantined_relationships),
        "quarantine_detail": {
            "entities": quarantined_entities[:20],  # cap for readability
            "relationships": quarantined_relationships[:20],
        },
    }
    RUN_REPORT_JSON.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    logger.info("=== Pipeline run complete: %d entities, %d relationships written ===",
                len(valid_entities), len(valid_relationships))
    logger.info("Entities by type: %s", by_type)
    return report


def main():
    parser = argparse.ArgumentParser(description="AI Orbit Data Ingestion Pipeline")
    parser.add_argument("--skip", default="", help="Comma-separated source names to skip, e.g. youtube,news")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    _setup_logging(args.verbose)
    skip = {s.strip() for s in args.skip.split(",") if s.strip()}
    report = run_pipeline(skip)
    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
