#!/usr/bin/env python3
"""エージェントの初期設定"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from src.config import get_settings
from src.db.session import get_session
from src.db.repository import Repository
from src.db.models import Base
from src.db.session import _get_engine


def setup_agent():
    settings = get_settings()

    print("DB テーブル確認・作成中...")
    Base.metadata.create_all(bind=_get_engine())

    with get_session() as session:
        repo = Repository(session)

        existing = repo.get_active_agent()
        if existing:
            print(f"エージェントは既に設定されています: {existing.name} (model={existing.model_id})")
            return

        agent = repo.create_agent(
            name=settings.AGENT_NAME,
            model_id=settings.CLAUDE_MODEL,
            description=settings.AGENT_DESCRIPTION,
            is_active=True,
            config={
                "initial_capital_jpy": settings.INITIAL_CAPITAL_JPY,
                "max_position_pct": settings.MAX_POSITION_PCT,
                "max_positions": settings.MAX_POSITIONS,
                "transaction_fee_pct": settings.TRANSACTION_FEE_PCT,
                "crypto_symbols": settings.CRYPTO_SYMBOLS,
                "us_stock_symbols": settings.US_STOCK_SYMBOLS,
                "jp_stock_symbols": settings.JP_STOCK_SYMBOLS,
            }
        )
        print(f"エージェント作成完了: {agent.name} (id={agent.id})")

        # 初期ポートフォリオスナップショット
        from datetime import datetime
        repo.save_portfolio(
            agent_id=agent.id,
            snapshot_at=datetime.utcnow(),
            cash_balance_jpy=settings.INITIAL_CAPITAL_JPY,
            total_value_jpy=settings.INITIAL_CAPITAL_JPY,
            total_cost_jpy=0.0,
            unrealized_pnl_jpy=0.0,
            realized_pnl_jpy=0.0,
            holdings=[],
        )
        print(f"初期ポートフォリオ作成完了: ¥{settings.INITIAL_CAPITAL_JPY:,.0f}")

        # ベンチマーク初期価格を取得・保存
        print("ベンチマーク初期価格を取得中...")
        try:
            from src.market_data.factory import MarketDataFactory
            factory = MarketDataFactory()
            bench_prices = factory.get_benchmark_prices()
            for sym, price in bench_prices.items():
                repo.save_benchmark_price(
                    symbol=sym,
                    recorded_at=datetime.utcnow(),
                    price_jpy=price,
                    initial_price_jpy=price,
                    return_pct=0.0,
                )
                print(f"  {sym}: ¥{price:,.2f}")
        except Exception as e:
            print(f"ベンチマーク取得エラー (後で自動取得されます): {e}")

    print("\nセットアップ完了！")
    print("次のコマンドで実行できます:")
    print("  朝の分析: python scripts/morning_analysis.py")
    print("  夕の判断: python scripts/evening_analysis.py")
    print("  週次反省会: python scripts/weekly_review.py")
    print("  ダッシュボード: streamlit run src/dashboard/app.py")
    print("  スケジューラー: python main.py")


if __name__ == "__main__":
    setup_agent()
