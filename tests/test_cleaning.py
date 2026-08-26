import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.models.entity import Entity, EntityType, SourceRef
from src.processing.cleaning import clean_entity, normalize_url, sanitize_text


def test_sanitize_text_strips_html_and_whitespace():
    assert sanitize_text("  <b>Hello</b>   world  ") == "Hello world"


def test_sanitize_text_handles_empty_and_none():
    assert sanitize_text("") == ""
    assert sanitize_text(None) == ""


def test_normalize_url_lowercases_scheme_and_host():
    assert normalize_url("HTTPS://GitHub.com/openai/whisper") == "https://github.com/openai/whisper"


def test_normalize_url_strips_tracking_params():
    result = normalize_url("https://example.com/page?utm_source=x&id=5&ref=y")
    assert "utm_source" not in result
    assert "ref=y" not in result
    assert "id=5" in result


def test_normalize_url_strips_trailing_slash():
    assert normalize_url("https://example.com/page/") == "https://example.com/page"


def test_normalize_url_drops_fragment():
    assert "#" not in normalize_url("https://example.com/page#section")


def test_clean_entity_lowercases_categories():
    e = Entity(
        id="x", entity_type=EntityType.TOOL, name="  Test Tool  ",
        description="<p>desc</p>", url="https://Example.com/",
        categories=["AI", "  ml "], source=SourceRef(name="s", url="u"),
    )
    cleaned = clean_entity(e)
    assert cleaned.name == "Test Tool"
    assert cleaned.description == "desc"
    assert cleaned.categories == ["ai", "ml"]
