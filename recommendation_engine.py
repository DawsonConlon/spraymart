"""
Recommendation engine — combines plant stage + spray conditions into
the final green/yellow/red output for the farmer.
"""

from dataclasses import dataclass
from datetime import date
from typing import Optional

from app.services.gdd_engine import evaluate_plant_stage, GDDResult, PlantStage
from app.services.spray_scorer import score_conditions, SprayScoreResult, SprayDecision


@dataclass
class RecommendationResult:
    decision: SprayDecision           # SPRAY_NOW / WAIT / DO_NOT_SPRAY
    summary: str                      # One sentence the farmer reads
    plant_stage: GDDResult
    conditions: SprayScoreResult
    overall_score: float              # 0–100 composite


def generate_recommendation(
    # Field / crop inputs
    daily_weather_history: list[dict],
    crop_type: str,
    plant_date: date,

    # Current conditions (from EC or JD station)
    wind_speed_kmh: float,
    temperature_c: float,
    humidity_pct: float,
    rain_in_24h: bool,
    overnight_low_c: float,

    today: Optional[date] = None,
    next_window_hint: Optional[str] = None,
) -> RecommendationResult:

    # Step 1: Is the plant at a sprayable stage?
    stage_result = evaluate_plant_stage(
        daily_weather=daily_weather_history,
        crop_type=crop_type,
        plant_date=plant_date,
        today=today,
    )

    # Step 2: If stage gates out — don't bother scoring weather
    if not stage_result.spray_eligible:
        return RecommendationResult(
            decision=SprayDecision.DO_NOT_SPRAY,
            summary=stage_result.ineligibility_reason or "Plant stage does not permit spraying.",
            plant_stage=stage_result,
            conditions=None,
            overall_score=0.0,
        )

    # Step 3: Score weather conditions
    condition_result = score_conditions(
        wind_speed_kmh=wind_speed_kmh,
        temperature_c=temperature_c,
        humidity_pct=humidity_pct,
        rain_in_24h=rain_in_24h,
        overnight_low_c=overnight_low_c,
        next_window_hint=next_window_hint,
    )

    # Step 4: Composite score — stage confidence weighted 30%, conditions 70%
    composite = round(
        (stage_result.stage_confidence * 30) + (condition_result.overall_score * 0.70),
        1,
    )

    # Step 5: Late-stage penalty — LATE_VEGETATIVE gets a warning even if conditions pass
    summary = condition_result.summary
    if (
        stage_result.estimated_stage == PlantStage.LATE_VEGETATIVE
        and condition_result.decision == SprayDecision.SPRAY_NOW
    ):
        summary = (
            f"Conditions are good, but crop is in late vegetative stage "
            f"({stage_result.accumulated_gdd:.0f} GDD). "
            "Act within the next 24–48 hours or the window will close."
        )

    return RecommendationResult(
        decision=condition_result.decision,
        summary=summary,
        plant_stage=stage_result,
        conditions=condition_result,
        overall_score=composite,
    )
