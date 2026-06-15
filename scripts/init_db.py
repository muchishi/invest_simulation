#!/usr/bin/env python3
"""データベースの初期化 - テーブル作成"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from src.db.models import Base
from src.db.session import _get_engine


def init_db():
    print("データベース初期化中...")
    engine = _get_engine()
    Base.metadata.create_all(bind=engine)
    print("全テーブル作成完了")

    # テーブル一覧を表示
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"\n作成されたテーブル ({len(tables)}件):")
    for table in sorted(tables):
        cols = inspector.get_columns(table)
        print(f"  - {table} ({len(cols)} columns)")


if __name__ == "__main__":
    init_db()
