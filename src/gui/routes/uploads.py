"""스크린샷 업로드 API."""
import shutil
from pathlib import Path

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import FileResponse

from src.gui.session import get_session_dir, list_uploads

router = APIRouter()


@router.post("/uploads")
async def upload_files(
    session_id: str = Form(...),
    files: list[UploadFile] = File(...),
):
    upload_dir = get_session_dir(session_id) / "uploads"
    upload_dir.mkdir(exist_ok=True)

    existing = len(list(upload_dir.iterdir()))
    saved = []

    for i, f in enumerate(files):
        ext = Path(f.filename or "image.jpg").suffix.lower()
        if ext not in (".jpg", ".jpeg", ".png", ".webp"):
            continue
        idx = existing + i + 1
        fname = f"{idx:02d}{ext}"
        dest = upload_dir / fname
        content = await f.read()
        dest.write_bytes(content)
        saved.append({"filename": fname, "size_kb": round(len(content) / 1024, 1)})

    return {"uploaded": saved, "all": list_uploads(session_id)}


@router.get("/uploads")
async def get_uploads(session_id: str):
    return {"files": list_uploads(session_id)}


@router.delete("/uploads/{filename}")
async def delete_upload(filename: str, session_id: str):
    f = get_session_dir(session_id) / "uploads" / filename
    if f.exists():
        f.unlink()
    return {"files": list_uploads(session_id)}


@router.get("/uploads/{session_id}/{filename}")
async def serve_upload(session_id: str, filename: str):
    f = get_session_dir(session_id) / "uploads" / filename
    if not f.exists():
        return {"error": "not found"}
    return FileResponse(str(f))


@router.post("/uploads/reorder")
async def reorder_uploads(session_id: str = Form(...), order: str = Form(...)):
    """순서 변경: order는 쉼표 구분 파일명 리스트."""
    upload_dir = get_session_dir(session_id) / "uploads"
    if not upload_dir.exists():
        return {"files": []}

    filenames = [n.strip() for n in order.split(",") if n.strip()]
    tmp_dir = upload_dir.parent / "uploads_tmp"
    tmp_dir.mkdir(exist_ok=True)

    for old_name in filenames:
        src = upload_dir / old_name
        if src.exists():
            shutil.move(str(src), str(tmp_dir / old_name))

    for f in upload_dir.iterdir():
        f.unlink()

    for i, old_name in enumerate(filenames, 1):
        src = tmp_dir / old_name
        if src.exists():
            ext = Path(old_name).suffix
            shutil.move(str(src), str(upload_dir / f"{i:02d}{ext}"))

    shutil.rmtree(tmp_dir, ignore_errors=True)
    return {"files": list_uploads(session_id)}
