import hashlib
from datetime import datetime

import feedparser
from loguru import logger

from src.db.models import Article
from src.db.repository import db_session
from .rss_sources import RSS_SOURCES


def hash_url(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:32]


def fetch_all() -> int:
    saved = 0
    for src in RSS_SOURCES:
        try:
            feed = feedparser.parse(src["url"])
            entries = feed.entries
            logger.info(f"[{src['name']}] {len(entries)} entries fetched")

            if not entries:
                continue

            hashes = [hash_url(e.get("link", "")) for e in entries if e.get("link")]
            url_map = {hash_url(e["link"]): e for e in entries if e.get("link")}

            with db_session() as s:
                existing = set(
                    row[0]
                    for row in s.query(Article.url_hash)
                    .filter(Article.url_hash.in_(hashes))
                    .all()
                )

                for uh, entry in url_map.items():
                    if uh in existing:
                        continue

                    published = None
                    if entry.get("published_parsed"):
                        try:
                            published = datetime(*entry.published_parsed[:6])
                        except Exception:
                            pass

                    lang = src.get("language", "ko")
                    article = Article(
                        url=entry["link"],
                        url_hash=uh,
                        source=src["name"],
                        title=(entry.get("title") or "")[:500],
                        summary=(entry.get("summary") or "")[:2000],
                        category=src["category"],
                        language=lang,
                        region="korean" if lang == "ko" else "overseas",
                        published_at=published or datetime.utcnow(),
                    )
                    s.add(article)
                    saved += 1

        except Exception as e:
            logger.error(f"[{src['name']}] fetch failed: {e}")

    logger.info(f"Saved {saved} new articles")
    return saved
