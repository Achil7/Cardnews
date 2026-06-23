"""커뮤니티 인기글을 밈/유머 카드뉴스 콘텐츠로 변환한다."""
import json
import re

from anthropic import Anthropic
from loguru import logger

from config import settings
from .base import BaseGenerator, CardContent
from .meme_prompt import MEME_SYSTEM_PROMPT, MEME_USER_PROMPT


class MemeGenerator(BaseGenerator):
    def __init__(self):
        self.client = Anthropic(api_key=settings.anthropic_api_key)
        self.model = settings.anthropic_model

    def generate_card_content(self, article: dict) -> CardContent:
        if "top_comments" in article and isinstance(article["top_comments"], str):
            quotes_text = article["top_comments"][:2000]
        else:
            quotes_text = "\n".join(f"- {q}" for q in article.get("key_quotes", []))
        if not quotes_text:
            quotes_text = "(없음)"

        user_prompt = MEME_USER_PROMPT.format(
            topic=article["title"],
            demographic=article.get("demographic", ""),
            content=(article.get("content") or "")[:3000],
            quotes=quotes_text,
        )

        logger.info(f"Generating meme card for: {article['title'][:50]}")
        resp = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            system=MEME_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

        text = resp.content[0].text.strip()
        text = self._extract_json(text)

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            text = self._repair_json(text)
            try:
                data = json.loads(text)
            except json.JSONDecodeError as e:
                logger.error(f"JSON parse failed: {e}\nRaw: {text[:500]}")
                raise

        logger.info(f"Meme card hook: {data.get('hook', {}).get('text', '')[:30]}")
        return self._validate(data)

    def _validate(self, data: dict) -> CardContent:
        hook_text = data.get("hook_text") or data.get("hook", {}).get("text", "")
        if not hook_text:
            raise ValueError("Missing hook_text")
        data["hook_text"] = hook_text

        if not data.get("punchline"):
            raise ValueError("Missing punchline")

        if not data.get("caption"):
            raise ValueError("Missing caption")

        return CardContent(
            title=hook_text,
            subtitle="",
            caption=data["caption"],
            hashtags=data.get("hashtags", []),
            body_cards=[],
            raw_json=data,
        )

    @staticmethod
    def _extract_json(text: str) -> str:
        if text.startswith("```"):
            lines = text.split("\n")
            start = 1
            end = len(lines)
            for i in range(len(lines) - 1, 0, -1):
                if lines[i].strip() == "```":
                    end = i
                    break
            text = "\n".join(lines[start:end]).strip()
        return text

    @staticmethod
    def _repair_json(text: str) -> str:
        result = []
        in_string = False
        i = 0
        while i < len(text):
            ch = text[i]
            if in_string:
                if ch == '\\' and i + 1 < len(text):
                    result.append(ch)
                    result.append(text[i + 1])
                    i += 2
                    continue
                elif ch == '"':
                    in_string = False
                    result.append(ch)
                elif ch == '\n':
                    result.append('\\n')
                elif ch == '\r':
                    result.append('\\r')
                elif ch == '\t':
                    result.append('\\t')
                else:
                    result.append(ch)
            else:
                if ch == '"':
                    in_string = True
                result.append(ch)
            i += 1
        return ''.join(result)
