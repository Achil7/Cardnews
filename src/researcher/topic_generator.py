"""Claude API로 연령대별 트렌딩 밈/유머 주제를 생성한다."""
import json

from anthropic import Anthropic
from loguru import logger

from config import settings

TOPIC_SYSTEM_PROMPT = """너는 한국 인터넷 문화 전문가야.
사용자가 요청하는 연령대(20대/30대/40대)에 맞는 최신 밈, 유머, 공감 콘텐츠 주제를 제안해.

규칙:
- 한국 커뮤니티(에펨코리아, 디시인사이드, 네이트판, 인스타그램, X/트위터)에서 화제가 될 만한 주제
- 각 주제는 구체적이고 검색 가능한 형태여야 함
- 정치/혐오/성적 콘텐츠 제외, 가족 친화적 유머만
- JSON 배열로 5~8개 반환

예시 출력:
["요즘 직장인 퇴근 짤 모음", "MZ세대 카페 주문 밈", "20대 자취생 냉장고 현실"]
"""

TOPIC_USER_PROMPT = """요즘 한국 {demographic} 사이에서 인기 있거나 공감되는 밈/유머/트렌드 주제를 5~8개 제안해줘.
인스타그램 카드뉴스로 만들기 좋은 주제여야 해.
JSON 배열로만 답해."""


def generate_topics(demographic: str) -> list[str]:
    client = Anthropic(api_key=settings.anthropic_api_key)

    label = {"20s": "20대", "30s": "30대", "40s": "40대"}.get(demographic, demographic)

    model = settings.anthropic_model
    logger.info(f"Generating meme topics for {label} with {model}...")
    resp = client.messages.create(
        model=model,
        max_tokens=1024,
        system=TOPIC_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": TOPIC_USER_PROMPT.format(demographic=label)}],
    )

    text = resp.content[0].text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1]).strip()

    try:
        topics = json.loads(text)
        if isinstance(topics, list):
            logger.info(f"Generated {len(topics)} topics for {label}")
            return topics
    except json.JSONDecodeError:
        logger.error(f"Failed to parse topics: {text[:300]}")

    return []
