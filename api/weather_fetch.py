import requests

def get_hourly_weather(lat, lon):

    url = "https://archive-api.open-meteo.com/v1/archive"

    params = {
        "latitude": lat,
        "longitude": lon,

        "start_date": "2025-06-15",
        "end_date": "2025-06-15",

        "hourly": [
            "temperature_2m",
            "relative_humidity_2m",
            "wind_speed_10m",
            "precipitation",
            "surface_pressure",
            "dew_point_2m"
        ]
    }

    response = requests.get(url, params=params)
    data = response.json()["hourly"]

    hours = []

    for i in range(len(data["time"])):

        hours.append({
            "time": data["time"][i],
            "temperature": data["temperature_2m"][i],
            "humidity": data["relative_humidity_2m"][i],
            "wind_speed": data["wind_speed_10m"][i],
            "precipitation": data["precipitation"][i],
            "pressure": data["surface_pressure"][i],
            "dew_point": data["dew_point_2m"][i]
        })

    return hours