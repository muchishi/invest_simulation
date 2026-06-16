import logging
import time
from datetime import datetime
from typing import Optional
import pandas as pd
import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from .base import MarketDataProvider, AssetData, AssetType

logger = logging.getLogger(__name__)

COINGECKO_BASE = "https://api.coingecko.com/api/v3"
COINGECKO_PRO_BASE = "https://pro-api.coingecko.com/api/v3"

# Symbol -> CoinGecko ID mapping
COIN_ID_MAP: dict[str, str] = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "XRP": "ripple",
    "BNB": "binancecoin",
    "ADA": "cardano",
    "DOGE": "dogecoin",
    "AVAX": "avalanche-2",
    "MATIC": "matic-network",
    "DOT": "polkadot",
}


class CoinGeckoProvider(MarketDataProvider):
    """CoinGecko データプロバイダー (仮想通貨)"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        # Demo keys (CG-...) use the public endpoint; Pro keys use the Pro endpoint
        self._is_demo = api_key is not None and api_key.startswith("CG-")
        self._is_pro = api_key is not None and not self._is_demo
        self.base_url = COINGECKO_PRO_BASE if self._is_pro else COINGECKO_BASE
        self._last_request_time = 0.0
        self._rate_limit_delay = 1.0 if api_key else 2.0  # demo: ~50req/min, free: 30req/min

    def _get_headers(self) -> dict:
        if self._is_pro:
            return {"x-cg-pro-api-key": self.api_key}
        if self._is_demo:
            return {"x-cg-demo-api-key": self.api_key}
        return {}

    def _rate_limit(self):
        elapsed = time.time() - self._last_request_time
        if elapsed < self._rate_limit_delay:
            time.sleep(self._rate_limit_delay - elapsed)
        self._last_request_time = time.time()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=3, max=15))
    def _get(self, path: str, params: dict = None) -> dict:
        self._rate_limit()
        url = f"{self.base_url}{path}"
        resp = requests.get(url, headers=self._get_headers(), params=params or {}, timeout=15)
        resp.raise_for_status()
        return resp.json()

    def get_usdjpy_rate(self) -> float:
        try:
            data = self._get("/simple/price", {"ids": "bitcoin", "vs_currencies": "jpy,usd"})
            btc_jpy = data["bitcoin"]["jpy"]
            btc_usd = data["bitcoin"]["usd"]
            return btc_jpy / btc_usd
        except Exception as e:
            logger.warning(f"CoinGecko USDJPY failed: {e}")
            return 150.0

    def get_asset_data(self, symbol: str) -> Optional[AssetData]:
        coin_id = COIN_ID_MAP.get(symbol.upper())
        if not coin_id:
            logger.warning(f"Unknown coin symbol: {symbol}")
            return None
        try:
            data = self._get(
                f"/coins/{coin_id}",
                {
                    "localization": "false",
                    "tickers": "false",
                    "community_data": "false",
                    "developer_data": "false",
                    "sparkline": "false",
                },
            )
            market = data.get("market_data", {})

            price_usd = market.get("current_price", {}).get("usd")
            price_jpy = market.get("current_price", {}).get("jpy")
            volume_24h = market.get("total_volume", {}).get("usd")
            market_cap = market.get("market_cap", {}).get("usd")
            change_1h = market.get("price_change_percentage_1h_in_currency", {}).get("usd")
            change_24h = market.get("price_change_percentage_24h")
            change_7d = market.get("price_change_percentage_7d")
            high_24h = market.get("high_24h", {}).get("jpy")
            low_24h = market.get("low_24h", {}).get("jpy")

            ohlcv = self.get_ohlcv(symbol)

            return AssetData(
                symbol=symbol,
                asset_type=AssetType.CRYPTO,
                price_usd=price_usd,
                price_jpy=price_jpy,
                volume_24h=volume_24h,
                market_cap=market_cap,
                price_change_1h_pct=change_1h,
                price_change_24h_pct=change_24h,
                price_change_7d_pct=change_7d,
                high_24h=high_24h,
                low_24h=low_24h,
                ohlcv=ohlcv,
                raw_data={"coin_id": coin_id, "name": data.get("name")},
            )
        except Exception as e:
            logger.error(f"CoinGecko error for {symbol}: {e}")
            return None

    def get_multiple_assets(self, symbols: list[str]) -> dict[str, AssetData]:
        coin_ids = [COIN_ID_MAP[s] for s in symbols if s in COIN_ID_MAP]
        if not coin_ids:
            return {}
        try:
            # Bulk price fetch
            bulk_data = self._get(
                "/simple/price",
                {
                    "ids": ",".join(coin_ids),
                    "vs_currencies": "usd,jpy",
                    "include_24hr_change": "true",
                    "include_24hr_vol": "true",
                    "include_market_cap": "true",
                },
            )
        except Exception as e:
            logger.error(f"Bulk CoinGecko fetch failed: {e}")
            bulk_data = {}

        result = {}
        for symbol in symbols:
            coin_id = COIN_ID_MAP.get(symbol)
            if not coin_id or coin_id not in bulk_data:
                continue
            d = bulk_data[coin_id]
            # Fetch full data individually for OHLCV
            full = self.get_asset_data(symbol)
            if full:
                result[symbol] = full
        return result

    def get_ohlcv(self, symbol: str, period: str = "90d", interval: str = "1d") -> Optional[pd.DataFrame]:
        coin_id = COIN_ID_MAP.get(symbol.upper())
        if not coin_id:
            return None
        try:
            # CoinGecko market_chart returns daily OHLCV for 90d
            days = int(period.replace("d", "")) if "d" in period else 90
            data = self._get(
                f"/coins/{coin_id}/ohlc",
                {"vs_currency": "usd", "days": str(min(days, 90))},
            )
            if not data:
                return None
            df = pd.DataFrame(data, columns=["timestamp", "open", "high", "low", "close"])
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            df = df.set_index("timestamp")
            df["volume"] = 0.0  # OHLC endpoint doesn't include volume
            return df
        except Exception as e:
            logger.error(f"CoinGecko OHLCV error for {symbol}: {e}")
            return None
