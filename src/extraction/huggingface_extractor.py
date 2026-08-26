"""
Hugging Face extractor — "model" entities.

Uses the public Hub API (`https://huggingface.co/api/models`), which needs
no auth for read access to public model listings. We pull across a spread
of pipeline tags (text-generation, text-to-image, etc.) so the sample
reflects real diversity in modalities, not just whatever is globally
trending this week.
"""

from __future__ import annotations

import logging

from src.config import HF_TOKEN
from src.http_client import get_json
from src.models.entity import Entity, EntityType, SourceRef

logger = logging.getLogger("ai_orbit.extractors.huggingface")

MODELS_URL = "https://huggingface.co/api/models"

# Pipeline tags chosen to cover distinct modalities, so "modalities" metadata
# in the final dataset is actually varied (spec 4.2: Models -> modalities).
PIPELINE_TAGS = [
    "text-generation",
    "text-to-image",
    "automatic-speech-recognition",
    "text-to-speech",
    "image-classification",
    "text-classification",
]

TAG_TO_MODALITY = {
    "text-generation": ["text"],
    "text-to-image": ["text", "image"],
    "automatic-speech-recognition": ["audio", "text"],
    "text-to-speech": ["text", "audio"],
    "image-classification": ["image"],
    "text-classification": ["text"],
}


def _headers() -> dict:
    headers = {}
    if HF_TOKEN:
        headers["Authorization"] = f"Bearer {HF_TOKEN}"
    return headers


def _entity_from_model(item: dict, pipeline_tag: str) -> Entity:
    model_id = item.get("id") or item.get("modelId", "")
    canonical_key = f"huggingface.co/{model_id}"
    author = model_id.split("/")[0] if "/" in model_id else None
    return Entity(
        id=Entity.make_id(EntityType.MODEL, canonical_key),
        entity_type=EntityType.MODEL,
        name=model_id,
        description=f"{pipeline_tag.replace('-', ' ').title()} model on Hugging Face Hub",
        url=f"https://huggingface.co/{model_id}",
        categories=(item.get("tags") or [])[:10],
        source=SourceRef(name="Hugging Face Hub API", url=MODELS_URL),
        metadata={
            "license": next((t.split(":", 1)[1] for t in (item.get("tags") or []) if t.startswith("license:")), None),
            "modalities": TAG_TO_MODALITY.get(pipeline_tag, []),
            "provider": author,
            "downloads": item.get("downloads", 0),
            "likes": item.get("likes", 0),
            "pipeline_tag": pipeline_tag,
        },
        raw_name=model_id,
    )


def discover_models(per_tag: int = 15) -> list[Entity]:
    entities: list[Entity] = []
    seen_ids: set[str] = set()
    for tag in PIPELINE_TAGS:
        params = {"pipeline_tag": tag, "sort": "downloads", "direction": -1, "limit": per_tag}
        data = get_json(MODELS_URL, params=params, headers=_headers())
        if not data:
            logger.warning("Hugging Face query returned nothing for tag=%s", tag)
            continue
        for item in data:
            entity = _entity_from_model(item, tag)
            if entity.id in seen_ids:
                continue
            seen_ids.add(entity.id)
            entities.append(entity)
        logger.info("HF tag '%s' -> %d models", tag, len(data))
    return entities


def run() -> list[Entity]:
    models = discover_models()
    logger.info("Hugging Face extractor total: %d models", len(models))
    return models
