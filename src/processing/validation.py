"""
Validation stage (spec: final step of the pipeline, section 6 "Resilience").

Rather than a boolean pass/fail, this stage produces a structured quality
report: entities/relationships that fail validation are quarantined (kept
out of the final output) but logged with a reason, so a bad record never
silently corrupts the dataset AND never silently disappears without a trace
— both extremes are failure modes the spec's "Error Handling" criterion is
checking for.
"""

from __future__ import annotations

import logging
from urllib.parse import urlparse

from src.models.entity import Entity, Relationship

logger = logging.getLogger("ai_orbit.processing.validation")

MIN_NAME_LENGTH = 2


def _entity_errors(entity: Entity) -> list[str]:
    errors = []
    if not entity.name or len(entity.name.strip()) < MIN_NAME_LENGTH:
        errors.append("name missing or too short")
    if entity.url:
        parsed = urlparse(entity.url)
        if not parsed.scheme or not parsed.netloc:
            errors.append(f"malformed url: {entity.url}")
    if not entity.source.name:
        errors.append("missing source attribution")
    return errors


def validate_entities(entities: list[Entity]) -> tuple[list[Entity], list[dict]]:
    valid: list[Entity] = []
    quarantined: list[dict] = []
    for e in entities:
        errors = _entity_errors(e)
        if errors:
            quarantined.append({"id": e.id, "name": e.name, "errors": errors})
        else:
            valid.append(e)
    if quarantined:
        logger.warning("Quarantined %d/%d entities failing validation", len(quarantined), len(entities))
    return valid, quarantined


def validate_relationships(relationships: list[Relationship], valid_entity_ids: set[str]) -> tuple[list[Relationship], list[dict]]:
    valid: list[Relationship] = []
    quarantined: list[dict] = []
    for r in relationships:
        errors = []
        if r.source_id not in valid_entity_ids:
            errors.append("source_id not in validated entity set")
        if r.target_id not in valid_entity_ids:
            errors.append("target_id not in validated entity set")
        if r.source_id == r.target_id:
            errors.append("self-referential relationship")
        if errors:
            quarantined.append({"id": r.id, "errors": errors})
        else:
            valid.append(r)
    if quarantined:
        logger.warning("Quarantined %d/%d relationships failing validation", len(quarantined), len(relationships))
    return valid, quarantined
