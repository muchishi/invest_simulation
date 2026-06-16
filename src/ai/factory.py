from src.config import get_settings
from .base import AIAgent


def create_agent() -> AIAgent:
    """AI_PROVIDER 設定に基づいてエージェントを生成する"""
    settings = get_settings()
    provider = settings.AI_PROVIDER.lower()

    if provider == "groq":
        from .groq_agent import GroqAgent
        return GroqAgent()
    elif provider == "claude":
        from .claude_agent import ClaudeAgent
        return ClaudeAgent()
    else:
        raise ValueError(f"未知の AI_PROVIDER: '{provider}' ('claude' または 'groq' を指定してください)")
