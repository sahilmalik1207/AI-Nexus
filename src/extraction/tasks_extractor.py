"""
Tasks extractor — "task" entities.

Source: Hugging Face's public task taxonomy (`/api/tasks`), which lists the
canonical set of ML tasks (text-generation, image-segmentation, etc.) along
with a human description of what each accomplishes. This is a genuine
API-first source for "what users can accomplish with AI" (spec category:
Tasks) rather than a hand-written list, since HF's taxonomy is the de facto
industry-standard task ontology.
"""

from __future__ import annotations

import logging

from src.http_client import get_json
from src.models.entity import Entity, EntityType, SourceRef

logger = logging.getLogger("ai_orbit.extractors.tasks")

TASKS_URL = "https://huggingface.co/api/tasks"


def _entity_from_task(task_key: str, task_data: dict) -> Entity:
    summary = task_data.get("summary", "") or ""
    label = task_data.get("label", task_key.replace("-", " ").title())
    canonical_key = f"hf-task:{task_key}"

    return Entity(
        id=Entity.make_id(EntityType.TASK, canonical_key),
        entity_type=EntityType.TASK,
        name=label,
        description=summary[:500],
        url=f"https://huggingface.co/tasks/{task_key}",
        categories=["task", task_key],
        source=SourceRef(name="Hugging Face Task Taxonomy", url=TASKS_URL),
        metadata={
            "task_key": task_key,
            "modality": task_data.get("modality"),
        },
        raw_name=label,
    )


def discover_tasks(limit: int = 40) -> list[Entity]:
    data = get_json(TASKS_URL)
    if not data:
        logger.warning("Hugging Face task taxonomy unreachable — returning no task entities")
        return []

    entities: list[Entity] = []
    # The API returns a dict keyed by task slug -> metadata.
    for task_key, task_data in list(data.items())[:limit]:
        if not isinstance(task_data, dict):
            continue
        entities.append(_entity_from_task(task_key, task_data))

    logger.info("Tasks extractor total: %d tasks", len(entities))
    return entities


def run() -> list[Entity]:
    return discover_tasks()
