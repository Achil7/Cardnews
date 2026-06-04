"""기사 URL에서 대표 이미지 추출, 실패 시 AI 생성 fallback."""
import base64
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from loguru import logger

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
