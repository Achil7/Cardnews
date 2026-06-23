from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ResearchResult:
    topic: str
    demographic: str
    sources: list[str] = field(default_factory=list)
    content_summary: str = ""
    key_quotes: list[str] = field(default_factory=list)
    image_urls: list[str] = field(default_factory=list)
    searched_at: datetime = field(default_factory=datetime.now)
