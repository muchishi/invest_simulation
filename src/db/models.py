import uuid
from datetime import datetime, date
from typing import Any, Optional
from sqlalchemy import (
    String, Numeric, Integer, Boolean, Text, DateTime, Date,
    ForeignKey, JSON, Index, UniqueConstraint
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID


class Base(DeclarativeBase):
    pass


def new_uuid() -> str:
    return str(uuid.uuid4())


class Agent(Base):
    """AIエージェント設定"""
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    model_id: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    config: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    trades: Mapped[list["Trade"]] = relationship("Trade", back_populates="agent")
    portfolios: Mapped[list["Portfolio"]] = relationship("Portfolio", back_populates="agent")
    decisions: Mapped[list["Decision"]] = relationship("Decision", back_populates="agent")
    weekly_reviews: Mapped[list["WeeklyReview"]] = relationship("WeeklyReview", back_populates="agent")
    morning_analyses: Mapped[list["MorningAnalysis"]] = relationship("MorningAnalysis", back_populates="agent")


class Trade(Base):
    """売買履歴"""
    __tablename__ = "trades"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    agent_id: Mapped[str] = mapped_column(String(36), ForeignKey("agents.id"), nullable=False)
    decision_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("decisions.id"))
    executed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(20), nullable=False)  # crypto / stock_us / stock_jp
    action: Mapped[str] = mapped_column(String(10), nullable=False)  # BUY / SELL
    quantity: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    price_jpy: Mapped[float] = mapped_column(Numeric(20, 2), nullable=False)
    price_usd: Mapped[Optional[float]] = mapped_column(Numeric(20, 6))
    total_amount_jpy: Mapped[float] = mapped_column(Numeric(20, 2), nullable=False)
    fee_jpy: Mapped[float] = mapped_column(Numeric(20, 2), default=0)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    agent: Mapped["Agent"] = relationship("Agent", back_populates="trades")
    decision: Mapped[Optional["Decision"]] = relationship("Decision", back_populates="trade")

    __table_args__ = (
        Index("ix_trades_agent_id", "agent_id"),
        Index("ix_trades_executed_at", "executed_at"),
        Index("ix_trades_symbol", "symbol"),
    )


class Portfolio(Base):
    """ポートフォリオ履歴スナップショット"""
    __tablename__ = "portfolios"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    agent_id: Mapped[str] = mapped_column(String(36), ForeignKey("agents.id"), nullable=False)
    snapshot_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    cash_balance_jpy: Mapped[float] = mapped_column(Numeric(20, 2), nullable=False)
    total_value_jpy: Mapped[float] = mapped_column(Numeric(20, 2), nullable=False)
    total_cost_jpy: Mapped[float] = mapped_column(Numeric(20, 2), default=0)
    unrealized_pnl_jpy: Mapped[float] = mapped_column(Numeric(20, 2), default=0)
    realized_pnl_jpy: Mapped[float] = mapped_column(Numeric(20, 2), default=0)
    holdings: Mapped[Optional[list]] = mapped_column(JSON)  # [{symbol, qty, avg_cost, price, value, pnl, pct}]
    benchmark_values: Mapped[Optional[dict]] = mapped_column(JSON)  # {BTC: x, ETH: x, SPY: x, ...}

    agent: Mapped["Agent"] = relationship("Agent", back_populates="portfolios")

    __table_args__ = (
        Index("ix_portfolios_agent_id", "agent_id"),
        Index("ix_portfolios_snapshot_at", "snapshot_at"),
    )


class MorningAnalysis(Base):
    """朝の分析結果 (07:00 JST)"""
    __tablename__ = "morning_analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    agent_id: Mapped[str] = mapped_column(String(36), ForeignKey("agents.id"), nullable=False)
    analyzed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    overall_sentiment: Mapped[Optional[str]] = mapped_column(String(20))  # bullish/neutral/bearish
    market_analysis: Mapped[Optional[dict]] = mapped_column(JSON)
    investment_candidates: Mapped[Optional[list]] = mapped_column(JSON)
    risk_assessment: Mapped[Optional[dict]] = mapped_column(JSON)
    analysis_summary: Mapped[Optional[str]] = mapped_column(Text)
    system_prompt: Mapped[Optional[str]] = mapped_column(Text)
    user_prompt: Mapped[Optional[str]] = mapped_column(Text)
    ai_response: Mapped[Optional[str]] = mapped_column(Text)
    model_id: Mapped[Optional[str]] = mapped_column(String(100))
    input_tokens: Mapped[Optional[int]] = mapped_column(Integer)
    output_tokens: Mapped[Optional[int]] = mapped_column(Integer)
    api_cost_usd: Mapped[Optional[float]] = mapped_column(Numeric(10, 6))
    portfolio_snapshot: Mapped[Optional[dict]] = mapped_column(JSON)

    agent: Mapped["Agent"] = relationship("Agent", back_populates="morning_analyses")
    decisions: Mapped[list["Decision"]] = relationship("Decision", back_populates="morning_analysis")

    __table_args__ = (Index("ix_morning_analyses_agent_date", "agent_id", "analyzed_at"),)


class Decision(Base):
    """投資判断履歴"""
    __tablename__ = "decisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    agent_id: Mapped[str] = mapped_column(String(36), ForeignKey("agents.id"), nullable=False)
    morning_analysis_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("morning_analyses.id"))
    decided_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    session_type: Mapped[str] = mapped_column(String(20), nullable=False)  # morning / evening
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    action: Mapped[str] = mapped_column(String(10), nullable=False)  # BUY / SELL / HOLD
    quantity: Mapped[Optional[float]] = mapped_column(Numeric(20, 8))
    confidence: Mapped[Optional[int]] = mapped_column(Integer)  # 0-100
    expected_return_pct: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))
    risk_level: Mapped[Optional[str]] = mapped_column(String(20))  # low/medium/high
    investment_period: Mapped[Optional[str]] = mapped_column(String(50))
    reasoning: Mapped[Optional[str]] = mapped_column(Text)
    key_factors: Mapped[Optional[list]] = mapped_column(JSON)
    system_prompt: Mapped[Optional[str]] = mapped_column(Text)
    user_prompt: Mapped[Optional[str]] = mapped_column(Text)
    ai_response: Mapped[Optional[str]] = mapped_column(Text)
    model_id: Mapped[Optional[str]] = mapped_column(String(100))
    input_tokens: Mapped[Optional[int]] = mapped_column(Integer)
    output_tokens: Mapped[Optional[int]] = mapped_column(Integer)
    api_cost_usd: Mapped[Optional[float]] = mapped_column(Numeric(10, 6))
    portfolio_snapshot: Mapped[Optional[dict]] = mapped_column(JSON)
    market_data_snapshot: Mapped[Optional[dict]] = mapped_column(JSON)

    agent: Mapped["Agent"] = relationship("Agent", back_populates="decisions")
    morning_analysis: Mapped[Optional["MorningAnalysis"]] = relationship(
        "MorningAnalysis", back_populates="decisions"
    )
    trade: Mapped[Optional["Trade"]] = relationship("Trade", back_populates="decision")
    market_snapshots: Mapped[list["MarketSnapshot"]] = relationship(
        "MarketSnapshot", back_populates="decision"
    )

    __table_args__ = (
        Index("ix_decisions_agent_id", "agent_id"),
        Index("ix_decisions_decided_at", "decided_at"),
        Index("ix_decisions_symbol", "symbol"),
    )


class MarketSnapshot(Base):
    """市場データスナップショット"""
    __tablename__ = "market_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    decision_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("decisions.id"))
    morning_analysis_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("morning_analyses.id"))
    captured_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(20), nullable=False)
    price_jpy: Mapped[Optional[float]] = mapped_column(Numeric(20, 4))
    price_usd: Mapped[Optional[float]] = mapped_column(Numeric(20, 6))
    volume_24h: Mapped[Optional[float]] = mapped_column(Numeric(30, 2))
    market_cap: Mapped[Optional[float]] = mapped_column(Numeric(30, 2))
    price_change_1h_pct: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))
    price_change_24h_pct: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))
    price_change_7d_pct: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))
    volatility_7d: Mapped[Optional[float]] = mapped_column(Numeric(10, 6))
    technical_indicators: Mapped[Optional[dict]] = mapped_column(JSON)
    raw_data: Mapped[Optional[dict]] = mapped_column(JSON)

    decision: Mapped[Optional["Decision"]] = relationship("Decision", back_populates="market_snapshots")

    __table_args__ = (
        Index("ix_market_snapshots_captured_at", "captured_at"),
        Index("ix_market_snapshots_symbol", "symbol"),
    )


class WeeklyReview(Base):
    """Claude週次反省会"""
    __tablename__ = "weekly_reviews"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    agent_id: Mapped[str] = mapped_column(String(36), ForeignKey("agents.id"), nullable=False)
    review_date: Mapped[date] = mapped_column(Date, nullable=False)
    week_start: Mapped[date] = mapped_column(Date, nullable=False)
    week_end: Mapped[date] = mapped_column(Date, nullable=False)
    performance_summary: Mapped[Optional[str]] = mapped_column(Text)
    good_decisions: Mapped[Optional[list]] = mapped_column(JSON)
    bad_decisions: Mapped[Optional[list]] = mapped_column(JSON)
    key_learnings: Mapped[Optional[list]] = mapped_column(JSON)
    improvement_plan: Mapped[Optional[str]] = mapped_column(Text)
    next_week_strategy: Mapped[Optional[str]] = mapped_column(String(20))  # bullish/neutral/bearish
    next_week_rationale: Mapped[Optional[str]] = mapped_column(Text)
    win_rate: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    total_trades: Mapped[Optional[int]] = mapped_column(Integer)
    profitable_trades: Mapped[Optional[int]] = mapped_column(Integer)
    total_pnl_jpy: Mapped[Optional[float]] = mapped_column(Numeric(20, 2))
    system_prompt: Mapped[Optional[str]] = mapped_column(Text)
    user_prompt: Mapped[Optional[str]] = mapped_column(Text)
    ai_response: Mapped[Optional[str]] = mapped_column(Text)
    model_id: Mapped[Optional[str]] = mapped_column(String(100))
    input_tokens: Mapped[Optional[int]] = mapped_column(Integer)
    output_tokens: Mapped[Optional[int]] = mapped_column(Integer)
    api_cost_usd: Mapped[Optional[float]] = mapped_column(Numeric(10, 6))

    agent: Mapped["Agent"] = relationship("Agent", back_populates="weekly_reviews")

    __table_args__ = (UniqueConstraint("agent_id", "week_start", name="uq_weekly_reviews"),)


class BenchmarkPrice(Base):
    """ベンチマーク価格履歴"""
    __tablename__ = "benchmark_prices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    price_jpy: Mapped[float] = mapped_column(Numeric(20, 4), nullable=False)
    initial_price_jpy: Mapped[Optional[float]] = mapped_column(Numeric(20, 4))
    return_pct: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))

    __table_args__ = (
        Index("ix_benchmark_prices_symbol_date", "symbol", "recorded_at"),
    )
