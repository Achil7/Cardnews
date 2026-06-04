from src.renderer.render import render_html, _get_accent, ACCENT_COLORS


def test_get_accent_known():
    assert _get_accent("tech") == "#0EA5E9"
    assert _get_accent("economy") == "#10B981"


def test_get_accent_unknown_returns_default():
    assert _get_accent("unknown") == "#4A6CF7"


def test_render_html_cover():
    slide = {"type": "cover", "title": "Test Title", "subtitle": "Test Sub"}
    html = render_html(slide, 1, 5, "BBC", "tech")
    assert "card-cover" in html
    assert "Test Title" in html
    assert "Test Sub" in html
    assert "TECH" in html


def test_render_html_body():
    slide = {"type": "body", "heading": "Heading", "body": "Body text"}
    html = render_html(slide, 2, 5, "BBC", "tech")
    assert "card-body" in html
    assert "Heading" in html
    assert "Body text" in html
    assert "2 / 5" in html


def test_render_html_outro():
    slide = {"type": "outro", "source": "Reuters", "cta": "Share!"}
    html = render_html(slide, 5, 5, "Reuters", "world")
    assert "card-outro" in html
    assert "Share!" in html
    assert "Reuters" in html


def test_render_html_invalid_type():
    import pytest

    slide = {"type": "invalid"}
    with pytest.raises(ValueError, match="invalid"):
        render_html(slide, 1, 1, "test", "test")
