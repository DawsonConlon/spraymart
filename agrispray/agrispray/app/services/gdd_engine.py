"""
Growing Degree Day (GDD) engine.

Accumulates heat units from planting date to today using historical
weather data per LSD, then maps GDD + sunlight hours to a crop
growth stage estimate.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional
from enum import Enum


class PlantStage(str, Enum):
    PRE_EMERGENCE = "pre_emergence"       # Not yet out of ground
    EMERGENCE = "emergence"               # 1–2 leaf — most vulnerable
    EARLY_VEGETATIVE = "early_vegetative" # 3–4 leaf — spray window opens
    OPTIMAL = "optimal"                   # Target spray zone
    LATE_VEGETATIVE = "late_vegetative"   # Approaching cutoff
    REPRODUCTIVE = "reproductive"         # Flowering/bolting — spray may damage crop
    TOO_LATE = "too_late"                 # Weeds too large, crop too advanced


@dataclass
class GDDResult:
    accumulated_gdd: float
    sunlight_hours: float
    days_since_planting: int
    estimated_stage: PlantStage
    stage_confidence: float               # 0.0–1.0
    spray_eligible: bool
    ineligibility_reason: Optional[str]


# Base temperatures (°C) by crop — below this, no growth occurs
CROP_BASE_TEMPS = {
    "canola": 5.0,
    "wheat": 0.0,
    "barley": 0.0,
    "oats": 0.0,
    "lentils": 4.0,
    "peas": 4.0,
    "flax": 5.0,
}

# GDD thresholds for each stage by crop
# Format: (min_gdd, max_gdd, PlantStage)
CROP_STAGE_THRESHOLDS = {
    "canola": [
        (0,    100,  PlantStage.PRE_EMERGENCE),
        (100,  200,  PlantStage.EMERGENCE),
        (200,  350,  PlantStage.EARLY_VEGETATIVE),
        (350,  600,  PlantStage.OPTIMAL),
        (600,  800,  PlantStage.LATE_VEGETATIVE),
        (800,  1100, PlantStage.REPRODUCTIVE),
        (1100, 9999, PlantStage.TOO_LATE),
    ],
    "wheat": [
        (0,    75,   PlantStage.PRE_EMERGENCE),
        (75,   150,  PlantStage.EMERGENCE),
        (150,  300,  PlantStage.EARLY_VEGETATIVE),
        (300,  550,  PlantStage.OPTIMAL),
        (550,  750,  PlantStage.LATE_VEGETATIVE),
        (750,  1000, PlantStage.REPRODUCTIVE),
        (1000, 9999, PlantStage.TOO_LATE),
    ],
    "barley": [
        (0,    60,   PlantStage.PRE_EMERGENCE),
        (60,   130,  PlantStage.EMERGENCE),
        (130,  270,  PlantStage.EARLY_VEGETATIVE),
        (270,  500,  PlantStage.OPTIMAL),
        (500,  700,  PlantStage.LATE_VEGETATIVE),
        (700,  950,  PlantStage.REPRODUCTIVE),
        (950,  9999, PlantStage.TOO_LATE),
    ],
}

# Stages where spraying is permitted
SPRAY_ELIGIBLE_STAGES = {
    PlantStage.EARLY_VEGETATIVE,
    PlantStage.OPTIMAL,
    PlantStage.LATE_VEGETATIVE,
}

INELIGIBILITY_MESSAGES = {
    PlantStage.PRE_EMERGENCE: "Crop has not yet emerged — too early to spray",
    PlantStage.EMERGENCE:     "Seedlings too young and fragile for chemical application",
    PlantStage.REPRODUCTIVE:  "Crop is flowering/bolting — spraying risks pollinator harm and yield loss",
    PlantStage.TOO_LATE:      "Crop too mature and weeds too large for effective treatment",
}


def calculate_daily_gdd(max_temp_c: float, min_temp_c: float, base_temp: float) -> float:
    """Standard single-triangle GDD method used by AAFC and provincial agronomists."""
    avg = (max_temp_c + min_temp_c) / 2.0
    return max(0.0, avg - base_temp)


def accumulate_gdd(
    daily_weather: list[dict],   # [{"date": date, "max_c": float, "min_c": float, "sunlight_hours": float}]
    crop_type: str,
    plant_date: date,
) -> tuple[float, float]:
    """
    Sum GDD and sunlight hours from plant_date to most recent record.
    Returns (total_gdd, total_sunlight_hours).
    """
    base_temp = CROP_BASE_TEMPS.get(crop_type, 5.0)
    total_gdd = 0.0
    total_sunlight = 0.0

    for record in daily_weather:
        if record["date"] < plant_date:
            continue
        total_gdd += calculate_daily_gdd(record["max_c"], record["min_c"], base_temp)
        total_sunlight += record.get("sunlight_hours", 0.0)

    return total_gdd, total_sunlight


def estimate_stage(
    accumulated_gdd: float,
    sunlight_hours: float,
    days_since_planting: int,
    crop_type: str,
) -> tuple[PlantStage, float]:
    """
    Map GDD + sunlight context to a growth stage with a confidence score.

    Sunlight hours act as a modifier: if sunlight is low relative to days
    since planting (overcast spring), we nudge the stage estimate earlier
    because the crop is likely lagging behind what GDD alone suggests.
    """
    thresholds = CROP_STAGE_THRESHOLDS.get(crop_type, CROP_STAGE_THRESHOLDS["canola"])

    # Base stage from GDD
    stage = PlantStage.PRE_EMERGENCE
    for min_gdd, max_gdd, candidate_stage in thresholds:
        if min_gdd <= accumulated_gdd < max_gdd:
            stage = candidate_stage
            break

    # Sunlight modifier: expected ~14 hrs/day in SK May–June
    expected_sunlight = days_since_planting * 13.5
    sunlight_ratio = sunlight_hours / max(expected_sunlight, 1.0)

    # If significantly less sunlight than expected, reduce confidence
    # and apply a conservative (earlier) stage bump
    confidence = min(1.0, 0.6 + sunlight_ratio * 0.4)

    if sunlight_ratio < 0.7 and stage not in (PlantStage.PRE_EMERGENCE, PlantStage.TOO_LATE):
        # Crop may be behind — lower confidence, keep current stage conservative
        confidence *= 0.8

    return stage, round(confidence, 2)


def evaluate_plant_stage(
    daily_weather: list[dict],
    crop_type: str,
    plant_date: date,
    today: Optional[date] = None,
) -> GDDResult:
    """
    Main entry point for the plant stage evaluator.
    Returns a GDDResult with stage, eligibility, and reason.
    """
    today = today or date.today()
    days_since_planting = (today - plant_date).days

    accumulated_gdd, sunlight_hours = accumulate_gdd(daily_weather, crop_type, plant_date)
    stage, confidence = estimate_stage(accumulated_gdd, sunlight_hours, days_since_planting, crop_type)

    spray_eligible = stage in SPRAY_ELIGIBLE_STAGES
    reason = INELIGIBILITY_MESSAGES.get(stage) if not spray_eligible else None

    return GDDResult(
        accumulated_gdd=round(accumulated_gdd, 1),
        sunlight_hours=round(sunlight_hours, 1),
        days_since_planting=days_since_planting,
        estimated_stage=stage,
        stage_confidence=confidence,
        spray_eligible=spray_eligible,
        ineligibility_reason=reason,
    )
