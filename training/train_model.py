import pandas as pd
import joblib

from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier
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

# VPD
data["vpd"] = data["temperature"] - data["dew_point"]

# add growth stage (example random for training)
import numpy as np
data["growth_stage"] = np.random.randint(1,6,len(data))

# features
features = [
    "temperature",
    "humidity",
    "wind_speed",
    "precipitation",
    "pressure",
    "vpd",
    "growth_stage"
]

X = data[features]

# spray label
data["spray"] = (
    (data["wind_speed"] < 15) &
    (data["precipitation"] == 0) &
    (data["temperature"] > 5) & (data["temperature"] < 30) &
    (data["humidity"] > 30) & (data["humidity"] < 90)
).astype(int)

y = data["spray"]

# split
X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42
)

# decision tree
model = DecisionTreeClassifier(
    max_depth=5,
    random_state=42
)

model.fit(X_train, y_train)

# evaluate
preds = model.predict(X_test)

print("Accuracy:", accuracy_score(y_test, preds))
print(classification_report(y_test, preds))

# save
joblib.dump(model, "../models/spray_model.pkl")