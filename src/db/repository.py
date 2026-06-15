from datetime import datetime, date, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, func

from .models import (
    Agent, Trade, Portfolio, Decision, MarketSnapshot,
    WeeklyReview, MorningAnalysis, BenchmarkPrice
)


class Repository:
    def __init__(self, session: Session):
        self.session = session

    # ── Agent ────────────────────────────────────────────────
    def get_active_agent(self) -> Optional[Agent]:
        return self.session.query(Agent).filter(Agent.is_active == True).first()

    def create_agent(self, **kwargs) -> Agent:
        agent = Agent(**kwargs)
        self.session.add(agent)
        self.session.flush()
        return agent

    def get_or_create_agent(self, name: str, model_id: str, description: str = "") -> Agent:
        agent = self.get_active_agent()
        if agent:
            return agent
        return self.create_agent(name=name, model_id=model_id, description=description)

    # ── Portfolio ────────────────────────────────────────────
    def save_portfolio(self, agent_id: str, **kwargs) -> Portfolio:
        portfolio = Portfolio(agent_id=agent_id, **kwargs)
        self.session.add(portfolio)
        self.session.flush()
        return portfolio

    def get_latest_portfolio(self, agent_id: str) -> Optional[Portfolio]:
        return (
            self.session.query(Portfolio)
            .filter(Portfolio.agent_id == agent_id)
            .order_by(desc(Portfolio.snapshot_at))
            .first()
        )

    def get_portfolio_history(self, agent_id: str, days: int = 90) -> list[Portfolio]:
        since = datetime.utcnow() - timedelta(days=days)
        return (
            self.session.query(Portfolio)
            .filter(and_(Portfolio.agent_id == agent_id, Portfolio.snapshot_at >= since))
            .order_by(Portfolio.snapshot_at)
            .all()
        )

    # ── Trade ────────────────────────────────────────────────
    def save_trade(self, agent_id: str, **kwargs) -> Trade:
        trade = Trade(agent_id=agent_id, **kwargs)
        self.session.add(trade)
        self.session.flush()
        return trade

    def get_trades(self, agent_id: str, limit: int = 100) -> list[Trade]:
        return (
            self.session.query(Trade)
            .filter(Trade.agent_id == agent_id)
            .order_by(desc(Trade.executed_at))
            .limit(limit)
            .all()
        )

    def get_recent_trades_for_symbol(
        self, agent_id: str, symbol: str, hours: int = 24
    ) -> list[Trade]:
        since = datetime.utcnow() - timedelta(hours=hours)
        return (
            self.session.query(Trade)
            .filter(
                and_(
                    Trade.agent_id == agent_id,
                    Trade.symbol == symbol,
                    Trade.executed_at >= since,
                )
            )
            .all()
        )

    def get_realized_pnl(self, agent_id: str) -> float:
        """全確定損益を計算（BUY/SELLペアから）"""
        trades = self.session.query(Trade).filter(Trade.agent_id == agent_id).all()
        buys: dict[str, list[Trade]] = {}
        realized = 0.0
        for t in sorted(trades, key=lambda x: x.executed_at):
            sym = t.symbol
            if t.action == "BUY":
                buys.setdefault(sym, []).append(t)
            elif t.action == "SELL" and sym in buys and buys[sym]:
                buy = buys[sym].pop(0)
                sell_net = float(t.total_amount_jpy) - float(t.fee_jpy)
                buy_net = float(buy.total_amount_jpy) + float(buy.fee_jpy)
                realized += sell_net - buy_net
        return realized

    # ── Morning Analysis ─────────────────────────────────────
    def save_morning_analysis(self, agent_id: str, **kwargs) -> MorningAnalysis:
        ma = MorningAnalysis(agent_id=agent_id, **kwargs)
        self.session.add(ma)
        self.session.flush()
        return ma

    def get_latest_morning_analysis(self, agent_id: str) -> Optional[MorningAnalysis]:
        return (
            self.session.query(MorningAnalysis)
            .filter(MorningAnalysis.agent_id == agent_id)
            .order_by(desc(MorningAnalysis.analyzed_at))
            .first()
        )

    def get_morning_analyses(self, agent_id: str, limit: int = 10) -> list[MorningAnalysis]:
        return (
            self.session.query(MorningAnalysis)
            .filter(MorningAnalysis.agent_id == agent_id)
            .order_by(desc(MorningAnalysis.analyzed_at))
            .limit(limit)
            .all()
        )

    # ── Decision ─────────────────────────────────────────────
    def save_decision(self, agent_id: str, **kwargs) -> Decision:
        decision = Decision(agent_id=agent_id, **kwargs)
        self.session.add(decision)
        self.session.flush()
        return decision

    def get_decisions(self, agent_id: str, limit: int = 100) -> list[Decision]:
        return (
            self.session.query(Decision)
            .filter(Decision.agent_id == agent_id)
            .order_by(desc(Decision.decided_at))
            .limit(limit)
            .all()
        )

    def get_recent_decisions(self, agent_id: str, days: int = 7) -> list[Decision]:
        since = datetime.utcnow() - timedelta(days=days)
        return (
            self.session.query(Decision)
            .filter(and_(Decision.agent_id == agent_id, Decision.decided_at >= since))
            .order_by(desc(Decision.decided_at))
            .all()
        )

    def get_evening_decisions(self, agent_id: str, limit: int = 50) -> list[Decision]:
        return (
            self.session.query(Decision)
            .filter(
                and_(Decision.agent_id == agent_id, Decision.session_type == "evening")
            )
            .order_by(desc(Decision.decided_at))
            .limit(limit)
            .all()
        )

    # ── Market Snapshot ──────────────────────────────────────
    def save_market_snapshot(self, **kwargs) -> MarketSnapshot:
        snap = MarketSnapshot(**kwargs)
        self.session.add(snap)
        self.session.flush()
        return snap

    def save_market_snapshots(self, snapshots: list[dict]) -> list[MarketSnapshot]:
        result = []
        for data in snapshots:
            snap = MarketSnapshot(**data)
            self.session.add(snap)
            result.append(snap)
        self.session.flush()
        return result

    # ── Weekly Review ────────────────────────────────────────
    def save_weekly_review(self, agent_id: str, **kwargs) -> WeeklyReview:
        review = WeeklyReview(agent_id=agent_id, **kwargs)
        self.session.add(review)
        self.session.flush()
        return review

    def get_weekly_reviews(self, agent_id: str, limit: int = 12) -> list[WeeklyReview]:
        return (
            self.session.query(WeeklyReview)
            .filter(WeeklyReview.agent_id == agent_id)
            .order_by(desc(WeeklyReview.review_date))
            .limit(limit)
            .all()
        )

    def get_latest_weekly_review(self, agent_id: str) -> Optional[WeeklyReview]:
        return (
            self.session.query(WeeklyReview)
            .filter(WeeklyReview.agent_id == agent_id)
            .order_by(desc(WeeklyReview.review_date))
            .first()
        )

    # ── Benchmark ────────────────────────────────────────────
    def save_benchmark_price(self, **kwargs) -> BenchmarkPrice:
        bp = BenchmarkPrice(**kwargs)
        self.session.add(bp)
        self.session.flush()
        return bp

    def get_initial_benchmark_price(self, symbol: str) -> Optional[BenchmarkPrice]:
        return (
            self.session.query(BenchmarkPrice)
            .filter(BenchmarkPrice.symbol == symbol)
            .order_by(BenchmarkPrice.recorded_at)
            .first()
        )

    def get_benchmark_history(self, symbol: str, days: int = 90) -> list[BenchmarkPrice]:
        since = datetime.utcnow() - timedelta(days=days)
        return (
            self.session.query(BenchmarkPrice)
            .filter(
                and_(BenchmarkPrice.symbol == symbol, BenchmarkPrice.recorded_at >= since)
            )
            .order_by(BenchmarkPrice.recorded_at)
            .all()
        )

    # ── Statistics ───────────────────────────────────────────
    def get_win_rate(self, agent_id: str, days: int = 30) -> dict:
        """過去N日間の勝率を計算"""
        since = datetime.utcnow() - timedelta(days=days)
        decisions = (
            self.session.query(Decision)
            .filter(
                and_(
                    Decision.agent_id == agent_id,
                    Decision.session_type == "evening",
                    Decision.action.in_(["BUY", "SELL"]),
                    Decision.decided_at >= since,
                )
            )
            .all()
        )
        total = len(decisions)
        return {"total": total, "decisions": decisions}
