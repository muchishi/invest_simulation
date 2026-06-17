import pytz
from datetime import datetime

_JST = pytz.timezone("Asia/Tokyo")
_UTC = pytz.utc


def to_jst(dt: datetime | None) -> datetime | None:
    """naive (UTC想定) または aware な datetime を JST に変換して返す。"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = _UTC.localize(dt)
    return dt.astimezone(_JST)


_LABELS: dict[str, tuple[str, str]] = {
    # 暗号資産
    "BTC":     ("暗号資産", "Bitcoin"),
    "ETH":     ("暗号資産", "Ethereum"),
    "SOL":     ("暗号資産", "Solana"),
    "XRP":     ("暗号資産", "XRP"),
    # 米国株
    "AAPL":    ("米国株", "Apple"),
    "MSFT":    ("米国株", "Microsoft"),
    "GOOGL":   ("米国株", "Alphabet"),
    "AMZN":    ("米国株", "Amazon"),
    "NVDA":    ("米国株", "NVIDIA"),
    "META":    ("米国株", "Meta"),
    "TSLA":    ("米国株", "Tesla"),
    "JPM":     ("米国株", "JPMorgan Chase"),
    "V":       ("米国株", "Visa"),
    "WMT":     ("米国株", "Walmart"),
    # 日本株
    "7203.T":  ("日本株", "トヨタ自動車"),
    "6758.T":  ("日本株", "ソニーグループ"),
    "6861.T":  ("日本株", "キーエンス"),
    "9984.T":  ("日本株", "ソフトバンクG"),
    "8306.T":  ("日本株", "三菱UFJ FG"),
    "6501.T":  ("日本株", "日立製作所"),
    "7974.T":  ("日本株", "任天堂"),
    "4063.T":  ("日本株", "信越化学工業"),
    # ベンチマーク
    "BTC-USD": ("ベンチマーク", "Bitcoin USD"),
    "ETH-USD": ("ベンチマーク", "Ethereum USD"),
    "SPY":     ("ベンチマーク", "S&P500 ETF"),
    "QQQ":     ("ベンチマーク", "NASDAQ100 ETF"),
    "VT":      ("ベンチマーク", "全世界株 ETF"),
}


def format_symbol(symbol: str) -> str:
    """テーブル・ドロップダウン用: [カテゴリ] SYMBOL (名称)"""
    entry = _LABELS.get(symbol)
    if entry is None:
        return symbol
    category, name = entry
    return f"[{category}] {symbol} ({name})"


def short_name(symbol: str) -> str:
    """グラフ軸・パイチャート用: 名称のみ (未登録ならシンボルそのまま)"""
    entry = _LABELS.get(symbol)
    return entry[1] if entry else symbol
