import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from src.db.session import get_session
from src.db.repository import Repository


@st.cache_data(ttl=300)
def _load_data():
    with get_session() as session:
        repo = Repository(session)
        agent = repo.get_active_agent()
        if not agent:
            return None
        trades = repo.get_trades(agent.id, limit=200)
        return {"trades": trades}


def render_trades():
    st.title("売買履歴")
    data = _load_data()
    if not data:
        st.warning("エージェントが未設定です")
        return

    trades = data["trades"]
    if not trades:
        st.info("売買履歴がありません")
        return

    rows = []
    for t in trades:
        action_emoji = "🟢 BUY" if t.action == "BUY" else "🔴 SELL"
        rows.append({
            "日時": t.executed_at.strftime("%Y/%m/%d %H:%M"),
            "銘柄": t.symbol,
            "売買": action_emoji,
            "数量": t.quantity,
            "価格(円)": f"¥{float(t.price_jpy):,.2f}",
            "売買代金(円)": f"¥{float(t.total_amount_jpy):,.0f}",
            "手数料(円)": f"¥{float(t.fee_jpy):,.2f}",
            "種別": t.asset_type,
        })

    df = pd.DataFrame(rows)

    # フィルター
    col1, col2 = st.columns(2)
    with col1:
        symbols = ["全銘柄"] + sorted(list({t.symbol for t in trades}))
        selected_sym = st.selectbox("銘柄フィルター", symbols)
    with col2:
        actions = ["全て", "BUY", "SELL"]
        selected_action = st.selectbox("売買フィルター", actions)

    if selected_sym != "全銘柄":
        df = df[df["銘柄"] == selected_sym]
    if selected_action != "全て":
        df = df[df["売買"].str.contains(selected_action)]

    st.dataframe(df, use_container_width=True, hide_index=True)

    st.divider()

    # ── 売買頻度グラフ ────────────────────────────────────────────
    st.subheader("銘柄別売買回数")
    from collections import Counter
    symbol_counts = Counter(t.symbol for t in trades)
    fig = go.Figure(
        go.Bar(
            x=list(symbol_counts.keys()),
            y=list(symbol_counts.values()),
            marker_color="#42a5f5",
        )
    )
    fig.update_layout(
        height=300,
        yaxis_title="取引回数",
        plot_bgcolor="#0e1117",
        paper_bgcolor="#0e1117",
        font=dict(color="#fafafa"),
        margin=dict(l=0, r=0, t=0, b=0),
    )
    st.plotly_chart(fig, use_container_width=True)
