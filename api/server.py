import json
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

from api.weather_fetch import get_hourly_weather


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

    values = list(checks.values())
    good_count = values.count("good")
    iffy_count = values.count("iffy")
    bad_count = values.count("bad")

    # Majority-based day status: whichever category has the most metrics wins.
    # This ensures a day can still be green if only one metric is borderline.
    if good_count >= iffy_count and good_count >= bad_count:
        status = "good"
    elif bad_count > good_count and bad_count >= iffy_count:
        status = "bad"
    else:
        status = "iffy"

    return status, reasons


def build_daily_forecast(hours, growth_stage=3):

    grouped = {}
    for entry in hours:
        dt = datetime.fromisoformat(entry["time"])
        day_key = dt.date().isoformat()
        grouped.setdefault(day_key, []).append(
            {
                "time": dt,
                "temperature": entry["temperature"],
                "humidity": entry["humidity"],
                "wind": entry["wind_speed"],
                "precip": entry["precipitation"],
                "pressure": entry["pressure"],
                "dew": entry["dew_point"],
            }
        )

    days = []
    for day_key in sorted(grouped.keys())[:7]:
        entries = grouped[day_key]

        # Focus the spray window on the practical morning period: 5 am through 2 pm.
        spray_window = [e for e in entries if 5 <= e["time"].hour <= 14] or entries

        # Chart only the same 5 am through 2 pm spray window.
        all_day = [e for e in sorted(entries, key=lambda x: x["time"]) if 5 <= e["time"].hour <= 14] or sorted(entries, key=lambda x: x["time"])

        avg_temp = sum(e["temperature"] for e in spray_window) / len(spray_window)
        avg_humidity = sum(e["humidity"] for e in spray_window) / len(spray_window)
        avg_wind = sum(e["wind"] for e in spray_window) / len(spray_window)
        total_precip = sum(e["precip"] for e in spray_window)
        avg_dew_gap = sum((e["temperature"] - e["dew"]) for e in spray_window) / len(spray_window)

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
                "timeLabels": [e["time"].strftime("%H:%M") for e in all_day],
                "wind": [round(e["wind"], 1) for e in all_day],
                "temp": [round(e["temperature"], 1) for e in all_day],
                "humidity": [round(e["humidity"], 0) for e in all_day],
                "precip": [round(e["precip"], 1) for e in all_day],
                "dew": [round(e["temperature"] - e["dew"], 1) for e in all_day],
                "pressure": [round(e["pressure"], 1) for e in all_day],
                "gdd": [gdd_stage for _ in all_day],
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
        start_date = params.get("start_date", ["2025-06-15"])[0]
        end_date = params.get("end_date", ["2025-06-21"])[0]

        try:
            hours = get_hourly_weather(lat=lat, lon=lon, start_date=start_date, end_date=end_date)
            days = build_daily_forecast(hours, growth_stage=growth_stage)
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
                "source": "Open-Meteo Archive",
                "range": {
                    "start_date": start_date,
                    "end_date": end_date,
                },
                "days": days,
            },
        )


def run_server(host="0.0.0.0", port=8000):
    server = HTTPServer((host, port), ForecastHandler)
    print(f"Forecast API running at http://{host}:{port}/api/forecast")
    server.serve_forever()


if __name__ == "__main__":
    run_server()
