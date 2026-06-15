import logging
from typing import Optional
from .base import MarketDataProvider, AssetData, AssetType
from .yahoo_finance import YahooFinanceProvider
from .coingecko import CoinGeckoProvider
from src.config import get_settings

logger = logging.getLogger(__name__)


class MarketDataFactory:
    """市場データプロバイダーファクトリー (将来的な切り替え対応)"""

    def __init__(self):
        settings = get_settings()
        self._yf = YahooFinanceProvider()
        self._cg = CoinGeckoProvider(api_key=settings.COINGECKO_API_KEY)

    def get_provider(self, asset_type: AssetType) -> MarketDataProvider:
        if asset_type == AssetType.CRYPTO:
            return self._cg
        return self._yf

    def get_usdjpy_rate(self) -> float:
        return self._yf.get_usdjpy_rate()

    def get_all_tracked_assets(self) -> dict[str, AssetData]:
        """全追跡銘柄のデータを取得"""
        settings = get_settings()
        result: dict[str, AssetData] = {}

        # Crypto
        logger.info("Fetching crypto data...")
        for sym in settings.CRYPTO_SYMBOLS:
            data = self._cg.get_asset_data(sym)
            if data:
                result[sym] = data

        # US Stocks
        logger.info("Fetching US stock data...")
        us_data = self._yf.get_multiple_assets(settings.US_STOCK_SYMBOLS)
        result.update(us_data)

        # JP Stocks
        logger.info("Fetching JP stock data...")
        jp_data = self._yf.get_multiple_assets(settings.JP_STOCK_SYMBOLS)
        result.update(jp_data)

        logger.info(f"Fetched data for {len(result)} assets")
        return result

    def get_benchmark_prices(self) -> dict[str, float]:
        """ベンチマーク価格取得 (JPY)"""
        settings = get_settings()
        usdjpy = self.get_usdjpy_rate()
        prices: dict[str, float] = {}

        # Crypto benchmarks via CoinGecko
        for sym in ["BTC", "ETH"]:
            data = self._cg.get_asset_data(sym)
            if data and data.price_jpy:
                prices[f"{sym}-USD"] = data.price_jpy

        # ETF benchmarks via Yahoo Finance
        yf_symbols = ["SPY", "QQQ", "VT"]
        for sym in yf_symbols:
            data = self._yf.get_asset_data(sym)
            if data and data.price_jpy:
                prices[sym] = data.price_jpy

        return prices
