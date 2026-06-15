import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from src.db.session import get_session
from src.db.repository import Repository
from src.config import get_settings


@st.cache_data(ttl=300)
def _load_data():
    settings = get_settings()
    with get_session() as session:
        repo = Repository(session)
        agent = repo.get_active_agent()
        if not agent:
            return None
        portfolio_history = repo.get_portfolio_history(agent.id, days=365)
        trades = repo.get_trades(agent.id, limit=500)
        decisions = repo.get_decisions(agent.id, limit=500)
        evening_decisions = repo.get_evening_decisions(agent.id, limit=200)
        benchmark_btc = repo.get_benchmark_history("BTC-USD", days=365)
        benchmark_eth = repo.get_benchmark_history("ETH-USD", days=365)
        benchmark_spy = repo.get_benchmark_history("SPY", days=365)
        benchmark_qqq = repo.get_benchmark_history("QQQ", days=365)
        benchmark_vt = repo.get_benchmark_history("VT", days=365)
        return {
            "portfolio_history": portfolio_history,
            "trades": trades,
            "decisions": decisions,
            "evening_decisions": evening_decisions,
            "benchmarks": {
                "BTC Buy&Hold": benchmark_btc,
                "ETH Buy&Hold": benchmark_eth,
                "S&P500 (SPY)": benchmark_spy,
                "NASDAQ100 (QQQ)": benchmark_qqq,
                "全世界株式 (VT)": benchmark_vt,
            },
            "initial_capital": settings.INITIAL_CAPITAL_JPY,
        }


def render_performance():
    st.title("パフォーマンス分析")
    data = _load_data()
    if not data:
        st.warning("エージェントが未設定です")
        return

    history = data["portfolio_history"]
    initial = data["initial_capital"]

    if not history:
        st.info("パフォーマンスデータがありません")
        return

    # ── ポートフォリオシリーズ作成 ────────────────────────────────
    df = pd.DataFrame([
        {"date": p.snapshot_at, "value": float(p.total_value_jpy), "cash": float(p.cash_balance_jpy)}
        for p in history
    ])
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").drop_duplicates("date", keep="last").set_index("date")
    df["return_pct"] = (df["value"] / initial - 1) * 100
    df["daily_return"] = df["value"].pct_change()

    # ── KPI 計算 ─────────────────────────────────────────────────
    total_return = df["return_pct"].iloc[-1]
    days_elapsed = (df.index[-1] - df.index[0]).days
    annualized_return = ((1 + total_return / 100) ** (365 / max(days_elapsed, 1)) - 1) * 100 if days_elapsed > 0 else 0

    daily_rets = df["daily_return"].dropna()
    sharpe = float(daily_rets.mean() / daily_rets.std() * np.sqrt(252)) if len(daily_rets) > 1 and daily_rets.std() > 0 else 0

    rolling_max = df["value"].cummax()
    drawdown = (df["value"] - rolling_max) / rolling_max * 100
    max_drawdown = float(drawdown.min())

    # ── KPI 表示 ─────────────────────────────────────────────────
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("総リターン", f"{total_return:+.2f}%")
    col2.metric("年率リターン", f"{annualized_return:+.2f}%")
    col3.metric("シャープレシオ", f"{sharpe:.2f}")
    col4.metric("最大ドローダウン", f"{max_drawdown:.2f}%")
    col5.metric("経過日数", f"{days_elapsed}日")

    trades = data["trades"]
    if trades:
        buy_count = sum(1 for t in trades if t.action == "BUY")
        sell_count = sum(1 for t in trades if t.action == "SELL")
        col1, col2, col3 = st.columns(3)
        col1.metric("総取引回数", len(trades))
        col2.metric("BUY", buy_count)
        col3.metric("SELL", sell_count)

    st.divider()

    # ── リターン vs ベンチマーク ───────────────────────────────────
    st.subheader("リターン推移 vs ベンチマーク")
    fig = go.Figure()

    # Claude fund
    fig.add_trace(go.Scatter(
        x=df.index, y=df["return_pct"],
        name="Claude AI Fund",
        line=dict(color="#26a69a", width=2.5),
    ))

    # Benchmarks
    bench_colors = {"BTC Buy&Hold": "#f7931a", "ETH Buy&Hold": "#627eea",
                    "S&P500 (SPY)": "#42a5f5", "NASDAQ100 (QQQ)": "#ab47bc", "全世界株式 (VT)": "#ffa726"}
    for name, bench_history in data["benchmarks"].items():
        if bench_history:
            bench_df = pd.DataFrame([
                {"date": b.recorded_at, "return_pct": float(b.return_pct or 0)}
                for b in bench_history
            ]).set_index("date").sort_index()
            if not bench_df.empty:
                fig.add_trace(go.Scatter(
                    x=bench_df.index, y=bench_df["return_pct"],
                    name=name,
                    line=dict(color=bench_colors.get(name, "#gray"), width=1.5, dash="dot"),
                ))

    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
    fig.update_layout(
        height=400,
        yaxis_title="リターン (%)",
        xaxis_title="",
        plot_bgcolor="#0e1117",
        paper_bgcolor="#0e1117",
        font=dict(color="#fafafa"),
        legend=dict(x=0, y=1, bgcolor="rgba(0,0,0,0)"),
        margin=dict(l=0, r=0, t=20, b=0),
    )
    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ── ドローダウン ──────────────────────────────────────────────
    st.subheader("ドローダウン")
    fig_dd = go.Figure()
    fig_dd.add_trace(go.Scatter(
        x=drawdown.index, y=drawdown,
        fill="tozeroy",
        line=dict(color="#ef5350"),
        fillcolor="rgba(239, 83, 80, 0.3)",
        name="ドローダウン",
    ))
    fig_dd.update_layout(
        height=250,
        yaxis_title="ドローダウン (%)",
        plot_bgcolor="#0e1117",
        paper_bgcolor="#0e1117",
        font=dict(color="#fafafa"),
        margin=dict(l=0, r=0, t=0, b=0),
    )
    st.plotly_chart(fig_dd, use_container_width=True)

    st.divider()

    # ── 月次リターン ──────────────────────────────────────────────
    st.subheader("月次リターン")
    monthly = df["value"].resample("ME").last()
    monthly_returns = monthly.pct_change().dropna() * 100

    if not monthly_returns.empty:
        colors = ["#26a69a" if r >= 0 else "#ef5350" for r in monthly_returns]
        fig_monthly = go.Figure(go.Bar(
            x=[d.strftime("%Y-%m") for d in monthly_returns.index],
            y=monthly_returns.values,
            marker_color=colors,
            text=[f"{r:+.2f}%" for r in monthly_returns.values],
            textposition="outside",
        ))
        fig_monthly.update_layout(
            height=300,
            yaxis_title="月次リターン (%)",
            plot_bgcolor="#0e1117",
            paper_bgcolor="#0e1117",
            font=dict(color="#fafafa"),
            margin=dict(l=0, r=0, t=0, b=0),
        )
        st.plotly_chart(fig_monthly, use_container_width=True)

    # ── APIコスト集計 ─────────────────────────────────────────────
    st.divider()
    st.subheader("API コスト集計")
    decisions = data["decisions"]
    total_cost = sum(float(d.api_cost_usd or 0) for d in decisions)
    total_input = sum(d.input_tokens or 0 for d in decisions)
    total_output = sum(d.output_tokens or 0 for d in decisions)

    col1, col2, col3 = st.columns(3)
    col1.metric("累計APIコスト", f"${total_cost:.4f}")
    col2.metric("累計入力トークン", f"{total_input:,}")
    col3.metric("累計出力トークン", f"{total_output:,}")
