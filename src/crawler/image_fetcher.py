"""기사 URL에서 대표 이미지 추출, 커뮤니티 글 스크린샷."""
import asyncio
import base64
from io import BytesIO
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from loguru import logger
from PIL import Image

from config import settings

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    )
}


def fetch_article_image(url: str) -> bytes | None:
    """기사 URL에서 og:image 등 대표 이미지를 가져온다."""
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        logger.warning(f"Article page fetch failed: {e}")
        return None

    soup = BeautifulSoup(resp.text, "lxml")

    candidates = [
        ("meta[og:image]", soup.find("meta", property="og:image")),
        ("meta[twitter:image]", soup.find("meta", attrs={"name": "twitter:image"})),
    ]

    for label, tag in candidates:
        if tag and tag.get("content"):
            img_url = tag["content"]
            if not img_url.startswith("http"):
                img_url = urljoin(url, img_url)
            logger.info(f"Found {label}: {img_url}")
            img_bytes = _download_image(img_url)
            if img_bytes:
                return img_bytes

    for img_tag in soup.find_all("img"):
        src = img_tag.get("src", "")
        if not src or any(kw in src.lower() for kw in ("logo", "icon", "banner", "ad")):
            continue
        if not src.startswith("http"):
            src = urljoin(url, src)
        img_bytes = _download_image(src, min_size=10_000)
        if img_bytes:
            return img_bytes

    return None


def _download_image(url: str, min_size: int = 5_000) -> bytes | None:
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=15)
        if resp.status_code == 200 and len(resp.content) >= min_size:
            return resp.content
    except Exception as e:
        logger.debug(f"Image download failed: {url} → {e}")
    return None


def verify_image_relevance(image_bytes: bytes, title: str) -> bool:
    """gpt-4o-mini vision으로 이미지가 기사 제목과 관련 있는지 검증."""
    if not settings.openai_api_key or settings.openai_api_key == "sk-...":
        return True

    try:
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key)
        b64 = base64.b64encode(image_bytes).decode("ascii")

        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=10,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                f"뉴스 제목: \"{title}\"\n"
                                "이 이미지가 위 뉴스 제목의 내용과 관련이 있나요? "
                                "매체 로고만 있거나 내용과 전혀 무관한 이미지면 NO, "
                                "관련 있으면 YES. 한 단어로만 답해."
                            ),
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{b64}",
                                "detail": "low",
                            },
                        },
                    ],
                }
            ],
        )
        answer = resp.choices[0].message.content.strip().upper()
        is_relevant = "YES" in answer
        logger.info(f"Image relevance check: {answer} → {'relevant' if is_relevant else 'NOT relevant'}")
        return is_relevant
    except Exception as e:
        logger.warning(f"Image relevance check failed: {e}")
        return True


def generate_ai_image(title: str, category: str, summary: str = "") -> bytes | None:
    """OpenAI gpt-image-1으로 뉴스 기사 내용에 맞는 썸네일 이미지를 AI 생성한다."""
    if not settings.openai_api_key or settings.openai_api_key == "sk-...":
        logger.warning("No OpenAI API key for AI image generation")
        return None

    context = summary[:300] if summary else title
    prompt = (
        f"Create a photorealistic editorial news photograph that visually represents this news: "
        f"\"{title}\". Context: {context}. "
        f"Photojournalistic style, cinematic lighting, dramatic depth of field. "
        f"Must visually relate to the specific news topic, not a generic scene. "
        f"No text, no words, no letters, no watermarks, no UI elements. "
        f"Clean composition suitable as a background with text overlay. "
        f"Aspect ratio 3:4."
    )

    try:
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key)
        logger.info("Generating AI thumbnail with DALL-E...")
        response = client.images.generate(
            model="gpt-image-1",
            prompt=prompt,
            size="1024x1024",
            quality="low",
            n=1,
        )
        img_data = response.data[0]
        if img_data.b64_json:
            logger.info("AI thumbnail generated successfully")
            return base64.b64decode(img_data.b64_json)
        elif img_data.url:
            img_resp = requests.get(img_data.url, timeout=30)
            if img_resp.status_code == 200:
                logger.info("AI thumbnail generated successfully")
                return img_resp.content
    except Exception as e:
        logger.warning(f"DALL-E generation failed: {e}")

    return None


def fetch_post_images(url: str, max_count: int = 3) -> list[bytes]:
    """커뮤니티 글에서 실제 이미지를 최대 max_count개 추출한다."""
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        logger.warning(f"Post page fetch failed for images: {e}")
        return []

    soup = BeautifulSoup(resp.text, "lxml")
    images = []

    og = soup.find("meta", property="og:image")
    if og and og.get("content"):
        img_url = og["content"]
        if not img_url.startswith("http"):
            from urllib.parse import urljoin
            img_url = urljoin(url, img_url)
        img_bytes = _download_image(img_url, min_size=10_000)
        if img_bytes:
            images.append(img_bytes)

    for container_sel in ["div.write_div", "div.xe_content", "div.rd_body",
                          "div#contentArea", "div.memo_content", "div#cnts",
                          "article", "div.content"]:
        container = soup.select_one(container_sel)
        if container:
            for img_tag in container.select("img"):
                if len(images) >= max_count:
                    break
                src = img_tag.get("src") or img_tag.get("data-src") or ""
                if not src:
                    continue
                if any(kw in src.lower() for kw in ("logo", "icon", "banner", "ad", "emoji",
                                                     "sticker", "gif", "1x1", "spacer")):
                    continue
                if not src.startswith("http"):
                    from urllib.parse import urljoin
                    src = urljoin(url, src)
                if src in [None]:
                    continue
                img_bytes = _download_image(src, min_size=15_000)
                if img_bytes and img_bytes not in images:
                    images.append(img_bytes)
            break

    logger.info(f"Fetched {len(images)} real images from {url[:60]}")
    return images


def analyze_cover_layout(img_bytes: bytes) -> str:
    """이미지 밝기 분포를 분석해서 텍스트 배치 위치를 결정한다."""
    try:
        img = Image.open(BytesIO(img_bytes)).convert("L")
        w, h = img.size

        top_h = int(h * 0.4)
        bot_start = int(h * 0.6)

        top_data = list(img.crop((0, 0, w, top_h)).getdata())
        bot_data = list(img.crop((0, bot_start, w, h)).getdata())

        top_avg = sum(top_data) / len(top_data)
        bot_avg = sum(bot_data) / len(bot_data)

        diff = abs(top_avg - bot_avg)
        logger.info(f"Cover layout analysis: top={top_avg:.0f} bot={bot_avg:.0f} diff={diff:.0f}")

        if diff < 15:
            return "center"
        if bot_avg <= top_avg:
            return "bottom"
        return "top"
    except Exception as e:
        logger.warning(f"Cover layout analysis failed: {e}")
        return "bottom"


CONTENT_SELECTORS = {
    "dcinside": ["div.write_div", "div.writing_view_box"],
    "theqoo": ["div.rd_body", "article"],
    "natepann": ["div#contentArea", "div.posting_area"],
    "humoruniv": ["div#cnts", "div.post_content"],
    "instiz": ["div.memo_content", "div.xe_content"],
    "fmkorea": ["div.xe_content", "article"],
}

SLIDE_HEIGHT = 1350
SLIDE_WIDTH = 1080


def _split_screenshot(full_img_bytes: bytes, max_slides: int = 4) -> list[bytes]:
    """긴 스크린샷을 1080×1350 슬라이드 여러 장으로 분할한다."""
    img = Image.open(BytesIO(full_img_bytes))
    w, h = img.size

    scale = SLIDE_WIDTH / w
    new_w = SLIDE_WIDTH
    new_h = int(h * scale)
    img = img.resize((new_w, new_h), Image.LANCZOS)

    if new_h <= SLIDE_HEIGHT:
        buf = BytesIO()
        canvas = Image.new("RGB", (SLIDE_WIDTH, SLIDE_HEIGHT), (250, 250, 250))
        y_offset = (SLIDE_HEIGHT - new_h) // 2
        canvas.paste(img, (0, y_offset))
        canvas.save(buf, format="JPEG", quality=92)
        return [buf.getvalue()]

    slides = []
    y = 0
    while y < new_h and len(slides) < max_slides:
        crop_h = min(SLIDE_HEIGHT, new_h - y)
        canvas = Image.new("RGB", (SLIDE_WIDTH, SLIDE_HEIGHT), (250, 250, 250))
        cropped = img.crop((0, y, new_w, y + crop_h))
        canvas.paste(cropped, (0, 0))
        buf = BytesIO()
        canvas.save(buf, format="JPEG", quality=92)
        slides.append(buf.getvalue())
        y += SLIDE_HEIGHT

    return slides


def _is_valid_screenshot(img_bytes: bytes, min_size: int = 30_000) -> bool:
    """스크린샷이 유효한지 검증 — 거의 흰색이면 로딩 스피너만 찍힌 것."""
    if len(img_bytes) < min_size:
        return False
    try:
        img = Image.open(BytesIO(img_bytes)).convert("RGB")
        thumb = img.resize((100, 125))
        pixels = list(thumb.getdata())
        white_ish = sum(1 for r, g, b in pixels if r > 240 and g > 240 and b > 240)
        if white_ish / len(pixels) > 0.85:
            return False
    except Exception:
        return False
    return True


async def screenshot_post_content(url: str, site: str) -> list[bytes]:
    """Playwright로 커뮤니티 글의 콘텐츠 영역을 스크린샷한다."""
    from playwright.async_api import async_playwright

    selectors = CONTENT_SELECTORS.get(site, ["article", "div.content"])

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page(viewport={"width": 1080, "height": 900})
            await page.goto(url, wait_until="domcontentloaded", timeout=15000)

            element = None
            for sel in selectors:
                element = await page.query_selector(sel)
                if element:
                    break

            if not element:
                logger.warning(f"No content element found for {site}: {url[:60]}")
                await browser.close()
                return []

            await page.evaluate("""() => {
                // lazy-load 이미지 강제 로드
                document.querySelectorAll('img[data-src]').forEach(img => {
                    if (!img.src || img.src.includes('blank') || img.src.includes('loading')) {
                        img.src = img.dataset.src;
                    }
                });
                document.querySelectorAll('img[data-lazy-src]').forEach(img => {
                    img.src = img.dataset.lazySrc || img.dataset['lazy-src'];
                });
                document.querySelectorAll('img[data-original]').forEach(img => {
                    img.src = img.dataset.original;
                });
                // 광고/불필요 요소 제거
                document.querySelectorAll(
                    'iframe, .ad, .ads, [class*="banner"], [id*="ad-"], '
                    + '.comment_box, .comment_area, #comment, .cmt_list, '
                    + '.btn_area, .view_bottom_area, .relate_area'
                ).forEach(el => el.remove());
            }""")

            # 콘텐츠 끝까지 스크롤 → lazy-load 트리거
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(2500)
            await page.evaluate("window.scrollTo(0, 0)")
            await page.wait_for_timeout(1000)

            screenshot_bytes = await element.screenshot(type="jpeg", quality=92)
            await browser.close()

            if len(screenshot_bytes) < 10_000:
                logger.warning(f"Screenshot too small ({len(screenshot_bytes)} bytes)")
                return []

            slides = _split_screenshot(screenshot_bytes)
            valid = [s for s in slides if _is_valid_screenshot(s)]
            if not valid:
                logger.warning(f"All screenshots invalid (mostly white) for {url[:60]}")
                return []

            logger.info(f"Captured {len(valid)} valid screenshot slide(s) from {site}: {url[:60]}")
            return valid

    except Exception as e:
        logger.warning(f"Screenshot failed for {url[:60]}: {e}")
        return []


def get_cover_image(article_url: str, title: str, category: str) -> str | None:
    """표지 배경 이미지를 data URI로 반환한다.

    1순위: 기사 og:image
    2순위: AI 생성
    실패 시: None (기본 그라데이션 배경 사용)
    """
    img_bytes = fetch_article_image(article_url)

    if not img_bytes:
        logger.info("No article image found, trying AI generation...")
        img_bytes = generate_ai_image(title, category)

    if not img_bytes:
        logger.warning("No cover image available, using default gradient")
        return None

    b64 = base64.b64encode(img_bytes).decode("ascii")
    return f"data:image/jpeg;base64,{b64}"
