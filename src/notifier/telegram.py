import requests
from loguru import logger

from config import settings

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


def _build_message(
    date: str,
    total: int,
    success: int,
    failed: int,
    drive_url: str | None = None,
) -> str:
    if total == 0:
        return (
            f"📋 <b>[Cardnews] {date} 파이프라인 완료</b>\n\n"
            f"처리할 기사가 없습니다."
        )

    if failed == 0:
        status_emoji = "✅"
        status_text = "전체 성공"
    elif success == 0:
        status_emoji = "🔴"
        status_text = "전체 실패"
    else:
        status_emoji = "⚠️"
        status_text = "일부 실패"

    lines = [
        f"{status_emoji} <b>[Cardnews] {date} 파이프라인 완료</b>",
        "",
        f"📊 포스트: {success}/{total} 성공",
        f"📌 상태: {status_text}",
    ]

    if drive_url:
        lines.append("")
        lines.append(f'📁 <a href="{drive_url}">Drive 폴더 열기</a>')

    return "\n".join(lines)


def send_telegram_notification(
    date: str,
    total: int,
    success: int,
    failed: int,
    drive_url: str | None = None,
) -> bool:
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        logger.debug("Telegram not configured, skipping notification")
        return False

    message = _build_message(date, total, success, failed, drive_url)

    try:
        url = TELEGRAM_API.format(token=settings.telegram_bot_token)
        resp = requests.post(
            url,
            json={
                "chat_id": settings.telegram_chat_id,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=10,
        )
        resp.raise_for_status()
        logger.info("Telegram notification sent")
        return True
    except Exception as e:
        logger.warning(f"Telegram notification failed: {e}")
        return False
