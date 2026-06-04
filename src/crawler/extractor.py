from loguru import logger


def extract_body(url: str, language: str = "ko") -> str:
    try:
        from newspaper import Article as NPArticle

        article = NPArticle(url, language=language)
        article.download()
        article.parse()
        return article.text[:5000]
    except Exception as e:
        logger.warning(f"Extract failed {url}: {e}")
        return ""
