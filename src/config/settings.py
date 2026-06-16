from functools import lru_cache
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

    # Anthropic
    ANTHROPIC_API_KEY: str = Field(..., description="Anthropic API key")
    # claude-opus-4-8: 最高精度・複雑な投資判断に最適 ($15/$75 per MTok)
    # claude-sonnet-4-6: バランス型・コスト重視の場合 ($3/$15 per MTok)
    # claude-haiku-4-5: 高速・超低コスト・単純分類向け ($0.80/$4 per MTok)
    CLAUDE_MODEL: str = Field(default="claude-opus-4-8")

    # --- Database (Supabase / PostgreSQL) ---
    # SQLAlchemy直接接続に使用。Supabase API Keyは不要。
    # Supabase Dashboard > Settings > Database > Connection string (URI) から取得
    DATABASE_URL: str = Field(..., description="Supabase PostgreSQL direct connection string")

    # --- Supabase Client SDK (Storage / Auth / Realtime 利用時のみ必要) ---
    # 現在の実装では未使用。将来の拡張（レポートファイル保存等）用。
    # Supabase Dashboard > Settings > API から取得
    SUPABASE_URL: Optional[str] = Field(default=None, description="Supabase project URL (https://xxx.supabase.co)")
    SUPABASE_KEY: Optional[str] = Field(default=None, description="Supabase service_role key (NOT anon key)")

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

    # API cost per token (USD) - モデルに応じた価格を手動設定
    # claude-opus-4-8:    input=$15/MTok  output=$75/MTok
    # claude-sonnet-4-6:  input=$3/MTok   output=$15/MTok
    # claude-haiku-4-5:   input=$0.80/MTok output=$4/MTok
    CLAUDE_INPUT_TOKEN_COST: float = Field(default=15.0 / 1_000_000)
    CLAUDE_OUTPUT_TOKEN_COST: float = Field(default=75.0 / 1_000_000)

    @property
    def claude_token_costs(self) -> tuple[float, float]:
        """選択モデルに応じたトークンコスト (input, output) を返す"""
        costs = {
            "claude-opus-4-8":   (15.0 / 1_000_000, 75.0 / 1_000_000),
            "claude-sonnet-4-6": (3.0  / 1_000_000, 15.0 / 1_000_000),
            "claude-haiku-4-5-20251001": (0.80 / 1_000_000, 4.0 / 1_000_000),
        }
        return costs.get(self.CLAUDE_MODEL, (self.CLAUDE_INPUT_TOKEN_COST, self.CLAUDE_OUTPUT_TOKEN_COST))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
