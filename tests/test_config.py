from config import PROJECT_ROOT, settings


def test_project_root_exists():
    assert PROJECT_ROOT.exists()


def test_settings_defaults():
    assert settings.llm_provider in ("openai", "claude", "gemini")
    assert settings.posts_per_day >= 1
    assert settings.slides_per_post >= 3
    assert settings.timezone == "Asia/Seoul"


def test_database_url_is_absolute():
    assert "sqlite:///" in settings.database_url
    assert "\\" in settings.database_url or "/" in settings.database_url
