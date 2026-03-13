"""
Spray condition scorer.

Evaluates real-time and forecast weather conditions against agronomic
thresholds and returns a scored recommendation: SPRAY_NOW / WAIT / DO_NOT_SPRAY.
"""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class SprayDecision(str, Enum):
    SPRAY_NOW = "spray_now"
    WAIT = "wait"
    DO_NOT_SPRAY = "do_not_spray"


@dataclass
class ConditionCheck:
    name: str
    passed: bool
    value: float | str | bool
    threshold: str
    message: str


@dataclass
class SprayScoreResult:
    decision: SprayDecision
    summary: str                          # Plain-language sentence for the farmer
    overall_score: float                  # 0–100
    checks: list[ConditionCheck] = field(default_factory=list)
    next_window_hint: Optional[str] = None   # "Conditions improve after 7am tomorrow"


# ── Thresholds ──────────────────────────────────────────────────────────────

WIND_MAX_KMPH = 15.0          # Above this: drift risk too high
WIND_IDEAL_MAX = 10.0         # Below this: ideal
TEMP_MIN_C = 10.0             # Below this: chemical efficacy drops
TEMP_MAX_C = 28.0             # Above this: volatilization risk
HUMIDITY_MIN_PCT = 40.0       # Below this: droplets evaporate before contact
HUMIDITY_MAX_PCT = 90.0       # Above this: poor drying, fungal risk
RAIN_WINDOW_HOURS = 24        # Avoid spraying if rain forecast within this window
INVERSION_TEMP_DIFF = 2.0     # If night cooler than day by <2°C: inversion risk


def check_wind(wind_speed_kmh: float) -> ConditionCheck:
    passed = wind_speed_kmh <= WIND_MAX_KMPH
    return ConditionCheck(
        name="wind_speed",
        passed=passed,
        value=wind_speed_kmh,
        threshold=f"≤ {WIND_MAX_KMPH} km/h",
        message=(
            f"Wind at {wind_speed_kmh:.1f} km/h — within drift limits"
            if passed
            else f"Wind at {wind_speed_kmh:.1f} km/h — exceeds {WIND_MAX_KMPH} km/h drift threshold"
        ),
    )


def check_temperature(temp_c: float) -> ConditionCheck:
    passed = TEMP_MIN_C <= temp_c <= TEMP_MAX_C
    if temp_c < TEMP_MIN_C:
        msg = f"Temperature {temp_c:.1f}°C — too cold, herbicide efficacy reduced below {TEMP_MIN_C}°C"
    elif temp_c > TEMP_MAX_C:
        msg = f"Temperature {temp_c:.1f}°C — too hot, volatilization risk above {TEMP_MAX_C}°C"
    else:
        msg = f"Temperature {temp_c:.1f}°C — within safe range"
    return ConditionCheck(
        name="temperature",
        passed=passed,
        value=temp_c,
        threshold=f"{TEMP_MIN_C}–{TEMP_MAX_C}°C",
        message=msg,
    )


def check_humidity(humidity_pct: float) -> ConditionCheck:
    passed = HUMIDITY_MIN_PCT <= humidity_pct <= HUMIDITY_MAX_PCT
    if humidity_pct < HUMIDITY_MIN_PCT:
        msg = f"Humidity {humidity_pct:.0f}% — too dry, droplets evaporate before contact"
    elif humidity_pct > HUMIDITY_MAX_PCT:
        msg = f"Humidity {humidity_pct:.0f}% — too humid, poor drying and fungal risk"
    else:
        msg = f"Humidity {humidity_pct:.0f}% — good"
    return ConditionCheck(
        name="humidity",
        passed=passed,
        value=humidity_pct,
        threshold=f"{HUMIDITY_MIN_PCT}–{HUMIDITY_MAX_PCT}%",
        message=msg,
    )


def check_rain_forecast(rain_in_24h: bool) -> ConditionCheck:
    passed = not rain_in_24h
    return ConditionCheck(
        name="rain_forecast",
        passed=passed,
        value=rain_in_24h,
        threshold="No rain forecast in 24h",
        message=(
            "No rain forecast in next 24 hours" if passed
            else "Rain forecast within 24 hours — application would be washed off"
        ),
    )


def check_temperature_inversion(
    current_temp_c: float,
    overnight_low_c: float,
) -> ConditionCheck:
    """
    Temperature inversions trap spray droplets near the ground and cause
    off-target drift. Risk is highest when the overnight low is close to
    the daytime high (small diurnal range).
    """
    diff = current_temp_c - overnight_low_c
    passed = diff >= INVERSION_TEMP_DIFF
    return ConditionCheck(
        name="temperature_inversion",
        passed=passed,
        value=round(diff, 1),
        threshold=f"Day/night diff ≥ {INVERSION_TEMP_DIFF}°C",
        message=(
            f"Day/night temp differential {diff:.1f}°C — inversion unlikely"
            if passed
            else f"Day/night differential only {diff:.1f}°C — temperature inversion risk, drift likely"
        ),
    )


def score_conditions(
    wind_speed_kmh: float,
    temperature_c: float,
    humidity_pct: float,
    rain_in_24h: bool,
    overnight_low_c: float,
    next_window_hint: Optional[str] = None,
) -> SprayScoreResult:
    """
    Run all condition checks and produce a final spray recommendation.
    """
    checks = [
        check_wind(wind_speed_kmh),
        check_temperature(temperature_c),
        check_humidity(humidity_pct),
        check_rain_forecast(rain_in_24h),
        check_temperature_inversion(temperature_c, overnight_low_c),
    ]

    passed = [c for c in checks if c.passed]
    failed = [c for c in checks if not c.passed]

    # Score: each check weighted equally for now
    overall_score = round((len(passed) / len(checks)) * 100)

    # Decision logic
    # Hard blocks: wind, rain, inversion — any single failure = WAIT or DO_NOT_SPRAY
    hard_failures = [c for c in failed if c.name in ("wind_speed", "rain_forecast", "temperature_inversion")]

    if len(failed) == 0:
        decision = SprayDecision.SPRAY_NOW
        summary = (
            f"All conditions met — wind {wind_speed_kmh:.0f} km/h, "
            f"temp {temperature_c:.0f}°C, humidity {humidity_pct:.0f}%. "
            "Good time to spray."
        )
    elif hard_failures:
        decision = SprayDecision.WAIT
        reasons = "; ".join(c.message for c in hard_failures)
        summary = f"Hold off — {reasons}."
        if next_window_hint:
            summary += f" {next_window_hint}."
    else:
        # Minor failures only (temp or humidity edge cases) — still advise waiting
        decision = SprayDecision.WAIT
        reasons = "; ".join(c.message for c in failed)
        summary = f"Conditions marginal — {reasons}."

    return SprayScoreResult(
        decision=decision,
        summary=summary,
        overall_score=overall_score,
        checks=checks,
        next_window_hint=next_window_hint,
    )
