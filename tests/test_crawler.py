from src.crawler.fetcher import hash_url


def test_hash_url_deterministic():
    url = "https://example.com/article/123"
    h1 = hash_url(url)
    h2 = hash_url(url)
    assert h1 == h2
    assert len(h1) == 32


def test_hash_url_different_for_different_urls():
    h1 = hash_url("https://example.com/a")
    h2 = hash_url("https://example.com/b")
    assert h1 != h2
