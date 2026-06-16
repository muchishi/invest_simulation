import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import pandas as pd
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
        latest_portfolio = repo.get_latest_portfolio(agent.id)
        portfolio_history = repo.get_portfolio_history(agent.id, days=90)
        recent_decisions = repo.get_recent_decisions(agent.id, days=7)
        latest_review = repo.get_latest_weekly_review(agent.id)
        morning = repo.get_latest_morning_analysis(agent.id)
        return {
            "agent": {"name": agent.name, "model_id": agent.model_id},
            "latest_portfolio": latest_portfolio,
            "portfolio_history": portfolio_history,
            "recent_decisions": recent_decisions,
            "latest_review": latest_review,
            "morning": morning,
            "initial_capital": settings.INITIAL_CAPITAL_JPY,
        }


def render_overview():
    st.title("概要 / Overview")
    data = _load_data()

    if not data:
        st.warning("エージェントが設定されていません。`python scripts/setup_agent.py` を実行してください。")
        return

    portfolio = data["latest_portfolio"]
    initial = data["initial_capital"]

    # ── KPI Metrics ──────────────────────────────────────────────
    col1, col2, col3, col4, col5 = st.columns(5)

    if portfolio:
        total_val = float(portfolio.total_value_jpy)
        cash = float(portfolio.cash_balance_jpy)
        unrealized = float(portfolio.unrealized_pnl_jpy or 0)
        realized = float(portfolio.realized_pnl_jpy or 0)
        total_return_pct = (total_val - initial) / initial * 100

        col1.metric("総資産", f"¥{total_val:,.0f}", f"{total_return_pct:+.2f}%")
        col2.metric("現金残高", f"¥{cash:,.0f}")
        col3.metric("評価損益", f"¥{unrealized:+,.0f}", delta_color="normal")
        col4.metric("確定損益", f"¥{realized:+,.0f}", delta_color="normal")
        col5.metric("総リターン", f"{total_return_pct:+.2f}%")
    else:
        col1.metric("総資産", f"¥{initial:,.0f}", "0.00%")
        col2.metric("現金残高", f"¥{initial:,.0f}")
        col3.metric("評価損益", "¥0")
        col4.metric("確定損益", "¥0")
        col5.metric("総リターン", "0.00%")

    st.divider()

    # ── 資産推移グラフ ────────────────────────────────────────────
    col_left, col_right = st.columns([3, 1])

    with col_left:
        st.subheader("総資産推移")
        history = data["portfolio_history"]
        if history:
            df = pd.DataFrame(
                [
                    {
                        "date": p.snapshot_at,
                        "total_value": float(p.total_value_jpy),
                        "cash": float(p.cash_balance_jpy),
                    }
                    for p in history
                ]
            )

            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=df["date"],
                    y=df["total_value"],
                    name="総資産",
                    line=dict(color="#26a69a", width=2),
                    fill="tozeroy",
                    fillcolor="rgba(38, 166, 154, 0.1)",
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=df["date"],
                    y=df["cash"],
                    name="現金",
                    line=dict(color="#ffa726", width=1, dash="dot"),
                )
            )
            fig.add_hline(
                y=initial,
                line_dash="dash",
                line_color="gray",
                annotation_text=f"初期資金 ¥{initial:,.0f}",
            )
            fig.update_layout(
                height=350,
                margin=dict(l=0, r=0, t=0, b=0),
                legend=dict(x=0, y=1),
                yaxis_tickformat=",.0f",
                xaxis_title="",
                yaxis_title="JPY",
                plot_bgcolor="#0e1117",
                paper_bgcolor="#0e1117",
                font=dict(color="#fafafa"),
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("ポートフォリオ履歴データがありません")

    with col_right:
        st.subheader("市場センチメント")
        morning = data["morning"]
        if morning:
            sentiment = morning.overall_sentiment or "neutral"
            color_map = {"bullish": "🟢", "neutral": "🟡", "bearish": "🔴"}
            st.metric("朝の分析", f"{color_map.get(sentiment, '⚪')} {sentiment.upper()}")
            st.caption(f"分析時刻: {morning.analyzed_at.strftime('%Y/%m/%d %H:%M')}")
            if morning.analysis_summary:
                st.text_area("サマリー", morning.analysis_summary[:300], height=120, disabled=True)
        else:
            st.info("本日の朝の分析データがありません")

        review = data["latest_review"]
        if review:
            st.subheader("週次戦略")
            strategy = review.next_week_strategy or "neutral"
            color_map = {"bullish": "🟢", "neutral": "🟡", "bearish": "🔴"}
            st.metric("来週の方針", f"{color_map.get(strategy, '⚪')} {strategy.upper()}")
            st.caption(f"更新: {review.review_date}")

    st.divider()

    # ── ベンチマーク比較 ──────────────────────────────────────────
    st.subheader("ベンチマーク比較")
    if portfolio and portfolio.benchmark_values:
        bench_data = []
        claude_return = (float(portfolio.total_value_jpy) - initial) / initial * 100

        bench_data.append({"名称": "Claude AI Fund", "リターン(%)": claude_return})
        for sym, bdata in portfolio.benchmark_values.items():
            if isinstance(bdata, dict):
                bench_data.append({"名称": sym, "リターン(%)": bdata.get("return_pct", 0)})

        if bench_data:
            df_bench = pd.DataFrame(bench_data)
            colors = ["#26a69a" if r >= 0 else "#ef5350" for r in df_bench["リターン(%)"]]
            fig_bench = go.Figure(
                go.Bar(
                    x=df_bench["名称"],
                    y=df_bench["リターン(%)"],
                    marker_color=colors,
                    text=[f"{r:+.2f}%" for r in df_bench["リターン(%)"]],
                    textposition="outside",
                )
            )
            fig_bench.update_layout(
                height=300,
                margin=dict(l=0, r=0, t=0, b=0),
                yaxis_title="リターン (%)",
                plot_bgcolor="#0e1117",
                paper_bgcolor="#0e1117",
                font=dict(color="#fafafa"),
            )
            st.plotly_chart(fig_bench, use_container_width=True)
    else:
        st.info("ベンチマークデータがありません")

    st.divider()

    # ── 直近の判断 ────────────────────────────────────────────────
    st.subheader("直近の判断 (過去7日間)")
    decisions = data["recent_decisions"]
    if decisions:
        rows = []
        for d in decisions[:10]:
            action_emoji = {"BUY": "🟢", "SELL": "🔴", "HOLD": "⚪"}.get(d.action, "⚪")
            rows.append({
                "日時": d.decided_at.strftime("%m/%d %H:%M"),
                "銘柄": d.symbol,
                "判断": f"{action_emoji} {d.action}",
                "信頼度": f"{d.confidence}%" if d.confidence else "-",
                "理由": (d.reasoning or "")[:60] + "..." if d.reasoning and len(d.reasoning) > 60 else (d.reasoning or ""),
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("判断履歴がありません")
