"""Claude web_search tool로 밈/유머 콘텐츠를 리서치한다."""
from anthropic import Anthropic
from loguru import logger

from config import settings
from .models import ResearchResult

RESEARCH_SYSTEM_PROMPT = """너는 한국 인터넷 밈/유머 콘텐츠 리서처야.
주어진 주제에 대해 웹 검색을 통해 재밌는 커뮤니티 글, 밈, 반응을 찾아서 정리해.

규칙:
- 한국어 커뮤니티(에펨코리아, 디시인사이드, 네이트판, 인스타그램, X/트위터, 루리웹 등) 위주로 검색
- 실제 커뮤니티 글이나 반응을 찾아서 인용
- 재밌는 댓글, 반응, 밈 포인트를 구체적으로 수집
- 정치/혐오/성적 콘텐츠 제외
- 결과를 한국어로 정리

출력 형식:
1. 주제 요약 (200~400자)
2. 핵심 포인트/재밌는 반응 3~5개 (각각 인용 형태로)
3. 출처 URL 목록
"""


def research_topic(topic: str, demographic: str) -> ResearchResult:
    client = Anthropic(api_key=settings.anthropic_api_key)

    logger.info(f"Researching topic: {topic}")
    resp = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=4096,
        system=RESEARCH_SYSTEM_PROMPT,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[
            {
                "role": "user",
                "content": (
                    f"다음 주제에 대해 웹 검색해서 재밌는 커뮤니티 글, 밈, 반응을 찾아줘.\n\n"
                    f"주제: {topic}\n"
                    f"타겟: 한국 {demographic}\n\n"
                    f"실제 커뮤니티 글이나 SNS 반응을 찾아서 구체적으로 인용해줘."
                ),
            }
        ],
    )

    content_text = ""
    sources = []
    for block in resp.content:
        if block.type == "text":
            content_text += block.text + "\n"
        elif block.type == "web_search_tool_result":
            for search_result in getattr(block, "content", []):
                if hasattr(search_result, "url"):
                    sources.append(search_result.url)

    if not content_text.strip():
        logger.warning(f"No research results for: {topic}")
        return ResearchResult(topic=topic, demographic=demographic)

    key_quotes = _extract_quotes(content_text)

    logger.info(f"Research done: {len(sources)} sources, {len(key_quotes)} quotes")
    return ResearchResult(
        topic=topic,
        demographic=demographic,
        sources=sources[:10],
        content_summary=content_text.strip()[:2000],
        key_quotes=key_quotes,
    )


def _extract_quotes(text: str) -> list[str]:
    """텍스트에서 인용문/핵심 포인트를 추출한다."""
    quotes = []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        if line.startswith(("- ", "• ", "· ", "\"", "'", "「", "『")):
            cleaned = line.lstrip("-•·\"'「『 ").rstrip("\"'」』")
            if len(cleaned) > 10:
                quotes.append(cleaned)
    return quotes[:5]
