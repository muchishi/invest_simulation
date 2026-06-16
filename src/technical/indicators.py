import logging
from dataclasses import dataclass
from typing import Optional
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class TechnicalIndicators:
    symbol: str
    # Trend
    sma_20: Optional[float] = None
    sma_50: Optional[float] = None
    sma_200: Optional[float] = None
    ema_12: Optional[float] = None
    ema_26: Optional[float] = None
    # Momentum
    rsi_14: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_histogram: Optional[float] = None
    stoch_k: Optional[float] = None
    stoch_d: Optional[float] = None
    # Volatility
    bb_upper: Optional[float] = None
    bb_middle: Optional[float] = None
    bb_lower: Optional[float] = None
    bb_width: Optional[float] = None
    bb_pct_b: Optional[float] = None
    atr_14: Optional[float] = None
    volatility_20d: Optional[float] = None
    # Volume
    obv: Optional[float] = None
    volume_sma_20: Optional[float] = None
    volume_ratio: Optional[float] = None
    # Price levels
    current_price: Optional[float] = None
    support_level: Optional[float] = None
    resistance_level: Optional[float] = None
    # Trend signals
    trend: Optional[str] = None  # uptrend/downtrend/sideways
    rsi_signal: Optional[str] = None  # overbought/oversold/neutral

    def to_dict(self) -> dict:
        return {k: (round(v, 6) if isinstance(v, float) else v) for k, v in self.__dict__.items()}

    def get_summary(self) -> str:
        parts = []
        if self.rsi_14 is not None:
            parts.append(f"RSI={self.rsi_14:.1f}({self.rsi_signal})")
        if self.macd is not None:
            parts.append(f"MACD={self.macd:.4f}(hist={self.macd_histogram:.4f})")
        if self.bb_pct_b is not None:
            parts.append(f"BB%B={self.bb_pct_b:.2f}")
        if self.trend:
            parts.append(f"Trend={self.trend}")
        if self.sma_20 and self.current_price:
            pct = (self.current_price - self.sma_20) / self.sma_20 * 100
            parts.append(f"Price vs SMA20={pct:+.1f}%")
        return " | ".join(parts)


class TechnicalAnalyzer:
    """テクニカル指標算出クラス"""

    def analyze(self, df: pd.DataFrame, symbol: str) -> TechnicalIndicators:
        if df is None or df.empty or len(df) < 20:
            return TechnicalIndicators(symbol=symbol)

        close = df["close"].astype(float)
        high = df["high"].astype(float)
        low = df["low"].astype(float)
        volume = df["volume"].astype(float) if "volume" in df.columns else pd.Series(dtype=float)

        ind = TechnicalIndicators(symbol=symbol)
        ind.current_price = float(close.iloc[-1])

        # ── Moving Averages ───────────────────────────────────
        if len(close) >= 20:
            ind.sma_20 = float(close.rolling(20).mean().iloc[-1])
        if len(close) >= 50:
            ind.sma_50 = float(close.rolling(50).mean().iloc[-1])
        if len(close) >= 200:
            ind.sma_200 = float(close.rolling(200).mean().iloc[-1])

        # EMA
        ind.ema_12 = float(close.ewm(span=12, adjust=False).mean().iloc[-1])
        ind.ema_26 = float(close.ewm(span=26, adjust=False).mean().iloc[-1])

        # ── MACD ─────────────────────────────────────────────
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        macd_line = ema12 - ema26
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        ind.macd = float(macd_line.iloc[-1])
        ind.macd_signal = float(signal_line.iloc[-1])
        ind.macd_histogram = float((macd_line - signal_line).iloc[-1])

        # ── RSI ───────────────────────────────────────────────
        if len(close) >= 15:
            ind.rsi_14 = self._rsi(close, 14)
            if ind.rsi_14 is not None:
                if ind.rsi_14 >= 70:
                    ind.rsi_signal = "overbought"
                elif ind.rsi_14 <= 30:
                    ind.rsi_signal = "oversold"
                else:
                    ind.rsi_signal = "neutral"

        # ── Stochastic ────────────────────────────────────────
        if len(close) >= 14:
            stoch_k, stoch_d = self._stochastic(high, low, close, 14, 3)
            ind.stoch_k = stoch_k
            ind.stoch_d = stoch_d

        # ── Bollinger Bands ───────────────────────────────────
        if len(close) >= 20:
            sma20 = close.rolling(20).mean()
            std20 = close.rolling(20).std()
            upper = sma20 + 2 * std20
            lower = sma20 - 2 * std20
            ind.bb_upper = float(upper.iloc[-1])
            ind.bb_middle = float(sma20.iloc[-1])
            ind.bb_lower = float(lower.iloc[-1])
            band_width = upper - lower
            if float(band_width.iloc[-1]) != 0:
                ind.bb_width = float(band_width.iloc[-1] / sma20.iloc[-1])
                ind.bb_pct_b = float((close.iloc[-1] - lower.iloc[-1]) / band_width.iloc[-1])

        # ── ATR (Average True Range) ──────────────────────────
        if len(close) >= 14:
            ind.atr_14 = self._atr(high, low, close, 14)

        # ── Volatility (20-day) ───────────────────────────────
        if len(close) >= 20:
            log_returns = np.log(close / close.shift(1)).dropna()
            ind.volatility_20d = float(log_returns.rolling(20).std().iloc[-1] * np.sqrt(252))

        # ── OBV ───────────────────────────────────────────────
        if not volume.empty and len(volume) > 0:
            direction = np.sign(close.diff().fillna(0))
            obv_series = (volume * direction).cumsum()
            ind.obv = float(obv_series.iloc[-1])
            if len(volume) >= 20:
                ind.volume_sma_20 = float(volume.rolling(20).mean().iloc[-1])
                if ind.volume_sma_20 and ind.volume_sma_20 > 0:
                    ind.volume_ratio = float(volume.iloc[-1]) / ind.volume_sma_20

        # ── Support / Resistance ──────────────────────────────
        if len(close) >= 20:
            ind.support_level = float(low.rolling(20).min().iloc[-1])
            ind.resistance_level = float(high.rolling(20).max().iloc[-1])

        # ── Trend determination ───────────────────────────────
        ind.trend = self._determine_trend(close, ind)

        return ind

    def _rsi(self, close: pd.Series, period: int) -> Optional[float]:
        try:
            delta = close.diff().dropna()
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)
            avg_gain = gain.ewm(com=period - 1, adjust=False).mean()
            avg_loss = loss.ewm(com=period - 1, adjust=False).mean()
            rs = avg_gain / avg_loss.replace(0, 1e-10)
            rsi = 100 - (100 / (1 + rs))
            return float(rsi.iloc[-1])
        except Exception:
            return None

    def _stochastic(
        self, high: pd.Series, low: pd.Series, close: pd.Series, k_period: int, d_period: int
    ) -> tuple[Optional[float], Optional[float]]:
        try:
            low_min = low.rolling(k_period).min()
            high_max = high.rolling(k_period).max()
            denom = high_max - low_min
            denom = denom.replace(0, 1e-10)
            k = 100 * (close - low_min) / denom
            d = k.rolling(d_period).mean()
            return float(k.iloc[-1]), float(d.iloc[-1])
        except Exception:
            return None, None

    def _atr(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int) -> Optional[float]:
        try:
            tr1 = high - low
            tr2 = (high - close.shift()).abs()
            tr3 = (low - close.shift()).abs()
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = tr.ewm(com=period - 1, adjust=False).mean()
            return float(atr.iloc[-1])
        except Exception:
            return None

    def _determine_trend(self, close: pd.Series, ind: TechnicalIndicators) -> str:
        signals = []
        price = ind.current_price
        if price and ind.sma_20:
            signals.append(1 if price > ind.sma_20 else -1)
        if price and ind.sma_50:
            signals.append(1 if price > ind.sma_50 else -1)
        if ind.macd_histogram is not None:
            signals.append(1 if ind.macd_histogram > 0 else -1)
        if not signals:
            return "sideways"
        avg = sum(signals) / len(signals)
        if avg >= 0.5:
            return "uptrend"
        elif avg <= -0.5:
            return "downtrend"
        return "sideways"
