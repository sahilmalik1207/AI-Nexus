import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.models.entity import Entity, EntityType


def test_make_id_is_deterministic():
    id1 = Entity.make_id(EntityType.REPOSITORY, "github.com/openai/whisper")
    id2 = Entity.make_id(EntityType.REPOSITORY, "github.com/openai/whisper")
    assert id1 == id2


def test_make_id_is_case_insensitive():
    id1 = Entity.make_id(EntityType.REPOSITORY, "github.com/OpenAI/Whisper")
    id2 = Entity.make_id(EntityType.REPOSITORY, "github.com/openai/whisper")
    assert id1 == id2


def test_make_id_differs_by_entity_type():
    id1 = Entity.make_id(EntityType.REPOSITORY, "same-key")
    id2 = Entity.make_id(EntityType.MODEL, "same-key")
    assert id1 != id2


def test_make_id_differs_by_key():
    id1 = Entity.make_id(EntityType.REPOSITORY, "key-a")
    id2 = Entity.make_id(EntityType.REPOSITORY, "key-b")
    assert id1 != id2
