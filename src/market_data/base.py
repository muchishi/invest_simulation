from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
import pandas as pd


class AssetType(str, Enum):
    CRYPTO = "crypto"
    STOCK_US = "stock_us"
    STOCK_JP = "stock_jp"


@dataclass
class AssetData:
    symbol: str
    asset_type: AssetType
    price_usd: Optional[float]
    price_jpy: Optional[float]
    volume_24h: Optional[float]
    market_cap: Optional[float]
    price_change_1h_pct: Optional[float]
    price_change_24h_pct: Optional[float]
    price_change_7d_pct: Optional[float]
    high_24h: Optional[float] = None
    low_24h: Optional[float] = None
    captured_at: datetime = field(default_factory=datetime.utcnow)
    ohlcv: Optional[pd.DataFrame] = None  # OHLCV history for technical analysis
    raw_data: dict = field(default_factory=dict)

    def to_snapshot_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "asset_type": self.asset_type.value,
            "price_jpy": self.price_jpy,
            "price_usd": self.price_usd,
            "volume_24h": self.volume_24h,
            "market_cap": self.market_cap,
            "price_change_1h_pct": self.price_change_1h_pct,
            "price_change_24h_pct": self.price_change_24h_pct,
            "price_change_7d_pct": self.price_change_7d_pct,
            "captured_at": self.captured_at.isoformat(),
        }


class MarketDataProvider(ABC):
    """市場データプロバイダー抽象基底クラス"""

    @abstractmethod
    def get_asset_data(self, symbol: str) -> Optional[AssetData]:
        """単一銘柄のデータ取得"""
        ...

    @abstractmethod
    def get_multiple_assets(self, symbols: list[str]) -> dict[str, AssetData]:
        """複数銘柄のデータ取得"""
        ...

    @abstractmethod
    def get_ohlcv(self, symbol: str, period: str = "90d", interval: str = "1d") -> Optional[pd.DataFrame]:
        """OHLCV価格履歴取得"""
        ...

    @abstractmethod
    def get_usdjpy_rate(self) -> float:
        """USD/JPY レート取得"""
        ...
