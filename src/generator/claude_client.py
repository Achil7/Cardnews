import json

from anthropic import Anthropic
from loguru import logger

from config import settings
from .base import BaseGenerator, CardContent
from .prompt import SYSTEM_PROMPT, USER_PROMPT


class ClaudeGenerator(BaseGenerator):
    def __init__(self):
        self.client = Anthropic(api_key=settings.anthropic_api_key)
        self.model = settings.anthropic_model

    def generate_card_content(self, article: dict) -> CardContent:
        user_prompt = USER_PROMPT.format(
            source=article["source"],
            category=article.get("category", ""),
            title=article["title"],
            published=str(article.get("published_at", "")),
            summary=(article.get("summary") or "")[:1500],
            body=(article.get("content") or "")[:3000],
        )

        logger.info(f"Calling Claude {self.model}...")
        resp = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
        text = resp.content[0].text.strip()
        text = self._extract_json(text)

        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse failed: {e}\nRaw: {text[:500]}")
            raise

        logger.info(f"Claude returned title: {data.get('title', '')[:30]}")
        return self._validate(data)

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
