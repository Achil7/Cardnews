import asyncio
import json
import shutil
import traceback
from datetime import datetime
from pathlib import Path

from loguru import logger

from config import PROJECT_ROOT, accounts_config
from src.crawler.fetcher import fetch_all
from src.crawler.image_fetcher import fetch_article_image, generate_ai_image, verify_image_relevance
from src.db.models import Article, Post
from src.db.repository import db_session, init_db
from src.generator import get_generator
from src.notifier.telegram import send_telegram_notification
from src.renderer.render import render_slides
from src.selector.ranker import select_for_all_accounts
from src.uploader.drive import upload_post_to_drive

REGION_LABEL = {"korean": "국내", "overseas": "해외"}


async def process_one(
    article_id: int,
    account_handle: str,
    category: str,
    region: str,
) -> tuple[bool, str | None]:
    with db_session() as s:
        a = s.get(Article, article_id)
        if not a:
            logger.error(f"Article {article_id} not found")
            return False, None
        article_dict = {
            "id": a.id,
            "url": a.url,
            "source": a.source,
            "category": a.category,
            "title": a.title,
            "summary": a.summary,
            "content": a.content,
            "published_at": a.published_at,
        }
        post = Post(
            article_id=a.id,
            account_handle=account_handle,
            status="pending",
        )
        s.add(post)
        s.flush()
        post_id = post.id

    generator = get_generator()

    try:
        logger.info(
            f"[{account_handle}] Generating content for "
            f"{category}/{region}: {article_dict['title'][:50]}"
        )
        card = generator.generate_card_content(article_dict)
    except Exception:
        logger.exception("Generate failed")
        with db_session() as s:
            p = s.get(Post, post_id)
            p.status = "failed"
            p.error_log = f"generate: {traceback.format_exc()}"
        return False, None

    cover_data_uri = None
    try:
        cover_bytes = fetch_article_image(article_dict["url"])
        if cover_bytes:
            if verify_image_relevance(cover_bytes, article_dict["title"]):
                logger.info("og:image verified as relevant")
            else:
                logger.info("og:image not relevant, trying AI generation...")
                cover_bytes = generate_ai_image(
                    article_dict["title"], category,
                    summary=article_dict.get("summary", ""),
                )
        else:
            logger.info("No og:image, trying AI generation...")
            cover_bytes = generate_ai_image(
                article_dict["title"], category,
                summary=article_dict.get("summary", ""),
            )
        if cover_bytes:
            import base64
            b64 = base64.b64encode(cover_bytes).decode("ascii")
            cover_data_uri = f"data:image/jpeg;base64,{b64}"
            logger.info("Cover image ready")
    except Exception as e:
        logger.warning(f"Cover image fetch failed: {e}")

    today = datetime.now().strftime("%Y-%m-%d")
    region_label = REGION_LABEL.get(region, region)
    category_label = accounts_config.get_label_ko(category)
    folder_name = f"{region_label}_{category_label}"
    out_dir = PROJECT_ROOT / "data" / "output" / today / account_handle / folder_name

    try:
        await render_slides(
            card.raw_json, out_dir, article_dict["source"], category,
            handle=account_handle, cover_image=cover_data_uri,
        )
    except Exception:
        logger.exception("Render failed")
        with db_session() as s:
            p = s.get(Post, post_id)
            p.status = "failed"
            p.error_log = f"render: {traceback.format_exc()}"
        return False, None

    with db_session() as s:
        p = s.get(Post, post_id)
        p.slides_json = json.dumps(card.raw_json, ensure_ascii=False)
        p.caption = card.caption
        p.hashtags = json.dumps(card.hashtags, ensure_ascii=False)
        p.output_dir = str(out_dir)
        p.status = "rendered"

        a = s.get(Article, article_id)
        a.status = "generated"

    logger.info(f"[{account_handle}] Post {post_id} saved → {out_dir}")

    drive_url = None
    try:
        drive_url = upload_post_to_drive(out_dir)
        if drive_url:
            with db_session() as s:
                p = s.get(Post, post_id)
                p.status = "uploaded"
            logger.info(f"[{account_handle}] Uploaded to Drive: {drive_url}")
            shutil.rmtree(out_dir, ignore_errors=True)
            logger.info(f"[{account_handle}] Local files cleaned: {out_dir}")
    except Exception as e:
        logger.warning(f"Drive upload failed, keeping local files: {e}")

    return True, drive_url


def _cleanup_empty_dirs(base_dir: Path):
    if not base_dir.exists():
        return
    for child in sorted(base_dir.iterdir(), reverse=True):
        if child.is_dir():
            _cleanup_empty_dirs(child)
            if not any(child.iterdir()):
                child.rmdir()


async def run_pipeline(test: bool = False):
    init_db()
    logger.info("=== Pipeline start ===")

    fetched = fetch_all()
    logger.info(f"Fetched {fetched} new articles")

    assignments = select_for_all_accounts()

    total_assigned = sum(len(v) for v in assignments.values())
    if not assignments or total_assigned == 0:
        logger.warning("No articles selected. Pipeline done (nothing to process).")
        today = datetime.now().strftime("%Y-%m-%d")
        send_telegram_notification(date=today, total=0, success=0, failed=0)
        return

    if test:
        first_handle = next(iter(assignments))
        first_item = assignments[first_handle][0]
        assignments = {first_handle: [first_item]}
        logger.info(f"[TEST] 1건만 생성: {first_handle} / {first_item['category']} / {first_item['region']}")

    results = []
    drive_url = None
    for account_handle, items in assignments.items():
        for item in items:
            success, url = await process_one(
                article_id=item["article_id"],
                account_handle=account_handle,
                category=item["category"],
                region=item["region"],
            )
            results.append(success)
            if url and not drive_url:
                drive_url = url
            await asyncio.sleep(4)

    today_str = datetime.now().strftime("%Y-%m-%d")
    output_base = PROJECT_ROOT / "data" / "output" / today_str
    _cleanup_empty_dirs(output_base)

    ok = sum(1 for s in results if s)
    fail = sum(1 for s in results if not s)
    logger.info(f"=== Pipeline done: {ok} success, {fail} failed ===")

    send_telegram_notification(
        date=today_str,
        total=total_assigned,
        success=ok,
        failed=fail,
        drive_url=drive_url,
    )
