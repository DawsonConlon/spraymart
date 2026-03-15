def explain_decision(weather):

    reasons = []

    if weather["wind_speed"] >= 15:
        reasons.append("Wind too strong")

    if weather["precipitation"] > 0:
        reasons.append("Rain detected")

    if weather["temperature"] < 5 or weather["temperature"] > 30:
        reasons.append("Temperature outside spray range")

    if weather["humidity"] < 30 or weather["humidity"] > 90:
        reasons.append("Humidity outside safe range")

    if not reasons:
        reasons.append("All spray conditions are safe")

    return reasons