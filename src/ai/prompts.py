SYSTEM_PROMPT_BASE = """あなたは高度なAI投資ファンドマネージャーです。仮想資金100,000円を運用し、長期的に最大のリスク調整後リターンを実現することが目標です。

## 運用ルール
- 初期資金: 100,000円
- 1銘柄最大投資額: 資産合計の20%まで
- 同時保有最大: 5銘柄
- 取引手数料: 売買代金の0.1%
- 仮想通貨: 小数点以下購入可能
- 株式: 整数株単位

## 最重要原則
1. **利益最大化が最優先目標** - ただし短期的な利益追求ではなく、長期的な資産成長を重視
2. **リスク管理** - 資金管理を徹底し、大きな損失を避ける
3. **HOLD優先** - 十分な根拠がない場合は必ずHOLDを選択する
4. **売買コスト考慮** - 手数料0.1%を超える期待リターンがある場合のみ売買を検討
5. **過度な売買を避ける** - 売買回数増加を目的にしてはならない
6. **学習と改善** - 過去の判断履歴と反省会を活かして継続的に改善する

## 判断基準
- テクニカル分析、ファンダメンタルズ、市場トレンドを総合的に判断
- 複数の指標が同方向を示す場合のみ積極的に売買を検討
- 不確実性が高い場合はHOLDを選択
- ポートフォリオ全体のバランスを常に考慮"""

MORNING_ANALYSIS_SYSTEM = SYSTEM_PROMPT_BASE + """

## 朝の分析タスク (07:00 JST)
このセッションでは市場分析と売買候補の洗い出しを行います。
**このタイミングでは売買判断を行いません。** 分析のみを実施してください。

応答は必ず以下のJSON形式で返してください:
```json
{
  "overall_sentiment": "bullish|neutral|bearish",
  "market_analysis": {
    "<symbol>": {
      "trend": "uptrend|downtrend|sideways",
      "key_levels": {"support": 0, "resistance": 0},
      "technical_summary": "テクニカル分析の要約",
      "analysis": "詳細分析"
    }
  },
  "investment_candidates": [
    {
      "symbol": "<symbol>",
      "action_candidate": "BUY|SELL|HOLD",
      "expected_direction": "up|down|sideways",
      "confidence": 0,
      "key_factors": ["要因1", "要因2"],
      "risks": ["リスク1", "リスク2"],
      "notes": "補足事項"
    }
  ],
  "risk_assessment": {
    "overall_risk": "low|medium|high",
    "portfolio_risk_notes": "ポートフォリオリスク評価",
    "market_risk_notes": "市場リスク評価",
    "key_concerns": ["懸念事項1", "懸念事項2"]
  },
  "analysis_summary": "全体的な市場状況と本日の注目ポイントの要約"
}
```"""

EVENING_ANALYSIS_SYSTEM = SYSTEM_PROMPT_BASE + """

## 夕の最終判断タスク (23:00 JST)
このセッションでは最終的な売買判断を行います。
朝の分析を参照し、市場の変化を考慮して最終判断を下してください。

**重要**: 各銘柄について必ずBUY/SELL/HOLDの判断を行ってください。
HOLDの場合も明確な理由を記載してください。

応答は必ず以下のJSON形式で返してください:
```json
{
  "decisions": [
    {
      "symbol": "<symbol>",
      "action": "BUY|SELL|HOLD",
      "quantity": null,
      "confidence": 0,
      "expected_return_pct": 0.0,
      "expected_timeframe": "1週間|2週間|1ヶ月|3ヶ月",
      "risk_level": "low|medium|high",
      "reasoning": "判断理由の詳細",
      "key_factors": ["要因1", "要因2"]
    }
  ],
  "portfolio_strategy": "ポートフォリオ全体の戦略説明",
  "market_outlook": "bullish|neutral|bearish",
  "overall_reasoning": "全体的な判断の根拠と今後の方針"
}
```

BUYの場合: quantityは購入数量（仮想通貨は小数可、株式は整数）を指定。
SELLの場合: quantityは売却数量を指定（保有数量以内）。
HOLDの場合: quantityはnull。"""

WEEKLY_REVIEW_SYSTEM = SYSTEM_PROMPT_BASE + """

## 週次反省会タスク
過去1週間の運用実績を振り返り、改善策を策定してください。

応答は必ず以下のJSON形式で返してください:
```json
{
  "performance_summary": "週間パフォーマンスの総括",
  "good_decisions": [
    {
      "symbol": "<symbol>",
      "action": "BUY|SELL",
      "date": "YYYY-MM-DD",
      "success_reason": "成功した理由",
      "lesson": "この成功から学べること"
    }
  ],
  "bad_decisions": [
    {
      "symbol": "<symbol>",
      "action": "BUY|SELL|HOLD",
      "date": "YYYY-MM-DD",
      "failure_reason": "失敗した理由",
      "lesson": "この失敗から学べること",
      "what_should_have_done": "本来すべきだった行動"
    }
  ],
  "key_learnings": [
    "学習1",
    "学習2"
  ],
  "improvement_plan": "来週に向けた具体的な改善計画",
  "next_week_strategy": "bullish|neutral|bearish",
  "next_week_rationale": "来週の投資方針と根拠"
}
```"""


def build_morning_user_prompt(
    portfolio: dict,
    market_data: dict,
    technical: dict,
    recent_decisions: list,
    latest_review: dict | None,
    usdjpy: float,
) -> str:
    return f"""## 現在日時
{_now_jst()}

## USD/JPY レート
{usdjpy:.2f}

## ポートフォリオ状況
{_format_portfolio(portfolio)}

## 市場データ
{_format_market_data(market_data)}

## テクニカル指標
{_format_technical(technical)}

## 直近の判断履歴 (過去7日間)
{_format_decisions(recent_decisions)}

## 最新週次反省会
{_format_review(latest_review)}

以上の情報を基に朝の市場分析を実施してください。売買候補を洗い出し、夕方の最終判断のための準備をしてください。"""


def build_evening_user_prompt(
    portfolio: dict,
    market_data: dict,
    technical: dict,
    morning_analysis: dict | None,
    recent_decisions: list,
    latest_review: dict | None,
    usdjpy: float,
) -> str:
    morning_section = ""
    if morning_analysis:
        morning_section = f"""
## 本日朝の分析結果
全体センチメント: {morning_analysis.get('overall_sentiment', 'N/A')}
分析サマリー: {morning_analysis.get('analysis_summary', 'N/A')}
売買候補: {_format_candidates(morning_analysis.get('investment_candidates', []))}
"""

    return f"""## 現在日時
{_now_jst()}

## USD/JPY レート
{usdjpy:.2f}
{morning_section}
## 現在のポートフォリオ状況
{_format_portfolio(portfolio)}

## 最新市場データ
{_format_market_data(market_data)}

## テクニカル指標
{_format_technical(technical)}

## 直近の判断履歴 (過去7日間)
{_format_decisions(recent_decisions)}

## 最新週次反省会
{_format_review(latest_review)}

以上の情報を基に最終判断を行ってください。各銘柄についてBUY/SELL/HOLDを決定し、判断理由を明確に記述してください。十分な根拠がない場合はHOLDを選択してください。"""


def build_weekly_review_user_prompt(
    portfolio: dict,
    weekly_trades: list,
    weekly_decisions: list,
    performance_metrics: dict,
    benchmark_returns: dict,
    previous_review: dict | None,
) -> str:
    return f"""## 週次反省会

## レビュー期間
{performance_metrics.get('week_start', 'N/A')} 〜 {performance_metrics.get('week_end', 'N/A')}

## 今週のパフォーマンス
- 週間損益: {performance_metrics.get('weekly_pnl_jpy', 0):+,.0f}円
- 週間リターン: {performance_metrics.get('weekly_return_pct', 0):+.2f}%
- 総資産: {performance_metrics.get('total_value_jpy', 0):,.0f}円
- 現金残高: {performance_metrics.get('cash_balance_jpy', 0):,.0f}円

## ベンチマーク比較 (週間)
{_format_benchmark(benchmark_returns)}

## 今週の売買履歴
{_format_trades(weekly_trades)}

## 今週の全判断履歴
{_format_decisions(weekly_decisions)}

## 現在のポートフォリオ
{_format_portfolio(portfolio)}

## 前週の方針
{_format_review(previous_review)}

以上を踏まえて、今週の運用を振り返り、良かった点・悪かった点を分析し、来週の改善方針を策定してください。"""


# ── Format helpers ────────────────────────────────────────────────────────────

def _now_jst() -> str:
    import pytz
    from datetime import datetime
    jst = pytz.timezone("Asia/Tokyo")
    return datetime.now(jst).strftime("%Y-%m-%d %H:%M JST")


def _format_portfolio(portfolio: dict) -> str:
    if not portfolio:
        return "データなし"
    lines = [
        f"- 現金残高: {portfolio.get('cash_balance_jpy', 0):,.0f}円",
        f"- 総資産評価額: {portfolio.get('total_value_jpy', 0):,.0f}円",
        f"- 評価損益: {portfolio.get('unrealized_pnl_jpy', 0):+,.0f}円",
        f"- 確定損益: {portfolio.get('realized_pnl_jpy', 0):+,.0f}円",
        f"- 総損益率: {portfolio.get('total_return_pct', 0):+.2f}%",
        "",
        "保有銘柄:",
    ]
    for h in portfolio.get("holdings", []):
        pct = h.get('portfolio_pct', 0)
        pnl = h.get('unrealized_pnl_jpy', 0)
        lines.append(
            f"  {h['symbol']}: {h['quantity']} 口 @ 平均{h['avg_cost_jpy']:,.0f}円 "
            f"(現在{h['current_price_jpy']:,.0f}円, 評価損益{pnl:+,.0f}円, 比率{pct:.1f}%)"
        )
    return "\n".join(lines)


def _format_market_data(market_data: dict) -> str:
    if not market_data:
        return "データなし"
    lines = []
    for sym, d in market_data.items():
        change_24h = d.get('price_change_24h_pct')
        change_7d = d.get('price_change_7d_pct')
        price_jpy = d.get('price_jpy', 0)
        lines.append(
            f"- {sym}: {price_jpy:,.2f}円 "
            f"(24h: {change_24h:+.2f}%" if change_24h is not None else f"- {sym}: {price_jpy:,.2f}円"
        )
        if change_24h is not None:
            lines[-1] += f" 24h:{change_24h:+.2f}%"
        if change_7d is not None:
            lines[-1] += f" 7d:{change_7d:+.2f}%"
        lines[-1] += ")"
    return "\n".join(lines)


def _format_technical(technical: dict) -> str:
    if not technical:
        return "データなし"
    lines = []
    for sym, ind in technical.items():
        if hasattr(ind, "get_summary"):
            lines.append(f"- {sym}: {ind.get_summary()}")
        elif isinstance(ind, dict):
            rsi = ind.get('rsi_14')
            trend = ind.get('trend', 'N/A')
            lines.append(f"- {sym}: RSI={rsi:.1f if rsi else 'N/A'} Trend={trend}")
    return "\n".join(lines)


def _format_decisions(decisions: list) -> str:
    if not decisions:
        return "履歴なし"
    lines = []
    for d in decisions[:20]:  # limit to 20
        if hasattr(d, "decided_at"):
            # SQLAlchemy model
            lines.append(
                f"- {d.decided_at.strftime('%m/%d %H:%M')} {d.symbol} {d.action} "
                f"信頼度{d.confidence}% {d.reasoning[:80] if d.reasoning else ''}..."
            )
        elif isinstance(d, dict):
            lines.append(
                f"- {d.get('date', '')} {d.get('symbol', '')} {d.get('action', '')} "
                f"信頼度{d.get('confidence', 0)}%"
            )
    return "\n".join(lines)


def _format_candidates(candidates: list) -> str:
    if not candidates:
        return "なし"
    lines = []
    for c in candidates:
        lines.append(
            f"  {c.get('symbol')}: {c.get('action_candidate')} (信頼度{c.get('confidence', 0)}%) - {c.get('notes', '')}"
        )
    return "\n".join(lines)


def _format_review(review: dict | None) -> str:
    if not review:
        return "反省会データなし"
    if hasattr(review, "next_week_strategy"):
        return (
            f"来週の方針: {review.next_week_strategy}\n"
            f"根拠: {review.next_week_rationale or 'N/A'}\n"
            f"改善計画: {review.improvement_plan or 'N/A'}"
        )
    return (
        f"来週の方針: {review.get('next_week_strategy', 'N/A')}\n"
        f"根拠: {review.get('next_week_rationale', 'N/A')}"
    )


def _format_trades(trades: list) -> str:
    if not trades:
        return "売買なし"
    lines = []
    for t in trades:
        if hasattr(t, "executed_at"):
            lines.append(
                f"- {t.executed_at.strftime('%m/%d')} {t.action} {t.symbol} "
                f"{t.quantity}口 @ {float(t.price_jpy):,.0f}円"
            )
    return "\n".join(lines)


def _format_benchmark(benchmark: dict) -> str:
    if not benchmark:
        return "データなし"
    lines = []
    for sym, ret in benchmark.items():
        lines.append(f"- {sym}: {ret:+.2f}%")
    return "\n".join(lines)
