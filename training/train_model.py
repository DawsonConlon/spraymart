import pandas as pd
import joblib

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score
from sklearn.metrics import classification_report


# load dataset

data = pd.read_csv("../data/raw/clean_weather_data.csv")


# rename columns

data = data.rename(columns={
    "Temp (°C)": "temperature",
    "Dew Point Temp (°C)": "dew_point",
    "Rel Hum (%)": "humidity",
    "Precip. Amount (mm)": "precipitation",
    "Wind Spd (km/h)": "wind_speed",
    "Wind Dir (10s deg)": "wind_direction",
    "Stn Press (kPa)": "pressure"
})

# feature extraction

# Vapor Pressure Deficit (important for spraying)
data["vpd"] = data["temperature"] - data["dew_point"]


# features we need for the model to predict

features = [
    "temperature",
    "humidity",
    "wind_speed",
    "precipitation",
    "pressure",
    "vpd"
]

X = data[features]


# generate spray label


data["spray"] = (
    (data["wind_speed"] < 15) &
    (data["precipitation"] == 0) &
    (data["temperature"] > 5) & (data["temperature"] < 30) &
    (data["humidity"] > 30) & (data["humidity"] < 90)
).astype(int)

y = data["spray"]


# training/testing dataset split

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42
)


# pipeline

pipeline = Pipeline([
    ("scaler", StandardScaler()),
    ("model", LogisticRegression())
])


# train the model

pipeline.fit(X_train, y_train)


# model evaluation

preds = pipeline.predict(X_test)

print("Accuracy:", accuracy_score(y_test, preds))


# save the model

joblib.dump(pipeline, "../models/spray_model.pkl")

print(classification_report(y_test, preds))