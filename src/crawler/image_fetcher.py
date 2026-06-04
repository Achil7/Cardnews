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


def generate_ai_image(title: str, category: str) -> bytes | None:
    """Gemini Imagen으로 뉴스 썸네일 이미지를 AI 생성한다."""
    if not settings.gemini_api_key:
        logger.warning("No Gemini API key for AI image generation")
        return None

    category_scenes = {
        "politics": (
            "Korean National Assembly building exterior at night, "
            "political podium with many microphones, dramatic spotlight beams, "
            "silhouette of a suited figure, deep navy and red tones"
        ),
        "economy": (
            "modern stock exchange trading floor with glowing screens, "
            "financial charts and candlestick graphs projected on glass walls, "
            "golden and green accent lighting, city skyline through windows"
        ),
        "world": (
            "United Nations style circular assembly hall, "
            "multiple national flags hanging in formation, "
            "warm golden lighting, diplomatic atmosphere, globe motif"
        ),
        "tech": (
            "close-up of glowing blue circuit board with data streams, "
            "holographic interface projections, server room with blue LED lights, "
            "futuristic and clean, cyan and purple tones"
        ),
        "entertainment": (
            "Hollywood red carpet premiere with golden spotlights, "
            "movie cameras flashing, velvet ropes, glamorous stage setting, "
            "warm golden and magenta lighting"
        ),
        "health": (
            "modern medical research laboratory with glowing microscopes, "
            "DNA helix hologram, clean white and blue sterile environment, "
            "subtle green accent lighting suggesting wellness and vitality"
        ),
        "sports": (
            "grand stadium at night with dramatic floodlights, "
            "vast green field, cheering crowd silhouettes in the stands, "
            "dynamic motion blur, electric blue and orange tones"
        ),
        "general": (
            "professional TV broadcast studio with multiple screens, "
            "camera equipment silhouettes, breaking news atmosphere, "
            "dramatic studio lighting with blue and white tones"
        ),
    }
    scene = category_scenes.get(category, category_scenes["general"])

    prompt = (
        f"A cinematic editorial news photograph for Instagram. "
        f"Scene: {scene}. "
        f"Ultra high quality, photorealistic, dramatic depth of field. "
        f"Dark moody atmosphere with professional editorial lighting. "
        f"Must look like a real editorial photograph, not a graphic design. "
        f"Absolutely no text, no words, no letters, no watermarks, no UI elements. "
        f"Clean composition suitable as a background with text overlay. "
        f"Aspect ratio 3:4."
    )

    try:
        from google import genai

        client = genai.Client(api_key=settings.gemini_api_key)
        logger.info("Generating AI thumbnail with Imagen...")
        response = client.models.generate_images(
            model="imagen-3.0-generate-002",
            prompt=prompt,
            config=genai.types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio="3:4",
                safety_filter_level="BLOCK_ONLY_HIGH",
            ),
        )
        if response.generated_images:
            logger.info("AI thumbnail generated successfully")
            return response.generated_images[0].image.image_bytes
    except Exception as e:
        logger.warning(f"Imagen generation failed: {e}")

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=settings.gemini_api_key)
        logger.info("Trying Gemini native image generation...")
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=(
                f"Generate an image: {prompt}"
            ),
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"],
            ),
        )
        for part in response.candidates[0].content.parts:
            if part.inline_data is not None:
                logger.info("Gemini native image generated successfully")
                return part.inline_data.data
    except Exception as e:
        logger.warning(f"Gemini native image generation failed: {e}")

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
