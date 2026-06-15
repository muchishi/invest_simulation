import logging
from datetime import datetime, date, timedelta
from typing import Optional

import pytz

from src.config import get_settings
from src.ai.claude_agent import ClaudeAgent
from src.db.session import get_session
from src.db.repository import Repository
from src.market_data.factory import MarketDataFactory
from src.technical.indicators import TechnicalAnalyzer
from src.trading.portfolio import PortfolioManager
from src.trading.executor import TradeExecutor

logger = logging.getLogger(__name__)


class InvestmentScheduler:
    """投資スケジューラー - 朝の分析・夕の売買判断・週次反省会を管理"""

    def __init__(self):
        self.settings = get_settings()
        self.agent = ClaudeAgent()
        self.market_factory = MarketDataFactory()
        self.technical = TechnicalAnalyzer()
        self.jst = pytz.timezone(self.settings.TIMEZONE)

    def run_morning_analysis(self):
        """07:00 JST: 朝の市場分析"""
        logger.info("=== 朝の分析開始 (07:00 JST) ===")
        with get_session() as session:
            repo = Repository(session)
            agent = repo.get_active_agent()
            if not agent:
                logger.error("アクティブなエージェントが見つかりません")
                return

            # ポートフォリオ復元
            portfolio_manager = self._load_portfolio(repo, agent.id)

            # 市場データ取得
            logger.info("市場データ取得中...")
            market_data = self.market_factory.get_all_tracked_assets()
            usdjpy = self.market_factory.get_usdjpy_rate()

            # 価格更新
            prices = {sym: d.price_jpy for sym, d in market_data.items() if d.price_jpy}
            portfolio_manager.state.update_prices(prices)

            # テクニカル分析
            technical_indicators = {}
            for sym, data in market_data.items():
                if data.ohlcv is not None and not data.ohlcv.empty:
                    technical_indicators[sym] = self.technical.analyze(data.ohlcv, sym)

            # 過去の判断履歴
            recent_decisions = repo.get_recent_decisions(agent.id, days=7)
            latest_review = repo.get_latest_weekly_review(agent.id)

            context = {
                "portfolio": portfolio_manager.get_snapshot(),
                "market_data": {sym: d.to_snapshot_dict() for sym, d in market_data.items()},
                "technical": technical_indicators,
                "recent_decisions": recent_decisions,
                "latest_review": latest_review,
                "usdjpy": usdjpy,
            }

            # Claude 朝の分析
            result = self.agent.run_morning_analysis(context)

            # 分析結果保存
            ma = repo.save_morning_analysis(
                agent_id=agent.id,
                analyzed_at=datetime.utcnow(),
                overall_sentiment=result.overall_sentiment,
                market_analysis=result.market_analysis,
                investment_candidates=result.investment_candidates,
                risk_assessment=result.risk_assessment,
                analysis_summary=result.analysis_summary,
                system_prompt=result.system_prompt,
                user_prompt=result.user_prompt,
                ai_response=result.raw_response,
                model_id=result.model_id,
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
                api_cost_usd=result.api_cost_usd,
                portfolio_snapshot=portfolio_manager.get_snapshot(),
            )

            # 市場スナップショット保存
            for sym, data in market_data.items():
                ind = technical_indicators.get(sym)
                repo.save_market_snapshot(
                    morning_analysis_id=ma.id,
                    captured_at=datetime.utcnow(),
                    symbol=sym,
                    asset_type=data.asset_type.value,
                    price_jpy=data.price_jpy,
                    price_usd=data.price_usd,
                    volume_24h=data.volume_24h,
                    market_cap=data.market_cap,
                    price_change_1h_pct=data.price_change_1h_pct,
                    price_change_24h_pct=data.price_change_24h_pct,
                    price_change_7d_pct=data.price_change_7d_pct,
                    technical_indicators=ind.to_dict() if ind else None,
                )

            # ポートフォリオスナップショット保存
            repo.save_portfolio(
                agent_id=agent.id,
                snapshot_at=datetime.utcnow(),
                cash_balance_jpy=portfolio_manager.state.cash_balance_jpy,
                total_value_jpy=portfolio_manager.state.total_value_jpy,
                total_cost_jpy=portfolio_manager.state.total_cost_jpy,
                unrealized_pnl_jpy=portfolio_manager.state.unrealized_pnl_jpy,
                realized_pnl_jpy=portfolio_manager.state.realized_pnl_jpy,
                holdings=portfolio_manager.get_snapshot()["holdings"],
            )

            logger.info(
                f"朝の分析完了: sentiment={result.overall_sentiment}, "
                f"candidates={len(result.investment_candidates)}, "
                f"cost=${result.api_cost_usd:.4f}"
            )

    def run_evening_analysis(self):
        """23:00 JST: 夕の最終判断・売買実行"""
        logger.info("=== 夕の最終判断開始 (23:00 JST) ===")
        with get_session() as session:
            repo = Repository(session)
            agent = repo.get_active_agent()
            if not agent:
                logger.error("アクティブなエージェントが見つかりません")
                return

            # ポートフォリオ復元
            portfolio_manager = self._load_portfolio(repo, agent.id)

            # 最新市場データ取得
            logger.info("最新市場データ取得中...")
            market_data = self.market_factory.get_all_tracked_assets()
            usdjpy = self.market_factory.get_usdjpy_rate()

            # 価格更新
            prices = {sym: d.price_jpy for sym, d in market_data.items() if d.price_jpy}
            portfolio_manager.state.update_prices(prices)

            # テクニカル分析
            technical_indicators = {}
            for sym, data in market_data.items():
                if data.ohlcv is not None and not data.ohlcv.empty:
                    technical_indicators[sym] = self.technical.analyze(data.ohlcv, sym)

            # 朝の分析取得
            morning = repo.get_latest_morning_analysis(agent.id)
            morning_dict = None
            if morning:
                morning_dict = {
                    "overall_sentiment": morning.overall_sentiment,
                    "analysis_summary": morning.analysis_summary,
                    "investment_candidates": morning.investment_candidates,
                }

            # 過去の判断履歴
            recent_decisions = repo.get_recent_decisions(agent.id, days=7)
            latest_review = repo.get_latest_weekly_review(agent.id)

            context = {
                "portfolio": portfolio_manager.get_snapshot(),
                "market_data": {sym: d.to_snapshot_dict() for sym, d in market_data.items()},
                "technical": technical_indicators,
                "morning_analysis": morning_dict,
                "recent_decisions": recent_decisions,
                "latest_review": latest_review,
                "usdjpy": usdjpy,
            }

            # Claude 夕の判断
            result = self.agent.run_evening_analysis(context)

            # 売買実行
            executor = TradeExecutor(portfolio_manager, repo)
            executed_trades = executor.execute_decisions(
                agent_id=agent.id,
                decisions=result.decisions,
                market_data=market_data,
                morning_analysis_id=morning.id if morning else None,
                evening_result=result,
            )

            # ポートフォリオスナップショット保存
            bench_prices = self.market_factory.get_benchmark_prices()
            bench_values = self._calc_benchmark_values(repo, agent.id, bench_prices)

            repo.save_portfolio(
                agent_id=agent.id,
                snapshot_at=datetime.utcnow(),
                cash_balance_jpy=portfolio_manager.state.cash_balance_jpy,
                total_value_jpy=portfolio_manager.state.total_value_jpy,
                total_cost_jpy=portfolio_manager.state.total_cost_jpy,
                unrealized_pnl_jpy=portfolio_manager.state.unrealized_pnl_jpy,
                realized_pnl_jpy=portfolio_manager.state.realized_pnl_jpy,
                holdings=portfolio_manager.get_snapshot()["holdings"],
                benchmark_values=bench_values,
            )

            # ベンチマーク価格保存
            self._save_benchmark_prices(repo, bench_prices)

            buy_count = sum(1 for t in executed_trades if t.get("action") == "BUY" and t.get("executed"))
            sell_count = sum(1 for t in executed_trades if t.get("action") == "SELL" and t.get("executed"))

            logger.info(
                f"夕の判断完了: BUY={buy_count}, SELL={sell_count}, "
                f"総資産={portfolio_manager.state.total_value_jpy:,.0f}円, "
                f"cost=${result.api_cost_usd:.4f}"
            )

    def run_weekly_review(self):
        """週次反省会"""
        logger.info("=== 週次反省会開始 ===")
        with get_session() as session:
            repo = Repository(session)
            agent = repo.get_active_agent()
            if not agent:
                logger.error("アクティブなエージェントが見つかりません")
                return

            today = date.today()
            week_end = today - timedelta(days=1)
            week_start = week_end - timedelta(days=6)

            # 週次データ収集
            portfolio_manager = self._load_portfolio(repo, agent.id)
            weekly_trades = repo.get_trades(agent.id, limit=50)
            weekly_trades = [t for t in weekly_trades if t.executed_at.date() >= week_start]
            weekly_decisions = repo.get_recent_decisions(agent.id, days=7)
            previous_review = repo.get_latest_weekly_review(agent.id)

            # ポートフォリオ履歴からパフォーマンス計算
            port_history = repo.get_portfolio_history(agent.id, days=7)
            weekly_pnl_jpy = 0.0
            weekly_return_pct = 0.0
            if len(port_history) >= 2:
                start_val = float(port_history[0].total_value_jpy)
                end_val = float(port_history[-1].total_value_jpy)
                weekly_pnl_jpy = end_val - start_val
                weekly_return_pct = (weekly_pnl_jpy / start_val * 100) if start_val else 0

            performance_metrics = {
                "week_start": week_start.isoformat(),
                "week_end": week_end.isoformat(),
                "weekly_pnl_jpy": weekly_pnl_jpy,
                "weekly_return_pct": weekly_return_pct,
                "total_value_jpy": portfolio_manager.state.total_value_jpy,
                "cash_balance_jpy": portfolio_manager.state.cash_balance_jpy,
            }

            # ベンチマークリターン
            bench_returns = self._calc_weekly_benchmark_returns(repo)

            context = {
                "portfolio": portfolio_manager.get_snapshot(),
                "weekly_trades": weekly_trades,
                "weekly_decisions": weekly_decisions,
                "performance_metrics": performance_metrics,
                "benchmark_returns": bench_returns,
                "previous_review": previous_review,
            }

            result = self.agent.run_weekly_review(context)

            # 勝率計算
            executed_decisions = [d for d in weekly_decisions if d.action in ("BUY", "SELL")]
            total_trades_count = len(executed_decisions)

            repo.save_weekly_review(
                agent_id=agent.id,
                review_date=today,
                week_start=week_start,
                week_end=week_end,
                performance_summary=result.performance_summary,
                good_decisions=result.good_decisions,
                bad_decisions=result.bad_decisions,
                key_learnings=result.key_learnings,
                improvement_plan=result.improvement_plan,
                next_week_strategy=result.next_week_strategy,
                next_week_rationale=result.next_week_rationale,
                total_trades=total_trades_count,
                total_pnl_jpy=weekly_pnl_jpy,
                system_prompt=result.system_prompt,
                user_prompt=result.user_prompt,
                ai_response=result.raw_response,
                model_id=result.model_id,
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
                api_cost_usd=result.api_cost_usd,
            )

            logger.info(
                f"週次反省会完了: 戦略={result.next_week_strategy}, cost=${result.api_cost_usd:.4f}"
            )

    def _load_portfolio(self, repo: Repository, agent_id: str) -> PortfolioManager:
        """DBからポートフォリオを復元、なければ初期化"""
        latest = repo.get_latest_portfolio(agent_id)
        if latest:
            return PortfolioManager.from_db_portfolio(latest)
        # 初期ポートフォリオ
        settings = get_settings()
        return PortfolioManager(
            initial_cash_jpy=settings.INITIAL_CAPITAL_JPY,
            fee_pct=settings.TRANSACTION_FEE_PCT,
        )

    def _calc_benchmark_values(
        self, repo: Repository, agent_id: str, current_prices: dict[str, float]
    ) -> dict:
        """ベンチマーク仮想運用額を計算 (同額で全額BUYホールドした場合)"""
        settings = get_settings()
        initial = settings.INITIAL_CAPITAL_JPY
        result = {}
        for sym, price in current_prices.items():
            initial_bp = repo.get_initial_benchmark_price(sym)
            if initial_bp and initial_bp.initial_price_jpy and initial_bp.initial_price_jpy > 0:
                units = initial / float(initial_bp.initial_price_jpy)
                current_value = units * price
                result[sym] = {
                    "initial_price_jpy": float(initial_bp.initial_price_jpy),
                    "current_price_jpy": price,
                    "current_value_jpy": current_value,
                    "return_pct": (current_value - initial) / initial * 100,
                }
        return result

    def _save_benchmark_prices(self, repo: Repository, prices: dict[str, float]):
        """ベンチマーク価格を保存"""
        for sym, price in prices.items():
            initial = repo.get_initial_benchmark_price(sym)
            initial_price = float(initial.initial_price_jpy) if initial else price
            ret_pct = (price - initial_price) / initial_price * 100 if initial_price > 0 else 0
            repo.save_benchmark_price(
                symbol=sym,
                recorded_at=datetime.utcnow(),
                price_jpy=price,
                initial_price_jpy=initial_price,
                return_pct=ret_pct,
            )

    def _calc_weekly_benchmark_returns(self, repo: Repository) -> dict[str, float]:
        """週次ベンチマークリターンを計算"""
        settings = get_settings()
        result = {}
        for sym in settings.BENCHMARK_SYMBOLS:
            history = repo.get_benchmark_history(sym, days=7)
            if len(history) >= 2:
                start = float(history[0].price_jpy)
                end = float(history[-1].price_jpy)
                if start > 0:
                    result[sym] = (end - start) / start * 100
        return result
