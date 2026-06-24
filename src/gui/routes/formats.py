"""포맷 목록 API."""
from fastapi import APIRouter

from src.gui.format_loader import load_format_options

router = APIRouter()


@router.get("/formats")
async def get_formats():
    return {"formats": load_format_options()}
