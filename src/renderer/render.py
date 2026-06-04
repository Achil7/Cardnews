from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from loguru import logger
from playwright.async_api import async_playwright

from config import accounts_config

TEMPLATE_DIR = Path(__file__).parent / "templates"

env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))

ACCENT_COLORS = {c.id: c.accent_color for c in accounts_config.categories}
ACCENT_COLORS.setdefault("general", "#4A6CF7")

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


async def render_thumbnail(
    card_data: dict,
    output_dir: Path,
    source: str,
    category: str,
    handle: str = "",
    cover_image: str | None = None,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)

    accent = _get_accent(category)
    tpl = env.get_template("card_cover.html")
    html = tpl.render(
        handle=handle,
        date=datetime.now().strftime("%Y.%m.%d"),
        index=1,
        index_padded="01",
        total=1,
        source=source,
        category=category.upper(),
        accent_color=accent,
        title=card_data["title"],
        subtitle=card_data.get("subtitle", ""),
        cover_image=cover_image,
    )
    html = _inline_css(html)

    thumb_path = output_dir / "thumbnail.jpg"

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(
            viewport={"width": 1080, "height": 1350},
            device_scale_factor=1,
        )
        page = await ctx.new_page()
        await page.set_content(html, wait_until="networkidle")
        await page.screenshot(
            path=str(thumb_path), type="jpeg", quality=92, full_page=False
        )
        await page.close()
        await browser.close()

    logger.info(f"Rendered {thumb_path.name}")

    caption = card_data.get("caption", "")
    hashtags_list = card_data.get("hashtags", [])
    hashtags_str = " ".join(hashtags_list)

    if hashtags_str and hashtags_str not in caption:
        caption_text = caption + "\n\n" + hashtags_str
    else:
        caption_text = caption

    caption_text = _deduplicate_caption(caption_text)
    (output_dir / "caption.txt").write_text(caption_text, encoding="utf-8")

    return thumb_path
