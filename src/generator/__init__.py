from config import settings
from .base import BaseGenerator, CardContent


def get_generator() -> BaseGenerator:
    provider = settings.llm_provider

    if provider == "openai":
        from .openai_client import OpenAIGenerator

        return OpenAIGenerator()
    elif provider == "claude":
        from .claude_client import ClaudeGenerator

        return ClaudeGenerator()
    elif provider == "gemini":
        from .gemini_client import GeminiGenerator

        return GeminiGenerator()
    else:
        raise ValueError(
            f"Unknown LLM_PROVIDER: {provider}. Must be 'openai', 'claude', or 'gemini'."
        )


__all__ = ["get_generator", "BaseGenerator", "CardContent"]
