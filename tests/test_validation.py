import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.models.entity import Entity, EntityType, Relationship, RelationType, SourceRef
from src.processing.validation import validate_entities, validate_relationships


def make_entity(id_, name="Name", url="https://example.com", source_name="Src"):
    return Entity(id=id_, entity_type=EntityType.TOOL, name=name, url=url,
                  source=SourceRef(name=source_name, url="https://example.com"))


def test_valid_entity_passes():
    valid, quarantined = validate_entities([make_entity("id1")])
    assert len(valid) == 1
    assert len(quarantined) == 0


def test_entity_with_no_name_is_quarantined():
    valid, quarantined = validate_entities([make_entity("id1", name="")])
    assert len(valid) == 0
    assert len(quarantined) == 1
    assert "name" in quarantined[0]["errors"][0]


def test_entity_with_malformed_url_is_quarantined():
    valid, quarantined = validate_entities([make_entity("id1", url="not-a-url")])
    assert len(valid) == 0
    assert len(quarantined) == 1


def test_entity_missing_source_is_quarantined():
    e = make_entity("id1", source_name="")
    valid, quarantined = validate_entities([e])
    assert len(quarantined) == 1


def test_relationship_with_unknown_entity_is_quarantined():
    rel = Relationship(id="r1", source_id="unknown", target_id="also-unknown",
                        relation_type=RelationType.DEVELOPS)
    valid, quarantined = validate_relationships([rel], valid_entity_ids={"id1"})
    assert len(valid) == 0
    assert len(quarantined) == 1


def test_self_referential_relationship_is_quarantined():
    rel = Relationship(id="r1", source_id="id1", target_id="id1",
                        relation_type=RelationType.DEVELOPS)
    valid, quarantined = validate_relationships([rel], valid_entity_ids={"id1"})
    assert len(valid) == 0
    assert len(quarantined) == 1


def test_valid_relationship_passes():
    rel = Relationship(id="r1", source_id="id1", target_id="id2",
                        relation_type=RelationType.DEVELOPS)
    valid, quarantined = validate_relationships([rel], valid_entity_ids={"id1", "id2"})
    assert len(valid) == 1
    assert len(quarantined) == 0
