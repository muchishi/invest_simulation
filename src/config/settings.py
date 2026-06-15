from functools import lru_cache
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

    # Anthropic
    ANTHROPIC_API_KEY: str = Field(..., description="Anthropic API key")
    CLAUDE_MODEL: str = Field(default="claude-opus-4-8")

    # Database
    DATABASE_URL: str = Field(..., description="PostgreSQL connection string")

    # CoinGecko
    COINGECKO_API_KEY: Optional[str] = Field(default=None)

    # Trading parameters
    INITIAL_CAPITAL_JPY: float = Field(default=100_000.0)
    MAX_POSITION_PCT: float = Field(default=0.20)
    MAX_POSITIONS: int = Field(default=5)
    TRANSACTION_FEE_PCT: float = Field(default=0.001)

    # Agent info
    AGENT_NAME: str = Field(default="Claude Investment Agent")
    AGENT_DESCRIPTION: str = Field(default="Claude-powered virtual investment fund manager")

    # Scheduler
    TIMEZONE: str = Field(default="Asia/Tokyo")

    # Logging
    LOG_LEVEL: str = Field(default="INFO")

    # Tracked assets
    CRYPTO_SYMBOLS: list[str] = Field(
        default=["BTC", "ETH", "SOL", "XRP"],
        description="CoinGecko coin IDs for price lookup",
    )
    CRYPTO_COINGECKO_IDS: dict[str, str] = Field(
        default={
            "BTC": "bitcoin",
            "ETH": "ethereum",
            "SOL": "solana",
            "XRP": "ripple",
        }
    )

    US_STOCK_SYMBOLS: list[str] = Field(
        default=["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "JPM", "V", "WMT"]
    )

    JP_STOCK_SYMBOLS: list[str] = Field(
        default=["7203.T", "6758.T", "6861.T", "9984.T", "8306.T", "6501.T", "7974.T", "4063.T"]
    )

    BENCHMARK_SYMBOLS: list[str] = Field(
        default=["BTC-USD", "ETH-USD", "SPY", "QQQ", "VT"]
    )

    # API cost per token (USD) - claude-opus-4-8
    CLAUDE_INPUT_TOKEN_COST: float = Field(default=15.0 / 1_000_000)
    CLAUDE_OUTPUT_TOKEN_COST: float = Field(default=75.0 / 1_000_000)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
