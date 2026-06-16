import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from src.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class Position:
    symbol: str
    asset_type: str
    quantity: float
    avg_cost_jpy: float  # per unit
    current_price_jpy: float = 0.0

    @property
    def total_cost_jpy(self) -> float:
        return self.quantity * self.avg_cost_jpy

    @property
    def current_value_jpy(self) -> float:
        return self.quantity * self.current_price_jpy

    @property
    def unrealized_pnl_jpy(self) -> float:
        return self.current_value_jpy - self.total_cost_jpy

    @property
    def unrealized_pnl_pct(self) -> float:
        if self.total_cost_jpy == 0:
            return 0.0
        return (self.unrealized_pnl_jpy / self.total_cost_jpy) * 100

    def to_dict(self, total_value: float = 0.0) -> dict:
        pct = (self.current_value_jpy / total_value * 100) if total_value > 0 else 0
        return {
            "symbol": self.symbol,
            "asset_type": self.asset_type,
            "quantity": self.quantity,
            "avg_cost_jpy": self.avg_cost_jpy,
            "current_price_jpy": self.current_price_jpy,
            "total_cost_jpy": self.total_cost_jpy,
            "current_value_jpy": self.current_value_jpy,
            "unrealized_pnl_jpy": self.unrealized_pnl_jpy,
            "unrealized_pnl_pct": self.unrealized_pnl_pct,
            "portfolio_pct": pct,
        }


@dataclass
class PortfolioState:
    cash_balance_jpy: float
    positions: dict[str, Position] = field(default_factory=dict)
    realized_pnl_jpy: float = 0.0

    @property
    def total_cost_jpy(self) -> float:
        return sum(p.total_cost_jpy for p in self.positions.values())

    @property
    def total_holdings_value_jpy(self) -> float:
        return sum(p.current_value_jpy for p in self.positions.values())

    @property
    def total_value_jpy(self) -> float:
        return self.cash_balance_jpy + self.total_holdings_value_jpy

    @property
    def unrealized_pnl_jpy(self) -> float:
        return sum(p.unrealized_pnl_jpy for p in self.positions.values())

    @property
    def total_return_pct(self) -> float:
        settings = get_settings()
        initial = settings.INITIAL_CAPITAL_JPY
        if initial == 0:
            return 0.0
        return (self.total_value_jpy - initial) / initial * 100

    def update_prices(self, prices: dict[str, float]):
        """現在価格を更新"""
        for symbol, price in prices.items():
            if symbol in self.positions:
                self.positions[symbol].current_price_jpy = price

    def to_dict(self) -> dict:
        total = self.total_value_jpy
        holdings = [p.to_dict(total) for p in self.positions.values()]
        return {
            "cash_balance_jpy": self.cash_balance_jpy,
            "total_value_jpy": total,
            "total_cost_jpy": self.total_cost_jpy,
            "total_holdings_value_jpy": self.total_holdings_value_jpy,
            "unrealized_pnl_jpy": self.unrealized_pnl_jpy,
            "realized_pnl_jpy": self.realized_pnl_jpy,
            "total_return_pct": self.total_return_pct,
            "holdings": holdings,
            "position_count": len(self.positions),
        }


class PortfolioManager:
    """ポートフォリオ管理クラス"""

    def __init__(self, initial_cash_jpy: float, fee_pct: float = 0.001):
        self.state = PortfolioState(cash_balance_jpy=initial_cash_jpy)
        self.fee_pct = fee_pct
        settings = get_settings()
        self.max_position_pct = settings.MAX_POSITION_PCT
        self.max_positions = settings.MAX_POSITIONS

    @classmethod
    def from_db_portfolio(cls, portfolio_row) -> "PortfolioManager":
        """DBのポートフォリオレコードからPortfolioManagerを復元"""
        settings = get_settings()
        manager = cls(
            initial_cash_jpy=float(portfolio_row.cash_balance_jpy),
            fee_pct=settings.TRANSACTION_FEE_PCT,
        )
        manager.state.cash_balance_jpy = float(portfolio_row.cash_balance_jpy)
        manager.state.realized_pnl_jpy = float(portfolio_row.realized_pnl_jpy or 0)

        for h in (portfolio_row.holdings or []):
            manager.state.positions[h["symbol"]] = Position(
                symbol=h["symbol"],
                asset_type=h.get("asset_type", "unknown"),
                quantity=float(h["quantity"]),
                avg_cost_jpy=float(h["avg_cost_jpy"]),
                current_price_jpy=float(h.get("current_price_jpy", h["avg_cost_jpy"])),
            )
        return manager

    def can_buy(self, symbol: str, amount_jpy: float, price_jpy: float) -> tuple[bool, str]:
        """BUY可能性チェック"""
        total_value = self.state.total_value_jpy

        # 十分な現金があるか
        total_cost = amount_jpy * (1 + self.fee_pct)
        if self.state.cash_balance_jpy < total_cost:
            return False, f"残高不足: 必要{total_cost:,.0f}円 / 保有{self.state.cash_balance_jpy:,.0f}円"

        # 最大ポジション数チェック
        if symbol not in self.state.positions and len(self.state.positions) >= self.max_positions:
            return False, f"最大保有銘柄数 {self.max_positions} に達しています"

        # ポジションサイズチェック
        existing_value = self.state.positions.get(symbol, Position(symbol, "", 0, 0)).current_value_jpy
        new_value = existing_value + amount_jpy
        max_allowed = total_value * self.max_position_pct
        if new_value > max_allowed:
            return False, f"1銘柄最大{self.max_position_pct*100:.0f}%超過: {new_value:,.0f}円 > {max_allowed:,.0f}円"

        return True, "OK"

    def can_sell(self, symbol: str, quantity: float) -> tuple[bool, str]:
        """SELL可能性チェック"""
        if symbol not in self.state.positions:
            return False, f"{symbol} を保有していません"
        pos = self.state.positions[symbol]
        if pos.quantity < quantity:
            return False, f"保有数量不足: 保有{pos.quantity} / 売却要求{quantity}"
        return True, "OK"

    def execute_buy(
        self, symbol: str, asset_type: str, quantity: float, price_jpy: float
    ) -> tuple[float, float, float]:
        """BUY実行。(amount_jpy, fee_jpy, total_jpy) を返す"""
        amount_jpy = quantity * price_jpy
        fee_jpy = amount_jpy * self.fee_pct
        total_jpy = amount_jpy + fee_jpy

        if self.state.cash_balance_jpy < total_jpy:
            raise ValueError(f"残高不足: {self.state.cash_balance_jpy:,.0f} < {total_jpy:,.0f}")

        self.state.cash_balance_jpy -= total_jpy

        if symbol in self.state.positions:
            pos = self.state.positions[symbol]
            new_qty = pos.quantity + quantity
            # VWAP average cost
            pos.avg_cost_jpy = (pos.total_cost_jpy + amount_jpy) / new_qty
            pos.quantity = new_qty
            pos.current_price_jpy = price_jpy
        else:
            self.state.positions[symbol] = Position(
                symbol=symbol,
                asset_type=asset_type,
                quantity=quantity,
                avg_cost_jpy=price_jpy,
                current_price_jpy=price_jpy,
            )

        logger.info(
            f"BUY {symbol}: {quantity} @ {price_jpy:,.2f}円 (手数料 {fee_jpy:,.2f}円)"
        )
        return amount_jpy, fee_jpy, total_jpy

    def execute_sell(
        self, symbol: str, quantity: float, price_jpy: float
    ) -> tuple[float, float, float, float]:
        """SELL実行。(amount_jpy, fee_jpy, net_jpy, realized_pnl_jpy) を返す"""
        if symbol not in self.state.positions:
            raise ValueError(f"{symbol} を保有していません")

        pos = self.state.positions[symbol]
        amount_jpy = quantity * price_jpy
        fee_jpy = amount_jpy * self.fee_pct
        net_jpy = amount_jpy - fee_jpy

        cost_basis = quantity * pos.avg_cost_jpy
        realized_pnl = net_jpy - cost_basis

        self.state.cash_balance_jpy += net_jpy
        self.state.realized_pnl_jpy += realized_pnl

        remaining_qty = pos.quantity - quantity
        if remaining_qty <= 1e-10:
            del self.state.positions[symbol]
        else:
            pos.quantity = remaining_qty

        logger.info(
            f"SELL {symbol}: {quantity} @ {price_jpy:,.2f}円 "
            f"(確定損益 {realized_pnl:+,.2f}円, 手数料 {fee_jpy:,.2f}円)"
        )
        return amount_jpy, fee_jpy, net_jpy, realized_pnl

    def calculate_buy_quantity(
        self, symbol: str, price_jpy: float, asset_type: str, target_amount_jpy: Optional[float] = None
    ) -> tuple[float, float]:
        """適切なBUY数量を計算。(quantity, actual_amount_jpy) を返す"""
        if target_amount_jpy is None:
            # デフォルト: 利用可能資金の20%以内、かつ最大ポジションサイズ以内
            max_by_rule = self.state.total_value_jpy * self.max_position_pct
            existing_value = 0.0
            if symbol in self.state.positions:
                existing_value = self.state.positions[symbol].current_value_jpy
            available_for_symbol = max(0, max_by_rule - existing_value)
            available_cash = self.state.cash_balance_jpy / (1 + self.fee_pct)
            target_amount_jpy = min(available_cash, available_for_symbol)

        if price_jpy <= 0 or target_amount_jpy <= 0:
            return 0.0, 0.0

        if asset_type == "crypto":
            # 小数点購入可
            quantity = target_amount_jpy / price_jpy
        else:
            # 整数株単位
            quantity = int(target_amount_jpy / price_jpy)
            if quantity < 1:
                return 0.0, 0.0

        actual_amount = quantity * price_jpy
        return quantity, actual_amount

    def get_snapshot(self) -> dict:
        return self.state.to_dict()
