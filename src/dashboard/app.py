import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st
from dotenv import load_dotenv
load_dotenv()

from src.dashboard.components.overview import render_overview
from src.dashboard.components.portfolio import render_portfolio
from src.dashboard.components.trades import render_trades
from src.dashboard.components.decisions import render_decisions
from src.dashboard.components.reviews import render_reviews
from src.dashboard.components.performance import render_performance

st.set_page_config(
    page_title="Claude AI Investment Simulator",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# CSS
st.markdown("""
<style>
.metric-card {
    background: #1e2329;
    border-radius: 8px;
    padding: 16px;
    border: 1px solid #2d3748;
}
.positive { color: #26a69a; }
.negative { color: #ef5350; }
</style>
""", unsafe_allow_html=True)

def main():
    with st.sidebar:
        st.title("Claude AI Fund")
        st.caption("仮想投資シミュレーター")
        st.divider()

        page = st.selectbox(
            "ページ選択",
            [
                "概要 / Overview",
                "ポートフォリオ",
                "売買履歴",
                "判断履歴",
                "週次反省会",
                "パフォーマンス分析",
            ],
            label_visibility="collapsed",
        )

        st.divider()
        st.caption("データ更新")
        if st.button("最新データ取得", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        st.divider()
        st.caption("自動更新")
        auto_refresh = st.checkbox("5分ごとに自動更新", value=False)
        if auto_refresh:
            import time
            time.sleep(300)
            st.rerun()

    if page == "概要 / Overview":
        render_overview()
    elif page == "ポートフォリオ":
        render_portfolio()
    elif page == "売買履歴":
        render_trades()
    elif page == "判断履歴":
        render_decisions()
    elif page == "週次反省会":
        render_reviews()
    elif page == "パフォーマンス分析":
        render_performance()


if __name__ == "__main__":
    main()
