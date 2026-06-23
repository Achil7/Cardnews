"""조회 API — GUI 상태바용 (API 키 설정 여부, 계정/카테고리).

설정 변경은 GUI가 아니라 서버의 .env / accounts.yaml 을 직접 수정 후 재배포한다.
(컨테이너는 시작 시점에 환경변수를 한 번 로드하므로 런타임 변경은 의미가 없음)
"""
from fastapi import APIRouter

from config import PROJECT_ROOT, accounts_config

router = APIRouter()

ENV_PATH = PROJECT_ROOT / ".env"


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


@router.get("/settings")
async def get_settings():
    """상태바 표시용 — 키 노출 없이 설정 여부만 반환."""
    env = _read_env()
    return {
        "keys_configured": bool(
            env.get("ANTHROPIC_API_KEY") and env.get("GOOGLE_DRIVE_FOLDER_ID")
        ),
    }


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
