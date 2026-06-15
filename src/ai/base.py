from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class AssetDecision:
    symbol: str
    action: str  # BUY / SELL / HOLD
    quantity: Optional[float]
    confidence: int  # 0-100
    expected_return_pct: Optional[float]
    expected_timeframe: Optional[str]
    risk_level: str  # low / medium / high
    reasoning: str
    key_factors: list[str] = field(default_factory=list)


@dataclass
class MorningAnalysisResult:
    overall_sentiment: str  # bullish / neutral / bearish
    market_analysis: dict[str, Any]
    investment_candidates: list[dict]
    risk_assessment: dict
    analysis_summary: str
    system_prompt: str
    user_prompt: str
    raw_response: str
    model_id: str
    input_tokens: int
    output_tokens: int
    api_cost_usd: float


@dataclass
class EveningDecisionResult:
    decisions: list[AssetDecision]
    portfolio_strategy: str
    market_outlook: str
    overall_reasoning: str
    system_prompt: str
    user_prompt: str
    raw_response: str
    model_id: str
    input_tokens: int
    output_tokens: int
    api_cost_usd: float


@dataclass
class WeeklyReviewResult:
    performance_summary: str
    good_decisions: list[dict]
    bad_decisions: list[dict]
    key_learnings: list[str]
    improvement_plan: str
    next_week_strategy: str  # bullish / neutral / bearish
    next_week_rationale: str
    system_prompt: str
    user_prompt: str
    raw_response: str
    model_id: str
    input_tokens: int
    output_tokens: int
    api_cost_usd: float


class AIAgent(ABC):
    @abstractmethod
    def run_morning_analysis(self, context: dict) -> MorningAnalysisResult:
        ...

    @abstractmethod
    def run_evening_analysis(self, context: dict) -> EveningDecisionResult:
        ...

    @abstractmethod
    def run_weekly_review(self, context: dict) -> WeeklyReviewResult:
        ...
