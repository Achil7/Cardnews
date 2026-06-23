import base64
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from loguru import logger
from playwright.async_api import async_playwright

from config import accounts_config

TEMPLATE_DIR = Path(__file__).parent / "templates"

env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))

ACCENT_COLORS = {c.id: c.accent_color for c in accounts_config.categories}
for mc in accounts_config.meme_categories:
    ACCENT_COLORS.setdefault(mc.id, mc.accent_color)
ACCENT_COLORS.setdefault("general", "#4A6CF7")

MEME_BG_COLORS = [
    "#FF3B30",
    "#FF9500",
    "#007AFF",
    "#AF52DE",
    "#FF2D55",
    "#34C759",
    "#5856D6",
]

_css_cache: str | None = None


def _load_css() -> str:
    global _css_cache
    if _css_cache is None:
        _css_cache = (TEMPLATE_DIR / "styles.css").read_text(encoding="utf-8")
    return _css_cache


def _get_accent(category: str) -> str:
    return ACCENT_COLORS.get(category, "#4A6CF7")


def _inline_css(html: str) -> str:
    css = _load_css()
    html = html.replace(
        '<link rel="stylesheet" href="styles.css">',
        f"<style>\n{css}\n</style>",
    )
    return html


def _deduplicate_caption(text: str) -> str:
    lines = text.strip().split("\n")
    seen = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            seen.append(line)
            continue
        if stripped not in [s.strip() for s in seen]:
            seen.append(line)
    return "\n".join(seen).strip()


async def render_slides(
    card_data: dict,
    output_dir: Path,
    source: str,
    category: str,
    handle: str = "",
    cover_image: str | None = None,
    slide_images: list[str | None] | None = None,
    file_prefix: str = "",
    content_type: str = "news",
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)

    prefix = f"{file_prefix}_" if file_prefix else ""
    accent = _get_accent(category)

    is_meme = content_type == "meme"

    if is_meme:
        all_htmls = _build_meme_slides(
            card_data, handle, accent, cover_image, slide_images,
        )
    else:
        all_htmls = _build_news_slides(
            card_data, handle, source, category, accent, cover_image,
        )

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(
            viewport={"width": 1080, "height": 1350},
            device_scale_factor=1,
        )
        page = await ctx.new_page()

        first_slide = None
        for i, slide_html in enumerate(all_htmls):
            slide_path = output_dir / f"{prefix}{i + 1}.jpg"
            await page.set_content(slide_html, wait_until="networkidle")
            await page.screenshot(
                path=str(slide_path), type="jpeg", quality=92, full_page=False,
            )
            logger.info(f"Rendered {prefix}{i + 1}.jpg")
            if i == 0:
                first_slide = slide_path

        await page.close()
        await browser.close()

    caption = card_data.get("caption", "")
    hashtags_list = card_data.get("hashtags", [])
    hashtags_str = " ".join(hashtags_list)

    if hashtags_str and hashtags_str not in caption:
        caption_text = caption + "\n\n" + hashtags_str
    else:
        caption_text = caption

    caption_text = _deduplicate_caption(caption_text)
    (output_dir / f"{prefix}caption.txt").write_text(caption_text, encoding="utf-8")

    return first_slide


def _split_content_to_slides(content: str, max_lines: int = 8) -> list[list[str]]:
    """원문 텍스트를 슬라이드 크기 청크로 나눈다."""
    lines = [line.strip() for line in content.split("\n")]
    lines = [l for l in lines if l]
    if not lines:
        return []

    slides = []
    current = []
    for line in lines:
        current.append(line)
        if len(current) >= max_lines:
            slides.append(current)
            current = []
    if current:
        slides.append(current)

    return slides[:4]


def _build_meme_slides(
    card_data: dict,
    handle: str,
    accent: str,
    cover_image: str | None,
    slide_images: list[str | None] | None,
) -> list[str]:
    htmls = []
    hook_text = card_data.get("hook_text", card_data.get("title", ""))
    punchline = card_data.get("punchline", "")
    content_mode = card_data.get("_content_mode", "text")
    content_data = card_data.get("_content_data", [])

    from src.crawler.image_fetcher import analyze_cover_layout

    layout = "center"
    if cover_image:
        try:
            img_bytes = base64.b64decode(cover_image.split(",")[1])
            layout = analyze_cover_layout(img_bytes)
        except Exception:
            layout = "bottom"
    logger.info(f"Cover layout: {layout}")

    hook_tpl = env.get_template("card_meme_hook.html")
    hook_html = hook_tpl.render(
        cover_image=cover_image,
        text=hook_text,
        handle=handle,
        layout=layout,
    )
    htmls.append(_inline_css(hook_html))

    if content_mode == "screenshot" and content_data:
        ss_tpl = env.get_template("card_meme_screenshot.html")
        for img_uri in content_data:
            ss_html = ss_tpl.render(image=img_uri, handle=handle)
            htmls.append(_inline_css(ss_html))
    elif content_data:
        text_tpl = env.get_template("card_meme_text.html")
        for text_lines in content_data:
            slide_html = text_tpl.render(
                lines=text_lines,
                punchline="",
                accent_color="",
                handle=handle,
            )
            htmls.append(_inline_css(slide_html))

    punch_color = MEME_BG_COLORS[hash(hook_text) % len(MEME_BG_COLORS)]
    if punchline:
        punch_tpl = env.get_template("card_meme_punchline.html")
        punch_html = punch_tpl.render(
            bg_color=punch_color,
            punchline=punchline,
            handle=handle,
        )
        htmls.append(_inline_css(punch_html))

    outro_tpl = env.get_template("card_meme_outro.html")
    bg = MEME_BG_COLORS[(len(htmls) + 1) % len(MEME_BG_COLORS)]
    outro_html = outro_tpl.render(bg_color=bg, handle=handle)
    htmls.append(_inline_css(outro_html))

    return htmls


def _build_news_slides(
    card_data: dict,
    handle: str,
    source: str,
    category: str,
    accent: str,
    cover_image: str | None,
) -> list[str]:
    htmls = []
    body_cards = card_data.get("body_cards", [])
    total = 1 + len(body_cards) + 1

    cover_tpl = env.get_template("card_cover.html")
    cover_html = cover_tpl.render(
        handle=handle,
        date=datetime.now(KST).strftime("%Y.%m.%d"),
        index=1,
        index_padded="01",
        total=total,
        source=source,
        category=category.upper(),
        accent_color=accent,
        title=card_data["title"],
        subtitle=card_data.get("subtitle", ""),
        cover_image=cover_image,
    )
    htmls.append(_inline_css(cover_html))

    body_tpl = env.get_template("card_body.html")
    for i, card in enumerate(body_cards):
        idx = i + 2
        html = body_tpl.render(
            handle=handle,
            index=idx,
            index_padded=f"{idx:02d}",
            total=total,
            category=category.upper(),
            accent_color=accent,
            heading=card["heading"],
            body=card["body"],
        )
        htmls.append(_inline_css(html))

    outro_tpl = env.get_template("card_outro.html")
    outro_html = outro_tpl.render(
        handle=handle,
        source=source,
        accent_color=accent,
    )
    htmls.append(_inline_css(outro_html))

    return htmls
