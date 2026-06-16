import json
import logging
import re
from typing import Any

import anthropic

from src.config import get_settings
from .base import (
    AIAgent, AssetDecision, MorningAnalysisResult, EveningDecisionResult, WeeklyReviewResult
)
from .prompts import (
    MORNING_ANALYSIS_SYSTEM, EVENING_ANALYSIS_SYSTEM, WEEKLY_REVIEW_SYSTEM,
    build_morning_user_prompt, build_evening_user_prompt, build_weekly_review_user_prompt,
)

logger = logging.getLogger(__name__)


class ClaudeAgent(AIAgent):
    """Claude API を使った投資判断エージェント"""

    def __init__(self):
        settings = get_settings()
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = settings.CLAUDE_MODEL
        self.input_cost, self.output_cost = settings.claude_token_costs

    def _call_api(self, system: str, user: str, max_tokens: int = 4096) -> tuple[str, int, int, float]:
        """Claude API 呼び出し。(response_text, input_tokens, output_tokens, cost_usd) を返す"""
        message = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        response_text = message.content[0].text
        input_tokens = message.usage.input_tokens
        output_tokens = message.usage.output_tokens
        cost_usd = input_tokens * self.input_cost + output_tokens * self.output_cost
        logger.info(
            f"API call: model={self.model} in={input_tokens} out={output_tokens} cost=${cost_usd:.4f}"
        )
        return response_text, input_tokens, output_tokens, cost_usd

    def _extract_json(self, text: str) -> dict:
        """レスポンスからJSONを抽出してパース"""
        # Try to find JSON block in code fence
        fence_match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", text)
        if fence_match:
            try:
                return json.loads(fence_match.group(1))
            except json.JSONDecodeError:
                pass

        # Try to find raw JSON
        brace_match = re.search(r"\{[\s\S]+\}", text)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except json.JSONDecodeError:
                pass

        logger.error(f"Failed to parse JSON from response: {text[:200]}")
        return {}

    def run_morning_analysis(self, context: dict) -> MorningAnalysisResult:
        settings = get_settings()
        system_prompt = MORNING_ANALYSIS_SYSTEM
        user_prompt = build_morning_user_prompt(
            portfolio=context.get("portfolio", {}),
            market_data=context.get("market_data", {}),
            technical=context.get("technical", {}),
            recent_decisions=context.get("recent_decisions", []),
            latest_review=context.get("latest_review"),
            usdjpy=context.get("usdjpy", 150.0),
        )

        logger.info("Running morning analysis with Claude...")
        raw_response, input_tokens, output_tokens, cost = self._call_api(
            system_prompt, user_prompt, max_tokens=4096
        )

        parsed = self._extract_json(raw_response)

        return MorningAnalysisResult(
            overall_sentiment=parsed.get("overall_sentiment", "neutral"),
            market_analysis=parsed.get("market_analysis", {}),
            investment_candidates=parsed.get("investment_candidates", []),
            risk_assessment=parsed.get("risk_assessment", {}),
            analysis_summary=parsed.get("analysis_summary", raw_response[:500]),
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            raw_response=raw_response,
            model_id=self.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            api_cost_usd=cost,
        )

    def run_evening_analysis(self, context: dict) -> EveningDecisionResult:
        system_prompt = EVENING_ANALYSIS_SYSTEM
        user_prompt = build_evening_user_prompt(
            portfolio=context.get("portfolio", {}),
            market_data=context.get("market_data", {}),
            technical=context.get("technical", {}),
            morning_analysis=context.get("morning_analysis"),
            recent_decisions=context.get("recent_decisions", []),
            latest_review=context.get("latest_review"),
            usdjpy=context.get("usdjpy", 150.0),
        )

        logger.info("Running evening analysis with Claude...")
        raw_response, input_tokens, output_tokens, cost = self._call_api(
            system_prompt, user_prompt, max_tokens=4096
        )

        parsed = self._extract_json(raw_response)
        decisions = self._parse_decisions(parsed.get("decisions", []))

        return EveningDecisionResult(
            decisions=decisions,
            portfolio_strategy=parsed.get("portfolio_strategy", ""),
            market_outlook=parsed.get("market_outlook", "neutral"),
            overall_reasoning=parsed.get("overall_reasoning", raw_response[:500]),
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            raw_response=raw_response,
            model_id=self.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            api_cost_usd=cost,
        )

    def run_weekly_review(self, context: dict) -> WeeklyReviewResult:
        system_prompt = WEEKLY_REVIEW_SYSTEM
        user_prompt = build_weekly_review_user_prompt(
            portfolio=context.get("portfolio", {}),
            weekly_trades=context.get("weekly_trades", []),
            weekly_decisions=context.get("weekly_decisions", []),
            performance_metrics=context.get("performance_metrics", {}),
            benchmark_returns=context.get("benchmark_returns", {}),
            previous_review=context.get("previous_review"),
        )

        logger.info("Running weekly review with Claude...")
        raw_response, input_tokens, output_tokens, cost = self._call_api(
            system_prompt, user_prompt, max_tokens=4096
        )

        parsed = self._extract_json(raw_response)

        return WeeklyReviewResult(
            performance_summary=parsed.get("performance_summary", ""),
            good_decisions=parsed.get("good_decisions", []),
            bad_decisions=parsed.get("bad_decisions", []),
            key_learnings=parsed.get("key_learnings", []),
            improvement_plan=parsed.get("improvement_plan", ""),
            next_week_strategy=parsed.get("next_week_strategy", "neutral"),
            next_week_rationale=parsed.get("next_week_rationale", ""),
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            raw_response=raw_response,
            model_id=self.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            api_cost_usd=cost,
        )

    def _parse_decisions(self, raw_decisions: list) -> list[AssetDecision]:
        decisions = []
        for d in raw_decisions:
            if not isinstance(d, dict):
                continue
            action = str(d.get("action", "HOLD")).upper()
            if action not in ("BUY", "SELL", "HOLD"):
                action = "HOLD"
            decisions.append(
                AssetDecision(
                    symbol=d.get("symbol", ""),
                    action=action,
                    quantity=d.get("quantity"),
                    confidence=int(d.get("confidence", 50)),
                    expected_return_pct=d.get("expected_return_pct"),
                    expected_timeframe=d.get("expected_timeframe"),
                    risk_level=d.get("risk_level", "medium"),
                    reasoning=d.get("reasoning", ""),
                    key_factors=d.get("key_factors", []),
                )
            )
        return decisions
