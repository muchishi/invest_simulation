import logging
from .base import AIAgent

logger = logging.getLogger(__name__)


def create_agent() -> AIAgent:
    """設定に応じてAIエージェントを生成するファクトリー

    .env の AI_PROVIDER で切り替え:
      AI_PROVIDER=claude  → ClaudeAgent  (有料、高品質)
      AI_PROVIDER=groq    → GroqAgent    (無料枠あり)
    """
    from src.config import get_settings
    settings = get_settings()
    provider = settings.AI_PROVIDER.lower()

    if provider == "groq":
        from .groq_agent import GroqAgent
        logger.info(f"AI Provider: Groq ({settings.GROQ_MODEL})")
        return GroqAgent()

    if provider == "claude":
        from .claude_agent import ClaudeAgent
        logger.info(f"AI Provider: Claude ({settings.CLAUDE_MODEL})")
        return ClaudeAgent()

    raise ValueError(
        f"未対応の AI_PROVIDER: '{provider}'\n"
        "対応プロバイダー: claude, groq"
    )
