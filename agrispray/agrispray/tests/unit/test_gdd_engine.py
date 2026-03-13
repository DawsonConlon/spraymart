"""
Unit tests for the GDD engine — the most critical piece of the system.
Run with: pytest tests/unit/test_gdd_engine.py -v
"""

import pytest
from datetime import date
from app.services.gdd_engine import (
    calculate_daily_gdd,
    evaluate_plant_stage,
    PlantStage,
)


# ── GDD calculation ──────────────────────────────────────────────────────────

def test_gdd_normal_day():
    assert calculate_daily_gdd(max_temp_c=22, min_temp_c=8, base_temp=5) == 10.0

def test_gdd_cold_day_returns_zero():
    """Below-base days contribute nothing."""
    assert calculate_daily_gdd(max_temp_c=4, min_temp_c=0, base_temp=5) == 0.0

def test_gdd_exact_base_temp():
    assert calculate_daily_gdd(max_temp_c=10, min_temp_c=0, base_temp=5) == 0.0


# ── Plant stage evaluator ────────────────────────────────────────────────────

def _make_weather(days: int, max_c: float, min_c: float, sun: float = 13.0) -> list[dict]:
    """Helper: generate N days of uniform weather starting May 1."""
    start = date(2024, 5, 1)
    from datetime import timedelta
    return [
        {"date": start + timedelta(days=i), "max_c": max_c, "min_c": min_c, "sunlight_hours": sun}
        for i in range(days)
    ]


def test_canola_pre_emergence():
    """Only 3 warm days — crop hasn't emerged yet."""
    weather = _make_weather(3, max_c=15, min_c=5, sun=12)
    result = evaluate_plant_stage(weather, "canola", date(2024, 5, 1))
    assert result.estimated_stage == PlantStage.PRE_EMERGENCE
    assert result.spray_eligible is False


def test_canola_optimal_window():
    """25 warm days should put canola in the optimal spray window."""
    weather = _make_weather(25, max_c=22, min_c=10, sun=14)
    result = evaluate_plant_stage(weather, "canola", date(2024, 5, 1))
    assert result.estimated_stage in (PlantStage.OPTIMAL, PlantStage.EARLY_VEGETATIVE)
    assert result.spray_eligible is True
    assert result.accumulated_gdd > 300


def test_too_late_to_spray():
    """60 hot days — canola is reproductive, window closed."""
    weather = _make_weather(60, max_c=28, min_c=14, sun=15)
    result = evaluate_plant_stage(weather, "canola", date(2024, 5, 1))
    assert result.estimated_stage in (PlantStage.REPRODUCTIVE, PlantStage.TOO_LATE)
    assert result.spray_eligible is False
    assert result.ineligibility_reason is not None


def test_low_sunlight_reduces_confidence():
    """Overcast spring — confidence drops but stage estimate stays conservative."""
    weather = _make_weather(20, max_c=20, min_c=8, sun=4.0)
    result = evaluate_plant_stage(weather, "canola", date(2024, 5, 1))
    assert result.stage_confidence < 0.85


def test_wheat_different_thresholds():
    """Wheat has a lower base temp — should accumulate GDD faster than canola."""
    weather = _make_weather(10, max_c=12, min_c=2, sun=12)
    canola = evaluate_plant_stage(weather, "canola", date(2024, 5, 1))
    wheat = evaluate_plant_stage(weather, "wheat", date(2024, 5, 1))
    assert wheat.accumulated_gdd > canola.accumulated_gdd
