"""PortfolioManager の単体テスト"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from unittest.mock import patch, MagicMock
from src.trading.portfolio import PortfolioManager, Position, PortfolioState


class TestPortfolioManager(unittest.TestCase):

    def setUp(self):
        self.pm = PortfolioManager(initial_cash_jpy=100_000.0, fee_pct=0.001)

    def test_initial_state(self):
        self.assertEqual(self.pm.state.cash_balance_jpy, 100_000.0)
        self.assertEqual(len(self.pm.state.positions), 0)
        self.assertEqual(self.pm.state.total_value_jpy, 100_000.0)

    def test_buy_crypto(self):
        amount, fee, total = self.pm.execute_buy("BTC", "crypto", 0.01, 7_000_000.0)
        self.assertAlmostEqual(amount, 70_000.0)
        self.assertAlmostEqual(fee, 70.0)
        self.assertAlmostEqual(total, 70_070.0)
        self.assertIn("BTC", self.pm.state.positions)
        self.assertAlmostEqual(self.pm.state.cash_balance_jpy, 29_930.0)
        self.assertAlmostEqual(self.pm.state.positions["BTC"].quantity, 0.01)

    def test_buy_insufficient_cash(self):
        with self.assertRaises(ValueError):
            self.pm.execute_buy("BTC", "crypto", 10.0, 7_000_000.0)

    def test_sell_position(self):
        self.pm.execute_buy("BTC", "crypto", 0.01, 7_000_000.0)
        amount, fee, net, pnl = self.pm.execute_sell("BTC", 0.01, 8_000_000.0)
        self.assertAlmostEqual(amount, 80_000.0)
        self.assertAlmostEqual(fee, 80.0)
        self.assertAlmostEqual(net, 79_920.0)
        self.assertGreater(pnl, 0)  # profit
        self.assertNotIn("BTC", self.pm.state.positions)

    def test_sell_no_position(self):
        with self.assertRaises(ValueError):
            self.pm.execute_sell("BTC", 0.01, 7_000_000.0)

    def test_can_buy_max_positions(self):
        # Fill max positions
        for i, sym in enumerate(["A", "B", "C", "D", "E"]):
            self.pm.state.positions[sym] = Position(sym, "stock", 1, 10_000.0, 10_000.0)
        can, reason = self.pm.can_buy("F", 10_000.0, 10_000.0)
        self.assertFalse(can)
        self.assertIn("最大保有銘柄数", reason)

    def test_can_buy_max_position_size(self):
        can, reason = self.pm.can_buy("BTC", 30_000.0, 7_000_000.0)
        # 30_000 / 100_000 = 30% > 20%
        self.assertFalse(can)
        self.assertIn("最大", reason)

    def test_average_cost_updated_on_additional_buy(self):
        # Use a larger portfolio for this test
        pm = PortfolioManager(initial_cash_jpy=1_000_000.0, fee_pct=0.001)
        pm.execute_buy("ETH", "crypto", 1.0, 300_000.0)
        pm.execute_buy("ETH", "crypto", 1.0, 400_000.0)
        pos = pm.state.positions["ETH"]
        self.assertAlmostEqual(pos.quantity, 2.0)
        # VWAP: (300000 + 400000) / 2 = 350000
        self.assertAlmostEqual(pos.avg_cost_jpy, 350_000.0, places=0)

    def test_calculate_buy_quantity_crypto(self):
        qty, amount = self.pm.calculate_buy_quantity("BTC", 7_000_000.0, "crypto")
        self.assertGreater(qty, 0)
        self.assertLessEqual(amount, 100_000.0 * 0.20)

    def test_calculate_buy_quantity_stock_integer(self):
        qty, amount = self.pm.calculate_buy_quantity("AAPL", 30_000.0, "stock_us")
        self.assertEqual(qty, int(qty))  # must be integer

    def test_total_return_pct(self):
        self.pm.execute_buy("BTC", "crypto", 0.001, 7_000_000.0)
        self.pm.state.positions["BTC"].current_price_jpy = 8_000_000.0
        # Unrealized profit: 0.001 * 1_000_000 = 1000
        # Total: 100000 - 7007 + 8000 = 100993
        total = self.pm.state.total_value_jpy
        self.assertGreater(total, 100_000.0)


class TestTechnicalIndicators(unittest.TestCase):

    def test_rsi_calculation(self):
        import pandas as pd
        import numpy as np
        from src.technical.indicators import TechnicalAnalyzer

        np.random.seed(42)
        prices = 100 + np.cumsum(np.random.randn(50) * 2)
        df = pd.DataFrame({
            "open": prices * 0.99,
            "high": prices * 1.01,
            "low": prices * 0.98,
            "close": prices,
            "volume": np.random.randint(1000, 10000, 50).astype(float),
        })

        analyzer = TechnicalAnalyzer()
        ind = analyzer.analyze(df, "TEST")

        self.assertIsNotNone(ind.rsi_14)
        self.assertGreaterEqual(ind.rsi_14, 0)
        self.assertLessEqual(ind.rsi_14, 100)
        self.assertIsNotNone(ind.macd)
        self.assertIsNotNone(ind.trend)
        self.assertIn(ind.trend, ["uptrend", "downtrend", "sideways"])

    def test_empty_dataframe(self):
        import pandas as pd
        from src.technical.indicators import TechnicalAnalyzer

        analyzer = TechnicalAnalyzer()
        ind = analyzer.analyze(pd.DataFrame(), "TEST")
        self.assertIsNone(ind.rsi_14)
        self.assertIsNone(ind.trend)


if __name__ == "__main__":
    unittest.main()
