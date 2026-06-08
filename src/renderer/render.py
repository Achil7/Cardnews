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


async def render_slides(
    card_data: dict,
    output_dir: Path,
    source: str,
    category: str,
    handle: str = "",
    cover_image: str | None = None,
    file_prefix: str = "",
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)

    prefix = f"{file_prefix}_" if file_prefix else ""
    accent = _get_accent(category)
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
    cover_html = _inline_css(cover_html)

    body_tpl = env.get_template("card_body.html")
    body_htmls = []
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
        body_htmls.append(_inline_css(html))

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(
            viewport={"width": 1080, "height": 1350},
            device_scale_factor=1,
        )
        page = await ctx.new_page()

        await page.set_content(cover_html, wait_until="networkidle")
        slide_1 = output_dir / f"{prefix}1.jpg"
        await page.screenshot(path=str(slide_1), type="jpeg", quality=92, full_page=False)
        logger.info(f"Rendered {prefix}1.jpg (cover)")

        for i, bhtml in enumerate(body_htmls):
            slide_path = output_dir / f"{prefix}{i + 2}.jpg"
            await page.set_content(bhtml, wait_until="networkidle")
            await page.screenshot(path=str(slide_path), type="jpeg", quality=92, full_page=False)
            logger.info(f"Rendered {prefix}{i + 2}.jpg (body)")

        outro_tpl = env.get_template("card_outro.html")
        outro_html = outro_tpl.render(
            handle=handle,
            source=source,
            accent_color=accent,
        )
        outro_html = _inline_css(outro_html)
        outro_idx = len(body_cards) + 2
        outro_path = output_dir / f"{prefix}{outro_idx}.jpg"
        await page.set_content(outro_html, wait_until="networkidle")
        await page.screenshot(path=str(outro_path), type="jpeg", quality=92, full_page=False)
        logger.info(f"Rendered {prefix}{outro_idx}.jpg (outro)")

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

    return slide_1
