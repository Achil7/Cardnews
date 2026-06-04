import pytest

from src.generator import get_generator
from src.generator.base import BaseGenerator, CardContent


def test_factory_returns_base_generator():
    gen = get_generator()
    assert isinstance(gen, BaseGenerator)


def test_validate_slides_valid():
    gen = get_generator()
    data = {
        "title": "Test",
        "subtitle": "Sub",
        "slides": [
            {"type": "cover", "title": "T", "subtitle": "S"},
            {"type": "body", "heading": "H1", "body": "B1"},
            {"type": "body", "heading": "H2", "body": "B2"},
            {"type": "outro", "source": "Src", "cta": "CTA"},
        ],
        "caption": "Caption",
        "hashtags": ["#test"],
    }
    result = gen._validate_slides(data, 4)
    assert isinstance(result, CardContent)
    assert len(result.slides) == 4
    assert result.title == "Test"


def test_validate_slides_missing_cover():
    gen = get_generator()
    data = {
        "slides": [
            {"type": "body", "heading": "H", "body": "B"},
            {"type": "outro", "source": "S", "cta": "C"},
        ]
    }
    with pytest.raises(ValueError, match="cover"):
        gen._validate_slides(data, 2)


def test_validate_slides_missing_outro():
    gen = get_generator()
    data = {
        "slides": [
            {"type": "cover", "title": "T", "subtitle": "S"},
            {"type": "body", "heading": "H", "body": "B"},
        ]
    }
    with pytest.raises(ValueError, match="outro"):
        gen._validate_slides(data, 2)


def test_validate_slides_body_missing_heading():
    gen = get_generator()
    data = {
        "slides": [
            {"type": "cover", "title": "T", "subtitle": "S"},
            {"type": "body", "heading": "", "body": "B"},
            {"type": "outro", "source": "S", "cta": "C"},
        ]
    }
    with pytest.raises(ValueError, match="heading"):
        gen._validate_slides(data, 3)


def test_claude_extract_json():
    from src.generator.claude_client import ClaudeGenerator

    raw = '```json\n{"title": "test"}\n```'
    assert ClaudeGenerator._extract_json(raw) == '{"title": "test"}'

    plain = '{"title": "test"}'
    assert ClaudeGenerator._extract_json(plain) == '{"title": "test"}'
