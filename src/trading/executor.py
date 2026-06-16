import logging
from datetime import datetime, timedelta
from typing import Optional

from src.config import get_settings
from src.ai.base import AssetDecision, EveningDecisionResult
from src.db.repository import Repository
from src.market_data.base import AssetData
from .portfolio import PortfolioManager

logger = logging.getLogger(__name__)


class TradeExecutor:
    """仮想売買実行クラス"""

    def __init__(self, portfolio: PortfolioManager, repo: Repository):
        self.portfolio = portfolio
        self.repo = repo
        settings = get_settings()
        self.fee_pct = settings.TRANSACTION_FEE_PCT

    def execute_decisions(
        self,
        agent_id: str,
        decisions: list[AssetDecision],
        market_data: dict[str, AssetData],
        morning_analysis_id: Optional[str],
        evening_result: EveningDecisionResult,
    ) -> list[dict]:
        """夕方の判断を実行し、トレード結果を返す"""
        executed = []
        now = datetime.utcnow()

        for decision in decisions:
            sym = decision.symbol
            action = decision.action

            # HOLD はトレード不要
            if action == "HOLD":
                self._save_decision(
                    agent_id=agent_id,
                    decision=decision,
                    morning_analysis_id=morning_analysis_id,
                    evening_result=evening_result,
                    trade_id=None,
                    market_data=market_data,
                    now=now,
                )
                executed.append({"symbol": sym, "action": "HOLD", "executed": False})
                continue

            # 市場データ確認
            asset_data = market_data.get(sym)
            if not asset_data or not asset_data.price_jpy:
                logger.warning(f"No market data for {sym}, skipping")
                continue

            price_jpy = asset_data.price_jpy
            price_usd = asset_data.price_usd
            asset_type = asset_data.asset_type.value

            # 24時間以内の同銘柄売買チェック
            recent = self.repo.get_recent_trades_for_symbol(agent_id, sym, hours=24)
            if recent:
                logger.info(f"Skipping {sym}: traded within 24h")
                executed.append({"symbol": sym, "action": action, "executed": False, "reason": "24h restriction"})
                continue

            trade_id = None
            if action == "BUY":
                result = self._execute_buy(
                    agent_id, sym, asset_type, price_jpy, price_usd, decision, now
                )
                if result:
                    trade_id = result["trade_id"]
                    executed.append({**result, "executed": True})
                else:
                    executed.append({"symbol": sym, "action": "BUY", "executed": False})

            elif action == "SELL":
                result = self._execute_sell(
                    agent_id, sym, price_jpy, price_usd, decision, now
                )
                if result:
                    trade_id = result["trade_id"]
                    executed.append({**result, "executed": True})
                else:
                    executed.append({"symbol": sym, "action": "SELL", "executed": False})

            self._save_decision(
                agent_id=agent_id,
                decision=decision,
                morning_analysis_id=morning_analysis_id,
                evening_result=evening_result,
                trade_id=trade_id,
                market_data=market_data,
                now=now,
            )

        return executed

    def _execute_buy(
        self,
        agent_id: str,
        symbol: str,
        asset_type: str,
        price_jpy: float,
        price_usd: Optional[float],
        decision: AssetDecision,
        now: datetime,
    ) -> Optional[dict]:
        # 数量決定
        if decision.quantity and decision.quantity > 0:
            quantity = decision.quantity
            # 整数制限
            if asset_type != "crypto":
                quantity = int(quantity)
            if quantity <= 0:
                return None
            can, reason = self.portfolio.can_buy(symbol, quantity * price_jpy, price_jpy)
        else:
            quantity, _ = self.portfolio.calculate_buy_quantity(symbol, price_jpy, asset_type)
            if quantity <= 0:
                logger.info(f"Cannot determine buy quantity for {symbol}")
                return None
            can, reason = self.portfolio.can_buy(symbol, quantity * price_jpy, price_jpy)

        if not can:
            logger.info(f"Cannot buy {symbol}: {reason}")
            return None

        try:
            amount_jpy, fee_jpy, total_jpy = self.portfolio.execute_buy(
                symbol, asset_type, quantity, price_jpy
            )
        except ValueError as e:
            logger.error(f"BUY execution failed for {symbol}: {e}")
            return None

        trade = self.repo.save_trade(
            agent_id=agent_id,
            executed_at=now,
            symbol=symbol,
            asset_type=asset_type,
            action="BUY",
            quantity=quantity,
            price_jpy=price_jpy,
            price_usd=price_usd,
            total_amount_jpy=amount_jpy,
            fee_jpy=fee_jpy,
        )

        logger.info(f"BUY executed: {symbol} x{quantity} @ {price_jpy:,.2f}円")
        return {
            "symbol": symbol,
            "action": "BUY",
            "quantity": quantity,
            "price_jpy": price_jpy,
            "amount_jpy": amount_jpy,
            "fee_jpy": fee_jpy,
            "trade_id": trade.id,
        }

    def _execute_sell(
        self,
        agent_id: str,
        symbol: str,
        price_jpy: float,
        price_usd: Optional[float],
        decision: AssetDecision,
        now: datetime,
    ) -> Optional[dict]:
        if symbol not in self.portfolio.state.positions:
            logger.info(f"No position in {symbol} to sell")
            return None

        pos = self.portfolio.state.positions[symbol]
        asset_type = pos.asset_type

        # 数量決定
        if decision.quantity and decision.quantity > 0:
            quantity = min(decision.quantity, pos.quantity)
            if asset_type != "crypto":
                quantity = int(quantity)
        else:
            quantity = pos.quantity  # 全量売却

        if quantity <= 0:
            return None

        can, reason = self.portfolio.can_sell(symbol, quantity)
        if not can:
            logger.info(f"Cannot sell {symbol}: {reason}")
            return None

        try:
            amount_jpy, fee_jpy, net_jpy, realized_pnl = self.portfolio.execute_sell(
                symbol, quantity, price_jpy
            )
        except ValueError as e:
            logger.error(f"SELL execution failed for {symbol}: {e}")
            return None

        trade = self.repo.save_trade(
            agent_id=agent_id,
            executed_at=now,
            symbol=symbol,
            asset_type=asset_type,
            action="SELL",
            quantity=quantity,
            price_jpy=price_jpy,
            price_usd=price_usd,
            total_amount_jpy=amount_jpy,
            fee_jpy=fee_jpy,
            notes=f"確定損益: {realized_pnl:+,.2f}円",
        )

        logger.info(f"SELL executed: {symbol} x{quantity} @ {price_jpy:,.2f}円 PnL={realized_pnl:+,.0f}円")
        return {
            "symbol": symbol,
            "action": "SELL",
            "quantity": quantity,
            "price_jpy": price_jpy,
            "amount_jpy": amount_jpy,
            "fee_jpy": fee_jpy,
            "realized_pnl_jpy": realized_pnl,
            "trade_id": trade.id,
        }

    def _save_decision(
        self,
        agent_id: str,
        decision: AssetDecision,
        morning_analysis_id: Optional[str],
        evening_result: EveningDecisionResult,
        trade_id: Optional[str],
        market_data: dict,
        now: datetime,
    ):
        snapshot = self.portfolio.get_snapshot()
        asset_data = market_data.get(decision.symbol)

        self.repo.save_decision(
            agent_id=agent_id,
            morning_analysis_id=morning_analysis_id,
            decided_at=now,
            session_type="evening",
            symbol=decision.symbol,
            action=decision.action,
            quantity=decision.quantity,
            confidence=decision.confidence,
            expected_return_pct=decision.expected_return_pct,
            risk_level=decision.risk_level,
            investment_period=decision.expected_timeframe,
            reasoning=decision.reasoning,
            key_factors=decision.key_factors,
            system_prompt=evening_result.system_prompt,
            user_prompt=evening_result.user_prompt,
            ai_response=evening_result.raw_response,
            model_id=evening_result.model_id,
            input_tokens=evening_result.input_tokens,
            output_tokens=evening_result.output_tokens,
            api_cost_usd=evening_result.api_cost_usd,
            portfolio_snapshot=snapshot,
            market_data_snapshot=asset_data.to_snapshot_dict() if asset_data else None,
        )
