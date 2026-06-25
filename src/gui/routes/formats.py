"""포맷(오버레이 프리셋) 목록 + 예시 썸네일 업로드/삭제 API."""
import re
from pathlib import Path

from fastapi import APIRouter, File, UploadFile
from loguru import logger

from src.gui.format_loader import load_format_options, THUMBS_DIR

router = APIRouter()

_IMG_EXTS = (".jpg", ".jpeg", ".png", ".webp")


def _safe_name(filename: str) -> str:
    """파일명 정화 — traversal 방지 + 허용 확장자."""
    stem = re.sub(r"[^A-Za-z0-9_-]", "_", Path(filename).stem)[:40] or "thumb"
    ext = Path(filename).suffix.lower()
    if ext not in _IMG_EXTS:
        ext = ".jpg"
    return stem + ext


@router.get("/formats")
async def get_formats():
    return {"formats": load_format_options()}


@router.post("/thumbnails")
async def upload_thumbnails(files: list[UploadFile] = File(...)):
    """예시 이미지 업로드 — thumbnails/ 에 저장(동명 덮어쓰기). 즉시 선택지로 반영."""
    THUMBS_DIR.mkdir(parents=True, exist_ok=True)
    saved = []
    for f in files:
        if Path(f.filename or "").suffix.lower() not in _IMG_EXTS:
            continue
        name = _safe_name(f.filename or "thumb.jpg")
        (THUMBS_DIR / name).write_bytes(await f.read())
        saved.append(name)
    logger.info(f"Uploaded thumbnails: {saved}")
    return {"saved": saved, "formats": load_format_options()}


@router.delete("/thumbnails/{filename}")
async def delete_thumbnail(filename: str):
    safe = Path(filename).name  # traversal 방지
    p = THUMBS_DIR / safe
    if p.exists() and p.suffix.lower() in _IMG_EXTS:
        p.unlink()
        logger.info(f"Deleted thumbnail: {safe}")
    return {"formats": load_format_options()}
