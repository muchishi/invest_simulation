from functools import lru_cache
from typing import Optional
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore", env_ignore_empty=True)

    @model_validator(mode="before")
    @classmethod
    def _drop_empty_strings(cls, values: dict) -> dict:
        return {k: v for k, v in values.items() if v != ""}

    # ── AI Provider ──────────────────────────────────────────────────────────
    # "claude" | "groq"
    AI_PROVIDER: str = Field(default="claude", description="使用するAIプロバイダー")

    # Anthropic (AI_PROVIDER=claude の場合)
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None, description="Anthropic API key")
    # claude-opus-4-8:   最高精度・複雑な投資判断に最適 ($15/$75 per MTok)
    # claude-sonnet-4-6: バランス型・コスト重視 ($3/$15 per MTok)
    # claude-haiku-4-5:  高速・超低コスト ($0.80/$4 per MTok)
    CLAUDE_MODEL: str = Field(default="claude-opus-4-8")

    # Groq (AI_PROVIDER=groq の場合) - 無料枠で運用可能
    GROQ_API_KEY: Optional[str] = Field(default=None, description="Groq API key (console.groq.com)")
    # llama-3.3-70b-versatile: 最高品質・推奨 (無料: 30req/分, 6000req/日)
    # llama-3.1-70b-versatile: 高品質
    # llama-3.1-8b-instant:    高速・軽量
    GROQ_MODEL: str = Field(default="llama-3.3-70b-versatile")

    # ── Database (Supabase / PostgreSQL) ──────────────────────────────────────
    # SQLAlchemy直接接続に使用。API Keyは不要。
    # Supabase Dashboard > Settings > Database > Connection string (URI) から取得
    DATABASE_URL: str = Field(..., description="Supabase PostgreSQL direct connection string")

    # Supabase Client SDK (Storage / Auth / Realtime 利用時のみ必要)
    SUPABASE_URL: Optional[str] = Field(default=None, description="Supabase project URL (https://xxx.supabase.co)")
    SUPABASE_KEY: Optional[str] = Field(default=None, description="Supabase service_role key")

    # ── Market Data ───────────────────────────────────────────────────────────
    COINGECKO_API_KEY: Optional[str] = Field(default=None)

    # ── Trading Parameters ────────────────────────────────────────────────────
    INITIAL_CAPITAL_JPY: float = Field(default=100_000.0)
    MAX_POSITION_PCT: float = Field(default=0.20)
    MAX_POSITIONS: int = Field(default=5)
    TRANSACTION_FEE_PCT: float = Field(default=0.001)

    # ── Agent Info ────────────────────────────────────────────────────────────
    AGENT_NAME: str = Field(default="AI Investment Agent")
    AGENT_DESCRIPTION: str = Field(default="AI-powered virtual investment fund manager")

    # ── Scheduler ─────────────────────────────────────────────────────────────
    TIMEZONE: str = Field(default="Asia/Tokyo")
    LOG_LEVEL: str = Field(default="INFO")

    # ── Tracked Assets ────────────────────────────────────────────────────────
    CRYPTO_SYMBOLS: list[str] = Field(default=["BTC", "ETH", "SOL", "XRP"])
    CRYPTO_COINGECKO_IDS: dict[str, str] = Field(
        default={"BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana", "XRP": "ripple"}
    )
    US_STOCK_SYMBOLS: list[str] = Field(
        default=["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "JPM", "V", "WMT"]
    )
    JP_STOCK_SYMBOLS: list[str] = Field(
        default=["7203.T", "6758.T", "6861.T", "9984.T", "8306.T", "6501.T", "7974.T", "4063.T"]
    )
    BENCHMARK_SYMBOLS: list[str] = Field(default=["BTC-USD", "ETH-USD", "SPY", "QQQ", "VT"])

    # ── API Token Cost ────────────────────────────────────────────────────────
    CLAUDE_INPUT_TOKEN_COST: float = Field(default=15.0 / 1_000_000)
    CLAUDE_OUTPUT_TOKEN_COST: float = Field(default=75.0 / 1_000_000)

    @property
    def claude_token_costs(self) -> tuple[float, float]:
        """Claude モデルに応じたトークンコスト (input, output) を返す"""
        costs = {
            "claude-opus-4-8":           (15.0 / 1_000_000, 75.0 / 1_000_000),
            "claude-sonnet-4-6":         (3.0  / 1_000_000, 15.0 / 1_000_000),
            "claude-haiku-4-5-20251001": (0.80 / 1_000_000,  4.0 / 1_000_000),
        }
        return costs.get(self.CLAUDE_MODEL, (self.CLAUDE_INPUT_TOKEN_COST, self.CLAUDE_OUTPUT_TOKEN_COST))

    @property
    def groq_token_costs(self) -> tuple[float, float]:
        """Groq モデルのトークンコスト (無料枠は$0、有料移行時の参考値)"""
        costs = {
            "llama-3.3-70b-versatile": (0.59 / 1_000_000, 0.79 / 1_000_000),
            "llama-3.1-70b-versatile": (0.59 / 1_000_000, 0.79 / 1_000_000),
            "llama-3.1-8b-instant":    (0.05 / 1_000_000, 0.08 / 1_000_000),
            "mixtral-8x7b-32768":      (0.24 / 1_000_000, 0.24 / 1_000_000),
        }
        return costs.get(self.GROQ_MODEL, (0.0, 0.0))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
