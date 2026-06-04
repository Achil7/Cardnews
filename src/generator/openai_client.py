import json

from loguru import logger
from openai import OpenAI

from config import settings
from .base import BaseGenerator, CardContent
from .prompt import SYSTEM_PROMPT, USER_PROMPT


CARD_NEWS_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "subtitle": {"type": "string"},
        "slides": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": ["cover", "body", "outro"],
                    },
                    "title": {"type": "string"},
                    "subtitle": {"type": "string"},
                    "heading": {"type": "string"},
                    "body": {"type": "string"},
                    "source": {"type": "string"},
                    "cta": {"type": "string"},
                },
                "required": ["type"],
                "additionalProperties": False,
            },
        },
        "caption": {"type": "string"},
        "hashtags": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["title", "subtitle", "slides", "caption", "hashtags"],
    "additionalProperties": False,
}


class OpenAIGenerator(BaseGenerator):
    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model

    def generate_card_content(self, article: dict, num_slides: int = 6) -> CardContent:
        sys_prompt = SYSTEM_PROMPT.format(slides=num_slides, body_end=num_slides - 1)
        user_prompt = USER_PROMPT.format(
            source=article["source"],
            category=article.get("category", ""),
            title=article["title"],
            published=str(article.get("published_at", "")),
            summary=(article.get("summary") or "")[:1500],
            body=(article.get("content") or "")[:3000],
            slides=num_slides,
        )

        logger.info(f"Calling OpenAI {self.model}...")
        resp = self.client.responses.create(
            model=self.model,
            instructions=sys_prompt,
            input=user_prompt,
            text={
                "format": {
                    "type": "json_schema",
                    "name": "card_news",
                    "schema": CARD_NEWS_SCHEMA,
                    "strict": True,
                }
            },
        )

        data = json.loads(resp.output_text)
        logger.info(f"OpenAI returned {len(data.get('slides', []))} slides")
        return self._validate_slides(data, num_slides)
