"""GUI 세션 관리 — 세션별 임시 디렉토리."""
import shutil
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from config import PROJECT_ROOT

SESSIONS_DIR = PROJECT_ROOT / "data" / "gui_sessions"


def create_session() -> str:
    sid = uuid.uuid4().hex[:12]
    d = SESSIONS_DIR / sid
    d.mkdir(parents=True, exist_ok=True)
    (d / ".created").write_text(datetime.utcnow().isoformat())
    return sid


def get_session_dir(session_id: str) -> Path:
    d = SESSIONS_DIR / session_id
    if not d.exists():
        d.mkdir(parents=True, exist_ok=True)
    return d


def list_uploads(session_id: str) -> list[dict]:
    d = get_session_dir(session_id) / "uploads"
    if not d.exists():
        return []
    result = []
    for f in sorted(d.iterdir()):
        if f.is_file() and f.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
            result.append({
                "filename": f.name,
                "size_kb": round(f.stat().st_size / 1024, 1),
            })
    return result


def cleanup_old_sessions(max_age_hours: int = 24):
    if not SESSIONS_DIR.exists():
        return
    cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
    for d in SESSIONS_DIR.iterdir():
        if not d.is_dir():
            continue
        marker = d / ".created"
        if marker.exists():
            try:
                created = datetime.fromisoformat(marker.read_text().strip())
                if created < cutoff:
                    shutil.rmtree(d, ignore_errors=True)
            except Exception:
                pass
