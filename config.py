from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).parent.resolve()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
    )

    # LLM Provider
    llm_provider: Literal["openai", "claude", "gemini"] = "openai"

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-mini"

    # Anthropic
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-5-20250514"

    # Gemini
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

    # DB
    database_url: str = f"sqlite:///{PROJECT_ROOT / 'data' / 'db.sqlite'}"

    # Runtime
    slides_per_post: int = 6
    timezone: str = "Asia/Seoul"
    log_level: str = "INFO"

    # Google Drive Upload
    google_drive_folder_id: str = ""
    google_credentials_path: str = "credentials.json"

    # Telegram Notification
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # Accounts config
    accounts_config_path: str = "accounts.yaml"


class CategoryConfig(BaseModel):
    id: str
    label_ko: str
    accent_color: str


class AccountConfig(BaseModel):
    handle: str
    enabled: bool = True


class AccountsConfig(BaseModel):
    categories: list[CategoryConfig]
    accounts: list[AccountConfig]

    @property
    def enabled_accounts(self) -> list[AccountConfig]:
        return [a for a in self.accounts if a.enabled]

    @property
    def category_ids(self) -> list[str]:
        return [c.id for c in self.categories]

    def get_accent_color(self, category_id: str) -> str:
        for c in self.categories:
            if c.id == category_id:
                return c.accent_color
        return "#4A6CF7"

    def get_label_ko(self, category_id: str) -> str:
        for c in self.categories:
            if c.id == category_id:
                return c.label_ko
        return category_id


def load_accounts_config() -> AccountsConfig:
    config_path = PROJECT_ROOT / settings.accounts_config_path
    with open(config_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return AccountsConfig(**data)


settings = Settings()
accounts_config = load_accounts_config()
