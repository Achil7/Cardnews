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


def render_html(
    slide: dict, index: int, total: int, source: str, category: str, handle: str = ""
) -> str:
    accent = _get_accent(category)
    common = {
        "handle": handle,
        "date": datetime.now().strftime("%Y.%m.%d"),
        "index": index,
        "index_padded": f"{index:02d}",
        "total": total,
        "source": source,
        "category": category.upper(),
        "accent_color": accent,
    }

    if slide["type"] == "cover":
        tpl = env.get_template("card_cover.html")
        return tpl.render(
            **common,
            title=slide["title"],
            subtitle=slide["subtitle"],
            cover_image=slide.get("cover_image"),
        )

    if slide["type"] == "body":
        tpl = env.get_template("card_body.html")
        return tpl.render(**common, heading=slide["heading"], body=slide["body"])

    if slide["type"] == "outro":
        tpl = env.get_template("card_outro.html")
        outro_common = {**common, "source": slide.get("source", source)}
        return tpl.render(
            **outro_common,
            cta=slide.get("cta", "저장하고 공유해주세요!"),
        )

    raise ValueError(f"Unknown slide type: {slide['type']}")


def _inline_css(html: str) -> str:
    css = _load_css()
    html = html.replace(
        '<link rel="stylesheet" href="styles.css">',
        f"<style>\n{css}\n</style>",
    )
    return html


async def render_post(
    post_data: dict,
    output_dir: Path,
    source: str,
    category: str,
    handle: str = "",
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    slides = post_data["slides"]
    total = len(slides)
    paths = []

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(
            viewport={"width": 1080, "height": 1350},
            device_scale_factor=1,
        )

        for i, slide in enumerate(slides, start=1):
            html = render_html(slide, i, total, source, category, handle)
            html = _inline_css(html)

            page = await ctx.new_page()
            await page.set_content(html, wait_until="networkidle")
            out_path = output_dir / f"slide_{i}.jpg"
            await page.screenshot(
                path=str(out_path), type="jpeg", quality=92, full_page=False
            )
            await page.close()
            paths.append(out_path)
            logger.info(f"Rendered {out_path.name}")

        await browser.close()

    caption_text = post_data.get("caption", "") + "\n\n" + " ".join(
        post_data.get("hashtags", [])
    )
    (output_dir / "caption.txt").write_text(caption_text, encoding="utf-8")

    return paths
