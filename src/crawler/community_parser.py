"""커뮤니티 사이트별 HTML 파서 — 목록 페이지 + 상세 페이지."""
import re
from bs4 import BeautifulSoup
from loguru import logger

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8",
}


def parse_listing(site: str, html: str) -> list[dict]:
    parser = _LISTING_PARSERS.get(site)
    if not parser:
        logger.warning(f"No listing parser for site: {site}")
        return []
    try:
        return parser(html)
    except Exception as e:
        logger.error(f"[{site}] listing parse failed: {e}")
        return []


def parse_post_detail(site: str, html: str) -> dict:
    parser = _DETAIL_PARSERS.get(site)
    if not parser:
        return _generic_detail(html)
    try:
        return parser(html)
    except Exception as e:
        logger.error(f"[{site}] detail parse failed: {e}")
        return {}


def _parse_int(text: str) -> int:
    return int(re.sub(r"[^\d]", "", text or "0") or "0")


# ──────────────────────────── FMKorea ────────────────────────────

def _fmkorea_listing(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    posts = []
    for li in soup.select("li.li"):
        a = li.select_one("a.hotdeal_var8")
        if not a:
            continue
        href = a.get("href", "")
        title_el = a.select_one("span.ellipsis-target")
        title = title_el.get_text(strip=True) if title_el else a.get_text(strip=True)
        title = re.sub(r"\[\d+\]$", "", title).strip()

        cmt = li.select_one("span.comment_count")
        cmt_count = _parse_int(cmt.get_text()) if cmt else 0

        likes_el = li.select_one("span.count")
        likes = _parse_int(likes_el.get_text()) if likes_el else 0

        srl_match = re.search(r"document_srl=(\d+)", href)
        url = f"https://www.fmkorea.com/{srl_match.group(1)}" if srl_match else f"https://www.fmkorea.com{href}"

        posts.append({
            "url": url,
            "title": title,
            "likes": likes,
            "comment_count": cmt_count,
            "views": 0,
        })
    return posts


def _fmkorea_detail(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    article = soup.select_one("div.xe_content") or soup.select_one("article")
    content = article.get_text("\n", strip=True)[:5000] if article else ""
    comments = _extract_comments_generic(soup, "div.fdb_lst_ul li, div.comment_content")
    return {"content": content, "top_comments": comments}


# ──────────────────────────── DC Inside ────────────────────────────

def _dcinside_listing(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    posts = []
    for tr in soup.select("tr.ub-content"):
        num_td = tr.select_one("td.gall_num")
        if not num_td or not num_td.get_text(strip=True).isdigit():
            continue

        td_title = tr.select_one("td.gall_tit")
        if not td_title:
            continue
        a = td_title.select_one('a[href*="/board/view/"]')
        if not a:
            continue

        title = a.get_text(strip=True)
        title = re.sub(r"\[\d+\]$", "", title).strip()
        href = a.get("href", "")
        url = f"https://gall.dcinside.com{href}" if href.startswith("/") else href

        reply = td_title.select_one(".reply_numbox")
        cmt = _parse_int(reply.get_text()) if reply else 0

        views_td = tr.select_one("td.gall_count")
        views = _parse_int(views_td.get_text()) if views_td else 0

        rec_td = tr.select_one("td.gall_recommend")
        likes = _parse_int(rec_td.get_text()) if rec_td else 0

        posts.append({
            "url": url,
            "title": title,
            "likes": likes,
            "comment_count": cmt,
            "views": views,
        })
    return posts


def _dcinside_detail(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    article = soup.select_one("div.write_div") or soup.select_one("div.writing_view_box")
    content = article.get_text("\n", strip=True)[:5000] if article else ""
    comments = _extract_comments_generic(
        soup, "li.ub-content p.usertxt, div.comment_dccon"
    )
    return {"content": content, "top_comments": comments}


# ──────────────────────────── TheQoo ────────────────────────────

def _theqoo_listing(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    posts = []
    table = soup.select_one("table.bd_lst")
    if not table:
        return posts

    for tr in table.select("tr"):
        no_td = tr.select_one("td.no")
        if not no_td or not no_td.get_text(strip=True).isdigit():
            continue

        title_td = tr.select_one("td.title")
        if not title_td:
            continue
        a = title_td.select_one("a")
        if not a:
            continue

        raw_title = a.get_text(strip=True)
        cmt_match = re.search(r"(\d+)$", raw_title)
        cmt = int(cmt_match.group(1)) if cmt_match else 0
        title = re.sub(r"\d+$", "", raw_title).strip() if cmt_match else raw_title

        href = a.get("href", "")
        url = f"https://theqoo.net{href}" if href.startswith("/") else href

        views_td = tr.select_one("td.m_no")
        views = _parse_int(views_td.get_text()) if views_td else 0

        posts.append({
            "url": url,
            "title": title,
            "likes": 0,
            "comment_count": cmt,
            "views": views,
        })
    return posts


def _theqoo_detail(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    article = soup.select_one("div.rd_body") or soup.select_one("article")
    content = article.get_text("\n", strip=True)[:5000] if article else ""
    comments = _extract_comments_generic(soup, "div.comment_content, li.fdb_itm")
    return {"content": content, "top_comments": comments}


# ──────────────────────────── Nate Pann ────────────────────────────

def _natepann_listing(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    posts = []
    for dl in soup.select("dl"):
        dt = dl.select_one("dt")
        if not dt:
            continue
        a = dt.select_one('a[href*="/talk/"]')
        if not a:
            continue

        href = a.get("href", "")
        if not re.search(r"/talk/\d+", href):
            continue

        title = a.get_text(strip=True)
        url = f"https://pann.nate.com{href}" if href.startswith("/") else href

        cmt_el = dt.select_one("span.reple-num")
        cmt = _parse_int(cmt_el.get_text()) if cmt_el else 0

        info_dd = dl.select_one("dd.info")
        views = 0
        likes = 0
        if info_dd:
            count_el = info_dd.select_one("span.count")
            if count_el:
                views = _parse_int(count_el.get_text())
            rcm_el = info_dd.select_one("span.rcm")
            if rcm_el:
                likes = _parse_int(rcm_el.get_text())

        posts.append({
            "url": url,
            "title": title,
            "likes": likes,
            "comment_count": cmt,
            "views": views,
        })
    return posts


def _natepann_detail(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    article = soup.select_one("div#contentArea") or soup.select_one("div.posting_area")
    content = article.get_text("\n", strip=True)[:5000] if article else ""
    comments = _extract_comments_generic(soup, "div.reply_area li, div.cmt_txt")
    return {"content": content, "top_comments": comments}


# ──────────────────────────── Humor Univ ────────────────────────────

def _humoruniv_listing(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    posts = []
    for tr in soup.select("tr"):
        a = tr.select_one('a[href*="read.html"]')
        if not a:
            continue
        title = a.get_text(strip=True)
        cmt_match = re.search(r"\[(\d+)\]", title)
        cmt = int(cmt_match.group(1)) if cmt_match else 0
        title = re.sub(r"\s*\[\d+\]", "", title).strip()

        href = a.get("href", "")
        url = f"https://web.humoruniv.com/board/humor/{href}" if not href.startswith("http") else href

        tds = tr.select("td")
        likes = 0
        views = 0
        for td in tds:
            txt = td.get_text(strip=True)
            if re.match(r"^\+\d+", txt):
                likes = _parse_int(txt)
            elif re.match(r"^\d[\d,]+$", txt) and _parse_int(txt) > 50:
                views = _parse_int(txt)

        posts.append({
            "url": url,
            "title": title,
            "likes": likes,
            "comment_count": cmt,
            "views": views,
        })
    return posts


def _humoruniv_detail(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    article = soup.select_one("div#cnts") or soup.select_one("div.post_content")
    content = article.get_text("\n", strip=True)[:5000] if article else ""
    comments = _extract_comments_generic(soup, "div.re_body, div.comment_content")
    return {"content": content, "top_comments": comments}


# ──────────────────────────── Instiz ────────────────────────────

def _instiz_listing(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    posts = []
    for a in soup.select('a[href*="/pt/"]'):
        href = a.get("href", "")
        if not re.search(r"/pt/\d+", href):
            continue
        title = a.get_text(strip=True)
        if not title or len(title) < 3:
            continue

        cmt_match = re.search(r"(\d+)$", title)
        cmt = int(cmt_match.group(1)) if cmt_match and int(cmt_match.group(1)) < 1000 else 0
        if cmt_match and cmt:
            title = title[: cmt_match.start()].strip()

        url = href if href.startswith("http") else f"https://www.instiz.net{href}"

        parent = a.parent
        views = 0
        if parent:
            views_match = re.search(r"(\d[\d,]+)", parent.get_text())
            if views_match:
                v = _parse_int(views_match.group(1))
                if v > 100:
                    views = v

        if url not in [p["url"] for p in posts]:
            posts.append({
                "url": url,
                "title": title,
                "likes": 0,
                "comment_count": cmt,
                "views": views,
            })
    return posts


def _instiz_detail(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    article = soup.select_one("div.memo_content") or soup.select_one("div.xe_content")
    content = article.get_text("\n", strip=True)[:5000] if article else ""
    comments = _extract_comments_generic(soup, "div.comment_content, div.cmt_txt")
    return {"content": content, "top_comments": comments}


# ──────────────────────────── Helpers ────────────────────────────

def _extract_comments_generic(soup: BeautifulSoup, selector: str, limit: int = 10) -> str:
    comments = []
    for el in soup.select(selector)[:limit]:
        txt = el.get_text(strip=True)
        if txt and len(txt) > 3:
            comments.append(txt[:200])
    return "\n---\n".join(comments) if comments else ""


def _generic_detail(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.select("script, style, nav, header, footer, aside"):
        tag.decompose()
    article = soup.select_one("article") or soup.select_one("div.content") or soup.select_one("main")
    content = article.get_text("\n", strip=True)[:5000] if article else ""
    return {"content": content, "top_comments": ""}


_LISTING_PARSERS = {
    "fmkorea": _fmkorea_listing,
    "dcinside": _dcinside_listing,
    "theqoo": _theqoo_listing,
    "natepann": _natepann_listing,
    "humoruniv": _humoruniv_listing,
    "instiz": _instiz_listing,
}

_DETAIL_PARSERS = {
    "fmkorea": _fmkorea_detail,
    "dcinside": _dcinside_detail,
    "theqoo": _theqoo_detail,
    "natepann": _natepann_detail,
    "humoruniv": _humoruniv_detail,
    "instiz": _instiz_detail,
}
