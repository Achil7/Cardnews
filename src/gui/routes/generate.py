"""LLM 텍스트 생성 API."""
import asyncio

from fastapi import APIRouter
from pydantic import BaseModel
from loguru import logger

from src.db.models import CommunityPost
from src.db.repository import db_session

router = APIRouter()


class GenerateRequest(BaseModel):
    post_id: int
    demographic: str = "20s"


@router.post("/generate-text")
async def generate_text(req: GenerateRequest):
    with db_session() as s:
        p = s.get(CommunityPost, req.post_id)
        if not p:
            return {"error": "post not found"}

        article = {
            "title": p.title,
            "source": p.source_name,
            "category": f"meme_{req.demographic}",
            "demographic": req.demographic,
            "content": (p.content or "")[:3000],
            "top_comments": (p.top_comments or "")[:2000],
        }

    try:
        from src.generator.meme_generator import MemeGenerator
        gen = MemeGenerator()
        card = await asyncio.to_thread(gen.generate_card_content, article)

        return {
            "hook_text": card.raw_json.get("hook_text", ""),
            "punchline": card.raw_json.get("punchline", ""),
            "caption": card.raw_json.get("caption", ""),
            "hashtags": card.raw_json.get("hashtags", []),
            "image_prompt": card.raw_json.get("image_prompt", ""),
        }
    except Exception as e:
        logger.exception("Text generation failed")
        return {"error": str(e)}
