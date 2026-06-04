from datetime import datetime, timedelta

from loguru import logger

from config import accounts_config
from src.crawler.rss_sources import RSS_SOURCES
from src.db.models import Article
from src.db.repository import db_session

_SOURCE_WEIGHTS = {src["name"]: src.get("weight", 1.0) for src in RSS_SOURCES}

REGIONS = ["korean", "overseas"]


def score_article(a: Article) -> float:
    age_hours = (
        (datetime.utcnow() - a.published_at).total_seconds() / 3600
        if a.published_at
        else 999
    )
    freshness = max(0, 48 - age_hours) / 48
    weight = _SOURCE_WEIGHTS.get(a.source, 1.0)
    tl = len(a.title or "")
    title_score = 1.0 if 10 <= tl <= 100 else 0.5
    return freshness * weight * title_score


def select_for_all_accounts() -> dict[str, list[dict]]:
    """멀티 계정용 기사 선별.

    Returns:
        {"account_1": [{"article_id": 1, "category": "economy", "region": "korean"}, ...], ...}
    """
    accounts = accounts_config.enabled_accounts
    categories = accounts_config.category_ids
    num_accounts = len(accounts)

    if not accounts or not categories:
        logger.warning("No accounts or categories configured")
        return {}

    pools: dict[tuple[str, str], list[tuple[Article, float]]] = {}

    with db_session() as s:
        cutoff = datetime.utcnow() - timedelta(hours=48)

        for cat in categories:
            for region in REGIONS:
                candidates = (
                    s.query(Article)
                    .filter(
                        Article.status == "new",
                        Article.category == cat,
                        Article.region == region,
                        Article.published_at >= cutoff,
                    )
                    .all()
                )

                scored = [(a, score_article(a)) for a in candidates]
                scored.sort(key=lambda x: x[1], reverse=True)
                pools[(cat, region)] = scored[:num_accounts]

                if len(scored) < num_accounts:
                    logger.warning(
                        f"[{cat}/{region}] {len(scored)}/{num_accounts} articles available"
                    )

        assignments: dict[str, list[dict]] = {a.handle: [] for a in accounts}

        for cat in categories:
            for region in REGIONS:
                pool = pools.get((cat, region), [])
                for idx, account in enumerate(accounts):
                    if idx >= len(pool):
                        logger.warning(
                            f"[{account.handle}] No article for {cat}/{region}, skipping"
                        )
                        continue
                    article, sc = pool[idx]
                    article.status = "selected"
                    article.score = sc
                    assignments[account.handle].append(
                        {
                            "article_id": article.id,
                            "category": cat,
                            "region": region,
                        }
                    )
                    logger.info(
                        f"[{account.handle}] {cat}/{region}: "
                        f"[{article.source}] {article.title[:50]} (score={sc:.3f})"
                    )

    total = sum(len(v) for v in assignments.values())
    logger.info(f"Total {total} articles assigned to {num_accounts} accounts")
    return assignments
