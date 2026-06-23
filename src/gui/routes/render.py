"""미리보기 & 최종 렌더링 + Drive 업로드 API."""
import base64
import json
import re
import shutil
from datetime import datetime, timezone, timedelta
from pathlib import Path

from fastapi import APIRouter
from loguru import logger
from pydantic import BaseModel

from config import PROJECT_ROOT, accounts_config
from src.gui.session import get_session_dir

router = APIRouter()

KST = timezone(timedelta(hours=9))


class PreviewRequest(BaseModel):
    session_id: str
    format_id: str = "classic_dark"
    hook_text: str
    punchline: str = ""
    caption: str = ""
    hashtags: list[str] = []
    handle: str = "TBD_meme"


class FinalizeRequest(BaseModel):
    session_id: str
    format_id: str = "classic_dark"
    hook_text: str
    punchline: str = ""
    caption: str = ""
    hashtags: list[str] = []
    handle: str = "TBD_meme"
    demographic: str = "20s"
    post_id: int | None = None


def _build_card_data(
    req, screenshot_uris: list[str],
) -> dict:
    return {
        "hook_text": req.hook_text,
        "punchline": req.punchline,
        "caption": req.caption,
        "hashtags": req.hashtags,
        "_content_mode": "screenshot" if screenshot_uris else "text",
        "_content_data": screenshot_uris,
    }


def _load_screenshots_as_uris(session_id: str) -> list[str]:
    upload_dir = get_session_dir(session_id) / "uploads"
    if not upload_dir.exists():
        return []

    uris = []
    for f in sorted(upload_dir.iterdir()):
        if f.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
            data = f.read_bytes()
            ext = f.suffix.lower().lstrip(".")
            if ext == "jpg":
                ext = "jpeg"
            b64 = base64.b64encode(data).decode("ascii")
            uris.append(f"data:image/{ext};base64,{b64}")
    return uris


@router.post("/preview")
async def preview(req: PreviewRequest):
    screenshot_uris = _load_screenshots_as_uris(req.session_id)
    card_data = _build_card_data(req, screenshot_uris)

    preview_dir = get_session_dir(req.session_id) / "preview"
    if preview_dir.exists():
        shutil.rmtree(preview_dir)
    preview_dir.mkdir(parents=True)

    cover_image = screenshot_uris[0] if screenshot_uris else None
    content_uris = screenshot_uris[1:] if len(screenshot_uris) > 1 else screenshot_uris

    card_data["_content_data"] = content_uris

    try:
        from src.renderer.render import render_slides, _css_cache
        import src.renderer.render as render_mod
        render_mod._css_cache = None

        meme_cat = accounts_config.get_meme_category("20s")
        category = meme_cat.id if meme_cat else "meme_20s"

        await render_slides(
            card_data,
            preview_dir,
            "gui_preview",
            category,
            handle=req.handle,
            cover_image=cover_image,
            slide_images=[],
            file_prefix="",
            content_type="meme",
        )

        slides = []
        for f in sorted(preview_dir.iterdir()):
            if f.suffix.lower() in (".jpg", ".jpeg"):
                b64 = base64.b64encode(f.read_bytes()).decode("ascii")
                slides.append({
                    "index": int(re.sub(r"\D", "", f.stem) or "0"),
                    "base64": b64,
                })

        return {"slides": slides}
    except Exception as e:
        logger.exception("Preview render failed")
        return {"error": str(e)}


@router.post("/finalize")
async def finalize(req: FinalizeRequest):
    screenshot_uris = _load_screenshots_as_uris(req.session_id)
    card_data = _build_card_data(req, screenshot_uris)

    cover_image = screenshot_uris[0] if screenshot_uris else None
    card_data["_content_data"] = screenshot_uris[1:] if len(screenshot_uris) > 1 else screenshot_uris

    now_kst = datetime.now(KST)
    today = now_kst.strftime("%Y-%m-%d")
    slug = re.sub(r'[^\w가-힣\s]', '', req.hook_text)[:20].strip().replace(' ', '_') or "post"
    meme_cat = accounts_config.get_meme_category(req.demographic)
    label = meme_cat.label_ko if meme_cat else f"밈{req.demographic}"
    category = meme_cat.id if meme_cat else "meme_20s"

    out_dir = PROJECT_ROOT / "data" / "output" / today / req.handle / label / slug

    try:
        from src.renderer.render import render_slides
        import src.renderer.render as render_mod
        render_mod._css_cache = None

        await render_slides(
            card_data,
            out_dir,
            "gui_manual",
            category,
            handle=req.handle,
            cover_image=cover_image,
            slide_images=[],
            file_prefix="",
            content_type="meme",
        )

        drive_url = None
        try:
            from src.uploader.drive import upload_post_to_drive
            drive_url = upload_post_to_drive(out_dir)
            if drive_url:
                shutil.rmtree(out_dir, ignore_errors=True)
        except Exception as e:
            logger.warning(f"Drive upload failed: {e}")

        if req.post_id:
            from src.db.models import CommunityPost
            from src.db.repository import db_session
            with db_session() as s:
                cp = s.get(CommunityPost, req.post_id)
                if cp:
                    cp.status = "used"

        return {
            "status": "done",
            "drive_url": drive_url,
            "output_dir": str(out_dir),
        }
    except Exception as e:
        logger.exception("Finalize failed")
        return {"error": str(e)}
