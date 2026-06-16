# Claude AI 投資ファンド シミュレーター

Claudeによる仮想資産運用シミュレーションシステム。
「Claudeは長期的にインデックス投資を上回る運用成績を出せるのか」を検証するプロジェクトです。

## システム構成図

```
┌─────────────────────────────────────────────────────────┐
│                   Claude AI Fund Simulator               │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────┐    ┌──────────────┐                   │
│  │  Scheduler   │    │  Dashboard   │                   │
│  │ (APScheduler)│    │  (Streamlit) │                   │
│  └──────┬───────┘    └──────┬───────┘                   │
│         │                   │                           │
│  ┌──────▼───────────────────▼───────┐                   │
│  │        Business Logic Layer      │                   │
│  │  ┌──────────┐  ┌──────────────┐ │                   │
│  │  │  Claude  │  │  Portfolio   │ │                   │
│  │  │  Agent   │  │  Manager     │ │                   │
│  │  └──────────┘  └──────────────┘ │                   │
│  │  ┌──────────┐  ┌──────────────┐ │                   │
│  │  │Technical │  │  Trade       │ │                   │
│  │  │Analysis  │  │  Executor    │ │                   │
│  │  └──────────┘  └──────────────┘ │                   │
│  └──────────────────────────────────┘                   │
│                                                          │
│  ┌──────────────────────────────────┐                   │
│  │        Data Layer                │                   │
│  │  ┌────────────┐  ┌────────────┐ │                   │
│  │  │Yahoo Finance│  │ CoinGecko  │ │ (Market Data)    │
│  │  └────────────┘  └────────────┘ │                   │
│  │  ┌────────────────────────────┐ │                   │
│  │  │  Supabase (PostgreSQL)     │ │ (Database)        │
│  │  └────────────────────────────┘ │                   │
│  └──────────────────────────────────┘                   │
└─────────────────────────────────────────────────────────┘
```

## ディレクトリ構成

```
invest_simulation/
├── main.py                    # スケジューラー起動
├── requirements.txt
├── .env.example
├── docker-compose.yml
├── Dockerfile
├── src/
│   ├── config/
│   │   └── settings.py        # Pydantic設定管理
│   ├── db/
│   │   ├── models.py          # SQLAlchemyモデル
│   │   ├── session.py         # DBセッション
│   │   └── repository.py      # データアクセス層
│   ├── market_data/
│   │   ├── base.py            # 抽象インターフェース
│   │   ├── yahoo_finance.py   # Yahoo Finance実装
│   │   ├── coingecko.py       # CoinGecko実装
│   │   └── factory.py         # プロバイダーファクトリー
│   ├── technical/
│   │   └── indicators.py      # テクニカル分析
│   ├── ai/
│   │   ├── base.py            # AI抽象クラス
│   │   ├── claude_agent.py    # Claude実装
│   │   └── prompts.py         # プロンプトテンプレート
│   ├── trading/
│   │   ├── portfolio.py       # ポートフォリオ管理
│   │   └── executor.py        # 売買実行
│   ├── scheduler/
│   │   └── jobs.py            # スケジュールジョブ
│   └── dashboard/
│       ├── app.py             # Streamlitメイン
│       └── components/        # 各ページコンポーネント
├── scripts/
│   ├── init_db.py             # DB初期化
│   ├── setup_agent.py         # エージェント設定
│   ├── morning_analysis.py    # 朝の分析手動実行
│   ├── evening_analysis.py    # 夕の判断手動実行
│   └── weekly_review.py       # 週次反省会手動実行
└── tests/
    └── test_portfolio.py
```

## DB設計

| テーブル | 用途 |
|---------|------|
| `agents` | Claudeエージェント設定 |
| `portfolios` | ポートフォリオ履歴スナップショット |
| `trades` | 売買履歴 |
| `decisions` | 投資判断履歴 (BUY/SELL/HOLD) |
| `morning_analyses` | 朝の分析結果 |
| `market_snapshots` | 市場データスナップショット |
| `weekly_reviews` | 週次反省会 |
| `benchmark_prices` | ベンチマーク価格履歴 |

## セットアップ手順

### 1. 環境変数設定

```bash
cp .env.example .env
# .envを編集してAPIキーとDB URLを設定
```

### 2. 依存パッケージインストール

```bash
pip install -r requirements.txt
```

### 3. Supabase設定

1. [Supabase](https://supabase.com) でプロジェクト作成
2. Settings > Database > Connection string (URI) をコピー
3. `.env`の`DATABASE_URL`に設定

### 4. DBとエージェント初期化

```bash
python scripts/init_db.py
python scripts/setup_agent.py
```

### 5. 動作確認

```bash
python scripts/morning_analysis.py
python scripts/evening_analysis.py
streamlit run src/dashboard/app.py
```

### 6. 本番スケジューラー起動

```bash
python main.py
```

## Docker での実行

```bash
cp .env.example .env
docker compose up -d
```

## 運用スケジュール

| 時刻 (JST) | 処理 |
|-----------|------|
| 毎日 07:00 | 朝の市場分析（売買なし）|
| 毎日 23:00 | 最終判断・仮想売買実行 |
| 毎週日曜 22:00 | 週次反省会 |

## 運用ルール

- **初期資金**: 100,000円
- **1銘柄最大**: 総資産の20%
- **同時保有上限**: 5銘柄
- **取引手数料**: 0.1%（仮想）
- **売買制限**: 同一銘柄24時間以内の再売買禁止

## 対象銘柄

**仮想通貨**: BTC, ETH, SOL, XRP

**米国株**: AAPL, MSFT, GOOGL, AMZN, NVDA, META, TSLA, JPM, V, WMT

**日本株**: 7203.T, 6758.T, 6861.T, 9984.T, 8306.T, 6501.T, 7974.T, 4063.T

## ベンチマーク比較

BTC Buy&Hold / ETH Buy&Hold / S&P500(SPY) / NASDAQ100(QQQ) / 全世界株式(VT)

## 将来拡張

- GPT / Gemini 対応 (`src/ai/`に新クラスを追加)
- ニュース・SNSセンチメント分析
- メール・LINE通知
- 新規データソース追加 (`src/market_data/`に新クラスを追加)
