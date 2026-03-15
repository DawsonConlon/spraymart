import json
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

import requests


def _safe_float(value, default):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def fetch_open_meteo_forecast(lat: float, lon: float, days: int = 7):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": [
            "temperature_2m",
            "relative_humidity_2m",
            "wind_speed_10m",
            "precipitation",
            "surface_pressure",
            "dew_point_2m",
        ],
        "forecast_days": days,
        "timezone": "auto",
    }

    response = requests.get(url, params=params, timeout=20)
    response.raise_for_status()
    return response.json()


def evaluate_status(day):
    checks = {
        "wind": "good" if day["windKmh"] <= 10 else "iffy" if day["windKmh"] <= 15 else "bad",
        "temp": "bad"
        if day["temperatureC"] < 10 or day["temperatureC"] > 30
        else "good"
        if 12 <= day["temperatureC"] <= 25
        else "iffy",
        "humidity": "bad"
        if day["humidityPct"] < 40 or day["humidityPct"] > 90
        else "good"
        if 50 <= day["humidityPct"] <= 80
        else "iffy",
        "precip": "bad"
        if day["precipitationMm"] > 2
        else "good"
        if day["precipitationMm"] == 0
        else "iffy",
        "dew": "bad"
        if day["dewPointGap"] < 3 or day["dewPointGap"] > 20
        else "good"
        if 5 <= day["dewPointGap"] <= 15
        else "iffy",
        "pressure": "good"
        if 1 <= day["pressureTrend"] <= 3
        else "iffy"
        if -1 <= day["pressureTrend"] <= 1
        else "bad",
        "gdd": "bad"
        if day["gddStage"] < 200 or day["gddStage"] > 800
        else "good"
        if 350 <= day["gddStage"] <= 600
        else "iffy",
    }

    reasons = []
    if checks["wind"] == "bad":
        reasons.append("Wind is too strong")
    if checks["temp"] == "bad":
        reasons.append("Temperature is outside safe range")
    if checks["humidity"] == "bad":
        reasons.append("Humidity is outside safe range")
    if checks["precip"] == "bad":
        reasons.append("Rain is too heavy")
    if checks["dew"] == "bad":
        reasons.append("Dew point gap is outside safe range")
    if checks["pressure"] == "bad":
        reasons.append("Pressure trend is too extreme")
    if checks["gdd"] == "bad":
        reasons.append("Growth stage is outside optimal range")

    if checks["wind"] == "iffy":
        reasons.append("Wind is close to limit")
    if checks["temp"] == "iffy":
        reasons.append("Temperature is near threshold")
    if checks["humidity"] == "iffy":
        reasons.append("Humidity is near threshold")
    if checks["precip"] == "iffy":
        reasons.append("Chance of rain is rising")
    if checks["dew"] == "iffy":
        reasons.append("Dew point gap is near threshold")
    if checks["pressure"] == "iffy":
        reasons.append("Pressure trend is near threshold")
    if checks["gdd"] == "iffy":
        reasons.append("Growth stage is near threshold")

    status = "bad" if "bad" in checks.values() else "iffy" if "iffy" in checks.values() else "good"
    return status, reasons


def build_daily_forecast(raw, growth_stage=3):
    hourly = raw["hourly"]
    times = hourly["time"]

    grouped = {}
    for i, iso_time in enumerate(times):
        dt = datetime.fromisoformat(iso_time)
        day_key = dt.date().isoformat()
        grouped.setdefault(day_key, []).append(
            {
                "time": dt,
                "temperature": hourly["temperature_2m"][i],
                "humidity": hourly["relative_humidity_2m"][i],
                "wind": hourly["wind_speed_10m"][i],
                "precip": hourly["precipitation"][i],
                "pressure": hourly["surface_pressure"][i],
                "dew": hourly["dew_point_2m"][i],
            }
        )

    days = []
    for day_key in sorted(grouped.keys())[:7]:
        entries = grouped[day_key]

        # Use daytime window when possible for practical spray checks.
        daytime = [e for e in entries if 6 <= e["time"].hour <= 18] or entries

        avg_temp = sum(e["temperature"] for e in daytime) / len(daytime)
        avg_humidity = sum(e["humidity"] for e in daytime) / len(daytime)
        avg_wind = sum(e["wind"] for e in daytime) / len(daytime)
        total_precip = sum(e["precip"] for e in daytime)
        avg_dew_gap = sum((e["temperature"] - e["dew"]) for e in daytime) / len(daytime)

        pressure_by_hour = sorted(entries, key=lambda x: x["time"])
        p_start = pressure_by_hour[0]["pressure"]
        p_3h = pressure_by_hour[min(3, len(pressure_by_hour) - 1)]["pressure"]
        pressure_trend = p_3h - p_start

        gdd_stage = 200 + growth_stage * 100

        day = {
            "date": day_key,
            "temperatureC": round(avg_temp, 1),
            "humidityPct": round(avg_humidity, 0),
            "windKmh": round(avg_wind, 1),
            "precipitationMm": round(total_precip, 1),
            "dewPointGap": round(avg_dew_gap, 1),
            "pressureTrend": round(pressure_trend, 1),
            "gddStage": gdd_stage,
            "hourly": {
                "wind": [round(e["wind"], 1) for e in entries[:8]],
                "temp": [round(e["temperature"], 1) for e in entries[:8]],
                "humidity": [round(e["humidity"], 0) for e in entries[:8]],
                "precip": [round(e["precip"], 1) for e in entries[:8]],
                "dew": [round(e["temperature"] - e["dew"], 1) for e in entries[:8]],
                "pressure": [round(e["pressure"], 1) for e in entries[:8]],
                "gdd": [gdd_stage for _ in range(min(8, len(entries)))],
            },
        }

        status, reasons = evaluate_status(day)
        day["status"] = status
        day["reasons"] = reasons
        days.append(day)

    return days


class ForecastHandler(BaseHTTPRequestHandler):
    def _send_json(self, status_code, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self._send_json(200, {"ok": True})

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path != "/api/forecast":
            self._send_json(404, {"error": "Not found"})
            return

        params = parse_qs(parsed.query)
        lat = _safe_float(params.get("lat", [52.13])[0], 52.13)
        lon = _safe_float(params.get("lon", [-106.67])[0], -106.67)
        growth_stage = _safe_int(params.get("growth_stage", [3])[0], 3)

        try:
            raw = fetch_open_meteo_forecast(lat=lat, lon=lon, days=7)
            days = build_daily_forecast(raw, growth_stage=growth_stage)
        except Exception as exc:
            self._send_json(500, {"error": str(exc)})
            return

        self._send_json(
            200,
            {
                "location": {
                    "lat": lat,
                    "lon": lon,
                    "label": "SASKATOON, SK",
                },
                "source": "Open-Meteo",
                "days": days,
            },
        )


def run_server(host="0.0.0.0", port=8000):
    server = HTTPServer((host, port), ForecastHandler)
    print(f"Forecast API running at http://{host}:{port}/api/forecast")
    server.serve_forever()


if __name__ == "__main__":
    run_server()
