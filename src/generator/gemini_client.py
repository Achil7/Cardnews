import json

from google import genai
from loguru import logger

from config import settings
from .base import BaseGenerator, CardContent
from .prompt import SYSTEM_PROMPT, USER_PROMPT


class GeminiGenerator(BaseGenerator):
    def __init__(self):
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model = settings.gemini_model

    def generate_card_content(self, article: dict) -> CardContent:
        user_prompt = USER_PROMPT.format(
            source=article["source"],
            category=article.get("category", ""),
            title=article["title"],
            published=str(article.get("published_at", "")),
            summary=(article.get("summary") or "")[:1500],
            body=(article.get("content") or "")[:3000],
        )

        logger.info(f"Calling Gemini {self.model}...")
        resp = self.client.models.generate_content(
            model=self.model,
            contents=user_prompt,
            config=genai.types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                response_mime_type="application/json",
            ),
        )
        text = resp.text.strip()
        text = self._extract_json(text)

        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse failed: {e}\nRaw: {text[:500]}")
            raise

        logger.info(f"Gemini returned title: {data.get('title', '')[:30]}")
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
