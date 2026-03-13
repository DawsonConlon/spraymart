from fastapi import APIRouter, Query
from app.services.weather_client import weather_client

router = APIRouter()


@router.get("/current")
async def current_conditions(lat: float = Query(...), lon: float = Query(...)):
    return await weather_client.get_current_conditions(lat, lon)


@router.get("/forecast")
async def forecast(lat: float = Query(...), lon: float = Query(...)):
    return await weather_client.get_forecast(lat, lon)
