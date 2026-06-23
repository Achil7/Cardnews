"""설정 관리 API — API 키, 계정 정보."""
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel
from loguru import logger

from config import PROJECT_ROOT, accounts_config

router = APIRouter()

ENV_PATH = PROJECT_ROOT / ".env"


class SettingsUpdate(BaseModel):
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    gemini_api_key: str = ""
    google_drive_folder_id: str = ""
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""


def _read_env() -> dict[str, str]:
    result = {}
    if not ENV_PATH.exists():
        return result
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, v = line.split("=", 1)
            result[k.strip()] = v.strip()
    return result


def _mask_key(key: str) -> str:
    if not key or len(key) < 10:
        return key
    return key[:6] + "..." + key[-4:]


@router.get("/settings")
async def get_settings():
    env = _read_env()
    return {
        "openai_api_key": _mask_key(env.get("OPENAI_API_KEY", "")),
        "anthropic_api_key": _mask_key(env.get("ANTHROPIC_API_KEY", "")),
        "gemini_api_key": _mask_key(env.get("GEMINI_API_KEY", "")),
        "google_drive_folder_id": env.get("GOOGLE_DRIVE_FOLDER_ID", ""),
        "telegram_bot_token": _mask_key(env.get("TELEGRAM_BOT_TOKEN", "")),
        "telegram_chat_id": env.get("TELEGRAM_CHAT_ID", ""),
        "keys_configured": bool(
            env.get("ANTHROPIC_API_KEY") and env.get("GOOGLE_DRIVE_FOLDER_ID")
        ),
    }


@router.post("/settings")
async def update_settings(req: SettingsUpdate):
    env = _read_env()

    if req.openai_api_key and "..." not in req.openai_api_key:
        env["OPENAI_API_KEY"] = req.openai_api_key
    if req.anthropic_api_key and "..." not in req.anthropic_api_key:
        env["ANTHROPIC_API_KEY"] = req.anthropic_api_key
    if req.gemini_api_key and "..." not in req.gemini_api_key:
        env["GEMINI_API_KEY"] = req.gemini_api_key
    if req.google_drive_folder_id:
        env["GOOGLE_DRIVE_FOLDER_ID"] = req.google_drive_folder_id
    if req.telegram_bot_token and "..." not in req.telegram_bot_token:
        env["TELEGRAM_BOT_TOKEN"] = req.telegram_bot_token
    if req.telegram_chat_id:
        env["TELEGRAM_CHAT_ID"] = req.telegram_chat_id

    lines = []
    key_order = [
        ("# LLM Provider", None),
        ("LLM_PROVIDER", env.get("LLM_PROVIDER", "openai")),
        ("", None),
        ("# OpenAI", None),
        ("OPENAI_API_KEY", env.get("OPENAI_API_KEY", "")),
        ("", None),
        ("# Anthropic (Claude)", None),
        ("ANTHROPIC_API_KEY", env.get("ANTHROPIC_API_KEY", "")),
        ("", None),
        ("# Gemini", None),
        ("GEMINI_API_KEY", env.get("GEMINI_API_KEY", "")),
        ("", None),
        ("# Runtime", None),
        ("SLIDES_PER_POST", env.get("SLIDES_PER_POST", "6")),
        ("LOG_LEVEL", env.get("LOG_LEVEL", "INFO")),
        ("", None),
        ("# Google Drive Upload", None),
        ("GOOGLE_DRIVE_FOLDER_ID", env.get("GOOGLE_DRIVE_FOLDER_ID", "")),
        ("GOOGLE_CREDENTIALS_PATH", env.get("GOOGLE_CREDENTIALS_PATH", "credentials.json")),
        ("", None),
        ("# Telegram Notification", None),
        ("TELEGRAM_BOT_TOKEN", env.get("TELEGRAM_BOT_TOKEN", "")),
        ("TELEGRAM_CHAT_ID", env.get("TELEGRAM_CHAT_ID", "")),
    ]

    for key, val in key_order:
        if val is None:
            lines.append(key)
        elif key == "":
            lines.append("")
        else:
            lines.append(f"{key}={val}")

    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    logger.info("Settings updated via GUI")

    return {"status": "saved", "message": "설정이 저장되었습니다. 프로그램을 재시작하세요."}


@router.get("/accounts")
async def get_accounts():
    meme_accounts = [
        {"handle": a.handle, "enabled": a.enabled, "demographics": a.demographics}
        for a in accounts_config.meme_accounts
    ]
    meme_categories = [
        {"id": mc.id, "label_ko": mc.label_ko, "demographic": mc.demographic}
        for mc in accounts_config.meme_categories
    ]
    return {"accounts": meme_accounts, "categories": meme_categories}
