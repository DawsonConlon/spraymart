from datetime import date

from fastapi import APIRouter, Query
from app.services.weather_client import weather_client

router = APIRouter()


@router.get("/current")
async def current_conditions(lat: float = Query(...), lon: float = Query(...)):
    return await weather_client.get_current_conditions(lat, lon)


@router.get("/forecast")
async def forecast(lat: float = Query(...), lon: float = Query(...)):
    return await weather_client.get_forecast(lat, lon)


@router.get("/historical")
async def historical(
    lat: float = Query(...),
    lon: float = Query(...),
    start_date: date = Query(...),
    end_date: date | None = Query(None),
    hourly: str | None = Query(None),
    daily: str | None = Query(None),
    timezone: str = Query("UTC"),
):
    """Fetch historical weather from Open-Meteo ERA5 archive."""
    return await weather_client.get_open_meteo_historical(
        lat,
        lon,
        start_date,
        end_date=end_date,
        hourly=hourly or "temperature_2m,relative_humidity_2m,dew_point_2m,rain,wind_speed_10m,wind_direction_10m,wind_gusts_10m,soil_temperature_7_to_28cm,soil_moisture_7_to_28cm",
        daily=daily or "temperature_2m_min",
        timezone=timezone,
    )
