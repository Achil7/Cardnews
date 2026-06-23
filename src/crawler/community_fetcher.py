"""커뮤니티 인기글 크롤링 — fetcher.py 패턴 재사용."""
import hashlib
import time
from datetime import datetime

import requests
from loguru import logger

from src.db.models import CommunityPost
from src.db.repository import db_session
from .community_parser import HEADERS, parse_listing, parse_post_detail
from .community_sources import COMMUNITY_SOURCES


def _hash_url(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:32]


def fetch_community_posts() -> int:
    total_saved = 0
    for src in COMMUNITY_SOURCES:
        try:
            saved = _fetch_one_source(src)
            total_saved += saved
            time.sleep(2)
        except Exception as e:
            logger.error(f"[{src['name']}] community fetch failed: {e}")
    logger.info(f"Community crawl done: {total_saved} new posts saved")
    return total_saved


def _fetch_one_source(src: dict) -> int:
    resp = requests.get(src["base_url"], headers=HEADERS, timeout=15)
    resp.raise_for_status()

    posts_meta = parse_listing(src["site"], resp.text)
    if not posts_meta:
        logger.warning(f"[{src['name']}] no posts parsed from listing")
        return 0
    logger.info(f"[{src['name']}] {len(posts_meta)} posts found")

    hashes = [_hash_url(p["url"]) for p in posts_meta]
    with db_session() as s:
        existing = set(
            row[0]
            for row in s.query(CommunityPost.url_hash)
            .filter(CommunityPost.url_hash.in_(hashes))
            .all()
        )

    new_posts = [p for p in posts_meta if _hash_url(p["url"]) not in existing]
    if not new_posts:
        logger.info(f"[{src['name']}] all posts already in DB")
        return 0

    new_posts.sort(
        key=lambda p: p.get("likes", 0) + p.get("comment_count", 0) * 2 + p.get("views", 0) / 100,
        reverse=True,
    )
    top_n = new_posts[:10]

    saved = 0
    for post_meta in top_n:
        try:
            time.sleep(1.5)
            detail_resp = requests.get(post_meta["url"], headers=HEADERS, timeout=15)
            detail = parse_post_detail(src["site"], detail_resp.text)

            with db_session() as s:
                cp = CommunityPost(
                    url=post_meta["url"],
                    url_hash=_hash_url(post_meta["url"]),
                    source_name=src["name"],
                    site=src["site"],
                    title=post_meta["title"],
                    content=(detail.get("content") or "")[:5000],
                    top_comments=(detail.get("top_comments") or "")[:3000],
                    likes=post_meta.get("likes", 0),
                    comment_count=post_meta.get("comment_count", 0),
                    views=post_meta.get("views", 0),
                    category=src["category"],
                    published_at=datetime.utcnow(),
                    fetched_at=datetime.utcnow(),
                )
                s.add(cp)
                saved += 1
                logger.debug(f"[{src['name']}] saved: {post_meta['title'][:40]}")
        except Exception as e:
            logger.warning(f"[{src['name']}] detail fetch failed: {post_meta.get('title', '')[:30]} — {e}")

    logger.info(f"[{src['name']}] {saved} new posts saved")
    return saved
