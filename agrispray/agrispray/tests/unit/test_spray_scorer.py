import pytest
from app.services.spray_scorer import score_conditions, SprayDecision


def test_all_conditions_pass():
    result = score_conditions(
        wind_speed_kmh=8, temperature_c=18, humidity_pct=65,
        rain_in_24h=False, overnight_low_c=10
    )
    assert result.decision == SprayDecision.SPRAY_NOW
    assert result.overall_score == 100


def test_high_wind_blocks_spray():
    result = score_conditions(
        wind_speed_kmh=22, temperature_c=18, humidity_pct=65,
        rain_in_24h=False, overnight_low_c=10
    )
    assert result.decision == SprayDecision.WAIT
    wind_check = next(c for c in result.checks if c.name == "wind_speed")
    assert wind_check.passed is False


def test_rain_forecast_blocks_spray():
    result = score_conditions(
        wind_speed_kmh=8, temperature_c=18, humidity_pct=65,
        rain_in_24h=True, overnight_low_c=10
    )
    assert result.decision == SprayDecision.WAIT


def test_temperature_inversion_risk():
    """Day and night temps too close — inversion risk."""
    result = score_conditions(
        wind_speed_kmh=5, temperature_c=14, humidity_pct=60,
        rain_in_24h=False, overnight_low_c=13
    )
    inv_check = next(c for c in result.checks if c.name == "temperature_inversion")
    assert inv_check.passed is False
    assert result.decision == SprayDecision.WAIT


def test_next_window_hint_in_summary():
    result = score_conditions(
        wind_speed_kmh=20, temperature_c=18, humidity_pct=65,
        rain_in_24h=False, overnight_low_c=10,
        next_window_hint="Wind drops below 10 km/h at 6am tomorrow"
    )
    assert "6am tomorrow" in result.summary
