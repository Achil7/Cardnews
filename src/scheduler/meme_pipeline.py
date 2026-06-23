"""밈/유머 카드뉴스 파이프라인 — 커뮤니티 크롤링 → 선별 → 콘텐츠 생성 → 렌더링 → 업로드."""
import asyncio
import base64
import json
import re
import shutil
import traceback
from datetime import datetime, timezone, timedelta
from pathlib import Path

from loguru import logger

from config import PROJECT_ROOT, accounts_config
from src.crawler.community_fetcher import fetch_community_posts
from src.crawler.image_fetcher import fetch_post_images, screenshot_post_content, generate_ai_image
from src.db.models import Post
from src.db.repository import db_session, init_db
from src.generator.meme_generator import MemeGenerator
from src.notifier.telegram import send_telegram_notification
from src.renderer.render import render_slides, _split_content_to_slides
from src.selector.meme_ranker import select_meme_posts
from src.uploader.drive import upload_post_to_drive

KST = timezone(timedelta(hours=9))


def _bytes_to_data_uri(img_bytes: bytes) -> str:
    return f"data:image/jpeg;base64,{base64.b64encode(img_bytes).decode('ascii')}"


def _fetch_cover_image(
    post_url: str | None, card_data: dict = None, category: str = "",
) -> str | None:
    """커버 이미지: 실제 이미지 우선, 없으면 AI 생성."""
    if post_url:
        logger.info(f"Fetching cover image from: {post_url[:60]}")
        real_images = fetch_post_images(post_url, max_count=1)
        if real_images:
            logger.info("Cover: real image from source")
            return _bytes_to_data_uri(real_images[0])

    prompt = (card_data or {}).get("image_prompt", "")
    if prompt:
        logger.info(f"No real image, AI cover: {prompt[:60]}")
        img_bytes = generate_ai_image(prompt, category, summary=prompt)
        if img_bytes:
            return _bytes_to_data_uri(img_bytes)

    logger.info("No cover image available")
    return None


async def _get_content_slides(post_data: dict) -> tuple[list, str]:
    """콘텐츠 슬라이드: 스크린샷 우선, 텍스트 폴백."""
    url = post_data.get("url", "")
    source_name = post_data.get("source_name", "")
    site = source_name.split("_")[0] if source_name else ""

    if url and site:
        screenshots = await screenshot_post_content(url, site)
        if screenshots:
            return [_bytes_to_data_uri(s) for s in screenshots], "screenshot"

    content = post_data.get("content", "")
    if content:
        chunks = _split_content_to_slides(content, max_lines=8)
        if chunks:
            return chunks, "text"

    return [], "text"


def _title_slug(title: str, max_len: int = 20) -> str:
    """제목에서 폴더명용 슬러그 생성. 특수문자 제거, 공백→언더스코어."""
    cleaned = re.sub(r'\[.*?\]', '', title).strip()
    cleaned = re.sub(r'[^\w가-힣\s]', '', cleaned).strip()
    slug = cleaned[:max_len].strip().replace(' ', '_')
    return slug or "post"


async def process_meme(
    post_data: dict,
    account_handle: str,
    demographic: str,
    post_seq: int = 1,
) -> tuple[bool, str | None]:
    meme_cat = accounts_config.get_meme_category(demographic)
    if not meme_cat:
        logger.error(f"No meme category for demographic: {demographic}")
        return False, None

    title = post_data["title"]
    source_name = post_data["source_name"]

    with db_session() as s:
        post = Post(
            content_type="meme",
            demographic=demographic,
            research_topic=title,
            account_handle=account_handle,
            status="pending",
        )
        s.add(post)
        s.flush()
        post_id = post.id

    generator = MemeGenerator()

    try:
        article_dict = {
            "title": title,
            "source": source_name,
            "category": meme_cat.id,
            "demographic": demographic,
            "content": post_data.get("content") or "",
            "top_comments": post_data.get("top_comments") or "",
        }
        logger.info(f"[{account_handle}] Generating meme: {title[:50]}")
        card = generator.generate_card_content(article_dict)
    except Exception:
        logger.exception("Meme generate failed")
        with db_session() as s:
            p = s.get(Post, post_id)
            p.status = "failed"
            p.error_log = f"generate: {traceback.format_exc()}"
        return False, None

    post_url = post_data.get("url")
    cover_image = _fetch_cover_image(post_url, card.raw_json, meme_cat.id)

    try:
        content_data, content_mode = await _get_content_slides(post_data)
        logger.info(f"Content mode: {content_mode}, slides: {len(content_data)}")
    except Exception as e:
        logger.warning(f"Content slides failed: {e}")
        content_data, content_mode = [], "text"

    card.raw_json["_content_mode"] = content_mode
    card.raw_json["_content_data"] = content_data

    now_kst = datetime.now(KST)
    today = now_kst.strftime("%Y-%m-%d")
    date_short = now_kst.strftime("%m%d")
    hour_tag = now_kst.strftime("%H")
    slug = _title_slug(title)
    post_folder = f"{post_seq}_{slug}"
    file_prefix = ""
    out_dir = PROJECT_ROOT / "data" / "output" / today / account_handle / meme_cat.label_ko / post_folder

    try:
        await render_slides(
            card.raw_json, out_dir, source_name, meme_cat.id,
            handle=account_handle,
            cover_image=cover_image,
            slide_images=[],
            file_prefix=file_prefix,
            content_type="meme",
        )
    except Exception:
        logger.exception("Meme render failed")
        with db_session() as s:
            p = s.get(Post, post_id)
            p.status = "failed"
            p.error_log = f"render: {traceback.format_exc()}"
        return False, None

    with db_session() as s:
        p = s.get(Post, post_id)
        save_json = {k: v for k, v in card.raw_json.items() if not k.startswith("_")}
        p.slides_json = json.dumps(save_json, ensure_ascii=False)
        p.caption = card.caption
        p.hashtags = json.dumps(card.hashtags, ensure_ascii=False)
        p.output_dir = str(out_dir)
        p.status = "rendered"

    logger.info(f"[{account_handle}] Meme post {post_id} saved → {out_dir}")

    drive_url = None
    try:
        drive_url = upload_post_to_drive(out_dir)
        if drive_url:
            with db_session() as s:
                p = s.get(Post, post_id)
                p.status = "uploaded"
            logger.info(f"[{account_handle}] Uploaded to Drive: {drive_url}")
            shutil.rmtree(out_dir, ignore_errors=True)
    except Exception as e:
        logger.warning(f"Drive upload failed, keeping local files: {e}")

    from src.db.models import CommunityPost
    cp_id = post_data.get("id")
    if cp_id:
        with db_session() as s:
            cp = s.get(CommunityPost, cp_id)
            if cp:
                cp.status = "used"

    return True, drive_url


async def run_meme_pipeline(test: bool = False):
    init_db()
    logger.info("=== Meme Pipeline start ===")

    meme_accounts = accounts_config.enabled_meme_accounts
    if not meme_accounts:
        logger.warning("No enabled meme accounts. Done.")
        return

    logger.info("Step 1: Crawling community posts...")
    saved_count = fetch_community_posts()
    logger.info(f"Step 1 done: {saved_count} new posts saved")

    all_demographics = set()
    for account in meme_accounts:
        all_demographics.update(account.demographics)

    posts_per = 3

    logger.info(f"Step 2: Selecting posts for {len(all_demographics)} demographics...")
    selections = select_meme_posts(list(all_demographics), posts_per_demographic=posts_per)

    results = []
    drive_url = None

    for account in meme_accounts:
        for demographic in account.demographics:
            posts = selections.get(demographic, [])
            if not posts:
                logger.warning(f"No community posts selected for {demographic}")
                continue

            if test:
                posts = posts[:1]
                logger.info(f"[TEST] 1건만 생성: {account.handle} / {demographic}")

            for seq_i, post_data in enumerate(posts, 1):
                success, url = await process_meme(
                    post_data, account.handle, demographic,
                    post_seq=seq_i,
                )
                results.append(success)
                if url and not drive_url:
                    drive_url = url
                await asyncio.sleep(2)

                if test and success:
                    break
            if test:
                break
        if test:
            break

    now_kst = datetime.now(KST)
    today_str = now_kst.strftime("%Y-%m-%d")

    ok = sum(1 for s in results if s)
    fail = sum(1 for s in results if not s)
    logger.info(f"=== Meme Pipeline done: {ok} success, {fail} failed ===")

    send_telegram_notification(
        date=today_str,
        total=len(results),
        success=ok,
        failed=fail,
        drive_url=drive_url,
    )
