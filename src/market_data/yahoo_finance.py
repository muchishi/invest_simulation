import logging
from datetime import datetime
from typing import Optional
import pandas as pd
import yfinance as yf
from tenacity import retry, stop_after_attempt, wait_exponential

from .base import MarketDataProvider, AssetData, AssetType

logger = logging.getLogger(__name__)


class YahooFinanceProvider(MarketDataProvider):
    """Yahoo Finance データプロバイダー (株式・ベンチマーク)"""

    def get_usdjpy_rate(self) -> float:
        try:
            ticker = yf.Ticker("USDJPY=X")
            hist = ticker.history(period="2d")
            if not hist.empty:
                return float(hist["Close"].iloc[-1])
        except Exception as e:
            logger.warning(f"USDJPY fetch failed: {e}")
        return 150.0  # fallback

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def get_asset_data(self, symbol: str) -> Optional[AssetData]:
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            hist = ticker.history(period="8d", interval="1d")

            if hist.empty:
                logger.warning(f"No data for {symbol}")
                return None

            usdjpy = self.get_usdjpy_rate()
            current_price_usd = float(hist["Close"].iloc[-1])

            # 日本株はすでにJPY建て
            if symbol.endswith(".T"):
                asset_type = AssetType.STOCK_JP
                price_jpy = current_price_usd
                price_usd = current_price_usd / usdjpy
            else:
                asset_type = AssetType.STOCK_US
                price_jpy = current_price_usd * usdjpy
                price_usd = current_price_usd

            # 変化率計算
            if len(hist) >= 2:
                prev_close = float(hist["Close"].iloc[-2])
                change_24h = (current_price_usd - prev_close) / prev_close * 100 if prev_close else None
            else:
                change_24h = None

            if len(hist) >= 7:
                price_7d_ago = float(hist["Close"].iloc[-7])
                change_7d = (current_price_usd - price_7d_ago) / price_7d_ago * 100 if price_7d_ago else None
            else:
                change_7d = None

            volume_24h = float(hist["Volume"].iloc[-1]) if "Volume" in hist.columns else None
            high_24h = float(hist["High"].iloc[-1]) if "High" in hist.columns else None
            low_24h = float(hist["Low"].iloc[-1]) if "Low" in hist.columns else None
            market_cap = info.get("marketCap")

            ohlcv = self._get_ohlcv_df(symbol)

            return AssetData(
                symbol=symbol,
                asset_type=asset_type,
                price_usd=price_usd,
                price_jpy=price_jpy,
                volume_24h=volume_24h,
                market_cap=float(market_cap) if market_cap else None,
                price_change_1h_pct=None,
                price_change_24h_pct=change_24h,
                price_change_7d_pct=change_7d,
                high_24h=high_24h * (usdjpy if not symbol.endswith(".T") else 1) if high_24h else None,
                low_24h=low_24h * (usdjpy if not symbol.endswith(".T") else 1) if low_24h else None,
                ohlcv=ohlcv,
                raw_data={"info": {k: v for k, v in info.items() if isinstance(v, (str, int, float, bool, type(None)))}},
            )
        except Exception as e:
            logger.error(f"Error fetching {symbol}: {e}")
            return None

    def get_multiple_assets(self, symbols: list[str]) -> dict[str, AssetData]:
        result = {}
        for symbol in symbols:
            data = self.get_asset_data(symbol)
            if data:
                result[symbol] = data
        return result

    def get_ohlcv(self, symbol: str, period: str = "90d", interval: str = "1d") -> Optional[pd.DataFrame]:
        return self._get_ohlcv_df(symbol, period, interval)

    def _get_ohlcv_df(self, symbol: str, period: str = "90d", interval: str = "1d") -> Optional[pd.DataFrame]:
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period, interval=interval)
            if hist.empty:
                return None
            hist.index = pd.to_datetime(hist.index)
            return hist[["Open", "High", "Low", "Close", "Volume"]].rename(
                columns=str.lower
            )
        except Exception as e:
            logger.error(f"OHLCV fetch error for {symbol}: {e}")
            return None

    def get_benchmark_data(self, symbols: list[str]) -> dict[str, float]:
        """ベンチマーク現在価格取得 (JPY)"""
        prices = {}
        usdjpy = self.get_usdjpy_rate()
        for sym in symbols:
            try:
                ticker = yf.Ticker(sym)
                hist = ticker.history(period="2d")
                if not hist.empty:
                    price_usd = float(hist["Close"].iloc[-1])
                    prices[sym] = price_usd * usdjpy
            except Exception as e:
                logger.warning(f"Benchmark fetch failed for {sym}: {e}")
        return prices
