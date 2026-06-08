from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class CardContent:
    title: str
    subtitle: str
    caption: str
    hashtags: list[str]
    body_cards: list[dict] = field(default_factory=list)
    raw_json: dict = field(default_factory=dict, repr=False)


class BaseGenerator(ABC):
    @abstractmethod
    def generate_card_content(self, article: dict) -> CardContent:
        ...

    def _validate(self, data: dict) -> CardContent:
        if not data.get("title"):
            raise ValueError("Missing title in LLM response")
        if not data.get("caption"):
            raise ValueError("Missing caption in LLM response")

        body_cards = data.get("body_cards", [])
        for card in body_cards:
            if not isinstance(card, dict) or "heading" not in card or "body" not in card:
                raise ValueError(f"Invalid body_card: {card}")

        return CardContent(
            title=data.get("title", ""),
            subtitle=data.get("subtitle", ""),
            caption=data.get("caption", ""),
            hashtags=data.get("hashtags", []),
            body_cards=body_cards,
            raw_json=data,
        )
