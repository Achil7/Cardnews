"""글 크롤링 & 선별 API."""
import asyncio
from datetime import datetime, timedelta

from fastapi import APIRouter, Query
from loguru import logger

from src.db.models import CommunityPost
from src.db.repository import db_session

router = APIRouter()

_crawl_running = False


@router.post("/crawl")
async def crawl():
    global _crawl_running
    if _crawl_running:
        return {"status": "already_running"}

    _crawl_running = True
    try:
        from src.crawler.community_fetcher import fetch_community_posts
        count = await asyncio.to_thread(fetch_community_posts)
        return {"status": "done", "saved_count": count}
    except Exception as e:
        logger.exception("Crawl failed")
        return {"status": "error", "error": str(e)}
    finally:
        _crawl_running = False


@router.get("/posts")
async def get_posts(limit: int = Query(30, ge=1, le=100)):
    from src.crawler.community_sources import COMMUNITY_SOURCES

    source_weights = {s["name"]: s.get("weight", 1.0) for s in COMMUNITY_SOURCES}

    with db_session() as s:
        cutoff = datetime.utcnow() - timedelta(hours=72)
        rows = (
            s.query(CommunityPost)
            .filter(
                CommunityPost.status.in_(["new", "selected"]),
                CommunityPost.fetched_at >= cutoff,
            )
            .all()
        )

        scored = []
        for p in rows:
            age_h = (datetime.utcnow() - p.fetched_at).total_seconds() / 3600 if p.fetched_at else 999
            freshness = max(0.0, (72 - age_h) / 72)
            weight = source_weights.get(p.source_name, 1.0)
            engagement = min(1.0, (p.likes + p.comment_count * 2) / 500)
            sc = freshness * weight * (0.5 + 0.5 * engagement)
            scored.append((p, sc))

        scored.sort(key=lambda x: x[1], reverse=True)

        result = []
        for p, sc in scored[:limit]:
            result.append({
                "id": p.id,
                "title": p.title,
                "source_name": p.source_name,
                "site": p.site,
                "url": p.url,
                "likes": p.likes,
                "comment_count": p.comment_count,
                "views": p.views,
                "content": (p.content or "")[:200],
                "top_comments": (p.top_comments or "")[:200],
                "score": round(sc, 3),
                "fetched_at": p.fetched_at.isoformat() if p.fetched_at else None,
            })

    return {"posts": result}


@router.get("/posts/{post_id}")
async def get_post_detail(post_id: int):
    with db_session() as s:
        p = s.get(CommunityPost, post_id)
        if not p:
            return {"error": "not found"}
        return {
            "id": p.id,
            "title": p.title,
            "source_name": p.source_name,
            "site": p.site,
            "url": p.url,
            "likes": p.likes,
            "comment_count": p.comment_count,
            "content": p.content or "",
            "top_comments": p.top_comments or "",
        }
