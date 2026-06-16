import streamlit as st
import pandas as pd
from src.db.session import get_session
from src.db.repository import Repository


@st.cache_data(ttl=600)
def _load_data():
    with get_session() as session:
        repo = Repository(session)
        agent = repo.get_active_agent()
        if not agent:
            return None
        reviews = repo.get_weekly_reviews(agent.id, limit=12)
        return {"reviews": reviews}


def render_reviews():
    st.title("Claude 週次反省会")
    data = _load_data()
    if not data:
        st.warning("エージェントが未設定です")
        return

    reviews = data["reviews"]
    if not reviews:
        st.info("週次反省会データがありません")
        return

    # 週の選択
    review_options = [f"{r.week_start} 〜 {r.week_end}" for r in reviews]
    selected_idx = st.selectbox("レビュー週を選択", range(len(reviews)), format_func=lambda i: review_options[i])
    review = reviews[selected_idx]

    st.divider()

    # ── パフォーマンスサマリー ─────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("対象期間", f"{review.week_start} 〜 {review.week_end}")
    col2.metric("総取引数", review.total_trades or 0)
    pnl = float(review.total_pnl_jpy or 0)
    col3.metric("週間損益", f"¥{pnl:+,.0f}")
    strategy_emoji = {"bullish": "🟢", "neutral": "🟡", "bearish": "🔴"}.get(review.next_week_strategy or "", "⚪")
    col4.metric("来週の方針", f"{strategy_emoji} {(review.next_week_strategy or 'neutral').upper()}")

    st.divider()

    # ── パフォーマンスサマリーテキスト ────────────────────────────
    if review.performance_summary:
        st.subheader("今週の総括")
        st.markdown(review.performance_summary)

    col_left, col_right = st.columns(2)

    with col_left:
        # ── 良かった判断 ──────────────────────────────────────────
        st.subheader("良かった判断 ✅")
        good = review.good_decisions or []
        if good:
            for g in good:
                with st.expander(f"{g.get('symbol', '-')} {g.get('action', '-')} ({g.get('date', '-')})"):
                    st.markdown(f"**成功した理由:** {g.get('success_reason', '-')}")
                    st.markdown(f"**学んだこと:** {g.get('lesson', '-')}")
        else:
            st.info("特記なし")

    with col_right:
        # ── 悪かった判断 ──────────────────────────────────────────
        st.subheader("悪かった判断 ❌")
        bad = review.bad_decisions or []
        if bad:
            for b in bad:
                with st.expander(f"{b.get('symbol', '-')} {b.get('action', '-')} ({b.get('date', '-')})"):
                    st.markdown(f"**失敗した理由:** {b.get('failure_reason', '-')}")
                    st.markdown(f"**本来すべきだった行動:** {b.get('what_should_have_done', '-')}")
                    st.markdown(f"**学んだこと:** {b.get('lesson', '-')}")
        else:
            st.info("特記なし")

    st.divider()

    # ── キーラーニング ────────────────────────────────────────────
    st.subheader("重要な学習ポイント")
    learnings = review.key_learnings or []
    if learnings:
        for i, l in enumerate(learnings, 1):
            st.markdown(f"{i}. {l}")
    else:
        st.info("データなし")

    st.divider()

    # ── 改善計画・来週の方針 ──────────────────────────────────────
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("改善計画")
        if review.improvement_plan:
            st.markdown(review.improvement_plan)
        else:
            st.info("データなし")
    with col2:
        st.subheader("来週の方針")
        if review.next_week_rationale:
            st.markdown(f"**{strategy_emoji} {(review.next_week_strategy or '').upper()}**")
            st.markdown(review.next_week_rationale)
        else:
            st.info("データなし")

    # ── APIコスト情報 ─────────────────────────────────────────────
    with st.expander("API使用情報"):
        st.markdown(f"**モデル:** {review.model_id}")
        st.markdown(f"**入力トークン:** {review.input_tokens:,}" if review.input_tokens else "**入力トークン:** -")
        st.markdown(f"**出力トークン:** {review.output_tokens:,}" if review.output_tokens else "**出力トークン:** -")
        st.markdown(f"**APIコスト:** ${review.api_cost_usd:.4f}" if review.api_cost_usd else "**APIコスト:** -")

    if review.ai_response:
        with st.expander("Claude 応答全文"):
            st.text_area("", review.ai_response, height=400, disabled=True, label_visibility="collapsed")
