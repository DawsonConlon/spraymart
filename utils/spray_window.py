def find_spray_windows(hourly_weather):

    windows = []

    for w in hourly_weather:

        if (
            w["wind_speed"] < 15 and
            w["precipitation"] == 0 and
            5 < w["temperature"] < 30 and
            30 < w["humidity"] < 90
        ):
            windows.append(w["time"])

    return windows