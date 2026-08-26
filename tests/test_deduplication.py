import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.models.entity import Entity, EntityType, SourceRef
from src.processing.deduplication import deduplicate


def make_entity(id_, name, url, entity_type=EntityType.COMPANY, description="", metadata=None):
    return Entity(
        id=id_, entity_type=entity_type, name=name, description=description,
        url=url, source=SourceRef(name="s", url="u"), metadata=metadata or {},
    )


def test_exact_id_duplicates_are_merged():
    e1 = make_entity("same-id", "OpenAI", "https://openai.com", description="short")
    e2 = make_entity("same-id", "OpenAI", "https://openai.com", description="a longer richer description")
    result = deduplicate([e1, e2])
    assert len(result) == 1
    assert result[0].description == "a longer richer description"


def test_same_url_different_id_is_merged():
    e1 = make_entity("id1", "OpenAI", "https://openai.com", metadata={"sector": "AI"})
    e2 = make_entity("id2", "OpenAI Inc", "https://openai.com", metadata={"hq": "SF"})
    result = deduplicate([e1, e2])
    assert len(result) == 1
    assert result[0].metadata.get("sector") == "AI"
    assert result[0].metadata.get("hq") == "SF"


def test_fuzzy_name_variant_is_merged():
    e1 = make_entity("id1", "OpenAI", "https://openai.com")
    e2 = make_entity("id2", "Open AI", "https://different-url.example.com")
    result = deduplicate([e1, e2])
    assert len(result) == 1


def test_different_entity_types_are_not_merged_even_with_same_name():
    e1 = make_entity("id1", "Whisper", "https://a.com", entity_type=EntityType.MODEL)
    e2 = make_entity("id2", "Whisper", "https://b.com", entity_type=EntityType.TOOL)
    result = deduplicate([e1, e2])
    assert len(result) == 2


def test_dissimilar_names_are_not_merged():
    e1 = make_entity("id1", "OpenAI", "https://a.com")
    e2 = make_entity("id2", "Anthropic", "https://b.com")
    result = deduplicate([e1, e2])
    assert len(result) == 2
