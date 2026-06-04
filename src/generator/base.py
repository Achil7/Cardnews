from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class CardContent:
    title: str
    subtitle: str
    caption: str
    hashtags: list[str]
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

        return CardContent(
            title=data.get("title", ""),
            subtitle=data.get("subtitle", ""),
            caption=data.get("caption", ""),
            hashtags=data.get("hashtags", []),
            raw_json=data,
        )
