"""
Core data models for the AI Orbit ecosystem graph.

Design notes
------------
- `Entity` is the canonical, storage-ready representation. Every record that
  leaves the pipeline (post validation) conforms to this shape.
- Domain-specific extra fields (stars, license, founding_year, etc.) live in
  `metadata`, keeping the top-level schema stable while still satisfying the
  "Specialized Metadata" requirement in the spec.
- IDs are deterministic (UUIDv5) rather than random (UUIDv4) so that the same
  logical entity (e.g. the GitHub repo "openai/whisper") always resolves to
  the same id across pipeline re-runs. This is what makes idempotent
  re-ingestion and downstream relationship linking possible without a
  database round-trip.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl, field_validator

# Fixed namespace for deterministic UUIDv5 generation. Any valid UUID works;
# what matters is that it never changes across runs.
NAMESPACE_AI_ORBIT = uuid.UUID("6f1b3a2e-8c2d-4e5a-9f0a-1b2c3d4e5f60")


class EntityType(str, Enum):
    TOOL = "tool"
    TASK = "task"
    COMPANY = "company"
    NEWS = "news"
    VIDEO = "video"
    ROBOT = "robot"
    DEVICE = "device"
    MODEL = "model"
    REPOSITORY = "repository"
    MCP = "mcp"
    COLLECTION = "collection"
    PERSONAL = "personal"
    CREATIVE = "creative"


class SourceRef(BaseModel):
    name: str
    url: str


class Entity(BaseModel):
    """Canonical entity record. See project spec section 4.1."""

    id: str
    entity_type: EntityType
    name: str
    description: str = ""
    url: str = ""
    categories: list[str] = Field(default_factory=list)
    source: SourceRef

    # Specialized / domain metadata (section 4.2). Kept as a free-form dict
    # so each extractor can attach only the fields relevant to its domain,
    # e.g. {"stars": 120, "language": "Python"} for a repository, or
    # {"license": "apache-2.0", "modalities": ["text", "image"]} for a model.
    metadata: dict = Field(default_factory=dict)

    # Bookkeeping fields, not part of the "public" schema but useful for
    # dedup/audit trails.
    first_seen: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    raw_name: Optional[str] = None  # pre-canonicalization name, for audit

    @staticmethod
    def make_id(entity_type: EntityType | str, canonical_key: str) -> str:
        """Deterministic id: same (type, canonical_key) -> same UUID always."""
        etype = entity_type.value if isinstance(entity_type, EntityType) else entity_type
        return str(uuid.uuid5(NAMESPACE_AI_ORBIT, f"{etype}:{canonical_key.lower().strip()}"))


class RelationType(str, Enum):
    DEVELOPS = "develops"          # Company -> develops -> Tool/Model
    SOLVES = "solves"               # Tool -> solves -> Task
    INTEGRATES_WITH = "integrates_with"  # MCP -> integrates_with -> Tool
    RUNS = "runs"                    # Device -> runs -> Model
    MENTIONS = "mentions"            # News/Video -> mentions -> Entity
    RELATED_TO = "related_to"        # generic fallback, used sparingly


class Relationship(BaseModel):
    id: str
    source_id: str
    target_id: str
    relation_type: RelationType
    confidence: float = 1.0
    evidence: Optional[str] = None  # short justification, e.g. matched text

    @staticmethod
    def make_id(source_id: str, relation_type: RelationType, target_id: str) -> str:
        key = f"{source_id}:{relation_type.value}:{target_id}"
        return str(uuid.uuid5(NAMESPACE_AI_ORBIT, key))
