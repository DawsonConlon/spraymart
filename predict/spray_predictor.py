import joblib
import pandas as pd

model = joblib.load("models/spray_model.pkl")

def predict_spray(weather, growth_stage):

    temp = weather["temperature"]
    humidity = weather["humidity"]
    wind_speed = weather["wind_speed"]
    precipitation = weather["precipitation"]
    pressure = weather["pressure"]
    dew_point = weather["dew_point"]

    vpd = temp - dew_point

    features = pd.DataFrame([{
        "temperature": temp,
        "humidity": humidity,
        "wind_speed": wind_speed,
        "precipitation": precipitation,
        "pressure": pressure,
        "vpd": vpd,
        "growth_stage": growth_stage
    }])

    prediction = model.predict(features)[0]

    return "SPRAY" if prediction == 1 else "DO NOT SPRAY"

'''if __name__ == "__main__":

    weather = {
        "temperature": 15.6,
        "dew_point": 1.4,
        "humidity": 38,
        "precipitation": 0,
        "wind_speed": 11,
        "pressure": 92.42
    }

    growth_stage = 3

    result = predict_spray(weather, growth_stage)

    print("Prediction:", result)'''