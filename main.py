from api.weather_fetch import get_hourly_weather
from predict.spray_predictor import predict_spray
from utils.spray_window import find_spray_windows
from datetime import datetime

lat = 52.13
lon = -106.67

growth_stage = 3

weather_hours = get_hourly_weather(lat, lon)

windows = find_spray_windows(weather_hours)

print("\nSPRAY WINDOW ANALYSIS")
print("---------------------")

if not windows:
    print("No safe spray window detected today.")
else:

    # convert timestamps to readable times
    readable = []
    for w in windows:
        t = datetime.fromisoformat(w)
        readable.append(t.strftime("%I:%M %p"))

    # group into a single range
    start = readable[0]
    end = readable[min(len(readable)-1, 5)]

    print(f"Best Spray Window: {start} - {end}")

current_weather = weather_hours[0]

result = predict_spray(current_weather, growth_stage)

print("\nCURRENT CONDITIONS")
print("------------------")

temp = current_weather["temperature"]
wind = current_weather["wind_speed"]
humidity = current_weather["humidity"]
rain = current_weather["precipitation"]

print(f"Temperature: {temp}°C")
print(f"Wind: {wind} km/h")
print(f"Humidity: {humidity}%")

if rain > 0:
    print(f"Rain: {rain} mm")
else:
    print("Rain: none")

print("\nRECOMMENDATION")
print("--------------")

print(result)