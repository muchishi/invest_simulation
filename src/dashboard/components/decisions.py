import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from src.db.session import get_session
from src.db.repository import Repository
from src.dashboard.symbol_labels import format_symbol, to_jst


@st.cache_data(ttl=300)
def _load_data():
    with get_session() as session:
        repo = Repository(session)
        agent = repo.get_active_agent()
        if not agent:
            return None
        decisions = repo.get_decisions(agent.id, limit=200)
        return {"decisions": decisions}


def render_decisions():
    st.title("判断履歴")
    data = _load_data()
    if not data:
        st.warning("エージェントが未設定です")
        return

    decisions = data["decisions"]
    if not decisions:
        st.info("判断履歴がありません")
        return

    # ── フィルター ────────────────────────────────────────────────
    col1, col2, col3 = st.columns(3)
    with col1:
        raw_symbols = sorted({d.symbol for d in decisions})
        sym_options = {"全銘柄": None} | {format_symbol(s): s for s in raw_symbols}
        sel_label = st.selectbox("銘柄", list(sym_options.keys()))
        sel_sym_raw = sym_options[sel_label]
    with col2:
        actions = ["全て", "BUY", "SELL", "HOLD"]
        sel_action = st.selectbox("判断", actions)
    with col3:
        sessions = ["全て", "morning", "evening"]
        sel_session = st.selectbox("セッション", sessions)

    filtered = decisions
    if sel_sym_raw is not None:
        filtered = [d for d in filtered if d.symbol == sel_sym_raw]
    if sel_action != "全て":
        filtered = [d for d in filtered if d.action == sel_action]
    if sel_session != "全て":
        filtered = [d for d in filtered if d.session_type == sel_session]

    st.caption(f"{len(filtered)} 件")

    # ── 判断分布 ────────────────────────────────────────────────
    action_counts = {"BUY": 0, "SELL": 0, "HOLD": 0}
    for d in filtered:
        if d.action in action_counts:
            action_counts[d.action] += 1

    col_a, col_b, col_c = st.columns(3)
    col_a.metric("BUY", action_counts["BUY"])
    col_b.metric("SELL", action_counts["SELL"])
    col_c.metric("HOLD", action_counts["HOLD"])

    st.divider()

    # ── テーブル表示 ──────────────────────────────────────────────
    rows = []
    for d in filtered[:100]:
        action_emoji = {"BUY": "🟢", "SELL": "🔴", "HOLD": "⚪"}.get(d.action, "⚪")
        risk_emoji = {"low": "🟢", "medium": "🟡", "high": "🔴"}.get(d.risk_level or "", "⚪")
        rows.append({
            "日時": to_jst(d.decided_at).strftime("%m/%d %H:%M"),
            "銘柄": format_symbol(d.symbol),
            "判断": f"{action_emoji} {d.action}",
            "信頼度": f"{d.confidence}%" if d.confidence else "-",
            "期待リターン": f"{d.expected_return_pct:+.1f}%" if d.expected_return_pct else "-",
            "リスク": f"{risk_emoji} {d.risk_level}" if d.risk_level else "-",
            "セッション": d.session_type,
            "理由": (d.reasoning or "")[:80] + "..." if d.reasoning and len(d.reasoning) > 80 else (d.reasoning or ""),
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # ── 判断詳細 ──────────────────────────────────────────────────
    st.divider()
    st.subheader("判断詳細")
    if filtered:
        selected_idx = st.selectbox(
            "詳細を見る",
            range(min(20, len(filtered))),
            format_func=lambda i: f"{to_jst(filtered[i].decided_at).strftime('%m/%d %H:%M')} {filtered[i].symbol} {filtered[i].action}",
        )
        d = filtered[selected_idx]

        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**銘柄:** {format_symbol(d.symbol)}")
            st.markdown(f"**判断:** {d.action}")
            st.markdown(f"**信頼度:** {d.confidence}%")
            st.markdown(f"**期待リターン:** {d.expected_return_pct:+.1f}%" if d.expected_return_pct else "**期待リターン:** -")
            st.markdown(f"**リスク:** {d.risk_level}")
            st.markdown(f"**投資期間:** {d.investment_period or '-'}")
        with col2:
            st.markdown(f"**モデル:** {d.model_id}")
            st.markdown(f"**入力トークン:** {d.input_tokens:,}" if d.input_tokens else "**入力トークン:** -")
            st.markdown(f"**出力トークン:** {d.output_tokens:,}" if d.output_tokens else "**出力トークン:** -")
            st.markdown(f"**APIコスト:** ${d.api_cost_usd:.4f}" if d.api_cost_usd else "**APIコスト:** -")

        if d.key_factors:
            st.markdown("**判断要因:**")
            for factor in d.key_factors:
                st.markdown(f"- {factor}")

        if d.reasoning:
            st.markdown("**判断理由:**")
            st.text_area("", d.reasoning, height=150, disabled=True, label_visibility="collapsed")

        if d.ai_response:
            with st.expander("Claude 応答全文"):
                st.text_area("", d.ai_response, height=300, disabled=True, label_visibility="collapsed")
