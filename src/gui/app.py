"""FastAPI 앱 — 밈 카드뉴스 반수동 GUI."""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.gui.session import cleanup_old_sessions

STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    cleanup_old_sessions()
    yield


app = FastAPI(title="Meme Cardnews GUI", lifespan=lifespan)

from src.gui.routes import posts, uploads, formats, generate, render as render_routes, settings

app.include_router(posts.router, prefix="/api")
app.include_router(uploads.router, prefix="/api")
app.include_router(formats.router, prefix="/api")
app.include_router(generate.router, prefix="/api")
app.include_router(render_routes.router, prefix="/api")
app.include_router(settings.router, prefix="/api")

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

FORMAT_THUMBNAILS = Path(__file__).parent / "formats" / "thumbnails"
if FORMAT_THUMBNAILS.exists():
    app.mount(
        "/format-thumbnails",
        StaticFiles(directory=str(FORMAT_THUMBNAILS)),
        name="format-thumbnails",
    )


@app.get("/")
async def index():
    return FileResponse(str(STATIC_DIR / "index.html"))
