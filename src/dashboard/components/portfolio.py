import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from src.db.session import get_session
from src.db.repository import Repository
from src.dashboard.symbol_labels import format_symbol, short_name


@st.cache_data(ttl=300)
def _load_data():
    with get_session() as session:
        repo = Repository(session)
        agent = repo.get_active_agent()
        if not agent:
            return None
        return {
            "latest_portfolio": repo.get_latest_portfolio(agent.id),
            "portfolio_history": repo.get_portfolio_history(agent.id, days=30),
        }


def render_portfolio():
    st.title("ポートフォリオ")
    data = _load_data()
    if not data:
        st.warning("エージェントが未設定です")
        return

    portfolio = data["latest_portfolio"]
    if not portfolio:
        st.info("ポートフォリオデータがありません")
        return

    col1, col2, col3 = st.columns(3)
    col1.metric("総資産", f"¥{float(portfolio.total_value_jpy):,.0f}")
    col2.metric("現金残高", f"¥{float(portfolio.cash_balance_jpy):,.0f}")
    holdings_value = float(portfolio.total_value_jpy) - float(portfolio.cash_balance_jpy)
    col3.metric("保有資産評価額", f"¥{holdings_value:,.0f}")

    st.divider()

    holdings = portfolio.holdings or []
    if not holdings:
        st.info("保有銘柄なし (全額現金)")
        _render_allocation_pie(portfolio, holdings)
        return

    col_left, col_right = st.columns([3, 2])

    with col_left:
        st.subheader("保有銘柄一覧")
        rows = []
        for h in holdings:
            pnl = float(h.get("unrealized_pnl_jpy", 0))
            pnl_pct = float(h.get("unrealized_pnl_pct", 0))
            rows.append({
                "銘柄": format_symbol(h["symbol"]),
                "数量": h["quantity"],
                "平均取得単価(円)": f"{float(h.get('avg_cost_jpy', 0)):,.2f}",
                "現在価格(円)": f"{float(h.get('current_price_jpy', 0)):,.2f}",
                "評価額(円)": f"{float(h.get('current_value_jpy', 0)):,.0f}",
                "評価損益(円)": f"{pnl:+,.0f}",
                "損益率": f"{pnl_pct:+.2f}%",
                "比率": f"{float(h.get('portfolio_pct', 0)):.1f}%",
            })

        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)

    with col_right:
        st.subheader("アセット配分")
        _render_allocation_pie(portfolio, holdings)

    st.divider()

    # ── 個別銘柄損益グラフ ────────────────────────────────────────
    if holdings:
        st.subheader("評価損益")
        symbols = [short_name(h["symbol"]) for h in holdings]
        pnls = [float(h.get("unrealized_pnl_jpy", 0)) for h in holdings]
        colors = ["#26a69a" if p >= 0 else "#ef5350" for p in pnls]

        fig = go.Figure(
            go.Bar(
                x=symbols,
                y=pnls,
                marker_color=colors,
                text=[f"¥{p:+,.0f}" for p in pnls],
                textposition="outside",
            )
        )
        fig.update_layout(
            height=300,
            yaxis_title="評価損益 (円)",
            plot_bgcolor="#0e1117",
            paper_bgcolor="#0e1117",
            font=dict(color="#fafafa"),
            margin=dict(l=0, r=0, t=20, b=0),
        )
        st.plotly_chart(fig, use_container_width=True)


def _render_allocation_pie(portfolio, holdings: list):
    total_val = float(portfolio.total_value_jpy)
    cash_val = float(portfolio.cash_balance_jpy)

    labels = ["現金"] + [short_name(h["symbol"]) for h in holdings]
    values = [cash_val] + [float(h.get("current_value_jpy", 0)) for h in holdings]
    colors = ["#546e7a", "#26a69a", "#42a5f5", "#ab47bc", "#ef5350", "#ffa726"]

    fig = go.Figure(
        go.Pie(
            labels=labels,
            values=values,
            hole=0.4,
            marker_colors=colors[: len(labels)],
            textinfo="label+percent",
        )
    )
    fig.update_layout(
        height=300,
        showlegend=True,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="#0e1117",
        font=dict(color="#fafafa"),
    )
    st.plotly_chart(fig, use_container_width=True)
