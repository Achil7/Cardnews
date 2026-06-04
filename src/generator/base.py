from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class CardContent:
    title: str
    subtitle: str
    slides: list[dict]
    caption: str
    hashtags: list[str]
    raw_json: dict = field(default_factory=dict, repr=False)


class BaseGenerator(ABC):
    @abstractmethod
    def generate_card_content(self, article: dict, num_slides: int = 6) -> CardContent:
        ...

    def _validate_slides(self, data: dict, expected_slides: int) -> CardContent:
        slides = data.get("slides", [])
        if not slides:
            raise ValueError("No slides in LLM response")

        if slides[0].get("type") != "cover":
            raise ValueError(
                f"First slide must be 'cover', got '{slides[0].get('type')}'"
            )
        if slides[-1].get("type") != "outro":
            raise ValueError(
                f"Last slide must be 'outro', got '{slides[-1].get('type')}'"
            )

        for i, s in enumerate(slides[1:-1], start=2):
            if s.get("type") != "body":
                raise ValueError(
                    f"Slide {i} must be 'body', got '{s.get('type')}'"
                )
            if not s.get("heading") or not s.get("body"):
                raise ValueError(f"Slide {i} missing heading or body")

        return CardContent(
            title=data.get("title", ""),
            subtitle=data.get("subtitle", ""),
            slides=slides,
            caption=data.get("caption", ""),
            hashtags=data.get("hashtags", []),
            raw_json=data,
        )
