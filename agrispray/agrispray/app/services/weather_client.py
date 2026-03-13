"""
Weather data client.

Pulls from Environment Canada (primary) with optional fallback to a
John Deere Operations Center weather station for hyper-local readings.
"""

import httpx
from datetime import date, timedelta
from typing import Optional

from app.core.config import settings


class WeatherClient:

    def __init__(self):
        self.ec_base = settings.ECCC_BASE_URL

    async def get_historical_daily(
        self,
        latitude: float,
        longitude: float,
        start_date: date,
        end_date: Optional[date] = None,
    ) -> list[dict]:
        """
        Fetch daily max/min temps and sunlight hours from Environment Canada
        for a given lat/lon from start_date to end_date (inclusive).

        Returns list of:
          {"date": date, "max_c": float, "min_c": float, "sunlight_hours": float}
        """
        end_date = end_date or date.today()

        # Environment Canada Climate Web Services (ECCC MSC GeoMet API)
        # Docs: https://api.weather.gc.ca
        url = f"{self.ec_base}/collections/climate-daily/items"
        params = {
            "LATITUDE": latitude,
            "LONGITUDE": longitude,
            "datetime": f"{start_date}/{end_date}",
            "f": "json",
            "limit": 365,
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        records = []
        for feature in data.get("features", []):
            props = feature["properties"]
            records.append({
                "date": date.fromisoformat(props["LOCAL_DATE"][:10]),
                "max_c": props.get("MAX_TEMPERATURE") or 0.0,
                "min_c": props.get("MIN_TEMPERATURE") or 0.0,
                "sunlight_hours": props.get("BRIGHT_SUNSHINE") or 0.0,
            })

        return sorted(records, key=lambda r: r["date"])

    async def get_current_conditions(
        self,
        latitude: float,
        longitude: float,
    ) -> dict:
        """
        Fetch current observations from the nearest EC station.
        Returns temperature, wind speed, humidity.
        """
        url = f"{self.ec_base}/collections/observations/items"
        params = {
            "LATITUDE": latitude,
            "LONGITUDE": longitude,
            "sortby": "-OBSERVATION_DATE",
            "limit": 1,
            "f": "json",
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        features = data.get("features", [])
        if not features:
            raise ValueError("No current observations found for this location")

        props = features[0]["properties"]
        return {
            "temperature_c": props.get("AIR_TEMP"),
            "wind_speed_kmh": props.get("WIND_SPEED"),
            "humidity_pct": props.get("RELATIVE_HUMIDITY"),
            "wind_direction": props.get("WIND_DIRECTION"),
            "observed_at": props.get("OBSERVATION_DATE"),
        }

    async def get_forecast(
        self,
        latitude: float,
        longitude: float,
    ) -> dict:
        """
        Fetch 48-hour forecast. Returns whether rain is expected and
        overnight low for inversion check.
        """
        url = f"{self.ec_base}/collections/weather-forecast/items"
        params = {
            "LATITUDE": latitude,
            "LONGITUDE": longitude,
            "f": "json",
            "limit": 48,
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        features = data.get("features", [])
        rain_in_24h = any(
            f["properties"].get("PRECIP_PROBABILITY", 0) > 40
            for f in features[:24]
        )
        overnight_lows = [
            f["properties"].get("AIR_TEMP_MIN")
            for f in features
            if f["properties"].get("AIR_TEMP_MIN") is not None
        ]
        overnight_low = min(overnight_lows) if overnight_lows else None

        return {
            "rain_in_24h": rain_in_24h,
            "overnight_low_c": overnight_low,
            "raw_features": features,
        }


weather_client = WeatherClient()
