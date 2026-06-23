"""커뮤니티 포스트 스코어링/선별 — ranker.py 패턴 재사용."""
from datetime import datetime, timedelta

from loguru import logger

from src.crawler.community_sources import COMMUNITY_SOURCES
from src.db.models import CommunityPost
from src.db.repository import db_session

_SOURCE_WEIGHTS = {src["name"]: src.get("weight", 1.0) for src in COMMUNITY_SOURCES}
_DEMOGRAPHIC_AFFINITY = {
    src["name"]: src.get("demographic_affinity", {}) for src in COMMUNITY_SOURCES
}


def _score(post: CommunityPost, demographic: str) -> float:
    age_hours = (
        (datetime.utcnow() - post.fetched_at).total_seconds() / 3600
        if post.fetched_at
        else 999
    )
    freshness = max(0.0, (48 - age_hours) / 48)

    weight = _SOURCE_WEIGHTS.get(post.source_name, 1.0)

    affinity = _DEMOGRAPHIC_AFFINITY.get(post.source_name, {}).get(demographic, 0.5)

    engagement = min(1.0, (post.likes + post.comment_count * 2) / 500)

    tl = len(post.title or "")
    title_q = 1.0 if 5 <= tl <= 80 else 0.5

    content_q = 1.0 if post.content and len(post.content) >= 100 else 0.5

    return freshness * weight * affinity * (0.5 + 0.5 * engagement) * title_q * content_q


def _post_to_dict(post: CommunityPost) -> dict:
    return {
        "id": post.id,
        "title": post.title,
        "content": post.content,
        "top_comments": post.top_comments,
        "source_name": post.source_name,
        "site": post.site,
        "url": post.url,
        "likes": post.likes,
        "comment_count": post.comment_count,
        "views": post.views,
        "category": post.category,
        "score": post.score,
    }


def select_meme_posts(
    demographics: list[str], posts_per_demographic: int = 3
) -> dict[str, list[dict]]:
    selections: dict[str, list[dict]] = {}
    used_ids: set[int] = set()

    with db_session() as s:
        cutoff = datetime.utcnow() - timedelta(hours=48)
        candidates = (
            s.query(CommunityPost)
            .filter(
                CommunityPost.status == "new",
                CommunityPost.fetched_at >= cutoff,
            )
            .all()
        )

        if not candidates:
            logger.warning("No community posts available for selection")
            return {d: [] for d in demographics}

        for demo in demographics:
            scored = [
                (p, _score(p, demo))
                for p in candidates
                if p.id not in used_ids
            ]
            scored.sort(key=lambda x: x[1], reverse=True)

            selected = []
            for post, sc in scored:
                if len(selected) >= posts_per_demographic:
                    break
                if not post.content or len(post.content) < 50:
                    continue
                post.status = "selected"
                post.score = sc
                selected.append(_post_to_dict(post))
                used_ids.add(post.id)
                logger.info(
                    f"[{demo}] Selected: [{post.source_name}] "
                    f"{post.title[:40]} (score={sc:.3f})"
                )

            selections[demo] = selected

    total = sum(len(v) for v in selections.values())
    logger.info(f"Selected {total} community posts for {len(demographics)} demographics")
    return selections
