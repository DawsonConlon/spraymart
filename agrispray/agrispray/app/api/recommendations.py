from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from app.db.session import get_db
from app.models.field import Field
from app.services.weather_client import weather_client
from app.services.recommendation_engine import generate_recommendation, RecommendationResult
from app.schemas.recommendation import RecommendationResponse

router = APIRouter()


@router.get("/{field_id}", response_model=RecommendationResponse)
async def get_recommendation(
    field_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a spray recommendation for a given field.
    Pulls weather automatically from Environment Canada using the field's LSD coords.
    """
    result = await db.execute(select(Field).where(Field.id == field_id))
    field = result.scalar_one_or_none()

    if not field:
        raise HTTPException(status_code=404, detail="Field not found")

    if not field.latitude or not field.longitude:
        raise HTTPException(
            status_code=422,
            detail="Field missing lat/lon — ensure LSD has been geocoded"
        )

    # Fetch weather data
    try:
        history = await weather_client.get_historical_daily(
            latitude=field.latitude,
            longitude=field.longitude,
            start_date=field.plant_date,
        )
        current = await weather_client.get_current_conditions(field.latitude, field.longitude)
        forecast = await weather_client.get_forecast(field.latitude, field.longitude)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Weather service error: {str(e)}")

    recommendation = generate_recommendation(
        daily_weather_history=history,
        crop_type=field.crop_type.value,
        plant_date=field.plant_date,
        wind_speed_kmh=current["wind_speed_kmh"] or 0,
        temperature_c=current["temperature_c"] or 15,
        humidity_pct=current["humidity_pct"] or 60,
        rain_in_24h=forecast["rain_in_24h"],
        overnight_low_c=forecast["overnight_low_c"] or 5,
    )

    return RecommendationResponse(
        field_id=field_id,
        field_name=field.name,
        decision=recommendation.decision,
        summary=recommendation.summary,
        overall_score=recommendation.overall_score,
        gdd_accumulated=recommendation.plant_stage.accumulated_gdd,
        estimated_stage=recommendation.plant_stage.estimated_stage,
        stage_confidence=recommendation.plant_stage.stage_confidence,
        condition_checks=[
            {
                "name": c.name,
                "passed": c.passed,
                "value": c.value,
                "threshold": c.threshold,
                "message": c.message,
            }
            for c in (recommendation.conditions.checks if recommendation.conditions else [])
        ],
    )
